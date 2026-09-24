import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:lumenis_app/platform/lumenis_window_material.dart';
import 'package:lumenis_app/platform/lumenis_window_material_stub.dart'
    as web_stub;

const _acrylicChannel = MethodChannel('com.alexmercerind/flutter_acrylic');
const _macOSChannel = MethodChannel('macos_window_utils/window_manipulator');

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  tearDown(() {
    debugDefaultTargetPlatformOverride = null;
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
      ..setMockMethodCallHandler(_acrylicChannel, null)
      ..setMockMethodCallHandler(_macOSChannel, null);
  });

  test('web fallback reports unsupported without a platform call', () async {
    expect(web_stub.windowMaterialSupported, isFalse);
    expect(
      await web_stub.applyWindowMaterial(enabled: true, dark: false),
      isFalse,
    );
  });

  test('unsupported native targets do not call either plugin', () async {
    final calls = <MethodCall>[];
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
      ..setMockMethodCallHandler(_acrylicChannel, (call) async {
        calls.add(call);
        return null;
      })
      ..setMockMethodCallHandler(_macOSChannel, (call) async {
        calls.add(call);
        return null;
      });

    for (final platform in [
      TargetPlatform.android,
      TargetPlatform.iOS,
      TargetPlatform.linux,
    ]) {
      debugDefaultTargetPlatformOverride = platform;
      expect(LumenisWindowMaterial.supported, isFalse);
      expect(
        await LumenisWindowMaterial.apply(enabled: true, dark: false),
        isFalse,
      );
    }
    expect(calls, isEmpty);
  });

  test(
    'Windows material changes run serially and failures return false',
    () async {
      debugDefaultTargetPlatformOverride = TargetPlatform.windows;
      final calls = <MethodCall>[];
      final firstEffectStarted = Completer<void>();
      final releaseFirstEffect = Completer<void>();
      var effectCalls = 0;
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(_acrylicChannel, (call) async {
            calls.add(call);
            if (call.method == 'SetEffect') {
              effectCalls += 1;
              if (effectCalls == 1) {
                firstEffectStarted.complete();
                await releaseFirstEffect.future;
              }
            }
            return null;
          });

      expect(LumenisWindowMaterial.supported, isTrue);
      final enable = LumenisWindowMaterial.apply(enabled: true, dark: false);
      await firstEffectStarted.future;
      final disable = LumenisWindowMaterial.apply(enabled: false, dark: true);
      await Future<void>.delayed(Duration.zero);
      expect(effectCalls, 1);

      releaseFirstEffect.complete();
      expect(await enable, isTrue);
      expect(await disable, isTrue);
      final effects = calls
          .where((call) => call.method == 'SetEffect')
          .map((call) => (call.arguments as Map<Object?, Object?>)['effect'])
          .toList();
      expect(effects, [4, 0]);

      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(_acrylicChannel, (call) async {
            if (call.method == 'SetEffect') {
              throw PlatformException(code: 'native-failure');
            }
            return null;
          });
      expect(
        await LumenisWindowMaterial.apply(enabled: true, dark: true),
        isFalse,
      );
    },
  );

  test(
    'macOS awaits system material calls and reports plugin failures',
    () async {
      debugDefaultTargetPlatformOverride = TargetPlatform.macOS;
      final calls = <MethodCall>[];
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(_macOSChannel, (call) async {
            calls.add(call);
            return null;
          });

      expect(LumenisWindowMaterial.supported, isTrue);
      expect(
        await LumenisWindowMaterial.apply(enabled: true, dark: false),
        isTrue,
      );
      expect(
        await LumenisWindowMaterial.apply(enabled: false, dark: true),
        isTrue,
      );
      expect(calls.map((call) => call.method), [
        'initialize',
        'overrideMacOSBrightness',
        'setMaterial',
        'overrideMacOSBrightness',
        'setMaterial',
      ]);
      final brightness = calls
          .where((call) => call.method == 'overrideMacOSBrightness')
          .map((call) => (call.arguments as Map<Object?, Object?>)['dark'])
          .toList();
      expect(brightness, [false, true]);
      final materials = calls
          .where((call) => call.method == 'setMaterial')
          .map((call) => (call.arguments as Map<Object?, Object?>)['material'])
          .toSet();
      expect(materials, hasLength(2));

      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(_macOSChannel, (call) async {
            if (call.method == 'overrideMacOSBrightness') {
              throw PlatformException(code: 'native-failure');
            }
            return null;
          });
      expect(
        await LumenisWindowMaterial.apply(enabled: true, dark: true),
        isFalse,
      );
    },
  );
}
