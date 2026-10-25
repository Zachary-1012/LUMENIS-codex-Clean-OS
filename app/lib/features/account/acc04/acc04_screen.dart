import 'package:flutter/material.dart';

import '../../../core/lumenis_icon.dart';

import '../../../core/lumenis_core_client.dart';
import '../../../core/lumenis_theme.dart';
import '../../../l10n/lumenis_localizations.dart';
import 'acc04_repository.dart';
import 'acc04_snapshot.dart';
import 'acc04_view_model.dart';

class Acc04Screen extends StatefulWidget {
  const Acc04Screen({
    required this.client,
    this.repository,
    this.onSwitchContext,
    this.onReturn,
    super.key,
  });

  final LumenisCoreClient client;
  final Acc04Repository? repository;
  final VoidCallback? onSwitchContext;
  final VoidCallback? onReturn;

  @override
  State<Acc04Screen> createState() => _Acc04ScreenState();
}

class _Acc04ScreenState extends State<Acc04Screen> {
  late final Acc04ViewModel _viewModel = Acc04ViewModel(
    repository: widget.repository ?? CoreAcc04Repository(client: widget.client),
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
          Acc04LoadPhase.loading => const _LoadingState(),
          Acc04LoadPhase.failed => _FailureState(
            kind: _viewModel.failureKind!,
            onRetry: _viewModel.refresh,
          ),
          Acc04LoadPhase.ready => _ReadyState(
            snapshot: _viewModel.snapshot!,
            onSwitchContext: widget.onSwitchContext,
            onReturn: widget.onReturn,
            onRetry: _viewModel.refresh,
          ),
        },
      ),
    ),
  );
}

class _ReadyState extends StatelessWidget {
  const _ReadyState({
    required this.snapshot,
    required this.onSwitchContext,
    required this.onReturn,
    required this.onRetry,
  });

  final Acc04Snapshot snapshot;
  final VoidCallback? onSwitchContext;
  final VoidCallback? onReturn;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, constraints) {
      final inset = constraints.maxWidth < 680
          ? LumenisSpace.control
          : LumenisSpace.gutter;
      final guard = _GuardPanel(snapshot: snapshot);
      final recovery = _RecoveryPanel(
        snapshot: snapshot,
        onSwitchContext: onSwitchContext,
        onReturn: onReturn,
        onRetry: onRetry,
      );
      return SingleChildScrollView(
        padding: EdgeInsets.fromLTRB(inset, 26, inset, 40),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 720),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _Heading(
                  title: context.lumenisL10n.text('screen.ACC-04'),
                  subtitle: _copy(context, zh: '', en: '', ko: ''),
                ),
                const SizedBox(height: 20),
                guard,
                const SizedBox(height: LumenisSpace.section),
                recovery,
              ],
            ),
          ),
        ),
      );
    },
  );
}

class _GuardPanel extends StatelessWidget {
  const _GuardPanel({required this.snapshot});
  final Acc04Snapshot snapshot;

  @override
  Widget build(BuildContext context) {
    final visual = switch (snapshot.guardState) {
      Acc04GuardState.available => (
        title: _copy(
          context,
          zh: '访问状态已更新',
          en: 'Access status updated',
          ko: '접근 상태가 업데이트되었습니다',
        ),
        color: LumenisTheme.of(context).positive,
      ),
      Acc04GuardState.blocked => (
        title: _copy(
          context,
          zh: '当前访问被阻挡',
          en: 'Current access is blocked',
          ko: '현재 접근 차단됨',
        ),
        color: LumenisTheme.of(context).caution,
      ),
      Acc04GuardState.unavailable => (
        title: _copy(
          context,
          zh: '暂时无法恢复',
          en: 'Recovery is unavailable',
          ko: '지금은 복구할 수 없습니다',
        ),
        color: LumenisTheme.of(context).quiet,
      ),
      Acc04GuardState.unknown => (
        title: _copy(
          context,
          zh: '访问状态待确认',
          en: 'Access state unconfirmed',
          ko: '접근 상태 확인 안 됨',
        ),
        color: LumenisTheme.of(context).quiet,
      ),
    };
    return _Panel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              LumenisIcon(Icons.shield_outlined, color: visual.color, size: 24),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  visual.title,
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          Text(
            snapshot.reason ??
                _copy(
                  context,
                  zh: '暂时无法确认访问状态，请重试或返回工作。',
                  en: 'Access could not be confirmed. Retry or return to your work.',
                  ko: '접근 상태를 확인할 수 없습니다. 다시 시도하거나 작업으로 돌아가세요.',
                ),
            style: TextStyle(
              color: LumenisTheme.of(context).muted,
              height: 1.55,
            ),
          ),
        ],
      ),
    );
  }
}

class _RecoveryPanel extends StatelessWidget {
  const _RecoveryPanel({
    required this.snapshot,
    required this.onSwitchContext,
    required this.onReturn,
    required this.onRetry,
  });

