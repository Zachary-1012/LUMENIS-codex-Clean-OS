import '../../core/lumenis_botanical.dart';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../core/lumenis_icon.dart';
import '../../core/lumenis_core_client.dart';
import '../../core/lumenis_theme.dart';
import '../../l10n/lumenis_localizations.dart';
import '../../navigation/lumenis_leave_guard.dart';
import 'ai01_conversations.dart';
import 'ai01_source_picker.dart';
import 'ai01_draft_actions.dart';
import 'ai01_workspace_draft.dart';

class Ai01ConversationPanel extends StatefulWidget {
  const Ai01ConversationPanel({
    required this.viewModel,
    required this.draftController,
    required this.onClose,
    this.currentTaskId,
    this.embedded = false,
    this.startActions,
    this.onOpenMaterials,
    super.key,
  });

  final Ai01ConversationViewModel viewModel;
  final TextEditingController draftController;
  final String? currentTaskId;
  final VoidCallback onClose;
  final bool embedded;
  final Widget? startActions;
  final VoidCallback? onOpenMaterials;

  @override
  State<Ai01ConversationPanel> createState() => _Ai01ConversationPanelState();
}

class _Ai01ConversationPanelState extends State<Ai01ConversationPanel> {
  final _ownedDialogs = <DialogRoute<bool>>{};
  bool _historyVisible = false;
  bool _draftActionsVisible = false;
  LumenisLeaveGuard? _draftGuard;

  @override
  void initState() {
    super.initState();
    widget.draftController.addListener(_draftChanged);
    widget.viewModel.refreshList(selectFirstIfEmpty: !widget.embedded);
    if (widget.embedded && widget.draftController is Ai01WorkspaceDraft) {
      (widget.draftController as Ai01WorkspaceDraft).status.addListener(
        _refreshGuard,
      );
    }
  }

  void _refreshGuard() => _draftGuard?.refresh();

  void _draftChanged() {
    if (mounted) setState(() {});
    _refreshGuard();
  }

