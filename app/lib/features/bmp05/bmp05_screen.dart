import 'package:flutter/material.dart';

import '../../core/lumenis_core_client.dart';
import '../../core/lumenis_theme.dart';
import '../../l10n/lumenis_localizations.dart';
import 'bmp05_repository.dart';
import 'bmp05_snapshot.dart';
import 'bmp05_view_model.dart';

class Bmp05Screen extends StatefulWidget {
  const Bmp05Screen({required this.client, this.repository, super.key});

  final LumenisCoreClient client;
  final Bmp05Repository? repository;

  @override
  State<Bmp05Screen> createState() => _Bmp05ScreenState();
}

class _Bmp05ScreenState extends State<Bmp05Screen> {
  late final Bmp05ViewModel _viewModel = Bmp05ViewModel(
    repository: widget.repository ?? CoreBmp05Repository(client: widget.client),
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
            Bmp05LoadPhase.loading => const _LoadingState(),
            Bmp05LoadPhase.failed => _FailureState(
              kind: _viewModel.failureKind!,
              onRetry: _viewModel.refresh,
            ),
            Bmp05LoadPhase.ready => _ReadyState(
              snapshot: _viewModel.snapshot!,
              viewModel: _viewModel,
            ),
          },
        ),
      ),
    );
  }
}

class _ReadyState extends StatelessWidget {
  const _ReadyState({required this.snapshot, required this.viewModel});

  final Bmp05Snapshot snapshot;
  final Bmp05ViewModel viewModel;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final compact = constraints.maxWidth < 720;
        final inset = compact ? 18.0 : 34.0;
        return Align(
          alignment: Alignment.topCenter,
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1420),
            child: SingleChildScrollView(
              padding: EdgeInsets.fromLTRB(inset, 26, inset, 40),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const _PageHeading(),
                  const SizedBox(height: 20),
                  _FocusBand(snapshot: snapshot),
                  const SizedBox(height: 20),
                  if (snapshot.presentationState ==
                          Bmp05PresentationState.ready ||
                      snapshot.presentationState ==
                          Bmp05PresentationState.partial ||
                      snapshot.presentationState ==
                          Bmp05PresentationState.stale)
                    _CreatorWorkspace(
                      snapshot: snapshot,
                      viewModel: viewModel,
                      compact: compact,
                    )
                  else
                    _AvailabilityPanel(
                      snapshot: snapshot,
                      onRetry: viewModel.refresh,
                    ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}

class _PageHeading extends StatelessWidget {
  const _PageHeading();

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          copy.text('screen.BMP-05'),
          style: Theme.of(context).textTheme.headlineMedium?.copyWith(
            color: LumenisTheme.of(context).foreground,
            fontWeight: FontWeight.w600,
            letterSpacing: -0.5,
          ),
        ),
        const SizedBox(height: 7),
        Text(
          copy.text('common.detail'),
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
            color: LumenisTheme.of(context).muted,
          ),
        ),
      ],
    );
  }
}

class _FocusBand extends StatelessWidget {
  const _FocusBand({required this.snapshot});

  final Bmp05Snapshot snapshot;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    final languageCode = Localizations.localeOf(context).languageCode == 'zh'
        ? 'zh-CN'
        : Localizations.localeOf(context).languageCode;
    final name = snapshot.focus.localizedName(languageCode);
    final title = name == null
        ? copy.text('bmp01.focus.global')
        : copy.text('shell.bmp.brand_named', values: {'name': name});
    final detail = copy.text('context.selector.scope_note');
    return Semantics(
      container: true,
      liveRegion: true,
      label: '$title. $detail',
      child: _Panel(
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(
              Icons.center_focus_strong,
              color: LumenisTheme.of(context).bmp,
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: TextStyle(
                      color: LumenisTheme.of(context).foreground,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    detail,
                    style: TextStyle(
                      color: LumenisTheme.of(context).muted,
                      height: 1.45,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _CreatorWorkspace extends StatelessWidget {
  const _CreatorWorkspace({
    required this.snapshot,
    required this.viewModel,
    required this.compact,
  });

  final Bmp05Snapshot snapshot;
  final Bmp05ViewModel viewModel;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final creators = viewModel.filteredCreators;
    final tiers = snapshot.creators.map((creator) => creator.tier).toSet();
    final risks = snapshot.creators
        .map((creator) => creator.risk?.level)
        .whereType<String>()
        .toSet();
    final selected = viewModel.selectedCreator;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _CreatorFilters(
          tiers: tiers.toList(),
          risks: risks.toList(),
          selectedTier: viewModel.tierFilter,
          selectedRisk: viewModel.riskFilter,
          onTierChanged: viewModel.setTierFilter,
          onRiskChanged: viewModel.setRiskFilter,
        ),
        const SizedBox(height: 18),
        if (creators.isEmpty)
          const _FilteredEmpty()
        else if (compact)
          Column(
            children: [
              _CreatorRoster(
                creators: creators,
                selectedId: viewModel.selectedCreatorId,
                onSelect: viewModel.selectCreator,
              ),
              const SizedBox(height: 14),
              _CreatorDossier(creator: selected),
            ],
          )
        else
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                flex: 7,
                child: _CreatorRoster(
                  creators: creators,
                  selectedId: viewModel.selectedCreatorId,
                  onSelect: viewModel.selectCreator,
                ),
              ),
              const SizedBox(width: 18),
              Expanded(flex: 5, child: _CreatorDossier(creator: selected)),
            ],
          ),
      ],
    );
  }
}

