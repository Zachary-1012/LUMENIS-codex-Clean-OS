import 'package:flutter/material.dart';

import '../../../core/lumenis_core_client.dart';
import '../../../core/lumenis_theme.dart';
import '../../../l10n/lumenis_localizations.dart';
import 'cth05_repository.dart';
import 'cth05_view_model.dart';

class Cth05Screen extends StatefulWidget {
  const Cth05Screen({required this.client, this.repository, super.key});

  final LumenisCoreClient client;
  final Cth05Repository? repository;

  @override
  State<Cth05Screen> createState() => _Cth05ScreenState();
}

class _Cth05ScreenState extends State<Cth05Screen> {
  late Cth05ViewModel _viewModel = _createViewModel()..refresh();

  Cth05ViewModel _createViewModel() => Cth05ViewModel(
    repository: widget.repository ?? CoreCth05Repository(client: widget.client),
  );

  @override
  void didUpdateWidget(covariant Cth05Screen oldWidget) {
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
          Cth05LoadPhase.loading => const _Cth05Loading(),
          Cth05LoadPhase.unavailable => _Cth05Unavailable(
            kind: _viewModel.failureKind ?? Cth05FailureKind.server,
            onRetry: _viewModel.refresh,
          ),
          Cth05LoadPhase.ready => _Cth05Workspace(
            data: _viewModel.data!,
            listMode: _viewModel.listMode,
            selectedDayIndex: _viewModel.selectedDayIndex,
            onToggleList: _viewModel.toggleListMode,
            onSelectDay: _viewModel.selectDay,
            onRetry: _viewModel.refresh,
          ),
        },
      ),
    ),
  );
}

class _Cth05Loading extends StatelessWidget {
  const _Cth05Loading();

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
            Text(copy.text('screen.CTH-05')),
          ],
        ),
      ),
    );
  }
}

class _Cth05Unavailable extends StatelessWidget {
  const _Cth05Unavailable({required this.kind, required this.onRetry});

  final Cth05FailureKind kind;
  final VoidCallback onRetry;

  String _detail(LumenisLocalizations copy) => switch (kind) {
    Cth05FailureKind.contextUnavailable => copy.text(
      'cth01.context_unavailable',
    ),
    Cth05FailureKind.pageNotBound || Cth05FailureKind.focusNotBound =>
      copy.text('context.screen_binding_unavailable'),
    Cth05FailureKind.authentication => copy.text('cth01.login_required'),
    Cth05FailureKind.permissionDenied => copy.text('cth01.access_unavailable'),
    Cth05FailureKind.offline => copy.text('cth01.connection_unavailable'),
    Cth05FailureKind.server => copy.text('cth01.generic_unavailable'),
  };

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    final binding =
        kind == Cth05FailureKind.pageNotBound ||
        kind == Cth05FailureKind.focusNotBound;
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

class _Cth05Workspace extends StatelessWidget {
  const _Cth05Workspace({
    required this.data,
    required this.listMode,
    required this.selectedDayIndex,
    required this.onToggleList,
    required this.onSelectDay,
    required this.onRetry,
  });

  final Cth05ScreenData data;
  final bool listMode;
  final int? selectedDayIndex;
  final VoidCallback onToggleList;
  final ValueChanged<int> onSelectDay;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, constraints) {
      final wide = constraints.maxWidth >= 1120;
      final padding = constraints.maxWidth < 480
          ? 18.0
          : constraints.maxWidth < 900
          ? 28.0
          : 40.0;
      final calendar = _CalendarPanel(
        data: data,
        listMode: listMode,
        selectedDayIndex: selectedDayIndex,
        onToggleList: onToggleList,
        onSelectDay: onSelectDay,
      );
      final detail = _DayDetail(data: data, selectedDayIndex: selectedDayIndex);
      return Align(
        alignment: Alignment.topCenter,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1680),
          child: SingleChildScrollView(
            padding: EdgeInsets.fromLTRB(padding, 28, padding, 48),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _Header(data: data, onRetry: onRetry),
                const SizedBox(height: 24),
                if (wide)
                  Row(
                    key: const ValueKey('cth05/desktop-layout'),
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(flex: 7, child: calendar),
                      const SizedBox(width: 24),
                      Expanded(flex: 4, child: detail),
                    ],
                  )
                else
                  Column(
                    key: const ValueKey('cth05/mobile-layout'),
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [calendar, const SizedBox(height: 18), detail],
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

  final Cth05ScreenData data;
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
              copy.text('screen.CTH-05'),
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

class _CalendarPanel extends StatelessWidget {
  const _CalendarPanel({
    required this.data,
    required this.listMode,
    required this.selectedDayIndex,
    required this.onToggleList,
    required this.onSelectDay,
  });

  final Cth05ScreenData data;
  final bool listMode;
  final int? selectedDayIndex;
  final VoidCallback onToggleList;
  final ValueChanged<int> onSelectDay;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    return _Panel(
      key: const ValueKey('cth05/calendar-panel'),
      title: copy.text('screen.CTH-05'),
      detail: copy.text('cth01.metrics.detail'),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _ViewSwitch(listMode: listMode, onToggle: onToggleList),
          const SizedBox(height: 16),
          if (!data.calendarAvailable)
            _CalendarUnavailable(state: data.state, definition: data.definition)
          else if (listMode)
            _DayList(
              days: data.days,
              selectedDayIndex: selectedDayIndex,
              onSelectDay: onSelectDay,
            )
          else
            _DayGrid(
              days: data.days,
              selectedDayIndex: selectedDayIndex,
              onSelectDay: onSelectDay,
            ),
          if (data.calendarAvailable) ...[
            const SizedBox(height: 16),
            const _Legend(),
          ],
        ],
      ),
    );
  }
}

