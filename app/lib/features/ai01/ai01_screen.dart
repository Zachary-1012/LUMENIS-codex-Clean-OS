import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../core/lumenis_core_client.dart';
import '../../core/lumenis_theme.dart';
import '../../l10n/lumenis_localizations.dart';
import 'ai01_draft_actions.dart';
import 'ai01_repository.dart';
import 'ai01_snapshot.dart';
import 'ai01_view_model.dart';

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
  final FocusNode _draftFocus = FocusNode();
  final GlobalKey _composerKey = GlobalKey(debugLabel: 'ai01-composer');
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
    _draftFocus.dispose();
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

  Future<void> _openFocusedEditor() async {
    final reduceMotion =
        MediaQuery.maybeOf(context)?.disableAnimations ?? false;
    await showDialog<void>(
      context: context,
      useSafeArea: false,
      animationStyle: reduceMotion
          ? AnimationStyle.noAnimation
          : const AnimationStyle(
              duration: Duration(milliseconds: 180),
              reverseDuration: Duration(milliseconds: 180),
              curve: Curves.easeOutCubic,
            ),
      builder: (context) => _FocusedDraftEditor(controller: _draftController),
    );
    if (mounted) _draftFocus.requestFocus();
  }

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(color: LumenisTheme.of(context).canvas),
      child: Stack(
        children: [
          SafeArea(
            child: AnimatedBuilder(
              animation: _viewModel,
              builder: (context, _) => _buildState(context),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildState(BuildContext context) {
    return _buildWorkbench(
      context,
      snapshot: _viewModel.snapshot,
      phase: _viewModel.phase,
      failureKind: _viewModel.failureKind,
      onRetry: _viewModel.refresh,
    );
  }

  Widget _buildWorkbench(
    BuildContext context, {
    required Ai01Snapshot? snapshot,
    required Ai01LoadPhase phase,
    required Ai01FailureKind? failureKind,
    required VoidCallback onRetry,
  }) {
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
              padding: EdgeInsets.fromLTRB(inset, phone ? 18 : 30, inset, 40),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _PageHeading(compact: phone),
                  SizedBox(height: phone ? 12 : 20),
                  if (wide)
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Expanded(
                          flex: 7,
                          child: _ComposerPane(
                            key: _composerKey,
                            controller: _draftController,
                            focusNode: _draftFocus,
                            blockedReason: context.lumenisL10n.text(
                              'ai01.blocked_reason',
                            ),
                            suggestions: snapshot?.suggestions ?? const [],
                            onChooseSuggestion: _chooseSuggestion,
                            onExpand: _openFocusedEditor,
                            compact: false,
                          ),
                        ),
                        const SizedBox(width: 18),
                        Expanded(
                          flex: 5,
                          child: snapshot == null
                              ? _ServiceReadStatus(
                                  phase: phase,
                                  failureKind: failureKind,
                                  onRetry: onRetry,
                                )
                              : _EvidenceInspector(
                                  snapshot: snapshot,
                                  showRuntimeNotice: !snapshot.isBound,
                                ),
                        ),
                      ],
                    )
                  else ...[
                    _ComposerPane(
                      key: _composerKey,
                      controller: _draftController,
                      focusNode: _draftFocus,
                      blockedReason: context.lumenisL10n.text(
                        'ai01.blocked_reason',
                      ),
                      suggestions: snapshot?.suggestions ?? const [],
                      onChooseSuggestion: _chooseSuggestion,
                      onExpand: _openFocusedEditor,
                      compact: phone,
                    ),
                    if (snapshot == null) ...[
                      SizedBox(height: phone ? 12 : 18),
                      _ServiceReadStatus(
                        phase: phase,
                        failureKind: failureKind,
                        onRetry: onRetry,
                      ),
                    ] else if (phone)
                      _MobileEvidenceSections(
                        snapshot: snapshot,
                        showRuntimeNotice: !snapshot.isBound,
                      )
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
                          label: Text(
                            context.lumenisL10n.text(
                              _showInspector
                                  ? 'ai01.inspector.hide'
                                  : 'ai01.inspector.show',
                            ),
                          ),
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
                                child: _EvidenceInspector(
                                  snapshot: snapshot,
                                  showRuntimeNotice: !snapshot.isBound,
                                ),
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
  const _PageHeading({required this.compact});

  final bool compact;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          context.lumenisL10n.text('ai01.title'),
          style:
              (compact
                      ? Theme.of(context).textTheme.headlineMedium
                      : Theme.of(context).textTheme.displaySmall)
                  ?.copyWith(
                    color: LumenisTheme.of(context).foreground,
                    fontSize: compact ? 24 : 28,
                    height: 1.25,
                    fontWeight: FontWeight.w600,
                    letterSpacing: 0,
                  ),
        ),
        if (!compact) ...[
          const SizedBox(height: 6),
          Text(
            context.lumenisL10n.text('ai01.subtitle'),
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              color: LumenisTheme.of(context).muted,
              fontSize: 14,
            ),
          ),
        ],
      ],
    );
  }
}

