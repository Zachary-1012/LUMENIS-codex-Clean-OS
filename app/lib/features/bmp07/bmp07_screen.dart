import 'package:flutter/material.dart';

import '../../core/lumenis_core_client.dart';
import '../../core/lumenis_theme.dart';
import '../../l10n/lumenis_localizations.dart';
import 'bmp07_repository.dart';
import 'bmp07_snapshot.dart';
import 'bmp07_view_model.dart';

class Bmp07Screen extends StatefulWidget {
  const Bmp07Screen({required this.client, this.repository, super.key});

  final LumenisCoreClient client;
  final Bmp07Repository? repository;

  @override
  State<Bmp07Screen> createState() => _Bmp07ScreenState();
}

class _Bmp07ScreenState extends State<Bmp07Screen> {
  late final Bmp07ViewModel _viewModel = Bmp07ViewModel(
    repository: widget.repository ?? CoreBmp07Repository(client: widget.client),
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
            Bmp07LoadPhase.loading => const _Loading(),
            Bmp07LoadPhase.failed => _Failure(
              kind: _viewModel.failureKind!,
              onRetry: _viewModel.refresh,
            ),
            Bmp07LoadPhase.ready => _CampaignWorkspace(
              snapshot: _viewModel.snapshot!,
              actionState: _viewModel.actionState,
              actionId: _viewModel.actionId,
              onRefresh: _viewModel.refresh,
              onAction: _viewModel.stageAction,
            ),
          },
        ),
      ),
    );
  }
}

class _CampaignWorkspace extends StatelessWidget {
  const _CampaignWorkspace({
    required this.snapshot,
    required this.actionState,
    required this.actionId,
    required this.onRefresh,
    required this.onAction,
  });

  final Bmp07Snapshot snapshot;
  final Bmp07ActionState actionState;
  final String? actionId;
  final VoidCallback onRefresh;
  final void Function(String actionId, String permission) onAction;

  @override
  Widget build(BuildContext context) {
    final copy = _Bmp07Copy.of(context);
    return LayoutBuilder(
      builder: (context, constraints) {
        final wide = constraints.maxWidth >= 1060;
        final padding = constraints.maxWidth >= 800 ? 32.0 : 18.0;
        final content = !snapshot.scopeApproved
            ? _CampaignGate(snapshot: snapshot, copy: copy)
            : snapshot.campaign == null
            ? _CampaignEmpty(copy: copy)
            : wide
            ? _DesktopRoom(campaign: snapshot.campaign!, copy: copy)
            : _MobileRoom(campaign: snapshot.campaign!, copy: copy);
        return Align(
          alignment: Alignment.topCenter,
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1320),
            child: SingleChildScrollView(
              padding: EdgeInsets.fromLTRB(padding, 28, padding, 40),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _Header(copy: copy, onRefresh: onRefresh),
                  const SizedBox(height: 26),
                  _RangeLine(
                    label: snapshot.scope.isGlobal
                        ? copy.globalRange
                        : copy.focusRange,
                    value:
                        snapshot.scope.localizedName(copy.languageCode) ??
                        (snapshot.scope.isGlobal
                            ? copy.allBrands
                            : copy.brandUnknown),
                  ),
                  const SizedBox(height: 18),
                  content,
                  const SizedBox(height: 24),
                  _ActionRail(
                    copy: copy,
                    state: actionState,
                    actionId: actionId,
                    onAction: onAction,
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

class _RangeLine extends StatelessWidget {
  const _RangeLine({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => DecoratedBox(
    decoration: BoxDecoration(
      border: Border(bottom: BorderSide(color: LumenisTheme.of(context).line)),
    ),
    child: Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        children: [
          Icon(Icons.public_rounded, color: LumenisTheme.of(context).bmp),
          const SizedBox(width: 10),
          Text(label, style: TextStyle(color: LumenisTheme.of(context).quiet)),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              value,
              style: TextStyle(
                color: LumenisTheme.of(context).foreground,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    ),
  );
}

class _Header extends StatelessWidget {
  const _Header({required this.copy, required this.onRefresh});

  final _Bmp07Copy copy;
  final VoidCallback onRefresh;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                context.lumenisL10n.text('screen.BMP-07'),
                style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                  color: LumenisTheme.of(context).foreground,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                copy.subtitle,
                style: TextStyle(
                  color: LumenisTheme.of(context).muted,
                  height: 1.5,
                ),
              ),
            ],
          ),
        ),
        IconButton(
          onPressed: onRefresh,
          tooltip: copy.refresh,
          icon: const Icon(Icons.refresh_rounded),
        ),
      ],
    );
  }
}

class _DesktopRoom extends StatelessWidget {
  const _DesktopRoom({required this.campaign, required this.copy});

  final Bmp07Campaign campaign;
  final _Bmp07Copy copy;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _ObjectiveStrip(campaign: campaign, copy: copy),
        const SizedBox(height: 18),
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              flex: 7,
              child: _MilestoneTimeline(
                milestones: campaign.milestones,
                stage: campaign.stage,
                copy: copy,
              ),
            ),
            const SizedBox(width: 18),
            Expanded(
              flex: 4,
              child: _ChannelMix(channels: campaign.channels, copy: copy),
            ),
          ],
        ),
        const SizedBox(height: 18),
        _OutcomeTrack(campaign: campaign, copy: copy),
      ],
    );
  }
}

