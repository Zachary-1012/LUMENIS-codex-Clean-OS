import 'package:flutter/material.dart';

import '../../core/lumenis_core_client.dart';
import '../../core/lumenis_theme.dart';
import 'bmp01_repository.dart';
import 'bmp01_snapshot.dart';
import 'bmp01_view_model.dart';

class Bmp01Screen extends StatefulWidget {
  const Bmp01Screen({required this.client, this.repository, super.key});

  final LumenisCoreClient client;
  final Bmp01Repository? repository;

  @override
  State<Bmp01Screen> createState() => _Bmp01ScreenState();
}

class _Bmp01ScreenState extends State<Bmp01Screen> {
  late final Bmp01ViewModel _viewModel = Bmp01ViewModel(
    repository: widget.repository ?? CoreBmp01Repository(client: widget.client),
  );

  @override
  void initState() {
    super.initState();
    _viewModel.refresh();
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
            Bmp01LoadPhase.loading => const _LoadingState(),
            Bmp01LoadPhase.failed => _FailureState(
              kind: _viewModel.failureKind!,
              onRetry: _viewModel.refresh,
            ),
            Bmp01LoadPhase.ready => _ScopeWorkspace(
              snapshot: _viewModel.snapshot!,
              onRefresh: _viewModel.refresh,
            ),
          },
        ),
      ),
    );
  }
}

class _ScopeWorkspace extends StatelessWidget {
  const _ScopeWorkspace({required this.snapshot, required this.onRefresh});

  final Bmp01Snapshot snapshot;
  final VoidCallback onRefresh;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final wide = constraints.maxWidth >= 960;
        final inset = wide ? 34.0 : 18.0;

        return Align(
          alignment: Alignment.topCenter,
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1320),
            child: SingleChildScrollView(
              padding: EdgeInsets.fromLTRB(inset, 26, inset, 40),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const _Heading(),
                  const SizedBox(height: 22),
                  if (wide)
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const SizedBox(width: 278, child: _BrandFocusRail()),
                        const SizedBox(width: 18),
                        Expanded(
                          child: _LineageCanvas(
                            snapshot: snapshot,
                            onRefresh: onRefresh,
                          ),
                        ),
                      ],
                    )
                  else ...[
                    const _BrandFocusRail(),
                    const SizedBox(height: 14),
                    _LineageCanvas(snapshot: snapshot, onRefresh: onRefresh),
                  ],
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}

class _Heading extends StatelessWidget {
  const _Heading();

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Container(
              width: 8,
              height: 28,
              decoration: BoxDecoration(
                color: LumenisTheme.bmp,
                borderRadius: BorderRadius.circular(8),
              ),
            ),
            const SizedBox(width: 11),
            Text(
              'BMP  /  BRAND & MARKET',
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                color: LumenisTheme.bmp,
                letterSpacing: 1.1,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ),
        const SizedBox(height: 13),
        Text(
          '品牌市场总览',
          style: Theme.of(context).textTheme.headlineMedium?.copyWith(
            color: LumenisTheme.foreground,
            fontWeight: FontWeight.w600,
            letterSpacing: -0.5,
          ),
        ),
        const SizedBox(height: 7),
        Text(
          '先确认 BrandFocus 与证据归属，再展示市场真值。',
          style: Theme.of(
            context,
          ).textTheme.bodyMedium?.copyWith(color: LumenisTheme.muted),
        ),
      ],
    );
  }
}

class _BrandFocusRail extends StatelessWidget {
  const _BrandFocusRail();

  @override
  Widget build(BuildContext context) {
    return _Panel(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _Eyebrow('ACTIVE BRANDFOCUS'),
          const SizedBox(height: 18),
          Container(
            width: 54,
            height: 54,
            decoration: BoxDecoration(
              color: LumenisTheme.bmp.withValues(alpha: 0.10),
              border: Border.all(
                color: LumenisTheme.bmp.withValues(alpha: 0.38),
              ),
              borderRadius: BorderRadius.circular(16),
            ),
            child: const Icon(
              Icons.storefront_outlined,
              color: LumenisTheme.bmp,
              size: 25,
            ),
          ),
          const SizedBox(height: 16),
          const Text(
            '品牌焦点未确认',
            style: TextStyle(
              color: LumenisTheme.foreground,
              fontSize: 19,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 8),
          const Text(
            'Product Core 当前响应没有返回已授权的 BrandFocus。品牌与市场指标保持隐藏。',
            style: TextStyle(color: LumenisTheme.muted, height: 1.6),
          ),
          const SizedBox(height: 18),
          const Divider(height: 1),
          const SizedBox(height: 17),
          const _ScopeRequirement(
            number: '01',
            title: '当前操作者',
            detail: '屏幕契约未提供 actor 绑定',
          ),
          const SizedBox(height: 15),
          const _ScopeRequirement(
            number: '02',
            title: '授权品牌',
            detail: '没有可验证的 BrandFocus',
          ),
          const SizedBox(height: 15),
          const _ScopeRequirement(
            number: '03',
            title: '读取权限',
            detail: '没有此屏的 Permission 决策',
          ),
        ],
      ),
    );
  }
}

