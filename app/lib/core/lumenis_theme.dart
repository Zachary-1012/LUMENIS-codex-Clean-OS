import 'package:flutter/material.dart';

/// App-level semantic colors. Screen layouts remain owned by their workflows.
abstract final class LumenisTheme {
  static const canvas = Color(0xFF0D0E10);
  static const surface = Color(0xFF15181B);
  static const surfaceRaised = Color(0xFF1D2226);
  static const line = Color(0xFF2A3034);
  static const foreground = Color(0xFFF2F3F4);
  static const muted = Color(0xFFA6ADB2);
  static const quiet = Color(0xFF737D82);
  static const accent = Color(0xFFB9E4D1);
  static const accentStrong = Color(0xFF74B99A);

  static const cth = Color(0xFFE7B36D);
  static const bmp = Color(0xFF7EC5C0);
  static const ai = Color(0xFFC8B4F3);
  static const shared = Color(0xFFE69A79);
  static const system = Color(0xFF91B6C8);

  static const positive = Color(0xFF7DC49C);
  static const caution = Color(0xFFE6B86D);
  static const danger = Color(0xFFE78375);

  static ThemeData get dark => ThemeData(
    useMaterial3: true,
    brightness: Brightness.dark,
    colorScheme: const ColorScheme.dark(
      primary: accent,
      onPrimary: canvas,
      secondary: bmp,
      onSecondary: canvas,
      surface: surface,
      onSurface: foreground,
      error: danger,
      onError: canvas,
    ),
    scaffoldBackgroundColor: canvas,
    canvasColor: canvas,
    dividerColor: line,
    textTheme: const TextTheme(
      bodyLarge: TextStyle(color: foreground, height: 1.45),
      bodyMedium: TextStyle(color: foreground, height: 1.45),
      bodySmall: TextStyle(color: muted, height: 1.4),
      titleLarge: TextStyle(color: foreground, fontWeight: FontWeight.w600),
      titleMedium: TextStyle(color: foreground, fontWeight: FontWeight.w600),
      labelLarge: TextStyle(fontWeight: FontWeight.w600),
    ),
    focusColor: accent.withValues(alpha: 0.2),
    splashColor: accent.withValues(alpha: 0.08),
    highlightColor: accent.withValues(alpha: 0.04),
  );
}
