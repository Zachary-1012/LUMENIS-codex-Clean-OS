import 'package:flutter/material.dart';
import 'package:lumenis_app/core/lumenis_icon.dart';

import '../../../core/lumenis_core_client.dart';
import '../../../core/lumenis_theme.dart';
import '../../../l10n/lumenis_localizations.dart';
import '../../../features/ai01/ai01_conversation_panel.dart';
import '../../../features/ai01/ai01_conversations.dart';
import '../../../navigation/lumenis_workspace_routes.dart';
import 'acc03_repository.dart';
import 'acc03_snapshot.dart';

class Acc03Screen extends StatefulWidget {
  const Acc03Screen({
    required this.client,
    this.repository,
    this.onOpen,
    this.lastOpenedScreenId,
    this.onOpenScreenId,
    this.draftController,
    this.scopeLabel,
    super.key,
  });

  final LumenisCoreClient client;

  /// Retained for callers that still pass the former Home status repository.
  /// Home navigation and task entry do not depend on that runtime read.
  final Acc03Repository? repository;
  final ValueChanged<Acc03Destination>? onOpen;
  final String? lastOpenedScreenId;
  final ValueChanged<String>? onOpenScreenId;
  final TextEditingController? draftController;
  final String? scopeLabel;

  @override
  State<Acc03Screen> createState() => _Acc03ScreenState();
}

class _Acc03ScreenState extends State<Acc03Screen> {
  late Ai01ConversationViewModel _conversations;
  TextEditingController? _ownedDraft;

  TextEditingController get _draft => widget.draftController ?? _ownedDraft!;

  @override
  void initState() {
    super.initState();
    _conversations = Ai01ConversationViewModel(
      repository: CoreAi01ConversationRepository(client: widget.client),
    );
    if (widget.draftController == null) _ownedDraft = TextEditingController();
  }

  @override
  void didUpdateWidget(covariant Acc03Screen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.client != widget.client) {
      _conversations.dispose();
      _conversations = Ai01ConversationViewModel(
        repository: CoreAi01ConversationRepository(client: widget.client),
      );
    }
    if (widget.draftController == null && _ownedDraft == null) {
      _ownedDraft = TextEditingController();
    }
  }

  @override
  void dispose() {
    _conversations.dispose();
    _ownedDraft?.dispose();
    super.dispose();
  }

  String? get _safeLastOpenedScreenId {
    final screenId = widget.lastOpenedScreenId;
    if (screenId == null ||
        screenId == LumenisWorkspaceRoutes.rootScreenId ||
        LumenisWorkspaceRoutes.focusedReturnScreenIds.contains(screenId) ||
        !LumenisWorkspaceRoutes.supportsWorkspaceScreen(screenId)) {
      return null;
    }
    return screenId;
  }

  @override
  Widget build(BuildContext context) {
    final lastPage = _safeLastOpenedScreenId;

    return ColoredBox(
      color: LumenisTheme.of(context).canvas,
      child: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 940),
            child: Ai01ConversationPanel(
              key: ObjectKey(_conversations),
              viewModel: _conversations,
              draftController: _draft,
              embedded: true,
              onClose: () {},
              onOpenMaterials: widget.onOpen == null
                  ? null
                  : () => widget.onOpen!(Acc03Destination.research),
              startActions: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Wrap(
                    spacing: 4,
                    runSpacing: 4,
                    alignment: WrapAlignment.start,
                    children: [
                      for (final destination in acc03HomeDestinations)
                        _BusinessDestination(
                          destination: destination,
                          onOpen: widget.onOpen,
                        ),
                    ],
                  ),
                  if (widget.onOpen != null)
                    Align(
                      alignment: Alignment.centerLeft,
                      child: TextButton.icon(
                        key: const ValueKey('acc03-analysis'),
                        onPressed: () => widget.onOpen!(Acc03Destination.ai),
                        icon: const LumenisIcon(Icons.search_rounded, size: 18),
                        label: Text(
                          _copy(
                            context,
                            zh: '分析问题',
                            en: 'Analyze a question',
                            ko: '질문 분석',
                          ),
                        ),
                      ),
                    ),
                  if (lastPage != null && widget.onOpenScreenId != null) ...[
                    const SizedBox(height: 6),
                    _ContinueLastPage(
                      screenId: lastPage,
                      onOpen: () => widget.onOpenScreenId!(lastPage),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _BusinessDestination extends StatelessWidget {
  const _BusinessDestination({required this.destination, required this.onOpen});

  final Acc03LaunchCard destination;
  final ValueChanged<Acc03Destination>? onOpen;

  @override
  Widget build(BuildContext context) {
    final (screenId, label, icon) = switch (destination.destination) {
      Acc03Destination.commerce => (
        'CTH-01',
        _copy(context, zh: '商业运营', en: 'Commerce', ko: '커머스 운영'),
        Icons.timeline_rounded,
      ),
      Acc03Destination.brand => (
        'BMP-01',
        _copy(context, zh: '品牌与市场', en: 'Brand & market', ko: '브랜드 & 마켓'),
        Icons.hub_outlined,
      ),
      Acc03Destination.research => (
        'SH-02',
        _copy(context, zh: '研究与资料', en: 'Research', ko: '리서치'),
        Icons.library_books_outlined,
      ),
      Acc03Destination.creation => (
        'SH-01',
        _copy(context, zh: '内容创作', en: 'Create', ko: '콘텐츠 만들기'),
        Icons.edit_note_rounded,
      ),
      Acc03Destination.ai => (
        'AI-01',
        _copy(context, zh: '新任务', en: 'New task', ko: '새 작업'),
        Icons.auto_awesome_outlined,
      ),
    };

    return TextButton.icon(
      key: ValueKey('acc03-destination-$screenId'),
      onPressed: onOpen == null ? null : () => onOpen!(destination.destination),
      style: TextButton.styleFrom(
        minimumSize: const Size(48, 48),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        foregroundColor: LumenisTheme.of(context).foreground,
        shape: const StadiumBorder(),
      ),
      icon: LumenisIcon(icon, size: 18, color: LumenisTheme.of(context).muted),
      label: Text(label),
    );
  }
}

class _ContinueLastPage extends StatelessWidget {
  const _ContinueLastPage({required this.screenId, required this.onOpen});

  final String screenId;
  final VoidCallback onOpen;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    final title = copy.text('screen.$screenId');
    return Align(
      alignment: Alignment.centerLeft,
      child: TextButton.icon(
        key: const ValueKey('acc03-last-opened'),
        onPressed: onOpen,
        style: TextButton.styleFrom(
          minimumSize: const Size(48, 48),
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
          alignment: Alignment.centerLeft,
        ),
        icon: const LumenisIcon(Icons.history_rounded, size: 18),
        label: Text(
          _copy(
            context,
            zh: '继续上次页面 · $title',
            en: 'Continue where you left off · $title',
            ko: '마지막 페이지에서 계속 · $title',
          ),
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
          textAlign: TextAlign.start,
        ),
      ),
    );
  }
}

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
