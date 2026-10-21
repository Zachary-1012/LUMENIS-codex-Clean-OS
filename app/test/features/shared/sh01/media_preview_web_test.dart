@TestOn('browser')
library;

import 'dart:typed_data';
import 'dart:ui_web' as ui_web;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/features/shared/sh01/media_preview_web.dart';
import 'package:lumenis_app/l10n/lumenis_localizations.dart';
import 'package:web/web.dart' as web;

// A short silent PCM fixture tests browser focus, not production audio quality.
Uint8List _silentWave() {
  final bytes = Uint8List(2044);
  final data = ByteData.sublistView(bytes);
  void word(int offset, String value) =>
      bytes.setRange(offset, offset + value.length, value.codeUnits);
  word(0, 'RIFF');
  data.setUint32(4, bytes.length - 8, Endian.little);
  word(8, 'WAVEfmt ');
  data.setUint32(16, 16, Endian.little);
  data.setUint16(20, 1, Endian.little);
  data.setUint16(22, 1, Endian.little);
  data.setUint32(24, 8000, Endian.little);
  data.setUint32(28, 16000, Endian.little);
  data.setUint16(32, 2, Endian.little);
  data.setUint16(34, 16, Endian.little);
  word(36, 'data');
  data.setUint32(40, bytes.length - 44, Endian.little);
  return bytes;
}

