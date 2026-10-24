import 'dart:async';

import 'package:flutter/material.dart';

import '../../../core/lumenis_icon.dart';

import '../../../core/lumenis_core_client.dart';
import '../../../core/lumenis_theme.dart';
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
    return ColoredBox(
      color: palette.canvas,
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
                        final wide =
                            constraints.maxWidth >= 900 &&
                            MediaQuery.textScalerOf(context).scale(16) <= 24;
                        final launch = _launchPanel();
                        final library = AnimatedBuilder(
                          animation: Listenable.merge([
                            _manuscripts,
                            _mediaLibrary,
                          ]),
                          builder: (context, _) => _library(),
                        );
                        if (wide) {
                          return Padding(
                            padding: const EdgeInsets.fromLTRB(24, 8, 24, 24),
                            child: Row(
                              crossAxisAlignment: CrossAxisAlignment.stretch,
                              children: [
                                SizedBox(
                                  width: 290,
                                  child: SingleChildScrollView(child: launch),
                                ),
                                const SizedBox(width: 28),
                                Expanded(child: library),
                              ],
                            ),
                          );
                        }
                        return SingleChildScrollView(
                          key: const PageStorageKey('sh01-creation-scroll'),
                          padding: const EdgeInsets.fromLTRB(18, 8, 18, 24),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              launch,
                              const SizedBox(height: 28),
                              library,
                            ],
                          ),
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
      final paired =
          constraints.maxWidth >= 320 &&
          MediaQuery.textScalerOf(context).scale(16) <= 24;
      final actions = <Widget>[
        _CreationAction(
          compact: paired,
          key: const Key('sh01-open-research'),
          title: _copy('研究资料', 'Research', '자료 연구'),
          object: _StudioObject.book,
          color: LumenisTheme.of(context).cth,
          onPressed: widget.onNavigate == null
              ? null
              : () => widget.onNavigate!('SH-02'),
        ),
        _CreationAction(
          compact: paired,
          key: const Key('sh01-create-manuscript'),
          title: _copy('提案 / 文稿', 'Proposal / document', '제안서 / 문서'),
          object: _StudioObject.paper,
          color: LumenisTheme.of(context).shared,
          onPressed: () => _openManuscript(),
        ),
        _CreationAction(
          compact: paired,
          key: const Key('sh01-open-video-editor'),
          title: _copy('视频', 'Video', '영상'),
          object: _StudioObject.film,
          color: LumenisTheme.of(context).bmp,
          onPressed: () => _openMedia('video'),
        ),
        _CreationAction(
          compact: paired,
          key: const Key('sh01-open-podcast-editor'),
          title: _copy('播客', 'Podcast', '팟캐스트'),
          object: _StudioObject.microphone,
          color: LumenisTheme.of(context).ai,
          onPressed: () => _openMedia('audio'),
        ),
      ];
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Padding(
            padding: const EdgeInsets.only(bottom: 14),
            child: Text(
              _copy('新建', 'Start new', '새로 만들기'),
              style: Theme.of(context).textTheme.titleSmall,
            ),
          ),
          if (paired)
            Wrap(
              spacing: 12,
              runSpacing: 4,
              children: [
                for (final action in actions)
                  SizedBox(
                    width: (constraints.maxWidth - 12) / 2,
                    child: action,
                  ),
              ],
            )
          else
            ...actions,
          const SizedBox(height: 10),
          TextButton.icon(
            key: const Key('sh01-open-linked-media'),
            onPressed: () => _openMedia('video', independent: false),
            icon: const LumenisIcon(Icons.folder_open_outlined, size: 18),
            label: Text(
              context.lumenisL10n.text('sh01.media.linked_workspace'),
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
              ChoiceChip(
                key: Key('sh01-library-$kind'),
                label: Text(label),
                selected: _libraryKind == kind,
                onSelected: (_) => _selectLibrary(kind),
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
          padding: const EdgeInsets.fromLTRB(8, 0, 8, 20),
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

enum _StudioObject { book, paper, film, microphone }

class _CreationAction extends StatefulWidget {
  const _CreationAction({
    required this.title,
    required this.object,
    this.compact = false,
    required this.color,
    required this.onPressed,
    super.key,
  });
  final String title;
  final _StudioObject object;
  final bool compact;
  final Color color;
  final VoidCallback? onPressed;
  @override
  State<_CreationAction> createState() => _CreationActionState();
}

class _CreationActionState extends State<_CreationAction> {
  bool _hover = false, _focus = false, _pressed = false;
  @override
  Widget build(BuildContext context) {
    final palette = LumenisTheme.of(context);
    final active = _hover || _focus;
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: AnimatedContainer(
        duration: MediaQuery.disableAnimationsOf(context)
            ? Duration.zero
            : const Duration(milliseconds: 90),
        transform: Matrix4.translationValues(
          0,
          _pressed ? 1 : (active ? -2 : 0),
          0,
        ),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(10),
          border: Border.all(
            color: _focus ? palette.accent : Colors.transparent,
          ),
          color: active
              ? palette.surface.withValues(alpha: .45)
              : Colors.transparent,
        ),
        child: Material(
          color: Colors.transparent,
          child: InkWell(
            onTap: widget.onPressed,
            onHover: (v) => setState(() => _hover = v),
            onFocusChange: (v) => setState(() => _focus = v),
            onHighlightChanged: (v) => setState(() => _pressed = v),
            borderRadius: BorderRadius.circular(10),
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 6),
              child: widget.compact
                  ? Column(
                      children: [
                        ExcludeSemantics(
                          child: CustomPaint(
                            size: const Size(92, 74),
                            painter: _StudioObjectPainter(
                              widget.object,
                              widget.color,
                              palette,
                            ),
                          ),
                        ),
                        const SizedBox(height: 6),
                        Text(
                          widget.title,
                          textAlign: TextAlign.center,
                          style: Theme.of(context).textTheme.titleMedium
                              ?.copyWith(fontWeight: FontWeight.w600),
                        ),
                      ],
                    )
                  : Row(
                      children: [
                        ExcludeSemantics(
                          child: CustomPaint(
                            size: const Size(106, 86),
                            painter: _StudioObjectPainter(
                              widget.object,
                              widget.color,
                              palette,
                            ),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Text(
                            widget.title,
                            style: Theme.of(context).textTheme.titleMedium
                                ?.copyWith(fontWeight: FontWeight.w600),
                          ),
                        ),
                        const SizedBox(width: 8),
                        LumenisIcon(Icons.add, size: 18, color: palette.muted),
                      ],
                    ),
            ),
          ),
        ),
      ),
    );
  }
}

