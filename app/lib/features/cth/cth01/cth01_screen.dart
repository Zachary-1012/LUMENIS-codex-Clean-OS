import 'package:flutter/services.dart';
import 'package:flutter/material.dart';

import '../../../core/lumenis_core_client.dart';
import '../../../core/lumenis_theme.dart';
import '../../../l10n/lumenis_localizations.dart';
import 'cth01_repository.dart';
import 'cth01_view_model.dart';

class Cth01Screen extends StatefulWidget {
  const Cth01Screen({required this.client, this.onNavigate, super.key});

  final LumenisCoreClient client;
  final ValueChanged<String>? onNavigate;

  @override
  State<Cth01Screen> createState() => _Cth01ScreenState();
}

class _Cth01ScreenState extends State<Cth01Screen> {
  late Cth01ViewModel _viewModel;

  @override
  void initState() {
    super.initState();
    _viewModel = Cth01ViewModel(Cth01Repository(widget.client))..load();
  }

  @override
  void didUpdateWidget(covariant Cth01Screen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.client != widget.client) {
      _viewModel.dispose();
      _viewModel = Cth01ViewModel(Cth01Repository(widget.client))..load();
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
          builder: (context, _) {
            final copy = context.lumenisL10n;
            return switch (_viewModel.status) {
              Cth01LoadStatus.loading => const _LoadingState(),
              Cth01LoadStatus.blocked => _UnavailableState(
                title: copy.text('cth01.subject_unavailable'),
                detail: copy.text(
                  _viewModel.message == Cth01LoadMessage.pageNotBound
                      ? 'context.screen_binding_unavailable'
                      : 'cth01.context_unavailable',
                ),
                actionLabel: copy.text('cth01.retry'),
                onAction: _viewModel.load,
                onNavigate: widget.onNavigate,
              ),
              Cth01LoadStatus.failed => _UnavailableState(
                title: copy.text('cth01.operation_unavailable'),
                detail: copy.text(_failureCopyKey(_viewModel.message)),
                actionLabel: copy.text('cth01.retry'),
                onAction: _viewModel.load,
                onNavigate: widget.onNavigate,
              ),
              Cth01LoadStatus.loaded => _Cth01Workspace(
                data: _viewModel.data!,
                selectedSignalIndex: _viewModel.selectedSignalIndex,
                onSelectSignal: _viewModel.selectSignal,
                onReturnToSignals: _viewModel.returnToSignals,
                onRetry: _viewModel.load,
              ),
            };
          },
        ),
      ),
    );
  }
}

String _failureCopyKey(Cth01LoadMessage? message) => switch (message) {
  // The local product opens directly. Authentication remains a server-side
  // boundary for protected scopes, but the workspace never sends the user to
  // an account wall from the default GLOBAL/ALL surface.
  Cth01LoadMessage.loginRequired => 'cth01.generic_unavailable',
  Cth01LoadMessage.accessUnavailable => 'cth01.generic_unavailable',
  Cth01LoadMessage.connectionUnavailable => 'cth01.connection_unavailable',
  _ => 'cth01.generic_unavailable',
};

class _LoadingState extends StatelessWidget {
  const _LoadingState();

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    return Semantics(
      liveRegion: true,
      label: copy.text('cth01.loading'),
      child: Align(
        alignment: Alignment.topCenter,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 720),
          child: Padding(
            padding: const EdgeInsets.all(28),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  copy.text('screen.CTH-01'),
                  style: TextStyle(
                    color: LumenisTheme.of(context).foreground,
                    fontSize: 26,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 20),
                _SkeletonLine(width: 250),
                const SizedBox(height: 12),
                _SkeletonLine(width: double.infinity),
                const SizedBox(height: 8),
                _SkeletonLine(width: 430),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _SkeletonLine extends StatelessWidget {
  const _SkeletonLine({required this.width});

  final double width;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: width,
      height: 13,
      decoration: BoxDecoration(
        color: LumenisTheme.of(context).surface,
        borderRadius: BorderRadius.circular(4),
      ),
    );
  }
}

class _UnavailableState extends StatelessWidget {
  const _UnavailableState({
    required this.title,
    required this.detail,
    required this.actionLabel,
    required this.onAction,
    this.onNavigate,
  });