class _CreatorFilters extends StatelessWidget {
  const _CreatorFilters({
    required this.tiers,
    required this.risks,
    required this.selectedTier,
    required this.selectedRisk,
    required this.onTierChanged,
    required this.onRiskChanged,
  });

  final List<String> tiers;
  final List<String> risks;
  final String? selectedTier;
  final String? selectedRisk;
  final ValueChanged<String?> onTierChanged;
  final ValueChanged<String?> onRiskChanged;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    return _Panel(
      child: Wrap(
        spacing: 9,
        runSpacing: 9,
        children: [
          FilterChip(
            selected: selectedTier == null && selectedRisk == null,
            label: Text(copy.text('common.all')),
            onSelected: (_) {
              onTierChanged(null);
              onRiskChanged(null);
            },
          ),
          for (final tier in tiers)
            FilterChip(
              selected: selectedTier == tier,
              label: Text(tier),
              onSelected: (value) => onTierChanged(value ? tier : null),
            ),
          for (final risk in risks)
            FilterChip(
              selected: selectedRisk == risk,
              label: Text(risk),
              onSelected: (value) => onRiskChanged(value ? risk : null),
            ),
        ],
      ),
    );
  }
}

class _CreatorRoster extends StatelessWidget {
  const _CreatorRoster({
    required this.creators,
    required this.selectedId,
    required this.onSelect,
  });

  final List<Bmp05Creator> creators;
  final String? selectedId;
  final ValueChanged<String> onSelect;

