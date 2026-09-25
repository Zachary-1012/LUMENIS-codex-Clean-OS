import 'package:flutter/material.dart';

import '../../../core/lumenis_core_client.dart';
import '../../../core/lumenis_theme.dart';
import '../../../l10n/lumenis_localizations.dart';
import 'acc03_repository.dart';
import 'acc03_snapshot.dart';
import 'acc03_view_model.dart';

class Acc03Screen extends StatefulWidget {
  const Acc03Screen({
    required this.client,
    this.repository,
    this.onOpen,
    super.key,
  });

  final LumenisCoreClient client;
  final Acc03Repository? repository;
  final ValueChanged<Acc03Destination>? onOpen;

  @override
  State<Acc03Screen> createState() => _Acc03ScreenState();
}

class _Acc03ScreenState extends State<Acc03Screen> {
  late final Acc03ViewModel _viewModel = Acc03ViewModel(
    repository: widget.repository ?? CoreAcc03Repository(client: widget.client),
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
          Acc03LoadPhase.loading => const _LoadingState(),
          Acc03LoadPhase.failed => _FailureState(
            kind: _viewModel.failureKind!,
            onRetry: _viewModel.refresh,
          ),
          Acc03LoadPhase.ready => _ReadyState(
            snapshot: _viewModel.snapshot!,
            onOpen: widget.onOpen,
          ),
        },
      ),
    ),
  );
}

class _ReadyState extends StatelessWidget {
  const _ReadyState({required this.snapshot, this.onOpen});

  final Acc03Snapshot snapshot;
  final ValueChanged<Acc03Destination>? onOpen;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, constraints) {
      final wide = constraints.maxWidth >= 980;
      final inset = constraints.maxWidth < 680 ? 18.0 : 34.0;
      final launches = _LaunchMap(cards: snapshot.launchCards, onOpen: onOpen);
      final checks = _StartupPanel(snapshot: snapshot);
      return SingleChildScrollView(
        padding: EdgeInsets.fromLTRB(inset, 26, inset, 40),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1280),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _Heading(
                  title: context.lumenisL10n.text('screen.ACC-03'),
                  subtitle: _copy(
                    context,
                    zh: '从一个当前查看范围出发，恢复最近入口或开始一项明确的工作。',
                    en: 'Start from the current view, resume a destination, or begin a named piece of work.',
                    ko: '현재 보기 범위에서 목적지를 다시 열거나 명확한 작업을 시작합니다.',
                  ),
                ),
                const SizedBox(height: 20),
                _CurrentView(snapshot: snapshot),
                const SizedBox(height: 16),
                if (wide)
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(flex: 8, child: launches),
                      const SizedBox(width: 18),
                      Expanded(flex: 4, child: checks),
                    ],
                  )
                else ...[
                  launches,
                  const SizedBox(height: 14),
                  checks,
                ],
                if (onOpen == null) ...[
                  const SizedBox(height: 14),
                  _Notice(
                    icon: Icons.alt_route_rounded,
                    color: LumenisTheme.of(context).quiet,
                    text: _copy(
                      context,
                      zh: '入口卡片只在收到宿主回调后导航；没有回调时不会伪造“已进入”。',
                      en: 'A destination opens only through the host callback; without it, the page never claims that navigation succeeded.',
                      ko: '목적지는 호스트 콜백을 통해서만 열립니다. 콜백이 없으면 이동 성공을 가장하지 않습니다.',
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
      );
    },
  );
}

class _CurrentView extends StatelessWidget {
  const _CurrentView({required this.snapshot});
  final Acc03Snapshot snapshot;

  @override
  Widget build(BuildContext context) => _Panel(
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(
          Icons.place_outlined,
          color: LumenisTheme.of(context).bmp,
          size: 22,
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                _copy(
                  context,
                  zh: '当前查看范围',
                  en: 'Current view',
                  ko: '현재 보기 범위',
                ),
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 4),
              Text(
                snapshot.currentView ??
                    switch (snapshot.contextState) {
                      Acc03RuntimeState.connected => _copy(
                        context,
                        zh: '当前查看范围（未命名）',
                        en: 'Current view (unnamed)',
                        ko: '현재 보기(이름 없음)',
                      ),
                      Acc03RuntimeState.restricted => _copy(
                        context,
                        zh: '查看范围访问受限',
                        en: 'View access is restricted',
                        ko: '보기 범위 접근이 제한됨',
                      ),
                      Acc03RuntimeState.unavailable => _copy(
                        context,
                        zh: '查看范围暂不可用',
                        en: 'View is unavailable',
                        ko: '보기 범위를 사용할 수 없음',
                      ),
                      _ => _copy(
                        context,
                        zh: '查看范围尚未确认',
                        en: 'View is not confirmed',
                        ko: '보기 범위가 확인되지 않음',
                      ),
                    },
                style: TextStyle(color: LumenisTheme.of(context).muted),
              ),
              const SizedBox(height: 5),
              Text(
                _copy(
                  context,
                  zh: '这是查看入口，不会改变资料的业务归属。',
                  en: 'This is a viewing entry and does not change business ownership.',
                  ko: '보기 진입이며 업무 소유권을 바꾸지 않습니다.',
                ),
                style: TextStyle(color: LumenisTheme.of(context).quiet),
              ),
            ],
          ),
        ),
      ],
    ),
  );
}

