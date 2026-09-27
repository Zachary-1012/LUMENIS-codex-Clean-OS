import 'package:flutter/material.dart';

/// Immutable neutral colors resolved from the nearest Material theme.
@immutable
class LumenisPalette extends ThemeExtension<LumenisPalette> {
  const LumenisPalette({
    required this.canvas,
    required this.surface,
    required this.surfaceRaised,
    required this.line,
    required this.foreground,
    required this.muted,
    required this.quiet,
    required this.accent,
    required this.accentStrong,
    required this.brightness,
    this.contrastBackground,
  });

  final Color canvas;
  final Color surface;
  final Color surfaceRaised;
  final Color line;
  final Color foreground;
  final Color muted;
  final Color quiet;
  final Color accent;
  final Color accentStrong;
  final Brightness brightness;

  /// Worst-case backdrop after wallpaper protection; null for other modes.
  final Color? contrastBackground;

  Color get cth => _semantic(LumenisTheme.cth);
  Color get bmp => _semantic(LumenisTheme.bmp);
  Color get ai => _semantic(LumenisTheme.ai);
  Color get shared => _semantic(LumenisTheme.shared);
  Color get system => _semantic(LumenisTheme.system);
  Color get positive => _semantic(LumenisTheme.positive);
  Color get caution => _semantic(LumenisTheme.caution);
  Color get danger => _semantic(LumenisTheme.danger);

  Color _semantic(Color source) {
    final color = brightness == Brightness.dark
        ? Color.lerp(source, const Color(0xFFFFFFFF), 0.35)!
        : source;
    final background = contrastBackground;
    if (background == null ||
        LumenisTheme._contrast(color, background) >= 4.5) {
      return color;
    }
    var lower = 0.0;
    var upper = 1.0;
    for (var step = 0; step < 16; step++) {
      final middle = (lower + upper) / 2;
      if (LumenisTheme._contrast(
            Color.lerp(color, foreground, middle)!,
            background,
          ) >=
          4.5) {
        upper = middle;
      } else {
        lower = middle;
      }
    }
    return Color.lerp(color, foreground, (upper + 1 / 255).clamp(0, 1))!;
  }

  /// Resolves the legacy static destination color into this palette.
  Color resolveSemantic(Color source) {
    if (source == LumenisTheme.cth) return cth;
    if (source == LumenisTheme.bmp) return bmp;
    if (source == LumenisTheme.ai) return ai;
    if (source == LumenisTheme.shared) return shared;
    if (source == LumenisTheme.system) return system;
    if (source == LumenisTheme.positive) return positive;
    if (source == LumenisTheme.caution) return caution;
    if (source == LumenisTheme.danger) return danger;
    return source;
  }

  @override
  LumenisPalette copyWith({
    Color? canvas,
    Color? surface,
    Color? surfaceRaised,
    Color? line,
    Color? foreground,
    Color? muted,
    Color? quiet,
    Color? accent,
    Color? accentStrong,
    Brightness? brightness,
    Color? contrastBackground,
  }) => LumenisPalette(
    canvas: canvas ?? this.canvas,
    surface: surface ?? this.surface,
    surfaceRaised: surfaceRaised ?? this.surfaceRaised,
    line: line ?? this.line,
    foreground: foreground ?? this.foreground,
    muted: muted ?? this.muted,
    quiet: quiet ?? this.quiet,
    accent: accent ?? this.accent,
    accentStrong: accentStrong ?? this.accentStrong,
    brightness: brightness ?? this.brightness,
    contrastBackground: contrastBackground ?? this.contrastBackground,
  );

  @override
  LumenisPalette lerp(ThemeExtension<LumenisPalette>? other, double t) {
    if (other is! LumenisPalette) return this;
    return LumenisPalette(
      canvas: Color.lerp(canvas, other.canvas, t) ?? canvas,
      surface: Color.lerp(surface, other.surface, t) ?? surface,
      surfaceRaised:
          Color.lerp(surfaceRaised, other.surfaceRaised, t) ?? surfaceRaised,
      line: Color.lerp(line, other.line, t) ?? line,
      foreground: Color.lerp(foreground, other.foreground, t) ?? foreground,
      muted: Color.lerp(muted, other.muted, t) ?? muted,
      quiet: Color.lerp(quiet, other.quiet, t) ?? quiet,
      accent: Color.lerp(accent, other.accent, t) ?? accent,
      accentStrong:
          Color.lerp(accentStrong, other.accentStrong, t) ?? accentStrong,
      brightness: t < 0.5 ? brightness : other.brightness,
      contrastBackground: Color.lerp(
        contrastBackground,
        other.contrastBackground,
        t,
      ),
    );
  }
}

