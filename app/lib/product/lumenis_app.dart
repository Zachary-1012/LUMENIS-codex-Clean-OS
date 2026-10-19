import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'dart:ui' as ui;

import '../core/lumenis_core_client.dart';
import '../core/lumenis_theme.dart';
import '../l10n/lumenis_localizations.dart';
import '../navigation/lumenis_router.dart';
import '../features/system/sys05/sys05_appearance_controller.dart';
import '../platform/lumenis_window_material.dart';
import '../platform/lumenis_url_strategy.dart';

class LumenisApp extends StatefulWidget {
  const LumenisApp({this.client, this.initialLocation, super.key});

  final LumenisCoreClient? client;
  final String? initialLocation;

  @override
  State<LumenisApp> createState() => _LumenisAppState();
}

class _LumenisAppState extends State<LumenisApp> {
  late final LumenisCoreClient _client;
  late final _router = createLumenisRouter(
    client: _client,
    onLocaleChanged: _setLocale,
    initialLocation: widget.initialLocation,
  );
  Locale? _locale;
  final _appearance = Sys05AppearanceController();
  String? _materialRequest;
  bool _nativeActive = false;

  @override
  void initState() {
    super.initState();
    _client = widget.client ?? LumenisCoreClient();
    _appearance.addListener(_applyAppearance);
    _appearance.restore();
  }

  void _applyAppearance() {
    if (!mounted) return;
    setState(() {});
    final enabled = _appearance.mode == WorkspaceBackdrop.desktop;
    final wasNativeActive = _nativeActive;
    final request = '$enabled:${_appearance.isDark}';
    if (request == _materialRequest) return;
    _materialRequest = request;
    LumenisWindowMaterial.apply(
      enabled: enabled,
      dark: _appearance.isDark,
    ).then((success) {
      if (!mounted || request != _materialRequest) return;
      if (success) {
        setState(() => _nativeActive = enabled);
        _appearance.clearNativeError();
      }
      if (!success && (enabled || wasNativeActive)) {
        _appearance.reportError(
          enabled ? 'appearance.nativeFailed' : 'appearance.nativeResetFailed',
        );
      }
    });
  }

  void _setLocale(Locale? locale) {
    setState(() => _locale = locale);
  }

  @override
  Widget build(BuildContext context) {
    final base = _appearance.isDark
        ? LumenisTheme.darkPalette
        : LumenisTheme.lightPalette;
    final usesWallpaper = _appearance.mode == WorkspaceBackdrop.wallpaper;
    var palette = base.copyWith(
      foreground: _appearance.mode == WorkspaceBackdrop.solid
          ? (_appearance.isDark ? Colors.white : Colors.black)
          : base.foreground,
      muted: usesWallpaper
          ? base.foreground
          : _appearance.mode == WorkspaceBackdrop.solid
          ? (_appearance.isDark ? Colors.white : Colors.black).withValues(
              alpha: .85,
            )
          : base.muted,
      quiet: usesWallpaper ? base.foreground : base.quiet,
      canvas: _appearance.isGlass
          ? Colors.transparent
          : _appearance.backgroundColor,
      surface: base.surface.withValues(
        alpha: _appearance.isGlass ? _appearance.panelOpacity : 1,
      ),
      surfaceRaised: base.surfaceRaised.withValues(
        alpha: _appearance.isGlass ? _appearance.panelOpacity : 1,
      ),
    );
    if (usesWallpaper) {
      palette = palette.copyWith(
        contrastBackground: Color.alphaBlend(
          LumenisTheme.wallpaperScrim(palette),
          palette.brightness == Brightness.dark ? Colors.white : Colors.black,
        ),
      );
    }
    return MaterialApp.router(
      title: '寰意 · OEVIRA',
      locale: _locale,
      supportedLocales: LumenisLocalizations.supportedLocales,
      localeResolutionCallback: (deviceLocale, supportedLocales) =>
          LumenisLocalizations.resolve(deviceLocale),
      localizationsDelegates: const [
        LumenisLocalizations.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      theme: LumenisTheme.forPalette(palette).copyWith(
        visualDensity: _appearance.compact
            ? VisualDensity.compact
            : VisualDensity.standard,
      ),
      themeAnimationDuration: _appearance.reducedMotion || usesWallpaper
          ? Duration.zero
          : const Duration(milliseconds: 160),
      builder: (context, child) {
        setLumenisDocumentLanguage(
          Localizations.localeOf(context).toLanguageTag(),
        );
        return Sys05AppearanceScope(
          controller: _appearance,
          child: MediaQuery(
            data: MediaQuery.of(context).copyWith(
              textScaler: _WorkspaceTextScaler(
                MediaQuery.textScalerOf(context),
                _appearance.uiFontSize / 14,
              ),
              disableAnimations:
                  _appearance.reducedMotion ||
                  MediaQuery.of(context).disableAnimations,
            ),
            child: Stack(
              fit: StackFit.expand,
              children: [
                ExcludeSemantics(
                  child: IgnorePointer(
                    child: _WorkspaceBackdrop(
                      appearance: _appearance,
                      nativeActive: _nativeActive,
                    ),
                  ),
                ),
                child ?? const SizedBox.shrink(),
              ],
            ),
          ),
        );
      },
      restorationScopeId: 'lumenis',
      debugShowCheckedModeBanner: false,
      routerConfig: _router,
    );
  }

  @override
  void dispose() {
    _appearance.removeListener(_applyAppearance);
    _appearance.dispose();
    _router.dispose();
    super.dispose();
  }
}

/// Preserve the platform's accessibility scaling, including nonlinear scaling.
class _WorkspaceTextScaler extends TextScaler {
  const _WorkspaceTextScaler(this.system, this.factor);
  final TextScaler system;
  final double factor;