class _LaunchMap extends StatelessWidget {
  const _LaunchMap({required this.cards, this.onOpen});
  final List<Acc03LaunchCard> cards;
  final ValueChanged<Acc03Destination>? onOpen;

  @override
  Widget build(BuildContext context) => _Panel(
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          _copy(context, zh: '工作入口', en: 'Work destinations', ko: '작업 목적지'),
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: 6),
        Text(
          _copy(
            context,
            zh: '每个入口保留自己的业务工作流，不把它们压成同一张看板。',
            en: 'Each destination keeps its own business workflow rather than becoming one generic dashboard.',
            ko: '각 목적지는 고유한 업무 흐름을 유지하며 하나의 일반 대시보드로 합쳐지지 않습니다.',
          ),
          style: TextStyle(color: LumenisTheme.of(context).muted),
        ),
        const SizedBox(height: 18),
        for (var index = 0; index < cards.length; index++) ...[
          _LaunchRow(card: cards[index], onOpen: onOpen),
          if (index != cards.length - 1) const Divider(height: 24),
        ],
      ],
    ),
  );
}

class _LaunchRow extends StatelessWidget {
  const _LaunchRow({required this.card, this.onOpen});
  final Acc03LaunchCard card;
  final ValueChanged<Acc03Destination>? onOpen;

  @override
  Widget build(BuildContext context) {
    final color = switch (card.destination) {
      Acc03Destination.commerce => LumenisTheme.of(context).cth,
      Acc03Destination.brand => LumenisTheme.of(context).bmp,
      Acc03Destination.ai => LumenisTheme.of(context).ai,
    };
    final title = switch (card.destination) {
      Acc03Destination.commerce => _copy(
        context,
        zh: '商业运营',
        en: 'Commerce operations',
        ko: '커머스 운영',
      ),
      Acc03Destination.brand => _copy(
        context,
        zh: '品牌市场',
        en: 'Brand & market',
        ko: '브랜드 & 마켓',
      ),
      Acc03Destination.ai => _copy(
        context,
        zh: '智能任务',
        en: 'AI tasks',
        ko: 'AI 작업',
      ),
    };
    final description = switch (card.destination) {
      Acc03Destination.commerce => _copy(
        context,
        zh: '以经营主体为起点查看运营信息。',
        en: 'Review operations from an authorized business Subject.',
        ko: '승인된 업무 주체에서 운영 정보를 봅니다.',
      ),
      Acc03Destination.brand => _copy(
        context,
        zh: '以品牌与市场关注范围进入分析。',
        en: 'Enter analysis from a Brand & Market focus.',
        ko: '브랜드 및 마켓 범위에서 분석을 시작합니다.',
      ),
      Acc03Destination.ai => _copy(
        context,
        zh: '先描述任务，再查看可用依据与服务状态。',
        en: 'Describe a task, then inspect available evidence and service state.',
        ko: '작업을 설명한 뒤 사용 가능한 근거와 서비스 상태를 확인합니다.',
      ),
    };
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: 10,
          height: 10,
          margin: const EdgeInsets.only(top: 8),
          decoration: BoxDecoration(color: color, shape: BoxShape.circle),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 4),
              Text(
                description,
                style: TextStyle(
                  color: LumenisTheme.of(context).muted,
                  height: 1.4,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(width: 12),
        OutlinedButton(
          onPressed: onOpen == null ? null : () => onOpen!(card.destination),
          child: Text(context.lumenisL10n.text('acc.continue')),
        ),
      ],
    );
  }
}

class _StartupPanel extends StatelessWidget {
  const _StartupPanel({required this.snapshot});
  final Acc03Snapshot snapshot;

  @override
  Widget build(BuildContext context) => _Panel(
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          _copy(context, zh: '入口检查', en: 'Entry checks', ko: '진입 확인'),
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: 14),
        for (final check in snapshot.startupChecks) ...[
          _CheckRow(check: check),
          const SizedBox(height: 12),
        ],
        const Divider(height: 10),
        const SizedBox(height: 10),
        Text(
          _copy(
            context,
            zh: '检查结果只说明入口状态，不代表业务数据已加载。',
            en: 'These checks describe entry state only; they do not mean business data has loaded.',
            ko: '이 확인은 진입 상태만 설명하며 업무 데이터가 로드되었다는 뜻이 아닙니다.',
          ),
          style: TextStyle(color: LumenisTheme.of(context).quiet, height: 1.45),
        ),
      ],
    ),
  );
}

