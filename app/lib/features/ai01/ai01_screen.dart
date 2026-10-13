import 'package:lumenis_app/core/lumenis_icon.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../core/lumenis_core_client.dart';
import '../../core/lumenis_theme.dart';
import '../../l10n/lumenis_localizations.dart';
import 'ai01_draft_actions.dart';
import 'ai01_draft_files.dart';
import 'ai01_intent.dart';
import 'ai01_repository.dart';
import 'ai01_snapshot.dart';
import 'ai01_view_model.dart';

class Ai01Screen extends StatefulWidget {
  const Ai01Screen({
    required this.client,
    this.repository,
    this.draftFiles,
    this.draftController,
    this.scopeLabel,
    this.embedded = false,
    super.key,
  });

  final LumenisCoreClient client;
  final Ai01Repository? repository;
  final Ai01DraftFiles? draftFiles;
  final TextEditingController? draftController;
  final String? scopeLabel;
  final bool embedded;

  @override
  State<Ai01Screen> createState() => _Ai01ScreenState();
}

class _Ai01ScreenState extends State<Ai01Screen> {
  late Ai01ViewModel _viewModel;
  late TextEditingController _draftController;
  TextEditingController? _ownedDraftController;
  final FocusNode _draftFocus = FocusNode();
  final FocusNode _detailsOpenerFocus = FocusNode(
    debugLabel: 'ai01-details-opener',
  );
  final _ownedDialogs = <DialogRoute<void>>{};
  final List<_Ai01SuggestionAdoption> _suggestionAdoptions = [];
  Ai01Suggestion? _reviewedSuggestion;
  bool _confirmSuggestionWithdrawal = false;

  Ai01Suggestion? get _adoptedSuggestion => _suggestionAdoptions.isEmpty
      ? null
      : _suggestionAdoptions.last.suggestion;

  @override
  void initState() {
    super.initState();
    _viewModel = _createViewModel();
    _draftController = widget.draftController ?? TextEditingController();
    if (widget.draftController == null) {
      _ownedDraftController = _draftController;
    }
    _draftController.addListener(_syncDraft);
    _syncDraft();
    _viewModel.refresh();
  }

  @override
  void didUpdateWidget(covariant Ai01Screen oldWidget) {
    super.didUpdateWidget(oldWidget);
    final readOwnerChanged =
        !identical(oldWidget.repository, widget.repository) ||
        (widget.repository == null &&
            !identical(oldWidget.client, widget.client));
    if (readOwnerChanged) {
      _closeOwnedDialogs();
      _viewModel.dispose();
      _viewModel = _createViewModel();
      _clearSuggestionState();
      _syncDraft();
      _viewModel.refresh();
    }
    if (oldWidget.draftController == widget.draftController) return;

    _closeOwnedDialogs();
    _clearSuggestionState();
    final previousController = _draftController;
    final previousValue = previousController.value;
    previousController.removeListener(_syncDraft);
    if (identical(_ownedDraftController, previousController)) {
      // The outgoing TextField and any focused editor finish unmounting first.
      WidgetsBinding.instance.addPostFrameCallback(
        (_) => previousController.dispose(),
      );
      _ownedDraftController = null;
    }

    final nextController = widget.draftController;
    if (nextController != null) {
      _draftController = nextController;
    } else {
      _draftController = TextEditingController.fromValue(previousValue);
      _ownedDraftController = _draftController;
    }
    _draftController.addListener(_syncDraft);
    _syncDraft();
  }

  @override
  void dispose() {
    _closeOwnedDialogs();
    _draftController.removeListener(_syncDraft);
    _ownedDraftController?.dispose();
    _viewModel.dispose();
    _draftFocus.dispose();
    _detailsOpenerFocus.dispose();
    super.dispose();
  }

  Ai01ViewModel _createViewModel() => Ai01ViewModel(
    repository: widget.repository ?? CoreAi01Repository(client: widget.client),
  );