class _ViewSwitch extends StatelessWidget {
  const _ViewSwitch({required this.listMode, required this.onToggle});

  final bool listMode;
  final VoidCallback onToggle;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    return SegmentedButton<bool>(
      segments: [
        ButtonSegment(
          value: false,
          label: Text(copy.text('common.all')),
          icon: const Icon(Icons.calendar_month_rounded),
        ),
        ButtonSegment(
          value: true,
          label: Text(copy.text('common.view_all')),
          icon: const Icon(Icons.view_list_rounded),
        ),
      ],
      selected: {listMode},
      onSelectionChanged: (_) => onToggle(),
    );
  }
}

class _CalendarUnavailable extends StatelessWidget {
  const _CalendarUnavailable({required this.state, required this.definition});

  final Cth05DataState state;
  final Cth05TrendDefinition? definition;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    final text = switch (state) {
      Cth05DataState.empty => copy.text('state.empty_true'),
      Cth05DataState.notCollected => copy.text('state.empty_notcollected'),
      Cth05DataState.offline => copy.text('state.offline'),
      Cth05DataState.stale => copy.text('state.stale'),
      Cth05DataState.blocked => copy.text('state.blocked'),
      Cth05DataState.partial => copy.text('state.partial'),
      Cth05DataState.error => copy.text('state.error'),
      _ => copy.text('common.empty'),
    };
    return Semantics(
      liveRegion: true,
      label: text,
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(
          color: LumenisTheme.of(context).surfaceRaised,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: LumenisTheme.of(context).line),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              text,
              style: TextStyle(
                color: LumenisTheme.of(context).muted,
                height: 1.55,
              ),
            ),
            if (definition != null && !definition!.isComplete) ...[
              const SizedBox(height: 10),
              Text(
                copy.text('cth01.scope.partial'),
                style: TextStyle(color: LumenisTheme.of(context).quiet),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _DayGrid extends StatelessWidget {
  const _DayGrid({
    required this.days,
    required this.selectedDayIndex,
    required this.onSelectDay,
  });

  final List<Cth05CalendarDay> days;
  final int? selectedDayIndex;
  final ValueChanged<int> onSelectDay;

  @override
  Widget build(BuildContext context) {
    final maxValue = days.fold<num>(
      0,
      (current, day) => current > day.negative ? current : day.negative,
    );
    return LayoutBuilder(
      builder: (context, constraints) => GridView.builder(
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        itemCount: days.length,
        gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
          crossAxisCount: 7,
          crossAxisSpacing: 7,
          mainAxisSpacing: 7,
          childAspectRatio: 0.84,
        ),
        itemBuilder: (context, index) => _DayCell(
          day: days[index],
          selected: index == selectedDayIndex,
          maxValue: maxValue,
          onTap: () => onSelectDay(index),
        ),
      ),
    );
  }
}

class _DayCell extends StatelessWidget {
  const _DayCell({
    required this.day,
    required this.selected,
    required this.maxValue,
    required this.onTap,
  });

  final Cth05CalendarDay day;
  final bool selected;
  final num maxValue;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    final ratio = maxValue == 0
        ? 0.0
        : (day.negative / maxValue).clamp(0, 1).toDouble();
    return Semantics(
      button: true,
      selected: selected,
      label:
          '${day.label}, ${copy.text('cth01.metric.negative_voice')} ${day.negative}, ${copy.text('cth01.severity.high')} ${day.highRisk}',
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(10),
        child: Container(
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: Color.lerp(
              LumenisTheme.of(context).surfaceRaised,
              LumenisTheme.of(context).danger.withValues(alpha: 0.7),
              ratio,
            ),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(
              color: selected
                  ? LumenisTheme.of(context).cth
                  : LumenisTheme.of(context).line,
              width: selected ? 2 : 1,
            ),
          ),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                day.label,
                style: TextStyle(
                  color: LumenisTheme.of(context).foreground,
                  fontSize: 10,
                  fontWeight: FontWeight.w600,
                ),
                maxLines: 1,
                overflow: TextOverflow.clip,
                softWrap: false,
              ),
              const SizedBox(height: 1),
              Text(
                '${day.negative}',
                style: TextStyle(
                  color: LumenisTheme.of(context).muted,
                  fontSize: 10,
                ),
                maxLines: 1,
                overflow: TextOverflow.clip,
                softWrap: false,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _DayList extends StatelessWidget {
  const _DayList({
    required this.days,
    required this.selectedDayIndex,
    required this.onSelectDay,
  });

  final List<Cth05CalendarDay> days;
  final int? selectedDayIndex;
  final ValueChanged<int> onSelectDay;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    return Column(
      children: [
        for (var index = 0; index < days.length; index++)
          Material(
            color: Colors.transparent,
            child: ListTile(
              selected: selectedDayIndex == index,
              onTap: () => onSelectDay(index),
              contentPadding: EdgeInsets.zero,
              title: Text(days[index].label),
              subtitle: Text(
                '${copy.text('cth01.metric.negative_voice')} ${days[index].negative} · ${copy.text('cth01.severity.high')} ${days[index].highRisk}',
              ),
              trailing: const Icon(Icons.chevron_right_rounded),
            ),
          ),
      ],
    );
  }
}

class _Legend extends StatelessWidget {
  const _Legend();

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    return Wrap(
      spacing: 14,
      runSpacing: 7,
      children: [
        _LegendItem(
          color: LumenisTheme.of(context).danger,
          label: copy.text('cth01.metric.negative_voice'),
        ),
        _LegendItem(
          color: LumenisTheme.of(context).caution,
          label: copy.text('cth01.severity.high'),
        ),
        _LegendItem(
          color: LumenisTheme.of(context).cth,
          label: copy.text('common.time'),
        ),
      ],
    );
  }
}

class _LegendItem extends StatelessWidget {
  const _LegendItem({required this.color, required this.label});

  final Color color;
  final String label;

  @override
  Widget build(BuildContext context) => Row(
    mainAxisSize: MainAxisSize.min,
    children: [
      Container(
        width: 10,
        height: 10,
        decoration: BoxDecoration(color: color, shape: BoxShape.circle),
      ),
      const SizedBox(width: 6),
      Text(
        label,
        style: TextStyle(color: LumenisTheme.of(context).muted, fontSize: 12),
      ),
    ],
  );
}

class _DayDetail extends StatelessWidget {
  const _DayDetail({required this.data, required this.selectedDayIndex});

  final Cth05ScreenData data;
  final int? selectedDayIndex;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    final day =
        selectedDayIndex == null || selectedDayIndex! >= data.days.length
        ? null
        : data.days[selectedDayIndex!];
    return _Panel(
      key: const ValueKey('cth05/day-detail'),
      title: copy.text('common.detail'),
      detail: copy.text('cth01.activity.detail'),
      child: day == null
          ? _InlineState(text: copy.text('state.empty_filter'))
          : Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  day.label,
                  style: TextStyle(
                    color: LumenisTheme.of(context).foreground,
                    fontSize: 18,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 14),
                Text(
                  '${copy.text('cth01.metric.negative_voice')} ${day.negative}',
                  style: TextStyle(color: LumenisTheme.of(context).danger),
                ),
                const SizedBox(height: 8),
                Text(
                  '${copy.text('cth01.severity.high')} ${day.highRisk}',
                  style: TextStyle(color: LumenisTheme.of(context).caution),
                ),
                const SizedBox(height: 16),
                Text(
                  copy.text('cth01.source.unavailable'),
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

String _contextLabel(BuildContext context, Cth05Context value) {
  final copy = context.lumenisL10n;
  if (value.isGlobal) return copy.text('context.mode.global_all');
  final locale = Localizations.localeOf(context);
  return value.displayName?[locale.toLanguageTag()] ??
      value.displayName?[locale.languageCode] ??
      value.displayName?['zh-CN'] ??
      copy.text('context.mode.focus');
}
