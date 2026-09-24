import 'package:flutter/material.dart';

import '../../../core/lumenis_core_client.dart';
import '../../../core/lumenis_theme.dart';
import 'sys02_repository.dart';
import 'sys02_snapshot.dart';
import 'sys02_view_model.dart';
import 'sys_system_foundation.dart';

class Sys02Screen extends StatefulWidget {
  const Sys02Screen({required this.client, this.repository, super.key});

  final LumenisCoreClient client;
  final Sys02Repository? repository;

  @override
  State<Sys02Screen> createState() => _Sys02ScreenState();
}

class _Sys02ScreenState extends State<Sys02Screen> {
  late final Sys02ViewModel _viewModel;

  @override
  void initState() {
    super.initState();
    _viewModel = Sys02ViewModel(
      repository:
          widget.repository ?? CoreSys02Repository(client: widget.client),
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
            SysLoadPhase.ready => _CollectorContent(
              snapshot: _viewModel.snapshot!,
              onRefresh: _viewModel.refresh,
            ),
          },
        ),
      ),
    );
  }
}

class _CollectorContent extends StatelessWidget {
  const _CollectorContent({required this.snapshot, required this.onRefresh});

  final Sys02Snapshot snapshot;
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
          eyebrow: copy('sys02.eyebrow'),
          title: copy('sys02.title'),
          subtitle: copy('sys02.subtitle'),
          onRefresh: onRefresh,
        );
        final summary = _SummaryStrip(metrics: snapshot.metrics);
        final lanes = SysPanel(
          title: copy('sys02.lanes.title'),
          detail: copy('sys02.lanes.detail'),
          child: _CollectorLanes(collectors: snapshot.collectors),
        );
        final boundary = SysPanel(
          title: copy('sys02.boundary.title'),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                copy('sys02.boundary.detail'),
                style: TextStyle(
                  color: LumenisTheme.of(context).muted,
                  height: 1.5,
                ),
              ),
              const SizedBox(height: 14),
              _BoundaryLine(
                icon: Icons.lock_outline_rounded,
                text: copy('sys02.boundary.noActions'),
              ),
              const SizedBox(height: 10),
              _BoundaryLine(
                icon: Icons.source_outlined,
                text: copy('sys02.source.detail'),
              ),
              if (snapshot.note != null && snapshot.note!.isNotEmpty) ...[
                const SizedBox(height: 14),
                Text(
                  snapshot.note!,
                  style: TextStyle(
                    color: LumenisTheme.of(context).quiet,
                    height: 1.45,
                  ),
                ),
              ],
            ],
          ),
        );

        final desktopContent = Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(flex: 7, child: lanes),
            const SizedBox(width: 18),
            Expanded(flex: 4, child: boundary),
          ],
        );
        final tabletContent = Column(
          key: const ValueKey('sys02/layout-tablet'),
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [lanes, const SizedBox(height: 14), boundary],
        );
        final mobileContent = Column(
          key: const ValueKey('sys02/layout-mobile'),
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            summary,
            const SizedBox(height: 14),
            lanes,
            const SizedBox(height: 14),
            boundary,
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
                  if (!mobile) summary,
                  if (!mobile) const SizedBox(height: 18),
                  if (desktop)
                    KeyedSubtree(
                      key: const ValueKey('sys02/layout-desktop'),
                      child: desktopContent,
                    )
                  else if (mobile)
                    mobileContent
                  else
                    tabletContent,
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}

class _SummaryStrip extends StatelessWidget {
  const _SummaryStrip({required this.metrics});

  final List<Sys02Metric> metrics;