class _LineageCanvas extends StatelessWidget {
  const _LineageCanvas({required this.snapshot, required this.onRefresh});

  final Bmp01Snapshot snapshot;
  final VoidCallback onRefresh;

  @override
  Widget build(BuildContext context) {
    final ownerMatches = snapshot.isBmpOwner;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _Panel(
          padding: const EdgeInsets.fromLTRB(20, 20, 20, 22),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Expanded(child: _Eyebrow('MARKET / EVIDENCE PATH')),
                  _ContractBadge(
                    label: !snapshot.contractBound
                        ? '契约未绑定'
                        : ownerMatches
                        ? 'ZBMP · zbmp'
                        : '归属待核验',
                    available: snapshot.contractBound && ownerMatches,
                  ),
                ],
              ),
              const SizedBox(height: 22),
              _LineageStep(
                number: 'A',
                title: '操作者与读取权限',
                detail: '身份 / Permission 未由此屏响应证明',
                state: _StepState.blocked,
              ),
              const _Connector(),
              _LineageStep(
                number: 'B',
                title: '已授权 BrandFocus',
                detail: '等待 BMP owner 提供可验证的品牌范围',
                state: _StepState.blocked,
              ),
              const _Connector(),
              _LineageStep(
                number: 'C',
                title: 'ZBMP Canonical Data',
                detail: ownerMatches
                    ? 'Core 返回 ZBMP / zbmp 产品快照；当前未按品牌聚合'
                    : '当前响应尚未验证为 ZBMP / zbmp',
                state: ownerMatches ? _StepState.pending : _StepState.blocked,
              ),
              const _Connector(),
              const _LineageStep(
                number: 'D',
                title: 'Shared Evidence Trace',
                detail: '尚无可核验的品牌级 Evidence 关联',
                state: _StepState.blocked,
              ),
              const SizedBox(height: 20),
              _DataContractNotice(snapshot: snapshot),
            ],
          ),
        ),
        if (snapshot.blockedFields.isNotEmpty) ...[
          const SizedBox(height: 14),
          _SourceGaps(fields: snapshot.blockedFields),
        ],
        const SizedBox(height: 14),
        Align(
          alignment: Alignment.centerLeft,
          child: OutlinedButton.icon(
            onPressed: onRefresh,
            icon: const Icon(Icons.refresh_rounded),
            label: const Text('重新读取产品契约'),
            style: OutlinedButton.styleFrom(minimumSize: const Size(48, 48)),
          ),
        ),
      ],
    );
  }
}

class _DataContractNotice extends StatelessWidget {
  const _DataContractNotice({required this.snapshot});

  final Bmp01Snapshot snapshot;

  @override
  Widget build(BuildContext context) {
    final text = !snapshot.isBmpOwner
        ? '响应归属不匹配，未展示任何品牌指标。'
        : snapshot.isNotCollected
        ? 'ZBMP 产品源当前没有已采集的 Canonical Data。此状态不代表品牌级零值。'
        : snapshot.dataState == 'READY'
        ? 'Core 返回了产品级快照。由于品牌范围和 Evidence lineage 未验证，指标、曲线与风险记录保持隐藏。'
        : '数据状态为 ${snapshot.dataState}。品牌范围与 Evidence lineage 未验证，业务指标保持隐藏。';

    return Semantics(
      liveRegion: true,
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: LumenisTheme.caution.withValues(alpha: 0.08),
          border: Border.all(
            color: LumenisTheme.caution.withValues(alpha: 0.3),
          ),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Icon(
              Icons.visibility_off_outlined,
              color: LumenisTheme.caution,
              size: 19,
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                text,
                style: const TextStyle(
                  color: LumenisTheme.foreground,
                  height: 1.5,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _SourceGaps extends StatelessWidget {
  const _SourceGaps({required this.fields});

  final List<Bmp01BlockedField> fields;

  @override
  Widget build(BuildContext context) {
    return _Panel(
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _Eyebrow('SOURCE-RETURNED GAPS'),
          const SizedBox(height: 12),
          for (final field in fields) ...[
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Icon(
                  Icons.remove_circle_outline,
                  size: 17,
                  color: LumenisTheme.quiet,
                ),
                const SizedBox(width: 9),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        field.field,
                        style: const TextStyle(fontWeight: FontWeight.w600),
                      ),
                      const SizedBox(height: 3),
                      Text(
                        field.reason,
                        style: const TextStyle(
                          color: LumenisTheme.muted,
                          height: 1.4,
                        ),
                      ),
                      if (field.required.isNotEmpty) ...[
                        const SizedBox(height: 3),
                        Text(
                          '需要：${field.required}',
                          style: const TextStyle(
                            color: LumenisTheme.quiet,
                            fontSize: 12,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ],
            ),
            if (field != fields.last) const Divider(height: 24),
          ],
        ],
      ),
    );
  }
}

enum _StepState { blocked, pending }

class _LineageStep extends StatelessWidget {
  const _LineageStep({
    required this.number,
    required this.title,
    required this.detail,
    required this.state,
  });

  final String number;
  final String title;
  final String detail;
  final _StepState state;

  @override
  Widget build(BuildContext context) {
    final isPending = state == _StepState.pending;
    final color = isPending ? LumenisTheme.caution : LumenisTheme.quiet;

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: 30,
          height: 30,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: color.withValues(alpha: 0.1),
            border: Border.all(color: color.withValues(alpha: 0.42)),
            borderRadius: BorderRadius.circular(9),
          ),
          child: Text(
            number,
            style: TextStyle(
              color: color,
              fontWeight: FontWeight.w700,
              fontSize: 11,
            ),
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Padding(
            padding: const EdgeInsets.only(top: 1),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(fontWeight: FontWeight.w600),
                ),
                const SizedBox(height: 4),
                Text(
                  detail,
                  style: const TextStyle(
                    color: LumenisTheme.muted,
                    height: 1.45,
                  ),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(width: 8),
        Icon(
          isPending ? Icons.hourglass_top_rounded : Icons.lock_outline_rounded,
          size: 17,
          color: color,
          semanticLabel: isPending ? '待确认' : '阻断',
        ),
      ],
    );
  }
}

class _Connector extends StatelessWidget {
  const _Connector();

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(left: 14, top: 7, bottom: 7),
      child: Container(width: 1, height: 16, color: LumenisTheme.line),
    );
  }
}

