import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../../core/lumenis_core_client.dart';
import '../../../l10n/lumenis_localizations.dart';
import '../../../core/lumenis_theme.dart';
import 'cth09_repository.dart';
import 'cth09_view_model.dart';

class Cth09Screen extends StatefulWidget {
  const Cth09Screen({required this.client, this.repository, super.key});

  final LumenisCoreClient client;
  final Cth09Repository? repository;

  @override
  State<Cth09Screen> createState() => _Cth09ScreenState();
}

class _Cth09ScreenState extends State<Cth09Screen> {
  late Cth09ViewModel _viewModel = _createViewModel()..load();

  Cth09ViewModel _createViewModel() => Cth09ViewModel(
    repository: widget.repository ?? CoreCth09Repository(client: widget.client),
  );

  @override
  void didUpdateWidget(covariant Cth09Screen oldWidget) {
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
  Widget build(BuildContext context) => ColoredBox(
    color: LumenisTheme.of(context).canvas,
    child: SafeArea(
      child: AnimatedBuilder(
        animation: _viewModel,
        builder: (context, _) {
          final copy = context.lumenisL10n;
          return switch (_viewModel.phase) {
            Cth09LoadPhase.loading => _LoadingState(copy: copy),
            Cth09LoadPhase.blocked => _BlockedState(
              copy: copy,
              onRetry: _viewModel.load,
            ),
            Cth09LoadPhase.failed => _FailureState(
              copy: copy,
              kind: _viewModel.failureKind,
              onRetry: _viewModel.load,
            ),
            Cth09LoadPhase.empty ||
            Cth09LoadPhase.notCollected ||
            Cth09LoadPhase.partial ||
            Cth09LoadPhase.ready => _Cth09Workspace(
              copy: copy,
              phase: _viewModel.phase,
              data: _viewModel.data!,
              selectedRisk: _viewModel.selectedRisk,
              selectedDecision: _viewModel.selectedDecision,
              onSelectRisk: _viewModel.selectRisk,
              onSelectDecision: _viewModel.selectDecision,
              onReturn: _viewModel.clearSelection,
              onRetry: _viewModel.load,
            ),
          };
        },
      ),
    ),
  );
}

String _cth09RiskLabel(LumenisLocalizations l10n, String level) {
  final key = switch (level.toLowerCase()) {
    'critical' => 'cth09.risk.critical',
    'high' => 'cth09.risk.high',
    'medium' => 'cth09.risk.medium',
    'low' => 'cth09.risk.low',
    _ => 'cth09.risk.pending',
  };
  return l10n.text(key);
}

String _cth09DecisionStatusLabel(LumenisLocalizations l10n, String status) {
  final key = switch (status.toLowerCase()) {
    'proposed' => 'cth09.decision.state.proposed',
    'pending' => 'cth09.decision.state.pending',
    'approved' => 'cth09.decision.state.approved',
    'blocked' => 'cth09.decision.state.blocked',
    _ => 'cth09.decision.state.unknown',
  };
  return l10n.text(key);
}

class _LoadingState extends StatelessWidget {
  const _LoadingState({required this.copy});

  final LumenisLocalizations copy;

