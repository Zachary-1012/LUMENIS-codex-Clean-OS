import 'package:flutter/material.dart';

import 'lumenis_theme.dart';
import 'lumenis_icon.dart';

enum LumenisPlant { gypsophila, orchid, spiderLily, palm, grape, jasmine }

class LumenisDomainGlyph extends StatelessWidget {
  const LumenisDomainGlyph({
    required this.domain,
    required this.fallback,
    this.size = 28,
    this.color,
    super.key,
  });

  final String domain;
  final IconData fallback;
  final double size;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    final plant = switch (domain.split('-').first.toUpperCase()) {
      'CTH' => LumenisPlant.orchid,
      'BMP' || 'ZBMP' => LumenisPlant.spiderLily,
      'SH' || 'SHARED' => LumenisPlant.palm,
      'SYS' || 'SYSTEM' => LumenisPlant.grape,
      'AI' => LumenisPlant.jasmine,
      _ => null,
    };
    final icon = LumenisIcon(fallback, size: size * .75, color: color);
    return SizedBox.square(
      dimension: size,
      child: plant == null
          ? icon
          : LumenisBotanical(plant: plant, size: size, fallback: icon),
    );
  }
}

class LumenisBotanicalScope extends InheritedWidget {
  const LumenisBotanicalScope({
    super.key,
    required this.enabled,
    required super.child,
  });

  final bool enabled;

  static bool enabledOf(BuildContext context) =>
      context
          .dependOnInheritedWidgetOfExactType<LumenisBotanicalScope>()
          ?.enabled ??
      true;

  @override
  bool updateShouldNotify(LumenisBotanicalScope oldWidget) =>
      enabled != oldWidget.enabled;
}

class LumenisBotanical extends StatelessWidget {
  const LumenisBotanical({
    super.key,
    this.plant = LumenisPlant.gypsophila,
    this.size = 48,
    this.monochrome = false,
    this.fallback,
  });

  final LumenisPlant plant;
  final double size;
  final bool monochrome;
  final Widget? fallback;

  @override
  Widget build(BuildContext context) =>
      plant != LumenisPlant.gypsophila &&
          !LumenisBotanicalScope.enabledOf(context)
      ? fallback ?? const SizedBox.shrink()
      : ExcludeSemantics(
          child: SizedBox.square(
            dimension: size,
            child: CustomPaint(
              painter: LumenisBotanicalPainter(
                plant: plant,
                palette: LumenisTheme.of(context),
                monochrome: monochrome,
              ),
            ),
          ),
        );
}

class LumenisBotanicalPainter extends CustomPainter {
  const LumenisBotanicalPainter({
    required this.plant,
    required this.palette,
    this.monochrome = false,
  });

  final LumenisPlant plant;
  final LumenisPalette palette;
  final bool monochrome;

