import 'package:flutter/material.dart';

import '../../../core/lumenis_core_client.dart';
import '../../../core/lumenis_theme.dart';
import '../../../l10n/lumenis_localizations.dart';
import 'sys01_repository.dart';
import 'sys01_snapshot.dart';
import 'sys01_view_model.dart';

class Sys01Screen extends StatefulWidget {
  const Sys01Screen({required this.client, this.repository, super.key});

  final LumenisCoreClient client;
  final Sys01Repository? repository;

  @override
  State<Sys01Screen> createState() => _Sys01ScreenState();
}

class _Sys01ScreenState extends State<Sys01Screen> {
  late final Sys01ViewModel _viewModel;

  @override
  void initState() {
    super.initState();
    _viewModel = Sys01ViewModel(
      repository:
          widget.repository ?? CoreSys01Repository(client: widget.client),
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
            Sys01LoadPhase.loading => const _LoadingState(),
            Sys01LoadPhase.failed => _FailureState(
              kind: _viewModel.failureKind!,
              onRetry: _viewModel.refresh,
            ),
            Sys01LoadPhase.ready => _RuntimeDashboard(
              snapshot: _viewModel.snapshot!,
              onRefresh: _viewModel.refresh,
            ),
          },
        ),
      ),
    );
  }
}

class _LoadingState extends StatelessWidget {
  const _LoadingState();

