import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../../core/lumenis_icon.dart';

import '../../../core/lumenis_core_client.dart';
import '../../../core/lumenis_theme.dart';
import '../../../l10n/lumenis_localizations.dart';
import '../read_aloud_action.dart';
import 'sh04_repository.dart';
import 'sh04_export_files.dart';
import 'sh04_snapshot.dart';
import 'sh04_view_model.dart';

class Sh04Screen extends StatefulWidget {
  const Sh04Screen({required this.client, this.repository, super.key});

  final LumenisCoreClient client;
  final Sh04Repository? repository;

  @override
  State<Sh04Screen> createState() => _Sh04ScreenState();
}

class _Sh04ScreenState extends State<Sh04Screen> {
  final _exportFiles = Sh04ExportFiles();
  late Sh04ViewModel _viewModel = Sh04ViewModel(
    repository: widget.repository ?? CoreSh04Repository(client: widget.client),
  );

  @override
  void initState() {
    super.initState();
    _viewModel.refresh();
  }

  @override
  void didUpdateWidget(covariant Sh04Screen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (!identical(oldWidget.client, widget.client) ||
        !identical(oldWidget.repository, widget.repository)) {
      _viewModel.dispose();
      _viewModel = Sh04ViewModel(
        repository:
            widget.repository ?? CoreSh04Repository(client: widget.client),
      );
      _viewModel.refresh();
    }
  }

  @override
  void dispose() {
    _viewModel.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => ColoredBox(
    color: LumenisTheme.of(context).canvas,
    child: SafeArea(
      child: AnimatedBuilder(
        animation: _viewModel,
        builder: (context, _) => switch (_viewModel.phase) {
          Sh04LoadPhase.loading => _LoadingState(),
          Sh04LoadPhase.blocked => _BlockedState(
            error: _viewModel.scopeError,
            onRetry: _viewModel.refresh,
          ),
          Sh04LoadPhase.failed => _FailureState(
            kind: _viewModel.failureKind!,
            onRetry: _viewModel.refresh,
          ),
          Sh04LoadPhase.ready => _Workspace(
            viewModel: _viewModel,
            onCreate: _createReport,
            onReopen: _reopen,
            onRevise: _revise,
            onExport: _export,
          ),
        },
      ),
    ),
  );

  Future<void> _createReport() async {
    final viewModel = _viewModel;
    final generation = viewModel.readGeneration;
    final saved = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => _Sh04EditorDialog(
        onSubmit: (title, markdown, _) async {
          try {
            if (!_isCurrent(viewModel, generation)) return false;
            await viewModel.saveReport(title: title, markdown: markdown);
            return true;
          } catch (_) {
            return false;
          }
        },
      ),
    );
    if (saved == true && mounted && _isCurrent(viewModel, generation)) {
      _showNotice(
        _copy(
          context,
          '报告已保存，可重新打开。',
          'Report saved and ready to reopen.',
          '보고서를 저장했습니다. 다시 열 수 있습니다.',
        ),
      );
    }
  }

