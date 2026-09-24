import 'package:flutter/material.dart';

import '../../../core/lumenis_core_client.dart';
import '../../../core/lumenis_theme.dart';
import '../../../l10n/lumenis_localizations.dart';
import 'cth03_repository.dart';
import 'cth03_view_model.dart';

class Cth03Screen extends StatefulWidget {
  const Cth03Screen({required this.client, this.repository, super.key});

  final LumenisCoreClient client;
  final Cth03Repository? repository;

  @override
  State<Cth03Screen> createState() => _Cth03ScreenState();
}

class _Cth03ScreenState extends State<Cth03Screen> {
  late Cth03ViewModel _viewModel = _createViewModel()..refresh();

  Cth03ViewModel _createViewModel() => Cth03ViewModel(
    repository: widget.repository ?? CoreCth03Repository(client: widget.client),
  );

  @override
  void didUpdateWidget(covariant Cth03Screen oldWidget) {
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
            Cth03LoadPhase.loading => const _Cth03Loading(),
            Cth03LoadPhase.unavailable => _Cth03Unavailable(
              kind: _viewModel.failureKind ?? Cth03FailureKind.server,
              onRetry: _viewModel.refresh,
            ),
            Cth03LoadPhase.ready => _Cth03Workspace(
              data: _viewModel.data!,
              selectedChannel: _viewModel.selectedChannel,
              visibleRecords: _viewModel.visibleRecords(),
              onChannelChanged: _viewModel.chooseChannel,
              onRetry: _viewModel.refresh,
            ),
          },
        ),
      ),
    );
  }
}