class _StudioObjectPainter extends CustomPainter {
  const _StudioObjectPainter(this.object, this.accent, this.palette);
  final _StudioObject object;
  final Color accent;
  final LumenisPalette palette;
  @override
  void paint(Canvas canvas, Size size) {
    canvas.save();
    canvas.scale(size.width / 112, size.height / 92);
    final dark = palette.brightness == Brightness.dark;
    final paper = dark ? const Color(0xFFC4C6C2) : const Color(0xFFF7F6EF);
    final metal = const Color(0xFF424B50);
    final line = Paint()
      ..color = metal.withValues(alpha: .5)
      ..strokeWidth = 1;
    void face(Rect rect, Color color, {double radius = 4}) {
      final path = Path()
        ..addRRect(RRect.fromRectAndRadius(rect, Radius.circular(radius)));
      canvas.drawShadow(path, Colors.black.withValues(alpha: .35), 3, false);
      canvas.drawPath(
        path,
        Paint()
          ..shader = LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              Color.lerp(color, Colors.white, .25)!,
              color,
              Color.lerp(color, Colors.black, .15)!,
            ],
          ).createShader(rect),
      );
      canvas.drawPath(
        path,
        Paint()
          ..color = Colors.white.withValues(alpha: .35)
          ..style = PaintingStyle.stroke
          ..strokeWidth = .7,
      );
    }

    canvas.drawOval(
      const Rect.fromLTWH(17, 78, 78, 7),
      Paint()
        ..color = Colors.black.withValues(alpha: .12)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 4),
    );
    switch (object) {
      case _StudioObject.book:
        face(const Rect.fromLTWH(27, 14, 61, 64), accent);
        face(const Rect.fromLTWH(31, 17, 55, 56), paper, radius: 2);
        face(const Rect.fromLTWH(23, 10, 61, 60), accent);
        canvas.drawLine(const Offset(32, 12), const Offset(32, 68), line);
        for (var y = 0; y < 3; y++) {
          canvas.drawLine(
            Offset(45, 30.0 + y * 5),
            Offset(y == 2 ? 62 : 72, 30.0 + y * 5),
            Paint()
              ..color = paper.withValues(alpha: .75)
              ..strokeWidth = 1.4,
          );
        }
      case _StudioObject.paper:
        face(const Rect.fromLTWH(24, 17, 55, 62), paper, radius: 2);
        face(const Rect.fromLTWH(29, 10, 55, 63), paper, radius: 2);
        for (var y = 0; y < 5; y++) {
          canvas.drawLine(
            Offset(39, 25.0 + y * 7),
            Offset(y == 4 ? 60 : 72, 25.0 + y * 7),
            line,
          );
        }
        canvas.save();
        canvas.translate(80, 44);
        canvas.rotate(.43);
        face(const Rect.fromLTWH(-3, -26, 6, 49), accent, radius: 2);
        canvas.drawPath(
          Path()
            ..moveTo(-3, 23)
            ..lineTo(3, 23)
            ..lineTo(0, 31)
            ..close(),
          Paint()..color = metal,
        );
        canvas.restore();
      case _StudioObject.film:
        face(const Rect.fromLTWH(19, 30, 75, 48), accent);
        face(const Rect.fromLTWH(19, 18, 75, 16), metal, radius: 2);
        final stripes = Paint()..color = paper;
        for (var x = 28; x < 90; x += 20) {
          canvas.drawPath(
            Path()
              ..moveTo(x.toDouble(), 19)
              ..lineTo(x + 10, 19)
              ..lineTo(x + 1, 33)
              ..lineTo(x - 9, 33)
              ..close(),
            stripes,
          );
        }
        canvas.drawPath(
          Path()
            ..moveTo(49, 44)
            ..lineTo(49, 65)
            ..lineTo(66, 54.5)
            ..close(),
          Paint()..color = paper.withValues(alpha: .9),
        );
      case _StudioObject.microphone:
        face(const Rect.fromLTWH(35, 72, 43, 7), metal);
        face(const Rect.fromLTWH(53, 49, 7, 24), metal, radius: 2);
        final cradle = Path()
          ..moveTo(36, 36)
          ..lineTo(36, 47)
          ..quadraticBezierTo(36, 66, 56, 66)
          ..quadraticBezierTo(77, 66, 77, 47)
          ..lineTo(77, 36);
        canvas.drawPath(
          cradle,
          Paint()
            ..color = accent
            ..style = PaintingStyle.stroke
            ..strokeWidth = 4,
        );
        face(const Rect.fromLTWH(43, 9, 27, 47), accent, radius: 14);
        for (var y = 17; y <= 47; y += 5) {
          canvas.drawLine(
            Offset(49, y.toDouble()),
            Offset(64, y.toDouble()),
            line..strokeWidth = 1.5,
          );
        }
    }
    canvas.restore();
  }

  @override
  bool shouldRepaint(_StudioObjectPainter old) =>
      old.object != object || old.accent != accent || old.palette != palette;
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