class _MobileRoom extends StatelessWidget {
  const _MobileRoom({required this.campaign, required this.copy});

  final Bmp07Campaign campaign;
  final _Bmp07Copy copy;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _ObjectiveStrip(campaign: campaign, copy: copy),
        const SizedBox(height: 14),
        _MobileSteps(campaign: campaign, copy: copy),
        const SizedBox(height: 14),
        _OutcomeTrack(campaign: campaign, copy: copy),
        const SizedBox(height: 14),
        _ChannelMix(channels: campaign.channels, copy: copy),
      ],
    );
  }
}

class _ObjectiveStrip extends StatelessWidget {
  const _ObjectiveStrip({required this.campaign, required this.copy});

  final Bmp07Campaign campaign;
  final _Bmp07Copy copy;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: LumenisTheme.of(context).surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: LumenisTheme.of(context).line),
      ),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(22, 20, 22, 18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              copy.objective,
              style: TextStyle(
                color: LumenisTheme.of(context).quiet,
                fontSize: 11,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              campaign.goal ?? copy.goalUnavailable,
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 18),
            _StageSteps(current: campaign.stage, copy: copy),
          ],
        ),
      ),
    );
  }
}

class _StageSteps extends StatelessWidget {
  const _StageSteps({required this.current, required this.copy});

  final String current;
  final _Bmp07Copy copy;

  static const stages = <String>[
    'PLANNED',
    'BUDGETED',
    'LAUNCHED',
    'OBSERVED',
    'MEASURED',
  ];

  @override
  Widget build(BuildContext context) {
    final currentIndex = stages.indexOf(current);
    return Wrap(
      spacing: 0,
      runSpacing: 12,
      children: [
        for (var index = 0; index < stages.length; index++)
          SizedBox(
            width: 130,
            child: Row(
              children: [
                Semantics(
                  label: copy.stage(stages[index]),
                  child: Container(
                    width: 24,
                    height: 24,
                    alignment: Alignment.center,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: index <= currentIndex
                          ? LumenisTheme.of(context).bmp
                          : LumenisTheme.of(context).surfaceRaised,
                      border: Border.all(color: LumenisTheme.of(context).line),
                    ),
                    child: Text(
                      '${index + 1}',
                      style: TextStyle(
                        color: index <= currentIndex
                            ? LumenisTheme.of(context).canvas
                            : LumenisTheme.of(context).quiet,
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 7),
                Flexible(
                  child: Text(
                    copy.stage(stages[index]),
                    style: TextStyle(
                      color: index == currentIndex
                          ? LumenisTheme.of(context).foreground
                          : LumenisTheme.of(context).muted,
                      fontSize: 11,
                    ),
                  ),
                ),
              ],
            ),
          ),
      ],
    );
  }
}

class _MilestoneTimeline extends StatelessWidget {
  const _MilestoneTimeline({
    required this.milestones,
    required this.stage,
    required this.copy,
  });

  final List<Bmp07Milestone> milestones;
  final String stage;
  final _Bmp07Copy copy;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: LumenisTheme.of(context).surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: LumenisTheme.of(context).line),
      ),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(copy.timeline, style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 16),
            if (milestones.isEmpty)
              Text(
                copy.noMilestones,
                style: TextStyle(color: LumenisTheme.of(context).muted),
              )
            else
              for (var index = 0; index < milestones.length; index++)
                _MilestoneRow(
                  item: milestones[index],
                  isLast: index == milestones.length - 1,
                  copy: copy,
                ),
            const SizedBox(height: 12),
            Text(
              copy.stageNote(stage),
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
}

class _MobileSteps extends StatelessWidget {
  const _MobileSteps({required this.campaign, required this.copy});

