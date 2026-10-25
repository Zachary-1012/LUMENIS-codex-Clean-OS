import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';

abstract final class LumenisSpace {
  static const unit = 4.0;
  static const tight = 8.0;
  static const inset = 12.0;
  static const control = 16.0;
  static const section = 24.0;
  static const gutter = 32.0;
  static const chapter = 48.0;
  static const touchTarget = 48.0;
  static const railWidth = 216.0;
  static const toolbarHeight = 58.0;
  static const readingWidth = 940.0;
}

abstract final class LumenisMotion {
  static const feedback = Duration(milliseconds: 90);
  static const selection = Duration(milliseconds: 150);
  static const panel = Duration(milliseconds: 250);
  static const exit = Duration(milliseconds: 200);
  static const transition = Duration(milliseconds: 300);
  static const page = Duration(milliseconds: 400);

  static Duration of(BuildContext context, Duration duration) =>
      MediaQuery.maybeOf(context)?.disableAnimations ?? false
      ? Duration.zero
      : duration;
}

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
    final background =
        contrastBackground ??
        (brightness == Brightness.dark ? surfaceRaised : null);
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
  static const canvas = Color(0xFFF0F1E7);
  static const surface = Color(0xFFFAFBF4);
  static const surfaceRaised = Color(0xFFE2E7D9);
  static const line = Color(0xFFB5BEAA);
  static const foreground = Color(0xFF1D2B24);
  static const muted = Color(0xFF4F5D52);
  static const quiet = Color(0xFF566255);
  static const accent = Color(0xFF355E3B);
  static const accentStrong = Color(0xFF25492C);

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
    canvas: Color(0xFF101A16),
    surface: Color(0xFF17221C),
    surfaceRaised: Color(0xFF263229),
    line: Color(0xFF52634D),
    foreground: Color(0xFFEEF3DB),
    muted: Color(0xFFC1CAB4),
    quiet: Color(0xFFAFBDA8),
    accent: Color(0xFFB5DA91),
    accentStrong: Color(0xFFC8E8A7),
    brightness: Brightness.dark,
  );

  static LumenisPalette of(BuildContext context) =>
      Theme.of(context).extension<LumenisPalette>() ?? lightPalette;

  static ThemeData get light => forPalette(lightPalette);
  static ThemeData get dark => forPalette(darkPalette);

  static BoxDecoration chassis(LumenisPalette palette, {double radius = 0}) =>
      BoxDecoration(color: palette.canvas);

  static ShapeDecoration panel(
    LumenisPalette palette, {
    double radius = 12,
    bool recessed = false,
  }) => ShapeDecoration(
    color: recessed ? palette.canvas : palette.surfaceRaised,
    shape: LumenisPixelBorder(side: BorderSide(color: palette.line)),
  );

  static ShapeDecoration paper(LumenisPalette palette, {double radius = 16}) =>
      ShapeDecoration(
        color: palette.surface,
        shape: LumenisPixelBorder(side: BorderSide(color: palette.line)),
        shadows: [
          BoxShadow(
            color: palette.line.withValues(alpha: .32),
            offset: const Offset(3, 3),
          ),
        ],
      );

  static ShapeDecoration keycap(
    LumenisPalette palette, {
    Color? tint,
    double radius = 10,
    bool selected = false,
    bool pressed = false,
  }) => ShapeDecoration(
    color: selected
        ? (tint ?? palette.accent).withValues(alpha: .12)
        : palette.surface,
    shape: LumenisPixelBorder(
      step: 3,
      side: BorderSide(color: selected ? tint ?? palette.accent : palette.line),
    ),
    shadows: [
      if (!pressed && !selected)
        BoxShadow(color: palette.line, offset: const Offset(2, 2)),
    ],
  );

  static Widget _buttonFace(
    BuildContext context,
    Set<WidgetState> states,
    Widget? child, {
    bool raised = true,
  }) {
    final palette = of(context);
    final pressed = states.contains(WidgetState.pressed);
    final disabled = states.contains(WidgetState.disabled);
    final reduceMotion =
        MediaQuery.maybeOf(context)?.disableAnimations ?? false;
    return AnimatedContainer(
      duration: reduceMotion ? Duration.zero : LumenisMotion.feedback,
      transform: Matrix4.translationValues(
        pressed && !reduceMotion ? 1 : 0,
        pressed && !reduceMotion ? 1 : 0,
        0,
      ),
      decoration: ShapeDecoration(
        color: pressed ? palette.foreground.withValues(alpha: .06) : null,
        shape: LumenisPixelBorder(
          step: 2,
          side: raised
              ? BorderSide(
                  color: palette.foreground.withValues(
                    alpha: disabled ? .04 : .12,
                  ),
                )
              : BorderSide.none,
        ),
      ),
      child: child,
    );
  }

  static ThemeData forPalette(LumenisPalette palette) {
    final isLight = palette.brightness == Brightness.light;
    final onAccent = isLight
        ? const Color(0xFFFFFFFF)
        : const Color(0xFF151619);
    const controlShape = LumenisPixelBorder(step: 2);
    final frameShape = LumenisPixelBorder(
      step: 4,
      side: BorderSide(color: palette.line),
    );
    final focusSide = WidgetStateProperty.resolveWith<BorderSide>((states) {
      if (states.contains(WidgetState.disabled)) {
        return BorderSide(color: palette.line.withValues(alpha: .5));
      }
      if (states.contains(WidgetState.focused)) {
        return BorderSide(color: palette.accentStrong, width: 2);
      }
      return BorderSide(
        color: states.contains(WidgetState.hovered)
            ? palette.muted
            : palette.line,
      );
    });
    final overlay = WidgetStateProperty.resolveWith<Color?>((states) {
      if (states.contains(WidgetState.pressed)) {
        return palette.accent.withValues(alpha: .14);
      }
      if (states.contains(WidgetState.focused)) {
        return palette.accent.withValues(alpha: .10);
      }
      if (states.contains(WidgetState.hovered)) {
        return palette.accent.withValues(alpha: .06);
      }
      return null;
    });
    OutlineInputBorder inputBorder(Color color, [double width = 1]) =>
        OutlineInputBorder(
          borderRadius: BorderRadius.zero,
          borderSide: BorderSide(color: color, width: width),
        );
    return ThemeData(
      useMaterial3: true,
      fontFamily: 'LumenisSansSC',
      fontFamilyFallback: const ['LumenisSansKR', if (kIsWeb) 'LumenisEmoji'],
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
      materialTapTargetSize: MaterialTapTargetSize.padded,
      splashFactory: NoSplash.splashFactory,
      appBarTheme: AppBarTheme(
        backgroundColor: palette.canvas,
        foregroundColor: palette.foreground,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        titleTextStyle: TextStyle(
          color: palette.foreground,
          fontFamily: 'LumenisSansSC',
          fontFamilyFallback: const ['LumenisSansKR'],
          fontSize: 20,
          fontWeight: FontWeight.w600,
        ),
      ),
      scrollbarTheme: ScrollbarThemeData(
        thickness: const WidgetStatePropertyAll(5),
        radius: Radius.zero,
        thumbColor: WidgetStateProperty.resolveWith(
          (states) => palette.muted.withValues(
            alpha: states.contains(WidgetState.dragged) ? .65 : .3,
          ),
        ),
      ),
      textSelectionTheme: TextSelectionThemeData(
        cursorColor: palette.accentStrong,
        selectionColor: palette.accent.withValues(alpha: .20),
        selectionHandleColor: palette.accentStrong,
      ),
      iconButtonTheme: IconButtonThemeData(
        style:
            IconButton.styleFrom(
              minimumSize: const Size.square(LumenisSpace.touchTarget),
              foregroundColor: palette.muted,
              shape: controlShape,
            ).copyWith(
              overlayColor: overlay,
              animationDuration: LumenisMotion.feedback,
              side: WidgetStateProperty.resolveWith(
                (states) => states.contains(WidgetState.focused)
                    ? BorderSide(color: palette.accentStrong, width: 2)
                    : BorderSide.none,
              ),
            ),
      ),
      chipTheme: ChipThemeData(
        backgroundColor: palette.surface,
        selectedColor: palette.surfaceRaised,
        secondarySelectedColor: palette.surfaceRaised,
        side: BorderSide(color: palette.line),
        shape: controlShape,
        labelStyle: TextStyle(
          color: palette.foreground,
          fontSize: 13,
          fontWeight: FontWeight.w500,
        ),
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
        showCheckmark: true,
        checkmarkColor: palette.accentStrong,
        disabledColor: palette.surfaceRaised.withValues(alpha: .5),
      ),
      bottomSheetTheme: BottomSheetThemeData(
        backgroundColor: palette.surface.withValues(alpha: .98),
        modalBackgroundColor: palette.surface.withValues(alpha: .98),
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        shape: frameShape,
      ),
      popupMenuTheme: PopupMenuThemeData(
        color: palette.surface.withValues(alpha: .98),
        surfaceTintColor: Colors.transparent,
        shape: frameShape,
        elevation: 6,
        shadowColor: palette.foreground.withValues(alpha: .12),
      ),
      cardTheme: CardThemeData(
        color: palette.surface,
        elevation: 0,
        shadowColor: Colors.black.withValues(alpha: .12),
        shape: frameShape,
        surfaceTintColor: Colors.transparent,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: palette.surface,
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 14,
          vertical: 15,
        ),
        border: inputBorder(palette.line),
        enabledBorder: inputBorder(palette.line),
        focusedBorder: inputBorder(palette.accentStrong, 2),
        errorBorder: inputBorder(palette.danger),
        focusedErrorBorder: inputBorder(palette.danger, 2),
        disabledBorder: inputBorder(palette.line.withValues(alpha: .5)),
        hintStyle: TextStyle(color: palette.quiet, fontWeight: FontWeight.w400),
        labelStyle: TextStyle(color: palette.muted, fontSize: 14),
        errorStyle: TextStyle(color: palette.danger, fontSize: 13, height: 1.4),
        errorMaxLines: 3,
      ),
      filledButtonTheme: FilledButtonThemeData(
        style:
            FilledButton.styleFrom(
              backgroundColor: palette.accentStrong,
              foregroundColor: onAccent,
              minimumSize: const Size(48, 48),
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
              shape: controlShape,
            ).copyWith(
              backgroundBuilder: _buttonFace,
              animationDuration: LumenisMotion.feedback,
              side: WidgetStateProperty.resolveWith(
                (states) => states.contains(WidgetState.focused)
                    ? BorderSide(color: palette.foreground, width: 2)
                    : BorderSide.none,
              ),
            ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style:
            ElevatedButton.styleFrom(
              backgroundColor: palette.surfaceRaised.withValues(alpha: .45),
              foregroundColor: palette.foreground,
              surfaceTintColor: Colors.transparent,
              elevation: 0,
              minimumSize: const Size(48, 48),
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
              shape: controlShape,
            ).copyWith(
              backgroundBuilder: (context, states, child) =>
                  _buttonFace(context, states, child, raised: false),
              side: focusSide,
              overlayColor: overlay,
              animationDuration: LumenisMotion.feedback,
            ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style:
            OutlinedButton.styleFrom(
              backgroundColor: palette.surface,
              foregroundColor: palette.foreground,
              minimumSize: const Size(48, 48),
              side: BorderSide(color: palette.line),
              padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
              shape: controlShape,
            ).copyWith(
              side: focusSide,
              overlayColor: overlay,
              animationDuration: LumenisMotion.feedback,
            ),
      ),
      textButtonTheme: TextButtonThemeData(
        style:
            TextButton.styleFrom(
              foregroundColor: palette.accentStrong,
              minimumSize: const Size.square(LumenisSpace.touchTarget),
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              shape: controlShape,
            ).copyWith(
              overlayColor: overlay,
              animationDuration: LumenisMotion.feedback,
            ),
      ),
      dialogTheme: DialogThemeData(
        backgroundColor: palette.surface,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        shadowColor: Colors.black.withValues(alpha: .22),
        shape: frameShape,
      ),
      drawerTheme: DrawerThemeData(
        backgroundColor: palette.surface,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        shape: frameShape,
        endShape: frameShape,
        scrimColor: palette.foreground.withValues(alpha: .26),
      ),
      navigationDrawerTheme: NavigationDrawerThemeData(
        backgroundColor: palette.surface,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        indicatorShape: controlShape,
        indicatorColor: palette.surfaceRaised,
        labelTextStyle: WidgetStateProperty.resolveWith(
          (states) => TextStyle(
            color: palette.foreground,
            fontSize: 14,
            fontWeight: states.contains(WidgetState.selected)
                ? FontWeight.w600
                : FontWeight.w400,
          ),
        ),
      ),
      dataTableTheme: DataTableThemeData(
        headingRowColor: WidgetStatePropertyAll(palette.surfaceRaised),
        dataRowColor: WidgetStateProperty.resolveWith(
          (states) => states.contains(WidgetState.selected)
              ? palette.accent.withValues(alpha: .10)
              : states.contains(WidgetState.hovered)
              ? palette.accent.withValues(alpha: .05)
              : Colors.transparent,
        ),
        headingTextStyle: TextStyle(
          color: palette.foreground,
          fontWeight: FontWeight.w600,
          fontSize: 13,
        ),
        dataTextStyle: TextStyle(
          color: palette.foreground,
          fontSize: 14,
          height: 1.5,
        ),
        dataRowMinHeight: 48,
        dataRowMaxHeight: double.infinity,
        horizontalMargin: 16,
        columnSpacing: 28,
        dividerThickness: 1,
      ),
      searchBarTheme: SearchBarThemeData(
        backgroundColor: WidgetStatePropertyAll(palette.surface),
        surfaceTintColor: const WidgetStatePropertyAll(Colors.transparent),
        elevation: const WidgetStatePropertyAll(0),
        shape: const WidgetStatePropertyAll(controlShape),
        side: focusSide,
        overlayColor: overlay,
        padding: const WidgetStatePropertyAll(
          EdgeInsets.symmetric(horizontal: 16),
        ),
        textStyle: WidgetStatePropertyAll(
          TextStyle(color: palette.foreground, fontSize: 14),
        ),
        hintStyle: WidgetStatePropertyAll(
          TextStyle(color: palette.quiet, fontSize: 14),
        ),
      ),
      searchViewTheme: SearchViewThemeData(
        backgroundColor: palette.surface,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        shape: frameShape,
        dividerColor: palette.line,
        headerTextStyle: TextStyle(color: palette.foreground, fontSize: 16),
        headerHintStyle: TextStyle(color: palette.quiet, fontSize: 16),
      ),
      datePickerTheme: DatePickerThemeData(
        backgroundColor: palette.surface,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        shape: frameShape,
        headerBackgroundColor: palette.surfaceRaised,
        headerForegroundColor: palette.foreground,
        dividerColor: palette.line,
        dayShape: const WidgetStatePropertyAll(controlShape),
        dayForegroundColor: WidgetStateProperty.resolveWith(
          (states) => states.contains(WidgetState.disabled)
              ? palette.quiet
              : states.contains(WidgetState.selected)
              ? onAccent
              : palette.foreground,
        ),
        dayBackgroundColor: WidgetStateProperty.resolveWith(
          (states) => states.contains(WidgetState.selected)
              ? palette.accentStrong
              : Colors.transparent,
        ),
        dayOverlayColor: overlay,
        todayBorder: BorderSide(color: palette.accentStrong, width: 2),
        rangePickerBackgroundColor: palette.surface,
        rangePickerSurfaceTintColor: Colors.transparent,
        rangePickerShape: frameShape,
        rangeSelectionBackgroundColor: palette.accent.withValues(alpha: .12),
        rangeSelectionOverlayColor: overlay,
      ),
      timePickerTheme: TimePickerThemeData(
        backgroundColor: palette.surface,
        elevation: 0,
        shape: frameShape,
        hourMinuteShape: controlShape,
        hourMinuteColor: palette.surfaceRaised,
        hourMinuteTextColor: palette.foreground,
        dayPeriodShape: controlShape,
        dayPeriodBorderSide: BorderSide(color: palette.line),
        dayPeriodColor: palette.surfaceRaised,
        dayPeriodTextColor: palette.foreground,
        dialBackgroundColor: palette.surfaceRaised,
        dialHandColor: palette.accentStrong,
        entryModeIconColor: palette.foreground,
      ),
      dividerTheme: DividerThemeData(
        color: palette.line,
        thickness: 1,
        space: 1,
      ),
      listTileTheme: ListTileThemeData(
        minTileHeight: 48,
        horizontalTitleGap: 12,
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 2),
        shape: controlShape,
        selectedColor: palette.accentStrong,
        selectedTileColor: palette.accent.withValues(alpha: .08),
        iconColor: palette.muted,
        textColor: palette.foreground,
      ),
      segmentedButtonTheme: SegmentedButtonThemeData(
        style: ButtonStyle(
          shape: const WidgetStatePropertyAll(controlShape),
          side: focusSide,
          overlayColor: overlay,
          minimumSize: const WidgetStatePropertyAll(Size(48, 48)),
          foregroundColor: WidgetStatePropertyAll(palette.foreground),
          backgroundColor: WidgetStateProperty.resolveWith(
            (states) => states.contains(WidgetState.selected)
                ? palette.surfaceRaised
                : palette.surface,
          ),
          animationDuration: LumenisMotion.feedback,
        ),
      ),
      menuTheme: MenuThemeData(
        style: MenuStyle(
          backgroundColor: WidgetStatePropertyAll(palette.surface),
          surfaceTintColor: const WidgetStatePropertyAll(Colors.transparent),
          shape: WidgetStatePropertyAll(frameShape),
          padding: const WidgetStatePropertyAll(EdgeInsets.all(6)),
        ),
      ),
      dropdownMenuTheme: DropdownMenuThemeData(
        textStyle: TextStyle(color: palette.foreground, fontSize: 14),
        menuStyle: MenuStyle(
          backgroundColor: WidgetStatePropertyAll(palette.surface),
          surfaceTintColor: const WidgetStatePropertyAll(Colors.transparent),
          shape: WidgetStatePropertyAll(frameShape),
          padding: const WidgetStatePropertyAll(EdgeInsets.all(6)),
          elevation: const WidgetStatePropertyAll(0),
          side: WidgetStatePropertyAll(BorderSide(color: palette.line)),
        ),
      ),
      radioTheme: RadioThemeData(
        fillColor: WidgetStateProperty.resolveWith(
          (states) => states.contains(WidgetState.disabled)
              ? palette.line
              : states.contains(WidgetState.selected)
              ? palette.accentStrong
              : palette.muted,
        ),
        overlayColor: overlay,
        materialTapTargetSize: MaterialTapTargetSize.padded,
      ),
      expansionTileTheme: ExpansionTileThemeData(
        backgroundColor: palette.surface,
        collapsedBackgroundColor: Colors.transparent,
        iconColor: palette.accentStrong,
        collapsedIconColor: palette.muted,
        textColor: palette.foreground,
        collapsedTextColor: palette.foreground,
        shape: Border(bottom: BorderSide(color: palette.line)),
        collapsedShape: Border(bottom: BorderSide(color: palette.line)),
        tilePadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
        childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
      ),
      menuButtonTheme: MenuButtonThemeData(
        style: ButtonStyle(
          shape: const WidgetStatePropertyAll(controlShape),
          overlayColor: overlay,
          minimumSize: const WidgetStatePropertyAll(Size(48, 48)),
          foregroundColor: WidgetStatePropertyAll(palette.foreground),
          textStyle: const WidgetStatePropertyAll(TextStyle(fontSize: 14)),
        ),
      ),
      checkboxTheme: CheckboxThemeData(
        shape: const RoundedRectangleBorder(),
        side: BorderSide(color: palette.muted, width: 1.5),
        fillColor: WidgetStateProperty.resolveWith(
          (states) => states.contains(WidgetState.selected)
              ? palette.accentStrong
              : palette.surface,
        ),
        checkColor: WidgetStatePropertyAll(onAccent),
        overlayColor: overlay,
      ),
      tabBarTheme: TabBarThemeData(
        labelColor: palette.foreground,
        unselectedLabelColor: palette.muted,
        dividerColor: palette.line,
        indicatorColor: palette.accentStrong,
        indicatorSize: TabBarIndicatorSize.label,
        labelStyle: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600),
        unselectedLabelStyle: const TextStyle(
          fontSize: 14,
          fontWeight: FontWeight.w400,
        ),
        overlayColor: overlay,
      ),
      snackBarTheme: SnackBarThemeData(
        behavior: SnackBarBehavior.floating,
        backgroundColor: palette.foreground,
        contentTextStyle: TextStyle(
          color: palette.surface.withValues(alpha: 1),
          fontSize: 14,
          height: 1.5,
        ),
        actionTextColor: palette.surface.withValues(alpha: 1),
        shape: const LumenisPixelBorder(step: 3),
        elevation: 0,
      ),
      progressIndicatorTheme: ProgressIndicatorThemeData(
        color: palette.accentStrong,
        linearTrackColor: palette.surfaceRaised,
        circularTrackColor: palette.surfaceRaised,
        linearMinHeight: 3,
      ),
      sliderTheme: SliderThemeData(
        activeTrackColor: palette.accent,
        inactiveTrackColor: palette.line,
        thumbColor: palette.surface,
        overlayColor: palette.accent.withValues(alpha: .12),
        disabledThumbColor: palette.line,
        disabledActiveTrackColor: palette.line,
        disabledInactiveTrackColor: palette.line.withValues(alpha: .35),
        valueIndicatorColor: palette.foreground,
        valueIndicatorTextStyle: TextStyle(color: palette.surface),
        trackHeight: 3,
        trackShape: const RectangularSliderTrackShape(),
        thumbShape: const _PixelSliderThumb(),
      ),
      switchTheme: SwitchThemeData(
        thumbColor: WidgetStatePropertyAll(palette.surface),
        trackColor: WidgetStateProperty.resolveWith(
          (states) => states.contains(WidgetState.disabled)
              ? palette.line.withValues(alpha: .35)
              : states.contains(WidgetState.selected)
              ? palette.accent
              : palette.line,
        ),
        overlayColor: overlay,
        trackOutlineColor: WidgetStateProperty.resolveWith(
          (states) => states.contains(WidgetState.focused)
              ? palette.accentStrong
              : Colors.transparent,
        ),
        trackOutlineWidth: const WidgetStatePropertyAll(2),
      ),
      tooltipTheme: TooltipThemeData(
        textStyle: TextStyle(
          color: palette.surface.withValues(alpha: 1),
          fontSize: 12,
          height: 1.4,
        ),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        waitDuration: const Duration(milliseconds: 500),
        decoration: ShapeDecoration(
          color: palette.foreground,
          shape: const LumenisPixelBorder(step: 2),
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

class _PixelSliderThumb extends SliderComponentShape {
  const _PixelSliderThumb();

  @override
  Size getPreferredSize(bool isEnabled, bool isDiscrete) => const Size(18, 22);

  @override
  void paint(
    PaintingContext context,
    Offset center, {
    required Animation<double> activationAnimation,
    required Animation<double> enableAnimation,
    required bool isDiscrete,
    required TextPainter labelPainter,
    required RenderBox parentBox,
    required SliderThemeData sliderTheme,
    required TextDirection textDirection,
    required double value,
    required double textScaleFactor,
    required Size sizeWithOverflow,
  }) {
    final color = Color.lerp(
      sliderTheme.disabledThumbColor,
      sliderTheme.thumbColor,
      enableAnimation.value,
    )!;
    final ink = Color.lerp(
      sliderTheme.disabledActiveTrackColor,
      sliderTheme.activeTrackColor,
      enableAnimation.value,
    )!;
    const shape = LumenisPixelBorder(step: 2);
    final rect = Rect.fromCenter(center: center, width: 18, height: 22);
    final canvas = context.canvas;
    canvas.drawPath(shape.getOuterPath(rect), Paint()..color = color);
    shape
        .copyWith(side: BorderSide(color: ink, width: 1.5))
        .paint(canvas, rect);
    canvas.drawRect(
      Rect.fromCenter(center: center, width: 2, height: 8),
      Paint()..color = ink,
    );
  }
}

class LumenisPixelBorder extends OutlinedBorder {
  const LumenisPixelBorder({super.side, this.step = 4});

  final double step;

  Path _path(Rect rect) {
    final s = step.clamp(0.0, rect.shortestSide / 6);
    return Path()
      ..moveTo(rect.left + 2 * s, rect.top)
      ..lineTo(rect.right - 2 * s, rect.top)
      ..lineTo(rect.right - 2 * s, rect.top + s)
      ..lineTo(rect.right - s, rect.top + s)
      ..lineTo(rect.right - s, rect.top + 2 * s)
      ..lineTo(rect.right, rect.top + 2 * s)
      ..lineTo(rect.right, rect.bottom - 2 * s)
      ..lineTo(rect.right - s, rect.bottom - 2 * s)
      ..lineTo(rect.right - s, rect.bottom - s)
      ..lineTo(rect.right - 2 * s, rect.bottom - s)
      ..lineTo(rect.right - 2 * s, rect.bottom)
      ..lineTo(rect.left + 2 * s, rect.bottom)
      ..lineTo(rect.left + 2 * s, rect.bottom - s)
      ..lineTo(rect.left + s, rect.bottom - s)
      ..lineTo(rect.left + s, rect.bottom - 2 * s)
      ..lineTo(rect.left, rect.bottom - 2 * s)
      ..lineTo(rect.left, rect.top + 2 * s)
      ..lineTo(rect.left + s, rect.top + 2 * s)
      ..lineTo(rect.left + s, rect.top + s)
      ..lineTo(rect.left + 2 * s, rect.top + s)
      ..close();
  }

  @override
  EdgeInsetsGeometry get dimensions => EdgeInsets.all(side.width);

  @override
  LumenisPixelBorder copyWith({BorderSide? side}) =>
      LumenisPixelBorder(side: side ?? this.side, step: step);

  @override
  ShapeBorder scale(double t) =>
      LumenisPixelBorder(side: side.scale(t), step: step * t);

  @override
  Path getOuterPath(Rect rect, {TextDirection? textDirection}) => _path(rect);

  @override
  Path getInnerPath(Rect rect, {TextDirection? textDirection}) =>
      _path(rect.deflate(side.width));

  @override
  void paint(Canvas canvas, Rect rect, {TextDirection? textDirection}) {
    if (side.style == BorderStyle.none) return;
    canvas.drawPath(_path(rect.deflate(side.width / 2)), side.toPaint());
  }
}
