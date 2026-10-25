import 'dart:math' as math;
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/physics.dart';

import '../../../core/lumenis_icon.dart';

import '../../../core/lumenis_core_client.dart';
import '../../../core/lumenis_theme.dart';
import '../../../core/lumenis_split_handle.dart';
import '../../../l10n/lumenis_localizations.dart';
import '../../../navigation/lumenis_leave_guard.dart';
import '../sh01/media_project_files.dart';
import 'sh02_office_controller.dart';
import 'office_property_editor.dart';
import 'sh02_repository.dart';
import 'sh02_snapshot.dart';
import 'sh02_view_model.dart';
import '../research/shared_research_repository.dart';
import '../research/shared_research_workspace.dart';

class Sh02Screen extends StatefulWidget {
  const Sh02Screen({
    required this.client,
    this.repository,
    this.documentPicker,
    this.initialArtifactId,
    this.initialWorkKind,
    this.onBack,
    this.officeRepository,
    this.officeFiles,
    super.key,
  });

  final LumenisCoreClient client;
  final Sh02Repository? repository;
  final Sh02DocumentPicker? documentPicker;
  final String? initialArtifactId;
  final String? initialWorkKind;
  final VoidCallback? onBack;
  final Sh02OfficeRepository? officeRepository;
  final MediaProjectFiles? officeFiles;

  @override
  State<Sh02Screen> createState() => _Sh02ScreenState();
}

class _Sh02ScreenState extends State<Sh02Screen> {
  late final Sh02ViewModel _viewModel = Sh02ViewModel(
    repository: widget.repository ?? CoreSh02Repository(client: widget.client),
    documentPicker: widget.documentPicker ?? PlatformSh02DocumentPicker(),
  );

  @override
  void initState() {
    super.initState();
    unawaited(_loadInitial());
  }

  Future<void> _loadInitial() async {
    await _viewModel.refresh();
    if (mounted &&
        widget.initialWorkKind == 'material' &&
        widget.initialArtifactId != null) {
      await _viewModel.openImportById(widget.initialArtifactId!);
    }
  }

  @override
  void dispose() {
    _viewModel.dispose();
    super.dispose();
  }

  void _research() => unawaited(_openResearch());

  Future<void> _openResearch() async {
    if (!await (LumenisLeaveScope.maybeOf(context)?.requestLeave() ??
            Future.value(true)) ||
        !mounted) {
      return;
    }
    _viewModel.closeImport();
    await openSharedResearch(
      context,
      repository: CoreSharedResearchRepository(widget.client),
      sources: {
        for (final item in _viewModel.recentImports)
          item.artifactId: item.filename,
      },
    );
  }

  @override
  Widget build(BuildContext context) =>
      widget.initialArtifactId != null && widget.initialWorkKind != 'material'
      ? SharedResearchWorkspace(
          repository: CoreSharedResearchRepository(widget.client),
          sources: const {},
          initialArtifactId: widget.initialArtifactId,
          onBack: widget.onBack,
        )
      : ColoredBox(
          color: LumenisTheme.of(context).canvas,
          child: SafeArea(
            child: AnimatedBuilder(
              animation: _viewModel,
              builder: (context, _) => _LibraryWorkspace(
                viewModel: _viewModel,
                onResearch: _research,
                officeRepository:
                    widget.officeRepository ??
                    CoreSh02OfficeRepository(widget.client),
                officeFiles: widget.officeFiles ?? MediaProjectFiles(),
              ),
            ),
          ),
        );
}

enum _BrowseMode { list, space }

class _LibraryWorkspace extends StatefulWidget {
  const _LibraryWorkspace({
    required this.viewModel,
    required this.onResearch,
    required this.officeRepository,
    required this.officeFiles,
  });
  final Sh02ViewModel viewModel;
  final VoidCallback onResearch;
  final Sh02OfficeRepository officeRepository;
  final MediaProjectFiles officeFiles;

  @override
  State<_LibraryWorkspace> createState() => _LibraryWorkspaceState();
}

class _LibraryWorkspaceState extends State<_LibraryWorkspace> {
  bool _sources = false;

  @override
  Widget build(BuildContext context) {
    final model = widget.viewModel;
    final palette = LumenisTheme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(24, 20, 24, 16),
          child: LayoutBuilder(
            builder: (context, box) {
              final title = Text(
                context.lumenisL10n.text('screen.SH-02'),
                style: TextStyle(
                  fontSize: 30,
                  fontWeight: FontWeight.w600,
                  letterSpacing: -0.8,
                  color: palette.foreground,
                ),
              );
              final actions = _ImportActions(
                viewModel: model,
                onResearch: widget.onResearch,
              );
              if (box.maxWidth >= 760 &&
                  MediaQuery.textScalerOf(context).scale(16) <= 24) {
                return Row(
                  children: [
                    Expanded(child: title),
                    actions,
                  ],
                );
              }
              return Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [title, const SizedBox(height: 14), actions],
              );
            },
          ),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24),
          child: Row(
            children: [
              _tab(false, _copy(context, '我的资料', 'My materials', '내 자료')),
              const SizedBox(width: 24),
              _tab(true, _copy(context, '来源资料', 'Sources', '출처 자료')),
            ],
          ),
        ),
        Expanded(
          child: DecoratedBox(
            decoration: BoxDecoration(
              color: palette.surface,
              border: Border(top: BorderSide(color: palette.line)),
            ),
            child: Padding(
              padding: const EdgeInsets.only(top: 1),
              child: IndexedStack(
                index: _sources ? 1 : 0,
                children: [
                  _ImportPanel(
                    viewModel: model,
                    officeRepository: widget.officeRepository,
                    officeFiles: widget.officeFiles,
                  ),
                  switch (model.phase) {
                    Sh02LoadPhase.loading => _LoadingState(),
                    Sh02LoadPhase.blocked => _BlockedState(
                      error: model.scopeError,
                      onRetry: model.refresh,
                    ),
                    Sh02LoadPhase.failed => _FailureState(
                      kind: model.failureKind!,
                      onRetry: model.refresh,
                    ),
                    Sh02LoadPhase.ready => _Workspace(viewModel: model),
                  },
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _tab(bool sources, String label) {
    final palette = LumenisTheme.of(context);
    final selected = _sources == sources;
    return Semantics(
      selected: selected,
      button: true,
      child: DecoratedBox(
        decoration: BoxDecoration(
          border: Border(
            bottom: BorderSide(
              width: 3,
              color: selected ? palette.accent : Colors.transparent,
            ),
          ),
        ),
        child: TextButton(
          key: Key(sources ? 'sh02-sources-tab' : 'sh02-materials-tab'),
          style: TextButton.styleFrom(
            foregroundColor: selected ? palette.foreground : palette.muted,
            minimumSize: const Size(48, 48),
            padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 12),
            shape: const RoundedRectangleBorder(),
          ),
          onPressed: () => setState(() => _sources = sources),
          child: Text(label),
        ),
      ),
    );
  }
}

class _Workspace extends StatefulWidget {
  const _Workspace({required this.viewModel});

  final Sh02ViewModel viewModel;

  @override
  State<_Workspace> createState() => _WorkspaceState();
}

class _WorkspaceState extends State<_Workspace> {
  final TransformationController _camera = TransformationController();
  final ScrollController _browseScrollController = ScrollController();
  final TextEditingController _queryController = TextEditingController();
  final FocusNode _browseFallbackFocusNode = FocusNode(
    debugLabel: 'SH-02 search fallback',
  );
  final Map<String, FocusNode> _itemFocusNodes = {};
  _BrowseMode _mode = _BrowseMode.space;
  String? _focusedItemId;
  String? _originItemId;
  double? _browseOffsetBeforeFocus;

  @override
  void initState() {
    super.initState();
    _queryController.text = widget.viewModel.query;
    _syncItemFocusNodes();
  }

  @override
  void didUpdateWidget(covariant _Workspace oldWidget) {
    super.didUpdateWidget(oldWidget);
    _syncItemFocusNodes();
    final query = widget.viewModel.query;
    if (_queryController.text != query) {
      _queryController.value = TextEditingValue(
        text: query,
        selection: TextSelection.collapsed(offset: query.length),
      );
    }
  }

  void _syncItemFocusNodes() {
    final visibleIds = widget.viewModel.visibleEvidence
        .map((item) => item.internalId)
        .toSet();
    for (final item in widget.viewModel.visibleEvidence) {
      _itemFocusNodes.putIfAbsent(
        item.internalId,
        () => FocusNode(debugLabel: 'SH-02 material'),
      );
    }
    final staleIds = _itemFocusNodes.keys
        .where((itemId) => !visibleIds.contains(itemId))
        .toList();
    if (staleIds.isEmpty) return;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      final stillVisibleIds = widget.viewModel.visibleEvidence
          .map((item) => item.internalId)
          .toSet();
      for (final itemId in staleIds) {
        if (!stillVisibleIds.contains(itemId)) {
          _itemFocusNodes.remove(itemId)?.dispose();
        }
      }
    });
  }

  @override
  void dispose() {
    _camera.dispose();
    _browseScrollController.dispose();
    _queryController.dispose();
    _browseFallbackFocusNode.dispose();
    for (final node in _itemFocusNodes.values) {
      node.dispose();
    }
    super.dispose();
  }

  void _openItem(Sh02Evidence item) {
    if (!widget.viewModel.visibleEvidence.any(
      (visibleItem) => visibleItem.internalId == item.internalId,
    )) {
      return;
    }
    _originItemId = item.internalId;
    _browseOffsetBeforeFocus = _browseScrollController.hasClients
        ? _browseScrollController.offset
        : null;
    widget.viewModel.select(item);
    setState(() => _focusedItemId = item.internalId);
  }

  void _returnFromFocus() {
    final originItemId = _originItemId;
    final browseOffset = _browseOffsetBeforeFocus;
    _originItemId = null;
    _browseOffsetBeforeFocus = null;
    setState(() => _focusedItemId = null);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      if (browseOffset != null && _browseScrollController.hasClients) {
        final position = _browseScrollController.position;
        _browseScrollController.jumpTo(
          browseOffset
              .clamp(position.minScrollExtent, position.maxScrollExtent)
              .toDouble(),
        );
      }

      final itemIsVisible =
          originItemId != null &&
          widget.viewModel.visibleEvidence.any(
            (item) => item.internalId == originItemId,
          );
      final itemFocusNode = originItemId == null
          ? null
          : _itemFocusNodes[originItemId];
      if (itemIsVisible &&
          itemFocusNode != null &&
          itemFocusNode.context != null &&
          itemFocusNode.canRequestFocus) {
        itemFocusNode.requestFocus();
      } else if (_browseFallbackFocusNode.context != null) {
        _browseFallbackFocusNode.requestFocus();
      }
    });
  }

  void _zoom(double factor, Size viewport) {
    final current = _camera.value.getMaxScaleOnAxis();
    final target = (current * factor).clamp(0.5, 2.25).toDouble();
    if (target == current) return;
    final center = Offset(viewport.width / 2, viewport.height / 2);
    final sceneCenter = _camera.toScene(center);
    _camera.value = Matrix4.identity()
      ..translateByDouble(center.dx, center.dy, 0, 1)
      ..scaleByDouble(target, target, 1, 1)
      ..translateByDouble(-sceneCenter.dx, -sceneCenter.dy, 0, 1);
  }

  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, constraints) {
      final wide = constraints.maxWidth >= 1120;
      final medium = constraints.maxWidth >= 760;
      final viewModel = widget.viewModel;
      final snapshot = viewModel.snapshot!;
      Sh02Evidence? focused;
      final focusedId = _focusedItemId;
      if (focusedId != null) {
        for (final item in viewModel.visibleEvidence) {
          if (item.internalId == focusedId) {
            focused = item;
            break;
          }
        }
      }
      final isFocused = focusedId != null;
      final browser = isFocused
          ? _FocusedMaterial(
              item: focused,
              returnLabel: _copy(
                context,
                _mode == _BrowseMode.space ? '返回空间' : '返回列表',
                _mode == _BrowseMode.space ? 'Back to space' : 'Back to list',
                _mode == _BrowseMode.space ? '공간으로 돌아가기' : '목록으로 돌아가기',
              ),
              onReturn: _returnFromFocus,
            )
          : _BrowseStage(
              viewModel: viewModel,
              mode: _mode,
              camera: _camera,
              focusNodes: _itemFocusNodes,
              onModeChanged: (mode) => setState(() => _mode = mode),
              onOpenItem: _openItem,
              onZoom: _zoom,
            );
      final inspector = isFocused
          ? null
          : _TraceInspector(item: viewModel.selected);
      return Align(
        alignment: Alignment.topCenter,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1540),
          child: SingleChildScrollView(
            key: const Key('sh02-workspace-scroll'),
            controller: _browseScrollController,
            padding: EdgeInsets.fromLTRB(
              wide ? 32 : 18,
              24,
              wide ? 32 : 18,
              44,
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _ScopeBanner(scope: snapshot.scope),
                if (snapshot.partial)
                  _InfoMessage(
                    _copy(
                      context,
                      '部分资料暂不可用，已显示可读取的内容。',
                      'Some materials are unavailable. Available items are shown.',
                      '일부 자료를 사용할 수 없습니다. 읽을 수 있는 자료를 표시합니다.',
                    ),
                  ),
                const SizedBox(height: 16),
                if (wide)
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      SizedBox(
                        width: 270,
                        child: _SearchRail(
                          viewModel: viewModel,
                          queryController: _queryController,
                          focusNode: _browseFallbackFocusNode,
                        ),
                      ),
                      const SizedBox(width: 16),
                      Expanded(child: browser),
                      if (inspector != null) ...[
                        const SizedBox(width: 16),
                        SizedBox(width: 330, child: inspector),
                      ],
                    ],
                  )
                else if (medium)
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      _SearchRail(
                        viewModel: viewModel,
                        queryController: _queryController,
                        focusNode: _browseFallbackFocusNode,
                      ),
                      const SizedBox(height: 14),
                      if (inspector == null)
                        browser
                      else
                        Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Expanded(child: browser),
                            const SizedBox(width: 14),
                            Expanded(child: inspector),
                          ],
                        ),
                    ],
                  )
                else ...[
                  if (!isFocused) ...[
                    _SearchRail(
                      viewModel: viewModel,
                      queryController: _queryController,
                      focusNode: _browseFallbackFocusNode,
                    ),
                    const SizedBox(height: 14),
                  ],
                  browser,
                  if (inspector != null) ...[
                    const SizedBox(height: 14),
                    inspector,
                  ],
                ],
                if (!isFocused) ...[
                  const SizedBox(height: 14),
                  Align(
                    alignment: Alignment.centerLeft,
                    child: OutlinedButton.icon(
                      onPressed: viewModel.refresh,
                      icon: const LumenisIcon(Icons.refresh_rounded),
                      label: Text(
                        _copy(context, '重新读取', 'Read again', '다시 읽기'),
                      ),
                      style: OutlinedButton.styleFrom(
                        minimumSize: const Size(48, 48),
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
      );
    },
  );
}