class _RuntimeUnboundNotice extends StatelessWidget {
  const _RuntimeUnboundNotice();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: LumenisTheme.of(context).ai.withValues(alpha: 0.06),
        border: Border.all(
          color: LumenisTheme.of(context).ai.withValues(alpha: 0.18),
        ),
        borderRadius: BorderRadius.circular(18),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            Icons.sync_problem,
            color: LumenisTheme.of(context).caution,
            size: 20,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              context.lumenisL10n.text('ai01.unbound'),
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: LumenisTheme.of(context).muted,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _ContextBoundary extends StatelessWidget {
  const _ContextBoundary();

  @override
  Widget build(BuildContext context) {
    final label = context.lumenisL10n.text('ai01.context.label');
    return Semantics(
      container: true,
      excludeSemantics: true,
      liveRegion: true,
      label: label,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.only(top: 2),
            child: Icon(
              Icons.lock_outline,
              color: LumenisTheme.of(context).caution,
              size: 16,
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              label,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: LumenisTheme.of(context).muted,
              ),
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
    required this.focusNode,
    required this.blockedReason,
    required this.suggestions,
    required this.onChooseSuggestion,
    required this.onExpand,
    required this.compact,
    super.key,
  });

  final TextEditingController controller;
  final FocusNode focusNode;
  final String blockedReason;
  final List<Ai01Suggestion> suggestions;
  final ValueChanged<Ai01Suggestion> onChooseSuggestion;
  final VoidCallback onExpand;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final safeSuggestions = suggestions
        .where((suggestion) => suggestion.isProductSafe)
        .toList(growable: false);
    return Container(
      key: const ValueKey('ai01-composer-surface'),
      width: double.infinity,
      padding: EdgeInsets.all(compact ? 16 : 22),
      decoration: BoxDecoration(
        color: LumenisTheme.of(context).surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: LumenisTheme.of(context).line),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            alignment: WrapAlignment.spaceBetween,
            crossAxisAlignment: WrapCrossAlignment.center,
            runSpacing: 8,
            children: [
              Text(
                context.lumenisL10n.text('ai01.draft.title'),
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                ),
              ),
              _StatusTag(
                label: context.lumenisL10n.text('ai01.draft.badge'),
                color: LumenisTheme.of(context).ai,
              ),
              TextButton.icon(
                key: const ValueKey('ai01-focus-open'),
                onPressed: onExpand,
                icon: const Icon(Icons.open_in_full_rounded, size: 17),
                label: Text(context.lumenisL10n.text('ai01.focus.open')),
                style: TextButton.styleFrom(minimumSize: const Size(48, 48)),
              ),
            ],
          ),
          const SizedBox(height: 12),
          TextField(
            key: const ValueKey('ai01-task-input'),
            controller: controller,
            focusNode: focusNode,
            style: Theme.of(
              context,
            ).textTheme.bodyLarge?.copyWith(fontSize: 16, height: 1.5),
            minLines: compact ? 4 : 6,
            maxLines: compact ? 8 : 10,
            maxLength: 4000,
            textInputAction: TextInputAction.newline,
            decoration: InputDecoration(
              filled: false,
              isDense: true,
              contentPadding: EdgeInsets.symmetric(
                horizontal: 0,
                vertical: compact ? 8 : 10,
              ),
              counterStyle: TextStyle(color: LumenisTheme.of(context).quiet),
              hintText: context.lumenisL10n.text('ai01.draft.hint'),
              alignLabelWithHint: true,
              border: InputBorder.none,
              enabledBorder: InputBorder.none,
              focusedBorder: UnderlineInputBorder(
                borderSide: BorderSide(
                  color: Theme.of(context).colorScheme.primary,
                  width: 1.5,
                ),
              ),
            ),
          ),
          const SizedBox(height: 8),
          Theme(
            data: Theme.of(context).copyWith(
              textButtonTheme: TextButtonThemeData(
                style: TextButton.styleFrom(minimumSize: const Size(64, 48)),
              ),
            ),
            child: Ai01DraftActions(
              key: const ValueKey('ai01-draft-actions'),
              controller: controller,
              focusNode: focusNode,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            context.lumenisL10n.text('ai01.draft.notice'),
            style: TextStyle(
              color: LumenisTheme.of(context).quiet,
              fontSize: 12,
            ),
          ),
          if (safeSuggestions.isNotEmpty) ...[
            const SizedBox(height: 12),
            Text(
              context.lumenisL10n.text('ai01.suggestions.title'),
              style: Theme.of(context).textTheme.labelMedium?.copyWith(
                color: LumenisTheme.of(context).muted,
              ),
            ),
            const SizedBox(height: 6),
            Wrap(
              spacing: 8,
              runSpacing: 6,
              children: [
                for (final suggestion in safeSuggestions)
                  ActionChip(
                    onPressed: () => onChooseSuggestion(suggestion),
                    label: Text(suggestion.safeTitle!),
                    padding: const EdgeInsets.symmetric(horizontal: 8),
                    backgroundColor: LumenisTheme.of(
                      context,
                    ).ai.withValues(alpha: 0.08),
                    side: BorderSide(
                      color: LumenisTheme.of(
                        context,
                      ).ai.withValues(alpha: 0.18),
                    ),
                    shape: const StadiumBorder(),
                    labelStyle: TextStyle(color: LumenisTheme.of(context).ai),
                  ),
              ],
            ),
          ],
          const SizedBox(height: 14),
          Divider(height: 1, color: LumenisTheme.of(context).line),
          const SizedBox(height: 12),
          if (compact)
            Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const _ContextBoundary(),
                const SizedBox(height: 10),
                SizedBox(
                  height: 48,
                  child: _submitButton(context, blockedReason),
                ),
              ],
            )
          else
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Expanded(child: _ContextBoundary()),
                const SizedBox(width: 12),
                _submitButton(context, blockedReason),
              ],
            ),
          const SizedBox(height: 10),
        ],
      ),
    );
  }
}

