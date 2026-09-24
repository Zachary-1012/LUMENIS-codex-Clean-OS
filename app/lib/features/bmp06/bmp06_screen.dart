import 'package:flutter/material.dart';

import '../../core/lumenis_core_client.dart';
import '../../core/lumenis_theme.dart';
import '../../l10n/lumenis_localizations.dart';
import 'bmp06_repository.dart';
import 'bmp06_snapshot.dart';
import 'bmp06_view_model.dart';

class Bmp06Screen extends StatefulWidget {
  const Bmp06Screen({required this.client, this.repository, super.key});

  final LumenisCoreClient client;
  final Bmp06Repository? repository;

  @override
  State<Bmp06Screen> createState() => _Bmp06ScreenState();
}

class _Bmp06ScreenState extends State<Bmp06Screen> {
  late final Bmp06ViewModel _viewModel = Bmp06ViewModel(
    repository: widget.repository ?? CoreBmp06Repository(client: widget.client),
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
            Bmp06LoadPhase.loading => const _Loading(),
            Bmp06LoadPhase.failed => _Failure(
              kind: _viewModel.failureKind!,
              onRetry: _viewModel.refresh,
            ),
            Bmp06LoadPhase.ready => _ContentCenter(
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

class _ContentCenter extends StatelessWidget {
  const _ContentCenter({
    required this.snapshot,
    required this.actionState,
    required this.actionId,
    required this.onRefresh,
    required this.onAction,
  });

  final Bmp06Snapshot snapshot;
  final Bmp06ActionState actionState;
  final String? actionId;
  final VoidCallback onRefresh;
  final void Function(String actionId, String permission) onAction;

  @override
  Widget build(BuildContext context) {
    final copy = _Bmp06Copy.of(context);
    return LayoutBuilder(
      builder: (context, constraints) {
        final wide = constraints.maxWidth >= 1100;
        final padding = constraints.maxWidth >= 800 ? 32.0 : 18.0;
        final body = snapshot.isScopeApproved
            ? (wide
                  ? _DesktopProduction(snapshot: snapshot, copy: copy)
                  : _CompactProduction(snapshot: snapshot, copy: copy))
            : _ScopeGate(snapshot: snapshot, copy: copy);

        return Align(
          alignment: Alignment.topCenter,
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1440),
            child: SingleChildScrollView(
              padding: EdgeInsets.fromLTRB(padding, 28, padding, 40),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _Header(copy: copy, onRefresh: onRefresh),
                  const SizedBox(height: 26),
                  body,
                  const SizedBox(height: 20),
                  _ActionRail(
                    copy: copy,
                    actionState: actionState,
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

  final _Bmp06Copy copy;
  final VoidCallback onRefresh;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                context.lumenisL10n.text('screen.BMP-06'),
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
}

class _DesktopProduction extends StatelessWidget {
  const _DesktopProduction({required this.snapshot, required this.copy});

  final Bmp06Snapshot snapshot;
  final _Bmp06Copy copy;

  @override
  Widget build(BuildContext context) {
    final scopeLabel = snapshot.scope.isGlobal
        ? copy.globalRange
        : copy.focusLabel;
    final brand =
        snapshot.scope.localizedName(copy.languageCode) ??
        (snapshot.scope.isGlobal ? copy.allBrands : copy.brandUnknown);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _ContextLine(copy: copy, brand: brand, scopeLabel: scopeLabel),
        const SizedBox(height: 16),
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: _SwimlaneBoard(assets: snapshot.assets, copy: copy),
            ),
            const SizedBox(width: 18),
            SizedBox(
              width: 300,
              child: _VersionInspector(assets: snapshot.assets, copy: copy),
            ),
          ],
        ),
      ],
    );
  }
}

class _CompactProduction extends StatelessWidget {
  const _CompactProduction({required this.snapshot, required this.copy});

  final Bmp06Snapshot snapshot;
  final _Bmp06Copy copy;

  @override
  Widget build(BuildContext context) {
    final scopeLabel = snapshot.scope.isGlobal
        ? copy.globalRange
        : copy.focusLabel;
    final brand =
        snapshot.scope.localizedName(copy.languageCode) ??
        (snapshot.scope.isGlobal ? copy.allBrands : copy.brandUnknown);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _ContextLine(copy: copy, brand: brand, scopeLabel: scopeLabel),
        const SizedBox(height: 14),
        _QueueView(assets: snapshot.assets, copy: copy),
      ],
    );
  }
}

class _ContextLine extends StatelessWidget {
  const _ContextLine({
    required this.copy,
    required this.brand,
    required this.scopeLabel,
  });

