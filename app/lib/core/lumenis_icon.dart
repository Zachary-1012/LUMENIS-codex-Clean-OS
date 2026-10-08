import 'package:flutter/material.dart';

import 'lumenis_icon_geometry.dart';

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