  Future<void> _revise(Sh04Export item) async {
    final viewModel = _viewModel;
    final generation = viewModel.readGeneration;
    final saved = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => _Sh04EditorDialog(
        source: item,
        onSubmit: (title, markdown, reason) async {
          try {
            if (!_isCurrent(viewModel, generation)) return false;
            await viewModel.reviseReport(
              parent: item,
              title: title,
              markdown: markdown,
              reason: reason,
            );
            return true;
          } catch (_) {
            return false;
          }
        },
      ),
    );
    if (saved == true && mounted && _isCurrent(viewModel, generation)) {
      _showNotice(
        _copy(
          context,
          '新版本已保存，原版本仍可重新打开。',
          'A new version was saved. The earlier version remains available.',
          '새 버전을 저장했습니다. 이전 버전도 다시 열 수 있습니다.',
        ),
      );
    }
  }

  Future<void> _reopen(Sh04Export item) async {
    final viewModel = _viewModel;
    final generation = viewModel.readGeneration;
    try {
      await viewModel.reopen(item);
      if (mounted && _isCurrent(viewModel, generation)) {
        _showNotice(
          _copy(
            context,
            '已从保存的版本重新打开。',
            'Reopened the saved version.',
            '저장된 버전을 다시 열었습니다.',
          ),
        );
      }
    } catch (_) {
      if (mounted && _isCurrent(viewModel, generation)) {
        _showNotice(
          _copy(
            context,
            '此版本暂时无法重新打开。请重新读取后再试。',
            'This version could not be reopened. Read the list again and retry.',
            '이 버전을 다시 열 수 없습니다. 목록을 새로 읽고 다시 시도하세요.',
          ),
        );
      }
    }
  }

  Future<void> _export(Sh04Export item) async {
    final viewModel = _viewModel;
    final generation = viewModel.readGeneration;
    final formats = _exportFiles.canSaveFile
        ? const ['md', 'txt', 'docx', 'pdf', 'xlsx', 'pptx']
        : const ['md', 'txt'];
    final format = await showDialog<String>(
      context: context,
      builder: (dialogContext) => _Sh04FormatDialog(formats: formats),
    );
    if (format == null || !_isCurrent(viewModel, generation)) {
      return;
    }
    try {
      final file = await viewModel.export(item, format);
      if (!mounted || !_isCurrent(viewModel, generation)) return;
      if (_exportFiles.canSaveFile) {
        final saved = await _exportFiles.save(
          file,
          suggestedName: 'lumenis-report-v${item.version}.$format',
        );
        if (saved && mounted && _isCurrent(viewModel, generation)) {
          _showNotice(
            _copy(
              context,
              kIsWeb ? '文件已交给浏览器下载，请检查下载记录。' : '文件已保存到所选位置。',
              kIsWeb
                  ? 'The file was handed to the browser. Check Downloads.'
                  : 'The file was saved to the selected location.',
              kIsWeb
                  ? '브라우저에 파일을 전달했습니다. 다운로드 목록을 확인하세요.'
                  : '선택한 위치에 파일을 저장했습니다.',
            ),
          );
        }
      } else {
        final text = utf8.decode(file.bytes);
        await Clipboard.setData(ClipboardData(text: text));
        if (mounted && _isCurrent(viewModel, generation)) {
          _showNotice(
            _copy(
              context,
              '导出文本已复制，可粘贴到文件或其他应用。',
              'Exported text copied. Paste it into a file or another app.',
              '내보낸 텍스트를 복사했습니다. 파일이나 다른 앱에 붙여넣을 수 있습니다.',
            ),
          );
        }
      }
    } catch (_) {
      if (mounted && _isCurrent(viewModel, generation)) {
        _showNotice(
          _copy(
            context,
            '导出未完成。请检查权限后重试。',
            'Export did not complete. Check access and retry.',
            '내보내기를 완료하지 못했습니다. 권한을 확인하고 다시 시도하세요.',
          ),
        );
      }
    }
  }

  bool _isCurrent(Sh04ViewModel model, int generation) =>
      mounted &&
      identical(model, _viewModel) &&
      model.readGeneration == generation;

  void _showNotice(String text) {
    ScaffoldMessenger.maybeOf(
      context,
    )?.showSnackBar(SnackBar(content: Text(text)));
  }
}

class _Workspace extends StatelessWidget {
  const _Workspace({
    required this.viewModel,
    required this.onCreate,
    required this.onReopen,
    required this.onRevise,
    required this.onExport,
  });

