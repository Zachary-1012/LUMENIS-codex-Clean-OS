import 'package:flutter/material.dart';

import '../../core/lumenis_core_client.dart';
import '../../core/lumenis_theme.dart';
import '../../l10n/lumenis_localizations.dart';
import 'bmp10_repository.dart';
import 'bmp10_snapshot.dart';
import 'bmp10_view_model.dart';

class Bmp10Screen extends StatefulWidget {
  const Bmp10Screen({required this.client, this.repository, super.key});

  final LumenisCoreClient client;
  final Bmp10Repository? repository;

  @override
  State<Bmp10Screen> createState() => _Bmp10ScreenState();
}

class _Bmp10ScreenState extends State<Bmp10Screen> {
  late final Bmp10ViewModel _viewModel = Bmp10ViewModel(
    repository: widget.repository ?? CoreBmp10Repository(client: widget.client),
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
            Bmp10LoadPhase.loading => const _Loading(),
            Bmp10LoadPhase.failed => _Failure(
              kind: _viewModel.failureKind!,
              onRetry: _viewModel.refresh,
            ),
            Bmp10LoadPhase.ready => _RiskDesk(
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

class _RiskDesk extends StatelessWidget {
  const _RiskDesk({
    required this.snapshot,
    required this.actionState,
    required this.actionId,
    required this.onRefresh,
    required this.onAction,
  });

  final Bmp10Snapshot snapshot;
  final Bmp10ActionState actionState;
  final String? actionId;
  final VoidCallback onRefresh;
  final void Function(String actionId, String permission) onAction;

  @override
  Widget build(BuildContext context) {
    final copy = _Bmp10Copy.of(context);
    return LayoutBuilder(
      builder: (context, constraints) {
        final wide = constraints.maxWidth >= 1040;
        final padding = constraints.maxWidth >= 800 ? 32.0 : 18.0;
        final body = !snapshot.scopeApproved
            ? _Gate(snapshot: snapshot, copy: copy)
            : snapshot.risks.isEmpty && snapshot.events.isEmpty
            ? _Empty(copy: copy)
            : wide
            ? _DesktopRisk(snapshot: snapshot, copy: copy)
            : _MobileRisk(snapshot: snapshot, copy: copy);
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
                  body,
                  const SizedBox(height: 22),
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

class _Header extends StatelessWidget {
  const _Header({required this.copy, required this.onRefresh});

  final _Bmp10Copy copy;
  final VoidCallback onRefresh;

  @override
  Widget build(BuildContext context) => Row(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Expanded(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              context.lumenisL10n.text('screen.BMP-10'),
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

class _DesktopRisk extends StatelessWidget {
  const _DesktopRisk({required this.snapshot, required this.copy});

  final Bmp10Snapshot snapshot;
  final _Bmp10Copy copy;

  @override
  Widget build(BuildContext context) {
    final scopeLabel = snapshot.scope.isGlobal ? copy.globalRange : copy.focus;
    final brand =
        snapshot.scope.localizedName(copy.languageCode) ??
        (snapshot.scope.isGlobal ? copy.allBrands : copy.brandUnknown);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _FocusLine(brand: brand, copy: copy, scopeLabel: scopeLabel),
        const SizedBox(height: 16),
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              flex: 5,
              child: _IncidentField(risks: snapshot.risks, copy: copy),
            ),
            const SizedBox(width: 18),
            Expanded(
              flex: 6,
              child: _ResponseTimeline(events: snapshot.events, copy: copy),
            ),
          ],
        ),
      ],
    );
  }
}

class _MobileRisk extends StatelessWidget {
  const _MobileRisk({required this.snapshot, required this.copy});

  final Bmp10Snapshot snapshot;
  final _Bmp10Copy copy;

  @override
  Widget build(BuildContext context) {
    final scopeLabel = snapshot.scope.isGlobal ? copy.globalRange : copy.focus;
    final brand =
        snapshot.scope.localizedName(copy.languageCode) ??
        (snapshot.scope.isGlobal ? copy.allBrands : copy.brandUnknown);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _FocusLine(brand: brand, copy: copy, scopeLabel: scopeLabel),
        const SizedBox(height: 14),
        _IncidentField(risks: snapshot.risks, copy: copy),
        const SizedBox(height: 14),
        _ResponseTimeline(events: snapshot.events, copy: copy),
      ],
    );
  }
}

class _FocusLine extends StatelessWidget {
  const _FocusLine({
    required this.brand,
    required this.copy,
    required this.scopeLabel,
  });

  final String brand;
  final _Bmp10Copy copy;
  final String scopeLabel;

  @override
  Widget build(BuildContext context) => DecoratedBox(
    decoration: BoxDecoration(
      border: Border(bottom: BorderSide(color: LumenisTheme.of(context).line)),
    ),
    child: Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        children: [
          Icon(Icons.shield_outlined, color: LumenisTheme.of(context).bmp),
          const SizedBox(width: 10),
          Text(
            scopeLabel,
            style: TextStyle(color: LumenisTheme.of(context).quiet),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              brand,
              style: TextStyle(
                color: LumenisTheme.of(context).foreground,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          Text(
            copy.brandOnly,
            style: TextStyle(
              color: LumenisTheme.of(context).quiet,
              fontSize: 11,
            ),
          ),
        ],
      ),
    ),
  );
}

class _IncidentField extends StatelessWidget {
  const _IncidentField({required this.risks, required this.copy});

  final List<Bmp10Risk> risks;
  final _Bmp10Copy copy;

  @override
  Widget build(BuildContext context) {
    final severityOrder = const ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'];
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
            Text(
              copy.incidents,
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 14),
            for (final severity in severityOrder)
              for (final risk in risks.where(
                (item) => item.severity == severity,
              ))
                _RiskRow(risk: risk, copy: copy),
          ],
        ),
      ),
    );
  }
}

