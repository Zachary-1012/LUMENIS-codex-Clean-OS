import 'package:flutter/material.dart';

import '../../../core/lumenis_icon.dart';

import '../../../core/lumenis_core_client.dart';
import '../../../core/lumenis_theme.dart';
import '../../../l10n/lumenis_localizations.dart';
import 'cth04_repository.dart';
import 'cth04_view_model.dart';

class Cth04Screen extends StatefulWidget {
  const Cth04Screen({required this.client, this.repository, super.key});

  final LumenisCoreClient client;
  final Cth04Repository? repository;

  @override
  State<Cth04Screen> createState() => _Cth04ScreenState();
}

class _Cth04ScreenState extends State<Cth04Screen> {
  late Cth04ViewModel _viewModel = _createViewModel()..refresh();

  Cth04ViewModel _createViewModel() => Cth04ViewModel(
    repository: widget.repository ?? CoreCth04Repository(client: widget.client),
  );

  @override
  void didUpdateWidget(covariant Cth04Screen oldWidget) {
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
          Cth04LoadPhase.loading => const _Cth04Loading(),
          Cth04LoadPhase.unavailable => _Cth04Unavailable(
            kind: _viewModel.failureKind ?? Cth04FailureKind.server,
            onRetry: _viewModel.refresh,
          ),
          Cth04LoadPhase.ready => _Cth04Workspace(
            data: _viewModel.data!,
            selectedEventIndex: _viewModel.selectedEventIndex,
            onSelectEvent: _viewModel.selectEvent,
            onReturn: _viewModel.returnToTimeline,
            onRetry: _viewModel.refresh,
          ),
        },
      ),
    ),
  );
}

class _Cth04Loading extends StatelessWidget {
  const _Cth04Loading();

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
            Text(copy.text('screen.CTH-04')),
          ],
        ),
      ),
    );
  }
}

class _Cth04Unavailable extends StatelessWidget {
  const _Cth04Unavailable({required this.kind, required this.onRetry});

  final Cth04FailureKind kind;
  final VoidCallback onRetry;

  String _detail(LumenisLocalizations copy) => switch (kind) {
    Cth04FailureKind.contextUnavailable => copy.text(
      'cth01.context_unavailable',
    ),
    Cth04FailureKind.pageNotBound || Cth04FailureKind.focusNotBound =>
      copy.text('context.screen_binding_unavailable'),
    Cth04FailureKind.authentication => copy.text('cth01.login_required'),
    Cth04FailureKind.permissionDenied => copy.text('cth01.access_unavailable'),
    Cth04FailureKind.offline => copy.text('cth01.connection_unavailable'),
    Cth04FailureKind.server => copy.text('cth01.generic_unavailable'),
  };

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    final binding =
        kind == Cth04FailureKind.pageNotBound ||
        kind == Cth04FailureKind.focusNotBound;
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

class _Cth04Workspace extends StatelessWidget {
  const _Cth04Workspace({
    required this.data,
    required this.selectedEventIndex,
    required this.onSelectEvent,
    required this.onReturn,
    required this.onRetry,
  });