class _FocusedDraftEditor extends StatefulWidget {
  const _FocusedDraftEditor({required this.controller});

  final TextEditingController controller;

  @override
  State<_FocusedDraftEditor> createState() => _FocusedDraftEditorState();
}

class _FocusedDraftEditorState extends State<_FocusedDraftEditor> {
  final FocusNode _focus = FocusNode();

  @override
  void dispose() {
    _focus.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    final theme = LumenisTheme.of(context);
    return CallbackShortcuts(
      bindings: {
        const SingleActivator(LogicalKeyboardKey.escape): () =>
            Navigator.of(context).pop(),
      },
      child: Dialog.fullscreen(
        key: const ValueKey('ai01-focus-dialog'),
        backgroundColor: theme.surface.withValues(alpha: 1),
        child: SafeArea(
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 940),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 18),
                child: LayoutBuilder(
                  builder: (context, constraints) {
                    final short = constraints.maxHeight < 340;
                    return Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Align(
                          alignment: Alignment.centerLeft,
                          child: TextButton.icon(
                            key: const ValueKey('ai01-focus-return'),
                            onPressed: () => Navigator.of(context).pop(),
                            icon: const Icon(
                              Icons.arrow_back_rounded,
                              size: 20,
                            ),
                            label: Text(copy.text('ai01.focus.return')),
                            style: TextButton.styleFrom(
                              minimumSize: const Size(48, 48),
                            ),
                          ),
                        ),
                        if (!short)
                          Padding(
                            padding: const EdgeInsets.symmetric(vertical: 12),
                            child: Text(
                              copy.text('ai01.draft.title'),
                              style: Theme.of(context).textTheme.titleLarge,
                            ),
                          ),
                        Expanded(
                          child: TextField(
                            key: const ValueKey('ai01-focus-input'),
                            controller: widget.controller,
                            focusNode: _focus,
                            autofocus: true,
                            expands: true,
                            minLines: null,
                            maxLines: null,
                            maxLength: 4000,
                            textAlignVertical: TextAlignVertical.top,
                            textInputAction: TextInputAction.newline,
                            style: Theme.of(context).textTheme.bodyLarge
                                ?.copyWith(
                                  fontSize: 16,
                                  height: 1.5,
                                  color: theme.foreground,
                                ),
                            decoration: InputDecoration(
                              hintText: copy.text('ai01.draft.hint'),
                              filled: false,
                              contentPadding: const EdgeInsets.symmetric(
                                vertical: 12,
                              ),
                              border: InputBorder.none,
                              enabledBorder: InputBorder.none,
                              focusedBorder: InputBorder.none,
                              counterStyle: TextStyle(color: theme.quiet),
                            ),
                          ),
                        ),
                        Padding(
                          padding: EdgeInsets.symmetric(
                            vertical: short ? 4 : 12,
                          ),
                          child: Text(
                            copy.text(
                              short
                                  ? 'ai01.focus.localOnly'
                                  : 'ai01.focus.notice',
                            ),
                            style: Theme.of(
                              context,
                            ).textTheme.bodySmall?.copyWith(color: theme.muted),
                          ),
                        ),
                      ],
                    );
                  },
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

Widget _submitButton(BuildContext context, String blockedReason) => Tooltip(
  message: blockedReason,
  child: FilledButton.icon(
    onPressed: null,
    icon: const Icon(Icons.arrow_forward, size: 18),
    label: Text(context.lumenisL10n.text('ai01.submit')),
    style: FilledButton.styleFrom(shape: const StadiumBorder()),
  ),
);

class _EvidenceInspector extends StatelessWidget {
  const _EvidenceInspector({
    required this.snapshot,
    required this.showRuntimeNotice,
  });

  final Ai01Snapshot snapshot;
  final bool showRuntimeNotice;

  @override
  Widget build(BuildContext context) {
    return _SurfacePanel(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (showRuntimeNotice) ...[
            const _RuntimeUnboundNotice(),
            const SizedBox(height: 18),
          ],
          _EvidencePanel(contained: true),
          Divider(height: 30, color: LumenisTheme.of(context).line),
          _ProviderPanel(providers: snapshot.providers, contained: true),
          Divider(height: 30, color: LumenisTheme.of(context).line),
          _ExecutionPanel(contained: true),
        ],
      ),
    );
  }
}

