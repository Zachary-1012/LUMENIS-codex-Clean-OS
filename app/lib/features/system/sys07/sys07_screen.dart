import 'package:flutter/material.dart';

import '../../../core/lumenis_core_client.dart';
import '../../../core/lumenis_theme.dart';
import '../sys02/sys_system_foundation.dart';
import 'sys07_repository.dart';
import 'sys07_snapshot.dart';
import 'sys07_view_model.dart';

class Sys07Screen extends StatefulWidget {
  const Sys07Screen({required this.client, this.repository, super.key});

  final LumenisCoreClient client;
  final Sys07Repository? repository;

  @override
  State<Sys07Screen> createState() => _Sys07ScreenState();
}

class _Sys07ScreenState extends State<Sys07Screen> {
  late final Sys07ViewModel _viewModel;

  @override
  void initState() {
    super.initState();
    _viewModel = Sys07ViewModel(
      repository:
          widget.repository ?? CoreSys07Repository(client: widget.client),
    )..refresh();
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
          builder: (context, _) => switch (_viewModel.phase) {
            SysLoadPhase.loading => const SysLoadingView(
              titleKey: 'sys.common.loading',
            ),
            SysLoadPhase.failed => SysFailureView(
              kind: _viewModel.failureKind!,
              onRetry: _viewModel.refresh,
            ),
            SysLoadPhase.ready => _EvaluationContent(
              snapshot: _viewModel.snapshot!,
              onRefresh: _viewModel.refresh,
            ),
          },
        ),
      ),
    );
  }
}

class _EvaluationContent extends StatelessWidget {
  const _EvaluationContent({required this.snapshot, required this.onRefresh});

  final Sys07Snapshot snapshot;
  final VoidCallback onRefresh;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final width = constraints.maxWidth;
        final mobile = width < 768;
        final desktop = width >= 1100;
        final horizontalPadding = width < 480
            ? 18.0
            : width < 900
            ? 26.0
            : 38.0;
        String copy(String key) => SysSystemCopy.text(context, key);
        final header = SysPageHeader(
          eyebrow: copy('sys07.eyebrow'),
          title: copy('sys07.title'),
          subtitle: copy('sys07.subtitle'),
          onRefresh: onRefresh,
        );
        final posture = SysPanel(
          title: copy('sys07.posture.title'),
          child: _Posture(snapshot: snapshot),
        );
        final gates = SysPanel(
          title: copy('sys07.gates.title'),
          detail: copy('sys07.gates.detail'),
          child: _GateList(gates: snapshot.gates),
        );
        final checks = SysPanel(
          title: copy('sys07.checks.title'),
          child: _CheckList(checks: snapshot.checks),
        );
        final main = desktop
            ? Row(
                key: const ValueKey('sys07/layout-desktop'),
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(flex: 4, child: posture),
                  const SizedBox(width: 18),
                  Expanded(
                    flex: 8,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [gates, const SizedBox(height: 14), checks],
                    ),
                  ),
                ],
              )
            : Column(
                key: ValueKey(
                  mobile ? 'sys07/layout-mobile' : 'sys07/layout-tablet',
                ),
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  posture,
                  const SizedBox(height: 14),
                  gates,
                  const SizedBox(height: 14),
                  checks,
                ],
              );
        return Align(
          alignment: Alignment.topCenter,
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1660),
            child: SingleChildScrollView(
              padding: EdgeInsets.fromLTRB(
                horizontalPadding,
                26,
                horizontalPadding,
                48,
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [header, const SizedBox(height: 24), main],
              ),
            ),
          ),
        );
      },
    );
  }
}

class _Posture extends StatelessWidget {
  const _Posture({required this.snapshot});

  final Sys07Snapshot snapshot;

  @override
  Widget build(BuildContext context) {
    String copy(String key) => SysSystemCopy.text(context, key);
    final state = snapshot.hasCompleteGateEvidence ? 'ready' : 'unknown';
    final label = snapshot.hasCompleteGateEvidence
        ? copy('sys07.posture.ready')
        : copy('sys07.posture.unknown');
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SysStatusBadge(state: state, label: label),
        const SizedBox(height: 18),
        _CountRow(
          label: copy('sys07.field.check'),
          value: snapshot.owaspCheckCount,
        ),
        const Divider(height: 26),
        _CountRow(label: copy('sys07.skills'), value: snapshot.skillCount),
        const SizedBox(height: 18),
        Text(
          copy('sys07.notPass'),
          style: TextStyle(
            color: LumenisTheme.of(context).caution,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 8),
        Text(
          copy('sys07.source'),
          style: TextStyle(color: LumenisTheme.of(context).quiet, height: 1.45),
        ),
      ],
    );
  }
}

class _CountRow extends StatelessWidget {
  const _CountRow({required this.label, required this.value});

  final String label;
  final int? value;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: Text(
            label,
            style: TextStyle(color: LumenisTheme.of(context).muted),
          ),
        ),
        Text(
          value?.toString() ??
              SysSystemCopy.text(context, 'sys.common.unavailable'),
          style: TextStyle(
            color: LumenisTheme.of(context).system,
            fontSize: 24,
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }
}

class _GateList extends StatelessWidget {
  const _GateList({required this.gates});

  final List<Sys07Gate> gates;

  @override
  Widget build(BuildContext context) {
    String copy(String key) => SysSystemCopy.text(context, key);
    if (gates.isEmpty) {
      return Text(
        copy('sys07.gates.empty'),
        style: TextStyle(color: LumenisTheme.of(context).muted, height: 1.5),
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (var index = 0; index < gates.length; index++) ...[
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Text(
                  gates[index].name,
                  style: TextStyle(
                    color: LumenisTheme.of(context).foreground,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
              SysStatusBadge(
                state: gates[index].state,
                label: gates[index].evidence == '—'
                    ? copy('sys.common.unknown')
                    : gates[index].state,
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            gates[index].evidence == '—'
                ? copy('sys.common.notReturned')
                : gates[index].evidence,
            style: TextStyle(
              color: LumenisTheme.of(context).quiet,
              height: 1.4,
            ),
          ),
          if (index < gates.length - 1) const Divider(height: 24),
        ],
      ],
    );
  }
}

class _CheckList extends StatelessWidget {
  const _CheckList({required this.checks});

  final List<Sys07Check> checks;

  @override
  Widget build(BuildContext context) {
    String copy(String key) => SysSystemCopy.text(context, key);
    if (checks.isEmpty) {
      return Text(
        copy('sys07.checks.empty'),
        style: TextStyle(color: LumenisTheme.of(context).muted, height: 1.5),
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (var index = 0; index < checks.length; index++) ...[
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Text(
                  checks[index].name,
                  style: TextStyle(color: LumenisTheme.of(context).foreground),
                ),
              ),
              SysStatusBadge(
                state: checks[index].state,
                label: checks[index].state,
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            checks[index].evidence == '—'
                ? copy('sys.common.notReturned')
                : checks[index].evidence,
            style: TextStyle(
              color: LumenisTheme.of(context).quiet,
              height: 1.4,
            ),
          ),
          if (index < checks.length - 1) const Divider(height: 24),
        ],
      ],
    );
  }
}
