import 'package:flutter/material.dart';

import '../../core/lumenis_core_client.dart';
import '../../core/lumenis_theme.dart';
import '../../l10n/lumenis_localizations.dart';
import 'bmp02_repository.dart';
import 'bmp02_snapshot.dart';
import 'bmp02_view_model.dart';

class Bmp02Screen extends StatefulWidget {
  const Bmp02Screen({required this.client, this.repository, super.key});

  final LumenisCoreClient client;
  final Bmp02Repository? repository;

  @override
  State<Bmp02Screen> createState() => _Bmp02ScreenState();
}

class _Bmp02ScreenState extends State<Bmp02Screen> {
  late final Bmp02ViewModel _viewModel = Bmp02ViewModel(
    repository: widget.repository ?? CoreBmp02Repository(client: widget.client),
  );
  late final TextEditingController _queryController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _queryController.addListener(_syncQuery);
    _viewModel.refresh();
  }

  @override
  void dispose() {
    _queryController
      ..removeListener(_syncQuery)
      ..dispose();
    _viewModel.dispose();
    super.dispose();
  }

  void _syncQuery() => _viewModel.updateQuery(_queryController.text);

  @override
  Widget build(BuildContext context) {
    return ColoredBox(
      color: LumenisTheme.of(context).canvas,
      child: SafeArea(
        child: AnimatedBuilder(
          animation: _viewModel,
          builder: (context, _) => switch (_viewModel.phase) {
            Bmp02LoadPhase.loading => const _LoadingState(),
            Bmp02LoadPhase.failed => _FailureState(
              kind: _viewModel.failureKind!,
              onRetry: _viewModel.refresh,
            ),
            Bmp02LoadPhase.ready => _buildReady(context, _viewModel.snapshot!),
          },
        ),
      ),
    );
  }

  Widget _buildReady(BuildContext context, Bmp02Snapshot snapshot) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final compact = constraints.maxWidth < 700;
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
                  _PageHeading(snapshot: snapshot),
                  const SizedBox(height: 20),
                  _FocusBand(snapshot: snapshot),
                  const SizedBox(height: 20),
                  if (snapshot.presentationState ==
                          Bmp02PresentationState.ready ||
                      snapshot.presentationState ==
                          Bmp02PresentationState.partial ||
                      snapshot.presentationState ==
                          Bmp02PresentationState.stale)
                    _PortfolioView(
                      viewModel: _viewModel,
                      queryController: _queryController,
                      compact: compact,
                    )
                  else
                    _AvailabilityPanel(
                      snapshot: snapshot,
                      onRetry: _viewModel.refresh,
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
  const _PageHeading({required this.snapshot});

  final Bmp02Snapshot snapshot;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          copy.text('screen.BMP-02'),
          style: Theme.of(context).textTheme.headlineMedium?.copyWith(
            color: LumenisTheme.of(context).foreground,
            fontWeight: FontWeight.w600,
            letterSpacing: -0.5,
          ),
        ),
        const SizedBox(height: 7),
        Text(
          copy.text('context.selector.scope_note'),
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

  final Bmp02Snapshot snapshot;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    final languageCode = Localizations.localeOf(context).languageCode == 'zh'
        ? 'zh-CN'
        : Localizations.localeOf(context).languageCode;
    final name = snapshot.focus.localizedName(languageCode);
    final label = name == null
        ? copy.text('bmp01.focus.global')
        : copy.text('shell.bmp.brand_named', values: {'name': name});
    final detail = copy.text('context.selector.scope_note');
    return Semantics(
      container: true,
      liveRegion: true,
      label: '$label. $detail',
      child: _Panel(
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 15),
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
                    label,
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

class _PortfolioView extends StatelessWidget {
  const _PortfolioView({
    required this.viewModel,
    required this.queryController,
    required this.compact,
  });

  final Bmp02ViewModel viewModel;
  final TextEditingController queryController;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final brands = viewModel.filteredBrands;
    final selected = viewModel.selectedBrand;
    final filterRoles = brands.map((brand) => brand.role).toSet().toList();
    final content = Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _PortfolioControls(
          controller: queryController,
          roles: filterRoles,
          brands: brands,
          selectedRole: viewModel.roleFilter,
          onRoleChanged: viewModel.setRoleFilter,
        ),
        const SizedBox(height: 18),
        if (brands.isEmpty)
          const _FilteredEmpty()
        else if (compact)
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _PortfolioConstellation(
                brands: brands,
                selectedId: viewModel.selectedBrandId,
                onSelect: viewModel.selectBrand,
              ),
              const SizedBox(height: 16),
              _BrandDossier(brand: selected),
            ],
          )
        else
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                flex: 7,
                child: _PortfolioConstellation(
                  brands: brands,
                  selectedId: viewModel.selectedBrandId,
                  onSelect: viewModel.selectBrand,
                ),
              ),
              const SizedBox(width: 18),
              Expanded(flex: 5, child: _BrandDossier(brand: selected)),
            ],
          ),
      ],
    );
    return content;
  }
}

