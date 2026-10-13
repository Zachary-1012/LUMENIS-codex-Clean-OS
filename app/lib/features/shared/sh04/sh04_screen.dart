import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import '../../../core/lumenis_core_client.dart';
import '../../../core/lumenis_icon.dart';
import '../../../core/lumenis_theme.dart';
import '../../../l10n/lumenis_localizations.dart';
import '../read_aloud_action.dart';
import '../sh01/media_project_files.dart';
import 'sh04_repository.dart';
import 'sh04_snapshot.dart';
import 'sh04_view_model.dart';

class Sh04Screen extends StatefulWidget {
  const Sh04Screen({
    required this.client,
    this.repository,
    this.files,
    super.key,
  });
  final LumenisCoreClient client;
  final Sh04Repository? repository;
  final MediaProjectFiles? files;
  @override
  State<Sh04Screen> createState() => _Sh04ScreenState();
}

class _Sh04ScreenState extends State<Sh04Screen> {
  late final _viewModel = Sh04ViewModel(
    repository: widget.repository ?? CoreSh04Repository(client: widget.client),
  );
  final _search = TextEditingController();
  late final _files = widget.files ?? MediaProjectFiles();
  String? _notice;
  bool _downloading = false;
  bool _details = false;
  bool _comparing = false;

  bool _legacyReadable(Sh04Export? item) =>
      item != null &&
      item.savedWork == null &&
      item.scopeVerified &&
      item.reopenable &&
      item.state == Sh04ExportState.ready;

  @override
  void initState() {
    super.initState();
    _viewModel.refresh();
  }

  @override
  void dispose() {
    _viewModel.dispose();
    _search.dispose();
    super.dispose();
  }

  Future<void> _download(String format) async {
    final record = _viewModel.opened?.savedWork;
    if (record == null || !record.committed || _downloading) return;
    setState(() {
      _downloading = true;
      _notice = null;
    });
    try {
      final file = await widget.client.exportSavedWork(
        domainId: record.domainId,
        artifactId: record.artifactId,
        format: format,
      );
      if (!mounted ||
          _viewModel.opened?.savedWork?.artifactId != record.artifactId) {
        return;
      }
      final saved = await _files.save(file);
      if (mounted && saved) {
        setState(
          () => _notice = kIsWeb
              ? _copy(
                  context,
                  '已请求下载，请查看浏览器下载记录。',
                  'Download requested. Check your browser downloads.',
                  '다운로드를 요청했습니다. 브라우저 다운로드를 확인하세요.',
                )
              : _copy(context, '文件已保存。', 'File saved.', '파일을 저장했습니다.'),
        );
      }
    } catch (error) {
      if (mounted &&
          _viewModel.opened?.savedWork?.artifactId == record.artifactId) {
        final denied =
            error is LumenisCoreException &&
            (error.statusCode == 401 || error.statusCode == 403);
        setState(
          () => _notice = denied
              ? _copy(
                  context,
                  '当前无法下载这份成果，访问条件已发生变化。请重新读取。',
                  'This result can no longer be downloaded with the current access. Read it again.',
                  '현재 접근 조건으로 이 결과를 다운로드할 수 없습니다. 다시 읽어 주세요.',
                )
              : _copy(
                  context,
                  '下载未完成，可重试或选择其他格式。',
                  'Download did not finish. Retry or choose another format.',
                  '다운로드를 완료하지 못했습니다. 다시 시도하거나 다른 형식을 선택하세요.',
                ),
        );
      }
    } finally {
      if (mounted) setState(() => _downloading = false);
    }
  }

  void _open(Sh04Export item) {
    setState(() {
      _details = false;
      _comparing = false;
      _notice = null;
    });
    _viewModel.open(item);
  }

