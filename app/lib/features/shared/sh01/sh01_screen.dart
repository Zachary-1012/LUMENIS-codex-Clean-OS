import 'dart:async';

import 'package:flutter/material.dart';

import '../../../core/lumenis_icon.dart';

import '../../../core/lumenis_core_client.dart';
import '../../../core/lumenis_theme.dart';
import '../../../core/lumenis_work_object.dart';
import '../../../l10n/lumenis_localizations.dart';
import 'sh01_repository.dart';
import 'sh01_snapshot.dart';
import 'sh01_view_model.dart';
import 'media_project_workbench.dart';
import 'manuscript_editor.dart';
import 'manuscript_controller.dart';
import 'saved_media_projects_controller.dart';

String _catalogFailureCopy(String? error) => switch (error) {
  '登录已失效，请重新登录后读取。' => 'sh01.failure.auth',
  '当前账号无权读取共享能力目录。' => 'sh01.failure.permission',
  'Product Core 暂时不可用。' => 'sh01.failure.offline',
  _ => 'sh01.failure.other',
};

String _consumerLabel(BuildContext context, String consumer) =>
    switch (consumer.trim().toUpperCase()) {
      'CTH' ||
      'COMMERCE' ||
      'COMMERCE OPERATIONS' => context.lumenisL10n.text('navgroup.cth'),
      'BMP' ||
      'ZBMP' ||
      'BRAND' ||
      'BRAND MARKET' => context.lumenisL10n.text('navgroup.bmp'),
      _ => context.lumenisL10n.text('navgroup.shared'),
    };

String _categoryLabel(BuildContext context, String category) =>
    switch (category.trim().toUpperCase()) {
      'RESEARCH' ||
      '研究与证据' ||
      '研究资料' => context.lumenisL10n.text('sh01.category.research'),
      'CONTENT' ||
      '内容制作' ||
      '内容创作' => context.lumenisL10n.text('sh01.category.content'),
      '' => context.lumenisL10n.text('sh01.category.other'),
      _ => context.lumenisL10n.text('sh01.category.other'),
    };

String _permissionLabel(BuildContext context, String permission) {
  final labels = {
    'READ': context.lumenisL10n.text('sh01.permission.read'),
    'RESEARCH': context.lumenisL10n.text('sh01.permission.research'),
    'ANALYZE': context.lumenisL10n.text('sh01.permission.analyze'),
    'SUGGEST': context.lumenisL10n.text('sh01.permission.suggest'),
    'AUDIT': context.lumenisL10n.text('sh01.permission.audit'),
    'WRITE': context.lumenisL10n.text('sh01.permission.write'),
    'EXPORT': context.lumenisL10n.text('sh01.permission.export'),
    'PUBLISH': context.lumenisL10n.text('sh01.permission.publish'),
  };
  final parts = permission
      .split(RegExp(r'\s*/\s*'))
      .map((part) => part.trim().toUpperCase())
      .toList(growable: false);
  if (parts.isEmpty || parts.any((part) => !labels.containsKey(part))) {
    return context.lumenisL10n.text('sh01.permission.other');
  }
  return parts.map((part) => labels[part]!).join('、');
}

String _riskLabel(BuildContext context, String risk) =>
    switch (risk.trim().toUpperCase()) {
      'LOW' => context.lumenisL10n.text('sh01.risk.low'),
      'MEDIUM' => context.lumenisL10n.text('sh01.risk.medium'),
      'HIGH' => context.lumenisL10n.text('sh01.risk.high'),
      _ => context.lumenisL10n.text('sh01.risk.unknown'),
    };

String _useLimitLabel(BuildContext context, String policy) =>
    switch (policy.trim().toUpperCase()) {
      'READ_ONLY' => context.lumenisL10n.text('sh01.limit.read_only'),
      'NO_EXTERNAL_WRITE' => context.lumenisL10n.text(
        'sh01.limit.no_external_write',
      ),
      'APPROVAL_REQUIRED' => context.lumenisL10n.text('sh01.limit.approval'),
      'AUDIT_ONLY' => context.lumenisL10n.text('sh01.limit.audit'),
      _ => context.lumenisL10n.text('sh01.limit.unknown'),
    };

String? _safeBusinessCopy(String value) {
  final normalized = value.trim();
  if (normalized.isEmpty || normalized.length > 280) return null;
  if (RegExp(
    r'(api|database|sqlite|\bdb\b|provider|model|permission|evidence|owner|runtime|contract|canonical|viewmodel|subject|brandfocus|cth|bmp|zbmp|token|cookie|secret|internal|private|path|https?)',
    caseSensitive: false,
  ).hasMatch(normalized)) {
    return null;
  }
  if (normalized.runes.any((rune) => !_isAllowedBusinessRune(rune))) {
    return null;
  }
  return normalized;
}

bool _isAllowedBusinessRune(int rune) {
  final asciiLetterOrDigit =
      rune >= 0x30 && rune <= 0x39 ||
      rune >= 0x41 && rune <= 0x5a ||
      rune >= 0x61 && rune <= 0x7a;
  final naturalLanguageRange =
      rune >= 0x3400 && rune <= 0x9fff ||
      rune >= 0xac00 && rune <= 0xd7af ||
      rune >= 0x00c0 && rune <= 0x024f;
  const punctuation = ' \t\n\r&·、，。！？：；（）()“”‘’+-—–';
  return asciiLetterOrDigit ||
      naturalLanguageRange ||
      punctuation.runes.contains(rune);
}

