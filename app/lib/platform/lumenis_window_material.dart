import 'lumenis_window_material_stub.dart'
    if (dart.library.io) 'lumenis_window_material_io.dart'
    as platform;

/// Applies the desktop system window material when the host supports it.
///
/// This adapter reports whether the platform call completed. It cannot verify
/// the operating system's final rendered appearance.
class LumenisWindowMaterial {
  const LumenisWindowMaterial._();

  static bool get supported => platform.windowMaterialSupported;

  static Future<bool> apply({required bool enabled, required bool dark}) =>
      platform.applyWindowMaterial(enabled: enabled, dark: dark);
}
