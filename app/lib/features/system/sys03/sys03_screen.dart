import 'package:flutter/material.dart';

import '../../../core/lumenis_icon.dart';

import '../../../core/lumenis_core_client.dart';
import '../../../core/lumenis_theme.dart';
import '../sys02/sys_system_foundation.dart';
import 'sys03_repository.dart';
import 'sys03_snapshot.dart';
import 'sys03_view_model.dart';

class Sys03Screen extends StatefulWidget {
  const Sys03Screen({required this.client, this.repository, super.key});

  final LumenisCoreClient client;
  final Sys03Repository? repository;

  @override
  State<Sys03Screen> createState() => _Sys03ScreenState();
}

class _Sys03ScreenState extends State<Sys03Screen> {
  late final Sys03ViewModel _viewModel;

  @override
  void initState() {
    super.initState();
    _viewModel = Sys03ViewModel(
      repository:
          widget.repository ?? CoreSys03Repository(client: widget.client),
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
            SysLoadPhase.ready => _DatabaseContent(
              snapshot: _viewModel.snapshot!,
              onRefresh: _viewModel.refresh,
            ),
          },
        ),
      ),
    );
  }
}

class _DatabaseContent extends StatelessWidget {
  const _DatabaseContent({required this.snapshot, required this.onRefresh});

