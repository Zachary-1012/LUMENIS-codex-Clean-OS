import 'package:flutter/material.dart';

import '../../core/lumenis_icon.dart';

import '../../core/lumenis_core_client.dart';
import '../../core/lumenis_theme.dart';
import '../../l10n/lumenis_localizations.dart';
import 'ai04_repository.dart';
import 'ai04_snapshot.dart';
import 'ai04_view_model.dart';

class Ai04Screen extends StatefulWidget {
  const Ai04Screen({
    required this.client,
    this.repository,
    this.onRun,
    super.key,
  });

  final LumenisCoreClient client;
  final Ai04Repository? repository;
  final ValueChanged<Ai04SkillCapability>? onRun;

  @override
  State<Ai04Screen> createState() => _Ai04ScreenState();
}

class _Ai04ScreenState extends State<Ai04Screen> {
  late final Ai04ViewModel _viewModel = Ai04ViewModel(
    repository: widget.repository ?? CoreAi04Repository(client: widget.client),
  );
  final TextEditingController _filterController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _filterController.addListener(
      () => _viewModel.updateFilter(_filterController.text),
    );
    _viewModel.refresh();
  }

  @override
  void dispose() {
    _filterController.dispose();
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
          Ai04LoadPhase.loading => const _LoadingState(),
          Ai04LoadPhase.failed => _FailureState(
            kind: _viewModel.failureKind!,
            onRetry: _viewModel.refresh,
          ),
          Ai04LoadPhase.ready => _ReadyState(
            snapshot: _viewModel.snapshot!,
            viewModel: _viewModel,
            filterController: _filterController,
            onRun: widget.onRun,
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
    required this.filterController,
    required this.onRun,
  });

  final Ai04Snapshot snapshot;
  final Ai04ViewModel viewModel;
  final TextEditingController filterController;
  final ValueChanged<Ai04SkillCapability>? onRun;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, constraints) {
      final wide = constraints.maxWidth >= 1080;
      final inset = constraints.maxWidth < 680 ? 18.0 : 34.0;
      final skills = viewModel.filteredSkills;
      final selected =
          viewModel.selectedSkill ?? (skills.isNotEmpty ? skills.first : null);
      final list = _CatalogList(
        skills: skills,
        selectedId: selected?.skillId,
        filterController: filterController,
        rejectedCount: snapshot.rejectedCount,
        bounded: wide,
        onSelect: viewModel.selectSkill,
      );
      final detail = _SkillDetail(skill: selected, onRun: onRun);
      return SingleChildScrollView(
        padding: EdgeInsets.fromLTRB(inset, 26, inset, 40),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1440),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _Heading(
                  title: context.lumenisL10n.text('screen.AI-04'),
                  subtitle: _copy(
                    context,
                    zh: '只展示已登记、已版本化并通过绑定核验的能力；目录不是安装或审批入口。',
                    en: 'Show only registered, versioned, and binding-verified capabilities; this catalog is not an install or approval surface.',
                    ko: '등록·버전 관리·바인딩 검증을 통과한 역량만 표시하며 이 카탈로그는 설치나 승인 화면이 아닙니다.',
                  ),
                ),
                const SizedBox(height: 20),
                _CatalogNotice(snapshot: snapshot),
                const SizedBox(height: 16),
                if (wide)
                  SizedBox(
                    height: 650,
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Expanded(flex: 7, child: list),
                        const SizedBox(width: 18),
                        Expanded(flex: 5, child: detail),
                      ],
                    ),
                  )
                else ...[
                  list,
                  const SizedBox(height: 14),
                  detail,
                ],
              ],
            ),
          ),
        ),
      );
    },
  );
}

