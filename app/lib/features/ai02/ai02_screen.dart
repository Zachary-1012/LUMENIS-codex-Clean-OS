import 'package:flutter/material.dart';

import '../../core/lumenis_icon.dart';

import '../../core/lumenis_core_client.dart';
import '../../core/lumenis_theme.dart';
import '../../l10n/lumenis_localizations.dart';
import 'ai02_repository.dart';
import 'ai02_snapshot.dart';
import 'ai02_view_model.dart';

class Ai02Screen extends StatefulWidget {
  const Ai02Screen({
    required this.client,
    this.repository,
    this.onStart,
    super.key,
  });

  final LumenisCoreClient client;
  final Ai02Repository? repository;
  final VoidCallback? onStart;

  @override
  State<Ai02Screen> createState() => _Ai02ScreenState();
}

class _Ai02ScreenState extends State<Ai02Screen> {
  late final Ai02ViewModel _viewModel = Ai02ViewModel(
    repository: widget.repository ?? CoreAi02Repository(client: widget.client),
  );
  final TextEditingController _draftController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _draftController.addListener(
      () => _viewModel.updateDraft(_draftController.text),
    );
    _viewModel.refresh();
  }

  @override
  void dispose() {
    _draftController.dispose();
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
          Ai02LoadPhase.loading => const _LoadingState(),
          Ai02LoadPhase.failed => _FailureState(
            kind: _viewModel.failureKind!,
            onRetry: _viewModel.refresh,
          ),
          Ai02LoadPhase.ready => _ReadyState(
            snapshot: _viewModel.snapshot!,
            viewModel: _viewModel,
            controller: _draftController,
            onStart: widget.onStart,
          ),
        },
      ),
    ),
  );
}

class _ReadyState extends StatelessWidget {
  const _ReadyState({
    required this.snapshot,
    required this.viewModel,
    required this.controller,
    required this.onStart,
  });
  final Ai02Snapshot snapshot;
  final Ai02ViewModel viewModel;
  final TextEditingController controller;
  final VoidCallback? onStart;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, constraints) {
      final wide = constraints.maxWidth >= 1050;
      final inset = constraints.maxWidth < 680 ? 18.0 : 34.0;
      final editor = _TaskEditor(
        snapshot: snapshot,
        viewModel: viewModel,
        controller: controller,
        onStart: onStart,
      );
      final inspector = _ArtifactInspector(snapshot: snapshot);
      return SingleChildScrollView(
        padding: EdgeInsets.fromLTRB(inset, 26, inset, 40),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1380),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _Heading(
                  title: context.lumenisL10n.text('screen.AI-02'),
                  subtitle: _copy(
                    context,
                    zh: '把任务拆成可观察的阶段；每个阶段都要保留真实依据与授权边界。',
                    en: 'Represent a task as observable stages, preserving real evidence and authorization boundaries at every step.',
                    ko: '작업을 관찰 가능한 단계로 표현하고 각 단계의 실제 근거와 권한 경계를 보존합니다.',
                  ),
                ),
                const SizedBox(height: 20),
                _BindingNotice(snapshot: snapshot),
                const SizedBox(height: 16),
                if (wide)
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(flex: 7, child: editor),
                      const SizedBox(width: 18),
                      Expanded(flex: 5, child: inspector),
                    ],
                  )
                else ...[
                  editor,
                  const SizedBox(height: 14),
                  inspector,
                ],
                const SizedBox(height: 14),
                Text(
                  _copy(
                    context,
                    zh: 'AI 输出是派生结果；它不能改写原始资料、业务事实或授权状态。',
                    en: 'AI output is derivative and cannot rewrite source material, business truth, or authorization state.',
                    ko: 'AI 출력은 파생 결과이며 원본 자료, 업무 사실 또는 권한 상태를 바꿀 수 없습니다.',
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

class _TaskEditor extends StatelessWidget {
  const _TaskEditor({
    required this.snapshot,
    required this.viewModel,
    required this.controller,
    required this.onStart,
  });
  final Ai02Snapshot snapshot;
  final Ai02ViewModel viewModel;
  final TextEditingController controller;
  final VoidCallback? onStart;

  @override
  Widget build(BuildContext context) {
    final actionConnected = viewModel.canStart && onStart != null;
    final actionMessage = actionConnected
        ? _copy(
            context,
            zh: '服务器已核验任务入口，宿主可以发起一次受控任务。',
            en: 'The server verified the task entry; the host can start one governed task.',
            ko: '서버가 작업 진입을 확인했으며 호스트가 관리되는 작업을 시작할 수 있습니다.',
          )
        : onStart == null && viewModel.canStart
        ? _copy(
            context,
            zh: '服务器已核验任务入口，但宿主尚未连接实际动作。',
            en: 'The server verified the task entry, but the host has not connected the real action.',
            ko: '서버가 작업 진입을 확인했지만 호스트가 실제 동작을 연결하지 않았습니다.',
          )
        : viewModel.blockedReason;
    return _Panel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  _copy(context, zh: '任务草稿', en: 'Task draft', ko: '작업 초안'),
                  style: Theme.of(context).textTheme.titleMedium,
                ),
              ),
              _Tag(
                label: _copy(
                  context,
                  zh: '不会自动运行',
                  en: 'Does not run automatically',
                  ko: '자동 실행 안 함',
                ),
                color: LumenisTheme.of(context).ai,
              ),
            ],
          ),
          const SizedBox(height: 12),
          TextField(
            controller: controller,
            minLines: 4,
            maxLines: 8,
            maxLength: 4000,
            decoration: InputDecoration(
              hintText: _copy(
                context,
                zh: '描述要完成的任务。',
                en: 'Describe the task to complete.',
                ko: '완료할 작업을 설명하세요.',
              ),
              alignLabelWithHint: true,
              border: const OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 10),
          Text(
            actionMessage,
            style: TextStyle(
              color: LumenisTheme.of(context).caution,
              height: 1.4,
            ),
          ),
          const SizedBox(height: 12),
          Tooltip(
            message: actionMessage,
            child: SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: actionConnected ? onStart : null,
                icon: const LumenisIcon(Icons.play_arrow_rounded),
                label: Text(
                  _copy(context, zh: '开始任务', en: 'Start task', ko: '작업 시작'),
                ),
              ),
            ),
          ),
          if (snapshot.steps.isNotEmpty) ...[
            const SizedBox(height: 22),
            Text(
              _copy(context, zh: '阶段进度', en: 'Stage progress', ko: '단계 진행'),
              style: Theme.of(context).textTheme.titleSmall,
            ),
            const SizedBox(height: 10),
            for (var index = 0; index < snapshot.steps.length; index++) ...[
              _StepRow(
                step: snapshot.steps[index],
                index: index,
                last: index == snapshot.steps.length - 1,
              ),
            ],
          ] else
            const SizedBox(height: 6),
        ],
      ),
    );
  }
}