  @override
  Widget build(BuildContext context) => ColoredBox(
    color: LumenisTheme.of(context).canvas,
    child: SafeArea(
      child: AnimatedBuilder(
        animation: _viewModel,
        builder: (context, _) {
          return switch (_viewModel.phase) {
            Sh04LoadPhase.loading => _LoadingState(),
            Sh04LoadPhase.blocked => _BlockedState(
              error: _viewModel.scopeError,
              onRetry: _viewModel.refresh,
            ),
            Sh04LoadPhase.failed => _FailureState(
              kind: _viewModel.failureKind!,
              onRetry: _viewModel.refresh,
            ),
            Sh04LoadPhase.ready => LayoutBuilder(
              builder: (context, box) {
                final wide =
                    box.maxWidth >= 920 &&
                    MediaQuery.textScalerOf(context).scale(1) <= 1.4;
                final reading =
                    _legacyReadable(_viewModel.selected) ||
                    _viewModel.opened != null ||
                    _viewModel.opening ||
                    _viewModel.actionFailure != null;
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Padding(
                      padding: const EdgeInsets.fromLTRB(20, 12, 12, 10),
                      child: Row(
                        children: [
                          if (!wide && reading)
                            IconButton(
                              tooltip: _copy(
                                context,
                                '返回成果',
                                'Back to results',
                                '결과 목록으로',
                              ),
                              onPressed: _downloading
                                  ? null
                                  : _viewModel.backToList,
                              icon: const LumenisIcon(
                                Icons.arrow_back_rounded,
                                size: 20,
                              ),
                            ),
                          Expanded(
                            child: Text(
                              context.lumenisL10n.text('screen.SH-04'),
                              style: const TextStyle(
                                fontSize: 18,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ),
                          IconButton(
                            tooltip: _copy(
                              context,
                              '重新读取',
                              'Read again',
                              '다시 읽기',
                            ),
                            onPressed: _downloading ? null : _viewModel.refresh,
                            icon: const LumenisIcon(
                              Icons.refresh_rounded,
                              size: 20,
                            ),
                          ),
                        ],
                      ),
                    ),
                    if (_viewModel.snapshot!.incomplete)
                      _noticeRow(
                        _copy(
                          context,
                          '部分成果尚未读取完整，可重新读取。',
                          'Some results could not be read completely. You can retry.',
                          '일부 결과를 완전히 읽지 못했습니다. 다시 읽을 수 있습니다.',
                        ),
                      ),
                    if (_notice != null) _noticeRow(_notice!),
                    const Divider(height: 1),
                    Expanded(
                      child: wide
                          ? Row(
                              crossAxisAlignment: CrossAxisAlignment.stretch,
                              children: [
                                SizedBox(
                                  width: 308,
                                  child: _readingSurface(_list(), list: true),
                                ),
                                const VerticalDivider(width: 1),
                                Expanded(child: _readingSurface(_reader())),
                              ],
                            )
                          : reading
                          ? _readingSurface(_reader())
                          : _readingSurface(_list(), list: true),
                    ),
                  ],
                );
              },
            ),
          };
        },
      ),
    ),
  );

  Widget _readingSurface(Widget child, {bool list = false}) => ColoredBox(
    color: LumenisTheme.of(context).surface.withValues(alpha: list ? .90 : .97),
    child: child,
  );