class _CatalogNotice extends StatelessWidget {
  const _CatalogNotice({required this.snapshot});
  final Ai04Snapshot snapshot;

  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    padding: const EdgeInsets.all(14),
    decoration: BoxDecoration(
      color: LumenisTheme.of(context).shared.withValues(alpha: 0.08),
      borderRadius: BorderRadius.circular(14),
      border: Border.all(
        color: LumenisTheme.of(context).shared.withValues(alpha: 0.3),
      ),
    ),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        LumenisIcon(
          Icons.verified_outlined,
          color: LumenisTheme.of(context).shared,
          size: 20,
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Text(
            snapshot.state == Ai04CatalogState.empty
                ? _copy(
                    context,
                    zh: '当前没有返回可核验的技能条目；未核验内容不会降级为“可用”。',
                    en: 'No verifiable skill entry was returned; unverified content is not downgraded to “available”.',
                    ko: '확인 가능한 스킬 항목이 반환되지 않았으며 검증되지 않은 항목을 사용 가능으로 표시하지 않습니다.',
                  )
                : _copy(
                    context,
                    zh: '目录只读。能力的输入、输出、风险和所需范围来自服务端登记；启用、更新、停用和推广仍走原有注册与审批边界。',
                    en: 'The catalog is read-only. Input, output, risk, and required scope come from the server registry; enable, update, disable, and promotion stay behind the existing registry and approval boundary.',
                    ko: '카탈로그는 읽기 전용입니다. 입력·출력·위험·필요 범위는 서버 등록에서 오며 활성화·업데이트·비활성화·승격은 기존 등록 및 승인 경계를 따릅니다.',
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

class _CatalogList extends StatelessWidget {
  const _CatalogList({
    required this.skills,
    required this.selectedId,
    required this.filterController,
    required this.rejectedCount,
    required this.bounded,
    required this.onSelect,
  });

  final List<Ai04SkillCapability> skills;
  final String? selectedId;
  final TextEditingController filterController;
  final int rejectedCount;
  final bool bounded;
  final ValueChanged<Ai04SkillCapability> onSelect;

  @override
  Widget build(BuildContext context) {
    final body = skills.isEmpty
        ? _EmptyState(
            title: _copy(
              context,
              zh: '没有匹配的已核验能力',
              en: 'No verified capability matches',
              ko: '일치하는 검증된 역량 없음',
            ),
            detail: _copy(
              context,
              zh: '清除筛选或等待服务端返回新的登记结果。',
              en: 'Clear the filter or wait for a new registry result.',
              ko: '필터를 지우거나 새 등록 결과를 기다리세요.',
            ),
          )
        : ListView.separated(
            shrinkWrap: !bounded,
            physics: bounded ? null : const NeverScrollableScrollPhysics(),
            itemCount: skills.length,
            separatorBuilder: (_, _) => const Divider(height: 1),
            itemBuilder: (context, index) {
              final skill = skills[index];
              final selected = skill.skillId == selectedId;
              return Material(
                color: Colors.transparent,
                child: ListTile(
                  selected: selected,
                  selectedTileColor: LumenisTheme.of(
                    context,
                  ).shared.withValues(alpha: 0.09),
                  contentPadding: const EdgeInsets.symmetric(horizontal: 4),
                  leading: Icon(
                    selected
                        ? Icons.radio_button_checked
                        : Icons.radio_button_off,
                    color: selected
                        ? LumenisTheme.of(context).shared
                        : LumenisTheme.of(context).quiet,
                  ),
                  title: Text(skill.name),
                  subtitle: Text(
                    '${skill.category} · ${skill.version}',
                    style: TextStyle(color: LumenisTheme.of(context).quiet),
                  ),
                  onTap: () => onSelect(skill),
                ),
              );
            },
          );
    return _Panel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  _copy(
                    context,
                    zh: '已核验能力',
                    en: 'Verified capabilities',
                    ko: '검증된 역량',
                  ),
                  style: Theme.of(context).textTheme.titleMedium,
                ),
              ),
              Text(
                skills.length.toString(),
                style: TextStyle(color: LumenisTheme.of(context).quiet),
              ),
            ],
          ),
          const SizedBox(height: 12),
          TextField(
            controller: filterController,
            textInputAction: TextInputAction.search,
            decoration: InputDecoration(
              prefixIcon: const LumenisIcon(Icons.search),
              hintText: _copy(
                context,
                zh: '按名称、用途或类别搜索',
                en: 'Search by name, use, or category',
                ko: '이름·용도·카테고리 검색',
              ),
              border: const OutlineInputBorder(),
            ),
          ),
          if (rejectedCount > 0) ...[
            const SizedBox(height: 9),
            Text(
              _copy(
                context,
                zh: '另有 $rejectedCount 条记录未通过核验，已隐藏。',
                en: '$rejectedCount record(s) failed verification and are hidden.',
                ko: '$rejectedCount개 항목은 검증에 실패하여 숨겨졌습니다.',
              ),
              style: TextStyle(
                color: LumenisTheme.of(context).quiet,
                fontSize: 12,
              ),
            ),
          ],
          const SizedBox(height: 12),
          bounded ? Expanded(child: body) : SizedBox(height: 360, child: body),
        ],
      ),
    );
  }
}

