import 'package:flutter/material.dart';

import '../../../core/lumenis_core_client.dart';
import '../../../core/lumenis_theme.dart';
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
      color: LumenisTheme.canvas,
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
      label: '正在读取系统运行状态',
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
                  '运行状态',
                  style: TextStyle(
                    color: LumenisTheme.foreground,
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
      color: LumenisTheme.surface,
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
    final (title, detail, canRetry) = switch (kind) {
      Sys01FailureKind.authentication => ('需要登录', '请登录后查看系统运行状态。', false),
      Sys01FailureKind.permissionDenied => (
        '当前账号无法查看',
        '如需查看系统运行状态，请联系系统管理员。',
        false,
      ),
      Sys01FailureKind.offline => ('系统服务暂不可用', '暂时无法读取当前运行状态。请检查连接后重试。', true),
      Sys01FailureKind.response => ('运行状态暂不可用', '系统暂时无法提供有效状态，请稍后重试。', true),
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
              const _Eyebrow('系统运行'),
              const SizedBox(height: 16),
              Text(
                title,
                style: const TextStyle(
                  color: LumenisTheme.foreground,
                  fontSize: 26,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 10),
              Text(
                detail,
                style: const TextStyle(color: LumenisTheme.muted, height: 1.5),
              ),
              if (canRetry) ...[
                const SizedBox(height: 20),
                FilledButton.tonal(
                  onPressed: onRetry,
                  child: const Text('重新检查'),
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
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      _CountStack(
                        counts: [
                          _CountEntry('后台进程总数', snapshot.registeredWorkers),
                          _CountEntry('异常后台进程', snapshot.failedWorkers),
                          _CountEntry('失败队列记录总数', snapshot.dlqTotal),
                        ],
                      ),
                      const SizedBox(height: 18),
                      _GuardrailPanel(snapshot: snapshot),
                    ],
                  ),
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
            _CountCard(label: '异常后台进程', count: snapshot.failedWorkers),
            const SizedBox(height: 10),
            _CountCard(label: '失败队列记录总数', count: snapshot.dlqTotal),
            const SizedBox(height: 10),
            _CountCard(label: '后台进程总数', count: snapshot.registeredWorkers),
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
                _CountEntry('后台进程总数', snapshot.registeredWorkers),
                _CountEntry('异常后台进程', snapshot.failedWorkers),
                _CountEntry('失败队列记录总数', snapshot.dlqTotal),
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
        const Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _Eyebrow('系统运行'),
            SizedBox(height: 8),
            Text(
              '运行状态',
              style: TextStyle(
                color: LumenisTheme.foreground,
                fontSize: 28,
                height: 1.2,
                fontWeight: FontWeight.w600,
              ),
            ),
            SizedBox(height: 6),
            Text(
              '后台任务、失败队列与服务保护状态',
              style: TextStyle(color: LumenisTheme.muted, fontSize: 13),
            ),
          ],
        ),
        Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              snapshot.hasCompleteRuntimeSample ? '当前状态' : '部分数据',
              style: const TextStyle(color: LumenisTheme.muted, fontSize: 12),
            ),
            const SizedBox(width: 8),
            IconButton(
              tooltip: '刷新运行状态',
              onPressed: onRefresh,
              icon: const Icon(Icons.refresh_rounded),
              color: LumenisTheme.system,
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
    final label = _overallLabel(snapshot.overall);
    final color = _stateColor(snapshot.overallState);
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
        color: LumenisTheme.surface,
        border: Border.all(
          color: available ? color.withValues(alpha: 0.48) : LumenisTheme.line,
        ),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 10,
            height: 10,
            margin: const EdgeInsets.only(top: 7),
            decoration: BoxDecoration(color: color, shape: BoxShape.circle),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  '系统整体状态',
                  style: TextStyle(color: LumenisTheme.muted, fontSize: 13),
                ),
                const SizedBox(height: 6),
                Semantics(
                  liveRegion: true,
                  label: '系统整体状态：${available ? label : '暂不可用'}',
                  child: Text(
                    available ? label : '暂不可用',
                    style: TextStyle(
                      color: available ? color : LumenisTheme.muted,
                      fontSize: 23,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
                if (available) ...[
                  const SizedBox(height: 4),
                  Text(
                    '本次系统状态检查已完成',
                    style: const TextStyle(
                      color: LumenisTheme.quiet,
                      fontSize: 12,
                    ),
                  ),
                ] else ...[
                  const SizedBox(height: 4),
                  const Text(
                    '当前无法确认系统整体状态',
                    style: TextStyle(color: LumenisTheme.muted, fontSize: 12),
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(width: 8),
          _StateTag(label: available ? label : '暂不可用', color: color),
        ],
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
      title: '后台任务与失败队列',
      detail: '展示当前已确认的数量；暂未提供的数据会单独标明。',
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
  const _CountCard({required this.label, required this.count});

  final String label;
  final Sys01Count count;

  @override
  Widget build(BuildContext context) {
    return _Panel(
      key: ValueKey('sys01/count-${_countKey(label)}'),
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
              style: const TextStyle(color: LumenisTheme.muted),
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
      label: available ? '$value' : '系统状态暂不可用',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          Text(
            available ? '$value' : '—',
            style: TextStyle(
              color: available ? LumenisTheme.foreground : LumenisTheme.muted,
              fontSize: compact ? 20 : 30,
              height: 1.15,
              fontWeight: FontWeight.w600,
              fontFeatures: const [FontFeature.tabularFigures()],
            ),
          ),
          if (!available) ...[
            const SizedBox(height: 3),
            Text(
              count.state == 'offline' ? '当前不可用' : '暂未提供',
              style: const TextStyle(color: LumenisTheme.quiet, fontSize: 11),
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
      title: '服务保护状态',
      detail: snapshot.hasCompleteRuntimeSample ? '本次检查数据完整' : '部分服务状态暂无法确认',
      child: Column(
        children: [
          _GuardrailLine(
            label: '过期任务回收服务',
            value: _reaperLabel(snapshot.reaperRunning),
            color: snapshot.reaperRunning == true
                ? LumenisTheme.positive
                : snapshot.reaperRunning == false
                ? LumenisTheme.caution
                : LumenisTheme.muted,
          ),
          const _Rule(),
          _GuardrailLine(
            label: '已触发的调用保护',
            value: snapshot.openBreakers?.toString() ?? '暂不可用',
            color: _breakerColor(snapshot.openBreakers),
          ),
          const _Rule(),
          _GuardrailLine(
            label: '已配置的调用保护',
            value: snapshot.registeredBreakers?.toString() ?? '暂不可用',
            color: snapshot.registeredBreakers == null
                ? LumenisTheme.muted
                : LumenisTheme.foreground,
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
        color: LumenisTheme.surface,
        border: Border.all(color: LumenisTheme.line),
        borderRadius: BorderRadius.circular(12),
      ),
      child: ExpansionTile(
        key: const ValueKey('sys01/guardrail-inspector'),
        title: const Text('服务保护状态'),
        subtitle: Text(
          snapshot.hasCompleteRuntimeSample ? '查看任务回收与调用保护' : '部分服务状态暂无法确认',
          style: const TextStyle(color: LumenisTheme.muted, fontSize: 12),
        ),
        iconColor: LumenisTheme.system,
        collapsedIconColor: LumenisTheme.muted,
        childrenPadding: const EdgeInsets.fromLTRB(14, 0, 14, 14),
        children: [_GuardrailPanel(snapshot: snapshot)],
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
              style: const TextStyle(color: LumenisTheme.muted),
            ),
          ),
          Text(
            value,
            style: TextStyle(color: color, fontWeight: FontWeight.w600),
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
      title: '数据来源与更新时间',
      detail: '每次打开或刷新时读取当前状态',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _SourceLine(label: '状态来源', value: '系统运行监测'),
          if (snapshot.guardianName != null) ...[
            const _Rule(),
            const _SourceLine(label: '运行服务状态', value: '已识别'),
          ],
          const _Rule(),
          _SourceLine(
            label: '状态检查时间',
            value: snapshot.sampleTimestamp ?? '未提供',
            emphasize: true,
          ),
          const SizedBox(height: 12),
          const Text(
            '显示时间来自系统运行状态检查记录。',
            style: TextStyle(
              color: LumenisTheme.quiet,
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
            style: const TextStyle(color: LumenisTheme.quiet, fontSize: 11),
          ),
          const SizedBox(height: 4),
          SelectableText(
            value,
            style: TextStyle(
              color: emphasize ? LumenisTheme.system : LumenisTheme.foreground,
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
        color: LumenisTheme.surface,
        border: Border.all(color: LumenisTheme.line),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: const TextStyle(
              color: LumenisTheme.foreground,
              fontSize: 16,
              fontWeight: FontWeight.w600,
            ),
          ),
          if (detail != null) ...[
            const SizedBox(height: 4),
            Text(
              detail!,
              style: const TextStyle(
                color: LumenisTheme.quiet,
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
    style: const TextStyle(
      color: LumenisTheme.system,
      fontSize: 10,
      letterSpacing: 1.2,
      fontWeight: FontWeight.w600,
    ),
  );
}

class _Rule extends StatelessWidget {
  const _Rule();

  @override
  Widget build(BuildContext context) =>
      const SizedBox(height: 1, child: ColoredBox(color: LumenisTheme.line));
}

String _overallLabel(String? value) => switch (value?.toLowerCase()) {
  'healthy' || 'ok' => '正常',
  'degraded' => '部分异常',
  'unhealthy' => '异常',
  'error' => '异常',
  _ => '暂不可用',
};

String _reaperLabel(bool? running) => switch (running) {
  true => '运行中',
  false => '已停止',
  null => '暂不可用',
};

Color _stateColor(String state) => switch (state) {
  'ok' || 'ready' => LumenisTheme.positive,
  'warn' || 'idle' => LumenisTheme.caution,
  'bad' || 'error' => LumenisTheme.danger,
  _ => LumenisTheme.muted,
};

Color _breakerColor(int? count) => count == null
    ? LumenisTheme.muted
    : count > 0
    ? LumenisTheme.danger
    : LumenisTheme.positive;

String _countKey(String label) => switch (label) {
  '后台进程总数' => 'registered-workers',
  '异常后台进程' => 'failed-workers',
  '失败队列记录总数' => 'dlq',
  _ => 'metric',
};