  Widget _noticeRow(String text) => Semantics(
    liveRegion: true,
    child: Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
      child: Text(
        text,
        style: TextStyle(color: LumenisTheme.of(context).muted, fontSize: 13),
      ),
    ),
  );

  Widget _list() {
    final items = _viewModel.exports;
    final selection = _viewModel.opened?.internalId;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                _copy(context, '成果队列', 'Saved results', '결과물 대기열'),
                style: TextStyle(
                  color: LumenisTheme.of(context).muted,
                  fontSize: 12,
                ),
              ),
              const SizedBox(height: 10),
              TextField(
                controller: _search,
                enabled: !_downloading,
                onSubmitted: (_) => _viewModel.search(_search.text.trim()),
                decoration: InputDecoration(
                  hintText: _copy(
                    context,
                    '搜索标题或正文',
                    'Search title or text',
                    '제목 또는 본문 검색',
                  ),
                  isDense: true,
                  prefixIcon: const LumenisIcon(Icons.search_rounded, size: 18),
                  suffixIcon: IconButton(
                    tooltip: _copy(context, '搜索', 'Search', '검색'),
                    onPressed: _downloading
                        ? null
                        : () => _viewModel.search(_search.text.trim()),
                    icon: const LumenisIcon(
                      Icons.arrow_forward_rounded,
                      size: 18,
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
        Expanded(
          child: items.isEmpty
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(20),
                    child: Text(
                      _copy(
                        context,
                        '这里还没有可读取的成果。',
                        'No readable results here yet.',
                        '아직 읽을 수 있는 결과가 없습니다.',
                      ),
                      textAlign: TextAlign.center,
                      style: TextStyle(color: LumenisTheme.of(context).muted),
                    ),
                  ),
                )
              : ListView.builder(
                  key: const PageStorageKey('sh04-results'),
                  padding: const EdgeInsets.only(bottom: 12),
                  itemCount: items.length + (_viewModel.hasMore ? 1 : 0),
                  itemBuilder: (context, index) {
                    if (index == items.length) {
                      return Padding(
                        padding: const EdgeInsets.all(12),
                        child: OutlinedButton(
                          onPressed: _viewModel.loadingMore
                              ? null
                              : _viewModel.loadMore,
                          child: Text(
                            _viewModel.loadingMore
                                ? _copy(context, '读取中…', 'Loading…', '읽는 중…')
                                : _copy(context, '继续读取', 'Load more', '더 읽기'),
                          ),
                        ),
                      );
                    }
                    final item = items[index];
                    final saved = item.savedWork;
                    return Material(
                      color: selection == item.internalId
                          ? LumenisTheme.of(
                              context,
                            ).accent.withValues(alpha: .10)
                          : Colors.transparent,
                      child: InkWell(
                        onTap:
                            _downloading ||
                                (saved == null && !_legacyReadable(item))
                            ? null
                            : () => _open(item),
                        child: Padding(
                          padding: const EdgeInsets.fromLTRB(16, 14, 16, 14),
                          child: Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Padding(
                                padding: const EdgeInsets.only(
                                  top: 2,
                                  right: 10,
                                ),
                                child: LumenisIcon(
                                  saved?.kind == 'research'
                                      ? Icons.find_in_page_outlined
                                      : Icons.description_outlined,
                                  size: 20,
                                  color: LumenisTheme.of(context).shared,
                                ),
                              ),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      item.title,
                                      maxLines: 2,
                                      overflow: TextOverflow.ellipsis,
                                      style: const TextStyle(
                                        fontSize: 14,
                                        height: 1.4,
                                        fontWeight: FontWeight.w500,
                                      ),
                                    ),
                                    const SizedBox(height: 5),
                                    Text(
                                      [
                                        if (saved != null) 'v${saved.version}',
                                        _date(item.generatedAt),
                                      ].where((s) => s.isNotEmpty).join(' · '),
                                      style: TextStyle(
                                        fontSize: 12,
                                        color: LumenisTheme.of(context).muted,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                              const SizedBox(width: 8),
                              const LumenisIcon(
                                Icons.chevron_right_rounded,
                                size: 18,
                              ),
                            ],
                          ),
                        ),
                      ),
                    );
                  },
                ),
        ),
      ],
    );
  }

  Widget _reader() {
    if (_viewModel.opening) return _LoadingState();
    if (_viewModel.actionFailure != null) {
      return _FailureState(
        kind: _viewModel.actionFailure!,
        onRetry: _viewModel.retrySelected,
      );
    }
    final item =
        _viewModel.opened ??
        (_legacyReadable(_viewModel.selected) ? _viewModel.selected : null);
    if (item == null) {
      return Center(
        child: Text(
          _copy(context, '选择一份成果', 'Select a result', '결과 선택'),
          style: TextStyle(color: LumenisTheme.of(context).quiet),
        ),
      );
    }
    final saved = item.savedWork;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 12),
          child: Wrap(
            spacing: 8,
            runSpacing: 4,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              Text(
                _copy(context, '成果预览', 'Result preview', '결과 미리보기'),
                style: TextStyle(
                  fontSize: 12,
                  color: LumenisTheme.of(context).muted,
                ),
              ),
              if (saved != null)
                Text('v${saved.version}', style: const TextStyle(fontSize: 12)),
              if (saved?.parentArtifactId != null)
                TextButton.icon(
                  onPressed: _downloading
                      ? null
                      : () {
                          setState(() {
                            _comparing = false;
                            _details = false;
                          });
                          _viewModel.openParent();
                        },
                  icon: const LumenisIcon(Icons.history_rounded, size: 18),
                  label: Text(
                    _copy(context, '上一版本', 'Previous version', '이전 버전'),
                  ),
                ),
              if (saved?.parentArtifactId != null)
                TextButton.icon(
                  onPressed: _downloading
                      ? null
                      : () {
                          setState(() {
                            _comparing = !_comparing;
                            _details = false;
                          });
                          if (_comparing) _viewModel.compareParent();
                        },
                  icon: const LumenisIcon(
                    Icons.compare_arrows_rounded,
                    size: 18,
                  ),
                  label: Text(
                    _comparing
                        ? _copy(context, '返回正文', 'Read document', '본문 보기')
                        : _copy(context, '对比版本', 'Compare versions', '버전 비교'),
                  ),
                ),
              if (saved != null && saved.committed) ...[
                Semantics(
                  expanded: _details,
                  child: TextButton.icon(
                    onPressed: () => setState(() {
                      _details = !_details;
                      _comparing = false;
                    }),
                    icon: const LumenisIcon(
                      Icons.info_outline_rounded,
                      size: 18,
                    ),
                    label: Text(
                      _copy(context, '来源与详情', 'Sources & details', '출처 및 상세'),
                    ),
                  ),
                ),
                PopupMenuButton<String>(
                  enabled: !_downloading && _files.canSave,
                  tooltip: _copy(context, '下载', 'Download', '다운로드'),
                  onSelected: _download,
                  itemBuilder: (_) => const [
                    PopupMenuItem(value: 'pdf', child: Text('PDF')),
                    PopupMenuItem(value: 'docx', child: Text('Word')),
                    PopupMenuItem(value: 'md', child: Text('Markdown')),
                    PopupMenuItem(value: 'txt', child: Text('TXT')),
                    PopupMenuItem(value: 'json', child: Text('JSON')),
                    PopupMenuItem(value: 'xlsx', child: Text('Excel')),
                  ],
                  child: Container(
                    constraints: const BoxConstraints(
                      minWidth: 44,
                      minHeight: 44,
                    ),
                    padding: const EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 10,
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        LumenisIcon(
                          _downloading
                              ? Icons.hourglass_top_rounded
                              : Icons.download_rounded,
                          size: 18,
                        ),
                        const SizedBox(width: 6),
                        Text(_copy(context, '下载', 'Download', '다운로드')),
                      ],
                    ),
                  ),
                ),
              ],
            ],
          ),
        ),
        const Divider(height: 1),
        Expanded(
          child: SingleChildScrollView(
            key: ValueKey('sh04-body-${item.internalId}-$_details'),
            padding: const EdgeInsets.fromLTRB(24, 24, 24, 40),
            child: Align(
              alignment: Alignment.topCenter,
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 780),
                child: SelectionArea(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Semantics(
                        header: true,
                        child: Text(
                          item.title,
                          style: const TextStyle(
                            fontSize: 23,
                            height: 1.35,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        _date(item.generatedAt),
                        style: TextStyle(
                          color: LumenisTheme.of(context).muted,
                          fontSize: 12,
                        ),
                      ),
                      const SizedBox(height: 24),
                      if (_comparing) ...[
                        if (_viewModel.comparisonFailure != null)
                          _FailureState(
                            kind: _viewModel.comparisonFailure!,
                            onRetry: _viewModel.retryComparison,
                          )
                        else if (_viewModel.comparedParent == null)
                          const Center(child: CircularProgressIndicator())
                        else
                          _DocumentComparison(
                            current: item,
                            previous: _viewModel.comparedParent!,
                          ),
                      ] else if (_details && saved != null) ...[
                        Text(
                          _copy(
                            context,
                            '已保存版本，未发布。保存不等于事实已核验。',
                            'Saved version, not published. Storage does not establish factual accuracy.',
                            '저장된 버전이며 게시되지 않았습니다. 저장은 사실 검증을 뜻하지 않습니다.',
                          ),
                          style: TextStyle(
                            color: LumenisTheme.of(context).muted,
                            height: 1.5,
                          ),
                        ),
                        const SizedBox(height: 20),
                        Text(
                          saved.sources.isEmpty
                              ? _copy(
                                  context,
                                  '这份成果没有引用外部来源。',
                                  'This result cites no external sources.',
                                  '외부 출처를 인용하지 않은 결과입니다.',
                                )
                              : _copy(
                                  context,
                                  '引用来源',
                                  'Cited sources',
                                  '인용 출처',
                                ),
                          style: const TextStyle(fontWeight: FontWeight.w600),
                        ),
                        for (var i = 0; i < saved.sources.length; i++)
                          Padding(
                            padding: const EdgeInsets.only(top: 12),
                            child: _SourceNote(
                              index: i + 1,
                              source: saved.sources[i],
                            ),
                          ),
                      ] else ...[
                        Text(
                          item.preview,
                          style: TextStyle(
                            color: LumenisTheme.of(context).foreground,
                            fontSize: 15,
                            height: 1.7,
                          ),
                        ),
                        if (item.preview.isNotEmpty &&
                            saved?.committed == true &&
                            item.scopeVerified &&
                            item.reopenable &&
                            item.state == Sh04ExportState.ready)
                          Padding(
                            padding: const EdgeInsets.only(top: 24),
                            child: Align(
                              alignment: Alignment.centerLeft,
                              child: ReadAloudAction(
                                key: ValueKey(item.internalId),
                                sessionId: 'sh04-preview',
                                scopeVersion:
                                    '${item.internalId}:${saved?.hash ?? item.generatedAt}',
                                text: item.preview,
                                purpose: ReadAloudPurpose.savedPreview,
                              ),
                            ),
                          ),
                      ],
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class _DocumentComparison extends StatefulWidget {
  const _DocumentComparison({required this.current, required this.previous});
  final Sh04Export current;
  final Sh04Export previous;
  @override
  State<_DocumentComparison> createState() => _DocumentComparisonState();
}

class _DocumentComparisonState extends State<_DocumentComparison> {
  bool _showPrevious = false;
  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, box) {
      final current = widget.current;
      final previous = widget.previous;
      final unchanged = current.preview == previous.preview;
      Widget textVersion(Sh04Export item, String other, {required bool old}) {
        final text = item.preview;
        // Mark the contiguous changed region; preserve the complete original
        // strings. This is a local text comparison, never a factual evaluation.
        var start = 0;
        var end = 0;
        final units = text.runes.toList();
        final otherUnits = other.runes.toList();
        while (start < units.length &&
            start < otherUnits.length &&
            units[start] == otherUnits[start]) {
          start++;
        }
        while (end < units.length - start &&
            end < otherUnits.length - start &&
            units[units.length - end - 1] ==
                otherUnits[otherUnits.length - end - 1]) {
          end++;
        }
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              'v${item.savedWork!.version} · ${item.title}',
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 14),
            Text.rich(
              TextSpan(
                children: [
                  TextSpan(text: String.fromCharCodes(units.take(start))),
                  TextSpan(
                    text: String.fromCharCodes(
                      units.skip(start).take(units.length - start - end),
                    ),
                    style: TextStyle(
                      backgroundColor:
                          (old
                                  ? LumenisTheme.of(context).caution
                                  : LumenisTheme.of(context).positive)
                              .withValues(alpha: .12),
                    ),
                  ),
                  if (end > 0)
                    TextSpan(
                      text: String.fromCharCodes(
                        units.skip(units.length - end),
                      ),
                    ),
                ],
              ),
              style: const TextStyle(fontSize: 14, height: 1.65),
            ),
          ],
        );
      }

      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            unchanged
                ? _copy(
                    context,
                    '正文相同',
                    'Document text is unchanged',
                    '본문이 동일합니다',
                  )
                : _copy(
                    context,
                    '高亮区间包含两版正文之间的变化。',
                    'Highlighted ranges contain the changes between versions.',
                    '강조한 구간에 두 버전의 변경 내용이 포함되어 있습니다.',
                  ),
            style: TextStyle(
              color: LumenisTheme.of(context).muted,
              fontSize: 12,
            ),
          ),
          const SizedBox(height: 18),
          if (box.maxWidth >= 680)
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: textVersion(previous, current.preview, old: true),
                ),
                const SizedBox(width: 24),
                Expanded(
                  child: textVersion(current, previous.preview, old: false),
                ),
              ],
            )
          else ...[
            Wrap(
              spacing: 8,
              children: [
                ChoiceChip(
                  label: Text(_copy(context, '上一版本', 'Previous', '이전 버전')),
                  selected: _showPrevious,
                  onSelected: (_) => setState(() => _showPrevious = true),
                ),
                ChoiceChip(
                  label: Text(_copy(context, '当前版本', 'Current', '현재 버전')),
                  selected: !_showPrevious,
                  onSelected: (_) => setState(() => _showPrevious = false),
                ),
              ],
            ),
            const SizedBox(height: 16),
            _showPrevious
                ? textVersion(previous, current.preview, old: true)
                : textVersion(current, previous.preview, old: false),
          ],
        ],
      );
    },
  );
}