  @override
  void paint(Canvas canvas, Size size) {
    canvas.save();
    canvas.scale(size.width / 32, size.height / 32);
    final paint = Paint()..isAntiAlias = false;
    final stem = palette.accentStrong;
    final petal = monochrome ? stem : palette.surfaceRaised;
    void pixel(int x, int y, Color color, [double width = 1]) {
      paint.color = color;
      canvas.drawRect(
        Rect.fromLTWH(x.toDouble(), y.toDouble(), width, width),
        paint,
      );
    }

    void line(int x0, int y0, int x1, int y1, Color color) {
      final dx = (x1 - x0).abs();
      final dy = -(y1 - y0).abs();
      final sx = x0 < x1 ? 1 : -1;
      final sy = y0 < y1 ? 1 : -1;
      var error = dx + dy;
      while (true) {
        pixel(x0, y0, color);
        if (x0 == x1 && y0 == y1) break;
        final twice = error * 2;
        if (twice >= dy) {
          error += dy;
          x0 += sx;
        }
        if (twice <= dx) {
          error += dx;
          y0 += sy;
        }
      }
    }

    void leaf(List<Offset> points, Color color) {
      final path = Path()..addPolygon(points, true);
      paint.color = color;
      canvas.drawPath(path, paint);
    }

    void flower(int x, int y, Color color, [int r = 1]) {
      pixel(x - r, y - 1, stem, (r + 1).toDouble());
      pixel(x, y - r, stem, (r + 1).toDouble());
      pixel(x - r, y, color, r.toDouble());
      pixel(x + 1, y, color, r.toDouble());
      pixel(x, y - r, color, r.toDouble());
      pixel(x, y + 1, color, r.toDouble());
      pixel(x, y, monochrome ? stem : palette.cth);
    }

    switch (plant) {
      case LumenisPlant.gypsophila:
        for (final (x, y, ax, ay) in const [
          (5, 10, 12, 20),
          (8, 5, 12, 14),
          (14, 4, 16, 17),
          (22, 6, 18, 20),
          (27, 12, 22, 20),
          (6, 19, 13, 23),
          (24, 21, 19, 25),
          (18, 10, 16, 17),
          (12, 13, 15, 21),
        ]) {
          line(16, 29, ax, ay, stem);
          line(ax, ay, x, y, stem);
          flower(x, y, petal);
        }
      case LumenisPlant.orchid:
        line(15, 29, 17, 10, stem);
        leaf(const [
          Offset(15, 29),
          Offset(5, 20),
          Offset(9, 21),
          Offset(15, 26),
        ], stem);
        leaf(const [
          Offset(15, 29),
          Offset(26, 20),
          Offset(24, 25),
          Offset(18, 29),
        ], stem);
        final ink = monochrome ? stem : palette.ai;
        final glow = monochrome ? stem : Color.lerp(ink, palette.surface, .55)!;
        leaf(const [
          Offset(15, 14),
          Offset(9, 5),
          Offset(5, 6),
          Offset(6, 11),
          Offset(12, 15),
        ], ink);
        leaf(const [
          Offset(17, 14),
          Offset(22, 4),
          Offset(26, 6),
          Offset(25, 11),
          Offset(19, 16),
        ], ink);
        leaf(const [
          Offset(14, 14),
          Offset(5, 12),
          Offset(2, 16),
          Offset(7, 19),
          Offset(14, 17),
        ], glow);
        leaf(const [
          Offset(18, 14),
          Offset(27, 12),
          Offset(30, 16),
          Offset(25, 19),
          Offset(18, 17),
        ], glow);
        leaf(const [
          Offset(15, 13),
          Offset(13, 5),
          Offset(16, 2),
          Offset(19, 5),
          Offset(17, 13),
        ], glow);
        leaf(const [
          Offset(14, 17),
          Offset(12, 21),
          Offset(16, 24),
          Offset(20, 21),
          Offset(18, 17),
        ], ink);
        flower(16, 17, petal, 1);
      case LumenisPlant.spiderLily:
        line(16, 29, 16, 14, stem);
        final ink = monochrome ? stem : palette.danger;
        for (final (x, y) in const [
          (5, 8),
          (10, 4),
          (17, 3),
          (24, 6),
          (28, 12),
          (5, 17),
          (26, 20),
        ]) {
          line(16, 15, x, y, ink);
          line(x, y, x + (x < 16 ? 2 : -2), y - 2, ink);
          pixel(x, y, petal);
        }
        flower(16, 13, ink, 2);
      case LumenisPlant.palm:
        final trunk = monochrome ? stem : palette.cth;
        leaf(const [
          Offset(18, 30),
          Offset(21, 30),
          Offset(18, 20),
          Offset(16, 12),
          Offset(14, 12),
          Offset(16, 22),
        ], trunk);
        final crown = monochrome ? stem : palette.positive;
        for (final (x, y) in const [
          (3, 9),
          (4, 16),
          (10, 3),
          (20, 4),
          (28, 10),
          (26, 18),
        ]) {
          leaf([
            const Offset(15, 11),
            Offset(x.toDouble(), y.toDouble()),
            Offset(x.toDouble(), y + 3.0),
            Offset((x + 15) / 2, (y + 14) / 2),
          ], crown);
          line(15, 11, x, y, stem);
        }
        pixel(14, 13, monochrome ? stem : palette.cth, 3);
        pixel(18, 12, monochrome ? stem : palette.cth, 3);
      case LumenisPlant.grape:
        line(16, 3, 16, 11, stem);
        line(16, 5, 25, 4, stem);
        line(16, 6, 9, 3, stem);
        line(9, 3, 5, 7, stem);
        line(5, 7, 12, 9, stem);
        line(12, 9, 16, 6, stem);
        final ink = monochrome ? stem : palette.ai;
        for (final (x, y) in const [
          (10, 11),
          (17, 11),
          (7, 16),
          (14, 16),
          (21, 16),
          (11, 21),
          (18, 21),
          (15, 26),
        ]) {
          pixel(x, y + 1, ink, 4);
          pixel(x + 1, y, ink, 2);
          pixel(x + 1, y + 4, ink, 2);
          pixel(
            x + 1,
            y + 1,
            monochrome ? stem : Color.lerp(ink, palette.surface, .55)!,
            2,
          );
        }
      case LumenisPlant.jasmine:
        line(16, 29, 16, 14, stem);
        leaf(const [
          Offset(16, 27),
          Offset(5, 18),
          Offset(6, 24),
          Offset(12, 28),
        ], stem);
        leaf(const [
          Offset(16, 24),
          Offset(27, 16),
          Offset(26, 22),
          Offset(20, 26),
        ], stem);
        for (final (x, y) in const [
          (16, 5),
          (8, 10),
          (23, 10),
          (11, 18),
          (21, 18),
        ]) {
          leaf([
            const Offset(16, 12),
            Offset(x - 2.0, y - 1.0),
            Offset(x.toDouble(), y - 3.0),
            Offset(x + 3.0, y.toDouble()),
            Offset(x + 1.0, y + 3.0),
          ], stem);
          leaf([
            const Offset(16, 12),
            Offset(x - 1.0, y.toDouble()),
            Offset(x.toDouble(), y - 2.0),
            Offset(x + 2.0, y.toDouble()),
            Offset(x.toDouble(), y + 2.0),
          ], petal);
        }
        pixel(15, 11, monochrome ? stem : palette.caution, 3);
    }
    canvas.restore();
  }

