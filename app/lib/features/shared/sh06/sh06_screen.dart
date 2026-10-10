import 'package:flutter/material.dart';

import '../../../core/lumenis_icon.dart';

import '../../../core/lumenis_core_client.dart';
import '../../../core/lumenis_theme.dart';
import '../../../l10n/lumenis_localizations.dart';
import 'sh06_repository.dart';
import 'sh06_snapshot.dart';
import 'sh06_view_model.dart';

class Sh06Screen extends StatefulWidget {
  const Sh06Screen({required this.client, this.repository, super.key});

  final LumenisCoreClient client;
  final Sh06Repository? repository;

  @override
  State<Sh06Screen> createState() => _Sh06ScreenState();
}

class _Sh06ScreenState extends State<Sh06Screen> {
  late final Sh06ViewModel _viewModel = Sh06ViewModel(
    repository: widget.repository ?? CoreSh06Repository(client: widget.client),
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
  Widget build(BuildContext context) => ColoredBox(
    color: LumenisTheme.of(context).canvas,
    child: SafeArea(
      child: AnimatedBuilder(
        animation: _viewModel,
        builder: (context, _) => switch (_viewModel.phase) {
          Sh06LoadPhase.loading => _LoadingState(),
          Sh06LoadPhase.blocked => _BlockedState(
            error: _viewModel.scopeError,
            onRetry: _viewModel.refresh,
          ),
          Sh06LoadPhase.failed => _FailureState(
            kind: _viewModel.failureKind!,
            onRetry: _viewModel.refresh,
          ),
          Sh06LoadPhase.ready => _Workspace(viewModel: _viewModel),
        },
      ),
    ),
  );
}

class _Workspace extends StatelessWidget {
  const _Workspace({required this.viewModel});

  final Sh06ViewModel viewModel;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, constraints) {
      final wide = constraints.maxWidth >= 1120;
      final lanes = _LaneRail(viewModel: viewModel);
      final detail = _InboxDetail(item: viewModel.selected);
      final scope = viewModel.snapshot!.scope;
      return Align(
        alignment: Alignment.topCenter,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1500),
          child: SingleChildScrollView(
            padding: EdgeInsets.fromLTRB(
              wide ? 32 : 18,
              24,
              wide ? 32 : 18,
              44,
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _Header(),
                const SizedBox(height: 18),
                _ScopeBanner(scope: scope),
                const SizedBox(height: 16),
                if (wide)
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(child: lanes),
                      const SizedBox(width: 16),
                      SizedBox(width: 360, child: detail),
                    ],
                  )
                else
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [lanes, const SizedBox(height: 14), detail],
                  ),
                const SizedBox(height: 14),
                _OperationalNote(state: viewModel.operationalState),
                const SizedBox(height: 14),
                Align(
                  alignment: Alignment.centerLeft,
                  child: OutlinedButton.icon(
                    onPressed: viewModel.refresh,
                    icon: const LumenisIcon(Icons.refresh_rounded),
                    label: Text(_copy(context, '重新读取', 'Read again', '다시 읽기')),
                    style: OutlinedButton.styleFrom(
                      minimumSize: const Size(48, 48),
                    ),
                  ),
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
  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      _Eyebrow(_copy(context, '及时处理', 'ACTION INBOX', '처리함')),
      const SizedBox(height: 9),
      Text(
        context.lumenisL10n.text('screen.SH-06'),
        style: Theme.of(context).textTheme.headlineMedium?.copyWith(
          color: LumenisTheme.of(context).foreground,
          fontWeight: FontWeight.w600,
        ),
      ),
      const SizedBox(height: 6),
      Text(
        _copy(
          context,
          '把待办、通知和告警放在不同优先级通道中，并保留每条事项的来源。',
          'Separate tasks, notifications and alerts into urgency lanes while keeping each item’s origin visible.',
          '할 일·알림·경고를 우선순위 채널로 나누고 각 항목의 출처를 유지합니다.',
        ),
        style: TextStyle(color: LumenisTheme.of(context).muted, height: 1.45),
      ),
    ],
  );
}

class _ScopeBanner extends StatelessWidget {
  const _ScopeBanner({required this.scope});

  final Sh06Scope scope;