class _PortfolioControls extends StatelessWidget {
  const _PortfolioControls({
    required this.controller,
    required this.roles,
    required this.brands,
    required this.selectedRole,
    required this.onRoleChanged,
  });

  final TextEditingController controller;
  final List<String> roles;
  final List<Bmp02Brand> brands;
  final String? selectedRole;
  final ValueChanged<String?> onRoleChanged;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    return _Panel(
      padding: const EdgeInsets.all(14),
      child: Wrap(
        spacing: 10,
        runSpacing: 10,
        crossAxisAlignment: WrapCrossAlignment.center,
        children: [
          SizedBox(
            width: 280,
            child: TextField(
              controller: controller,
              textInputAction: TextInputAction.search,
              decoration: InputDecoration(
                prefixIcon: const Icon(Icons.search),
                hintText: copy.text('common.search'),
                labelText: copy.text('common.search'),
                border: const OutlineInputBorder(),
              ),
            ),
          ),
          FilterChip(
            selected: selectedRole == null,
            label: Text(copy.text('common.all')),
            onSelected: (_) => onRoleChanged(null),
          ),
          for (final role in roles)
            FilterChip(
              selected: selectedRole == role,
              label: Text(_roleLabel(context, role)),
              onSelected: (selected) => onRoleChanged(selected ? role : null),
            ),
        ],
      ),
    );
  }

  String _roleLabel(BuildContext context, String role) {
    final languageCode = Localizations.localeOf(context).languageCode;
    final key = languageCode == 'zh' ? 'zh-CN' : languageCode;
    for (final brand in brands) {
      if (brand.role == role) {
        return brand.roleLabel[key] ?? brand.roleLabel['en'] ?? role;
      }
    }
    return role;
  }
}

class _PortfolioConstellation extends StatelessWidget {
  const _PortfolioConstellation({
    required this.brands,
    required this.selectedId,
    required this.onSelect,
  });

  final List<Bmp02Brand> brands;
  final String? selectedId;
  final ValueChanged<String> onSelect;

