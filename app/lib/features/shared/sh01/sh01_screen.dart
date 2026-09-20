import 'package:flutter/material.dart';

import '../../../core/lumenis_core_client.dart';
import '../../../core/lumenis_theme.dart';
import 'sh01_repository.dart';
import 'sh01_snapshot.dart';
import 'sh01_view_model.dart';

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
            message: _viewModel.error ?? '共享能力目录暂不可用。',
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
            'SHARED CAPABILITY  /  SH-01',
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
        '共享能力目录',
        style: Theme.of(context).textTheme.headlineMedium?.copyWith(
          color: LumenisTheme.foreground,
          fontWeight: FontWeight.w600,
          letterSpacing: -0.5,
        ),
      ),
      const SizedBox(height: 7),
      Text(
        '浏览由 Shared Capability 提供给 CTH 与 BMP 的已登记能力。目录元数据不代表运行状态。',
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
        const _Eyebrow('CAPABILITY OWNER'),
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
          catalog.capability.isEmpty ? 'Shared Capability' : catalog.capability,
          style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: 8),
        const Text(
          '共享能力归 Shared Capability 所有，供生态产品复用。它本身不建立 CTH Subject 或 BMP BrandFocus。',
          style: TextStyle(color: LumenisTheme.muted, height: 1.5),
        ),
        const SizedBox(height: 17),
        const Divider(height: 1),
        const SizedBox(height: 14),
        const _Eyebrow('REGISTERED CONSUMERS'),
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
          '此页只浏览目录元数据。READ / ANALYZE / SUGGEST 执行仍需可信的产品域操作者上下文。',
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
            const Expanded(child: _Eyebrow('REGISTERED CAPABILITIES')),
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
          const _InfoMessage('目录没有返回能力项目。')
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
                        item.category,
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
        ? const _InfoMessage('目录暂时没有可查看的能力。')
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
      Row(
        children: [
          const Expanded(child: _Eyebrow('CAPABILITY RECORD')),
          _MetaChip(capability.id),
        ],
      ),
      const SizedBox(height: 17),
      Text(capability.name, style: Theme.of(context).textTheme.headlineSmall),
      if (capability.description.isNotEmpty) ...[
        const SizedBox(height: 10),
        Text(
          capability.description,
          style: const TextStyle(color: LumenisTheme.muted, height: 1.6),
        ),
      ],
      const SizedBox(height: 22),
      const _Eyebrow('REGISTERED POLICY METADATA'),
      const SizedBox(height: 11),
      _FactRow('Owner', capability.owner),
      _FactRow('Category', capability.category),
      _FactRow('Version', capability.version),
      _FactRow('Permission', capability.permission),
      _FactRow('Risk', capability.risk),
      _FactRow('Execution policy', capability.executionPolicy),
      _FactRow('Evaluation registration', capability.evaluationStatus),
      _FactRow('Implementation registration', capability.implementationState),
      _FactRow('Consumers', capability.consumers.join(' · ')),
      const SizedBox(height: 15),
      const _InfoMessage('这些值来自目录登记。它们不表示能力当前可运行，也不是本次调用的 Permission 判定或执行结果。'),
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
              Text(
                'Evidence 读取受 scope contract 阻断',
                style: TextStyle(fontWeight: FontWeight.w600),
              ),
              SizedBox(height: 5),
              Text(
                '现有 SH-01 列表与 detail 路由没有 authenticated actor-to-domain/object scope。此 App 不请求或展示全局 Evidence、数量或正文。待后端返回可验证 scope 与 Permission 结果后再绑定。',
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
      label: '正在读取 Shared Capability 目录',
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
              Text('共享能力目录暂不可读', style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 8),
              Text(message, style: Theme.of(context).textTheme.bodyMedium),
              const SizedBox(height: 16),
              OutlinedButton.icon(
                onPressed: onRetry,
                icon: const Icon(Icons.refresh_rounded),
                label: const Text('重新读取目录'),
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
