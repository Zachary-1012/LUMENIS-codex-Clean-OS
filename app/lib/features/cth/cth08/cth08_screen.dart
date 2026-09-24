import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../../core/lumenis_core_client.dart';
import '../../../l10n/lumenis_localizations.dart';
import '../../../core/lumenis_theme.dart';
import 'cth08_repository.dart';
import 'cth08_view_model.dart';

class Cth08Screen extends StatefulWidget {
  const Cth08Screen({required this.client, this.repository, super.key});

  final LumenisCoreClient client;
  final Cth08Repository? repository;

  @override
  State<Cth08Screen> createState() => _Cth08ScreenState();
}

class _Cth08ScreenState extends State<Cth08Screen> {
  late Cth08ViewModel _viewModel = _createViewModel()..load();

  Cth08ViewModel _createViewModel() => Cth08ViewModel(
    repository: widget.repository ?? CoreCth08Repository(client: widget.client),
  );

  @override
  void didUpdateWidget(covariant Cth08Screen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.client != widget.client ||
        oldWidget.repository != widget.repository) {
      _viewModel.dispose();
      _viewModel = _createViewModel()..load();
    }
  }

  @override
  void dispose() {
    _viewModel.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return ColoredBox(
      color: LumenisTheme.of(context).canvas,
      child: SafeArea(
        child: AnimatedBuilder(
          animation: _viewModel,
          builder: (context, _) {
            final copy = context.lumenisL10n;
            return switch (_viewModel.phase) {
              Cth08LoadPhase.loading => _LoadingState(copy: copy),
              Cth08LoadPhase.blocked => _BlockedState(
                copy: copy,
                onRetry: _viewModel.load,
              ),
              Cth08LoadPhase.failed => _FailureState(
                copy: copy,
                kind: _viewModel.failureKind,
                onRetry: _viewModel.load,
              ),
              Cth08LoadPhase.empty ||
              Cth08LoadPhase.notCollected ||
              Cth08LoadPhase.partial ||
              Cth08LoadPhase.ready => _Cth08Workspace(
                copy: copy,
                phase: _viewModel.phase,
                data: _viewModel.data!,
                selectedCase: _viewModel.selectedCase,
                onSelectCase: _viewModel.selectCase,
                onReturn: _viewModel.clearSelection,
                onRetry: _viewModel.load,
              ),
            };
          },
        ),
      ),
    );
  }
}

String _cth08StateLabel(LumenisLocalizations l10n, String state) {
  final key = switch (state.toLowerCase()) {
    'open' => 'cth08.state.open',
    'in_review' => 'cth08.state.in_review',
    'closed' => 'cth08.state.closed',
    'archived' => 'cth08.state.archived',
    _ => 'cth08.state.pending',
  };
  return l10n.text(key);
}

String _cth08RiskLabel(LumenisLocalizations l10n, String risk) {
  final key = switch (risk.toLowerCase()) {
    'critical' => 'cth08.risk.critical',
    'high' => 'cth08.risk.high',
    'medium' => 'cth08.risk.medium',
    'low' => 'cth08.risk.low',
    _ => 'cth08.risk.pending',
  };
  return l10n.text(key);
}

String _cth08TimelineStateLabel(
  LumenisLocalizations l10n,
  Cth08TimelineState state,
) => l10n.text(switch (state) {
  Cth08TimelineState.done => 'cth08.timeline.state.done',
  Cth08TimelineState.current => 'cth08.timeline.state.current',
  Cth08TimelineState.pending => 'cth08.timeline.state.pending',
  Cth08TimelineState.blocked => 'cth08.timeline.state.blocked',
});

class _LoadingState extends StatelessWidget {
  const _LoadingState({required this.copy});

  final LumenisLocalizations copy;

  @override
  Widget build(BuildContext context) => Center(
    child: Semantics(
      liveRegion: true,
      label: copy.text('cth08.loading'),
      child: const CircularProgressIndicator(),
    ),
  );
}

class _BlockedState extends StatelessWidget {
  const _BlockedState({required this.copy, required this.onRetry});

  final LumenisLocalizations copy;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => _MessageState(
    copy: copy,
    title: copy.text('cth08.blocked.title'),
    detail: copy.text('cth08.blocked.detail'),
    onRetry: onRetry,
  );
}