  final Cth04ScreenData data;
  final int? selectedEventIndex;
  final ValueChanged<int> onSelectEvent;
  final VoidCallback onReturn;
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
      final constellation = _ConstellationPanel(graph: data.graph);
      final timeline = _TimelinePanel(
        events: data.events,
        state: data.eventsState,
        selectedEventIndex: selectedEventIndex,
        onSelectEvent: onSelectEvent,
      );
      final inspection = selectedEventIndex == null
          ? const SizedBox.shrink()
          : _EventInspection(
              event: data.events[selectedEventIndex!],
              onReturn: onReturn,
            );
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
                    key: const ValueKey('cth04/desktop-layout'),
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(flex: 5, child: constellation),
                      const SizedBox(width: 24),
                      Expanded(flex: 6, child: timeline),
                    ],
                  )
                else
                  Column(
                    key: const ValueKey('cth04/mobile-layout'),
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      timeline,
                      const SizedBox(height: 18),
                      constellation,
                    ],
                  ),
                if (selectedEventIndex != null) ...[
                  const SizedBox(height: 20),
                  inspection,
                ],
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

  final Cth04ScreenData data;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
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
              copy.text('screen.CTH-04'),
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 9),
            Semantics(
              label: _contextLabel(context, data.context),
              child: Text(
                _contextLabel(context, data.context),
                style: TextStyle(
                  color: LumenisTheme.of(context).foreground,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
            const SizedBox(height: 7),
            Text(
              data.generatedAt.isEmpty
                  ? copy.text('cth01.activity.heading')
                  : '${copy.text('cth01.activity.heading')} · ${data.generatedAt}',
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

class _ConstellationPanel extends StatelessWidget {
  const _ConstellationPanel({required this.graph});

  final Cth04Graph graph;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    return _Panel(
      key: const ValueKey('cth04/constellation'),
      title: copy.text('common.detail'),
      detail: copy.text('cth01.activity.detail'),
      child: graph.available
          ? Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '${copy.text('common.status')}: ${graph.nodes.length} · ${graph.edgeCount}',
                  style: TextStyle(color: LumenisTheme.of(context).muted),
                ),
                const SizedBox(height: 14),
                for (var index = 0; index < graph.nodes.length; index++)
                  _GraphNode(
                    label: graph.nodes[index],
                    isLast: index == graph.nodes.length - 1,
                  ),
              ],
            )
          : Semantics(
              liveRegion: true,
              label: copy.text('cth01.generic_unavailable'),
              child: Container(
                width: double.infinity,
                padding: const EdgeInsets.all(18),
                decoration: BoxDecoration(
                  color: LumenisTheme.of(context).surfaceRaised,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: LumenisTheme.of(context).line),
                ),
                child: Text(
                  copy.text('cth01.scope.partial'),
                  style: TextStyle(
                    color: LumenisTheme.of(context).muted,
                    height: 1.55,
                  ),
                ),
              ),
            ),
    );
  }
}

class _GraphNode extends StatelessWidget {
  const _GraphNode({required this.label, required this.isLast});

  final String label;
  final bool isLast;

  @override
  Widget build(BuildContext context) => Row(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      SizedBox(
        width: 28,
        child: Column(
          children: [
            LumenisIcon(Icons.circle, size: 12, color: LumenisTheme.of(context).cth),
            if (!isLast)
              Container(
                width: 1,
                height: 34,
                color: LumenisTheme.of(context).line,
              ),
          ],
        ),
      ),
      Expanded(
        child: Padding(
          padding: const EdgeInsets.only(top: 1, bottom: 13),
          child: Text(
            label,
            style: TextStyle(color: LumenisTheme.of(context).foreground),
          ),
        ),
      ),
    ],
  );
}

class _TimelinePanel extends StatelessWidget {
  const _TimelinePanel({
    required this.events,
    required this.state,
    required this.selectedEventIndex,
    required this.onSelectEvent,
  });

  final List<Cth04Event> events;
  final Cth04DataState state;
  final int? selectedEventIndex;
  final ValueChanged<int> onSelectEvent;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    return _Panel(
      key: const ValueKey('cth04/event-timeline'),
      title: copy.text('cth01.activity.heading'),
      detail: copy.text('cth01.activity.detail'),
      child: events.isEmpty
          ? _InlineState(text: _emptyCopy(copy, state))
          : Column(
              children: [
                for (var index = 0; index < events.length; index++)
                  _EventRow(
                    event: events[index],
                    selected: index == selectedEventIndex,
                    onTap: () => onSelectEvent(index),
                  ),
              ],
            ),
    );
  }

  String _emptyCopy(LumenisLocalizations copy, Cth04DataState state) {
    return switch (state) {
      Cth04DataState.empty => copy.text('state.empty_true'),
      Cth04DataState.notCollected => copy.text('state.empty_notcollected'),
      Cth04DataState.offline => copy.text('state.offline'),
      Cth04DataState.stale => copy.text('state.stale'),
      Cth04DataState.blocked => copy.text('state.blocked'),
      Cth04DataState.partial => copy.text('state.partial'),
      Cth04DataState.error => copy.text('state.error'),
      _ => copy.text('common.empty'),
    };
  }
}

class _EventRow extends StatelessWidget {
  const _EventRow({
    required this.event,
    required this.selected,
    required this.onTap,
  });

