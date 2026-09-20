import 'package:flutter/material.dart';

import '../../core/lumenis_core_client.dart';
import '../../core/lumenis_theme.dart';
import 'ai01_repository.dart';
import 'ai01_snapshot.dart';
import 'ai01_view_model.dart';

const _submitBlockedReason = '当前尚未确认可处理的经营主体或品牌，暂不能开始分析。';

class Ai01Screen extends StatefulWidget {
  const Ai01Screen({required this.client, this.repository, super.key});

  final LumenisCoreClient client;
  final Ai01Repository? repository;

  @override
  State<Ai01Screen> createState() => _Ai01ScreenState();
}

class _Ai01ScreenState extends State<Ai01Screen> {
  late final Ai01ViewModel _viewModel = Ai01ViewModel(
    repository: widget.repository ?? CoreAi01Repository(client: widget.client),
  );
  final TextEditingController _draftController = TextEditingController();
  bool _showInspector = false;

  @override
  void initState() {
    super.initState();
    _draftController.addListener(_syncDraft);
    _viewModel.refresh();
  }

  @override
  void dispose() {
    _draftController
      ..removeListener(_syncDraft)
      ..dispose();
    _viewModel.dispose();
    super.dispose();
  }

  void _syncDraft() => _viewModel.updateDraft(_draftController.text);

  void _chooseSuggestion(Ai01Suggestion suggestion) {
    _viewModel.useSuggestion(suggestion);
    _draftController.value = TextEditingValue(
      text: _viewModel.draft,
      selection: TextSelection.collapsed(offset: _viewModel.draft.length),
    );
  }

  @override
  Widget build(BuildContext context) {
    return ColoredBox(
      color: LumenisTheme.canvas,
      child: SafeArea(
        child: AnimatedBuilder(
          animation: _viewModel,
          builder: (context, _) => _buildState(context),
        ),
      ),
    );
  }

  Widget _buildState(BuildContext context) {
    return switch (_viewModel.phase) {
      Ai01LoadPhase.loading => const _LoadingState(),
      Ai01LoadPhase.failed => _FailureState(
        kind: _viewModel.failureKind!,
        onRetry: _viewModel.refresh,
      ),
      Ai01LoadPhase.ready => _buildWorkbench(_viewModel.snapshot!),
    };
  }

  Widget _buildWorkbench(Ai01Snapshot snapshot) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final width = constraints.maxWidth;
        final wide = width >= 1100;
        final phone = width < 768;
        final inset = phone ? 18.0 : 36.0;

        return Align(
          alignment: Alignment.topCenter,
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1440),
            child: SingleChildScrollView(
              padding: EdgeInsets.fromLTRB(inset, 26, inset, 40),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const _PageHeading(),
                  const SizedBox(height: 22),
                  const _ContextBoundary(),
                  const SizedBox(height: 22),
                  if (!snapshot.isBound) ...[
                    const _RuntimeUnboundNotice(),
                    const SizedBox(height: 18),
                  ],
                  if (wide)
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Expanded(
                          flex: 7,
                          child: _ComposerPane(
                            controller: _draftController,
                            blockedReason: _submitBlockedReason,
                            suggestions: snapshot.suggestions,
                            onChooseSuggestion: _chooseSuggestion,
                          ),
                        ),
                        const SizedBox(width: 18),
                        Expanded(
                          flex: 5,
                          child: _EvidenceInspector(snapshot: snapshot),
                        ),
                      ],
                    )
                  else ...[
                    _ComposerPane(
                      controller: _draftController,
                      blockedReason: _submitBlockedReason,
                      suggestions: snapshot.suggestions,
                      onChooseSuggestion: _chooseSuggestion,
                    ),
                    if (phone)
                      _MobileEvidenceSections(snapshot: snapshot)
                    else ...[
                      const SizedBox(height: 14),
                      Align(
                        alignment: Alignment.centerLeft,
                        child: TextButton.icon(
                          onPressed: () =>
                              setState(() => _showInspector = !_showInspector),
                          icon: Icon(
                            _showInspector
                                ? Icons.expand_less
                                : Icons.account_tree_outlined,
                          ),
                          label: Text(_showInspector ? '收起资料依据' : '查看资料依据'),
                        ),
                      ),
                      AnimatedSize(
                        duration:
                            MediaQuery.maybeOf(context)?.disableAnimations ==
                                true
                            ? Duration.zero
                            : const Duration(milliseconds: 180),
                        curve: Curves.easeOut,
                        child: _showInspector
                            ? Padding(
                                padding: const EdgeInsets.only(top: 12),
                                child: _EvidenceInspector(snapshot: snapshot),
                              )
                            : const SizedBox.shrink(),
                      ),
                    ],
                  ],
                  const SizedBox(height: 18),
                  const _TruthBoundaryNote(),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}

