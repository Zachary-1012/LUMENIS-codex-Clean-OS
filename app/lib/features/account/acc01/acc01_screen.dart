import 'package:flutter/material.dart';

import '../../../core/lumenis_icon.dart';

import '../../../core/lumenis_core_client.dart';
import '../../../core/lumenis_theme.dart';
import '../../../l10n/lumenis_localizations.dart';
import 'acc01_repository.dart';
import 'acc01_snapshot.dart';
import 'acc01_view_model.dart';

class Acc01Screen extends StatefulWidget {
  const Acc01Screen({
    required this.client,
    this.repository,
    this.onContinue,
    super.key,
  });

  final LumenisCoreClient client;
  final Acc01Repository? repository;
  final VoidCallback? onContinue;

  @override
  State<Acc01Screen> createState() => _Acc01ScreenState();
}

class _Acc01ScreenState extends State<Acc01Screen> {
  late final Acc01ViewModel _viewModel = Acc01ViewModel(
    repository: widget.repository ?? CoreAcc01Repository(client: widget.client),
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
            Acc01LoadPhase.loading => const _LoadingState(),
            Acc01LoadPhase.failed => _FailureState(
              kind: _viewModel.failureKind!,
              onRetry: _viewModel.refresh,
            ),
            Acc01LoadPhase.ready => _ReadyState(
              snapshot: _viewModel.snapshot!,
              onContinue: widget.onContinue,
            ),
          },
        ),
      ),
    );
  }
}

class _ReadyState extends StatelessWidget {
  const _ReadyState({required this.snapshot, this.onContinue});

  final Acc01Snapshot snapshot;
  final VoidCallback? onContinue;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final wide = constraints.maxWidth >= 980;
        final inset = constraints.maxWidth < 680 ? 20.0 : 36.0;
        final status = _statusCopy(context, snapshot.runtimeHealth);