  @override
  bool shouldRepaint(LumenisBotanicalPainter oldDelegate) =>
      oldDelegate.plant != plant ||
      oldDelegate.palette != palette ||
      oldDelegate.monochrome != monochrome;
}

class LumenisBotanicalField extends StatelessWidget {
  const LumenisBotanicalField({super.key, this.height = 148});

  final double height;

  @override
  Widget build(BuildContext context) =>
      !LumenisBotanicalScope.enabledOf(context)
      ? const SizedBox.shrink()
      : ExcludeSemantics(
          child: IgnorePointer(
            child: SizedBox(
              height: height,
              child: RepaintBoundary(
                child: CustomPaint(
                  painter: _BotanicalFieldPainter(LumenisTheme.of(context)),
                  child: const SizedBox.expand(),
                ),
              ),
            ),
          ),
        );
}

class _BotanicalFieldPainter extends CustomPainter {
  const _BotanicalFieldPainter(this.palette);

  final LumenisPalette palette;

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..isAntiAlias = false
      ..color = palette.line.withValues(alpha: .35);
    for (var x = 8.0; x < size.width; x += 16) {
      for (var y = 8.0; y < size.height - 12; y += 16) {
        canvas.drawRect(Rect.fromLTWH(x, y, 1, 1), paint);
      }
    }
    final plants = [
      (LumenisPlant.orchid, .07, .57),
      (LumenisPlant.palm, .26, .75),
      (LumenisPlant.gypsophila, .48, 1.0),
      (LumenisPlant.jasmine, .72, .65),
      (LumenisPlant.spiderLily, .88, .49),
    ];
    for (final (plant, position, scale) in plants) {
      final extent = size.height * scale;
      final left = (size.width * position - extent / 2).clamp(
        0.0,
        (size.width - extent).clamp(0.0, size.width),
      );
      canvas.save();
      canvas.translate(left, size.height - extent - 6);
      LumenisBotanicalPainter(
        plant: plant,
        palette: palette,
      ).paint(canvas, Size.square(extent));
      canvas.restore();
    }
    paint.color = palette.accent.withValues(alpha: .5);
    canvas.drawRect(Rect.fromLTWH(0, size.height - 2, size.width, 1), paint);
    for (var x = 0.0; x < size.width; x += 8) {
      canvas.drawRect(Rect.fromLTWH(x, size.height - 5, 2, 2), paint);
    }
  }

  @override
  bool shouldRepaint(_BotanicalFieldPainter oldDelegate) =>
      oldDelegate.palette != palette;
}