  final String title;
  final String detail;
  final String actionLabel;
  final VoidCallback onAction;
  final ValueChanged<String>? onNavigate;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) => Align(
        alignment: Alignment.topCenter,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 720),
          child: SingleChildScrollView(
            padding: EdgeInsets.all(constraints.maxWidth < 480 ? 22 : 32),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (onNavigate != null) ...[
                  Text(
                    context.lumenisL10n.text('workflow.observe'),
                    style: Theme.of(context).textTheme.headlineLarge?.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 28),
                  _OperationsEntries(onNavigate: onNavigate!),
                  const SizedBox(height: 32),
                  const Divider(),
                  const SizedBox(height: 20),
                ],
                Text(
                  title,
                  style: TextStyle(
                    color: LumenisTheme.of(context).foreground,
                    fontSize: 20,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  detail,
                  style: TextStyle(
                    color: LumenisTheme.of(context).muted,
                    height: 1.5,
                  ),
                ),
                const SizedBox(height: 22),
                _CthTextButton(label: actionLabel, onPressed: onAction),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _OperationsEntries extends StatelessWidget {
  const _OperationsEntries({required this.onNavigate});
  final ValueChanged<String> onNavigate;

  @override
  Widget build(BuildContext context) => Column(
    children: [
      for (final entry in const [
        ('workflow.observe', 'CTH-03', Icons.radar_rounded),
        ('workflow.resolve', 'CTH-04', Icons.view_timeline_outlined),
        ('workflow.plan', 'CTH-10', Icons.article_outlined),
      ])
        Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: Material(
            color: LumenisTheme.of(context).surface,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
              side: BorderSide(color: LumenisTheme.of(context).line),
            ),
            clipBehavior: Clip.antiAlias,
            child: ListTile(
              contentPadding: const EdgeInsets.symmetric(
                horizontal: 20,
                vertical: 12,
              ),
              leading: Icon(entry.$3, color: LumenisTheme.of(context).cth),
              title: Text(context.lumenisL10n.text(entry.$1)),
              subtitle: Text(context.lumenisL10n.text('screen.${entry.$2}')),
              trailing: const Icon(Icons.arrow_outward_rounded, size: 18),
              onTap: () => onNavigate(entry.$2),
            ),
          ),
        ),
    ],
  );
}

class _Cth01Workspace extends StatelessWidget {
  const _Cth01Workspace({
    required this.data,
    required this.selectedSignalIndex,
    required this.onSelectSignal,
    required this.onReturnToSignals,
    required this.onRetry,
  });

  final Cth01ScreenData data;
  final int? selectedSignalIndex;
  final ValueChanged<int> onSelectSignal;
  final VoidCallback onReturnToSignals;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final width = constraints.maxWidth;
        final wide = width >= 1100;
        final compact = width >= 768 && !wide;
        final sidePadding = width < 480
            ? 18.0
            : width < 900
            ? 28.0
            : 40.0;

        final signals = _SignalFlow(
          data: data,
          selectedSignalIndex: selectedSignalIndex,
          onSelectSignal: onSelectSignal,
        );
        final inspection = _SignalInspection(
          data: data,
          selectedSignalIndex: selectedSignalIndex,
          onReturn: onReturnToSignals,
        );
        final insights = _InsightColumn(data: data);

        return Focus(
          onKeyEvent: (node, event) {
            if (selectedSignalIndex != null &&
                event is KeyDownEvent &&
                event.logicalKey == LogicalKeyboardKey.escape) {
              onReturnToSignals();
              return KeyEventResult.handled;
            }
            return KeyEventResult.ignored;
          },
          child: Align(
            alignment: Alignment.topCenter,
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 1680),
              child: SingleChildScrollView(
                padding: EdgeInsets.fromLTRB(sidePadding, 30, sidePadding, 52),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _PageHeader(data: data, onRetry: onRetry),
                    const SizedBox(height: 24),
                    _ScopeNotice(data: data),
                    const SizedBox(height: 22),
                    if (wide) ...[
                      _MetricSpine(data: data, compact: false),
                      const SizedBox(height: 28),
                    ],
                    if (wide)
                      Row(
                        key: const ValueKey('cth01/layout-desktop'),
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Expanded(flex: 7, child: signals),
                          const SizedBox(width: 32),
                          Expanded(
                            flex: 4,
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                inspection,
                                if (selectedSignalIndex != null)
                                  const SizedBox(height: 24),
                                insights,
                              ],
                            ),
                          ),
                        ],
                      )
                    else
                      Column(
                        key: const ValueKey('cth01/layout-single-task'),
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          signals,
                          if (compact || selectedSignalIndex != null) ...[
                            const SizedBox(height: 22),
                            inspection,
                          ],
                          const SizedBox(height: 28),
                          insights,
                          const SizedBox(height: 24),
                          _MetricSpine(data: data, compact: true),
                        ],
                      ),
                  ],
                ),
              ),
            ),
          ),
        );
      },
    );
  }
}

