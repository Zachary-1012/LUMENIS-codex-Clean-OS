import 'package:flutter/material.dart';
import '../features/system/sys05/sys05_appearance_editor.dart';

import '../core/lumenis_core_client.dart';
import '../core/lumenis_theme.dart';
import '../features/account/acc01/acc01_screen.dart';
import '../features/account/acc02/acc02_screen.dart';
import '../features/account/acc03/acc03_screen.dart';
import '../features/account/acc03/acc03_snapshot.dart';
import '../features/account/acc04/acc04_screen.dart';
import '../features/ai01/ai01_screen.dart';
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
import '../features/system/sys07/sys07_screen.dart';
import '../features/system/sys08/sys08_screen.dart';
import '../l10n/lumenis_localizations.dart';
import '../navigation/lumenis_workspace_routes.dart';

Widget buildLumenisWorkspaceScreen({
  required String screenId,
  required LumenisCoreClient client,
  ValueChanged<String>? onNavigate,
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
      onOpen: onNavigate == null
          ? null
          : (destination) => onNavigate(switch (destination) {
              Acc03Destination.commerce => 'CTH-01',
              Acc03Destination.brand => 'BMP-01',
              Acc03Destination.ai => 'AI-01',
            }),
    ),
    'ACC-04' => Acc04Screen(
      client: client,
      onReturn: onNavigate == null ? null : () => onNavigate('ACC-03'),
    ),
    'AI-01' => Ai01Screen(client: client),
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
    'BMP-01' => Bmp01Screen(client: client),
    'BMP-02' => Bmp02Screen(client: client),
    'BMP-03' => Bmp03Screen(client: client),
    'BMP-04' => Bmp04Screen(client: client),
    'BMP-05' => Bmp05Screen(client: client),
    'BMP-06' => Bmp06Screen(client: client),
    'BMP-07' => Bmp07Screen(client: client),
    'BMP-08' => Bmp08Screen(client: client),
    'BMP-09' => Bmp09Screen(client: client),
    'BMP-10' => Bmp10Screen(client: client),
    'BMP-11' => Bmp11Screen(client: client),
    'SH-01' => Sh01Screen(client: client),
    'SH-02' => Sh02Screen(client: client),
    'SH-03' => Sh03Screen(client: client),
    'SH-04' => Sh04Screen(client: client),
    'SH-05' => Sh05Screen(client: client),
    'SH-06' => Sh06Screen(client: client),
    'SYS-01' => Sys01Screen(client: client),
    'SYS-02' => Sys02Screen(client: client),
    'SYS-03' => Sys03Screen(client: client),
    'SYS-04' => Sys04Screen(client: client),
    'SYS-05' => Sys05Screen(client: client),
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
    this.initialScreenId = 'CTH-01',
    this.onScreenSelected,
    this.onLocaleChanged,
    super.key,
  });

  final LumenisCoreClient client;
  final Map<String, dynamic> runtime;
  final List<Map<String, dynamic>> subjects;
  final Map<String, dynamic>? contextEnvelope;
  final String? subjectDirectoryMessage;
  final String initialScreenId;
  final ValueChanged<String>? onScreenSelected;
  final ValueChanged<Locale?>? onLocaleChanged;

  @override
  State<LumenisWorkspaceShell> createState() => _LumenisWorkspaceShellState();
}

