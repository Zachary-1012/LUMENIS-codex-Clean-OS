import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart'
    show LogicalKeyboardKey, MethodCall, MethodChannel;
import 'package:flutter/semantics.dart' show SemanticsData, SemanticsNode;
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:lumenis_app/features/system/sys05/sys05_appearance_editor.dart';
import 'package:lumenis_app/features/system/sys05/sys05_appearance_controller.dart';
import 'package:lumenis_app/l10n/lumenis_localizations.dart';
import 'package:shared_preferences/shared_preferences.dart';

const _fileSelectorChannel = MethodChannel('plugins.flutter.io/file_selector');

class _DeviceStore extends Fake implements SharedPreferencesAsync {
  final values = <String, String>{};
  final state = _StoreState();
  bool get fail => state.fail;
  set fail(bool value) => state.fail = value;
  @override
  Future<String?> getString(String key) async => values[key];
  @override
  Future<void> setString(String key, String value) async {
    if (fail) throw StateError('Storage is full');
    if (state.writes++ == 0) {
      await Future<void>.delayed(const Duration(milliseconds: 15));
    }
    values[key] = value;
  }

  @override
  Future<void> remove(String key) async {
    values.remove(key);
  }
}

class _StoreState {
  bool fail = false;
  int writes = 0;
}

class _WriteAttempt {
  _WriteAttempt(this.key, this.value);

  final String key;
  final String value;
  final completion = Completer<void>();

  void succeed() => completion.complete();
  void fail() => completion.completeError(StateError('Storage is full'));
}

class _ControlledStore extends Fake implements SharedPreferencesAsync {
  final values = <String, String>{};
  final attempts = <_WriteAttempt>[];
  final _attemptsChanged = StreamController<int>.broadcast(sync: true);

  @override
  Future<String?> getString(String key) async => values[key];

  @override
  Future<void> setString(String key, String value) async {
    final attempt = _WriteAttempt(key, value);
    attempts.add(attempt);
    _attemptsChanged.add(attempts.length);
    await attempt.completion.future;
    values[key] = value;
  }

  Future<void> waitForAttempts(int count) async {
    while (attempts.length < count) {
      await _attemptsChanged.stream.first;
    }
  }

  Future<void> dispose() => _attemptsChanged.close();
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test(
    'UI base font size clamps and round trips in local preferences',
    () async {
      final storage = _DeviceStore()
        ..values[Sys05AppearanceController.preferenceKey] =
            '{"mode":"white","uiFontSize":1e999}';
      final controller = Sys05AppearanceController(storage: storage);
      await controller.restore();

      expect(controller.mode, WorkspaceBackdrop.white);
      expect(controller.uiFontSize, 14);

      await controller.update(uiFontSize: 12);
      expect(controller.uiFontSize, 13);
      await controller.update(uiFontSize: 18.5);
      expect(controller.uiFontSize, 18);

      final reopened = Sys05AppearanceController(storage: storage);
      await reopened.restore();
      expect(reopened.uiFontSize, 18);

      await reopened.update(uiFontSize: double.infinity);
      expect(reopened.uiFontSize, 14);
      controller.dispose();
      reopened.dispose();
    },
  );

  testWidgets(
    'font size control shows a localized value and appearance preview',
    (tester) async {
      tester.view.physicalSize = const Size(900, 1200);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      final storage = _DeviceStore();
      final controller = Sys05AppearanceController(storage: storage);
      await controller.restore();
      final semantics = tester.ensureSemantics();
      try {
        final cases = [
          (const Locale('zh', 'CN'), '界面基础字号', '外观预览', '序境 LUMENIS · 字号示例'),
          (
            const Locale('en'),
            'Workspace base text size',
            'Appearance preview',
            'LUMENIS · text size sample',
          ),
          (
            const Locale('ko'),
            '작업 공간 기본 글자 크기',
            '모양 미리보기',
            'LUMENIS · 글자 크기 예시',
          ),
        ];

        for (final (locale, label, preview, sample) in cases) {
          await tester.pumpWidget(
            MaterialApp(
              locale: locale,
              supportedLocales: LumenisLocalizations.supportedLocales,
              localizationsDelegates: const [
                LumenisLocalizations.delegate,
                GlobalMaterialLocalizations.delegate,
                GlobalWidgetsLocalizations.delegate,
                GlobalCupertinoLocalizations.delegate,
              ],
              home: Scaffold(
                body: Sys05AppearanceEditor(controller: controller),
              ),
            ),
          );
          await tester.pumpAndSettle();
          expect(find.text(label), findsOneWidget);
          expect(find.text('14 px'), findsOneWidget);
          expect(find.text(preview), findsOneWidget);
          expect(find.text(sample), findsOneWidget);
          expect(
            find.byKey(const ValueKey('appearance/uiFontSize')),
            findsOneWidget,
          );
          final fontNode = tester.getSemantics(
            find.byKey(const ValueKey('appearance/uiFontSize')),
          );
          expect(fontNode.getSemanticsData().label, contains(label));
          final fontSemantics = _rangeSemantics(fontNode);
          expect(fontSemantics.value, '14 px');
          expect(fontSemantics.hasAction(ui.SemanticsAction.increase), isTrue);
          expect(fontSemantics.hasAction(ui.SemanticsAction.decrease), isTrue);
        }

        final blurNode = tester.getSemantics(
          find.byKey(const ValueKey('appearance/blur')),
        );
        expect(blurNode.getSemanticsData().label, contains('배경 흐림'));
        final blurSemantics = _rangeSemantics(blurNode);
        expect(blurSemantics.value, '24 px');
        final opacityNode = tester.getSemantics(
          find.byKey(const ValueKey('appearance/panelOpacity')),
        );
        expect(opacityNode.getSemanticsData().label, contains('콘텐츠 불투명도'));
        final opacitySemantics = _rangeSemantics(opacityNode);
        expect(opacitySemantics.value, '90%');

        final slider = find.byKey(const ValueKey('appearance/uiFontSize'));
        await tester.ensureVisible(slider);
        final beforeKeyboardChange = controller.uiFontSize;
        await tester.tap(slider);
        await tester.sendKeyEvent(LogicalKeyboardKey.arrowRight);
        await tester.pumpAndSettle();
        expect(controller.uiFontSize, greaterThan(beforeKeyboardChange));
        expect(
          find.text('${controller.uiFontSize.round()} px'),
          findsOneWidget,
        );
      } finally {
        semantics.dispose();
        controller.dispose();
      }
    },
  );

