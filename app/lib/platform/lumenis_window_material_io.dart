import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart' show Color, TargetPlatform;
import 'package:flutter/widgets.dart' show WidgetsFlutterBinding;
import 'package:flutter_acrylic/flutter_acrylic.dart' as acrylic;
import 'package:macos_window_utils/macos/ns_visual_effect_view_material.dart'
    as macos;
import 'package:macos_window_utils/window_manipulator.dart' as macos;

bool get windowMaterialSupported =>
    !kIsWeb &&
    (defaultTargetPlatform == TargetPlatform.windows ||
        defaultTargetPlatform == TargetPlatform.macOS);

Future<void> _requestTail = Future<void>.value();
Future<void>? _windowsInitialization;
Future<void>? _macOSInitialization;

Future<bool> applyWindowMaterial({required bool enabled, required bool dark}) {
  if (!windowMaterialSupported) return Future<bool>.value(false);

  final result = Completer<bool>();
  _requestTail = _requestTail.then((_) async {
    try {
      WidgetsFlutterBinding.ensureInitialized();
      if (defaultTargetPlatform == TargetPlatform.macOS) {
        await _ensureMacOSInitialized();
        await macos.WindowManipulator.overrideMacOSBrightness(dark: dark);
        await macos.WindowManipulator.setMaterial(
          enabled
              ? macos.NSVisualEffectViewMaterial.fullScreenUI
              : macos.NSVisualEffectViewMaterial.windowBackground,
        );
      } else {
        await _ensureWindowsInitialized();
        await acrylic.Window.setEffect(
          effect: enabled
              ? acrylic.WindowEffect.acrylic
              : acrylic.WindowEffect.disabled,
          color: enabled
              ? (dark ? const Color(0xCC151A22) : const Color(0xCCF2F4F7))
              : const Color(0x00000000),
          dark: dark,
        );
      }
      result.complete(true);
    } catch (_) {
      result.complete(false);
    }
  });
  return result.future;
}

Future<void> _ensureWindowsInitialized() {
  return _windowsInitialization ??= _initializeWindows();
}

Future<void> _initializeWindows() async {
  try {
    await acrylic.Window.initialize();
  } catch (_) {
    _windowsInitialization = null;
    rethrow;
  }
}

Future<void> _ensureMacOSInitialized() {
  return _macOSInitialization ??= _initializeMacOS();
}

Future<void> _initializeMacOS() async {
  try {
    await macos.WindowManipulator.initialize();
  } catch (_) {
    _macOSInitialization = null;
    rethrow;
  }
}