  @override
  Widget build(BuildContext context) {
    return Semantics(
      liveRegion: true,
      label: context.lumenisL10n.text('sys01.loading'),
      child: Align(
        alignment: Alignment.topCenter,
        child: ConstrainedBox(
          constraints: BoxConstraints(maxWidth: 960),
          child: Padding(
            padding: EdgeInsets.all(28),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  context.lumenisL10n.text('sys01.title'),
                  style: TextStyle(
                    color: LumenisTheme.of(context).foreground,
                    fontSize: 27,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                SizedBox(height: 20),
                _LoadingLine(width: 260),
                SizedBox(height: 12),
                _LoadingLine(width: 420),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _LoadingLine extends StatelessWidget {
  const _LoadingLine({required this.width});

  final double width;

  @override
  Widget build(BuildContext context) => Container(
    width: width,
    height: 14,
    decoration: BoxDecoration(
      color: LumenisTheme.of(context).surface,
      borderRadius: BorderRadius.circular(4),
    ),
  );
}

class _FailureState extends StatelessWidget {
  const _FailureState({required this.kind, required this.onRetry});

  final Sys01FailureKind kind;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    final (title, detail, canRetry) = switch (kind) {
      Sys01FailureKind.authentication => (
        copy.text('sys01.failure.auth.title'),
        copy.text('sys01.failure.auth.detail'),
        false,
      ),
      Sys01FailureKind.permissionDenied => (
        copy.text('sys01.failure.permission.title'),
        copy.text('sys01.failure.permission.detail'),
        false,
      ),
      Sys01FailureKind.offline => (
        copy.text('sys01.failure.offline.title'),
        copy.text('sys01.failure.offline.detail'),
        true,
      ),
      Sys01FailureKind.response => (
        copy.text('sys01.failure.response.title'),
        copy.text('sys01.failure.response.detail'),
        true,
      ),
    };

    return Align(
      alignment: Alignment.topCenter,
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 720),
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _Eyebrow(copy.text('sys01.eyebrow')),
              const SizedBox(height: 16),
              Text(
                title,
                style: TextStyle(
                  color: LumenisTheme.of(context).foreground,
                  fontSize: 26,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 10),
              Text(
                detail,
                style: TextStyle(
                  color: LumenisTheme.of(context).muted,
                  height: 1.5,
                ),
              ),
              if (canRetry) ...[
                const SizedBox(height: 20),
                FilledButton.tonal(
                  onPressed: onRetry,
                  child: Text(copy.text('sys01.retry')),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _RuntimeDashboard extends StatelessWidget {
  const _RuntimeDashboard({required this.snapshot, required this.onRefresh});

  final Sys01Snapshot snapshot;
  final VoidCallback onRefresh;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final width = constraints.maxWidth;
        final desktop = width >= 1100;
        final mobile = width < 768;
        final horizontalPadding = width < 480
            ? 18.0
            : width < 900
            ? 26.0
            : 38.0;

        final header = _PageHeader(snapshot: snapshot, onRefresh: onRefresh);
        final overview = _OverallStatus(snapshot: snapshot);
        final sourceRail = _SourceRail(snapshot: snapshot);
        final copy = context.lumenisL10n;
        final desktopSpine = Column(
          key: const ValueKey('sys01/layout-desktop'),
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            overview,
            const SizedBox(height: 20),
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  flex: 7,
                  child: _CountStack(
                    counts: [
                      _CountEntry(
                        copy.text('sys01.count.total'),
                        snapshot.registeredWorkers,
                      ),
                      _CountEntry(
                        copy.text('sys01.count.failed'),
                        snapshot.failedWorkers,
                      ),
                      _CountEntry(
                        copy.text('sys01.count.dlq'),
                        snapshot.dlqTotal,
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 18),
                SizedBox(
                  width: 250,
                  child: _GuardrailPanel(snapshot: snapshot),
                ),
                const SizedBox(width: 26),
                Expanded(flex: 4, child: sourceRail),
              ],
            ),
          ],
        );

        final mobileSpine = Column(
          key: const ValueKey('sys01/layout-mobile'),
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            overview,
            const SizedBox(height: 16),
            _CountCard(
              keyName: 'failed-workers',
              label: copy.text('sys01.count.failed'),
              count: snapshot.failedWorkers,
            ),
            const SizedBox(height: 10),
            _CountCard(
              keyName: 'dlq',
              label: copy.text('sys01.count.dlq'),
              count: snapshot.dlqTotal,
            ),
            const SizedBox(height: 10),
            _CountCard(
              keyName: 'registered-workers',
              label: copy.text('sys01.count.total'),
              count: snapshot.registeredWorkers,
            ),
            const SizedBox(height: 18),
            _GuardrailPanel(snapshot: snapshot),
            const SizedBox(height: 14),
            sourceRail,
          ],
        );

        final tabletSpine = Column(
          key: const ValueKey('sys01/layout-tablet'),
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            overview,
            const SizedBox(height: 16),
            _CountStack(
              counts: [
                _CountEntry(
                  copy.text('sys01.count.total'),
                  snapshot.registeredWorkers,
                ),
                _CountEntry(
                  copy.text('sys01.count.failed'),
                  snapshot.failedWorkers,
                ),
                _CountEntry(copy.text('sys01.count.dlq'), snapshot.dlqTotal),
              ],
            ),
            const SizedBox(height: 12),
            _GuardrailDisclosure(snapshot: snapshot),
            const SizedBox(height: 12),
            sourceRail,
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
                    desktopSpine
                  else if (mobile)
                    mobileSpine
                  else
                    tabletSpine,
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}

class _PageHeader extends StatelessWidget {
  const _PageHeader({required this.snapshot, required this.onRefresh});

  final Sys01Snapshot snapshot;
  final VoidCallback onRefresh;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      alignment: WrapAlignment.spaceBetween,
      crossAxisAlignment: WrapCrossAlignment.center,
      spacing: 18,
      runSpacing: 14,
      children: [
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _Eyebrow(context.lumenisL10n.text('sys01.eyebrow')),
            SizedBox(height: 8),
            Text(
              context.lumenisL10n.text('sys01.title'),
              style: TextStyle(
                color: LumenisTheme.of(context).foreground,
                fontSize: 28,
                height: 1.2,
                fontWeight: FontWeight.w600,
              ),
            ),
            SizedBox(height: 6),
            Text(
              context.lumenisL10n.text('sys01.subtitle'),
              style: TextStyle(
                color: LumenisTheme.of(context).muted,
                fontSize: 13,
              ),
            ),
          ],
        ),
        Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              snapshot.hasCompleteRuntimeSample
                  ? context.lumenisL10n.text('sys01.status.current')
                  : context.lumenisL10n.text('sys01.status.partial'),
              style: TextStyle(
                color: LumenisTheme.of(context).muted,
                fontSize: 12,
              ),
            ),
            const SizedBox(width: 8),
            IconButton(
              tooltip: context.lumenisL10n.text('sys01.refresh.tooltip'),
              onPressed: onRefresh,
              icon: const Icon(Icons.refresh_rounded),
              color: LumenisTheme.of(context).system,
            ),
          ],
        ),
      ],
    );
  }
}

class _OverallStatus extends StatelessWidget {
  const _OverallStatus({required this.snapshot});

  final Sys01Snapshot snapshot;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    final label = _overallLabel(context, snapshot.overall);
    final color = _stateColor(snapshot.overallState, LumenisTheme.of(context));
    final overall = snapshot.overall;
    final available =
        overall != null &&
        snapshot.overallState != 'offline' &&
        overall.toLowerCase() != 'unknown';

    return Container(
      key: const ValueKey('sys01/overall'),
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(20, 18, 20, 19),
      decoration: BoxDecoration(
        color: LumenisTheme.of(context).surface,
        border: Border.all(
          color: available
              ? color.withValues(alpha: 0.48)
              : LumenisTheme.of(context).line,
        ),
        borderRadius: BorderRadius.circular(14),
      ),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final summary = Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                copy.text('sys01.status.overall'),
                style: TextStyle(
                  color: LumenisTheme.of(context).muted,
                  fontSize: 13,
                ),
              ),
              const SizedBox(height: 6),
              Semantics(
                liveRegion: true,
                label:
                    '${copy.text('sys01.status.overall')}：${available ? label : copy.text('sys01.unavailable')}',
                child: Text(
                  available ? label : copy.text('sys01.unavailable'),
                  style: TextStyle(
                    color: available ? color : LumenisTheme.of(context).muted,
                    fontSize: 23,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
              const SizedBox(height: 4),
              Text(
                available
                    ? copy.text('sys01.status.confirmed')
                    : copy.text('sys01.status.unavailable'),
                style: TextStyle(
                  color: available
                      ? LumenisTheme.of(context).quiet
                      : LumenisTheme.of(context).muted,
                  fontSize: 12,
                ),
              ),
            ],
          );
          final stateTag = _StateTag(
            label: available ? label : copy.text('sys01.unavailable'),
            color: color,
          );
          final dot = Container(
            width: 10,
            height: 10,
            margin: const EdgeInsets.only(top: 7),
            decoration: BoxDecoration(color: color, shape: BoxShape.circle),
          );
          if (constraints.maxWidth < 520) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    dot,
                    const SizedBox(width: 14),
                    Expanded(child: summary),
                  ],
                ),
                const SizedBox(height: 12),
                stateTag,
              ],
            );
          }
          return Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              dot,
              const SizedBox(width: 14),
              Expanded(child: summary),
              const SizedBox(width: 8),
              stateTag,
            ],
          );
        },
      ),
    );
  }
}