/// App-level semantic colors. Screen layouts remain owned by their workflows.
abstract final class LumenisTheme {
  // Compatibility tokens for older callers and semantic-only code. New
  // neutral color consumers should resolve LumenisTheme.of(context).
  static const canvas = Color(0xFFFAF9F7);
  static const surface = Color(0xFFFFFFFF);
  static const surfaceRaised = Color(0xFFF1F0EE);
  static const line = Color(0xFFE3E1DE);
  static const foreground = Color(0xFF202124);
  static const muted = Color(0xFF626367);
  static const quiet = Color(0xFF6D6E73);
  static const accent = Color(0xFF242529);
  static const accentStrong = Color(0xFF121315);

  /// The least neutral tint that keeps the current text roles readable over
  /// any image pixel. Using the worst possible region avoids sampling misses
  /// on small highlights, dark edges, resized images, and mixed exposures.
  static Color wallpaperScrim(LumenisPalette palette) {
    final dark = palette.brightness == Brightness.dark;
    final tint = dark ? Colors.black : Colors.white;
    final worstRegion = dark ? Colors.white : Colors.black;
    bool readable(double opacity) {
      final background = Color.alphaBlend(
        tint.withValues(alpha: opacity),
        worstRegion,
      );
      return [
        palette.foreground,
        palette.muted,
        palette.quiet,
        palette.accent,
        palette.accentStrong,
      ].every((ink) => _contrast(ink, background) >= 4.5);
    }

    var lower = 0.0;
    var upper = 1.0;
    for (var step = 0; step < 16; step++) {
      final middle = (lower + upper) / 2;
      if (readable(middle)) {
        upper = middle;
      } else {
        lower = middle;
      }
    }
    // Keep a one-channel rounding margin for the rasterized background.
    return tint.withValues(alpha: (upper + 1 / 255).clamp(0, 1));
  }

  static double _contrast(Color ink, Color background) {
    final text = Color.alphaBlend(ink, background).computeLuminance();
    final paper = background.computeLuminance();
    return text > paper
        ? (text + .05) / (paper + .05)
        : (paper + .05) / (text + .05);
  }

  static const cth = Color(0xFF865523);
  static const bmp = Color(0xFF326D66);
  static const ai = Color(0xFF6C548E);
  static const shared = Color(0xFF99543D);
  static const system = Color(0xFF42677D);

  static const positive = Color(0xFF287F60);
  static const caution = Color(0xFF8F601C);
  static const danger = Color(0xFFB74638);

  static const lightPalette = LumenisPalette(
    canvas: canvas,
    surface: surface,
    surfaceRaised: surfaceRaised,
    line: line,
    foreground: foreground,
    muted: muted,
    quiet: quiet,
    accent: accent,
    accentStrong: accentStrong,
    brightness: Brightness.light,
  );

  static const darkPalette = LumenisPalette(
    canvas: Color(0xFF151619),
    surface: Color(0xFF202226),
    surfaceRaised: Color(0xFF2A2D32),
    line: Color(0xFF41464D),
    foreground: Color(0xFFF2F1EE),
    muted: Color(0xFFB6B8BC),
    quiet: Color(0xFF979BA2),
    accent: Color(0xFFF2F1EE),
    accentStrong: Color(0xFFFFFFFF),
    brightness: Brightness.dark,
  );

  static LumenisPalette of(BuildContext context) =>
      Theme.of(context).extension<LumenisPalette>() ?? lightPalette;

  static ThemeData get light => forPalette(lightPalette);
  static ThemeData get dark => forPalette(darkPalette);