class _SourceNote extends StatelessWidget {
  const _SourceNote({required this.index, required this.source});
  final int index;
  final Map<String, dynamic> source;
  @override
  Widget build(BuildContext context) {
    // Only explicitly named user-facing fields; never dump raw source payloads,
    // principal identifiers or internal paths into the interface.
    final title = source['title'];
    final url = source['source_url'];
    final locator = source['locator'];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title is String && title.isNotEmpty
              ? '$index. $title'
              : _copy(context, '来源 $index', 'Source $index', '출처 $index'),
        ),
        if (url is String &&
            const {'https', 'http'}.contains(Uri.tryParse(url)?.scheme))
          Text(
            url,
            style: TextStyle(
              color: LumenisTheme.of(context).muted,
              fontSize: 12,
            ),
          ),
        if (locator is String)
          Text(
            locator,
            style: TextStyle(
              color: LumenisTheme.of(context).muted,
              fontSize: 12,
            ),
          ),
      ],
    );
  }
}

String _date(String raw) {
  final parsed = DateTime.tryParse(raw)?.toLocal();
  if (parsed == null) return '';
  String pad(int value) => '$value'.padLeft(2, '0');
  return '${parsed.year}-${pad(parsed.month)}-${pad(parsed.day)} ${pad(parsed.hour)}:${pad(parsed.minute)}';
}

