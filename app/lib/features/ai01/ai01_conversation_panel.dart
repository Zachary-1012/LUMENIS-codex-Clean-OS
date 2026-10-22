import 'package:flutter/material.dart';

import '../../core/lumenis_icon.dart';
import '../../core/lumenis_theme.dart';
import '../../l10n/lumenis_localizations.dart';
import 'ai01_conversations.dart';

class Ai01ConversationPanel extends StatefulWidget {
  const Ai01ConversationPanel({
    required this.viewModel,
    required this.draftController,
    required this.onClose,
    this.currentTaskId,
    super.key,
  });

  final Ai01ConversationViewModel viewModel;
  final TextEditingController draftController;
  final String? currentTaskId;
  final VoidCallback onClose;

  @override
  State<Ai01ConversationPanel> createState() => _Ai01ConversationPanelState();
}

class _Ai01ConversationPanelState extends State<Ai01ConversationPanel> {
  final _ownedDialogs = <DialogRoute<bool>>{};

  @override
  void initState() {
    super.initState();
    widget.viewModel.refreshList();
  }

  Future<void> _send() async {
    final controller = widget.draftController;
    final draft = controller.value;
    final text = draft.text;
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
    _closeOwnedDialogs();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    final theme = LumenisTheme.of(context);
    final phone = MediaQuery.sizeOf(context).width < 600;
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
        Divider(height: 1, color: theme.line),
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
      margin: const EdgeInsets.fromLTRB(14, 4, 14, 8),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: theme.caution.withValues(alpha: 0.08),
        border: Border.all(color: theme.caution.withValues(alpha: 0.28)),
        borderRadius: BorderRadius.circular(12),
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