class _PageHeader extends StatelessWidget {
  const _PageHeader({required this.data, required this.onRetry});

  final Cth01ScreenData data;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    final locale = Localizations.localeOf(context);
    final contextName = data.contextMode == 'GLOBAL_ALL'
        ? copy.text('context.mode.global_all')
        : data.contextDisplayName?[locale.toLanguageTag()] ??
              data.contextDisplayName?[locale.languageCode] ??
              data.contextDisplayName?['en'] ??
              data.contextDisplayName?['zh-CN'] ??
              copy.text('context.selector.unnamed_subject');
    return Wrap(
      alignment: WrapAlignment.spaceBetween,
      crossAxisAlignment: WrapCrossAlignment.center,
      runSpacing: 18,
      spacing: 20,
      children: [
        ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 820),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                copy.text('screen.CTH-01'),
                style: TextStyle(
                  color: LumenisTheme.of(context).foreground,
                  fontSize: 28,
                  height: 1.2,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 13),
              Semantics(
                key: const ValueKey('cth01/current-subject'),
                label: contextName,
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      width: 7,
                      height: 7,
                      decoration: BoxDecoration(
                        color: LumenisTheme.of(context).cth,
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(width: 10),
                    Flexible(
                      child: Text(
                        contextName,
                        style: TextStyle(
                          color: LumenisTheme.of(context).foreground,
                          fontSize: 15,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 7),
              Text(
                copy.text('cth01.summary'),
                style: TextStyle(
                  color: LumenisTheme.of(context).muted,
                  height: 1.45,
                ),
              ),
            ],
          ),
        ),
        _CthTextButton(label: copy.text('cth01.refresh'), onPressed: onRetry),
      ],
    );
  }
}

class _ScopeNotice extends StatelessWidget {
  const _ScopeNotice({required this.data});

  final Cth01ScreenData data;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    final complete =
        data.footfall.hasValue &&
        data.memberSales.hasValue &&
        data.negativeVoice.hasValue;
    final detail = copy.text(
      complete ? 'cth01.scope.complete' : 'cth01.scope.partial',
    );

    return Semantics(
      key: const ValueKey('cth01/data-boundary'),
      liveRegion: true,
      label: detail,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 12),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Padding(
              padding: const EdgeInsets.only(top: 6, right: 11),
              child: Container(
                width: 7,
                height: 7,
                decoration: BoxDecoration(
                  color: LumenisTheme.of(context).caution,
                  shape: BoxShape.circle,
                ),
              ),
            ),
            Expanded(
              child: Text(
                detail,
                style: TextStyle(
                  color: LumenisTheme.of(context).caution,
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

class _MetricSpine extends StatelessWidget {
  const _MetricSpine({required this.data, required this.compact});

  final Cth01ScreenData data;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    return DecoratedBox(
      decoration: BoxDecoration(
        border: Border(
          top: BorderSide(color: LumenisTheme.of(context).line),
          bottom: BorderSide(color: LumenisTheme.of(context).line),
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _SectionHeading(
              title: copy.text('cth01.metrics.heading'),
              detail: copy.text('cth01.metrics.detail'),
            ),
            const SizedBox(height: 15),
            if (compact)
              Column(
                children: [
                  _MetricLine(
                    key: const ValueKey('cth01/metric-negative-voice'),
                    label: copy.text('cth01.metric.negative_voice'),
                    metric: data.negativeVoice,
                    readyUnit: copy.text('cth01.metric.unit.records'),
                  ),
                  const _ThinRule(),
                  _MetricLine(
                    key: const ValueKey('cth01/metric-footfall'),
                    label: copy.text('cth01.metric.footfall'),
                    metric: data.footfall,
                  ),
                  const _ThinRule(),
                  _MetricLine(
                    key: const ValueKey('cth01/metric-member-sales'),
                    label: copy.text('cth01.metric.member_sales'),
                    metric: data.memberSales,
                  ),
                ],
              )
            else
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: _MetricLine(
                      key: const ValueKey('cth01/metric-negative-voice'),
                      label: copy.text('cth01.metric.negative_voice'),
                      metric: data.negativeVoice,
                      readyUnit: copy.text('cth01.metric.unit.records'),
                    ),
                  ),
                  const _VerticalRule(),
                  Expanded(
                    child: _MetricLine(
                      key: const ValueKey('cth01/metric-footfall'),
                      label: copy.text('cth01.metric.footfall'),
                      metric: data.footfall,
                    ),
                  ),
                  const _VerticalRule(),
                  Expanded(
                    child: _MetricLine(
                      key: const ValueKey('cth01/metric-member-sales'),
                      label: copy.text('cth01.metric.member_sales'),
                      metric: data.memberSales,
                    ),
                  ),
                ],
              ),
          ],
        ),
      ),
    );
  }
}

