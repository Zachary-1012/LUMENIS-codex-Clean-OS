import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../core/lumenis_core_client.dart';
import '../../core/lumenis_theme.dart';
import '../../l10n/lumenis_localizations.dart';
import 'bmp03_repository.dart';
import 'bmp03_snapshot.dart';
import 'bmp03_view_model.dart';

class Bmp03Screen extends StatefulWidget {
  const Bmp03Screen({required this.client, this.repository, super.key});

  final LumenisCoreClient client;
  final Bmp03Repository? repository;

  @override
  State<Bmp03Screen> createState() => _Bmp03ScreenState();
}

class _Bmp03ScreenState extends State<Bmp03Screen> {
  late final Bmp03ViewModel _viewModel = Bmp03ViewModel(
    repository: widget.repository ?? CoreBmp03Repository(client: widget.client),
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
            Bmp03LoadPhase.loading => const _LoadingState(),
            Bmp03LoadPhase.failed => _FailureState(
              kind: _viewModel.failureKind!,
              onRetry: _viewModel.refresh,
            ),
            Bmp03LoadPhase.ready => _ReadyState(
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

  final Bmp03Snapshot snapshot;
  final Bmp03ViewModel viewModel;

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
                          Bmp03PresentationState.ready ||
                      snapshot.presentationState ==
                          Bmp03PresentationState.partial ||
                      snapshot.presentationState ==
                          Bmp03PresentationState.stale)
                    _IntelligenceWorkspace(
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
          copy.text('screen.BMP-03'),
          style: Theme.of(context).textTheme.headlineMedium?.copyWith(
            color: LumenisTheme.of(context).foreground,
            fontWeight: FontWeight.w600,
            letterSpacing: -0.5,
          ),
        ),
        const SizedBox(height: 7),
        Text(
          copy.text('common.source'),
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

  final Bmp03Snapshot snapshot;

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

class _IntelligenceWorkspace extends StatelessWidget {
  const _IntelligenceWorkspace({
    required this.snapshot,
    required this.viewModel,
    required this.compact,
  });

  final Bmp03Snapshot snapshot;
  final Bmp03ViewModel viewModel;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final signals = viewModel.filteredSignals;
    final kinds = snapshot.signals
        .map((signal) => signal.kind)
        .toSet()
        .toList();
    final selected = viewModel.selectedSignal;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _KindFilters(
          kinds: kinds,
          selected: viewModel.kindFilter,
          onChanged: viewModel.setKindFilter,
          snapshot: snapshot,
        ),
        const SizedBox(height: 18),
        if (signals.isEmpty)
          const _FilteredEmpty()
        else if (compact)
          Column(
            children: [
              _RadarPanel(
                signals: signals,
                selectedId: viewModel.selectedSignalId,
                onSelect: viewModel.selectSignal,
              ),
              const SizedBox(height: 16),
              _SourceBrief(signal: selected),
            ],
          )
        else
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                flex: 7,
                child: _RadarPanel(
                  signals: signals,
                  selectedId: viewModel.selectedSignalId,
                  onSelect: viewModel.selectSignal,
                ),
              ),
              const SizedBox(width: 18),
              Expanded(flex: 5, child: _SourceBrief(signal: selected)),
            ],
          ),
      ],
    );
  }
}

class _KindFilters extends StatelessWidget {
  const _KindFilters({
    required this.kinds,
    required this.selected,
    required this.onChanged,
    required this.snapshot,
  });

  final List<String> kinds;
  final String? selected;
  final ValueChanged<String?> onChanged;
  final Bmp03Snapshot snapshot;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    return _Panel(
      child: Wrap(
        spacing: 9,
        runSpacing: 9,
        children: [
          FilterChip(
            selected: selected == null,
            label: Text(copy.text('common.all')),
            onSelected: (_) => onChanged(null),
          ),
          for (final kind in kinds)
            FilterChip(
              selected: selected == kind,
              label: Text(_kindLabel(snapshot, kind)),
              onSelected: (value) => onChanged(value ? kind : null),
            ),
        ],
      ),
    );
  }

  String _kindLabel(Bmp03Snapshot snapshot, String kind) {
    for (final signal in snapshot.signals) {
      if (signal.kind == kind) return signal.localizedKind('zh-CN');
    }
    return kind;
  }
}

class _RadarPanel extends StatelessWidget {
  const _RadarPanel({
    required this.signals,
    required this.selectedId,
    required this.onSelect,
  });

  final List<Bmp03Signal> signals;
  final String? selectedId;
  final ValueChanged<String> onSelect;