String _businessDescription(String description) {
  final normalized = description
      .replaceAll('已入库 Evidence', '已入库资料')
      .replaceAll(RegExp('Evidence', caseSensitive: false), '资料依据')
      .replaceAll(RegExp(r'\bBrief\b', caseSensitive: false), '需求说明')
      .replaceAll(RegExp(r'Canonical Data', caseSensitive: false), '正式业务数据')
      .replaceAll(RegExp(r'\bCanonical\b', caseSensitive: false), '正式记录')
      .replaceAll(RegExp(r'\bSVG\b', caseSensitive: false), '矢量图')
      .replaceAll(RegExp(r'\bArtifact\b', caseSensitive: false), '成果')
      .replaceAll(RegExp(r'(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])'), '');
  return _safeBusinessCopy(normalized) ?? '';
}

String _capabilityName(BuildContext context, String name) =>
    _safeBusinessCopy(name) ?? context.lumenisL10n.text('sh01.detail.empty');

String _catalogTitle(BuildContext context, String _) =>
    context.lumenisL10n.text('sh01.charter.title');

class Sh01Screen extends StatefulWidget {
  const Sh01Screen({
    required this.client,
    this.repository,
    this.invokingDomain,
    this.contextAvailable = true,
    this.initialWorkspaceEntry,
    this.returnScreenId,
    this.initialArtifactId,
    this.onSavedManuscript,
    this.onNavigate,
    super.key,
  });

  final LumenisCoreClient client;
  final Sh01Repository? repository;
  final String? invokingDomain;
  final bool contextAvailable;
  final String? initialWorkspaceEntry;
  final String? returnScreenId;
  final String? initialArtifactId;
  final ValueChanged<String>? onSavedManuscript;
  final ValueChanged<String>? onNavigate;

  @override
  State<Sh01Screen> createState() => _Sh01ScreenState();
}

class _Sh01ScreenState extends State<Sh01Screen> {
  bool _editing = false;
  bool _writing = false;
  bool _catalog = false;
  bool _independent = true;
  String _mediaOutputKind = 'video';
  String _libraryKind = 'document';
  String? _initialArtifact;
  late final Sh01ViewModel _viewModel = Sh01ViewModel(
    repository: widget.repository ?? CoreSh01Repository(client: widget.client),
  );
  late final ManuscriptController _manuscripts = ManuscriptController(
    client: widget.client,
    scope: const SharedWorkspaceScope(),
    draft: InternalPitchManuscript(
      title: '',
      summary: '',
      sections: [],
      language: 'zh',
      authorship: 'user_supplied',
    ),
  );
  late final SavedMediaProjectsController _mediaLibrary =
      SavedMediaProjectsController(
        loadPage: (cursor) =>
            widget.client.listContentProjects(domainId: null, cursor: cursor),
        contextKey: () => 'shared_workspace:${widget.contextAvailable}',
      );

  @override
  void initState() {
    super.initState();
    if (widget.initialArtifactId != null) {
      _initialArtifact = widget.initialArtifactId;
      _writing = widget.initialWorkspaceEntry == 'manuscript';
      _editing = const {
        'audio',
        'video',
      }.contains(widget.initialWorkspaceEntry);
      _mediaOutputKind = widget.initialWorkspaceEntry == 'audio'
          ? 'audio'
          : 'video';
      return;
    }
    if (const {
      'manuscript',
      'video',
      'audio',
    }.contains(widget.initialWorkspaceEntry)) {
      _writing = widget.initialWorkspaceEntry == 'manuscript';
      _editing = !_writing;
      _mediaOutputKind = widget.initialWorkspaceEntry == 'audio'
          ? 'audio'
          : 'video';
      return;
    }
    _editing =
        widget.initialWorkspaceEntry == 'media' &&
        widget.returnScreenId == 'BMP-08';
    if (_editing) {
      _mediaOutputKind = 'audio';
      _independent = widget.invokingDomain == null;
    } else {
      unawaited(_manuscripts.list());
    }
  }