class _MetricLine extends StatelessWidget {
  const _MetricLine({
    required this.label,
    required this.metric,
    this.readyUnit = '',
    super.key,
  });

  final String label;
  final Cth01Metric metric;
  final String readyUnit;

  @override
  Widget build(BuildContext context) {
    final stateText = metric.hasValue
        ? _formatNumber(metric.value!) +
              (readyUnit.isEmpty ? metric.unit : readyUnit)
        : _metricAvailabilityLabel(context, metric.state);
    final stateColor = metric.hasValue
        ? LumenisTheme.of(context).foreground
        : metric.state == Cth01BackendState.notCollected
        ? LumenisTheme.of(context).caution
        : LumenisTheme.of(context).muted;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: TextStyle(
              color: LumenisTheme.of(context).muted,
              fontSize: 13,
            ),
          ),
          const SizedBox(height: 6),
          Semantics(
            label: '$label：$stateText',
            child: Text(
              stateText,
              style: TextStyle(
                color: stateColor,
                fontSize: metric.hasValue ? 22 : 15,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _SignalFlow extends StatelessWidget {
  const _SignalFlow({
    required this.data,
    required this.selectedSignalIndex,
    required this.onSelectSignal,
  });

  final Cth01ScreenData data;
  final int? selectedSignalIndex;
  final ValueChanged<int> onSelectSignal;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _SectionHeading(
          title: copy.text('cth01.activity.heading'),
          detail: copy.text('cth01.activity.detail'),
        ),
        const SizedBox(height: 10),
        _TrendAvailability(),
        const SizedBox(height: 16),
        if (data.signals.isEmpty)
          _UnavailableInline(
            key: const ValueKey('cth01/events-empty-or-unknown'),
            title: _signalEmptyTitle(context, data.eventState),
            detail: _signalEmptyDetail(context, data.eventState),
          )
        else ...[
          for (var index = 0; index < data.signals.length; index++)
            _SignalRow(
              key: ValueKey('cth01/signal-$index'),
              signal: data.signals[index],
              selected: selectedSignalIndex == index,
              onTap: () => onSelectSignal(index),
            ),
        ],
      ],
    );
  }
}

class _SignalRow extends StatefulWidget {
  const _SignalRow({
    required this.signal,
    required this.selected,
    required this.onTap,
    super.key,
  });

  final Cth01Signal signal;
  final bool selected;
  final VoidCallback onTap;

  @override
  State<_SignalRow> createState() => _SignalRowState();
}

class _SignalRowState extends State<_SignalRow> {
  bool _showFocus = false;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    final signal = widget.signal;
    final time = [
      signal.date,
      signal.time,
    ].where((value) => value.isNotEmpty && value != '—').join(' · ');
    final severity = _severityLabel(context, signal.level);
    final dateLabel = time.isEmpty
        ? copy.text('cth01.signal.time_missing')
        : time;
    final title = signal.title.isEmpty
        ? copy.text('cth01.signal.unnamed')
        : signal.title;
    final semanticLabel = '$dateLabel，$severity，$title';

