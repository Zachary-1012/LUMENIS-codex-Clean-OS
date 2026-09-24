import 'package:flutter/material.dart';

import '../../core/lumenis_core_client.dart';
import '../../core/lumenis_theme.dart';
import '../../l10n/lumenis_localizations.dart';
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
      color: LumenisTheme.of(context).canvas,
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
                        SizedBox(
                          width: 278,
                          child: _BrandFocusRail(snapshot: snapshot),
                        ),
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
                    _BrandFocusRail(snapshot: snapshot),
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
                color: LumenisTheme.of(context).bmp,
                borderRadius: BorderRadius.circular(8),
              ),
            ),
            const SizedBox(width: 11),
            Text(
              context.lumenisL10n.text('bmp01.eyebrow'),
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                color: LumenisTheme.of(context).bmp,
                letterSpacing: 1.1,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ),
        const SizedBox(height: 13),
        Text(
          context.lumenisL10n.text('bmp01.title'),
          style: Theme.of(context).textTheme.headlineMedium?.copyWith(
            color: LumenisTheme.of(context).foreground,
            fontWeight: FontWeight.w600,
            letterSpacing: -0.5,
          ),
        ),
        const SizedBox(height: 7),
        Text(
          context.lumenisL10n.text('bmp01.subtitle'),
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
            color: LumenisTheme.of(context).muted,
          ),
        ),
      ],
    );
  }
}

class _BrandFocusRail extends StatelessWidget {
  const _BrandFocusRail({required this.snapshot});

  final Bmp01Snapshot snapshot;

  @override
  Widget build(BuildContext context) {
    return _Panel(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _Eyebrow(context.lumenisL10n.text('bmp01.focus.eyebrow')),
          const SizedBox(height: 18),
          Container(
            width: 54,
            height: 54,
            decoration: BoxDecoration(
              color: LumenisTheme.of(context).bmp.withValues(alpha: 0.10),
              border: Border.all(
                color: LumenisTheme.of(context).bmp.withValues(alpha: 0.38),
              ),
              borderRadius: BorderRadius.circular(16),
            ),
            child: Icon(
              Icons.storefront_outlined,
              color: LumenisTheme.of(context).bmp,
              size: 25,
            ),
          ),
          const SizedBox(height: 16),
          if (snapshot.focusContext.isGlobal && snapshot.isNotCollected) ...[
            Text(
              context.lumenisL10n.text('bmp01.focus.global'),
              style: TextStyle(
                color: LumenisTheme.of(context).bmp,
                fontSize: 12,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 6),
          ],
          Text(
            _focusTitle(context),
            style: TextStyle(
              color: LumenisTheme.of(context).foreground,
              fontSize: 19,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            _focusDetail(context),
            style: TextStyle(
              color: LumenisTheme.of(context).muted,
              height: 1.6,
            ),
          ),
        ],
      ),
    );
  }

  String _focusTitle(BuildContext context) {
    final name = snapshot.focusContext.localizedName(
      Localizations.localeOf(context).languageCode == 'zh'
          ? 'zh-CN'
          : Localizations.localeOf(context).languageCode,
    );
    if (snapshot.focusContext.isFocus && name != null) {
      return context.lumenisL10n.text(
        'bmp01.focus.selected',
        values: {'name': name},
      );
    }
    if (snapshot.focusContext.isFocus) {
      return context.lumenisL10n.text('bmp01.focus.unavailable');
    }
    if (snapshot.isNotCollected) {
      return context.lumenisL10n.text('bmp01.focus.empty.title');
    }
    return context.lumenisL10n.text('bmp01.focus.global');
  }

  String _focusDetail(BuildContext context) =>
      context.lumenisL10n.text('bmp01.focus.empty.detail');
}

class _MarketOverview extends StatelessWidget {
  const _MarketOverview({required this.snapshot, required this.onRefresh});

