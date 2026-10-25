import 'package:flutter/material.dart';

import '../core/lumenis_botanical.dart';
import '../core/lumenis_icon.dart';
import '../core/lumenis_theme.dart';

@immutable
class LumenisWorkDestination {
  const LumenisWorkDestination({
    required this.id,
    required this.label,
    required this.icon,
    required this.selected,
    required this.onOpen,
    this.separate = false,
    this.nested = false,
  });

  final String id;
  final String label;
  final IconData icon;
  final bool selected;
  final VoidCallback onOpen;
  final bool separate;
  final bool nested;
}

class LumenisWorkspaceFrame extends StatefulWidget {
  const LumenisWorkspaceFrame({
    required this.title,
    required this.scope,
    required this.destinations,
    required this.onHome,
    required this.onSearch,
    required this.onScope,
    required this.onTasks,
    required this.onNotifications,
    required this.onSettings,
    required this.onTools,
    required this.tools,
    required this.child,
    this.inspector,
    super.key,
  });

  final String title;
  final String scope;
  final List<LumenisWorkDestination> destinations;
  final VoidCallback onHome;
  final VoidCallback onSearch;
  final VoidCallback onScope;
  final VoidCallback onTasks;
  final VoidCallback onNotifications;
  final VoidCallback onSettings;
  final VoidCallback onTools;
  final List<Widget> tools;
  final Widget child;
  final Widget? inspector;

  @override
  State<LumenisWorkspaceFrame> createState() => _LumenisWorkspaceFrameState();
}

class _LumenisWorkspaceFrameState extends State<LumenisWorkspaceFrame> {
  bool? _expanded;
  final _scaffold = GlobalKey<ScaffoldState>();

  String _copy(String zh, String en, String ko) =>
      switch (Localizations.localeOf(context).languageCode) {
        'en' => en,
        'ko' => ko,
        _ => zh,
      };