class _Cth03Loading extends StatelessWidget {
  const _Cth03Loading();

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    return Semantics(
      liveRegion: true,
      label: copy.text('state.loading_d'),
      child: Align(
        alignment: Alignment.topCenter,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 760),
          child: Padding(
            padding: const EdgeInsets.all(32),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  copy.text('screen.CTH-03'),
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
                const SizedBox(height: 22),
                const LinearProgressIndicator(minHeight: 3),
                const SizedBox(height: 18),
                Text(
                  copy.text('state.loading_d'),
                  style: TextStyle(color: LumenisTheme.of(context).muted),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _Cth03Unavailable extends StatelessWidget {
  const _Cth03Unavailable({required this.kind, required this.onRetry});

  final Cth03FailureKind kind;
  final VoidCallback onRetry;

  String _detail(LumenisLocalizations copy) => switch (kind) {
    Cth03FailureKind.contextUnavailable => copy.text(
      'cth01.context_unavailable',
    ),
    Cth03FailureKind.focusNotBound || Cth03FailureKind.pageNotBound =>
      copy.text('context.screen_binding_unavailable'),
    Cth03FailureKind.authentication => copy.text('cth01.login_required'),
    Cth03FailureKind.permissionDenied => copy.text('cth01.access_unavailable'),
    Cth03FailureKind.offline => copy.text('cth01.connection_unavailable'),
    Cth03FailureKind.server => copy.text('cth01.generic_unavailable'),
  };

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    final bindingFailure =
        kind == Cth03FailureKind.focusNotBound ||
        kind == Cth03FailureKind.pageNotBound;
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
                  bindingFailure
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

class _Cth03Workspace extends StatelessWidget {
  const _Cth03Workspace({
    required this.data,
    required this.selectedChannel,
    required this.visibleRecords,
    required this.onChannelChanged,
    required this.onRetry,
  });

  final Cth03ScreenData data;
  final String? selectedChannel;
  final List<Cth03Record> visibleRecords;
  final ValueChanged<String?> onChannelChanged;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final wide = constraints.maxWidth >= 1120;
        final padding = constraints.maxWidth < 480
            ? 18.0
            : constraints.maxWidth < 900
            ? 28.0
            : 40.0;
        final stream = _StreamPanel(
          state: data.recordState,
          records: visibleRecords,
          selectedChannel: selectedChannel,
        );
        final channels = _ChannelPanel(
          channels: data.channels,
          selectedChannel: selectedChannel,
          onChannelChanged: onChannelChanged,
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
                  const SizedBox(height: 20),
                  _PulseBand(data: data),
                  const SizedBox(height: 24),
                  if (wide)
                    Row(
                      key: const ValueKey('cth03/desktop-layout'),
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Expanded(flex: 7, child: stream),
                        const SizedBox(width: 24),
                        Expanded(flex: 4, child: channels),
                      ],
                    )
                  else
                    Column(
                      key: const ValueKey('cth03/mobile-layout'),
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [channels, const SizedBox(height: 18), stream],
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

class _Header extends StatelessWidget {
  const _Header({required this.data, required this.onRetry});

  final Cth03ScreenData data;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    final contextLabel = _contextLabel(context, data.context);
    return Wrap(
      alignment: WrapAlignment.spaceBetween,
      crossAxisAlignment: WrapCrossAlignment.center,
      runSpacing: 16,
      spacing: 20,
      children: [
        ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 820),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                copy.text('screen.CTH-03'),
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
                copy.text('cth01.scope.complete'),
                style: TextStyle(
                  color: LumenisTheme.of(context).muted,
                  height: 1.5,
                ),
              ),
            ],
          ),
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

class _PulseBand extends StatelessWidget {
  const _PulseBand({required this.data});

  final Cth03ScreenData data;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    return Container(
      key: const ValueKey('cth03/pulse-band'),
      decoration: BoxDecoration(
        color: LumenisTheme.of(context).surface,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: LumenisTheme.of(context).line),
      ),
      padding: const EdgeInsets.all(18),
      child: Wrap(
        spacing: 28,
        runSpacing: 18,
        crossAxisAlignment: WrapCrossAlignment.center,
        children: [
          _PulseValue(
            label: copy.text('cth01.activity.heading'),
            metric: data.recentCount,
            accent: LumenisTheme.of(context).cth,
          ),
          _PulseValue(
            label: copy.text('cth01.metric.negative_voice'),
            metric: data.negativeCount,
            accent: LumenisTheme.of(context).danger,
          ),
          _Freshness(
            text: data.generatedAt.isEmpty
                ? copy.text('freshness.stale')
                : '${copy.text('common.time')} ${data.generatedAt}',
          ),
        ],
      ),
    );
  }
}

class _PulseValue extends StatelessWidget {
  const _PulseValue({
    required this.label,
    required this.metric,
    required this.accent,
  });

  final String label;
  final Cth03Metric metric;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    final value = metric.hasValue ? '${metric.value}' : '—';
    final copy = context.lumenisL10n;
    final detail = metric.state == Cth03DataState.notCollected
        ? copy.text('cth01.metric.state.not_collected')
        : metric.state == Cth03DataState.empty
        ? copy.text('cth01.metric.state.empty')
        : metric.hasValue
        ? copy.text('cth01.metric.state.unconfirmed')
        : copy.text('cth01.metric.state.unavailable');
    return Semantics(
      container: true,
      label: '$label $value，$detail',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: TextStyle(color: LumenisTheme.of(context).muted)),
          const SizedBox(height: 5),
          Text(
            value,
            style: TextStyle(
              color: accent,
              fontSize: 26,
              fontWeight: FontWeight.w700,
              fontFeatures: const [FontFeature.tabularFigures()],
            ),
          ),
          Text(
            detail,
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

class _Freshness extends StatelessWidget {
  const _Freshness({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) => Semantics(
    liveRegion: true,
    label: text,
    child: LayoutBuilder(
      builder: (context, constraints) {
        final width = constraints.hasBoundedWidth
            ? constraints.maxWidth
            : 420.0;
        return SizedBox(
          width: width,
          child: Row(
            children: [
              Icon(
                Icons.schedule_rounded,
                size: 17,
                color: LumenisTheme.of(context).muted,
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  text,
                  softWrap: true,
                  style: TextStyle(color: LumenisTheme.of(context).muted),
                ),
              ),
            ],
          ),
        );
      },
    ),
  );
}

class _ChannelPanel extends StatelessWidget {
  const _ChannelPanel({
    required this.channels,
    required this.selectedChannel,
    required this.onChannelChanged,
  });

  final List<Cth03Channel> channels;
  final String? selectedChannel;
  final ValueChanged<String?> onChannelChanged;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    return _Panel(
      key: const ValueKey('cth03/channel-lanes'),
      title: copy.text('common.status'),
      detail: copy.text('cth01.metrics.detail'),
      child: channels.isEmpty
          ? _InlineState(text: copy.text('cth01.metric.state.unavailable'))
          : Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: channels
                  .map(
                    (channel) => Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: Semantics(
                        container: true,
                        label: '${channel.name}，${channel.status}',
                        child: InkWell(
                          onTap: () => onChannelChanged(
                            selectedChannel == channel.name
                                ? null
                                : channel.name,
                          ),
                          borderRadius: BorderRadius.circular(12),
                          child: Container(
                            width: double.infinity,
                            padding: const EdgeInsets.all(14),
                            decoration: BoxDecoration(
                              color: selectedChannel == channel.name
                                  ? LumenisTheme.of(
                                      context,
                                    ).cth.withValues(alpha: 0.10)
                                  : LumenisTheme.of(context).surfaceRaised,
                              borderRadius: BorderRadius.circular(12),
                              border: Border.all(
                                color: selectedChannel == channel.name
                                    ? LumenisTheme.of(
                                        context,
                                      ).cth.withValues(alpha: 0.55)
                                    : LumenisTheme.of(context).line,
                              ),
                            ),
                            child: Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Icon(
                                  Icons.radio_button_checked_rounded,
                                  size: 17,
                                  color: LumenisTheme.of(context).cth,
                                ),
                                const SizedBox(width: 10),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        channel.name,
                                        style: TextStyle(
                                          color: LumenisTheme.of(
                                            context,
                                          ).foreground,
                                          fontWeight: FontWeight.w600,
                                        ),
                                      ),
                                      const SizedBox(height: 4),
                                      Text(
                                        channel.status.isEmpty
                                            ? copy.text(
                                                'cth01.metric.state.unavailable',
                                              )
                                            : channel.status,
                                        style: TextStyle(
                                          color: LumenisTheme.of(context).muted,
                                        ),
                                      ),
                                      if (channel.detail.isNotEmpty) ...[
                                        const SizedBox(height: 3),
                                        Text(
                                          channel.detail,
                                          style: TextStyle(
                                            color: LumenisTheme.of(
                                              context,
                                            ).quiet,
                                            fontSize: 12,
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
                    ),
                  )
                  .toList(growable: false),
            ),
    );
  }
}

class _StreamPanel extends StatelessWidget {
  const _StreamPanel({
    required this.state,
    required this.records,
    required this.selectedChannel,
  });

  final Cth03DataState state;
  final List<Cth03Record> records;
  final String? selectedChannel;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    final streamLabel = copy.text('cth01.activity.heading');
    final title = selectedChannel == null
        ? streamLabel
        : '$selectedChannel · $streamLabel';
    return _Panel(
      key: const ValueKey('cth03/record-stream'),
      title: title,
      detail: copy.text('cth01.activity.detail'),
      child: records.isEmpty
          ? _InlineState(text: _emptyCopy(context, state))
          : Column(
              children: records
                  .map((record) => _RecordRow(record: record))
                  .toList(growable: false),
            ),
    );
  }

  String _emptyCopy(BuildContext context, Cth03DataState state) {
    final copy = context.lumenisL10n;
    return switch (state) {
      Cth03DataState.empty => copy.text('state.empty_true'),
      Cth03DataState.notCollected => copy.text('state.empty_notcollected'),
      Cth03DataState.offline => copy.text('state.offline'),
      Cth03DataState.stale => copy.text('state.stale'),
      Cth03DataState.blocked => copy.text('state.blocked'),
      Cth03DataState.partial => copy.text('state.partial'),
      Cth03DataState.error => copy.text('state.error'),
      _ => copy.text('common.empty'),
    };
  }
}

class _RecordRow extends StatelessWidget {
  const _RecordRow({required this.record});

  final Cth03Record record;

  @override
  Widget build(BuildContext context) => Semantics(
    container: true,
    label: [
      record.title,
      if (record.date.isNotEmpty) record.date,
      if (record.channel.isNotEmpty) record.channel,
      if (record.sentiment.isNotEmpty) record.sentiment,
      if (record.risk.isNotEmpty) record.risk,
    ].join('，'),
    child: Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(vertical: 15),
      decoration: BoxDecoration(
        border: Border(
          bottom: BorderSide(color: LumenisTheme.of(context).line),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            record.title,
            style: TextStyle(
              color: LumenisTheme.of(context).foreground,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 7),
          Wrap(
            spacing: 12,
            runSpacing: 5,
            children: [
              if (record.date.isNotEmpty)
                _Meta(Icons.schedule_rounded, record.date),
              if (record.channel.isNotEmpty)
                _Meta(Icons.public_rounded, record.channel),
              if (record.sentiment.isNotEmpty)
                _Meta(Icons.mood_rounded, record.sentiment),
              if (record.risk.isNotEmpty)
                _Meta(Icons.warning_amber_rounded, record.risk),
            ],
          ),
        ],
      ),
    ),
  );
}

class _Meta extends StatelessWidget {
  const _Meta(this.icon, this.text);

  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) => Row(
    mainAxisSize: MainAxisSize.min,
    children: [
      Icon(icon, size: 14, color: LumenisTheme.of(context).quiet),
      const SizedBox(width: 5),
      Text(
        text,
        style: TextStyle(color: LumenisTheme.of(context).muted, fontSize: 12),
      ),
    ],
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

String _contextLabel(BuildContext context, Cth03Context value) {
  final copy = context.lumenisL10n;
  if (value.isGlobal) return copy.text('context.mode.global_all');
  final locale = Localizations.localeOf(context);
  return value.displayName?[locale.toLanguageTag()] ??
      value.displayName?[locale.languageCode] ??
      value.displayName?['zh-CN'] ??
      copy.text('context.mode.focus');
}