  @override
  void didUpdateWidget(covariant Ai01ConversationPanel oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.draftController != widget.draftController) {
      oldWidget.draftController.removeListener(_draftChanged);
      widget.draftController.addListener(_draftChanged);
    }
    if (oldWidget.draftController != widget.draftController ||
        oldWidget.embedded != widget.embedded) {
      if (oldWidget.draftController is Ai01WorkspaceDraft) {
        (oldWidget.draftController as Ai01WorkspaceDraft).status.removeListener(
          _refreshGuard,
        );
      }
      _draftGuard?.unregister(this);
      _draftGuard = null;
      if (widget.embedded && widget.draftController is Ai01WorkspaceDraft) {
        (widget.draftController as Ai01WorkspaceDraft).status.addListener(
          _refreshGuard,
        );
      }
      _bindDraftGuard();
    }
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _bindDraftGuard();
  }

  String _draftCopy(String zh, String en, String ko) =>
      switch (context.lumenisL10n.locale.languageCode) {
        'en' => en,
        'ko' => ko,
        _ => zh,
      };

  void _bindDraftGuard() {
    final draft = widget.draftController;
    if (!widget.embedded || draft is! Ai01WorkspaceDraft) return;
    final guard = LumenisLeaveScope.maybeOf(context);
    if (identical(guard, _draftGuard)) return;
    _draftGuard?.unregister(this);
    _draftGuard = guard;
    guard?.register(
      this,
      needsProtection: () => draft.hasUnsavedChanges,
      requestLeave: () async {
        await draft.flush();
        if (!mounted) return false;
        if (!draft.hasUnsavedChanges) return true;
        setState(() => _draftActionsVisible = true);
        final discard = await _showOwnedConfirmation(
          (context) => AlertDialog(
            title: Text(
              _draftCopy('草稿尚未保存', 'Draft not saved', '초안이 저장되지 않았습니다'),
            ),
            content: Text(
              _draftCopy(
                '可以先保存为文件，或放弃本次修改。',
                'Save a copy to a file, or discard these changes.',
                '파일로 사본을 저장하거나 변경 내용을 버릴 수 있습니다.',
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context, false),
                child: Text(_draftCopy('继续编辑', 'Keep editing', '계속 편집')),
              ),
              TextButton(
                onPressed: () => Navigator.pop(context, true),
                child: Text(
                  _draftCopy('放弃修改并离开', 'Discard and leave', '변경 사항을 버리고 나가기'),
                ),
              ),
            ],
          ),
        );
        if (discard && mounted) draft.discardLocalChanges();
        return discard;
      },
    );
  }

  Future<void> _send() async {
    final controller = widget.draftController;
    final draft = controller.value;
    final text = draft.text;
    if (widget.embedded && widget.viewModel.selectedId == null) {
      await _createConversation();
      if (!mounted || !widget.viewModel.canSend) return;
    }
    await widget.viewModel.send(
      text,
      onPersisted: () {
        if (mounted &&
            identical(controller, widget.draftController) &&
            controller.value == draft &&
            draft.text == text) {
          controller.clear();
        }
      },
    );
  }

  Future<void> _checkOutcome() async {
    final controller = widget.draftController;
    final draft = controller.value;
    final pending = widget.viewModel.pendingAppendText;
    await widget.viewModel.checkOutcome(
      onAppendPersisted: () {
        if (mounted &&
            identical(controller, widget.draftController) &&
            pending != null &&
            draft.text == pending &&
            controller.value == draft) {
          controller.clear();
        }
      },
    );
  }

  Future<void> _retryAppend() async {
    final controller = widget.draftController;
    final draft = controller.value;
    final pending = widget.viewModel.pendingAppendText;
    await widget.viewModel.retryPendingAppend(
      onPersisted: () {
        if (mounted &&
            identical(controller, widget.draftController) &&
            pending != null &&
            draft.text == pending &&
            controller.value == draft) {
          controller.clear();
        }
      },
    );
  }

  Future<void> _createConversation() async {
    final model = widget.viewModel;
    var acknowledgeUnresolvedPrevious = false;
    if (model.creatingUnknown) {
      final copy = context.lumenisL10n;
      acknowledgeUnresolvedPrevious = await _showOwnedConfirmation(
        (context) => AlertDialog(
          key: const ValueKey('ai01-conversation-create-again-confirm'),
          title: Text(copy.text('ai01.conversation.create_again.title')),
          content: Text(copy.text('ai01.conversation.create_again.detail')),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: Text(copy.text('common.cancel')),
            ),
            FilledButton(
              onPressed: () => Navigator.of(context).pop(true),
              child: Text(copy.text('ai01.conversation.create_again.confirm')),
            ),
          ],
        ),
      );
      if (!mounted || !acknowledgeUnresolvedPrevious) return;
    }
    await model.createConversation(
      acknowledgeUnresolvedPrevious: acknowledgeUnresolvedPrevious,
    );
  }

  Future<void> _editContext() async {
    final model = widget.viewModel;
    final id = model.selectedId;
    if (id == null) return;
    final navigator = Navigator.of(context);
    final route = DialogRoute<bool>(
      context: context,
      barrierDismissible: false,
      builder: (_) => _ConversationContextEditor(
        conversationId: id,
        viewModel: model,
        leaveGuard: LumenisLeaveScope.maybeOf(context),
      ),
      themes: InheritedTheme.capture(from: context, to: navigator.context),
      useSafeArea: true,
      traversalEdgeBehavior: TraversalEdgeBehavior.closedLoop,
    );
    _ownedDialogs.add(route);
    try {
      await navigator.push(route);
    } finally {
      _ownedDialogs.remove(route);
    }
  }

  Future<void> _confirmRetry(Ai01ConversationTurn userTurn) async {
    final copy = context.lumenisL10n;
    final confirmed = await _showOwnedConfirmation(
      (context) => AlertDialog(
        key: const ValueKey('ai01-conversation-retry-confirm'),
        title: Text(copy.text('ai01.conversation.retry.title')),
        content: Text(copy.text('ai01.conversation.retry.detail')),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: Text(copy.text('common.cancel')),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: Text(copy.text('ai01.conversation.retry.confirm')),
          ),
        ],
      ),
    );
    if (confirmed == true && mounted) {
      await widget.viewModel.retryResponse(userTurn, confirmed: true);
    }
  }

  Future<void> _confirmInterrupt(Ai01ConversationTurn turn) async {
    final copy = context.lumenisL10n;
    final confirmed = await _showOwnedConfirmation(
      (context) => AlertDialog(
        key: const ValueKey('ai01-conversation-interrupt-confirm'),
        title: Text(copy.text('ai01.conversation.interrupt.title')),
        content: Text(copy.text('ai01.conversation.interrupt.detail')),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: Text(copy.text('common.cancel')),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: Text(copy.text('ai01.conversation.interrupt.confirm')),
          ),
        ],
      ),
    );
    if (confirmed == true && mounted) {
      await widget.viewModel.interruptResponse(turn, confirmed: true);
    }
  }

  Future<bool> _showOwnedConfirmation(WidgetBuilder builder) async {
    if (!mounted) return false;
    final navigator = Navigator.of(context, rootNavigator: true);
    final route = DialogRoute<bool>(
      context: context,
      builder: builder,
      themes: InheritedTheme.capture(from: context, to: navigator.context),
      useSafeArea: true,
      traversalEdgeBehavior: TraversalEdgeBehavior.closedLoop,
    );
    _ownedDialogs.add(route);
    try {
      return await navigator.push(route) ?? false;
    } finally {
      _ownedDialogs.remove(route);
    }
  }

  void _closeOwnedDialogs() {
    final dialogs = _ownedDialogs.toList();
    _ownedDialogs.clear();
    if (dialogs.isEmpty) return;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      for (final route in dialogs) {
        final navigator = route.navigator;
        if (navigator != null && navigator.mounted && route.isActive) {
          navigator.removeRoute(route);
        }
      }
    });
  }

  @override
  void dispose() {
    widget.draftController.removeListener(_draftChanged);
    _draftGuard?.unregister(this);
    if (widget.embedded && widget.draftController is Ai01WorkspaceDraft) {
      (widget.draftController as Ai01WorkspaceDraft).status.removeListener(
        _refreshGuard,
      );
    }
    _closeOwnedDialogs();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    final theme = LumenisTheme.of(context);
    final phone = MediaQuery.sizeOf(context).width < 600;
    if (widget.embedded) {
      return AnimatedBuilder(
        animation: widget.viewModel,
        builder: (context, _) => _buildEmbedded(context),
      );
    }
    return Dialog(
      key: const ValueKey('ai01-conversation-dialog'),
      alignment: phone ? Alignment.bottomCenter : Alignment.centerRight,
      insetPadding: EdgeInsets.symmetric(
        horizontal: phone ? 8 : 20,
        vertical: phone ? 8 : 16,
      ),
      backgroundColor: theme.surface,
      child: LayoutBuilder(
        builder: (context, constraints) {
          final maxHeight = (MediaQuery.sizeOf(context).height * 0.92)
              .clamp(240.0, 820.0)
              .toDouble();
          final width = phone
              ? constraints.maxWidth
              : constraints.maxWidth.clamp(280.0, 1080.0).toDouble();
          return SizedBox(
            width: width,
            height: maxHeight,
            child: AnimatedBuilder(
              animation: widget.viewModel,
              builder: (context, _) => Column(
                children: [
                  _PanelHeader(
                    title: copy.text('ai01.conversation.title'),
                    onClose: widget.onClose,
                    onRefresh: widget.viewModel.refreshList,
                    onCreate: _createConversation,
                    busy: widget.viewModel.busy,
                  ),
                  Divider(height: 1, color: theme.line),
                  Expanded(
                    child: phone
                        ? _buildPhone(context)
                        : Row(
                            children: [
                              SizedBox(
                                width: 260,
                                child: _ConversationList(
                                  viewModel: widget.viewModel,
                                  onSelect: widget.viewModel.open,
                                  onLoadMore:
                                      widget.viewModel.loadMoreConversations,
                                ),
                              ),
                              VerticalDivider(width: 1, color: theme.line),
                              Expanded(child: _buildConversation(context)),
                            ],
                          ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _buildEmbedded(BuildContext context) {
    final model = widget.viewModel;
    final copy = context.lumenisL10n;
    return Column(
      key: const ValueKey('ai01-conversation-workspace'),
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
          child: Wrap(
            alignment: WrapAlignment.end,
            spacing: 4,
            children: [
              TextButton.icon(
                key: const ValueKey('ai01-conversation-history'),
                onPressed: () =>
                    setState(() => _historyVisible = !_historyVisible),
                icon: LumenisIcon(
                  _historyVisible ? Icons.close_rounded : Icons.history_rounded,
                  size: 18,
                ),
                label: Text(
                  copy.text(
                    _historyVisible ? 'common.close' : 'ai01.conversation.list',
                  ),
                ),
              ),
              TextButton.icon(
                key: const ValueKey('ai01-conversation-new-work'),
                onPressed: model.busy || model.outcomeUnknown
                    ? null
                    : model.creatingUnknown
                    ? _createConversation
                    : () {
                        model.showConversationList();
                        setState(() => _historyVisible = false);
                      },
                icon: const LumenisIcon(Icons.add_rounded, size: 18),
                label: Text(copy.text('ai01.conversation.new')),
              ),
            ],
          ),
        ),
        Expanded(
          child: _historyVisible
              ? _ConversationList(
                  viewModel: model,
                  onSelect: (id) {
                    model.open(id);
                    setState(() => _historyVisible = false);
                  },
                  onLoadMore: model.loadMoreConversations,
                )
              : model.selectedId == null
              ? _buildStart(context)
              : _buildConversation(context),
        ),
      ],
    );
  }

  Widget _buildStart(BuildContext context) {
    final model = widget.viewModel;
    final theme = LumenisTheme.of(context);
    return LayoutBuilder(
      builder: (context, constraints) {
        final compact = constraints.maxWidth < 620;
        final margin = compact ? 20.0 : 44.0;
        return SingleChildScrollView(
          key: const ValueKey('acc03-home-scroll'),
          padding: EdgeInsets.fromLTRB(
            margin,
            constraints.maxHeight > 800 ? 56 : 16,
            margin,
            28,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Padding(
                padding: const EdgeInsets.only(bottom: 28),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Expanded(
                      child: Text(
                        switch (context.lumenisL10n.locale.languageCode) {
                          'en' => 'What are we working on?',
                          'ko' => '어떤 작업을 시작할까요?',
                          _ => '今天要完成什么？',
                        },
                        style: TextStyle(
                          color: theme.foreground,
                          fontSize: compact ? 29 : 40,
                          fontWeight: FontWeight.w500,
                          letterSpacing: -.8,
                          height: 1.25,
                        ),
                      ),
                    ),
                    if (!compact)
                      const Padding(
                        padding: EdgeInsets.only(left: 24),
                        child: LumenisBotanical(size: 64),
                      ),
                  ],
                ),
              ),
              _composer(context, newConversation: true),
              if (model.issue != null) ...[
                const SizedBox(height: 12),
                _ConversationNotice(
                  issue: model.issue!,
                  unknown: model.creatingUnknown,
                  checkKey: 'ai01-conversation-start-retry',
                  onCheck: () => model.refreshList(selectFirstIfEmpty: false),
                ),
              ],
              if (widget.startActions != null) ...[
                const SizedBox(height: 20),
                widget.startActions!,
              ],
            ],
          ),
        );
      },
    );
  }

  Widget _composer(BuildContext context, {bool newConversation = false}) {
    final model = widget.viewModel;
    final copy = context.lumenisL10n;
    final theme = LumenisTheme.of(context);
    final canSend = newConversation
        ? !model.busy && !model.creatingUnknown && !model.outcomeUnknown
        : model.canSend;
    void submitShortcut() {
      final value = widget.draftController.value;
      if (canSend &&
          value.text.trim().isNotEmpty &&
          (!value.composing.isValid || value.composing.isCollapsed)) {
        _send();
      }
    }

    return CallbackShortcuts(
      bindings: {
        const SingleActivator(LogicalKeyboardKey.enter, control: true):
            submitShortcut,
        const SingleActivator(LogicalKeyboardKey.enter, meta: true):
            submitShortcut,
      },
      child: Container(
        key: const ValueKey('ai01-conversation-composer'),
        padding: const EdgeInsets.fromLTRB(22, 20, 14, 12),
        decoration: ShapeDecoration(
          color: theme.surface,
          shape: LumenisPixelBorder(
            step: 4,
            side: BorderSide(color: theme.foreground, width: 1.2),
          ),
          shadows: [
            BoxShadow(
              color: theme.line.withValues(alpha: .5),
              offset: const Offset(4, 4),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            TextField(
              key: const ValueKey('ai01-conversation-input'),
              controller: widget.draftController,
              enabled: !model.busy,
              minLines: newConversation ? 2 : 1,
              maxLines: 5,
              maxLength: 4000,
              onChanged: (_) => setState(() {}),
              textInputAction: TextInputAction.newline,
              decoration: InputDecoration(
                hintText: copy.text('ai01.conversation.input_hint'),
                counterText: '',
                border: InputBorder.none,
                enabledBorder: InputBorder.none,
                focusedBorder: InputBorder.none,
                filled: false,
                contentPadding: EdgeInsets.zero,
              ),
            ),
            const SizedBox(height: 12),
            Divider(height: 1, color: theme.line.withValues(alpha: .55)),
            const SizedBox(height: 8),
            Row(
              children: [
                if (widget.onOpenMaterials != null)
                  IconButton(
                    key: const ValueKey('ai01-conversation-materials'),
                    tooltip: copy.text('screen.SH-02'),
                    onPressed: widget.onOpenMaterials,
                    icon: const LumenisIcon(
                      Icons.attach_file_rounded,
                      size: 20,
                    ),
                  ),
                IconButton(
                  key: const ValueKey('ai01-conversation-draft-actions'),
                  tooltip: switch (copy.locale.languageCode) {
                    'en' => 'Draft',
                    'ko' => '초안',
                    _ => '草稿',
                  },
                  isSelected: _draftActionsVisible,
                  onPressed: () => setState(
                    () => _draftActionsVisible = !_draftActionsVisible,
                  ),
                  icon: const LumenisIcon(Icons.more_horiz_rounded, size: 20),
                ),
                if (newConversation)
                  IconButton(
                    key: const ValueKey('ai01-conversation-new-context'),
                    tooltip: copy.text('ai01.conversation.context.open'),
                    onPressed: model.busy || model.outcomeUnknown
                        ? null
                        : () async {
                            await _createConversation();
                            if (mounted && model.selectedId != null) {
                              await _editContext();
                            }
                          },
                    icon: const LumenisIcon(Icons.tune_rounded, size: 20),
                  ),
                const Spacer(),
                IconButton.filled(
                  key: const ValueKey('ai01-conversation-send'),
                  tooltip: copy.text('ai01.conversation.send'),
                  style: IconButton.styleFrom(
                    backgroundColor: theme.accentStrong,
                    shape: const LumenisPixelBorder(step: 3),
                  ),
                  onPressed:
                      canSend && widget.draftController.text.trim().isNotEmpty
                      ? _send
                      : null,
                  icon: model.busy
                      ? const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const LumenisIcon(Icons.arrow_upward_rounded, size: 20),
                ),
              ],
            ),
            if (widget.draftController case final Ai01WorkspaceDraft draft)
              Ai01DraftStatus(draft: draft),
            if (_draftActionsVisible)
              Ai01DraftActions(
                key: ObjectKey(widget.draftController),
                controller: widget.draftController,
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildPhone(BuildContext context) {
    final model = widget.viewModel;
    if (model.selectedId == null) {
      return _ConversationList(
        viewModel: model,
        onSelect: model.open,
        onLoadMore: model.loadMoreConversations,
      );
    }
    return Column(
      children: [
        Align(
          alignment: Alignment.centerLeft,
          child: TextButton.icon(
            key: const ValueKey('ai01-conversation-back-list'),
            onPressed: model.busy ? null : model.showConversationList,
            icon: const LumenisIcon(Icons.arrow_back_rounded, size: 18),
            label: Text(context.lumenisL10n.text('ai01.conversation.list')),
          ),
        ),
        Expanded(child: _buildConversation(context)),
      ],
    );
  }

  Widget _buildConversation(BuildContext context) {
    final model = widget.viewModel;
    final copy = context.lumenisL10n;
    final theme = LumenisTheme.of(context);
    final detail = model.detail;
    if (model.detailLoading && detail == null) {
      return const Center(child: CircularProgressIndicator());
    }
    if (model.selectedId == null || detail == null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(copy.text('ai01.conversation.empty')),
              const SizedBox(height: 14),
              FilledButton.icon(
                key: const ValueKey('ai01-conversation-create-empty'),
                onPressed: model.busy ? null : _createConversation,
                icon: const LumenisIcon(Icons.add_rounded, size: 18),
                label: Text(copy.text('ai01.conversation.new')),
              ),
            ],
          ),
        ),
      );
    }
    final currentTaskId = widget.currentTaskId;
    final taskAlreadyLinked =
        currentTaskId != null &&
        detail.turns.any((turn) => turn.taskId == currentTaskId);
    final userTurns = {
      for (final turn in detail.turns)
        if (turn.originKind == 'user_input') turn.id: turn,
    };
    final respondedTurnIds = detail.turns
        .where((turn) => turn.originKind == 'model_output')
        .map((turn) => turn.replyTo)
        .whereType<String>()
        .toSet();
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 10, 16, 8),
          child: Row(
            children: [
              Expanded(
                child: Text(
                  detail.title.isEmpty
                      ? copy.text('ai01.conversation.untitled')
                      : detail.title,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.titleMedium,
                ),
              ),
              IconButton(
                key: const ValueKey('ai01-conversation-context-open'),
                tooltip: copy.text('ai01.conversation.context.open'),
                onPressed: detail.state == 'active' ? _editContext : null,
                icon: const LumenisIcon(Icons.edit_note_rounded, size: 21),
              ),
              IconButton(
                key: const ValueKey('ai01-conversation-refresh'),
                tooltip: copy.text('ai01.conversation.check'),
                onPressed: model.detailLoading ? null : _checkOutcome,
                icon: const LumenisIcon(Icons.refresh_rounded, size: 19),
              ),
            ],
          ),
        ),
        if (model.issue != null)
          _ConversationNotice(
            issue: model.issue!,
            unknown: model.outcomeUnknown,
            checkKey: 'ai01-conversation-check-outcome-detail',
            onCheck: model.outcomeUnknown ? _checkOutcome : null,
            onRetryAppend: model.pendingAppendText == null || model.busy
                ? null
                : _retryAppend,
          ),
        if (currentTaskId != null && !taskAlreadyLinked)
          Align(
            alignment: Alignment.centerLeft,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 14),
              child: TextButton.icon(
                key: const ValueKey('ai01-conversation-attach-task'),
                onPressed: model.busy
                    ? null
                    : () => model.attachTask(currentTaskId),
                icon: const LumenisIcon(Icons.link_rounded, size: 18),
                label: Text(copy.text('ai01.conversation.attach_task')),
              ),
            ),
          ),
        Divider(height: 1, color: theme.line),
        Expanded(
          child: detail.turns.isEmpty
              ? Center(child: Text(copy.text('ai01.conversation.no_messages')))
              : ListView.builder(
                  key: ValueKey('ai01-conversation-turns-${detail.id}'),
                  padding: const EdgeInsets.all(16),
                  itemCount: detail.turns.length + (detail.hasMore ? 1 : 0),
                  itemBuilder: (context, index) {
                    if (detail.hasMore && index == detail.turns.length) {
                      return Center(
                        child: TextButton.icon(
                          key: const ValueKey(
                            'ai01-conversation-load-more-turns',
                          ),
                          onPressed: model.detailLoading
                              ? null
                              : model.loadMoreTurns,
                          icon: model.detailLoading
                              ? const SizedBox(
                                  width: 16,
                                  height: 16,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                  ),
                                )
                              : const LumenisIcon(
                                  Icons.expand_more_rounded,
                                  size: 18,
                                ),
                          label: Text(copy.text('ai01.conversation.load_more')),
                        ),
                      );
                    }
                    final turn = detail.turns[index];
                    final userTurn = turn.replyTo == null
                        ? null
                        : userTurns[turn.replyTo];
                    return Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: _TurnCard(
                        turn: turn,
                        onRetry:
                            userTurn == null ||
                                model.busy ||
                                !{
                                  'failed',
                                  'unavailable',
                                  'interrupted',
                                }.contains(turn.state)
                            ? null
                            : () => _confirmRetry(userTurn),
                        onRespond:
                            turn.originKind == 'user_input' &&
                                !respondedTurnIds.contains(turn.id) &&
                                !model.busy &&
                                !model.outcomeUnknown
                            ? () => model.respondToTurn(turn, confirmed: true)
                            : null,
                        onInterrupt: turn.state != 'reserved' || model.busy
                            ? null
                            : () => _confirmInterrupt(turn),
                      ),
                    );
                  },
                ),
        ),
        if (widget.embedded)
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
            child: _composer(context),
          )
        else
          Padding(
            padding: const EdgeInsets.fromLTRB(14, 10, 14, 12),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Expanded(
                  child: TextField(
                    key: const ValueKey('ai01-conversation-input'),
                    controller: widget.draftController,
                    enabled: model.canSend,
                    minLines: 1,
                    maxLines: 4,
                    maxLength: 4000,
                    onChanged: (_) => setState(() {}),
                    textInputAction: TextInputAction.newline,
                    decoration: InputDecoration(
                      hintText: copy.text('ai01.conversation.input_hint'),
                      counterText: '',
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(16),
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                IconButton.filled(
                  key: const ValueKey('ai01-conversation-send'),
                  tooltip: copy.text('ai01.conversation.send'),
                  onPressed:
                      model.canSend &&
                          widget.draftController.text.trim().isNotEmpty
                      ? _send
                      : null,
                  icon: model.busy
                      ? const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const LumenisIcon(Icons.arrow_upward_rounded, size: 20),
                ),
              ],
            ),
          ),
      ],
    );
  }
}