    return FocusableActionDetector(
      mouseCursor: SystemMouseCursors.click,
      onShowFocusHighlight: (value) => setState(() => _showFocus = value),
      shortcuts: const <ShortcutActivator, Intent>{
        SingleActivator(LogicalKeyboardKey.enter): ActivateIntent(),
        SingleActivator(LogicalKeyboardKey.space): ActivateIntent(),
      },
      actions: <Type, Action<Intent>>{
        ActivateIntent: CallbackAction<ActivateIntent>(
          onInvoke: (intent) {
            widget.onTap();
            return null;
          },
        ),
      },
      child: Semantics(
        button: true,
        selected: widget.selected,
        label: semanticLabel,
        onTap: widget.onTap,
        child: GestureDetector(
          behavior: HitTestBehavior.opaque,
          onTap: widget.onTap,
          child: Container(
            constraints: const BoxConstraints(minHeight: 58),
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
            decoration: BoxDecoration(
              color: widget.selected
                  ? LumenisTheme.of(context).surfaceRaised
                  : null,
              border: Border(
                top: _showFocus || widget.selected
                    ? BorderSide(color: LumenisTheme.of(context).cth)
                    : BorderSide.none,
                bottom: BorderSide(color: LumenisTheme.of(context).line),
                left: BorderSide(
                  color: _showFocus
                      ? LumenisTheme.of(context).cth
                      : const Color(0x00000000),
                  width: 1,
                ),
                right: BorderSide(
                  color: _showFocus
                      ? LumenisTheme.of(context).cth
                      : const Color(0x00000000),
                  width: 1,
                ),
              ),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Padding(
                  padding: const EdgeInsets.only(top: 7, right: 13),
                  child: Container(
                    width: 8,
                    height: 8,
                    decoration: BoxDecoration(
                      color: _severityColor(context, signal.level),
                      shape: BoxShape.circle,
                    ),
                  ),
                ),
                SizedBox(
                  width: 100,
                  child: Text(
                    dateLabel,
                    style: TextStyle(
                      color: LumenisTheme.of(context).quiet,
                      fontSize: 12,
                      height: 1.45,
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Wrap(
                        spacing: 9,
                        runSpacing: 4,
                        crossAxisAlignment: WrapCrossAlignment.center,
                        children: [
                          Text(
                            title,
                            style: TextStyle(
                              color: LumenisTheme.of(context).foreground,
                              fontWeight: FontWeight.w600,
                              height: 1.4,
                            ),
                          ),
                          Text(
                            severity,
                            style: TextStyle(
                              color: _severityColor(context, signal.level),
                              fontSize: 12,
                            ),
                          ),
                        ],
                      ),
                      if (signal.summary.isNotEmpty) ...[
                        const SizedBox(height: 5),
                        Text(
                          signal.summary,
                          maxLines: 3,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            color: LumenisTheme.of(context).muted,
                            fontSize: 13,
                            height: 1.45,
                          ),
                        ),
                      ],
                    ],
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

class _SignalInspection extends StatelessWidget {
  const _SignalInspection({
    required this.data,
    required this.selectedSignalIndex,
    required this.onReturn,
  });

  final Cth01ScreenData data;
  final int? selectedSignalIndex;
  final VoidCallback onReturn;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    if (selectedSignalIndex == null ||
        selectedSignalIndex! >= data.signals.length) {
      return const SizedBox.shrink();
    }
    final signal = data.signals[selectedSignalIndex!];
    final timestamp = [
      signal.date,
      signal.time,
    ].where((value) => value.isNotEmpty && value != '—').join(' · ');

    return Container(
      key: const ValueKey('cth01/signal-inspection'),
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(17, 16, 17, 15),
      decoration: BoxDecoration(
        color: LumenisTheme.of(context).surface,
        border: Border.all(
          color: LumenisTheme.of(context).cth.withValues(alpha: 0.55),
        ),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _SectionHeading(
            title: copy.text('cth01.signal.detail_heading'),
            detail: copy.text('cth01.signal.detail_description'),
          ),
          const SizedBox(height: 12),
          Text(
            signal.title.isEmpty
                ? copy.text('cth01.signal.unnamed')
                : signal.title,
            style: TextStyle(
              color: LumenisTheme.of(context).foreground,
              fontSize: 17,
              fontWeight: FontWeight.w600,
              height: 1.4,
            ),
          ),
          const SizedBox(height: 9),
          _DetailLine(
            label: copy.text('cth01.field.time'),
            value: timestamp.isEmpty
                ? copy.text('cth01.field.not_provided')
                : timestamp,
          ),
          _DetailLine(
            label: copy.text('cth01.field.severity'),
            value: _severityLabel(context, signal.level),
          ),
          if (signal.summary.isNotEmpty)
            _DetailLine(
              label: copy.text('cth01.field.summary'),
              value: signal.summary,
            ),
          if (signal.tags.isNotEmpty)
            _DetailLine(
              label: copy.text('cth01.field.tags'),
              value: signal.tags.join(' · '),
            ),
          const SizedBox(height: 8),
          Text(
            copy.text('cth01.source.unavailable'),
            style: TextStyle(
              color: LumenisTheme.of(context).quiet,
              fontSize: 12,
            ),
          ),
          const SizedBox(height: 11),
          _CthTextButton(
            label: copy.text('cth01.signal.return'),
            onPressed: onReturn,
          ),
        ],
      ),
    );
  }
}

class _InsightColumn extends StatelessWidget {
  const _InsightColumn({required this.data});

  final Cth01ScreenData data;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _DailySummaryView(summary: data.dailySummary),
        const SizedBox(height: 22),
        _RiskNotesView(risks: data.risks),
        const SizedBox(height: 22),
        const _EvidenceLineageState(),
      ],
    );
  }
}

class _DailySummaryView extends StatelessWidget {
  const _DailySummaryView({required this.summary});

  final Cth01DailySummary summary;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    return _ReadSection(
      key: const ValueKey('cth01/daily-summary'),
      title: copy.text('cth01.summary.heading'),
      detail: copy.text('cth01.summary.detail'),
      child: summary.hasValues
          ? Column(
              children: [
                if (summary.riskIndex != null)
                  _FactLine(
                    label: copy.text('cth01.summary.risk_index'),
                    value: '${_formatNumber(summary.riskIndex!)} / 100',
                  ),
                if (summary.subjectHealthScore != null)
                  _FactLine(
                    label: copy.text('cth01.summary.health_score'),
                    value:
                        '${_formatNumber(summary.subjectHealthScore!)} / 100',
                  ),
                if (summary.mediumHighRiskNoteCount != null)
                  _FactLine(
                    label: copy.text('cth01.summary.risk_content'),
                    value: _formatNumber(summary.mediumHighRiskNoteCount!),
                  ),
                const SizedBox(height: 9),
                Text(
                  copy.text('cth01.summary.note'),
                  style: TextStyle(
                    color: LumenisTheme.of(context).quiet,
                    fontSize: 12,
                    height: 1.45,
                  ),
                ),
              ],
            )
          : Text(
              copy.text('cth01.summary.unavailable'),
              style: TextStyle(
                color: LumenisTheme.of(context).muted,
                height: 1.5,
              ),
            ),
    );
  }
}

class _RiskNotesView extends StatelessWidget {
  const _RiskNotesView({required this.risks});