  @override
  void didUpdateWidget(covariant Sh01Screen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.contextAvailable != widget.contextAvailable) {
      _mediaLibrary.invalidate();
      if (_libraryKind != 'document' && widget.contextAvailable) {
        unawaited(_mediaLibrary.refresh());
      }
    }
  }

  void _leaveWorkspace() {
    final returnTo = widget.returnScreenId;
    if (widget.initialArtifactId != null &&
        returnTo != null &&
        widget.onNavigate != null) {
      widget.onNavigate!(returnTo);
      return;
    }
    final shouldReturnToPodcast =
        _editing &&
        widget.initialWorkspaceEntry == 'media' &&
        returnTo == 'BMP-08' &&
        widget.onNavigate != null;
    setState(() {
      _editing = false;
      _writing = false;
      _initialArtifact = null;
    });
    if (shouldReturnToPodcast && returnTo != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) widget.onNavigate!(returnTo);
      });
    } else {
      _refreshLibrary();
    }
  }

  void _openMedia(String kind, {bool independent = true, String? artifact}) {
    setState(() {
      _independent = independent;
      _mediaOutputKind = kind;
      _initialArtifact = artifact;
      _editing = true;
    });
  }

  void _openManuscript([String? artifact]) => setState(() {
    _initialArtifact = artifact;
    _writing = true;
  });

  void _refreshLibrary() {
    if (_libraryKind == 'document') {
      unawaited(_manuscripts.list());
    } else {
      unawaited(_mediaLibrary.refresh());
    }
  }

  void _selectLibrary(String kind) {
    setState(() => _libraryKind = kind);
    if (kind != 'document' && !_mediaLibrary.loaded && !_mediaLibrary.busy) {
      unawaited(_mediaLibrary.refresh());
    }
  }

  @override
  void dispose() {
    _viewModel.dispose();
    _manuscripts.dispose();
    _mediaLibrary.dispose();
    super.dispose();
  }

  String _copy(String zh, String en, String ko) =>
      switch (Localizations.localeOf(context).languageCode) {
        'zh' => zh,
        'ko' => ko,
        _ => en,
      };

  @override
  Widget build(BuildContext context) {
    if (_writing) {
      return ManuscriptEditor(
        client: widget.client,
        initialArtifactId: _initialArtifact,
        onSaved: widget.onSavedManuscript,
        contextAvailable: widget.contextAvailable,
        onBack: _leaveWorkspace,
      );
    }
    if (_editing) {
      return MediaProjectWorkbench(
        client: widget.client,
        invokingDomain: _independent ? null : widget.invokingDomain,
        sharedWorkspace: _independent,
        contextAvailable: widget.contextAvailable,
        initialOutputKind: _mediaOutputKind,
        initialArtifactId: _initialArtifact,
        onBack: _leaveWorkspace,
      );
    }
    final palette = LumenisTheme.of(context);
    return DecoratedBox(
      decoration: BoxDecoration(color: palette.canvas),
      child: SafeArea(
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(24, 12, 16, 12),
              child: Row(
                children: [
                  if (_catalog)
                    IconButton(
                      key: const Key('sh01-close-catalog'),
                      tooltip: _copy('返回创作', 'Back to creation', '창작으로 돌아가기'),
                      onPressed: () => setState(() => _catalog = false),
                      icon: const LumenisIcon(Icons.arrow_back),
                    ),
                  Expanded(
                    child: Text(
                      _catalog
                          ? _copy('工具', 'Tools', '도구')
                          : _copy('创作', 'Create', '창작'),
                      style: Theme.of(context).textTheme.headlineMedium
                          ?.copyWith(fontWeight: FontWeight.w600),
                    ),
                  ),
                  if (!_catalog)
                    TextButton.icon(
                      key: const Key('sh01-open-catalog'),
                      onPressed: () {
                        setState(() => _catalog = true);
                        if (_viewModel.catalog == null) _viewModel.refresh();
                      },
                      icon: const LumenisIcon(Icons.widgets_outlined, size: 18),
                      label: Text(_copy('工具', 'Tools', '도구')),
                    ),
                ],
              ),
            ),
            Expanded(
              child: _catalog
                  ? AnimatedBuilder(
                      animation: _viewModel,
                      builder: (context, _) => switch (_viewModel.phase) {
                        Sh01LoadPhase.loading => const _LoadingState(),
                        Sh01LoadPhase.failed => _FailureState(
                          messageKey: _catalogFailureCopy(_viewModel.error),
                          onRetry: _viewModel.refresh,
                        ),
                        Sh01LoadPhase.ready => _Workspace(
                          viewModel: _viewModel,
                          catalog: _viewModel.catalog!,
                        ),
                      },
                    )
                  : LayoutBuilder(
                      builder: (context, constraints) {
                        final inset = constraints.maxWidth >= 1000
                            ? 48.0
                            : 20.0;
                        final library = AnimatedBuilder(
                          animation: Listenable.merge([
                            _manuscripts,
                            _mediaLibrary,
                          ]),
                          builder: (context, _) => _library(),
                        );
                        return CustomScrollView(
                          key: const PageStorageKey('sh01-creation-scroll'),
                          slivers: [
                            SliverPadding(
                              padding: EdgeInsets.fromLTRB(inset, 8, inset, 0),
                              sliver: SliverToBoxAdapter(child: _launchPanel()),
                            ),
                            SliverPadding(
                              padding: EdgeInsets.fromLTRB(
                                inset,
                                24,
                                inset,
                                28,
                              ),
                              sliver: SliverToBoxAdapter(child: library),
                            ),
                          ],
                        );
                      },
                    ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _launchPanel() => LayoutBuilder(
    builder: (context, constraints) {
      final wideText = MediaQuery.textScalerOf(context).scale(16) > 24;
      final columns = constraints.maxWidth >= 680 && !wideText ? 4 : 2;
      final actions = <(String, String, LumenisWorkObject, VoidCallback?)>[
        (
          'sh01-open-research',
          _copy('研究资料', 'Research', '자료 연구'),
          LumenisWorkObject.book,
          widget.onNavigate == null ? null : () => widget.onNavigate!('SH-02'),
        ),
        (
          'sh01-create-manuscript',
          _copy('提案 / 文稿', 'Proposal / document', '제안서 / 문서'),
          LumenisWorkObject.paper,
          () => _openManuscript(),
        ),
        (
          'sh01-open-video-editor',
          _copy('视频', 'Video', '영상'),
          LumenisWorkObject.film,
          () => _openMedia('video'),
        ),
        (
          'sh01-open-podcast-editor',
          _copy('播客', 'Podcast', '팟캐스트'),
          LumenisWorkObject.microphone,
          () => _openMedia('audio'),
        ),
      ];
      final palette = LumenisTheme.of(context);
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 8),
            child: Text(
              _copy('新建作品', 'New work', '새 작품'),
              style: TextStyle(fontSize: 14, color: palette.muted),
            ),
          ),
          DecoratedBox(
            decoration: BoxDecoration(
              border: Border(
                bottom: BorderSide(color: palette.foreground, width: 2),
              ),
            ),
            child: Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Wrap(
                spacing: 16,
                runSpacing: 8,
                children: [
                  for (final (id, label, object, open) in actions)
                    SizedBox(
                      width:
                          (constraints.maxWidth - (columns - 1) * 16) / columns,
                      child: LumenisWorkObjectAction(
                        key: Key(id),
                        object: object,
                        label: label,
                        onPressed: open,
                        large: true,
                      ),
                    ),
                ],
              ),
            ),
          ),
          Align(
            alignment: Alignment.centerRight,
            child: TextButton.icon(
              key: const Key('sh01-open-linked-media'),
              onPressed: () => _openMedia('video', independent: false),
              icon: const LumenisIcon(Icons.folder_open_outlined, size: 18),
              label: Text(
                context.lumenisL10n.text('sh01.media.linked_workspace'),
              ),
            ),
          ),
        ],
      );
    },
  );

  Widget _library() {
    final documents = _libraryKind == 'document';
    final busy = documents ? _manuscripts.busy : _mediaLibrary.busy;
    final error = documents ? _manuscripts.errorCode : _mediaLibrary.errorCode;
    final rows = documents
        ? _manuscripts.items
        : _mediaLibrary.projects
              .where((p) => p.outputKind == _libraryKind)
              .toList();
    final hasMore = documents
        ? _manuscripts.hasMore
        : _mediaLibrary.nextCursor != null;
    final incomplete =
        !documents &&
        (_mediaLibrary.status == SavedMediaProjectsStatus.scanIncomplete ||
            _mediaLibrary.status ==
                SavedMediaProjectsStatus.integrityIncomplete);
    final palette = LumenisTheme.of(context);
    final works = <String, List<InternalPitchSavedManuscript>>{};
    if (documents) {
      for (final item in _manuscripts.items) {
        works.putIfAbsent(item.workId, () => []).add(item);
      }
      for (final versions in works.values) {
        versions.sort((a, b) => b.version.compareTo(a.version));
      }
    }
    final contents = Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        Row(
          children: [
            Expanded(
              child: Text(
                _copy('继续工作', 'Continue working', '이어서 작업'),
                style: Theme.of(context).textTheme.titleLarge,
              ),
            ),
            IconButton(
              key: const Key('sh01-refresh-projects'),
              tooltip: _copy('刷新', 'Refresh', '새로 고침'),
              onPressed: busy ? null : _refreshLibrary,
              icon: const LumenisIcon(Icons.refresh_rounded),
            ),
          ],
        ),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            for (final (kind, label) in [
              ('document', _copy('文稿', 'Documents', '문서')),
              ('video', _copy('视频', 'Videos', '영상')),
              ('audio', _copy('播客', 'Podcasts', '팟캐스트')),
            ])
              TextButton(
                key: Key('sh01-library-$kind'),
                onPressed: () => _selectLibrary(kind),
                style: TextButton.styleFrom(
                  foregroundColor: _libraryKind == kind
                      ? palette.foreground
                      : palette.muted,
                  padding: const EdgeInsets.symmetric(
                    horizontal: 16,
                    vertical: 12,
                  ),
                  shape: const RoundedRectangleBorder(),
                ),
                child: Container(
                  padding: const EdgeInsets.only(bottom: 7),
                  decoration: BoxDecoration(
                    border: Border(
                      bottom: BorderSide(
                        color: _libraryKind == kind
                            ? palette.accentStrong
                            : Colors.transparent,
                        width: 3,
                      ),
                    ),
                  ),
                  child: Text(label),
                ),
              ),
          ],
        ),
        const SizedBox(height: 16),
        if (busy) const LinearProgressIndicator(minHeight: 2),
        if (error != null)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 24),
            child: Text(
              _copy(
                '作品暂时无法读取，请刷新重试。',
                'Your work could not be loaded. Please refresh to retry.',
                '작품을 불러올 수 없습니다. 새로 고침하여 다시 시도하세요.',
              ),
            ),
          )
        else if (!busy && rows.isEmpty)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 36),
            child: Text(
              hasMore
                  ? _copy(
                      '这一页没有此类作品，可继续查看。',
                      'No matching work on this page. More pages are available.',
                      '이 페이지에 해당 작품이 없습니다. 다음 페이지를 확인할 수 있습니다.',
                    )
                  : _copy(
                      '尚未读取到保存的作品。',
                      'No saved work was returned.',
                      '저장한 작품이 반환되지 않았습니다.',
                    ),
              style: TextStyle(color: palette.muted),
            ),
          ),
        if (error == null) ...[
          if (documents)
            LayoutBuilder(
              builder: (context, constraints) {
                final columns = constraints.maxWidth >= 680 ? 2 : 1;
                final width =
                    (constraints.maxWidth - (columns - 1) * 24) / columns;
                return Wrap(
                  spacing: 24,
                  runSpacing: 24,
                  children: [
                    for (final versions in works.values)
                      SizedBox(
                        width: width,
                        child: _ManuscriptFolio(
                          versions: versions,
                          onOpen: _openManuscript,
                          versionLabel: _copy('版本', 'Version', '버전'),
                        ),
                      ),
                  ],
                );
              },
            ),
          if (!documents)
            for (final item in _mediaLibrary.projects.where(
              (p) => p.outputKind == _libraryKind,
            ))
              _SavedCreationRow(
                key: Key('sh01-saved-${item.artifactId}'),
                title:
                    item.title ??
                    (item.outputKind == 'audio'
                        ? _copy('播客作品', 'Podcast', '팟캐스트')
                        : _copy('视频作品', 'Video', '영상')),
                detail:
                    '${_savedDate(item.createdAt)}${item.projectRevision == null ? '' : ' · v${item.projectRevision}'}'
                    '${item.renderState == 'not_rendered' ? ' · ${_copy('工程', 'Project', '프로젝트')}' : ''}',
                icon: item.outputKind == 'audio'
                    ? Icons.mic_none_rounded
                    : Icons.movie_outlined,
                onPressed: () =>
                    _openMedia(item.outputKind, artifact: item.artifactId),
              ),
        ],
        if (incomplete)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 12),
            child: Text(
              _copy(
                '仍有作品尚未完成读取。',
                'Some work has not been fully read.',
                '일부 작품을 아직 모두 읽지 못했습니다.',
              ),
            ),
          ),
        if (hasMore && error == null)
          TextButton(
            onPressed: busy
                ? null
                : () => documents
                      ? _manuscripts.loadMore()
                      : _mediaLibrary.loadMore(),
            child: Text(_copy('继续查看', 'Load more', '더 보기')),
          ),
      ],
    );
    return LayoutBuilder(
      builder: (context, constraints) {
        final padded = Padding(
          padding: const EdgeInsets.fromLTRB(0, 0, 0, 20),
          child: contents,
        );
        return constraints.hasBoundedHeight
            ? SingleChildScrollView(child: padded)
            : padded;
      },
    );
  }

  String _savedDate(String value) {
    final date = DateTime.tryParse(value)?.toLocal();
    if (date == null) {
      return _copy('保存时间未知', 'Save time unknown', '저장 시간 알 수 없음');
    }
    return '${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')} ${date.hour.toString().padLeft(2, '0')}:${date.minute.toString().padLeft(2, '0')}';
  }
}