class _ConversationContextEditor extends StatefulWidget {
  const _ConversationContextEditor({
    required this.conversationId,
    required this.viewModel,
    this.leaveGuard,
  });

  final String conversationId;
  final Ai01ConversationViewModel viewModel;
  final LumenisLeaveGuard? leaveGuard;

  @override
  State<_ConversationContextEditor> createState() =>
      _ConversationContextEditorState();
}

class _ConversationContextEditorState
    extends State<_ConversationContextEditor> {
  final _goal = TextEditingController();
  final _constraints = TextEditingController();
  final _draft = TextEditingController();
  final _decisions = TextEditingController();
  final _excluded = <String>{};
  List<Map<String, dynamic>> _sources = [];
  Ai01ConversationContext? _saved;
  Ai01ConversationContext? _remote;
  bool _loading = true;
  bool _saving = false;
  String? _notice;

  Map<String, dynamic> get _value => {
    'goal': _goal.text,
    'constraints': _lines(_constraints.text),
    'draft': _draft.text,
    'decisions': _lines(_decisions.text),
    'excluded_turn_ids': _excluded.toList()..sort(),
  };

  static List<String> _lines(String text) => text
      .split('\n')
      .map((line) => line.trim())
      .where((line) => line.isNotEmpty)
      .toList();

  static String _signature(Map<String, dynamic> value) => jsonEncode({
    for (final key in ['goal', 'constraints', 'draft', 'decisions'])
      key: value[key],
    'excluded_turn_ids': List<String>.from(value['excluded_turn_ids'] as List)
      ..sort(),
  });

  String _sourceSignature(List<Map<String, dynamic>> sources) =>
      jsonEncode(sources.map((source) => source['reference']).toList());

  bool get _dirty =>
      _saved != null &&
      (_signature(_value) != _signature(_saved!.value) ||
          _sourceSignature(_sources) !=
              _sourceSignature(_saved!.sourceReferences));

  Future<void> _addSource() async {
    final repository = widget.viewModel.repository;
    if (repository is! Ai01ConversationSources || _saved == null) return;
    final source = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (_) => Ai01SourcePicker(
        repository: repository as Ai01ConversationSources,
        conversationId: widget.conversationId,
      ),
    );
    if (!mounted || source == null) return;
    final identity = jsonEncode(source['reference']);
    if (!_sources.any((item) => jsonEncode(item['reference']) == identity)) {
      setState(() => _sources = [..._sources, source]);
      widget.leaveGuard?.refresh();
    }
  }

  @override
  void initState() {
    super.initState();
    for (final controller in [_goal, _constraints, _draft, _decisions]) {
      controller.addListener(_changed);
    }
    widget.viewModel.addListener(_changed);
    widget.leaveGuard?.register(
      this,
      needsProtection: () => _dirty || _saving,
      requestLeave: () async => false,
    );
    _load(replaceLocal: true);
  }

  void _changed() {
    if (mounted && widget.viewModel.selectedId != widget.conversationId) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) Navigator.of(context).pop(false);
      });
      return;
    }
    if (mounted) setState(() {});
    widget.leaveGuard?.refresh();
  }

  void _apply(Ai01ConversationContext saved) {
    _saved = saved;
    _sources = saved.sourceReferences
        .map((source) => Map<String, dynamic>.from(source))
        .toList();
    _remote = null;
    _goal.text = saved.value['goal'] as String;
    _constraints.text = (saved.value['constraints'] as List).join('\n');
    _draft.text = saved.value['draft'] as String;
    _decisions.text = (saved.value['decisions'] as List).join('\n');
    _excluded
      ..clear()
      ..addAll(List<String>.from(saved.value['excluded_turn_ids'] as List));
    if (saved.turn case final Ai01ConversationTurn turn) {
      widget.viewModel.applyContextMutation(
        Ai01ConversationMutation(
          turn: turn,
          revision: saved.revision,
          idempotentHit: true,
        ),
      );
    }
  }

  static bool _readDenied(int? status) =>
      const {401, 403, 404, 410}.contains(status);

  Future<void> _clearRestricted(int? status) async {
    _saved = null;
    _remote = null;
    _excluded.clear();
    _sources = [];
    _notice = status == 401 ? 'authentication' : 'permission';
    for (final controller in [_goal, _constraints, _draft, _decisions]) {
      controller.clear();
    }
    // The transcript shares this read gate. Reopen through its existing owner
    // so the parent also drops its cached detail before any further display.
    await widget.viewModel.open(widget.conversationId);
  }

  Future<void> _load({bool replaceLocal = false}) async {
    setState(() => _loading = true);
    try {
      final saved = await widget.viewModel.repository.readContext(
        widget.conversationId,
      );
      if (!mounted) return;
      if (replaceLocal ||
          _saved == null ||
          (_signature(saved.value) == _signature(_value) &&
              _sourceSignature(saved.sourceReferences) ==
                  _sourceSignature(_sources))) {
        _apply(saved);
        _notice = replaceLocal ? null : 'saved';
      } else {
        _remote = saved;
        _notice = 'conflict';
      }
    } on LumenisCoreException catch (error) {
      if (!mounted) return;
      if (_readDenied(error.statusCode)) {
        await _clearRestricted(error.statusCode);
      } else {
        _notice = 'load_error';
      }
    } catch (_) {
      if (!mounted) return;
      _notice = 'load_error';
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _save({bool keepLocal = false}) async {
    final saved = keepLocal ? _remote : _saved;
    if (saved == null || _saving || _loading) return;
    final value = _value;
    final sources = _sources
        .map((item) => Map<String, dynamic>.from(item))
        .toList();
    setState(() {
      _saving = true;
      _notice = null;
    });
    try {
      final result = await widget.viewModel.repository.updateContext(
        conversationId: widget.conversationId,
        value: value,
        idempotencyKey: 'context-${DateTime.now().microsecondsSinceEpoch}',
        expectedRevision: saved.revision,
        sourceReferences: sources
            .map((item) => Map<String, dynamic>.from(item['reference'] as Map))
            .toList(),
      );
      if (!mounted) return;
      // Editing stays available during save; a receipt never overwrites text
      // entered after the submitted snapshot.
      _saved = Ai01ConversationContext(
        conversationId: widget.conversationId,
        revision: result.revision,
        value: value,
        turn: result.turn,
        sourceReferences: sources,
      );
      _remote = null;
      widget.viewModel.applyContextMutation(result);
      _notice = _signature(value) == _signature(_value) ? 'saved' : null;
    } on LumenisCoreException catch (error) {
      if (!mounted) return;
      if (error.statusCode == 409) {
        await _load();
        if (mounted && _remote != null) _notice = 'conflict';
      } else if (_readDenied(error.statusCode)) {
        // A denied write does not establish that reading was revoked. Keep
        // permitted writing, but clear it if the independent read is denied.
        await _load();
        if (mounted && _saved != null && _notice != 'load_error') {
          _notice = error.statusCode == 401 ? 'authentication' : 'permission';
        }
      } else {
        _notice = switch (error.statusCode) {
          400 => 'invalid',
          _ => 'save_error',
        };
      }
    } catch (_) {
      if (!mounted) return;
      _notice = 'save_error';
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  void dispose() {
    widget.leaveGuard?.unregister(this);
    widget.viewModel.removeListener(_changed);
    for (final controller in [_goal, _constraints, _draft, _decisions]) {
      controller.removeListener(_changed);
      controller.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    final theme = LumenisTheme.of(context);
    String text(String key) => copy.text('ai01.conversation.context.$key');
    final turns =
        _saved != null && widget.viewModel.detail?.id == widget.conversationId
        ? widget.viewModel.detail!.turns
              .where((turn) => turn.originKind == 'user_input')
              .toList()
        : <Ai01ConversationTurn>[];
    return PopScope(
      canPop: !_dirty && !_saving,
      child: AlertDialog(
        key: const ValueKey('ai01-conversation-context-editor'),
        title: Text(text('title')),
        content: SizedBox(
          width: 640,
          height: MediaQuery.sizeOf(context).height * .62,
          child: _loading && _saved == null
              ? const Center(child: CircularProgressIndicator())
              : ListView(
                  children: [
                    if (widget.viewModel.repository
                        is Ai01ConversationSources) ...[
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              _referenceText('参考资料', 'References', '참고 자료'),
                              style: Theme.of(context).textTheme.titleSmall,
                            ),
                          ),
                          TextButton.icon(
                            onPressed: _saved == null || _saving
                                ? null
                                : _addSource,
                            icon: const Icon(Icons.add, size: 18),
                            label: Text(_referenceText('添加', 'Add', '추가')),
                          ),
                        ],
                      ),
                      for (final source in _sources)
                        ListTile(
                          contentPadding: EdgeInsets.zero,
                          leading: Icon(
                            source['state'] == 'available'
                                ? Icons.description_outlined
                                : Icons.link_off,
                          ),
                          title: Text(
                            source['state'] == 'available'
                                ? (source['title'] as String? ??
                                      _referenceText(
                                        '已选资料',
                                        'Selected material',
                                        '선택한 자료',
                                      ))
                                : _referenceText(
                                    '资料不可用',
                                    'Material unavailable',
                                    '자료 사용 불가',
                                  ),
                            maxLines: 2,
                          ),
                          trailing: IconButton(
                            onPressed: _saving
                                ? null
                                : () {
                                    setState(() => _sources.remove(source));
                                    widget.leaveGuard?.refresh();
                                  },
                            tooltip: _referenceText('移除', 'Remove', '제거'),
                            icon: const Icon(Icons.close, size: 18),
                          ),
                        ),
                      const Divider(height: 24),
                    ],
                    if (_notice case final String notice) ...[
                      Text(
                        const {
                              'authentication',
                              'permission',
                              'invalid',
                            }.contains(notice)
                            ? copy.text('ai01.conversation.issue.$notice')
                            : text(notice),
                        key: const ValueKey('ai01-conversation-context-notice'),
                        style: TextStyle(
                          color: notice == 'saved'
                              ? theme.muted
                              : theme.caution,
                        ),
                      ),
                      const SizedBox(height: 12),
                    ],
                    if (_remote != null) ...[
                      ExpansionTile(
                        key: const ValueKey(
                          'ai01-conversation-context-remote-preview',
                        ),
                        title: Text(text('check')),
                        children: [
                          for (final key in [
                            'goal',
                            'constraints',
                            'draft',
                            'decisions',
                          ])
                            Padding(
                              padding: const EdgeInsets.fromLTRB(12, 4, 12, 12),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.stretch,
                                children: [
                                  Text(
                                    text(key),
                                    style: Theme.of(
                                      context,
                                    ).textTheme.labelMedium,
                                  ),
                                  SelectableText(
                                    _remote!.value[key] is List
                                        ? (_remote!.value[key] as List).join(
                                            '\n',
                                          )
                                        : _remote!.value[key] as String,
                                  ),
                                ],
                              ),
                            ),
                        ],
                      ),
                      TextButton(
                        key: const ValueKey(
                          'ai01-conversation-context-use-saved',
                        ),
                        onPressed: _saving
                            ? null
                            : () => setState(() {
                                _apply(_remote!);
                                _notice = null;
                              }),
                        child: Text(text('use_saved')),
                      ),
                      TextButton(
                        key: const ValueKey(
                          'ai01-conversation-context-keep-local',
                        ),
                        onPressed: _saving
                            ? null
                            : () => _save(keepLocal: true),
                        child: Text(text('keep_local')),
                      ),
                    ],
                    for (final field in [
                      (name: 'goal', controller: _goal, lines: 2),
                      (name: 'constraints', controller: _constraints, lines: 3),
                      (name: 'draft', controller: _draft, lines: 5),
                      (name: 'decisions', controller: _decisions, lines: 3),
                    ]) ...[
                      TextField(
                        key: ValueKey(
                          'ai01-conversation-context-${field.name}',
                        ),
                        controller: field.controller,
                        enabled: _saved != null,
                        minLines: field.lines,
                        maxLines: field.lines + 3,
                        maxLength: 32000,
                        decoration: InputDecoration(
                          labelText: text(field.name),
                          counterText: '',
                        ),
                      ),
                      const SizedBox(height: 16),
                    ],
                    Text(
                      text('forget'),
                      style: Theme.of(context).textTheme.titleSmall,
                    ),
                    const SizedBox(height: 6),
                    Text(text('forget_detail')),
                    const SizedBox(height: 8),
                    for (final turn in turns)
                      ExpansionTile(
                        title: Text(
                          turn.text ?? '',
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                        trailing: Checkbox(
                          key: ValueKey(
                            'ai01-conversation-context-exclude-${turn.id}',
                          ),
                          semanticLabel: text('forget'),
                          value: _excluded.contains(turn.id),
                          onChanged: _saved == null
                              ? null
                              : (value) => setState(() {
                                  value == true
                                      ? _excluded.add(turn.id)
                                      : _excluded.remove(turn.id);
                                }),
                        ),
                        children: [
                          Padding(
                            padding: const EdgeInsets.all(12),
                            child: SelectableText(turn.text ?? ''),
                          ),
                        ],
                      ),
                    if (widget.viewModel.detail?.hasMore == true)
                      TextButton(
                        onPressed: widget.viewModel.detailLoading
                            ? null
                            : widget.viewModel.loadMoreTurns,
                        child: Text(copy.text('ai01.conversation.load_more')),
                      ),
                  ],
                ),
        ),
        actions: [
          TextButton(
            key: const ValueKey('ai01-conversation-context-close'),
            onPressed: _saving ? null : () => Navigator.of(context).pop(false),
            child: Text(copy.text(_dirty ? 'common.cancel' : 'common.close')),
          ),
          TextButton(
            key: const ValueKey('ai01-conversation-context-check'),
            onPressed: _saving || _loading ? null : _load,
            child: Text(text('check')),
          ),
          FilledButton(
            key: const ValueKey('ai01-conversation-context-save'),
            onPressed:
                _saving ||
                    _loading ||
                    _saved == null ||
                    !_dirty ||
                    _remote != null ||
                    _notice == 'save_error'
                ? null
                : _save,
            child: _saving
                ? const SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : Text(copy.text('common.save')),
          ),
        ],
      ),
    );
  }

  String _referenceText(String zh, String en, String ko) =>
      switch (context.lumenisL10n.locale.languageCode) {
        'en' => en,
        'ko' => ko,
        _ => zh,
      };
}

