import 'package:flutter/material.dart';

import '../../../core/lumenis_core_client.dart';
import '../../../core/lumenis_theme.dart';
import 'sys06_browser_repository.dart';

/// SYSTEM's single-page controlled reader.
///
/// It displays a server-owned, permission-checked page frame.  It is not a
/// WebView and never opens the user's installed browser, profile or session.
/// The preview deliberately remains non-interactive until a separately owned
/// Browser input contract has been accepted.
class Sys06Screen extends StatefulWidget {
  const Sys06Screen({required this.client, this.browserRepository, super.key});

  final LumenisCoreClient client;
  final Sys06BrowserRepository? browserRepository;

  @override
  State<Sys06Screen> createState() => _Sys06ScreenState();
}

class _Sys06ScreenState extends State<Sys06Screen> {
  late Sys06BrowserRepository _repository;
  late final TextEditingController _addressController;

  Sys06BrowserSession? _session;
  Sys06BrowserFrame? _frame;
  _Sys06Notice _notice = _Sys06Notice.ready;
  int _generation = 0;
  int? _activeOperation;
  bool _busy = false;
  bool _stopping = false;

  @override
  void initState() {
    super.initState();
    _repository = _repositoryFor(widget);
    _addressController = TextEditingController();
  }

  @override
  void didUpdateWidget(covariant Sys06Screen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (identical(oldWidget.client, widget.client) &&
        identical(oldWidget.browserRepository, widget.browserRepository)) {
      return;
    }
    _generation++;
    _activeOperation = null;
    _repository = _repositoryFor(widget);
    _session = null;
    _frame = null;
    _notice = _Sys06Notice.ready;
    _busy = false;
    _stopping = false;
    _addressController.clear();
  }

  @override
  void dispose() {
    _addressController.dispose();
    super.dispose();
  }

  Future<void> _open() => _run((generation, repository) async {
    final session = await repository.open();
    if (!_isCurrent(generation, repository)) return;
    _adoptSession(session, clearFrame: true);
    await _readFrame(session, generation, repository);
  });

  Future<void> _navigate() => _run((generation, repository) async {
    final session = _session;
    if (session == null || !session.allowedActions.contains('navigate')) return;
    final address = _addressController.text.trim();
    final parsed = Uri.tryParse(address);
    if (parsed == null ||
        parsed.host.isEmpty ||
        (parsed.scheme != 'https' && parsed.scheme != 'http') ||
        parsed.userInfo.isNotEmpty) {
      if (mounted) setState(() => _notice = _Sys06Notice.invalidAddress);
      return;
    }
    if (mounted) {
      setState(() {
        _frame = null;
        _notice = _Sys06Notice.navigating;
      });
    }
    final updated = await repository.navigate(
      sessionId: session.sessionId,
      url: address,
    );
    if (!_isCurrentSession(generation, repository, session.sessionId)) return;
    _adoptSession(updated, clearFrame: true);
    await _readFrame(updated, generation, repository);
  });

  Future<void> _reload() => _run((generation, repository) async {
    final session = _session;
    if (session == null || !session.allowedActions.contains('reload')) return;
    if (mounted) {
      setState(() {
        _frame = null;
        _notice = _Sys06Notice.navigating;
      });
    }
    final updated = await repository.reload(session.sessionId);
    if (!_isCurrentSession(generation, repository, session.sessionId)) return;
    _adoptSession(updated, clearFrame: true);
    await _readFrame(updated, generation, repository);
  });

  Future<void> _refreshFrame() => _run((generation, repository) async {
    final session = _session;
    if (session == null) return;
    await _readFrame(session, generation, repository);
  });

  Future<void> _stop() async {
    final session = _session;
    if (session == null || _stopping) return;
    final repository = _repository;
    final generation = ++_generation;
    _activeOperation = null;
    setState(() {
      _busy = false;
      _stopping = true;
      _frame = null;
      _notice = _Sys06Notice.stopping;
    });
    try {
      await repository.stop(session.sessionId);
      if (!_isCurrentSession(generation, repository, session.sessionId)) return;
      setState(() {
        _session = null;
        _frame = null;
        _addressController.clear();
        _notice = _Sys06Notice.closed;
        _stopping = false;
      });
    } catch (error) {
      if (!_isCurrentSession(generation, repository, session.sessionId)) return;
      setState(() {
        _frame = null;
        _notice = _noticeForError(error);
        _stopping = false;
      });
    }
  }

