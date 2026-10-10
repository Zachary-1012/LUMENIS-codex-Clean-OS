import 'package:flutter/material.dart';

import '../../core/lumenis_icon.dart';

import '../../core/lumenis_core_client.dart';
import '../../core/lumenis_theme.dart';
import '../../l10n/lumenis_localizations.dart';
import 'ai03_repository.dart';
import 'ai03_snapshot.dart';
import 'ai03_view_model.dart';

class Ai03Screen extends StatefulWidget {
  const Ai03Screen({required this.client, this.repository, super.key});

  final LumenisCoreClient client;
  final Ai03Repository? repository;

  @override
  State<Ai03Screen> createState() => _Ai03ScreenState();
}

class _Ai03ScreenState extends State<Ai03Screen> {
  late final Ai03ViewModel _viewModel = Ai03ViewModel(
    repository: widget.repository ?? CoreAi03Repository(client: widget.client),
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
          Ai03LoadPhase.loading => const _LoadingState(),
          Ai03LoadPhase.failed => _FailureState(
            kind: _viewModel.failureKind!,
            onRetry: _viewModel.refresh,
          ),
          Ai03LoadPhase.ready => _ReadyState(
            snapshot: _viewModel.snapshot!,
            viewModel: _viewModel,
          ),
        },
      ),
    ),
  );
}

class _ReadyState extends StatelessWidget {
  const _ReadyState({required this.snapshot, required this.viewModel});

  final Ai03Snapshot snapshot;
  final Ai03ViewModel viewModel;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, constraints) {
      final wide = constraints.maxWidth >= 1050;
      final inset = constraints.maxWidth < 680 ? 18.0 : 34.0;
      final thread = _ThreadPanel(snapshot: snapshot, viewModel: viewModel);
      final inspector = _CitationInspector(
        citation: viewModel.selectedCitation,
        hasEvidence: snapshot.hasEvidence,
      );
      return SingleChildScrollView(
        padding: EdgeInsets.fromLTRB(inset, 26, inset, 40),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1380),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _Heading(
                  title: context.lumenisL10n.text('screen.AI-03'),
                  subtitle: _copy(
                    context,
                    zh: '每个结论都要带回可核实的来源；没有来源就保持不确定。',
                    en: 'Return every conclusion to a verifiable source; without one, keep it uncertain.',
                    ko: '모든 결론을 확인 가능한 출처로 되돌리고 출처가 없으면 불확실한 상태로 둡니다.',
                  ),
                ),
                const SizedBox(height: 20),
                _BindingNotice(snapshot: snapshot),
                const SizedBox(height: 16),
                if (wide)
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(flex: 7, child: thread),
                      const SizedBox(width: 18),
                      Expanded(flex: 5, child: inspector),
                    ],
                  )
                else ...[
                  thread,
                  const SizedBox(height: 14),
                  inspector,
                ],
                const SizedBox(height: 14),
                Text(
                  _copy(
                    context,
                    zh: '创建处置或指派责任人需要独立的服务器动作与授权；当前线程不会伪造这些结果。',
                    en: 'Creating a case or assigning an owner requires a separate server action and authorization; this thread never fabricates either result.',
                    ko: '케이스 생성 또는 담당자 지정에는 별도의 서버 작업과 권한이 필요하며 이 스레드는 결과를 가장하지 않습니다.',
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

class _ThreadPanel extends StatelessWidget {
  const _ThreadPanel({required this.snapshot, required this.viewModel});

  final Ai03Snapshot snapshot;
  final Ai03ViewModel viewModel;

  @override
  Widget build(BuildContext context) => _Panel(
    child: snapshot.thread.isEmpty
        ? _EmptyThread(snapshot: snapshot)
        : Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      _copy(
                        context,
                        zh: '分析线程',
                        en: 'Analysis thread',
                        ko: '분석 스레드',
                      ),
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                  ),
                  _Tag(
                    label: _copy(
                      context,
                      zh: '来源优先',
                      en: 'Source first',
                      ko: '출처 우선',
                    ),
                    color: LumenisTheme.of(context).ai,
                  ),
                ],
              ),
              const SizedBox(height: 16),
              for (var index = 0; index < snapshot.thread.length; index++) ...[
                _ThreadEntry(
                  entry: snapshot.thread[index],
                  viewModel: viewModel,
                ),
                if (index != snapshot.thread.length - 1)
                  const Divider(height: 28),
              ],
            ],
          ),
  );
}

