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
                          child: _MarketOverview(
                            snapshot: snapshot,
                            onRefresh: onRefresh,
                          ),
                        ),
                      ],
                    )
                  else ...[
                    const _BrandFocusRail(),
                    const SizedBox(height: 14),
                    _MarketOverview(snapshot: snapshot, onRefresh: onRefresh),
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
              'BMP · 品牌市场',
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
          '围绕品牌，持续了解市场变化、竞品动态与消费者关注。',
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
          const _Eyebrow('关注品牌'),
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
            '暂无可展示的品牌信息',
            style: TextStyle(
              color: LumenisTheme.foreground,
              fontSize: 19,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 8),
          const Text(
            '目前无法呈现品牌表现。品牌数据准备好后，会在这里汇总品牌与市场动态。',
            style: TextStyle(color: LumenisTheme.muted, height: 1.6),
          ),
        ],
      ),
    );
  }
}

class _MarketOverview extends StatelessWidget {
  const _MarketOverview({required this.snapshot, required this.onRefresh});

  final Bmp01Snapshot snapshot;
  final VoidCallback onRefresh;

  @override
  Widget build(BuildContext context) {
    final ownerMatches = snapshot.isBmpOwner;
    final title = !ownerMatches
        ? '品牌市场信息暂不可用'
        : snapshot.isNotCollected
        ? '暂时没有品牌市场数据'
        : snapshot.dataState == 'READY'
        ? '尚未选择关注品牌'
        : '品牌市场信息暂不可用';
    final detail = !ownerMatches
        ? '请刷新后重试，当前不会展示未经确认的品牌信息。'
        : snapshot.isNotCollected
        ? '品牌表现、竞品动态与市场变化会在数据可用后呈现。'
        : snapshot.dataState == 'READY'
        ? '当前没有已确认的关注品牌，因此暂不展示品牌表现或竞品数据。'
        : '请刷新后重试，当前不会展示未经确认的品牌信息。';

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _Panel(
          padding: const EdgeInsets.fromLTRB(24, 22, 24, 24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const _Eyebrow('品牌市场动态'),
              const SizedBox(height: 24),
              Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 460),
                  child: Column(
                    children: [
                      const _BrandSignalMark(),
                      const SizedBox(height: 24),
                      Text(
                        title,
                        textAlign: TextAlign.center,
                        style: Theme.of(context).textTheme.titleLarge?.copyWith(
                          color: LumenisTheme.foreground,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      const SizedBox(height: 9),
                      Text(
                        detail,
                        textAlign: TextAlign.center,
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: LumenisTheme.muted,
                          height: 1.6,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 14),
        Align(
          alignment: Alignment.centerLeft,
          child: OutlinedButton.icon(
            onPressed: onRefresh,
            icon: const Icon(Icons.refresh_rounded),
            label: const Text('刷新数据'),
            style: OutlinedButton.styleFrom(minimumSize: const Size(48, 48)),
          ),
        ),
      ],
    );
  }
}

class _BrandSignalMark extends StatelessWidget {
  const _BrandSignalMark();

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 142,
      height: 142,
      child: Stack(
        alignment: Alignment.center,
        children: [
          for (final size in const [142.0, 104.0, 66.0])
            Container(
              width: size,
              height: size,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                border: Border.all(
                  color: LumenisTheme.bmp.withValues(
                    alpha: size == 142 ? 0.16 : 0.24,
                  ),
                ),
              ),
            ),
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: LumenisTheme.bmp.withValues(alpha: 0.12),
              border: Border.all(
                color: LumenisTheme.bmp.withValues(alpha: 0.5),
              ),
            ),
            child: const Icon(
              Icons.local_offer_outlined,
              color: LumenisTheme.bmp,
              size: 20,
            ),
          ),
        ],
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
        label: '正在加载品牌市场信息',
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
      Bmp01FailureKind.authentication => ('需要登录', '登录后即可查看品牌市场信息。'),
      Bmp01FailureKind.permissionDenied => ('当前账号暂时无法查看此内容', '如需访问，请联系管理员。'),
      Bmp01FailureKind.offline => ('暂时无法连接', '请检查网络连接后重试。'),
      Bmp01FailureKind.server => ('品牌市场信息暂不可用', '请稍后重试。'),
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
                  label: const Text('重试'),
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