  Future<void> _readFrame(
    Sys06BrowserSession expected,
    int generation,
    Sys06BrowserRepository repository,
  ) async {
    if (!expected.allowedActions.contains('frame') ||
        expected.targetId == null) {
      if (_isCurrentSession(generation, repository, expected.sessionId)) {
        setState(() => _notice = _Sys06Notice.enterAddress);
      }
      return;
    }
    try {
      final frame = await repository.readFrame(expected.sessionId);
      if (!_isCurrentSession(generation, repository, expected.sessionId)) {
        return;
      }
      final current = _session;
      if (current == null ||
          frame.frame.targetId != current.targetId ||
          frame.frame.pageRevision != current.pageRevision) {
        return;
      }
      setState(() {
        _frame = frame;
        _notice = _Sys06Notice.previewReady;
      });
    } catch (error) {
      if (!_isCurrentSession(generation, repository, expected.sessionId)) {
        return;
      }
      setState(() {
        _frame = null;
        _notice = _noticeForError(error);
      });
    }
  }

  Future<void> _run(
    Future<void> Function(int generation, Sys06BrowserRepository repository)
    operation,
  ) async {
    if (_busy || _stopping) return;
    final generation = ++_generation;
    final repository = _repository;
    _activeOperation = generation;
    setState(() => _busy = true);
    try {
      await operation(generation, repository);
    } catch (error) {
      if (_isCurrent(generation, repository)) {
        setState(() {
          _frame = null;
          _notice = _noticeForError(error);
        });
      }
    } finally {
      if (mounted && _activeOperation == generation) {
        _activeOperation = null;
        setState(() => _busy = false);
      }
    }
  }

  bool _isCurrent(int generation, Sys06BrowserRepository repository) =>
      mounted &&
      generation == _generation &&
      identical(repository, _repository);

  bool _isCurrentSession(
    int generation,
    Sys06BrowserRepository repository,
    String sessionId,
  ) => _isCurrent(generation, repository) && _session?.sessionId == sessionId;

  Sys06BrowserRepository _repositoryFor(Sys06Screen source) =>
      source.browserRepository ??
      CoreSys06BrowserRepository(client: source.client);

  void _adoptSession(Sys06BrowserSession session, {required bool clearFrame}) {
    setState(() {
      _session = session;
      if (clearFrame) _frame = null;
      _notice = session.targetId == null
          ? _Sys06Notice.enterAddress
          : _Sys06Notice.reading;
      // The server strips query/fragment material before it reaches this field.
      // A raw typed address is never stored after navigation succeeds.
      if (session.currentUrl.isNotEmpty) {
        _addressController.text = session.currentUrl;
      }
    });
  }

  _Sys06Notice _noticeForError(Object error) {
    if (error is LumenisCoreException) {
      if (error.statusCode == 401 || error.statusCode == 403) {
        return _Sys06Notice.accessUnavailable;
      }
      return switch (error.errorCode) {
        'BROWSER_FRAME_PENDING' => _Sys06Notice.framePending,
        'BROWSER_FRAME_EMPTY' => _Sys06Notice.frameEmpty,
        'BROWSER_CAPACITY_OCCUPIED' => _Sys06Notice.capacityOccupied,
        'BROWSER_PERMISSION_DENIED' => _Sys06Notice.accessUnavailable,
        'BROWSER_ACTOR_REQUIRED' => _Sys06Notice.accessUnavailable,
        _ => _Sys06Notice.unavailable,
      };
    }
    return error is FormatException
        ? _Sys06Notice.invalidAddress
        : _Sys06Notice.unavailable;
  }