  @override
  Widget build(BuildContext context) => Center(
    child: Semantics(
      liveRegion: true,
      label: copy.text('cth09.loading'),
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
    title: copy.text('cth09.blocked.title'),
    detail: copy.text('cth09.blocked.detail'),
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
  final Cth09FailureKind? kind;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => _MessageState(
    copy: copy,
    title: copy.text('cth09.error.generic'),
    detail: switch (kind) {
      Cth09FailureKind.authentication ||
      Cth09FailureKind.permissionDenied => copy.text('cth09.error.auth'),
      _ => copy.text('cth09.error.generic'),
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
                Text(copy.text('cth09.eyebrow'), style: _eyebrowStyle(context)),
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
                  label: copy.text('cth09.action.retry'),
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

class _Cth09Workspace extends StatelessWidget {
  const _Cth09Workspace({
    required this.copy,
    required this.phase,
    required this.data,
    required this.selectedRisk,
    required this.selectedDecision,
    required this.onSelectRisk,
    required this.onSelectDecision,
    required this.onReturn,
    required this.onRetry,
  });

  final LumenisLocalizations copy;
  final Cth09LoadPhase phase;
  final Cth09WorkbenchData data;
  final Cth09Risk? selectedRisk;
  final Cth09Decision? selectedDecision;
  final ValueChanged<String> onSelectRisk;
  final ValueChanged<String> onSelectDecision;
  final VoidCallback onReturn;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, constraints) {
      final desktop = constraints.maxWidth >= 1120;
      final inset = constraints.maxWidth < 480
          ? 18.0
          : constraints.maxWidth < 1000
          ? 26.0
          : 38.0;
      return Focus(
        onKeyEvent: (node, event) {
          if (event is KeyDownEvent &&
              event.logicalKey == LogicalKeyboardKey.escape &&
              (selectedRisk != null || selectedDecision != null)) {
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
                  _ScopeBanner(copy: copy, data: data),
                  const SizedBox(height: 22),
                  if (phase == Cth09LoadPhase.empty ||
                      phase == Cth09LoadPhase.notCollected)
                    _InlineNotice(
                      key: const ValueKey('cth09/content-state'),
                      text: phase == Cth09LoadPhase.empty
                          ? copy.text('cth09.state.empty')
                          : copy.text('cth09.state.not_collected'),
                      caution: phase == Cth09LoadPhase.notCollected,
                    ),
                  if (phase == Cth09LoadPhase.partial)
                    _InlineNotice(
                      key: const ValueKey('cth09/partial-state'),
                      text: copy.text('cth09.state.partial'),
                      caution: true,
                    ),
                  if (desktop)
                    Row(
                      key: const ValueKey('cth09/desktop-layout'),
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Expanded(
                          flex: 6,
                          child: _RiskRegister(
                            copy: copy,
                            risks: data.risks,
                            selectedRisk: selectedRisk,
                            onSelectRisk: onSelectRisk,
                          ),
                        ),
                        const SizedBox(width: 24),
                        Expanded(
                          flex: 5,
                          child: _DecisionLedger(
                            copy: copy,
                            decisions: data.decisions,
                            selectedDecision: selectedDecision,
                            onSelectDecision: onSelectDecision,
                          ),
                        ),
                      ],
                    )
                  else
                    Column(
                      key: ValueKey(
                        constraints.maxWidth >= 760
                            ? 'cth09/tablet-layout'
                            : 'cth09/mobile-layout',
                      ),
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        _RiskRegister(
                          copy: copy,
                          risks: data.risks,
                          selectedRisk: selectedRisk,
                          onSelectRisk: onSelectRisk,
                        ),
                        const SizedBox(height: 20),
                        _RiskInspector(
                          copy: copy,
                          risk: selectedRisk,
                          onReturn: onReturn,
                        ),
                        const SizedBox(height: 20),
                        _DecisionLedger(
                          copy: copy,
                          decisions: data.decisions,
                          selectedDecision: selectedDecision,
                          onSelectDecision: onSelectDecision,
                        ),
                      ],
                    ),
                  if (desktop) ...[
                    const SizedBox(height: 20),
                    _RiskInspector(
                      copy: copy,
                      risk: selectedRisk,
                      onReturn: onReturn,
                    ),
                  ],
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
            Text(copy.text('cth09.eyebrow'), style: _eyebrowStyle(context)),
            const SizedBox(height: 9),
            Text(
              copy.text('cth09.title'),
              style: TextStyle(
                color: LumenisTheme.of(context).foreground,
                fontSize: 28,
                height: 1.2,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 9),
            Text(
              copy.text('cth09.summary'),
              style: TextStyle(
                color: LumenisTheme.of(context).muted,
                height: 1.5,
              ),
            ),
          ],
        ),
      ),
      IconButton(
        tooltip: copy.text('cth09.action.retry'),
        onPressed: onRetry,
        icon: const Icon(Icons.refresh_rounded),
      ),
    ],
  );
}

class _ScopeBanner extends StatelessWidget {
  const _ScopeBanner({required this.copy, required this.data});

  final LumenisLocalizations copy;
  final Cth09WorkbenchData data;

  @override
  Widget build(BuildContext context) {
    final label = data.context.mode == Cth09ContextMode.globalAll
        ? copy.text('cth09.scope.global_all')
        : data.context.displayName ?? copy.text('cth09.scope.focused');
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
              copy.text('cth09.title'),
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

class _RiskRegister extends StatelessWidget {
  const _RiskRegister({
    required this.copy,
    required this.risks,
    required this.selectedRisk,
    required this.onSelectRisk,
  });

  final LumenisLocalizations copy;
  final List<Cth09Risk> risks;
  final Cth09Risk? selectedRisk;
  final ValueChanged<String> onSelectRisk;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      _SectionHeading(title: copy.text('cth09.risks.heading')),
      const SizedBox(height: 12),
      if (risks.isEmpty)
        _EmptyPanel(text: copy.text('cth09.risk.none'))
      else
        ...risks.map(
          (item) => Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: _RiskRow(
              copy: copy,
              risk: item,
              selected: selectedRisk?.id == item.id,
              onTap: () => onSelectRisk(item.id),
            ),
          ),
        ),
    ],
  );
}

class _RiskRow extends StatelessWidget {
  const _RiskRow({
    required this.copy,
    required this.risk,
    required this.selected,
    required this.onTap,
  });

