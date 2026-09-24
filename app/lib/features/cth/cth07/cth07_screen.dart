import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../../core/lumenis_core_client.dart';
import '../../../core/lumenis_theme.dart';
import '../../../l10n/lumenis_localizations.dart';
import 'cth07_repository.dart';
import 'cth07_view_model.dart';

class Cth07Screen extends StatefulWidget {
  const Cth07Screen({required this.client, this.repository, super.key});

  final LumenisCoreClient client;
  final Cth07Repository? repository;

  @override
  State<Cth07Screen> createState() => _Cth07ScreenState();
}

class _Cth07ScreenState extends State<Cth07Screen> {
  late Cth07ViewModel _viewModel = _createViewModel()..refresh();

  Cth07ViewModel _createViewModel() => Cth07ViewModel(
    repository: widget.repository ?? CoreCth07Repository(client: widget.client),
  );

  @override
  void didUpdateWidget(covariant Cth07Screen oldWidget) {
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
  Widget build(BuildContext context) => ColoredBox(
    color: LumenisTheme.of(context).canvas,
    child: SafeArea(
      child: AnimatedBuilder(
        animation: _viewModel,
        builder: (context, _) => switch (_viewModel.phase) {
          Cth07LoadPhase.loading => const _Cth07Loading(),
          Cth07LoadPhase.unavailable => _Cth07Unavailable(
            kind: _viewModel.failureKind ?? Cth07FailureKind.server,
            onRetry: _viewModel.refresh,
          ),
          Cth07LoadPhase.ready => _Cth07Workspace(
            data: _viewModel.data!,
            selectedSeries: _viewModel.selectedSeries,
            onSelectSeries: _viewModel.selectSeries,
            onRetry: _viewModel.refresh,
          ),
        },
      ),
    ),
  );
}

class _Cth07Loading extends StatelessWidget {
  const _Cth07Loading();

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    return Semantics(
      liveRegion: true,
      label: copy.text('state.loading_d'),
      child: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const CircularProgressIndicator(),
            const SizedBox(height: 16),
            Text(copy.text('screen.CTH-07')),
          ],
        ),
      ),
    );
  }
}

class _Cth07Unavailable extends StatelessWidget {
  const _Cth07Unavailable({required this.kind, required this.onRetry});

  final Cth07FailureKind kind;
  final VoidCallback onRetry;

  String _detail(LumenisLocalizations copy) => switch (kind) {
    Cth07FailureKind.contextUnavailable => copy.text(
      'cth01.context_unavailable',
    ),
    Cth07FailureKind.pageNotBound || Cth07FailureKind.focusNotBound =>
      copy.text('context.screen_binding_unavailable'),
    Cth07FailureKind.authentication => copy.text('cth01.login_required'),
    Cth07FailureKind.permissionDenied => copy.text('cth01.access_unavailable'),
    Cth07FailureKind.offline => copy.text('cth01.connection_unavailable'),
    Cth07FailureKind.server => copy.text('cth01.generic_unavailable'),
  };

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    final binding =
        kind == Cth07FailureKind.pageNotBound ||
        kind == Cth07FailureKind.focusNotBound;
    return LayoutBuilder(
      builder: (context, constraints) => Align(
        alignment: Alignment.topCenter,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 720),
          child: Padding(
            padding: EdgeInsets.all(constraints.maxWidth < 480 ? 22 : 32),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  binding
                      ? copy.text('cth01.subject_unavailable')
                      : copy.text('cth01.operation_unavailable'),
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
                const SizedBox(height: 12),
                Text(
                  _detail(copy),
                  style: TextStyle(
                    color: LumenisTheme.of(context).muted,
                    height: 1.55,
                  ),
                ),
                const SizedBox(height: 22),
                FilledButton.tonalIcon(
                  onPressed: onRetry,
                  icon: const Icon(Icons.refresh_rounded),
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

class _Cth07Workspace extends StatelessWidget {
  const _Cth07Workspace({
    required this.data,
    required this.selectedSeries,
    required this.onSelectSeries,
    required this.onRetry,
  });

  final Cth07ScreenData data;
  final Cth07Series? selectedSeries;
  final ValueChanged<int> onSelectSeries;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, constraints) {
      final wide = constraints.maxWidth >= 1180;
      final padding = constraints.maxWidth < 480
          ? 18.0
          : constraints.maxWidth < 900
          ? 28.0
          : 40.0;
      final definition = _DefinitionRail(data: data);
      final chart = _TrendCanvas(
        data: data,
        selectedSeries: selectedSeries,
        onSelectSeries: onSelectSeries,
      );
      final decomposition = _DecompositionPanel(
        data: data,
        selectedSeries: selectedSeries,
      );
      return Align(
        alignment: Alignment.topCenter,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1760),
          child: SingleChildScrollView(
            padding: EdgeInsets.fromLTRB(padding, 28, padding, 48),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _Header(data: data, onRetry: onRetry),
                const SizedBox(height: 24),
                if (wide)
                  Row(
                    key: const ValueKey('cth07/desktop-layout'),
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      SizedBox(width: 255, child: definition),
                      const SizedBox(width: 24),
                      Expanded(flex: 7, child: chart),
                      const SizedBox(width: 24),
                      Expanded(flex: 3, child: decomposition),
                    ],
                  )
                else
                  Column(
                    key: const ValueKey('cth07/mobile-layout'),
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      chart,
                      const SizedBox(height: 18),
                      definition,
                      const SizedBox(height: 18),
                      decomposition,
                    ],
                  ),
              ],
            ),
          ),
        ),
      );
    },
  );
}