  final _Bmp06Copy copy;
  final String brand;
  final String scopeLabel;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      container: true,
      label: '$scopeLabel: $brand',
      child: DecoratedBox(
        decoration: BoxDecoration(
          border: Border(
            bottom: BorderSide(color: LumenisTheme.of(context).line),
          ),
        ),
        child: Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: Row(
            children: [
              Icon(
                Icons.local_offer_outlined,
                color: LumenisTheme.of(context).bmp,
              ),
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
            ],
          ),
        ),
      ),
    );
  }
}

class _SwimlaneBoard extends StatelessWidget {
  const _SwimlaneBoard({required this.assets, required this.copy});

  final List<Bmp06Asset> assets;
  final _Bmp06Copy copy;

  static const stages = <String>[
    'BRIEF',
    'DRAFT',
    'REVIEW',
    'APPROVED',
    'SCHEDULED',
    'DELIVERED',
  ];

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: LumenisTheme.of(context).surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: LumenisTheme.of(context).line),
      ),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.all(16),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            for (var index = 0; index < stages.length; index++) ...[
              if (index > 0) const SizedBox(width: 10),
              _Lane(
                stage: stages[index],
                assets: assets
                    .where((asset) => asset.state == stages[index])
                    .toList(),
                copy: copy,
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _Lane extends StatelessWidget {
  const _Lane({required this.stage, required this.assets, required this.copy});

  final String stage;
  final List<Bmp06Asset> assets;
  final _Bmp06Copy copy;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 164,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            copy.stage(stage),
            style: TextStyle(
              color: LumenisTheme.of(context).muted,
              fontSize: 12,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 12),
          if (assets.isEmpty)
            Text(
              copy.noAssets,
              style: TextStyle(color: LumenisTheme.of(context).quiet),
            )
          else
            for (final asset in assets) ...[
              _AssetSlip(asset: asset, copy: copy),
              const SizedBox(height: 8),
            ],
        ],
      ),
    );
  }
}

class _AssetSlip extends StatelessWidget {
  const _AssetSlip({required this.asset, required this.copy});