class _FailureState extends StatelessWidget {
  const _FailureState({
    required this.copy,
    required this.kind,
    required this.onRetry,
  });

  final LumenisLocalizations copy;
  final Cth08FailureKind? kind;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => _MessageState(
    copy: copy,
    title: copy.text('cth08.error.generic'),
    detail: switch (kind) {
      Cth08FailureKind.authentication ||
      Cth08FailureKind.permissionDenied => copy.text('cth08.error.auth'),
      _ => copy.text('cth08.error.generic'),
    },
    onRetry: onRetry,
  );
}

class _MessageState extends StatelessWidget {
  const _MessageState({
    required this.copy,
    required this.title,
    required this.detail,
    required this.onRetry,
  });

  final LumenisLocalizations copy;
  final String title;
  final String detail;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, constraints) => Align(
      alignment: Alignment.topCenter,
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 720),
        child: Padding(
          padding: EdgeInsets.all(constraints.maxWidth < 480 ? 22 : 34),
          child: Semantics(
            liveRegion: true,
            label: '$title $detail',
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(copy.text('cth08.eyebrow'), style: _eyebrowStyle(context)),
                const SizedBox(height: 12),
                Text(
                  title,
                  style: TextStyle(
                    color: LumenisTheme.of(context).foreground,
                    fontSize: 26,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  detail,
                  style: TextStyle(
                    color: LumenisTheme.of(context).muted,
                    height: 1.55,
                  ),
                ),
                const SizedBox(height: 22),
                _TextButton(
                  label: copy.text('cth08.action.retry'),
                  onPressed: onRetry,
                ),
              ],
            ),
          ),
        ),
      ),
    ),
  );
}

class _Cth08Workspace extends StatelessWidget {
  const _Cth08Workspace({
    required this.copy,
    required this.phase,
    required this.data,
    required this.selectedCase,
    required this.onSelectCase,
    required this.onReturn,
    required this.onRetry,
  });

  final LumenisLocalizations copy;
  final Cth08LoadPhase phase;
  final Cth08WorkspaceData data;
  final Cth08Case? selectedCase;
  final ValueChanged<String> onSelectCase;
  final VoidCallback onReturn;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, constraints) {
      final width = constraints.maxWidth;
      final desktop = width >= 1120;
      final tablet = width >= 760 && !desktop;
      final inset = width < 480
          ? 18.0
          : width < 1000
          ? 26.0
          : 38.0;
      final banner = _ScopeBanner(copy: copy, data: data);

      return Focus(
        onKeyEvent: (node, event) {
          if (event is KeyDownEvent &&
              event.logicalKey == LogicalKeyboardKey.escape &&
              selectedCase != null) {
            onReturn();
            return KeyEventResult.handled;
          }
          return KeyEventResult.ignored;
        },
        child: Align(
          alignment: Alignment.topCenter,
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1580),
            child: SingleChildScrollView(
              padding: EdgeInsets.fromLTRB(inset, 26, inset, 46),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _PageHeader(copy: copy, onRetry: onRetry),
                  const SizedBox(height: 18),
                  banner,
                  const SizedBox(height: 22),
                  if (phase == Cth08LoadPhase.empty ||
                      phase == Cth08LoadPhase.notCollected)
                    _InlineNotice(
                      key: const ValueKey('cth08/content-state'),
                      text: phase == Cth08LoadPhase.empty
                          ? copy.text('cth08.state.empty')
                          : copy.text('cth08.state.not_collected'),
                      caution: phase == Cth08LoadPhase.notCollected,
                    ),
                  if (phase == Cth08LoadPhase.partial)
                    _InlineNotice(
                      key: const ValueKey('cth08/partial-state'),
                      text: copy.text('cth08.state.partial'),
                      caution: true,
                    ),
                  if (desktop)
                    Row(
                      key: const ValueKey('cth08/desktop-layout'),
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Expanded(
                          flex: 7,
                          child: _CaseBoard(
                            copy: copy,
                            cases: data.cases,
                            selectedCase: selectedCase,
                            onSelectCase: onSelectCase,
                          ),
                        ),
                        const SizedBox(width: 24),
                        Expanded(
                          flex: 4,
                          child: _CaseInspector(
                            copy: copy,
                            selectedCase: selectedCase,
                            onReturn: onReturn,
                          ),
                        ),
                      ],
                    )
                  else
                    Column(
                      key: ValueKey(
                        tablet ? 'cth08/tablet-layout' : 'cth08/mobile-layout',
                      ),
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        _CaseBoard(
                          copy: copy,
                          cases: data.cases,
                          selectedCase: selectedCase,
                          onSelectCase: onSelectCase,
                        ),
                        const SizedBox(height: 20),
                        _CaseInspector(
                          copy: copy,
                          selectedCase: selectedCase,
                          onReturn: onReturn,
                        ),
                      ],
                    ),
                  const SizedBox(height: 28),
                  _KnowledgeShelf(copy: copy, items: data.knowledge),
                ],
              ),
            ),
          ),
        ),
      );
    },
  );
}