class _PageHeading extends StatelessWidget {
  const _PageHeading();

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const _AccentMark(),
            const SizedBox(width: 10),
            Text(
              'AI 助手',
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                color: LumenisTheme.ai,
                letterSpacing: 1.2,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        Text(
          'AI 意图入口',
          style: Theme.of(context).textTheme.headlineMedium?.copyWith(
            color: LumenisTheme.foreground,
            fontWeight: FontWeight.w600,
            letterSpacing: -0.6,
          ),
        ),
        const SizedBox(height: 6),
        Text(
          '描述想弄清的问题，查看可用资料和模型服务状态。',
          style: Theme.of(
            context,
          ).textTheme.bodyMedium?.copyWith(color: LumenisTheme.muted),
        ),
      ],
    );
  }
}

class _AccentMark extends StatelessWidget {
  const _AccentMark();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 9,
      height: 9,
      decoration: const BoxDecoration(
        color: LumenisTheme.ai,
        shape: BoxShape.circle,
      ),
    );
  }
}

class _ContextBoundary extends StatelessWidget {
  const _ContextBoundary();

  @override
  Widget build(BuildContext context) {
    return Semantics(
      container: true,
      liveRegion: true,
      label: '尚未确认可用的经营主体或品牌',
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        decoration: BoxDecoration(
          color: LumenisTheme.surface,
          border: Border.all(
            color: LumenisTheme.caution.withValues(alpha: 0.48),
          ),
          borderRadius: BorderRadius.circular(14),
        ),
        child: const Wrap(
          spacing: 10,
          runSpacing: 8,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            Icon(Icons.lock_outline, color: LumenisTheme.caution, size: 18),
            Text(
              '尚未确认可用的经营对象',
              style: TextStyle(
                color: LumenisTheme.foreground,
                fontWeight: FontWeight.w600,
              ),
            ),
            Text(
              '当前尚未确认可处理的经营主体或品牌，暂不能开始分析。',
              style: TextStyle(color: LumenisTheme.muted),
            ),
          ],
        ),
      ),
    );
  }
}

class _RuntimeUnboundNotice extends StatelessWidget {
  const _RuntimeUnboundNotice();

  @override
  Widget build(BuildContext context) {
    return _SurfacePanel(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(Icons.sync_problem, color: LumenisTheme.caution, size: 20),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              '暂未读取到完整的 AI 服务状态；未确认的信息不会用示例补齐。',
              style: Theme.of(
                context,
              ).textTheme.bodyMedium?.copyWith(color: LumenisTheme.muted),
            ),
          ),
        ],
      ),
    );
  }
}

class _ComposerPane extends StatelessWidget {
  const _ComposerPane({
    required this.controller,
    required this.blockedReason,
    required this.suggestions,
    required this.onChooseSuggestion,
  });

  final TextEditingController controller;
  final String blockedReason;
  final List<Ai01Suggestion> suggestions;
  final ValueChanged<Ai01Suggestion> onChooseSuggestion;

  @override
  Widget build(BuildContext context) {
    return _SurfacePanel(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text('意图草稿', style: Theme.of(context).textTheme.titleMedium),
              const Spacer(),
              const _StatusTag(label: '不会自动发送', color: LumenisTheme.ai),
            ],
          ),
          const SizedBox(height: 12),
          TextField(
            controller: controller,
            minLines: 5,
            maxLines: 9,
            maxLength: 4000,
            textInputAction: TextInputAction.newline,
            decoration: const InputDecoration(
              hintText: '描述要分析的问题。离开页面后，草稿不会保留。',
              alignLabelWithHint: true,
              border: InputBorder.none,
            ),
          ),
          if (suggestions.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(
              '可参考的分析问题',
              style: Theme.of(
                context,
              ).textTheme.labelMedium?.copyWith(color: LumenisTheme.muted),
            ),
            const SizedBox(height: 6),
            Wrap(
              spacing: 8,
              runSpacing: 4,
              children: [
                for (final suggestion in suggestions)
                  if (suggestion.intent != null)
                    TextButton(
                      onPressed: () => onChooseSuggestion(suggestion),
                      child: Text(suggestion.title),
                    ),
              ],
            ),
          ],
          const SizedBox(height: 12),
          const Divider(height: 1),
          const SizedBox(height: 12),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Text(
                  blockedReason,
                  style: Theme.of(
                    context,
                  ).textTheme.bodySmall?.copyWith(color: LumenisTheme.caution),
                ),
              ),
              const SizedBox(width: 12),
              Tooltip(
                message: blockedReason,
                child: FilledButton.icon(
                  onPressed: null,
                  icon: const Icon(Icons.arrow_forward, size: 18),
                  label: const Text('开始分析'),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          const Text(
            '草稿只保留在此页面；目前还不能开始分析。',
            style: TextStyle(color: LumenisTheme.quiet, fontSize: 12),
          ),
        ],
      ),
    );
  }
}