class _SkillDetail extends StatelessWidget {
  const _SkillDetail({required this.skill, required this.onRun});

  final Ai04SkillCapability? skill;
  final ValueChanged<Ai04SkillCapability>? onRun;

  @override
  Widget build(BuildContext context) {
    if (skill == null) {
      return _Panel(
        child: _EmptyState(
          title: _copy(
            context,
            zh: '选择一个能力',
            en: 'Select a capability',
            ko: '역량을 선택하세요',
          ),
          detail: _copy(
            context,
            zh: '详情只来自已核验的服务端登记。',
            en: 'Details come only from the verified server registry.',
            ko: '상세 정보는 검증된 서버 등록에서만 옵니다.',
          ),
        ),
      );
    }
    final item = skill!;
    return _Panel(
      child: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Text(
                    item.name,
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                ),
                _Tag(
                  label: item.canRunReadOnly
                      ? _copy(
                          context,
                          zh: '可受控运行',
                          en: 'Run verified',
                          ko: '실행 확인됨',
                        )
                      : _copy(
                          context,
                          zh: '仅登记',
                          en: 'Catalog only',
                          ko: '카탈로그 전용',
                        ),
                  color: item.canRunReadOnly
                      ? LumenisTheme.of(context).positive
                      : LumenisTheme.of(context).quiet,
                ),
              ],
            ),
            const SizedBox(height: 9),
            Text(
              item.description,
              style: TextStyle(
                color: LumenisTheme.of(context).muted,
                height: 1.45,
              ),
            ),
            const SizedBox(height: 18),
            _DetailRow(
              label: _copy(context, zh: '版本', en: 'Version', ko: '버전'),
              value: item.version,
            ),
            _DetailRow(
              label: _copy(context, zh: '归属', en: 'Owner', ko: '소유자'),
              value: item.owner,
            ),
            _DetailRow(
              label: _copy(context, zh: '适用产品', en: 'Consumers', ko: '사용 제품'),
              value: item.consumers.isEmpty
                  ? _copy(
                      context,
                      zh: '以服务端范围为准',
                      en: 'Server-defined scope',
                      ko: '서버 범위 기준',
                    )
                  : item.consumers.join(' · '),
            ),
            _DetailRow(
              label: _copy(
                context,
                zh: '所需能力',
                en: 'Permission level',
                ko: '필요 역량',
              ),
              value: _permissionLabel(context, item.permissionLevel),
            ),
            _DetailRow(
              label: _copy(context, zh: '风险', en: 'Risk', ko: '위험'),
              value: _riskLabel(context, item.riskLevel),
            ),
            _DetailRow(
              label: _copy(context, zh: '执行方式', en: 'Execution', ko: '실행 방식'),
              value: _policyLabel(context, item.executionPolicy),
            ),
            const SizedBox(height: 18),
            _HintBlock(
              title: _copy(context, zh: '输入', en: 'Input', ko: '입력'),
              text: item.inputHint,
            ),
            const SizedBox(height: 10),
            _HintBlock(
              title: _copy(context, zh: '输出', en: 'Output', ko: '출력'),
              text: item.outputHint,
            ),
            const SizedBox(height: 18),
            if (item.isReadOnly)
              SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  onPressed: item.canRunReadOnly && onRun != null
                      ? () => onRun!(item)
                      : null,
                  icon: const LumenisIcon(Icons.play_arrow_rounded),
                  label: Text(
                    _copy(
                      context,
                      zh: '运行只读能力',
                      en: 'Run read-only capability',
                      ko: '읽기 전용 역량 실행',
                    ),
                  ),
                ),
              )
            else
              _Notice(
                icon: Icons.lock_outline,
                color: LumenisTheme.of(context).caution,
                text: _copy(
                  context,
                  zh: '该能力需要审批或更高授权；目录页不执行。',
                  en: 'This capability requires approval or stronger authorization; the catalog does not execute it.',
                  ko: '이 역량은 승인 또는 더 높은 권한이 필요하며 카탈로그에서 실행하지 않습니다.',
                ),
              ),
            if (item.isReadOnly && !item.canRunReadOnly)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(
                  _copy(
                    context,
                    zh: '当前条目缺少版本化评估记录或当前操作人访问许可，暂不运行。',
                    en: 'This entry lacks a versioned evaluation record or current actor access; it cannot run yet.',
                    ko: '버전이 지정된 평가 기록 또는 현재 작업자 접근 권한이 없어 아직 실행할 수 없습니다.',
                  ),
                  style: TextStyle(
                    color: LumenisTheme.of(context).caution,
                    height: 1.4,
                  ),
                ),
              ),
            const SizedBox(height: 12),
            Text(
              _copy(
                context,
                zh: '安装、启用、更新、停用和推广不在此页面完成。',
                en: 'Install, enable, update, disable, and promotion do not happen on this page.',
                ko: '설치·활성화·업데이트·비활성화·승격은 이 페이지에서 수행되지 않습니다.',
              ),
              style: TextStyle(
                color: LumenisTheme.of(context).quiet,
                height: 1.4,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _DetailRow extends StatelessWidget {
  const _DetailRow({required this.label, required this.value});
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 9),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 105,
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

class _HintBlock extends StatelessWidget {
  const _HintBlock({required this.title, required this.text});
  final String title;
  final String text;

  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    padding: const EdgeInsets.all(12),
    decoration: BoxDecoration(
      color: LumenisTheme.of(context).canvas,
      borderRadius: BorderRadius.circular(12),
      border: Border.all(color: LumenisTheme.of(context).line),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: TextStyle(color: LumenisTheme.of(context).quiet, fontSize: 12),
        ),
        const SizedBox(height: 5),
        Text(
          text,
          style: TextStyle(color: LumenisTheme.of(context).muted, height: 1.4),
        ),
      ],
    ),
  );
}