class _PageHeader extends StatelessWidget {
  const _PageHeader({required this.copy, required this.onRetry});

  final LumenisLocalizations copy;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => Wrap(
    alignment: WrapAlignment.spaceBetween,
    crossAxisAlignment: WrapCrossAlignment.center,
    runSpacing: 16,
    spacing: 18,
    children: [
      ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 780),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(copy.text('cth08.eyebrow'), style: _eyebrowStyle(context)),
            const SizedBox(height: 9),
            Text(
              copy.text('cth08.title'),
              style: TextStyle(
                color: LumenisTheme.of(context).foreground,
                fontSize: 28,
                height: 1.2,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 9),
            Text(
              copy.text('cth08.summary'),
              style: TextStyle(
                color: LumenisTheme.of(context).muted,
                height: 1.5,
              ),
            ),
          ],
        ),
      ),
      Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Tooltip(
            message: copy.text('cth08.action.unavailable'),
            child: Semantics(
              button: true,
              enabled: false,
              label: copy.text('cth08.action.unavailable'),
              child: FilledButton.icon(
                onPressed: null,
                icon: const Icon(Icons.add_rounded),
                label: Text(copy.text('cth08.action.new_case')),
              ),
            ),
          ),
          const SizedBox(width: 8),
          IconButton(
            tooltip: copy.text('cth08.action.retry'),
            onPressed: onRetry,
            icon: const Icon(Icons.refresh_rounded),
          ),
        ],
      ),
    ],
  );
}

class _ScopeBanner extends StatelessWidget {
  const _ScopeBanner({required this.copy, required this.data});

  final LumenisLocalizations copy;
  final Cth08WorkspaceData data;