class _ArtifactInspector extends StatelessWidget {
  const _ArtifactInspector({required this.snapshot});
  final Ai02Snapshot snapshot;

  @override
  Widget build(BuildContext context) => _Panel(
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          _copy(
            context,
            zh: '依据与产出',
            en: 'Evidence & artifacts',
            ko: '근거 및 산출물',
          ),
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: 12),
        if (snapshot.evidenceRefs.isEmpty)
          Text(
            _copy(
              context,
              zh: '当前没有服务器返回的证据锚点。',
              en: 'No evidence anchor was returned by the server.',
              ko: '서버가 반환한 근거 앵커가 없습니다.',
            ),
            style: TextStyle(
              color: LumenisTheme.of(context).muted,
              height: 1.45,
            ),
          )
        else ...[
          Text(
            _copy(
              context,
              zh: '已关联的证据锚点',
              en: 'Returned evidence anchors',
              ko: '반환된 근거 앵커',
            ),
            style: TextStyle(color: LumenisTheme.of(context).quiet),
          ),
          const SizedBox(height: 8),
          for (final ref in snapshot.evidenceRefs) _EvidenceRef(id: ref),
        ],
        const SizedBox(height: 18),
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(13),
          decoration: BoxDecoration(
            color: LumenisTheme.of(context).canvas,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: LumenisTheme.of(context).line),
          ),
          child: Text(
            _copy(
              context,
              zh: '阶段、依据和权限必须由受控任务服务返回；本页不会用本地状态假装任务已暂停、取消或完成。',
              en: 'Stages, evidence, and permissions must come from the governed task service; local state never pretends that a task was paused, cancelled, or completed.',
              ko: '단계, 근거 및 권한은 관리되는 작업 서비스가 반환해야 하며 로컬 상태로 일시 중지·취소·완료를 가장하지 않습니다.',
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

class _StepRow extends StatelessWidget {
  const _StepRow({required this.step, required this.index, required this.last});
  final Ai02TaskStep step;
  final int index;
  final bool last;

  @override
  Widget build(BuildContext context) {
    final visual = switch (step.state) {
      Ai02TaskState.completed => (
        icon: Icons.check_circle_outline,
        color: LumenisTheme.of(context).positive,
        label: _copy(context, zh: '已完成', en: 'Completed', ko: '완료'),
      ),
      Ai02TaskState.running => (
        icon: Icons.play_circle_outline,
        color: LumenisTheme.of(context).ai,
        label: _copy(context, zh: '进行中', en: 'Running', ko: '진행 중'),
      ),
      Ai02TaskState.blocked => (
        icon: Icons.lock_outline,
        color: LumenisTheme.of(context).caution,
        label: _copy(context, zh: '被阻挡', en: 'Blocked', ko: '차단됨'),
      ),
      Ai02TaskState.unavailable => (
        icon: Icons.sync_problem_outlined,
        color: LumenisTheme.of(context).danger,
        label: _copy(context, zh: '暂不可用', en: 'Unavailable', ko: '사용 불가'),
      ),
      Ai02TaskState.pending => (
        icon: Icons.schedule_outlined,
        color: LumenisTheme.of(context).quiet,
        label: _copy(context, zh: '待处理', en: 'Pending', ko: '대기'),
      ),
      Ai02TaskState.unknown => (
        icon: Icons.help_outline,
        color: LumenisTheme.of(context).quiet,
        label: _copy(context, zh: '待确认', en: 'Unconfirmed', ko: '확인 필요'),
      ),
    };
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 28,
          child: Icon(visual.icon, color: visual.color, size: 19),
        ),
        Expanded(child: Text('${index + 1}. ${step.label}')),
        const SizedBox(width: 8),
        Text(visual.label, style: TextStyle(color: visual.color, fontSize: 12)),
        if (!last) const SizedBox(height: 32),
      ],
    );
  }
}