  final Sys03Snapshot snapshot;
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
          eyebrow: copy('sys03.eyebrow'),
          title: copy('sys03.title'),
          subtitle: copy('sys03.subtitle'),
          onRefresh: onRefresh,
        );
        final validation = SysPanel(
          title: copy('sys03.validation.title'),
          detail: copy('sys03.validation.detail'),
          child: _ValidationSpine(snapshot: snapshot),
        );
        final chain = SysPanel(
          title: copy('sys03.chain.title'),
          child: _TruthChain(snapshot: snapshot),
        );
        final checks = SysPanel(
          title: copy('sys03.checks.title'),
          child: _ChecksTable(snapshot: snapshot),
        );
        final identity = SysPanel(
          title: copy('sys03.identity.title'),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _StateLine(
                label: copy('sys03.identity.state'),
                state: snapshot.identityState,
                value: snapshot.identityState == 'unknown'
                    ? copy('sys.common.notReturned')
                    : copy('sys.common.ready'),
              ),
              const SizedBox(height: 12),
              Text(
                copy('sys03.identity.detail'),
                style: TextStyle(
                  color: LumenisTheme.of(context).muted,
                  height: 1.45,
                ),
              ),
              const SizedBox(height: 12),
              Text(
                copy('sys03.boundary'),
                style: TextStyle(
                  color: LumenisTheme.of(context).quiet,
                  height: 1.45,
                ),
              ),
            ],
          ),
        );

        final desktopLayout = Column(
          key: const ValueKey('sys03/layout-desktop'),
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(flex: 5, child: validation),
                const SizedBox(width: 18),
                Expanded(flex: 7, child: chain),
              ],
            ),
            const SizedBox(height: 18),
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(flex: 7, child: checks),
                const SizedBox(width: 18),
                Expanded(flex: 5, child: identity),
              ],
            ),
          ],
        );
        final tabletLayout = Column(
          key: const ValueKey('sys03/layout-tablet'),
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            validation,
            const SizedBox(height: 14),
            chain,
            const SizedBox(height: 14),
            checks,
            const SizedBox(height: 14),
            identity,
          ],
        );
        final mobileLayout = Column(
          key: const ValueKey('sys03/layout-mobile'),
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            validation,
            const SizedBox(height: 14),
            chain,
            const SizedBox(height: 14),
            checks,
            const SizedBox(height: 14),
            identity,
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
                children: [
                  header,
                  const SizedBox(height: 24),
                  if (desktop)
                    desktopLayout
                  else if (mobile)
                    mobileLayout
                  else
                    tabletLayout,
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}

class _ValidationSpine extends StatelessWidget {
  const _ValidationSpine({required this.snapshot});

  final Sys03Snapshot snapshot;

  @override
  Widget build(BuildContext context) {
    String copy(String key) => SysSystemCopy.text(context, key);
    final rows = [
      _StateLine(
        label: copy('sys03.validation.schema'),
        state: snapshot.schemaState,
        value:
            snapshot.schemaVersions?.toString() ??
            copy('sys.common.unavailable'),
      ),
      _StateLine(
        label: copy('sys03.validation.integrity'),
        state: snapshot.integrityState,
        value: switch (snapshot.integrityState) {
          'notcollected' => copy('sys.common.notCollected'),
          'ready' => copy('sys.common.ready'),
          'unknown' => copy('sys.common.unknown'),
          'notreturned' => copy('sys.common.notReturned'),
          _ => copy('sys.common.unavailable'),
        },
      ),
      _StateLine(
        label: copy('sys03.validation.readability'),
        state: snapshot.readabilityState,
        value: snapshot.readabilityState == 'notreturned'
            ? copy('sys.common.notReturned')
            : copy('sys.common.ready'),
      ),
    ];
    return Column(
      children: [
        for (var i = 0; i < rows.length; i++) ...[
          rows[i],
          if (i < rows.length - 1) const Divider(height: 24),
        ],
      ],
    );
  }
}

class _StateLine extends StatelessWidget {
  const _StateLine({
    required this.label,
    required this.state,
    required this.value,
  });

  final String label;
  final String state;
  final String value;

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
          value,
          style: TextStyle(
            color: sysStatusColor(state, palette: LumenisTheme.of(context)),
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }
}

class _TruthChain extends StatelessWidget {
  const _TruthChain({required this.snapshot});

  final Sys03Snapshot snapshot;

  @override
  Widget build(BuildContext context) {
    String copy(String key) => SysSystemCopy.text(context, key);
    final labels = [
      copy('sys03.chain.source'),
      copy('sys03.chain.evidence'),
      copy('sys03.chain.canonical'),
      copy('sys03.chain.metric'),
    ];
    return Column(
      children: [
        for (var index = 0; index < labels.length; index++) ...[
          _ChainStage(
            stage: _stageAt(snapshot.truthStages, index, labels[index]),
            label: labels[index],
          ),
          if (index < labels.length - 1)
            Padding(
              padding: const EdgeInsets.only(left: 13),
              child: Align(
                alignment: Alignment.centerLeft,
                child: Container(
                  width: 1,
                  height: 20,
                  color: LumenisTheme.of(context).line,
                ),
              ),
            ),
        ],
        if (snapshot.truthStages.isEmpty) ...[
          const SizedBox(height: 14),
          Align(
            alignment: Alignment.centerLeft,
            child: Text(
              copy('sys03.chain.unavailable'),
              style: TextStyle(
                color: LumenisTheme.of(context).quiet,
                height: 1.45,
              ),
            ),
          ),
        ],
      ],
    );
  }
}

Sys03TruthStage _stageAt(
  List<Sys03TruthStage> stages,
  int index,
  String label,
) {
  if (index < stages.length) return stages[index];
  return Sys03TruthStage(name: label, state: 'unknown', detail: '');
}

class _ChainStage extends StatelessWidget {
  const _ChainStage({required this.stage, required this.label});

  final Sys03TruthStage stage;
  final String label;

  @override
  Widget build(BuildContext context) {
    final detail = stage.detail.isEmpty
        ? SysSystemCopy.text(context, 'sys.common.notReturned')
        : stage.detail;
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        LumenisIcon(
          Icons.radio_button_checked_rounded,
          color: sysStatusColor(stage.state, palette: LumenisTheme.of(context)),
          size: 26,
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                label,
                style: TextStyle(
                  color: LumenisTheme.of(context).foreground,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                detail,
                style: TextStyle(
                  color: LumenisTheme.of(context).muted,
                  height: 1.4,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _ChecksTable extends StatelessWidget {
  const _ChecksTable({required this.snapshot});

  final Sys03Snapshot snapshot;

  @override
  Widget build(BuildContext context) {
    if (snapshot.checks.isEmpty) {
      return Text(
        SysSystemCopy.text(context, 'sys03.checks.empty'),
        style: TextStyle(color: LumenisTheme.of(context).muted, height: 1.5),
      );
    }
    return Column(
      children: [
        for (var index = 0; index < snapshot.checks.length; index++) ...[
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Text(
                  snapshot.checks[index].name,
                  style: TextStyle(color: LumenisTheme.of(context).foreground),
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                flex: 2,
                child: Text(
                  snapshot.checks[index].result,
                  style: TextStyle(
                    color: LumenisTheme.of(context).muted,
                    height: 1.4,
                  ),
                ),
              ),
            ],
          ),
          if (index < snapshot.checks.length - 1) const Divider(height: 22),
        ],
      ],
    );
  }
}
