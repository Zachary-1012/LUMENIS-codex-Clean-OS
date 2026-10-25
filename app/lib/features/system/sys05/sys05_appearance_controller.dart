import 'dart:convert';
import 'dart:ui' as ui;

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../../core/lumenis_theme.dart';

enum WaitingTone { playful, simple, off }

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
  Color solidColor = const Color(0xFFF0F1E7);
  String localeTag = 'system';
  bool darkGlass = false;
  bool compact = false;
  bool reducedMotion = false;
  bool botanicalRoles = true;
  WaitingTone waitingTone = WaitingTone.simple;
  double blur = 24;
  double panelOpacity = .9;
  double uiFontSize = defaultUiFontSize;
  Uint8List? wallpaper;
  bool loaded = false;
  bool saving = false;
  bool resetting = false;
  String? errorKey;
  String? statusKey;
  bool _disposed = false;
  int _preferenceRevision = 0;
  Future<void> _pendingSave = Future.value();
  Future<void> _pendingWallpaperOperation = Future.value();

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
    _ => isDark ? LumenisTheme.darkPalette.canvas : LumenisTheme.canvas,
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
        if (const [
          'system',
          'zh-CN',
          'en',
          'ko',
        ].contains(value['localeTag'])) {
          localeTag = value['localeTag'] as String;
        }
        if (value['solidColor'] is int) {
          solidColor = Color(value['solidColor'] as int).withValues(alpha: 1);
        }
        darkGlass = value['darkGlass'] == true;
        compact = value['compact'] == true;
        reducedMotion = value['reducedMotion'] == true;
        botanicalRoles = value['botanicalRoles'] != false;
        waitingTone = WaitingTone.values.firstWhere(
          (tone) => tone.name == value['waitingTone'],
          orElse: () => WaitingTone.simple,
        );
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
      solidColor = const Color(0xFFF0F1E7);
      localeTag = 'system';
      darkGlass = false;
      compact = false;
      reducedMotion = false;
      botanicalRoles = true;
      waitingTone = WaitingTone.simple;
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
    String? localeTag,
    WorkspaceBackdrop? mode,
    Color? solidColor,
    bool? darkGlass,
    bool? compact,
    bool? reducedMotion,
    bool? botanicalRoles,
    WaitingTone? waitingTone,
    double? blur,
    double? panelOpacity,
    double? uiFontSize,
  }) {
    if (resetting) return Future<void>.value();
    if (localeTag != null &&
        const ['system', 'zh-CN', 'en', 'ko'].contains(localeTag)) {
      this.localeTag = localeTag;
    }
    this.mode = mode ?? this.mode;
    this.solidColor = solidColor ?? this.solidColor;
    this.darkGlass = darkGlass ?? this.darkGlass;
    this.compact = compact ?? this.compact;
    this.reducedMotion = reducedMotion ?? this.reducedMotion;
    this.botanicalRoles = botanicalRoles ?? this.botanicalRoles;
    this.waitingTone = waitingTone ?? this.waitingTone;
    this.blur = (blur ?? this.blur).clamp(0, 48);
    this.panelOpacity = (panelOpacity ?? this.panelOpacity).clamp(.65, 1);
    this.uiFontSize = uiFontSize == null
        ? this.uiFontSize
        : _normalizeUiFontSize(uiFontSize);
    final revision = ++_preferenceRevision;
    _clearNonNativeError();
    final encoded = jsonEncode({
      'version': 1,
      'localeTag': this.localeTag,
      'mode': this.mode.name,
      'solidColor': this.solidColor.toARGB32(),
      'darkGlass': this.darkGlass,
      'compact': this.compact,
      'reducedMotion': this.reducedMotion,
      'botanicalRoles': this.botanicalRoles,
      'waitingTone': this.waitingTone.name,
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

  Future<bool> resetLocalAppearance() async {
    if (resetting) return false;
    resetting = true;
    saving = true;
    statusKey = null;
    final revision = ++_preferenceRevision;
    _notify();

    // Wallpaper operations are serialized separately because setting an image
    // also queues a preference write. Wait for those operations first, then
    // wait for every preference write they may have queued before removing keys.
    await _pendingWallpaperOperation;
    await _pendingSave;

    var succeeded = false;
    _pendingSave = _pendingSave.then((_) async {
      Object? failure;
      for (final key in const [preferenceKey, wallpaperKey]) {
        try {
          await _storage.remove(key);
        } on Object catch (error) {
          failure ??= error;
        }
      }
      try {
        await _storage.setString(
          preferenceKey,
          jsonEncode({'version': 1, 'localeTag': localeTag}),
        );
      } on Object catch (error) {
        failure ??= error;
      }

      if (revision == _preferenceRevision) {
        succeeded = failure == null;
        if (succeeded) {
          mode = WorkspaceBackdrop.frosted;
          solidColor = const Color(0xFFF0F1E7);
          darkGlass = false;
          compact = false;
          reducedMotion = false;
          botanicalRoles = true;
          waitingTone = WaitingTone.simple;
          blur = 24;
          panelOpacity = .9;
          uiFontSize = defaultUiFontSize;
          wallpaper = null;
          errorKey = null;
          statusKey = 'appearance.resetLocalComplete';
        } else {
          errorKey = 'appearance.resetLocalFailed';
          statusKey = null;
        }
        resetting = false;
        saving = false;
        _notify();
      }
    });
    await _pendingSave;
    return succeeded;
  }

  Future<bool> setWallpaper(Uint8List bytes) {
    if (resetting) return Future<bool>.value(false);
    final operation = _pendingWallpaperOperation.then((_) async {
      if (resetting) return false;
      _clearNonNativeError();
      try {
        await _validateImage(bytes);
        if (resetting) return false;
        // Persist before replacing the visible wallpaper; quota failures preserve it.
        await _storage.setString(wallpaperKey, base64Encode(bytes));
        if (resetting) return false;
        wallpaper = bytes;
        await update(mode: WorkspaceBackdrop.wallpaper);
        return errorKey != 'appearance.saveFailed';
      } on FormatException {
        if (resetting) return false;
        errorKey = 'appearance.invalidImage';
      } catch (_) {
        if (resetting) return false;
        errorKey = 'appearance.saveFailed';
      }
      _notify();
      return false;
    });
    _pendingWallpaperOperation = operation.then<void>(
      (_) {},
      onError: (Object error, StackTrace stackTrace) {
        // A failed image operation must not poison later recovery operations.
      },
    );
    return operation;
  }

  Future<void> removeWallpaper() {
    if (resetting) return Future<void>.value();
    final operation = _pendingWallpaperOperation.then((_) async {
      if (resetting) return;
      try {
        await _storage.remove(wallpaperKey);
        wallpaper = null;
        if (resetting) {
          if (mode == WorkspaceBackdrop.wallpaper) {
            mode = WorkspaceBackdrop.frosted;
          }
          return;
        }
        await update(mode: WorkspaceBackdrop.frosted);
      } catch (_) {
        if (resetting) return;
        errorKey = 'appearance.saveFailed';
        _notify();
      }
    });
    _pendingWallpaperOperation = operation.then<void>(
      (_) {},
      onError: (Object error, StackTrace stackTrace) {
        // A failed image operation must not poison later recovery operations.
      },
    );
    return operation;
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
    statusKey = null;
    if (errorKey != 'appearance.nativeFailed' &&
        errorKey != 'appearance.nativeResetFailed' &&
        errorKey != 'appearance.resetLocalFailed' &&
        errorKey != 'appearance.restoreFailed') {
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
