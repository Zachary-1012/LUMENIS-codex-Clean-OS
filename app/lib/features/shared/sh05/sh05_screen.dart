import 'package:flutter/material.dart';

import '../../../core/lumenis_icon.dart';

import '../../../core/lumenis_core_client.dart';
import '../../../core/lumenis_theme.dart';
import '../../../l10n/lumenis_localizations.dart';
import 'sh05_repository.dart';
import 'sh05_snapshot.dart';
import 'sh05_view_model.dart';

class Sh05Screen extends StatefulWidget {
  const Sh05Screen({required this.client, this.repository, super.key});

  final LumenisCoreClient client;
  final Sh05Repository? repository;

  @override
  State<Sh05Screen> createState() => _Sh05ScreenState();
}

class _Sh05ScreenState extends State<Sh05Screen> {
  late final Sh05ViewModel _viewModel = Sh05ViewModel(
    repository: widget.repository ?? CoreSh05Repository(client: widget.client),
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
          Sh05LoadPhase.loading => _LoadingState(),
          Sh05LoadPhase.blocked => _BlockedState(
            error: _viewModel.scopeError,
            onRetry: _viewModel.refresh,
          ),
          Sh05LoadPhase.failed => _FailureState(
            kind: _viewModel.failureKind!,
            onRetry: _viewModel.refresh,
          ),
          Sh05LoadPhase.ready => _Workspace(viewModel: _viewModel),
        },
      ),
    ),
  );
}

class _Workspace extends StatelessWidget {
  const _Workspace({required this.viewModel});

  final Sh05ViewModel viewModel;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, constraints) {
      final wide = constraints.maxWidth >= 1120;
      final shelf = _AssetShelf(viewModel: viewModel);
      final inspector = _AssetInspector(asset: viewModel.selected);
      final scope = viewModel.snapshot!.scope;
      return Align(
        alignment: Alignment.topCenter,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1540),
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
                      Expanded(child: shelf),
                      const SizedBox(width: 16),
                      SizedBox(width: 360, child: inspector),
                    ],
                  )
                else
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [shelf, const SizedBox(height: 14), inspector],
                  ),
                const SizedBox(height: 14),
                _GovernanceNote(),
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
      _Eyebrow(_copy(context, '可复用经验', 'REVIEWED LEARNING', '검토된 학습')),
      const SizedBox(height: 9),
      Text(
        context.lumenisL10n.text('screen.SH-05'),
        style: Theme.of(context).textTheme.headlineMedium?.copyWith(
          color: LumenisTheme.of(context).foreground,
          fontWeight: FontWeight.w600,
        ),
      ),
      const SizedBox(height: 6),
      Text(
        _copy(
          context,
          '按成熟度查看 SOP、复盘、培训和评估资产；每个版本都保留来源与回退状态。',
          'Browse SOPs, retrospectives, training and evaluation assets by maturity, with provenance and rollback state per version.',
          '성숙도별 SOP·회고·교육·평가 자산을 확인하고 버전별 출처와 롤백 상태를 봅니다.',
        ),
        style: TextStyle(color: LumenisTheme.of(context).muted, height: 1.45),
      ),
    ],
  );
}

class _ScopeBanner extends StatelessWidget {
  const _ScopeBanner({required this.scope});

  final Sh05Scope scope;