  final LumenisLocalizations copy;
  final Cth09Risk risk;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final label = [
      risk.title,
      _cth09RiskLabel(copy, risk.level),
      if (risk.score != null) _formatScore(risk.score!),
    ].join(' · ');
    final color = _levelColor(context, risk.level);
    return Semantics(
      button: true,
      selected: selected,
      label: label,
      child: Material(
        color: selected
            ? LumenisTheme.of(context).surfaceRaised
            : LumenisTheme.of(context).surface,
        child: InkWell(
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: 4,
                  height: 62,
                  margin: const EdgeInsets.only(right: 12),
                  color: color,
                ),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Expanded(
                            child: Text(
                              risk.title,
                              style: TextStyle(
                                color: LumenisTheme.of(context).foreground,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ),
                          Text(
                            _cth09RiskLabel(copy, risk.level),
                            style: TextStyle(color: color, fontSize: 12),
                          ),
                        ],
                      ),
                      if (risk.summary.isNotEmpty) ...[
                        const SizedBox(height: 6),
                        Text(
                          risk.summary,
                          maxLines: 3,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            color: LumenisTheme.of(context).muted,
                            height: 1.4,
                          ),
                        ),
                      ],
                      const SizedBox(height: 9),
                      Row(
                        children: [
                          Expanded(
                            child: _ScoreTrack(score: risk.score, color: color),
                          ),
                          const SizedBox(width: 12),
                          if (risk.score != null)
                            Text(
                              _formatScore(risk.score!),
                              style: TextStyle(
                                color: LumenisTheme.of(context).foreground,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                        ],
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

  static String _formatScore(num value) => value == value.roundToDouble()
      ? value.toInt().toString()
      : value.toStringAsFixed(1);
}

class _ScoreTrack extends StatelessWidget {
  const _ScoreTrack({required this.score, required this.color});

  final num? score;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final ratio = score == null
        ? 0.0
        : (score!.toDouble() / 100).clamp(0.0, 1.0);
    return ClipRRect(
      borderRadius: BorderRadius.circular(3),
      child: LinearProgressIndicator(
        minHeight: 5,
        value: ratio,
        backgroundColor: LumenisTheme.of(context).line,
        valueColor: AlwaysStoppedAnimation<Color>(color),
      ),
    );
  }
}

class _DecisionLedger extends StatelessWidget {
  const _DecisionLedger({
    required this.copy,
    required this.decisions,
    required this.selectedDecision,
    required this.onSelectDecision,
  });

  final LumenisLocalizations copy;
  final List<Cth09Decision> decisions;
  final Cth09Decision? selectedDecision;
  final ValueChanged<String> onSelectDecision;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      _SectionHeading(title: copy.text('cth09.decisions.heading')),
      const SizedBox(height: 12),
      if (decisions.isEmpty)
        _EmptyPanel(text: copy.text('cth09.decision.none'))
      else
        ...decisions.map(
          (item) => Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: _DecisionRow(
              copy: copy,
              decision: item,
              selected: selectedDecision?.id == item.id,
              onSelect: () => onSelectDecision(item.id),
            ),
          ),
        ),
    ],
  );
}

class _DecisionRow extends StatelessWidget {
  const _DecisionRow({
    required this.copy,
    required this.decision,
    required this.selected,
    required this.onSelect,
  });

  final LumenisLocalizations copy;
  final Cth09Decision decision;
  final bool selected;
  final VoidCallback onSelect;

