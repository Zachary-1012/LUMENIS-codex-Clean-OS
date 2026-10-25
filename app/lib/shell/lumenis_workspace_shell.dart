import '../core/lumenis_botanical.dart';
import 'lumenis_workspace_frame.dart';
import 'dart:async';
import 'package:lumenis_app/core/lumenis_icon.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../features/system/sys05/sys05_appearance_editor.dart';

import '../core/lumenis_core_client.dart';
import '../core/lumenis_theme.dart';
import '../features/account/acc01/acc01_screen.dart';
import '../features/account/acc02/acc02_screen.dart';
import '../features/account/acc03/acc03_screen.dart';
import '../features/account/acc03/acc03_snapshot.dart';
import '../features/account/acc04/acc04_screen.dart';
import '../features/ai01/ai01_screen.dart';
import '../features/ai01/ai01_workspace_draft.dart';
import '../features/ai02/ai02_screen.dart';
import '../features/ai03/ai03_screen.dart';
import '../features/ai04/ai04_screen.dart';
import '../features/ai05/ai05_screen.dart';
import '../features/bmp01/bmp01_screen.dart';
import '../features/bmp02/bmp02_screen.dart';
import '../features/bmp03/bmp03_screen.dart';
import '../features/bmp04/bmp04_screen.dart';
import '../features/bmp05/bmp05_screen.dart';
import '../features/bmp06/bmp06_screen.dart';
import '../features/bmp07/bmp07_screen.dart';
import '../features/bmp08/bmp08_screen.dart';
import '../features/bmp09/bmp09_screen.dart';
import '../features/bmp10/bmp10_screen.dart';
import '../features/bmp11/bmp11_screen.dart';
import '../features/cth/cth01/cth01_screen.dart';
import '../features/cth/cth02/cth02_screen.dart';
import '../features/cth/cth03/cth03_screen.dart';
import '../features/cth/cth04/cth04_screen.dart';
import '../features/cth/cth05/cth05_screen.dart';
import '../features/cth/cth06/cth06_screen.dart';
import '../features/cth/cth07/cth07_screen.dart';
import '../features/cth/cth08/cth08_screen.dart';
import '../features/cth/cth09/cth09_screen.dart';
import '../features/cth/cth10/cth10_screen.dart';
import '../features/shared/sh01/sh01_screen.dart';
import '../features/shared/sh02/sh02_screen.dart';
import '../features/shared/sh03/sh03_screen.dart';
import '../features/shared/sh04/sh04_screen.dart';
import '../features/shared/sh05/sh05_screen.dart';
import '../features/shared/sh06/sh06_screen.dart';
import '../features/system/sys01/sys01_screen.dart';
import '../features/system/sys02/sys02_screen.dart';
import '../features/system/sys03/sys03_screen.dart';
import '../features/system/sys04/sys04_screen.dart';
import '../features/system/sys05/sys05_screen.dart';
import '../features/system/sys06/sys06_screen.dart';
import '../features/system/sys07/sys07_screen.dart';
import '../features/system/sys08/sys08_screen.dart';
import '../l10n/lumenis_localizations.dart';
import '../navigation/lumenis_workspace_routes.dart';
import '../navigation/lumenis_leave_guard.dart';

Widget buildLumenisWorkspaceScreen({
  required String screenId,
  required LumenisCoreClient client,
  bool contextAvailable = true,
  ValueChanged<String>? onNavigate,
  String? lastOpenedScreenId,
  String? workspaceEntry,
  String? returnScreenId,
  String? initialArtifactId,
  void Function(String kind, String artifactId)? onOpenSavedWork,
  ValueChanged<String>? onStartCreation,
  TextEditingController? taskDraftController,
  String? taskScopeLabel,
}) {
  if (!LumenisWorkspaceRoutes.supportsWorkspaceScreen(screenId)) {
    throw ArgumentError.value(
      screenId,
      'screenId',
      'Screen is not available in Web Workspace',
    );
  }
  return switch (screenId) {
    'ACC-01' => Acc01Screen(
      client: client,
      onContinue: onNavigate == null ? null : () => onNavigate('ACC-03'),
    ),
    'ACC-02' => Acc02Screen(
      client: client,
      onContinue: onNavigate == null ? null : () => onNavigate('ACC-03'),
    ),
    'ACC-03' => Acc03Screen(
      client: client,
      draftController: taskDraftController,
      scopeLabel: taskScopeLabel,
      onOpenWork: onOpenSavedWork,
      onStartCreation: onStartCreation,
      lastOpenedScreenId: lastOpenedScreenId,
      onOpenScreenId: onNavigate,
      onOpen: onNavigate == null
          ? null
          : (destination) => onNavigate(switch (destination) {
              Acc03Destination.commerce => 'CTH-01',
              Acc03Destination.brand => 'BMP-01',
              Acc03Destination.research => 'SH-02',
              Acc03Destination.creation => 'SH-01',
              Acc03Destination.ai => 'AI-01',
            }),
    ),
    'ACC-04' => Acc04Screen(
      client: client,
      onReturn: onNavigate == null ? null : () => onNavigate('ACC-03'),
    ),
    'AI-01' => Ai01Screen(
      client: client,
      draftController: taskDraftController,
      scopeLabel: taskScopeLabel,
    ),
    'AI-02' => Ai02Screen(client: client),
    'AI-03' => Ai03Screen(client: client),
    'AI-04' => Ai04Screen(client: client),
    'AI-05' => Ai05Screen(client: client),
    'CTH-01' => Cth01Screen(client: client, onNavigate: onNavigate),
    'CTH-02' => Cth02Screen(client: client),
    'CTH-03' => Cth03Screen(client: client),
    'CTH-04' => Cth04Screen(client: client),
    'CTH-05' => Cth05Screen(client: client),
    'CTH-06' => Cth06Screen(client: client),
    'CTH-07' => Cth07Screen(client: client),
    'CTH-08' => Cth08Screen(client: client),
    'CTH-09' => Cth09Screen(client: client),
    'CTH-10' => Cth10Screen(client: client),
    'BMP-01' => Bmp01Screen(client: client, onNavigate: onNavigate),
    'BMP-02' => Bmp02Screen(client: client),
    'BMP-03' => Bmp03Screen(client: client),
    'BMP-04' => Bmp04Screen(client: client),
    'BMP-05' => Bmp05Screen(client: client),
    'BMP-06' => Bmp06Screen(client: client),
    'BMP-07' => Bmp07Screen(client: client),
    'BMP-08' => Bmp08Screen(client: client, onNavigate: onNavigate),
    'BMP-09' => Bmp09Screen(client: client),
    'BMP-10' => Bmp10Screen(client: client),
    'BMP-11' => Bmp11Screen(client: client),
    'SH-01' => Sh01Screen(
      client: client,
      contextAvailable: contextAvailable,
      initialWorkspaceEntry: workspaceEntry,
      returnScreenId: returnScreenId,
      initialArtifactId: initialArtifactId,
      onSavedManuscript: onOpenSavedWork == null
          ? null
          : (artifact) => onOpenSavedWork('manuscript', artifact),
      onNavigate: onNavigate,
    ),
    'SH-02' => Sh02Screen(
      client: client,
      initialArtifactId: initialArtifactId,
      initialWorkKind: workspaceEntry,
      onBack: onNavigate == null ? null : () => onNavigate('SH-02'),
    ),
    'SH-03' => Sh03Screen(client: client),
    'SH-04' => Sh04Screen(client: client, initialArtifactId: initialArtifactId),
    'SH-05' => Sh05Screen(client: client),
    'SH-06' => Sh06Screen(client: client),
    'SYS-01' => Sys01Screen(client: client),
    'SYS-02' => Sys02Screen(client: client),
    'SYS-03' => Sys03Screen(client: client),
    'SYS-04' => Sys04Screen(client: client),
    'SYS-05' => Sys05Screen(
      client: client,
      onOpenSubjects: onNavigate == null ? null : () => onNavigate('ACC-02'),
      onNavigate: onNavigate,
    ),
    'SYS-06' => Sys06Screen(client: client),
    'SYS-07' => Sys07Screen(client: client),
    'SYS-08' => Sys08Screen(client: client),
    _ => throw StateError('Unmapped workspace Screen ID: $screenId'),
  };
}

class LumenisWorkspaceShell extends StatefulWidget {
  const LumenisWorkspaceShell({
    required this.client,
    required this.runtime,
    required this.subjects,
    this.contextEnvelope,
    this.subjectDirectoryMessage,
    this.initialScreenId = LumenisWorkspaceRoutes.rootScreenId,
    this.initialWorkspaceEntry,
    this.returnScreenId,
    this.initialArtifactId,
    this.onOpenSavedWork,
    this.onStartCreation,
    this.onScreenSelected,
    this.onLocaleChanged,
    this.onRetryRuntime,
    super.key,
  });

