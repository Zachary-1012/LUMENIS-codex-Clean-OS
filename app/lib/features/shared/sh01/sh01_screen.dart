import 'package:flutter/material.dart';

import '../../../core/lumenis_core_client.dart';
import '../../../core/lumenis_theme.dart';
import 'sh01_repository.dart';
import 'sh01_snapshot.dart';
import 'sh01_view_model.dart';

String _catalogFailureCopy(String? error) => switch (error) {
  '登录已失效，请重新登录后读取。' => '登录状态已过期，请重新登录后查看工具目录。',
  '当前账号无权读取共享能力目录。' => '当前账号暂不能查看工具目录。',
  'Product Core 暂时不可用。' => '工具目录服务暂时无法连接，请检查网络后重试。',
  _ => '工具目录数据暂不可用，请稍后重试。',
};

String _catalogTitle(String title) => switch (title.trim()) {
  'Shared Content & Creation' => '共享内容与创作',
  '' => '研究与创作服务',
  final value
      when value.runes.any((rune) => rune >= 0x4e00 && rune <= 0x9fff) =>
    value,
  _ => '研究与创作服务',
};

String _providerTeam(String owner) => switch (owner.trim()) {
  'Shared Capability / Content Studio' => '共享内容与创作团队',
  final value
      when value.runes.any((rune) => rune >= 0x4e00 && rune <= 0x9fff) =>
    value,
  '' => '目录未注明',
  _ => '目录已登记的提供团队',
};

String _categoryLabel(String category) =>
    switch (category.trim().toUpperCase()) {
      'RESEARCH' => '研究资料',
      'CONTENT' => '内容创作',
      '' => '未分类',
      final value
          when value.runes.any((rune) => rune >= 0x4e00 && rune <= 0x9fff) =>
        category.trim(),
      _ => '未分类',
    };

String _permissionLabel(String permission) {
  const labels = {
    'READ': '读取',
    'RESEARCH': '研究资料',
    'ANALYZE': '分析',
    'SUGGEST': '提供建议',
    'AUDIT': '检查',
    'WRITE': '修改',
    'EXPORT': '导出',
    'PUBLISH': '发布',
  };
  final parts = permission
      .split(RegExp(r'\s*/\s*'))
      .map((part) => part.trim().toUpperCase())
      .toList(growable: false);
  if (parts.isEmpty || parts.any((part) => !labels.containsKey(part))) {
    return '以当前账号权限为准';
  }
  return parts.map((part) => labels[part]!).join('、');
}

String _riskLabel(String risk) => switch (risk.trim().toUpperCase()) {
  'LOW' => '低',
  'MEDIUM' => '中',
  'HIGH' => '高',
  _ => '未说明',
};

String _useLimitLabel(String policy) => switch (policy.trim().toUpperCase()) {
  'READ_ONLY' => '仅读取资料，不修改原始内容',
  'NO_EXTERNAL_WRITE' => '不会直接向外部平台提交内容',
  'APPROVAL_REQUIRED' => '操作前需要审核',
  'AUDIT_ONLY' => '仅供检查',
  _ => '目录暂未说明',
};

String _businessDescription(String description) => description
    .replaceAll('已入库 Evidence', '已入库资料')
    .replaceAll(RegExp('Evidence', caseSensitive: false), '资料依据')
    .replaceAll(RegExp(r'\bBrief\b', caseSensitive: false), '需求说明')
    .replaceAll(RegExp(r'Canonical Data', caseSensitive: false), '正式业务数据')
    .replaceAll(RegExp(r'\bCanonical\b', caseSensitive: false), '正式记录')
    .replaceAll(RegExp(r'\bSVG\b', caseSensitive: false), '矢量图')
    .replaceAll(RegExp(r'\bArtifact\b', caseSensitive: false), '成果')
    .replaceAll(RegExp(r'(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])'), '');

class Sh01Screen extends StatefulWidget {
  const Sh01Screen({required this.client, this.repository, super.key});

  final LumenisCoreClient client;
  final Sh01Repository? repository;

  @override
  State<Sh01Screen> createState() => _Sh01ScreenState();
}

