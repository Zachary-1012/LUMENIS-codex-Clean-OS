import 'package:flutter/material.dart';

import 'lumenis_icon_geometry.dart';
import 'lumenis_theme.dart';

/// Uses the existing disclosure controller; the tile retains tap and semantics.
class LumenisExpansionIndicator extends StatelessWidget {
  const LumenisExpansionIndicator({super.key});

  @override
  Widget build(BuildContext context) {
    final controller = ExpansibleController.of(context);
    return ListenableBuilder(
      listenable: controller,
      builder: (context, child) => AnimatedRotation(
        turns: controller.isExpanded ? .5 : 0,
        duration: MediaQuery.disableAnimationsOf(context)
            ? Duration.zero
            : const Duration(milliseconds: 200),
        curve: Curves.easeInOut,
        child: child,
      ),
      child: const LumenisIcon(Icons.expand_more_rounded, size: 18),
    );
  }
}

/// Draws the reviewed LUMENIS vector for a supported Material icon identity.
///
/// The inherited [Icon.icon] remains the symbol identity, so existing
/// [IconButton]s, semantics, and `find.byIcon` callers keep their behavior.
/// Unknown symbols and font styling this vector renderer does not implement
/// deliberately fall back to Flutter's native [Icon] renderer.
class LumenisIcon extends Icon {
  static const IconThemeData _nativeDefaultIconTheme = IconThemeData.fallback();

  const LumenisIcon(
    super.icon, {
    super.key,
    super.size,
    super.fill,
    super.weight,
    super.grade,
    super.opticalSize,
    super.color,
    super.shadows,
    super.semanticLabel,
    super.textDirection,
    super.applyTextScaling,
    super.blendMode,
    super.fontWeight,
  });

  /// Current Material icon names and their reviewed LUMENIS geometry aliases.
  static const Map<String, String> supportedSymbols = lumenisIconAliases;

  /// The [IconData] identity for each supported Material symbol.
  static const Map<String, IconData> supportedIcons = lumenisIconData;

  static final Map<IconData, String> _glyphByIcon =
      Map<IconData, String>.unmodifiable({
        for (final entry in lumenisIconData.entries)
          entry.value: lumenisIconAliases[entry.key]!,
      });

  /// Returns the authored geometry name for a supported symbol identity.
  static String? glyphNameFor(IconData? icon) =>
      icon == null ? null : _glyphByIcon[icon];

  /// Returns geometry by either a current Material symbol name or glyph name.
  static LumenisIconGeometry? geometryForSymbol(String symbol) {
    final glyph = supportedSymbols[symbol] ?? symbol;
    return lumenisIconGeometry[glyph];
  }

  @override
  Widget build(BuildContext context) {
    assert(textDirection != null || debugCheckHasDirectionality(context));

    final iconData = icon;
    final iconTheme = IconTheme.of(context);
    final glyphName = glyphNameFor(iconData);
    final geometry = glyphName == null ? null : lumenisIconGeometry[glyphName];

    // Preserve Flutter's variable-font axes, font weight, shadows, blend mode,
    // and future symbol behavior whenever the fixed vector renderer cannot
    // represent the requested native Icon styling exactly.
    if (iconData == null ||
        geometry == null ||
        _requiresNativeFontStyle(iconTheme)) {
      return super.build(context);
    }

    final applyScaling =
        applyTextScaling ?? iconTheme.applyTextScaling ?? false;
    final requestedSize = size ?? iconTheme.size ?? kDefaultFontSize;
    final iconSize = applyScaling
        ? MediaQuery.textScalerOf(context).scale(requestedSize)
        : requestedSize;
    final resolvedColor = color ?? iconTheme.color!;
    final opacity = iconTheme.opacity ?? 1.0;
    final effectiveColor = resolvedColor.withValues(
      alpha: resolvedColor.a * opacity,
    );
    final direction = textDirection ?? Directionality.of(context);

    Widget paintedIcon = CustomPaint(
      size: Size(iconSize, iconSize),
      painter: LumenisIconPainter(geometry: geometry, color: effectiveColor),
    );
    if (iconData.matchTextDirection && direction == TextDirection.rtl) {
      paintedIcon = Transform(
        transform: Matrix4.identity()..scaleByDouble(-1.0, 1.0, 1.0, 1),
        alignment: Alignment.center,
        transformHitTests: false,
        child: paintedIcon,
      );
    }

    return Semantics(
      label: semanticLabel,
      child: ExcludeSemantics(
        child: SizedBox(
          width: iconSize,
          height: iconSize,
          child: Center(child: paintedIcon),
        ),
      ),
    );
  }