class _ImportActions extends StatelessWidget {
  const _ImportActions({required this.viewModel, required this.onResearch});
  final Sh02ViewModel viewModel;
  final VoidCallback onResearch;

  @override
  Widget build(BuildContext context) {
    final status = viewModel.importStatus;
    return Wrap(
      spacing: 10,
      runSpacing: 8,
      children: [
        OutlinedButton.icon(
          key: const Key('sh02-import-document'),
          onPressed: status == Sh02ImportStatus.uploading
              ? null
              : status == Sh02ImportStatus.uncertain
              ? viewModel.checkImportStatus
              : () async {
                  if (await (LumenisLeaveScope.maybeOf(
                        context,
                      )?.requestLeave() ??
                      Future.value(true))) {
                    await viewModel.importDocument();
                  }
                },
          icon: Icon(
            status == Sh02ImportStatus.uncertain
                ? Icons.sync_rounded
                : Icons.add_rounded,
          ),
          label: Text(switch (status) {
            Sh02ImportStatus.uploading => _copy(
              context,
              '正在保存…',
              'Saving…',
              '저장 중…',
            ),
            Sh02ImportStatus.uncertain => _copy(
              context,
              '核对导入结果',
              'Check import status',
              '가져오기 결과 확인',
            ),
            _ => _copy(context, '选择文件', 'Choose a file', '파일 선택'),
          }),
          style: OutlinedButton.styleFrom(minimumSize: const Size(48, 48)),
        ),
        TextButton.icon(
          onPressed: onResearch,
          icon: const Icon(Icons.auto_stories_outlined),
          label: Text(_copy(context, '研究与成果', 'Research & results', '연구와 결과')),
        ),
      ],
    );
  }
}

class _ImportPanel extends StatefulWidget {
  const _ImportPanel({
    required this.viewModel,
    required this.officeRepository,
    required this.officeFiles,
  });
  final Sh02ViewModel viewModel;
  final Sh02OfficeRepository officeRepository;
  final MediaProjectFiles officeFiles;

  @override
  State<_ImportPanel> createState() => _ImportPanelState();
}

class _ImportPanelState extends State<_ImportPanel> {
  final _query = TextEditingController();
  final _timeline = ScrollController();
  final _cardFocus = <String, FocusNode>{};
  double? _returnOffset;
  String? _returnArtifact;

  Future<void> _open(Sh02ImportedMaterial item) async {
    if (widget.viewModel.openedImport?.artifactId == item.artifactId) return;
    if (!await (LumenisLeaveScope.maybeOf(context)?.requestLeave() ??
            Future.value(true)) ||
        !mounted) {
      return;
    }
    if (widget.viewModel.openedImport == null && _timeline.hasClients) {
      _returnOffset = _timeline.offset;
    }
    _returnArtifact = item.artifactId;
    unawaited(widget.viewModel.openImport(item));
  }

  Future<void> _close() async {
    if (!await (LumenisLeaveScope.maybeOf(context)?.requestLeave() ??
            Future.value(true)) ||
        !mounted) {
      return;
    }
    widget.viewModel.closeImport();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      if (_returnOffset != null && _timeline.hasClients) {
        _timeline.jumpTo(
          _returnOffset!.clamp(0, _timeline.position.maxScrollExtent),
        );
      }
      final focus = _cardFocus[_returnArtifact];
      if (focus?.context != null) focus!.requestFocus();
    });
  }

  @override
  void dispose() {
    _query.dispose();
    _timeline.dispose();
    for (final node in _cardFocus.values) {
      node.dispose();
    }
    super.dispose();
  }

  Widget _notice(BuildContext context) {
    final model = widget.viewModel;
    final status = model.importStatus;
    final message = status == Sh02ImportStatus.uploading
        ? _copy(context, '正在保存资料…', 'Saving material…', '자료 저장 중…')
        : status == Sh02ImportStatus.uncertain
        ? _copy(
            context,
            '结果尚未确认。请继续核对最近导入记录，确认前不要重复上传。',
            'The result is not confirmed yet. Check recent imports before trying again.',
            '결과가 아직 확인되지 않았습니다. 다시 업로드하기 전에 최근 가져오기를 확인하세요.',
          )
        : status == Sh02ImportStatus.failed
        ? _copy(
            context,
            '未能导入。请检查文件格式和大小（最多 8 MB），然后重试。',
            'Could not import. Check the format and size (up to 8 MB), then retry.',
            '가져오지 못했습니다. 형식과 크기(최대 8MB)를 확인한 뒤 다시 시도하세요.',
          )
        : model.importOpenFailed
        ? _copy(
            context,
            '这份资料暂时无法读取。',
            'This material is temporarily unreadable.',
            '자료를 지금 읽을 수 없습니다.',
          )
        : !model.importsVerificationComplete && !model.importsFailed
        ? _copy(
            context,
            '部分记录无法核验或读取；下方只显示可确认的资料。',
            'Some records could not be verified or read. Only confirmed materials are shown below.',
            '일부 기록을 확인하거나 읽지 못했습니다. 아래에는 확인된 자료만 표시합니다.',
          )
        : null;
    return message == null
        ? const SizedBox.shrink()
        : Semantics(
            liveRegion: true,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(22, 8, 22, 0),
              child: Text(
                message,
                style: TextStyle(color: LumenisTheme.of(context).muted),
              ),
            ),
          );
  }

  String _date(BuildContext context, String value) {
    final date = DateTime.tryParse(value)?.toLocal();
    return date == null
        ? _copy(context, '入库时间未知', 'Import date unknown', '등록 날짜 알 수 없음')
        : MaterialLocalizations.of(context).formatFullDate(date);
  }

  Widget _materials(BuildContext context, {required bool compact}) {
    final model = widget.viewModel;
    final query = _query.text.trim().toLowerCase();
    final items = model.recentImports
        .where(
          (item) =>
              query.isEmpty ||
              item.filename.toLowerCase().contains(query) ||
              item.excerpts.any((text) => text.toLowerCase().contains(query)),
        )
        .toList();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(22, 18, 22, 12),
          child: TextField(
            key: const Key('sh02-import-search'),
            controller: _query,
            onChanged: (_) => setState(() {}),
            decoration: InputDecoration(
              hintText: _copy(
                context,
                '查找已载入资料',
                'Find loaded materials',
                '불러온 자료 찾기',
              ),
              prefixIcon: const Icon(Icons.search_rounded),
              suffixIcon: _query.text.isEmpty
                  ? null
                  : IconButton(
                      tooltip: _copy(context, '清除', 'Clear', '지우기'),
                      icon: const Icon(Icons.close),
                      onPressed: () => setState(_query.clear),
                    ),
            ),
          ),
        ),
        Expanded(
          child: CustomScrollView(
            key: const PageStorageKey('sh02-material-timeline'),
            controller: _timeline,
            slivers: [
              SliverPadding(
                padding: const EdgeInsets.fromLTRB(22, 2, 22, 10),
                sliver: SliverToBoxAdapter(
                  child: Text(
                    _copy(context, '最近导入', 'Recent imports', '최근 가져오기'),
                    style: const TextStyle(
                      fontSize: 15,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ),
              if (model.importsLoading && model.recentImports.isEmpty)
                const SliverToBoxAdapter(
                  child: LinearProgressIndicator(minHeight: 2),
                ),
              if (model.importsFailed)
                SliverToBoxAdapter(
                  child: Padding(
                    padding: const EdgeInsets.all(22),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          _copy(
                            context,
                            '最近导入暂时无法读取。',
                            'Recent imports are unavailable.',
                            '최근 가져오기를 읽을 수 없습니다.',
                          ),
                        ),
                        TextButton(
                          onPressed: () => model.loadRecentImports(),
                          child: Text(_copy(context, '重试', 'Retry', '다시 시도')),
                        ),
                      ],
                    ),
                  ),
                ),
              if (!model.importsLoading &&
                  !model.importsFailed &&
                  items.isEmpty)
                SliverFillRemaining(
                  hasScrollBody: false,
                  child: Center(
                    child: Padding(
                      padding: const EdgeInsets.all(26),
                      child: Text(
                        query.isEmpty
                            ? _copy(
                                context,
                                '导入第一份资料',
                                'Import your first material',
                                '첫 자료 가져오기',
                              )
                            : _copy(
                                context,
                                '已载入资料中没有匹配项',
                                'No matches in loaded materials',
                                '불러온 자료에 일치 항목 없음',
                              ),
                        style: TextStyle(
                          color: LumenisTheme.of(context).muted,
                          fontSize: 20,
                        ),
                      ),
                    ),
                  ),
                ),
              SliverLayoutBuilder(
                builder: (context, constraints) {
                  final groups = <String, List<Sh02ImportedMaterial>>{};
                  for (final item in items) {
                    groups
                        .putIfAbsent(_date(context, item.createdAt), () => [])
                        .add(item);
                  }
                  final days = groups.keys.toList();
                  final available = constraints.crossAxisExtent - 44;
                  final columns = compact
                      ? 1
                      : (available / 340).floor().clamp(1, 4);
                  final width = (available - (columns - 1) * 20) / columns;
                  return SliverPadding(
                    padding: const EdgeInsets.symmetric(horizontal: 22),
                    sliver: SliverList.builder(
                      itemCount: days.length,
                      itemBuilder: (context, index) => Padding(
                        padding: const EdgeInsets.only(bottom: 30),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            Padding(
                              padding: const EdgeInsets.only(
                                top: 4,
                                bottom: 16,
                              ),
                              child: Text(
                                days[index],
                                style: TextStyle(
                                  fontSize: 12,
                                  color: LumenisTheme.of(context).muted,
                                ),
                              ),
                            ),
                            Wrap(
                              spacing: 20,
                              runSpacing: 20,
                              children: [
                                for (final item in groups[days[index]]!)
                                  SizedBox(
                                    width: width,
                                    child: compact
                                        ? Material(
                                            color: Colors.transparent,
                                            child: ListTile(
                                              contentPadding: EdgeInsets.zero,
                                              selected:
                                                  model
                                                      .openedImport
                                                      ?.artifactId ==
                                                  item.artifactId,
                                              leading: const Icon(
                                                Icons.description_outlined,
                                              ),
                                              title: Text(
                                                item.filename,
                                                maxLines: 2,
                                                overflow: TextOverflow.ellipsis,
                                              ),
                                              subtitle: Text(
                                                '${(item.sizeBytes / 1024).toStringAsFixed(1)} KB',
                                              ),
                                              onTap: () => _open(item),
                                            ),
                                          )
                                        : _ImportedMaterialCard(
                                            key: ValueKey(item.artifactId),
                                            item: item,
                                            focusNode: _cardFocus.putIfAbsent(
                                              item.artifactId,
                                              FocusNode.new,
                                            ),
                                            onOpen: () => _open(item),
                                          ),
                                  ),
                              ],
                            ),
                          ],
                        ),
                      ),
                    ),
                  );
                },
              ),
              if (model.importsHaveMore)
                SliverPadding(
                  padding: const EdgeInsets.all(16),
                  sliver: SliverToBoxAdapter(
                    child: TextButton.icon(
                      onPressed: model.importsLoading
                          ? null
                          : model.loadMoreImports,
                      icon: const Icon(Icons.expand_more_rounded),
                      label: Text(
                        _copy(context, '更多资料', 'More imports', '더 보기'),
                      ),
                    ),
                  ),
                ),
            ],
          ),
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    final model = widget.viewModel;
    final opened = model.openedImport;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _notice(context),
        if (model.openingImport) const LinearProgressIndicator(minHeight: 2),
        Expanded(
          child: LayoutBuilder(
            builder: (context, constraints) {
              final wide = constraints.maxWidth >= 1050;
              final reading = opened != null;
              final reader = reading
                  ? SingleChildScrollView(
                      key: ValueKey(
                        'reader-${opened.workId ?? opened.artifactId}',
                      ),
                      padding: const EdgeInsets.fromLTRB(28, 22, 28, 36),
                      child: _ImportedMaterialReader(
                        item: opened,
                        onClose: _close,
                        viewModel: model,
                        officeRepository: widget.officeRepository,
                        officeFiles: widget.officeFiles,
                      ),
                    )
                  : Center(
                      child: Padding(
                        padding: const EdgeInsets.all(30),
                        child: Text(
                          _copy(context, '打开一份资料', 'Open a material', '자료 열기'),
                          style: TextStyle(
                            fontSize: 25,
                            color: LumenisTheme.of(context).muted,
                          ),
                        ),
                      ),
                    );
              if (!wide && reading) return reader;
              if (!reading) return _materials(context, compact: false);
              return Row(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  SizedBox(
                    width: reading ? 280 : 340,
                    child: _materials(context, compact: reading),
                  ),
                  VerticalDivider(
                    width: 1,
                    color: LumenisTheme.of(context).line,
                  ),
                  Expanded(
                    child: DecoratedBox(
                      decoration: LumenisTheme.paper(
                        LumenisTheme.of(context),
                        radius: 0,
                      ),
                      child: reader,
                    ),
                  ),
                ],
              );
            },
          ),
        ),
      ],
    );
  }
}