class _ScopeRequirement extends StatelessWidget {
  const _ScopeRequirement({
    required this.number,
    required this.title,
    required this.detail,
  });

  final String number;
  final String title;
  final String detail;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          number,
          style: const TextStyle(
            color: LumenisTheme.bmp,
            fontSize: 11,
            fontWeight: FontWeight.w700,
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: const TextStyle(fontWeight: FontWeight.w600)),
              const SizedBox(height: 3),
              Text(
                detail,
                style: const TextStyle(
                  color: LumenisTheme.muted,
                  fontSize: 12,
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

class _ContractBadge extends StatelessWidget {
  const _ContractBadge({required this.label, required this.available});

  final String label;
  final bool available;

  @override
  Widget build(BuildContext context) {
    final color = available ? LumenisTheme.bmp : LumenisTheme.caution;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        border: Border.all(color: color.withValues(alpha: 0.28)),
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
  Widget build(BuildContext context) {
    return Text(
      label,
      style: const TextStyle(
        color: LumenisTheme.quiet,
        fontSize: 10,
        letterSpacing: 1,
        fontWeight: FontWeight.w700,
      ),
    );
  }
}

class _Panel extends StatelessWidget {
  const _Panel({required this.child, this.padding = const EdgeInsets.all(18)});

  final Widget child;
  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: padding,
      decoration: BoxDecoration(
        color: LumenisTheme.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: LumenisTheme.line),
      ),
      child: child,
    );
  }
}

class _LoadingState extends StatelessWidget {
  const _LoadingState();

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Semantics(
        liveRegion: true,
        label: '正在读取 BMP-01 品牌市场契约',
        child: const CircularProgressIndicator(color: LumenisTheme.bmp),
      ),
    );
  }
}

class _FailureState extends StatelessWidget {
  const _FailureState({required this.kind, required this.onRetry});

  final Bmp01FailureKind kind;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final (title, detail) = switch (kind) {
      Bmp01FailureKind.authentication => (
        '需要登录',
        '请先完成 Product Core 登录，再重新读取 BMP-01。',
      ),
      Bmp01FailureKind.permissionDenied => (
        '访问被拒绝',
        '当前账号没有读取此来源的权限。品牌数据不会显示。',
      ),
      Bmp01FailureKind.offline => (
        'Product Core 未连接',
        '当前无法读取 BMP-01 来源。恢复连接后可以重新读取。',
      ),
      Bmp01FailureKind.server => ('品牌市场来源暂不可用', '当前来源没有返回可验证的 BMP-01 合约。'),
    };

    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 520),
          child: _Panel(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: Theme.of(context).textTheme.titleLarge),
                const SizedBox(height: 8),
                Text(detail, style: Theme.of(context).textTheme.bodyMedium),
                const SizedBox(height: 16),
                OutlinedButton.icon(
                  onPressed: onRetry,
                  icon: const Icon(Icons.refresh_rounded),
                  label: const Text('重新读取'),
                  style: OutlinedButton.styleFrom(
                    minimumSize: const Size(48, 48),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