class _LumenisWorkspaceShellState extends State<LumenisWorkspaceShell>
    with RestorationMixin {
  final RestorableString _activeScreen = RestorableString('CTH-01');
  final GlobalKey _screenHostKey = GlobalKey(
    debugLabel: 'workspace-screen-host',
  );
  Map<String, dynamic>? _contextEnvelope;
  Map<String, dynamic>? _unavailableContextEnvelope;
  bool _hasConfirmedFocusRecoveryHint = false;

  @override
  void initState() {
    super.initState();
    _contextEnvelope =
        widget.contextEnvelope ?? widget.client.currentContextEnvelope;
    _hasConfirmedFocusRecoveryHint = _isConfirmedFocusEnvelope(
      _contextEnvelope,
    );
  }

  @override
  void didUpdateWidget(covariant LumenisWorkspaceShell oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.contextEnvelope != widget.contextEnvelope &&
        widget.contextEnvelope != null &&
        !identical(widget.contextEnvelope, _unavailableContextEnvelope)) {
      _contextEnvelope = widget.contextEnvelope;
      _unavailableContextEnvelope = null;
      _hasConfirmedFocusRecoveryHint = _isConfirmedFocusEnvelope(
        widget.contextEnvelope,
      );
    }
    if (oldWidget.initialScreenId != widget.initialScreenId &&
        LumenisWorkspaceRoutes.supportsWorkspaceScreen(
          widget.initialScreenId,
        ) &&
        _activeScreen.value != widget.initialScreenId) {
      setState(() => _activeScreen.value = widget.initialScreenId);
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

  static _WorkspaceDestination _accountDestination(Color accent) =>
      _WorkspaceDestination(
        id: 'ACC-01',
        labelKey: 'screen.ACC-01',
        mobileLabelKey: 'screen.ACC-01',
        groupKey: 'screen.ACC-03',
        icon: Icons.person_outline_rounded,
        color: accent,
      );

  @override
  String get restorationId => 'workspace-shell';

  @override
  void restoreState(RestorationBucket? oldBucket, bool initialRestore) {
    registerForRestoration(_activeScreen, 'active-screen');
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
    _activeScreen.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        if (constraints.maxWidth < 768) {
          return _buildPhone(context);
        }
        if (constraints.maxWidth < 1280) {
          return _buildCompactWorkspace(context);
        }
        return _buildWideWorkspace(
          context,
          showInspector: constraints.maxWidth >= 1720,
        );
      },
    );
  }

  String get _activeGroup =>
      LumenisWorkspaceRoutes.groupForScreen(_activeScreen.value);

  int get _selectedIndex =>
      _destinations.indexWhere((item) => item.id.startsWith('$_activeGroup-'));

  _WorkspaceDestination get _selectedDestination => _activeGroup == 'ACC'
      ? _accountDestination(LumenisTheme.of(context).accent)
      : _destinations[_selectedIndex < 0 ? 0 : _selectedIndex];

  List<String> get _secondaryScreenIds {
    final groupScreenIds =
        LumenisWorkspaceRoutes.screenIdsByGroup[_activeGroup] ?? const [];
    if (_activeGroup == 'ACC' || groupScreenIds.length < 2) {
      return groupScreenIds;
    }
    return groupScreenIds.skip(1).toList(growable: false);
  }

  void _select(int index) {
    if (index < 0 || index >= _destinations.length) return;
    _activateScreen(_destinations[index].id);
  }

  void _activateScreen(String screenId, {bool notifyRoute = true}) {
    if (!LumenisWorkspaceRoutes.supportsScreen(screenId)) {
      return;
    }
    if (LumenisWorkspaceRoutes.desktopRequiredScreenIds.contains(screenId)) {
      if (notifyRoute) widget.onScreenSelected?.call(screenId);
      return;
    }
    if (_activeScreen.value == screenId) return;
    final currentEnvelope = widget.client.currentContextEnvelope;
    final shouldAdoptCurrentEnvelope =
        currentEnvelope != null &&
        !identical(currentEnvelope, _unavailableContextEnvelope);
    setState(() {
      if (shouldAdoptCurrentEnvelope) {
        _contextEnvelope = currentEnvelope;
        _unavailableContextEnvelope = null;
        _hasConfirmedFocusRecoveryHint = _isConfirmedFocusEnvelope(
          currentEnvelope,
        );
      }
      _activeScreen.value = screenId;
    });
    if (notifyRoute) widget.onScreenSelected?.call(screenId);
  }

  Widget _screen() => buildLumenisWorkspaceScreen(
    screenId: _activeScreen.value,
    client: widget.client,
    onNavigate: _activateScreen,
  );

  Widget _screenTransition() {
    final reduceMotion =
        MediaQuery.maybeOf(context)?.disableAnimations ?? false;
    final duration = reduceMotion
        ? Duration.zero
        : const Duration(milliseconds: 180);

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
        key: ValueKey('${_activeScreen.value}:$_contextFingerprint'),
        child: _screen(),
      ),
    );
  }

  Widget _buildPhone(BuildContext context) {
    return Scaffold(
      backgroundColor: LumenisTheme.of(context).canvas,
      body: SafeArea(
        bottom: false,
        child: Column(
          children: [
            _PhoneHeader(
              screenId: _activeScreen.value,
              contextLabel: _contextLabel(),
              onOpenContextPicker: _openContextPicker,
              onOpenPages: _openPhonePages,
              onOpenTools: _openPhoneTools,
              onReturnToCth: _returnFromCth02,
              isCth02: _activeScreen.value == 'CTH-02',
            ),
            Expanded(child: _screenTransition()),
          ],
        ),
      ),
      bottomNavigationBar: _activeGroup == 'ACC'
          ? null
          : NavigationBar(
              height: 68,
              elevation: 0,
              surfaceTintColor: Colors.transparent,
              shadowColor: Colors.transparent,
              selectedIndex: _selectedIndex < 0 ? 0 : _selectedIndex,
              onDestinationSelected: _select,
              backgroundColor: LumenisTheme.of(
                context,
              ).surface.withValues(alpha: .94),
              indicatorColor: Colors.transparent,
              labelTextStyle: WidgetStateProperty.resolveWith(
                (states) => TextStyle(
                  fontSize: 12,
                  height: 1.3,
                  fontWeight: states.contains(WidgetState.selected)
                      ? FontWeight.w700
                      : FontWeight.w400,
                  color: LumenisTheme.of(context).foreground,
                ),
              ),
              labelBehavior: NavigationDestinationLabelBehavior.alwaysShow,
              destinations: [
                for (final item in _destinations)
                  NavigationDestination(
                    icon: Icon(item.icon),
                    selectedIcon: Stack(
                      clipBehavior: Clip.none,
                      children: [
                        Icon(
                          item.icon,
                          color: LumenisTheme.of(
                            context,
                          ).resolveSemantic(item.color),
                        ),
                        Positioned(
                          bottom: -5,
                          left: 8,
                          right: 8,
                          child: Container(
                            height: 2,
                            color: LumenisTheme.of(context).foreground,
                          ),
                        ),
                      ],
                    ),
                    label: context.lumenisL10n.text(item.mobileLabelKey),
                    tooltip: context.lumenisL10n.text(item.labelKey),
                  ),
              ],
            ),
    );
  }

  Future<void> _openPhonePages() async {
    final copy = context.lumenisL10n;
    final workflows = LumenisWorkspaceRoutes.workflowsByGroup[_activeGroup]!;
    final selected = await showModalBottomSheet<String>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      constraints: const BoxConstraints(maxWidth: 620),
      builder: (sheetContext) => SafeArea(
        child: ConstrainedBox(
          constraints: BoxConstraints(
            maxHeight: MediaQuery.sizeOf(sheetContext).height * .75,
          ),
          child: _PhoneSheet(
            title: copy.text(_selectedDestination.labelKey),
            child: ListView(
              shrinkWrap: true,
              padding: const EdgeInsets.fromLTRB(20, 0, 20, 24),
              children: [
                for (final workflow in workflows.entries) ...[
                  Padding(
                    padding: const EdgeInsets.only(top: 24, bottom: 6),
                    child: Text(
                      copy.text(workflow.key),
                      style: Theme.of(sheetContext).textTheme.labelMedium,
                    ),
                  ),
                  for (final screenId in workflow.value)
                    ListTile(
                      key: ValueKey('workspace-nav-$screenId'),
                      contentPadding: const EdgeInsets.symmetric(horizontal: 8),
                      title: Text(copy.text('screen.$screenId')),
                      selected: screenId == _activeScreen.value,
                      trailing: screenId == _activeScreen.value
                          ? const Icon(Icons.check_rounded, size: 20)
                          : LumenisWorkspaceRoutes.desktopRequiredScreenIds
                                .contains(screenId)
                          ? const Icon(Icons.desktop_windows_outlined, size: 20)
                          : null,
                      onTap: () => Navigator.of(sheetContext).pop(screenId),
                    ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
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
                ListTile(
                  key: const ValueKey('workspace-account-navigation'),
                  contentPadding: EdgeInsets.zero,
                  leading: Icon(
                    _activeGroup == 'ACC'
                        ? Icons.arrow_back_rounded
                        : Icons.person_outline_rounded,
                  ),
                  title: Text(
                    copy.text(
                      _activeGroup == 'ACC' ? 'navgroup.cth' : 'screen.ACC-01',
                    ),
                  ),
                  onTap: () => Navigator.of(sheetContext).pop('account'),
                ),
                if (_activeGroup == 'CTH')
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: const Icon(Icons.account_tree_outlined),
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
      case 'account':
        _openAccount();
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

  Widget _buildCompactWorkspace(BuildContext context) {
    final destination = _selectedDestination;
    return Scaffold(
      backgroundColor: LumenisTheme.of(context).canvas,
      body: Row(
        children: [
          NavigationRail(
            selectedIndex: _selectedIndex < 0 ? null : _selectedIndex,
            onDestinationSelected: _select,
            backgroundColor: LumenisTheme.of(context).surface,
            indicatorColor: LumenisTheme.of(
              context,
            ).accent.withValues(alpha: 0.13),
            labelType: NavigationRailLabelType.none,
            leading: const Padding(
              padding: EdgeInsets.only(bottom: 18, top: 16),
              child: _LumenisMark(compact: true),
            ),
            destinations: [
              for (final item in _destinations)
                NavigationRailDestination(
                  icon: Tooltip(
                    message: context.lumenisL10n.text(item.labelKey),
                    child: Icon(item.icon),
                  ),
                  selectedIcon: Icon(
                    item.icon,
                    color: LumenisTheme.of(context).resolveSemantic(item.color),
                  ),
                  label: Text(context.lumenisL10n.text(item.labelKey)),
                ),
            ],
          ),
          const VerticalDivider(width: 1, thickness: 1),
          Expanded(
            child: Column(
              children: [
                _WorkspaceHeader(
                  destination: destination,
                  activeScreenId: _activeScreen.value,
                  contextLabel: _contextLabel(),
                  coreLabel: _coreLabel,
                  onOpenContextPicker: _openContextPicker,
                  onOpenAccount: _openAccount,
                  onLocaleChanged: widget.onLocaleChanged,
                  compact: true,
                  onOpenCth02: _openCth02,
                  onReturnToCth: _returnFromCth02,
                  isCth02: _activeScreen.value == 'CTH-02',
                  accountActive: _activeGroup == 'ACC',
                ),
                _SecondaryNavigation(
                  screenIds: _secondaryScreenIds,
                  activeScreenId: _activeScreen.value,
                  color: LumenisTheme.of(
                    context,
                  ).resolveSemantic(destination.color),
                  onSelected: _activateScreen,
                ),
                Expanded(child: _screenTransition()),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildWideWorkspace(
    BuildContext context, {
    required bool showInspector,
  }) {
    final destination = _selectedDestination;
    return Scaffold(
      backgroundColor: LumenisTheme.of(context).canvas,
      body: Row(
        children: [
          _WideNavigation(
            destinations: _destinations,
            selectedIndex: _selectedIndex,
            onSelected: _select,
            accountDestination: _accountDestination(
              LumenisTheme.of(context).accent,
            ),
            accountSelected: _activeGroup == 'ACC',
            onAccountSelected: _openAccount,
            screenIds: _secondaryScreenIds,
            activeScreenId: _activeScreen.value,
            onScreenSelected: _activateScreen,
          ),
          const VerticalDivider(width: 1, thickness: 1),
          Expanded(
            child: Column(
              children: [
                _WorkspaceHeader(
                  destination: destination,
                  activeScreenId: _activeScreen.value,
                  contextLabel: _contextLabel(),
                  coreLabel: _coreLabel,
                  onOpenContextPicker: _openContextPicker,
                  onOpenAccount: _openAccount,
                  onLocaleChanged: widget.onLocaleChanged,
                  onOpenCth02: _openCth02,
                  onReturnToCth: _returnFromCth02,
                  isCth02: _activeScreen.value == 'CTH-02',
                  accountActive: _activeGroup == 'ACC',
                ),
                Expanded(child: _screenTransition()),
              ],
            ),
          ),
          if (showInspector) ...[
            const VerticalDivider(width: 1, thickness: 1),
            _ContextInspector(
              destination: destination,
              contextLabel: _contextLabel(),
              selectionContext: _contextMap,
              contextUnavailable: _contextEnvelope == null,
            ),
          ],
        ],
      ),
    );
  }

  String get _coreLabel => context.lumenisL10n.text(
    widget.runtime['ok'] == true ? 'shell.connected' : 'shell.pending',
  );

  Map<String, dynamic>? get _contextMap {
    final value = _contextEnvelope?['context'];
    if (value is Map<String, dynamic>) return value;
    if (value is Map) return value.map((key, value) => MapEntry('$key', value));
    return null;
  }

  String get _contextFingerprint {
    final selection = _contextMap;
    return '${selection?['mode']}:${selection?['domain_id']}:${selection?['subject_id']}';
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
    final canReturnToGlobal = _hasConfirmedFocusRecoveryHint;
    final selected = await showDialog<Map<String, dynamic>>(
      context: context,
      barrierDismissible: false,
      builder: (_) => _ContextPickerDialog(
        client: widget.client,
        canReturnToGlobal: canReturnToGlobal,
        onContextConfirmed: _acceptContextEnvelope,
        onContextUnavailable: _markContextUnavailable,
      ),
    );
    if (selected != null) _acceptContextEnvelope(selected);
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

  void _acceptContextEnvelope(Map<String, dynamic> envelope) {
    if (!mounted) return;
    setState(() {
      _contextEnvelope = envelope;
      _unavailableContextEnvelope = null;
      _hasConfirmedFocusRecoveryHint = _isConfirmedFocusEnvelope(envelope);
    });
  }

  void _markContextUnavailable() {
    if (!mounted) return;
    setState(() {
      _unavailableContextEnvelope ??=
          _contextEnvelope ?? widget.client.currentContextEnvelope;
      _contextEnvelope = null;
    });
  }

  void _openCth02() => _activateScreen('CTH-02');

  void _returnFromCth02() => _activateScreen('CTH-01');

  void _openAccount() => _activateScreen(
    _activeGroup == 'ACC' ? LumenisWorkspaceRoutes.rootScreenId : 'ACC-01',
  );
}

class _SecondaryNavigation extends StatefulWidget {
  const _SecondaryNavigation({
    required this.screenIds,
    required this.activeScreenId,
    required this.color,
    required this.onSelected,
  });

  final List<String> screenIds;
  final String activeScreenId;
  final Color color;
  final ValueChanged<String> onSelected;

  @override
  State<_SecondaryNavigation> createState() => _SecondaryNavigationState();
}

class _SecondaryNavigationState extends State<_SecondaryNavigation> {
  final GlobalKey _activeItemKey = GlobalKey();

  @override
  void initState() {
    super.initState();
    _revealActiveItem();
  }

  @override
  void didUpdateWidget(covariant _SecondaryNavigation oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.activeScreenId != widget.activeScreenId ||
        oldWidget.screenIds != widget.screenIds) {
      _revealActiveItem();
    }
  }

  void _revealActiveItem() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final itemContext = _activeItemKey.currentContext;
      if (!mounted || itemContext == null) return;
      final reduceMotion =
          MediaQuery.maybeOf(context)?.disableAnimations ?? false;
      Scrollable.ensureVisible(
        itemContext,
        alignment: 0.5,
        duration: reduceMotion
            ? Duration.zero
            : const Duration(milliseconds: 180),
        curve: Curves.easeOutCubic,
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    final workflows =
        LumenisWorkspaceRoutes
            .workflowsByGroup[LumenisWorkspaceRoutes.groupForScreen(
          widget.activeScreenId,
        )]!;
    final activeWorkflow = LumenisWorkspaceRoutes.workflowForScreen(
      widget.activeScreenId,
    );
    final stages = workflows[activeWorkflow]!;
    return SizedBox(
      height: 52,
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: LumenisTheme.of(context).canvas,
          border: Border(
            bottom: BorderSide(color: LumenisTheme.of(context).line),
          ),
        ),
        child: SingleChildScrollView(
          key: ValueKey(
            'workspace-secondary-${widget.activeScreenId.split('-').first}',
          ),
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: 14),
          child: Row(
            children: [
              PopupMenuButton<String>(
                tooltip: copy.text(activeWorkflow),
                onSelected: (workflow) =>
                    widget.onSelected(workflows[workflow]!.first),
                itemBuilder: (context) => [
                  for (final workflow in workflows.keys)
                    PopupMenuItem(
                      value: workflow,
                      child: Text(copy.text(workflow)),
                    ),
                ],
                child: Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 10,
                    vertical: 14,
                  ),
                  child: Row(
                    children: [
                      Text(
                        copy.text(activeWorkflow),
                        style: const TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      const SizedBox(width: 4),
                      const Icon(Icons.expand_more, size: 16),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 20, child: VerticalDivider(width: 12)),
              for (var index = 0; index < stages.length; index++) ...[
                if (index > 0) const SizedBox(width: 4),
                Builder(
                  builder: (context) {
                    final screenId = stages[index];
                    final selected = screenId == widget.activeScreenId;
                    final desktopRequired = LumenisWorkspaceRoutes
                        .desktopRequiredScreenIds
                        .contains(screenId);
                    return Semantics(
                      button: true,
                      selected: selected,
                      label: copy.text('screen.$screenId'),
                      child: InkWell(
                        key: ValueKey('workspace-nav-$screenId'),
                        onTap: () => widget.onSelected(screenId),
                        borderRadius: BorderRadius.circular(8),
                        child: Container(
                          key: selected ? _activeItemKey : null,
                          constraints: const BoxConstraints(
                            minWidth: 48,
                            minHeight: 48,
                          ),
                          padding: const EdgeInsets.symmetric(horizontal: 12),
                          decoration: BoxDecoration(
                            border: Border(
                              bottom: BorderSide(
                                color: selected
                                    ? widget.color
                                    : Colors.transparent,
                                width: 2,
                              ),
                            ),
                          ),
                          alignment: Alignment.center,
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Text(
                                copy.text('screen.$screenId'),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: TextStyle(
                                  color: selected
                                      ? LumenisTheme.of(context).foreground
                                      : LumenisTheme.of(context).muted,
                                  fontSize: 13,
                                  fontWeight: selected
                                      ? FontWeight.w600
                                      : FontWeight.w400,
                                ),
                              ),
                              if (desktopRequired) ...[
                                const SizedBox(width: 6),
                                Icon(
                                  Icons.desktop_windows_outlined,
                                  size: 14,
                                  color: LumenisTheme.of(context).quiet,
                                ),
                              ],
                            ],
                          ),
                        ),
                      ),
                    );
                  },
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _WideNavigation extends StatelessWidget {
  const _WideNavigation({
    required this.destinations,
    required this.selectedIndex,
    required this.onSelected,
    required this.accountDestination,
    required this.accountSelected,
    required this.onAccountSelected,
    required this.screenIds,
    required this.activeScreenId,
    required this.onScreenSelected,
  });

  final List<_WorkspaceDestination> destinations;
  final int selectedIndex;
  final ValueChanged<int> onSelected;
  final _WorkspaceDestination accountDestination;
  final bool accountSelected;
  final VoidCallback onAccountSelected;
  final List<String> screenIds;
  final String activeScreenId;
  final ValueChanged<String> onScreenSelected;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    return SizedBox(
      width: 216,
      child: DecoratedBox(
        decoration: BoxDecoration(color: LumenisTheme.of(context).canvas),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Padding(
              padding: EdgeInsets.fromLTRB(20, 20, 16, 26),
              child: _LumenisMark(),
            ),
            Padding(
              padding: EdgeInsets.fromLTRB(22, 0, 16, 12),
              child: _SectionLabel(copy.text('shell.workspace')),
            ),
            Expanded(
              child: ListView(
                padding: const EdgeInsets.symmetric(horizontal: 10),
                children: [
                  for (var index = 0; index < destinations.length; index++) ...[
                    _WideDestinationRow(
                      destination: destinations[index],
                      selected: index == selectedIndex,
                      onTap: () => onSelected(index),
                    ),
                    if (index == selectedIndex)
                      _NavigationTree(
                        screenIds: screenIds,
                        activeScreenId: activeScreenId,
                        onSelected: onScreenSelected,
                      ),
                  ],
                  if (accountSelected)
                    _NavigationTree(
                      screenIds: screenIds,
                      activeScreenId: activeScreenId,
                      onSelected: onScreenSelected,
                    ),
                ],
              ),
            ),
            const Divider(height: 1),
            Padding(
              padding: const EdgeInsets.fromLTRB(10, 10, 10, 0),
              child: _WideDestinationRow(
                destination: accountDestination,
                selected: accountSelected,
                onTap: onAccountSelected,
              ),
            ),
            Padding(
              padding: EdgeInsets.fromLTRB(22, 16, 20, 22),
              child: Text(
                copy.text('shell.workspace_summary'),
                style: TextStyle(
                  color: LumenisTheme.of(context).quiet,
                  height: 1.7,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _NavigationTree extends StatelessWidget {
  const _NavigationTree({
    required this.screenIds,
    required this.activeScreenId,
    required this.onSelected,
  });

  final List<String> screenIds;
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
                    borderRadius: BorderRadius.circular(8),
                    child: InkWell(
                      key: ValueKey('workspace-nav-$screenId'),
                      onTap: () => onSelected(screenId),
                      borderRadius: BorderRadius.circular(8),
                      child: ConstrainedBox(
                        constraints: const BoxConstraints(minHeight: 44),
                        child: Padding(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 14,
                            vertical: 9,
                          ),
                          child: Row(
                            children: [
                              Icon(
                                LumenisWorkspaceRoutes.desktopRequiredScreenIds
                                        .contains(screenId)
                                    ? Icons.desktop_windows_outlined
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
        borderRadius: BorderRadius.circular(8),
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(8),
          child: Semantics(
            button: true,
            selected: selected,
            label:
                '${copy.text(destination.labelKey)}，${copy.text(destination.groupKey)}',
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
              child: Row(
                children: [
                  Icon(destination.icon, size: 19, color: foreground),
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
    );
  }
}

class _WorkspaceHeader extends StatelessWidget {
  const _WorkspaceHeader({
    required this.destination,
    required this.activeScreenId,
    required this.contextLabel,
    required this.coreLabel,
    required this.onOpenContextPicker,
    required this.onOpenAccount,
    required this.onLocaleChanged,
    required this.onOpenCth02,
    required this.onReturnToCth,
    required this.isCth02,
    required this.accountActive,
    this.compact = false,
  });

  final _WorkspaceDestination destination;
  final String activeScreenId;
  final String contextLabel;
  final String coreLabel;
  final VoidCallback onOpenContextPicker;
  final VoidCallback onOpenAccount;
  final ValueChanged<Locale?>? onLocaleChanged;
  final VoidCallback onOpenCth02;
  final VoidCallback onReturnToCth;
  final bool isCth02;
  final bool accountActive;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    return Container(
      height: 64,
      padding: EdgeInsets.symmetric(horizontal: compact ? 20 : 26),
      decoration: BoxDecoration(
        border: Border(
          bottom: BorderSide(color: LumenisTheme.of(context).line),
        ),
      ),
      child: Row(
        children: [
          Expanded(
            child: Text(
              copy.text('screen.$activeScreenId'),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                color: LumenisTheme.of(context).foreground,
                fontSize: 16,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          if (!compact) ...[
            const SizedBox(width: 18),
            _StatusPill(label: coreLabel),
            const SizedBox(width: 18),
          ],
          Flexible(
            flex: 2,
            child: Text(
              contextLabel,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              textAlign: TextAlign.right,
              style: TextStyle(
                color: LumenisTheme.of(context).muted,
                fontSize: 13,
              ),
            ),
          ),
          IconButton(
            tooltip: copy.text('context.selector.open'),
            onPressed: onOpenContextPicker,
            icon: const Icon(Icons.tune_rounded),
            color: LumenisTheme.of(context).muted,
          ),
          IconButton(
            key: const ValueKey('workspace-account-navigation'),
            tooltip: copy.text(
              accountActive ? 'navgroup.cth' : 'screen.ACC-01',
            ),
            onPressed: onOpenAccount,
            icon: Icon(
              accountActive
                  ? Icons.space_dashboard_outlined
                  : Icons.person_outline_rounded,
            ),
            color: accountActive
                ? LumenisTheme.of(context).accent
                : LumenisTheme.of(context).muted,
          ),
          if (onLocaleChanged != null)
            _LocaleSwitcher(onLocaleChanged: onLocaleChanged!),
          const Sys05AppearanceButton(),
          if (isCth02)
            IconButton(
              tooltip: copy.text('shell.return_to_overview'),
              onPressed: onReturnToCth,
              icon: const Icon(Icons.arrow_back_rounded),
              color: LumenisTheme.of(context).muted,
            )
          else if (destination.id == 'CTH-01')
            IconButton(
              tooltip: copy.text('shell.open_subject_directory'),
              onPressed: onOpenCth02,
              icon: const Icon(Icons.account_tree_outlined),
              color: LumenisTheme.of(context).muted,
            ),
        ],
      ),
    );
  }
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
              icon: const Icon(Icons.close_rounded),
            ),
          ],
        ),
      ),
      Flexible(child: child),
    ],
  );
}

class _PhoneHeader extends StatelessWidget {
  const _PhoneHeader({
    required this.screenId,
    required this.contextLabel,
    required this.onOpenContextPicker,
    required this.onOpenPages,
    required this.onOpenTools,
    required this.onReturnToCth,
    required this.isCth02,
  });

  final String screenId;
  final String contextLabel;
  final VoidCallback onOpenContextPicker;
  final VoidCallback onOpenPages;
  final VoidCallback onOpenTools;
  final VoidCallback onReturnToCth;
  final bool isCth02;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    return Container(
      key: const ValueKey('workspace-phone-header'),
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: LumenisTheme.of(context).surface,
        border: Border(
          bottom: BorderSide(color: LumenisTheme.of(context).line),
        ),
      ),
      child: Row(
        children: [
          IconButton(
            key: const ValueKey('workspace-phone-pages'),
            tooltip: copy.text('shell.pages'),
            onPressed: onOpenPages,
            icon: const Icon(Icons.menu_rounded, size: 22),
          ),
          Expanded(
            child: Tooltip(
              message: copy.text('context.selector.open'),
              child: InkWell(
                onTap: onOpenContextPicker,
                borderRadius: BorderRadius.circular(8),
                child: ConstrainedBox(
                  constraints: const BoxConstraints(minHeight: 48),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 8,
                      vertical: 3,
                    ),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          copy.text('screen.$screenId'),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            color: LumenisTheme.of(context).foreground,
                            fontSize: 15,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Row(
                          children: [
                            Flexible(
                              child: Text(
                                contextLabel,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: TextStyle(
                                  color: LumenisTheme.of(context).muted,
                                  fontSize: 12,
                                ),
                              ),
                            ),
                            const SizedBox(width: 3),
                            Icon(
                              Icons.expand_more_rounded,
                              size: 14,
                              color: LumenisTheme.of(context).muted,
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
          const Sys05AppearanceButton(),
          if (isCth02)
            IconButton(
              tooltip: copy.text('shell.return_to_overview'),
              onPressed: onReturnToCth,
              icon: const Icon(Icons.arrow_back_rounded, size: 20),
              color: LumenisTheme.of(context).muted,
            ),
          IconButton(
            key: const ValueKey('workspace-phone-tools'),
            tooltip: copy.text('common.more'),
            onPressed: onOpenTools,
            icon: const Icon(Icons.more_horiz_rounded, size: 22),
          ),
        ],
      ),
    );
  }
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
              decoration: BoxDecoration(
                color: LumenisTheme.of(context).surface,
                border: Border.all(color: LumenisTheme.of(context).line),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(
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
    required this.onContextUnavailable,
  });

  final LumenisCoreClient client;
  final bool canReturnToGlobal;
  final ValueChanged<Map<String, dynamic>> onContextConfirmed;
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
    try {
      final envelope = await widget.client.selectContext(
        domainId: domainId,
        subjectId: subjectId,
      );
      if (!mounted) return;
      widget.onContextConfirmed(envelope);
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
    try {
      final envelope = await widget.client.clearContext();
      if (!mounted) return;
      widget.onContextConfirmed(envelope);
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
                      icon: const Icon(Icons.close_rounded),
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
                            icon: const Icon(Icons.public_rounded),
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
                      prefixIcon: const Icon(Icons.search_rounded),
                      filled: true,
                      fillColor: LumenisTheme.of(context).canvas,
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(10),
                        borderSide: BorderSide(
                          color: LumenisTheme.of(context).line,
                        ),
                      ),
                      enabledBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(10),
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
                            leading: Icon(
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
                                : const Icon(Icons.chevron_right_rounded),
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
  const _LumenisMark({this.compact = false});

  final bool compact;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    return Row(
      mainAxisSize: compact ? MainAxisSize.min : MainAxisSize.max,
      children: [
        Container(
          width: 34,
          height: 34,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: LumenisTheme.of(context).accent.withValues(alpha: 0.10),
            border: Border.all(
              color: LumenisTheme.of(context).accent.withValues(alpha: 0.38),
            ),
            borderRadius: BorderRadius.circular(11),
          ),
          child: Text(
            '序',
            style: TextStyle(
              color: LumenisTheme.of(context).accent,
              fontSize: 19,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
        if (!compact) ...[
          const SizedBox(width: 11),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'LUMENIS',
                  style: TextStyle(
                    color: LumenisTheme.of(context).foreground,
                    letterSpacing: 1.15,
                    fontWeight: FontWeight.w700,
                    fontSize: 13,
                  ),
                ),
                SizedBox(height: 3),
                Text(
                  copy.text('shell.workspace_summary'),
                  style: TextStyle(
                    color: LumenisTheme.of(context).quiet,
                    letterSpacing: 0.45,
                    fontSize: 9,
                  ),
                ),
              ],
            ),
          ),
        ],
      ],
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

class _StatusPill extends StatelessWidget {
  const _StatusPill({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: LumenisTheme.of(context).quiet.withValues(alpha: 0.08),
        border: Border.all(
          color: LumenisTheme.of(context).quiet.withValues(alpha: 0.22),
        ),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.circle, color: LumenisTheme.of(context).quiet, size: 6),
          const SizedBox(width: 7),
          Text(
            label,
            style: TextStyle(
              color: LumenisTheme.of(context).muted,
              fontSize: 12,
            ),
          ),
        ],
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
      icon: const Icon(Icons.language_rounded),
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