class _ManuscriptFolio extends StatelessWidget {
  const _ManuscriptFolio({
    required this.versions,
    required this.onOpen,
    required this.versionLabel,
  });
  final List<InternalPitchSavedManuscript> versions;
  final ValueChanged<String> onOpen;
  final String versionLabel;
  @override
  Widget build(BuildContext context) {
    final palette = LumenisTheme.of(context);
    final item = versions.first;
    final body = item.manuscript.sections
        .map((section) => section.body)
        .join('\n');
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Stack(
          children: [
            if (versions.length > 1)
              Positioned.fill(
                top: 8,
                right: 0,
                left: 8,
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    color: palette.surfaceRaised,
                    border: Border.all(color: palette.line),
                    borderRadius: BorderRadius.circular(3),
                  ),
                ),
              ),
            Padding(
              padding: const EdgeInsets.only(right: 5, bottom: 5),
              child: DecoratedBox(
                decoration: BoxDecoration(
                  color: palette.surface,
                  border: Border.all(color: palette.line),
                  borderRadius: BorderRadius.circular(3),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: .13),
                      blurRadius: 10,
                      offset: const Offset(0, 5),
                    ),
                  ],
                ),
                child: Material(
                  color: Colors.transparent,
                  child: InkWell(
                    key: Key('sh01-saved-${item.artifactId}'),
                    onTap: () => onOpen(item.artifactId),
                    child: Padding(
                      padding: const EdgeInsets.all(24),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            item.manuscript.title,
                            maxLines: 3,
                            overflow: TextOverflow.ellipsis,
                            style: Theme.of(context).textTheme.titleLarge
                                ?.copyWith(fontWeight: FontWeight.w600),
                          ),
                          const SizedBox(height: 16),
                          Text(
                            item.manuscript.summary,
                            maxLines: 3,
                            overflow: TextOverflow.ellipsis,
                            style: Theme.of(context).textTheme.bodyMedium
                                ?.copyWith(color: palette.muted, height: 1.65),
                          ),
                          const Divider(height: 32),
                          Text(
                            body,
                            maxLines: 4,
                            overflow: TextOverflow.ellipsis,
                            style: Theme.of(
                              context,
                            ).textTheme.bodySmall?.copyWith(height: 1.9),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
        Row(
          children: [
            Expanded(
              child: Text(
                '$versionLabel ${item.version}',
                style: Theme.of(
                  context,
                ).textTheme.bodySmall?.copyWith(color: palette.muted),
              ),
            ),
            PopupMenuButton<String>(
              tooltip: versionLabel,
              onSelected: onOpen,
              itemBuilder: (_) => [
                for (final version in versions)
                  PopupMenuItem(
                    value: version.artifactId,
                    child: Text('$versionLabel ${version.version}'),
                  ),
              ],
              icon: const LumenisIcon(Icons.history_rounded, size: 20),
            ),
          ],
        ),
      ],
    );
  }
}

