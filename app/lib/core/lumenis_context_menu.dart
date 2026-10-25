import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'lumenis_icon.dart';

class LumenisContextAction {
  const LumenisContextAction(this.label, this.onSelected, {this.icon});
  final String label;
  final VoidCallback? onSelected;
  final IconData? icon;
}

class LumenisContextMenu extends StatelessWidget {
  const LumenisContextMenu({
    required this.actions,
    required this.child,
    super.key,
  });

  final List<LumenisContextAction> actions;
  final Widget child;

  @override
  Widget build(BuildContext context) => MenuAnchor(
    consumeOutsideTap: true,
    menuChildren: [
      for (final action in actions)
        MenuItemButton(
          autofocus:
              actions.indexOf(action) ==
              actions.indexWhere((item) => item.onSelected != null),
          onPressed: action.onSelected,
          leadingIcon: action.icon == null
              ? null
              : LumenisIcon(action.icon, size: 18),
          child: Text(action.label),
        ),
    ],
    builder: (context, controller, _) => CallbackShortcuts(
      bindings: {
        const SingleActivator(LogicalKeyboardKey.f10, shift: true): () =>
            controller.open(),
        const SingleActivator(LogicalKeyboardKey.contextMenu): () =>
            controller.open(),
      },
      child: GestureDetector(
        onSecondaryTapDown: (event) =>
            controller.open(position: event.localPosition),
        onLongPressStart: (event) =>
            controller.open(position: event.localPosition),
        child: child,
      ),
    ),
  );
}