class _Sh01ScreenState extends State<Sh01Screen> {
  late final Sh01ViewModel _viewModel = Sh01ViewModel(
    repository: widget.repository ?? CoreSh01Repository(client: widget.client),
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
    color: LumenisTheme.canvas,
    child: SafeArea(
      child: AnimatedBuilder(
        animation: _viewModel,
        builder: (context, _) => switch (_viewModel.phase) {
          Sh01LoadPhase.loading => const _LoadingState(),
          Sh01LoadPhase.failed => _FailureState(
            message: _catalogFailureCopy(_viewModel.error),
            onRetry: _viewModel.refresh,
          ),
          Sh01LoadPhase.ready => _Workspace(
            viewModel: _viewModel,
            catalog: _viewModel.catalog!,
          ),
        },
      ),
    ),
  );
}

class _Workspace extends StatelessWidget {
  const _Workspace({required this.viewModel, required this.catalog});

  final Sh01ViewModel viewModel;
  final Sh01Catalog catalog;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, constraints) {
      final wide = constraints.maxWidth >= 1120;
      final medium = constraints.maxWidth >= 760;
      final inset = wide ? 30.0 : 18.0;
      final index = _CapabilityIndex(
        catalog: catalog,
        selected: viewModel.selected,
        onSelect: viewModel.select,
      );
      final detail = _CapabilityDetail(capability: viewModel.selected);
      return Align(
        alignment: Alignment.topCenter,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1480),
          child: SingleChildScrollView(
            padding: EdgeInsets.fromLTRB(inset, 24, inset, 36),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const _Heading(),
                const SizedBox(height: 22),
                if (wide)
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      SizedBox(
                        width: 270,
                        child: _SharedCharter(catalog: catalog),
                      ),
                      const SizedBox(width: 16),
                      SizedBox(width: 365, child: index),
                      const SizedBox(width: 16),
                      Expanded(child: detail),
                    ],
                  )
                else if (medium)
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      SizedBox(
                        width: 260,
                        child: _SharedCharter(catalog: catalog),
                      ),
                      const SizedBox(width: 14),
                      Expanded(child: index),
                    ],
                  )
                else ...[
                  _SharedCharter(catalog: catalog),
                  const SizedBox(height: 14),
                  index,
                ],
                if (!wide && viewModel.selected != null) ...[
                  const SizedBox(height: 14),
                  detail,
                ],
                const SizedBox(height: 14),
                const _EvidenceBoundary(),
                const SizedBox(height: 14),
                Align(
                  alignment: Alignment.centerLeft,
                  child: OutlinedButton.icon(
                    onPressed: viewModel.refresh,
                    icon: const Icon(Icons.refresh_rounded),
                    label: const Text('重新读取能力目录'),
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

class _Heading extends StatelessWidget {
  const _Heading();

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Row(
        children: [
          Container(
            width: 8,
            height: 28,
            decoration: BoxDecoration(
              color: LumenisTheme.shared,
              borderRadius: BorderRadius.circular(8),
            ),
          ),
          const SizedBox(width: 11),
          Text(
            '研究与创作',
            style: Theme.of(context).textTheme.labelSmall?.copyWith(
              color: LumenisTheme.shared,
              letterSpacing: 1,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
      const SizedBox(height: 13),
      Text(
        '研究与创作工具',
        style: Theme.of(context).textTheme.headlineMedium?.copyWith(
          color: LumenisTheme.foreground,
          fontWeight: FontWeight.w600,
          letterSpacing: -0.5,
        ),
      ),
      const SizedBox(height: 7),
      Text(
        '查看可供 CTH 与 BMP 使用的研究和内容工具；条目介绍用途，不代表此刻可以使用。',
        style: Theme.of(
          context,
        ).textTheme.bodyMedium?.copyWith(color: LumenisTheme.muted),
      ),
    ],
  );
}

class _SharedCharter extends StatelessWidget {
  const _SharedCharter({required this.catalog});

  final Sh01Catalog catalog;

  @override
  Widget build(BuildContext context) => _Panel(
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const _Eyebrow('服务提供方'),
        const SizedBox(height: 16),
        Container(
          width: 52,
          height: 52,
          decoration: BoxDecoration(
            color: LumenisTheme.shared.withValues(alpha: 0.1),
            border: Border.all(
              color: LumenisTheme.shared.withValues(alpha: 0.35),
            ),
            borderRadius: BorderRadius.circular(15),
          ),
          child: const Icon(
            Icons.hub_outlined,
            color: LumenisTheme.shared,
            size: 25,
          ),
        ),
        const SizedBox(height: 14),
        Text(
          _catalogTitle(catalog.capability),
          style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: 8),
        const Text(
          '这些服务供 CTH 与 BMP 的业务流程共同使用，但不会替代各自的经营主体、品牌资料或业务结论。',
          style: TextStyle(color: LumenisTheme.muted, height: 1.5),
        ),
        const SizedBox(height: 17),
        const Divider(height: 1),
        const SizedBox(height: 14),
        const _Eyebrow('适用产品'),
        const SizedBox(height: 9),
        Wrap(
          spacing: 7,
          runSpacing: 7,
          children: [
            for (final consumer in catalog.consumers) _MetaChip(consumer),
          ],
        ),
        const SizedBox(height: 16),
        const Text(
          '此处只查看工具介绍，不会运行工具。实际使用前还需确认业务对象和当前账号权限。',
          style: TextStyle(
            color: LumenisTheme.quiet,
            fontSize: 12,
            height: 1.5,
          ),
        ),
      ],
    ),
  );
}

class _CapabilityIndex extends StatelessWidget {
  const _CapabilityIndex({
    required this.catalog,
    required this.selected,
    required this.onSelect,
  });

  final Sh01Catalog catalog;
  final Sh01Capability? selected;
  final ValueChanged<Sh01Capability> onSelect;

  @override
  Widget build(BuildContext context) => _Panel(
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const Expanded(child: _Eyebrow('工具列表')),
            Text(
              catalog.skills.length.toString(),
              style: const TextStyle(
                color: LumenisTheme.shared,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        if (catalog.skills.isEmpty)
          const _InfoMessage('当前没有可展示的研究或创作工具。')
        else
          for (final item in catalog.skills)
            _CapabilityRow(
              item: item,
              selected: selected?.id == item.id,
              onTap: () => onSelect(item),
            ),
      ],
    ),
  );
}

class _CapabilityRow extends StatelessWidget {
  const _CapabilityRow({
    required this.item,
    required this.selected,
    required this.onTap,
  });

  final Sh01Capability item;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 7),
    child: Material(
      color: selected
          ? LumenisTheme.shared.withValues(alpha: 0.09)
          : LumenisTheme.surfaceRaised,
      borderRadius: BorderRadius.circular(11),
      child: InkWell(
        key: Key('sh01-capability-${item.id}'),
        onTap: onTap,
        borderRadius: BorderRadius.circular(11),
        child: Container(
          constraints: const BoxConstraints(minHeight: 62),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          decoration: BoxDecoration(
            border: Border.all(
              color: selected
                  ? LumenisTheme.shared.withValues(alpha: 0.55)
                  : LumenisTheme.line,
            ),
            borderRadius: BorderRadius.circular(11),
          ),
          child: Row(
            children: [
              Container(
                width: 30,
                height: 30,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: LumenisTheme.canvas,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Icon(
                  Icons.extension_outlined,
                  size: 17,
                  color: selected ? LumenisTheme.shared : LumenisTheme.quiet,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      item.name,
                      style: const TextStyle(fontWeight: FontWeight.w600),
                    ),
                    if (item.category.isNotEmpty) ...[
                      const SizedBox(height: 3),
                      Text(
                        _categoryLabel(item.category),
                        style: const TextStyle(
                          color: LumenisTheme.muted,
                          fontSize: 11,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
              const Icon(
                Icons.chevron_right_rounded,
                color: LumenisTheme.quiet,
              ),
            ],
          ),
        ),
      ),
    ),
  );
}

class _CapabilityDetail extends StatelessWidget {
  const _CapabilityDetail({required this.capability});

  final Sh01Capability? capability;

  @override
  Widget build(BuildContext context) => _Panel(
    child: capability == null
        ? const _InfoMessage('目录中暂时没有可查看的工具。')
        : _CapabilityFacts(capability: capability!),
  );
}

class _CapabilityFacts extends StatelessWidget {
  const _CapabilityFacts({required this.capability});

  final Sh01Capability capability;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Row(children: [const Expanded(child: _Eyebrow('工具介绍'))]),
      const SizedBox(height: 17),
      Text(capability.name, style: Theme.of(context).textTheme.headlineSmall),
      if (capability.description.isNotEmpty) ...[
        const SizedBox(height: 10),
        Text(
          _businessDescription(capability.description),
          style: const TextStyle(color: LumenisTheme.muted, height: 1.6),
        ),
      ],
      const SizedBox(height: 22),
      const _Eyebrow('使用信息'),
      const SizedBox(height: 11),
      _FactRow('提供团队', _providerTeam(capability.owner)),
      _FactRow('内容类别', _categoryLabel(capability.category)),
      _FactRow('适用产品', capability.consumers.join(' · ')),
      _FactRow('可处理内容', _permissionLabel(capability.permission)),
      _FactRow('操作风险', _riskLabel(capability.risk)),
      _FactRow('使用限制', _useLimitLabel(capability.executionPolicy)),
      const SizedBox(height: 15),
      const _InfoMessage('以上为目录介绍，不表示工具当前可用或已替你执行。能否使用取决于所选业务对象和当前账号权限。'),
    ],
  );
}

class _FactRow extends StatelessWidget {
  const _FactRow(this.label, this.value);

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    if (value.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 7),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 150,
            child: Text(
              label,
              style: const TextStyle(color: LumenisTheme.quiet),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: SelectableText(
              value,
              style: const TextStyle(color: LumenisTheme.foreground),
            ),
          ),
        ],
      ),
    );
  }
}

