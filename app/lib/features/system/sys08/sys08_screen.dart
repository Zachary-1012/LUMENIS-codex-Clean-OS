import 'package:flutter/material.dart';

import '../../../core/lumenis_core_client.dart';
import '../../../core/lumenis_theme.dart';
import '../sys02/sys_system_foundation.dart';
import 'sys08_repository.dart';
import 'sys08_snapshot.dart';
import 'sys08_view_model.dart';

class Sys08Screen extends StatefulWidget {
  const Sys08Screen({required this.client, this.repository, super.key});

  final LumenisCoreClient client;
  final Sys08Repository? repository;

  @override
  State<Sys08Screen> createState() => _Sys08ScreenState();
}

class _Sys08ScreenState extends State<Sys08Screen> {
  late final Sys08ViewModel _viewModel;

  @override
  void initState() {
    super.initState();
    _viewModel = Sys08ViewModel(
      repository:
          widget.repository ?? CoreSys08Repository(client: widget.client),
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
            SysLoadPhase.ready => _ObservabilityContent(
              snapshot: _viewModel.snapshot!,
              onRefresh: _viewModel.refresh,
            ),
          },
        ),
      ),
    );
  }
}

class _ObservabilityContent extends StatelessWidget {
  const _ObservabilityContent({
    required this.snapshot,
    required this.onRefresh,
  });

  final Sys08Snapshot snapshot;
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
          eyebrow: copy('sys08.eyebrow'),
          title: copy('sys08.title'),
          subtitle: copy('sys08.subtitle'),
          onRefresh: onRefresh,
        );
        final inventory = SysPanel(
          title: copy('sys08.inventory.title'),
          child: _Inventory(snapshot: snapshot),
        );
        final trace = SysPanel(
          title: copy('sys08.trace.title'),
          detail: copy('sys08.trace.detail'),
          child: _TraceBoundary(),
        );
        final logs = SysPanel(
          title: copy('sys08.logs.title'),
          child: _LogRecords(records: snapshot.records),
        );
        final content = desktop
            ? Row(
                key: const ValueKey('sys08/layout-desktop'),
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(flex: 5, child: inventory),
                  const SizedBox(width: 18),
                  Expanded(
                    flex: 7,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [trace, const SizedBox(height: 14), logs],
                    ),
                  ),
                ],
              )
            : Column(
                key: ValueKey(
                  mobile ? 'sys08/layout-mobile' : 'sys08/layout-tablet',
                ),
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  inventory,
                  const SizedBox(height: 14),
                  trace,
                  const SizedBox(height: 14),
                  logs,
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
                children: [header, const SizedBox(height: 24), content],
              ),
            ),
          ),
        );
      },
    );
  }
}

class _Inventory extends StatelessWidget {
  const _Inventory({required this.snapshot});

  final Sys08Snapshot snapshot;

  @override
  Widget build(BuildContext context) {
    String copy(String key) => SysSystemCopy.text(context, key);
    final size = snapshot.totalSizeMb == null
        ? copy('sys.common.unavailable')
        : '${snapshot.totalSizeMb!.toStringAsFixed(2)} MB';
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _InventoryRow(label: copy('sys08.files'), value: snapshot.totalFiles),
        const Divider(height: 24),
        _InventoryRow(label: copy('sys08.size'), valueText: size),
        const Divider(height: 24),
        _InventoryRow(
          label: copy('sys08.entries'),
          value: snapshot.records.isEmpty ? null : snapshot.records.length,
        ),
        const SizedBox(height: 18),
        if (snapshot.files.isEmpty)
          Text(
            copy('sys08.logs.empty'),
            style: TextStyle(
              color: LumenisTheme.of(context).muted,
              height: 1.5,
            ),
          )
        else
          for (var index = 0; index < snapshot.files.length; index++) ...[
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Text(
                    snapshot.files[index].name,
                    style: TextStyle(
                      color: LumenisTheme.of(context).foreground,
                    ),
                  ),
                ),
                Text(
                  snapshot.files[index].sizeMb == null
                      ? copy('sys.common.unavailable')
                      : '${snapshot.files[index].sizeMb!.toStringAsFixed(2)} MB',
                  style: TextStyle(color: LumenisTheme.of(context).system),
                ),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              snapshot.files[index].modified == '—'
                  ? copy('sys.common.notReturned')
                  : snapshot.files[index].modified,
              style: TextStyle(
                color: LumenisTheme.of(context).quiet,
                fontSize: 12,
              ),
            ),
            if (index < snapshot.files.length - 1) const Divider(height: 22),
          ],
        const SizedBox(height: 14),
        Text(
          copy('sys08.safe'),
          style: TextStyle(
            color: LumenisTheme.of(context).positive,
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }
}

class _InventoryRow extends StatelessWidget {
  const _InventoryRow({required this.label, this.value, this.valueText});

  final String label;
  final int? value;
  final String? valueText;

  @override
  Widget build(BuildContext context) => Row(
    children: [
      Expanded(
        child: Text(
          label,
          style: TextStyle(color: LumenisTheme.of(context).muted),
        ),
      ),
      Text(
        valueText ??
            value?.toString() ??
            SysSystemCopy.text(context, 'sys.common.unavailable'),
        style: TextStyle(
          color: LumenisTheme.of(context).system,
          fontSize: 22,
          fontWeight: FontWeight.w600,
        ),
      ),
    ],
  );
}

class _TraceBoundary extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    String copy(String key) => SysSystemCopy.text(context, key);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Semantics(
          liveRegion: true,
          child: Text(
            copy('sys08.trace.unavailable'),
            style: TextStyle(
              color: LumenisTheme.of(context).caution,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
        const SizedBox(height: 10),
        Text(
          copy('sys08.trace.detail'),
          style: TextStyle(color: LumenisTheme.of(context).muted, height: 1.5),
        ),
        const SizedBox(height: 16),
        Text(
          copy('sys08.exportUnavailable'),
          style: TextStyle(color: LumenisTheme.of(context).quiet, height: 1.45),
        ),
      ],
    );
  }
}

class _LogRecords extends StatelessWidget {
  const _LogRecords({required this.records});

  final List<Sys08LogRecord> records;

  @override
  Widget build(BuildContext context) {
    String copy(String key) => SysSystemCopy.text(context, key);
    if (records.isEmpty) {
      return Text(
        copy('sys08.logs.empty'),
        style: TextStyle(color: LumenisTheme.of(context).muted, height: 1.5),
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (var index = 0; index < records.length; index++) ...[
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Text(
                  records[index].message,
                  style: TextStyle(color: LumenisTheme.of(context).foreground),
                ),
              ),
              SysStatusBadge(
                state: records[index].level,
                label: records[index].level,
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            '${records[index].time} · ${records[index].module}',
            style: TextStyle(
              color: LumenisTheme.of(context).quiet,
              fontSize: 12,
            ),
          ),
          if (records[index].trace != '—') ...[
            const SizedBox(height: 4),
            Text(
              '${copy('sys08.field.trace')}: ${records[index].trace}',
              style: TextStyle(
                color: LumenisTheme.of(context).system,
                fontSize: 12,
              ),
            ),
          ],
          if (index < records.length - 1) const Divider(height: 24),
        ],
      ],
    );
  }
}
