import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

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
  late Bmp03ViewModel _viewModel = _createViewModel();

  Bmp03ViewModel _createViewModel() => Bmp03ViewModel(
    repository: widget.repository ?? CoreBmp03Repository(client: widget.client),
  );

  @override
  void initState() {
    super.initState();
    _viewModel.refresh();
  }

  @override
  void didUpdateWidget(covariant Bmp03Screen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.client != widget.client ||
        oldWidget.repository != widget.repository) {
      _viewModel.dispose();
      _viewModel = _createViewModel()..refresh();
    }
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
              key: ObjectKey(_viewModel.snapshot),
              snapshot: _viewModel.snapshot!,
              viewModel: _viewModel,
            ),
          },
        ),
      ),
    );
  }
}

class _ReadyState extends StatefulWidget {
  const _ReadyState({
    required this.snapshot,
    required this.viewModel,
    super.key,
  });

  final Bmp03Snapshot snapshot;
  final Bmp03ViewModel viewModel;

  @override
  State<_ReadyState> createState() => _ReadyStateState();
}

class _ReadyStateState extends State<_ReadyState> {
  final _browseScroll = ScrollController();
  final _briefScroll = ScrollController();
  final _returnFocus = FocusNode();
  final _filterFocus = FocusNode();
  late final _signalFocus = {
    for (final signal in widget.snapshot.signals) signal.id: FocusNode(),
  };
  bool _reading = false;
  double _browseOffset = 0;

  @override
  void dispose() {
    _browseScroll.dispose();
    _briefScroll.dispose();
    _returnFocus.dispose();
    _filterFocus.dispose();
    for (final node in _signalFocus.values) {
      node.dispose();
    }
    super.dispose();
  }