class _SavedCreationRow extends StatelessWidget {
  const _SavedCreationRow({
    required this.title,
    required this.detail,
    required this.icon,
    required this.onPressed,
    super.key,
  });
  final String title;
  final String detail;
  final IconData icon;
  final VoidCallback onPressed;
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 8),
    child: ListTile(
      contentPadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 12),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(10),
        side: BorderSide(color: LumenisTheme.of(context).line),
      ),
      leading: LumenisIcon(icon, size: 24),
      title: Text(title),
      subtitle: Padding(
        padding: const EdgeInsets.only(top: 6),
        child: Text(detail, maxLines: 2, overflow: TextOverflow.ellipsis),
      ),
      trailing: const LumenisIcon(Icons.arrow_outward, size: 18),
      onTap: onPressed,
    ),
  );
}

class _Workspace extends StatelessWidget {
  const _Workspace({required this.viewModel, required this.catalog});

  final Sh01ViewModel viewModel;
  final Sh01Catalog catalog;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, constraints) {
      final wide = constraints.maxWidth >= 1120;
      final medium = constraints.maxWidth >= 760;
      final inset = wide ? 30.0 : 18.0;
      final index = _CapabilityIndex(
        catalog: catalog,
        selected: viewModel.selected,
        onSelect: viewModel.select,
      );
      final detail = _CapabilityDetail(
        capability: viewModel.selected,
        hasTools: catalog.skills.isNotEmpty,
      );
      return Align(
        alignment: Alignment.topCenter,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1480),
          child: SingleChildScrollView(
            padding: EdgeInsets.fromLTRB(inset, 24, inset, 36),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const _Heading(),
                const SizedBox(height: 22),
                if (wide)
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      SizedBox(
                        width: 270,
                        child: _SharedCharter(catalog: catalog),
                      ),
                      const SizedBox(width: 16),
                      SizedBox(width: 365, child: index),
                      const SizedBox(width: 16),
                      Expanded(child: detail),
                    ],
                  )
                else if (medium)
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      SizedBox(
                        width: 260,
                        child: _SharedCharter(catalog: catalog),
                      ),
                      const SizedBox(width: 14),
                      Expanded(child: index),
                    ],
                  )
                else ...[
                  _SharedCharter(catalog: catalog),
                  const SizedBox(height: 14),
                  index,
                ],
                if (!wide && viewModel.selected != null) ...[
                  const SizedBox(height: 14),
                  detail,
                ],
                const SizedBox(height: 14),
                const _EvidenceBoundary(),
                const SizedBox(height: 14),
                Align(
                  alignment: Alignment.centerLeft,
                  child: OutlinedButton.icon(
                    onPressed: viewModel.refresh,
                    icon: const Icon(Icons.refresh_rounded),
                    label: Text(context.lumenisL10n.text('sh01.refresh')),
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

class _Heading extends StatelessWidget {
  const _Heading();

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Row(
        children: [
          Container(
            width: 8,
            height: 28,
            decoration: BoxDecoration(
              color: LumenisTheme.of(context).shared,
              borderRadius: BorderRadius.circular(8),
            ),
          ),
          const SizedBox(width: 11),
          Text(
            context.lumenisL10n.text('sh01.eyebrow'),
            style: Theme.of(context).textTheme.labelSmall?.copyWith(
              color: LumenisTheme.of(context).shared,
              letterSpacing: 1,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
      const SizedBox(height: 13),
      Text(
        context.lumenisL10n.text('sh01.title'),
        style: Theme.of(context).textTheme.headlineMedium?.copyWith(
          color: LumenisTheme.of(context).foreground,
          fontWeight: FontWeight.w600,
          letterSpacing: -0.5,
        ),
      ),
      const SizedBox(height: 7),
      Text(
        context.lumenisL10n.text('sh01.subtitle'),
        style: Theme.of(
          context,
        ).textTheme.bodyMedium?.copyWith(color: LumenisTheme.of(context).muted),
      ),
    ],
  );
}

class _SharedCharter extends StatelessWidget {
  const _SharedCharter({required this.catalog});

  final Sh01Catalog catalog;

  @override
  Widget build(BuildContext context) => _Panel(
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _Eyebrow(context.lumenisL10n.text('sh01.charter.eyebrow')),
        const SizedBox(height: 16),
        Container(
          width: 52,
          height: 52,
          decoration: BoxDecoration(
            color: LumenisTheme.of(context).shared.withValues(alpha: 0.1),
            border: Border.all(
              color: LumenisTheme.of(context).shared.withValues(alpha: 0.35),
            ),
            borderRadius: BorderRadius.circular(15),
          ),
          child: Icon(
            Icons.hub_outlined,
            color: LumenisTheme.of(context).shared,
            size: 25,
          ),
        ),
        const SizedBox(height: 14),
        Text(
          _catalogTitle(context, catalog.capability),
          style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: 8),
        Text(
          context.lumenisL10n.text('sh01.charter.detail'),
          style: TextStyle(color: LumenisTheme.of(context).muted, height: 1.5),
        ),
        const SizedBox(height: 17),
        const Divider(height: 1),
        const SizedBox(height: 14),
        _Eyebrow(context.lumenisL10n.text('sh01.charter.products')),
        const SizedBox(height: 9),
        Wrap(
          spacing: 7,
          runSpacing: 7,
          children: [
            for (final consumer in catalog.consumers)
              _MetaChip(_consumerLabel(context, consumer)),
          ],
        ),
        const SizedBox(height: 16),
        Text(
          context.lumenisL10n.text('sh01.charter.note'),
          style: TextStyle(
            color: LumenisTheme.of(context).quiet,
            fontSize: 12,
            height: 1.5,
          ),
        ),
      ],
    ),
  );
}

class _CapabilityIndex extends StatelessWidget {
  const _CapabilityIndex({
    required this.catalog,
    required this.selected,
    required this.onSelect,
  });

  final Sh01Catalog catalog;
  final Sh01Capability? selected;
  final ValueChanged<Sh01Capability> onSelect;

  @override
  Widget build(BuildContext context) => _Panel(
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(
              child: _Eyebrow(context.lumenisL10n.text('sh01.index.title')),
            ),
            Text(
              catalog.skills.length.toString(),
              style: TextStyle(
                color: LumenisTheme.of(context).shared,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        if (catalog.skills.isEmpty)
          _InfoMessage(context.lumenisL10n.text('sh01.index.empty'))
        else
          for (final item in catalog.skills)
            _CapabilityRow(
              item: item,
              selected: selected?.id == item.id,
              onTap: () => onSelect(item),
            ),
      ],
    ),
  );
}

class _CapabilityRow extends StatelessWidget {
  const _CapabilityRow({
    required this.item,
    required this.selected,
    required this.onTap,
  });

  final Sh01Capability item;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 7),
    child: Material(
      color: selected
          ? LumenisTheme.of(context).shared.withValues(alpha: 0.09)
          : LumenisTheme.of(context).surfaceRaised,
      borderRadius: BorderRadius.circular(11),
      child: InkWell(
        key: Key('sh01-capability-${item.id}'),
        onTap: onTap,
        borderRadius: BorderRadius.circular(11),
        child: Container(
          constraints: const BoxConstraints(minHeight: 62),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          decoration: BoxDecoration(
            border: Border.all(
              color: selected
                  ? LumenisTheme.of(context).shared.withValues(alpha: 0.55)
                  : LumenisTheme.of(context).line,
            ),
            borderRadius: BorderRadius.circular(11),
          ),
          child: Row(
            children: [
              Container(
                width: 30,
                height: 30,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: LumenisTheme.of(context).canvas,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Icon(
                  Icons.extension_outlined,
                  size: 17,
                  color: selected
                      ? LumenisTheme.of(context).shared
                      : LumenisTheme.of(context).quiet,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      _capabilityName(context, item.name),
                      style: const TextStyle(fontWeight: FontWeight.w600),
                    ),
                    if (item.category.isNotEmpty) ...[
                      const SizedBox(height: 3),
                      Text(
                        _categoryLabel(context, item.category),
                        style: TextStyle(
                          color: LumenisTheme.of(context).muted,
                          fontSize: 11,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
              Icon(
                Icons.chevron_right_rounded,
                color: LumenisTheme.of(context).quiet,
              ),
            ],
          ),
        ),
      ),
    ),
  );
}

class _CapabilityDetail extends StatelessWidget {
  const _CapabilityDetail({required this.capability, required this.hasTools});

  final Sh01Capability? capability;
  final bool hasTools;

  @override
  Widget build(BuildContext context) => _Panel(
    child: capability == null
        ? _InfoMessage(
            context.lumenisL10n.text(
              hasTools ? 'sh01.detail.select' : 'sh01.detail.empty',
            ),
          )
        : _CapabilityFacts(capability: capability!),
  );
}

class _CapabilityFacts extends StatelessWidget {
  const _CapabilityFacts({required this.capability});

  final Sh01Capability capability;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Row(
        children: [
          Expanded(
            child: _Eyebrow(context.lumenisL10n.text('sh01.detail.title')),
          ),
        ],
      ),
      const SizedBox(height: 17),
      Text(
        _capabilityName(context, capability.name),
        style: Theme.of(context).textTheme.headlineSmall,
      ),
      if (_businessDescription(capability.description).isNotEmpty) ...[
        const SizedBox(height: 10),
        Text(
          _businessDescription(capability.description),
          style: TextStyle(color: LumenisTheme.of(context).muted, height: 1.6),
        ),
      ],
      const SizedBox(height: 22),
      _Eyebrow(context.lumenisL10n.text('sh01.detail.info')),
      const SizedBox(height: 11),
      _FactRow(
        context.lumenisL10n.text('sh01.detail.category'),
        _categoryLabel(context, capability.category),
      ),
      _FactRow(
        context.lumenisL10n.text('sh01.detail.products'),
        capability.consumers
            .map((consumer) => _consumerLabel(context, consumer))
            .join(' · '),
      ),
      _FactRow(
        context.lumenisL10n.text('sh01.detail.permission'),
        _permissionLabel(context, capability.permission),
      ),
      _FactRow(
        context.lumenisL10n.text('sh01.detail.risk'),
        _riskLabel(context, capability.risk),
      ),
      _FactRow(
        context.lumenisL10n.text('sh01.detail.limit'),
        _useLimitLabel(context, capability.executionPolicy),
      ),
      const SizedBox(height: 15),
      _InfoMessage(context.lumenisL10n.text('sh01.detail.note')),
    ],
  );
}

class _FactRow extends StatelessWidget {
  const _FactRow(this.label, this.value);

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    if (value.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 7),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 150,
            child: Text(
              label,
              style: TextStyle(color: LumenisTheme.of(context).quiet),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: SelectableText(
              value,
              style: TextStyle(color: LumenisTheme.of(context).foreground),
            ),
          ),
        ],
      ),
    );
  }
}