  final Sh04ViewModel viewModel;
  final VoidCallback onCreate;
  final ValueChanged<Sh04Export> onReopen;
  final ValueChanged<Sh04Export> onRevise;
  final ValueChanged<Sh04Export> onExport;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, constraints) {
      final wide = constraints.maxWidth >= 1120;
      final snapshot = viewModel.snapshot!;
      final queue = _ExportQueue(viewModel: viewModel, onReopen: onReopen);
      final inspector = _ArtifactInspector(
        exportItem: viewModel.selected,
        scope: snapshot.scope,
        busy: viewModel.operationBusy,
        onRevise: viewModel.selected == null
            ? null
            : () => onRevise(viewModel.selected!),
        onExport: viewModel.selected == null
            ? null
            : () => onExport(viewModel.selected!),
      );
      return Align(
        alignment: Alignment.topCenter,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1480),
          child: SingleChildScrollView(
            padding: EdgeInsets.fromLTRB(
              wide ? 32 : 18,
              24,
              wide ? 32 : 18,
              44,
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _Header(),
                const SizedBox(height: 18),
                _ScopeBanner(scope: snapshot.scope),
                const SizedBox(height: 12),
                Align(
                  alignment: Alignment.centerRight,
                  child: FilledButton.icon(
                    key: const Key('sh04-create-report'),
                    onPressed: viewModel.operationBusy ? null : onCreate,
                    icon: const LumenisIcon(Icons.edit_note_rounded),
                    label: Text(
                      _copy(context, '撰写报告', 'Write a report', '보고서 작성'),
                    ),
                  ),
                ),
                if (!snapshot.verificationComplete ||
                    snapshot.unverifiedCandidates > 0) ...[
                  const SizedBox(height: 12),
                  _InfoMessage(
                    _copy(
                      context,
                      '部分保存成果未能完成核验，已暂时隐藏。重新读取后可再次检查。',
                      'Some saved reports could not be verified and are hidden for now. Read again to check later.',
                      '일부 저장된 보고서를 확인하지 못해 임시로 숨겼습니다. 목록을 다시 읽어 확인하세요.',
                    ),
                  ),
                ],
                const SizedBox(height: 16),
                if (wide)
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      SizedBox(width: 390, child: queue),
                      const SizedBox(width: 16),
                      Expanded(child: inspector),
                    ],
                  )
                else
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [queue, const SizedBox(height: 14), inspector],
                  ),
                if (snapshot.hasMore) ...[
                  const SizedBox(height: 14),
                  if (viewModel.loadMoreFailureKind != null) ...[
                    _InfoMessage(
                      _copy(
                        context,
                        '更多报告暂未读取，已显示的版本仍可用。可重试读取。',
                        'More reports could not be read. The versions already shown remain available; you can retry.',
                        '추가 보고서를 읽지 못했습니다. 이미 표시된 버전은 계속 사용할 수 있으며 다시 시도할 수 있습니다.',
                      ),
                    ),
                    const SizedBox(height: 10),
                  ],
                  Align(
                    alignment: Alignment.centerLeft,
                    child: OutlinedButton(
                      key: const Key('sh04-load-more'),
                      onPressed: viewModel.operationBusy
                          ? null
                          : viewModel.loadMore,
                      child: Text(
                        viewModel.loadMoreFailureKind == null
                            ? _copy(context, '加载更多', 'Load more', '더 보기')
                            : _copy(context, '重试读取', 'Retry reading', '다시 읽기'),
                      ),
                    ),
                  ),
                ],
                const SizedBox(height: 14),
                Align(
                  alignment: Alignment.centerLeft,
                  child: OutlinedButton.icon(
                    onPressed: viewModel.refresh,
                    icon: const LumenisIcon(Icons.refresh_rounded),
                    label: Text(_copy(context, '重新读取', 'Read again', '다시 읽기')),
                    style: OutlinedButton.styleFrom(
                      minimumSize: const Size(48, 48),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      );
    },
  );
}