  bool _requiresNativeFontStyle(IconThemeData iconTheme) =>
      fill != null ||
      weight != null ||
      grade != null ||
      opticalSize != null ||
      (shadows ?? iconTheme.shadows) != null ||
      blendMode != null ||
      fontWeight != null ||
      iconTheme.fill != _nativeDefaultIconTheme.fill ||
      iconTheme.weight != _nativeDefaultIconTheme.weight ||
      iconTheme.grade != _nativeDefaultIconTheme.grade ||
      iconTheme.opticalSize != _nativeDefaultIconTheme.opticalSize;
}

/// Paints one cached 24-unit LUMENIS geometry group.
class LumenisIconPainter extends CustomPainter {
  LumenisIconPainter({required this.geometry, required this.color})
    : _strokePaint = Paint()
        ..color = color
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.6
        ..strokeCap = StrokeCap.round
        ..strokeJoin = StrokeJoin.round,
      _fillPaint = Paint()
        ..color = color
        ..style = PaintingStyle.fill;

  static const double drawingSize = 24;

  final LumenisIconGeometry geometry;
  final Color color;
  final Paint _strokePaint;
  final Paint _fillPaint;

  @override
  void paint(Canvas canvas, Size size) {
    canvas.save();
    canvas.scale(size.width / drawingSize, size.height / drawingSize);
    geometry.paint(canvas, _strokePaint, _fillPaint);
    canvas.restore();
  }

  @override
  bool shouldRepaint(LumenisIconPainter oldDelegate) =>
      geometry != oldDelegate.geometry || color != oldDelegate.color;
}

/// Original task objects shared by Home and the existing creation workspace.
enum LumenisWorkObject { book, paper, film, microphone }

class LumenisWorkObjectPainter extends CustomPainter {
  const LumenisWorkObjectPainter(this.object, this.accent, this.palette);
  final LumenisWorkObject object;
  final Color accent;
  final LumenisPalette palette;
  @override
  void paint(Canvas canvas, Size size) {
    canvas.save();
    canvas.scale(size.width / 112, size.height / 92);
    final ink = palette.foreground;
    final sheet = palette.surface;
    final paint = Paint()..isAntiAlias = false;
    void block(double x, double y, double w, double h, Color color) {
      canvas.drawRect(Rect.fromLTWH(x, y, w, h), paint..color = color);
    }

    block(24, 77, 65, 3, palette.line);
    switch (object) {
      case LumenisWorkObject.book:
        block(26, 14, 58, 60, ink);
        block(29, 17, 52, 54, accent);
        block(33, 17, 3, 54, ink);
        block(41, 25, 32, 24, sheet);
        block(46, 31, 22, 2, accent);
        block(46, 38, 16, 2, accent);
        block(36, 66, 45, 5, sheet);
      case LumenisWorkObject.paper:
        block(25, 18, 54, 58, palette.line);
        block(31, 11, 54, 60, ink);
        block(34, 14, 48, 54, sheet);
        for (var row = 0; row < 5; row++) {
          block(
            42,
            25 + row * 7,
            row == 4 ? 18 : 30,
            2,
            row == 0 ? accent : palette.line,
          );
        }
        block(73, 42, 5, 28, accent);
        block(74, 70, 3, 4, ink);
      case LumenisWorkObject.film:
        block(20, 20, 74, 55, ink);
        block(23, 33, 68, 39, accent);
        for (var column = 0; column < 5; column++) {
          block(24 + column * 14, 24, 8, 5, sheet);
        }
        block(49, 43, 4, 20, sheet);
        block(53, 47, 5, 12, sheet);
        block(58, 50, 5, 6, sheet);
      case LumenisWorkObject.microphone:
        block(45, 10, 22, 46, ink);
        block(42, 15, 28, 35, accent);
        for (var row = 0; row < 6; row++) {
          block(48, 19 + row * 5, 16, 2, sheet);
        }
        block(35, 36, 3, 22, ink);
        block(74, 36, 3, 22, ink);
        block(38, 58, 36, 4, ink);
        block(54, 62, 4, 13, ink);
        block(40, 75, 32, 3, ink);
    }
    canvas.restore();
  }

  @override
  bool shouldRepaint(LumenisWorkObjectPainter old) =>
      old.object != object || old.accent != accent || old.palette != palette;
}