  void _select(String id, bool compact) {
    _browseOffset = _browseScroll.hasClients ? _browseScroll.offset : 0;
    widget.viewModel.selectSignal(id);
    setState(() => _reading = compact);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      if (_briefScroll.hasClients) _briefScroll.jumpTo(0);
      if (compact) _returnFocus.requestFocus();
    });
  }

  void _returnToSignals() {
    setState(() => _reading = false);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      if (_browseScroll.hasClients) {
        _browseScroll.jumpTo(
          _browseOffset.clamp(
            _browseScroll.position.minScrollExtent,
            _browseScroll.position.maxScrollExtent,
          ),
        );
      }
      (_signalFocus[widget.viewModel.selectedSignal?.id] ?? _filterFocus)
          .requestFocus();
    });
  }

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final compact =
            constraints.maxWidth < 960 ||
            MediaQuery.textScalerOf(context).scale(14) > 22;
        final inset = compact ? 18.0 : 28.0;
        final snapshot = widget.snapshot;
        final viewModel = widget.viewModel;
        final available =
            snapshot.scopeReady &&
            {
              Bmp03PresentationState.ready,
              Bmp03PresentationState.partial,
              Bmp03PresentationState.stale,
            }.contains(snapshot.presentationState);
        final focused = compact && _reading && available;
        final kinds = snapshot.signals
            .map((signal) => signal.kind)
            .toSet()
            .toList();
        final header = Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Expanded(child: _PageHeading()),
                IconButton(
                  onPressed: viewModel.refresh,
                  tooltip: context.lumenisL10n.text('common.refresh'),
                  icon: const Icon(Icons.refresh_rounded),
                ),
              ],
            ),
            const SizedBox(height: 8),
            _FocusBand(snapshot: snapshot),
            if (available) ...[
              const SizedBox(height: 14),
              _KindFilters(
                kinds: kinds,
                selected: viewModel.kindFilter,
                onChanged: viewModel.setKindFilter,
                snapshot: snapshot,
                focusNode: _filterFocus,
              ),
            ],
          ],
        );
        final browse = SingleChildScrollView(
          key: const PageStorageKey('bmp03-browse'),
          controller: _browseScroll,
          child: viewModel.filteredSignals.isEmpty
              ? const _FilteredEmpty()
              : _RadarPanel(
                  signals: viewModel.filteredSignals,
                  selectedId: viewModel.selectedSignal?.id,
                  focusNodes: _signalFocus,
                  showRadar: !compact,
                  onSelect: (id) => _select(id, compact),
                ),
        );
        final brief = SingleChildScrollView(
          key: const Key('bmp03-brief-scroll'),
          controller: _briefScroll,
          child: _SourceBrief(signal: viewModel.selectedSignal),
        );
        final content = !available
            ? SingleChildScrollView(
                child: _AvailabilityPanel(
                  snapshot: snapshot,
                  onRetry: viewModel.refresh,
                ),
              )
            : focused
            ? brief
            : compact
            ? browse
            : Row(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Expanded(flex: 6, child: browse),
                  const SizedBox(width: 20),
                  Expanded(flex: 5, child: brief),
                ],
              );
        final height = constraints.hasBoundedHeight
            ? constraints.maxHeight
            : MediaQuery.sizeOf(context).height;
        return Align(
          alignment: Alignment.topCenter,
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1420),
            child: SizedBox(
              height: height,
              child: Padding(
                padding: EdgeInsets.fromLTRB(inset, 18, inset, 16),
                child: CallbackShortcuts(
                  bindings: {
                    const SingleActivator(LogicalKeyboardKey.escape): () {
                      if (_reading) _returnToSignals();
                    },
                  },
                  child: FocusTraversalGroup(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        ConstrainedBox(
                          constraints: BoxConstraints(maxHeight: height * .36),
                          child: SingleChildScrollView(
                            child: focused
                                ? Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      TextButton.icon(
                                        key: const Key('bmp03-brief-return'),
                                        focusNode: _returnFocus,
                                        onPressed: _returnToSignals,
                                        icon: const Icon(
                                          Icons.arrow_back_rounded,
                                        ),
                                        label: Text(
                                          _readingCopy(context, 'return'),
                                        ),
                                      ),
                                      const SizedBox(height: 8),
                                      _FocusBand(snapshot: snapshot),
                                    ],
                                  )
                                : header,
                          ),
                        ),
                        const SizedBox(height: 14),
                        Expanded(child: content),
                      ],
                    ),
                  ),
                ),
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
    return Semantics(
      container: true,
      label: title,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            Icons.center_focus_strong,
            size: 16,
            color: LumenisTheme.of(context).muted,
          ),
          const SizedBox(width: 7),
          Expanded(
            child: Text(
              title,
              style: TextStyle(
                color: LumenisTheme.of(context).muted,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _KindFilters extends StatelessWidget {
  const _KindFilters({
    required this.kinds,
    required this.selected,
    required this.onChanged,
    required this.snapshot,
    required this.focusNode,
  });

  final List<String> kinds;
  final String? selected;
  final ValueChanged<String?> onChanged;
  final Bmp03Snapshot snapshot;
  final FocusNode focusNode;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    return Wrap(
      spacing: 9,
      runSpacing: 9,
      children: [
        FilterChip(
          focusNode: focusNode,
          selected: selected == null,
          label: Text(copy.text('common.all')),
          onSelected: (_) => onChanged(null),
        ),
        for (final kind in kinds)
          FilterChip(
            selected: selected == kind,
            label: Text(_kindLabel(context, snapshot, kind)),
            onSelected: (value) => onChanged(value ? kind : null),
          ),
      ],
    );
  }

  String _kindLabel(BuildContext context, Bmp03Snapshot snapshot, String kind) {
    for (final signal in snapshot.signals) {
      if (signal.kind == kind) {
        return signal.localizedKind(_languageCode(context));
      }
    }
    return kind;
  }
}

class _RadarPanel extends StatelessWidget {
  const _RadarPanel({
    required this.signals,
    required this.selectedId,
    required this.onSelect,
    required this.focusNodes,
    required this.showRadar,
  });

  final List<Bmp03Signal> signals;
  final String? selectedId;
  final ValueChanged<String> onSelect;
  final Map<String, FocusNode> focusNodes;
  final bool showRadar;

  @override
  Widget build(BuildContext context) {
    return _Panel(
      padding: const EdgeInsets.fromLTRB(18, 18, 18, 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (showRadar) ...[
            Text(
              '${context.lumenisL10n.text('comp.trend')} · ${context.lumenisL10n.text('comp.confidence')}',
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
            if (signals.any(
              (signal) => signal.confidence == null || signal.momentum == null,
            ))
              Text(
                _readingCopy(context, 'chartUnknown'),
                style: TextStyle(
                  color: LumenisTheme.of(context).muted,
                  fontSize: 12,
                ),
              ),
          ],
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
                  focusNode: focusNodes[signal.id],
                  onTap: () => onSelect(signal.id),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(
                      vertical: 12,
                      horizontal: 4,
                    ),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Icon(
                          selected
                              ? Icons.radio_button_checked
                              : Icons.radio_button_unchecked,
                          size: 16,
                          color: selected
                              ? LumenisTheme.of(context).bmp
                              : LumenisTheme.of(context).quiet,
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          flex: 3,
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                signal.title,
                                style: TextStyle(
                                  color: LumenisTheme.of(context).foreground,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                              const SizedBox(height: 4),
                              Text(
                                signal.source,
                                style: TextStyle(
                                  color: LumenisTheme.of(context).muted,
                                  fontSize: 12,
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(width: 10),
                        Flexible(
                          fit: FlexFit.loose,
                          child: Text(
                            signal.localizedKind(_languageCode(context)),
                            textAlign: TextAlign.end,
                            style: TextStyle(
                              color: LumenisTheme.of(context).muted,
                              fontSize: 12,
                            ),
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
            if (signal!.summary != null)
              SelectableText(
                signal!.summary!,
                style: TextStyle(
                  color: LumenisTheme.of(context).foreground,
                  height: 1.6,
                ),
              )
            else
              Text(
                _readingCopy(context, 'summaryMissing'),
                style: TextStyle(color: LumenisTheme.of(context).muted),
              ),
            const SizedBox(height: 20),
            _BriefLine(
              label: copy.text('comp.confidence'),
              value: _percent(context, signal!.confidence),
            ),
            _BriefLine(
              label: copy.text('comp.trend'),
              value: _percent(context, signal!.momentum),
            ),
            _BriefLine(
              label: copy.text('common.source'),
              value: signal!.source,
            ),
            if (signal!.capturedAt != null)
              _BriefLine(
                label: _readingCopy(context, 'captured'),
                value: signal!.capturedAt!,
              ),
            if (signal!.timeWindow != null)
              _BriefLine(
                label: _readingCopy(context, 'window'),
                value: signal!.timeWindow!,
              ),
            const SizedBox(height: 20),
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

  String _percent(BuildContext context, num? value) {
    if (value == null) return _readingCopy(context, 'unknown');
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
      final momentum = signal.momentum;
      final confidence = signal.confidence;
      if (momentum == null || confidence == null) continue;
      final angle = (index / signals.length) * 6.28318 - 1.5708;
      final distance = radius * (momentum / 100);
      final point = Offset(
        center.dx + distance * math.cos(angle),
        center.dy + distance * math.sin(angle),
      );
      canvas.drawLine(
        center,
        point,
        gridPaint..color = palette.bmp.withValues(alpha: 0.25),
      );
      canvas.drawCircle(point, 5 + confidence / 30, dotPaint);
    }
  }

  @override
  bool shouldRepaint(covariant _RadarPainter oldDelegate) =>
      oldDelegate.signals != signals || oldDelegate.palette != palette;
}

String _languageCode(BuildContext context) {
  final language = Localizations.localeOf(context).languageCode;
  return language == 'zh' ? 'zh-CN' : language;
}

String _readingCopy(BuildContext context, String key) {
  const copy = {
    'return': ['返回资讯', 'Back to signals', '정보 목록으로'],
    'unknown': ['未提供', 'Not provided', '제공되지 않음'],
    'captured': ['采集时间', 'Captured', '수집 시간'],
    'window': ['观察期间', 'Observation period', '관찰 기간'],
    'summaryMissing': [
      '这条资讯暂未提供概述。',
      'No summary was supplied for this signal.',
      '이 정보에는 요약이 제공되지 않았습니다.',
    ],
    'chartUnknown': [
      '指标不完整的资讯保留在列表中。',
      'Signals with incomplete metrics remain in the list.',
      '지표가 불완전한 정보도 목록에 유지됩니다.',
    ],
  };
  final language = Localizations.localeOf(context).languageCode;
  return copy[key]![language == 'zh'
      ? 0
      : language == 'ko'
      ? 2
      : 1];
}