class _Header extends StatelessWidget {
  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      _Eyebrow(_copy(context, '可回溯成果', 'REOPENABLE OUTPUT', '다시 열 수 있는 결과물')),
      const SizedBox(height: 9),
      Text(
        context.lumenisL10n.text('screen.SH-04'),
        style: Theme.of(context).textTheme.headlineMedium?.copyWith(
          color: LumenisTheme.of(context).foreground,
          fontWeight: FontWeight.w600,
        ),
      ),
      const SizedBox(height: 6),
      Text(
        _copy(
          context,
          '在共享工作区撰写和修订报告，重新打开保存版本，并通过权限检查后导出。',
          'Write and revise reports in the Shared workspace, reopen saved versions, and export after access checks.',
          '공유 작업공간에서 보고서를 작성하고 수정한 뒤 저장 버전을 다시 열고 권한 확인 후 내보냅니다.',
        ),
        style: TextStyle(color: LumenisTheme.of(context).muted, height: 1.45),
      ),
    ],
  );
}

class _ScopeBanner extends StatelessWidget {
  const _ScopeBanner({required this.scope});

  final Sh04Scope scope;

  @override
  Widget build(BuildContext context) {
    final range = _copy(context, '共享工作区', 'Shared workspace', '공유 작업 공간');
    return Semantics(
      liveRegion: true,
      label: _copy(
        context,
        '当前成果范围：$range',
        'Current output range: $range',
        '현재 결과 범위: $range',
      ),
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(horizontal: 15, vertical: 12),
        decoration: BoxDecoration(
          color: LumenisTheme.of(context).accentStrong.withValues(alpha: 0.08),
          border: Border.all(
            color: LumenisTheme.of(
              context,
            ).accentStrong.withValues(alpha: 0.35),
          ),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Row(
          children: [
            Icon(
              Icons.lock_outline_rounded,
              color: LumenisTheme.of(context).accentStrong,
              size: 19,
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                range,
                style: const TextStyle(fontWeight: FontWeight.w600),
              ),
            ),
            Text(
              _copy(
                context,
                '每次操作均检查工作区权限',
                'Workspace access is checked for each action',
                '각 작업에서 작업공간 권한을 확인합니다',
              ),
              style: TextStyle(
                color: LumenisTheme.of(context).muted,
                fontSize: 12,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

typedef _Sh04Submit =
    Future<bool> Function(String title, String markdown, String reason);

class _Sh04EditorDialog extends StatefulWidget {
  const _Sh04EditorDialog({this.source, required this.onSubmit});

  final Sh04Export? source;
  final _Sh04Submit onSubmit;

  @override
  State<_Sh04EditorDialog> createState() => _Sh04EditorDialogState();
}

class _Sh04EditorDialogState extends State<_Sh04EditorDialog> {
  late final _title = TextEditingController(text: widget.source?.title ?? '');
  late final _markdown = TextEditingController(
    text: widget.source?.markdown ?? '',
  );
  final _reason = TextEditingController();
  bool _busy = false;
  bool _failed = false;

  @override
  void dispose() {
    _title.dispose();
    _markdown.dispose();
    _reason.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (_title.text.trim().isEmpty ||
        _markdown.text.trim().isEmpty ||
        (widget.source != null && _reason.text.trim().isEmpty)) {
      setState(() => _failed = true);
      return;
    }
    setState(() {
      _busy = true;
      _failed = false;
    });
    final saved = await widget.onSubmit(
      _title.text.trim(),
      _markdown.text,
      _reason.text.trim(),
    );
    if (!mounted) return;
    if (saved) {
      Navigator.of(context).pop(true);
    } else {
      setState(() {
        _busy = false;
        _failed = true;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final isRevision = widget.source != null;
    return AlertDialog(
      title: Text(
        isRevision
            ? _copy(context, '修订报告', 'Revise report', '보고서 수정')
            : _copy(context, '撰写报告', 'Write a report', '보고서 작성'),
      ),
      content: SizedBox(
        width: 600,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              TextField(
                key: const Key('sh04-report-title'),
                controller: _title,
                maxLength: 300,
                decoration: InputDecoration(
                  labelText: _copy(context, '标题', 'Title', '제목'),
                ),
              ),
              const SizedBox(height: 10),
              TextField(
                key: const Key('sh04-report-markdown'),
                controller: _markdown,
                minLines: 10,
                maxLines: 18,
                keyboardType: TextInputType.multiline,
                decoration: InputDecoration(
                  alignLabelWithHint: true,
                  labelText: _copy(context, '报告内容', 'Report text', '보고서 내용'),
                ),
              ),
              if (isRevision) ...[
                const SizedBox(height: 10),
                TextField(
                  key: const Key('sh04-revision-reason'),
                  controller: _reason,
                  minLines: 2,
                  maxLines: 4,
                  decoration: InputDecoration(
                    alignLabelWithHint: true,
                    labelText: _copy(
                      context,
                      '本次修订说明',
                      'Reason for this revision',
                      '이번 수정 사유',
                    ),
                  ),
                ),
              ],
              if (_failed) ...[
                const SizedBox(height: 12),
                Text(
                  _copy(
                    context,
                    '保存未完成，内容仍保留。若上次结果不确定，请用相同内容重试。',
                    'The save did not complete and your text is still here. If the previous result is uncertain, retry with the same text.',
                    '저장을 완료하지 못했지만 내용은 남아 있습니다. 이전 결과가 불확실하면 같은 내용으로 다시 시도하세요.',
                  ),
                  style: TextStyle(color: LumenisTheme.of(context).danger),
                ),
              ],
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: _busy ? null : () => Navigator.of(context).pop(false),
          child: Text(_copy(context, '取消', 'Cancel', '취소')),
        ),
        FilledButton(
          key: const Key('sh04-save-report'),
          onPressed: _busy ? null : _save,
          child: _busy
              ? const SizedBox.square(
                  dimension: 18,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : Text(
                  isRevision
                      ? _copy(context, '保存新版本', 'Save new version', '새 버전 저장')
                      : _copy(context, '保存报告', 'Save report', '보고서 저장'),
                ),
        ),
      ],
    );
  }
}

class _Sh04FormatDialog extends StatelessWidget {
  const _Sh04FormatDialog({required this.formats});

  final List<String> formats;

  @override
  Widget build(BuildContext context) => AlertDialog(
    title: Text(
      _copy(context, '选择导出格式', 'Choose an export format', '내보내기 형식 선택'),
    ),
    content: Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        for (final format in formats)
          ListTile(
            key: Key('sh04-export-$format'),
            leading: const LumenisIcon(Icons.article_outlined),
            title: Text(format.toUpperCase()),
            onTap: () => Navigator.of(context).pop(format),
          ),
      ],
    ),
    actions: [
      TextButton(
        onPressed: () => Navigator.of(context).pop(),
        child: Text(_copy(context, '取消', 'Cancel', '취소')),
      ),
    ],
  );
}

class _ExportQueue extends StatelessWidget {
  const _ExportQueue({required this.viewModel, required this.onReopen});

  final Sh04ViewModel viewModel;
  final ValueChanged<Sh04Export> onReopen;

  @override
  Widget build(BuildContext context) {
    final items = viewModel.exports;
    return _Panel(
      title: _copy(context, '成果队列', 'Output queue', '결과물 대기열'),
      detail: _copy(
        context,
        '每个条目都是已保存的报告版本；选择条目会向服务器重新打开该版本。',
        'Each entry is a saved report version. Selecting one reopens that version on the server.',
        '각 항목은 저장된 보고서 버전입니다. 선택하면 서버에서 해당 버전을 다시 엽니다.',
      ),
      child: items.isEmpty
          ? _InfoMessage(
              _copy(
                context,
                '共享工作区中还没有保存的报告。',
                'There are no saved reports in the Shared workspace yet.',
                '공유 작업공간에 저장된 보고서가 아직 없습니다.',
              ),
            )
          : Column(
              children: [
                for (final item in items)
                  _ExportRow(
                    item: item,
                    selected: viewModel.selected?.internalId == item.internalId,
                    onTap: viewModel.operationBusy
                        ? null
                        : () => onReopen(item),
                  ),
              ],
            ),
    );
  }
}

class _ExportRow extends StatelessWidget {
  const _ExportRow({
    required this.item,
    required this.selected,
    required this.onTap,
  });

  final Sh04Export item;
  final bool selected;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 8),
    child: Material(
      color: selected
          ? LumenisTheme.of(context).accentStrong.withValues(alpha: 0.1)
          : LumenisTheme.of(context).surfaceRaised,
      borderRadius: BorderRadius.circular(10),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(10),
        child: Container(
          constraints: const BoxConstraints(minHeight: 78),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          decoration: BoxDecoration(
            border: Border.all(
              color: selected
                  ? LumenisTheme.of(
                      context,
                    ).accentStrong.withValues(alpha: 0.55)
                  : LumenisTheme.of(context).line,
            ),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(
                _formatIcon(item.format),
                color: selected
                    ? LumenisTheme.of(context).accentStrong
                    : LumenisTheme.of(context).quiet,
                size: 19,
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      item.title,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontWeight: FontWeight.w600),
                    ),
                    const SizedBox(height: 6),
                    Wrap(
                      spacing: 8,
                      runSpacing: 4,
                      children: [
                        Text(
                          item.formatLabel,
                          style: TextStyle(
                            color: LumenisTheme.of(context).muted,
                            fontSize: 11,
                          ),
                        ),
                        Text(
                          _copy(
                            context,
                            '版本 ${item.version}',
                            'Version ${item.version}',
                            '버전 ${item.version}',
                          ),
                          style: TextStyle(
                            color: LumenisTheme.of(context).muted,
                            fontSize: 11,
                          ),
                        ),
                        _StateTag(
                          _exportStateLabel(context, item.state),
                          color: _stateColor(context, item.state),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 6),
              Icon(
                selected
                    ? Icons.chevron_right_rounded
                    : Icons.visibility_outlined,
                color: LumenisTheme.of(context).quiet,
                size: 18,
              ),
            ],
          ),
        ),
      ),
    ),
  );
}

class _ArtifactInspector extends StatelessWidget {
  const _ArtifactInspector({
    required this.exportItem,
    required this.scope,
    required this.busy,
    required this.onRevise,
    required this.onExport,
  });

  final Sh04Export? exportItem;
  final Sh04Scope scope;
  final bool busy;
  final VoidCallback? onRevise;
  final VoidCallback? onExport;

  @override
  Widget build(BuildContext context) {
    final item = exportItem;
    return _Panel(
      title: _copy(context, '成果预览', 'Output preview', '결과물 미리보기'),
      detail: _copy(
        context,
        '只显示由 Shared SavedWork 返回、版本链和原始引用已由服务器核验的报告。',
        'Only reports returned by Shared SavedWork with server-verified version and source references are shown.',
        'Shared SavedWork가 반환하고 서버가 버전 및 원본 참조를 확인한 보고서만 표시합니다.',
      ),
      child: item == null
          ? _InfoMessage(
              _copy(
                context,
                '选择一个成果查看状态。',
                'Select an output to inspect its state.',
                '결과물을 선택해 상태를 확인하세요.',
              ),
            )
          : Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  item.title,
                  style: const TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 12),
                _DetailLine(
                  label: _copy(context, '格式', 'Format', '형식'),
                  value: item.formatLabel,
                ),
                _DetailLine(
                  label: _copy(context, '状态', 'State', '상태'),
                  value: _exportStateLabel(context, item.state),
                ),
                _DetailLine(
                  label: _copy(context, '引用数', 'Citations', '인용 수'),
                  value: '${item.evidenceCount}',
                ),
                _DetailLine(
                  label: _copy(context, '版本', 'Version', '버전'),
                  value: '${item.version}',
                ),
                if (item.parentArtifactId != null)
                  _DetailLine(
                    label: _copy(context, '版本关系', 'Version history', '버전 기록'),
                    value: _copy(
                      context,
                      '基于上一保存版本修订',
                      'Revised from an earlier saved version',
                      '이전 저장 버전에서 수정됨',
                    ),
                  ),
                if (item.generatedAt.isNotEmpty)
                  _DetailLine(
                    label: _copy(context, '保存时间', 'Saved', '저장'),
                    value: item.generatedAt,
                  ),
                if (item.state == Sh04ExportState.ready && item.reopenable)
                  _VerifiedNotice(
                    _copy(
                      context,
                      '这是一个已保存的版本，可重新读取或修订。',
                      'This saved version can be reopened or revised.',
                      '저장된 버전을 다시 열거나 수정할 수 있습니다.',
                    ),
                  )
                else
                  _InfoMessage(
                    _copy(
                      context,
                      '当前没有可重新打开的真实成果。',
                      'There is no real output available to reopen.',
                      '다시 열 수 있는 실제 결과물이 없습니다.',
                    ),
                  ),
                if (item.preview.isNotEmpty) ...[
                  const SizedBox(height: 15),
                  Text(
                    _copy(context, '已保存内容', 'Saved content', '저장된 내용'),
                    style: TextStyle(
                      color: LumenisTheme.of(context).quiet,
                      fontSize: 11,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(13),
                    decoration: BoxDecoration(
                      color: LumenisTheme.of(context).canvas,
                      borderRadius: BorderRadius.circular(9),
                    ),
                    child: Text(
                      item.preview,
                      maxLines: 12,
                      overflow: TextOverflow.fade,
                      style: const TextStyle(height: 1.5),
                    ),
                  ),
                ],
                if (item.state == Sh04ExportState.ready &&
                    item.reopenable &&
                    item.preview.isNotEmpty)
                  ReadAloudAction(
                    sessionId: 'sh04:${item.internalId}',
                    scopeVersion:
                        '${scope.wireScopeKind}:${item.internalId}:${item.sha256}',
                    text: item.preview,
                    purpose: ReadAloudPurpose.savedPreview,
                  ),
                const SizedBox(height: 13),
                Wrap(
                  spacing: 10,
                  runSpacing: 8,
                  children: [
                    OutlinedButton.icon(
                      key: const Key('sh04-revise-report'),
                      onPressed: busy ? null : onRevise,
                      icon: const LumenisIcon(Icons.edit_outlined),
                      label: Text(
                        _copy(context, '修订版本', 'Revise version', '버전 수정'),
                      ),
                    ),
                    FilledButton.tonalIcon(
                      key: const Key('sh04-export-report'),
                      onPressed: busy ? null : onExport,
                      icon: const LumenisIcon(Icons.file_download_outlined),
                      label: Text(_copy(context, '导出', 'Export', '내보내기')),
                    ),
                  ],
                ),
              ],
            ),
    );
  }
}

class _VerifiedNotice extends StatelessWidget {
  const _VerifiedNotice(this.message);

  final String message;

  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 11),
    decoration: BoxDecoration(
      color: LumenisTheme.of(context).positive.withValues(alpha: 0.1),
      border: Border.all(
        color: LumenisTheme.of(context).positive.withValues(alpha: 0.35),
      ),
      borderRadius: BorderRadius.circular(9),
    ),
    child: Row(
      children: [
        Icon(
          Icons.check_circle_outline_rounded,
          color: LumenisTheme.of(context).positive,
          size: 18,
        ),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            message,
            style: TextStyle(
              color: LumenisTheme.of(context).muted,
              height: 1.4,
            ),
          ),
        ),
      ],
    ),
  );
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
        '当前账号没有这个范围的查看权限。',
        'This account cannot view the selected range.',
        '이 계정은 선택한 범위를 볼 수 없습니다.',
      ),
      Sh04ScopeErrorKind.malformed => _copy(
        context,
        '服务返回的范围不完整，因此不会显示成果。',
        'The returned range is incomplete, so outputs are not shown.',
        '반환된 범위가 불완전하여 결과물을 표시하지 않습니다.',
      ),
      _ => _copy(
        context,
        '尚未确认账号与成果范围的对应关系，因此不会显示成果。',
        'The account and output range have not been verified, so outputs are not shown.',
        '계정과 결과물 범위가 확인되지 않아 결과물을 표시하지 않습니다.',
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
        '成果服务暂时无法连接，请检查连接后重试。',
        'The output service cannot connect right now. Check the connection and try again.',
        '결과물 서비스에 연결할 수 없습니다. 연결을 확인하고 다시 시도하세요.',
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
  Widget build(BuildContext context) => Center(
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
  );
}