  final Cth04Event event;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    return Semantics(
      button: true,
      selected: selected,
      label: '${event.title}, ${event.date} ${event.time}, ${event.level}',
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Container(
          width: double.infinity,
          margin: const EdgeInsets.only(bottom: 10),
          padding: const EdgeInsets.all(15),
          decoration: BoxDecoration(
            color: selected
                ? LumenisTheme.of(context).cth.withValues(alpha: 0.11)
                : LumenisTheme.of(context).surfaceRaised,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: selected
                  ? LumenisTheme.of(context).cth
                  : LumenisTheme.of(context).line,
            ),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Padding(
                padding: EdgeInsets.only(top: 4),
                child: LumenisIcon(
                  Icons.radio_button_checked_rounded,
                  size: 15,
                  color: LumenisTheme.of(context).cth,
                ),
              ),
              const SizedBox(width: 11),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      event.title,
                      style: TextStyle(
                        color: LumenisTheme.of(context).foreground,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 5),
                    Text(
                      '${event.date} ${event.time}'.trim(),
                      style: TextStyle(
                        color: LumenisTheme.of(context).muted,
                        fontSize: 12,
                      ),
                    ),
                    if (event.description.isNotEmpty) ...[
                      const SizedBox(height: 7),
                      Text(
                        event.description,
                        style: TextStyle(
                          color: LumenisTheme.of(context).muted,
                          height: 1.45,
                        ),
                      ),
                    ],
                    if (event.tags.isNotEmpty) ...[
                      const SizedBox(height: 8),
                      Wrap(
                        spacing: 7,
                        runSpacing: 5,
                        children: event.tags
                            .map((tag) => _Tag(tag))
                            .toList(growable: false),
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(width: 10),
              Text(
                event.level.isEmpty
                    ? copy.text('cth01.severity.unrated')
                    : event.level,
                style: TextStyle(
                  color: LumenisTheme.of(context).caution,
                  fontSize: 12,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _EventInspection extends StatelessWidget {
  const _EventInspection({required this.event, required this.onReturn});

  final Cth04Event event;
  final VoidCallback onReturn;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    return Container(
      key: const ValueKey('cth04/event-inspection'),
      decoration: BoxDecoration(
        color: LumenisTheme.of(context).surface,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(
          color: LumenisTheme.of(context).cth.withValues(alpha: 0.5),
        ),
      ),
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            copy.text('common.detail'),
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 11),
          Text(
            event.title,
            style: TextStyle(
              color: LumenisTheme.of(context).foreground,
              fontWeight: FontWeight.w600,
              fontSize: 17,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            event.description.isEmpty
                ? copy.text('cth01.field.not_provided')
                : event.description,
            style: TextStyle(
              color: LumenisTheme.of(context).muted,
              height: 1.5,
            ),
          ),
          const SizedBox(height: 14),
          Wrap(
            spacing: 14,
            runSpacing: 6,
            children: [
              if (event.date.isNotEmpty)
                Text(
                  event.date,
                  style: TextStyle(color: LumenisTheme.of(context).quiet),
                ),
              if (event.time.isNotEmpty)
                Text(
                  event.time,
                  style: TextStyle(color: LumenisTheme.of(context).quiet),
                ),
              if (event.level.isNotEmpty)
                Text(
                  event.level,
                  style: TextStyle(color: LumenisTheme.of(context).caution),
                ),
            ],
          ),
          const SizedBox(height: 16),
          TextButton.icon(
            onPressed: onReturn,
            icon: const LumenisIcon(Icons.arrow_back_rounded),
            label: Text(copy.text('common.back')),
          ),
        ],
      ),
    );
  }
}

class _Tag extends StatelessWidget {
  const _Tag(this.text);

  final String text;

  @override
  Widget build(BuildContext context) => DecoratedBox(
    decoration: BoxDecoration(
      color: LumenisTheme.of(context).surface,
      borderRadius: BorderRadius.circular(99),
      border: Border.all(color: LumenisTheme.of(context).line),
    ),
    child: Padding(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      child: Text(
        text,
        style: TextStyle(color: LumenisTheme.of(context).quiet, fontSize: 11),
      ),
    ),
  );
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

String _contextLabel(BuildContext context, Cth04Context value) {
  final copy = context.lumenisL10n;
  if (value.isGlobal) return copy.text('context.mode.global_all');
  final locale = Localizations.localeOf(context);
  return value.displayName?[locale.toLanguageTag()] ??
      value.displayName?[locale.languageCode] ??
      value.displayName?['zh-CN'] ??
      copy.text('context.mode.focus');
}