class _ThreadEntry extends StatelessWidget {
  const _ThreadEntry({required this.entry, required this.viewModel});

  final Ai03ThreadEntry entry;
  final Ai03ViewModel viewModel;

  @override
  Widget build(BuildContext context) {
    final speaker = switch (entry.speaker) {
      'user' => _copy(context, zh: '你的任务', en: 'Your task', ko: '내 작업'),
      'system' => _copy(
        context,
        zh: '工作区提示',
        en: 'Workspace note',
        ko: '워크스페이스 안내',
      ),
      _ => _copy(context, zh: '分析结果', en: 'Analysis', ko: '분석'),
    };
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          speaker,
          style: TextStyle(
            color: LumenisTheme.of(context).quiet,
            fontSize: 12,
            fontWeight: FontWeight.w700,
          ),
        ),
        const SizedBox(height: 7),
        Text(
          entry.text,
          style: TextStyle(
            color: LumenisTheme.of(context).foreground,
            height: 1.5,
          ),
        ),
        if (entry.citations.isNotEmpty) ...[
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final citation in entry.citations)
                OutlinedButton.icon(
                  onPressed: () => viewModel.selectCitation(citation.id),
                  icon: const LumenisIcon(Icons.link, size: 16),
                  label: Text(citation.id),
                ),
            ],
          ),
        ],
      ],
    );
  }
}

class _CitationInspector extends StatelessWidget {
  const _CitationInspector({required this.citation, required this.hasEvidence});

  final Ai03Citation? citation;
  final bool hasEvidence;

  @override
  Widget build(BuildContext context) => _Panel(
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          _copy(context, zh: '来源检查', en: 'Source inspector', ko: '출처 검사'),
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: 12),
        if (!hasEvidence)
          Text(
            _copy(
              context,
              zh: '当前线程没有服务器返回的证据锚点。',
              en: 'The server returned no evidence anchors for this thread.',
              ko: '서버가 이 스레드의 근거 앵커를 반환하지 않았습니다.',
            ),
            style: TextStyle(
              color: LumenisTheme.of(context).muted,
              height: 1.45,
            ),
          )
        else if (citation == null)
          Text(
            _copy(
              context,
              zh: '选择一条来源以查看其返回的段落。',
              en: 'Select a source to inspect its returned passage.',
              ko: '출처를 선택하여 반환된 구절을 확인하세요.',
            ),
            style: TextStyle(
              color: LumenisTheme.of(context).muted,
              height: 1.45,
            ),
          )
        else ...[
          _InfoRow(
            label: _copy(context, zh: '来源标识', en: 'Source id', ko: '출처 ID'),
            value: citation!.id,
          ),
          if (citation!.title != null)
            _InfoRow(
              label: _copy(
                context,
                zh: '来源名称',
                en: 'Source title',
                ko: '출처 이름',
              ),
              value: citation!.title!,
            ),
          const SizedBox(height: 12),
          Text(
            citation!.passage ??
                _copy(
                  context,
                  zh: '服务器没有返回可定位的段落。',
                  en: 'The server returned no locatable passage.',
                  ko: '서버가 위치를 찾을 수 있는 구절을 반환하지 않았습니다.',
                ),
            style: TextStyle(
              color: LumenisTheme.of(context).muted,
              height: 1.5,
            ),
          ),
        ],
        const SizedBox(height: 18),
        Text(
          _copy(
            context,
            zh: '点击来源只改变本页检查位置，不代表已经打开原始资料。',
            en: 'Selecting a source changes the inspector only; it does not claim that the original material was opened.',
            ko: '출처 선택은 검사 위치만 바꾸며 원본 자료를 열었다고 주장하지 않습니다.',
          ),
          style: TextStyle(color: LumenisTheme.of(context).quiet, height: 1.4),
        ),
      ],
    ),
  );
}