class _Header extends StatelessWidget {
  const _Header({required this.data, required this.onRetry});

  final Cth07ScreenData data;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    final contextLabel = _contextLabel(context, data.context);
    return Wrap(
      alignment: WrapAlignment.spaceBetween,
      crossAxisAlignment: WrapCrossAlignment.center,
      runSpacing: 15,
      spacing: 20,
      children: [
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              copy.text('screen.CTH-07'),
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 9),
            Semantics(
              label: contextLabel,
              child: Text(
                contextLabel,
                style: TextStyle(
                  color: LumenisTheme.of(context).foreground,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
            const SizedBox(height: 7),
            Text(
              data.generatedAt.isEmpty
                  ? copy.text('cth01.activity.detail')
                  : '${copy.text('cth01.activity.detail')} · ${data.generatedAt}',
              style: TextStyle(color: LumenisTheme.of(context).muted),
            ),
          ],
        ),
        FilledButton.tonalIcon(
          onPressed: onRetry,
          icon: const Icon(Icons.refresh_rounded),
          label: Text(copy.text('common.refresh')),
        ),
      ],
    );
  }
}

class _DefinitionRail extends StatelessWidget {
  const _DefinitionRail({required this.data});

  final Cth07ScreenData data;

  @override
  Widget build(BuildContext context) {
    final definition = data.definition;
    final copy = context.lumenisL10n;
    return _Panel(
      key: const ValueKey('cth07/definition-rail'),
      title: copy.text('common.detail'),
      detail: copy.text('cth01.metrics.detail'),
      child: definition == null || !definition.isComplete
          ? _InlineState(text: copy.text('state.empty_notcollected'))
          : Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _Definition(
                  label: copy.text('common.type'),
                  value: definition.numerator,
                ),
                _Definition(
                  label: copy.text('common.all'),
                  value: definition.denominator,
                ),
                _Definition(
                  label: copy.text('common.time'),
                  value: definition.timeWindow,
                ),
                _Definition(
                  label: copy.text('freshness.stale'),
                  value: definition.freshness,
                ),
                if (definition.source.isNotEmpty)
                  _Definition(
                    label: copy.text('common.source'),
                    value: definition.source,
                  ),
              ],
            ),
    );
  }
}

class _Definition extends StatelessWidget {
  const _Definition({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 15),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: TextStyle(color: LumenisTheme.of(context).quiet, fontSize: 11),
        ),
        const SizedBox(height: 4),
        Text(
          value,
          style: TextStyle(
            color: LumenisTheme.of(context).foreground,
            height: 1.35,
          ),
        ),
      ],
    ),
  );
}

class _TrendCanvas extends StatelessWidget {
  const _TrendCanvas({
    required this.data,
    required this.selectedSeries,
    required this.onSelectSeries,
  });

  final Cth07ScreenData data;
  final Cth07Series? selectedSeries;
  final ValueChanged<int> onSelectSeries;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    return _Panel(
      key: const ValueKey('cth07/trend-canvas'),
      title: copy.text('screen.CTH-07'),
      detail: copy.text('cth01.activity.detail'),
      child: !data.trendAvailable
          ? _InlineState(text: copy.text('state.empty_notcollected'))
          : Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    for (var index = 0; index < data.series.length; index++)
                      ChoiceChip(
                        label: Text(data.series[index].label),
                        selected: data.series[index] == selectedSeries,
                        onSelected: (_) => onSelectSeries(index),
                      ),
                  ],
                ),
                const SizedBox(height: 20),
                _Chart(data: data, selectedSeries: selectedSeries),
                const SizedBox(height: 18),
                _SeriesTable(data: data, selectedSeries: selectedSeries),
              ],
            ),
    );
  }
}

class _Chart extends StatelessWidget {
  const _Chart({required this.data, required this.selectedSeries});

  final Cth07ScreenData data;
  final Cth07Series? selectedSeries;

  @override
  Widget build(BuildContext context) {
    final series = selectedSeries ?? data.series.first;
    final copy = context.lumenisL10n;
    return Semantics(
      label:
          '${series.label}, ${data.labels.length} ${copy.text('common.time')}',
      child: SizedBox(
        height: 250,
        width: double.infinity,
        child: CustomPaint(
          painter: _TrendPainter(
            values: series.values,
            color: LumenisTheme.of(context).cth,
          ),
        ),
      ),
    );
  }
}

class _TrendPainter extends CustomPainter {
  const _TrendPainter({required this.values, required this.color});