  final Bmp07Campaign campaign;
  final _Bmp07Copy copy;

  @override
  Widget build(BuildContext context) {
    if (campaign.milestones.isEmpty) {
      return _MilestoneTimeline(
        milestones: const [],
        stage: campaign.stage,
        copy: copy,
      );
    }
    return DecoratedBox(
      decoration: BoxDecoration(
        color: LumenisTheme.of(context).surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: LumenisTheme.of(context).line),
      ),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(20, 18, 20, 10),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              copy.nextSteps,
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 12),
            for (var index = 0; index < campaign.milestones.length; index++)
              _MilestoneRow(
                item: campaign.milestones[index],
                isLast: index == campaign.milestones.length - 1,
                copy: copy,
              ),
          ],
        ),
      ),
    );
  }
}

class _MilestoneRow extends StatelessWidget {
  const _MilestoneRow({
    required this.item,
    required this.isLast,
    required this.copy,
  });

  final Bmp07Milestone item;
  final bool isLast;
  final _Bmp07Copy copy;

  @override
  Widget build(BuildContext context) {
    return IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          SizedBox(
            width: 24,
            child: Column(
              children: [
                Container(
                  width: 10,
                  height: 10,
                  margin: const EdgeInsets.only(top: 5),
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: LumenisTheme.of(context).bmp,
                  ),
                ),
                if (!isLast)
                  Expanded(
                    child: VerticalDivider(
                      color: LumenisTheme.of(context).line,
                      width: 1,
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.only(bottom: 16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    item.label,
                    style: TextStyle(
                      color: LumenisTheme.of(context).foreground,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    '${item.date} · ${copy.stage(item.stage)}',
                    style: TextStyle(
                      color: LumenisTheme.of(context).muted,
                      fontSize: 12,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _ChannelMix extends StatelessWidget {
  const _ChannelMix({required this.channels, required this.copy});

  final List<Bmp07Channel> channels;
  final _Bmp07Copy copy;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: LumenisTheme.of(context).surfaceRaised,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: LumenisTheme.of(context).line),
      ),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(copy.channels, style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 12),
            if (channels.isEmpty)
              Text(
                copy.noChannels,
                style: TextStyle(color: LumenisTheme.of(context).muted),
              )
            else
              for (final channel in channels)
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 7),
                  child: Row(
                    children: [
                      Icon(
                        channel.budgeted
                            ? Icons.check_circle_outline_rounded
                            : Icons.radio_button_unchecked_rounded,
                        size: 18,
                        color: channel.budgeted
                            ? LumenisTheme.of(context).bmp
                            : LumenisTheme.of(context).quiet,
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          channel.name,
                          style: TextStyle(
                            color: LumenisTheme.of(context).foreground,
                          ),
                        ),
                      ),
                      Text(
                        channel.budgeted ? copy.budgeted : copy.planned,
                        style: TextStyle(
                          color: LumenisTheme.of(context).muted,
                          fontSize: 11,
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

class _OutcomeTrack extends StatelessWidget {
  const _OutcomeTrack({required this.campaign, required this.copy});

  final Bmp07Campaign campaign;
  final _Bmp07Copy copy;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: LumenisTheme.of(context).surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: LumenisTheme.of(context).line),
      ),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: _OutcomeCell(
                label: copy.plannedOutcome,
                value: campaign.plannedRoi == null
                    ? copy.notSet
                    : '${campaign.plannedRoi}',
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: _OutcomeCell(
                label: copy.actualOutcome,
                value: campaign.actualRoi == null
                    ? copy.actualPending
                    : '${campaign.actualRoi}',
                accent: campaign.actualRoi != null,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _OutcomeCell extends StatelessWidget {
  const _OutcomeCell({
    required this.label,
    required this.value,
    this.accent = false,
  });

  final String label;
  final String value;
  final bool accent;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: TextStyle(color: LumenisTheme.of(context).muted)),
        const SizedBox(height: 8),
        Text(
          value,
          style: TextStyle(
            color: accent
                ? LumenisTheme.of(context).positive
                : LumenisTheme.of(context).foreground,
            fontSize: 20,
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }
}

class _CampaignGate extends StatelessWidget {
  const _CampaignGate({required this.snapshot, required this.copy});

  final Bmp07Snapshot snapshot;
  final _Bmp07Copy copy;

  @override
  Widget build(BuildContext context) {
    final notCollected = snapshot.dataState == 'NOT_COLLECTED';
    return _MessagePanel(
      icon: notCollected
          ? Icons.event_busy_outlined
          : Icons.lock_outline_rounded,
      title: notCollected ? copy.notCollectedTitle : copy.unavailableTitle,
      detail: notCollected ? copy.notCollectedDetail : copy.unavailableDetail,
      copy: copy,
    );
  }
}

class _CampaignEmpty extends StatelessWidget {
  const _CampaignEmpty({required this.copy});

  final _Bmp07Copy copy;

  @override
  Widget build(BuildContext context) => _MessagePanel(
    icon: Icons.event_note_outlined,
    title: copy.noCampaignTitle,
    detail: copy.noCampaignDetail,
    copy: copy,
  );
}

class _MessagePanel extends StatelessWidget {
  const _MessagePanel({
    required this.icon,
    required this.title,
    required this.detail,
    required this.copy,
  });

  final IconData icon;
  final String title;
  final String detail;
  final _Bmp07Copy copy;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: LumenisTheme.of(context).surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: LumenisTheme.of(context).line),
      ),
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, color: LumenisTheme.of(context).caution, size: 28),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 8),
                  Text(
                    detail,
                    style: TextStyle(
                      color: LumenisTheme.of(context).muted,
                      height: 1.55,
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

class _ActionRail extends StatelessWidget {
  const _ActionRail({
    required this.copy,
    required this.state,
    required this.actionId,
    required this.onAction,
  });

  final _Bmp07Copy copy;
  final Bmp07ActionState state;
  final String? actionId;
  final void Function(String actionId, String permission) onAction;

  @override
  Widget build(BuildContext context) {
    final notice = switch (state) {
      Bmp07ActionState.idle => null,
      Bmp07ActionState.blocked => copy.actionBlocked,
      Bmp07ActionState.staged => copy.actionStaged,
    };
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (notice != null) ...[
          Semantics(
            liveRegion: true,
            child: Text(
              notice,
              style: TextStyle(
                color: state == Bmp07ActionState.staged
                    ? LumenisTheme.of(context).positive
                    : LumenisTheme.of(context).caution,
              ),
            ),
          ),
          const SizedBox(height: 12),
        ],
        DecoratedBox(
          decoration: BoxDecoration(
            border: Border(
              top: BorderSide(color: LumenisTheme.of(context).line),
            ),
          ),
          child: Padding(
            padding: const EdgeInsets.only(top: 16),
            child: Wrap(
              spacing: 10,
              runSpacing: 10,
              children: [
                FilledButton.icon(
                  onPressed: () =>
                      onAction('BMP-07.add-content', 'campaign:write'),
                  icon: const Icon(Icons.add_to_photos_outlined),
                  label: Text(copy.addContent),
                ),
                OutlinedButton.icon(
                  onPressed: () =>
                      onAction('BMP-07.end-campaign', 'campaign:close'),
                  icon: const Icon(Icons.stop_circle_outlined),
                  label: Text(copy.endCampaign),
                ),
              ],
            ),
          ),
        ),
        if (actionId == 'BMP-07.end-campaign') ...[
          const SizedBox(height: 9),
          Text(
            copy.closeGuard,
            style: TextStyle(
              color: LumenisTheme.of(context).quiet,
              fontSize: 12,
            ),
          ),
        ],
      ],
    );
  }
}

class _Loading extends StatelessWidget {
  const _Loading();

  @override
  Widget build(BuildContext context) => Center(
    child: Semantics(
      liveRegion: true,
      label: _Bmp07Copy.of(context).loading,
      child: Padding(
        padding: EdgeInsets.all(48),
        child: CircularProgressIndicator(color: LumenisTheme.of(context).bmp),
      ),
    ),
  );
}

class _Failure extends StatelessWidget {
  const _Failure({required this.kind, required this.onRetry});

  final Bmp07FailureKind kind;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final copy = _Bmp07Copy.of(context);
    final title = switch (kind) {
      Bmp07FailureKind.authentication => copy.signIn,
      Bmp07FailureKind.permissionDenied => copy.accessDenied,
      Bmp07FailureKind.offline => copy.offline,
      Bmp07FailureKind.server => copy.unavailableTitle,
    };
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _MessagePanel(
              icon: Icons.cloud_off_outlined,
              title: title,
              detail: copy.retryDetail,
              copy: copy,
            ),
            const SizedBox(height: 14),
            OutlinedButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh_rounded),
              label: Text(copy.refresh),
            ),
          ],
        ),
      ),
    );
  }
}

class _Bmp07Copy {
  _Bmp07Copy(this.languageCode);

