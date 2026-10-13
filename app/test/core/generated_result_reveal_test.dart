import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/generated_result_reveal.dart';

void main() {
  testWidgets('new result starts after stable measured layout', (tester) async {
    final host = _RevealHost();
    addTearDown(host.dispose);

    await tester.pumpWidget(host.build());
    final resultRectBefore = tester.getRect(find.byKey(host.resultKey));
    _expectNoReveal(tester);
    await _pumpPreparationWindow(tester);

    expect(
      find.byKey(const ValueKey('generated-result-reveal/paint')),
      findsOneWidget,
    );
    expect(tester.getRect(find.byKey(host.resultKey)), resultRectBefore);

    await tester.tap(
      find.byKey(const ValueKey('generated-result-reveal/skip')),
    );
    await tester.pump();

    _expectNoReveal(tester);
    expect(tester.getRect(find.byKey(host.resultKey)), resultRectBefore);
  });

  testWidgets('registered Material icon font remains eligible for reveal', (
    tester,
  ) async {
    final host = _RevealHost();
    addTearDown(host.dispose);

    await tester.pumpWidget(host.build(includeBundledIcon: true));
    await _pumpPreparationWindow(tester);

    expect(
      find.byKey(const ValueKey('generated-result-reveal/paint')),
      findsOneWidget,
    );
  });

  testWidgets('scroll cancels preparation before the reveal can start', (
    tester,
  ) async {
    final host = _RevealHost();
    addTearDown(host.dispose);

    await tester.pumpWidget(host.build());
    expect(host.revealKey.currentState?.isPlaying, isFalse);

    host.scrollController.jumpTo(40);
    await _pumpPreparationWindow(tester);

    _expectNoReveal(tester);
  });

  testWidgets('pointer interaction cancels preparation before the reveal', (
    tester,
  ) async {
    final host = _RevealHost();
    addTearDown(host.dispose);

    await tester.pumpWidget(host.build());
    expect(host.revealKey.currentState?.isPlaying, isFalse);

    await tester.tap(find.text('真实结果标题'));
    await _pumpPreparationWindow(tester);

    _expectNoReveal(tester);
  });

  testWidgets('backgrounding cancels preparation before the reveal', (
    tester,
  ) async {
    final host = _RevealHost();
    addTearDown(host.dispose);

    await tester.pumpWidget(host.build());
    expect(host.revealKey.currentState?.isPlaying, isFalse);

    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.inactive);
    await _pumpPreparationWindow(tester);

    _expectNoReveal(tester);
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
  });

  testWidgets('font change invalidates preparation geometry', (tester) async {
    final host = _RevealHost();
    addTearDown(host.dispose);

    await tester.pumpWidget(host.build());
    expect(host.revealKey.currentState?.isPlaying, isFalse);

    await tester.binding.defaultBinaryMessenger.handlePlatformMessage(
      SystemChannels.system.name,
      SystemChannels.system.codec.encodeMessage({'type': 'fontsChange'}),
      null,
    );
    await _pumpPreparationWindow(tester);

    _expectNoReveal(tester);
  });

  testWidgets('unregistered dynamic font keeps the result immediately usable', (
    tester,
  ) async {
    final host = _RevealHost();
    addTearDown(host.dispose);

    await tester.pumpWidget(
      host.build(fontFamily: 'UnregisteredDynamicResultFont'),
    );
    await _pumpPreparationWindow(tester);

    _expectNoReveal(tester);
    expect(find.text('真实结果标题'), findsOneWidget);
  });

  testWidgets('unregistered inline font does not start a partial reveal', (
    tester,
  ) async {
    final host = _RevealHost();
    addTearDown(host.dispose);

    await tester.pumpWidget(
      host.build(inlineFontFamily: 'UnregisteredDynamicResultFont'),
    );
    await _pumpPreparationWindow(tester);

    _expectNoReveal(tester);
    expect(find.text('真实结果标题'), findsOneWidget);
  });
}

void _expectNoReveal(WidgetTester tester) {
  expect(
    find.byKey(const ValueKey('generated-result-reveal/skip')),
    findsOneWidget,
  );
  expect(
    tester
        .widget<Opacity>(
          find.byKey(const ValueKey('generated-result-reveal/skip-opacity')),
        )
        .opacity,
    0,
  );
  expect(
    tester
        .widget<ExcludeFocus>(
          find.byKey(const ValueKey('generated-result-reveal/skip-focus')),
        )
        .excluding,
    isTrue,
  );
  expect(
    tester
        .widget<ExcludeSemantics>(
          find.byKey(const ValueKey('generated-result-reveal/skip-semantics')),
        )
        .excluding,
    isTrue,
  );
  expect(
    tester
        .widget<IgnorePointer>(
          find.byKey(const ValueKey('generated-result-reveal/skip-pointer')),
        )
        .ignoring,
    isTrue,
  );
  expect(
    find.byKey(const ValueKey('generated-result-reveal/paint')),
    findsNothing,
  );
}

Future<void> _pumpPreparationWindow(WidgetTester tester) async {
  for (var frame = 0; frame < 5; frame++) {
    await tester.pump(const Duration(milliseconds: 16));
  }
}

class _RevealHost {
  final GlobalKey<GeneratedResultRevealState> revealKey =
      GlobalKey<GeneratedResultRevealState>();
  final Key resultKey = const ValueKey('generated-result-reveal/result');
  late final ScrollController scrollController = ScrollController()
    ..addListener(_cancelForScroll);

  void _cancelForScroll() =>
      revealKey.currentState?.cancelForScrollOrInteraction();

  Widget build({
    String fontFamily = 'LumenisSansSC',
    String? inlineFontFamily,
    bool includeBundledIcon = false,
  }) => MaterialApp(
    theme: ThemeData(
      fontFamily: fontFamily,
      fontFamilyFallback: const ['LumenisSansKR', 'LumenisEmoji'],
    ),
    home: Scaffold(
      body: SingleChildScrollView(
        controller: scrollController,
        child: GeneratedResultReveal(
          key: revealKey,
          resultVersion: 'scope:job:immutable-hash',
          arrivalToken: 'new-result-event',
          choice: GeneratedResultMotionChoice.full,
          skipLabel: '跳过',
          accent: Colors.blue,
          foreground: Colors.white,
          child: SizedBox(
            key: resultKey,
            height: 1200,
            child: Align(
              alignment: Alignment.topLeft,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    '真实结果标题',
                    style: inlineFontFamily == null
                        ? null
                        : TextStyle(fontFamily: inlineFontFamily),
                  ),
                  if (includeBundledIcon) const Icon(Icons.copy),
                ],
              ),
            ),
          ),
        ),
      ),
    ),
  );

  void dispose() {
    scrollController
      ..removeListener(_cancelForScroll)
      ..dispose();
  }
}