  @override
  Widget build(BuildContext context) {
    final copy = _Sys06Copy.of(context);
    return ColoredBox(
      color: LumenisTheme.of(context).canvas,
      child: SafeArea(
        child: LayoutBuilder(
          builder: (context, constraints) {
            final narrow = constraints.maxWidth < 720;
            final constrainedHeight = constraints.maxHeight < 620;
            final padding = EdgeInsets.fromLTRB(
              narrow ? 18 : 30,
              narrow ? 18 : 24,
              narrow ? 18 : 30,
              narrow ? 20 : 26,
            );
            final header = _ReaderHeader(
              copy: copy,
              session: _session,
              notice: _notice,
            );
            final controls = _ReaderControls(
              copy: copy,
              addressController: _addressController,
              session: _session,
              busy: _busy || _stopping,
              stopping: _stopping,
              onOpen: _open,
              onNavigate: _navigate,
              onReload: _reload,
              onRefreshFrame: _refreshFrame,
              onStop: _stop,
            );
            final preview = _ReaderPreview(
              copy: copy,
              frame: _frame,
              notice: _notice,
              busy: _busy || _stopping,
              onRefresh: _refreshFrame,
            );
            final content = _ReaderBoundary(copy: copy);
            if (constrainedHeight) {
              return SingleChildScrollView(
                padding: padding,
                child: Center(
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 1500),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        header,
                        const SizedBox(height: 18),
                        controls,
                        const SizedBox(height: 14),
                        SizedBox(height: 440, child: preview),
                        const SizedBox(height: 14),
                        content,
                      ],
                    ),
                  ),
                ),
              );
            }
            return Padding(
              padding: padding,
              child: Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 1500),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      header,
                      const SizedBox(height: 18),
                      controls,
                      const SizedBox(height: 14),
                      Expanded(child: preview),
                      const SizedBox(height: 14),
                      content,
                    ],
                  ),
                ),
              ),
            );
          },
        ),
      ),
    );
  }
}

class _ReaderHeader extends StatelessWidget {
  const _ReaderHeader({
    required this.copy,
    required this.session,
    required this.notice,
  });

  final _Sys06Copy copy;
  final Sys06BrowserSession? session;
  final _Sys06Notice notice;