  final Bmp06Asset asset;
  final _Bmp06Copy copy;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      container: true,
      label: '${asset.title}, ${copy.stage(asset.state)}',
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: LumenisTheme.of(context).surfaceRaised,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: LumenisTheme.of(context).line),
        ),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                asset.title,
                maxLines: 3,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  color: LumenisTheme.of(context).foreground,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 9),
              Text(
                copy.kind(asset.kind),
                style: TextStyle(
                  color: LumenisTheme.of(context).quiet,
                  fontSize: 11,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                copy.approval(asset.approval),
                style: TextStyle(
                  color: LumenisTheme.of(context).muted,
                  fontSize: 11,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _VersionInspector extends StatelessWidget {
  const _VersionInspector({required this.assets, required this.copy});

  final List<Bmp06Asset> assets;
  final _Bmp06Copy copy;

  @override
  Widget build(BuildContext context) {
    final selected = assets.isEmpty ? null : assets.first;
    return DecoratedBox(
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
            Text(
              copy.inspector,
              style: TextStyle(
                color: LumenisTheme.of(context).quiet,
                fontSize: 11,
              ),
            ),
            const SizedBox(height: 18),
            if (selected == null)
              Text(
                copy.inspectorEmpty,
                style: TextStyle(
                  color: LumenisTheme.of(context).muted,
                  height: 1.5,
                ),
              )
            else ...[
              Text(
                selected.title,
                style: TextStyle(
                  color: LumenisTheme.of(context).foreground,
                  fontSize: 18,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 16),
              _InspectorRow(
                label: copy.stageLabel,
                value: copy.stage(selected.state),
              ),
              _InspectorRow(
                label: copy.kindLabel,
                value: copy.kind(selected.kind),
              ),
              _InspectorRow(
                label: copy.approvalLabel,
                value: copy.approval(selected.approval),
              ),
              const SizedBox(height: 14),
              Text(
                copy.lineageReady,
                style: TextStyle(color: LumenisTheme.of(context).positive),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _InspectorRow extends StatelessWidget {
  const _InspectorRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 7),
      child: Row(
        children: [
          Expanded(
            child: Text(
              label,
              style: TextStyle(color: LumenisTheme.of(context).muted),
            ),
          ),
          const SizedBox(width: 8),
          Flexible(
            child: Text(
              value,
              textAlign: TextAlign.end,
              style: TextStyle(color: LumenisTheme.of(context).foreground),
            ),
          ),
        ],
      ),
    );
  }
}

class _QueueView extends StatelessWidget {
  const _QueueView({required this.assets, required this.copy});

  final List<Bmp06Asset> assets;
  final _Bmp06Copy copy;

  @override
  Widget build(BuildContext context) {
    if (assets.isEmpty) return _EmptyProduction(copy: copy);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(copy.queueTitle, style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 12),
        for (final asset in assets) ...[
          _QueueRow(asset: asset, copy: copy),
          const SizedBox(height: 8),
        ],
      ],
    );
  }
}

class _QueueRow extends StatelessWidget {
  const _QueueRow({required this.asset, required this.copy});

  final Bmp06Asset asset;
  final _Bmp06Copy copy;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: LumenisTheme.of(context).surface,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: LumenisTheme.of(context).line),
      ),
      child: Padding(
        padding: const EdgeInsets.all(15),
        child: Row(
          children: [
            Icon(_icon(asset.state), color: LumenisTheme.of(context).bmp),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    asset.title,
                    style: TextStyle(
                      color: LumenisTheme.of(context).foreground,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 5),
                  Text(
                    '${copy.stage(asset.state)} · ${copy.approval(asset.approval)}',
                    style: TextStyle(
                      color: LumenisTheme.of(context).muted,
                      fontSize: 12,
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

  IconData _icon(String state) => switch (state) {
    'BRIEF' => Icons.assignment_outlined,
    'DRAFT' => Icons.edit_note_rounded,
    'REVIEW' => Icons.rate_review_outlined,
    'APPROVED' => Icons.verified_outlined,
    'SCHEDULED' => Icons.schedule_rounded,
    _ => Icons.check_circle_outline_rounded,
  };
}

class _ScopeGate extends StatelessWidget {
  const _ScopeGate({required this.snapshot, required this.copy});

  final Bmp06Snapshot snapshot;
  final _Bmp06Copy copy;

  @override
  Widget build(BuildContext context) {
    final notCollected = snapshot.dataState == 'NOT_COLLECTED';
    return DecoratedBox(
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
            Icon(
              notCollected
                  ? Icons.hourglass_empty_rounded
                  : Icons.visibility_off_outlined,
              color: LumenisTheme.of(context).caution,
              size: 28,
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    notCollected
                        ? copy.notCollectedTitle
                        : copy.unavailableTitle,
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    notCollected
                        ? copy.notCollectedDetail
                        : copy.unavailableDetail,
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
}

class _EmptyProduction extends StatelessWidget {
  const _EmptyProduction({required this.copy});

  final _Bmp06Copy copy;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: LumenisTheme.of(context).surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: LumenisTheme.of(context).line),
      ),
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Row(
          children: [
            Icon(
              Icons.inbox_outlined,
              color: LumenisTheme.of(context).bmp,
              size: 28,
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Text(
                copy.noAssets,
                style: TextStyle(color: LumenisTheme.of(context).muted),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ActionRail extends StatelessWidget {
  const _ActionRail({
    required this.copy,
    required this.actionState,
    required this.actionId,
    required this.onAction,
  });

  final _Bmp06Copy copy;
  final Bmp06ActionState actionState;
  final String? actionId;
  final void Function(String actionId, String permission) onAction;

  @override
  Widget build(BuildContext context) {
    final result = switch (actionState) {
      Bmp06ActionState.idle => null,
      Bmp06ActionState.blocked => copy.actionBlocked,
      Bmp06ActionState.staged => copy.actionStaged,
    };
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (result != null) ...[
          Semantics(
            liveRegion: true,
            child: Text(
              result,
              style: TextStyle(
                color: actionState == Bmp06ActionState.staged
                    ? LumenisTheme.of(context).positive
                    : LumenisTheme.of(context).caution,
              ),
            ),
          ),
          const SizedBox(height: 12),
        ],
        DecoratedBox(
          decoration: BoxDecoration(
            border: Border(
              top: BorderSide(color: LumenisTheme.of(context).line),
            ),
          ),
          child: Padding(
            padding: const EdgeInsets.only(top: 16),
            child: Wrap(
              spacing: 10,
              runSpacing: 10,
              children: [
                FilledButton.icon(
                  onPressed: () => onAction('BMP-06.new', 'content:draft'),
                  icon: const Icon(Icons.add_rounded),
                  label: Text(copy.newContent),
                ),
                OutlinedButton.icon(
                  onPressed: () =>
                      onAction('BMP-06.submit-review', 'content:submit'),
                  icon: const Icon(Icons.rate_review_outlined),
                  label: Text(copy.submitReview),
                ),
                OutlinedButton.icon(
                  onPressed: () =>
                      onAction('BMP-06.publish', 'content:publish'),
                  icon: const Icon(Icons.outbox_outlined),
                  label: Text(copy.publish),
                ),
              ],
            ),
          ),
        ),
        if (actionId == 'BMP-06.publish') ...[
          const SizedBox(height: 9),
          Text(
            copy.publishGuard,
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
      label: _Bmp06Copy.of(context).loading,
      child: Padding(
        padding: EdgeInsets.all(48),
        child: CircularProgressIndicator(color: LumenisTheme.of(context).bmp),
      ),
    ),
  );
}

class _Failure extends StatelessWidget {
  const _Failure({required this.kind, required this.onRetry});

  final Bmp06FailureKind kind;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final copy = _Bmp06Copy.of(context);
    final title = switch (kind) {
      Bmp06FailureKind.authentication => copy.signIn,
      Bmp06FailureKind.permissionDenied => copy.accessDenied,
      Bmp06FailureKind.offline => copy.offline,
      Bmp06FailureKind.server => copy.unavailableTitle,
    };
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 520),
          child: DecoratedBox(
            decoration: BoxDecoration(
              color: LumenisTheme.of(context).surface,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: LumenisTheme.of(context).line),
            ),
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 8),
                  Text(
                    copy.retryDetail,
                    style: TextStyle(
                      color: LumenisTheme.of(context).muted,
                      height: 1.5,
                    ),
                  ),
                  const SizedBox(height: 16),
                  OutlinedButton.icon(
                    onPressed: onRetry,
                    icon: const Icon(Icons.refresh_rounded),
                    label: Text(copy.refresh),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _Bmp06Copy {
  _Bmp06Copy(this.languageCode);

  final String languageCode;

  static _Bmp06Copy of(BuildContext context) {
    final languageCode = Localizations.localeOf(context).languageCode;
    return _Bmp06Copy(
      languageCode == 'en' || languageCode == 'ko' ? languageCode : 'zh-CN',
    );
  }

  String get subtitle => _get('subtitle');
  String get refresh => _get('refresh');
  String get focusLabel => _get('focus');
  String get globalRange => _get('globalRange');
  String get allBrands => _get('allBrands');
  String get brandUnknown => _get('brandUnknown');
  String get inspector => _get('inspector');
  String get inspectorEmpty => _get('inspectorEmpty');
  String get stageLabel => _get('stageLabel');
  String get kindLabel => _get('kindLabel');
  String get approvalLabel => _get('approvalLabel');
  String get lineageReady => _get('lineageReady');
  String get queueTitle => _get('queueTitle');
  String get noAssets => _get('noAssets');
  String get unavailableTitle => _get('unavailableTitle');
  String get unavailableDetail => _get('unavailableDetail');
  String get notCollectedTitle => _get('notCollectedTitle');
  String get notCollectedDetail => _get('notCollectedDetail');
  String get actionBlocked => _get('actionBlocked');
  String get actionStaged => _get('actionStaged');
  String get publishGuard => _get('publishGuard');
  String get loading => _get('loading');
  String get signIn => _get('signIn');
  String get accessDenied => _get('accessDenied');
  String get offline => _get('offline');
  String get retryDetail => _get('retryDetail');
  String get newContent => _get('newContent');
  String get submitReview => _get('submitReview');
  String get publish => _get('publish');

  String stage(String value) => _get('stage.$value');
  String kind(String value) => _get('kind.$value');
  String approval(String value) => _get('approval.$value');

  String _get(String key) =>
      _values[languageCode]?[key] ?? _values['zh-CN']![key]!;

  static const _values = <String, Map<String, String>>{
    'zh-CN': {
      'subtitle': '让 Brief、版本、审核与交付停留在同一条内容生产线上。',
      'refresh': '刷新内容队列',
      'focus': '当前品牌',
      'globalRange': '全球品牌范围',
      'allBrands': '已授权的全球品牌集合',
      'brandUnknown': '品牌名称暂不可用',
      'inspector': '版本检查',
      'inspectorEmpty': '选择一项有来源的内容，查看它的版本与审核状态。',
      'stageLabel': '当前阶段',
      'kindLabel': '内容类型',
      'approvalLabel': '审核进度',
      'lineageReady': '来源已关联',
      'queueTitle': '内容生产队列',
      'noAssets': '当前品牌暂无可展示的内容版本。',
      'unavailableTitle': '内容生产资料暂不可用',
      'unavailableDetail': '当前品牌范围或资料来源尚未确认，暂不展示其他品牌的内容，也不会把缺失当作零条记录。',
      'notCollectedTitle': '还没有开始收集内容资料',
      'notCollectedDetail': '内容资料准备好后，这里会显示 Brief、版本、审核与交付状态。',
      'actionBlocked': '当前范围还不能执行这项操作；请先确认品牌访问范围与审核条件。',
      'actionStaged': '本地内容请求草稿已保存；尚未创建、提交或发布任何内容。',
      'publishGuard': '这里仅保存本地请求草稿；内容不会发布，直到授权、审批与明确结果都准备好。',
      'loading': '正在加载内容生产队列',
      'signIn': '需要登录后查看内容',
      'accessDenied': '当前账号暂时无法查看内容',
      'offline': '暂时无法连接内容服务',
      'retryDetail': '请检查连接后重试；没有确认的内容不会显示。',
      'newContent': '保存内容草稿',
      'submitReview': '保存审核请求草稿',
      'publish': '保存发布请求草稿',
      'stage.BRIEF': 'Brief',
      'stage.DRAFT': '草稿',
      'stage.REVIEW': '审核中',
      'stage.APPROVED': '已批准',
      'stage.SCHEDULED': '已排期',
      'stage.DELIVERED': '已交付',
      'kind.BRIEF': 'Brief',
      'kind.DRAFT': '文字草稿',
      'kind.VIDEO': '视频',
      'kind.IMAGE': '图片',
      'kind.COPY': '文案',
      'approval.NOT_REQUESTED': '未提交',
      'approval.PENDING': '等待审核',
      'approval.APPROVED': '审核通过',
      'approval.REJECTED': '需要修改',
    },
    'en': {
      'subtitle':
          'Keep the brief, versions, review and delivery on one production line.',
      'refresh': 'Refresh content queue',
      'focus': 'Brand focus',
      'globalRange': 'Global brand range',
      'allBrands': 'Authorized global brand set',
      'brandUnknown': 'Brand name unavailable',
      'inspector': 'Version check',
      'inspectorEmpty':
          'Choose a sourced asset to inspect its version and review state.',
      'stageLabel': 'Current stage',
      'kindLabel': 'Content type',
      'approvalLabel': 'Review progress',
      'lineageReady': 'Source attached',
      'queueTitle': 'Production queue',
      'noAssets': 'No content versions are available for this brand.',
      'unavailableTitle': 'Content production is unavailable',
      'unavailableDetail':
          'The brand range or source material is not confirmed. Content from another brand stays hidden, and missing data is not shown as zero.',
      'notCollectedTitle': 'Content material has not been collected',
      'notCollectedDetail':
          'Briefs, versions, review and delivery states will appear when source material is ready.',
      'actionBlocked':
          'This action is not available in the current brand range or review state.',
      'actionStaged':
          'Local content request draft saved. No content was created, submitted or published.',
      'publishGuard':
          'This only saves a local request draft. Content is not published until authorization, approval and a confirmed result are ready.',
      'loading': 'Loading content production queue',
      'signIn': 'Sign in to view content',
      'accessDenied': 'This account cannot view content right now',
      'offline': 'Content service is unavailable',
      'retryDetail':
          'Check the connection and try again. Unconfirmed content stays hidden.',
      'newContent': 'Save content draft',
      'submitReview': 'Save review request draft',
      'publish': 'Save publishing request draft',
      'stage.BRIEF': 'Brief',
      'stage.DRAFT': 'Draft',
      'stage.REVIEW': 'In review',
      'stage.APPROVED': 'Approved',
      'stage.SCHEDULED': 'Scheduled',
      'stage.DELIVERED': 'Delivered',
      'kind.BRIEF': 'Brief',
      'kind.DRAFT': 'Copy draft',
      'kind.VIDEO': 'Video',
      'kind.IMAGE': 'Image',
      'kind.COPY': 'Copy',
      'approval.NOT_REQUESTED': 'Not submitted',
      'approval.PENDING': 'Awaiting review',
      'approval.APPROVED': 'Approved',
      'approval.REJECTED': 'Needs changes',
    },
    'ko': {
      'subtitle': '브리프, 버전, 검토와 전달을 하나의 제작 흐름으로 관리합니다.',
      'refresh': '콘텐츠 대기열 새로고침',
      'focus': '현재 브랜드',
      'globalRange': '글로벌 브랜드 범위',
      'allBrands': '승인된 글로벌 브랜드 집합',
      'brandUnknown': '브랜드 이름을 사용할 수 없습니다',
      'inspector': '버전 확인',
      'inspectorEmpty': '출처가 연결된 콘텐츠를 선택해 버전과 검토 상태를 확인하세요.',
      'stageLabel': '현재 단계',
      'kindLabel': '콘텐츠 유형',
      'approvalLabel': '검토 진행',
      'lineageReady': '출처 연결됨',
      'queueTitle': '제작 대기열',
      'noAssets': '이 브랜드에서 표시할 콘텐츠 버전이 없습니다.',
      'unavailableTitle': '콘텐츠 제작 자료를 사용할 수 없습니다',
      'unavailableDetail':
          '브랜드 범위 또는 자료 출처가 확인되지 않았습니다. 다른 브랜드의 콘텐츠를 표시하지 않으며 누락을 0으로 바꾸지 않습니다.',
      'notCollectedTitle': '아직 콘텐츠 자료가 수집되지 않았습니다',
      'notCollectedDetail': '자료가 준비되면 브리프, 버전, 검토와 전달 상태가 표시됩니다.',
      'actionBlocked': '현재 브랜드 범위 또는 검토 상태에서는 이 작업을 사용할 수 없습니다.',
      'actionStaged': '콘텐츠 요청 초안을 로컬에 저장했습니다. 콘텐츠를 생성, 제출 또는 게시하지 않았습니다.',
      'publishGuard':
          '여기서는 로컬 요청 초안만 저장합니다. 접근, 승인과 확인된 결과가 준비될 때까지 콘텐츠를 게시하지 않습니다.',
      'loading': '콘텐츠 제작 대기열을 불러오는 중',
      'signIn': '콘텐츠를 보려면 로그인하세요',
      'accessDenied': '이 계정은 지금 콘텐츠를 볼 수 없습니다',
      'offline': '콘텐츠 서비스에 연결할 수 없습니다',
      'retryDetail': '연결을 확인하고 다시 시도하세요. 확인되지 않은 콘텐츠는 숨겨집니다.',
      'newContent': '콘텐츠 초안 저장',
      'submitReview': '검토 요청 초안 저장',
      'publish': '게시 요청 초안 저장',
      'stage.BRIEF': '브리프',
      'stage.DRAFT': '초안',
      'stage.REVIEW': '검토 중',
      'stage.APPROVED': '승인됨',
      'stage.SCHEDULED': '예약됨',
      'stage.DELIVERED': '전달됨',
      'kind.BRIEF': '브리프',
      'kind.DRAFT': '문구 초안',
      'kind.VIDEO': '영상',
      'kind.IMAGE': '이미지',
      'kind.COPY': '문구',
      'approval.NOT_REQUESTED': '미제출',
      'approval.PENDING': '검토 대기',
      'approval.APPROVED': '검토 승인',
      'approval.REJECTED': '수정 필요',
    },
  };
}