class _PanelHeader extends StatelessWidget {
  const _PanelHeader({
    required this.title,
    required this.onClose,
    required this.onRefresh,
    required this.onCreate,
    required this.busy,
  });

  final String title;
  final VoidCallback onClose;
  final VoidCallback onRefresh;
  final VoidCallback onCreate;
  final bool busy;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    final theme = LumenisTheme.of(context);
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 10, 8, 10),
      child: Row(
        children: [
          Expanded(
            child: Text(
              title,
              style: Theme.of(
                context,
              ).textTheme.titleLarge?.copyWith(color: theme.foreground),
            ),
          ),
          IconButton(
            key: const ValueKey('ai01-conversation-list-refresh'),
            tooltip: copy.text('common.refresh'),
            onPressed: busy ? null : onRefresh,
            icon: const LumenisIcon(Icons.refresh_rounded, size: 19),
          ),
          FilledButton.tonalIcon(
            key: const ValueKey('ai01-conversation-new'),
            onPressed: busy ? null : onCreate,
            icon: const LumenisIcon(Icons.add_rounded, size: 18),
            label: Text(copy.text('ai01.conversation.new')),
          ),
          IconButton(
            key: const ValueKey('ai01-conversation-close'),
            tooltip: copy.text('common.close'),
            onPressed: onClose,
            icon: const LumenisIcon(Icons.close_rounded, size: 20),
          ),
        ],
      ),
    );
  }
}