class _Panel extends StatelessWidget {
  const _Panel({required this.title, required this.child, this.detail});

  final String title;
  final String? detail;
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
        if (detail != null) ...[
          const SizedBox(height: 4),
          Text(
            detail!,
            style: TextStyle(
              color: LumenisTheme.of(context).quiet,
              fontSize: 11,
              height: 1.45,
            ),
          ),
        ],
        const SizedBox(height: 12),
        child,
      ],
    ),
  );
}

class _DetailLine extends StatelessWidget {
  const _DetailLine({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 10),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 86,
          child: Text(
            label,
            style: TextStyle(
              color: LumenisTheme.of(context).quiet,
              fontSize: 11,
            ),
          ),
        ),
        Expanded(
          child: Text(
            value,
            style: const TextStyle(fontWeight: FontWeight.w600),
          ),
        ),
      ],
    ),
  );
}

class _StateTag extends StatelessWidget {
  const _StateTag(this.label, {required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 4),
    decoration: BoxDecoration(
      color: color.withValues(alpha: 0.12),
      borderRadius: BorderRadius.circular(12),
    ),
    child: Text(
      label,
      style: TextStyle(color: color, fontSize: 10, fontWeight: FontWeight.w600),
    ),
  );
}

class _InfoMessage extends StatelessWidget {
  const _InfoMessage(this.message);