  final List<Cth01RiskNote> risks;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    return _ReadSection(
      key: const ValueKey('cth01/risk-notes'),
      title: copy.text('cth01.risks.heading'),
      detail: copy.text('cth01.risks.detail'),
      child: risks.isEmpty
          ? Text(
              copy.text('cth01.risks.unavailable'),
              style: TextStyle(
                color: LumenisTheme.of(context).muted,
                height: 1.5,
              ),
            )
          : Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                for (var index = 0; index < risks.length; index++) ...[
                  if (index > 0) const _ThinRule(),
                  _RiskNoteLine(risk: risks[index]),
                ],
              ],
            ),
    );
  }
}

class _RiskNoteLine extends StatelessWidget {
  const _RiskNoteLine({required this.risk});

  final Cth01RiskNote risk;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    final details = <String>[_severityLabel(context, risk.level)];
    if (risk.score != null) {
      details.add(
        copy.text(
          'cth01.risks.score',
          values: {'score': _formatNumber(risk.score!)},
        ),
      );
    }

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            risk.title.isEmpty ? copy.text('cth01.risk.unnamed') : risk.title,
            style: TextStyle(
              color: LumenisTheme.of(context).foreground,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 5),
          Text(
            details.join(' · '),
            style: TextStyle(
              color: _severityColor(context, risk.level),
              fontSize: 12,
            ),
          ),
          if (risk.description.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(
              risk.description,
              style: TextStyle(
                color: LumenisTheme.of(context).muted,
                fontSize: 13,
                height: 1.45,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _TrendAvailability extends StatelessWidget {
  const _TrendAvailability();

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    return _UnavailableInline(
      key: ValueKey('cth01/trend-blocked'),
      title: copy.text('cth01.trend.unavailable_title'),
      detail: copy.text('cth01.trend.unavailable_detail'),
    );
  }
}

class _EvidenceLineageState extends StatelessWidget {
  const _EvidenceLineageState();

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    return _UnavailableInline(
      key: ValueKey('cth01/evidence-scope-blocked'),
      title: copy.text('cth01.evidence.unavailable_title'),
      detail: copy.text('cth01.evidence.unavailable_detail'),
    );
  }
}

class _UnavailableInline extends StatelessWidget {
  const _UnavailableInline({
    required this.title,
    required this.detail,
    super.key,
  });

  final String title;
  final String detail;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 11),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.only(top: 5, right: 11),
            child: Container(
              width: 6,
              height: 6,
              decoration: BoxDecoration(
                color: LumenisTheme.of(context).quiet,
                shape: BoxShape.circle,
              ),
            ),
          ),
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
                const SizedBox(height: 5),
                Text(
                  detail,
                  style: TextStyle(
                    color: LumenisTheme.of(context).muted,
                    fontSize: 12,
                    height: 1.45,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ReadSection extends StatelessWidget {
  const _ReadSection({
    required this.title,
    required this.detail,
    required this.child,
    super.key,
  });

  final String title;
  final String detail;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        border: Border(top: BorderSide(color: LumenisTheme.of(context).line)),
      ),
      child: Padding(
        padding: const EdgeInsets.only(top: 17),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _SectionHeading(title: title, detail: detail),
            const SizedBox(height: 12),
            child,
          ],
        ),
      ),
    );
  }
}