class _EvidenceBoundary extends StatelessWidget {
  const _EvidenceBoundary();

  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    padding: const EdgeInsets.all(16),
    decoration: BoxDecoration(
      color: LumenisTheme.of(context).caution.withValues(alpha: 0.07),
      border: Border.all(
        color: LumenisTheme.of(context).caution.withValues(alpha: 0.28),
      ),
      borderRadius: BorderRadius.circular(14),
    ),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(
          Icons.lock_outline_rounded,
          color: LumenisTheme.of(context).caution,
          size: 19,
        ),
        const SizedBox(width: 11),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                context.lumenisL10n.text('sh01.evidence.title'),
                style: TextStyle(fontWeight: FontWeight.w600),
              ),
              SizedBox(height: 5),
              Text(
                context.lumenisL10n.text('sh01.evidence.detail'),
                style: TextStyle(
                  color: LumenisTheme.of(context).muted,
                  height: 1.5,
                ),
              ),
            ],
          ),
        ),
      ],
    ),
  );
}

class _InfoMessage extends StatelessWidget {
  const _InfoMessage(this.message);

  final String message;

  @override
  Widget build(BuildContext context) => Text(
    message,
    style: TextStyle(color: LumenisTheme.of(context).muted, height: 1.5),
  );
}

class _MetaChip extends StatelessWidget {
  const _MetaChip(this.label);