  @override
  Widget build(BuildContext context) {
    final theme = LumenisTheme.of(context);
    return Semantics(
      header: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            copy.text('eyebrow'),
            style: TextStyle(
              color: theme.system,
              fontWeight: FontWeight.w700,
              letterSpacing: 1.1,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            copy.text('title'),
            style: TextStyle(
              color: theme.foreground,
              fontSize: 28,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            copy.text('subtitle'),
            style: TextStyle(color: theme.muted, height: 1.45),
          ),
          const SizedBox(height: 10),
          Semantics(
            liveRegion: true,
            child: Text(
              copy.notice(notice, session: session),
              key: const ValueKey('sys06-status'),
              style: TextStyle(
                color: notice.isFailure ? theme.caution : theme.quiet,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _ReaderControls extends StatelessWidget {
  const _ReaderControls({
    required this.copy,
    required this.addressController,
    required this.session,
    required this.busy,
    required this.stopping,
    required this.onOpen,
    required this.onNavigate,
    required this.onReload,
    required this.onRefreshFrame,
    required this.onStop,
  });

  final _Sys06Copy copy;
  final TextEditingController addressController;
  final Sys06BrowserSession? session;
  final bool busy;
  final bool stopping;
  final VoidCallback onOpen;
  final VoidCallback onNavigate;
  final VoidCallback onReload;
  final VoidCallback onRefreshFrame;
  final VoidCallback onStop;

  @override
  Widget build(BuildContext context) {
    final active = session;
    final canNavigate =
        !busy && active?.allowedActions.contains('navigate') == true;
    final canReload =
        !busy && active?.allowedActions.contains('reload') == true;
    final canFrame = !busy && active?.allowedActions.contains('frame') == true;
    return DecoratedBox(
      decoration: BoxDecoration(
        color: LumenisTheme.of(context).surfaceRaised,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: LumenisTheme.of(context).line),
      ),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: active == null
            ? Align(
                alignment: Alignment.centerLeft,
                child: FilledButton.icon(
                  key: const ValueKey('sys06-open'),
                  onPressed: busy ? null : onOpen,
                  icon: const Icon(Icons.travel_explore_rounded),
                  label: Text(copy.text('open')),
                ),
              )
            : Wrap(
                alignment: WrapAlignment.start,
                crossAxisAlignment: WrapCrossAlignment.center,
                spacing: 8,
                runSpacing: 8,
                children: [
                  SizedBox(
                    width: MediaQuery.sizeOf(context).width < 520
                        ? double.infinity
                        : 420,
                    child: TextField(
                      key: const ValueKey('sys06-address'),
                      controller: addressController,
                      enabled: canNavigate,
                      keyboardType: TextInputType.url,
                      textInputAction: TextInputAction.go,
                      autocorrect: false,
                      enableSuggestions: false,
                      onSubmitted: (_) => onNavigate(),
                      decoration: InputDecoration(
                        isDense: true,
                        prefixIcon: const Icon(Icons.language_rounded),
                        labelText: copy.text('address'),
                        hintText: copy.text('addressHint'),
                      ),
                    ),
                  ),
                  FilledButton(
                    key: const ValueKey('sys06-go'),
                    onPressed: canNavigate ? onNavigate : null,
                    child: Text(copy.text('go')),
                  ),
                  Tooltip(
                    message: copy.text('reload'),
                    child: IconButton(
                      key: const ValueKey('sys06-reload'),
                      onPressed: canReload ? onReload : null,
                      icon: const Icon(Icons.refresh_rounded),
                    ),
                  ),
                  Tooltip(
                    message: copy.text('refreshPreview'),
                    child: IconButton(
                      key: const ValueKey('sys06-refresh-frame'),
                      onPressed: canFrame ? onRefreshFrame : null,
                      icon: const Icon(Icons.photo_camera_back_outlined),
                    ),
                  ),
                  OutlinedButton.icon(
                    key: const ValueKey('sys06-stop'),
                    onPressed: stopping ? null : onStop,
                    icon: const Icon(Icons.stop_circle_outlined),
                    label: Text(copy.text('end')),
                  ),
                ],
              ),
      ),
    );
  }
}

class _ReaderPreview extends StatelessWidget {
  const _ReaderPreview({
    required this.copy,
    required this.frame,
    required this.notice,
    required this.busy,
    required this.onRefresh,
  });

  final _Sys06Copy copy;
  final Sys06BrowserFrame? frame;
  final _Sys06Notice notice;
  final bool busy;
  final VoidCallback onRefresh;

  @override
  Widget build(BuildContext context) {
    final theme = LumenisTheme.of(context);
    final value = frame;
    return DecoratedBox(
      decoration: BoxDecoration(
        color: theme.surface,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: theme.line),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(18),
        child: value == null
            ? _PreviewEmpty(
                copy: copy,
                notice: notice,
                busy: busy,
                onRefresh: onRefresh,
              )
            : Semantics(
                key: const ValueKey('sys06-preview-readonly'),
                label: copy.text('previewSemantics'),
                image: true,
                child: Stack(
                  fit: StackFit.expand,
                  children: [
                    ColoredBox(
                      color: Colors.black,
                      child: InteractiveViewer(
                        minScale: 1,
                        maxScale: 4,
                        child: Center(
                          child: Image.memory(
                            value.frame.bytes,
                            key: const ValueKey('sys06-frame'),
                            fit: BoxFit.contain,
                            gaplessPlayback: false,
                            filterQuality: FilterQuality.medium,
                          ),
                        ),
                      ),
                    ),
                    Positioned(
                      left: 12,
                      right: 12,
                      top: 12,
                      child: IgnorePointer(
                        child: DecoratedBox(
                          decoration: BoxDecoration(
                            color: Colors.black.withValues(alpha: 0.68),
                            borderRadius: BorderRadius.circular(9),
                          ),
                          child: Padding(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 10,
                              vertical: 7,
                            ),
                            child: Text(
                              copy.previewTimestamp(value.frame.capturedAt),
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 12,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
      ),
    );
  }
}

class _PreviewEmpty extends StatelessWidget {
  const _PreviewEmpty({
    required this.copy,
    required this.notice,
    required this.busy,
    required this.onRefresh,
  });

  final _Sys06Copy copy;
  final _Sys06Notice notice;
  final bool busy;
  final VoidCallback onRefresh;

  @override
  Widget build(BuildContext context) {
    final theme = LumenisTheme.of(context);
    final progress =
        busy ||
        notice == _Sys06Notice.navigating ||
        notice == _Sys06Notice.reading;
    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 420),
        child: Padding(
          padding: const EdgeInsets.all(28),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (progress)
                const SizedBox(
                  height: 30,
                  width: 30,
                  child: CircularProgressIndicator(strokeWidth: 2.5),
                )
              else
                Icon(
                  notice.isFailure
                      ? Icons.portable_wifi_off_rounded
                      : Icons.pageview_outlined,
                  color: notice.isFailure ? theme.caution : theme.system,
                  size: 34,
                ),
              const SizedBox(height: 14),
              Text(
                copy.emptyTitle(notice),
                key: const ValueKey('sys06-preview-state'),
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: theme.foreground,
                  fontWeight: FontWeight.w700,
                  fontSize: 18,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                copy.emptyDetail(notice),
                textAlign: TextAlign.center,
                style: TextStyle(color: theme.muted, height: 1.45),
              ),
              if (notice.canRetry) ...[
                const SizedBox(height: 16),
                OutlinedButton.icon(
                  key: const ValueKey('sys06-retry'),
                  onPressed: busy ? null : onRefresh,
                  icon: const Icon(Icons.refresh_rounded),
                  label: Text(copy.text('retry')),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _ReaderBoundary extends StatelessWidget {
  const _ReaderBoundary({required this.copy});

  final _Sys06Copy copy;

  @override
  Widget build(BuildContext context) => Semantics(
    container: true,
    label: copy.text('boundaryTitle'),
    child: Text(
      copy.text('boundary'),
      style: TextStyle(color: LumenisTheme.of(context).quiet, height: 1.4),
    ),
  );
}

enum _Sys06Notice {
  ready,
  enterAddress,
  stopping,
  navigating,
  reading,
  previewReady,
  framePending,
  frameEmpty,
  capacityOccupied,
  accessUnavailable,
  invalidAddress,
  unavailable,
  closed,
}

extension on _Sys06Notice {
  bool get isFailure => switch (this) {
    _Sys06Notice.frameEmpty ||
    _Sys06Notice.capacityOccupied ||
    _Sys06Notice.accessUnavailable ||
    _Sys06Notice.invalidAddress ||
    _Sys06Notice.unavailable => true,
    _ => false,
  };

  bool get canRetry => switch (this) {
    _Sys06Notice.framePending ||
    _Sys06Notice.frameEmpty ||
    _Sys06Notice.unavailable => true,
    _ => false,
  };
}

class _Sys06Copy {
  const _Sys06Copy(this._language);

  final String _language;

  static _Sys06Copy of(BuildContext context) {
    final language = Localizations.localeOf(context).languageCode;
    return _Sys06Copy(
      language == 'ko'
          ? 'ko'
          : language == 'en'
          ? 'en'
          : 'zh',
    );
  }

  String text(String key) => (_values[_language]?[key] ?? _values['en']![key])!;

  String notice(_Sys06Notice notice, {Sys06BrowserSession? session}) {
    if (notice == _Sys06Notice.previewReady &&
        session?.currentTitle.isNotEmpty == true) {
      return '${text('previewReady')} · ${session!.currentTitle}';
    }
    return text('notice.${notice.name}');
  }

  String emptyTitle(_Sys06Notice notice) => text('empty.${notice.name}.title');

  String emptyDetail(_Sys06Notice notice) =>
      text('empty.${notice.name}.detail');

  String previewTimestamp(DateTime timestamp) =>
      '${text('preview')} · ${timestamp.toLocal().toIso8601String().replaceFirst('T', ' ').split('.').first}';

  static const _values = <String, Map<String, String>>{
    'zh': {
      'eyebrow': 'SYSTEM · 受控来源阅读',
      'title': '内置来源阅读器',
      'subtitle': '页面在序境受控会话中读取，不会跳转或使用你的个人浏览器。',
      'open': '打开受控阅读器',
      'address': '允许的公开来源地址',
      'addressHint': 'https://example.com',
      'go': '前往',
      'reload': '重新加载页面',
      'refreshPreview': '更新只读预览',
      'end': '结束会话',
      'retry': '重试预览',
      'preview': '只读页面预览',
      'previewSemantics': '只读页面预览。此区域不可点击、输入或远程滚动。',
      'boundaryTitle': '安全边界',
      'boundary':
          '预览只显示当前已授权页面的短暂快照。它不会读取个人浏览器、Cookie、账号、端口或本地路径；点击、输入和远程滚动尚未开放。',
      'previewReady': '已更新只读预览',
      'notice.ready': '尚未开启受控会话。',
      'notice.enterAddress': '会话已开启。输入一个允许的公开来源地址。',
      'notice.stopping': '正在请求结束受控会话。',
      'notice.navigating': '正在请求受控导航。',
      'notice.reading': '正在读取已授权页面。',
      'notice.previewReady': '已更新只读预览。',
      'notice.framePending': '页面仍在准备预览，可稍后更新。',
      'notice.frameEmpty': '页面没有可用的可视预览。',
      'notice.capacityOccupied': '受控浏览容量暂被其他会话占用。',
      'notice.accessUnavailable': '当前工作区没有此浏览权限。',
      'notice.invalidAddress': '请输入一个有效的 http 或 https 地址。',
      'notice.unavailable': '受控阅读暂时不可用。',
      'notice.closed': '受控会话已结束。',
      'empty.ready.title': '在序境内开始读取',
      'empty.ready.detail': '先开启受控会话，再输入一个允许的公开来源地址。',
      'empty.enterAddress.title': '输入来源地址',
      'empty.enterAddress.detail': '导航成功后，系统会显示已授权页面的只读快照。',
      'empty.stopping.title': '正在结束会话',
      'empty.stopping.detail': '正在向当前受控会话请求停止。',
      'empty.navigating.title': '正在导航',
      'empty.navigating.detail': '不会打开外部浏览器。',
      'empty.reading.title': '正在生成预览',
      'empty.reading.detail': '页面加载完成后可更新快照。',
      'empty.previewReady.title': '预览已更新',
      'empty.previewReady.detail': '当前预览已失效，请重新读取。',
      'empty.framePending.title': '页面仍在准备',
      'empty.framePending.detail': '等待页面绘制后再更新预览。',
      'empty.frameEmpty.title': '没有可用预览',
      'empty.frameEmpty.detail': '这不代表来源为空或采集完成。',
      'empty.capacityOccupied.title': '受控浏览容量被占用',
      'empty.capacityOccupied.detail': '其他会话不会被识别、关闭或接管。',
      'empty.accessUnavailable.title': '浏览权限不可用',
      'empty.accessUnavailable.detail': '请返回工作区继续其他任务，权限恢复后再试。',
      'empty.invalidAddress.title': '地址不可用',
      'empty.invalidAddress.detail': '只接受无凭证的 http 或 https 公开地址。',
      'empty.unavailable.title': '预览暂时不可用',
      'empty.unavailable.detail': '不会保留旧页面或伪造成功状态。',
      'empty.closed.title': '会话已结束',
      'empty.closed.detail': '需要时可重新开启一个受控会话。',
    },
    'en': {
      'eyebrow': 'SYSTEM · CONTROLLED SOURCE READING',
      'title': 'Internal source reader',
      'subtitle':
          'The page is read in a LUMENIS-controlled session. Your personal browser is never opened or used.',
      'open': 'Open controlled reader',
      'address': 'Allowed public source address',
      'addressHint': 'https://example.com',
      'go': 'Go',
      'reload': 'Reload page',
      'refreshPreview': 'Refresh read-only preview',
      'end': 'End session',
      'retry': 'Retry preview',
      'preview': 'Read-only page preview',
      'previewSemantics':
          'Read-only page preview. This area cannot click, type, or scroll the remote page.',
      'boundaryTitle': 'Safety boundary',
      'boundary':
          'The preview contains only a temporary snapshot of the currently authorized page. It never reads a personal browser, cookies, accounts, ports, or local paths. Remote click, typing, and scrolling are not enabled.',
      'previewReady': 'Read-only preview updated',
      'notice.ready': 'No controlled session is open.',
      'notice.enterAddress':
          'Session opened. Enter an allowed public source address.',
      'notice.stopping': 'Requesting the controlled session to stop.',
      'notice.navigating': 'Requesting controlled navigation.',
      'notice.reading': 'Reading the authorized page.',
      'notice.previewReady': 'Read-only preview updated.',
      'notice.framePending': 'The page is still preparing a preview.',
      'notice.frameEmpty': 'The page has no usable visual preview.',
      'notice.capacityOccupied': 'Controlled browsing capacity is occupied.',
      'notice.accessUnavailable': 'This workspace has no browser access.',
      'notice.invalidAddress': 'Enter a valid http or https address.',
      'notice.unavailable': 'Controlled reading is temporarily unavailable.',
      'notice.closed': 'Controlled session ended.',
      'empty.ready.title': 'Read inside LUMENIS',
      'empty.ready.detail':
          'Open a controlled session, then enter an allowed public source address.',
      'empty.enterAddress.title': 'Enter a source address',
      'empty.enterAddress.detail':
          'After navigation, the system shows a read-only snapshot of the authorized page.',
      'empty.stopping.title': 'Ending session',
      'empty.stopping.detail':
          'Requesting stop for the current controlled session.',
      'empty.navigating.title': 'Navigating',
      'empty.navigating.detail': 'No external browser will open.',
      'empty.reading.title': 'Preparing preview',
      'empty.reading.detail': 'Refresh once the page has painted.',
      'empty.previewReady.title': 'Preview updated',
      'empty.previewReady.detail':
          'The current preview expired. Read it again.',
      'empty.framePending.title': 'Page is still preparing',
      'empty.framePending.detail': 'Refresh after the page finishes painting.',
      'empty.frameEmpty.title': 'No usable preview',
      'empty.frameEmpty.detail':
          'This does not mean the source is empty or collection completed.',
      'empty.capacityOccupied.title': 'Controlled capacity occupied',
      'empty.capacityOccupied.detail':
          'Another session is not identified, closed, or taken over.',
      'empty.accessUnavailable.title': 'Browser access unavailable',
      'empty.accessUnavailable.detail':
          'Return to other work and try again after access is restored.',
      'empty.invalidAddress.title': 'Address unavailable',
      'empty.invalidAddress.detail':
          'Only credential-free http or https public addresses are accepted.',
      'empty.unavailable.title': 'Preview temporarily unavailable',
      'empty.unavailable.detail':
          'No old page is kept and no success state is fabricated.',
      'empty.closed.title': 'Session ended',
      'empty.closed.detail': 'Open a new controlled session when needed.',
    },
    'ko': {
      'eyebrow': 'SYSTEM · 제어된 소스 읽기',
      'title': '내장 소스 리더',
      'subtitle': '페이지는 LUMENIS 제어 세션에서 읽습니다. 개인 브라우저를 열거나 사용하지 않습니다.',
      'open': '제어된 리더 열기',
      'address': '허용된 공개 소스 주소',
      'addressHint': 'https://example.com',
      'go': '이동',
      'reload': '페이지 새로고침',
      'refreshPreview': '읽기 전용 미리보기 갱신',
      'end': '세션 종료',
      'retry': '미리보기 재시도',
      'preview': '읽기 전용 페이지 미리보기',
      'previewSemantics':
          '읽기 전용 페이지 미리보기입니다. 이 영역은 원격 페이지를 클릭, 입력 또는 스크롤할 수 없습니다.',
      'boundaryTitle': '안전 경계',
      'boundary':
          '미리보기에는 현재 승인된 페이지의 임시 스냅샷만 표시됩니다. 개인 브라우저, 쿠키, 계정, 포트 또는 로컬 경로를 읽지 않으며 원격 클릭, 입력 및 스크롤은 활성화되지 않았습니다.',
      'previewReady': '읽기 전용 미리보기가 갱신되었습니다',
      'notice.ready': '제어된 세션이 열려 있지 않습니다.',
      'notice.enterAddress': '세션이 열렸습니다. 허용된 공개 소스 주소를 입력하세요.',
      'notice.stopping': '제어 세션 종료를 요청하고 있습니다.',
      'notice.navigating': '제어된 탐색을 요청하고 있습니다.',
      'notice.reading': '승인된 페이지를 읽고 있습니다.',
      'notice.previewReady': '읽기 전용 미리보기가 갱신되었습니다.',
      'notice.framePending': '페이지가 아직 미리보기를 준비하고 있습니다.',
      'notice.frameEmpty': '페이지에 사용할 수 있는 시각 미리보기가 없습니다.',
      'notice.capacityOccupied': '제어된 브라우징 용량이 사용 중입니다.',
      'notice.accessUnavailable': '이 작업 공간에는 브라우저 권한이 없습니다.',
      'notice.invalidAddress': '유효한 http 또는 https 주소를 입력하세요.',
      'notice.unavailable': '제어된 읽기를 일시적으로 사용할 수 없습니다.',
      'notice.closed': '제어된 세션이 종료되었습니다.',
      'empty.ready.title': 'LUMENIS 안에서 읽기 시작',
      'empty.ready.detail': '제어된 세션을 연 다음 허용된 공개 소스 주소를 입력하세요.',
      'empty.enterAddress.title': '소스 주소 입력',
      'empty.enterAddress.detail': '탐색 뒤에 시스템이 승인된 페이지의 읽기 전용 스냅샷을 표시합니다.',
      'empty.stopping.title': '세션 종료 중',
      'empty.stopping.detail': '현재 제어 세션에 종료를 요청하고 있습니다.',
      'empty.navigating.title': '탐색 중',
      'empty.navigating.detail': '외부 브라우저를 열지 않습니다.',
      'empty.reading.title': '미리보기 준비 중',
      'empty.reading.detail': '페이지가 그려진 뒤 미리보기를 갱신하세요.',
      'empty.previewReady.title': '미리보기 갱신됨',
      'empty.previewReady.detail': '현재 미리보기가 만료되었습니다. 다시 읽으세요.',
      'empty.framePending.title': '페이지 준비 중',
      'empty.framePending.detail': '페이지가 그려진 후 미리보기를 갱신하세요.',
      'empty.frameEmpty.title': '사용 가능한 미리보기 없음',
      'empty.frameEmpty.detail': '소스가 비었거나 수집이 완료되었다는 뜻은 아닙니다.',
      'empty.capacityOccupied.title': '제어된 용량 사용 중',
      'empty.capacityOccupied.detail': '다른 세션을 식별, 종료 또는 인계하지 않습니다.',
      'empty.accessUnavailable.title': '브라우저 접근 불가',
      'empty.accessUnavailable.detail': '다른 작업으로 돌아가고 접근이 복구된 뒤 다시 시도하세요.',
      'empty.invalidAddress.title': '주소를 사용할 수 없음',
      'empty.invalidAddress.detail': '자격 증명이 없는 http 또는 https 공개 주소만 허용됩니다.',
      'empty.unavailable.title': '미리보기를 일시적으로 사용할 수 없음',
      'empty.unavailable.detail': '이전 페이지를 유지하거나 성공 상태를 만들지 않습니다.',
      'empty.closed.title': '세션 종료됨',
      'empty.closed.detail': '필요할 때 새 제어 세션을 여세요.',
    },
  };
}