class _EvidenceInspector extends StatelessWidget {
  const _EvidenceInspector({required this.snapshot});

  final Ai01Snapshot snapshot;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _EvidencePanel(),
        const SizedBox(height: 12),
        _ProviderPanel(providers: snapshot.providers),
        const SizedBox(height: 12),
        _ExecutionPanel(),
      ],
    );
  }
}

class _EvidencePanel extends StatelessWidget {
  const _EvidencePanel();

  @override
  Widget build(BuildContext context) {
    return _SurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _PanelEyebrow(label: '业务资料依据'),
          const SizedBox(height: 12),
          Text(
            '当前账号与经营主体或品牌的查看权限尚未确认，因此暂不展示资料总数或历史内容。',
            style: Theme.of(
              context,
            ).textTheme.bodyMedium?.copyWith(color: LumenisTheme.muted),
          ),
          const SizedBox(height: 14),
          const _TraceBoundary(),
        ],
      ),
    );
  }
}

class _TraceBoundary extends StatelessWidget {
  const _TraceBoundary();

  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    padding: const EdgeInsets.all(12),
    decoration: BoxDecoration(
      color: LumenisTheme.canvas,
      border: Border.all(color: LumenisTheme.line),
      borderRadius: BorderRadius.circular(10),
    ),
    child: const Text(
      '当前账号与经营主体或品牌的查看权限尚未确认，因此不展示资料总数或历史明细。',
      style: TextStyle(color: LumenisTheme.muted, height: 1.5),
    ),
  );
}

class _ProviderPanel extends StatelessWidget {
  const _ProviderPanel({required this.providers});

  final List<Ai01ProviderState> providers;

  @override
  Widget build(BuildContext context) {
    return _SurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _PanelEyebrow(label: '模型服务状态'),
          const SizedBox(height: 9),
          if (providers.isEmpty)
            const Text(
              '暂未收到模型服务的状态。',
              style: TextStyle(color: LumenisTheme.muted),
            )
          else
            for (final provider in providers) ...[
              _ProviderRow(provider: provider),
              if (provider != providers.last) const Divider(height: 1),
            ],
        ],
      ),
    );
  }
}

class _ProviderRow extends StatelessWidget {
  const _ProviderRow({required this.provider});

  final Ai01ProviderState provider;

  @override
  Widget build(BuildContext context) {
    final color = switch (provider.state) {
      'ok' => LumenisTheme.positive,
      'idle' => LumenisTheme.caution,
      'offline' => LumenisTheme.danger,
      _ => LumenisTheme.quiet,
    };

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 9),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.only(top: 3),
            child: _StateDot(color: color),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  _providerDisplayName(provider.name),
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          Text(
            _providerStateLabel(provider.state),
            style: TextStyle(color: color, fontSize: 12),
          ),
        ],
      ),
    );
  }
}

class _ExecutionPanel extends StatelessWidget {
  const _ExecutionPanel();

  @override
  Widget build(BuildContext context) {
    return _SurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _PanelEyebrow(label: '近期分析记录'),
          const SizedBox(height: 9),
          Text(
            '当前账号可查看的经营范围尚未确认，暂时无法显示近期分析记录。',
            style: Theme.of(
              context,
            ).textTheme.bodySmall?.copyWith(color: LumenisTheme.muted),
          ),
        ],
      ),
    );
  }
}

class _MobileEvidenceSections extends StatelessWidget {
  const _MobileEvidenceSections({required this.snapshot});

  final Ai01Snapshot snapshot;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        const SizedBox(height: 12),
        _DisclosureSection(
          title: '数据依据',
          icon: Icons.account_tree_outlined,
          child: _EvidencePanel(),
        ),
        const SizedBox(height: 8),
        _DisclosureSection(
          title: '模型服务状态',
          icon: Icons.hub_outlined,
          child: _ProviderPanel(providers: snapshot.providers),
        ),
        const SizedBox(height: 8),
        _DisclosureSection(
          title: '近期分析记录',
          icon: Icons.history,
          child: _ExecutionPanel(),
        ),
      ],
    );
  }
}