  final String languageCode;

  static _Bmp07Copy of(BuildContext context) {
    final languageCode = Localizations.localeOf(context).languageCode;
    return _Bmp07Copy(
      languageCode == 'en' || languageCode == 'ko' ? languageCode : 'zh-CN',
    );
  }

  String get subtitle => _get('subtitle');
  String get refresh => _get('refresh');
  String get focusRange => _get('focusRange');
  String get globalRange => _get('globalRange');
  String get allBrands => _get('allBrands');
  String get brandUnknown => _get('brandUnknown');
  String get objective => _get('objective');
  String get goalUnavailable => _get('goalUnavailable');
  String get timeline => _get('timeline');
  String get nextSteps => _get('nextSteps');
  String get noMilestones => _get('noMilestones');
  String get channels => _get('channels');
  String get noChannels => _get('noChannels');
  String get planned => _get('planned');
  String get budgeted => _get('budgeted');
  String get plannedOutcome => _get('plannedOutcome');
  String get actualOutcome => _get('actualOutcome');
  String get notSet => _get('notSet');
  String get actualPending => _get('actualPending');
  String get unavailableTitle => _get('unavailableTitle');
  String get unavailableDetail => _get('unavailableDetail');
  String get notCollectedTitle => _get('notCollectedTitle');
  String get notCollectedDetail => _get('notCollectedDetail');
  String get noCampaignTitle => _get('noCampaignTitle');
  String get noCampaignDetail => _get('noCampaignDetail');
  String get actionBlocked => _get('actionBlocked');
  String get actionStaged => _get('actionStaged');
  String get closeGuard => _get('closeGuard');
  String get loading => _get('loading');
  String get signIn => _get('signIn');
  String get accessDenied => _get('accessDenied');
  String get offline => _get('offline');
  String get retryDetail => _get('retryDetail');
  String get addContent => _get('addContent');
  String get endCampaign => _get('endCampaign');