        final entry = _Panel(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                _copy(
                  context,
                  zh: '内部 Beta 入口',
                  en: 'Internal beta entry',
                  ko: '내부 베타 진입',
                ),
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 10),
              Text(
                _copy(
                  context,
                  zh: '工作区入口保持可用，不要求先创建新的产品账号。',
                  en: 'The workspace stays usable without creating a new product account first.',
                  ko: '새 제품 계정을 먼저 만들지 않아도 워크스페이스를 사용할 수 있습니다.',
                ),
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: LumenisTheme.of(context).muted,
                ),
              ),
              const SizedBox(height: 22),
              _StatusLine(
                title: _copy(
                  context,
                  zh: '当前入口状态',
                  en: 'Entry status',
                  ko: '진입 상태',
                ),
                value: status.label,
                color: status.color,
              ),
              if (snapshot.focusName != null) ...[
                const SizedBox(height: 12),
                _StatusLine(
                  title: _copy(
                    context,
                    zh: '当前查看范围',
                    en: 'Current view',
                    ko: '현재 보기 범위',
                  ),
                  value: snapshot.focusName!,
                  color: LumenisTheme.of(context).accent,
                ),
              ],
              const SizedBox(height: 22),
              SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  onPressed: onContinue,
                  icon: const LumenisIcon(Icons.arrow_forward_rounded),
                  label: Text(
                    _copy(
                      context,
                      zh: '进入工作区',
                      en: 'Enter workspace',
                      ko: '워크스페이스로 이동',
                    ),
                  ),
                ),
              ),
              if (onContinue == null) ...[
                const SizedBox(height: 9),
                Text(
                  _copy(
                    context,
                    zh: '返回路径由宿主工作区提供。',
                    en: 'The host workspace provides the return path.',
                    ko: '호스트 워크스페이스가 반환 경로를 제공합니다.',
                  ),
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: LumenisTheme.of(context).quiet,
                  ),
                ),
              ],
            ],
          ),
        );

        final boundary = _Panel(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _PanelTitle(
                icon: Icons.shield_outlined,
                title: _copy(
                  context,
                  zh: '产品账号边界',
                  en: 'Product account boundary',
                  ko: '제품 계정 경계',
                ),
              ),
              const SizedBox(height: 12),
              Text(
                _copy(
                  context,
                  zh: '产品账号计划在内部 Beta 之后接入。当前页面只报告已经确认的运行时入口，不把技术连接状态当作客户账号，也不绕过受保护的业务范围。',
                  en: 'The product account is planned after internal beta. This page reports only the confirmed runtime entry; transport access is not a customer account and does not bypass protected business scope.',
                  ko: '제품 계정은 내부 베타 이후에 도입될 예정입니다. 이 페이지는 확인된 런타임 진입만 표시하며 전송 인증을 고객 계정으로 간주하거나 보호된 업무 범위를 우회하지 않습니다.',
                ),
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: LumenisTheme.of(context).muted,
                  height: 1.55,
                ),
              ),
              const SizedBox(height: 18),
              _BoundaryPill(
                label: _copy(
                  context,
                  zh: snapshot.productAccountDeferred
                      ? '产品账号：Beta 后接入'
                      : '产品账号：状态未确认',
                  en: snapshot.productAccountDeferred
                      ? 'Product account: after beta'
                      : 'Product account: unconfirmed',
                  ko: snapshot.productAccountDeferred
                      ? '제품 계정: 베타 이후'
                      : '제품 계정: 확인되지 않음',
                ),
              ),
            ],
          ),
        );

        return SingleChildScrollView(
          padding: EdgeInsets.fromLTRB(inset, 28, inset, 40),
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 1180),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _Heading(
                    title: context.lumenisL10n.text('screen.ACC-01'),
                    subtitle: _copy(
                      context,
                      zh: '先确认入口与运行状态，再进入工作区。',
                      en: 'Confirm the entry and runtime state before entering the workspace.',
                      ko: '워크스페이스에 들어가기 전에 진입 및 런타임 상태를 확인합니다.',
                    ),
                  ),
                  const SizedBox(height: 24),
                  if (wide)
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Expanded(flex: 7, child: entry),
                        const SizedBox(width: 18),
                        Expanded(flex: 5, child: boundary),
                      ],
                    )
                  else ...[
                    entry,
                    const SizedBox(height: 14),
                    boundary,
                  ],
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}

({String label, Color color}) _statusCopy(
  BuildContext context,
  Acc01RuntimeHealth health,
) => switch (health) {
  Acc01RuntimeHealth.healthy => (
    label: _copy(context, zh: '已连接', en: 'Connected', ko: '연결됨'),
    color: LumenisTheme.of(context).positive,
  ),
  Acc01RuntimeHealth.degraded => (
    label: _copy(
      context,
      zh: '部分可用',
      en: 'Partially available',
      ko: '부분 사용 가능',
    ),
    color: LumenisTheme.of(context).caution,
  ),
  Acc01RuntimeHealth.unavailable => (
    label: _copy(context, zh: '暂不可用', en: 'Unavailable', ko: '사용할 수 없음'),
    color: LumenisTheme.of(context).danger,
  ),
  Acc01RuntimeHealth.unknown => (
    label: _copy(context, zh: '状态待确认', en: 'Unconfirmed', ko: '확인되지 않음'),
    color: LumenisTheme.of(context).quiet,
  ),
};

class _Heading extends StatelessWidget {
  const _Heading({required this.title, required this.subtitle});

  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) {
    return Column(
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
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
            color: LumenisTheme.of(context).muted,
          ),
        ),
      ],
    );
  }
}

class _Panel extends StatelessWidget {
  const _Panel({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: LumenisTheme.of(context).surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: LumenisTheme.of(context).line),
      ),
      child: child,
    );
  }
}

class _PanelTitle extends StatelessWidget {
  const _PanelTitle({required this.icon, required this.title});