class _CheckRow extends StatelessWidget {
  const _CheckRow({required this.check});
  final Acc03StartupCheck check;

  @override
  Widget build(BuildContext context) {
    final visual = switch (check.state) {
      Acc03RuntimeState.connected => (
        label: _copy(context, zh: '已确认', en: 'Confirmed', ko: '확인됨'),
        color: LumenisTheme.of(context).positive,
      ),
      Acc03RuntimeState.degraded => (
        label: _copy(context, zh: '部分可用', en: 'Partial', ko: '부분'),
        color: LumenisTheme.of(context).caution,
      ),
      Acc03RuntimeState.unavailable => (
        label: _copy(context, zh: '暂不可用', en: 'Unavailable', ko: '사용 불가'),
        color: LumenisTheme.of(context).danger,
      ),
      Acc03RuntimeState.restricted => (
        label: _copy(context, zh: '访问受限', en: 'Access restricted', ko: '접근 제한'),
        color: LumenisTheme.of(context).caution,
      ),
      Acc03RuntimeState.unknown => (
        label: _copy(context, zh: '待确认', en: 'Unconfirmed', ko: '확인 필요'),
        color: LumenisTheme.of(context).quiet,
      ),
    };
    return Row(
      children: [
        Expanded(child: Text(check.name)),
        Text(visual.label, style: TextStyle(color: visual.color, fontSize: 12)),
      ],
    );
  }
}

class _Notice extends StatelessWidget {
  const _Notice({required this.icon, required this.color, required this.text});
  final IconData icon;
  final Color color;
  final String text;

  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    padding: const EdgeInsets.all(14),
    decoration: BoxDecoration(
      color: color.withValues(alpha: 0.08),
      borderRadius: BorderRadius.circular(14),
      border: Border.all(color: color.withValues(alpha: 0.28)),
    ),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, color: color, size: 19),
        const SizedBox(width: 10),
        Expanded(
          child: Text(
            text,
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

class _Panel extends StatelessWidget {
  const _Panel({required this.child});
  final Widget child;

  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    padding: const EdgeInsets.all(18),
    decoration: BoxDecoration(
      color: LumenisTheme.of(context).surface,
      borderRadius: BorderRadius.circular(16),
      border: Border.all(color: LumenisTheme.of(context).line),
    ),
    child: child,
  );
}

class _Heading extends StatelessWidget {
  const _Heading({required this.title, required this.subtitle});
  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(
        title,
        style: Theme.of(context).textTheme.headlineMedium?.copyWith(
          fontWeight: FontWeight.w600,
          letterSpacing: -0.6,
        ),
      ),
      const SizedBox(height: 8),
      Text(
        subtitle,
        style: TextStyle(color: LumenisTheme.of(context).muted, height: 1.5),
      ),
    ],
  );
}

class _LoadingState extends StatelessWidget {
  const _LoadingState();
  @override
  Widget build(BuildContext context) => Center(
    child: Padding(
      padding: EdgeInsets.all(32),
      child: CircularProgressIndicator(color: LumenisTheme.of(context).accent),
    ),
  );
}

class _FailureState extends StatelessWidget {
  const _FailureState({required this.kind, required this.onRetry});
  final Acc03FailureKind kind;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => Center(
    child: Padding(
      padding: const EdgeInsets.all(24),
      child: _Panel(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(switch (kind) {
              Acc03FailureKind.authentication => _copy(
                context,
                zh: '入口身份未确认',
                en: 'Entry identity unconfirmed',
                ko: '진입 신원 확인 안 됨',
              ),
              Acc03FailureKind.permissionDenied => _copy(
                context,
                zh: '当前入口未获访问确认',
                en: 'Entry access not confirmed',
                ko: '진입 접근 확인 안 됨',
              ),
              Acc03FailureKind.offline => _copy(
                context,
                zh: '工作区暂时离线',
                en: 'Workspace is offline',
                ko: '워크스페이스 오프라인',
              ),
              Acc03FailureKind.server => _copy(
                context,
                zh: '工作区入口暂不可用',
                en: 'Workspace entry unavailable',
                ko: '워크스페이스 진입 사용 불가',
              ),
            }, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 8),
            Text(
              _copy(
                context,
                zh: '没有用静态卡片替代真实入口状态。',
                en: 'Static cards are not used as a substitute for the real entry state.',
                ko: '실제 진입 상태를 대신해 정적 카드를 사용하지 않았습니다.',
              ),
              style: TextStyle(color: LumenisTheme.of(context).muted),
            ),
            const SizedBox(height: 16),
            FilledButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh),
              label: Text(context.lumenisL10n.text('common.refresh')),
            ),
          ],
        ),
      ),
    ),
  );
}

String _copy(
  BuildContext context, {
  required String zh,
  required String en,
  required String ko,
}) => switch (context.lumenisL10n.locale.languageCode) {
  'en' => en,
  'ko' => ko,
  _ => zh,
};
