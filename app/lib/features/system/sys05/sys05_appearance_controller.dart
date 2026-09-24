import 'dart:convert';
import 'dart:ui' as ui;

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

enum WorkspaceBackdrop { frosted, wallpaper, desktop, white, black, solid }

/// Device appearance belongs to SYS-05. It contains no business or account data.
class Sys05AppearanceController extends ChangeNotifier {
  Sys05AppearanceController({SharedPreferencesAsync? storage})
    : _providedStorage = storage;

  static const preferenceKey = 'lumenis.sys05.appearance.v1';
  static const wallpaperKey = 'lumenis.sys05.wallpaper.v1';
  static const maxWallpaperBytes = 3 * 1024 * 1024;
  static const minUiFontSize = 13.0;
  static const maxUiFontSize = 18.0;
  static const defaultUiFontSize = 14.0;
  final SharedPreferencesAsync? _providedStorage;
  late final SharedPreferencesAsync _storage =
      _providedStorage ?? SharedPreferencesAsync();
  WorkspaceBackdrop mode = WorkspaceBackdrop.frosted;
  Color solidColor = const Color(0xFFE8E4EC);
  bool darkGlass = false;
  bool compact = false;
  bool reducedMotion = false;
  double blur = 24;
  double panelOpacity = .9;
  double uiFontSize = defaultUiFontSize;
  Uint8List? wallpaper;
  bool loaded = false;
  bool saving = false;
  String? errorKey;
  bool _disposed = false;
  int _preferenceRevision = 0;
  Future<void> _pendingSave = Future.value();

  bool get isDark => switch (mode) {
    WorkspaceBackdrop.black => true,
    WorkspaceBackdrop.white => false,
    WorkspaceBackdrop.solid => solidColor.computeLuminance() < .179,
    _ => darkGlass,
  };
  bool get isGlass => switch (mode) {
    WorkspaceBackdrop.frosted ||
    WorkspaceBackdrop.wallpaper ||
    WorkspaceBackdrop.desktop => true,
    _ => false,
  };
  Color get backgroundColor => switch (mode) {
    WorkspaceBackdrop.white => Colors.white,
    WorkspaceBackdrop.black => Colors.black,
    WorkspaceBackdrop.solid => solidColor,
    WorkspaceBackdrop.desktop => Colors.transparent,
    _ => isDark ? const Color(0xFF15151B) : const Color(0xFFF1EDF4),
  };

  Future<void> restore() async {
    try {
      final raw = await _storage.getString(preferenceKey);
      if (raw != null) {
        final value = jsonDecode(raw);
        if (value is! Map<String, dynamic>) throw const FormatException();
        mode = WorkspaceBackdrop.values.firstWhere(
          (entry) => entry.name == value['mode'],
          orElse: () => WorkspaceBackdrop.frosted,
        );
        if (value['solidColor'] is int) {
          solidColor = Color(value['solidColor'] as int).withValues(alpha: 1);
        }
        darkGlass = value['darkGlass'] == true;
        compact = value['compact'] == true;
        reducedMotion = value['reducedMotion'] == true;
        if (value['blur'] is num) {
          blur = (value['blur'] as num).toDouble().clamp(0, 48);
        }
        if (value['panelOpacity'] is num) {
          panelOpacity = (value['panelOpacity'] as num).toDouble().clamp(
            .65,
            1,
          );
        }
        uiFontSize = _normalizeUiFontSize(value['uiFontSize']);
      }
      final image = await _storage.getString(wallpaperKey);
      if (image != null) {
        final bytes = base64Decode(image);
        await _validateImage(bytes);
        wallpaper = bytes;
      }
      if (mode == WorkspaceBackdrop.wallpaper && wallpaper == null) {
        mode = WorkspaceBackdrop.frosted;
      }
    } catch (_) {
      mode = WorkspaceBackdrop.frosted;
      solidColor = const Color(0xFFE8E4EC);
      darkGlass = false;
      compact = false;
      reducedMotion = false;
      blur = 24;
      panelOpacity = .9;
      uiFontSize = defaultUiFontSize;
      wallpaper = null;
      errorKey = 'appearance.restoreFailed';
    }
    loaded = true;
    _notify();
  }