  @override
  Widget build(BuildContext context) {
    final range = scope.isGlobal
        ? _copy(context, '全部范围', 'All scopes', '전체 범위')
        : '${scope.businessDomain} · ${scope.displayName}';
    return Semantics(
      liveRegion: true,
      label: _copy(
        context,
        '当前通知范围：$range',
        'Current inbox range: $range',
        '현재 받은편지함 범위: $range',
      ),
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(horizontal: 15, vertical: 12),
        decoration: BoxDecoration(
          color: LumenisTheme.of(context).cth.withValues(alpha: 0.08),
          border: Border.all(
            color: LumenisTheme.of(context).cth.withValues(alpha: 0.35),
          ),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Row(
          children: [
            Icon(
              Icons.filter_alt_outlined,
              color: LumenisTheme.of(context).cth,
              size: 19,
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                range,
                style: const TextStyle(fontWeight: FontWeight.w600),
              ),
            ),
            Text(
              _copy(context, '已确认查看范围', 'Verified viewing range', '확인된 조회 범위'),
              style: TextStyle(
                color: LumenisTheme.of(context).muted,
                fontSize: 12,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _LaneRail extends StatelessWidget {
  const _LaneRail({required this.viewModel});

  final Sh06ViewModel viewModel;

  @override
  Widget build(BuildContext context) {
    final items = viewModel.visibleItems;
    return _Panel(
      title: _copy(context, '处理通道', 'Action lanes', '처리 채널'),
      detail: _copy(
        context,
        '选择一条事项查看来源和当前状态。',
        'Select an item to inspect its origin and current state.',
        '항목을 선택해 출처와 현재 상태를 확인하세요.',
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _LaneTabs(viewModel: viewModel),
          const SizedBox(height: 14),
          if (items.isEmpty)
            _InfoMessage(
              _copy(
                context,
                '当前通道没有已核实事项。',
                'No verified items are in this lane.',
                '현재 채널에 확인된 항목이 없습니다.',
              ),
            )
          else
            for (final item in items)
              _InboxRow(
                item: item,
                selected: viewModel.selected?.internalId == item.internalId,
                onTap: () => viewModel.select(item),
              ),
        ],
      ),
    );
  }
}

class _LaneTabs extends StatelessWidget {
  const _LaneTabs({required this.viewModel});

  final Sh06ViewModel viewModel;

  @override
  Widget build(BuildContext context) => Wrap(
    spacing: 7,
    runSpacing: 7,
    children: [
      for (final lane in Sh06Lane.values)
        ChoiceChip(
          label: Text(_laneLabel(context, lane)),
          selected: viewModel.lane == lane,
          onSelected: (_) => viewModel.setLane(lane),
          avatar: Icon(_laneIcon(lane), size: 16),
          materialTapTargetSize: MaterialTapTargetSize.padded,
        ),
    ],
  );
}

class _InboxRow extends StatelessWidget {
  const _InboxRow({
    required this.item,
    required this.selected,
    required this.onTap,
  });

  final Sh06Item item;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 8),
    child: Material(
      color: selected
          ? LumenisTheme.of(context).cth.withValues(alpha: 0.1)
          : LumenisTheme.of(context).surfaceRaised,
      borderRadius: BorderRadius.circular(10),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(10),
        child: Container(
          constraints: const BoxConstraints(minHeight: 78),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          decoration: BoxDecoration(
            border: Border.all(
              color: selected
                  ? LumenisTheme.of(context).cth.withValues(alpha: 0.55)
                  : LumenisTheme.of(context).line,
            ),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(
                _laneIcon(
                  item.kind == Sh06ItemKind.task
                      ? Sh06Lane.tasks
                      : item.kind == Sh06ItemKind.alert
                      ? Sh06Lane.alerts
                      : Sh06Lane.notifications,
                ),
                color: _priorityColor(context, item.priority),
                size: 19,
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      item.title,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontWeight: FontWeight.w600),
                    ),
                    const SizedBox(height: 6),
                    Wrap(
                      spacing: 8,
                      runSpacing: 4,
                      children: [
                        if (item.sourceLabel.isNotEmpty)
                          Text(
                            item.sourceLabel,
                            style: TextStyle(
                              color: LumenisTheme.of(context).muted,
                              fontSize: 11,
                            ),
                          ),
                        _SmallTag(
                          item.priorityLabel,
                          color: _priorityColor(context, item.priority),
                        ),
                        _SmallTag(
                          item.stateLabel,
                          color: _stateColor(context, item.state),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              Icon(
                selected
                    ? Icons.chevron_right_rounded
                    : Icons.visibility_outlined,
                color: LumenisTheme.of(context).quiet,
                size: 18,
              ),
            ],
          ),
        ),
      ),
    ),
  );
}

class _InboxDetail extends StatelessWidget {
  const _InboxDetail({required this.item});

  final Sh06Item? item;

  @override
  Widget build(BuildContext context) {
    final selected = item;
    return _Panel(
      title: _copy(context, '事项详情', 'Item detail', '항목 세부 정보'),
      detail: _copy(
        context,
        '来源和返回路径必须先核实，处理动作不会在这里伪造。',
        'Origin and return path must be verified before any action; actions are not simulated here.',
        '작업 전에 출처와 반환 경로를 확인해야 하며 여기서 작업을 가장하지 않습니다.',
      ),
      child: selected == null
          ? _InfoMessage(
              _copy(
                context,
                '选择一条事项查看详情。',
                'Select an item to inspect its details.',
                '항목을 선택해 세부 정보를 확인하세요.',
              ),
            )
          : Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  selected.title,
                  style: const TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 13),
                _DetailLine(
                  label: _copy(context, '类型', 'Type', '유형'),
                  value: selected.kindLabel,
                ),
                _DetailLine(
                  label: _copy(context, '状态', 'State', '상태'),
                  value: selected.stateLabel,
                ),
                _DetailLine(
                  label: _copy(context, '优先级', 'Priority', '우선순위'),
                  value: selected.priorityLabel,
                ),
                if (selected.sourceLabel.isNotEmpty)
                  _DetailLine(
                    label: _copy(context, '来源', 'Origin', '출처'),
                    value: selected.sourceLabel,
                  ),
                if (selected.due.isNotEmpty)
                  _DetailLine(
                    label: _copy(context, '时间', 'Time', '시간'),
                    value: selected.due,
                  ),
                if (selected.detail.isNotEmpty) ...[
                  const SizedBox(height: 4),
                  Text(
                    selected.detail,
                    style: TextStyle(
                      color: LumenisTheme.of(context).muted,
                      height: 1.5,
                    ),
                  ),
                ],
                const SizedBox(height: 14),
                _OriginStatus(
                  originVerified: selected.originVerified,
                  evidenceLinked: selected.evidenceLinked,
                ),
                const SizedBox(height: 14),
                Text(
                  _copy(
                    context,
                    '通过、指派、稍后提醒等动作需要单独的受控入口；当前只展示真实状态。',
                    'Approve, assign and snooze actions need a separate governed entry; this view only shows real state.',
                    '승인·할당·다시 알림 작업에는 별도의 통제 입구가 필요하며 이 화면은 실제 상태만 표시합니다.',
                  ),
                  style: TextStyle(
                    color: LumenisTheme.of(context).quiet,
                    fontSize: 11,
                    height: 1.45,
                  ),
                ),
              ],
            ),
    );
  }
}

class _OriginStatus extends StatelessWidget {
  const _OriginStatus({
    required this.originVerified,
    required this.evidenceLinked,
  });