  @override
  Widget build(BuildContext context) {
    return _Panel(
      padding: const EdgeInsets.fromLTRB(18, 18, 18, 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.lumenisL10n.text('common.type'),
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 5),
          Text(
            context.lumenisL10n.text('common.source'),
            style: TextStyle(color: LumenisTheme.of(context).muted),
          ),
          const SizedBox(height: 10),
          SizedBox(
            height: 122,
            width: double.infinity,
            child: CustomPaint(
              painter: _CreatorGraphPainter(
                count: creators.length,
                palette: LumenisTheme.of(context),
              ),
            ),
          ),
          ListView.separated(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: creators.length,
            separatorBuilder: (_, _) => const Divider(height: 1),
            itemBuilder: (context, index) {
              final creator = creators[index];
              final selected = creator.id == selectedId;
              return Semantics(
                button: true,
                selected: selected,
                label: '${creator.name}, ${creator.tier}',
                child: InkWell(
                  key: Key('bmp05-creator-${creator.id}'),
                  onTap: () => onSelect(creator.id),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(
                      vertical: 12,
                      horizontal: 4,
                    ),
                    child: Row(
                      children: [
                        Icon(
                          selected
                              ? Icons.radio_button_checked
                              : Icons.radio_button_unchecked,
                          color: selected
                              ? LumenisTheme.of(context).bmp
                              : LumenisTheme.of(context).quiet,
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            creator.name,
                            style: TextStyle(
                              color: LumenisTheme.of(context).foreground,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ),
                        Text(
                          creator.tier,
                          style: TextStyle(
                            color: LumenisTheme.of(context).bmp,
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        const SizedBox(width: 8),
                        Text(
                          creator.platform,
                          style: TextStyle(
                            color: LumenisTheme.of(context).muted,
                            fontSize: 12,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              );
            },
          ),
        ],
      ),
    );
  }
}

class _CreatorDossier extends StatelessWidget {
  const _CreatorDossier({required this.creator});

  final Bmp05Creator? creator;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    if (creator == null) {
      return _Panel(
        padding: const EdgeInsets.all(20),
        child: Text(
          copy.text('state.empty_filter_d'),
          style: TextStyle(color: LumenisTheme.of(context).muted),
        ),
      );
    }
    return _Panel(
      padding: const EdgeInsets.all(20),
      child: Semantics(
        container: true,
        label: creator!.name,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(creator!.name, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 6),
            Text(
              '${creator!.tier} · ${creator!.platform}',
              style: TextStyle(color: LumenisTheme.of(context).bmp),
            ),
            const SizedBox(height: 18),
            _MetricLine(
              label: copy.text('common.type'),
              metric: creator!.posts,
            ),
            _MetricLine(
              label: copy.text('comp.insight'),
              metric: creator!.engagement,
            ),
            _MetricLine(
              label: copy.text('comp.actions'),
              metric: creator!.conversion,
            ),
            if (creator!.risk != null) ...[
              const Divider(height: 26),
              Text(
                creator!.risk!.label,
                style: TextStyle(
                  color: creator!.risk!.level.toLowerCase() == 'high'
                      ? LumenisTheme.of(context).danger
                      : LumenisTheme.of(context).caution,
                  fontWeight: FontWeight.w600,
                ),
              ),
              if (creator!.risk!.score != null)
                Text(
                  _format(creator!.risk!.score!),
                  style: TextStyle(color: LumenisTheme.of(context).muted),
                ),
            ],
            const Divider(height: 26),
            Text(
              '${copy.text('common.source')}: ${creator!.source}',
              style: TextStyle(
                color: LumenisTheme.of(context).muted,
                height: 1.45,
              ),
            ),
            const SizedBox(height: 5),
            Text(
              '${copy.text('common.source')}: ${creator!.evidenceReference}',
              style: TextStyle(
                color: LumenisTheme.of(context).quiet,
                fontSize: 12,
              ),
            ),
          ],
        ),
      ),
    );
  }

  String _format(num value) {
    if (value == value.roundToDouble()) return value.toInt().toString();
    return value.toStringAsFixed(2);
  }
}

class _MetricLine extends StatelessWidget {
  const _MetricLine({required this.label, required this.metric});

  final String label;
  final Bmp05Metric? metric;

  @override
  Widget build(BuildContext context) {
    final value = metric == null
        ? context.lumenisL10n.text('state.empty_true')
        : _format(metric!.value) +
              (metric!.unit == null ? '' : ' ${metric!.unit!}');
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Text(
              label,
              style: TextStyle(color: LumenisTheme.of(context).muted),
            ),
          ),
          const SizedBox(width: 12),
          Flexible(
            child: Text(
              value,
              textAlign: TextAlign.end,
              style: TextStyle(
                color: LumenisTheme.of(context).foreground,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }

  String _format(num value) {
    if (value == value.roundToDouble()) return value.toInt().toString();
    return value.toStringAsFixed(2);
  }
}

class _FilteredEmpty extends StatelessWidget {
  const _FilteredEmpty();

  @override
  Widget build(BuildContext context) {
    return _Panel(
      padding: const EdgeInsets.all(24),
      child: Semantics(
        liveRegion: true,
        label: context.lumenisL10n.text('state.empty_filter_d'),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              context.lumenisL10n.text('state.empty_filter'),
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 6),
            Text(
              context.lumenisL10n.text('state.empty_filter_d'),
              style: TextStyle(color: LumenisTheme.of(context).muted),
            ),
          ],
        ),
      ),
    );
  }
}

class _AvailabilityPanel extends StatelessWidget {
  const _AvailabilityPanel({required this.snapshot, required this.onRetry});

  final Bmp05Snapshot snapshot;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    final title = switch (snapshot.presentationState) {
      Bmp05PresentationState.global => copy.text('bmp01.market.global.title'),
      Bmp05PresentationState.notCollected => copy.text(
        'state.empty_notcollected',
      ),
      Bmp05PresentationState.empty => copy.text('state.empty_true'),
      Bmp05PresentationState.blocked => copy.text('state.permission_denied'),
      Bmp05PresentationState.unavailable => copy.text('state.error'),
      Bmp05PresentationState.stale => copy.text('state.stale'),
      Bmp05PresentationState.partial => copy.text('state.partial'),
      _ => copy.text('state.error'),
    };
    final detail = switch (snapshot.presentationState) {
      Bmp05PresentationState.global => copy.text('bmp01.market.global.detail'),
      Bmp05PresentationState.notCollected => copy.text(
        'state.empty_notcollected_d',
      ),
      Bmp05PresentationState.empty => copy.text('state.empty_true_d'),
      Bmp05PresentationState.blocked => copy.text('state.permission_denied_d'),
      Bmp05PresentationState.unavailable => copy.text(
        'context.screen_binding_unavailable',
      ),
      Bmp05PresentationState.stale => copy.text('state.stale_d'),
      Bmp05PresentationState.partial => copy.text('state.partial_d'),
      _ => copy.text('state.error_d'),
    };
    return _Panel(
      padding: const EdgeInsets.all(24),
      child: Semantics(
        liveRegion: true,
        label: '$title. $detail',
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(
              snapshot.presentationState == Bmp05PresentationState.blocked
                  ? Icons.lock_outline
                  : Icons.info_outline,
              color: LumenisTheme.of(context).caution,
            ),
            const SizedBox(height: 14),
            Text(title, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 7),
            Text(
              detail,
              style: TextStyle(
                color: LumenisTheme.of(context).muted,
                height: 1.55,
              ),
            ),
            const SizedBox(height: 18),
            FilledButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh),
              label: Text(copy.text('common.refresh')),
            ),
          ],
        ),
      ),
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
        label: context.lumenisL10n.text('state.loading_d'),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const CircularProgressIndicator(),
            const SizedBox(height: 14),
            Text(context.lumenisL10n.text('state.loading')),
          ],
        ),
      ),
    );
  }
}