  final String message;

  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 15),
    decoration: BoxDecoration(
      color: LumenisTheme.of(context).canvas,
      borderRadius: BorderRadius.circular(9),
    ),
    child: Text(
      message,
      style: TextStyle(color: LumenisTheme.of(context).muted, height: 1.45),
    ),
  );
}

class _Eyebrow extends StatelessWidget {
  const _Eyebrow(this.label);

  final String label;

  @override
  Widget build(BuildContext context) => Text(
    label,
    style: TextStyle(
      color: LumenisTheme.of(context).accentStrong,
      fontSize: 10,
      letterSpacing: 1.1,
      fontWeight: FontWeight.w700,
    ),
  );
}

IconData _formatIcon(Sh04Format format) => switch (format) {
  Sh04Format.markdown => Icons.article_outlined,
};

Color _stateColor(BuildContext context, Sh04ExportState state) =>
    switch (state) {
      Sh04ExportState.ready => LumenisTheme.of(context).positive,
      Sh04ExportState.unavailable => LumenisTheme.of(context).muted,
    };

String _exportStateLabel(BuildContext context, Sh04ExportState state) =>
    switch (state) {
      Sh04ExportState.ready => _copy(context, '已保存', 'Saved', '저장됨'),
      Sh04ExportState.unavailable => _copy(
        context,
        '暂不可用',
        'Unavailable',
        '사용할 수 없음',
      ),
    };

String _copy(BuildContext context, String zh, String en, String ko) =>
    switch (context.lumenisL10n.locale.languageCode) {
      'en' => en,
      'ko' => ko,
      _ => zh,
    };