  final IconData icon;
  final String title;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(icon, color: LumenisTheme.of(context).accent, size: 20),
        const SizedBox(width: 10),
        Text(title, style: Theme.of(context).textTheme.titleMedium),
      ],
    );
  }
}

class _StatusLine extends StatelessWidget {
  const _StatusLine({
    required this.title,
    required this.value,
    required this.color,
  });

  final String title;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(top: 5),
          child: Container(
            width: 8,
            height: 8,
            decoration: BoxDecoration(color: color, shape: BoxShape.circle),
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Text(
            title,
            style: TextStyle(color: LumenisTheme.of(context).muted),
          ),
        ),
        const SizedBox(width: 12),
        Flexible(
          child: Text(
            value,
            textAlign: TextAlign.end,
            style: TextStyle(color: color, fontWeight: FontWeight.w600),
          ),
        ),
      ],
    );
  }
}

class _BoundaryPill extends StatelessWidget {
  const _BoundaryPill({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: LumenisTheme.of(context).accent.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(99),
        border: Border.all(
          color: LumenisTheme.of(context).accent.withValues(alpha: 0.35),
        ),
      ),
      child: Text(
        label,
        style: TextStyle(color: LumenisTheme.of(context).accent),
      ),
    );
  }
}

class _LoadingState extends StatelessWidget {
  const _LoadingState();

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: EdgeInsets.all(32),
        child: CircularProgressIndicator(
          color: LumenisTheme.of(context).accent,
        ),
      ),
    );
  }
}

class _FailureState extends StatelessWidget {
  const _FailureState({required this.kind, required this.onRetry});

  final Acc01FailureKind kind;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final title = switch (kind) {
      Acc01FailureKind.authentication => _copy(
        context,
        zh: '访问身份未确认',
        en: 'Access identity unconfirmed',
        ko: '접근 신원 확인 안 됨',
      ),
      Acc01FailureKind.permissionDenied => _copy(
        context,
        zh: '当前入口暂不可访问',
        en: 'Entry is not available for this access',
        ko: '현재 접근으로 진입할 수 없음',
      ),
      Acc01FailureKind.offline => _copy(
        context,
        zh: '暂时无法连接工作区',
        en: 'Workspace cannot be reached',
        ko: '워크스페이스에 연결할 수 없음',
      ),
      Acc01FailureKind.server => _copy(
        context,
        zh: '暂时无法读取入口状态',
        en: 'Entry status could not be read',
        ko: '진입 상태를 읽을 수 없음',
      ),
    };
    final detail = switch (kind) {
      Acc01FailureKind.authentication => _copy(
        context,
        zh: '没有创建或假设新的产品账号，请返回后重试。',
        en: 'No new product account was created or assumed. Return and try again.',
        ko: '새 제품 계정을 만들거나 가정하지 않았습니다. 돌아가 다시 시도하세요.',
      ),
      Acc01FailureKind.permissionDenied => _copy(
        context,
        zh: '服务器没有确认当前入口的访问范围。',
        en: 'The server did not confirm the access scope for this entry.',
        ko: '서버가 이 진입의 접근 범위를 확인하지 않았습니다.',
      ),
      Acc01FailureKind.offline => _copy(
        context,
        zh: '请检查连接后重新读取入口状态。',
        en: 'Check the connection and read the entry status again.',
        ko: '연결을 확인한 후 진입 상태를 다시 읽으세요.',
      ),
      Acc01FailureKind.server => _copy(
        context,
        zh: '入口状态没有返回可核实结果。',
        en: 'The entry status did not return a verifiable result.',
        ko: '진입 상태에서 확인 가능한 결과가 반환되지 않았습니다.',
      ),
    };
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 540),
          child: _Panel(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: Theme.of(context).textTheme.titleLarge),
                const SizedBox(height: 8),
                Text(
                  detail,
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
      ),
    );
  }
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