class _ImportedMaterialCard extends StatefulWidget {
  const _ImportedMaterialCard({
    super.key,
    required this.item,
    required this.onOpen,
    this.focusNode,
  });
  final Sh02ImportedMaterial item;
  final VoidCallback onOpen;
  final FocusNode? focusNode;

  @override
  State<_ImportedMaterialCard> createState() => _ImportedMaterialCardState();
}

class _ImportedMaterialCardState extends State<_ImportedMaterialCard>
    with TickerProviderStateMixin {
  bool _hovered = false;
  bool _pressed = false;
  bool _details = false;
  Offset _tilt = Offset.zero;
  bool _dragging = false;
  static const _travel = 24.0;
  static const _spring = SpringDescription(
    mass: 1.2,
    stiffness: 240,
    damping: 23,
  );
  late final _horizontal = AnimationController.unbounded(vsync: this);
  late final _vertical = AnimationController.unbounded(vsync: this);
  late final _flip = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 360),
  );

  @override
  void dispose() {
    _horizontal.dispose();
    _vertical.dispose();
    _flip.dispose();
    super.dispose();
  }

  void _release([Offset velocity = Offset.zero]) {
    setState(() => _dragging = false);
    for (final (controller, speed) in [
      (_horizontal, velocity.dx),
      (_vertical, velocity.dy),
    ]) {
      controller.animateWith(
        SpringSimulation(_spring, controller.value, 0, speed.clamp(-180, 180)),
      );
    }
  }

  void _turn(bool reduced) {
    setState(() => _details = !_details);
    if (reduced) {
      _flip.value = _details ? 1 : 0;
    } else {
      _flip.animateTo(_details ? 1 : 0, curve: Curves.easeInOutCubic);
    }
  }

  @override
  Widget build(BuildContext context) {
    final palette = LumenisTheme.of(context);
    final item = widget.item;
    final reduced = MediaQuery.disableAnimationsOf(context);
    final date = DateTime.tryParse(item.createdAt)?.toLocal();
    final stamp = date == null
        ? item.createdAt
        : MaterialLocalizations.of(context).formatMediumDate(date);
    final preview = item.excerpts.isNotEmpty ? item.excerpts.first : item.text;
    final transform = Matrix4.identity()..setEntry(3, 2, 0.001);
    if (!reduced) {
      transform
        ..translateByDouble(
          0,
          _pressed
              ? 1
              : _hovered
              ? -4
              : 0,
          0,
          1,
        )
        ..rotateX(_tilt.dy * -0.025)
        ..rotateY(_tilt.dx * 0.025);
    }
    return AnimatedBuilder(
      animation: Listenable.merge([_horizontal, _vertical, _flip]),
      builder: (context, _) {
        final flipped = reduced ? _details : _flip.value >= 0.5;
        final physical = Matrix4.copy(transform);
        if (!reduced) {
          physical
            ..translateByDouble(
              _horizontal.value.clamp(-_travel, _travel),
              _vertical.value.clamp(-_travel, _travel) - (_dragging ? 6 : 0),
              0,
              1,
            )
            ..rotateY(math.pi * _flip.value - (flipped ? math.pi : 0));
        }
        return LayoutBuilder(
          builder: (context, constraints) => MouseRegion(
            onEnter: (_) => setState(() => _hovered = true),
            onExit: (_) => setState(() {
              _hovered = false;
              _tilt = Offset.zero;
            }),
            onHover: reduced
                ? null
                : (event) => setState(
                    () => _tilt = Offset(
                      (event.localPosition.dx / constraints.maxWidth * 2 - 1)
                          .clamp(-1, 1),
                      (event.localPosition.dy / 240 * 2 - 1).clamp(-1, 1),
                    ),
                  ),
            child: GestureDetector(
              onPanStart: reduced
                  ? null
                  : (_) {
                      _horizontal.stop();
                      _vertical.stop();
                      setState(() => _dragging = true);
                    },
              onPanUpdate: reduced
                  ? null
                  : (event) {
                      _horizontal.value =
                          (_horizontal.value + event.delta.dx * 0.55).clamp(
                            -_travel,
                            _travel,
                          );
                      _vertical.value =
                          (_vertical.value + event.delta.dy * 0.55).clamp(
                            -_travel,
                            _travel,
                          );
                    },
              onPanEnd: reduced
                  ? null
                  : (event) => _release(event.velocity.pixelsPerSecond),
              onPanCancel: reduced ? null : _release,
              child: AnimatedContainer(
                duration:
                    reduced ||
                        _dragging ||
                        _flip.isAnimating ||
                        _horizontal.isAnimating ||
                        _vertical.isAnimating
                    ? Duration.zero
                    : const Duration(milliseconds: 80),
                curve: Curves.easeOutCubic,
                transform: physical,
                transformAlignment: Alignment.center,
                decoration: ShapeDecoration(
                  color: palette.surfaceRaised,
                  shape: LumenisPixelBorder(
                    side: BorderSide(
                      color: _hovered
                          ? palette.foreground.withValues(alpha: 0.5)
                          : palette.line,
                    ),
                  ),
                  shadows: [
                    BoxShadow(
                      color: palette.foreground.withValues(
                        alpha: _hovered ? 0.10 : 0.04,
                      ),
                      blurRadius: _hovered ? 18 : 6,
                      offset: Offset(0, _hovered ? 10 : 3),
                    ),
                  ],
                ),
                child: Material(
                  color: Colors.transparent,
                  child: InkWell(
                    canRequestFocus: false,
                    excludeFromSemantics: true,
                    key: Key(
                      'sh02-import-${item.sourceSha256.substring(0, 12)}',
                    ),
                    onTap: widget.onOpen,
                    onHighlightChanged: (value) =>
                        setState(() => _pressed = value),
                    onFocusChange: (value) => setState(() => _hovered = value),
                    borderRadius: BorderRadius.circular(6),
                    child: Padding(
                      padding: const EdgeInsets.all(20),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Icon(
                                Icons.description_outlined,
                                size: 19,
                                color: palette.shared,
                              ),
                              const SizedBox(width: 9),
                              Expanded(
                                child: Text(
                                  stamp,
                                  style: TextStyle(
                                    fontSize: 12,
                                    color: palette.muted,
                                  ),
                                ),
                              ),
                              IconButton(
                                tooltip: _details
                                    ? _copy(
                                        context,
                                        '查看摘录',
                                        'Show extract',
                                        '발췌 보기',
                                      )
                                    : _copy(
                                        context,
                                        '资料详情',
                                        'Details',
                                        '자료 정보',
                                      ),
                                key: Key('sh02-flip-${item.artifactId}'),
                                onPressed: () => _turn(reduced),
                                icon: Icon(
                                  _details
                                      ? Icons.subject_rounded
                                      : Icons.info_outline_rounded,
                                  size: 18,
                                ),
                                constraints: const BoxConstraints(
                                  minWidth: 48,
                                  minHeight: 48,
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 12),
                          Text(
                            item.filename,
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              fontSize: 19,
                              height: 1.35,
                              fontWeight: FontWeight.w500,
                              color: palette.foreground,
                            ),
                          ),
                          const SizedBox(height: 18),
                          AnimatedSize(
                            duration: reduced
                                ? Duration.zero
                                : const Duration(milliseconds: 180),
                            alignment: Alignment.topLeft,
                            child: flipped
                                ? Text(
                                    _copy(
                                      context,
                                      '${item.characterCount} 字 · ${item.tableCount} 个表格',
                                      '${item.characterCount} characters · ${item.tableCount} tables',
                                      '${item.characterCount}자 · 표 ${item.tableCount}개',
                                    ),
                                    style: TextStyle(
                                      color: palette.muted,
                                      height: 1.65,
                                    ),
                                  )
                                : Text(
                                    preview.isEmpty
                                        ? _copy(
                                            context,
                                            '打开资料',
                                            'Open material',
                                            '자료 열기',
                                          )
                                        : preview,
                                    maxLines: 4,
                                    overflow: TextOverflow.ellipsis,
                                    style: TextStyle(
                                      color: palette.muted,
                                      height: 1.65,
                                    ),
                                  ),
                          ),
                          const SizedBox(height: 24),
                          Row(
                            children: [
                              TextButton(
                                focusNode: widget.focusNode,
                                onPressed: widget.onOpen,
                                child: Text(
                                  _copy(context, '阅读', 'Read', '읽기'),
                                  semanticsLabel: _copy(
                                    context,
                                    '阅读 ${item.filename}',
                                    'Read ${item.filename}',
                                    '${item.filename} 읽기',
                                  ),
                                ),
                              ),
                              const Spacer(),
                              Icon(
                                Icons.north_east_rounded,
                                size: 17,
                                color: palette.foreground,
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ),
        );
      },
    );
  }
}

class _ImportedMaterialReader extends StatefulWidget {
  const _ImportedMaterialReader({
    required this.item,
    required this.onClose,
    required this.viewModel,
    required this.officeRepository,
    required this.officeFiles,
  });
  final Sh02ImportedMaterial item;
  final VoidCallback onClose;
  final Sh02ViewModel viewModel;
  final Sh02OfficeRepository officeRepository;
  final MediaProjectFiles officeFiles;
  @override
  State<_ImportedMaterialReader> createState() =>
      _ImportedMaterialReaderState();
}

class _ImportedMaterialReaderState extends State<_ImportedMaterialReader> {
  bool _details = false;
  bool _officeMode = false;
  Sh02OfficeController? _office;
  LumenisLeaveGuard? _guard;
  String _officeText(String key, [Map<String, Object?> values = const {}]) =>
      context.lumenisL10n.text('sh02.office.$key', values: values);

  @override
  void didUpdateWidget(covariant _ImportedMaterialReader oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (_office case final office?) {
      if (widget.item.artifactId != office.source.artifactId) {
        office.dispose();
        _office = null;
        _officeMode = false;
        _guard?.refresh();
      }
    }
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final next = LumenisLeaveScope.maybeOf(context);
    if (!identical(next, _guard)) {
      _guard?.unregister(this);
      _guard = next;
      next?.register(
        this,
        needsProtection: () => _officeMode && _office?.protected == true,
        requestLeave: _requestLeave,
      );
    }
  }

  Future<bool> _requestLeave() async {
    final office = _office;
    if (!_officeMode || office == null || !office.protected) return true;
    if (office.busy) return false;
    final leave =
        await showDialog<bool>(
          context: context,
          builder: (context) => AlertDialog(
            title: Text(_officeText('leaveTitle')),
            content: Text(_officeText('leaveDetail')),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context, false),
                child: Text(_officeText('stay')),
              ),
              TextButton(
                onPressed: () => Navigator.pop(context, true),
                child: Text(_officeText('leave')),
              ),
            ],
          ),
        ) ??
        false;
    if (leave) office.undo(null);
    return leave;
  }

  void _beginOffice() {
    final office = _office ??= Sh02OfficeController(
      repository: widget.officeRepository,
      source: widget.item,
    )..addListener(_officeChanged);
    setState(() => _officeMode = true);
    if (office.page == null && !office.busy) unawaited(office.load());
  }

  void _officeChanged() {
    _guard?.refresh();
    final office = _office;
    if (office?.notice == 'saved' &&
        office!.source.artifactId != widget.item.artifactId) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted && identical(office, _office)) {
          widget.viewModel.presentOfficeVersion(office.source);
          unawaited(widget.viewModel.loadRecentImports());
        }
      });
    }
    if (mounted) setState(() {});
  }

  Future<void> _readOriginal() async {
    if (!await _requestLeave() || !mounted) return;
    final source = _office?.source;
    if (source != null) widget.viewModel.presentOfficeVersion(source);
    setState(() => _officeMode = false);
    if (widget.viewModel.sourcePage == null) {
      unawaited(widget.viewModel.loadSourcePage(0));
    }
  }

  @override
  void dispose() {
    _guard?.unregister(this);
    _office?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final item = _officeMode ? _office!.source : widget.item;
    final palette = LumenisTheme.of(context);
    final imported = DateTime.tryParse(item.createdAt)?.toLocal();
    final stamp = imported == null
        ? _copy(context, '未知', 'Unknown', '알 수 없음')
        : '${MaterialLocalizations.of(context).formatMediumDate(imported)} '
              '${MaterialLocalizations.of(context).formatTimeOfDay(TimeOfDay.fromDateTime(imported))}';
    final structured = {
      'xlsx',
      'xls',
      'docx',
      'doc',
      'pdf',
      'csv',
    }.contains(item.filename.split('.').last.toLowerCase());
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Align(
          alignment: Alignment.centerLeft,
          child: TextButton.icon(
            onPressed: widget.onClose,
            icon: const Icon(Icons.arrow_back_rounded),
            label: Text(
              _copy(
                context,
                '返回最近导入',
                'Back to recent imports',
                '최근 가져오기로 돌아가기',
              ),
            ),
          ),
        ),
        const SizedBox(height: 16),
        Text(
          _copy(context, '资料内容', 'Document', '자료 내용'),
          style: TextStyle(color: palette.muted, fontSize: 12),
        ),
        const SizedBox(height: 8),
        SelectableText(
          item.filename,
          style: TextStyle(
            fontWeight: FontWeight.w500,
            fontSize: 25,
            color: palette.foreground,
          ),
        ),
        const SizedBox(height: 22),
        if ({
          'docx',
          'pptx',
          'xlsx',
        }.contains(item.filename.split('.').last.toLowerCase())) ...[
          Align(
            alignment: Alignment.centerLeft,
            child: OutlinedButton.icon(
              key: const Key('sh02-office-mode'),
              onPressed: _office?.busy == true
                  ? null
                  : _officeMode
                  ? _readOriginal
                  : _beginOffice,
              icon: Icon(
                _officeMode ? Icons.description_outlined : Icons.edit_outlined,
                size: 18,
              ),
              label: Text(
                _officeText(_officeMode ? 'readOriginal' : 'editOriginal'),
              ),
            ),
          ),
          const SizedBox(height: 16),
        ],
        if (_officeMode && _office != null)
          _OfficeObjectsWorkspace(
            controller: _office!,
            files: widget.officeFiles,
          )
        else ...[
          Align(
            alignment: Alignment.centerLeft,
            child: SegmentedButton<bool>(
              showSelectedIcon: false,
              segments: [
                ButtonSegment(
                  value: false,
                  label: Text(_copy(context, '原文', 'Original', '원문')),
                ),
                ButtonSegment(
                  value: true,
                  label: Text(_copy(context, '概况', 'Overview', '개요')),
                ),
              ],
              selected: {_details},
              onSelectionChanged: (value) =>
                  setState(() => _details = value.single),
            ),
          ),
          const SizedBox(height: 24),
          if (_details) ...[
            Wrap(
              spacing: 28,
              runSpacing: 12,
              children: [
                Text(
                  _copy(
                    context,
                    '${item.characterCount} 字',
                    '${item.characterCount} characters',
                    '${item.characterCount}자',
                  ),
                ),
                Text(
                  _copy(
                    context,
                    '${item.tableCount} 个表格',
                    '${item.tableCount} tables',
                    '표 ${item.tableCount}개',
                  ),
                ),
                Text('${(item.sizeBytes / 1024).toStringAsFixed(1)} KB'),
              ],
            ),
            const SizedBox(height: 20),
            _DetailLine(
              label: _copy(context, '入库时间', 'Imported', '등록 시간'),
              value: stamp,
            ),
            _DetailLine(
              label: _copy(
                context,
                '原发布时间',
                'Original publication',
                '원래 게시 시간',
              ),
              value: _copy(context, '未提供', 'Not provided', '제공되지 않음'),
            ),
            if (item.excerpts.isNotEmpty) ...[
              const SizedBox(height: 26),
              Text(
                _copy(context, '资料摘录', 'Excerpts', '자료 발췌'),
                style: const TextStyle(fontWeight: FontWeight.w600),
              ),
              for (final excerpt in item.excerpts)
                Padding(
                  padding: const EdgeInsets.only(top: 14),
                  child: SelectableText(
                    excerpt,
                    style: const TextStyle(height: 1.7),
                  ),
                ),
            ],
            if (item.limitations.isNotEmpty) ...[
              const SizedBox(height: 26),
              for (final limitation in item.limitations)
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Text(
                    _materialLimitation(context, limitation),
                    style: TextStyle(color: palette.muted, height: 1.6),
                  ),
                ),
            ],
          ] else if (structured)
            _OriginalRows(viewModel: widget.viewModel)
          else
            SelectableText(
              item.text.isEmpty
                  ? _copy(
                      context,
                      '没有可显示的文本。',
                      'No readable text was returned.',
                      '표시할 텍스트가 없습니다.',
                    )
                  : item.text,
              style: const TextStyle(fontSize: 16, height: 1.8),
            ),
        ],
      ],
    );
  }
}