  void _closeOwnedDialogs() {
    final dialogs = _ownedDialogs.toList();
    _ownedDialogs.clear();
    if (dialogs.isNotEmpty) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        for (final route in dialogs) {
          final navigator = route.navigator;
          if (navigator != null && navigator.mounted && route.isActive) {
            navigator.removeRoute(route);
          }
        }
      });
    }
  }

  void _syncDraft() => _viewModel.updateDraft(_draftController.text);

  void _clearSuggestionState() {
    _reviewedSuggestion = null;
    _suggestionAdoptions.clear();
    _confirmSuggestionWithdrawal = false;
  }

  String? _submitBlockedText(BuildContext context) {
    final copy = context.lumenisL10n;
    return switch (_viewModel.submitBlock) {
      Ai01SubmitBlock.none => null,
      Ai01SubmitBlock.notReady => copy.text('ai01.blocked_reason'),
      Ai01SubmitBlock.emptyDraft => copy.text('ai01.submit.blocked.empty'),
      Ai01SubmitBlock.tooLong => copy.text('ai01.submit.blocked.too_long'),
      Ai01SubmitBlock.submitting => copy.text('ai01.submit.blocked.submitting'),
      Ai01SubmitBlock.alreadySubmitted => copy.text(
        'ai01.submit.blocked.submitted',
      ),
    };
  }

  void _reviewSuggestion(Ai01Suggestion suggestion) {
    setState(() {
      _reviewedSuggestion = suggestion;
      _confirmSuggestionWithdrawal = false;
    });
  }

  void _closeSuggestionReview() {
    setState(() {
      _reviewedSuggestion = null;
      _confirmSuggestionWithdrawal = false;
    });
  }

  void _adoptSuggestion(Ai01Suggestion suggestion) {
    final intent = suggestion.safeIntent;
    if (intent == null || intent.isEmpty) return;

    final previousDraft = _draftController.value;
    final nextText = _appendSafeIntent(previousDraft.text, intent);
    if (nextText == null || nextText.trim().runes.length > ai01MaxTaskLength) {
      return;
    }
    final adoptedDraft = TextEditingValue(
      text: nextText,
      selection: TextSelection.collapsed(offset: nextText.length),
    );
    setState(() {
      _reviewedSuggestion = suggestion;
      _suggestionAdoptions.add(
        _Ai01SuggestionAdoption(
          suggestion: suggestion,
          before: previousDraft,
          after: adoptedDraft,
        ),
      );
      _confirmSuggestionWithdrawal = false;
    });
    _viewModel.updateDraft(nextText);
    _draftController.value = adoptedDraft;
  }

  void _requestSuggestionWithdrawal() {
    if (_suggestionAdoptions.isEmpty) return;
    final adoption = _suggestionAdoptions.last;
    if (_draftController.text == adoption.after.text) {
      _withdrawSuggestion();
      return;
    }
    setState(() => _confirmSuggestionWithdrawal = true);
  }

  void _withdrawSuggestion() {
    if (_suggestionAdoptions.isEmpty) return;
    final adoption = _suggestionAdoptions.last;
    setState(() {
      _suggestionAdoptions.removeLast();
      _reviewedSuggestion = _suggestionAdoptions.isEmpty
          ? adoption.suggestion
          : _suggestionAdoptions.last.suggestion;
      _confirmSuggestionWithdrawal = false;
    });
    _draftController.value = adoption.before;
  }

  void _cancelSuggestionWithdrawal() {
    setState(() => _confirmSuggestionWithdrawal = false);
  }

  Future<void> _openFocusedEditor() async {
    final reduceMotion =
        MediaQuery.maybeOf(context)?.disableAnimations ?? false;
    await _showOwnedDialog(
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

  Future<void> _openDetails() async {
    final reduceMotion =
        MediaQuery.maybeOf(context)?.disableAnimations ?? false;
    await _showOwnedDialog(
      animationStyle: reduceMotion
          ? AnimationStyle.noAnimation
          : const AnimationStyle(
              duration: Duration(milliseconds: 170),
              reverseDuration: Duration(milliseconds: 170),
              curve: Curves.easeOutCubic,
            ),
      builder: (context) => AnimatedBuilder(
        animation: _viewModel,
        builder: (context, _) => _Ai01DetailsDialog(
          snapshot: _viewModel.snapshot,
          phase: _viewModel.phase,
          failureKind: _viewModel.failureKind,
          onRetry: _viewModel.refresh,
        ),
      ),
    );
    if (mounted) _detailsOpenerFocus.requestFocus();
  }

  Future<void> _showOwnedDialog({
    required WidgetBuilder builder,
    required AnimationStyle animationStyle,
    bool useSafeArea = true,
  }) async {
    final navigator = Navigator.of(context, rootNavigator: true);
    final route = DialogRoute<void>(
      context: context,
      builder: builder,
      themes: InheritedTheme.capture(from: context, to: navigator.context),
      useSafeArea: useSafeArea,
      animationStyle: animationStyle,
      traversalEdgeBehavior: TraversalEdgeBehavior.closedLoop,
    );
    _ownedDialogs.add(route);
    try {
      await navigator.push(route);
    } finally {
      _ownedDialogs.remove(route);
    }
  }

  @override
  Widget build(BuildContext context) {
    final content = AnimatedBuilder(
      animation: _viewModel,
      builder: (context, _) => _buildState(context),
    );
    if (widget.embedded) return content;

    return DecoratedBox(
      decoration: BoxDecoration(color: LumenisTheme.of(context).canvas),
      child: Stack(children: [SafeArea(child: content)]),
    );
  }

  Widget _buildState(BuildContext context) {
    return _buildWorkbench(
      context,
      snapshot: _viewModel.snapshot,
      phase: _viewModel.phase,
      failureKind: _viewModel.failureKind,
      onRetry: _viewModel.refresh,
      embedded: widget.embedded,
    );
  }

  Widget _buildWorkbench(
    BuildContext context, {
    required Ai01Snapshot? snapshot,
    required Ai01LoadPhase phase,
    required Ai01FailureKind? failureKind,
    required VoidCallback onRetry,
    required bool embedded,
  }) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final phone = constraints.maxWidth < 600;
        final inset = phone ? 18.0 : 28.0;

        final workbench = Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 820),
            child: Column(
              key: embedded ? const ValueKey('ai01-embedded-content') : null,
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                if (!embedded) ...[
                  _PageHeading(compact: phone),
                  SizedBox(height: phone ? 18 : 24),
                ],
                _ComposerPane(
                  controller: _draftController,
                  focusNode: _draftFocus,
                  draftFiles: widget.draftFiles,
                  scopeLabel: widget.scopeLabel,
                  submitBlockedReason: _submitBlockedText(context),
                  onSubmit: _viewModel.canSubmit ? _viewModel.submit : null,
                  submitPhase: _viewModel.submitPhase,
                  intentResult: _viewModel.intentResult,
                  suggestions: snapshot?.suggestions ?? const [],
                  reviewedSuggestion: _reviewedSuggestion,
                  adoptedSuggestion: _adoptedSuggestion,
                  confirmSuggestionWithdrawal: _confirmSuggestionWithdrawal,
                  onReviewSuggestion: _reviewSuggestion,
                  onCloseSuggestionReview: _closeSuggestionReview,
                  onAdoptSuggestion: _adoptSuggestion,
                  onRequestSuggestionWithdrawal: _requestSuggestionWithdrawal,
                  onConfirmSuggestionWithdrawal: _withdrawSuggestion,
                  onCancelSuggestionWithdrawal: _cancelSuggestionWithdrawal,
                  onExpand: _openFocusedEditor,
                  compact: phone,
                ),
                if (snapshot == null) ...[
                  const SizedBox(height: 14),
                  _ServiceReadStatus(
                    phase: phase,
                    failureKind: failureKind,
                    onRetry: onRetry,
                  ),
                ],
                const SizedBox(height: 8),
                Align(
                  alignment: Alignment.centerLeft,
                  child: TextButton.icon(
                    key: const ValueKey('ai01-details-open'),
                    focusNode: _detailsOpenerFocus,
                    onPressed: _openDetails,
                    icon: const LumenisIcon(
                      Icons.account_tree_outlined,
                      size: 18,
                    ),
                    label: Text(
                      context.lumenisL10n.text('ai01.inspector.show'),
                    ),
                    style: TextButton.styleFrom(
                      minimumSize: const Size(48, 48),
                    ),
                  ),
                ),
              ],
            ),
          ),
        );
        if (embedded) {
          return Padding(
            padding: const EdgeInsets.only(bottom: 24),
            child: workbench,
          );
        }
        return SingleChildScrollView(
          padding: EdgeInsets.fromLTRB(inset, phone ? 18 : 36, inset, 32),
          child: workbench,
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
    return Text(
      context.lumenisL10n.text('ai01.title'),
      style:
          (compact
                  ? Theme.of(context).textTheme.headlineMedium
                  : Theme.of(context).textTheme.displaySmall)
              ?.copyWith(
                color: LumenisTheme.of(context).foreground,
                fontSize: compact ? 25 : 30,
                height: 1.25,
                fontWeight: FontWeight.w600,
                letterSpacing: 0,
              ),
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
          LumenisIcon(
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
  const _ContextBoundary({this.scopeLabel});

  final String? scopeLabel;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    final label = scopeLabel ?? copy.text('ai01.context.label');
    return Tooltip(
      message: copy.text('ai01.context.detail'),
      child: Semantics(
        container: true,
        excludeSemantics: true,
        liveRegion: true,
        label: '$label. ${copy.text('ai01.context.detail')}',
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Padding(
              padding: const EdgeInsets.only(top: 2),
              child: LumenisIcon(
                Icons.public_rounded,
                color: LumenisTheme.of(context).muted,
                size: 16,
              ),
            ),
            const SizedBox(width: 8),
            Flexible(
              child: Text(
                label,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: LumenisTheme.of(context).muted,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ComposerPane extends StatelessWidget {
  const _ComposerPane({
    required this.controller,
    required this.focusNode,
    required this.draftFiles,
    required this.scopeLabel,
    required this.submitBlockedReason,
    required this.onSubmit,
    required this.submitPhase,
    required this.intentResult,
    required this.suggestions,
    required this.reviewedSuggestion,
    required this.adoptedSuggestion,
    required this.confirmSuggestionWithdrawal,
    required this.onReviewSuggestion,
    required this.onCloseSuggestionReview,
    required this.onAdoptSuggestion,
    required this.onRequestSuggestionWithdrawal,
    required this.onConfirmSuggestionWithdrawal,
    required this.onCancelSuggestionWithdrawal,
    required this.onExpand,
    required this.compact,
  });

  final TextEditingController controller;
  final FocusNode focusNode;
  final Ai01DraftFiles? draftFiles;
  final String? scopeLabel;
  final String? submitBlockedReason;
  final VoidCallback? onSubmit;
  final Ai01SubmitPhase submitPhase;
  final Ai01IntentResult? intentResult;
  final List<Ai01Suggestion> suggestions;
  final Ai01Suggestion? reviewedSuggestion;
  final Ai01Suggestion? adoptedSuggestion;
  final bool confirmSuggestionWithdrawal;
  final ValueChanged<Ai01Suggestion> onReviewSuggestion;
  final VoidCallback onCloseSuggestionReview;
  final ValueChanged<Ai01Suggestion> onAdoptSuggestion;
  final VoidCallback onRequestSuggestionWithdrawal;
  final VoidCallback onConfirmSuggestionWithdrawal;
  final VoidCallback onCancelSuggestionWithdrawal;
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
      padding: EdgeInsets.all(compact ? 14 : 18),
      decoration: BoxDecoration(
        color: LumenisTheme.of(context).surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: LumenisTheme.of(context).line),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          TextField(
            key: const ValueKey('ai01-task-input'),
            controller: controller,
            focusNode: focusNode,
            style: Theme.of(
              context,
            ).textTheme.bodyLarge?.copyWith(fontSize: 16, height: 1.5),
            minLines: 3,
            maxLines: 10,
            maxLength: 4000,
            textInputAction: TextInputAction.newline,
            decoration: InputDecoration(
              filled: false,
              isDense: true,
              contentPadding: EdgeInsets.symmetric(
                horizontal: 0,
                vertical: compact ? 8 : 10,
              ),
              counterText: '',
              hintText: context.lumenisL10n.text('ai01.draft.hint'),
              alignLabelWithHint: true,
              border: InputBorder.none,
              enabledBorder: InputBorder.none,
              focusedBorder: InputBorder.none,
            ),
          ),
          const SizedBox(height: 2),
          _Ai01DraftLengthCounter(controller: controller),
          if (safeSuggestions.isNotEmpty) ...[
            const SizedBox(height: 10),
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
                for (var index = 0; index < safeSuggestions.length; index++)
                  ActionChip(
                    key: ValueKey('ai01-suggestion-$index'),
                    onPressed: () => onReviewSuggestion(safeSuggestions[index]),
                    label: Text(safeSuggestions[index].safeTitle!),
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
          if (reviewedSuggestion != null &&
              reviewedSuggestion!.isProductSafe) ...[
            const SizedBox(height: 10),
            _Ai01SuggestionReview(
              suggestion: reviewedSuggestion!,
              isCurrentAdoption: _sameAi01Suggestion(
                reviewedSuggestion!,
                adoptedSuggestion,
              ),
              intentAlreadyInDraft: _containsSafeIntentLine(
                controller.text,
                reviewedSuggestion!.safeIntent!,
              ),
              intentWouldExceedTaskLimit: _wouldExceedAi01TaskLimit(
                controller.text,
                reviewedSuggestion!.safeIntent!,
              ),
              onClose: onCloseSuggestionReview,
              onAdopt: () => onAdoptSuggestion(reviewedSuggestion!),
            ),
          ],
          if (adoptedSuggestion != null) ...[
            const SizedBox(height: 10),
            _Ai01AdoptionControls(
              adoptedSuggestion: adoptedSuggestion!,
              confirmWithdrawal: confirmSuggestionWithdrawal,
              onRequestWithdrawal: onRequestSuggestionWithdrawal,
              onConfirmWithdrawal: onConfirmSuggestionWithdrawal,
              onCancelWithdrawal: onCancelSuggestionWithdrawal,
            ),
          ],
          const SizedBox(height: 6),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Theme(
                  data: Theme.of(context).copyWith(
                    textButtonTheme: TextButtonThemeData(
                      style: TextButton.styleFrom(
                        minimumSize: const Size(64, 48),
                      ),
                    ),
                  ),
                  child: Ai01DraftActions(
                    key: const ValueKey('ai01-draft-actions'),
                    controller: controller,
                    focusNode: focusNode,
                    files: draftFiles,
                  ),
                ),
              ),
              const SizedBox(width: 4),
              IconButton(
                key: const ValueKey('ai01-focus-open'),
                tooltip: context.lumenisL10n.text('ai01.focus.open'),
                onPressed: onExpand,
                icon: const LumenisIcon(Icons.open_in_full_rounded, size: 18),
                constraints: const BoxConstraints.tightFor(
                  width: 48,
                  height: 48,
                ),
              ),
            ],
          ),
          const SizedBox(height: 2),
          Text(
            context.lumenisL10n.text('ai01.draft.notice'),
            style: TextStyle(
              color: LumenisTheme.of(context).quiet,
              fontSize: 12,
            ),
          ),
          const SizedBox(height: 10),
          Divider(height: 1, color: LumenisTheme.of(context).line),
          const SizedBox(height: 8),
          LayoutBuilder(
            builder: (context, constraints) => SizedBox(
              width: constraints.maxWidth,
              child: Wrap(
                alignment: WrapAlignment.spaceBetween,
                crossAxisAlignment: WrapCrossAlignment.center,
                spacing: 12,
                runSpacing: 8,
                children: [
                  ConstrainedBox(
                    constraints: BoxConstraints(
                      maxWidth: constraints.maxWidth
                          .clamp(0.0, 140.0)
                          .toDouble(),
                    ),
                    child: _ContextBoundary(scopeLabel: scopeLabel),
                  ),
                  SizedBox(
                    height: 48,
                    child: _submitButton(
                      context,
                      onSubmit: onSubmit,
                      blockedReason: submitBlockedReason,
                      busy: submitPhase == Ai01SubmitPhase.submitting,
                    ),
                  ),
                ],
              ),
            ),
          ),
          if (submitPhase != Ai01SubmitPhase.idle) ...[
            const SizedBox(height: 12),
            _SubmitStatus(phase: submitPhase, result: intentResult),
          ],
        ],
      ),
    );
  }
}

class _Ai01DraftLengthCounter extends StatelessWidget {
  const _Ai01DraftLengthCounter({required this.controller});

  final TextEditingController controller;

  @override
  Widget build(
    BuildContext context,
  ) => ValueListenableBuilder<TextEditingValue>(
    valueListenable: controller,
    builder: (context, value, _) {
      final count = value.text.trim().runes.length;
      final overLimit = count > ai01MaxTaskLength;
      final theme = LumenisTheme.of(context);
      final countLabel = _ai01LocalCopy(
        context,
        zh: '草稿长度 $count/4000 字符',
        en: 'Draft length $count of 4,000 characters',
        ko: '초안 길이 $count/4000자',
      );
      return Column(
        crossAxisAlignment: CrossAxisAlignment.end,
        mainAxisSize: MainAxisSize.min,
        children: [
          Semantics(
            label: countLabel,
            child: ExcludeSemantics(
              child: Text(
                '$count/4000',
                key: const ValueKey('ai01-draft-character-count'),
                textAlign: TextAlign.end,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: overLimit ? theme.danger : theme.quiet,
                ),
              ),
            ),
          ),
          if (overLimit) ...[
            const SizedBox(height: 2),
            Semantics(
              liveRegion: true,
              child: Text(
                _ai01LocalCopy(
                  context,
                  zh: '超出 4000 字符时不能提交或加入建议，草稿仍可编辑和保存。',
                  en: 'Over 4,000 characters, submission and adding suggestions are disabled; you can still edit and save the draft.',
                  ko: '4,000자를 넘으면 제출과 제안 추가는 제한되지만 초안은 계속 편집하고 저장할 수 있어요.',
                ),
                key: const ValueKey('ai01-draft-limit-note'),
                textAlign: TextAlign.end,
                style: Theme.of(
                  context,
                ).textTheme.bodySmall?.copyWith(color: theme.danger),
              ),
            ),
          ],
        ],
      );
    },
  );
}

class _Ai01SuggestionReview extends StatelessWidget {
  const _Ai01SuggestionReview({
    required this.suggestion,
    required this.isCurrentAdoption,
    required this.intentAlreadyInDraft,
    required this.intentWouldExceedTaskLimit,
    required this.onClose,
    required this.onAdopt,
  });

  final Ai01Suggestion suggestion;
  final bool isCurrentAdoption;
  final bool intentAlreadyInDraft;
  final bool intentWouldExceedTaskLimit;
  final VoidCallback onClose;
  final VoidCallback onAdopt;

  @override
  Widget build(BuildContext context) {
    final theme = LumenisTheme.of(context);
    final intent = suggestion.safeIntent!;
    return Semantics(
      container: true,
      liveRegion: true,
      child: Container(
        key: const ValueKey('ai01-suggestion-review'),
        width: double.infinity,
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: theme.ai.withValues(alpha: 0.045),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: theme.ai.withValues(alpha: 0.16)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    _ai01LocalCopy(
                      context,
                      zh: '将加入任务的内容',
                      en: 'Text to add to the task',
                      ko: '작업에 추가할 내용',
                    ),
                    style: Theme.of(
                      context,
                    ).textTheme.labelMedium?.copyWith(color: theme.muted),
                  ),
                ),
                IconButton(
                  key: const ValueKey('ai01-suggestion-review-close'),
                  tooltip: _ai01LocalCopy(
                    context,
                    zh: '关闭建议说明',
                    en: 'Close suggestion details',
                    ko: '제안 설명 닫기',
                  ),
                  onPressed: onClose,
                  constraints: const BoxConstraints.tightFor(
                    width: 48,
                    height: 48,
                  ),
                  padding: EdgeInsets.zero,
                  icon: const LumenisIcon(Icons.close_rounded, size: 18),
                ),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              intent,
              key: const ValueKey('ai01-suggestion-safe-intent'),
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: theme.foreground,
                height: 1.4,
              ),
            ),
            if (!intentAlreadyInDraft) ...[
              const SizedBox(height: 8),
              OutlinedButton.icon(
                key: const ValueKey('ai01-suggestion-adopt'),
                onPressed: intentWouldExceedTaskLimit ? null : onAdopt,
                style: OutlinedButton.styleFrom(
                  minimumSize: const Size(48, 48),
                ),
                icon: const LumenisIcon(Icons.add_task_rounded, size: 18),
                label: Text(
                  _ai01LocalCopy(
                    context,
                    zh: '加入任务',
                    en: 'Add to task',
                    ko: '작업에 추가',
                  ),
                ),
              ),
              if (intentWouldExceedTaskLimit) ...[
                const SizedBox(height: 4),
                Text(
                  _ai01LocalCopy(
                    context,
                    zh: '加入后会超过 4000 字符限制，请先删减草稿。',
                    en: 'Adding this would exceed the 4,000-character limit. Shorten the draft first.',
                    ko: '추가하면 4,000자 제한을 넘습니다. 먼저 초안을 줄여 주세요.',
                  ),
                  key: const ValueKey('ai01-suggestion-too-long'),
                  style: Theme.of(
                    context,
                  ).textTheme.bodySmall?.copyWith(color: theme.muted),
                ),
              ],
            ] else if (!isCurrentAdoption) ...[
              const SizedBox(height: 8),
              Text(
                _ai01LocalCopy(
                  context,
                  zh: '这条内容已在任务中，无需重复加入。',
                  en: 'This content is already in the task.',
                  ko: '이 내용은 이미 작업에 있어요.',
                ),
                key: const ValueKey('ai01-suggestion-already-added'),
                style: Theme.of(
                  context,
                ).textTheme.bodySmall?.copyWith(color: theme.muted),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _Ai01SuggestionAdoption {
  const _Ai01SuggestionAdoption({
    required this.suggestion,
    required this.before,
    required this.after,
  });

  final Ai01Suggestion suggestion;
  final TextEditingValue before;
  final TextEditingValue after;
}

String? _appendSafeIntent(String draft, String intent) {
  if (_containsSafeIntentLine(draft, intent)) return null;
  if (draft.isEmpty) return intent;
  final separator = draft.endsWith('\n') ? '' : '\n';
  return '$draft$separator$intent';
}

bool _containsSafeIntentLine(String draft, String intent) =>
    draft.split(RegExp(r'\r\n|\r|\n')).any((line) => line.trim() == intent);

bool _wouldExceedAi01TaskLimit(String draft, String intent) {
  final appended = _appendSafeIntent(draft, intent);
  return appended != null && appended.trim().runes.length > ai01MaxTaskLength;
}

class _Ai01AdoptionControls extends StatelessWidget {
  const _Ai01AdoptionControls({
    required this.adoptedSuggestion,
    required this.confirmWithdrawal,
    required this.onRequestWithdrawal,
    required this.onConfirmWithdrawal,
    required this.onCancelWithdrawal,
  });

  final Ai01Suggestion adoptedSuggestion;
  final bool confirmWithdrawal;
  final VoidCallback onRequestWithdrawal;
  final VoidCallback onConfirmWithdrawal;
  final VoidCallback onCancelWithdrawal;

  @override
  Widget build(BuildContext context) {
    final title = adoptedSuggestion.safeTitle!;
    final message = confirmWithdrawal
        ? _ai01LocalCopy(
            context,
            zh: '撤回会恢复采用前的草稿，并移除之后的编辑内容。',
            en: 'Withdrawing restores the draft from before adoption and removes later edits.',
            ko: '되돌리면 적용 전 초안으로 복원되고 이후 편집 내용은 사라져요.',
          )
        : _ai01LocalCopy(
            context,
            zh: '已加入任务「$title」，你可以继续编辑。',
            en: '“$title” is in the task draft. You can keep editing.',
            ko: '「$title」을(를) 작업 초안에 추가했어요. 계속 편집할 수 있어요.',
          );
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Semantics(
          liveRegion: true,
          child: Text(
            message,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: LumenisTheme.of(context).muted,
            ),
          ),
        ),
        if (confirmWithdrawal) ...[
          const SizedBox(height: 6),
          Wrap(
            spacing: 8,
            runSpacing: 4,
            children: [
              TextButton(
                key: const ValueKey('ai01-suggestion-withdraw-cancel'),
                onPressed: onCancelWithdrawal,
                style: TextButton.styleFrom(minimumSize: const Size(48, 48)),
                child: Text(
                  _ai01LocalCopy(
                    context,
                    zh: '保留当前编辑',
                    en: 'Keep current edits',
                    ko: '현재 편집 유지',
                  ),
                ),
              ),
              FilledButton.tonal(
                key: const ValueKey('ai01-suggestion-withdraw-confirm'),
                onPressed: onConfirmWithdrawal,
                style: FilledButton.styleFrom(minimumSize: const Size(48, 48)),
                child: Text(
                  _ai01LocalCopy(
                    context,
                    zh: '恢复采用前草稿',
                    en: 'Restore previous draft',
                    ko: '이전 초안 복원',
                  ),
                ),
              ),
            ],
          ),
        ] else
          Align(
            alignment: Alignment.centerLeft,
            child: TextButton.icon(
              key: const ValueKey('ai01-suggestion-withdraw'),
              onPressed: onRequestWithdrawal,
              icon: const LumenisIcon(Icons.undo_rounded, size: 18),
              style: TextButton.styleFrom(minimumSize: const Size(48, 48)),
              label: Text(
                _ai01LocalCopy(
                  context,
                  zh: '撤回建议',
                  en: 'Undo suggestion',
                  ko: '제안 되돌리기',
                ),
              ),
            ),
          ),
      ],
    );
  }
}