class _EmptyThread extends StatelessWidget {
  const _EmptyThread({required this.snapshot});

  final Ai03Snapshot snapshot;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.all(12),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(
          snapshot.isBound ? Icons.forum_outlined : Icons.sync_problem_outlined,
          color: LumenisTheme.of(context).quiet,
          size: 28,
        ),
        const SizedBox(height: 12),
        Text(
          snapshot.isBound
              ? _copy(
                  context,
                  zh: '当前没有返回分析结论',
                  en: 'No analysis conclusion was returned',
                  ko: '분석 결론이 반환되지 않음',
                )
              : _copy(
                  context,
                  zh: '分析线程尚未接入',
                  en: 'Analysis thread is not bound',
                  ko: '분석 스레드 연결 안 됨',
                ),
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: 7),
        Text(
          _copy(
            context,
            zh: '没有用示例对话或无来源结论填充页面。',
            en: 'Sample dialogue and unsupported conclusions are not used to fill this page.',
            ko: '샘플 대화나 출처 없는 결론으로 페이지를 채우지 않습니다.',
          ),
          style: TextStyle(color: LumenisTheme.of(context).muted, height: 1.45),
        ),
      ],
    ),
  );
}

class _InfoRow extends StatelessWidget {
  const _InfoRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 9),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 88,
          child: Text(
            label,
            style: TextStyle(color: LumenisTheme.of(context).quiet),
          ),
        ),
        Expanded(child: Text(value)),
      ],
    ),
  );
}

class _BindingNotice extends StatelessWidget {
  const _BindingNotice({required this.snapshot});

  final Ai03Snapshot snapshot;

  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    padding: const EdgeInsets.all(14),
    decoration: BoxDecoration(
      color: LumenisTheme.of(context).quiet.withValues(alpha: 0.08),
      borderRadius: BorderRadius.circular(14),
      border: Border.all(
        color: LumenisTheme.of(context).quiet.withValues(alpha: 0.3),
      ),
    ),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        LumenisIcon(
          Icons.info_outline,
          color: LumenisTheme.of(context).quiet,
          size: 19,
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Text(
            snapshot.isBound
                ? _copy(
                    context,
                    zh: '线程数据来自已返回的服务结果；来源详情仍以返回字段为准。',
                    en: 'Thread data comes from the returned service result; source detail is limited to returned fields.',
                    ko: '스레드 데이터는 반환된 서비스 결과에서 오며 출처 상세는 반환 필드로 제한됩니다.',
                  )
                : _copy(
                    context,
                    zh: '当前服务没有绑定分析线程；页面保持空状态，不展示示例结论。',
                    en: 'The service has no bound analysis thread; the page stays empty instead of showing sample conclusions.',
                    ko: '현재 서비스에 분석 스레드가 연결되지 않아 샘플 결론을 표시하지 않습니다.',
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

  final Ai03FailureKind kind;
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
              Ai03FailureKind.authentication => _copy(
                context,
                zh: '访问身份未确认',
                en: 'Access identity unconfirmed',
                ko: '접근 신원 확인 안 됨',
              ),
              Ai03FailureKind.permissionDenied => _copy(
                context,
                zh: '分析线程未获访问确认',
                en: 'Analysis thread access not confirmed',
                ko: '분석 스레드 접근 확인 안 됨',
              ),
              Ai03FailureKind.offline => _copy(
                context,
                zh: '分析服务暂时离线',
                en: 'Analysis service is offline',
                ko: '분석 서비스 오프라인',
              ),
              Ai03FailureKind.server => _copy(
                context,
                zh: '分析线程暂不可用',
                en: 'Analysis thread unavailable',
                ko: '분석 스레드 사용 불가',
              ),
            }, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 8),
            Text(
              _copy(
                context,
                zh: '没有用示例结论替代真实线程。',
                en: 'No sample conclusions were used as a substitute for the real thread.',
                ko: '실제 스레드를 대신해 샘플 결론을 사용하지 않았습니다.',
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