  @override
  double scale(double fontSize) => system.scale(fontSize) * factor;

  @override
  double get textScaleFactor => scale(14) / 14;
}

class _WorkspaceBackdrop extends StatelessWidget {
  const _WorkspaceBackdrop({
    required this.appearance,
    required this.nativeActive,
  });
  final Sys05AppearanceController appearance;
  final bool nativeActive;
  @override
  Widget build(BuildContext context) {
    if (appearance.mode == WorkspaceBackdrop.desktop && nativeActive) {
      return ColoredBox(
        color: (appearance.isDark ? Colors.black : Colors.white).withValues(
          alpha: .12,
        ),
      );
    }
    if (!appearance.isGlass) {
      return ColoredBox(color: appearance.backgroundColor);
    }
    final wallpaper = appearance.mode == WorkspaceBackdrop.wallpaper
        ? appearance.wallpaper
        : null;
    return ClipRect(
      child: Stack(
        fit: StackFit.expand,
        children: [
          if (wallpaper != null)
            ImageFiltered(
              imageFilter: ui.ImageFilter.blur(
                sigmaX: appearance.blur,
                sigmaY: appearance.blur,
                tileMode: TileMode.clamp,
              ),
              child: Image.memory(
                wallpaper,
                fit: BoxFit.cover,
                cacheWidth: 1920,
                gaplessPlayback: true,
              ),
            )
          else
            ColoredBox(
              color: appearance.isDark
                  ? const Color(0xFF14161C)
                  : const Color(0xFFF7F5F2),
              child: ImageFiltered(
                imageFilter: ui.ImageFilter.blur(
                  sigmaX: appearance.blur,
                  sigmaY: appearance.blur,
                  tileMode: TileMode.clamp,
                ),
                child: CustomPaint(
                  painter: _OpticalFieldPainter(dark: appearance.isDark),
                ),
              ),
            ),
          ColoredBox(
            key: const ValueKey('workspace/backdrop-scrim'),
            color: appearance.mode == WorkspaceBackdrop.wallpaper
                ? LumenisTheme.wallpaperScrim(LumenisTheme.of(context))
                : (appearance.isDark ? Colors.black : Colors.white).withValues(
                    alpha: .18,
                  ),
          ),
        ],
      ),
    );
  }
}

class _OpticalFieldPainter extends CustomPainter {
  const _OpticalFieldPainter({required this.dark});
  final bool dark;
  @override
  void paint(Canvas canvas, Size size) {
    final radius = size.shortestSide * .62;
    for (final bloom in [
      (Offset(size.width * .78, size.height * .15), const Color(0xFF9198D3)),
      (Offset(size.width * .1, size.height * .58), const Color(0xFFE3A68A)),
      (Offset(size.width * .82, size.height * .9), const Color(0xFF8FBBC5)),
    ]) {
      canvas.drawCircle(
        bloom.$1,
        radius,
        Paint()
          ..shader = ui.Gradient.radial(bloom.$1, radius, [
            bloom.$2.withValues(alpha: dark ? .22 : .26),
            bloom.$2.withValues(alpha: 0),
          ]),
      );
    }
  }

  @override
  bool shouldRepaint(_OpticalFieldPainter oldDelegate) =>
      oldDelegate.dark != dark;
}