  final String label;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 6),
    decoration: BoxDecoration(
      color: LumenisTheme.of(context).canvas,
      border: Border.all(color: LumenisTheme.of(context).line),
      borderRadius: BorderRadius.circular(20),
    ),
    child: Text(
      label,
      style: TextStyle(color: LumenisTheme.of(context).muted, fontSize: 11),
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
      color: LumenisTheme.of(context).quiet,
      fontSize: 10,
      letterSpacing: 0.9,
      fontWeight: FontWeight.w700,
    ),
  );
}

class _Panel extends StatelessWidget {
  const _Panel({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    padding: const EdgeInsets.all(18),
    decoration: BoxDecoration(
      color: LumenisTheme.of(context).surface,
      borderRadius: BorderRadius.circular(16),
      border: Border.all(color: LumenisTheme.of(context).line),
    ),
    child: child,
  );
}

class _LoadingState extends StatelessWidget {
  const _LoadingState();

  @override
  Widget build(BuildContext context) => Center(
    child: Semantics(
      liveRegion: true,
      label: context.lumenisL10n.text('sh01.loading'),
      child: CircularProgressIndicator(color: LumenisTheme.of(context).shared),
    ),
  );
}

class _FailureState extends StatelessWidget {
  const _FailureState({required this.messageKey, required this.onRetry});

  final String messageKey;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => Center(
    child: Padding(
      padding: const EdgeInsets.all(24),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 520),
        child: _Panel(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                context.lumenisL10n.text('sh01.failure.title'),
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 8),
              Text(
                context.lumenisL10n.text(messageKey),
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              const SizedBox(height: 16),
              OutlinedButton.icon(
                onPressed: onRetry,
                icon: const Icon(Icons.refresh_rounded),
                label: Text(context.lumenisL10n.text('sh01.failure.retry')),
                style: OutlinedButton.styleFrom(
                  minimumSize: const Size(48, 48),
                ),
              ),
            ],
          ),
        ),
      ),
    ),
  );
}