class _EvidenceBoundary extends StatelessWidget {
  const _EvidenceBoundary();

  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    padding: const EdgeInsets.all(16),
    decoration: BoxDecoration(
      color: LumenisTheme.caution.withValues(alpha: 0.07),
      border: Border.all(color: LumenisTheme.caution.withValues(alpha: 0.28)),
      borderRadius: BorderRadius.circular(14),
    ),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Icon(
          Icons.lock_outline_rounded,
          color: LumenisTheme.caution,
          size: 19,
        ),
        const SizedBox(width: 11),
        const Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('业务资料依据暂不显示', style: TextStyle(fontWeight: FontWeight.w600)),
              SizedBox(height: 5),
              Text(
                '当前资料还未按你的账号和经营主体或品牌完成查看权限核对，因此暂不展示记录数量、详情或内容。',
                style: TextStyle(color: LumenisTheme.muted, height: 1.5),
              ),
            ],
          ),
        ),
      ],
    ),
  );
}

class _InfoMessage extends StatelessWidget {
  const _InfoMessage(this.message);

  final String message;

  @override
  Widget build(BuildContext context) => Text(
    message,
    style: const TextStyle(color: LumenisTheme.muted, height: 1.5),
  );
}

class _MetaChip extends StatelessWidget {
  const _MetaChip(this.label);