String _ai01LocalCopy(
  BuildContext context, {
  required String zh,
  required String en,
  required String ko,
}) => switch (context.lumenisL10n.locale.languageCode) {
  'en' => en,
  'ko' => ko,
  _ => zh,
};

bool _sameAi01Suggestion(Ai01Suggestion first, Ai01Suggestion? second) =>
    second != null &&
    first.title == second.title &&
    first.description == second.description &&
    first.intent == second.intent;

class _SubmitStatus extends StatelessWidget {
  const _SubmitStatus({required this.phase, required this.result});

  final Ai01SubmitPhase phase;
  final Ai01IntentResult? result;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    final theme = LumenisTheme.of(context);
    final result = this.result;
    final headline = switch (phase) {
      Ai01SubmitPhase.idle => '',
      Ai01SubmitPhase.submitting => copy.text('ai01.submit.sending'),
      Ai01SubmitPhase.completed => copy.text('ai01.submit.completed'),
      Ai01SubmitPhase.notCompleted => copy.text('ai01.submit.not_completed'),
      Ai01SubmitPhase.pendingApproval => copy.text(
        'ai01.submit.pending_approval',
      ),
      Ai01SubmitPhase.denied => copy.text('ai01.submit.denied'),
      Ai01SubmitPhase.invalid => copy.text('ai01.submit.invalid'),
      Ai01SubmitPhase.authentication => copy.text('ai01.submit.auth'),
      Ai01SubmitPhase.failed => copy.text('ai01.submit.failed'),
      Ai01SubmitPhase.outcomeUnknown => copy.text('ai01.submit.unknown'),
    };
    final isCompleted = phase == Ai01SubmitPhase.completed;
    final details = <Widget>[
      if (result != null)
        Text(
          '${copy.text('ai01.submit.status_label')}: ${result.status}',
          style: TextStyle(color: theme.muted),
        ),
      if (result?.executionId != null)
        SelectableText(
          '${copy.text('ai01.submit.execution_id')}: ${result!.executionId}',
          style: TextStyle(color: theme.muted),
        ),
      if (result?.auditId != null)
        SelectableText(
          '${copy.text('ai01.submit.audit_id')}: ${result!.auditId}',
          style: TextStyle(color: theme.muted),
        ),
      if (result?.evidenceRecorded != null)
        Text(
          copy.text(
            result!.evidenceRecorded!
                ? 'ai01.submit.evidence.recorded'
                : 'ai01.submit.evidence.unconfirmed',
          ),
          style: TextStyle(color: theme.muted),
        ),
      if (result?.executionId != null)
        Text(
          copy.text('ai01.submit.trace_unavailable'),
          style: TextStyle(color: theme.quiet, fontSize: 12),
        ),
    ];
    return Semantics(
      liveRegion: true,
      container: true,
      child: Container(
        key: const ValueKey('ai01-submit-status'),
        width: double.infinity,
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: theme.canvas,
          border: Border.all(color: theme.line),
          borderRadius: BorderRadius.circular(10),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (phase == Ai01SubmitPhase.submitting) ...[
                  const SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
                  const SizedBox(width: 10),
                ],
                Expanded(
                  child: Text(
                    headline,
                    key: ValueKey(
                      isCompleted
                          ? 'ai01-submit-status-completed'
                          : 'ai01-submit-status-${phase.name}',
                    ),
                    style: Theme.of(
                      context,
                    ).textTheme.bodyMedium?.copyWith(height: 1.5),
                  ),
                ),
              ],
            ),
            if (details.isNotEmpty) ...[
              const SizedBox(height: 6),
              for (final detail in details) detail,
            ],
          ],
        ),
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
                            icon: const LumenisIcon(
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
                              counterText: '',
                            ),
                          ),
                        ),
                        _Ai01DraftLengthCounter(controller: widget.controller),
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