  final Bmp01Snapshot snapshot;
  final VoidCallback onRefresh;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    final ownerMatches = snapshot.isBmpOwner;
    final metricsReady = snapshot.canDisplayMetrics;
    final title = !ownerMatches
        ? copy.text('bmp01.market.blocked.title')
        : snapshot.isNotCollected
        ? copy.text('bmp01.market.not_collected.title')
        : metricsReady
        ? copy.text('bmp01.market.ready.title')
        : snapshot.focusContext.isGlobal
        ? copy.text('bmp01.market.global.title')
        : copy.text('bmp01.market.blocked.title');
    final detail = !ownerMatches
        ? copy.text('bmp01.market.blocked.detail')
        : snapshot.isNotCollected
        ? copy.text('bmp01.market.not_collected.detail')
        : metricsReady
        ? copy.text('bmp01.market.ready.detail')
        : snapshot.focusContext.isGlobal
        ? copy.text('bmp01.market.global.detail')
        : copy.text('bmp01.market.blocked.detail');

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _Panel(
          padding: const EdgeInsets.fromLTRB(24, 22, 24, 24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _Eyebrow(copy.text('bmp01.market.eyebrow')),
              const SizedBox(height: 24),
              Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 460),
                  child: Column(
                    children: [
                      const _BrandSignalMark(),
                      const SizedBox(height: 24),
                      Semantics(
                        liveRegion: true,
                        label: '$title. $detail',
                        child: Text(
                          title,
                          textAlign: TextAlign.center,
                          style: Theme.of(context).textTheme.titleLarge
                              ?.copyWith(
                                color: LumenisTheme.of(context).foreground,
                                fontWeight: FontWeight.w600,
                              ),
                        ),
                      ),
                      if (metricsReady) ...[
                        const SizedBox(height: 22),
                        _ScopedMetricSpine(metrics: snapshot.metrics),
                      ],
                      const SizedBox(height: 9),
                      Text(
                        detail,
                        textAlign: TextAlign.center,
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: LumenisTheme.of(context).muted,
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
            label: Text(copy.text('bmp01.refresh')),
            style: OutlinedButton.styleFrom(minimumSize: const Size(48, 48)),
          ),
        ),
      ],
    );
  }
}

class _ScopedMetricSpine extends StatelessWidget {
  const _ScopedMetricSpine({required this.metrics});

  final List<Bmp01Metric> metrics;

  @override
  Widget build(BuildContext context) {
    final visible = metrics.where((metric) => metric.isReady).toList();
    if (visible.isEmpty) return const SizedBox.shrink();
    return Semantics(
      container: true,
      label: context.lumenisL10n.text('bmp01.metrics.label'),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          for (var index = 0; index < visible.length; index++) ...[
            if (index > 0) const Divider(height: 1),
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 11),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      visible[index].label,
                      style: TextStyle(color: LumenisTheme.of(context).muted),
                    ),
                  ),
                  Text(
                    visible[index].safeValueText!,
                    style: TextStyle(
                      color: LumenisTheme.of(context).foreground,
                      fontSize: 20,
                      fontWeight: FontWeight.w600,
                      fontFeatures: [FontFeature.tabularFigures()],
                    ),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
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
                  color: LumenisTheme.of(
                    context,
                  ).bmp.withValues(alpha: size == 142 ? 0.16 : 0.24),
                ),
              ),
            ),
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: LumenisTheme.of(context).bmp.withValues(alpha: 0.12),
              border: Border.all(
                color: LumenisTheme.of(context).bmp.withValues(alpha: 0.5),
              ),
            ),
            child: Icon(
              Icons.local_offer_outlined,
              color: LumenisTheme.of(context).bmp,
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
      style: TextStyle(
        color: LumenisTheme.of(context).quiet,
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
        color: LumenisTheme.of(context).surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: LumenisTheme.of(context).line),
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
        label: context.lumenisL10n.text('bmp01.loading'),
        child: CircularProgressIndicator(color: LumenisTheme.of(context).bmp),
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
    final copy = context.lumenisL10n;
    final (title, detail) = switch (kind) {
      Bmp01FailureKind.authentication => (
        copy.text('bmp01.failure.auth.title'),
        copy.text('bmp01.failure.auth.detail'),
      ),
      Bmp01FailureKind.permissionDenied => (
        copy.text('bmp01.failure.permission.title'),
        copy.text('bmp01.failure.permission.detail'),
      ),
      Bmp01FailureKind.offline => (
        copy.text('bmp01.failure.offline.title'),
        copy.text('bmp01.failure.offline.detail'),
      ),
      Bmp01FailureKind.server => (
        copy.text('bmp01.failure.server.title'),
        copy.text('bmp01.failure.server.detail'),
      ),
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
                  label: Text(copy.text('bmp01.retry')),
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