class _LoadingState extends StatelessWidget {
  @override
  Widget build(BuildContext context) => Semantics(
    liveRegion: true,
    label: _copy(
      context,
      '正在读取报告成果',
      'Reading report outputs',
      '보고서 결과물을 읽는 중',
    ),
    child: const Center(child: CircularProgressIndicator()),
  );
}

class _BlockedState extends StatelessWidget {
  const _BlockedState({required this.error, required this.onRetry});

  final Sh04ScopeErrorKind? error;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => _StateMessage(
    title: _copy(
      context,
      '成果中心暂不显示',
      'Output center is hidden for now',
      '결과물 센터를 현재 표시하지 않습니다',
    ),
    detail: switch (error) {
      Sh04ScopeErrorKind.denied => _copy(
        context,
        '当前内容不可访问。',
        'This content is not accessible.',
        '현재 콘텐츠에 접근할 수 없습니다.',
      ),
      Sh04ScopeErrorKind.malformed => _copy(
        context,
        '服务返回的范围不完整，因此不会显示成果。',
        'The returned range is incomplete, so outputs are not shown.',
        '반환된 범위가 불완전하여 결과물을 표시하지 않습니다.',
      ),
      _ => _copy(
        context,
        '暂时无法读取成果，请重试。',
        'These results could not be read. Please try again.',
        '결과물을 읽을 수 없습니다. 다시 시도하세요.',
      ),
    },
    onRetry: onRetry,
  );
}