  @override
  Widget build(BuildContext context) {
    return _Panel(
      padding: const EdgeInsets.fromLTRB(18, 18, 18, 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.lumenisL10n.text('screen.BMP-03'),
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 5),
          Text(
            context.lumenisL10n.text('comp.confidence'),
            style: TextStyle(color: LumenisTheme.of(context).muted),
          ),
          const SizedBox(height: 12),
          SizedBox(
            height: 180,
            width: double.infinity,
            child: CustomPaint(
              painter: _RadarPainter(
                signals: signals,
                palette: LumenisTheme.of(context),
              ),
              child: const SizedBox.expand(),
            ),
          ),
          const SizedBox(height: 4),
          ListView.separated(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: signals.length,
            separatorBuilder: (_, _) => const Divider(height: 1),
            itemBuilder: (context, index) {
              final signal = signals[index];
              final selected = signal.id == selectedId;
              return Semantics(
                button: true,
                selected: selected,
                label: signal.title,
                child: InkWell(
                  key: Key('bmp03-signal-${signal.id}'),
                  onTap: () => onSelect(signal.id),
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
                            signal.title,
                            style: TextStyle(
                              color: LumenisTheme.of(context).foreground,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ),
                        Text(
                          signal.localizedKind('zh-CN'),
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

class _SourceBrief extends StatelessWidget {
  const _SourceBrief({required this.signal});

  final Bmp03Signal? signal;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    if (signal == null) {
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
        label: signal!.title,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(signal!.title, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 6),
            Text(
              signal!.localizedKind(
                Localizations.localeOf(context).languageCode == 'zh'
                    ? 'zh-CN'
                    : Localizations.localeOf(context).languageCode,
              ),
              style: TextStyle(color: LumenisTheme.of(context).bmp),
            ),
            const SizedBox(height: 18),
            _BriefLine(
              label: copy.text('comp.confidence'),
              value: _percent(signal!.confidence),
            ),
            _BriefLine(
              label: copy.text('comp.trend'),
              value: _percent(signal!.momentum),
            ),
            _BriefLine(
              label: copy.text('common.source'),
              value: signal!.source,
            ),
            if (signal!.capturedAt != null)
              _BriefLine(
                label: copy.text('common.time'),
                value: signal!.capturedAt!,
              ),
            if (signal!.timeWindow != null)
              _BriefLine(
                label: copy.text('common.status'),
                value: signal!.timeWindow!,
              ),
            if (signal!.summary != null) ...[
              const Divider(height: 26),
              Text(
                signal!.summary!,
                style: TextStyle(
                  color: LumenisTheme.of(context).muted,
                  height: 1.55,
                ),
              ),
            ],
            const Divider(height: 26),
            Text(
              '${copy.text('common.source')}: ${signal!.evidenceReference}',
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

  String _percent(num value) {
    return value == value.roundToDouble()
        ? '${value.toInt()}%'
        : '${value.toStringAsFixed(1)}%';
  }
}

class _BriefLine extends StatelessWidget {
  const _BriefLine({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
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

  final Bmp03Snapshot snapshot;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    final title = switch (snapshot.presentationState) {
      Bmp03PresentationState.global => copy.text('bmp01.market.global.title'),
      Bmp03PresentationState.notCollected => copy.text(
        'state.empty_notcollected',
      ),
      Bmp03PresentationState.empty => copy.text('state.empty_true'),
      Bmp03PresentationState.blocked => copy.text('state.permission_denied'),
      Bmp03PresentationState.unavailable => copy.text('state.error'),
      Bmp03PresentationState.stale => copy.text('state.stale'),
      Bmp03PresentationState.partial => copy.text('state.partial'),
      _ => copy.text('state.error'),
    };
    final detail = switch (snapshot.presentationState) {
      Bmp03PresentationState.global => copy.text('bmp01.market.global.detail'),
      Bmp03PresentationState.notCollected => copy.text(
        'state.empty_notcollected_d',
      ),
      Bmp03PresentationState.empty => copy.text('state.empty_true_d'),
      Bmp03PresentationState.blocked => copy.text('state.permission_denied_d'),
      Bmp03PresentationState.unavailable => copy.text(
        'context.screen_binding_unavailable',
      ),
      Bmp03PresentationState.stale => copy.text('state.stale_d'),
      Bmp03PresentationState.partial => copy.text('state.partial_d'),
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
              snapshot.presentationState == Bmp03PresentationState.blocked
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

  final Bmp03FailureKind kind;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    final title = kind == Bmp03FailureKind.offline
        ? copy.text('state.offline')
        : kind == Bmp03FailureKind.server
        ? copy.text('state.error')
        : copy.text('state.permission_denied');
    final detail = kind == Bmp03FailureKind.offline
        ? copy.text('state.offline_d')
        : kind == Bmp03FailureKind.server
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

class _RadarPainter extends CustomPainter {
  const _RadarPainter({required this.signals, required this.palette});

  final List<Bmp03Signal> signals;
  final LumenisPalette palette;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width * 0.5, size.height * 0.52);
    final radius = size.shortestSide * 0.38;
    final gridPaint = Paint()
      ..color = palette.line
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1;
    for (final scale in <double>[0.35, 0.67, 1]) {
      canvas.drawCircle(center, radius * scale, gridPaint);
    }
    canvas.drawLine(
      Offset(center.dx - radius, center.dy),
      Offset(center.dx + radius, center.dy),
      gridPaint,
    );
    canvas.drawLine(
      Offset(center.dx, center.dy - radius),
      Offset(center.dx, center.dy + radius),
      gridPaint,
    );
    final dotPaint = Paint()..color = palette.bmp;
    for (var index = 0; index < signals.length; index++) {
      final signal = signals[index];
      final angle = (index / signals.length) * 6.28318 - 1.5708;
      final distance = radius * (signal.momentum / 100);
      final point = Offset(
        center.dx + distance * math.cos(angle),
        center.dy + distance * math.sin(angle),
      );
      canvas.drawLine(
        center,
        point,
        gridPaint..color = palette.bmp.withValues(alpha: 0.25),
      );
      canvas.drawCircle(point, 5 + signal.confidence / 30, dotPaint);
    }
  }

  @override
  bool shouldRepaint(covariant _RadarPainter oldDelegate) =>
      oldDelegate.signals != signals || oldDelegate.palette != palette;
}