  final bool originVerified;
  final bool evidenceLinked;

  @override
  Widget build(BuildContext context) => Column(
    children: [
      _StatusLine(
        label: _copy(context, '来源', 'Origin', '출처'),
        value: originVerified
            ? _copy(context, '已确认', 'Verified', '확인됨')
            : _copy(context, '未确认', 'Unconfirmed', '미확인'),
        color: originVerified
            ? LumenisTheme.of(context).positive
            : LumenisTheme.of(context).caution,
      ),
      const SizedBox(height: 8),
      _StatusLine(
        label: _copy(context, '关联资料', 'Linked material', '연결 자료'),
        value: evidenceLinked
            ? _copy(context, '已关联', 'Linked', '연결됨')
            : _copy(context, '未提供', 'Not provided', '제공되지 않음'),
        color: evidenceLinked
            ? LumenisTheme.of(context).positive
            : LumenisTheme.of(context).muted,
      ),
    ],
  );
}

class _OperationalNote extends StatelessWidget {
  const _OperationalNote({required this.state});

  final String state;

  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    padding: const EdgeInsets.fromLTRB(15, 13, 15, 13),
    decoration: BoxDecoration(
      color: LumenisTheme.of(context).cth.withValues(alpha: 0.08),
      border: Border.all(
        color: LumenisTheme.of(context).cth.withValues(alpha: 0.32),
      ),
      borderRadius: BorderRadius.circular(11),
    ),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(
          Icons.monitor_heart_outlined,
          color: LumenisTheme.of(context).cth,
          size: 19,
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Text(
            _copy(
              context,
              '当前运行状态：$state。队列和通知只显示范围已确认的事项；动作是否可用仍由受控入口决定。',
              'Operational state: $state. The inbox shows only range-confirmed items; action availability still comes from a governed entry.',
              '현재 실행 상태: $state. 받은편지함에는 범위가 확인된 항목만 표시되며 작업 가능 여부는 통제된 입구가 결정합니다.',
            ),
            style: TextStyle(
              color: LumenisTheme.of(context).muted,
              height: 1.45,
            ),
          ),
        ),
      ],
    ),
  );
}