  String stage(String value) => _get('stage.$value');
  String stageNote(String value) => _get('stageNote.$value');

  String _get(String key) =>
      _values[languageCode]?[key] ?? _values['zh-CN']![key]!;

  static const _values = <String, Map<String, String>>{
    'zh-CN': {
      'subtitle': '把目标、受众、渠道、里程碑与真实结果放在同一间活动控制室。',
      'refresh': '刷新活动状态',
      'focusRange': '当前品牌',
      'globalRange': '全球品牌范围',
      'allBrands': '已授权的全球品牌集合',
      'brandUnknown': '品牌名称暂不可用',
      'objective': '活动目标',
      'goalUnavailable': '活动目标暂不可用',
      'timeline': '里程碑时间线',
      'nextSteps': '活动推进',
      'noMilestones': '还没有可确认的里程碑。',
      'channels': '渠道组合',
      'noChannels': '还没有可确认的渠道安排。',
      'planned': '计划中',
      'budgeted': '已预算',
      'plannedOutcome': '计划结果',
      'actualOutcome': '实际结果',
      'notSet': '尚未设置',
      'actualPending': '等待真实结果',
      'unavailableTitle': '活动资料暂不可用',
      'unavailableDetail': '当前品牌活动范围尚未确认，暂不显示其他品牌的活动、预算或结果。',
      'notCollectedTitle': '还没有活动资料',
      'notCollectedDetail': '活动目标、节奏和来源资料准备好后，这里会显示可推进的工作。',
      'noCampaignTitle': '当前品牌还没有可展示的活动',
      'noCampaignDetail': '可以保留计划入口，但不会把配额或冷却状态当作活动结果。',
      'actionBlocked': '当前范围还不能执行这项活动操作；请先确认品牌范围与授权条件。',
      'actionStaged': '本地活动请求草稿已保存；尚未追加内容或结束活动。',
      'closeGuard': '这里仅保存本地结束活动草稿；活动不会结束，直到授权与实际结果归档。',
      'loading': '正在加载活动控制室',
      'signIn': '当前内容暂时无法打开',
      'accessDenied': '当前内容不可访问',
      'offline': '暂时无法连接活动服务',
      'retryDetail': '可重试读取，或返回后稍后再试。',
      'addContent': '保存追加内容草稿',
      'endCampaign': '保存结束活动草稿',
      'stage.PLANNED': '已规划',
      'stage.BUDGETED': '已预算',
      'stage.LAUNCHED': '已启动',
      'stage.OBSERVED': '已观察',
      'stage.MEASURED': '已测量',
      'stageNote.PLANNED': '当前只确认了活动计划。',
      'stageNote.BUDGETED': '预算已经记录，尚未代表活动已启动。',
      'stageNote.LAUNCHED': '活动已启动，实际表现仍待回传。',
      'stageNote.OBSERVED': '已有观察结果，测量口径仍需完成。',
      'stageNote.MEASURED': '已记录测量结果，可进入评估。',
    },
    'en': {
      'subtitle':
          'Keep objective, audience, channels, milestones and real outcomes in one campaign room.',
      'refresh': 'Refresh campaign state',
      'focusRange': 'Brand focus',
      'globalRange': 'Global brand range',
      'allBrands': 'Authorized global brand set',
      'brandUnknown': 'Brand name unavailable',
      'objective': 'Campaign objective',
      'goalUnavailable': 'Campaign objective unavailable',
      'timeline': 'Milestone timeline',
      'nextSteps': 'Campaign progress',
      'noMilestones': 'No confirmed milestones are available.',
      'channels': 'Channel mix',
      'noChannels': 'No confirmed channel plan is available.',
      'planned': 'Planned',
      'budgeted': 'Budgeted',
      'plannedOutcome': 'Planned outcome',
      'actualOutcome': 'Actual outcome',
      'notSet': 'Not set',
      'actualPending': 'Waiting for actual result',
      'unavailableTitle': 'Campaign material is unavailable',
      'unavailableDetail':
          'The current brand campaign range is not confirmed. Activity, budget and outcomes from another brand stay hidden.',
      'notCollectedTitle': 'No campaign material has been collected',
      'notCollectedDetail':
          'Confirmed objectives, timing and source material will appear when ready.',
      'noCampaignTitle': 'No campaign is available for this brand',
      'noCampaignDetail':
          'A planning entry may remain available, but process quota or cooldown is not a campaign outcome.',
      'actionBlocked':
          'This campaign action is not available in the current brand range or access state.',
      'actionStaged':
          'Local campaign request draft saved. No content was added and no campaign was closed.',
      'closeGuard':
          'This only saves a local campaign-close draft. The campaign is not closed until authorization and an archived actual result are ready.',
      'loading': 'Loading campaign room',
      'signIn': 'This content cannot be opened right now.',
      'accessDenied': 'This content is not accessible.',
      'offline': 'Campaign service is unavailable',
      'retryDetail': 'You can retry reading it or return and try again later.',
      'addContent': 'Save content-addition draft',
      'endCampaign': 'Save campaign-close draft',
      'stage.PLANNED': 'Planned',
      'stage.BUDGETED': 'Budgeted',
      'stage.LAUNCHED': 'Launched',
      'stage.OBSERVED': 'Observed',
      'stage.MEASURED': 'Measured',
      'stageNote.PLANNED': 'Only the campaign plan is confirmed.',
      'stageNote.BUDGETED':
          'Budget is recorded; this does not mean the campaign launched.',
      'stageNote.LAUNCHED':
          'The campaign launched; actual performance is still pending.',
      'stageNote.OBSERVED':
          'Observations exist; the measurement definition is still pending.',
      'stageNote.MEASURED':
          'A measured result is recorded and can be evaluated.',
    },
    'ko': {
      'subtitle': '목표, 대상, 채널, 마일스톤과 실제 결과를 하나의 캠페인 룸에서 관리합니다.',
      'refresh': '캠페인 상태 새로고침',
      'focusRange': '현재 브랜드',
      'globalRange': '글로벌 브랜드 범위',
      'allBrands': '승인된 글로벌 브랜드 집합',
      'brandUnknown': '브랜드 이름을 사용할 수 없습니다',
      'objective': '캠페인 목표',
      'goalUnavailable': '캠페인 목표를 사용할 수 없습니다',
      'timeline': '마일스톤 타임라인',
      'nextSteps': '캠페인 진행',
      'noMilestones': '확인된 마일스톤이 없습니다.',
      'channels': '채널 구성',
      'noChannels': '확인된 채널 계획이 없습니다.',
      'planned': '계획됨',
      'budgeted': '예산 반영',
      'plannedOutcome': '계획 결과',
      'actualOutcome': '실제 결과',
      'notSet': '설정되지 않음',
      'actualPending': '실제 결과 대기',
      'unavailableTitle': '캠페인 자료를 사용할 수 없습니다',
      'unavailableDetail':
          '현재 브랜드 캠페인 범위가 확인되지 않았습니다. 다른 브랜드의 활동, 예산과 결과를 표시하지 않습니다.',
      'notCollectedTitle': '아직 캠페인 자료가 수집되지 않았습니다',
      'notCollectedDetail': '확인된 목표, 일정과 자료가 준비되면 표시됩니다.',
      'noCampaignTitle': '이 브랜드에 표시할 캠페인이 없습니다',
      'noCampaignDetail': '계획 진입점은 남길 수 있지만 처리 한도나 대기 시간은 캠페인 결과가 아닙니다.',
      'actionBlocked': '현재 브랜드 범위 또는 접근 상태에서는 이 작업을 사용할 수 없습니다.',
      'actionStaged': '캠페인 요청 초안을 로컬에 저장했습니다. 콘텐츠를 추가하거나 캠페인을 종료하지 않았습니다.',
      'closeGuard':
          '여기서는 로컬 캠페인 종료 초안만 저장합니다. 접근과 실제 결과가 준비될 때까지 캠페인을 종료하지 않습니다.',
      'loading': '캠페인 룸을 불러오는 중',
      'signIn': '현재 콘텐츠를 지금 열 수 없습니다.',
      'accessDenied': '현재 콘텐츠에 접근할 수 없습니다.',
      'offline': '캠페인 서비스에 연결할 수 없습니다',
      'retryDetail': '다시 읽기를 시도하거나 돌아간 뒤 나중에 다시 시도할 수 있습니다.',
      'addContent': '콘텐츠 추가 초안 저장',
      'endCampaign': '캠페인 종료 초안 저장',
      'stage.PLANNED': '계획됨',
      'stage.BUDGETED': '예산 반영',
      'stage.LAUNCHED': '시작됨',
      'stage.OBSERVED': '관찰됨',
      'stage.MEASURED': '측정됨',
      'stageNote.PLANNED': '캠페인 계획만 확인되었습니다.',
      'stageNote.BUDGETED': '예산이 기록되었지만 캠페인 시작을 뜻하지 않습니다.',
      'stageNote.LAUNCHED': '캠페인이 시작되었으며 실제 성과를 기다리고 있습니다.',
      'stageNote.OBSERVED': '관찰 결과가 있지만 측정 정의가 아직 필요합니다.',
      'stageNote.MEASURED': '측정 결과가 기록되어 평가할 수 있습니다.',
    },
  };
}