class _FailureState extends StatelessWidget {
  const _FailureState({required this.kind, required this.onRetry});

  final Sh04FailureKind kind;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => _StateMessage(
    title: _copy(
      context,
      '成果中心暂不可用',
      'Output center unavailable',
      '결과물 센터를 사용할 수 없습니다',
    ),
    detail: switch (kind) {
      Sh04FailureKind.authentication => _copy(
        context,
        '当前内容暂时无法打开。可重试读取，或返回后稍后再试。',
        'This content cannot be opened right now. You can retry reading it or return and try again later.',
        '현재 콘텐츠를 지금 열 수 없습니다. 다시 읽기를 시도하거나 돌아간 뒤 나중에 다시 시도할 수 있습니다.',
      ),
      Sh04FailureKind.permissionDenied => _copy(
        context,
        '当前内容不可访问。',
        'This content is not accessible.',
        '현재 콘텐츠에 접근할 수 없습니다.',
      ),
      Sh04FailureKind.offline => _copy(
        context,
        '成果暂时无法读取，请稍后重试。',
        'Results could not be read right now. Please try again.',
        '지금 결과물을 읽을 수 없습니다. 다시 시도하세요.',
      ),
      Sh04FailureKind.response => _copy(
        context,
        '成果服务没有返回可验证的数据，请稍后重试。',
        'The output service did not return verifiable data. Try again later.',
        '결과물 서비스가 확인 가능한 데이터를 반환하지 않았습니다. 나중에 다시 시도하세요.',
      ),
    },
    onRetry: onRetry,
  );
}

