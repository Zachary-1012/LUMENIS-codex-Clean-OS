import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../../core/lumenis_core_client.dart';
import '../../../core/lumenis_theme.dart';
import '../../../l10n/lumenis_localizations.dart';
import 'sh02_repository.dart';
import 'sh02_snapshot.dart';
import 'sh02_view_model.dart';

class Sh02Screen extends StatefulWidget {
  const Sh02Screen({required this.client, this.repository, super.key});

  final LumenisCoreClient client;
  final Sh02Repository? repository;

  @override
  State<Sh02Screen> createState() => _Sh02ScreenState();
}

class _Sh02ScreenState extends State<Sh02Screen> {
  late final Sh02ViewModel _viewModel = Sh02ViewModel(
    repository: widget.repository ?? CoreSh02Repository(client: widget.client),
  );

  @override
  void initState() {
    super.initState();
    _viewModel.refresh();
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
          Sh02LoadPhase.loading => _LoadingState(),
          Sh02LoadPhase.blocked => _BlockedState(
            error: _viewModel.scopeError,
            onRetry: _viewModel.refresh,
          ),
          Sh02LoadPhase.failed => _FailureState(
            kind: _viewModel.failureKind!,
            onRetry: _viewModel.refresh,
          ),
          Sh02LoadPhase.ready => _Workspace(viewModel: _viewModel),
        },
      ),
    ),
  );
}

enum _BrowseMode { list, space }

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
                _Header(),
                const SizedBox(height: 18),
                _ScopeBanner(scope: snapshot.scope),
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
                      icon: const Icon(Icons.refresh_rounded),
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

class _Header extends StatelessWidget {
  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      _Eyebrow(_copy(context, '共享资料', 'SHARED MATERIAL', '공유 자료')),
      const SizedBox(height: 9),
      Text(
        context.lumenisL10n.text('screen.SH-02'),
        style: Theme.of(context).textTheme.headlineMedium?.copyWith(
          color: LumenisTheme.of(context).foreground,
          fontWeight: FontWeight.w600,
        ),
      ),
      const SizedBox(height: 6),
      Text(
        _copy(
          context,
          '按来源、时间和链路查找已核实的业务资料，并把原始来源与摘录放在同一处。',
          'Find verified business material by source, time and lineage, with the original source beside its extract.',
          '출처·시간·계보별로 확인된 업무 자료를 찾고 원본과 발췌 내용을 함께 확인합니다.',
        ),
        style: TextStyle(color: LumenisTheme.of(context).muted, height: 1.45),
      ),
    ],
  );
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
            Icon(
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
            prefixIcon: const Icon(Icons.search_rounded),
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
          icon: const Icon(Icons.view_list_rounded),
          label: Text(_copy(context, '列表', 'List', '목록')),
        ),
        ButtonSegment(
          value: _BrowseMode.space,
          icon: const Icon(Icons.space_dashboard_outlined),
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
                    icon: const Icon(Icons.center_focus_strong_rounded),
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
                  Icon(
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
          icon: const Icon(Icons.arrow_back_rounded),
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
    child: Icon(
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