class _EvidencePanel extends StatelessWidget {
  const _EvidencePanel({this.contained = false});

  final bool contained;

  @override
  Widget build(BuildContext context) {
    final content = Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _PanelEyebrow(label: context.lumenisL10n.text('ai01.evidence.title')),
        const SizedBox(height: 12),
        Text(
          context.lumenisL10n.text('ai01.evidence.detail'),
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
            color: LumenisTheme.of(context).muted,
          ),
        ),
        const SizedBox(height: 14),
        const _TraceBoundary(),
      ],
    );
    return contained ? content : _SurfacePanel(child: content);
  }
}

class _TraceBoundary extends StatelessWidget {
  const _TraceBoundary();

  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    padding: const EdgeInsets.all(12),
    decoration: BoxDecoration(
      color: LumenisTheme.of(context).canvas,
      border: Border.all(color: LumenisTheme.of(context).line),
      borderRadius: BorderRadius.circular(10),
    ),
    child: Text(
      context.lumenisL10n.text('ai01.evidence.trace'),
      style: TextStyle(color: LumenisTheme.of(context).muted, height: 1.5),
    ),
  );
}

class _ProviderPanel extends StatelessWidget {
  const _ProviderPanel({required this.providers, this.contained = false});

  final List<Ai01ProviderState> providers;
  final bool contained;