class _ConversationList extends StatelessWidget {
  const _ConversationList({
    required this.viewModel,
    required this.onSelect,
    required this.onLoadMore,
  });

  final Ai01ConversationViewModel viewModel;
  final ValueChanged<String> onSelect;
  final VoidCallback onLoadMore;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    if (viewModel.listLoading && viewModel.conversations.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }
    if (viewModel.issue != null && viewModel.conversations.isEmpty) {
      return Column(
        children: [
          _ConversationNotice(
            issue: viewModel.issue!,
            unknown: viewModel.creatingUnknown,
            checkKey: 'ai01-conversation-check-outcome-list-empty',
            onCheck: viewModel.refreshList,
          ),
          Expanded(
            child: Center(
              child: Padding(
                padding: const EdgeInsets.all(18),
                child: Text(copy.text('ai01.conversation.empty_list')),
              ),
            ),
          ),
        ],
      );
    }
    return Column(
      children: [
        if (viewModel.issue != null)
          _ConversationNotice(
            issue: viewModel.issue!,
            unknown: viewModel.creatingUnknown,
            checkKey: 'ai01-conversation-check-outcome-list',
            onCheck: viewModel.refreshList,
          ),
        Expanded(
          child: viewModel.conversations.isEmpty
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(18),
                    child: Text(copy.text('ai01.conversation.empty_list')),
                  ),
                )
              : ListView.builder(
                  key: const ValueKey('ai01-conversation-list'),
                  padding: const EdgeInsets.all(10),
                  itemCount:
                      viewModel.conversations.length +
                      (viewModel.listHasMore ? 1 : 0),
                  itemBuilder: (context, index) {
                    if (index == viewModel.conversations.length) {
                      return TextButton(
                        key: const ValueKey('ai01-conversation-load-more-list'),
                        onPressed: viewModel.canLoadMoreConversations
                            ? onLoadMore
                            : null,
                        child: Text(copy.text('ai01.conversation.load_more')),
                      );
                    }
                    final item = viewModel.conversations[index];
                    return Padding(
                      padding: const EdgeInsets.only(bottom: 6),
                      child: ListTile(
                        key: ValueKey('ai01-conversation-${item.id}'),
                        selected: item.id == viewModel.selectedId,
                        title: Text(
                          item.title.isEmpty
                              ? copy.text('ai01.conversation.untitled')
                              : item.title,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                        subtitle: item.state == 'archived'
                            ? Text(copy.text('ai01.conversation.archived'))
                            : null,
                        onTap: () => onSelect(item.id),
                      ),
                    );
                  },
                ),
        ),
      ],
    );
  }
}