class _CountEntry {
  const _CountEntry(this.label, this.count);

  final String label;
  final Sys01Count count;
}

class _CountStack extends StatelessWidget {
  const _CountStack({required this.counts});

  final List<_CountEntry> counts;

  @override
  Widget build(BuildContext context) {
    return _Panel(
      key: const ValueKey('sys01/counts'),
      title: context.lumenisL10n.text('sys01.counts.title'),
      detail: context.lumenisL10n.text('sys01.counts.detail'),
      child: Column(
        children: [
          for (var index = 0; index < counts.length; index++) ...[
            if (index > 0) const _Rule(),
            _CountLine(entry: counts[index]),
          ],
        ],
      ),
    );
  }
}

class _CountCard extends StatelessWidget {
  const _CountCard({
    required this.keyName,
    required this.label,
    required this.count,
  });

  final String keyName;
  final String label;
  final Sys01Count count;

  @override
  Widget build(BuildContext context) {
    return _Panel(
      key: ValueKey('sys01/count-$keyName'),
      title: label,
      child: _CountValue(count: count, compact: false),
    );
  }
}

class _CountLine extends StatelessWidget {
  const _CountLine({required this.entry});

  final _CountEntry entry;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Expanded(
            child: Text(
              entry.label,
              style: TextStyle(color: LumenisTheme.of(context).muted),
            ),
          ),
          _CountValue(count: entry.count, compact: true),
        ],
      ),
    );
  }
}

class _CountValue extends StatelessWidget {
  const _CountValue({required this.count, required this.compact});

