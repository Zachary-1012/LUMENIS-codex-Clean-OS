import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'lumenis_theme.dart';

class LumenisSplitHandle extends StatefulWidget {
  const LumenisSplitHandle({
    required this.label,
    required this.onDelta,
    required this.onReset,
    this.axis = Axis.horizontal,
    super.key,
  });

  final String label;
  final ValueChanged<double> onDelta;
  final VoidCallback onReset;
  final Axis axis;

  @override
  State<LumenisSplitHandle> createState() => _LumenisSplitHandleState();
}

class _LumenisSplitHandleState extends State<LumenisSplitHandle> {
  bool _hover = false;
  bool _focus = false;
  bool _dragging = false;

  @override
  Widget build(BuildContext context) {
    final horizontal = widget.axis == Axis.horizontal;
    final palette = LumenisTheme.of(context);
    final active = _hover || _focus || _dragging;
    return Semantics(
      label: widget.label,
      onIncrease: () => widget.onDelta(24),
      onDecrease: () => widget.onDelta(-24),
      child: FocusableActionDetector(
        mouseCursor: horizontal
            ? SystemMouseCursors.resizeColumn
            : SystemMouseCursors.resizeRow,
        onShowFocusHighlight: (value) => setState(() => _focus = value),
        onShowHoverHighlight: (value) => setState(() => _hover = value),
        shortcuts: {
          SingleActivator(
            horizontal
                ? LogicalKeyboardKey.arrowRight
                : LogicalKeyboardKey.arrowDown,
          ): const _ResizePaneIntent(
            24,
          ),
          SingleActivator(
            horizontal
                ? LogicalKeyboardKey.arrowLeft
                : LogicalKeyboardKey.arrowUp,
          ): const _ResizePaneIntent(
            -24,
          ),
          const SingleActivator(LogicalKeyboardKey.home):
              const _ResetPaneIntent(),
        },
        actions: {
          _ResizePaneIntent: CallbackAction<_ResizePaneIntent>(
            onInvoke: (intent) {
              widget.onDelta(intent.delta);
              return null;
            },
          ),
          _ResetPaneIntent: CallbackAction<_ResetPaneIntent>(
            onInvoke: (_) {
              widget.onReset();
              return null;
            },
          ),
        },
        child: GestureDetector(
          behavior: HitTestBehavior.opaque,
          onDoubleTap: widget.onReset,
          onHorizontalDragStart: horizontal
              ? (_) => setState(() => _dragging = true)
              : null,
          onHorizontalDragUpdate: horizontal
              ? (details) => widget.onDelta(details.delta.dx)
              : null,
          onHorizontalDragEnd: horizontal
              ? (_) => setState(() => _dragging = false)
              : null,
          onHorizontalDragCancel: horizontal
              ? () => setState(() => _dragging = false)
              : null,
          onVerticalDragStart: horizontal
              ? null
              : (_) => setState(() => _dragging = true),
          onVerticalDragUpdate: horizontal
              ? null
              : (details) => widget.onDelta(details.delta.dy),
          onVerticalDragEnd: horizontal
              ? null
              : (_) => setState(() => _dragging = false),
          onVerticalDragCancel: horizontal
              ? null
              : () => setState(() => _dragging = false),
          child: Tooltip(
            message: widget.label,
            child: AnimatedContainer(
              duration: MediaQuery.disableAnimationsOf(context)
                  ? Duration.zero
                  : const Duration(milliseconds: 90),
              width: horizontal ? 12 : null,
              height: horizontal ? null : 12,
              color: active
                  ? palette.accent.withValues(alpha: .12)
                  : palette.canvas,
              alignment: Alignment.center,
              child: Container(
                width: horizontal ? 2 : 32,
                height: horizontal ? 32 : 2,
                color: active ? palette.accent : palette.line,
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _ResizePaneIntent extends Intent {
  const _ResizePaneIntent(this.delta);
  final double delta;
}

class _ResetPaneIntent extends Intent {
  const _ResetPaneIntent();
}