class _TurnCard extends StatelessWidget {
  const _TurnCard({
    required this.turn,
    this.onRetry,
    this.onRespond,
    this.onInterrupt,
  });

  final Ai01ConversationTurn turn;
  final VoidCallback? onRetry;
  final VoidCallback? onRespond;
  final VoidCallback? onInterrupt;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    final theme = LumenisTheme.of(context);
    final user = turn.role == 'user';
    final text = turn.text;
    final label = switch (turn.originKind) {
      'user_input' => copy.text('ai01.conversation.you'),
      'model_output' => copy.text('ai01.conversation.reply'),
      'task_projection' => copy.text('ai01.conversation.task'),
      _ => copy.text('ai01.conversation.status'),
    };
    final stateLabel = switch (turn.state) {
      'reserved' => copy.text('ai01.conversation.state.reserved'),
      'unavailable' => copy.text('ai01.conversation.state.unavailable'),
      'failed' => copy.text('ai01.conversation.state.failed'),
      'interrupted' => copy.text('ai01.conversation.state.interrupted'),
      _ => null,
    };
    final displayText =
        text ??
        switch (turn.state) {
          'reserved' => copy.text('ai01.conversation.waiting'),
          'unavailable' => copy.text('ai01.conversation.no_reply'),
          'failed' => copy.text('ai01.conversation.no_reply'),
          'interrupted' => copy.text('ai01.conversation.interrupted_unknown'),
          _
              when turn.originKind == 'task_projection' &&
                  turn.content['state'] == 'source_access_unavailable' =>
            copy.text('ai01.conversation.task_unavailable'),
          _ when turn.originKind == 'task_projection' => copy.text(
            'ai01.conversation.task_attached',
          ),
          _
              when turn.originKind == 'system_status' &&
                  turn.content['schema'] == 'conversation-human-context/v1' =>
            copy.text('ai01.conversation.context.saved'),
          _ => copy.text('ai01.conversation.content_unavailable'),
        };
    return Align(
      alignment: user ? Alignment.centerRight : Alignment.centerLeft,
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 680),
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: user ? theme.ai.withValues(alpha: 0.1) : theme.canvas,
            border: Border.all(color: theme.line),
            borderRadius: BorderRadius.circular(16),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      label,
                      style: Theme.of(
                        context,
                      ).textTheme.labelMedium?.copyWith(color: theme.muted),
                    ),
                  ),
                  if (stateLabel != null)
                    Text(
                      stateLabel,
                      style: Theme.of(context).textTheme.labelSmall?.copyWith(
                        color: turn.state == 'completed'
                            ? theme.muted
                            : theme.caution,
                      ),
                    ),
                ],
              ),
              const SizedBox(height: 8),
              SelectableText(
                displayText,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: theme.foreground,
                  height: 1.5,
                ),
              ),
              if (turn.state == 'reserved' && onInterrupt != null) ...[
                const SizedBox(height: 8),
                TextButton(
                  key: ValueKey('ai01-conversation-interrupt-${turn.id}'),
                  onPressed: onInterrupt,
                  child: Text(copy.text('ai01.conversation.interrupt.action')),
                ),
              ],
              if (onRespond != null) ...[
                const SizedBox(height: 8),
                TextButton.icon(
                  key: ValueKey('ai01-conversation-respond-${turn.id}'),
                  onPressed: onRespond,
                  icon: const LumenisIcon(Icons.reply_rounded, size: 17),
                  label: Text(copy.text('ai01.conversation.respond.action')),
                ),
              ],
              if (onRetry != null) ...[
                const SizedBox(height: 8),
                TextButton.icon(
                  key: ValueKey('ai01-conversation-retry-${turn.id}'),
                  onPressed: onRetry,
                  icon: const LumenisIcon(Icons.refresh_rounded, size: 17),
                  label: Text(copy.text('ai01.conversation.retry.action')),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _ConversationNotice extends StatelessWidget {
  const _ConversationNotice({
    required this.issue,
    required this.unknown,
    required this.checkKey,
    this.onCheck,
    this.onRetryAppend,
  });

  final String issue;
  final bool unknown;
  final String checkKey;
  final VoidCallback? onCheck;
  final VoidCallback? onRetryAppend;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    final theme = LumenisTheme.of(context);
    final key = issue == 'create_unknown'
        ? 'ai01.conversation.issue.create_unknown'
        : issue == 'append_unknown'
        ? 'ai01.conversation.issue.append_unknown'
        : unknown
        ? 'ai01.conversation.issue.unknown'
        : 'ai01.conversation.issue.$issue';
    return Container(
      key: const ValueKey('ai01-conversation-notice'),
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.fromLTRB(14, 10, 14, 6),
      decoration: BoxDecoration(
        color: theme.caution.withValues(alpha: 0.08),
        border: Border(left: BorderSide(color: theme.caution, width: 3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(copy.text(key)),
          if (onCheck != null || onRetryAppend != null)
            Wrap(
              spacing: 4,
              runSpacing: 2,
              children: [
                if (onCheck != null)
                  TextButton(
                    key: ValueKey(checkKey),
                    onPressed: onCheck,
                    child: Text(copy.text('ai01.conversation.check')),
                  ),
                if (onRetryAppend != null)
                  TextButton(
                    key: const ValueKey('ai01-conversation-retry-append'),
                    onPressed: onRetryAppend,
                    child: Text(copy.text('ai01.conversation.append.retry')),
                  ),
              ],
            ),
        ],
      ),
    );
  }
}