class _RiskRow extends StatelessWidget {
  const _RiskRow({required this.risk, required this.copy});

  final Bmp10Risk risk;
  final _Bmp10Copy copy;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 12),
    child: DecoratedBox(
      decoration: BoxDecoration(
        color: LumenisTheme.of(context).surfaceRaised,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: _severityColor(context, risk.severity).withValues(alpha: 0.35),
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(13, 12, 13, 11),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 9,
              height: 9,
              margin: const EdgeInsets.only(top: 5),
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: _severityColor(context, risk.severity),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    risk.title,
                    style: TextStyle(
                      color: LumenisTheme.of(context).foreground,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 5),
                  Text(
                    '${copy.severity(risk.severity)} · ${risk.recency}',
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
    ),
  );

  Color _severityColor(BuildContext context, String severity) =>
      switch (severity) {
        'CRITICAL' => LumenisTheme.of(context).danger,
        'HIGH' => LumenisTheme.of(context).caution,
        'MEDIUM' => LumenisTheme.of(context).bmp,
        _ => LumenisTheme.of(context).muted,
      };
}

class _ResponseTimeline extends StatelessWidget {
  const _ResponseTimeline({required this.events, required this.copy});

  final List<Bmp10Event> events;
  final _Bmp10Copy copy;

  @override
  Widget build(BuildContext context) => DecoratedBox(
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
          Text(copy.timeline, style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 14),
          if (events.isEmpty)
            Text(
              copy.noEvents,
              style: TextStyle(color: LumenisTheme.of(context).muted),
            )
          else
            for (var index = 0; index < events.length; index++)
              _EventRow(
                event: events[index],
                copy: copy,
                last: index == events.length - 1,
              ),
        ],
      ),
    ),
  );
}

class _EventRow extends StatelessWidget {
  const _EventRow({
    required this.event,
    required this.copy,
    required this.last,
  });

  final Bmp10Event event;
  final _Bmp10Copy copy;
  final bool last;