  final Sys01Count count;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final value = count.value;
    final available = value != null;
    return Semantics(
      label: available
          ? '$value'
          : context.lumenisL10n.text('sys01.unavailable'),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          Text(
            available ? '$value' : '—',
            style: TextStyle(
              color: available
                  ? LumenisTheme.of(context).foreground
                  : LumenisTheme.of(context).muted,
              fontSize: compact ? 20 : 30,
              height: 1.15,
              fontWeight: FontWeight.w600,
              fontFeatures: const [FontFeature.tabularFigures()],
            ),
          ),
          if (!available) ...[
            const SizedBox(height: 3),
            Text(
              count.state == 'offline'
                  ? context.lumenisL10n.text('sys01.unavailable.current')
                  : context.lumenisL10n.text('sys01.unavailable.not_provided'),
              style: TextStyle(
                color: LumenisTheme.of(context).quiet,
                fontSize: 11,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _GuardrailPanel extends StatelessWidget {
  const _GuardrailPanel({required this.snapshot});

  final Sys01Snapshot snapshot;

  @override
  Widget build(BuildContext context) {
    return _Panel(
      key: const ValueKey('sys01/guardrails'),
      title: context.lumenisL10n.text('sys01.guardrails.title'),
      detail: snapshot.hasCompleteRuntimeSample
          ? context.lumenisL10n.text('sys01.guardrails.complete')
          : context.lumenisL10n.text('sys01.guardrails.partial'),
      child: Column(
        children: [
          _GuardrailLine(
            label: context.lumenisL10n.text('sys01.guardrails.reaper'),
            value: _reaperLabel(context, snapshot.reaperRunning),
            color: snapshot.reaperRunning == true
                ? LumenisTheme.of(context).positive
                : snapshot.reaperRunning == false
                ? LumenisTheme.of(context).caution
                : LumenisTheme.of(context).muted,
          ),
          const _Rule(),
          _GuardrailLine(
            label: context.lumenisL10n.text('sys01.guardrails.open'),
            value:
                snapshot.openBreakers?.toString() ??
                context.lumenisL10n.text('sys01.unavailable'),
            color: _breakerColor(
              snapshot.openBreakers,
              LumenisTheme.of(context),
            ),
          ),
          const _Rule(),
          _GuardrailLine(
            label: context.lumenisL10n.text('sys01.guardrails.registered'),
            value:
                snapshot.registeredBreakers?.toString() ??
                context.lumenisL10n.text('sys01.unavailable'),
            color: snapshot.registeredBreakers == null
                ? LumenisTheme.of(context).muted
                : LumenisTheme.of(context).foreground,
          ),
        ],
      ),
    );
  }
}

class _GuardrailDisclosure extends StatelessWidget {
  const _GuardrailDisclosure({required this.snapshot});

  final Sys01Snapshot snapshot;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: LumenisTheme.of(context).surface,
        border: Border.all(color: LumenisTheme.of(context).line),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Material(
        color: Colors.transparent,
        child: ExpansionTile(
          key: const ValueKey('sys01/guardrail-inspector'),
          title: Text(context.lumenisL10n.text('sys01.guardrails.title')),
          subtitle: Text(
            snapshot.hasCompleteRuntimeSample
                ? context.lumenisL10n.text('sys01.guardrail.inspect')
                : context.lumenisL10n.text('sys01.guardrail.partial'),
            style: TextStyle(
              color: LumenisTheme.of(context).muted,
              fontSize: 12,
            ),
          ),
          iconColor: LumenisTheme.of(context).system,
          collapsedIconColor: LumenisTheme.of(context).muted,
          childrenPadding: const EdgeInsets.fromLTRB(14, 0, 14, 14),
          children: [_GuardrailPanel(snapshot: snapshot)],
        ),
      ),
    );
  }
}

class _GuardrailLine extends StatelessWidget {
  const _GuardrailLine({
    required this.label,
    required this.value,
    required this.color,
  });

  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 10),
      child: Row(
        children: [
          Expanded(
            child: Text(
              label,
              style: TextStyle(color: LumenisTheme.of(context).muted),
            ),
          ),
          Flexible(
            child: Text(
              value,
              textAlign: TextAlign.end,
              style: TextStyle(color: color, fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
    );
  }
}

class _SourceRail extends StatelessWidget {
  const _SourceRail({required this.snapshot});

  final Sys01Snapshot snapshot;

  @override
  Widget build(BuildContext context) {
    return _Panel(
      key: const ValueKey('sys01/source-rail'),
      title: context.lumenisL10n.text('sys01.source.title'),
      detail: context.lumenisL10n.text('sys01.source.detail'),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _SourceLine(
            label: context.lumenisL10n.text('sys01.source.source'),
            value: context.lumenisL10n.text('sys01.source.monitoring'),
          ),
          const _Rule(),
          _SourceLine(
            label: context.lumenisL10n.text('sys01.source.observation'),
            value: snapshot.observationAvailable
                ? context.lumenisL10n.text('sys01.source.observation_ready')
                : context.lumenisL10n.text('sys01.source.no_observation'),
          ),
          if (snapshot.guardianName != null) ...[
            const _Rule(),
            _SourceLine(
              label: context.lumenisL10n.text('sys01.source.runtime'),
              value: context.lumenisL10n.text('sys01.source.identified'),
            ),
          ],
          const _Rule(),
          _SourceLine(
            label: context.lumenisL10n.text('sys01.source.time'),
            value:
                snapshot.sampleTimestamp ??
                context.lumenisL10n.text('sys01.unavailable'),
            emphasize: true,
          ),
          const _Rule(),
          _SourceLine(
            label: context.lumenisL10n.text('sys01.source.trace'),
            value:
                snapshot.observationTraceId ??
                context.lumenisL10n.text('sys01.unavailable'),
          ),
          const _Rule(),
          _SourceLine(
            label: context.lumenisL10n.text('sys01.source.boundary'),
            value: context.lumenisL10n.text('sys01.source.read_only'),
          ),
          const SizedBox(height: 12),
          Text(
            context.lumenisL10n.text('sys01.source.detail'),
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

class _SourceLine extends StatelessWidget {
  const _SourceLine({
    required this.label,
    required this.value,
    this.emphasize = false,
  });

  final String label;
  final String value;
  final bool emphasize;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 9),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: TextStyle(
              color: LumenisTheme.of(context).quiet,
              fontSize: 11,
            ),
          ),
          const SizedBox(height: 4),
          SelectableText(
            value,
            style: TextStyle(
              color: emphasize
                  ? LumenisTheme.of(context).system
                  : LumenisTheme.of(context).foreground,
              fontSize: 13,
              height: 1.4,
              fontWeight: emphasize ? FontWeight.w500 : FontWeight.w400,
            ),
          ),
        ],
      ),
    );
  }
}

class _Panel extends StatelessWidget {
  const _Panel({
    required this.title,
    required this.child,
    this.detail,
    super.key,
  });

  final String title;
  final String? detail;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(16, 15, 16, 14),
      decoration: BoxDecoration(
        color: LumenisTheme.of(context).surface,
        border: Border.all(color: LumenisTheme.of(context).line),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: TextStyle(
              color: LumenisTheme.of(context).foreground,
              fontSize: 16,
              fontWeight: FontWeight.w600,
            ),
          ),
          if (detail != null) ...[
            const SizedBox(height: 4),
            Text(
              detail!,
              style: TextStyle(
                color: LumenisTheme.of(context).quiet,
                fontSize: 11,
                height: 1.4,
              ),
            ),
          ],
          const SizedBox(height: 11),
          child,
        ],
      ),
    );
  }
}