class _DisclosureSection extends StatelessWidget {
  const _DisclosureSection({
    required this.title,
    required this.icon,
    required this.child,
  });

  final String title;
  final IconData icon;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Theme(
      data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
      child: ExpansionTile(
        leading: Icon(icon, color: LumenisTheme.shared),
        title: Text(title),
        tilePadding: const EdgeInsets.symmetric(horizontal: 12),
        childrenPadding: const EdgeInsets.only(bottom: 8),
        collapsedShape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(14),
          side: const BorderSide(color: LumenisTheme.line),
        ),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(14),
          side: const BorderSide(color: LumenisTheme.line),
        ),
        backgroundColor: LumenisTheme.surface,
        collapsedBackgroundColor: LumenisTheme.surface,
        children: [child],
      ),
    );
  }
}

class _TruthBoundaryNote extends StatelessWidget {
  const _TruthBoundaryNote();

  @override
  Widget build(BuildContext context) {
    return Text(
      'AI 提供整理与建议；经营数据、原始资料、授权范围和业务结论仍以各自业务记录为准。',
      style: Theme.of(
        context,
      ).textTheme.bodySmall?.copyWith(color: LumenisTheme.quiet),
    );
  }
}

class _PanelEyebrow extends StatelessWidget {
  const _PanelEyebrow({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Text(
      label,
      style: Theme.of(context).textTheme.labelSmall?.copyWith(
        color: LumenisTheme.quiet,
        letterSpacing: 0.9,
        fontWeight: FontWeight.w700,
      ),
    );
  }
}

class _StatusTag extends StatelessWidget {
  const _StatusTag({required this.label, required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        border: Border.all(color: color.withValues(alpha: 0.35)),
        borderRadius: BorderRadius.circular(99),
      ),
      child: Text(label, style: TextStyle(color: color, fontSize: 11)),
    );
  }
}

class _StateDot extends StatelessWidget {
  const _StateDot({required this.color});

  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 8,
      height: 8,
      decoration: BoxDecoration(color: color, shape: BoxShape.circle),
    );
  }
}

class _SurfacePanel extends StatelessWidget {
  const _SurfacePanel({
    required this.child,
    this.padding = const EdgeInsets.all(16),
  });

  final Widget child;
  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: padding,
      decoration: BoxDecoration(
        color: LumenisTheme.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: LumenisTheme.line),
      ),
      child: child,
    );
  }
}

class _LoadingState extends StatelessWidget {
  const _LoadingState();

  @override
  Widget build(BuildContext context) {
    return const Center(
      child: Padding(
        padding: EdgeInsets.all(28),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            CircularProgressIndicator(color: LumenisTheme.ai),
            SizedBox(height: 14),
            Text('正在读取 AI 服务状态', style: TextStyle(color: LumenisTheme.muted)),
          ],
        ),
      ),
    );
  }
}

class _FailureState extends StatelessWidget {
  const _FailureState({required this.kind, required this.onRetry});

  final Ai01FailureKind kind;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final title = switch (kind) {
      Ai01FailureKind.authentication => '需要登录',
      Ai01FailureKind.permissionDenied => '暂时无法查看',
      Ai01FailureKind.offline => 'AI 服务暂时无法连接',
      Ai01FailureKind.server => '暂时无法读取 AI 服务状态',
    };
    final explanation = switch (kind) {
      Ai01FailureKind.authentication => '请登录后再查看 AI 服务状态。',
      Ai01FailureKind.permissionDenied => '当前账号没有查看 AI 服务状态的权限。',
      Ai01FailureKind.offline => '请检查网络连接后重试。',
      Ai01FailureKind.server => '请稍后重新读取服务状态。',
    };

    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 520),
          child: _SurfacePanel(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: Theme.of(context).textTheme.titleLarge),
                const SizedBox(height: 8),
                Text(
                  explanation,
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
                const SizedBox(height: 14),
                FilledButton.icon(
                  onPressed: onRetry,
                  icon: const Icon(Icons.refresh),
                  label: const Text('重新读取'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

String _providerDisplayName(String name) => switch (name.trim()) {
  '' || 'Provider' => 'AI 模型服务',
  _ => name,
};

String _providerStateLabel(String state) =>
    switch (state.trim().toLowerCase()) {
      'ok' => '可用',
      'idle' => '未启动',
      'offline' => '暂不可用',
      _ => '状态待确认',
    };