  final String label;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 6),
    decoration: BoxDecoration(
      color: LumenisTheme.canvas,
      border: Border.all(color: LumenisTheme.line),
      borderRadius: BorderRadius.circular(20),
    ),
    child: Text(
      label,
      style: const TextStyle(color: LumenisTheme.muted, fontSize: 11),
    ),
  );
}

class _Eyebrow extends StatelessWidget {
  const _Eyebrow(this.label);

  final String label;

  @override
  Widget build(BuildContext context) => Text(
    label,
    style: const TextStyle(
      color: LumenisTheme.quiet,
      fontSize: 10,
      letterSpacing: 0.9,
      fontWeight: FontWeight.w700,
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
      color: LumenisTheme.surface,
      borderRadius: BorderRadius.circular(16),
      border: Border.all(color: LumenisTheme.line),
    ),
    child: child,
  );
}

class _LoadingState extends StatelessWidget {
  const _LoadingState();

  @override
  Widget build(BuildContext context) => Center(
    child: Semantics(
      liveRegion: true,
      label: '正在读取研究与创作工具',
      child: const CircularProgressIndicator(color: LumenisTheme.shared),
    ),
  );
}

class _FailureState extends StatelessWidget {
  const _FailureState({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => Center(
    child: Padding(
      padding: const EdgeInsets.all(24),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 520),
        child: _Panel(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('工具目录暂不可用', style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 8),
              Text(message, style: Theme.of(context).textTheme.bodyMedium),
              const SizedBox(height: 16),
              OutlinedButton.icon(
                onPressed: onRetry,
                icon: const Icon(Icons.refresh_rounded),
                label: const Text('重新读取工具目录'),
                style: OutlinedButton.styleFrom(
                  minimumSize: const Size(48, 48),
                ),
              ),
            ],
          ),
        ),
      ),
    ),
  );
}