String _officeCopy(
  BuildContext context,
  String key, [
  Map<String, Object?> values = const {},
]) => context.lumenisL10n.text('sh02.office.$key', values: values);

String _officeObjectLabel(
  BuildContext context,
  Sh02OfficeObject object,
  int number,
) {
  final locator = object.locator;
  final pieces = <String>[];
  if (locator['sheet_name'] is String &&
      (locator['sheet_name'] as String).isNotEmpty) {
    pieces.add(locator['sheet_name'] as String);
  } else if (locator['cell'] is String) {
    pieces.add(_officeCopy(context, 'sheetUnknown'));
  }
  if (locator['slide_number'] is int) {
    pieces.add(
      _officeCopy(context, 'slide', {'number': locator['slide_number']}),
    );
  }
  if (locator['notes'] == true) pieces.add(_officeCopy(context, 'notes'));
  if (locator['cell'] is String) {
    pieces.add(_officeCopy(context, 'cell', {'cell': locator['cell']}));
    if (object.kind == 'cell_style') {
      pieces.add(_copy(context, '样式', 'Style', '스타일'));
    }
  } else if (object.structured) {
    final type = switch (object.kind) {
      'word_run_format' ||
      'drawing_run_format' => _copy(context, '文字样式', 'Text style', '문자 스타일'),
      'word_paragraph_format' => _copy(
        context,
        '段落排版',
        'Paragraph layout',
        '문단 레이아웃',
      ),
      'shape_geometry' => _copy(context, '图形位置', 'Shape position', '도형 위치'),
      _ => _copy(context, '样式', 'Style', '스타일'),
    };
    pieces.add('$type ${locator['paragraph_index'] ?? number}');
  } else {
    pieces.add(
      _officeCopy(context, 'objectText', {
        'number': locator['paragraph_index'] ?? number,
      }),
    );
  }
  return pieces.join(' · ');
}

class _OfficeObjectsWorkspace extends StatefulWidget {
  const _OfficeObjectsWorkspace({
    required this.controller,
    required this.files,
  });
  final Sh02OfficeController controller;
  final MediaProjectFiles files;
  @override
  State<_OfficeObjectsWorkspace> createState() =>
      _OfficeObjectsWorkspaceState();
}

class _OfficeObjectsWorkspaceState extends State<_OfficeObjectsWorkspace> {
  double _indexWidth = 240;
  final _search = TextEditingController();
  final _reason = TextEditingController();
  final _listScroll = ScrollController();
  String? _selected;
  String? _sourceId;
  bool _signatureConsent = false;
  String? _fileNotice;
  final _adopted = <String>{};
  List<Sh02OfficeComparison>? _lastComparisons;
  Sh02OfficeController get model => widget.controller;
  @override
  void dispose() {
    _search.dispose();
    _reason.dispose();
    _listScroll.dispose();
    super.dispose();
  }

  Future<void> _download() async {
    setState(() => _fileNotice = null);
    final file = await model.download();
    if (file == null || !mounted) return;
    try {
      final saved = await widget.files.save(
        ContentProjectFile(
          bytes: file.bytes,
          filename: file.filename,
          mediaType: file.mediaType,
        ),
      );
      if (saved && mounted) setState(() => _fileNotice = 'downloaded');
    } catch (_) {
      if (mounted) setState(() => _fileNotice = 'downloadFailed');
    }
  }