  @override
  Widget build(BuildContext context) => IntrinsicHeight(
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        SizedBox(
          width: 22,
          child: Column(
            children: [
              Icon(Icons.circle, size: 9, color: LumenisTheme.of(context).bmp),
              if (!last)
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
                  event.title,
                  style: TextStyle(
                    color: LumenisTheme.of(context).foreground,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  '${event.date} · ${copy.eventState(event.state)}',
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

class _Gate extends StatelessWidget {
  const _Gate({required this.snapshot, required this.copy});

  final Bmp10Snapshot snapshot;
  final _Bmp10Copy copy;

  @override
  Widget build(BuildContext context) => _Notice(
    icon: snapshot.dataState == 'NOT_COLLECTED'
        ? Icons.hourglass_empty_rounded
        : Icons.lock_outline_rounded,
    title: snapshot.dataState == 'NOT_COLLECTED'
        ? copy.notCollectedTitle
        : copy.unavailableTitle,
    detail: snapshot.dataState == 'NOT_COLLECTED'
        ? copy.notCollectedDetail
        : copy.unavailableDetail,
  );
}

class _Empty extends StatelessWidget {
  const _Empty({required this.copy});

  final _Bmp10Copy copy;

  @override
  Widget build(BuildContext context) => _Notice(
    icon: Icons.shield_moon_outlined,
    title: copy.noRiskTitle,
    detail: copy.noRiskDetail,
  );
}

class _Notice extends StatelessWidget {
  const _Notice({
    required this.icon,
    required this.title,
    required this.detail,
  });

  final IconData icon;
  final String title;
  final String detail;

  @override
  Widget build(BuildContext context) => DecoratedBox(
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

class _ActionRail extends StatelessWidget {
  const _ActionRail({
    required this.copy,
    required this.state,
    required this.actionId,
    required this.onAction,
  });

  final _Bmp10Copy copy;
  final Bmp10ActionState state;
  final String? actionId;
  final void Function(String actionId, String permission) onAction;

  @override
  Widget build(BuildContext context) {
    final notice = switch (state) {
      Bmp10ActionState.idle => null,
      Bmp10ActionState.blocked => copy.actionBlocked,
      Bmp10ActionState.staged => copy.actionStaged,
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
                color: state == Bmp10ActionState.staged
                    ? LumenisTheme.of(context).positive
                    : LumenisTheme.of(context).caution,
              ),
            ),
          ),
          const SizedBox(height: 12),
        ],
        Wrap(
          spacing: 10,
          runSpacing: 10,
          children: [
            FilledButton.icon(
              onPressed: () => onAction('BMP-10.hold-creator', 'creator:hold'),
              icon: const Icon(Icons.pause_circle_outline_rounded),
              label: Text(copy.holdCreator),
            ),
            OutlinedButton.icon(
              onPressed: () =>
                  onAction('BMP-10.draft-response', 'response:draft'),
              icon: const Icon(Icons.edit_note_rounded),
              label: Text(copy.draftResponse),
            ),
          ],
        ),
        if (actionId == 'BMP-10.hold-creator') ...[
          const SizedBox(height: 9),
          Text(
            copy.holdGuard,
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
      label: _Bmp10Copy.of(context).loading,
      child: Padding(
        padding: EdgeInsets.all(48),
        child: CircularProgressIndicator(color: LumenisTheme.of(context).bmp),
      ),
    ),
  );
}

class _Failure extends StatelessWidget {
  const _Failure({required this.kind, required this.onRetry});

  final Bmp10FailureKind kind;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final copy = _Bmp10Copy.of(context);
    final title = switch (kind) {
      Bmp10FailureKind.authentication => copy.signIn,
      Bmp10FailureKind.permissionDenied => copy.accessDenied,
      Bmp10FailureKind.offline => copy.offline,
      Bmp10FailureKind.server => copy.unavailableTitle,
    };
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _Notice(
              icon: Icons.cloud_off_outlined,
              title: title,
              detail: copy.retryDetail,
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

class _Bmp10Copy {
  _Bmp10Copy(this.languageCode);

  final String languageCode;

  static _Bmp10Copy of(BuildContext context) {
    final languageCode = Localizations.localeOf(context).languageCode;
    return _Bmp10Copy(
      languageCode == 'en' || languageCode == 'ko' ? languageCode : 'zh-CN',
    );
  }

  String get subtitle => _get('subtitle');
  String get refresh => _get('refresh');
  String get focus => _get('focus');
  String get globalRange => _get('globalRange');
  String get allBrands => _get('allBrands');
  String get brandUnknown => _get('brandUnknown');
  String get brandOnly => _get('brandOnly');
  String get incidents => _get('incidents');
  String get timeline => _get('timeline');
  String get noEvents => _get('noEvents');
  String get noRiskTitle => _get('noRiskTitle');
  String get noRiskDetail => _get('noRiskDetail');
  String get unavailableTitle => _get('unavailableTitle');
  String get unavailableDetail => _get('unavailableDetail');
  String get notCollectedTitle => _get('notCollectedTitle');
  String get notCollectedDetail => _get('notCollectedDetail');
  String get actionBlocked => _get('actionBlocked');
  String get actionStaged => _get('actionStaged');
  String get holdGuard => _get('holdGuard');
  String get loading => _get('loading');
  String get signIn => _get('signIn');
  String get accessDenied => _get('accessDenied');
  String get offline => _get('offline');
  String get retryDetail => _get('retryDetail');
  String get holdCreator => _get('holdCreator');
  String get draftResponse => _get('draftResponse');

  String severity(String value) => _get('severity.$value');
  String eventState(String value) => _get('event.$value');

  String _get(String key) =>
      _values[languageCode]?[key] ?? _values['zh-CN']![key]!;

  static const _values = <String, Map<String, String>>{
    'zh-CN': {
      'subtitle': '把品牌事件、风险等级、扩散时间与回应路径放在同一条可追踪的处置线上。',
      'refresh': '刷新品牌风险',
      'focus': '当前品牌',
      'globalRange': '全球品牌范围',
      'allBrands': '已授权的全球品牌集合',
      'brandUnknown': '品牌名称暂不可用',
      'brandOnly': '仅当前品牌',
      'incidents': '事件现场',
      'timeline': '回应时间线',
      'noEvents': '当前品牌还没有可确认的回应事件。',
      'noRiskTitle': '当前没有可展示的品牌风险',
      'noRiskDetail': '已确认的品牌事件出现后，这里会按严重程度和时间组织风险，不会把其他领域的事件移入品牌范围。',
      'unavailableTitle': '品牌风险暂不可用',
      'unavailableDetail': '当前品牌范围或风险来源尚未确认，暂不显示其他品牌或其他领域的风险记录。',
      'notCollectedTitle': '还没有品牌风险资料',
      'notCollectedDetail': '风险事件和来源准备好后，这里会显示事件现场、回应负责人和后续状态。',
      'actionBlocked': '当前范围还不能执行这项处置操作；请先确认品牌范围与授权条件。',
      'actionStaged': '本地处置请求草稿已保存；尚未暂停合作或发送回应。',
      'holdGuard': '这里仅保存本地暂停/回应草稿；不会暂停合作或发送回应，直到确认、授权与可回溯结果都准备好。',
      'loading': '正在加载品牌风险',
      'signIn': '当前内容暂时无法打开',
      'accessDenied': '当前内容不可访问',
      'offline': '暂时无法连接品牌风险服务',
      'retryDetail': '可重试读取，或返回后稍后再试。',
      'holdCreator': '保存暂停合作草稿',
      'draftResponse': '保存回应草稿',
      'severity.CRITICAL': '严重',
      'severity.HIGH': '高风险',
      'severity.MEDIUM': '中风险',
      'severity.LOW': '低风险',
      'event.OPEN': '待处置',
      'event.MONITORING': '持续观察',
      'event.RESOLVED': '已复盘',
    },
    'en': {
      'subtitle':
          'Keep brand incidents, severity, spread timing and response steps on one traceable response line.',
      'refresh': 'Refresh brand risk',
      'focus': 'Brand focus',
      'globalRange': 'Global brand range',
      'allBrands': 'Authorized global brand set',
      'brandUnknown': 'Brand name unavailable',
      'brandOnly': 'This brand only',
      'incidents': 'Incident field',
      'timeline': 'Response timeline',
      'noEvents': 'No confirmed response events are available for this brand.',
      'noRiskTitle': 'No brand risk is ready to show',
      'noRiskDetail':
          'Confirmed brand incidents will be organized by severity and time. Events from other domains do not enter this brand view.',
      'unavailableTitle': 'Brand risk is unavailable',
      'unavailableDetail':
          'The current brand range or risk source is not confirmed. Risks from another brand or domain stay hidden.',
      'notCollectedTitle': 'No brand risk material has been collected',
      'notCollectedDetail':
          'Incident and source material will show the incident field, response owner and next state when ready.',
      'actionBlocked':
          'This response action is not available in the current brand range or access state.',
      'actionStaged':
          'Local response-action draft saved. No partnership was paused and no response was sent.',
      'holdGuard':
          'Only a local hold/response draft is saved here; no partnership is paused and no response is sent until confirmation, access, and a traceable result are ready.',
      'loading': 'Loading brand risk',
      'signIn': 'This content cannot be opened right now.',
      'accessDenied': 'This content is not accessible.',
      'offline': 'Brand risk service is unavailable',
      'retryDetail': 'You can retry reading it or return and try again later.',
      'holdCreator': 'Save partnership-hold draft',
      'draftResponse': 'Save response draft',
      'severity.CRITICAL': 'Critical',
      'severity.HIGH': 'High',
      'severity.MEDIUM': 'Medium',
      'severity.LOW': 'Low',
      'event.OPEN': 'Needs response',
      'event.MONITORING': 'Monitoring',
      'event.RESOLVED': 'Reviewed',
    },
    'ko': {
      'subtitle': '브랜드 사건, 심각도, 확산 시점과 대응 단계를 추적 가능한 흐름으로 관리합니다.',
      'refresh': '브랜드 리스크 새로고침',
      'focus': '현재 브랜드',
      'globalRange': '글로벌 브랜드 범위',
      'allBrands': '승인된 글로벌 브랜드 집합',
      'brandUnknown': '브랜드 이름을 사용할 수 없습니다',
      'brandOnly': '현재 브랜드만',
      'incidents': '사건 현장',
      'timeline': '대응 타임라인',
      'noEvents': '이 브랜드에서 확인된 대응 사건이 없습니다.',
      'noRiskTitle': '표시할 브랜드 리스크가 없습니다',
      'noRiskDetail':
          '확인된 브랜드 사건을 심각도와 시간으로 정리합니다. 다른 영역의 사건을 브랜드 화면으로 옮기지 않습니다.',
      'unavailableTitle': '브랜드 리스크를 사용할 수 없습니다',
      'unavailableDetail':
          '현재 브랜드 범위 또는 위험 출처가 확인되지 않았습니다. 다른 브랜드와 영역의 기록은 숨겨집니다.',
      'notCollectedTitle': '아직 브랜드 리스크 자료가 수집되지 않았습니다',
      'notCollectedDetail': '사건과 출처가 준비되면 사건 현장, 대응 담당자와 다음 상태가 표시됩니다.',
      'actionBlocked': '현재 브랜드 범위 또는 접근 상태에서는 이 대응 작업을 사용할 수 없습니다.',
      'actionStaged': '로컬 대응 작업 초안을 저장했습니다. 협력을 중단하거나 응답을 보내지 않았습니다.',
      'holdGuard':
          '여기서는 로컬 보류/응답 초안만 저장합니다. 확인, 접근 권한과 추적 가능한 결과가 준비되기 전에는 협력을 중단하거나 응답을 보내지 않습니다.',
      'loading': '브랜드 리스크를 불러오는 중',
      'signIn': '현재 콘텐츠를 지금 열 수 없습니다.',
      'accessDenied': '현재 콘텐츠에 접근할 수 없습니다.',
      'offline': '브랜드 리스크 서비스에 연결할 수 없습니다',
      'retryDetail': '다시 읽기를 시도하거나 돌아간 뒤 나중에 다시 시도할 수 있습니다.',
      'holdCreator': '협력 보류 초안 저장',
      'draftResponse': '응답 초안 저장',
      'severity.CRITICAL': '심각',
      'severity.HIGH': '높음',
      'severity.MEDIUM': '중간',
      'severity.LOW': '낮음',
      'event.OPEN': '대응 필요',
      'event.MONITORING': '관찰 중',
      'event.RESOLVED': '검토 완료',
    },
  };
}