  Future<void> update({
    WorkspaceBackdrop? mode,
    Color? solidColor,
    bool? darkGlass,
    bool? compact,
    bool? reducedMotion,
    double? blur,
    double? panelOpacity,
    double? uiFontSize,
  }) {
    this.mode = mode ?? this.mode;
    this.solidColor = solidColor ?? this.solidColor;
    this.darkGlass = darkGlass ?? this.darkGlass;
    this.compact = compact ?? this.compact;
    this.reducedMotion = reducedMotion ?? this.reducedMotion;
    this.blur = (blur ?? this.blur).clamp(0, 48);
    this.panelOpacity = (panelOpacity ?? this.panelOpacity).clamp(.65, 1);
    this.uiFontSize = uiFontSize == null
        ? this.uiFontSize
        : _normalizeUiFontSize(uiFontSize);
    final revision = ++_preferenceRevision;
    _clearNonNativeError();
    final encoded = jsonEncode({
      'version': 1,
      'mode': this.mode.name,
      'solidColor': this.solidColor.toARGB32(),
      'darkGlass': this.darkGlass,
      'compact': this.compact,
      'reducedMotion': this.reducedMotion,
      'blur': this.blur,
      'panelOpacity': this.panelOpacity,
      'uiFontSize': this.uiFontSize,
    });
    saving = true;
    _notify();
    // Serialize writes so fast slider changes cannot restore an older preference.
    _pendingSave = _pendingSave.then((_) async {
      try {
        await _storage.setString(preferenceKey, encoded);
        if (revision == _preferenceRevision &&
            errorKey == 'appearance.saveFailed') {
          errorKey = null;
        }
      } catch (_) {
        if (revision == _preferenceRevision) {
          errorKey = 'appearance.saveFailed';
        }
      } finally {
        if (revision == _preferenceRevision) {
          saving = false;
          _notify();
        }
      }
    });
    return _pendingSave;
  }

  Future<bool> setWallpaper(Uint8List bytes) async {
    _clearNonNativeError();
    try {
      await _validateImage(bytes);
      // Persist before replacing the visible wallpaper; quota failures preserve it.
      await _storage.setString(wallpaperKey, base64Encode(bytes));
      wallpaper = bytes;
      await update(mode: WorkspaceBackdrop.wallpaper);
      return errorKey != 'appearance.saveFailed';
    } on FormatException {
      errorKey = 'appearance.invalidImage';
    } catch (_) {
      errorKey = 'appearance.saveFailed';
    }
    _notify();
    return false;
  }

  Future<void> removeWallpaper() async {
    try {
      await _storage.remove(wallpaperKey);
      wallpaper = null;
      await update(mode: WorkspaceBackdrop.frosted);
    } catch (_) {
      errorKey = 'appearance.saveFailed';
      _notify();
    }
  }

  Future<void> _validateImage(Uint8List bytes) async {
    if (bytes.isEmpty || bytes.length > maxWallpaperBytes) {
      throw const FormatException();
    }
    ui.Codec? codec;
    ui.FrameInfo? frame;
    try {
      // ImageDescriptor.width/height are unsupported for encoded Web images.
      // The SDK codec callback reports intrinsic size on all target platforms
      // and takes ownership of the immutable buffer.
      codec = await ui.instantiateImageCodecWithSize(
        await ui.ImmutableBuffer.fromUint8List(bytes),
        getTargetSize: (width, height) {
          if (width > 8192 || height > 8192 || width * height > 32000000) {
            throw const FormatException();
          }
          return const ui.TargetImageSize(width: 1, height: 1);
        },
      );
      frame = await codec.getNextFrame();
    } catch (_) {
      throw const FormatException();
    } finally {
      frame?.image.dispose();
      codec?.dispose();
    }
  }

  static double _normalizeUiFontSize(Object? value) {
    if (value is! num) return defaultUiFontSize;
    final size = value.toDouble();
    if (!size.isFinite) return defaultUiFontSize;
    return size.clamp(minUiFontSize, maxUiFontSize).toDouble();
  }

  void _notify() {
    if (!_disposed) notifyListeners();
  }

  void _clearNonNativeError() {
    if (errorKey != 'appearance.nativeFailed' &&
        errorKey != 'appearance.nativeResetFailed') {
      errorKey = null;
    }
  }

  void clearNativeError() {
    if (errorKey == 'appearance.nativeFailed' ||
        errorKey == 'appearance.nativeResetFailed') {
      errorKey = null;
      _notify();
    }
  }

  void reportError(String key) {
    errorKey = key;
    _notify();
  }

  @override
  void dispose() {
    _disposed = true;
    super.dispose();
  }
}

class Sys05AppearanceScope
    extends InheritedNotifier<Sys05AppearanceController> {
  const Sys05AppearanceScope({
    required Sys05AppearanceController controller,
    required super.child,
    super.key,
  }) : super(notifier: controller);
  static Sys05AppearanceController? maybeOf(BuildContext context) => context
      .dependOnInheritedWidgetOfExactType<Sys05AppearanceScope>()
      ?.notifier;
}