  final LumenisCoreClient client;
  final Map<String, dynamic> runtime;
  final List<Map<String, dynamic>> subjects;
  final Map<String, dynamic>? contextEnvelope;
  final String? subjectDirectoryMessage;
  final String initialScreenId;
  final String? initialWorkspaceEntry;
  final String? returnScreenId;
  final String? initialArtifactId;
  final void Function(String kind, String artifactId)? onOpenSavedWork;
  final ValueChanged<String>? onStartCreation;
  final ValueChanged<String>? onScreenSelected;
  final ValueChanged<Locale?>? onLocaleChanged;
  final VoidCallback? onRetryRuntime;

  @override
  State<LumenisWorkspaceShell> createState() => _LumenisWorkspaceShellState();
}

class _LumenisWorkspaceShellState extends State<LumenisWorkspaceShell>
    with RestorationMixin {
  final RestorableString _activeScreen = RestorableString(
    LumenisWorkspaceRoutes.rootScreenId,
  );
  final RestorableStringN _lastOpenedScreen = RestorableStringN(null);
  GlobalKey _screenHostKey = GlobalKey(debugLabel: 'workspace-screen-host');
  int _clientRevision = 0;
  DialogRoute<Map<String, dynamic>>? _contextPickerRoute;
  Map<String, dynamic>? _contextEnvelope;
  Map<String, dynamic>? _unavailableContextEnvelope;
  bool _hasConfirmedFocusRecoveryHint = false;
  final _localLeaveGuard = LumenisLeaveGuard();
  int _editorScopeRevision = 0;
  String? _localWorkspaceEntry;
  String? _localReturnScreenId;
  late TextEditingController _taskDraftController;
  final _scopeDrafts = <String, TextEditingController>{};
  String _taskDraftScope = 'GLOBAL_ALL::';
  bool _inspectorVisible = false;
  bool _navigationOpen = false;

  LumenisLeaveGuard get _leaveGuard =>
      LumenisLeaveScope.maybeOf(context) ?? _localLeaveGuard;

  @override
  void initState() {
    super.initState();
    _contextEnvelope =
        widget.contextEnvelope ?? widget.client.currentContextEnvelope;
    _taskDraftScope = _fingerprintFor(_contextEnvelope);
    _taskDraftController = _newTaskDraft(_taskDraftScope);
    _hasConfirmedFocusRecoveryHint = _isConfirmedFocusEnvelope(
      _contextEnvelope,
    );
  }

  @override
  void didUpdateWidget(covariant LumenisWorkspaceShell oldWidget) {
    super.didUpdateWidget(oldWidget);
    final clientChanged = oldWidget.client != widget.client;
    final previousContextFingerprint = _contextFingerprint;
    var contextChanged = clientChanged;

    if (clientChanged) {
      // Never carry mounted repositories or a recovery hint across clients.
      // Replace the host itself so the outgoing client's data is not animated.
      _clientRevision++;
      _screenHostKey = GlobalKey(debugLabel: 'workspace-screen-host');
      _dismissContextPicker();
      _contextEnvelope =
          widget.contextEnvelope ?? widget.client.currentContextEnvelope;
      _unavailableContextEnvelope = null;
      _hasConfirmedFocusRecoveryHint = _isConfirmedFocusEnvelope(
        _contextEnvelope,
      );
      _replaceTaskDraft(flush: false);
      _taskDraftScope = _fingerprintFor(_contextEnvelope);
    } else if (oldWidget.contextEnvelope != widget.contextEnvelope &&
        widget.contextEnvelope != null &&
        !identical(widget.contextEnvelope, _unavailableContextEnvelope)) {
      contextChanged |=
          _fingerprintFor(widget.contextEnvelope) != previousContextFingerprint;
      _contextEnvelope = widget.contextEnvelope;
      _unavailableContextEnvelope = null;
      _hasConfirmedFocusRecoveryHint = _isConfirmedFocusEnvelope(
        widget.contextEnvelope,
      );
    }

    _alignTaskDraftScope(_contextEnvelope);
    if (contextChanged) _lastOpenedScreen.value = null;
    if (oldWidget.initialScreenId != widget.initialScreenId &&
        LumenisWorkspaceRoutes.supportsWorkspaceScreen(
          widget.initialScreenId,
        ) &&
        _activeScreen.value != widget.initialScreenId) {
      final previousScreenId = _activeScreen.value;
      setState(() {
        if (!contextChanged &&
            previousScreenId != LumenisWorkspaceRoutes.rootScreenId &&
            LumenisWorkspaceRoutes.supportsWorkspaceScreen(previousScreenId)) {
          _lastOpenedScreen.value = previousScreenId;
        }
        _activeScreen.value = widget.initialScreenId;
      });
    }
  }

  static const _destinations = <_WorkspaceDestination>[
    _WorkspaceDestination(
      id: 'CTH-01',
      labelKey: 'navgroup.cth',
      mobileLabelKey: 'nav.mobile.commerce',
      groupKey: 'domain.cth',
      icon: Icons.timeline_rounded,
      color: LumenisTheme.cth,
    ),
    _WorkspaceDestination(
      id: 'BMP-01',
      labelKey: 'navgroup.bmp',
      mobileLabelKey: 'nav.mobile.brand',
      groupKey: 'domain.zbmp',
      icon: Icons.hub_outlined,
      color: LumenisTheme.bmp,
    ),
    _WorkspaceDestination(
      id: 'AI-01',
      labelKey: 'navgroup.ai',
      mobileLabelKey: 'nav.mobile.ai',
      groupKey: 'navgroup.ai',
      icon: Icons.auto_awesome_outlined,
      color: LumenisTheme.ai,
    ),
    _WorkspaceDestination(
      id: 'SH-01',
      labelKey: 'navgroup.shared',
      mobileLabelKey: 'nav.mobile.shared',
      groupKey: 'navgroup.shared',
      icon: Icons.edit_note_rounded,
      color: LumenisTheme.shared,
    ),
    _WorkspaceDestination(
      id: 'SYS-01',
      labelKey: 'navgroup.system',
      mobileLabelKey: 'nav.mobile.system',
      groupKey: 'navgroup.system',
      icon: Icons.monitor_heart_outlined,
      color: LumenisTheme.system,
    ),
  ];

  @override
  String get restorationId => 'workspace-shell';

  @override
  void restoreState(RestorationBucket? oldBucket, bool initialRestore) {
    registerForRestoration(_activeScreen, 'active-screen');
    registerForRestoration(_lastOpenedScreen, 'last-opened-screen');
    if (LumenisWorkspaceRoutes.supportsWorkspaceScreen(
      widget.initialScreenId,
    )) {
      _activeScreen.value = widget.initialScreenId;
    } else if (!LumenisWorkspaceRoutes.supportsWorkspaceScreen(
      _activeScreen.value,
    )) {
      _activeScreen.value = LumenisWorkspaceRoutes.rootScreenId;
    }
  }

  @override
  void dispose() {
    _dismissContextPicker();
    _activeScreen.dispose();
    _lastOpenedScreen.dispose();
    _localLeaveGuard.dispose();
    for (final draft in _scopeDrafts.values) {
      draft.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final layout = LumenisWorkspaceFrame(
      title: _isHome
          ? _shellCopy(context, zh: '开始工作', en: 'Start work', ko: '작업 시작')
          : context.lumenisL10n.text('screen.${_activeScreen.value}'),
      scope: _contextLabel(),
      destinations: _workDestinations(),
      onHome: _goHome,
      onSearch: _openNavigation,
      onScope: _openContextPicker,
      onTasks: () => _activateScreen('AI-02'),
      onNotifications: () => _activateScreen('SH-06'),
      onSettings: () => _activateScreen('SYS-05'),
      onTools: _openPhoneTools,
      tools: [
        if (_activeScreen.value == 'CTH-02')
          IconButton(
            tooltip: context.lumenisL10n.text('shell.return_to_overview'),
            onPressed: _returnFromCth02,
            icon: const LumenisIcon(Icons.arrow_back, size: 20),
          ),
        if (widget.onLocaleChanged != null)
          _LocaleSwitcher(onLocaleChanged: widget.onLocaleChanged!),
        const Sys05AppearanceButton(),
        if (!_isHome)
          IconButton(
            tooltip: _shellCopy(
              context,
              zh: '工作详情',
              en: 'Work details',
              ko: '작업 세부 정보',
            ),
            onPressed: _toggleWorkDetails,
            icon: LumenisIcon(
              _inspectorVisible ? Icons.close : Icons.info_outline,
              size: 20,
            ),
          ),
      ],
      inspector: _inspectorVisible && !_isHome && _activeScreen.value != 'AI-01'
          ? _ContextInspector(
              destination: _selectedDestination,
              contextLabel: _contextLabel(),
              selectionContext: _contextMap,
              contextUnavailable: _contextEnvelope == null,
            )
          : null,
      child: _screenTransition(),
    );
    final guarded = LumenisLeaveScope.maybeOf(context) == null
        ? LumenisLeaveScope(guard: _localLeaveGuard, child: layout)
        : layout;
    return CallbackShortcuts(
      bindings: {
        const SingleActivator(LogicalKeyboardKey.keyK, control: true):
            _openNavigation,
        const SingleActivator(LogicalKeyboardKey.keyK, meta: true):
            _openNavigation,
      },
      child: guarded,
    );
  }

  bool get _isHome =>
      _activeScreen.value == LumenisWorkspaceRoutes.rootScreenId;

  String get _activeGroup =>
      LumenisWorkspaceRoutes.groupForScreen(_activeScreen.value);

  int get _selectedIndex =>
      _destinations.indexWhere((item) => item.id.startsWith('$_activeGroup-'));

  // Account screens remain addressable for legacy deep links, but are not a
  // product destination in the open workspace. A restored account route
  // therefore falls back to the first business destination for shell chrome.
  _WorkspaceDestination get _selectedDestination =>
      _destinations[_selectedIndex < 0 ? 0 : _selectedIndex];

  Future<void> _activateScreen(
    String screenId, {
    bool notifyRoute = true,
  }) async {
    if (!LumenisWorkspaceRoutes.supportsScreen(screenId)) {
      return;
    }
    if (LumenisWorkspaceRoutes.focusedReturnScreenIds.contains(screenId)) {
      // A controlled reader is a push-only focus layer.  Its origin remains
      // mounted beneath it, so draft protection stays with that origin and no
      // local screen replacement or destructive leave may occur here.
      if (notifyRoute) widget.onScreenSelected?.call(screenId);
      return;
    }
    if (LumenisWorkspaceRoutes.unavailableScreenIds.contains(screenId)) {
      if (notifyRoute) widget.onScreenSelected?.call(screenId);
      return;
    }
    if (_activeScreen.value == screenId) return;
    if (notifyRoute &&
        widget.onScreenSelected != null &&
        _leaveGuard.routeDriven) {
      // The router owns acceptance and then updates initialScreenId. Selecting
      // locally first would discard the editor before onEnter can protect it.
      widget.onScreenSelected!(screenId);
      return;
    }
    if (!await _leaveGuard.requestLeave() || !mounted) return;
    final previousScreenId = _activeScreen.value;
    final currentEnvelope = widget.client.currentContextEnvelope;
    final shouldAdoptCurrentEnvelope =
        currentEnvelope != null &&
        !identical(currentEnvelope, _unavailableContextEnvelope);
    final contextChanged =
        shouldAdoptCurrentEnvelope &&
        _fingerprintFor(currentEnvelope) != _contextFingerprint;
    setState(() {
      if (previousScreenId == 'BMP-08' && screenId == 'SH-01') {
        _localWorkspaceEntry = 'media';
        _localReturnScreenId = 'BMP-08';
      } else {
        _localWorkspaceEntry = null;
        _localReturnScreenId = null;
      }
      if (shouldAdoptCurrentEnvelope) {
        _alignTaskDraftScope(currentEnvelope);
        _contextEnvelope = currentEnvelope;
        _unavailableContextEnvelope = null;
        _hasConfirmedFocusRecoveryHint = _isConfirmedFocusEnvelope(
          currentEnvelope,
        );
      }
      if (contextChanged) {
        _lastOpenedScreen.value = null;
      } else if (previousScreenId != LumenisWorkspaceRoutes.rootScreenId &&
          LumenisWorkspaceRoutes.supportsWorkspaceScreen(previousScreenId)) {
        _lastOpenedScreen.value = previousScreenId;
      }
      _activeScreen.value = screenId;
    });
    if (notifyRoute) widget.onScreenSelected?.call(screenId);
  }

  Widget _screen() {
    final isSharedMediaEntry =
        _activeScreen.value == 'SH-01' &&
        ((widget.initialWorkspaceEntry == 'media' &&
                widget.returnScreenId == 'BMP-08') ||
            (_localWorkspaceEntry == 'media' &&
                _localReturnScreenId == 'BMP-08'));
    return buildLumenisWorkspaceScreen(
      screenId: _activeScreen.value,
      client: widget.client,
      contextAvailable: _contextEnvelope != null,
      onNavigate: _activateScreen,
      lastOpenedScreenId: _lastOpenedScreen.value,
      workspaceEntry:
          widget.initialWorkspaceEntry != null &&
              _activeScreen.value == widget.initialScreenId
          ? widget.initialWorkspaceEntry
          : isSharedMediaEntry
          ? 'media'
          : null,
      initialArtifactId: _activeScreen.value == widget.initialScreenId
          ? widget.initialArtifactId
          : null,
      onOpenSavedWork: widget.onOpenSavedWork,
      onStartCreation: widget.onStartCreation,
      returnScreenId:
          widget.initialArtifactId != null &&
              _activeScreen.value == widget.initialScreenId
          ? widget.returnScreenId
          : isSharedMediaEntry
          ? widget.returnScreenId ?? _localReturnScreenId
          : null,
      taskDraftController: _taskDraftController,
      taskScopeLabel: _contextLabel(),
    );
  }

  Widget _screenTransition() {
    final reduceMotion =
        MediaQuery.maybeOf(context)?.disableAnimations ?? false;
    final duration = reduceMotion ? Duration.zero : LumenisMotion.panel;

    return AnimatedSwitcher(
      key: _screenHostKey,
      duration: duration,
      reverseDuration: duration,
      switchInCurve: Curves.easeOutCubic,
      switchOutCurve: Curves.easeInCubic,
      transitionBuilder: (child, animation) {
        final position = animation.drive(
          Tween<Offset>(
            begin: reduceMotion ? Offset.zero : const Offset(0.012, 0),
            end: Offset.zero,
          ).chain(CurveTween(curve: Curves.easeOutCubic)),
        );
        return FadeTransition(
          opacity: animation,
          child: SlideTransition(position: position, child: child),
        );
      },
      child: KeyedSubtree(
        key: ValueKey(
          '${_activeScreen.value}:${widget.initialArtifactId ?? ''}:${_activeScreen.value == 'SH-01' ? _editorScopeRevision : _contextFingerprint}:${_activeScreen.value == 'SH-01' ? widget.initialWorkspaceEntry ?? _localWorkspaceEntry : null}:${_activeScreen.value == 'SH-01' ? widget.returnScreenId ?? _localReturnScreenId : null}',
        ),
        child: _screen(),
      ),
    );
  }

  Future<void> _openNavigation() async {
    if (_navigationOpen) return;
    _navigationOpen = true;
    final reduceMotion =
        MediaQuery.maybeOf(context)?.disableAnimations ?? false;
    String? selected;
    try {
      selected = await showDialog<String>(
        context: context,
        animationStyle: reduceMotion
            ? AnimationStyle.noAnimation
            : const AnimationStyle(
                duration: LumenisMotion.panel,
                reverseDuration: LumenisMotion.exit,
                curve: Curves.easeOutCubic,
                reverseCurve: Curves.easeOutCubic,
              ),
        builder: (dialogContext) => CallbackShortcuts(
          bindings: {
            const SingleActivator(LogicalKeyboardKey.escape): () =>
                Navigator.of(dialogContext).pop(),
          },
          child: _WorkspaceNavigationDialog(
            destinations: _destinations,
            activeScreenId: _activeScreen.value,
          ),
        ),
      );
    } finally {
      _navigationOpen = false;
    }
    if (mounted && selected != null) _activateScreen(selected);
  }

  Future<void> _openPhoneTools() async {
    final copy = context.lumenisL10n;
    final selection = await showModalBottomSheet<String>(
      context: context,
      showDragHandle: true,
      constraints: const BoxConstraints(maxWidth: 620),
      builder: (sheetContext) => SafeArea(
        child: _PhoneSheet(
          title: copy.text('shell.workspace'),
          child: SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(20, 0, 20, 24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              mainAxisSize: MainAxisSize.min,
              children: [
                Padding(
                  padding: const EdgeInsets.only(top: 8, bottom: 16),
                  child: Text(
                    _coreLabel,
                    style: Theme.of(sheetContext).textTheme.bodySmall,
                  ),
                ),
                if (widget.onRetryRuntime != null)
                  TextButton.icon(
                    key: const ValueKey('workspace-runtime-retry'),
                    onPressed: () => Navigator.of(sheetContext).pop('retry'),
                    icon: const LumenisIcon(Icons.refresh, size: 18),
                    label: Text(copy.text('launch.retry')),
                  ),
                if (_activeGroup == 'CTH')
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: const LumenisIcon(Icons.account_tree_outlined),
                    title: Text(copy.text('shell.open_subject_directory')),
                    onTap: () => Navigator.of(sheetContext).pop('directory'),
                  ),
                if (widget.onLocaleChanged != null) ...[
                  const Divider(height: 24),
                  Text(
                    copy.text('shell.locale.tooltip'),
                    style: Theme.of(sheetContext).textTheme.labelLarge,
                  ),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 8,
                    children: [
                      for (final locale in const [
                        'system',
                        'zh-CN',
                        'en',
                        'ko',
                      ])
                        TextButton(
                          onPressed: () =>
                              Navigator.of(sheetContext).pop(locale),
                          child: Text(copy.text('locale.$locale')),
                        ),
                    ],
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
    if (!mounted || selection == null) return;
    switch (selection) {
      case 'retry':
        widget.onRetryRuntime?.call();
      case 'directory':
        _openCth02();
      default:
        widget.onLocaleChanged?.call(switch (selection) {
          'zh-CN' => const Locale('zh', 'CN'),
          'en' => const Locale('en'),
          'ko' => const Locale('ko'),
          _ => null,
        });
    }
  }

  void _toggleWorkDetails() {
    if (MediaQuery.sizeOf(context).width >= 1500) {
      setState(() => _inspectorVisible = !_inspectorVisible);
      return;
    }
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (context) => SafeArea(
        child: SizedBox(
          height: MediaQuery.sizeOf(context).height * .7,
          child: _ContextInspector(
            destination: _selectedDestination,
            contextLabel: _contextLabel(),
            selectionContext: _contextMap,
            contextUnavailable: _contextEnvelope == null,
          ),
        ),
      ),
    );
  }

  List<LumenisWorkDestination> _workDestinations() {
    final entries = <LumenisWorkDestination>[];
    for (final (id, icon, zh, en, ko, separate) in const [
      (
        'ACC-03',
        Icons.chat_bubble_outline,
        '开始工作',
        'Start work',
        '작업 시작',
        false,
      ),
      ('CTH-01', Icons.timeline, '商业运营', 'Commerce', '커머스 운영', true),
      (
        'BMP-01',
        Icons.hub_outlined,
        '品牌与市场',
        'Brand & market',
        '브랜드와 시장',
        false,
      ),
      (
        'SH-02',
        Icons.auto_stories_outlined,
        '研究与资料',
        'Research',
        '리서치와 자료',
        true,
      ),
      ('SH-01', Icons.edit_note, '创作与作品', 'Studio', '창작 스튜디오', false),
      ('SYS-06', Icons.language, '浏览器', 'Browser', '브라우저', true),
      ('AI-02', Icons.checklist, '任务', 'Tasks', '작업', false),
      ('SH-06', Icons.notifications_none, '通知', 'Notifications', '알림', false),
    ]) {
      entries.add(
        LumenisWorkDestination(
          id: id,
          label: _shellCopy(context, zh: zh, en: en, ko: ko),
          icon: icon,
          selected:
              _activeScreen.value == id ||
              (id == 'CTH-01' && _activeGroup == 'CTH') ||
              (id == 'BMP-01' && _activeGroup == 'BMP'),
          separate: separate,
          onOpen: () => _activateScreen(id),
        ),
      );
      if (id == 'SH-01' && widget.onStartCreation != null) {
        for (final (kind, icon, zh, en, ko) in const [
          ('manuscript', Icons.notes, '文稿与提案', 'Writing & proposals', '글과 제안서'),
          ('video', Icons.movie_outlined, '视频', 'Video', '영상'),
          ('audio', Icons.graphic_eq, '播客', 'Podcast', '팟캐스트'),
        ]) {
          entries.add(
            LumenisWorkDestination(
              id: 'create-$kind',
              label: _shellCopy(context, zh: zh, en: en, ko: ko),
              icon: icon,
              selected:
                  _activeScreen.value == 'SH-01' &&
                  widget.initialWorkspaceEntry == kind,
              nested: true,
              onOpen: () => widget.onStartCreation!(kind),
            ),
          );
        }
      }
    }
    return entries;
  }

  String get _coreLabel =>
      context.lumenisL10n.text(switch (widget.runtime['state']) {
        'LOADING' => 'shell.connecting',
        'OFFLINE' => 'shell.offline',
        'AUTH_REQUIRED' => 'shell.auth_unavailable',
        'ACCESS_UNAVAILABLE' => 'shell.restricted',
        'ERROR' => 'shell.error',
        'DEGRADED' => 'shell.degraded',
        'UNKNOWN' => 'shell.pending',
        _ => widget.runtime['ok'] == true ? 'shell.connected' : 'shell.pending',
      });

  Map<String, dynamic>? get _contextMap {
    final value = _contextEnvelope?['context'];
    if (value is Map<String, dynamic>) return value;
    if (value is Map) return value.map((key, value) => MapEntry('$key', value));
    return null;
  }

  String get _contextFingerprint => _fingerprintFor(_contextEnvelope);

  // A task draft belongs to the current window and scope. Page navigation
  // preserves it; a confirmed scope change starts a separate task. Temporary
  // scope-read errors must not destroy local writing.
  void _alignTaskDraftScope(Map<String, dynamic>? envelope) {
    final selection = envelope?['context'];
    if (selection is! Map ||
        (selection['mode'] != 'GLOBAL_ALL' && selection['mode'] != 'FOCUS')) {
      return;
    }
    final next = _fingerprintFor(envelope);
    if (next != _taskDraftScope) {
      // A pending file chooser or outgoing editor must never write into the
      // new scope. Replace both the controller and its mounted host together.
      _replaceTaskDraft(scope: next);
      _screenHostKey = GlobalKey(debugLabel: 'workspace-screen-host');
    }
    _taskDraftScope = next;
  }

  void _replaceTaskDraft({String? scope, bool flush = true}) {
    final previous = _taskDraftController;
    final retired = flush
        ? <TextEditingController>[]
        : _scopeDrafts.values.toList();
    if (!flush) _scopeDrafts.clear();
    _taskDraftController = _newTaskDraft(
      scope ?? _fingerprintFor(_contextEnvelope),
    );
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (flush && previous is Ai01WorkspaceDraft) {
        unawaited(previous.flush());
      }
      for (final draft in retired) {
        draft.dispose();
      }
    });
  }

  TextEditingController _newTaskDraft(String scope) => _scopeDrafts.putIfAbsent(
    scope,
    () => scope == 'GLOBAL_ALL::' || scope.startsWith('FOCUS:')
        ? Ai01WorkspaceDraft(widget.client, scope)
        : TextEditingController(),
  );

  String _fingerprintFor(Map<String, dynamic>? envelope) {
    final raw = envelope?['context'];
    final selection = raw is Map
        ? raw.map((key, value) => MapEntry('$key', value))
        : null;
    final focusId = selection?['domain_id'] == 'BMP'
        ? (selection?['brand_focus_id'] ?? selection?['subject_id'])
        : selection?['subject_id'];
    return "${selection?['mode'] ?? 'unknown'}:"
        "${selection?['domain_id'] ?? ''}:"
        "${focusId ?? ''}";
  }

  String _contextLabel() {
    final copy = context.lumenisL10n;
    if (_activeScreen.value == 'CTH-02') {
      return copy.text('shell.cth.directory_context');
    }
    final selection = _contextMap;
    if (selection == null) return copy.text('shell.context.unavailable');
    if (selection['mode'] == 'GLOBAL_ALL') {
      return copy.text('context.mode.global_all');
    }
    if (selection['mode'] != 'FOCUS') {
      return copy.text('shell.context.unavailable');
    }
    final displayName = _localizedDisplayName(selection['display_name']);
    if (displayName != null) return displayName;
    return copy.text('context.selector.unnamed_subject');
  }

  String? _localizedDisplayName(Object? value) {
    if (value is! Map) return null;
    final locale = Localizations.localeOf(context);
    final name =
        value[locale.toLanguageTag()] ??
        value[locale.languageCode] ??
        value['en'] ??
        value['zh-CN'];
    return name is String && name.trim().isNotEmpty ? name.trim() : null;
  }

  Future<void> _openContextPicker() async {
    if (_contextPickerRoute != null) return;
    final client = widget.client;
    final revision = _clientRevision;
    bool isCurrentClient() =>
        mounted &&
        revision == _clientRevision &&
        identical(client, widget.client);
    final canReturnToGlobal = _hasConfirmedFocusRecoveryHint;
    final navigator = Navigator.of(context, rootNavigator: true);
    final route = DialogRoute<Map<String, dynamic>>(
      context: context,
      themes: InheritedTheme.capture(from: context, to: navigator.context),
      barrierDismissible: false,
      traversalEdgeBehavior: TraversalEdgeBehavior.closedLoop,
      builder: (_) => _ContextPickerDialog(
        client: client,
        canReturnToGlobal: canReturnToGlobal,
        onContextConfirmed: (envelope) {
          if (isCurrentClient()) _acceptContextEnvelope(envelope);
        },
        beforeContextChange: () async {
          if (!isCurrentClient()) return false;
          final allowed = await _leaveGuard.requestLeave();
          return allowed && isCurrentClient();
        },
        onContextChanged: (envelope) {
          if (isCurrentClient()) {
            _acceptContextEnvelope(envelope, resetEditor: true);
          }
        },
        onContextUnavailable: () {
          if (isCurrentClient()) _markContextUnavailable();
        },
      ),
    );
    _contextPickerRoute = route;
    try {
      final selected = await navigator.push(route);
      if (selected != null && isCurrentClient()) {
        _acceptContextEnvelope(selected);
      }
    } finally {
      if (identical(_contextPickerRoute, route)) _contextPickerRoute = null;
    }
  }

  void _dismissContextPicker() {
    final route = _contextPickerRoute;
    _contextPickerRoute = null;
    if (route == null) return;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final navigator = route.navigator;
      if (navigator != null && navigator.mounted && route.isActive) {
        navigator.removeRoute(route);
      }
    });
  }

  bool _isConfirmedFocusEnvelope(Map<String, dynamic>? envelope) {
    final selection = envelope?['context'];
    if (selection is! Map) return false;
    final subjectId = selection['subject_id'];
    return envelope?['ok'] == true &&
        envelope?['contract'] == 'lumenis.context.v1' &&
        envelope?['selection_only'] == true &&
        selection['mode'] == 'FOCUS' &&
        (selection['domain_id'] == 'CTH' || selection['domain_id'] == 'BMP') &&
        subjectId is String &&
        subjectId.trim().isNotEmpty;
  }

  void _acceptContextEnvelope(
    Map<String, dynamic> envelope, {
    bool resetEditor = false,
  }) {
    if (!mounted) return;
    _alignTaskDraftScope(envelope);
    if (_fingerprintFor(envelope) != _contextFingerprint) {
      _lastOpenedScreen.value = null;
    }
    setState(() {
      if (resetEditor) _editorScopeRevision++;
      _contextEnvelope = envelope;
      _unavailableContextEnvelope = null;
      _hasConfirmedFocusRecoveryHint = _isConfirmedFocusEnvelope(envelope);
    });
  }

  void _markContextUnavailable() {
    if (!mounted) return;
    _lastOpenedScreen.value = null;
    setState(() {
      _unavailableContextEnvelope ??=
          _contextEnvelope ?? widget.client.currentContextEnvelope;
      _contextEnvelope = null;
    });
  }

  void _goHome() => _activateScreen(LumenisWorkspaceRoutes.rootScreenId);

  void _openCth02() => _activateScreen('CTH-02');

  void _returnFromCth02() => _activateScreen('CTH-01');
}

class _NavigationTree extends StatelessWidget {
  const _NavigationTree({
    required this.activeScreenId,
    required this.onSelected,
  });

  final String activeScreenId;
  final ValueChanged<String> onSelected;

  @override
  Widget build(BuildContext context) => Padding(
    key: ValueKey('workspace-secondary-${activeScreenId.split('-').first}'),
    padding: const EdgeInsets.only(left: 14, bottom: 14),
    child: Column(
      children: [
        for (final workflow
            in LumenisWorkspaceRoutes
                .workflowsByGroup[LumenisWorkspaceRoutes.groupForScreen(
                  activeScreenId,
                )]!
                .entries)
          ExpansionTile(
            trailing: const LumenisExpansionIndicator(),
            key: ValueKey('workflow-group-${workflow.key}'),
            initiallyExpanded: workflow.value.contains(activeScreenId),
            tilePadding: const EdgeInsets.symmetric(horizontal: 8),
            childrenPadding: EdgeInsets.zero,
            shape: const Border(),
            collapsedShape: const Border(),
            dense: true,
            title: Text(
              context.lumenisL10n.text(workflow.key),
              style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
            ),
            children: [
              for (final screenId in workflow.value)
                Semantics(
                  selected: screenId == activeScreenId,
                  button: true,
                  child: Material(
                    color: screenId == activeScreenId
                        ? LumenisTheme.of(context).surfaceRaised
                        : Colors.transparent,
                    shape: const LumenisPixelBorder(step: 2),
                    child: InkWell(
                      key: ValueKey('workspace-nav-$screenId'),
                      onTap: () => onSelected(screenId),
                      customBorder: const LumenisPixelBorder(step: 2),
                      child: ConstrainedBox(
                        constraints: const BoxConstraints(
                          minHeight: LumenisSpace.touchTarget,
                        ),
                        child: Padding(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 14,
                            vertical: 9,
                          ),
                          child: Row(
                            children: [
                              LumenisIcon(
                                LumenisWorkspaceRoutes.unavailableScreenIds
                                        .contains(screenId)
                                    ? Icons.info_outline_rounded
                                    : Icons.description_outlined,
                                size: 16,
                                color: LumenisTheme.of(context).quiet,
                              ),
                              const SizedBox(width: 10),
                              Expanded(
                                child: Text(
                                  context.lumenisL10n.text('screen.$screenId'),
                                  style: TextStyle(
                                    color: screenId == activeScreenId
                                        ? LumenisTheme.of(context).foreground
                                        : LumenisTheme.of(context).muted,
                                    fontSize: 13,
                                    fontWeight: screenId == activeScreenId
                                        ? FontWeight.w600
                                        : FontWeight.w400,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
            ],
          ),
      ],
    ),
  );
}

class _WideDestinationRow extends StatelessWidget {
  const _WideDestinationRow({
    super.key,
    required this.destination,
    required this.selected,
    required this.onTap,
  });

  final _WorkspaceDestination destination;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    final foreground = selected
        ? LumenisTheme.of(context).foreground
        : LumenisTheme.of(context).muted;
    return Padding(
      padding: const EdgeInsets.only(bottom: 5),
      child: Material(
        color: selected
            ? LumenisTheme.of(context).surfaceRaised
            : Colors.transparent,
        shape: const LumenisPixelBorder(step: 2),
        child: InkWell(
          onTap: onTap,
          customBorder: const LumenisPixelBorder(step: 2),
          child: Semantics(
            button: true,
            selected: selected,
            label:
                '${copy.text(destination.labelKey)}，${copy.text(destination.groupKey)}',
            child: ConstrainedBox(
              constraints: const BoxConstraints(minHeight: 48),
              child: Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: 12,
                  vertical: 12,
                ),
                child: Row(
                  children: [
                    LumenisDomainGlyph(
                      domain: destination.id,
                      fallback: destination.icon,
                      color: foreground,
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        copy.text(destination.labelKey),
                        style: TextStyle(
                          color: selected
                              ? LumenisTheme.of(context).foreground
                              : foreground,
                          fontSize: 14,
                          fontWeight: selected
                              ? FontWeight.w600
                              : FontWeight.w500,
                        ),
                      ),
                    ),
                    if (selected)
                      Container(
                        width: 5,
                        height: 5,
                        decoration: BoxDecoration(
                          color: LumenisTheme.of(
                            context,
                          ).resolveSemantic(destination.color),
                          shape: BoxShape.circle,
                        ),
                      ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _WorkspaceNavigationDialog extends StatefulWidget {
  const _WorkspaceNavigationDialog({
    required this.destinations,
    required this.activeScreenId,
  });

  final List<_WorkspaceDestination> destinations;
  final String activeScreenId;

  @override
  State<_WorkspaceNavigationDialog> createState() =>
      _WorkspaceNavigationDialogState();
}

class _WorkspaceNavigationDialogState
    extends State<_WorkspaceNavigationDialog> {
  final _search = TextEditingController();
  final _resultKeys = <String, GlobalKey>{};
  int _highlighted = 0;

  void _moveResult(int step, List<String> matches) {
    if (matches.isEmpty) return;
    setState(() => _highlighted = (_highlighted + step) % matches.length);
    final targetId = matches[_highlighted];
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      final target = _resultKeys[targetId]?.currentContext;
      if (target != null) {
        Scrollable.ensureVisible(
          target,
          duration: LumenisMotion.of(context, LumenisMotion.feedback),
          alignment: .5,
        );
      }
    });
  }

  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }

  late String _previewGroup = LumenisWorkspaceRoutes.groupForScreen(
    widget.activeScreenId,
  );

  String get _previewScreenId {
    final activeGroup = LumenisWorkspaceRoutes.groupForScreen(
      widget.activeScreenId,
    );
    if (_previewGroup == activeGroup) return widget.activeScreenId;
    return LumenisWorkspaceRoutes.screenIdsByGroup[_previewGroup]!.first;
  }

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    final theme = LumenisTheme.of(context);
    final query = _search.text.trim().toLowerCase();
    final matches =
        LumenisWorkspaceRoutes.workspaceScreenIds.where((id) {
          final title = copy.text('screen.$id').toLowerCase();
          final group = LumenisWorkspaceRoutes.groupForScreen(id);
          final destination = widget.destinations
              .where((entry) => entry.id.startsWith('$group-'))
              .firstOrNull;
          final groupName = destination == null
              ? ''
              : copy.text(destination.labelKey).toLowerCase();
          return title.contains(query) || groupName.contains(query);
        }).toList()..sort((a, b) {
          int rank(String id) {
            final title = copy.text('screen.$id').toLowerCase();
            if (title == query) return 0;
            if (title.startsWith(query)) return 1;
            if (title.contains(query)) return 2;
            return 3;
          }

          final priority = rank(a).compareTo(rank(b));
          return priority != 0 ? priority : a.compareTo(b);
        });

    return CallbackShortcuts(
      bindings: query.isEmpty
          ? const {}
          : {
              const SingleActivator(LogicalKeyboardKey.arrowDown): () =>
                  _moveResult(1, matches),
              const SingleActivator(LogicalKeyboardKey.arrowUp): () =>
                  _moveResult(-1, matches),
            },
      child: Dialog(
        key: const ValueKey('workspace-navigation-dialog'),
        backgroundColor: theme.surface.withValues(alpha: 1),
        surfaceTintColor: Colors.transparent,
        insetPadding: const EdgeInsets.all(20),
        child: ConstrainedBox(
          constraints: BoxConstraints(
            maxWidth: 600,
            maxHeight: MediaQuery.sizeOf(context).height * 0.86,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 10, 8, 10),
                child: Row(
                  children: [
                    const Expanded(child: _LumenisMark()),
                    IconButton(
                      key: const ValueKey('workspace-navigation-close'),
                      tooltip: copy.text('common.close'),
                      onPressed: () => Navigator.of(context).pop(),
                      icon: const LumenisIcon(Icons.close_rounded),
                    ),
                  ],
                ),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 0, 20, 18),
                child: TextField(
                  key: const ValueKey('workspace-navigation-search'),
                  controller: _search,
                  autofocus: true,
                  onChanged: (_) => setState(() => _highlighted = 0),
                  onSubmitted: (_) {
                    if (query.isNotEmpty && matches.isNotEmpty) {
                      Navigator.of(
                        context,
                      ).pop(matches[_highlighted.clamp(0, matches.length - 1)]);
                    }
                  },
                  decoration: InputDecoration(
                    hintText: _shellCopy(
                      context,
                      zh: '查找工作',
                      en: 'Find a workspace',
                      ko: '작업 찾기',
                    ),
                    prefixIcon: const LumenisIcon(Icons.search_rounded),
                    suffixIcon: query.isEmpty
                        ? null
                        : IconButton(
                            tooltip: _shellCopy(
                              context,
                              zh: '清除',
                              en: 'Clear',
                              ko: '지우기',
                            ),
                            onPressed: () => setState(() {
                              _search.clear();
                              _highlighted = 0;
                            }),
                            icon: const LumenisIcon(Icons.close_rounded),
                          ),
                  ),
                ),
              ),
              Divider(height: 1, color: theme.line),
              Flexible(
                child: query.isNotEmpty
                    ? matches.isEmpty
                          ? Padding(
                              padding: const EdgeInsets.all(28),
                              child: Text(
                                _shellCopy(
                                  context,
                                  zh: '没有匹配的工作',
                                  en: 'No matching workspace',
                                  ko: '일치하는 작업 없음',
                                ),
                              ),
                            )
                          : ListView(
                              shrinkWrap: true,
                              padding: const EdgeInsets.all(8),
                              children: [
                                for (final (index, id) in matches.indexed)
                                  KeyedSubtree(
                                    key: _resultKeys.putIfAbsent(
                                      id,
                                      GlobalKey.new,
                                    ),
                                    child: ListTile(
                                      key: ValueKey('workspace-search-$id'),
                                      selected: index == _highlighted,
                                      title: Text(copy.text('screen.$id')),
                                      trailing: const LumenisIcon(
                                        Icons.north_east_rounded,
                                      ),
                                      onTap: () =>
                                          Navigator.of(context).pop(id),
                                    ),
                                  ),
                              ],
                            )
                    : SingleChildScrollView(
                        key: const ValueKey('workspace-navigation-list'),
                        child: Padding(
                          padding: const EdgeInsets.fromLTRB(12, 12, 12, 20),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              for (final destination
                                  in widget.destinations) ...[
                                _domainRow(destination),
                                if (_previewGroup ==
                                    destination.id.split('-').first)
                                  _navigationTree(),
                              ],
                            ],
                          ),
                        ),
                      ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _domainRow(_WorkspaceDestination destination) {
    final group = destination.id.split('-').first;
    return _WideDestinationRow(
      key: ValueKey('workspace-domain-$group'),
      destination: destination,
      selected: _previewGroup == group,
      onTap: () => setState(() => _previewGroup = group),
    );
  }

  Widget _navigationTree() => _NavigationTree(
    activeScreenId: _previewScreenId,
    onSelected: (screenId) => Navigator.of(context).pop(screenId),
  );
}

class _PhoneSheet extends StatelessWidget {
  const _PhoneSheet({required this.title, required this.child});

  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) => Column(
    mainAxisSize: MainAxisSize.min,
    children: [
      Padding(
        padding: const EdgeInsets.only(left: 20, right: 8, bottom: 8),
        child: Row(
          children: [
            Expanded(
              child: Text(title, style: Theme.of(context).textTheme.titleLarge),
            ),
            IconButton(
              key: const ValueKey('workspace-sheet-close'),
              tooltip: MaterialLocalizations.of(context).closeButtonTooltip,
              onPressed: () => Navigator.of(context).pop(),
              icon: const LumenisIcon(Icons.close_rounded),
            ),
          ],
        ),
      ),
      Flexible(child: child),
    ],
  );
}

class _ContextInspector extends StatelessWidget {
  const _ContextInspector({
    required this.destination,
    required this.contextLabel,
    required this.selectionContext,
    required this.contextUnavailable,
  });

  final _WorkspaceDestination destination;
  final String contextLabel;
  final Map<String, dynamic>? selectionContext;
  final bool contextUnavailable;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    final domainKey = switch (selectionContext?['domain_id']) {
      'CTH' => 'domain.cth',
      'BMP' => 'domain.zbmp',
      _ => null,
    };
    final scopeText = contextUnavailable
        ? copy.text('shell.context.unavailable')
        : selectionContext?['mode'] == 'GLOBAL_ALL'
        ? copy.text('context.mode.global_all')
        : domainKey == null
        ? copy.text('context.selector.unnamed_subject')
        : copy.text(domainKey);

    return SizedBox(
      key: const ValueKey('workspace-context-inspector'),
      width: 258,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(20, 28, 20, 24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _SectionLabel(copy.text('shell.current_object')),
            const SizedBox(height: 16),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(16),
              decoration: ShapeDecoration(
                color: LumenisTheme.of(context).surface,
                shape: LumenisPixelBorder(
                  side: BorderSide(color: LumenisTheme.of(context).line),
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  LumenisIcon(
                    destination.icon,
                    color: LumenisTheme.of(
                      context,
                    ).resolveSemantic(destination.color),
                    size: 18,
                  ),
                  const SizedBox(height: 14),
                  Text(contextLabel, style: const TextStyle(height: 1.4)),
                  const SizedBox(height: 8),
                  Text(
                    scopeText,
                    style: TextStyle(
                      color: LumenisTheme.of(context).muted,
                      fontSize: 12,
                    ),
                  ),
                ],
              ),
            ),
            const Spacer(),
            Text(
              copy.text('shell.context_rule'),
              style: TextStyle(
                color: LumenisTheme.of(context).quiet,
                fontSize: 12,
                height: 1.6,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ContextPickerDialog extends StatefulWidget {
  const _ContextPickerDialog({
    required this.client,
    required this.canReturnToGlobal,
    required this.onContextConfirmed,
    required this.beforeContextChange,
    required this.onContextChanged,
    required this.onContextUnavailable,
  });

  final LumenisCoreClient client;
  final bool canReturnToGlobal;
  final ValueChanged<Map<String, dynamic>> onContextConfirmed;
  final Future<bool> Function() beforeContextChange;
  final ValueChanged<Map<String, dynamic>> onContextChanged;
  final VoidCallback onContextUnavailable;

  @override
  State<_ContextPickerDialog> createState() => _ContextPickerDialogState();
}

class _ContextPickerDialogState extends State<_ContextPickerDialog> {
  Map<String, dynamic>? _envelope;
  List<Map<String, dynamic>> _domains = const [];
  List<Map<String, dynamic>> _subjects = const [];
  String? _domainId;
  String? _messageKey;
  String _query = '';
  bool _loadingContext = true;
  bool _loadingSubjects = false;
  bool _selecting = false;
  bool _contextRequestInFlight = false;

  @override
  void initState() {
    super.initState();
    _refreshContext();
  }

  Future<void> _refreshContext() async {
    if (_contextRequestInFlight || _selecting) return;
    _contextRequestInFlight = true;
    if (mounted) {
      setState(() {
        _loadingContext = true;
        _messageKey = null;
        _envelope = null;
        _domains = const [];
        _subjects = const [];
        _domainId = null;
        _query = '';
      });
    }
    try {
      final envelope = await widget.client.settingsContext();
      if (!mounted) return;
      widget.onContextConfirmed(envelope);
      final domains = _readDomains(envelope['authorized_domains']);
      final contextValue = _asMap(envelope['context']);
      final currentDomain = contextValue?['domain_id'];
      final nextDomain = domains.any((item) => item['id'] == currentDomain)
          ? currentDomain as String
          : domains.isEmpty
          ? null
          : domains.first['id'] as String;
      setState(() {
        _envelope = envelope;
        _domains = domains;
        _domainId = nextDomain;
        _loadingContext = false;
        _contextRequestInFlight = false;
        _messageKey = null;
      });
      if (nextDomain != null) await _loadSubjects(nextDomain);
    } on Object catch (error) {
      if (!mounted) return;
      widget.onContextUnavailable();
      setState(() {
        _loadingContext = false;
        _contextRequestInFlight = false;
        _messageKey = _errorMessageKey(error, forDirectory: false);
      });
    }
  }

  Future<void> _loadSubjects(String domainId) async {
    setState(() {
      _domainId = domainId;
      _subjects = const [];
      _loadingSubjects = true;
      _messageKey = null;
    });
    try {
      final response = await widget.client.settingsSubjects(domainId: domainId);
      final domains = _readDomains(response['domains']);
      if (response['ok'] != true ||
          response['source'] != 'lumenis_subject_registry' ||
          response['selection_only'] != true ||
          !domains.any((item) => item['id'] == domainId)) {
        throw const FormatException('Invalid subject directory response.');
      }
      final rawSubjects = response['subjects'];
      if (rawSubjects is! List) {
        throw const FormatException('Subject directory list was not returned.');
      }
      final subjects = rawSubjects
          .map(_asMap)
          .whereType<Map<String, dynamic>>()
          .where((item) => item['domain_id'] == domainId)
          .toList(growable: false);
      if (!mounted) return;
      setState(() {
        _subjects = subjects;
        _loadingSubjects = false;
        _messageKey = null;
      });
    } on Object catch (error) {
      if (!mounted) return;
      setState(() {
        _loadingSubjects = false;
        _messageKey = _errorMessageKey(error, forDirectory: true);
      });
    }
  }

  Future<void> _select(String domainId, String subjectId) async {
    if (_selecting || _contextRequestInFlight || _loadingContext) return;
    setState(() {
      _selecting = true;
      _messageKey = null;
    });
    if (!await widget.beforeContextChange() || !mounted) {
      if (mounted) setState(() => _selecting = false);
      return;
    }
    try {
      final envelope = await widget.client.selectContext(
        domainId: domainId,
        subjectId: subjectId,
      );
      if (!mounted) return;
      widget.onContextChanged(envelope);
      Navigator.of(context).pop(envelope);
    } on Object catch (error) {
      if (!mounted) return;
      setState(() {
        _selecting = false;
        _messageKey = _errorMessageKey(error, forDirectory: false);
      });
    }
  }

  Future<void> _clear() async {
    if (_selecting || _contextRequestInFlight || _loadingContext) return;
    setState(() {
      _selecting = true;
    });
    if (!await widget.beforeContextChange() || !mounted) {
      if (mounted) setState(() => _selecting = false);
      return;
    }
    try {
      final envelope = await widget.client.clearContext();
      if (!mounted) return;
      widget.onContextChanged(envelope);
      Navigator.of(context).pop(envelope);
    } on Object catch (error) {
      if (!mounted) return;
      setState(() {
        _selecting = false;
        _messageKey = _errorMessageKey(error, forDirectory: false);
      });
    }
  }

  List<Map<String, dynamic>> _readDomains(Object? value) {
    if (value is! List) return const [];
    return value
        .map(_asMap)
        .whereType<Map<String, dynamic>>()
        .where((item) => item['id'] == 'CTH' || item['id'] == 'BMP')
        .toList(growable: false);
  }

  static Map<String, dynamic>? _asMap(Object? value) {
    if (value is Map<String, dynamic>) return value;
    if (value is Map) return value.map((key, value) => MapEntry('$key', value));
    return null;
  }

  String _errorMessageKey(Object error, {required bool forDirectory}) {
    if (error is LumenisCoreException) {
      const accepted = {
        'context.error.auth_required',
        'context.error.authorization_unavailable',
        'context.error.invalid_selection',
        'context.error.permission_denied',
        'context.error.subject_unavailable',
        'context.error.registry_unavailable',
        'context.error.unavailable',
      };
      if (error.messageKey != null && accepted.contains(error.messageKey)) {
        return error.messageKey!;
      }
      return switch (error.statusCode) {
        401 => 'context.error.auth_required',
        403 => 'context.error.permission_denied',
        503 => 'context.error.authorization_unavailable',
        _ =>
          forDirectory
              ? 'context.error.registry_unavailable'
              : 'context.error.unavailable',
      };
    }
    return forDirectory
        ? 'context.error.registry_unavailable'
        : 'context.error.unavailable';
  }

  String _subjectName(Map<String, dynamic> subject, BuildContext context) {
    final display = _asMap(subject['display_name']);
    final locale = Localizations.localeOf(context);
    final name =
        display?[locale.toLanguageTag()] ??
        display?[locale.languageCode] ??
        (locale.languageCode == 'zh' ? subject['name_zh'] : null) ??
        display?['en'] ??
        display?['zh-CN'] ??
        subject['name_en'] ??
        subject['name_zh'];
    return name is String && name.trim().isNotEmpty
        ? name.trim()
        : context.lumenisL10n.text('context.selector.unnamed_subject');
  }

  List<Map<String, dynamic>> _filteredSubjects(BuildContext context) {
    final query = _query.trim().toLowerCase();
    if (query.isEmpty) return _subjects;
    return _subjects
        .where((subject) {
          final fields = [
            _subjectName(subject, context),
            subject['industry'],
            subject['subject_type_name'],
          ];
          return fields.whereType<String>().any(
            (value) => value.toLowerCase().contains(query),
          );
        })
        .toList(growable: false);
  }

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    final current = _asMap(_envelope?['context']);
    final currentSubjectId = current?['subject_id'];
    final filteredSubjects = _filteredSubjects(context);
    return PopScope(
      canPop: !_selecting,
      child: Dialog(
        insetPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 24),
        backgroundColor: LumenisTheme.of(context).surface,
        child: ConstrainedBox(
          constraints: BoxConstraints(
            maxWidth: 620,
            maxHeight: MediaQuery.sizeOf(context).height * 0.86,
          ),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(24, 20, 24, 20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        copy.text('context.selector.open'),
                        style: TextStyle(
                          color: LumenisTheme.of(context).foreground,
                          fontSize: 20,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                    IconButton(
                      key: const ValueKey('context-picker-close'),
                      tooltip: copy.text('context.selector.close'),
                      onPressed: _selecting
                          ? null
                          : () => Navigator.of(context).maybePop(),
                      icon: const LumenisIcon(Icons.close_rounded),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                Text(
                  copy.text('context.selector.scope_note'),
                  style: TextStyle(
                    color: LumenisTheme.of(context).muted,
                    height: 1.45,
                  ),
                ),
                const SizedBox(height: 18),
                if (_loadingContext)
                  Semantics(
                    liveRegion: true,
                    label: copy.text('context.selector.loading'),
                    child: const LinearProgressIndicator(minHeight: 2),
                  )
                else if (_domains.isEmpty)
                  Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      _ContextPickerMessage(
                        text: copy.text(
                          _messageKey ?? 'context.selector.no_domains',
                        ),
                        onRetry: _selecting || _contextRequestInFlight
                            ? null
                            : _refreshContext,
                      ),
                      if (widget.canReturnToGlobal && _messageKey != null)
                        Align(
                          alignment: Alignment.centerRight,
                          child: TextButton.icon(
                            key: const ValueKey('context-picker-return-global'),
                            onPressed: _selecting || _contextRequestInFlight
                                ? null
                                : _clear,
                            icon: const LumenisIcon(Icons.public_rounded),
                            label: Text(copy.text('context.mode.global_all')),
                          ),
                        ),
                      if (_selecting)
                        const Padding(
                          padding: EdgeInsets.only(top: 8),
                          child: LinearProgressIndicator(minHeight: 2),
                        ),
                    ],
                  )
                else ...[
                  _ScopeModeRow(
                    current: current,
                    currentLabel: current?['mode'] == 'GLOBAL_ALL'
                        ? copy.text('context.mode.global_all')
                        : current == null
                        ? copy.text('shell.context.unavailable')
                        : _subjectName(current, context),
                    selecting: _selecting,
                    onClear: _clear,
                  ),
                  const SizedBox(height: 18),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      for (final domain in _domains)
                        ChoiceChip(
                          label: Text(_domainLabel(domain['id'], copy)),
                          selected: _domainId == domain['id'],
                          onSelected: _loadingSubjects || _selecting
                              ? null
                              : (_) => _loadSubjects(domain['id'] as String),
                        ),
                    ],
                  ),
                  const SizedBox(height: 14),
                  TextField(
                    enabled: !_loadingSubjects && !_selecting,
                    onChanged: (value) => setState(() => _query = value),
                    decoration: InputDecoration(
                      hintText: copy.text('context.selector.search_hint'),
                      prefixIcon: const LumenisIcon(Icons.search_rounded),
                      filled: true,
                      fillColor: LumenisTheme.of(context).canvas,
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.zero,
                        borderSide: BorderSide(
                          color: LumenisTheme.of(context).line,
                        ),
                      ),
                      enabledBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.zero,
                        borderSide: BorderSide(
                          color: LumenisTheme.of(context).line,
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: 10),
                  if (_loadingSubjects)
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 18),
                      child: Semantics(
                        liveRegion: true,
                        label: copy.text('context.selector.loading_subjects'),
                        child: const LinearProgressIndicator(minHeight: 2),
                      ),
                    )
                  else if (_messageKey != null)
                    _ContextPickerMessage(
                      text: copy.text(_messageKey!),
                      onRetry: _selecting || _contextRequestInFlight
                          ? null
                          : _domainId == null
                          ? _refreshContext
                          : () => _loadSubjects(_domainId!),
                    )
                  else if (filteredSubjects.isEmpty)
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 20),
                      child: Text(
                        copy.text('context.selector.empty'),
                        style: TextStyle(
                          color: LumenisTheme.of(context).muted,
                          height: 1.5,
                        ),
                      ),
                    )
                  else
                    Expanded(
                      child: ListView.separated(
                        itemCount: filteredSubjects.length,
                        separatorBuilder: (_, _) => const Divider(height: 1),
                        itemBuilder: (context, index) {
                          final subject = filteredSubjects[index];
                          final subjectId = subject['subject_id'];
                          if (subjectId is! String || subjectId.isEmpty) {
                            return const SizedBox.shrink();
                          }
                          final subjectDomain = subject['domain_id'];
                          if (subjectDomain != _domainId) {
                            return const SizedBox.shrink();
                          }
                          final name = _subjectName(subject, context);
                          final metadata =
                              [
                                subject['subject_type_name'],
                                subject['industry'],
                              ].whereType<String>().where(
                                (item) => item.isNotEmpty,
                              );
                          return ListTile(
                            contentPadding: EdgeInsets.zero,
                            enabled: !_selecting,
                            leading: LumenisIcon(
                              _domainId == 'BMP'
                                  ? Icons.sell_outlined
                                  : Icons.apartment_rounded,
                              color: _domainId == 'BMP'
                                  ? LumenisTheme.of(context).bmp
                                  : LumenisTheme.of(context).cth,
                            ),
                            title: Text(name),
                            subtitle: metadata.isEmpty
                                ? null
                                : Text(metadata.join(' · ')),
                            trailing: currentSubjectId == subjectId
                                ? Text(
                                    copy.text('context.selector.selected'),
                                    style: TextStyle(
                                      color: LumenisTheme.of(context).accent,
                                      fontSize: 13,
                                    ),
                                  )
                                : const LumenisIcon(
                                    Icons.chevron_right_rounded,
                                  ),
                            onTap: _selecting || _domainId == null
                                ? null
                                : () => _select(_domainId!, subjectId),
                          );
                        },
                      ),
                    ),
                ],
                if (_selecting)
                  const Padding(
                    padding: EdgeInsets.only(top: 8),
                    child: LinearProgressIndicator(minHeight: 2),
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  String _domainLabel(Object? id, LumenisLocalizations copy) => switch (id) {
    'CTH' => copy.text('domain.cth'),
    'BMP' => copy.text('domain.zbmp'),
    _ => copy.text('context.selector.unnamed_subject'),
  };
}

class _ScopeModeRow extends StatelessWidget {
  const _ScopeModeRow({
    required this.current,
    required this.currentLabel,
    required this.selecting,
    required this.onClear,
  });

  final Map<String, dynamic>? current;
  final String currentLabel;
  final bool selecting;
  final VoidCallback onClear;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    final isGlobal = current?['mode'] == 'GLOBAL_ALL';
    return DecoratedBox(
      decoration: BoxDecoration(
        border: Border(
          bottom: BorderSide(color: LumenisTheme.of(context).line),
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.only(bottom: 14),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    copy.text('context.selector.selected'),
                    style: TextStyle(
                      color: LumenisTheme.of(context).quiet,
                      fontSize: 12,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    currentLabel,
                    style: TextStyle(
                      color: LumenisTheme.of(context).foreground,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
            ),
            if (!isGlobal)
              TextButton(
                onPressed: selecting ? null : onClear,
                child: Text(copy.text('context.mode.global_all')),
              ),
          ],
        ),
      ),
    );
  }
}

class _ContextPickerMessage extends StatelessWidget {
  const _ContextPickerMessage({required this.text, required this.onRetry});

  final String text;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 12),
    child: Row(
      children: [
        Expanded(
          child: Text(
            text,
            style: TextStyle(
              color: LumenisTheme.of(context).muted,
              height: 1.5,
            ),
          ),
        ),
        TextButton(
          key: const ValueKey('context-picker-retry'),
          onPressed: onRetry,
          child: Text(context.lumenisL10n.text('context.selector.retry')),
        ),
      ],
    ),
  );
}

class _LumenisMark extends StatelessWidget {
  const _LumenisMark();

  @override
  Widget build(BuildContext context) {
    final theme = LumenisTheme.of(context);
    return Semantics(
      container: true,
      label: '寰意 / OEVIRA',
      child: ExcludeSemantics(
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const LumenisBotanical(size: 38, monochrome: true),
            const SizedBox(width: 10),
            Flexible(
              child: Text(
                'OEVIRA',
                style: TextStyle(
                  color: theme.foreground,
                  fontSize: 16,
                  letterSpacing: 2.5,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _SectionLabel extends StatelessWidget {
  const _SectionLabel(this.text);

  final String text;

  @override
  Widget build(BuildContext context) {
    return Text(
      text,
      style: TextStyle(
        color: LumenisTheme.of(context).quiet,
        fontSize: 12,
        letterSpacing: 0,
        fontWeight: FontWeight.w600,
      ),
    );
  }
}

class _LocaleSwitcher extends StatelessWidget {
  const _LocaleSwitcher({required this.onLocaleChanged});

  final ValueChanged<Locale?> onLocaleChanged;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    return PopupMenuButton<String>(
      tooltip: copy.text('shell.locale.tooltip'),
      icon: const LumenisIcon(Icons.language_rounded),
      onSelected: (selection) {
        final locale = switch (selection) {
          'zh-CN' => const Locale('zh', 'CN'),
          'en' => const Locale('en'),
          'ko' => const Locale('ko'),
          _ => null,
        };
        onLocaleChanged(locale);
      },
      itemBuilder: (context) => [
        PopupMenuItem(value: 'system', child: Text(copy.text('locale.system'))),
        PopupMenuItem(value: 'zh-CN', child: Text(copy.text('locale.zh-CN'))),
        PopupMenuItem(value: 'en', child: Text(copy.text('locale.en'))),
        PopupMenuItem(value: 'ko', child: Text(copy.text('locale.ko'))),
      ],
    );
  }
}

class _WorkspaceDestination {
  const _WorkspaceDestination({
    required this.id,
    required this.labelKey,
    required this.mobileLabelKey,
    required this.groupKey,
    required this.icon,
    required this.color,
  });

  final String id;
  final String labelKey;
  final String mobileLabelKey;
  final String groupKey;
  final IconData icon;
  final Color color;
}

String _shellCopy(
  BuildContext context, {
  required String zh,
  required String en,
  required String ko,
}) => switch (context.lumenisL10n.locale.languageCode) {
  'en' => en,
  'ko' => ko,
  _ => zh,
};
