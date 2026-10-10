import 'package:flutter/material.dart';

import '../../core/lumenis_icon.dart';

import '../../core/lumenis_core_client.dart';
import '../../core/lumenis_theme.dart';
import '../../l10n/lumenis_localizations.dart';
import 'ai05_repository.dart';
import 'ai05_snapshot.dart';
import 'ai05_view_model.dart';

class Ai05Screen extends StatefulWidget {
  const Ai05Screen({required this.client, this.repository, super.key});

  final LumenisCoreClient client;
  final Ai05Repository? repository;

  @override
  State<Ai05Screen> createState() => _Ai05ScreenState();
}

class _Ai05ScreenState extends State<Ai05Screen> {
  late final Ai05ViewModel _viewModel = Ai05ViewModel(
    repository: widget.repository ?? CoreAi05Repository(client: widget.client),
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
          Ai05LoadPhase.loading => const _LoadingState(),
          Ai05LoadPhase.failed => _FailureState(
            kind: _viewModel.failureKind!,
            onRetry: _viewModel.refresh,
          ),
          Ai05LoadPhase.ready => _ReadyState(snapshot: _viewModel.snapshot!),
        },
      ),
    ),
  );
}

class _ReadyState extends StatelessWidget {
  const _ReadyState({required this.snapshot});
  final Ai05Snapshot snapshot;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, constraints) {
      final wide = constraints.maxWidth >= 980;
      final inset = constraints.maxWidth < 680 ? 18.0 : 34.0;
      final providers = _ProviderPanel(providers: snapshot.providers);
      final observations = _ObservationPanel(series: snapshot.callSeries);
      return SingleChildScrollView(
        padding: EdgeInsets.fromLTRB(inset, 26, inset, 40),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1280),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _Heading(
                  title: context.lumenisL10n.text('screen.AI-05'),
                  subtitle: _copy(
                    context,
                    zh: '这是服务诊断页：显示可核实的能力状态，不把模型细节放进主要业务工作流。',
                    en: 'This is a service diagnostic surface: show verifiable capability state without putting model detail in the primary business workflow.',
                    ko: '서비스 진단 화면입니다. 확인 가능한 역량 상태만 표시하고 모델 상세를 주요 업무 흐름에 넣지 않습니다.',
                  ),
                ),
                const SizedBox(height: 20),
                _BindingNotice(snapshot: snapshot),
                const SizedBox(height: 16),
                if (wide)
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(flex: 7, child: providers),
                      const SizedBox(width: 18),
                      Expanded(flex: 5, child: observations),
                    ],
                  )
                else ...[
                  providers,
                  const SizedBox(height: 14),
                  observations,
                ],
                const SizedBox(height: 14),
                Text(
                  _copy(
                    context,
                    zh: '服务降级或不可用时，核心业务读取不会被诊断页伪造为成功。',
                    en: 'When a service is degraded or unavailable, this diagnostic page never presents core business reads as successful.',
                    ko: '서비스가 저하되거나 사용할 수 없을 때 이 진단 화면은 핵심 업무 읽기를 성공으로 가장하지 않습니다.',
                  ),
                  style: TextStyle(
                    color: LumenisTheme.of(context).quiet,
                    height: 1.45,
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

class _BindingNotice extends StatelessWidget {
  const _BindingNotice({required this.snapshot});
  final Ai05Snapshot snapshot;

  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    padding: const EdgeInsets.all(14),
    decoration: BoxDecoration(
      color:
          (snapshot.bindingState == Ai05BindingState.fallbackDiagnostic
                  ? LumenisTheme.of(context).caution
                  : LumenisTheme.of(context).system)
              .withValues(alpha: 0.08),
      borderRadius: BorderRadius.circular(14),
      border: Border.all(
        color:
            (snapshot.bindingState == Ai05BindingState.fallbackDiagnostic
                    ? LumenisTheme.of(context).caution
                    : LumenisTheme.of(context).system)
                .withValues(alpha: 0.3),
      ),
    ),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(
          snapshot.bindingState == Ai05BindingState.fallbackDiagnostic
              ? Icons.alt_route_rounded
              : Icons.monitor_heart_outlined,
          color: snapshot.bindingState == Ai05BindingState.fallbackDiagnostic
              ? LumenisTheme.of(context).caution
              : LumenisTheme.of(context).system,
          size: 20,
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Text(
            snapshot.bindingState == Ai05BindingState.fallbackDiagnostic
                ? _copy(
                    context,
                    zh: 'AI-05 尚未独立绑定；以下是现有运行状态检查返回的诊断信息，不能当作 AI-05 独立能力已完成。',
                    en: 'AI-05 is not independently bound; the diagnostic below comes from the existing runtime check and does not mean AI-05 is complete.',
                    ko: 'AI-05는 아직 독립적으로 연결되지 않았습니다. 아래 진단은 기존 런타임 확인에서 오며 AI-05가 완료되었다는 뜻이 아닙니다.',
                  )
                : _copy(
                    context,
                    zh: '状态来自实际服务返回；未返回的延迟、模型或调用链细节不会被补齐。',
                    en: 'State comes from the real service response; missing latency, model, or call-chain detail is not filled in.',
                    ko: '상태는 실제 서비스 응답에서 오며 반환되지 않은 지연·모델·호출 체인 상세는 채우지 않습니다.',
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

class _ProviderPanel extends StatelessWidget {
  const _ProviderPanel({required this.providers});
  final List<Ai05ProviderStatus> providers;

  @override
  Widget build(BuildContext context) => _Panel(
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          _copy(
            context,
            zh: '服务能力状态',
            en: 'Service capability state',
            ko: '서비스 역량 상태',
          ),
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: 8),
        Text(
          _copy(
            context,
            zh: '名称已按产品安全规则归一化；详情只用于诊断，不会改变业务上下文。',
            en: 'Names are normalized for product safety; this diagnostic detail does not change business context.',
            ko: '이름은 제품 안전 규칙에 따라 정규화되며 진단 상세는 업무 컨텍스트를 바꾸지 않습니다.',
          ),
          style: TextStyle(color: LumenisTheme.of(context).muted, height: 1.4),
        ),
        const SizedBox(height: 14),
        if (providers.isEmpty)
          _EmptyState(
            title: _copy(
              context,
              zh: '没有返回服务状态',
              en: 'No service state returned',
              ko: '서비스 상태가 반환되지 않음',
            ),
            detail: _copy(
              context,
              zh: '当前不能推断任何模型或服务可用。',
              en: 'No model or service availability is inferred.',
              ko: '모델 또는 서비스 사용 가능 여부를 추론하지 않습니다.',
            ),
          )
        else
          for (var index = 0; index < providers.length; index++) ...[
            _ProviderRow(provider: providers[index]),
            if (index != providers.length - 1) const Divider(height: 22),
          ],
      ],
    ),
  );
}

class _ProviderRow extends StatelessWidget {
  const _ProviderRow({required this.provider});
  final Ai05ProviderStatus provider;

  @override
  Widget build(BuildContext context) {
    final visual = switch (provider.state) {
      Ai05ProviderState.available => (
        label: _copy(context, zh: '可用', en: 'Available', ko: '사용 가능'),
        color: LumenisTheme.of(context).positive,
      ),
      Ai05ProviderState.notReady => (
        label: _copy(context, zh: '未就绪', en: 'Not ready', ko: '준비되지 않음'),
        color: LumenisTheme.of(context).caution,
      ),
      Ai05ProviderState.unavailable => (
        label: _copy(context, zh: '暂不可用', en: 'Unavailable', ko: '사용 불가'),
        color: LumenisTheme.of(context).danger,
      ),
      Ai05ProviderState.unknown => (
        label: _copy(context, zh: '待确认', en: 'Unconfirmed', ko: '확인 필요'),
        color: LumenisTheme.of(context).quiet,
      ),
    };
    final name = switch (provider.kind) {
      Ai05ProviderKind.local => _copy(
        context,
        zh: '本地模型服务',
        en: 'Local model service',
        ko: '로컬 모델 서비스',
      ),
      Ai05ProviderKind.optional => _copy(
        context,
        zh: '可选模型服务',
        en: 'Optional model service',
        ko: '선택형 모델 서비스',
      ),
      Ai05ProviderKind.generic => _copy(
        context,
        zh: 'AI 模型服务',
        en: 'AI model service',
        ko: 'AI 모델 서비스',
      ),
    };
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(top: 5),
          child: Container(
            width: 8,
            height: 8,
            decoration: BoxDecoration(
              color: visual.color,
              shape: BoxShape.circle,
            ),
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Text(name, style: Theme.of(context).textTheme.bodyMedium),
        ),
        const SizedBox(width: 12),
        Column(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Text(
              visual.label,
              style: TextStyle(color: visual.color, fontSize: 12),
            ),
            if (provider.latencyMs != null)
              Text(
                '${provider.latencyMs} ms',
                style: TextStyle(
                  color: LumenisTheme.of(context).quiet,
                  fontSize: 11,
                ),
              ),
          ],
        ),
      ],
    );
  }
}