  @override
  Widget build(BuildContext context) {
    final content = Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _PanelEyebrow(label: context.lumenisL10n.text('ai01.providers.title')),
        const SizedBox(height: 9),
        if (providers.isEmpty)
          Text(
            context.lumenisL10n.text('ai01.providers.empty'),
            style: TextStyle(color: LumenisTheme.of(context).muted),
          )
        else
          for (final provider in providers) ...[
            _ProviderRow(provider: provider),
            if (provider != providers.last) const Divider(height: 1),
          ],
      ],
    );
    return contained ? content : _SurfacePanel(child: content);
  }
}

class _ProviderRow extends StatelessWidget {
  const _ProviderRow({required this.provider});

  final Ai01ProviderState provider;

  @override
  Widget build(BuildContext context) {
    final color = switch (provider.state) {
      'ok' => LumenisTheme.of(context).positive,
      'idle' => LumenisTheme.of(context).caution,
      'offline' => LumenisTheme.of(context).danger,
      _ => LumenisTheme.of(context).quiet,
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
                  _providerDisplayName(context, provider.name),
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          Text(
            _providerStateLabel(context, provider.state),
            style: TextStyle(color: color, fontSize: 12),
          ),
        ],
      ),
    );
  }
}

class _ExecutionPanel extends StatelessWidget {
  const _ExecutionPanel({this.contained = false});

  final bool contained;

  @override
  Widget build(BuildContext context) {
    final content = Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _PanelEyebrow(label: context.lumenisL10n.text('ai01.executions.title')),
        const SizedBox(height: 9),
        Text(
          context.lumenisL10n.text('ai01.executions.detail'),
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
            color: LumenisTheme.of(context).muted,
          ),
        ),
      ],
    );
    return contained ? content : _SurfacePanel(child: content);
  }
}

class _MobileEvidenceSections extends StatelessWidget {
  const _MobileEvidenceSections({
    required this.snapshot,
    required this.showRuntimeNotice,
  });