  testWidgets(
    'selecting wallpaper opens the picker and cancel keeps the current mode',
    (tester) async {
      final storage = _DeviceStore();
      final controller = Sys05AppearanceController(storage: storage);
      await controller.restore();
      final update = controller.update(mode: WorkspaceBackdrop.white);
      await tester.pump(const Duration(milliseconds: 20));
      await update;

      final calls = <MethodCall>[];
      final messenger =
          TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger;
      messenger.setMockMethodCallHandler(_fileSelectorChannel, (call) async {
        calls.add(call);
        return null;
      });
      addTearDown(() {
        messenger.setMockMethodCallHandler(_fileSelectorChannel, null);
      });

      await tester.pumpWidget(
        MaterialApp(
          supportedLocales: LumenisLocalizations.supportedLocales,
          localizationsDelegates: const [
            LumenisLocalizations.delegate,
            GlobalMaterialLocalizations.delegate,
            GlobalWidgetsLocalizations.delegate,
            GlobalCupertinoLocalizations.delegate,
          ],
          home: Scaffold(body: Sys05AppearanceEditor(controller: controller)),
        ),
      );
      await tester.tap(find.byKey(const ValueKey('appearance/wallpaper')));
      await tester.pumpAndSettle();

      expect(calls, hasLength(1));
      expect(calls.single.method, 'openFile');
      expect(controller.mode, WorkspaceBackdrop.white);
      expect(controller.wallpaper, isNull);
      controller.dispose();
    },
  );

  test(
    'valid local wallpaper can be restored and removed without network storage',
    () async {
      final recorder = ui.PictureRecorder();
      final canvas = Canvas(recorder);
      canvas.drawRect(
        const Rect.fromLTWH(0, 0, 8, 8),
        Paint()..color = Colors.orange,
      );
      final picture = recorder.endRecording();
      final image = await picture.toImage(8, 8);
      final data = await image.toByteData(format: ui.ImageByteFormat.png);
      final bytes = data!.buffer.asUint8List();
      final storage = _DeviceStore();
      final c = Sys05AppearanceController(storage: storage);
      await c.restore();
      c.reportError('appearance.nativeFailed');
      expect(await c.setWallpaper(bytes), isTrue);
      expect(c.errorKey, 'appearance.nativeFailed');
      final reopened = Sys05AppearanceController(storage: storage);
      await reopened.restore();
      expect(reopened.mode, WorkspaceBackdrop.wallpaper);
      expect(reopened.wallpaper, orderedEquals(bytes));
      await reopened.removeWallpaper();
      expect(
        storage.values.containsKey(Sys05AppearanceController.wallpaperKey),
        isFalse,
      );
      expect(reopened.wallpaper, isNull);
      c.dispose();
      reopened.dispose();
      image.dispose();
      picture.dispose();
    },
  );