  Future<void> _adopt() async {
    if (_adopted.length != model.edits.length) {
      final confirmed =
          await showDialog<bool>(
            context: context,
            builder: (context) => AlertDialog(
              title: Text(_officeCopy(context, 'adopt')),
              content: Text(_officeCopy(context, 'adoptDetail')),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(context, false),
                  child: Text(context.lumenisL10n.text('common.cancel')),
                ),
                FilledButton(
                  onPressed: () => Navigator.pop(context, true),
                  child: Text(_officeCopy(context, 'adopt')),
                ),
              ],
            ),
          ) ??
          false;
      if (!confirmed || !mounted) return;
    }
    model.adoptComparison(_adopted);
  }

  @override
  Widget build(BuildContext context) {
    final page = model.page;
    final palette = LumenisTheme.of(context);
    if (_sourceId != model.source.artifactId) {
      _sourceId = model.source.artifactId;
      _signatureConsent = false;
      _fileNotice = null;
      if (model.notice == 'saved') _reason.clear();
    }
    if (!identical(_lastComparisons, model.comparisons)) {
      _lastComparisons = model.comparisons;
      _adopted
        ..clear()
        ..addAll(
          model.comparisons
              .where(
                (row) =>
                    row.latest != null && row.latest!.accepts(row.proposed),
              )
              .map((row) => row.previous.id),
        );
    }
    return Material(
      color: Colors.transparent,
      child: Column(
        key: const Key('sh02-office-workspace'),
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (model.busy) const LinearProgressIndicator(minHeight: 2),
          if (model.problem != null)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 12),
              child: Semantics(
                liveRegion: true,
                child: Text(
                  _officeCopy(context, model.problem!),
                  style: TextStyle(color: palette.caution),
                ),
              ),
            ),
          if (_fileNotice != null)
            Semantics(
              liveRegion: true,
              child: Text(_officeCopy(context, _fileNotice!)),
            ),
          if (model.notice == 'saved' && page != null)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 12),
              child: Semantics(
                liveRegion: true,
                child: Text(
                  _officeCopy(context, 'saved', {'version': page.version}),
                ),
              ),
            ),
          if (page == null)
            Align(
              alignment: Alignment.centerLeft,
              child: OutlinedButton.icon(
                key: const Key('sh02-office-load'),
                onPressed: model.busy ? null : () => model.load(),
                icon: const LumenisIcon(Icons.refresh_rounded, size: 18),
                label: Text(
                  _officeCopy(context, model.busy ? 'loading' : 'load'),
                ),
              ),
            )
          else ...[
            Wrap(
              spacing: 12,
              runSpacing: 8,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                Text(
                  _officeCopy(context, 'version', {'version': page.version}),
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                if (model.dirty)
                  Text(
                    _officeCopy(context, 'modified', {
                      'count': model.edits.length,
                    }),
                    style: TextStyle(color: palette.caution),
                  ),
                TextButton.icon(
                  key: const Key('sh02-office-download'),
                  onPressed: model.busy || !widget.files.canSave
                      ? null
                      : _download,
                  icon: const LumenisIcon(Icons.download_outlined, size: 18),
                  label: Text(_officeCopy(context, 'download')),
                ),
                if (model.source.parentArtifactId != null)
                  TextButton(
                    key: const Key('sh02-office-parent'),
                    onPressed: model.protected
                        ? null
                        : () =>
                              model.openVersion(model.source.parentArtifactId!),
                    child: Text(_officeCopy(context, 'parent')),
                  ),
                if (model.canOpenNewer)
                  TextButton(
                    key: const Key('sh02-office-newer'),
                    onPressed: model.protected ? null : model.openNewer,
                    child: Text(_officeCopy(context, 'newer')),
                  ),
                if (model.dirty)
                  TextButton(
                    key: const Key('sh02-office-undo-all'),
                    onPressed: model.busy || model.saveUnknown
                        ? null
                        : () => model.undo(null),
                    child: Text(_officeCopy(context, 'undoAll')),
                  ),
              ],
            ),
            if (!page.current)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 12),
                child: Text(
                  _officeCopy(context, 'historical'),
                  style: TextStyle(color: palette.muted),
                ),
              ),
            if (page.activeContent)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 12),
                child: Text(
                  _officeCopy(context, 'activeContent'),
                  style: TextStyle(color: palette.caution),
                ),
              ),
            if (page.formulaRecalculationNeeded)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 12),
                child: Text(
                  _officeCopy(context, 'formulaNotice'),
                  style: TextStyle(color: palette.muted),
                ),
              ),
            if (page.unsupported > 0)
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Text(
                  _officeCopy(context, 'unsupported', {
                    'count': page.unsupported,
                  }),
                  style: TextStyle(color: palette.muted),
                ),
              ),
            if (model.conflict || !page.current)
              Align(
                alignment: Alignment.centerLeft,
                child: OutlinedButton(
                  key: const Key('sh02-office-compare'),
                  onPressed: model.busy ? null : model.compareLatest,
                  child: Text(_officeCopy(context, 'compare')),
                ),
              ),
            const SizedBox(height: 12),
            SizedBox(
              height: (MediaQuery.sizeOf(context).height - 320).clamp(
                420.0,
                760.0,
              ),
              child:
                  model.comparisons.isNotEmpty || model.comparisonPage != null
                  ? _comparison()
                  : LayoutBuilder(
                      builder: (context, box) {
                        final wide =
                            box.maxWidth >= 680 &&
                            MediaQuery.textScalerOf(context).scale(16) <= 24;
                        final selected = model.objects
                            .where((object) => object.id == _selected)
                            .firstOrNull;
                        final index = _index();
                        final editor = selected == null
                            ? Center(
                                child: Text(
                                  _officeCopy(context, 'selectObject'),
                                ),
                              )
                            : _editor(selected, wide);
                        return DecoratedBox(
                          decoration: LumenisTheme.paper(palette, radius: 10),
                          child: ClipPath(
                            clipper: ShapeBorderClipper(
                              shape: const LumenisPixelBorder(),
                            ),
                            child: Material(
                              color: Colors.transparent,
                              child: wide
                                  ? Row(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.stretch,
                                      children: [
                                        SizedBox(
                                          width: _indexWidth.clamp(
                                            180.0,
                                            box.maxWidth * .4,
                                          ),
                                          child: index,
                                        ),
                                        LumenisSplitHandle(
                                          key: const Key(
                                            'sh02-office-index-resize',
                                          ),
                                          label: switch (Localizations.localeOf(
                                            context,
                                          ).languageCode) {
                                            'zh' => '调整目录宽度',
                                            'ko' => '목차 너비 조절',
                                            _ => 'Resize outline',
                                          },
                                          onDelta: (delta) => setState(
                                            () => _indexWidth =
                                                (_indexWidth + delta).clamp(
                                                  180.0,
                                                  box.maxWidth * .4,
                                                ),
                                          ),
                                          onReset: () =>
                                              setState(() => _indexWidth = 240),
                                        ),
                                        Expanded(child: editor),
                                      ],
                                    )
                                  : selected == null
                                  ? index
                                  : editor,
                            ),
                          ),
                        );
                      },
                    ),
            ),
            if (model.dirty || model.saveUnknown) ...[
              const SizedBox(height: 18),
              if (page.signed) ...[
                Text(
                  _officeCopy(context, 'signatureWarning'),
                  style: TextStyle(color: palette.caution),
                ),
                CheckboxListTile(
                  key: const Key('sh02-office-signature-consent'),
                  contentPadding: EdgeInsets.zero,
                  controlAffinity: ListTileControlAffinity.leading,
                  value: _signatureConsent,
                  onChanged: model.busy || model.saveUnknown
                      ? null
                      : (value) =>
                            setState(() => _signatureConsent = value == true),
                  title: Text(_officeCopy(context, 'signatureConsent')),
                ),
              ],
              TextField(
                key: const Key('sh02-office-reason'),
                controller: _reason,
                minLines: 1,
                maxLines: 3,
                maxLength: 2000,
                enabled: !model.busy && !model.saveUnknown,
                decoration: InputDecoration(
                  labelText: _officeCopy(context, 'reason'),
                  counterText: '',
                ),
                onChanged: (_) => setState(() {}),
              ),
              const SizedBox(height: 12),
              Wrap(
                spacing: 12,
                runSpacing: 8,
                children: [
                  FilledButton.icon(
                    key: const Key('sh02-office-save'),
                    onPressed:
                        model.canSave &&
                            _reason.text.trim().isNotEmpty &&
                            (!page.signed || _signatureConsent)
                        ? () => model.save(
                            _reason.text,
                            invalidateSignature: _signatureConsent,
                          )
                        : null,
                    icon: const LumenisIcon(Icons.save_outlined, size: 18),
                    label: Text(_officeCopy(context, 'save')),
                  ),
                  if (model.saveUnknown)
                    OutlinedButton(
                      key: const Key('sh02-office-check'),
                      onPressed: model.busy ? null : model.checkSave,
                      child: Text(
                        _officeCopy(
                          context,
                          model.notice == 'checkMore' ? 'checkMore' : 'check',
                        ),
                      ),
                    ),
                ],
              ),
            ],
          ],
        ],
      ),
    );
  }

  Widget _index() {
    final query = _search.text.trim().toLowerCase();
    final visible = model.objects.indexed
        .where(
          (entry) =>
              query.isEmpty ||
              officeValueSummary(
                context,
                entry.$2.value,
              ).toLowerCase().contains(query) ||
              _officeObjectLabel(
                context,
                entry.$2,
                entry.$1 + 1,
              ).toLowerCase().contains(query),
        )
        .toList(growable: false);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.all(12),
          child: TextField(
            key: const Key('sh02-office-search'),
            controller: _search,
            decoration: InputDecoration(
              hintText: _officeCopy(context, 'search'),
              prefixIcon: const LumenisIcon(Icons.search_rounded, size: 18),
            ),
            onChanged: (_) => setState(() {}),
          ),
        ),
        Expanded(
          child: visible.isEmpty
              ? Center(child: Text(_officeCopy(context, 'empty')))
              : ListView.builder(
                  key: const Key('sh02-office-objects'),
                  controller: _listScroll,
                  itemCount: visible.length,
                  itemBuilder: (context, index) {
                    final (ordinal, object) = visible[index];
                    return ListTile(
                      key: ValueKey('sh02-office-object-${object.id}'),
                      selected: _selected == object.id,
                      title: Text(
                        _officeObjectLabel(
                          context,
                          object,
                          model.objects.indexOf(object) + 1,
                        ),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                      subtitle: Text(
                        officeValueSummary(context, model.value(object)),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                      trailing: model.edits.containsKey(object.id)
                          ? Tooltip(
                              message: _officeCopy(context, 'edited'),
                              child: const LumenisIcon(
                                Icons.edit_outlined,
                                size: 16,
                              ),
                            )
                          : null,
                      onTap: () => setState(() => _selected = object.id),
                    );
                  },
                ),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(12, 10, 12, 6),
          child: Text(
            _officeCopy(context, 'page', {
              'loaded': model.objects.length,
              'total': model.page!.total,
            }),
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ),
        if (model.nextOffset != null)
          TextButton(
            key: const Key('sh02-office-more'),
            onPressed: model.busy ? null : () => model.load(more: true),
            child: Text(_officeCopy(context, 'loadMore')),
          ),
      ],
    );
  }

  Widget _editor(Sh02OfficeObject object, bool wide) => ListView(
    key: ValueKey('sh02-office-editor-${model.source.artifactId}-${object.id}'),
    padding: const EdgeInsets.all(22),
    children: [
      if (!wide)
        Align(
          alignment: Alignment.centerLeft,
          child: TextButton.icon(
            onPressed: () => setState(() => _selected = null),
            icon: const LumenisIcon(Icons.arrow_back_rounded, size: 18),
            label: Text(_officeCopy(context, 'objects')),
          ),
        ),
      Text(
        _officeObjectLabel(context, object, model.objects.indexOf(object) + 1),
        style: Theme.of(context).textTheme.titleMedium,
      ),
      const SizedBox(height: 18),
      _OfficeValueEditor(
        key: ValueKey('${model.source.artifactId}:${object.id}'),
        object: object,
        value: model.value(object),
        enabled: model.canEdit,
        styleOptions: model.page?.styleOptions ?? const [],
        onChanged: (value) => model.change(object, value),
      ),
      if (model.edits.containsKey(object.id)) ...[
        const SizedBox(height: 12),
        Align(
          alignment: Alignment.centerLeft,
          child: TextButton.icon(
            key: const Key('sh02-office-undo-object'),
            onPressed: model.busy || model.saveUnknown
                ? null
                : () => model.undo(object.id),
            icon: const LumenisIcon(Icons.undo, size: 18),
            label: Text(_officeCopy(context, 'undo')),
          ),
        ),
        ExpansionTile(
          title: Text(_officeCopy(context, 'previousValue')),
          tilePadding: EdgeInsets.zero,
          children: [
            Align(
              alignment: Alignment.centerLeft,
              child: SelectableText(officeValueSummary(context, object.value)),
            ),
          ],
        ),
      ],
    ],
  );

  Widget _comparison() => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      Expanded(
        child: ListView.separated(
          itemCount: model.comparisons.length,
          separatorBuilder: (_, _) => const Divider(height: 28),
          itemBuilder: (context, index) {
            final row = model.comparisons[index];
            return Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                CheckboxListTile(
                  controlAffinity: ListTileControlAffinity.leading,
                  value: _adopted.contains(row.previous.id),
                  onChanged:
                      row.latest == null || !row.latest!.accepts(row.proposed)
                      ? null
                      : (value) => setState(() {
                          value == true
                              ? _adopted.add(row.previous.id)
                              : _adopted.remove(row.previous.id);
                        }),
                  title: Text(
                    _officeObjectLabel(context, row.previous, index + 1),
                  ),
                ),
                for (final (label, value) in [
                  ('previousValue', row.previous.value),
                  (
                    'currentValue',
                    row.latest?.value ?? _officeCopy(context, 'missingObject'),
                  ),
                  ('yourValue', row.proposed),
                ])
                  Padding(
                    padding: const EdgeInsets.fromLTRB(16, 4, 16, 12),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          _officeCopy(context, label),
                          style: Theme.of(context).textTheme.labelMedium,
                        ),
                        const SizedBox(height: 4),
                        SelectableText(officeValueSummary(context, value)),
                      ],
                    ),
                  ),
              ],
            );
          },
        ),
      ),
      Align(
        alignment: Alignment.centerLeft,
        child: FilledButton(
          key: const Key('sh02-office-adopt'),
          onPressed: model.busy ? null : _adopt,
          child: Text(_officeCopy(context, 'adopt')),
        ),
      ),
    ],
  );
}

class _OfficeValueEditor extends StatefulWidget {
  const _OfficeValueEditor({
    required this.object,
    required this.value,
    required this.enabled,
    required this.onChanged,
    this.styleOptions = const [],
    super.key,
  });
  final Sh02OfficeObject object;
  final Object value;
  final bool enabled;
  final ValueChanged<Object> onChanged;
  final List<Map<String, dynamic>> styleOptions;
  @override
  State<_OfficeValueEditor> createState() => _OfficeValueEditorState();
}