  final Acc04Snapshot snapshot;
  final VoidCallback? onSwitchContext;
  final VoidCallback? onReturn;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final paths = snapshot.recoveryPaths;
    return _Panel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            _copy(
              context,
              zh: '可以做什么',
              en: 'Available recovery paths',
              ko: '가능한 복구 경로',
            ),
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 12),
          for (final path in paths) _PathRow(path: path),
          const SizedBox(height: 18),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh),
              label: Text(
                _copy(context, zh: '重新检查', en: 'Check again', ko: '다시 확인'),
              ),
            ),
          ),
          if (onSwitchContext != null) ...[
            const SizedBox(height: 8),
            SizedBox(
              width: double.infinity,
              child: OutlinedButton(
                onPressed: onSwitchContext,
                child: Text(
                  _copy(
                    context,
                    zh: '切换查看范围',
                    en: 'Switch view',
                    ko: '보기 범위 전환',
                  ),
                ),
              ),
            ),
          ],
          if (onReturn != null) ...[
            const SizedBox(height: 8),
            SizedBox(
              width: double.infinity,
              child: TextButton(
                onPressed: onReturn,
                child: Text(context.lumenisL10n.text('common.back')),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _PathRow extends StatelessWidget {
  const _PathRow({required this.path});
  final Acc04RecoveryPath path;

  @override
  Widget build(BuildContext context) {
    final copy = switch (path) {
      Acc04RecoveryPath.recheck => (
        title: _copy(
          context,
          zh: '重新读取当前访问状态',
          en: 'Read the current access state again',
          ko: '현재 접근 상태 다시 읽기',
        ),
        detail: _copy(
          context,
          zh: '只有新的服务器响应才能改变状态。',
          en: 'Only a new server response can change the state.',
          ko: '새 서버 응답만 상태를 바꿀 수 있습니다.',
        ),
      ),
      Acc04RecoveryPath.switchContext => (
        title: _copy(
          context,
          zh: '切换到已确认的查看范围',
          en: 'Switch to a confirmed view',
          ko: '확인된 보기로 전환',
        ),
        detail: _copy(
          context,
          zh: '切换本身不会授予新的权限。',
          en: 'Switching does not grant new access.',
          ko: '전환만으로 새 접근 권한이 부여되지 않습니다.',
        ),
      ),
      Acc04RecoveryPath.requestAccess => (
        title: _copy(
          context,
          zh: '请求真实的访问协助',
          en: 'Request real access assistance',
          ko: '실제 접근 지원 요청',
        ),
        detail: _copy(
          context,
          zh: '当前页面不生成申请，也不伪造批准结果。',
          en: 'This page neither creates a request nor invents approval.',
          ko: '이 페이지는 요청을 만들거나 승인을 가장하지 않습니다.',
        ),
      ),
      Acc04RecoveryPath.returnToWorkspace => (
        title: _copy(
          context,
          zh: '返回工作区',
          en: 'Return to workspace',
          ko: '워크스페이스로 돌아가기',
        ),
        detail: _copy(
          context,
          zh: '由宿主恢复之前的入口状态。',
          en: 'The host restores the previous entry state.',
          ko: '호스트가 이전 진입 상태를 복원합니다.',
        ),
      ),
    };
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          LumenisIcon(
            Icons.arrow_right_rounded,
            color: LumenisTheme.of(context).accent,
            size: 20,
          ),
          const SizedBox(width: 7),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  copy.title,
                  style: const TextStyle(fontWeight: FontWeight.w600),
                ),
                const SizedBox(height: 3),
                Text(
                  copy.detail,
                  style: TextStyle(
                    color: LumenisTheme.of(context).muted,
                    height: 1.4,
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

class _Panel extends StatelessWidget {
  const _Panel({required this.child});
  final Widget child;

  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    padding: const EdgeInsets.all(LumenisSpace.section),
    decoration: LumenisTheme.paper(LumenisTheme.of(context)),
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
      if (subtitle.isNotEmpty) ...[
        const SizedBox(height: 8),
        Text(
          subtitle,
          style: TextStyle(color: LumenisTheme.of(context).muted, height: 1.5),
        ),
      ],
    ],
  );
}

class _LoadingState extends StatelessWidget {
  const _LoadingState();
  @override
  Widget build(BuildContext context) => Center(
    child: Padding(
      padding: EdgeInsets.all(32),
      child: CircularProgressIndicator(color: LumenisTheme.of(context).caution),
    ),
  );
}

class _FailureState extends StatelessWidget {
  const _FailureState({required this.kind, required this.onRetry});
  final Acc04FailureKind kind;
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
              Acc04FailureKind.authentication => _copy(
                context,
                zh: '访问身份未确认',
                en: 'Access identity unconfirmed',
                ko: '접근 신원 확인 안 됨',
              ),
              Acc04FailureKind.permissionDenied => _copy(
                context,
                zh: '当前步骤被拒绝',
                en: 'Current step was denied',
                ko: '현재 단계 거부됨',
              ),
              Acc04FailureKind.offline => _copy(
                context,
                zh: '暂时无法读取恢复状态',
                en: 'Recovery state cannot be read',
                ko: '복구 상태를 읽을 수 없음',
              ),
              Acc04FailureKind.server => _copy(
                context,
                zh: '恢复状态暂不可用',
                en: 'Recovery state unavailable',
                ko: '복구 상태 사용 불가',
              ),
            }, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 8),
            Text(
              _copy(
                context,
                zh: '请重试，或从导航返回工作。',
                en: 'Retry, or return to your work using navigation.',
                ko: '다시 시도하거나 탐색 메뉴에서 작업으로 돌아가세요.',
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