class _SectionHeading extends StatelessWidget {
  const _SectionHeading({required this.title, required this.detail});

  final String title;
  final String detail;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: TextStyle(
            color: LumenisTheme.of(context).foreground,
            fontSize: 17,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          detail,
          style: TextStyle(
            color: LumenisTheme.of(context).quiet,
            fontSize: 12,
            height: 1.45,
          ),
        ),
      ],
    );
  }
}

class _FactLine extends StatelessWidget {
  const _FactLine({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 7),
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
              softWrap: true,
              style: TextStyle(
                color: LumenisTheme.of(context).foreground,
                fontWeight: FontWeight.w600,
                fontFeatures: [FontFeature.tabularFigures()],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _DetailLine extends StatelessWidget {
  const _DetailLine({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 7),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 82,
            child: Text(
              label,
              style: TextStyle(
                color: LumenisTheme.of(context).quiet,
                fontSize: 12,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: TextStyle(
                color: LumenisTheme.of(context).muted,
                fontSize: 13,
                height: 1.45,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _ThinRule extends StatelessWidget {
  const _ThinRule();

  @override
  Widget build(BuildContext context) => Padding(
    padding: EdgeInsets.symmetric(vertical: 12),
    child: SizedBox(
      height: 1,
      child: ColoredBox(color: LumenisTheme.of(context).line),
    ),
  );
}

class _VerticalRule extends StatelessWidget {
  const _VerticalRule();

  @override
  Widget build(BuildContext context) => Padding(
    padding: EdgeInsets.symmetric(horizontal: 15),
    child: SizedBox(
      height: 76,
      width: 1,
      child: ColoredBox(color: LumenisTheme.of(context).line),
    ),
  );
}

class _CthTextButton extends StatefulWidget {
  const _CthTextButton({required this.label, required this.onPressed});

  final String label;
  final VoidCallback onPressed;

  @override
  State<_CthTextButton> createState() => _CthTextButtonState();
}

class _CthTextButtonState extends State<_CthTextButton> {
  bool _showFocus = false;

  @override
  Widget build(BuildContext context) {
    return FocusableActionDetector(
      mouseCursor: SystemMouseCursors.click,
      onShowFocusHighlight: (value) => setState(() => _showFocus = value),
      shortcuts: const <ShortcutActivator, Intent>{
        SingleActivator(LogicalKeyboardKey.enter): ActivateIntent(),
        SingleActivator(LogicalKeyboardKey.space): ActivateIntent(),
      },
      actions: <Type, Action<Intent>>{
        ActivateIntent: CallbackAction<ActivateIntent>(
          onInvoke: (intent) {
            widget.onPressed();
            return null;
          },
        ),
      },
      child: Semantics(
        button: true,
        label: widget.label,
        onTap: widget.onPressed,
        child: GestureDetector(
          behavior: HitTestBehavior.opaque,
          onTap: widget.onPressed,
          child: Container(
            constraints: const BoxConstraints(minHeight: 48, minWidth: 48),
            alignment: Alignment.center,
            padding: const EdgeInsets.symmetric(horizontal: 15, vertical: 11),
            decoration: BoxDecoration(
              color: LumenisTheme.of(context).surfaceRaised,
              border: Border.all(
                color: _showFocus
                    ? LumenisTheme.of(context).cth
                    : LumenisTheme.of(context).line,
              ),
              borderRadius: BorderRadius.circular(9),
            ),
            child: Text(
              widget.label,
              style: TextStyle(
                color: LumenisTheme.of(context).foreground,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ),
      ),
    );
  }
}

String _metricAvailabilityLabel(
  BuildContext context,
  Cth01BackendState state,
) => context.lumenisL10n.text(switch (state) {
  Cth01BackendState.ready ||
  Cth01BackendState.offline ||
  Cth01BackendState.error => 'cth01.metric.state.unavailable',
  Cth01BackendState.empty => 'cth01.metric.state.empty',
  Cth01BackendState.notCollected => 'cth01.metric.state.not_collected',
  Cth01BackendState.unknown => 'cth01.metric.state.unconfirmed',
  Cth01BackendState.stale => 'cth01.metric.state.stale',
  Cth01BackendState.partial => 'cth01.metric.state.partial',
  Cth01BackendState.blocked => 'cth01.metric.state.blocked',
});

String _signalEmptyTitle(BuildContext context, Cth01BackendState state) {
  final suffix = switch (state) {
    Cth01BackendState.empty || Cth01BackendState.ready => 'empty',
    Cth01BackendState.notCollected => 'not_collected',
    Cth01BackendState.offline => 'offline',
    Cth01BackendState.stale => 'stale',
    Cth01BackendState.partial => 'partial',
    Cth01BackendState.blocked => 'blocked',
    Cth01BackendState.error || Cth01BackendState.unknown => 'error',
  };
  return context.lumenisL10n.text('cth01.activity.$suffix.title');
}

String _signalEmptyDetail(BuildContext context, Cth01BackendState state) {
  final suffix = switch (state) {
    Cth01BackendState.empty || Cth01BackendState.ready => 'empty',
    Cth01BackendState.notCollected => 'not_collected',
    Cth01BackendState.offline => 'offline',
    Cth01BackendState.stale => 'stale',
    Cth01BackendState.partial => 'partial',
    Cth01BackendState.blocked => 'blocked',
    Cth01BackendState.error || Cth01BackendState.unknown => 'error',
  };
  return context.lumenisL10n.text('cth01.activity.$suffix.detail');
}

String _severityLabel(BuildContext context, String level) {
  final key = switch (level.toLowerCase()) {
    'critical' => 'critical',
    'high' => 'high',
    'medium' || 'med' => 'medium',
    'low' => 'low',
    _ => 'unrated',
  };
  return context.lumenisL10n.text('cth01.severity.$key');
}

Color _severityColor(BuildContext context, String level) =>
    switch (level.toLowerCase()) {
      'critical' || 'high' => LumenisTheme.of(context).danger,
      'medium' || 'med' => LumenisTheme.of(context).caution,
      'low' => LumenisTheme.of(context).positive,
      _ => LumenisTheme.of(context).muted,
    };

String _formatNumber(num value) {
  if (value % 1 == 0) return value.toInt().toString();
  return value.toStringAsFixed(1);
}