void main() {
  testWidgets('queued seek survives metadata loading and source replacement', (
    tester,
  ) async {
    final environment = ui_web.TestEnvironment.instance;
    ui_web.TestEnvironment.setUp(
      ui_web.TestEnvironment(
        ignorePlatformMessages: false,
        forceTestFonts: environment.forceTestFonts,
        disableFontFallbacks: environment.disableFontFallbacks,
        keepSemanticsDisabledOnUpdate:
            environment.keepSemanticsDisabledOnUpdate,
        defaultToTestUrlStrategy: environment.defaultToTestUrlStrategy,
      ),
    );
    addTearDown(() => ui_web.TestEnvironment.setUp(environment));
    final positions = <Duration>[];
    var file = ContentProjectFile(
      bytes: _silentWave(),
      filename: 'seek-fixture.wav',
      mediaType: 'audio/wav',
    );
    var target = const Duration(milliseconds: 50);
    var request = 1;
    Future<web.HTMLMediaElement> mount() async {
      await tester.pumpWidget(
        MaterialApp(
          locale: const Locale('en'),
          localizationsDelegates: const [LumenisLocalizations.delegate],
          home: Scaffold(
            body: SizedBox(
              width: 400,
              height: 220,
              child: MediaPreview(
                file: file,
                seekPosition: target,
                seekRequest: request,
                onPositionChanged: positions.add,
              ),
            ),
          ),
        ),
      );
      await tester.runAsync(() => Future<void>.delayed(Duration.zero));
      await tester.pumpAndSettle();
      final surface = tester.widget<PlatformViewSurface>(
        find.byType(PlatformViewSurface),
      );
      final media =
          ui_web.platformViewRegistry.getViewById(surface.controller.viewId)
              as web.HTMLMediaElement;
      if (!media.isConnected) {
        // The registry resolves the first child of its engine-owned wrapper.
        // Moving only the media would empty that wrapper and break the next
        // getViewById call when the same source is mounted again.
        final platformView = media.parentElement!;
        web.document.body!.appendChild(platformView);
        addTearDown(platformView.remove);
      }
      return media;
    }

    Future<void> expectPosition(web.HTMLMediaElement media) async {
      await tester.runAsync(() async {
        // Wait for real browser decode/seek events, not Flutter's fake clock.
        final deadline = DateTime.now().add(const Duration(seconds: 5));
        while ((!media.duration.isFinite ||
                media.seeking ||
                (media.currentTime - target.inMicroseconds / 1000000).abs() >
                    .005) &&
            DateTime.now().isBefore(deadline)) {
          await Future<void>.delayed(const Duration(milliseconds: 10));
        }
      });
      expect(media.error, isNull);
      expect(media.duration, closeTo(.125, .005));
      expect(media.currentTime, closeTo(target.inMicroseconds / 1000000, .005));
      expect(media.paused, isTrue, reason: 'Seeking must not start playback');
      expect(
        positions.any((p) => (p - target).inMilliseconds.abs() <= 5),
        isTrue,
        reason: 'The shared playhead receives the decoded position',
      );
      expect(tester.takeException(), isNull);
    }

    final first = await mount();
    addTearDown(() => first.remove());
    await expectPosition(first);
    target = const Duration(milliseconds: 90);
    request++;
    expect(await mount(), same(first));
    await expectPosition(first);

    file = ContentProjectFile(
      bytes: _silentWave(),
      filename: 'replacement-fixture.wav',
      mediaType: 'audio/wav',
    );
    target = const Duration(milliseconds: 30);
    request++;
    positions.clear();
    final replacement = await mount();
    addTearDown(() => replacement.remove());
    expect(replacement, isNot(same(first)));
    expect(first.hasAttribute('src'), isFalse);
    await expectPosition(replacement);
    await tester.pumpWidget(const SizedBox());
    await tester.pumpAndSettle();
    expect(replacement.hasAttribute('src'), isFalse);
    expect(tester.takeException(), isNull);
  });

  final originalReporter = reportTestException;
  reportTestException = (details, description) {
    // Keep the standard failure, and expose its cause in browser JSON reports.
    // ignore: avoid_print
    print(
      'BROWSER_TEST_CAUSE: ${details.exceptionAsString()}\n${details.stack}',
    );
    originalReporter(details, description);
  };
  testWidgets('native media focus releases stale Flutter activation target', (
    tester,
  ) async {
    // flutter test normally drops platform messages before the real engine can
    // create HtmlElementView. Enable real engine messages for this DOM test.
    final environment = ui_web.TestEnvironment.instance;
    ui_web.TestEnvironment.setUp(
      ui_web.TestEnvironment(
        ignorePlatformMessages: false,
        forceTestFonts: environment.forceTestFonts,
        disableFontFallbacks: environment.disableFontFallbacks,
        keepSemanticsDisabledOnUpdate:
            environment.keepSemanticsDisabledOnUpdate,
        defaultToTestUrlStrategy: environment.defaultToTestUrlStrategy,
      ),
    );
    addTearDown(() => ui_web.TestEnvironment.setUp(environment));
    void expectNoFrameworkException(String stage) {
      final exception = tester.takeException();
      expect(
        exception,
        isNull,
        reason:
            'Unexpected Flutter framework exception after $stage: $exception',
      );
    }

    final triggerFocus = FocusNode();
    addTearDown(triggerFocus.dispose);
    var activations = 0;
    await tester.pumpWidget(
      MaterialApp(
        locale: const Locale('en'),
        localizationsDelegates: const [LumenisLocalizations.delegate],
        home: Scaffold(
          body: Column(
            children: [
              OutlinedButton(
                focusNode: triggerFocus,
                onPressed: () => activations++,
                child: const Text('Versions'),
              ),
              SizedBox(
                width: 400,
                height: 220,
                child: MediaPreview(
                  file: ContentProjectFile(
                    bytes: _silentWave(),
                    filename: 'focus-fixture.wav',
                    mediaType: 'audio/wav',
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
    expectNoFrameworkException('initial widget mount');
    expect(find.byType(HtmlElementView), findsOneWidget);
    // The engine responds outside the fake widget clock. Yield one browser
    // turn for that response, then flush the widget's creation callback.
    await tester.runAsync(() => Future<void>.delayed(Duration.zero));
    await tester.pumpAndSettle();
    expectNoFrameworkException('platform-view creation');
    final surface = tester.widget<PlatformViewSurface>(
      find.byType(PlatformViewSurface),
    );
    final media =
        ui_web.platformViewRegistry.getViewById(surface.controller.viewId)
            as web.HTMLMediaElement;
    expect(media.controls, isTrue, reason: 'Product creation callback ran');
    expect(media.getAttribute('src'), startsWith('blob:'));
    // Browser tests do not paint the platform view. Attach its real element to
    // exercise focusin and browser ownership without mocking the focus bridge.
    final platformView = media.parentElement!;
    web.document.body!.appendChild(platformView);
    addTearDown(platformView.remove);
    triggerFocus.requestFocus();
    await tester.pump();
    expectNoFrameworkException('trigger button focus');
    expect(triggerFocus.hasPrimaryFocus, isTrue);
    await tester.runAsync(() async {
      media.focus();
      await Future<void>.delayed(Duration.zero);
    });
    await tester.pump();
    expectNoFrameworkException('native media focus');
    expect(web.document.activeElement, media);
    expect(triggerFocus.hasFocus, isFalse);

    await tester.sendKeyEvent(LogicalKeyboardKey.space);
    expectNoFrameworkException('Space while media is focused');
    expect(activations, 0);
    expect(media.controls, isTrue);
    final mediaFocus = FocusManager.instance.primaryFocus!;
    for (final key in [
      LogicalKeyboardKey.space,
      LogicalKeyboardKey.arrowRight,
      LogicalKeyboardKey.tab,
      LogicalKeyboardKey.escape,
    ]) {
      expect(
        mediaFocus.onKeyEvent!(
          mediaFocus,
          KeyDownEvent(
            physicalKey: PhysicalKeyboardKey.space,
            logicalKey: key,
            timeStamp: Duration.zero,
          ),
        ),
        KeyEventResult.skipRemainingHandlers,
      );
    }

    expect(
      mediaFocus.onKeyEvent!(
        mediaFocus,
        const KeyDownEvent(
          physicalKey: PhysicalKeyboardKey.keyA,
          logicalKey: LogicalKeyboardKey.keyA,
          timeStamp: Duration.zero,
        ),
      ),
      KeyEventResult.ignored,
    );
    await tester.sendKeyDownEvent(LogicalKeyboardKey.controlLeft);
    expectNoFrameworkException('Control key down');
    expect(
      mediaFocus.onKeyEvent!(
        mediaFocus,
        const KeyDownEvent(
          physicalKey: PhysicalKeyboardKey.space,
          logicalKey: LogicalKeyboardKey.space,
          timeStamp: Duration.zero,
        ),
      ),
      KeyEventResult.ignored,
    );
    await tester.sendKeyUpEvent(LogicalKeyboardKey.controlLeft);
    expectNoFrameworkException('Control key up');

    media.blur();
    triggerFocus.requestFocus();
    await tester.pump();
    expectNoFrameworkException('return to trigger button focus');
    await tester.sendKeyEvent(LogicalKeyboardKey.space);
    expectNoFrameworkException('Space after returning to the button');
    expect(activations, 1);
    await tester.pumpWidget(const SizedBox());
    expectNoFrameworkException('media widget removal');
    await tester.pumpAndSettle();
    expectNoFrameworkException('final settle');
    expect(media.hasAttribute('src'), isFalse);
    expect(tester.takeException(), isNull);
  });
}