  @override
  Widget build(BuildContext context) {
    return _Panel(
      padding: const EdgeInsets.fromLTRB(18, 18, 18, 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.lumenisL10n.text('common.type'),
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 5),
          Text(
            context.lumenisL10n.text('common.detail'),
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: LumenisTheme.of(context).muted,
            ),
          ),
          const SizedBox(height: 15),
          SizedBox(
            height: 84,
            width: double.infinity,
            child: CustomPaint(
              painter: _ConstellationPainter(palette: LumenisTheme.of(context)),
            ),
          ),
          const SizedBox(height: 4),
          ListView.separated(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: brands.length,
            separatorBuilder: (_, _) => const Divider(height: 1),
            itemBuilder: (context, index) {
              final brand = brands[index];
              final selected = brand.id == selectedId;
              return Semantics(
                button: true,
                selected: selected,
                label: '${brand.name}, ${_roleLabel(context, brand)}',
                child: InkWell(
                  key: Key('bmp02-brand-${brand.id}'),
                  onTap: () => onSelect(brand.id),
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
                          size: 20,
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            brand.name,
                            style: TextStyle(
                              color: LumenisTheme.of(context).foreground,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ),
                        Text(
                          _roleLabel(context, brand),
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

  String _roleLabel(BuildContext context, Bmp02Brand brand) {
    final languageCode = Localizations.localeOf(context).languageCode;
    return brand.roleLabel[languageCode == 'zh' ? 'zh-CN' : languageCode] ??
        brand.roleLabel['en'] ??
        brand.role;
  }
}

class _BrandDossier extends StatelessWidget {
  const _BrandDossier({required this.brand});

  final Bmp02Brand? brand;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    if (brand == null) {
      return _Panel(
        padding: const EdgeInsets.all(20),
        child: Text(
          copy.text('state.empty_filter_d'),
          style: TextStyle(color: LumenisTheme.of(context).muted),
        ),
      );
    }
    final languageCode = Localizations.localeOf(context).languageCode == 'zh'
        ? 'zh-CN'
        : Localizations.localeOf(context).languageCode;
    return _Panel(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(brand!.name, style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 6),
          Text(
            brand!.roleLabel[languageCode] ??
                brand!.roleLabel['en'] ??
                brand!.role,
            style: TextStyle(color: LumenisTheme.of(context).bmp),
          ),
          if (brand!.category != null) ...[
            const SizedBox(height: 4),
            Text(
              brand!.category!,
              style: TextStyle(color: LumenisTheme.of(context).muted),
            ),
          ],
          const SizedBox(height: 18),
          _MetricLine(label: copy.text('common.status'), metric: brand!.health),
          _MetricLine(label: copy.text('common.time'), metric: brand!.voice),
          _MetricLine(label: copy.text('common.type'), metric: brand!.positive),
          _MetricLine(
            label: copy.text('common.detail'),
            metric: brand!.engagement,
          ),
          const Divider(height: 26),
          Text(
            '${copy.text('common.source')}: ${brand!.source}',
            style: TextStyle(
              color: LumenisTheme.of(context).muted,
              height: 1.45,
            ),
          ),
          if (brand!.timeWindow != null) ...[
            const SizedBox(height: 5),
            Text(
              '${copy.text('common.time')}: ${brand!.timeWindow!}',
              style: TextStyle(color: LumenisTheme.of(context).muted),
            ),
          ],
          const SizedBox(height: 5),
          Text(
            '${copy.text('common.source')}: ${brand!.evidenceReference}',
            style: TextStyle(
              color: LumenisTheme.of(context).quiet,
              fontSize: 12,
            ),
          ),
        ],
      ),
    );
  }
}

class _MetricLine extends StatelessWidget {
  const _MetricLine({required this.label, required this.metric});

  final String label;
  final Bmp02Metric? metric;

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

  final Bmp02Snapshot snapshot;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    final title = switch (snapshot.presentationState) {
      Bmp02PresentationState.global => copy.text('bmp01.market.global.title'),
      Bmp02PresentationState.notCollected => copy.text(
        'state.empty_notcollected',
      ),
      Bmp02PresentationState.empty => copy.text('state.empty_true'),
      Bmp02PresentationState.blocked => copy.text('state.permission_denied'),
      Bmp02PresentationState.unavailable => copy.text('state.error'),
      Bmp02PresentationState.stale => copy.text('state.stale'),
      Bmp02PresentationState.partial => copy.text('state.partial'),
      _ => copy.text('state.error'),
    };
    final detail = switch (snapshot.presentationState) {
      Bmp02PresentationState.global => copy.text('bmp01.market.global.detail'),
      Bmp02PresentationState.notCollected => copy.text(
        'state.empty_notcollected_d',
      ),
      Bmp02PresentationState.empty => copy.text('state.empty_true_d'),
      Bmp02PresentationState.blocked => copy.text('state.permission_denied_d'),
      Bmp02PresentationState.unavailable => copy.text(
        'context.screen_binding_unavailable',
      ),
      Bmp02PresentationState.stale => copy.text('state.stale_d'),
      Bmp02PresentationState.partial => copy.text('state.partial_d'),
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
              snapshot.presentationState == Bmp02PresentationState.blocked
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

  final Bmp02FailureKind kind;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    final title = switch (kind) {
      Bmp02FailureKind.authentication => copy.text('state.permission_denied'),
      Bmp02FailureKind.permissionDenied => copy.text('state.permission_denied'),
      Bmp02FailureKind.offline => copy.text('state.offline'),
      Bmp02FailureKind.server => copy.text('state.error'),
    };
    final detail = switch (kind) {
      Bmp02FailureKind.authentication => copy.text('state.permission_denied_d'),
      Bmp02FailureKind.permissionDenied => copy.text(
        'state.permission_denied_d',
      ),
      Bmp02FailureKind.offline => copy.text('state.offline_d'),
      Bmp02FailureKind.server => copy.text('state.error_d'),
    };
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

class _ConstellationPainter extends CustomPainter {
  const _ConstellationPainter({required this.palette});

  final LumenisPalette palette;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width * 0.52, size.height * 0.5);
    final linePaint = Paint()
      ..color = palette.bmp.withValues(alpha: 0.30)
      ..strokeWidth = 1.2;
    final dotPaint = Paint()..color = palette.bmp.withValues(alpha: 0.85);
    final points = <Offset>[
      center,
      Offset(size.width * 0.18, size.height * 0.28),
      Offset(size.width * 0.78, size.height * 0.22),
      Offset(size.width * 0.82, size.height * 0.76),
    ];
    for (final point in points.skip(1)) {
      canvas.drawLine(center, point, linePaint);
    }
    canvas.drawCircle(center, 9, dotPaint);
    for (final point in points.skip(1)) {
      canvas.drawCircle(point, 5, dotPaint);
    }
  }

  @override
  bool shouldRepaint(covariant _ConstellationPainter oldDelegate) =>
      oldDelegate.palette != palette;
}
