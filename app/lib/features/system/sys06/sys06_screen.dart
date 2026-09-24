import 'package:flutter/material.dart';

import '../../../core/lumenis_core_client.dart';
import '../../../core/lumenis_theme.dart';
import '../sys02/sys_system_foundation.dart';
import 'sys06_repository.dart';
import 'sys06_snapshot.dart';
import 'sys06_view_model.dart';

class Sys06Screen extends StatefulWidget {
  const Sys06Screen({required this.client, this.repository, super.key});

  final LumenisCoreClient client;
  final Sys06Repository? repository;

  @override
  State<Sys06Screen> createState() => _Sys06ScreenState();
}

class _Sys06ScreenState extends State<Sys06Screen> {
  late final Sys06ViewModel _viewModel;

  @override
  void initState() {
    super.initState();
    _viewModel = Sys06ViewModel(
      repository:
          widget.repository ?? CoreSys06Repository(client: widget.client),
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
            SysLoadPhase.ready => _BrowserContent(
              snapshot: _viewModel.snapshot!,
              onRefresh: _viewModel.refresh,
            ),
          },
        ),
      ),
    );
  }
}

class _BrowserContent extends StatelessWidget {
  const _BrowserContent({required this.snapshot, required this.onRefresh});

  final Sys06Snapshot snapshot;
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
          eyebrow: copy('sys06.eyebrow'),
          title: copy('sys06.title'),
          subtitle: copy('sys06.subtitle'),
          onRefresh: onRefresh,
        );
        final capability = SysPanel(
          title: copy('sys06.boundary.title'),
          detail: copy('sys06.boundary.detail'),
          child: _CapabilitySummary(snapshot: snapshot),
        );
        final instances = SysPanel(
          title: copy('sys06.instances.title'),
          child: _InstanceStates(states: snapshot.instanceStates),
        );
        final content = desktop
            ? Row(
                key: const ValueKey('sys06/layout-desktop'),
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(flex: 5, child: capability),
                  const SizedBox(width: 18),
                  Expanded(flex: 7, child: instances),
                ],
              )
            : Column(
                key: ValueKey(
                  mobile ? 'sys06/layout-mobile' : 'sys06/layout-tablet',
                ),
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [capability, const SizedBox(height: 14), instances],
              );
        return Align(
          alignment: Alignment.topCenter,
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1500),
            child: SingleChildScrollView(
              padding: EdgeInsets.fromLTRB(
                horizontalPadding,
                26,
                horizontalPadding,
                48,
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [header, const SizedBox(height: 24), content],
              ),
            ),
          ),
        );
      },
    );
  }
}

class _CapabilitySummary extends StatelessWidget {
  const _CapabilitySummary({required this.snapshot});

  final Sys06Snapshot snapshot;

  @override
  Widget build(BuildContext context) {
    String copy(String key) => SysSystemCopy.text(context, key);
    final values = [
      _CapabilityValue(
        label: copy('sys06.instances'),
        value: snapshot.instances,
      ),
      _CapabilityValue(
        label: copy('sys06.online'),
        value: snapshot.onlineCount,
      ),
      _CapabilityValue(
        label: copy('sys06.capabilities'),
        value: snapshot.capabilityCount,
      ),
    ];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (var index = 0; index < values.length; index++) ...[
          Row(
            children: [
              Expanded(
                child: Text(
                  values[index].label,
                  style: TextStyle(color: LumenisTheme.of(context).muted),
                ),
              ),
              Text(
                values[index].value?.toString() ??
                    copy('sys.common.unavailable'),
                style: TextStyle(
                  color: LumenisTheme.of(context).system,
                  fontSize: 22,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
          if (index < values.length - 1) const Divider(height: 24),
        ],
        const SizedBox(height: 16),
        _BoundaryNote(
          icon: Icons.visibility_outlined,
          text: copy('sys06.boundary.allowed'),
        ),
        const SizedBox(height: 10),
        _BoundaryNote(
          icon: Icons.block_outlined,
          text: copy('sys06.boundary.blocked'),
        ),
        const SizedBox(height: 14),
        Text(
          copy('sys06.safe'),
          style: TextStyle(
            color: LumenisTheme.of(context).positive,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 8),
        Text(
          copy('sys06.source'),
          style: TextStyle(color: LumenisTheme.of(context).quiet, height: 1.45),
        ),
      ],
    );
  }
}

class _CapabilityValue {
  const _CapabilityValue({required this.label, required this.value});

  final String label;
  final int? value;
}

class _InstanceStates extends StatelessWidget {
  const _InstanceStates({required this.states});

  final List<Sys06InstanceState> states;

  @override
  Widget build(BuildContext context) {
    String copy(String key) => SysSystemCopy.text(context, key);
    if (states.isEmpty) {
      return Text(
        copy('sys06.noInstances'),
        style: TextStyle(color: LumenisTheme.of(context).muted, height: 1.5),
      );
    }
    return Column(
      children: [
        for (var index = 0; index < states.length; index++) ...[
          Row(
            children: [
              Expanded(
                child: Text(
                  copy('sys06.instance').replaceAll('{n}', '${index + 1}'),
                  style: TextStyle(
                    color: LumenisTheme.of(context).foreground,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
              SysStatusBadge(
                state: states[index].state.toLowerCase(),
                label: states[index].state,
              ),
            ],
          ),
          if (index < states.length - 1) const Divider(height: 24),
        ],
      ],
    );
  }
}

class _BoundaryNote extends StatelessWidget {
  const _BoundaryNote({required this.icon, required this.text});

  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) => Row(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Icon(icon, color: LumenisTheme.of(context).system, size: 18),
      const SizedBox(width: 9),
      Expanded(
        child: Text(
          text,
          style: TextStyle(color: LumenisTheme.of(context).muted, height: 1.45),
        ),
      ),
    ],
  );
}