  static ThemeData forPalette(LumenisPalette palette) {
    final isLight = palette.brightness == Brightness.light;
    final onAccent = isLight
        ? const Color(0xFFFFFFFF)
        : const Color(0xFF151619);
    return ThemeData(
      useMaterial3: true,
      fontFamily: 'LumenisSansSC',
      fontFamilyFallback: const ['LumenisSansKR'],
      brightness: palette.brightness,
      colorScheme: ColorScheme(
        brightness: palette.brightness,
        primary: palette.accent,
        onPrimary: onAccent,
        secondary: palette.bmp,
        onSecondary: onAccent,
        error: palette.danger,
        onError: onAccent,
        surface: palette.surface,
        onSurface: palette.foreground,
        surfaceContainerHighest: palette.surfaceRaised,
        onSurfaceVariant: palette.muted,
        outline: palette.line,
        outlineVariant: palette.line,
        shadow: Colors.black.withValues(alpha: isLight ? 0.12 : 0.35),
        scrim: Colors.black.withValues(alpha: 0.32),
        inverseSurface: palette.foreground,
        onInverseSurface: isLight ? Colors.white : const Color(0xFF151619),
        inversePrimary: isLight ? palette.accentStrong : palette.accent,
      ),
      extensions: <ThemeExtension<dynamic>>[palette],
      scaffoldBackgroundColor: palette.canvas,
      canvasColor: palette.canvas,
      dividerColor: palette.line,
      visualDensity: VisualDensity.standard,
      bottomSheetTheme: BottomSheetThemeData(
        backgroundColor: palette.surface.withValues(alpha: .98),
        modalBackgroundColor: palette.surface.withValues(alpha: .98),
      ),
      popupMenuTheme: PopupMenuThemeData(
        color: palette.surface.withValues(alpha: .98),
        surfaceTintColor: Colors.transparent,
      ),
      cardTheme: CardThemeData(
        color: palette.surface,
        elevation: 0,
        surfaceTintColor: Colors.transparent,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: palette.surface,
        contentPadding: const EdgeInsets.all(16),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: palette.line),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: palette.line),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: palette.accent, width: 1.5),
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: palette.accentStrong,
          foregroundColor: onAccent,
          minimumSize: const Size(48, 44),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(10),
          ),
        ),
      ),
      tooltipTheme: TooltipThemeData(
        textStyle: TextStyle(color: onAccent, fontSize: 12),
        decoration: BoxDecoration(
          color: palette.foreground,
          borderRadius: const BorderRadius.all(Radius.circular(6)),
        ),
      ),
      textTheme: TextTheme(
        displayLarge: TextStyle(
          color: palette.foreground,
          fontSize: 36,
          height: 1.25,
          fontWeight: FontWeight.w500,
          letterSpacing: 0,
        ),
        displayMedium: TextStyle(
          color: palette.foreground,
          fontSize: 32,
          height: 1.25,
          fontWeight: FontWeight.w500,
          letterSpacing: 0,
        ),
        displaySmall: TextStyle(
          color: palette.foreground,
          fontSize: 28,
          height: 1.3,
          fontWeight: FontWeight.w500,
          letterSpacing: 0,
        ),
        headlineLarge: TextStyle(
          color: palette.foreground,
          fontSize: 28,
          height: 1.3,
          fontWeight: FontWeight.w600,
          letterSpacing: 0,
        ),
        headlineMedium: TextStyle(
          color: palette.foreground,
          fontSize: 26,
          height: 1.3,
          fontWeight: FontWeight.w600,
          letterSpacing: 0,
        ),
        headlineSmall: TextStyle(
          color: palette.foreground,
          fontSize: 24,
          height: 1.35,
          fontWeight: FontWeight.w600,
          letterSpacing: 0,
        ),
        bodyLarge: TextStyle(
          color: palette.foreground,
          fontSize: 16,
          height: 1.6,
          letterSpacing: 0,
        ),
        bodyMedium: TextStyle(
          color: palette.foreground,
          fontSize: 14,
          height: 1.6,
          letterSpacing: 0,
        ),
        bodySmall: TextStyle(
          color: palette.muted,
          fontSize: 13,
          height: 1.55,
          letterSpacing: 0,
        ),
        titleLarge: TextStyle(
          color: palette.foreground,
          fontSize: 20,
          height: 1.35,
          letterSpacing: 0,
          fontWeight: FontWeight.w600,
        ),
        titleMedium: TextStyle(
          color: palette.foreground,
          fontSize: 16,
          height: 1.4,
          letterSpacing: 0,
          fontWeight: FontWeight.w500,
        ),
        titleSmall: TextStyle(
          color: palette.foreground,
          fontSize: 14,
          height: 1.4,
          fontWeight: FontWeight.w500,
          letterSpacing: 0,
        ),
        labelLarge: const TextStyle(
          fontSize: 14,
          height: 1.3,
          fontWeight: FontWeight.w500,
          letterSpacing: 0,
        ),
        labelMedium: const TextStyle(
          fontSize: 13,
          height: 1.3,
          fontWeight: FontWeight.w500,
          letterSpacing: 0,
        ),
        labelSmall: const TextStyle(
          fontSize: 12,
          height: 1.35,
          fontWeight: FontWeight.w500,
          letterSpacing: 0,
        ),
      ),
      focusColor: palette.accent.withValues(alpha: 0.2),
      splashColor: palette.accent.withValues(alpha: 0.08),
      highlightColor: palette.accent.withValues(alpha: 0.04),
    );
  }
}