  final Ai01Snapshot snapshot;
  final bool showRuntimeNotice;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        const SizedBox(height: 12),
        _DisclosureSection(
          title: context.lumenisL10n.text('ai01.disclosure.evidence'),
          icon: Icons.account_tree_outlined,
          child: _EvidencePanel(contained: true),
        ),
        const SizedBox(height: 8),
        _DisclosureSection(
          title: context.lumenisL10n.text('ai01.disclosure.providers'),
          icon: Icons.hub_outlined,
          child: Column(
            children: [
              if (showRuntimeNotice) ...[
                const _RuntimeUnboundNotice(),
                const SizedBox(height: 8),
              ],
              _ProviderPanel(providers: snapshot.providers, contained: true),
            ],
          ),
        ),
        const SizedBox(height: 8),
        _DisclosureSection(
          title: context.lumenisL10n.text('ai01.disclosure.executions'),
          icon: Icons.history,
          child: _ExecutionPanel(contained: true),
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
        leading: Icon(icon, color: LumenisTheme.of(context).shared),
        title: Text(title),
        tilePadding: const EdgeInsets.symmetric(horizontal: 12),
        childrenPadding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
        collapsedShape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(14),
          side: BorderSide(color: LumenisTheme.of(context).line),
        ),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(14),
          side: BorderSide(color: LumenisTheme.of(context).line),
        ),
        backgroundColor: LumenisTheme.of(context).surface,
        collapsedBackgroundColor: LumenisTheme.of(context).surface,
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
      context.lumenisL10n.text('ai01.truth'),
      style: Theme.of(
        context,
      ).textTheme.bodySmall?.copyWith(color: LumenisTheme.of(context).quiet),
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
        color: LumenisTheme.of(context).quiet,
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
        color: LumenisTheme.of(context).surface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: LumenisTheme.of(context).line),
      ),
      child: child,
    );
  }
}

class _ServiceReadStatus extends StatelessWidget {
  const _ServiceReadStatus({
    required this.phase,
    required this.failureKind,
    required this.onRetry,
  });

  final Ai01LoadPhase phase;
  final Ai01FailureKind? failureKind;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    final failed = phase == Ai01LoadPhase.failed && failureKind != null;
    final title = switch (failed ? failureKind : null) {
      Ai01FailureKind.authentication => copy.text('ai01.failure.auth.title'),
      Ai01FailureKind.permissionDenied => copy.text(
        'ai01.failure.permission.title',
      ),
      Ai01FailureKind.offline => copy.text('ai01.failure.offline.title'),
      Ai01FailureKind.server => copy.text('ai01.failure.server.title'),
      _ => copy.text('ai01.loading'),
    };
    final explanation = switch (failed ? failureKind : null) {
      Ai01FailureKind.authentication => copy.text('ai01.failure.auth.detail'),
      Ai01FailureKind.permissionDenied => copy.text(
        'ai01.failure.permission.detail',
      ),
      Ai01FailureKind.offline => copy.text('ai01.failure.offline.detail'),
      Ai01FailureKind.server => copy.text('ai01.failure.server.detail'),
      _ => null,
    };

    return _SurfacePanel(
      padding: const EdgeInsets.all(14),
      child: Semantics(
        container: true,
        liveRegion: true,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (!failed)
                  SizedBox.square(
                    dimension: 18,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: LumenisTheme.of(context).ai,
                    ),
                  )
                else
                  Icon(
                    Icons.info_outline,
                    size: 18,
                    color: LumenisTheme.of(context).caution,
                  ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        title,
                        style: Theme.of(context).textTheme.titleSmall,
                      ),
                      if (explanation != null) ...[
                        const SizedBox(height: 4),
                        Text(
                          explanation,
                          style: Theme.of(context).textTheme.bodySmall
                              ?.copyWith(color: LumenisTheme.of(context).muted),
                        ),
                      ],
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              copy.text('ai01.local.available'),
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: LumenisTheme.of(context).muted,
              ),
            ),
            if (failed) ...[
              const SizedBox(height: 8),
              TextButton.icon(
                onPressed: onRetry,
                icon: const Icon(Icons.refresh, size: 18),
                label: Text(copy.text('ai01.retry')),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

String _providerDisplayName(BuildContext context, String _) =>
    context.lumenisL10n.text('ai01.provider.default');

String _providerStateLabel(BuildContext context, String state) =>
    switch (state.trim().toLowerCase()) {
      'ok' => context.lumenisL10n.text('ai01.provider.available'),
      'idle' => context.lumenisL10n.text('ai01.provider.idle'),
      'offline' => context.lumenisL10n.text('ai01.provider.offline'),
      _ => context.lumenisL10n.text('ai01.provider.unknown'),
    };