  @override
  Widget build(BuildContext context) {
    final labels = <String, String>{
      'active': SysSystemCopy.text(context, 'sys02.summary.active'),
      'partial': SysSystemCopy.text(context, 'sys02.summary.partial'),
      'missing': SysSystemCopy.text(context, 'sys02.summary.missing'),
      'blocked': SysSystemCopy.text(context, 'sys02.summary.blocked'),
    };
    final values = <Sys02Metric>[];
    for (final key in labels.keys) {
      values.addAll(metrics.where((metric) => metric.id.endsWith(key)));
    }
    final display = values.isNotEmpty
        ? values
        : [
            for (final entry in labels.entries)
              Sys02Metric(
                id: entry.key,
                label: entry.value,
                value: null,
                state: 'unknown',
              ),
          ];
    return SysPanel(
      child: LayoutBuilder(
        builder: (context, constraints) {
          if (constraints.maxWidth < 600) {
            return Column(
              children: [
                for (var i = 0; i < display.length; i++) ...[
                  _MetricStack(
                    metric: display[i],
                    label:
                        labels[display[i].id.split('.').last] ??
                        display[i].label,
                  ),
                  if (i < display.length - 1) const Divider(height: 22),
                ],
              ],
            );
          }
          return Row(
            children: [
              for (var i = 0; i < display.length; i++) ...[
                SysMetricLine(
                  label:
                      labels[display[i].id.split('.').last] ?? display[i].label,
                  value: display[i].value,
                  state: display[i].state,
                ),
                if (i < display.length - 1)
                  const SizedBox(height: 42, child: VerticalDivider()),
              ],
            ],
          );
        },
      ),
    );
  }
}

class _MetricStack extends StatelessWidget {
  const _MetricStack({required this.metric, required this.label});

  final Sys02Metric metric;
  final String label;

  @override
  Widget build(BuildContext context) {
    final value = metric.value == null
        ? SysSystemCopy.text(context, 'sys.common.unavailable')
        : '${metric.value}';
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
            color: metric.value == null
                ? LumenisTheme.of(context).quiet
                : sysStatusColor(
                    metric.state,
                    palette: LumenisTheme.of(context),
                  ),
            fontSize: 20,
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }
}

class _CollectorLanes extends StatelessWidget {
  const _CollectorLanes({required this.collectors});

  final List<Sys02CollectorLane> collectors;

  @override
  Widget build(BuildContext context) {
    if (collectors.isEmpty) {
      return Text(
        SysSystemCopy.text(context, 'sys02.lanes.empty'),
        style: TextStyle(color: LumenisTheme.of(context).muted, height: 1.5),
      );
    }
    return Column(
      children: [
        for (var index = 0; index < collectors.length; index++) ...[
          _CollectorLane(lane: collectors[index]),
          if (index < collectors.length - 1) const Divider(height: 26),
        ],
      ],
    );
  }
}

class _CollectorLane extends StatelessWidget {
  const _CollectorLane({required this.lane});

  final Sys02CollectorLane lane;

  @override
  Widget build(BuildContext context) {
    String copy(String key) => SysSystemCopy.text(context, key);
    final status = lane.status.toLowerCase();
    final records = lane.parsedRecords == null
        ? copy('sys.common.unavailable')
        : '${lane.parsedRecords}';
    return Semantics(
      container: true,
      label: '${lane.platform}, ${copy('sys02.field.status')}: ${lane.status}',
      child: LayoutBuilder(
        builder: (context, constraints) {
          final narrow = constraints.maxWidth < 560;
          final identity = Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                lane.platform,
                style: TextStyle(
                  color: LumenisTheme.of(context).foreground,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 5),
              Text(
                lane.detail,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  color: LumenisTheme.of(context).muted,
                  height: 1.35,
                ),
              ),
            ],
          );
          final measure = Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                copy('sys02.field.records'),
                style: TextStyle(
                  color: LumenisTheme.of(context).quiet,
                  fontSize: 11,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                records,
                style: TextStyle(
                  color: LumenisTheme.of(context).foreground,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          );
          if (narrow) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                identity,
                const SizedBox(height: 12),
                Row(
                  children: [
                    SysStatusBadge(state: status, label: lane.status),
                    const SizedBox(width: 18),
                    measure,
                  ],
                ),
              ],
            );
          }
          return Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(child: identity),
              const SizedBox(width: 18),
              SysStatusBadge(state: status, label: lane.status),
              const SizedBox(width: 28),
              SizedBox(width: 110, child: measure),
            ],
          );
        },
      ),
    );
  }
}

class _BoundaryLine extends StatelessWidget {
  const _BoundaryLine({required this.icon, required this.text});

  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, color: LumenisTheme.of(context).system, size: 18),
        const SizedBox(width: 10),
        Expanded(
          child: Text(
            text,
            style: TextStyle(
              color: LumenisTheme.of(context).muted,
              height: 1.45,
            ),
          ),
        ),
      ],
    );
  }
}