class _ObservationPanel extends StatelessWidget {
  const _ObservationPanel({required this.series});
  final List<num> series;

  @override
  Widget build(BuildContext context) => _Panel(
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          _copy(context, zh: '调用观测', en: 'Call observations', ko: '호출 관측'),
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: 12),
        if (series.isEmpty)
          _EmptyState(
            title: _copy(
              context,
              zh: '没有返回调用序列',
              en: 'No call series returned',
              ko: '호출 시퀀스가 반환되지 않음',
            ),
            detail: _copy(
              context,
              zh: '不根据单次状态推断趋势、延迟或稳定性。',
              en: 'No trend, latency, or stability is inferred from a single state.',
              ko: '단일 상태에서 추세·지연·안정성을 추론하지 않습니다.',
            ),
          )
        else ...[
          Text(
            _copy(
                  context,
                  zh: '服务端返回了 ',
                  en: 'The server returned ',
                  ko: '서버가 반환한 관측점: ',
                ) +
                series.length.toString() +
                _copy(
                  context,
                  zh: ' 个观测点。',
                  en: ' observation point(s).',
                  ko: '개.',
                ),
            style: TextStyle(
              color: LumenisTheme.of(context).muted,
              height: 1.45,
            ),
          ),
          const SizedBox(height: 14),
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: [
              for (final value in series.take(24))
                Container(
                  width: 20,
                  height: (8 + (value.clamp(0, 100) / 100 * 34)).toDouble(),
                  decoration: BoxDecoration(
                    color: LumenisTheme.of(
                      context,
                    ).system.withValues(alpha: 0.45),
                    borderRadius: BorderRadius.circular(3),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            _copy(
              context,
              zh: '仅显示已返回的观测序列，不补充时间窗口或单位。',
              en: 'Only returned observations are shown; no time window or unit is invented.',
              ko: '반환된 관측만 표시하며 시간 범위나 단위를 추가하지 않습니다.',
            ),
            style: TextStyle(
              color: LumenisTheme.of(context).quiet,
              height: 1.4,
            ),
          ),
        ],
      ],
    ),
  );
}