  final List<num> values;
  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    if (values.isEmpty) return;
    final minValue = values.reduce(math.min).toDouble();
    final maxValue = values.reduce(math.max).toDouble();
    final range = maxValue - minValue == 0 ? 1.0 : maxValue - minValue;
    final paint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.5
      ..strokeCap = StrokeCap.round;
    final path = Path();
    for (var index = 0; index < values.length; index++) {
      final x = values.length == 1
          ? size.width / 2
          : index * size.width / (values.length - 1);
      final y =
          size.height -
          ((values[index].toDouble() - minValue) / range) * (size.height - 18) -
          9;
      if (index == 0) {
        path.moveTo(x, y);
      } else {
        path.lineTo(x, y);
      }
    }
    canvas.drawPath(path, paint);
    final dotPaint = Paint()
      ..color = color
      ..style = PaintingStyle.fill;
    for (var index = 0; index < values.length; index++) {
      final x = values.length == 1
          ? size.width / 2
          : index * size.width / (values.length - 1);
      final y =
          size.height -
          ((values[index].toDouble() - minValue) / range) * (size.height - 18) -
          9;
      canvas.drawCircle(Offset(x, y), 3.5, dotPaint);
    }
  }

  @override
  bool shouldRepaint(covariant _TrendPainter oldDelegate) =>
      oldDelegate.values != values || oldDelegate.color != color;
}

class _SeriesTable extends StatelessWidget {
  const _SeriesTable({required this.data, required this.selectedSeries});

  final Cth07ScreenData data;
  final Cth07Series? selectedSeries;

  @override
  Widget build(BuildContext context) {
    final series = selectedSeries ?? data.series.first;
    final copy = context.lumenisL10n;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          copy.text('common.detail'),
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: 8),
        for (var index = 0; index < data.labels.length; index++)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 6),
            child: Row(
              children: [
                Expanded(
                  child: Text(
                    data.labels[index],
                    style: TextStyle(color: LumenisTheme.of(context).muted),
                  ),
                ),
                Text(
                  '${series.values[index]}',
                  style: TextStyle(
                    color: LumenisTheme.of(context).foreground,
                    fontFeatures: [FontFeature.tabularFigures()],
                  ),
                ),
              ],
            ),
          ),
      ],
    );
  }
}

class _DecompositionPanel extends StatelessWidget {
  const _DecompositionPanel({required this.data, required this.selectedSeries});

  final Cth07ScreenData data;
  final Cth07Series? selectedSeries;

  @override
  Widget build(BuildContext context) {
    final series =
        selectedSeries ?? (data.series.isEmpty ? null : data.series.first);
    final delta = series == null || series.values.length < 2
        ? null
        : series.values.last - series.values.first;
    final copy = context.lumenisL10n;
    return _Panel(
      key: const ValueKey('cth07/decomposition'),
      title: copy.text('common.status'),
      detail: copy.text('cth01.activity.detail'),
      child: series == null || delta == null
          ? _InlineState(text: copy.text('common.empty'))
          : Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  series.label,
                  style: TextStyle(
                    color: LumenisTheme.of(context).foreground,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 10),
                Text(
                  '${copy.text('common.status')}: $delta',
                  style: TextStyle(
                    color: LumenisTheme.of(context).cth,
                    fontSize: 18,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 14),
                Text(
                  copy.text('cth01.scope.partial'),
                  style: TextStyle(
                    color: LumenisTheme.of(context).muted,
                    height: 1.5,
                  ),
                ),
              ],
            ),
    );
  }
}

class _Panel extends StatelessWidget {
  const _Panel({
    super.key,
    required this.title,
    required this.detail,
    required this.child,
  });

  final String title;
  final String detail;
  final Widget child;

  @override
  Widget build(BuildContext context) => Container(
    decoration: BoxDecoration(
      color: LumenisTheme.of(context).surface,
      borderRadius: BorderRadius.circular(18),
      border: Border.all(color: LumenisTheme.of(context).line),
    ),
    padding: const EdgeInsets.all(20),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: Theme.of(context).textTheme.titleLarge?.copyWith(fontSize: 20),
        ),
        const SizedBox(height: 6),
        Text(
          detail,
          style: TextStyle(color: LumenisTheme.of(context).muted, height: 1.45),
        ),
        const SizedBox(height: 16),
        child,
      ],
    ),
  );
}

class _InlineState extends StatelessWidget {
  const _InlineState({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) => Semantics(
    liveRegion: true,
    label: text,
    child: Padding(
      padding: const EdgeInsets.symmetric(vertical: 18),
      child: Text(
        text,
        style: TextStyle(color: LumenisTheme.of(context).muted, height: 1.5),
      ),
    ),
  );
}

String _contextLabel(BuildContext context, Cth07Context value) {
  final copy = context.lumenisL10n;
  if (value.isGlobal) return copy.text('context.mode.global_all');
  final locale = Localizations.localeOf(context);
  return value.displayName?[locale.toLanguageTag()] ??
      value.displayName?[locale.languageCode] ??
      value.displayName?['zh-CN'] ??
      copy.text('context.mode.focus');
}