class _EvidenceRef extends StatelessWidget {
  const _EvidenceRef({required this.id});
  final String id;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 7),
    child: Row(
      children: [
        LumenisIcon(Icons.link, size: 16, color: LumenisTheme.of(context).accent),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            id,
            style: TextStyle(color: LumenisTheme.of(context).accent),
          ),
        ),
      ],
    ),
  );
}

class _BindingNotice extends StatelessWidget {
  const _BindingNotice({required this.snapshot});
  final Ai02Snapshot snapshot;

  @override
  Widget build(BuildContext context) {
    final blocked = snapshot.bindingState == Ai02BindingState.blocked;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color:
            (blocked
                    ? LumenisTheme.of(context).caution
                    : LumenisTheme.of(context).quiet)
                .withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color:
              (blocked
                      ? LumenisTheme.of(context).caution
                      : LumenisTheme.of(context).quiet)
                  .withValues(alpha: 0.3),
        ),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            blocked ? Icons.lock_outline : Icons.info_outline,
            color: blocked
                ? LumenisTheme.of(context).caution
                : LumenisTheme.of(context).quiet,
            size: 19,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              blocked
                  ? _copy(
                      context,
                      zh: '任务工作台当前被访问边界阻挡；没有本地替代操作。',
                      en: 'The task workbench is blocked by the access boundary; no local substitute is offered.',
                      ko: '접근 경계로 작업 워크벤치가 차단되어 로컬 대체 작업을 제공하지 않습니다.',
                    )
                  : _copy(
                      context,
                      zh: '任务编排尚未返回可执行的生产绑定；这里不会展示示例阶段。',
                      en: 'Task orchestration has not returned an executable production binding; sample stages are not shown.',
                      ko: '작업 오케스트레이션이 실행 가능한 운영 바인딩을 반환하지 않아 샘플 단계를 표시하지 않습니다.',
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
}

class _Tag extends StatelessWidget {
  const _Tag({required this.label, required this.color});
  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
    decoration: BoxDecoration(
      color: color.withValues(alpha: 0.1),
      borderRadius: BorderRadius.circular(99),
      border: Border.all(color: color.withValues(alpha: 0.32)),
    ),
    child: Text(label, style: TextStyle(color: color, fontSize: 11)),
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
      child: CircularProgressIndicator(color: LumenisTheme.of(context).ai),
    ),
  );
}

class _FailureState extends StatelessWidget {
  const _FailureState({required this.kind, required this.onRetry});
  final Ai02FailureKind kind;
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
              Ai02FailureKind.authentication => _copy(
                context,
                zh: '访问身份未确认',
                en: 'Access identity unconfirmed',
                ko: '접근 신원 확인 안 됨',
              ),
              Ai02FailureKind.permissionDenied => _copy(
                context,
                zh: '任务工作台未获访问确认',
                en: 'Task workbench access not confirmed',
                ko: '작업 워크벤치 접근 확인 안 됨',
              ),
              Ai02FailureKind.offline => _copy(
                context,
                zh: '任务服务暂时离线',
                en: 'Task service is offline',
                ko: '작업 서비스 오프라인',
              ),
              Ai02FailureKind.server => _copy(
                context,
                zh: '任务状态暂不可用',
                en: 'Task state unavailable',
                ko: '작업 상태 사용 불가',
              ),
            }, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 8),
            Text(
              _copy(
                context,
                zh: '没有用本地阶段替代服务器结果。',
                en: 'No local stages were used as a substitute for the server result.',
                ko: '서버 결과를 대신해 로컬 단계를 사용하지 않았습니다.',
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