class _OfficeValueEditorState extends State<_OfficeValueEditor> {
  late final TextEditingController _value = TextEditingController(
    text: '${widget.value}',
  );
  @override
  void didUpdateWidget(covariant _OfficeValueEditor oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.value is String && _value.text != widget.value) {
      _value.value = TextEditingValue(
        text: widget.value as String,
        selection: TextSelection.collapsed(
          offset: _value.selection.extentOffset.clamp(
            0,
            (widget.value as String).length,
          ),
        ),
      );
    }
  }

  @override
  void dispose() {
    _value.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final kind = widget.object.kind;
    if (widget.object.structured) {
      return OfficePropertyEditor(
        kind: kind,
        value: Map<String, dynamic>.from(widget.value as Map),
        enabled: widget.enabled,
        styleOptions: widget.styleOptions,
        onChanged: widget.onChanged,
      );
    }
    if (kind == 'cell_boolean') {
      return SwitchListTile(
        key: const Key('sh02-office-value-boolean'),
        contentPadding: EdgeInsets.zero,
        value: widget.value as bool,
        onChanged: widget.enabled ? widget.onChanged : null,
        title: Text(
          _officeCopy(context, (widget.value as bool) ? 'true' : 'false'),
        ),
      );
    }
    return TextField(
      key: const Key('sh02-office-value'),
      controller: _value,
      enabled: widget.enabled,
      minLines: kind == 'cell_number' ? 1 : 3,
      maxLines: kind == 'cell_number' ? 2 : 12,
      keyboardType: kind == 'cell_number'
          ? const TextInputType.numberWithOptions(signed: true, decimal: true)
          : TextInputType.multiline,
      decoration: InputDecoration(
        labelText: _officeCopy(
          context,
          kind == 'cell_number'
              ? 'number'
              : kind == 'cell_formula'
              ? 'formula'
              : 'text',
        ),
        errorText: widget.object.accepts(widget.value)
            ? null
            : _officeCopy(context, 'invalid'),
      ),
      onChanged: widget.onChanged,
    );
  }
}

class _OriginalRows extends StatelessWidget {
  const _OriginalRows({required this.viewModel});
  final Sh02ViewModel viewModel;

  @override
  Widget build(BuildContext context) {
    final page = viewModel.sourcePage;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Wrap(
          spacing: 12,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            OutlinedButton.icon(
              key: const Key('sh02-original-rows'),
              onPressed: viewModel.rowsLoading
                  ? null
                  : () => viewModel.loadSourcePage(0),
              icon: const Icon(Icons.table_chart_outlined),
              label: Text(_copy(context, '逐页阅读', 'Read pages', '페이지 읽기')),
            ),
            if (page != null)
              Text(
                _copy(
                  context,
                  '第 ${page.rows.isEmpty ? 0 : page.offset + 1}–${page.offset + page.rows.length} 条 / 共 ${page.total} 条',
                  '${page.rows.isEmpty ? 0 : page.offset + 1}–${page.offset + page.rows.length} of ${page.total}',
                  '${page.rows.isEmpty ? 0 : page.offset + 1}–${page.offset + page.rows.length} / ${page.total}개',
                ),
              ),
          ],
        ),
        if (viewModel.rowsLoading) const LinearProgressIndicator(minHeight: 2),
        if (viewModel.rowsFailed)
          Text(
            _copy(
              context,
              '此页暂时无法读取。请重新打开资料后重试。',
              'This page is unavailable. Reopen the material and try again.',
              '페이지를 읽을 수 없습니다. 자료를 다시 열어 시도하세요.',
            ),
          ),
        if (page != null) ...[
          ConstrainedBox(
            constraints: const BoxConstraints(maxHeight: 460),
            child: ListView.separated(
              key: ValueKey(
                '${viewModel.openedImport?.artifactId}:${page.offset}',
              ),
              shrinkWrap: true,
              itemCount: page.rows.length,
              separatorBuilder: (_, _) => const Divider(height: 28),
              itemBuilder: (context, index) {
                final row = page.rows[index];
                final location = row.locator;
                final label = [
                  if (location['sheet_name'] is String) location['sheet_name'],
                  if (location['row_index'] is int)
                    _copy(
                      context,
                      '第 ${location['row_index']} 行',
                      'Row ${location['row_index']}',
                      '${location['row_index']}행',
                    ),
                  if (location['page_index'] is int)
                    _copy(
                      context,
                      '第 ${location['page_index']} 页',
                      'Page ${location['page_index']}',
                      '${location['page_index']}페이지',
                    ),
                ].join(' · ');
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text(
                      label.isEmpty ? '${row.index + 1}' : label,
                      style: TextStyle(color: LumenisTheme.of(context).muted),
                    ),
                    const SizedBox(height: 8),
                    for (var column = 0; column < row.fields.length; column++)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            SizedBox(
                              width: 110,
                              child: Text(
                                row.fields[column].key.isEmpty
                                    ? _copy(
                                        context,
                                        '第 ${column + 1} 列',
                                        'Column ${column + 1}',
                                        '${column + 1}열',
                                      )
                                    : row.fields[column].key,
                              ),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: SelectableText(row.fields[column].value),
                            ),
                          ],
                        ),
                      ),
                    if (row.fields.isEmpty) SelectableText(row.text),
                  ],
                );
              },
            ),
          ),
          Row(
            children: [
              TextButton(
                onPressed: page.offset == 0 || viewModel.rowsLoading
                    ? null
                    : () => viewModel.loadSourcePage(
                        math.max(0, page.offset - 50),
                      ),
                child: Text(_copy(context, '上一页', 'Previous', '이전')),
              ),
              TextButton(
                onPressed: !page.hasMore || viewModel.rowsLoading
                    ? null
                    : () => viewModel.loadSourcePage(
                        page.offset + page.rows.length,
                      ),
                child: Text(_copy(context, '下一页', 'Next', '다음')),
              ),
            ],
          ),
        ],
      ],
    );
  }
}

class _ScopeBanner extends StatelessWidget {
  const _ScopeBanner({required this.scope});

  final Sh02Scope scope;