  @override
  Widget build(BuildContext context) => DecoratedBox(
    decoration: BoxDecoration(
      color: selected
          ? LumenisTheme.of(context).surfaceRaised
          : LumenisTheme.of(context).surface,
      border: Border(top: BorderSide(color: LumenisTheme.of(context).line)),
    ),
    child: Padding(
      padding: const EdgeInsets.all(14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          InkWell(
            onTap: onSelect,
            child: Semantics(
              button: true,
              selected: selected,
              label: [
                decision.title,
                if (decision.owner.isNotEmpty) decision.owner,
                _cth09DecisionStatusLabel(copy, decision.status),
              ].join(' · '),
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
                          decision.title,
                          style: TextStyle(
                            color: LumenisTheme.of(context).foreground,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        const SizedBox(height: 5),
                        Text(
                          [
                            if (decision.owner.isNotEmpty) decision.owner,
                            _cth09DecisionStatusLabel(copy, decision.status),
                          ].join(' · '),
                          style: TextStyle(
                            color: LumenisTheme.of(context).muted,
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
          const SizedBox(height: 12),
          Text(
            decision.actionLabel,
            style: TextStyle(
              color: LumenisTheme.of(context).muted,
              height: 1.4,
            ),
          ),
          const SizedBox(height: 10),
          Tooltip(
            message: copy.text('cth09.action.unavailable'),
            child: Semantics(
              button: true,
              enabled: false,
              label:
                  '${decision.actionLabel} · ${copy.text('cth09.action.unavailable')}',
              child: OutlinedButton.icon(
                onPressed: null,
                icon: const Icon(Icons.lock_outline_rounded, size: 17),
                label: Text(copy.text('cth09.action.unavailable')),
              ),
            ),
          ),
          const SizedBox(height: 9),
          Text(
            copy.text('cth09.action.unavailable_detail'),
            style: TextStyle(
              color: LumenisTheme.of(context).caution,
              fontSize: 12,
            ),
          ),
          const SizedBox(height: 8),
          _EvidenceTrace(copy: copy, evidence: decision.evidence),
        ],
      ),
    ),
  );
}

class _RiskInspector extends StatelessWidget {
  const _RiskInspector({
    required this.copy,
    required this.risk,
    required this.onReturn,
  });

  final LumenisLocalizations copy;
  final Cth09Risk? risk;
  final VoidCallback onReturn;

  @override
  Widget build(BuildContext context) {
    final item = risk;
    if (item == null) {
      return _InspectorFrame(
        title: copy.text('cth09.basis'),
        child: _EmptyPanel(text: copy.text('cth09.risk.none')),
      );
    }
    return _InspectorFrame(
      title: copy.text('cth09.basis'),
      trailing: _TextButton(
        label: copy.text('cth09.action.clear_selection'),
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
          if (item.score != null) ...[
            const SizedBox(height: 12),
            Text(
              [
                _cth09RiskLabel(copy, item.level),
                _RiskRow._formatScore(item.score!),
              ].join(' · '),
              style: TextStyle(color: _levelColor(context, item.level)),
            ),
          ],
          const SizedBox(height: 15),
          _EvidenceTrace(copy: copy, evidence: item.evidence),
        ],
      ),
    );
  }
}

class _EvidenceTrace extends StatelessWidget {
  const _EvidenceTrace({required this.copy, required this.evidence});

  final LumenisLocalizations copy;
  final List<Cth09EvidenceReference> evidence;

  @override
  Widget build(BuildContext context) {
    if (evidence.isEmpty) {
      return Text(
        copy.text('cth09.source.none'),
        style: TextStyle(color: LumenisTheme.of(context).quiet),
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          copy.text('cth09.basis'),
          style: TextStyle(
            color: LumenisTheme.of(context).cth,
            fontSize: 12,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 5),
        ...evidence.map(
          (item) => Text(
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
      ],
    );
  }
}

class _InspectorFrame extends StatelessWidget {
  const _InspectorFrame({
    required this.title,
    required this.child,
    this.trailing,
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

Color _levelColor(BuildContext context, String level) =>
    switch (level.toLowerCase()) {
      'critical' => LumenisTheme.of(context).danger,
      'high' => LumenisTheme.of(context).caution,
      'medium' => LumenisTheme.of(context).cth,
      _ => LumenisTheme.of(context).quiet,
    };
