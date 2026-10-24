import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';

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
  const Sh04Screen({
    required this.client,
    this.repository,
    this.initialArtifactId,
    super.key,
  });

  final LumenisCoreClient client;
  final Sh04Repository? repository;
  final String? initialArtifactId;

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
    _load();
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
      _load();
    }
  }

  Future<void> _load() => widget.initialArtifactId == null
      ? _viewModel.refresh()
      : _viewModel.openArtifact(widget.initialArtifactId!);

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
            onRetry: _load,
          ),
          Sh04LoadPhase.failed => _FailureState(
            kind: _viewModel.failureKind!,
            onRetry: _load,
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
    if (item.isManuscript) {
      context.go(
        Uri(
          path: '/workspace/SH-01',
          queryParameters: {'entry': 'manuscript', 'artifact': item.internalId},
        ).toString(),
      );
      return;
    }
    if (!item.canReviseHere) return;
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
    final choice = await showDialog<({String format, String purpose})>(
      context: context,
      builder: (dialogContext) => _Sh04FormatDialog(formats: formats),
    );
    if (choice == null || !_isCurrent(viewModel, generation)) {
      return;
    }
    try {
      final format = choice.format;
      final file = await viewModel.export(
        item,
        format,
        purpose: choice.purpose,
      );
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
      final snapshot = viewModel.snapshot!;
      final selected = viewModel.selected;
      final palette = LumenisTheme.of(context);
      final wide = constraints.maxWidth >= 900;
      final shelf = Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _ExportQueue(viewModel: viewModel, onReopen: onReopen),
          if (!snapshot.verificationComplete ||
              snapshot.unverifiedCandidates > 0)
            _InfoMessage(
              _copy(
                context,
                '部分作品暂时无法读取。',
                'Some works could not be read.',
                '일부 작품을 읽을 수 없습니다.',
              ),
            ),
          if (snapshot.hasMore)
            Padding(
              padding: const EdgeInsets.all(12),
              child: OutlinedButton(
                key: const Key('sh04-load-more'),
                onPressed: viewModel.operationBusy ? null : viewModel.loadMore,
                child: Text(
                  viewModel.loadMoreFailureKind == null
                      ? _copy(context, '加载更多', 'Load more', '더 보기')
                      : _copy(context, '重试读取', 'Retry reading', '다시 읽기'),
                ),
              ),
            ),
        ],
      );
      final page = _ArtifactInspector(
        exportItem: selected,
        scope: snapshot.scope,
        busy: viewModel.operationBusy,
        onRevise:
            selected != null &&
                (selected.canReviseHere || selected.isManuscript)
            ? () => onRevise(selected)
            : null,
        onExport: selected == null ? null : () => onExport(selected),
      );
      final toolbar = Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
        decoration: LumenisTheme.panel(palette, radius: 0),
        child: Wrap(
          spacing: 18,
          runSpacing: 12,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            Text(
              context.lumenisL10n.text('screen.SH-04'),
              style: const TextStyle(fontSize: 21, fontWeight: FontWeight.w600),
            ),
            Text(
              _copy(context, '共享工作区', 'Shared workspace', '공유 작업 공간'),
              style: TextStyle(color: palette.muted, fontSize: 12),
            ),
            FilledButton.icon(
              key: const Key('sh04-create-report'),
              onPressed: viewModel.operationBusy ? null : onCreate,
              icon: const LumenisIcon(Icons.edit_note_rounded),
              label: Text(_copy(context, '撰写报告', 'Write a report', '보고서 작성')),
            ),
            IconButton(
              onPressed: viewModel.refresh,
              tooltip: _copy(context, '重新读取', 'Read again', '다시 읽기'),
              icon: const LumenisIcon(Icons.refresh_rounded),
            ),
          ],
        ),
      );
      final compact = Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          toolbar,
          shelf,
          Padding(padding: const EdgeInsets.all(18), child: page),
        ],
      );
      return DecoratedBox(
        decoration: LumenisTheme.chassis(palette),
        child:
            wide && constraints.hasBoundedHeight && constraints.maxHeight >= 460
            ? Column(
                children: [
                  toolbar,
                  Expanded(
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Container(
                          width: 300,
                          decoration: LumenisTheme.panel(
                            palette,
                            radius: 0,
                            recessed: true,
                          ),
                          child: SingleChildScrollView(
                            padding: const EdgeInsets.all(12),
                            child: shelf,
                          ),
                        ),
                        Expanded(
                          child: SingleChildScrollView(
                            padding: const EdgeInsets.fromLTRB(32, 28, 32, 40),
                            child: page,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              )
            : SingleChildScrollView(child: compact),
      );
    },
  );
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

class _Sh04FormatDialog extends StatefulWidget {
  const _Sh04FormatDialog({required this.formats});

  final List<String> formats;

  @override
  State<_Sh04FormatDialog> createState() => _Sh04FormatDialogState();
}

class _Sh04FormatDialogState extends State<_Sh04FormatDialog> {
  String _purpose = 'delivery';

  @override
  Widget build(BuildContext context) => AlertDialog(
    title: Text(
      _copy(context, '选择导出格式', 'Choose an export format', '내보내기 형식 선택'),
    ),
    content: Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        SegmentedButton<String>(
          segments: [
            ButtonSegment(
              value: 'delivery',
              label: Text(_copy(context, '交付文件', 'Delivery', '전달 파일')),
            ),
            ButtonSegment(
              value: 'audit_snapshot',
              label: Text(_copy(context, '归档副本', 'Archive', '보관 사본')),
            ),
          ],
          selected: {_purpose},
          onSelectionChanged: (value) =>
              setState(() => _purpose = value.single),
        ),
        const SizedBox(height: 12),
        for (final format in widget.formats)
          ListTile(
            key: Key('sh04-export-$format'),
            leading: const LumenisIcon(Icons.article_outlined),
            title: Text(format.toUpperCase()),
            onTap: () =>
                Navigator.of(context).pop((format: format, purpose: _purpose)),
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
    final palette = LumenisTheme.of(context);
    if (item == null) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 64),
        child: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              LumenisIcon(
                Icons.menu_book_outlined,
                size: 64,
                color: palette.quiet,
              ),
              const SizedBox(height: 20),
              Text(
                _copy(context, '选择一份作品', 'Choose a work', '작품 선택'),
                style: TextStyle(fontSize: 18, color: palette.muted),
              ),
            ],
          ),
        ),
      );
    }
    return Align(
      alignment: Alignment.topCenter,
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 840),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Wrap(
              spacing: 12,
              runSpacing: 10,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                Text(
                  _copy(
                    context,
                    '版本 ${item.version}',
                    'Version ${item.version}',
                    '버전 ${item.version}',
                  ),
                  style: TextStyle(color: palette.muted),
                ),
                if (onRevise != null)
                  OutlinedButton.icon(
                    key: const Key('sh04-revise-report'),
                    onPressed: busy ? null : onRevise,
                    icon: const LumenisIcon(Icons.edit_outlined),
                    label: Text(
                      item.isManuscript
                          ? _copy(context, '打开文稿', 'Open document', '문서 열기')
                          : _copy(context, '修订版本', 'Revise version', '버전 수정'),
                    ),
                  ),
                FilledButton.icon(
                  key: const Key('sh04-export-report'),
                  onPressed: busy ? null : onExport,
                  icon: const LumenisIcon(Icons.file_download_outlined),
                  label: Text(_copy(context, '导出', 'Export', '내보내기')),
                ),
                if (item.reopenable)
                  ReadAloudAction(
                    sessionId: 'sh04:${item.internalId}',
                    scopeVersion:
                        '${scope.wireScopeKind}:${item.internalId}:${item.sha256}',
                    text: item.preview,
                    purpose: ReadAloudPurpose.savedPreview,
                  ),
              ],
            ),
            const SizedBox(height: 22),
            Container(
              width: double.infinity,
              padding: EdgeInsets.all(
                MediaQuery.sizeOf(context).width < 600 ? 22 : 42,
              ),
              decoration: BoxDecoration(
                color: palette.surface,
                border: Border.all(color: palette.line),
                borderRadius: BorderRadius.circular(3),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: .16),
                    blurRadius: 20,
                    offset: const Offset(0, 8),
                  ),
                  BoxShadow(
                    color: palette.surfaceRaised,
                    offset: const Offset(3, 3),
                    spreadRadius: 1,
                  ),
                ],
              ),
              child: SelectionArea(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text(
                      item.title,
                      style: const TextStyle(
                        fontSize: 26,
                        fontWeight: FontWeight.w600,
                        height: 1.4,
                      ),
                    ),
                    const SizedBox(height: 24),
                    _ReportText(item.preview),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ReportText extends StatelessWidget {
  const _ReportText(this.text);

  final String text;

  @override
  Widget build(BuildContext context) {
    var fenced = false;
    final blocks = <Widget>[];
    final paragraph = <String>[];
    void flush() {
      if (paragraph.isEmpty) return;
      blocks.add(
        Padding(
          padding: const EdgeInsets.only(bottom: 14),
          child: Text(
            paragraph.join('\n'),
            style: const TextStyle(fontSize: 16, height: 1.8),
          ),
        ),
      );
      paragraph.clear();
    }

    for (final line in text.split('\n')) {
      if (line.trimLeft().startsWith('```')) fenced = !fenced;
      final heading = fenced
          ? null
          : RegExp(r'^(#{1,6})\s+(.+)$').firstMatch(line);
      if (heading != null) {
        flush();
        blocks.add(
          Padding(
            padding: const EdgeInsets.only(top: 12, bottom: 12),
            child: Semantics(
              header: true,
              child: Text(
                heading.group(2)!,
                style: TextStyle(
                  fontSize: heading.group(1)!.length == 1 ? 23 : 19,
                  fontWeight: FontWeight.w600,
                  height: 1.5,
                ),
              ),
            ),
          ),
        );
      } else if (!fenced && line.trim().isEmpty) {
        flush();
      } else {
        paragraph.add(line);
      }
    }
    flush();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: blocks,
    );
  }
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