class _FailureState extends StatelessWidget {
  const _FailureState({required this.kind, required this.onRetry});

  final Bmp05FailureKind kind;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    final title = kind == Bmp05FailureKind.offline
        ? copy.text('state.offline')
        : kind == Bmp05FailureKind.server
        ? copy.text('state.error')
        : copy.text('state.permission_denied');
    final detail = kind == Bmp05FailureKind.offline
        ? copy.text('state.offline_d')
        : kind == Bmp05FailureKind.server
        ? copy.text('state.error_d')
        : copy.text('state.permission_denied_d');
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: _Panel(
          padding: const EdgeInsets.all(24),
          child: Semantics(
            liveRegion: true,
            label: '$title. $detail',
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: Theme.of(context).textTheme.titleLarge),
                const SizedBox(height: 8),
                Text(
                  detail,
                  style: TextStyle(
                    color: LumenisTheme.of(context).muted,
                    height: 1.5,
                  ),
                ),
                const SizedBox(height: 18),
                FilledButton.icon(
                  onPressed: onRetry,
                  icon: const Icon(Icons.refresh),
                  label: Text(copy.text('common.refresh')),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _Panel extends StatelessWidget {
  const _Panel({required this.child, this.padding = const EdgeInsets.all(16)});

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

class _CreatorGraphPainter extends CustomPainter {
  const _CreatorGraphPainter({required this.count, required this.palette});

  final int count;
  final LumenisPalette palette;

  @override
  void paint(Canvas canvas, Size size) {
    final linePaint = Paint()
      ..color = palette.bmp.withValues(alpha: 0.24)
      ..strokeWidth = 1.2;
    final dotPaint = Paint()..color = palette.bmp;
    final center = Offset(size.width * 0.52, size.height * 0.50);
    final points = <Offset>[
      center,
      Offset(size.width * 0.14, size.height * 0.25),
      Offset(size.width * 0.80, size.height * 0.22),
      Offset(size.width * 0.82, size.height * 0.80),
      Offset(size.width * 0.20, size.height * 0.78),
    ];
    for (final point in points.skip(1)) {
      canvas.drawLine(center, point, linePaint);
      canvas.drawCircle(point, 5, dotPaint);
    }
    canvas.drawCircle(center, 9, dotPaint);
    for (var i = 0; i < count && i < 5; i++) {
      canvas.drawCircle(points[i], 3, Paint()..color = palette.accent);
    }
  }

  @override
  bool shouldRepaint(covariant _CreatorGraphPainter oldDelegate) =>
      oldDelegate.count != count || oldDelegate.palette != palette;
}