class _Notice extends StatelessWidget {
  const _Notice({required this.icon, required this.color, required this.text});
  final IconData icon;
  final Color color;
  final String text;

  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    padding: const EdgeInsets.all(13),
    decoration: BoxDecoration(
      color: color.withValues(alpha: 0.08),
      borderRadius: BorderRadius.circular(12),
      border: Border.all(color: color.withValues(alpha: 0.28)),
    ),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, color: color, size: 19),
        const SizedBox(width: 9),
        Expanded(
          child: Text(
            text,
            style: TextStyle(
              color: LumenisTheme.of(context).muted,
              height: 1.4,
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

class _EmptyState extends StatelessWidget {
  const _EmptyState({required this.title, required this.detail});
  final String title;
  final String detail;
  @override
  Widget build(BuildContext context) => Center(
    child: Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          LumenisIcon(
            Icons.inventory_2_outlined,
            color: LumenisTheme.of(context).quiet,
            size: 28,
          ),
          const SizedBox(height: 12),
          Text(
            title,
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 6),
          Text(
            detail,
            textAlign: TextAlign.center,
            style: TextStyle(
              color: LumenisTheme.of(context).muted,
              height: 1.45,
            ),
          ),
        ],
      ),
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
      child: CircularProgressIndicator(color: LumenisTheme.of(context).shared),
    ),
  );
}

