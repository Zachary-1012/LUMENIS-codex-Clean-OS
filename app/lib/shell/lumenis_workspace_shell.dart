import 'package:flutter/material.dart';

import '../core/lumenis_core_client.dart';
import '../core/lumenis_theme.dart';
import '../features/ai01/ai01_screen.dart';
import '../features/bmp01/bmp01_screen.dart';
import '../features/cth/cth01/cth01_screen.dart';
import '../features/cth/cth02/cth02_screen.dart';
import '../features/shared/sh01/sh01_screen.dart';
import '../features/system/sys01/sys01_screen.dart';

class LumenisWorkspaceShell extends StatefulWidget {
  const LumenisWorkspaceShell({
    required this.client,
    required this.runtime,
    required this.subjects,
    this.subjectDirectoryMessage,
    required this.onLogout,
    super.key,
  });

  final LumenisCoreClient client;
  final Map<String, dynamic> runtime;
  final List<Map<String, dynamic>> subjects;
  final String? subjectDirectoryMessage;
  final VoidCallback onLogout;

  @override
  State<LumenisWorkspaceShell> createState() => _LumenisWorkspaceShellState();
}

class _LumenisWorkspaceShellState extends State<LumenisWorkspaceShell>
    with RestorationMixin {
  final RestorableString _activeScreen = RestorableString('CTH-01');

  static const _destinations = <_WorkspaceDestination>[
    _WorkspaceDestination(
      id: 'CTH-01',
      label: '商业运营',
      mobileLabel: '经营',
      group: 'CTH · 商业运营',
      icon: Icons.timeline_rounded,
      color: LumenisTheme.cth,
    ),
    _WorkspaceDestination(
      id: 'BMP-01',
      label: '品牌市场',
      mobileLabel: '品牌',
      group: 'BMP · 品牌市场',
      icon: Icons.hub_outlined,
      color: LumenisTheme.bmp,
    ),
    _WorkspaceDestination(
      id: 'AI-01',
      label: 'AI 助理',
      mobileLabel: 'AI',
      group: 'AI · 智能助理',
      icon: Icons.auto_awesome_outlined,
      color: LumenisTheme.ai,
    ),
    _WorkspaceDestination(
      id: 'SH-01',
      label: '共享服务',
      mobileLabel: '共享',
      group: '共享服务',
      icon: Icons.edit_note_rounded,
      color: LumenisTheme.shared,
    ),
    _WorkspaceDestination(
      id: 'SYS-01',
      label: '运行健康',
      mobileLabel: '运行',
      group: '系统运行',
      icon: Icons.monitor_heart_outlined,
      color: LumenisTheme.system,
    ),
  ];

  @override
  String get restorationId => 'workspace-shell';

  @override
  void restoreState(RestorationBucket? oldBucket, bool initialRestore) {
    registerForRestoration(_activeScreen, 'active-screen');
    if (_activeScreen.value != 'CTH-02' &&
        !_destinations.any((item) => item.id == _activeScreen.value)) {
      _activeScreen.value = 'CTH-01';
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
          return _buildPhone();
        }
        if (constraints.maxWidth < 1280) {
          return _buildCompactWorkspace();
        }
        return _buildWideWorkspace(showInspector: constraints.maxWidth >= 1720);
      },
    );
  }

  int get _selectedIndex => _destinations.indexWhere(
    (item) =>
        item.id ==
        (_activeScreen.value == 'CTH-02' ? 'CTH-01' : _activeScreen.value),
  );

  _WorkspaceDestination get _selectedDestination =>
      _destinations[_selectedIndex < 0 ? 0 : _selectedIndex];

  void _select(int index) {
    if (index < 0 || index >= _destinations.length) return;
    setState(() => _activeScreen.value = _destinations[index].id);
  }

  Widget _screen() => switch (_activeScreen.value) {
    'CTH-01' => Cth01Screen(client: widget.client),
    'CTH-02' => Cth02Screen(client: widget.client),
    'BMP-01' => Bmp01Screen(client: widget.client),
    'AI-01' => Ai01Screen(client: widget.client),
    'SH-01' => Sh01Screen(client: widget.client),
    'SYS-01' => Sys01Screen(client: widget.client),
    _ => Cth01Screen(client: widget.client),
  };

  Widget _buildPhone() {
    final destination = _selectedDestination;
    return Scaffold(
      backgroundColor: LumenisTheme.canvas,
      body: SafeArea(
        bottom: false,
        child: Column(
          children: [
            _PhoneHeader(
              destination: destination,
              contextLabel: _contextLabel(destination),
              coreLabel: _coreLabel,
              onOpenCth02: _openCth02,
              onReturnToCth: _returnFromCth02,
              isCth02: _activeScreen.value == 'CTH-02',
              onLogout: widget.onLogout,
            ),
            Expanded(
              child: KeyedSubtree(
                key: ValueKey(destination.id),
                child: _screen(),
              ),
            ),
          ],
        ),
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _selectedIndex < 0 ? 0 : _selectedIndex,
        onDestinationSelected: _select,
        backgroundColor: LumenisTheme.surface,
        indicatorColor: LumenisTheme.accent.withValues(alpha: 0.13),
        labelBehavior: NavigationDestinationLabelBehavior.alwaysShow,
        destinations: [
          for (final item in _destinations)
            NavigationDestination(
              icon: Icon(item.icon),
              selectedIcon: Icon(item.icon, color: item.color),
              label: item.mobileLabel,
              tooltip: item.label,
            ),
        ],
      ),
    );
  }

  Widget _buildCompactWorkspace() {
    final destination = _selectedDestination;
    return Scaffold(
      backgroundColor: LumenisTheme.canvas,
      body: Row(
        children: [
          NavigationRail(
            selectedIndex: _selectedIndex < 0 ? 0 : _selectedIndex,
            onDestinationSelected: _select,
            backgroundColor: LumenisTheme.surface,
            indicatorColor: LumenisTheme.accent.withValues(alpha: 0.13),
            labelType: NavigationRailLabelType.none,
            leading: const Padding(
              padding: EdgeInsets.only(bottom: 18, top: 16),
              child: _LumenisMark(compact: true),
            ),
            destinations: [
              for (final item in _destinations)
                NavigationRailDestination(
                  icon: Tooltip(message: item.label, child: Icon(item.icon)),
                  selectedIcon: Icon(item.icon, color: item.color),
                  label: Text(item.label),
                ),
            ],
          ),
          const VerticalDivider(width: 1, thickness: 1),
          Expanded(
            child: Column(
              children: [
                _WorkspaceHeader(
                  destination: destination,
                  contextLabel: _contextLabel(destination),
                  coreLabel: _coreLabel,
                  compact: true,
                  onOpenCth02: _openCth02,
                  onReturnToCth: _returnFromCth02,
                  isCth02: _activeScreen.value == 'CTH-02',
                  onLogout: widget.onLogout,
                ),
                Expanded(
                  child: KeyedSubtree(
                    key: ValueKey(destination.id),
                    child: _screen(),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildWideWorkspace({required bool showInspector}) {
    final destination = _selectedDestination;
    return Scaffold(
      backgroundColor: LumenisTheme.canvas,
      body: Row(
        children: [
          _WideNavigation(
            destinations: _destinations,
            selectedIndex: _selectedIndex < 0 ? 0 : _selectedIndex,
            onSelected: _select,
          ),
          const VerticalDivider(width: 1, thickness: 1),
          Expanded(
            child: Column(
              children: [
                _WorkspaceHeader(
                  destination: destination,
                  contextLabel: _contextLabel(destination),
                  coreLabel: _coreLabel,
                  onOpenCth02: _openCth02,
                  onReturnToCth: _returnFromCth02,
                  isCth02: _activeScreen.value == 'CTH-02',
                  onLogout: widget.onLogout,
                ),
                Expanded(
                  child: KeyedSubtree(
                    key: ValueKey(destination.id),
                    child: _screen(),
                  ),
                ),
              ],
            ),
          ),
          if (showInspector) ...[
            const VerticalDivider(width: 1, thickness: 1),
            _ContextInspector(
              destination: destination,
              contextLabel: _contextLabel(destination),
              runtime: widget.runtime,
              subjects: widget.subjects,
              subjectDirectoryMessage: widget.subjectDirectoryMessage,
            ),
          ],
        ],
      ),
    );
  }

  String get _coreLabel {
    return widget.runtime['ok'] == true ? '服务已连接' : '连接状态待确认';
  }

  String _contextLabel(_WorkspaceDestination destination) {
    final rawScope = widget.runtime['subject'];
    final scope = rawScope is Map ? rawScope : const <Object?, Object?>{};
    final subjectId = scope['subject_id'];
    final brandKey = scope['brand_key'];
    final product = scope['product'];
    final domain = '${widget.runtime['domain'] ?? ''}'.toLowerCase();
    return switch (destination.id) {
      _ when _activeScreen.value == 'CTH-02' => '经营主体目录 · 当前经营主体不变',
      'CTH-01' =>
        domain != 'cth' ||
                product != 'CTH' ||
                subjectId == null ||
                '$subjectId'.trim().isEmpty
            ? '当前经营主体尚未确认'
            : '当前经营主体：$subjectId',
      'BMP-01' =>
        domain != 'zbmp' ||
                product != 'ZBMP' ||
                brandKey == null ||
                '$brandKey'.trim().isEmpty
            ? '当前品牌尚未确认'
            : '当前品牌：$brandKey',
      'AI-01' => 'AI 助理 · 输出供你审阅',
      'SH-01' => '共享服务目录',
      'SYS-01' => '系统运行状态',
      _ => destination.group,
    };
  }

  void _openCth02() => setState(() => _activeScreen.value = 'CTH-02');

  void _returnFromCth02() => setState(() => _activeScreen.value = 'CTH-01');
}

class _WideNavigation extends StatelessWidget {
  const _WideNavigation({
    required this.destinations,
    required this.selectedIndex,
    required this.onSelected,
  });

  final List<_WorkspaceDestination> destinations;
  final int selectedIndex;
  final ValueChanged<int> onSelected;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 244,
      child: DecoratedBox(
        decoration: const BoxDecoration(color: LumenisTheme.surface),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Padding(
              padding: EdgeInsets.fromLTRB(22, 24, 18, 34),
              child: _LumenisMark(),
            ),
            const Padding(
              padding: EdgeInsets.fromLTRB(22, 0, 16, 12),
              child: _SectionLabel('工作区'),
            ),
            Expanded(
              child: ListView.builder(
                padding: const EdgeInsets.symmetric(horizontal: 10),
                itemCount: destinations.length,
                itemBuilder: (context, index) => _WideDestinationRow(
                  destination: destinations[index],
                  selected: index == selectedIndex,
                  onTap: () => onSelected(index),
                ),
              ),
            ),
            const Padding(
              padding: EdgeInsets.fromLTRB(22, 16, 20, 22),
              child: Text(
                '经营 · 品牌 · 智能助理',
                style: TextStyle(color: LumenisTheme.quiet, height: 1.7),
              ),
            ),
          ],
        ),
      ),
    );
  }
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
    final foreground = selected ? destination.color : LumenisTheme.muted;
    return Padding(
      padding: const EdgeInsets.only(bottom: 5),
      child: Material(
        color: selected
            ? destination.color.withValues(alpha: 0.10)
            : Colors.transparent,
        borderRadius: BorderRadius.circular(8),
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(8),
          child: Semantics(
            button: true,
            selected: selected,
            label: '${destination.label}，${destination.group}',
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
              child: Row(
                children: [
                  Icon(destination.icon, size: 19, color: foreground),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      destination.label,
                      style: TextStyle(
                        color: selected ? LumenisTheme.foreground : foreground,
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
                        color: destination.color,
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
    required this.contextLabel,
    required this.coreLabel,
    required this.onOpenCth02,
    required this.onReturnToCth,
    required this.isCth02,
    required this.onLogout,
    this.compact = false,
  });

  final _WorkspaceDestination destination;
  final String contextLabel;
  final String coreLabel;
  final VoidCallback onOpenCth02;
  final VoidCallback onReturnToCth;
  final bool isCth02;
  final VoidCallback onLogout;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 78,
      padding: EdgeInsets.symmetric(horizontal: compact ? 24 : 34),
      decoration: const BoxDecoration(
        border: Border(bottom: BorderSide(color: LumenisTheme.line)),
      ),
      child: Row(
        children: [
          Container(
            width: 3,
            height: 32,
            decoration: BoxDecoration(
              color: destination.color,
              borderRadius: BorderRadius.circular(4),
            ),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  destination.group,
                  style: const TextStyle(
                    color: LumenisTheme.quiet,
                    fontSize: 10,
                    letterSpacing: 1.25,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 3),
                Text(
                  destination.label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: LumenisTheme.foreground,
                    fontSize: 17,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
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
              style: const TextStyle(color: LumenisTheme.muted, fontSize: 12),
            ),
          ),
          if (isCth02)
            IconButton(
              tooltip: '返回商业运营总览',
              onPressed: onReturnToCth,
              icon: const Icon(Icons.arrow_back_rounded),
              color: LumenisTheme.muted,
            )
          else if (destination.id == 'CTH-01')
            IconButton(
              tooltip: '查看经营主体目录',
              onPressed: onOpenCth02,
              icon: const Icon(Icons.account_tree_outlined),
              color: LumenisTheme.muted,
            ),
          IconButton(
            key: const ValueKey('shell/logout'),
            tooltip: '退出登录',
            onPressed: onLogout,
            icon: const Icon(Icons.logout_rounded),
            color: LumenisTheme.muted,
          ),
        ],
      ),
    );
  }
}

class _PhoneHeader extends StatelessWidget {
  const _PhoneHeader({
    required this.destination,
    required this.contextLabel,
    required this.coreLabel,
    required this.onOpenCth02,
    required this.onReturnToCth,
    required this.isCth02,
    required this.onLogout,
  });

  final _WorkspaceDestination destination;
  final String contextLabel;
  final String coreLabel;
  final VoidCallback onOpenCth02;
  final VoidCallback onReturnToCth;
  final bool isCth02;
  final VoidCallback onLogout;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(18, 12, 18, 14),
      decoration: const BoxDecoration(
        color: LumenisTheme.surface,
        border: Border(bottom: BorderSide(color: LumenisTheme.line)),
      ),
      child: Row(
        children: [
          const _LumenisMark(compact: true),
          const SizedBox(width: 13),
          Container(width: 1, height: 30, color: LumenisTheme.line),
          const SizedBox(width: 13),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  destination.label,
                  style: const TextStyle(
                    color: LumenisTheme.foreground,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  contextLabel,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: LumenisTheme.muted,
                    fontSize: 11,
                  ),
                ),
              ],
            ),
          ),
          Tooltip(
            message: coreLabel,
            child: const Icon(Icons.circle, color: LumenisTheme.quiet, size: 9),
          ),
          if (isCth02)
            IconButton(
              tooltip: '返回商业运营总览',
              onPressed: onReturnToCth,
              icon: const Icon(Icons.arrow_back_rounded, size: 20),
              color: LumenisTheme.muted,
            )
          else if (destination.id == 'CTH-01')
            IconButton(
              tooltip: '查看经营主体目录',
              onPressed: onOpenCth02,
              icon: const Icon(Icons.account_tree_outlined, size: 20),
              color: LumenisTheme.muted,
            ),
          IconButton(
            key: const ValueKey('shell/logout'),
            tooltip: '退出登录',
            onPressed: onLogout,
            icon: const Icon(Icons.logout_rounded, size: 20),
            color: LumenisTheme.muted,
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
    required this.runtime,
    required this.subjects,
    required this.subjectDirectoryMessage,
  });

  final _WorkspaceDestination destination;
  final String contextLabel;
  final Map<String, dynamic> runtime;
  final List<Map<String, dynamic>> subjects;
  final String? subjectDirectoryMessage;

  @override
  Widget build(BuildContext context) {
    final rawSubject = runtime['subject'];
    final subject = rawSubject is Map ? rawSubject : const <Object?, Object?>{};
    final domain = '${runtime['domain'] ?? ''}'.toLowerCase();
    final product = subject['product'];
    final isCthContext =
        destination.id == 'CTH-01' && domain == 'cth' && product == 'CTH';
    final productCode = product?.toString();
    final productLabel = productCode == 'ZBMP' ? 'BMP' : productCode;
    final scopeText = productLabel == null || productLabel.trim().isEmpty
        ? '当前产品尚未确认'
        : '产品：$productLabel';

    return SizedBox(
      width: 258,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(20, 28, 20, 24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const _SectionLabel('当前工作对象'),
            const SizedBox(height: 16),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: LumenisTheme.surface,
                border: Border.all(color: LumenisTheme.line),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(destination.icon, color: destination.color, size: 18),
                  const SizedBox(height: 14),
                  Text(contextLabel, style: const TextStyle(height: 1.4)),
                  const SizedBox(height: 8),
                  Text(
                    scopeText,
                    style: const TextStyle(
                      color: LumenisTheme.muted,
                      fontSize: 11,
                    ),
                  ),
                ],
              ),
            ),
            const Spacer(),
            const Text(
              '切换页面只改变查看内容，不会更改当前经营主体或品牌。',
              style: TextStyle(
                color: LumenisTheme.quiet,
                fontSize: 11,
                height: 1.6,
              ),
            ),
            if (isCthContext) ...[
              const SizedBox(height: 24),
              _SectionLabel('可浏览经营主体 · ${subjects.length}'),
              const SizedBox(height: 10),
              if (subjects.isEmpty)
                Text(
                  subjectDirectoryMessage == null
                      ? '当前没有可浏览的经营主体。'
                      : '经营主体列表暂不可用。请打开经营主体目录查看详情。',
                  style: TextStyle(
                    color: LumenisTheme.quiet,
                    fontSize: 11,
                    height: 1.6,
                  ),
                )
              else
                ...subjects.take(4).map(_RegisteredSubjectLine.new),
              if (subjects.length > 4)
                Text(
                  '另有 ${subjects.length - 4} 个经营主体',
                  style: const TextStyle(
                    color: LumenisTheme.quiet,
                    fontSize: 11,
                  ),
                ),
            ],
          ],
        ),
      ),
    );
  }
}

