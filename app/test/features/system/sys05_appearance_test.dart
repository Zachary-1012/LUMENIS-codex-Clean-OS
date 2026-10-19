import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart'
    show LogicalKeyboardKey, MethodCall, MethodChannel, rootBundle;
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
  final removalFailures = <String, int>{};
  Completer<void>? get nextRemovalGate => state.nextRemovalGate;
  set nextRemovalGate(Completer<void>? value) => state.nextRemovalGate = value;
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
    final gate = nextRemovalGate;
    nextRemovalGate = null;
    if (gate != null) await gate.future;
    final failuresLeft = removalFailures[key] ?? 0;
    if (failuresLeft > 0) {
      removalFailures[key] = failuresLeft - 1;
      throw StateError('Storage removal failed');
    }
    values.remove(key);
  }
}

class _StoreState {
  bool fail = false;
  int writes = 0;
  Completer<void>? nextRemovalGate;
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
  final removals = <String>[];
  final state = _StoreState();
  Completer<void>? get nextRemovalGate => state.nextRemovalGate;
  set nextRemovalGate(Completer<void>? value) => state.nextRemovalGate = value;
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

  @override
  Future<void> remove(String key) async {
    removals.add(key);
    final gate = nextRemovalGate;
    nextRemovalGate = null;
    if (gate != null) await gate.future;
    values.remove(key);
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
          (const Locale('zh', 'CN'), '界面基础字号', '外观预览', '寰意 OEVIRA · 字号示例'),
          (
            const Locale('en'),
            'Workspace base text size',
            'Appearance preview',
            'OEVIRA · text size sample',
          ),
          (
            const Locale('ko'),
            '작업 공간 기본 글자 크기',
            '모양 미리보기',
            'OEVIRA · 글자 크기 예시',
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
          expect(
            tester.widget<Text>(find.text(sample)).style?.fontSize,
            controller.uiFontSize,
          );
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
        expect(
          tester.widget<Text>(find.text(cases.last.$4)).style?.fontSize,
          controller.uiFontSize,
        );
      } finally {
        semantics.dispose();
        controller.dispose();
      }
    },
  );

  testWidgets(
    'wallpaper editor keeps one-row modes and preview-first order across widths',
    (tester) async {
      final storage = _DeviceStore()..state.writes = 1;
      late final Sys05AppearanceController controller;
      await tester.runAsync(() async {
        controller = Sys05AppearanceController(storage: storage);
        await controller.restore();
        await controller.setWallpaper(await _validPngBytes());
      });
      addTearDown(controller.dispose);

      final cases = [
        (const Size(390, 844), 1.0),
        (const Size(320, 720), 1.7),
        (const Size(1120, 900), 1.0),
      ];
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      for (final (size, textScale) in cases) {
        tester.view.physicalSize = size;
        tester.view.devicePixelRatio = 1;
        await tester.pumpWidget(
          MaterialApp(
            supportedLocales: LumenisLocalizations.supportedLocales,
            localizationsDelegates: const [
              LumenisLocalizations.delegate,
              GlobalMaterialLocalizations.delegate,
              GlobalWidgetsLocalizations.delegate,
              GlobalCupertinoLocalizations.delegate,
            ],
            builder: (context, child) => MediaQuery(
              data: MediaQuery.of(
                context,
              ).copyWith(textScaler: TextScaler.linear(textScale)),
              child: child!,
            ),
            home: Scaffold(
              body: Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 760),
                  child: Sys05AppearanceEditor(controller: controller),
                ),
              ),
            ),
          ),
        );
        await tester.pumpAndSettle();

        final modeTops =
            ['frosted', 'wallpaper', 'desktop', 'white', 'black', 'solid'].map((
              mode,
            ) {
              return tester
                  .getTopLeft(find.byKey(ValueKey('appearance/$mode')))
                  .dy;
            });
        expect(
          modeTops.toSet(),
          hasLength(1),
          reason:
              'Backdrop choices should stay in one horizontal row at $size.',
        );
        expect(
          tester
              .widget<SingleChildScrollView>(
                find.byKey(const ValueKey('appearance/modes-scroll')),
              )
              .scrollDirection,
          Axis.horizontal,
        );

        final preset = find.byKey(
          const ValueKey('appearance/preset/crimson-sunset'),
        );
        final presetButton = tester.widget<OutlinedButton>(preset);
        final presetShape = presetButton.style!.shape!.resolve({});
        expect(presetShape, isA<RoundedRectangleBorder>());
        expect(
          (presetShape! as RoundedRectangleBorder).borderRadius,
          BorderRadius.circular(14),
        );
        expect(tester.getSize(preset).height, greaterThanOrEqualTo(44));

        final orderedTopEdges = [
          tester.getTopLeft(preset).dy,
          tester
              .getTopLeft(
                find.byKey(const ValueKey('appearance/wallpaper-preview')),
              )
              .dy,
          tester
              .getTopLeft(
                find.byKey(const ValueKey('appearance/choose-wallpaper')),
              )
              .dy,
          tester
              .getTopLeft(find.byKey(const ValueKey('appearance/uiFontSize')))
              .dy,
          tester
              .getTopLeft(find.byKey(const ValueKey('appearance/compact')))
              .dy,
          tester
              .getTopLeft(find.byKey(const ValueKey('appearance/reduceMotion')))
              .dy,
        ];
        for (var index = 1; index < orderedTopEdges.length; index++) {
          expect(
            orderedTopEdges[index],
            greaterThan(orderedTopEdges[index - 1]),
            reason: 'Choose → preview → adjust order should hold at $size.',
          );
        }
        expect(tester.takeException(), isNull);
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

  testWidgets(
    'restore failure stays recoverable through settings edits and partial reset failure',
    (tester) async {
      final storage = _DeviceStore()
        ..state.writes = 1
        ..values[Sys05AppearanceController.preferenceKey] = '{broken'
        ..values[Sys05AppearanceController.wallpaperKey] = 'not-base64';
      final controller = Sys05AppearanceController(storage: storage);
      await controller.restore();
      expect(controller.errorKey, 'appearance.restoreFailed');
      expect(
        storage.values.containsKey(Sys05AppearanceController.wallpaperKey),
        isTrue,
      );

      await controller.update(blur: 30);
      expect(controller.errorKey, 'appearance.restoreFailed');
      expect(
        storage.values.containsKey(Sys05AppearanceController.wallpaperKey),
        isTrue,
      );

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
      await tester.pumpAndSettle();
      final resetButton = find.byKey(const ValueKey('appearance/reset-local'));
      expect(resetButton, findsOneWidget);

      final removeGate = Completer<void>();
      storage.nextRemovalGate = removeGate;
      storage.removalFailures[Sys05AppearanceController.wallpaperKey] = 1;
      await tester.ensureVisible(resetButton);
      await tester.pumpAndSettle();
      await tester.tap(resetButton);
      await tester.pump();

      expect(controller.resetting, isTrue);
      expect(resetButton, findsOneWidget);
      expect(tester.widget<TextButton>(resetButton).onPressed, isNull);
      expect(
        find.descendant(
          of: resetButton,
          matching: find.byType(CircularProgressIndicator),
        ),
        findsOneWidget,
      );
      removeGate.complete();
      await tester.pumpAndSettle();

      expect(controller.errorKey, 'appearance.resetLocalFailed');
      expect(
        storage.values.containsKey(Sys05AppearanceController.preferenceKey),
        isFalse,
      );
      expect(
        storage.values.containsKey(Sys05AppearanceController.wallpaperKey),
        isTrue,
      );
      expect(resetButton, findsOneWidget);

      await tester.ensureVisible(resetButton);
      await tester.pumpAndSettle();
      await tester.tap(resetButton);
      await tester.pumpAndSettle();
      expect(controller.errorKey, isNull);
      expect(controller.statusKey, 'appearance.resetLocalComplete');
      expect(controller.mode, WorkspaceBackdrop.frosted);
      expect(controller.blur, 24);
      expect(
        controller.uiFontSize,
        Sys05AppearanceController.defaultUiFontSize,
      );
      expect(
        storage.values.containsKey(Sys05AppearanceController.preferenceKey),
        isFalse,
      );
      expect(
        storage.values.containsKey(Sys05AppearanceController.wallpaperKey),
        isFalse,
      );
      expect(resetButton, findsNothing);

      final reopened = Sys05AppearanceController(storage: storage);
      await reopened.restore();
      expect(reopened.mode, WorkspaceBackdrop.frosted);
      expect(reopened.blur, 24);
      expect(reopened.wallpaper, isNull);
      controller.dispose();
      reopened.dispose();
    },
  );

  test(
    'local reset waits for pending preference writes before removing both keys',
    () async {
      final storage = _ControlledStore()
        ..values[Sys05AppearanceController.wallpaperKey] = 'old-wallpaper';
      final controller = Sys05AppearanceController(storage: storage);
      await controller.restore();

      final pendingUpdate = controller.update(mode: WorkspaceBackdrop.white);
      await storage.waitForAttempts(1);
      final reset = controller.resetLocalAppearance();
      expect(controller.resetting, isTrue);
      await controller.update(mode: WorkspaceBackdrop.black);
      await Future<void>.delayed(Duration.zero);
      expect(storage.removals, isEmpty);
      expect(storage.attempts, hasLength(1));

      storage.attempts.single.succeed();
      await pendingUpdate;
      expect(await reset, isTrue);
      expect(storage.removals, [
        Sys05AppearanceController.preferenceKey,
        Sys05AppearanceController.wallpaperKey,
      ]);
      expect(storage.values, isEmpty);
      expect(controller.mode, WorkspaceBackdrop.frosted);
      expect(controller.resetting, isFalse);

      final reopened = Sys05AppearanceController(storage: storage);
      await reopened.restore();
      expect(reopened.mode, WorkspaceBackdrop.frosted);
      expect(reopened.wallpaper, isNull);
      controller.dispose();
      reopened.dispose();
      await storage.dispose();
    },
  );

  test('local reset waits for an in-flight wallpaper write', () async {
    final bytes = await _validPngBytes();
    final storage = _ControlledStore();
    final controller = Sys05AppearanceController(storage: storage);
    await controller.restore();

    final settingWallpaper = controller.setWallpaper(bytes);
    await storage.waitForAttempts(1);
    expect(storage.attempts.single.key, Sys05AppearanceController.wallpaperKey);
    final reset = controller.resetLocalAppearance();
    await Future<void>.delayed(Duration.zero);
    expect(storage.removals, isEmpty);

    storage.attempts.single.succeed();
    expect(await settingWallpaper, isFalse);
    expect(await reset, isTrue);
    expect(storage.removals, [
      Sys05AppearanceController.preferenceKey,
      Sys05AppearanceController.wallpaperKey,
    ]);
    expect(storage.values, isEmpty);
    expect(storage.attempts, hasLength(1));
    expect(controller.mode, WorkspaceBackdrop.frosted);
    controller.dispose();
    await storage.dispose();
  });

  test('local reset waits for an in-flight wallpaper removal', () async {
    final storage = _ControlledStore()
      ..values[Sys05AppearanceController.wallpaperKey] = 'old-wallpaper';
    final controller = Sys05AppearanceController(storage: storage);
    await controller.restore();
    final removeGate = Completer<void>();
    storage.nextRemovalGate = removeGate;

    final removingWallpaper = controller.removeWallpaper();
    await Future<void>.delayed(Duration.zero);
    expect(storage.removals, [Sys05AppearanceController.wallpaperKey]);
    final reset = controller.resetLocalAppearance();
    await Future<void>.delayed(Duration.zero);
    expect(storage.removals, [Sys05AppearanceController.wallpaperKey]);

    removeGate.complete();
    await removingWallpaper;
    expect(await reset, isTrue);
    expect(storage.removals, [
      Sys05AppearanceController.wallpaperKey,
      Sys05AppearanceController.preferenceKey,
      Sys05AppearanceController.wallpaperKey,
    ]);
    expect(storage.values, isEmpty);
    expect(storage.attempts, isEmpty);
    controller.dispose();
    await storage.dispose();
  });

  testWidgets(
    'built-in wallpaper preset stores and restores the bundled bytes',
    (tester) async {
      final storage = _DeviceStore()..state.writes = 1;
      late final Sys05AppearanceController controller;
      await tester.runAsync(() async {
        controller = Sys05AppearanceController(storage: storage);
        await controller.restore();
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
      await tester.pumpAndSettle();

      final expectedBytes = await tester.runAsync(() async {
        final image = await rootBundle.load(
          'assets/wallpapers/crimson-sunset.jpg',
        );
        return Uint8List.fromList(
          image.buffer.asUint8List(image.offsetInBytes, image.lengthInBytes),
        );
      });
      expect(expectedBytes, isNotNull);
      final bytes = expectedBytes!;
      final preset = find.byKey(
        const ValueKey('appearance/preset/crimson-sunset'),
      );
      expect(preset, findsOneWidget);
      await tester.runAsync(() async {
        final wallpaperApplied = Completer<void>();
        void onAppearanceChanged() {
          if (controller.mode == WorkspaceBackdrop.wallpaper &&
              controller.wallpaper != null &&
              !controller.saving &&
              !wallpaperApplied.isCompleted) {
            wallpaperApplied.complete();
          }
        }

        controller.addListener(onAppearanceChanged);
        try {
          await tester.tap(preset);
          await wallpaperApplied.future.timeout(const Duration(seconds: 10));
        } finally {
          controller.removeListener(onAppearanceChanged);
        }
      });
      await tester.pumpAndSettle();

      expect(controller.mode, WorkspaceBackdrop.wallpaper);
      expect(controller.wallpaper, orderedEquals(bytes));
      expect(
        storage.values[Sys05AppearanceController.wallpaperKey],
        base64Encode(bytes),
      );

      late final Sys05AppearanceController reopened;
      await tester.runAsync(() async {
        reopened = Sys05AppearanceController(storage: storage);
        await reopened.restore();
      });
      expect(reopened.mode, WorkspaceBackdrop.wallpaper);
      expect(reopened.wallpaper, orderedEquals(bytes));
      controller.dispose();
      reopened.dispose();
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

Future<Uint8List> _validPngBytes() async {
  final recorder = ui.PictureRecorder();
  final canvas = Canvas(recorder);
  canvas.drawRect(
    const Rect.fromLTWH(0, 0, 8, 8),
    Paint()..color = Colors.orange,
  );
  final picture = recorder.endRecording();
  ui.Image? image;
  try {
    image = await picture.toImage(8, 8);
    final data = await image.toByteData(format: ui.ImageByteFormat.png);
    return Uint8List.fromList(
      data!.buffer.asUint8List(data.offsetInBytes, data.lengthInBytes),
    );
  } finally {
    image?.dispose();
    picture.dispose();
  }
}