  @override
  Widget build(BuildContext context) {
    final range = scope.isGlobal
        ? _copy(context, '全部范围', 'All scopes', '전체 범위')
        : '${_businessDomainLabel(context, scope.businessDomain)} · ${scope.displayName}';
    return Semantics(
      liveRegion: true,
      label: _copy(
        context,
        '当前查看范围：$range',
        'Current range: $range',
        '현재 범위: $range',
      ),
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(horizontal: 15, vertical: 12),
        decoration: BoxDecoration(
          color: LumenisTheme.of(context).shared.withValues(alpha: 0.08),
          border: Border.all(
            color: LumenisTheme.of(context).shared.withValues(alpha: 0.35),
          ),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Row(
          children: [
            LumenisIcon(
              Icons.filter_alt_outlined,
              color: LumenisTheme.of(context).shared,
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
              _copy(context, '已确认查看范围', 'Verified viewing range', '확인된 조회 범위'),
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

class _SearchRail extends StatelessWidget {
  const _SearchRail({
    required this.viewModel,
    required this.queryController,
    required this.focusNode,
  });

  final Sh02ViewModel viewModel;
  final TextEditingController queryController;
  final FocusNode focusNode;

  @override
  Widget build(BuildContext context) => _Panel(
    title: _copy(context, '检索资料', 'Search material', '자료 검색'),
    detail: _copy(
      context,
      '仅在已确认范围内筛选。',
      'Filters stay inside the verified range.',
      '확인된 범위 안에서만 필터링합니다.',
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        TextField(
          key: const Key('sh02-search'),
          controller: queryController,
          focusNode: focusNode,
          onChanged: viewModel.setQuery,
          textInputAction: TextInputAction.search,
          decoration: InputDecoration(
            labelText: _copy(
              context,
              '搜索摘要或来源',
              'Search summary or source',
              '요약 또는 출처 검색',
            ),
            prefixIcon: const LumenisIcon(Icons.search_rounded),
            border: const OutlineInputBorder(),
          ),
        ),
        const SizedBox(height: 15),
        Text(
          _copy(context, '资料类型', 'Material type', '자료 유형'),
          style: TextStyle(color: LumenisTheme.of(context).quiet, fontSize: 12),
        ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 7,
          runSpacing: 7,
          children: [
            _FilterChip(
              label: _copy(context, '全部', 'All', '전체'),
              selected: viewModel.kindFilter == null,
              onSelected: (_) => viewModel.setKindFilter(null),
            ),
            for (final kind in const [
              Sh02EvidenceKind.metric,
              Sh02EvidenceKind.source,
              Sh02EvidenceKind.finding,
              Sh02EvidenceKind.risk,
              Sh02EvidenceKind.caseItem,
            ])
              _FilterChip(
                label: _kindLabel(context, kind),
                selected: viewModel.kindFilter == kind,
                onSelected: (_) => viewModel.setKindFilter(kind),
              ),
          ],
        ),
      ],
    ),
  );
}

class _BrowseStage extends StatelessWidget {
  const _BrowseStage({
    required this.viewModel,
    required this.mode,
    required this.camera,
    required this.focusNodes,
    required this.onModeChanged,
    required this.onOpenItem,
    required this.onZoom,
  });

  final Sh02ViewModel viewModel;
  final _BrowseMode mode;
  final TransformationController camera;
  final Map<String, FocusNode> focusNodes;
  final ValueChanged<_BrowseMode> onModeChanged;
  final ValueChanged<Sh02Evidence> onOpenItem;
  final void Function(double factor, Size viewport) onZoom;

  @override
  Widget build(BuildContext context) {
    final reduceMotion = MediaQuery.maybeOf(context)?.disableAnimations == true;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _BrowseModeSelector(mode: mode, onChanged: onModeChanged),
        const SizedBox(height: 12),
        AnimatedSize(
          duration: reduceMotion
              ? Duration.zero
              : const Duration(milliseconds: 160),
          curve: Curves.easeOutCubic,
          alignment: Alignment.topCenter,
          child: mode == _BrowseMode.list
              ? _EvidenceList(
                  viewModel: viewModel,
                  focusNodes: focusNodes,
                  onOpenItem: onOpenItem,
                )
              : _SpatialDesk(
                  viewModel: viewModel,
                  camera: camera,
                  focusNodes: focusNodes,
                  onOpenItem: onOpenItem,
                  onZoom: onZoom,
                ),
        ),
      ],
    );
  }
}

class _BrowseModeSelector extends StatelessWidget {
  const _BrowseModeSelector({required this.mode, required this.onChanged});

  final _BrowseMode mode;
  final ValueChanged<_BrowseMode> onChanged;

  @override
  Widget build(BuildContext context) => Align(
    alignment: Alignment.centerLeft,
    child: SegmentedButton<_BrowseMode>(
      key: const Key('sh02-view-mode'),
      showSelectedIcon: false,
      segments: [
        ButtonSegment(
          value: _BrowseMode.list,
          icon: const LumenisIcon(Icons.view_list_rounded),
          label: Text(_copy(context, '列表', 'List', '목록')),
        ),
        ButtonSegment(
          value: _BrowseMode.space,
          icon: const LumenisIcon(Icons.space_dashboard_outlined),
          label: Text(_copy(context, '空间', 'Space', '공간')),
        ),
      ],
      selected: {mode},
      onSelectionChanged: (selection) {
        if (selection.isNotEmpty) onChanged(selection.first);
      },
      style: ButtonStyle(
        minimumSize: const WidgetStatePropertyAll(Size(0, 48)),
        shape: WidgetStatePropertyAll(
          RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
        ),
      ),
    ),
  );
}

class _SpatialDesk extends StatelessWidget {
  const _SpatialDesk({
    required this.viewModel,
    required this.camera,
    required this.focusNodes,
    required this.onOpenItem,
    required this.onZoom,
  });

  final Sh02ViewModel viewModel;
  final TransformationController camera;
  final Map<String, FocusNode> focusNodes;
  final ValueChanged<Sh02Evidence> onOpenItem;
  final void Function(double factor, Size viewport) onZoom;

  @override
  Widget build(BuildContext context) {
    final items = viewModel.visibleEvidence;
    return LayoutBuilder(
      builder: (context, constraints) {
        final compact = constraints.maxWidth < 600;
        final viewportHeight = compact ? 470.0 : 570.0;
        final boardWidth =
            (compact
                    ? math.max(340.0, constraints.maxWidth - 12)
                    : math.max(760.0, constraints.maxWidth + 100))
                .toDouble();
        final columns = compact ? 1 : 2;
        final cardWidth =
            (compact
                    ? math.max(260.0, boardWidth - 52)
                    : (boardWidth - 104) / columns)
                .toDouble();
        final rows = math.max(1, (items.length / columns).ceil()).toDouble();
        final boardHeight = math.max(520.0, 74.0 + rows * 236.0).toDouble();
        return _Panel(
          title: _copy(context, '资料空间', 'Material space', '자료 공간'),
          detail: _copy(
            context,
            '拖动浏览，缩放定位；打开资料可查看来源链路。',
            'Pan to explore and zoom to focus. Open material to inspect its source trail.',
            '드래그로 탐색하고 확대해 보세요. 자료를 열면 출처 흐름을 확인합니다.',
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Wrap(
                alignment: WrapAlignment.start,
                crossAxisAlignment: WrapCrossAlignment.center,
                spacing: 8,
                runSpacing: 4,
                children: [
                  _ZoomButton(
                    key: const Key('sh02-space-zoom-out'),
                    tooltip: _copy(context, '缩小', 'Zoom out', '축소'),
                    icon: Icons.remove_rounded,
                    onPressed: () => onZoom(
                      1 / 1.2,
                      Size(constraints.maxWidth, viewportHeight),
                    ),
                  ),
                  ValueListenableBuilder<Matrix4>(
                    valueListenable: camera,
                    builder: (context, matrix, _) => SizedBox(
                      width: 58,
                      child: Center(
                        child: Text(
                          '${(matrix.getMaxScaleOnAxis() * 100).round()}%',
                          style: TextStyle(
                            color: LumenisTheme.of(context).quiet,
                            fontSize: 11,
                          ),
                        ),
                      ),
                    ),
                  ),
                  _ZoomButton(
                    key: const Key('sh02-space-zoom-in'),
                    tooltip: _copy(context, '放大', 'Zoom in', '확대'),
                    icon: Icons.add_rounded,
                    onPressed: () =>
                        onZoom(1.2, Size(constraints.maxWidth, viewportHeight)),
                  ),
                  TextButton.icon(
                    key: const Key('sh02-space-reset'),
                    onPressed: () => camera.value = Matrix4.identity(),
                    icon: const LumenisIcon(Icons.center_focus_strong_rounded),
                    label: Text(_copy(context, '重置视图', 'Reset view', '보기 초기화')),
                    style: TextButton.styleFrom(
                      minimumSize: const Size(48, 48),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              ClipRRect(
                borderRadius: BorderRadius.circular(12),
                child: SizedBox(
                  height: viewportHeight,
                  child: DecoratedBox(
                    decoration: BoxDecoration(
                      color: LumenisTheme.of(context).canvas,
                      border: Border.all(color: LumenisTheme.of(context).line),
                    ),
                    child: items.isEmpty
                        ? Padding(
                            padding: const EdgeInsets.all(14),
                            child: _InfoMessage(
                              _copy(
                                context,
                                '当前范围没有匹配的已核实资料。',
                                'No verified material matches this range.',
                                '현재 범위에 일치하는 확인된 자료가 없습니다.',
                              ),
                            ),
                          )
                        : InteractiveViewer(
                            key: const Key('sh02-space-viewport'),
                            transformationController: camera,
                            constrained: false,
                            minScale: 0.5,
                            maxScale: 2.25,
                            boundaryMargin: const EdgeInsets.all(1200),
                            clipBehavior: Clip.hardEdge,
                            child: CustomPaint(
                              size: Size(boardWidth, boardHeight),
                              painter: _DeskGridPainter(
                                palette: LumenisTheme.of(context),
                              ),
                              child: SizedBox(
                                width: boardWidth,
                                height: boardHeight,
                                child: Stack(
                                  children: [
                                    for (
                                      var index = 0;
                                      index < items.length;
                                      index++
                                    )
                                      Positioned(
                                        left:
                                            26.0 +
                                            (index % columns) *
                                                (cardWidth + 28),
                                        top: 28.0 + (index ~/ columns) * 236.0,
                                        child: _SpaceMaterial(
                                          key: Key(
                                            'sh02-space-item-${items[index].internalId}',
                                          ),
                                          item: items[index],
                                          width: cardWidth,
                                          focusNode:
                                              focusNodes[items[index]
                                                  .internalId]!,
                                          selected:
                                              viewModel.selected?.internalId ==
                                              items[index].internalId,
                                          onTap: () => onOpenItem(items[index]),
                                        ),
                                      ),
                                  ],
                                ),
                              ),
                            ),
                          ),
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _ZoomButton extends StatelessWidget {
  const _ZoomButton({
    required this.tooltip,
    required this.icon,
    required this.onPressed,
    super.key,
  });

  final String tooltip;
  final IconData icon;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) => Tooltip(
    message: tooltip,
    child: IconButton(
      onPressed: onPressed,
      icon: Icon(icon),
      constraints: const BoxConstraints.tightFor(width: 48, height: 48),
    ),
  );
}

class _SpaceMaterial extends StatelessWidget {
  const _SpaceMaterial({
    required this.item,
    required this.width,
    required this.focusNode,
    required this.selected,
    required this.onTap,
    super.key,
  });

  final Sh02Evidence item;
  final double width;
  final FocusNode focusNode;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Semantics(
    button: true,
    selected: selected,
    label: _copy(
      context,
      '${_kindLabel(context, item.kind)}：${item.summary}，${item.source.isEmpty ? '来源未提供' : item.source}',
      '${_kindLabel(context, item.kind)}: ${item.summary}, ${item.source.isEmpty ? 'Source not provided' : item.source}',
      '${_kindLabel(context, item.kind)}: ${item.summary}, ${item.source.isEmpty ? '출처 정보 없음' : item.source}',
    ),
    child: Material(
      color: LumenisTheme.of(context).surface,
      elevation: selected ? 5 : 2,
      shadowColor: LumenisTheme.of(context).shared.withValues(alpha: 0.16),
      borderRadius: BorderRadius.circular(16),
      child: InkWell(
        canRequestFocus: true,
        focusNode: focusNode,
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Container(
          width: width,
          height: 218,
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            border: Border.all(
              color: selected
                  ? LumenisTheme.of(context).shared.withValues(alpha: 0.7)
                  : LumenisTheme.of(context).line,
              width: selected ? 1.5 : 1,
            ),
            borderRadius: BorderRadius.circular(16),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  _KindMark(kind: item.kind),
                  const SizedBox(width: 9),
                  Expanded(
                    child: Text(
                      _kindLabel(context, item.kind),
                      style: TextStyle(
                        color: LumenisTheme.of(context).shared,
                        fontWeight: FontWeight.w600,
                        fontSize: 12,
                      ),
                    ),
                  ),
                  LumenisIcon(
                    Icons.open_in_full_rounded,
                    size: 16,
                    color: LumenisTheme.of(context).quiet,
                  ),
                ],
              ),
              const SizedBox(height: 13),
              Text(
                item.summary,
                maxLines: 3,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  fontWeight: FontWeight.w600,
                  height: 1.4,
                ),
              ),
              const Spacer(),
              const SizedBox(height: 12),
              Divider(height: 1, color: LumenisTheme.of(context).line),
              const SizedBox(height: 9),
              Wrap(
                spacing: 10,
                runSpacing: 5,
                children: [
                  if (item.source.isNotEmpty)
                    Text(
                      item.source,
                      style: TextStyle(
                        color: LumenisTheme.of(context).muted,
                        fontSize: 11,
                      ),
                    ),
                  if (item.capturedAt.isNotEmpty)
                    Text(
                      item.capturedAt,
                      style: TextStyle(
                        color: LumenisTheme.of(context).quiet,
                        fontSize: 11,
                      ),
                    ),
                  Text(
                    _freshnessLabel(context, item.freshness),
                    style: TextStyle(
                      color: LumenisTheme.of(context).quiet,
                      fontSize: 11,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    ),
  );
}

class _DeskGridPainter extends CustomPainter {
  const _DeskGridPainter({required this.palette});

  final LumenisPalette palette;

  @override
  void paint(Canvas canvas, Size size) {
    final minor = Paint()
      ..color = palette.line.withValues(alpha: 0.4)
      ..strokeWidth = 0.65;
    final major = Paint()
      ..color = palette.shared.withValues(alpha: 0.12)
      ..strokeWidth = 1;
    for (var x = 0.0; x <= size.width; x += 32) {
      canvas.drawLine(
        Offset(x, 0),
        Offset(x, size.height),
        x % 160 == 0 ? major : minor,
      );
    }
    for (var y = 0.0; y <= size.height; y += 32) {
      canvas.drawLine(
        Offset(0, y),
        Offset(size.width, y),
        y % 160 == 0 ? major : minor,
      );
    }
  }

  @override
  bool shouldRepaint(covariant _DeskGridPainter oldDelegate) =>
      oldDelegate.palette != palette;
}

class _FocusedMaterial extends StatelessWidget {
  const _FocusedMaterial({
    required this.item,
    required this.returnLabel,
    required this.onReturn,
  });

  final Sh02Evidence? item;
  final String returnLabel;
  final VoidCallback onReturn;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      Align(
        alignment: Alignment.centerLeft,
        child: OutlinedButton.icon(
          key: const Key('sh02-focus-return'),
          onPressed: onReturn,
          icon: const LumenisIcon(Icons.arrow_back_rounded),
          label: Text(returnLabel),
          style: OutlinedButton.styleFrom(minimumSize: const Size(48, 48)),
        ),
      ),
      const SizedBox(height: 12),
      if (item == null)
        _Panel(
          title: _copy(
            context,
            '资料已不在当前结果中',
            'Material no longer in results',
            '자료가 현재 결과에 없습니다',
          ),
          child: _InfoMessage(
            _copy(
              context,
              '当前筛选条件下无法显示这条资料。返回浏览以继续查找。',
              'This material is outside the current filter. Return to browsing to continue.',
              '현재 필터에서 이 자료를 찾을 수 없습니다. 돌아가서 계속 탐색하세요.',
            ),
          ),
        )
      else
        _TraceInspector(item: item!),
    ],
  );
}

class _EvidenceList extends StatelessWidget {
  const _EvidenceList({
    required this.viewModel,
    required this.focusNodes,
    required this.onOpenItem,
  });

  final Sh02ViewModel viewModel;
  final Map<String, FocusNode> focusNodes;
  final ValueChanged<Sh02Evidence> onOpenItem;

  @override
  Widget build(BuildContext context) {
    final items = viewModel.visibleEvidence;
    return _Panel(
      title: _copy(context, '已核实资料', 'Verified material', '확인된 자료'),
      detail: _copy(
        context,
        '${items.length} 条结果，点击一条查看来源链路。',
        '${items.length} results. Select one to inspect its source trail.',
        '${items.length}개 결과. 선택하면 출처 흐름을 확인합니다.',
      ),
      child: items.isEmpty
          ? _InfoMessage(
              _copy(
                context,
                '当前范围没有匹配的已核实资料。',
                'No verified material matches this range.',
                '현재 범위에 일치하는 확인된 자료가 없습니다.',
              ),
            )
          : Column(
              children: [
                for (final item in items)
                  _EvidenceRow(
                    key: Key('sh02-item-${item.internalId}'),
                    item: item,
                    focusNode: focusNodes[item.internalId]!,
                    selected: viewModel.selected?.internalId == item.internalId,
                    onTap: () => onOpenItem(item),
                  ),
              ],
            ),
    );
  }
}

class _EvidenceRow extends StatelessWidget {
  const _EvidenceRow({
    required this.item,
    required this.focusNode,
    required this.selected,
    required this.onTap,
    super.key,
  });

  final Sh02Evidence item;
  final FocusNode focusNode;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 8),
    child: Material(
      color: selected
          ? LumenisTheme.of(context).shared.withValues(alpha: 0.1)
          : LumenisTheme.of(context).surfaceRaised,
      borderRadius: BorderRadius.circular(11),
      child: InkWell(
        canRequestFocus: true,
        focusNode: focusNode,
        onTap: onTap,
        borderRadius: BorderRadius.circular(11),
        child: Container(
          constraints: const BoxConstraints(minHeight: 76),
          padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 11),
          decoration: BoxDecoration(
            border: Border.all(
              color: selected
                  ? LumenisTheme.of(context).shared.withValues(alpha: 0.55)
                  : LumenisTheme.of(context).line,
            ),
            borderRadius: BorderRadius.circular(11),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _KindMark(kind: item.kind),
              const SizedBox(width: 11),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      item.summary,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontWeight: FontWeight.w600),
                    ),
                    const SizedBox(height: 7),
                    Wrap(
                      spacing: 9,
                      runSpacing: 4,
                      children: [
                        Text(
                          _kindLabel(context, item.kind),
                          style: TextStyle(
                            color: LumenisTheme.of(context).shared,
                            fontSize: 11,
                          ),
                        ),
                        if (item.source.isNotEmpty)
                          Text(
                            item.source,
                            style: TextStyle(
                              color: LumenisTheme.of(context).muted,
                              fontSize: 11,
                            ),
                          ),
                        if (item.capturedAt.isNotEmpty)
                          Text(
                            item.capturedAt,
                            style: TextStyle(
                              color: LumenisTheme.of(context).quiet,
                              fontSize: 11,
                            ),
                          ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              Icon(
                selected
                    ? Icons.chevron_right_rounded
                    : Icons.open_in_new_rounded,
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

class _TraceInspector extends StatelessWidget {
  const _TraceInspector({required this.item});

  final Sh02Evidence? item;

  @override
  Widget build(BuildContext context) {
    final selected = item;
    return _Panel(
      title: _copy(context, '来源链路', 'Source trail', '출처 흐름'),
      detail: _copy(
        context,
        '原始来源与摘录相邻显示。',
        'The original source and extract stay together.',
        '원본과 발췌 내용을 함께 표시합니다.',
      ),
      child: selected == null
          ? _InfoMessage(
              _copy(
                context,
                '选择一条资料查看链路。',
                'Select material to inspect its trail.',
                '자료를 선택해 흐름을 확인하세요.',
              ),
            )
          : Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _DetailLine(
                  label: _copy(context, '类型', 'Type', '유형'),
                  value: _kindLabel(context, selected.kind),
                ),
                _DetailLine(
                  label: _copy(context, '摘录', 'Extract', '발췌'),
                  value: selected.summary,
                ),
                _DetailLine(
                  label: _copy(context, '来源', 'Source', '출처'),
                  value: selected.source.isEmpty
                      ? _copy(
                          context,
                          '来源未提供',
                          'Source not provided',
                          '출처 정보 없음',
                        )
                      : selected.source,
                ),
                _DetailLine(
                  label: _copy(context, '新鲜度', 'Freshness', '최신성'),
                  value: _freshnessLabel(context, selected.freshness),
                ),
                if (selected.capturedAt.isNotEmpty)
                  _DetailLine(
                    label: _copy(context, '记录时间', 'Recorded', '기록 시간'),
                    value: selected.capturedAt,
                  ),
                const SizedBox(height: 5),
                Text(
                  _copy(context, '链路', 'Lineage', '계보'),
                  style: TextStyle(
                    color: LumenisTheme.of(context).quiet,
                    fontSize: 11,
                  ),
                ),
                const SizedBox(height: 7),
                Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  children: selected.lineage.isEmpty
                      ? [
                          _MetaChip(
                            _copy(
                              context,
                              '链路未完整',
                              'Lineage incomplete',
                              '계보 불완전',
                            ),
                          ),
                        ]
                      : [
                          for (final step in selected.lineage)
                            _MetaChip(_lineageLabel(context, step)),
                        ],
                ),
                if (selected.origin.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  _DetailLine(
                    label: _copy(context, '归属流程', 'Owning workflow', '원래 흐름'),
                    value: selected.origin,
                  ),
                ],
                const SizedBox(height: 12),
                Text(
                  _copy(
                    context,
                    '此处只允许查看，不会修改资料或替你提交动作。',
                    'This view is read-only; it does not change material or submit an action for you.',
                    '이 화면은 읽기 전용이며 자료를 변경하거나 작업을 대신 제출하지 않습니다.',
                  ),
                  style: TextStyle(
                    color: LumenisTheme.of(context).quiet,
                    fontSize: 11,
                    height: 1.45,
                  ),
                ),
              ],
            ),
    );
  }
}

class _LoadingState extends StatelessWidget {
  @override
  Widget build(BuildContext context) => Semantics(
    liveRegion: true,
    label: _copy(
      context,
      '正在读取已核实资料',
      'Reading verified material',
      '확인된 자료를 읽는 중',
    ),
    child: const Center(child: CircularProgressIndicator()),
  );
}

class _BlockedState extends StatelessWidget {
  const _BlockedState({required this.error, required this.onRetry});

  final Sh02ScopeErrorKind? error;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => _StateMessage(
    eyebrow: _copy(context, '查看范围', 'VIEWING RANGE', '조회 범위'),
    title: _copy(
      context,
      '资料暂不显示',
      'Material is hidden for now',
      '자료를 현재 표시하지 않습니다',
    ),
    detail: switch (error) {
      Sh02ScopeErrorKind.denied => _copy(
        context,
        '当前账号没有这个范围的查看权限。',
        'This account cannot view the selected range.',
        '이 계정은 선택한 범위를 볼 수 없습니다.',
      ),
      Sh02ScopeErrorKind.malformed => _copy(
        context,
        '服务返回的查看范围不完整，因此不会显示资料。',
        'The returned viewing range is incomplete, so material is not shown.',
        '반환된 조회 범위가 불완전하여 자료를 표시하지 않습니다.',
      ),
      _ => _copy(
        context,
        '尚未确认账号与业务范围的对应关系，因此不会显示资料。',
        'The account and business range have not been verified, so material is not shown.',
        '계정과 업무 범위가 확인되지 않아 자료를 표시하지 않습니다.',
      ),
    },
    actionLabel: _copy(context, '重新读取', 'Read again', '다시 읽기'),
    onAction: onRetry,
  );
}

class _FailureState extends StatelessWidget {
  const _FailureState({required this.kind, required this.onRetry});

  final Sh02FailureKind kind;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => _StateMessage(
    eyebrow: _copy(context, '资料库', 'MATERIAL LIBRARY', '자료 라이브러리'),
    title: _copy(
      context,
      '资料库暂不可用',
      'Material library unavailable',
      '자료 라이브러리를 사용할 수 없습니다',
    ),
    detail: switch (kind) {
      Sh02FailureKind.authentication => _copy(
        context,
        '当前内容暂时无法打开。可重试读取，或返回后稍后再试。',
        'This content cannot be opened right now. You can retry reading it or return and try again later.',
        '현재 콘텐츠를 지금 열 수 없습니다. 다시 읽기를 시도하거나 돌아간 뒤 나중에 다시 시도할 수 있습니다.',
      ),
      Sh02FailureKind.permissionDenied => _copy(
        context,
        '当前内容不可访问。',
        'This content is not accessible.',
        '현재 콘텐츠에 접근할 수 없습니다.',
      ),
      Sh02FailureKind.offline => _copy(
        context,
        '资料库服务暂时无法连接，请检查连接后重试。',
        'The library cannot connect right now. Check the connection and try again.',
        '라이브러리에 연결할 수 없습니다. 연결을 확인하고 다시 시도하세요.',
      ),
      Sh02FailureKind.response => _copy(
        context,
        '资料库没有返回可验证的数据，请稍后重试。',
        'The library did not return verifiable data. Try again later.',
        '라이브러리가 확인 가능한 데이터를 반환하지 않았습니다. 나중에 다시 시도하세요.',
      ),
    },
    actionLabel: _copy(context, '重新读取', 'Read again', '다시 읽기'),
    onAction: onRetry,
  );
}

class _StateMessage extends StatelessWidget {
  const _StateMessage({
    required this.eyebrow,
    required this.title,
    required this.detail,
    required this.actionLabel,
    required this.onAction,
  });

  final String eyebrow;
  final String title;
  final String detail;
  final String actionLabel;
  final VoidCallback onAction;

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
              _Eyebrow(eyebrow),
              const SizedBox(height: 11),
              Text(
                detail,
                style: TextStyle(
                  color: LumenisTheme.of(context).muted,
                  height: 1.5,
                ),
              ),
              const SizedBox(height: 18),
              OutlinedButton(onPressed: onAction, child: Text(actionLabel)),
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

class _KindMark extends StatelessWidget {
  const _KindMark({required this.kind});

  final Sh02EvidenceKind kind;

  @override
  Widget build(BuildContext context) => Container(
    width: 32,
    height: 32,
    alignment: Alignment.center,
    decoration: BoxDecoration(
      color: LumenisTheme.of(context).canvas,
      borderRadius: BorderRadius.circular(9),
    ),
    child: LumenisIcon(
      switch (kind) {
        Sh02EvidenceKind.metric => Icons.query_stats_rounded,
        Sh02EvidenceKind.source => Icons.link_rounded,
        Sh02EvidenceKind.finding => Icons.lightbulb_outline_rounded,
        Sh02EvidenceKind.risk => Icons.warning_amber_rounded,
        Sh02EvidenceKind.caseItem => Icons.folder_open_outlined,
        Sh02EvidenceKind.other => Icons.description_outlined,
      },
      size: 18,
      color: LumenisTheme.of(context).shared,
    ),
  );
}

class _FilterChip extends StatelessWidget {
  const _FilterChip({
    required this.label,
    required this.selected,
    required this.onSelected,
  });

  final String label;
  final bool selected;
  final ValueChanged<bool> onSelected;

  @override
  Widget build(BuildContext context) => FilterChip(
    label: Text(label),
    selected: selected,
    onSelected: onSelected,
    materialTapTargetSize: MaterialTapTargetSize.padded,
  );
}

class _MetaChip extends StatelessWidget {
  const _MetaChip(this.label);

  final String label;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
    decoration: BoxDecoration(
      color: LumenisTheme.of(context).canvas,
      borderRadius: BorderRadius.circular(7),
    ),
    child: Text(
      label,
      style: TextStyle(color: LumenisTheme.of(context).muted, fontSize: 11),
    ),
  );
}

class _DetailLine extends StatelessWidget {
  const _DetailLine({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 11),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: TextStyle(color: LumenisTheme.of(context).quiet, fontSize: 11),
        ),
        const SizedBox(height: 3),
        Text(value, style: const TextStyle(height: 1.4)),
      ],
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
      color: LumenisTheme.of(context).shared,
      fontSize: 10,
      letterSpacing: 1.1,
      fontWeight: FontWeight.w700,
    ),
  );
}

String _kindLabel(BuildContext context, Sh02EvidenceKind kind) =>
    switch (kind) {
      Sh02EvidenceKind.metric => _copy(context, '指标', 'Metric', '지표'),
      Sh02EvidenceKind.source => _copy(context, '来源', 'Source', '출처'),
      Sh02EvidenceKind.finding => _copy(context, '发现', 'Finding', '발견'),
      Sh02EvidenceKind.risk => _copy(context, '风险', 'Risk', '위험'),
      Sh02EvidenceKind.caseItem => _copy(context, '案例', 'Case', '사례'),
      Sh02EvidenceKind.other => _copy(context, '资料', 'Material', '자료'),
    };

String _businessDomainLabel(BuildContext context, String domain) =>
    switch (domain) {
      '商业运营' => _copy(context, '商业运营', 'Commerce', '상거래 운영'),
      '品牌市场' => _copy(context, '品牌市场', 'Brand & market', '브랜드·시장'),
      _ => _copy(context, '全部范围', 'All scopes', '전체 범위'),
    };

String _freshnessLabel(BuildContext context, String freshness) =>
    switch (freshness) {
      '已确认新鲜' => _copy(context, '已确认新鲜', 'Freshness confirmed', '최신성 확인됨'),
      '已标记为过期' => _copy(context, '已标记为过期', 'Marked stale', '오래된 자료로 표시됨'),
      '尚未采集' => _copy(context, '尚未采集', 'Not collected', '아직 수집되지 않음'),
      '暂时离线' => _copy(context, '暂时离线', 'Temporarily offline', '일시적으로 오프라인'),
      _ => _copy(context, '新鲜度未确认', 'Freshness unconfirmed', '최신성 미확인'),
    };

String _lineageLabel(BuildContext context, String step) => switch (step) {
  '来源' => _copy(context, '来源', 'Source', '출처'),
  '资料依据' => _copy(context, '资料依据', 'Evidence', '근거 자료'),
  '正式记录' => _copy(context, '正式记录', 'Canonical record', '정식 기록'),
  '指标' => _copy(context, '指标', 'Metric', '지표'),
  '事件' => _copy(context, '事件', 'Event', '이벤트'),
  _ => _copy(context, '未知链路', 'Unrecognized trail', '확인되지 않은 흐름'),
};

String _copy(BuildContext context, String zh, String en, String ko) =>
    switch (context.lumenisL10n.locale.languageCode) {
      'en' => en,
      'ko' => ko,
      _ => zh,
    };

String _materialLimitation(BuildContext context, String value) =>
    switch (value) {
      'Counts describe this uploaded document only.' => _copy(
        context,
        '统计范围为这份资料。',
        'Counts cover this document.',
        '이 자료의 통계입니다.',
      ),
      'Excerpts are source text, not verified facts or model summaries.' =>
        _copy(
          context,
          '摘录来自原文；内容真实性尚未核实。',
          'Extracts quote the original; factual accuracy is unverified.',
          '발췌는 원문이며 사실 여부는 확인되지 않았습니다.',
        ),
      'Authorship, rights and external redistribution are not established.' =>
        _copy(
          context,
          '作者及转载许可尚未确认。',
          'Authorship and redistribution permission are unconfirmed.',
          '저자와 재배포 허가는 확인되지 않았습니다.',
        ),
      _ => value,
    };
