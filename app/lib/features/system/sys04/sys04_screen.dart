import 'package:flutter/material.dart';

import '../../../core/lumenis_icon.dart';

import '../../../core/lumenis_core_client.dart';
import '../../../core/lumenis_theme.dart';
import '../sys02/sys_system_foundation.dart';
import 'sys04_repository.dart';
import 'sys04_snapshot.dart';
import 'sys04_view_model.dart';

class Sys04Screen extends StatefulWidget {
  const Sys04Screen({required this.client, this.repository, super.key});

  final LumenisCoreClient client;
  final Sys04Repository? repository;

  @override
  State<Sys04Screen> createState() => _Sys04ScreenState();
}

class _Sys04ScreenState extends State<Sys04Screen> {
  late final Sys04ViewModel _viewModel;

  @override
  void initState() {
    super.initState();
    _viewModel = Sys04ViewModel(
      repository:
          widget.repository ?? CoreSys04Repository(client: widget.client),
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
            SysLoadPhase.ready => _SecurityContent(
              snapshot: _viewModel.snapshot!,
              onRefresh: _viewModel.refresh,
            ),
          },
        ),
      ),
    );
  }
}

class _SecurityContent extends StatelessWidget {
  const _SecurityContent({required this.snapshot, required this.onRefresh});

  final Sys04Snapshot snapshot;
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
          eyebrow: copy('sys04.eyebrow'),
          title: copy('sys04.title'),
          subtitle: copy('sys04.subtitle'),
          onRefresh: onRefresh,
        );
        final matrix = SysPanel(
          title: copy('sys04.matrix.title'),
          detail: copy('sys04.matrix.detail'),
          child: _PermissionMatrix(rows: snapshot.rows),
        );
        final boundary = SysPanel(
          title: copy('sys04.audit.title'),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _OperationCount(snapshot: snapshot),
              const SizedBox(height: 18),
              Text(
                snapshot.auditAvailable
                    ? copy('sys.common.ready')
                    : copy('sys04.audit.unavailable'),
                style: TextStyle(
                  color: snapshot.auditAvailable
                      ? LumenisTheme.of(context).positive
                      : LumenisTheme.of(context).quiet,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 12),
              Text(
                copy('sys04.audit.detail'),
                style: TextStyle(
                  color: LumenisTheme.of(context).muted,
                  height: 1.45,
                ),
              ),
              const SizedBox(height: 12),
              Text(
                copy('sys04.boundary'),
                style: TextStyle(
                  color: LumenisTheme.of(context).quiet,
                  height: 1.45,
                ),
              ),
            ],
          ),
        );
        final desktopLayout = Row(
          key: const ValueKey('sys04/layout-desktop'),
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(flex: 7, child: matrix),
            const SizedBox(width: 18),
            Expanded(flex: 4, child: boundary),
          ],
        );
        final compactLayout = Column(
          key: ValueKey(mobile ? 'sys04/layout-mobile' : 'sys04/layout-tablet'),
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [matrix, const SizedBox(height: 14), boundary],
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
                  if (desktop) desktopLayout else compactLayout,
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}

class _PermissionMatrix extends StatelessWidget {
  const _PermissionMatrix({required this.rows});

  final List<Sys04PermissionRow> rows;

  @override
  Widget build(BuildContext context) {
    String copy(String key) => SysSystemCopy.text(context, key);
    if (rows.isEmpty) {
      return Text(
        copy('sys.common.bindingUnavailable'),
        style: TextStyle(color: LumenisTheme.of(context).muted, height: 1.5),
      );
    }
    return Column(
      children: [
        Row(
          children: [
            Expanded(
              child: Text(
                copy('sys04.field.level'),
                style: TextStyle(
                  color: LumenisTheme.of(context).quiet,
                  fontSize: 11,
                ),
              ),
            ),
            Expanded(
              child: Text(
                copy('sys04.field.scope'),
                style: TextStyle(
                  color: LumenisTheme.of(context).quiet,
                  fontSize: 11,
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 10),
        for (var index = 0; index < rows.length; index++) ...[
          Row(
            children: [
              Expanded(
                child: Text(
                  _levelLabel(context, rows[index].level),
                  style: TextStyle(
                    color: LumenisTheme.of(context).foreground,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
              Expanded(
                child: Row(
                  children: [
                    LumenisIcon(
                      Icons.shield_outlined,
                      size: 16,
                      color: sysStatusColor(
                        rows[index].state,
                        palette: LumenisTheme.of(context),
                      ),
                    ),
                    const SizedBox(width: 7),
                    Text(
                      rows[index].scope == 'CONTROLLED'
                          ? copy('sys.common.ready')
                          : copy('sys.common.unknown'),
                      style: TextStyle(color: LumenisTheme.of(context).muted),
                    ),
                  ],
                ),
              ),
            ],
          ),
          if (index < rows.length - 1) const Divider(height: 22),
        ],
      ],
    );
  }
}

String _levelLabel(BuildContext context, String level) => switch (level) {
  'READ' => SysSystemCopy.text(context, 'sys04.level.read'),
  'TASK' => SysSystemCopy.text(context, 'sys04.level.task'),
  'AUDIT' => SysSystemCopy.text(context, 'sys04.level.audit'),
  'WRITE' => SysSystemCopy.text(context, 'sys04.level.write'),
  'DEPLOY' => SysSystemCopy.text(context, 'sys04.level.deploy'),
  _ => SysSystemCopy.text(context, 'sys04.level.unknown'),
};

class _OperationCount extends StatelessWidget {
  const _OperationCount({required this.snapshot});

  final Sys04Snapshot snapshot;

  @override
  Widget build(BuildContext context) {
    String copy(String key) => SysSystemCopy.text(context, key);
    final value = snapshot.operationCount == null
        ? copy('sys.common.unavailable')
        : '${snapshot.operationCount}';
    return Row(
      children: [
        Expanded(
          child: Text(
            copy('sys04.operations'),
            style: TextStyle(color: LumenisTheme.of(context).muted),
          ),
        ),
        Text(
          value,
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