  @override
  Widget build(BuildContext context) {
    final label = data.context.mode == Cth08ContextMode.globalAll
        ? copy.text('cth08.scope.global_all')
        : data.context.displayName ?? copy.text('cth08.scope.focused');
    return Semantics(
      label: label,
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        decoration: BoxDecoration(
          border: Border(
            top: BorderSide(color: LumenisTheme.of(context).line),
            bottom: BorderSide(color: LumenisTheme.of(context).line),
          ),
        ),
        child: Row(
          children: [
            Icon(
              Icons.adjust_rounded,
              size: 17,
              color: LumenisTheme.of(context).cth,
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                label,
                style: TextStyle(
                  color: LumenisTheme.of(context).foreground,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
            Text(
              copy.text('cth08.title'),
              style: TextStyle(
                color: LumenisTheme.of(context).quiet,
                fontSize: 12,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _CaseBoard extends StatelessWidget {
  const _CaseBoard({
    required this.copy,
    required this.cases,
    required this.selectedCase,
    required this.onSelectCase,
  });

  final LumenisLocalizations copy;
  final List<Cth08Case> cases;
  final Cth08Case? selectedCase;
  final ValueChanged<String> onSelectCase;

  @override
  Widget build(BuildContext context) {
    final groups = <String, List<Cth08Case>>{
      'open': [],
      'in_review': [],
      'closed': [],
    };
    for (final item in cases) {
      final key = groups.containsKey(item.state.toLowerCase())
          ? item.state.toLowerCase()
          : 'open';
      groups[key]!.add(item);
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _SectionHeading(title: copy.text('cth08.cases.heading')),
        const SizedBox(height: 12),
        if (cases.isEmpty)
          _EmptyPanel(text: copy.text('cth08.state.empty'))
        else
          LayoutBuilder(
            builder: (context, constraints) {
              final columnWidth = constraints.maxWidth < 760
                  ? constraints.maxWidth
                  : (constraints.maxWidth - 24) / 3;
              return Wrap(
                spacing: 12,
                runSpacing: 12,
                children: groups.entries
                    .map(
                      (entry) => SizedBox(
                        width: columnWidth,
                        child: _CaseLane(
                          copy: copy,
                          state: entry.key,
                          cases: entry.value,
                          selectedCase: selectedCase,
                          onSelectCase: onSelectCase,
                        ),
                      ),
                    )
                    .toList(growable: false),
              );
            },
          ),
      ],
    );
  }
}

class _CaseLane extends StatelessWidget {
  const _CaseLane({
    required this.copy,
    required this.state,
    required this.cases,
    required this.selectedCase,
    required this.onSelectCase,
  });

  final LumenisLocalizations copy;
  final String state;
  final List<Cth08Case> cases;
  final Cth08Case? selectedCase;
  final ValueChanged<String> onSelectCase;

  @override
  Widget build(BuildContext context) => DecoratedBox(
    decoration: BoxDecoration(
      color: LumenisTheme.of(context).surface,
      border: Border(top: BorderSide(color: LumenisTheme.of(context).line)),
    ),
    child: Padding(
      padding: const EdgeInsets.fromLTRB(14, 14, 14, 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            _cth08StateLabel(copy, state),
            style: TextStyle(
              color: LumenisTheme.of(context).foreground,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 10),
          if (cases.isEmpty)
            Text(
              copy.text('cth08.timeline.none'),
              style: TextStyle(
                color: LumenisTheme.of(context).quiet,
                fontSize: 12,
              ),
            )
          else
            ...cases.map(
              (item) => Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: _CaseRow(
                  copy: copy,
                  item: item,
                  selected: selectedCase?.id == item.id,
                  onTap: () => onSelectCase(item.id),
                ),
              ),
            ),
        ],
      ),
    ),
  );
}

class _CaseRow extends StatelessWidget {
  const _CaseRow({
    required this.copy,
    required this.item,
    required this.selected,
    required this.onTap,
  });

  final LumenisLocalizations copy;
  final Cth08Case item;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final label = [
      item.title,
      _cth08StateLabel(copy, item.state),
      if (item.risk.isNotEmpty) _cth08RiskLabel(copy, item.risk),
    ].join(' · ');
    return Semantics(
      button: true,
      selected: selected,
      label: label,
      child: Material(
        color: selected
            ? LumenisTheme.of(context).surfaceRaised
            : LumenisTheme.of(context).canvas,
        child: InkWell(
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(
                  selected
                      ? Icons.radio_button_checked_rounded
                      : Icons.radio_button_unchecked_rounded,
                  size: 18,
                  color: LumenisTheme.of(context).cth,
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        item.title,
                        style: TextStyle(
                          color: LumenisTheme.of(context).foreground,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      if (item.summary.isNotEmpty) ...[
                        const SizedBox(height: 5),
                        Text(
                          item.summary,
                          maxLines: 3,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            color: LumenisTheme.of(context).muted,
                            height: 1.4,
                          ),
                        ),
                      ],
                      const SizedBox(height: 8),
                      Text(
                        [
                          _cth08StateLabel(copy, item.state),
                          if (item.risk.isNotEmpty)
                            _cth08RiskLabel(copy, item.risk),
                        ].join(' · '),
                        style: TextStyle(
                          color: LumenisTheme.of(context).caution,
                          fontSize: 12,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _CaseInspector extends StatelessWidget {
  const _CaseInspector({
    required this.copy,
    required this.selectedCase,
    required this.onReturn,
  });

  final LumenisLocalizations copy;
  final Cth08Case? selectedCase;
  final VoidCallback onReturn;

  @override
  Widget build(BuildContext context) {
    final item = selectedCase;
    if (item == null) {
      return _InspectorFrame(
        title: copy.text('cth08.timeline.heading'),
        child: _EmptyPanel(text: copy.text('cth08.timeline.none')),
      );
    }

    return _InspectorFrame(
      key: const ValueKey('cth08/case-inspector'),
      title: copy.text('cth08.timeline.heading'),
      trailing: _TextButton(
        label: copy.text('cth08.return'),
        onPressed: onReturn,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            item.title,
            style: TextStyle(
              color: LumenisTheme.of(context).foreground,
              fontSize: 19,
              fontWeight: FontWeight.w600,
            ),
          ),
          if (item.summary.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(
              item.summary,
              style: TextStyle(
                color: LumenisTheme.of(context).muted,
                height: 1.45,
              ),
            ),
          ],
          const SizedBox(height: 18),
          if (item.timeline.isEmpty)
            Text(
              copy.text('cth08.timeline.none'),
              style: TextStyle(color: LumenisTheme.of(context).quiet),
            )
          else
            ...item.timeline.map(
              (step) => _TimelineStep(copy: copy, step: step),
            ),
          const SizedBox(height: 16),
          _EvidenceTrace(copy: copy, evidence: item.evidence),
        ],
      ),
    );
  }
}

class _TimelineStep extends StatelessWidget {
  const _TimelineStep({required this.copy, required this.step});

  final LumenisLocalizations copy;
  final Cth08TimelineStep step;

  @override
  Widget build(BuildContext context) {
    final active = step.state == Cth08TimelineState.current;
    final markerColor = switch (step.state) {
      Cth08TimelineState.done => LumenisTheme.of(context).positive,
      Cth08TimelineState.current => LumenisTheme.of(context).cth,
      Cth08TimelineState.blocked => LumenisTheme.of(context).danger,
      Cth08TimelineState.pending => LumenisTheme.of(context).quiet,
    };
    return Semantics(
      label: [
        step.label,
        _cth08TimelineStateLabel(copy, step.state),
        if (step.occurredAt.isNotEmpty) step.occurredAt,
      ].join(' · '),
      child: Padding(
        padding: const EdgeInsets.only(bottom: 15),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 10,
              height: 10,
              margin: const EdgeInsets.only(top: 4, right: 12),
              decoration: BoxDecoration(
                color: markerColor,
                shape: BoxShape.circle,
              ),
            ),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          step.label,
                          style: TextStyle(
                            color: active
                                ? LumenisTheme.of(context).foreground
                                : LumenisTheme.of(context).muted,
                            fontWeight: active
                                ? FontWeight.w600
                                : FontWeight.w500,
                          ),
                        ),
                      ),
                      Text(
                        _cth08TimelineStateLabel(copy, step.state),
                        style: TextStyle(color: markerColor, fontSize: 12),
                      ),
                    ],
                  ),
                  if (step.detail.isNotEmpty) ...[
                    const SizedBox(height: 4),
                    Text(
                      step.detail,
                      style: TextStyle(
                        color: LumenisTheme.of(context).muted,
                        fontSize: 13,
                        height: 1.35,
                      ),
                    ),
                  ],
                  if (step.occurredAt.isNotEmpty) ...[
                    const SizedBox(height: 3),
                    Text(
                      step.occurredAt,
                      style: TextStyle(
                        color: LumenisTheme.of(context).quiet,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _KnowledgeShelf extends StatelessWidget {
  const _KnowledgeShelf({required this.copy, required this.items});

  final LumenisLocalizations copy;
  final List<Cth08KnowledgeItem> items;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      _SectionHeading(title: copy.text('cth08.knowledge.heading')),
      const SizedBox(height: 10),
      if (items.isEmpty)
        _EmptyPanel(text: copy.text('cth08.knowledge.none'))
      else
        LayoutBuilder(
          builder: (context, constraints) {
            final width = constraints.maxWidth >= 980
                ? (constraints.maxWidth - 24) / 3
                : constraints.maxWidth >= 620
                ? (constraints.maxWidth - 12) / 2
                : constraints.maxWidth;
            return Wrap(
              spacing: 12,
              runSpacing: 12,
              children: items
                  .map(
                    (item) => SizedBox(
                      width: width,
                      child: _KnowledgeItem(copy: copy, item: item),
                    ),
                  )
                  .toList(growable: false),
            );
          },
        ),
    ],
  );
}

class _KnowledgeItem extends StatelessWidget {
  const _KnowledgeItem({required this.copy, required this.item});

  final LumenisLocalizations copy;
  final Cth08KnowledgeItem item;

  @override
  Widget build(BuildContext context) => DecoratedBox(
    decoration: BoxDecoration(
      color: LumenisTheme.of(context).surface,
      border: Border(
        top: BorderSide(color: LumenisTheme.of(context).accentStrong),
      ),
    ),
    child: Padding(
      padding: const EdgeInsets.all(14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            item.title,
            style: TextStyle(
              color: LumenisTheme.of(context).foreground,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            item.summary.isEmpty
                ? copy.text('cth08.source.none')
                : item.summary,
            style: TextStyle(
              color: LumenisTheme.of(context).muted,
              height: 1.4,
            ),
          ),
          const SizedBox(height: 10),
          _EvidenceTrace(copy: copy, evidence: item.evidence),
        ],
      ),
    ),
  );
}

class _EvidenceTrace extends StatelessWidget {
  const _EvidenceTrace({required this.copy, required this.evidence});

  final LumenisLocalizations copy;
  final List<Cth08EvidenceReference> evidence;

  @override
  Widget build(BuildContext context) {
    if (evidence.isEmpty) {
      return Text(
        copy.text('cth08.source.none'),
        style: TextStyle(color: LumenisTheme.of(context).quiet),
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          copy.text('cth08.source.trail'),
          style: TextStyle(
            color: LumenisTheme.of(context).cth,
            fontSize: 12,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 6),
        ...evidence.map(
          (item) => Padding(
            padding: const EdgeInsets.only(bottom: 5),
            child: Semantics(
              label: [
                item.id,
                if (item.quote.isNotEmpty) item.quote,
                if (item.capturedAt.isNotEmpty) item.capturedAt,
              ].join(' · '),
              child: Text(
                [
                  item.id,
                  if (item.quote.isNotEmpty) item.quote,
                  if (item.capturedAt.isNotEmpty) item.capturedAt,
                ].join(' · '),
                style: TextStyle(
                  color: LumenisTheme.of(context).muted,
                  fontSize: 12,
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class _InspectorFrame extends StatelessWidget {
  const _InspectorFrame({
    required this.title,
    required this.child,
    this.trailing,
    super.key,
  });

  final String title;
  final Widget child;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) => DecoratedBox(
    decoration: BoxDecoration(
      border: Border(top: BorderSide(color: LumenisTheme.of(context).line)),
    ),
    child: Padding(
      padding: const EdgeInsets.fromLTRB(16, 14, 16, 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  title,
                  style: TextStyle(
                    color: LumenisTheme.of(context).foreground,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
              ?trailing,
            ],
          ),
          const SizedBox(height: 15),
          child,
        ],
      ),
    ),
  );
}

class _SectionHeading extends StatelessWidget {
  const _SectionHeading({required this.title});

  final String title;

  @override
  Widget build(BuildContext context) => Text(
    title,
    style: TextStyle(
      color: LumenisTheme.of(context).foreground,
      fontSize: 16,
      fontWeight: FontWeight.w600,
    ),
  );
}

class _EmptyPanel extends StatelessWidget {
  const _EmptyPanel({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    padding: const EdgeInsets.all(16),
    decoration: BoxDecoration(
      color: LumenisTheme.of(context).surface,
      border: Border(top: BorderSide(color: LumenisTheme.of(context).line)),
    ),
    child: Text(text, style: TextStyle(color: LumenisTheme.of(context).muted)),
  );
}

class _InlineNotice extends StatelessWidget {
  const _InlineNotice({required this.text, required this.caution, super.key});

  final String text;
  final bool caution;

  @override
  Widget build(BuildContext context) => Semantics(
    liveRegion: true,
    label: text,
    child: Padding(
      padding: const EdgeInsets.only(bottom: 18),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            caution ? Icons.info_outline_rounded : Icons.check_circle_outline,
            size: 18,
            color: caution
                ? LumenisTheme.of(context).caution
                : LumenisTheme.of(context).positive,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              text,
              style: TextStyle(
                color: caution
                    ? LumenisTheme.of(context).caution
                    : LumenisTheme.of(context).muted,
                height: 1.45,
              ),
            ),
          ),
        ],
      ),
    ),
  );
}

class _TextButton extends StatelessWidget {
  const _TextButton({required this.label, required this.onPressed});

  final String label;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) =>
      TextButton(onPressed: onPressed, child: Text(label));
}

TextStyle _eyebrowStyle(BuildContext context) => TextStyle(
  color: LumenisTheme.of(context).cth,
  fontSize: 12,
  fontWeight: FontWeight.w600,
  letterSpacing: 0.4,
);
