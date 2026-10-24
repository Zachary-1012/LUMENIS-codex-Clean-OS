import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import '../../../core/lumenis_core_client.dart';
import '../../../core/lumenis_icon.dart';
import '../../../core/lumenis_theme.dart';
import '../../../navigation/lumenis_leave_guard.dart';
import '../read_aloud_action.dart';
import 'manuscript_controller.dart';
import 'manuscript_draft_files.dart';
import 'media_project_files.dart';

/// The existing Shared manuscript owner, presented as a writing surface.
/// User writing stays local until an explicit save; it is not external fact.
class ManuscriptEditor extends StatefulWidget {
  const ManuscriptEditor({
    required this.client,
    required this.onBack,
    this.invokingDomain,
    this.contextAvailable = true,
    this.controller,
    this.draftFiles,
    this.outputFiles,
    this.initialArtifactId,
    this.onSaved,
    super.key,
  });

  final LumenisCoreClient client;
  final VoidCallback onBack;
  final String? invokingDomain;
  final bool contextAvailable;
  final ManuscriptController? controller;
  final ManuscriptDraftFiles? draftFiles;
  final MediaProjectFiles? outputFiles;
  final String? initialArtifactId;
  final ValueChanged<String>? onSaved;

  @override
  State<ManuscriptEditor> createState() => _ManuscriptEditorState();
}

class _SectionDraft {
  _SectionDraft({String heading = '', String body = ''})
    : heading = TextEditingController(text: heading),
      body = TextEditingController(text: body);
  final TextEditingController heading;
  final TextEditingController body;
  void dispose() {
    heading.dispose();
    body.dispose();
  }
}

class _ManuscriptEditorState extends State<ManuscriptEditor> {
  final _title = TextEditingController();
  final _summary = TextEditingController();
  final _sections = <_SectionDraft>[_SectionDraft()];
  late final ManuscriptController _controller;
  late final ManuscriptDraftFiles _draftFiles;
  late final MediaProjectFiles _outputFiles;
  LumenisLeaveGuard? _guard;
  int _selected = 0;
  int _revision = 0;
  bool _preview = false;
  bool _outlineVisible = false;
  bool _fileBusy = false;
  bool _loadingDraft = false;
  String _language = 'zh';
  String _authorship = 'user_supplied';
  String _baseline = '';
  String? _notice;
  String? _appliedArtifact;
  _SectionDraft? _removed;
  int? _removedAt;

  String _t(String zh, String en, String ko) =>
      switch (Localizations.localeOf(context).languageCode) {
        'zh' => zh,
        'ko' => ko,
        _ => en,
      };

  Map<String, dynamic> get _draft => {
    'title': _title.text,
    'summary': _summary.text,
    'sections': [
      for (final section in _sections)
        {'heading': section.heading.text, 'body': section.body.text},
    ],
    'language': _language,
    'authorship': _authorship,
  };

  InternalPitchManuscript get _manuscript => InternalPitchManuscript(
    title: _title.text,
    summary: _summary.text,
    sections: [
      for (final section in _sections)
        InternalPitchSection(
          heading: section.heading.text,
          body: section.body.text,
        ),
    ],
    language: _language,
    authorship: _authorship,
  );

  bool get _busy => _controller.busy || _fileBusy;
  bool get _dirty => jsonEncode(_draft) != _baseline;
  bool get _sectionLimitReached =>
      _sections.length + (_removed == null ? 0 : 1) >= 64;
  bool get _valid =>
      _title.text.trim().isNotEmpty &&
      _title.text.trim().runes.length <= 300 &&
      _summary.text.trim().isNotEmpty &&
      _sections.every(
        (s) =>
            s.heading.text.trim().isNotEmpty && s.body.text.trim().isNotEmpty,
      );

  LumenisWorkspaceScope? _scope() {
    final invokingDomain = widget.invokingDomain?.trim().toUpperCase();
    if (invokingDomain == null || invokingDomain == 'SHARED') {
      return const SharedWorkspaceScope();
    }
    if (invokingDomain != 'CTH' && invokingDomain != 'BMP') return null;
    if (!widget.contextAvailable) return null;
    final envelope = widget.client.currentContextEnvelope?['context'];
    if (envelope is! Map) return null;
    final mode = envelope['mode'];
    final domain = mode == 'FOCUS'
        ? (envelope['domain_id'] as String?)?.toUpperCase()
        : null;
    if (mode != 'FOCUS' || domain != invokingDomain) return null;
    final subject = envelope['subject_id'];
    final brand = envelope['brand_focus_id'];
    if (domain == 'CTH' &&
        (subject is! String || subject.isEmpty || brand != null)) {
      return null;
    }
    if (domain == 'BMP' &&
        (brand is! String || brand.isEmpty || subject != null)) {
      return null;
    }
    return InternalPitchScope(
      domainId: domain == 'BMP' ? 'bmp' : 'cth',
      subjectId: subject as String?,
      brandFocusId: brand as String?,
      globalScope: false,
    );
  }