class _Ai01DetailsDialog extends StatelessWidget {
  const _Ai01DetailsDialog({
    required this.snapshot,
    required this.phase,
    required this.failureKind,
    required this.onRetry,
  });

  final Ai01Snapshot? snapshot;
  final Ai01LoadPhase phase;
  final Ai01FailureKind? failureKind;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    final theme = LumenisTheme.of(context);
    final currentSnapshot = snapshot;
    return LayoutBuilder(
      builder: (context, constraints) {
        final desktop = constraints.maxWidth >= 768;
        final availableHeight = constraints.maxHeight.isFinite
            ? constraints.maxHeight
            : MediaQuery.sizeOf(context).height;
        final maxHeight = (availableHeight * 0.86)
            .clamp(160.0, 720.0)
            .toDouble();
        return CallbackShortcuts(
          bindings: {
            const SingleActivator(LogicalKeyboardKey.escape): () =>
                Navigator.of(context).pop(),
          },
          child: Dialog(
            key: const ValueKey('ai01-details-dialog'),
            alignment: desktop ? Alignment.centerRight : Alignment.bottomCenter,
            insetPadding: EdgeInsets.symmetric(
              horizontal: desktop ? 24 : 12,
              vertical: 12,
            ),
            constraints: BoxConstraints(maxWidth: 520, maxHeight: maxHeight),
            backgroundColor: theme.surface,
            child: SizedBox(
              key: const ValueKey('ai01-details-panel'),
              width: double.infinity,
              height: maxHeight,
              child: Column(
                children: [
                  Padding(
                    padding: const EdgeInsets.fromLTRB(18, 8, 8, 8),
                    child: Row(
                      children: [
                        Expanded(
                          child: Text(
                            copy.text('ai01.inspector.show'),
                            style: Theme.of(context).textTheme.titleMedium
                                ?.copyWith(color: theme.foreground),
                          ),
                        ),
                        IconButton(
                          key: const ValueKey('ai01-details-close'),
                          tooltip: copy.text('ai01.inspector.hide'),
                          onPressed: () => Navigator.of(context).pop(),
                          icon: const LumenisIcon(
                            Icons.close_rounded,
                            size: 20,
                          ),
                          constraints: const BoxConstraints.tightFor(
                            width: 48,
                            height: 48,
                          ),
                        ),
                      ],
                    ),
                  ),
                  Divider(height: 1, color: theme.line),
                  Expanded(
                    child: SingleChildScrollView(
                      key: const ValueKey('ai01-details-scroll'),
                      padding: const EdgeInsets.all(18),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          if (currentSnapshot == null)
                            _ServiceReadStatus(
                              phase: phase,
                              failureKind: failureKind,
                              onRetry: onRetry,
                            )
                          else
                            _EvidenceInspector(
                              snapshot: currentSnapshot,
                              showRuntimeNotice: !currentSnapshot.isBound,
                            ),
                          const SizedBox(height: 18),
                          const _TruthBoundaryNote(),
                        ],
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
}

Widget _submitButton(
  BuildContext context, {
  required VoidCallback? onSubmit,
  required String? blockedReason,
  required bool busy,
}) => Tooltip(
  message: blockedReason ?? '',
  child: FilledButton.icon(
    key: const ValueKey('ai01-submit'),
    onPressed: onSubmit,
    icon: busy
        ? const SizedBox(
            width: 18,
            height: 18,
            child: CircularProgressIndicator(strokeWidth: 2),
          )
        : const LumenisIcon(Icons.arrow_forward, size: 18),
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
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (showRuntimeNotice) ...[
          const _RuntimeUnboundNotice(),
          const SizedBox(height: 18),
        ],
        const _EvidencePanel(),
        Divider(height: 30, color: LumenisTheme.of(context).line),
        _ProviderPanel(providers: snapshot.providers),
        Divider(height: 30, color: LumenisTheme.of(context).line),
        const _ExecutionPanel(),
      ],
    );
  }
}

class _EvidencePanel extends StatelessWidget {
  const _EvidencePanel();

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
    return content;
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
  const _ProviderPanel({required this.providers});

  final List<Ai01ProviderState> providers;

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
    return content;
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
  const _ExecutionPanel();

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
    return content;
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

    return Semantics(
      container: true,
      liveRegion: true,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
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
                  LumenisIcon(
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
            if (failed) ...[
              const SizedBox(height: 6),
              TextButton.icon(
                key: const ValueKey('ai01-read-retry'),
                onPressed: onRetry,
                icon: const LumenisIcon(Icons.refresh, size: 18),
                label: Text(copy.text('ai01.retry')),
                style: TextButton.styleFrom(minimumSize: const Size(48, 48)),
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