class _LumenisMark extends StatelessWidget {
  const _LumenisMark({this.compact = false});

  final bool compact;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: compact ? MainAxisSize.min : MainAxisSize.max,
      children: [
        Container(
          width: 34,
          height: 34,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: LumenisTheme.accent.withValues(alpha: 0.10),
            border: Border.all(
              color: LumenisTheme.accent.withValues(alpha: 0.38),
            ),
            borderRadius: BorderRadius.circular(11),
          ),
          child: const Text(
            '序',
            style: TextStyle(
              color: LumenisTheme.accent,
              fontSize: 19,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
        if (!compact) ...[
          const SizedBox(width: 11),
          const Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'LUMENIS',
                  style: TextStyle(
                    color: LumenisTheme.foreground,
                    letterSpacing: 1.15,
                    fontWeight: FontWeight.w700,
                    fontSize: 13,
                  ),
                ),
                SizedBox(height: 3),
                Text(
                  '经营与品牌工作台',
                  style: TextStyle(
                    color: LumenisTheme.quiet,
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
      style: const TextStyle(
        color: LumenisTheme.quiet,
        fontSize: 10,
        letterSpacing: 1.1,
        fontWeight: FontWeight.w600,
      ),
    );
  }
}

class _RegisteredSubjectLine extends StatelessWidget {
  const _RegisteredSubjectLine(this.subject);

  final Map<String, dynamic> subject;

  @override
  Widget build(BuildContext context) {
    final name =
        subject['name'] ??
        subject['display_name'] ??
        subject['subject_name'] ??
        subject['id'] ??
        '未命名主体';
    final identifier = subject['id'] ?? subject['subject_id'];
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 5),
      child: Text(
        identifier == null ? '$name' : '$name · $identifier',
        maxLines: 2,
        overflow: TextOverflow.ellipsis,
        style: const TextStyle(color: LumenisTheme.muted, fontSize: 11),
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
        color: LumenisTheme.quiet.withValues(alpha: 0.08),
        border: Border.all(color: LumenisTheme.quiet.withValues(alpha: 0.22)),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.circle, color: LumenisTheme.quiet, size: 6),
          const SizedBox(width: 7),
          Text(
            label,
            style: const TextStyle(color: LumenisTheme.muted, fontSize: 10),
          ),
        ],
      ),
    );
  }
}

class _WorkspaceDestination {
  const _WorkspaceDestination({
    required this.id,
    required this.label,
    required this.mobileLabel,
    required this.group,
    required this.icon,
    required this.color,
  });

  final String id;
  final String label;
  final String mobileLabel;
  final String group;
  final IconData icon;
  final Color color;
}