class _StateMessage extends StatelessWidget {
  const _StateMessage({
    required this.title,
    required this.detail,
    required this.onRetry,
  });

  final String title;
  final String detail;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => Semantics(
    liveRegion: true,
    child: Center(
      child: SingleChildScrollView(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 620),
          child: Padding(
            padding: const EdgeInsets.all(26),
            child: _Panel(
              title: title,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    detail,
                    style: TextStyle(
                      color: LumenisTheme.of(context).muted,
                      height: 1.5,
                    ),
                  ),
                  const SizedBox(height: 18),
                  OutlinedButton(
                    onPressed: onRetry,
                    child: Text(_copy(context, '重新读取', 'Read again', '다시 읽기')),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    ),
  );
}

class _Panel extends StatelessWidget {
  const _Panel({required this.title, required this.child});

  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    padding: const EdgeInsets.fromLTRB(16, 15, 16, 15),
    decoration: BoxDecoration(
      color: LumenisTheme.of(context).surface,
      border: Border.all(color: LumenisTheme.of(context).line),
      borderRadius: BorderRadius.circular(13),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: 12),
        child,
      ],
    ),
  );
}

String _copy(BuildContext context, String zh, String en, String ko) =>
    switch (context.lumenisL10n.locale.languageCode) {
      'en' => en,
      'ko' => ko,
      _ => zh,
    };