  @override
  Widget build(BuildContext context) {
    final colors = LumenisTheme.of(context);
    return LayoutBuilder(
      builder: (context, size) {
        final narrow = size.maxWidth < 760;
        final wide = size.maxWidth >= 1120;
        final expanded = _expanded ?? wide;
        return Scaffold(
          key: _scaffold,
          backgroundColor: colors.canvas,
          drawer: narrow
              ? Drawer(
                  width: 264,
                  backgroundColor: colors.surface,
                  shape: const RoundedRectangleBorder(),
                  child: SafeArea(
                    child: _navigation(expanded: true, drawer: true),
                  ),
                )
              : null,
          body: SafeArea(
            bottom: false,
            child: Column(
              children: [
                _workbar(narrow: narrow, expanded: expanded),
                Expanded(
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      if (!narrow)
                        SizedBox(
                          width: expanded ? 204 : 72,
                          child: _navigation(expanded: expanded),
                        ),
                      Expanded(
                        child: ClipRect(
                          child: FocusTraversalGroup(child: widget.child),
                        ),
                      ),
                      if (widget.inspector != null &&
                          size.maxWidth >= 1500) ...[
                        VerticalDivider(width: 1, color: colors.line),
                        widget.inspector!,
                      ],
                    ],
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _workbar({required bool narrow, required bool expanded}) {
    final colors = LumenisTheme.of(context);
    final largeText = MediaQuery.textScalerOf(context).scale(14) > 20;
    return DecoratedBox(
      decoration: BoxDecoration(
        color: colors.surface,
        border: Border(bottom: BorderSide(color: colors.foreground, width: 1)),
      ),
      child: Padding(
        padding: EdgeInsets.symmetric(horizontal: narrow ? 8 : 16, vertical: 8),
        child: Column(
          children: [
            Row(
              children: [
                IconButton(
                  key: const ValueKey('workspace-navigation-open'),
                  tooltip: _copy('导航', 'Navigation', '탐색'),
                  onPressed: narrow
                      ? () => _scaffold.currentState?.openDrawer()
                      : () => setState(() => _expanded = !expanded),
                  icon: LumenisIcon(
                    expanded ? Icons.menu_open : Icons.menu,
                    size: 20,
                  ),
                ),
                TextButton(
                  key: const ValueKey('workspace-home'),
                  onPressed: widget.onHome,
                  style: TextButton.styleFrom(
                    padding: const EdgeInsets.symmetric(horizontal: 8),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const LumenisBotanical(size: 36, monochrome: true),
                      if (!narrow) ...[
                        const SizedBox(width: 8),
                        Text(
                          'OEVIRA',
                          style: TextStyle(
                            fontSize: 17,
                            letterSpacing: 3,
                            fontWeight: FontWeight.w800,
                            color: colors.foreground,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
                if (!narrow) ...[
                  const SizedBox(width: 28),
                  SizedBox(
                    height: 22,
                    child: VerticalDivider(color: colors.line),
                  ),
                  const SizedBox(width: 20),
                ],
                Expanded(
                  child: Text(
                    widget.title,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontWeight: FontWeight.w600,
                      color: colors.foreground,
                      fontSize: 14,
                    ),
                  ),
                ),
                IconButton(
                  key: const ValueKey('workspace-rail-search'),
                  tooltip: _copy(
                    '查找工作 · Ctrl / ⌘ K',
                    'Find work · Ctrl / ⌘ K',
                    '작업 찾기 · Ctrl / ⌘ K',
                  ),
                  onPressed: widget.onSearch,
                  icon: const LumenisIcon(Icons.search, size: 20),
                ),
                if (!narrow && !largeText) ...[
                  const SizedBox(width: 8),
                  Flexible(
                    child: TextButton.icon(
                      onPressed: widget.onScope,
                      icon: const LumenisIcon(Icons.expand_more, size: 16),
                      label: Text(
                        widget.scope,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ),
                  IconButton(
                    tooltip: _copy('任务', 'Tasks', '작업'),
                    onPressed: widget.onTasks,
                    icon: const LumenisIcon(Icons.checklist, size: 20),
                  ),
                  IconButton(
                    tooltip: _copy('通知', 'Notifications', '알림'),
                    onPressed: widget.onNotifications,
                    icon: const LumenisIcon(Icons.notifications_none, size: 20),
                  ),
                  ...widget.tools,
                ] else
                  IconButton(
                    tooltip: _copy('工作区选项', 'Workspace options', '작업 공간 옵션'),
                    onPressed: widget.onTools,
                    icon: const LumenisIcon(Icons.more_horiz, size: 20),
                  ),
              ],
            ),
            if (narrow || largeText)
              Align(
                alignment: Alignment.centerLeft,
                child: TextButton.icon(
                  onPressed: widget.onScope,
                  icon: const LumenisIcon(Icons.expand_more, size: 16),
                  label: Text(
                    widget.scope,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _navigation({required bool expanded, bool drawer = false}) {
    final colors = LumenisTheme.of(context);
    return DecoratedBox(
      decoration: BoxDecoration(
        color: colors.surfaceRaised,
        border: Border(right: BorderSide(color: colors.line)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (drawer)
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 16, 8, 16),
              child: Row(
                children: [
                  const LumenisBotanical(size: 40),
                  const SizedBox(width: 12),
                  const Expanded(
                    child: Text(
                      'OEVIRA',
                      style: TextStyle(
                        letterSpacing: 3,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ),
                  IconButton(
                    tooltip: _copy('关闭导航', 'Close navigation', '탐색 닫기'),
                    onPressed: () => Navigator.of(context).pop(),
                    icon: const LumenisIcon(Icons.close),
                  ),
                ],
              ),
            ),
          Expanded(
            child: ListView(
              key: const ValueKey('workspace-work-rail'),
              padding: EdgeInsets.fromLTRB(
                expanded ? 12 : 8,
                24,
                expanded ? 12 : 8,
                16,
              ),
              children: [
                for (final item in widget.destinations) ...[
                  if (item.separate)
                    Padding(
                      padding: const EdgeInsets.symmetric(
                        vertical: 14,
                        horizontal: 8,
                      ),
                      child: Divider(height: 1, color: colors.line),
                    ),
                  _destination(item, expanded: expanded, drawer: drawer),
                ],
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                _destination(
                  LumenisWorkDestination(
                    id: 'all',
                    label: _copy('全部工作', 'All work', '모든 작업'),
                    icon: Icons.apps,
                    selected: false,
                    onOpen: widget.onSearch,
                  ),
                  expanded: expanded,
                  drawer: drawer,
                ),
                _destination(
                  LumenisWorkDestination(
                    id: 'SYS-05',
                    label: _copy('设置', 'Settings', '설정'),
                    icon: Icons.tune,
                    selected: false,
                    onOpen: widget.onSettings,
                  ),
                  expanded: expanded,
                  drawer: drawer,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _destination(
    LumenisWorkDestination item, {
    required bool expanded,
    required bool drawer,
  }) {
    final colors = LumenisTheme.of(context);
    final foreground = item.selected ? colors.surface : colors.foreground;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Semantics(
        selected: item.selected,
        child: Tooltip(
          message: item.label,
          child: TextButton(
            key: ValueKey('workspace-rail-${item.id}'),
            onPressed: () {
              if (drawer) Navigator.of(context).pop();
              item.onOpen();
            },
            style: TextButton.styleFrom(
              alignment: expanded ? Alignment.centerLeft : Alignment.center,
              foregroundColor: foreground,
              backgroundColor: item.selected
                  ? colors.foreground
                  : Colors.transparent,
              minimumSize: const Size(48, 48),
              padding: EdgeInsets.symmetric(
                horizontal: expanded ? 12 : 4,
                vertical: 10,
              ),
              shape: const LumenisPixelBorder(step: 4),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                LumenisIcon(
                  item.icon,
                  size: item.nested ? 17 : 21,
                  color: foreground,
                ),
                if (expanded) ...[
                  SizedBox(width: item.nested ? 14 : 12),
                  Flexible(
                    child: Text(
                      item.label,
                      style: TextStyle(
                        fontSize: item.nested ? 12 : 13,
                        height: 1.4,
                        fontWeight: item.selected
                            ? FontWeight.w600
                            : FontWeight.w400,
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}
