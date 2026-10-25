import 'package:flutter/material.dart';

import 'lumenis_icon.dart';
import 'lumenis_theme.dart';

class LumenisWorkObjectAction extends StatefulWidget {
  const LumenisWorkObjectAction({
    required this.object,
    required this.label,
    required this.onPressed,
    this.large = false,
    super.key,
  });

  final LumenisWorkObject object;
  final String label;
  final VoidCallback? onPressed;
  final bool large;

  @override
  State<LumenisWorkObjectAction> createState() =>
      _LumenisWorkObjectActionState();
}

class _LumenisWorkObjectActionState extends State<LumenisWorkObjectAction> {
  bool _hover = false, _focused = false, _pressed = false;

  @override
  Widget build(BuildContext context) {
    final colors = LumenisTheme.of(context);
    final engaged = widget.onPressed != null && (_hover || _focused);
    final reduce = MediaQuery.disableAnimationsOf(context);
    final accent = switch (widget.object) {
      LumenisWorkObject.book => colors.cth,
      LumenisWorkObject.paper => colors.shared,
      LumenisWorkObject.film => colors.bmp,
      LumenisWorkObject.microphone => colors.ai,
    };
    final extent = widget.large ? 140.0 : 84.0;
    return Semantics(
      button: true,
      enabled: widget.onPressed != null,
      label: widget.label,
      excludeSemantics: true,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: widget.onPressed,
          onHover: (value) => setState(() => _hover = value),
          onFocusChange: (value) => setState(() => _focused = value),
          onHighlightChanged: (value) => setState(() => _pressed = value),
          customBorder: const LumenisPixelBorder(step: 4),
          child: AnimatedContainer(
            duration: LumenisMotion.of(context, LumenisMotion.feedback),
            padding: EdgeInsets.fromLTRB(8, widget.large ? 12 : 4, 8, 10),
            decoration: ShapeDecoration(
              shape: LumenisPixelBorder(
                side: BorderSide(
                  color: _focused ? colors.accentStrong : Colors.transparent,
                  width: 2,
                ),
                step: 4,
              ),
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                AnimatedSlide(
                  offset: reduce
                      ? Offset.zero
                      : Offset(
                          0,
                          _pressed
                              ? .025
                              : engaged
                              ? -.06
                              : 0,
                        ),
                  duration: LumenisMotion.of(context, LumenisMotion.selection),
                  curve: Curves.easeOutCubic,
                  child: AnimatedRotation(
                    turns: reduce || !engaged || _pressed ? 0 : -.012,
                    duration: LumenisMotion.of(
                      context,
                      LumenisMotion.selection,
                    ),
                    child: CustomPaint(
                      size: Size(extent, extent * 92 / 112),
                      painter: LumenisWorkObjectPainter(
                        widget.object,
                        accent,
                        colors,
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  widget.label,
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: widget.large ? 16 : 13,
                    height: 1.4,
                    fontWeight: engaged ? FontWeight.w600 : FontWeight.w400,
                    color: widget.onPressed == null
                        ? colors.quiet
                        : colors.foreground,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