class _FailureState extends StatelessWidget {
  const _FailureState({required this.kind, required this.onRetry});
  final Ai04FailureKind kind;
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
              Ai04FailureKind.authentication => _copy(
                context,
                zh: '访问身份未确认',
                en: 'Access identity unconfirmed',
                ko: '접근 신원 확인 안 됨',
              ),
              Ai04FailureKind.permissionDenied => _copy(
                context,
                zh: '技能目录未获访问确认',
                en: 'Skill catalog access not confirmed',
                ko: '스킬 카탈로그 접근 확인 안 됨',
              ),
              Ai04FailureKind.offline => _copy(
                context,
                zh: '技能目录暂时离线',
                en: 'Skill catalog is offline',
                ko: '스킬 카탈로그 오프라인',
              ),
              Ai04FailureKind.server => _copy(
                context,
                zh: '技能目录暂不可用',
                en: 'Skill catalog unavailable',
                ko: '스킬 카탈로그 사용 불가',
              ),
            }, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 8),
            Text(
              _copy(
                context,
                zh: '未读取到可核验的登记结果。',
                en: 'No verifiable registry result was read.',
                ko: '확인 가능한 등록 결과를 읽지 못했습니다.',
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

String _permissionLabel(BuildContext context, String value) => switch (value) {
  'READ' => _copy(context, zh: '读取', en: 'Read', ko: '읽기'),
  'RESEARCH' => _copy(context, zh: '研究', en: 'Research', ko: '연구'),
  'ANALYZE' => _copy(context, zh: '分析', en: 'Analyze', ko: '분석'),
  'SUGGEST' => _copy(context, zh: '建议', en: 'Suggest', ko: '제안'),
  'AUDIT' => _copy(context, zh: '检查', en: 'Audit', ko: '감사'),
  _ => _copy(context, zh: '以登记范围为准', en: 'Registry-defined', ko: '등록 기준'),
};

String _riskLabel(BuildContext context, String value) => switch (value) {
  'LOW' => _copy(context, zh: '低', en: 'Low', ko: '낮음'),
  'MEDIUM' => _copy(context, zh: '中', en: 'Medium', ko: '중간'),
  'HIGH' => _copy(context, zh: '高', en: 'High', ko: '높음'),
  'CRITICAL' => _copy(context, zh: '严重', en: 'Critical', ko: '심각'),
  _ => _copy(context, zh: '待确认', en: 'Unconfirmed', ko: '확인 필요'),
};

String _policyLabel(BuildContext context, String value) => switch (value) {
  'READ_ONLY' => _copy(context, zh: '只读', en: 'Read only', ko: '읽기 전용'),
  'AUDIT_ONLY' => _copy(context, zh: '仅检查', en: 'Audit only', ko: '감사 전용'),
  'APPROVAL_REQUIRED' => _copy(
    context,
    zh: '需要审批',
    en: 'Approval required',
    ko: '승인 필요',
  ),
  'AUTO_EXECUTE' => _copy(
    context,
    zh: '受规则允许时自动',
    en: 'Automatic when governed',
    ko: '관리 규칙 내 자동',
  ),
  _ => _copy(context, zh: '以登记范围为准', en: 'Registry-defined', ko: '등록 기준'),
};

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