class _EmptyState extends StatelessWidget {
  const _EmptyState({required this.title, required this.detail});
  final String title;
  final String detail;
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 16),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        LumenisIcon(
          Icons.data_exploration_outlined,
          color: LumenisTheme.of(context).quiet,
          size: 27,
        ),
        const SizedBox(height: 10),
        Text(title, style: Theme.of(context).textTheme.titleSmall),
        const SizedBox(height: 5),
        Text(
          detail,
          style: TextStyle(color: LumenisTheme.of(context).muted, height: 1.4),
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
      child: CircularProgressIndicator(color: LumenisTheme.of(context).system),
    ),
  );
}

class _FailureState extends StatelessWidget {
  const _FailureState({required this.kind, required this.onRetry});
  final Ai05FailureKind kind;
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
              Ai05FailureKind.authentication => _copy(
                context,
                zh: '访问身份未确认',
                en: 'Access identity unconfirmed',
                ko: '접근 신원 확인 안 됨',
              ),
              Ai05FailureKind.permissionDenied => _copy(
                context,
                zh: '诊断状态未获访问确认',
                en: 'Diagnostic access not confirmed',
                ko: '진단 접근 확인 안 됨',
              ),
              Ai05FailureKind.offline => _copy(
                context,
                zh: '诊断服务暂时离线',
                en: 'Diagnostic service is offline',
                ko: '진단 서비스 오프라인',
              ),
              Ai05FailureKind.server => _copy(
                context,
                zh: '诊断状态暂不可用',
                en: 'Diagnostic state unavailable',
                ko: '진단 상태 사용 불가',
              ),
            }, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 8),
            Text(
              _copy(
                context,
                zh: '没有根据失败响应推断服务可用。',
                en: 'Service availability is not inferred from a failed response.',
                ko: '실패한 응답에서 서비스 사용 가능 여부를 추론하지 않습니다.',
              ),
              style: TextStyle(color: LumenisTheme.of(context).muted),
            ),
            const SizedBox(height: 16),
            FilledButton.icon(
              onPressed: onRetry,
              icon: const LumenisIcon(Icons.refresh),
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