  test(
    'device theme survives a new controller and rapid updates keep newest value',
    () async {
      final storage = _DeviceStore();
      final first = Sys05AppearanceController(storage: storage);
      await first.restore();
      final a = first.update(mode: WorkspaceBackdrop.black);
      final b = first.update(
        mode: WorkspaceBackdrop.solid,
        solidColor: const Color(0xFF123456),
        blur: 12,
      );
      await Future.wait([a, b]);
      final reopened = Sys05AppearanceController(storage: storage);
      await reopened.restore();
      expect(reopened.mode, WorkspaceBackdrop.solid);
      expect(reopened.solidColor, const Color(0xFF123456));
      expect(reopened.blur, 12);
      expect(reopened.isDark, isTrue);
      first.dispose();
      reopened.dispose();
    },
  );

  test(
    'an older failed preference write cannot override a newer success',
    () async {
      final storage = _ControlledStore();
      final c = Sys05AppearanceController(storage: storage);
      await c.restore();

      final older = c.update(mode: WorkspaceBackdrop.black);
      final latest = c.update(mode: WorkspaceBackdrop.white);
      await storage.waitForAttempts(1);
      storage.attempts[0].fail();
      await storage.waitForAttempts(2);
      expect(c.errorKey, isNull);
      expect(c.saving, isTrue);

      storage.attempts[1].succeed();
      await Future.wait([older, latest]);

      expect(c.errorKey, isNull);
      expect(c.saving, isFalse);
      expect(
        jsonDecode(
          storage.values[Sys05AppearanceController.preferenceKey]!,
        )['mode'],
        'white',
      );
      c.dispose();
      await storage.dispose();
    },
  );

  test(
    'a newer failed preference write owns the final error and saving state',
    () async {
      final storage = _ControlledStore();
      final c = Sys05AppearanceController(storage: storage);
      await c.restore();

      final older = c.update(mode: WorkspaceBackdrop.black);
      final latest = c.update(mode: WorkspaceBackdrop.white);
      await storage.waitForAttempts(1);
      storage.attempts[0].succeed();
      await storage.waitForAttempts(2);
      expect(c.saving, isTrue);
      expect(c.errorKey, isNull);

      storage.attempts[1].fail();
      await Future.wait([older, latest]);

      expect(c.errorKey, 'appearance.saveFailed');
      expect(c.saving, isFalse);
      expect(
        jsonDecode(
          storage.values[Sys05AppearanceController.preferenceKey]!,
        )['mode'],
        'black',
      );
      c.dispose();
      await storage.dispose();
    },
  );

  test('preference writes do not clear native appearance errors', () async {
    final storage = _DeviceStore();
    final c = Sys05AppearanceController(storage: storage);
    await c.restore();
    c.reportError('appearance.nativeFailed');

    await c.update(mode: WorkspaceBackdrop.black);

    expect(c.errorKey, 'appearance.nativeFailed');
    c.dispose();
  });

  test(
    'invalid wallpaper preserves the previous preference and stores no image',
    () async {
      final storage = _DeviceStore();
      final c = Sys05AppearanceController(storage: storage);
      await c.restore();
      await c.update(mode: WorkspaceBackdrop.white);
      expect(await c.setWallpaper(Uint8List.fromList([1, 2, 3])), isFalse);
      expect(c.mode, WorkspaceBackdrop.white);
      expect(c.errorKey, 'appearance.invalidImage');
      expect(
        storage.values.containsKey(Sys05AppearanceController.wallpaperKey),
        isFalse,
      );
      c.dispose();
    },
  );

  test(
    'quota failure remains visible and never replaces persisted preference',
    () async {
      final storage = _DeviceStore();
      final c = Sys05AppearanceController(storage: storage);
      await c.restore();
      await c.update(mode: WorkspaceBackdrop.white);
      storage.fail = true;
      await c.update(mode: WorkspaceBackdrop.black);
      expect(c.errorKey, 'appearance.saveFailed');
      expect(c.saving, isFalse);
      expect(
        jsonDecode(
          storage.values[Sys05AppearanceController.preferenceKey]!,
        )['mode'],
        'white',
      );
      c.dispose();
    },
  );

  test(
    'corrupt preferences fall back explicitly and never become a successful restore',
    () async {
      final storage = _DeviceStore()
        ..values[Sys05AppearanceController.preferenceKey] = '{broken';
      final c = Sys05AppearanceController(storage: storage);
      await c.restore();
      expect(c.loaded, isTrue);
      expect(c.mode, WorkspaceBackdrop.frosted);
      expect(c.errorKey, 'appearance.restoreFailed');
      c.dispose();
    },
  );
}

// Flutter exposes the named parent and adjustable range as separate nodes.
SemanticsData _rangeSemantics(SemanticsNode root) {
  SemanticsData? range;
  void inspect(SemanticsNode node) {
    final data = node.getSemanticsData();
    if (data.hasAction(ui.SemanticsAction.increase) ||
        data.hasAction(ui.SemanticsAction.decrease)) {
      range = data;
    }
    node.visitChildren((child) {
      inspect(child);
      return true;
    });
  }

  inspect(root);
  expect(
    range,
    isNotNull,
    reason: 'The named control must expose an adjustable range.',
  );
  return range!;
}