class _LoadingState extends StatelessWidget {
  @override
  Widget build(BuildContext context) => Semantics(
    liveRegion: true,
    label: _copy(
      context,
      '正在读取通知与待办',
      'Reading tasks and notifications',
      '작업과 알림을 읽는 중',
    ),
    child: const Center(child: CircularProgressIndicator()),
  );
}

class _BlockedState extends StatelessWidget {
  const _BlockedState({required this.error, required this.onRetry});

  final Sh06ScopeErrorKind? error;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => _StateMessage(
    title: _copy(
      context,
      '通知与待办暂不显示',
      'Inbox is hidden for now',
      '받은편지함을 현재 표시하지 않습니다',
    ),
    detail: switch (error) {
      Sh06ScopeErrorKind.denied => _copy(
        context,
        '当前账号没有这个范围的查看权限。',
        'This account cannot view the selected range.',
        '이 계정은 선택한 범위를 볼 수 없습니다.',
      ),
      Sh06ScopeErrorKind.malformed => _copy(
        context,
        '服务返回的查看范围不完整，因此不会显示事项。',
        'The returned viewing range is incomplete, so items are not shown.',
        '반환된 조회 범위가 불완전하여 항목을 표시하지 않습니다.',
      ),
      _ => _copy(
        context,
        '尚未确认账号与业务范围的对应关系，因此不会显示事项。',
        'The account and business range have not been verified, so items are not shown.',
        '계정과 업무 범위가 확인되지 않아 항목을 표시하지 않습니다.',
      ),
    },
    onRetry: onRetry,
  );
}

class _FailureState extends StatelessWidget {
  const _FailureState({required this.kind, required this.onRetry});

  final Sh06FailureKind kind;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => _StateMessage(
    title: _copy(
      context,
      '通知与待办暂不可用',
      'Inbox unavailable',
      '받은편지함을 사용할 수 없습니다',
    ),
    detail: switch (kind) {
      Sh06FailureKind.authentication => _copy(
        context,
        '当前内容暂时无法打开。可重试读取，或返回后稍后再试。',
        'This content cannot be opened right now. You can retry reading it or return and try again later.',
        '현재 콘텐츠를 지금 열 수 없습니다. 다시 읽기를 시도하거나 돌아간 뒤 나중에 다시 시도할 수 있습니다.',
      ),
      Sh06FailureKind.permissionDenied => _copy(
        context,
        '当前内容不可访问。',
        'This content is not accessible.',
        '현재 콘텐츠에 접근할 수 없습니다.',
      ),
      Sh06FailureKind.offline => _copy(
        context,
        '通知服务暂时无法连接，请检查连接后重试。',
        'The inbox service cannot connect right now. Check the connection and try again.',
        '받은편지함 서비스에 연결할 수 없습니다. 연결을 확인하고 다시 시도하세요.',
      ),
      Sh06FailureKind.response => _copy(
        context,
        '通知服务没有返回可验证的数据，请稍后重试。',
        'The inbox service did not return verifiable data. Try again later.',
        '받은편지함 서비스가 확인 가능한 데이터를 반환하지 않았습니다. 나중에 다시 시도하세요.',
      ),
    },
    onRetry: onRetry,
  );
}

class _StateMessage extends StatelessWidget {
  const _StateMessage({
    required this.title,
    required this.detail,
    required this.onRetry,
  });

  final String title;
  final String detail;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => Center(
    child: ConstrainedBox(
      constraints: const BoxConstraints(maxWidth: 620),
      child: Padding(
        padding: const EdgeInsets.all(26),
        child: _Panel(
          title: title,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                detail,
                style: TextStyle(
                  color: LumenisTheme.of(context).muted,
                  height: 1.5,
                ),
              ),
              const SizedBox(height: 18),
              OutlinedButton(
                onPressed: onRetry,
                child: Text(_copy(context, '重新读取', 'Read again', '다시 읽기')),
              ),
            ],
          ),
        ),
      ),
    ),
  );
}