class _StateTag extends StatelessWidget {
  const _StateTag({required this.label, required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: color,
          fontSize: 11,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}

class _Eyebrow extends StatelessWidget {
  const _Eyebrow(this.label);

  final String label;

  @override
  Widget build(BuildContext context) => Text(
    label,
    style: TextStyle(
      color: LumenisTheme.of(context).system,
      fontSize: 10,
      letterSpacing: 1.2,
      fontWeight: FontWeight.w600,
    ),
  );
}

class _Rule extends StatelessWidget {
  const _Rule();

  @override
  Widget build(BuildContext context) => SizedBox(
    height: 1,
    child: ColoredBox(color: LumenisTheme.of(context).line),
  );
}

String _overallLabel(BuildContext context, String? value) => switch (value
    ?.toLowerCase()) {
  'healthy' || 'ok' => context.lumenisL10n.text('sys01.state.healthy'),
  'degraded' => context.lumenisL10n.text('sys01.state.degraded'),
  'unhealthy' || 'error' => context.lumenisL10n.text('sys01.state.unhealthy'),
  _ => context.lumenisL10n.text('sys01.unavailable'),
};

String _reaperLabel(BuildContext context, bool? running) => switch (running) {
  true => context.lumenisL10n.text('status.running'),
  false => context.lumenisL10n.text('sys01.state.stopped'),
  null => context.lumenisL10n.text('sys01.unavailable'),
};

Color _stateColor(String state, LumenisPalette palette) => switch (state) {
  'ok' || 'ready' => palette.positive,
  'warn' || 'idle' => palette.caution,
  'bad' || 'error' => palette.danger,
  _ => palette.muted,
};

Color _breakerColor(int? count, LumenisPalette palette) => count == null
    ? palette.muted
    : count > 0
    ? palette.danger
    : palette.positive;
