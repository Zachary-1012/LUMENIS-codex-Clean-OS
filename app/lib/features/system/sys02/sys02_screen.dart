import 'package:flutter/material.dart';

import '../../../core/lumenis_core_client.dart';
import '../../../core/lumenis_theme.dart';
import 'sys02_repository.dart';
import 'sys02_snapshot.dart';
import 'sys02_view_model.dart';
import 'sys_system_foundation.dart';
import 'collector_request_panel.dart';

class Sys02Screen extends StatefulWidget {
  const Sys02Screen({required this.client, this.repository, super.key});

  final LumenisCoreClient client;
  final Sys02Repository? repository;

  @override
  State<Sys02Screen> createState() => _Sys02ScreenState();
}

class _Sys02ScreenState extends State<Sys02Screen> {
  late final Sys02ViewModel _viewModel;
  bool _collecting = false;
  String? _collectMessageKey;

  Future<void> _manualCollect() async {
    if (_collecting) return;
    setState(() {
      _collecting = true;
      _collectMessageKey = null;
    });
    String key;
    try {
      final result = await widget.client.startManualCollection();
      key = result['ok'] == true
          ? 'sys02.manual.queued'
          : 'sys02.manual.failed';
    } on Object {
      key = 'sys02.manual.failed';
    }
    if (!mounted) return;
    setState(() {
      _collecting = false;
      _collectMessageKey = key;
    });
    _viewModel.refresh();
  }

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
              collecting: _collecting,
              collectMessageKey: _collectMessageKey,
              onManualCollect: _manualCollect,
              client: widget.client,
            ),
          },
        ),
      ),
    );
  }
}

class _CollectorContent extends StatelessWidget {
  const _CollectorContent({
    required this.snapshot,
    required this.onRefresh,
    required this.collecting,
    required this.collectMessageKey,
    required this.onManualCollect,
    required this.client,
  });

  final Sys02Snapshot snapshot;
  final VoidCallback onRefresh;
  final bool collecting;
  final String? collectMessageKey;
  final VoidCallback onManualCollect;
  final LumenisCoreClient client;

  @override
  Widget build(BuildContext context) {
    final palette = LumenisTheme.of(context);
    String copy(String key) => SysSystemCopy.text(context, key);
    final connections = Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            Expanded(
              child: Text(
                copy('sys02.lanes.title'),
                style: Theme.of(context).textTheme.titleLarge,
              ),
            ),
            IconButton(
              onPressed: onRefresh,
              tooltip: copy('sys.common.refresh'),
              icon: const Icon(Icons.refresh),
            ),
          ],
        ),
        const SizedBox(height: 12),
        _CollectorLanes(collectors: snapshot.collectors),
        if (snapshot.note != null && snapshot.note!.isNotEmpty) ...[
          const Divider(height: 28),
          Text(snapshot.note!, style: TextStyle(color: palette.muted)),
        ],
        const SizedBox(height: 20),
        Material(
          color: Colors.transparent,
          child: ExpansionTile(
            tilePadding: EdgeInsets.zero,
            title: Text(copy('sys02.summary.title')),
            children: [
              _SummaryStrip(metrics: snapshot.metrics),
              const SizedBox(height: 14),
              FilledButton.tonalIcon(
                key: const ValueKey('sys02-manual-collect'),
                onPressed: collecting ? null : onManualCollect,
                icon: const Icon(Icons.play_arrow_rounded),
                label: Text(copy('sys02.manual.action')),
              ),
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 12),
                child: Semantics(
                  liveRegion: collectMessageKey != null,
                  child: Text(copy(collectMessageKey ?? 'sys02.manual.hint')),
                ),
              ),
            ],
          ),
        ),
      ],
    );
    return LayoutBuilder(
      builder: (context, constraints) {
        final wide =
            constraints.maxWidth >= 1000 &&
            MediaQuery.textScalerOf(context).scale(16) <= 24;
        final request = CollectorRequestPanel(
          client: client,
          onComplete: onRefresh,
        );
        final heading = Padding(
          padding: const EdgeInsets.fromLTRB(24, 16, 24, 18),
          child: Row(
            children: [
              Expanded(
                child: Text(
                  copy('sys02.title'),
                  style: Theme.of(context).textTheme.headlineMedium,
                ),
              ),
              Container(width: 8, height: 8, color: palette.system),
            ],
          ),
        );
        if (wide) {
          return Column(
            key: const ValueKey('sys02/layout-desktop'),
            children: [
              heading,
              Expanded(
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Expanded(
                      flex: 6,
                      child: SingleChildScrollView(
                        padding: const EdgeInsets.fromLTRB(24, 0, 24, 24),
                        child: request,
                      ),
                    ),
                    VerticalDivider(width: 1, color: palette.line),
                    Expanded(
                      flex: 4,
                      child: ColoredBox(
                        color: palette.surface,
                        child: SingleChildScrollView(
                          padding: const EdgeInsets.fromLTRB(24, 0, 24, 24),
                          child: connections,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          );
        }
        return SingleChildScrollView(
          key: ValueKey(
            constraints.maxWidth < 768
                ? 'sys02/layout-mobile'
                : 'sys02/layout-tablet',
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              heading,
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 18),
                child: request,
              ),
              Padding(padding: const EdgeInsets.all(24), child: connections),
            ],
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