class _Panel extends StatelessWidget {
  const _Panel({required this.title, required this.child, this.detail});

  final String title;
  final String? detail;
  final Widget child;

  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    padding: const EdgeInsets.fromLTRB(16, 15, 16, 15),
    decoration: BoxDecoration(
      color: LumenisTheme.of(context).surface,
      border: Border.all(color: LumenisTheme.of(context).line),
      borderRadius: BorderRadius.circular(13),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
        ),
        if (detail != null) ...[
          const SizedBox(height: 4),
          Text(
            detail!,
            style: TextStyle(
              color: LumenisTheme.of(context).quiet,
              fontSize: 11,
              height: 1.45,
            ),
          ),
        ],
        const SizedBox(height: 12),
        child,
      ],
    ),
  );
}

class _DetailLine extends StatelessWidget {
  const _DetailLine({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 10),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 78,
          child: Text(
            label,
            style: TextStyle(
              color: LumenisTheme.of(context).quiet,
              fontSize: 11,
            ),
          ),
        ),
        Expanded(
          child: Text(
            value,
            style: const TextStyle(fontWeight: FontWeight.w600),
          ),
        ),
      ],
    ),
  );
}

class _StatusLine extends StatelessWidget {
  const _StatusLine({
    required this.label,
    required this.value,
    required this.color,
  });

  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) => Row(
    children: [
      Expanded(
        child: Text(
          label,
          style: TextStyle(color: LumenisTheme.of(context).quiet, fontSize: 11),
        ),
      ),
      Text(
        value,
        style: TextStyle(
          color: color,
          fontWeight: FontWeight.w600,
          fontSize: 12,
        ),
      ),
    ],
  );
}

class _SmallTag extends StatelessWidget {
  const _SmallTag(this.label, {required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 4),
    decoration: BoxDecoration(
      color: color.withValues(alpha: 0.12),
      borderRadius: BorderRadius.circular(12),
    ),
    child: Text(
      label,
      style: TextStyle(color: color, fontSize: 10, fontWeight: FontWeight.w600),
    ),
  );
}

class _InfoMessage extends StatelessWidget {
  const _InfoMessage(this.message);

  final String message;

  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 15),
    decoration: BoxDecoration(
      color: LumenisTheme.of(context).canvas,
      borderRadius: BorderRadius.circular(9),
    ),
    child: Text(
      message,
      style: TextStyle(color: LumenisTheme.of(context).muted, height: 1.45),
    ),
  );
}

class _Eyebrow extends StatelessWidget {
  const _Eyebrow(this.label);

  final String label;

  @override
  Widget build(BuildContext context) => Text(
    label,
    style: TextStyle(
      color: LumenisTheme.of(context).cth,
      fontSize: 10,
      letterSpacing: 1.1,
      fontWeight: FontWeight.w700,
    ),
  );
}

IconData _laneIcon(Sh06Lane lane) => switch (lane) {
  Sh06Lane.tasks => Icons.checklist_rounded,
  Sh06Lane.notifications => Icons.notifications_none_rounded,
  Sh06Lane.alerts => Icons.warning_amber_rounded,
};

String _laneLabel(BuildContext context, Sh06Lane lane) => switch (lane) {
  Sh06Lane.tasks => _copy(context, '待办', 'Tasks', '할 일'),
  Sh06Lane.notifications => _copy(context, '通知', 'Notifications', '알림'),
  Sh06Lane.alerts => _copy(context, '告警', 'Alerts', '경고'),
};

Color _priorityColor(BuildContext context, Sh06Priority priority) =>
    switch (priority) {
      Sh06Priority.high => LumenisTheme.of(context).danger,
      Sh06Priority.medium => LumenisTheme.of(context).caution,
      Sh06Priority.low => LumenisTheme.of(context).system,
      Sh06Priority.unknown => LumenisTheme.of(context).muted,
    };

Color _stateColor(BuildContext context, Sh06ItemState state) => switch (state) {
  Sh06ItemState.complete => LumenisTheme.of(context).positive,
  Sh06ItemState.inProgress => LumenisTheme.of(context).system,
  Sh06ItemState.blocked => LumenisTheme.of(context).danger,
  Sh06ItemState.open => LumenisTheme.of(context).caution,
  Sh06ItemState.unavailable => LumenisTheme.of(context).muted,
};

String _copy(BuildContext context, String zh, String en, String ko) =>
    switch (context.lumenisL10n.locale.languageCode) {
      'en' => en,
      'ko' => ko,
      _ => zh,
    };