  @override
  void initState() {
    super.initState();
    _draftFiles = widget.draftFiles ?? ManuscriptDraftFiles();
    _outputFiles = widget.outputFiles ?? MediaProjectFiles();
    _controller =
        widget.controller ??
        ManuscriptController(
          client: widget.client,
          scope: _scope(),
          draft: _manuscript,
        );
    _baseline = jsonEncode(_draft);
    _title.addListener(_edit);
    _summary.addListener(_edit);
    for (final section in _sections) {
      _listen(section);
    }
    _controller.addListener(_changed);
    final artifact = widget.initialArtifactId;
    if (artifact != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) _reopenArtifact(artifact);
      });
    }
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final next = LumenisLeaveScope.maybeOf(context);
    if (identical(next, _guard)) return;
    _guard?.unregister(this);
    _guard = next;
    _guard?.register(
      this,
      needsProtection: () => _dirty || _busy || _controller.hasUnresolvedSave,
      requestLeave: _leaveDecision,
    );
  }

  @override
  void didUpdateWidget(covariant ManuscriptEditor oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.controller == null) _controller.updateScope(_scope());
  }

  void _listen(_SectionDraft section) {
    section.heading.addListener(_edit);
    section.body.addListener(_edit);
  }

  void _edit() {
    if (_loadingDraft) return;
    _revision++;
    _controller.updateDraft(_manuscript);
    _guard?.refresh();
    if (mounted) setState(() => _notice = null);
  }

  void _changed() {
    if (!mounted) return;
    _guard?.refresh();
    setState(() {});
  }

  void _adopt(InternalPitchManuscript draft, {bool clean = true}) {
    _loadingDraft = true;
    _title.text = draft.title;
    _summary.text = draft.summary;
    for (final section in _sections) {
      section.dispose();
    }
    _sections.clear();
    for (final section in draft.sections) {
      final item = _SectionDraft(heading: section.heading, body: section.body);
      _listen(item);
      _sections.add(item);
    }
    _removed?.dispose();
    _removed = null;
    _selected = 0;
    _language = draft.language;
    _authorship = draft.authorship;
    _loadingDraft = false;
    _revision++;
    _controller.updateDraft(_manuscript);
    if (clean) _baseline = jsonEncode(_draft);
    _guard?.refresh();
    setState(() {});
  }

  Future<bool> _leaveDecision() async {
    if (_busy) {
      setState(
        () => _notice = _t(
          '操作进行中，请稍候。',
          'An operation is in progress.',
          '작업이 진행 중입니다.',
        ),
      );
      return false;
    }
    if (_controller.hasUnresolvedSave) {
      setState(
        () => _notice = _t(
          '本次保存尚未确认，请先核对或恢复保存。当前文稿仍可保存为本地草稿。',
          'This save is not confirmed yet. Check or recover it before leaving. You can keep a local draft copy.',
          '저장이 아직 확인되지 않았습니다. 나가기 전에 상태를 확인하거나 복구하세요. 로컬 초안은 저장할 수 있습니다.',
        ),
      );
      return false;
    }
    if (!_dirty) return true;
    return await showDialog<bool>(
          context: context,
          builder: (context) => AlertDialog(
            title: Text(_t('保留当前文稿？', 'Keep this draft?', '현재 초안을 유지할까요?')),
            content: Text(
              _t(
                '尚有未保存的修改。离开后这些修改将丢失。',
                'Unsaved changes will be lost when you leave.',
                '저장하지 않은 변경 사항은 나가면 사라집니다.',
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context, false),
                child: Text(_t('继续编辑', 'Keep editing', '계속 편집')),
              ),
              TextButton(
                onPressed: () => Navigator.pop(context, true),
                child: Text(_t('放弃修改', 'Discard changes', '변경 취소')),
              ),
            ],
          ),
        ) ??
        false;
  }

  Future<void> _back() async {
    if (await _leaveDecision() && mounted) widget.onBack();
  }

  Future<void> _save() async {
    setState(() => _notice = null);
    _controller.updateDraft(_manuscript);
    final sent = jsonEncode(_draft);
    await _controller.save();
    if (!mounted) return;
    _acceptSaved(sent);
  }

  void _acceptSaved(String sent) {
    final saved = _controller.savedWork;
    if (_controller.errorCode != null ||
        _controller.taskState != 'succeeded' ||
        saved == null ||
        saved.taskId != _controller.taskId ||
        saved.artifactId == _appliedArtifact) {
      return;
    }
    _appliedArtifact = saved.artifactId;
    // Network completion must never replace typing made after its snapshot.
    final accepted = jsonEncode(saved.manuscript.toJson());
    if (jsonEncode(_draft) == accepted && sent == accepted) {
      _baseline = accepted;
    }
    _guard?.refresh();
    setState(
      () => _notice = _t(
        '已保存，可继续修订。',
        'Saved. You can continue revising.',
        '저장되었습니다. 계속 수정할 수 있습니다.',
      ),
    );
    if (jsonEncode(_draft) == accepted && sent == accepted) {
      widget.onSaved?.call(saved.artifactId);
    }
  }

  Future<void> _recover(Future<void> Function() action) async {
    setState(() => _notice = null);
    final sent = jsonEncode(_draft);
    await action();
    if (mounted) _acceptSaved(sent);
  }

  Future<void> _saveLocal() async {
    final draft = _draft;
    final sent = jsonEncode(draft);
    setState(() => _fileBusy = true);
    _guard?.refresh();
    try {
      final saved = await _draftFiles.save(draft);
      if (!mounted || !saved) return;
      if (!kIsWeb && sent == jsonEncode(_draft)) _baseline = sent;
      setState(
        () => _notice = kIsWeb
            ? _t(
                '已请求下载草稿，请在浏览器确认文件已保存。',
                'Draft download requested. Check your browser for the saved file.',
                '초안 다운로드를 요청했습니다. 브라우저에서 저장을 확인하세요.',
              )
            : _t('草稿文件已保存。', 'Draft file saved.', '초안 파일을 저장했습니다.'),
      );
    } catch (_) {
      if (mounted) {
        setState(
          () => _notice = _t(
            '草稿未保存，请重试；当前内容仍保留。',
            'Draft was not saved. Your writing is still here; try again.',
            '초안을 저장하지 못했습니다. 내용은 유지됩니다. 다시 시도하세요.',
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _fileBusy = false);
        _guard?.refresh();
      }
    }
  }

  Future<void> _openLocal() async {
    if (!await _leaveDecision() || !mounted) return;
    setState(() => _fileBusy = true);
    _guard?.refresh();
    try {
      final data = await _draftFiles.open();
      if (data == null || !mounted) return;
      // A local draft deliberately carries no server identity or scope grant.
      final next = InternalPitchManuscript(
        title: data['title'] as String,
        summary: data['summary'] as String,
        sections: [
          for (final s in data['sections'] as List)
            InternalPitchSection(
              heading: s['heading'] as String,
              body: s['body'] as String,
            ),
        ],
        language: data['language'] as String,
        authorship: data['authorship'] as String,
      );
      if (!_controller.startNewDraft(next)) return;
      _appliedArtifact = null;
      _adopt(next);
      setState(
        () => _notice = _t('已打开草稿文件。', 'Draft file opened.', '초안 파일을 열었습니다.'),
      );
    } catch (_) {
      if (mounted) {
        setState(
          () => _notice = _t(
            '无法读取这份草稿，原文稿仍保留。',
            'This draft could not be read. Your current writing is preserved.',
            '초안을 읽을 수 없습니다. 기존 내용은 유지됩니다.',
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _fileBusy = false);
        _guard?.refresh();
      }
    }
  }

  Future<void> _export() async {
    setState(() => _fileBusy = true);
    _guard?.refresh();
    try {
      final file = await _controller.export();
      if (!mounted || file == null) return;
      final saved = await _outputFiles.save(
        ContentProjectFile(
          bytes: file.bytes,
          filename: file.filename,
          mediaType: file.mediaType,
        ),
      );
      if (mounted && saved) {
        setState(
          () => _notice = kIsWeb
              ? _t(
                  '已请求下载已保存版本。',
                  'Saved version download requested.',
                  '저장된 버전 다운로드를 요청했습니다.',
                )
              : _t('已导出已保存版本。', 'Saved version exported.', '저장된 버전을 내보냈습니다.'),
        );
      }
    } catch (_) {
      if (mounted) {
        setState(
          () => _notice = _t(
            '导出未完成，已保存版本仍可重试。',
            'Export did not finish. The saved version remains available.',
            '내보내기를 완료하지 못했습니다. 저장된 버전은 유지됩니다.',
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _fileBusy = false);
        _guard?.refresh();
      }
    }
  }

  Future<void> _library() async {
    if (_busy || !await _leaveDecision() || !mounted) return;
    _controller.list();
    final chosen = await showDialog<String>(
      context: context,
      builder: (dialogContext) => Dialog(
        child: SizedBox(
          width: 560,
          height: 520,
          child: AnimatedBuilder(
            animation: _controller,
            builder: (context, _) => Column(
              children: [
                Padding(
                  padding: const EdgeInsets.fromLTRB(20, 8, 8, 8),
                  child: Row(
                    children: [
                      Expanded(
                        child: Text(
                          _t('保存的文稿', 'Saved writing', '저장한 문서'),
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                      ),
                      IconButton(
                        tooltip: _t('关闭', 'Close', '닫기'),
                        onPressed: () => Navigator.pop(dialogContext),
                        icon: const LumenisIcon(Icons.close),
                      ),
                    ],
                  ),
                ),
                if (_controller.busy) const LinearProgressIndicator(),
                Expanded(
                  child: ListView(
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    children: [
                      if (_controller.errorCode != null) Text(_errorText()),
                      if (!_controller.busy && _controller.items.isEmpty)
                        Padding(
                          padding: const EdgeInsets.all(16),
                          child: Text(
                            _controller.hasMore
                                ? _t(
                                    '本页没有文稿，可继续查看。',
                                    'No manuscripts on this page. More pages are available.',
                                    '이 페이지에 문서가 없습니다. 다음 페이지를 확인할 수 있습니다.',
                                  )
                                : _t(
                                    '暂未读取到保存的文稿。',
                                    'No saved writing was returned.',
                                    '저장한 문서가 반환되지 않았습니다.',
                                  ),
                          ),
                        ),
                      for (final item in _controller.items)
                        ListTile(
                          title: Text(item.manuscript.title),
                          subtitle: Text(
                            '${_t('版本 ${item.version}', 'Version ${item.version}', '버전 ${item.version}')} · ${item.manuscript.summary}',
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                          ),
                          trailing: const LumenisIcon(
                            Icons.arrow_outward,
                            size: 18,
                          ),
                          onTap: _controller.busy
                              ? null
                              : () => Navigator.pop(
                                  dialogContext,
                                  item.artifactId,
                                ),
                        ),
                      if (_controller.hasMore)
                        TextButton(
                          onPressed: _controller.busy
                              ? null
                              : _controller.loadMore,
                          child: Text(_t('继续查看', 'Load more', '더 보기')),
                        ),
                    ],
                  ),
                ),
                TextButton(
                  onPressed: _controller.busy ? null : _controller.list,
                  child: Text(_t('重新读取', 'Reload', '다시 불러오기')),
                ),
              ],
            ),
          ),
        ),
      ),
    );
    if (chosen == null || !mounted) return;
    await _reopenArtifact(chosen);
  }

  Future<void> _reopenArtifact(String chosen) async {
    await _controller.reopen(chosen);
    if (!mounted) return;
    final saved = _controller.savedWork;
    if (saved?.artifactId == chosen) {
      _appliedArtifact = chosen;
      _adopt(saved!.manuscript);
    }
  }

  Future<void> _continueFromLatest() async {
    if (!_controller.canContinueFromLatest) return;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(
          _t('保留当前文字继续修订？', 'Continue with this writing?', '현재 내용으로 계속 수정할까요?'),
        ),
        content: Text(
          _t(
            '下一次保存会在最新版本之后新增一版，已有版本保持不变。',
            'Your next save adds a version after the latest one. Existing versions stay unchanged.',
            '다음 저장은 최신 버전 다음에 새 버전을 추가합니다. 기존 버전은 유지됩니다.',
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: Text(_t('取消', 'Cancel', '취소')),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: Text(_t('继续修订', 'Continue revising', '계속 수정')),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;
    await _controller.continueFromLatest();
    if (!mounted || _controller.errorCode != null) return;
    _appliedArtifact = _controller.savedWork?.artifactId;
    _baseline = jsonEncode(_controller.savedWork!.manuscript.toJson());
    _guard?.refresh();
    setState(() => _notice = null);
  }

  String _errorText() {
    final error = _controller.errorCode ?? '';
    if (error.contains('CONFLICT') ||
        error.contains('DIGEST') ||
        error.contains('PARENT')) {
      return _t(
        '已保存版本发生变化。请保留本地草稿，再读取最新版本。',
        'The saved version changed. Keep a local copy, then reopen the latest version.',
        '저장된 버전이 변경되었습니다. 로컬 초안을 보관한 뒤 최신 버전을 여세요.',
      );
    }
    if (error.contains('PERMISSION') || error.contains('DENIED')) {
      return _t(
        '当前无法保存到此位置，文稿仍保留；可以保存草稿文件。',
        'Saving here is unavailable. Your writing is preserved; you can save a draft file.',
        '현재 이 위치에 저장할 수 없습니다. 내용은 유지되며 초안 파일로 저장할 수 있습니다.',
      );
    }
    return _t(
      '操作未完成。文稿仍保留，请核对保存状态后重试。',
      'The operation did not finish. Your writing is preserved. Check save status before retrying.',
      '작업을 완료하지 못했습니다. 내용은 유지됩니다. 저장 상태를 확인한 뒤 다시 시도하세요.',
    );
  }

  void _addSection() {
    // Keep the removed paragraph recoverable even at the document limit.
    if (_sectionLimitReached || _busy) return;
    final section = _SectionDraft();
    _listen(section);
    setState(() {
      _sections.add(section);
      _selected = _sections.length - 1;
      _preview = false;
    });
    _edit();
  }

  void _move(int delta) {
    final destination = _selected + delta;
    if (_busy || destination < 0 || destination >= _sections.length) return;
    setState(() {
      final section = _sections.removeAt(_selected);
      _sections.insert(destination, section);
      _selected = destination;
    });
    _edit();
  }

  void _remove() {
    if (_busy || _sections.length == 1) return;
    _removed?.dispose();
    setState(() {
      _removedAt = _selected;
      _removed = _sections.removeAt(_selected);
      _selected = _selected.clamp(0, _sections.length - 1);
    });
    _edit();
  }

  void _undoRemove() {
    final removed = _removed;
    if (removed == null || _busy || _sections.length >= 64) return;
    setState(() {
      _selected = _removedAt!.clamp(0, _sections.length);
      _sections.insert(_selected, removed);
      _removed = null;
    });
    _edit();
  }

  @override
  void dispose() {
    _guard?.unregister(this);
    _controller.removeListener(_changed);
    if (widget.controller == null) _controller.dispose();
    _title.dispose();
    _summary.dispose();
    for (final section in _sections) {
      section.dispose();
    }
    _removed?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final colors = LumenisTheme.of(context);
    return Material(
      color: colors.canvas,
      child: SafeArea(
        child: LayoutBuilder(
          builder: (context, box) {
            final wide =
                box.maxWidth >= 960 &&
                MediaQuery.textScalerOf(context).scale(14) <= 22;
            return Column(
              children: [
                _header(wide),
                if (_busy) const LinearProgressIndicator(minHeight: 2),
                if (_notice != null || _controller.errorCode != null)
                  _message(
                    _controller.errorCode != null ? _errorText() : _notice!,
                  ),
                if (_controller.scope == null)
                  _message(
                    _t(
                      '可直接写作、预览和保存草稿文件。在线保存暂未连接。',
                      'Write, preview and save a draft file. Online saving is not connected yet.',
                      '작성, 미리보기, 초안 파일 저장이 가능합니다. 온라인 저장은 아직 연결되지 않았습니다.',
                    ),
                  ),
                if (_controller.taskId != null &&
                    (_controller.hasUnresolvedSave ||
                        _controller.errorCode != null))
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    child: Wrap(
                      spacing: 8,
                      children: [
                        TextButton(
                          onPressed: _busy
                              ? null
                              : () => _recover(_controller.read),
                          child: Text(
                            _t('核对保存状态', 'Check save status', '저장 상태 확인'),
                          ),
                        ),
                        if (_controller.runRetryAvailable)
                          TextButton(
                            onPressed: _busy
                                ? null
                                : () => _recover(_controller.retryRun),
                            child: Text(_t('重试保存', 'Retry saving', '저장 재시도')),
                          ),
                        if (_controller.hasUnresolvedSave)
                          TextButton(
                            onPressed: _busy
                                ? null
                                : () => _recover(_controller.cancel),
                            child: Text(
                              _t('停止本次保存', 'Stop this save', '이번 저장 중지'),
                            ),
                          ),
                        if (_controller.canContinueFromLatest)
                          TextButton(
                            onPressed: _continueFromLatest,
                            child: Text(
                              _t(
                                '保留当前文字继续修订',
                                'Continue with this writing',
                                '현재 내용으로 계속 수정',
                              ),
                            ),
                          ),
                      ],
                    ),
                  ),
                if (_controller.prepareAcknowledgementLost)
                  TextButton(
                    onPressed: _busy
                        ? null
                        : () => _recover(_controller.retryPrepare),
                    child: Text(_t('恢复本次保存', 'Recover this save', '이번 저장 복구')),
                  ),
                const Divider(height: 1),
                if (!wide)
                  Padding(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 4,
                    ),
                    child: SegmentedButton<bool>(
                      segments: [
                        ButtonSegment(
                          value: false,
                          label: Text(_t('编辑', 'Edit', '편집')),
                          icon: const LumenisIcon(
                            Icons.edit_outlined,
                            size: 18,
                          ),
                        ),
                        ButtonSegment(
                          value: true,
                          label: Text(_t('预览', 'Preview', '미리보기')),
                          icon: const LumenisIcon(
                            Icons.chrome_reader_mode_outlined,
                            size: 18,
                          ),
                        ),
                      ],
                      selected: {_preview},
                      onSelectionChanged: (value) =>
                          setState(() => _preview = value.first),
                    ),
                  ),
                Expanded(
                  child: wide
                      ? Row(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            if (_outlineVisible) ...[
                              SizedBox(width: 208, child: _outline()),
                              const VerticalDivider(width: 1),
                            ],
                            Expanded(child: _writingSurface()),
                          ],
                        )
                      : _preview
                      ? _document()
                      : _editor(compact: true),
                ),
              ],
            );
          },
        ),
      ),
    );
  }

  Widget _fileMenu() => PopupMenuButton<String>(
    tooltip: _t('文稿操作', 'Writing actions', '문서 작업'),
    enabled: !_busy,
    onSelected: (action) {
      if (action == 'save-local') _saveLocal();
      if (action == 'open-local') _openLocal();
      if (action == 'export') _export();
      if (action == 'continue-latest') _continueFromLatest();
    },
    itemBuilder: (context) => [
      if (_controller.savedWork != null)
        PopupMenuItem(
          value: 'continue-latest',
          enabled: _controller.canContinueFromLatest,
          child: Text(
            _t('保留当前文字继续修订', 'Continue with this writing', '현재 내용으로 계속 수정'),
          ),
        ),
      PopupMenuItem(
        value: 'save-local',
        enabled: _draftFiles.canSave,
        child: Text(_t('保存草稿文件', 'Save draft file', '초안 파일 저장')),
      ),
      PopupMenuItem(
        value: 'open-local',
        child: Text(_t('打开草稿文件', 'Open draft file', '초안 파일 열기')),
      ),
      PopupMenuItem(
        value: 'export',
        enabled: _controller.savedWork != null && _outputFiles.canSave,
        child: Text(
          _t(
            '导出已保存文稿 · DOCX',
            'Export saved writing · DOCX',
            '저장한 문서 내보내기 · DOCX',
          ),
        ),
      ),
    ],
  );

  Widget _header(bool wide) {
    final savedVersion = _controller.savedWork?.version;
    final status = _dirty
        ? _t('未保存修改', 'Unsaved changes', '저장하지 않은 변경')
        : savedVersion != null
        ? _t(
            '已保存 · 版本 $savedVersion',
            'Saved · Version $savedVersion',
            '저장됨 · 버전 $savedVersion',
          )
        : _t('草稿', 'Draft', '초안');
    final back = IconButton(
      key: const Key('manuscript-back'),
      tooltip: _t('返回创作', 'Back to creation', '창작으로 돌아가기'),
      onPressed: _back,
      icon: const LumenisIcon(Icons.arrow_back),
    );
    final title = Text(
      _t('文稿', 'Writing', '문서'),
      maxLines: 1,
      overflow: TextOverflow.ellipsis,
      style: Theme.of(context).textTheme.titleMedium,
    );
    final save = _busy || !_valid || !_controller.canSave ? null : _save;
    final open = _busy || _controller.scope == null ? null : _library;
    return Padding(
      padding: const EdgeInsets.fromLTRB(8, 4, 8, 4),
      child: wide
          ? Row(
              children: [
                back,
                const SizedBox(width: 8),
                title,
                const SizedBox(width: 16),
                Expanded(
                  child: Text(
                    status,
                    style: Theme.of(context).textTheme.labelMedium,
                  ),
                ),
                TextButton.icon(
                  key: const Key('manuscript-library'),
                  onPressed: open,
                  icon: const LumenisIcon(Icons.folder_open_outlined, size: 18),
                  label: Text(_t('打开', 'Open', '열기')),
                ),
                IconButton(
                  key: const Key('manuscript-outline-toggle'),
                  tooltip: _t('目录', 'Outline', '목차'),
                  isSelected: _outlineVisible,
                  onPressed: () =>
                      setState(() => _outlineVisible = !_outlineVisible),
                  icon: const LumenisIcon(
                    Icons.format_list_bulleted_rounded,
                    size: 20,
                  ),
                ),
                IconButton(
                  key: const Key('manuscript-preview-toggle'),
                  tooltip: _preview
                      ? _t('编辑', 'Edit', '편집')
                      : _t('预览', 'Preview', '미리보기'),
                  isSelected: _preview,
                  onPressed: () => setState(() => _preview = !_preview),
                  icon: LumenisIcon(
                    _preview
                        ? Icons.edit_outlined
                        : Icons.chrome_reader_mode_outlined,
                    size: 20,
                  ),
                ),
                const SizedBox(width: 8),
                FilledButton(
                  key: const Key('manuscript-save'),
                  onPressed: save,
                  child: Text(_t('保存版本', 'Save version', '버전 저장')),
                ),
                _fileMenu(),
              ],
            )
          : Row(
              children: [
                back,
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      title,
                      Text(
                        status,
                        style: Theme.of(context).textTheme.labelSmall,
                      ),
                    ],
                  ),
                ),
                IconButton(
                  key: const Key('manuscript-library'),
                  tooltip: _t('打开保存的文稿', 'Open saved writing', '저장한 문서 열기'),
                  onPressed: open,
                  icon: const LumenisIcon(Icons.folder_open_outlined, size: 20),
                ),
                IconButton(
                  key: const Key('manuscript-save'),
                  tooltip: _t('保存版本', 'Save version', '버전 저장'),
                  onPressed: save,
                  icon: const LumenisIcon(Icons.save_outlined, size: 20),
                ),
                _fileMenu(),
              ],
            ),
    );
  }

  Widget _message(String text) => Padding(
    padding: const EdgeInsets.fromLTRB(16, 4, 16, 8),
    child: ConstrainedBox(
      constraints: const BoxConstraints(maxHeight: 88),
      child: SingleChildScrollView(
        child: Align(
          alignment: Alignment.centerLeft,
          child: Semantics(
            liveRegion: true,
            child: Text(text, style: Theme.of(context).textTheme.bodySmall),
          ),
        ),
      ),
    ),
  );

  Widget _outline() => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      Padding(
        padding: const EdgeInsets.all(16),
        child: Text(
          _t('段落', 'Outline', '문단'),
          style: Theme.of(context).textTheme.labelLarge,
        ),
      ),
      Expanded(
        child: ListView(
          children: [
            for (var i = 0; i < _sections.length; i++)
              ListTile(
                selected: _selected == i,
                leading: Text('${i + 1}'.padLeft(2, '0')),
                title: Text(
                  _sections[i].heading.text.isEmpty
                      ? _t('未命名段落', 'Untitled section', '제목 없는 문단')
                      : _sections[i].heading.text,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
                onTap: () => setState(() => _selected = i),
              ),
          ],
        ),
      ),
      TextButton.icon(
        onPressed: _busy || _sectionLimitReached ? null : _addSection,
        icon: const LumenisIcon(Icons.add, size: 18),
        label: Text(_t('添加段落', 'Add section', '문단 추가')),
      ),
    ],
  );

  Widget _writingSurface() {
    final palette = LumenisTheme.of(context);
    return Padding(
      padding: const EdgeInsets.fromLTRB(24, 24, 24, 0),
      child: Align(
        alignment: Alignment.topCenter,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 860),
          child: DecoratedBox(
            decoration: BoxDecoration(
              color: palette.surface,
              border: Border.all(color: palette.line),
              borderRadius: const BorderRadius.vertical(
                top: Radius.circular(4),
              ),
              boxShadow: [
                BoxShadow(
                  color: palette.foreground.withValues(alpha: 0.035),
                  blurRadius: 28,
                  offset: const Offset(0, 8),
                ),
              ],
            ),
            child: _preview ? _document() : _editor(compact: !_outlineVisible),
          ),
        ),
      ),
    );
  }

  InputDecoration _writingField(String label, {String? error}) =>
      InputDecoration(
        hintText: label,
        errorText: error,
        filled: false,
        border: InputBorder.none,
        enabledBorder: InputBorder.none,
        focusedBorder: InputBorder.none,
        contentPadding: const EdgeInsets.symmetric(vertical: 8),
        isDense: true,
      );

  Widget _editor({bool compact = false}) => ListView(
    padding: EdgeInsets.all(MediaQuery.sizeOf(context).width < 600 ? 20 : 44),
    children: [
      Semantics(
        label: _t('标题', 'Title', '제목'),
        child: TextField(
          key: const Key('manuscript-title'),
          controller: _title,
          readOnly: _busy,
          maxLines: null,
          decoration: _writingField(
            _t('标题', 'Title', '제목'),
            error: _title.text.trim().runes.length > 300
                ? _t(
                    '标题最多 300 字符；内容未截断。',
                    'Title limit is 300 characters; nothing was truncated.',
                    '제목은 300자까지입니다. 입력 내용은 잘리지 않았습니다.',
                  )
                : null,
          ),
          style: Theme.of(context).textTheme.titleLarge?.copyWith(
            fontSize: 30,
            fontWeight: FontWeight.w600,
            height: 1.45,
          ),
        ),
      ),
      const SizedBox(height: 16),
      Semantics(
        label: _t('概要', 'Summary', '개요'),
        child: TextField(
          key: const Key('manuscript-summary'),
          controller: _summary,
          readOnly: _busy,
          minLines: 2,
          maxLines: 5,
          decoration: _writingField(_t('概要', 'Summary', '개요')),
          style: Theme.of(context).textTheme.bodyLarge?.copyWith(
            color: LumenisTheme.of(context).muted,
            height: 1.8,
          ),
        ),
      ),
      const SizedBox(height: 16),
      if (compact)
        DropdownButtonFormField<int>(
          key: ValueKey('manuscript-section-$_selected-${_sections.length}'),
          initialValue: _selected,
          isExpanded: true,
          decoration: InputDecoration(
            labelText: _t('当前段落', 'Current section', '현재 문단'),
          ),
          items: [
            for (var i = 0; i < _sections.length; i++)
              DropdownMenuItem(
                value: i,
                child: Text(
                  '${i + 1}. ${_sections[i].heading.text.isEmpty ? _t('未命名段落', 'Untitled section', '제목 없는 문단') : _sections[i].heading.text}',
                  overflow: TextOverflow.ellipsis,
                ),
              ),
          ],
          onChanged: (value) {
            if (value != null) setState(() => _selected = value);
          },
        ),
      const SizedBox(height: 12),
      Wrap(
        crossAxisAlignment: WrapCrossAlignment.center,
        spacing: 4,
        children: [
          Text(
            _t(
              '第 ${_selected + 1} 段',
              'Section ${_selected + 1}',
              '${_selected + 1}번째 문단',
            ),
          ),
          IconButton(
            tooltip: _t('向前移动', 'Move up', '위로 이동'),
            onPressed: _busy || _selected == 0 ? null : () => _move(-1),
            icon: const LumenisIcon(Icons.arrow_upward, size: 18),
          ),
          IconButton(
            tooltip: _t('向后移动', 'Move down', '아래로 이동'),
            onPressed: _busy || _selected == _sections.length - 1
                ? null
                : () => _move(1),
            icon: const LumenisIcon(Icons.arrow_downward, size: 18),
          ),
          IconButton(
            tooltip: _t('移除段落', 'Remove section', '문단 삭제'),
            onPressed: _busy || _sections.length == 1 ? null : _remove,
            icon: const LumenisIcon(Icons.delete_outline, size: 18),
          ),
          if (compact)
            IconButton(
              tooltip: _t('添加段落', 'Add section', '문단 추가'),
              onPressed: _busy || _sectionLimitReached ? null : _addSection,
              icon: const LumenisIcon(Icons.add, size: 18),
            ),
          if (_removed != null)
            TextButton(
              onPressed: _busy ? null : _undoRemove,
              child: Text(_t('撤销移除', 'Undo removal', '삭제 취소')),
            ),
        ],
      ),
      Semantics(
        label: _t('段落标题', 'Section heading', '문단 제목'),
        child: TextField(
          key: ValueKey('manuscript-heading-$_selected'),
          controller: _sections[_selected].heading,
          readOnly: _busy,
          decoration: _writingField(_t('段落标题', 'Section heading', '문단 제목')),
          style: Theme.of(context).textTheme.titleLarge?.copyWith(
            fontSize: 21,
            fontWeight: FontWeight.w500,
            height: 1.6,
          ),
        ),
      ),
      const SizedBox(height: 12),
      Semantics(
        label: _t('正文', 'Body', '본문'),
        child: TextField(
          key: ValueKey('manuscript-body-$_selected'),
          controller: _sections[_selected].body,
          readOnly: _busy,
          textAlignVertical: TextAlignVertical.top,
          minLines: 10,
          maxLines: null,
          decoration: _writingField(_t('正文', 'Body', '본문')),
          style: Theme.of(context).textTheme.bodyLarge?.copyWith(height: 1.9),
        ),
      ),
      const SizedBox(height: 20),
      DropdownButtonFormField<String>(
        initialValue: _language,
        key: ValueKey('manuscript-language-$_language'),
        decoration: InputDecoration(
          labelText: _t('文稿语言', 'Writing language', '문서 언어'),
        ),
        items: const [
          DropdownMenuItem(value: 'zh', child: Text('中文')),
          DropdownMenuItem(value: 'en', child: Text('English')),
          DropdownMenuItem(value: 'ko', child: Text('한국어')),
        ],
        onChanged: _busy
            ? null
            : (value) {
                if (value != null) {
                  _language = value;
                  _edit();
                }
              },
      ),
    ],
  );

  Widget _document() {
    final colors = LumenisTheme.of(context);
    final text = [
      _title.text,
      _summary.text,
      for (final s in _sections) '${s.heading.text}\n${s.body.text}',
    ].join('\n\n');
    return ColoredBox(
      color: colors.surface,
      child: ListView(
        padding: const EdgeInsets.all(28),
        children: [
          Wrap(
            crossAxisAlignment: WrapCrossAlignment.center,
            spacing: 8,
            children: [
              Text(
                _t('阅读预览', 'Reading preview', '읽기 미리보기'),
                style: Theme.of(
                  context,
                ).textTheme.labelMedium?.copyWith(color: colors.muted),
              ),
              ReadAloudAction(
                sessionId: 'shared-manuscript',
                scopeVersion: '$_revision-${_controller.scope?.toJson()}',
                text: text,
                purpose: ReadAloudPurpose.savedPreview,
              ),
            ],
          ),
          const SizedBox(height: 24),
          SelectableText(
            _title.text.isEmpty
                ? _t('未命名文稿', 'Untitled writing', '제목 없는 문서')
                : _title.text,
            style: Theme.of(
              context,
            ).textTheme.headlineSmall?.copyWith(fontSize: 26, height: 1.4),
          ),
          const SizedBox(height: 20),
          SelectableText(
            _summary.text,
            style: Theme.of(
              context,
            ).textTheme.bodyLarge?.copyWith(color: colors.muted, height: 1.8),
          ),
          for (final section in _sections) ...[
            const SizedBox(height: 28),
            SelectableText(
              section.heading.text,
              style: Theme.of(
                context,
              ).textTheme.titleMedium?.copyWith(height: 1.5),
            ),
            const SizedBox(height: 12),
            SelectableText(
              section.body.text,
              style: Theme.of(
                context,
              ).textTheme.bodyLarge?.copyWith(height: 1.9),
            ),
          ],
        ],
      ),
    );
  }
}