  @override
  Widget build(BuildContext context) {
    final range = scope.isGlobal
        ? _copy(context, '全部范围', 'All scopes', '전체 범위')
        : '${scope.businessDomain} · ${scope.displayName}';
    return Semantics(
      liveRegion: true,
      label: _copy(
        context,
        '当前资产范围：$range',
        'Current asset range: $range',
        '현재 자산 범위: $range',
      ),
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(horizontal: 15, vertical: 12),
        decoration: BoxDecoration(
          color: LumenisTheme.of(context).ai.withValues(alpha: 0.08),
          border: Border.all(
            color: LumenisTheme.of(context).ai.withValues(alpha: 0.35),
          ),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Row(
          children: [
            Icon(
              Icons.filter_alt_outlined,
              color: LumenisTheme.of(context).ai,
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

class _AssetShelf extends StatelessWidget {
  const _AssetShelf({required this.viewModel});

  final Sh05ViewModel viewModel;

  @override
  Widget build(BuildContext context) {
    final items = viewModel.visibleAssets;
    return _Panel(
      title: _copy(context, '资产货架', 'Asset shelves', '자산 선반'),
      detail: _copy(
        context,
        '已验证、候选和已退役版本分开浏览。',
        'Verified, candidate and retired versions are browsed separately.',
        '검증·후보·퇴역 버전을 나누어 확인합니다.',
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: 7,
            runSpacing: 7,
            children: [
              for (final shelf in Sh05Shelf.values)
                _ShelfChip(
                  shelf: shelf,
                  selected: viewModel.shelf == shelf,
                  onSelected: () => viewModel.setShelf(shelf),
                ),
            ],
          ),
          const SizedBox(height: 15),
          if (items.isEmpty)
            _InfoMessage(
              _copy(
                context,
                '当前货架没有可查看的学习资产。',
                'This shelf has no learning assets to show.',
                '현재 선반에 표시할 학습 자산이 없습니다.',
              ),
            )
          else
            LayoutBuilder(
              builder: (context, constraints) {
                final columns = constraints.maxWidth >= 900
                    ? 3
                    : constraints.maxWidth >= 560
                    ? 2
                    : 1;
                final width =
                    (constraints.maxWidth - (columns - 1) * 10) / columns;
                return Wrap(
                  spacing: 10,
                  runSpacing: 10,
                  children: [
                    for (final asset in items)
                      SizedBox(
                        width: width,
                        child: _AssetTile(
                          asset: asset,
                          selected:
                              viewModel.selected?.internalId ==
                              asset.internalId,
                          onTap: () => viewModel.select(asset),
                        ),
                      ),
                  ],
                );
              },
            ),
        ],
      ),
    );
  }
}

class _ShelfChip extends StatelessWidget {
  const _ShelfChip({
    required this.shelf,
    required this.selected,
    required this.onSelected,
  });

  final Sh05Shelf shelf;
  final bool selected;
  final VoidCallback onSelected;

  @override
  Widget build(BuildContext context) => FilterChip(
    label: Text(_shelfLabel(context, shelf)),
    selected: selected,
    onSelected: (_) => onSelected(),
    materialTapTargetSize: MaterialTapTargetSize.padded,
  );
}

class _AssetTile extends StatelessWidget {
  const _AssetTile({
    required this.asset,
    required this.selected,
    required this.onTap,
  });

  final Sh05Asset asset;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Material(
    color: selected
        ? LumenisTheme.of(context).ai.withValues(alpha: 0.1)
        : LumenisTheme.of(context).surfaceRaised,
    borderRadius: BorderRadius.circular(11),
    child: InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(11),
      child: Container(
        constraints: const BoxConstraints(minHeight: 138),
        padding: const EdgeInsets.fromLTRB(13, 13, 13, 12),
        decoration: BoxDecoration(
          border: Border.all(
            color: selected
                ? LumenisTheme.of(context).ai.withValues(alpha: 0.55)
                : LumenisTheme.of(context).line,
          ),
          borderRadius: BorderRadius.circular(11),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  _kindIcon(asset.kind),
                  color: selected
                      ? LumenisTheme.of(context).ai
                      : LumenisTheme.of(context).quiet,
                  size: 19,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    asset.kindLabel,
                    style: TextStyle(
                      color: LumenisTheme.of(context).muted,
                      fontSize: 11,
                    ),
                  ),
                ),
                Text(
                  'v${asset.version}',
                  style: TextStyle(
                    color: LumenisTheme.of(context).ai,
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            Text(
              asset.title,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 10),
            Wrap(
              spacing: 6,
              runSpacing: 5,
              children: [
                _StatusChip(
                  asset.promotionLabel,
                  color: _promotionColor(context, asset.promotionStatus),
                ),
                _StatusChip(
                  asset.reviewState,
                  color: LumenisTheme.of(context).muted,
                ),
              ],
            ),
          ],
        ),
      ),
    ),
  );
}

class _AssetInspector extends StatelessWidget {
  const _AssetInspector({required this.asset});

  final Sh05Asset? asset;

  @override
  Widget build(BuildContext context) {
    final item = asset;
    return _Panel(
      title: _copy(context, '版本档案', 'Version record', '버전 기록'),
      detail: _copy(
        context,
        '查看来源、复核和可回退状态；本页不会自动晋级资产。',
        'Inspect provenance, review and rollback state; this page never promotes an asset automatically.',
        '출처·검토·롤백 상태를 확인하며 이 화면은 자산을 자동 승격하지 않습니다.',
      ),
      child: item == null
          ? _InfoMessage(
              _copy(
                context,
                '选择一个资产查看版本档案。',
                'Select an asset to inspect its version record.',
                '자산을 선택해 버전 기록을 확인하세요.',
              ),
            )
          : Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  item.title,
                  style: const TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 13),
                _DetailLine(
                  label: _copy(context, '类型', 'Type', '유형'),
                  value: item.kindLabel,
                ),
                _DetailLine(
                  label: _copy(context, '版本', 'Version', '버전'),
                  value: 'v${item.version}',
                ),
                _DetailLine(
                  label: _copy(context, '晋级状态', 'Promotion', '승격 상태'),
                  value: item.promotionLabel,
                ),
                _DetailLine(
                  label: _copy(context, '复核状态', 'Review', '검토 상태'),
                  value: item.reviewState,
                ),
                if (item.reviewedAt.isNotEmpty)
                  _DetailLine(
                    label: _copy(context, '最近复核', 'Last review', '최근 검토'),
                    value: item.reviewedAt,
                  ),
                if (item.provenance.isNotEmpty)
                  _DetailLine(
                    label: _copy(context, '来源', 'Provenance', '출처'),
                    value: item.provenance,
                  ),
                const SizedBox(height: 5),
                _RollbackStatus(available: item.rollbackAvailable),
                if (item.description.isNotEmpty) ...[
                  const SizedBox(height: 15),
                  Text(
                    item.description,
                    style: TextStyle(
                      color: LumenisTheme.of(context).muted,
                      height: 1.5,
                    ),
                  ),
                ],
                const SizedBox(height: 15),
                Text(
                  _copy(
                    context,
                    '状态变更必须经过复核、评估和明确的人工决定；这里没有自动修改入口。',
                    'State changes require review, evaluation and an explicit human decision; there is no automatic mutation entry here.',
                    '상태 변경에는 검토·평가·명시적 사람의 결정이 필요하며 이 화면에는 자동 변경 입구가 없습니다.',
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

class _RollbackStatus extends StatelessWidget {
  const _RollbackStatus({required this.available});

  final bool available;

  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 11),
    decoration: BoxDecoration(
      color:
          (available
                  ? LumenisTheme.of(context).caution
                  : LumenisTheme.of(context).muted)
              .withValues(alpha: 0.1),
      border: Border.all(
        color:
            (available
                    ? LumenisTheme.of(context).caution
                    : LumenisTheme.of(context).muted)
                .withValues(alpha: 0.34),
      ),
      borderRadius: BorderRadius.circular(9),
    ),
    child: Row(
      children: [
        Icon(
          available ? Icons.undo_rounded : Icons.block_outlined,
          color: available
              ? LumenisTheme.of(context).caution
              : LumenisTheme.of(context).muted,
          size: 18,
        ),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            available
                ? _copy(
                    context,
                    '已有可回退版本，但回退仍需人工确认。',
                    'A rollback version exists, but rollback still needs human confirmation.',
                    '롤백 버전이 있지만 롤백에는 사람의 확인이 필요합니다.',
                  )
                : _copy(
                    context,
                    '当前没有确认可回退版本。',
                    'No rollback version is confirmed for this asset.',
                    '이 자산에 확인된 롤백 버전이 없습니다.',
                  ),
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

class _GovernanceNote extends StatelessWidget {
  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    padding: const EdgeInsets.fromLTRB(15, 13, 15, 13),
    decoration: BoxDecoration(
      color: LumenisTheme.of(context).ai.withValues(alpha: 0.08),
      border: Border.all(
        color: LumenisTheme.of(context).ai.withValues(alpha: 0.32),
      ),
      borderRadius: BorderRadius.circular(11),
    ),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(
          Icons.policy_outlined,
          color: LumenisTheme.of(context).ai,
          size: 19,
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Text(
            _copy(
              context,
              '学习资产只作为经过范围核对的输入，不会覆盖正式业务记录，也不会因为一次成功就自动晋级。',
              'Learning assets are scoped inputs; they do not overwrite formal business records or promote themselves after one success.',
              '학습 자산은 범위가 확인된 입력일 뿐 정식 업무 기록을 덮어쓰지 않으며 한 번의 성공으로 자동 승격되지 않습니다.',
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
    label: _copy(context, '正在读取学习资产', 'Reading learning assets', '학습 자산을 읽는 중'),
    child: const Center(child: CircularProgressIndicator()),
  );
}

class _BlockedState extends StatelessWidget {
  const _BlockedState({required this.error, required this.onRetry});

  final Sh05ScopeErrorKind? error;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => _StateMessage(
    title: _copy(
      context,
      '学习资产暂不显示',
      'Learning assets are hidden for now',
      '학습 자산을 현재 표시하지 않습니다',
    ),
    detail: switch (error) {
      Sh05ScopeErrorKind.denied => _copy(
        context,
        '当前账号没有这个范围的查看权限。',
        'This account cannot view the selected range.',
        '이 계정은 선택한 범위를 볼 수 없습니다.',
      ),
      Sh05ScopeErrorKind.malformed => _copy(
        context,
        '服务返回的查看范围不完整，因此不会显示资产。',
        'The returned viewing range is incomplete, so assets are not shown.',
        '반환된 조회 범위가 불완전하여 자산을 표시하지 않습니다.',
      ),
      _ => _copy(
        context,
        '尚未确认账号与业务范围的对应关系，因此不会显示资产。',
        'The account and business range have not been verified, so assets are not shown.',
        '계정과 업무 범위가 확인되지 않아 자산을 표시하지 않습니다.',
      ),
    },
    onRetry: onRetry,
  );
}

class _FailureState extends StatelessWidget {
  const _FailureState({required this.kind, required this.onRetry});

  final Sh05FailureKind kind;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => _StateMessage(
    title: _copy(
      context,
      '学习资产暂不可用',
      'Learning assets unavailable',
      '학습 자산을 사용할 수 없습니다',
    ),
    detail: switch (kind) {
      Sh05FailureKind.authentication => _copy(
        context,
        '当前内容暂时无法打开。可重试读取，或返回后稍后再试。',
        'This content cannot be opened right now. You can retry reading it or return and try again later.',
        '현재 콘텐츠를 지금 열 수 없습니다. 다시 읽기를 시도하거나 돌아간 뒤 나중에 다시 시도할 수 있습니다.',
      ),
      Sh05FailureKind.permissionDenied => _copy(
        context,
        '当前内容不可访问。',
        'This content is not accessible.',
        '현재 콘텐츠에 접근할 수 없습니다.',
      ),
      Sh05FailureKind.offline => _copy(
        context,
        '学习资产服务暂时无法连接，请检查连接后重试。',
        'The learning asset service cannot connect right now. Check the connection and try again.',
        '학습 자산 서비스에 연결할 수 없습니다. 연결을 확인하고 다시 시도하세요.',
      ),
      Sh05FailureKind.response => _copy(
        context,
        '学习资产服务没有返回可验证的数据，请稍后重试。',
        'The learning asset service did not return verifiable data. Try again later.',
        '학습 자산 서비스가 확인 가능한 데이터를 반환하지 않았습니다. 나중에 다시 시도하세요.',
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
          width: 84,
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

class _StatusChip extends StatelessWidget {
  const _StatusChip(this.label, {required this.color});

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
      color: LumenisTheme.of(context).ai,
      fontSize: 10,
      letterSpacing: 1.1,
      fontWeight: FontWeight.w700,
    ),
  );
}

IconData _kindIcon(Sh05AssetKind kind) => switch (kind) {
  Sh05AssetKind.sop => Icons.checklist_rounded,
  Sh05AssetKind.retrospective => Icons.history_rounded,
  Sh05AssetKind.training => Icons.school_outlined,
  Sh05AssetKind.evaluation => Icons.fact_check_outlined,
  Sh05AssetKind.pattern => Icons.auto_awesome_outlined,
  Sh05AssetKind.other => Icons.folder_outlined,
};

Color _promotionColor(BuildContext context, Sh05PromotionStatus status) =>
    switch (status) {
      Sh05PromotionStatus.domainVerified ||
      Sh05PromotionStatus.coreVerified ||
      Sh05PromotionStatus.repaired => LumenisTheme.of(context).positive,
      Sh05PromotionStatus.candidate ||
      Sh05PromotionStatus.transferCandidate ||
      Sh05PromotionStatus.observed => LumenisTheme.of(context).caution,
      Sh05PromotionStatus.rejected ||
      Sh05PromotionStatus.retired => LumenisTheme.of(context).danger,
      Sh05PromotionStatus.unknown => LumenisTheme.of(context).muted,
    };

String _shelfLabel(BuildContext context, Sh05Shelf shelf) => switch (shelf) {
  Sh05Shelf.all => _copy(context, '全部', 'All', '전체'),
  Sh05Shelf.verified => _copy(context, '已验证', 'Verified', '검증됨'),
  Sh05Shelf.candidates => _copy(context, '候选', 'Candidates', '후보'),
  Sh05Shelf.retired => _copy(
    context,
    '退役 / 拒绝',
    'Retired / rejected',
    '퇴역 / 거부',
  ),
};

String _copy(BuildContext context, String zh, String en, String ko) =>
    switch (context.lumenisL10n.locale.languageCode) {
      'en' => en,
      'ko' => ko,
      _ => zh,
    };
