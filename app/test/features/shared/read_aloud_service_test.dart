import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/generated_result_reveal.dart';
import 'package:lumenis_app/features/shared/read_aloud_action.dart';
import 'package:lumenis_app/features/shared/read_aloud_contract.dart';
import 'package:lumenis_app/features/shared/read_aloud_service.dart';
import 'package:lumenis_app/l10n/lumenis_localizations.dart';

void main() {
  group('ReadAloudService', () {
    test('requires an exact installed local locale before speaking', () async {
      final platform = _FakeReadAloudPlatform(locales: {'en-US'});
      final service = ReadAloudService(platform: platform);

      await service.start(_request(locale: ReadAloudLocale.zhCn));

      expect(platform.requests, isEmpty);
      expect(
        service
            .stateFor(sessionId: 'session-1', scopeVersion: 'scope-v1')
            .status,
        ReadAloudStatus.unavailable,
      );
      expect(
        service
            .stateFor(sessionId: 'session-1', scopeVersion: 'scope-v1')
            .errorCode,
        ReadAloudErrorCode.voiceUnavailable,
      );
      service.dispose();
    });

    test('reports each missing exact locale as unavailable', () async {
      for (final locale in ReadAloudLocale.values) {
        final platform = _FakeReadAloudPlatform(
          locales: ReadAloudLocale.values
              .where((candidate) => candidate != locale)
              .map((candidate) => candidate.tag)
              .toSet(),
        );
        final service = ReadAloudService(platform: platform);

        await service.start(_request(locale: locale));

        final state = service.stateFor(
          sessionId: 'session-1',
          scopeVersion: 'scope-v1',
        );
        expect(state.status, ReadAloudStatus.unavailable, reason: locale.tag);
        expect(
          state.errorCode,
          ReadAloudErrorCode.voiceUnavailable,
          reason: locale.tag,
        );
        expect(platform.requests, isEmpty, reason: locale.tag);
        service.dispose();
      }
    });

    test('replaces the current session and reports completion', () async {
      final platform = _FakeReadAloudPlatform();
      final service = ReadAloudService(platform: platform);

      await service.start(_request());
      await service.start(
        _request(sessionId: 'session-2', scopeVersion: 'scope-v2'),
      );
      await Future<void>.delayed(const Duration(milliseconds: 270));
      expect(platform.requests, hasLength(2));
      expect(platform.stopCount, 2);
      expect(
        service
            .stateFor(sessionId: 'session-2', scopeVersion: 'scope-v2')
            .status,
        ReadAloudStatus.playing,
      );

      platform.observation = ReadAloudPlaybackObservation.completed;
      await Future<void>.delayed(const Duration(milliseconds: 270));
      expect(
        service
            .stateFor(sessionId: 'session-2', scopeVersion: 'scope-v2')
            .status,
        ReadAloudStatus.completed,
      );
      service.dispose();
    });

    test(
      'queued speech stays starting until observation confirms playback',
      () async {
        final platform = _FakeReadAloudPlatform(
          observation: ReadAloudPlaybackObservation.starting,
        );
        final service = ReadAloudService(
          platform: platform,
          startupTimeout: const Duration(seconds: 1),
        );

        await service.start(_request());

        expect(
          service
              .stateFor(sessionId: 'session-1', scopeVersion: 'scope-v1')
              .status,
          ReadAloudStatus.starting,
        );
        await Future<void>.delayed(const Duration(milliseconds: 270));
        expect(
          service
              .stateFor(sessionId: 'session-1', scopeVersion: 'scope-v1')
              .status,
          ReadAloudStatus.starting,
        );
        expect(platform.stopCount, 1);
        service.dispose();
      },
    );

    test(
      'stops and fails if queued speech never starts before timeout',
      () async {
        final platform = _FakeReadAloudPlatform(
          observation: ReadAloudPlaybackObservation.starting,
        );
        final service = ReadAloudService(
          platform: platform,
          startupTimeout: const Duration(milliseconds: 40),
        );

        await service.start(_request());
        expect(
          service
              .stateFor(sessionId: 'session-1', scopeVersion: 'scope-v1')
              .status,
          ReadAloudStatus.starting,
        );
        await Future<void>.delayed(const Duration(milliseconds: 80));

        expect(
          service
              .stateFor(sessionId: 'session-1', scopeVersion: 'scope-v1')
              .status,
          ReadAloudStatus.failed,
        );
        expect(
          service
              .stateFor(sessionId: 'session-1', scopeVersion: 'scope-v1')
              .errorCode,
          ReadAloudErrorCode.playbackFailed,
        );
        expect(platform.stopCount, 2);
        service.dispose();
      },
    );

    test('shows playing only after playback observation confirms it', () async {
      final platform = _FakeReadAloudPlatform(
        observation: ReadAloudPlaybackObservation.starting,
      );
      final service = ReadAloudService(
        platform: platform,
        startupTimeout: const Duration(seconds: 1),
      );

      await service.start(_request());
      expect(
        service
            .stateFor(sessionId: 'session-1', scopeVersion: 'scope-v1')
            .status,
        ReadAloudStatus.starting,
      );
      platform.observation = ReadAloudPlaybackObservation.playing;
      await Future<void>.delayed(const Duration(milliseconds: 270));

      expect(
        service
            .stateFor(sessionId: 'session-1', scopeVersion: 'scope-v1')
            .status,
        ReadAloudStatus.playing,
      );
      service.dispose();
    });

    test('does not start an empty text session', () async {
      final platform = _FakeReadAloudPlatform();
      final service = ReadAloudService(platform: platform);

      await service.start(_request());
      await service.start(_request(text: ' \n  '));

      expect(platform.requests, hasLength(1));
      expect(platform.stopCount, 2);
      expect(
        service
            .stateFor(sessionId: 'session-1', scopeVersion: 'scope-v1')
            .status,
        ReadAloudStatus.failed,
      );
      expect(
        service
            .stateFor(sessionId: 'session-1', scopeVersion: 'scope-v1')
            .errorCode,
        ReadAloudErrorCode.textEmpty,
      );
      service.dispose();
    });

    test(
      'contains platform stop failures and does not begin playback',
      () async {
        final platform = _ThrowingStopReadAloudPlatform();
        final service = ReadAloudService(platform: platform);

        await expectLater(service.start(_request()), completes);

        expect(platform.requests, isEmpty);
        expect(
          service
              .stateFor(sessionId: 'session-1', scopeVersion: 'scope-v1')
              .status,
          ReadAloudStatus.failed,
        );
        expect(
          service
              .stateFor(sessionId: 'session-1', scopeVersion: 'scope-v1')
              .errorCode,
          ReadAloudErrorCode.playbackFailed,
        );
        service.dispose();
      },
    );

    test(
      'a stale speak completion cannot stop the replacement session',
      () async {
        final platform = _BlockingFirstSpeakReadAloudPlatform();
        final service = ReadAloudService(platform: platform);

        final firstStart = service.start(_request());
        await platform.firstSpeakEntered.future;
        final secondStart = service.start(
          _request(sessionId: 'session-2', scopeVersion: 'scope-v2'),
        );
        platform.firstSpeakResult.complete(
          const ReadAloudStartResult(ReadAloudStatus.playing),
        );

        await Future.wait([firstStart, secondStart]);
        await Future<void>.delayed(const Duration(milliseconds: 270));

        expect(platform.requests, hasLength(2));
        expect(platform.stopCount, 2);
        expect(
          service
              .stateFor(sessionId: 'session-2', scopeVersion: 'scope-v2')
              .status,
          ReadAloudStatus.playing,
        );
        service.dispose();
      },
    );
  });

  testWidgets('starting state says preparing and can be stopped', (
    tester,
  ) async {
    final platform = _FakeReadAloudPlatform(
      startStatus: ReadAloudStatus.starting,
      observation: ReadAloudPlaybackObservation.starting,
    );
    final service = ReadAloudService(
      platform: platform,
      startupTimeout: const Duration(seconds: 2),
    );
    await tester.pumpWidget(
      MaterialApp(
        locale: const Locale('zh', 'CN'),
        localizationsDelegates: const [
          LumenisLocalizations.delegate,
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        supportedLocales: LumenisLocalizations.supportedLocales,
        home: Scaffold(
          body: ReadAloudAction(
            service: service,
            sessionId: 'session-1',
            scopeVersion: 'scope-v1',
            text: 'visible user text',
            purpose: ReadAloudPurpose.savedPreview,
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('read-aloud/toggle')));
    await tester.pumpAndSettle();

    expect(find.text('正在准备朗读…'), findsOneWidget);
    expect(find.text('停止'), findsOneWidget);
    expect(
      service.stateFor(sessionId: 'session-1', scopeVersion: 'scope-v1').status,
      ReadAloudStatus.starting,
    );

    await tester.tap(find.byKey(const ValueKey('read-aloud/toggle')));
    await tester.pumpAndSettle();
    expect(platform.stopCount, 2);
    expect(
      service.stateFor(sessionId: 'session-1', scopeVersion: 'scope-v1').status,
      ReadAloudStatus.stopped,
    );
    await tester.pumpWidget(const SizedBox.shrink());
    await tester.pumpAndSettle();
    service.dispose();
  });

  testWidgets(
    'semantic read-aloud activation cancels result reveal without pointer input',
    (tester) async {
      final platform = _FakeReadAloudPlatform();
      final service = ReadAloudService(platform: platform);
      final revealKey = GlobalKey<GeneratedResultRevealState>();
      var userInteractions = 0;
      void cancelReveal() {
        userInteractions++;
        revealKey.currentState?.cancelForScrollOrInteraction();
      }

      await tester.pumpWidget(
        MaterialApp(
          theme: ThemeData(
            fontFamily: 'LumenisSansSC',
            fontFamilyFallback: const ['LumenisSansKR', 'LumenisEmoji'],
          ),
          locale: const Locale('zh', 'CN'),
          localizationsDelegates: const [
            LumenisLocalizations.delegate,
            GlobalMaterialLocalizations.delegate,
            GlobalWidgetsLocalizations.delegate,
            GlobalCupertinoLocalizations.delegate,
          ],
          supportedLocales: LumenisLocalizations.supportedLocales,
          home: Scaffold(
            body: SingleChildScrollView(
              child: GeneratedResultReveal(
                key: revealKey,
                resultVersion: 'scope:brief:immutable-hash',
                arrivalToken: 'new-result-event',
                choice: GeneratedResultMotionChoice.full,
                skipLabel: '跳过',
                accent: Colors.blue,
                foreground: Colors.white,
                onUserInteraction: cancelReveal,
                child: SizedBox(
                  height: 1200,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('Saved brief result'),
                      ReadAloudAction(
                        service: service,
                        sessionId: 'source-brief:1',
                        scopeVersion: 'scope:brief:immutable-hash',
                        text: 'Visible saved brief text',
                        purpose: ReadAloudPurpose.sourceBrief,
                        onUserInteraction: cancelReveal,
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      );
      for (var frame = 0; frame < 5; frame++) {
        await tester.pump(const Duration(milliseconds: 16));
      }
      expect(revealKey.currentState?.isPlaying, isTrue);
      expect(
        find.byKey(const ValueKey('generated-result-reveal/paint')),
        findsOneWidget,
      );

      final semantics = tester.ensureSemantics();
      try {
        final toggle = tester.getSemantics(
          find.byKey(const ValueKey('read-aloud/toggle')),
        );
        toggle.owner!.performAction(toggle.id, SemanticsAction.tap);
        await tester.pump();

        expect(userInteractions, 1);
        expect(revealKey.currentState?.isPlaying, isFalse);
        expect(
          find.byKey(const ValueKey('generated-result-reveal/paint')),
          findsNothing,
        );
        expect(platform.requests, hasLength(1));
      } finally {
        semantics.dispose();
      }

      await tester.pumpWidget(const SizedBox.shrink());
      await tester.pumpAndSettle();
      service.dispose();
    },
  );

  testWidgets('offers exact locale/rate and stops when bound text changes', (
    tester,
  ) async {
    final platform = _FakeReadAloudPlatform();
    final service = ReadAloudService(platform: platform);
    Widget action(String text) => MaterialApp(
      locale: const Locale('zh', 'CN'),
      localizationsDelegates: const [
        LumenisLocalizations.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      supportedLocales: LumenisLocalizations.supportedLocales,
      home: Scaffold(
        body: ReadAloudAction(
          key: const ValueKey('read-aloud-action'),
          service: service,
          sessionId: 'session-1',
          scopeVersion: 'scope-v1',
          text: text,
          purpose: ReadAloudPurpose.sourceBrief,
        ),
      ),
    );

    await tester.pumpWidget(action('visible analysis text'));
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('read-aloud/toggle')), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('read-aloud/locale')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('英语（美国）').last);
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('read-aloud/rate')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('快速 · 1.25×').last);
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('read-aloud/toggle')));
    await tester.pumpAndSettle();

    expect(platform.requests, hasLength(1));
    expect(platform.requests.single.locale, ReadAloudLocale.enUs);
    expect(platform.requests.single.rate, ReadAloudRate.fast);

    await tester.pumpWidget(action('revised visible analysis text'));
    await tester.pumpAndSettle();
    expect(platform.stopCount, greaterThanOrEqualTo(2));
    expect(
      service.stateFor(sessionId: 'session-1', scopeVersion: 'scope-v1').status,
      ReadAloudStatus.stopped,
    );

    await tester.pumpWidget(const SizedBox.shrink());
    await tester.pumpAndSettle();
    service.dispose();
  });

  testWidgets(
    'podcast script revision stops the old session and speaks the new text at 0.75x',
    (tester) async {
      final platform = _FakeReadAloudPlatform();
      final service = ReadAloudService(platform: platform);

      Widget action(String text, String version) => MaterialApp(
        locale: const Locale('zh', 'CN'),
        localizationsDelegates: const [
          LumenisLocalizations.delegate,
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        supportedLocales: LumenisLocalizations.supportedLocales,
        home: Scaffold(
          body: ReadAloudAction(
            key: const ValueKey('read-aloud-podcast-script'),
            service: service,
            sessionId: 'podcast-script-1',
            scopeVersion: version,
            text: text,
            purpose: ReadAloudPurpose.podcastScript,
          ),
        ),
      );

      await tester.pumpWidget(
        action('Original podcast sentence.', 'script-v1'),
      );
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const ValueKey('read-aloud/rate')));
      await tester.pumpAndSettle();
      await tester.tap(find.text('慢速 · 0.75×').last);
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const ValueKey('read-aloud/toggle')));
      await tester.pumpAndSettle();
      await tester.pump(const Duration(milliseconds: 300));
      expect(platform.requests.single.rate, ReadAloudRate.slow);
      expect(platform.requests.single.text, 'Original podcast sentence.');

      await tester.pumpWidget(action('Revised podcast sentence.', 'script-v2'));
      await tester.pumpAndSettle();
      expect(platform.stopCount, greaterThanOrEqualTo(2));
      expect(
        service
            .stateFor(sessionId: 'podcast-script-1', scopeVersion: 'script-v1')
            .status,
        ReadAloudStatus.stopped,
      );

      await tester.tap(find.byKey(const ValueKey('read-aloud/toggle')));
      await tester.pumpAndSettle();
      await tester.pump(const Duration(milliseconds: 300));
      expect(platform.requests, hasLength(2));
      expect(platform.requests.last.rate, ReadAloudRate.slow);
      expect(platform.requests.last.text, 'Revised podcast sentence.');
      expect(
        service
            .stateFor(sessionId: 'podcast-script-1', scopeVersion: 'script-v2')
            .status,
        ReadAloudStatus.playing,
      );

      await tester.pumpWidget(const SizedBox.shrink());
      await tester.pumpAndSettle();
      service.dispose();
    },
  );

  testWidgets('stops playback when another route covers the text', (
    tester,
  ) async {
    final platform = _FakeReadAloudPlatform();
    final service = ReadAloudService(platform: platform);
    await tester.pumpWidget(
      MaterialApp(
        locale: const Locale('zh', 'CN'),
        localizationsDelegates: const [
          LumenisLocalizations.delegate,
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        supportedLocales: LumenisLocalizations.supportedLocales,
        home: Scaffold(
          body: ReadAloudAction(
            service: service,
            sessionId: 'session-1',
            scopeVersion: 'scope-v1',
            text: 'visible user text',
            purpose: ReadAloudPurpose.savedPreview,
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('read-aloud/toggle')));
    await tester.pumpAndSettle();
    await tester.pump(const Duration(milliseconds: 300));
    expect(
      service.stateFor(sessionId: 'session-1', scopeVersion: 'scope-v1').status,
      ReadAloudStatus.playing,
    );

    final context = tester.element(find.byType(ReadAloudAction));
    Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (_) => const Scaffold(body: Text('next')),
      ),
    );
    await tester.pumpAndSettle();
    expect(platform.stopCount, greaterThanOrEqualTo(2));
    expect(
      service.stateFor(sessionId: 'session-1', scopeVersion: 'scope-v1').status,
      ReadAloudStatus.stopped,
    );

    await tester.pumpWidget(const SizedBox.shrink());
    await tester.pumpAndSettle();
    service.dispose();
  });
}

ReadAloudRequest _request({
  String sessionId = 'session-1',
  String scopeVersion = 'scope-v1',
  String text = 'visible user text',
  ReadAloudLocale locale = ReadAloudLocale.zhCn,
  ReadAloudRate rate = ReadAloudRate.normal,
}) => ReadAloudRequest(
  sessionId: sessionId,
  scopeVersion: scopeVersion,
  text: text,
  locale: locale,
  rate: rate,
);

class _FakeReadAloudPlatform implements ReadAloudPlatform {
  _FakeReadAloudPlatform({
    this.locales = const {'zh-CN', 'en-US', 'ko-KR'},
    this.startStatus = ReadAloudStatus.playing,
    this.observation = ReadAloudPlaybackObservation.playing,
  });

  final Set<String> locales;
  final List<ReadAloudRequest> requests = [];
  int stopCount = 0;
  final ReadAloudStatus startStatus;
  ReadAloudPlaybackObservation observation;

  @override
  Future<ReadAloudAvailability> availableLocales() async =>
      ReadAloudAvailability(supported: true, localLocales: locales);

  @override
  Future<ReadAloudStartResult> speak(ReadAloudRequest request) async {
    requests.add(request);
    return ReadAloudStartResult(startStatus);
  }

  @override
  Future<void> stop() async {
    stopCount++;
  }

  @override
  Future<ReadAloudPlaybackObservation> observe() async => observation;
}

class _ThrowingStopReadAloudPlatform extends _FakeReadAloudPlatform {
  @override
  Future<void> stop() async {
    stopCount++;
    throw StateError('simulated local stop failure');
  }
}

class _BlockingFirstSpeakReadAloudPlatform extends _FakeReadAloudPlatform {
  final Completer<void> firstSpeakEntered = Completer<void>();
  final Completer<ReadAloudStartResult> firstSpeakResult =
      Completer<ReadAloudStartResult>();

  @override
  Future<ReadAloudStartResult> speak(ReadAloudRequest request) {
    requests.add(request);
    if (requests.length == 1) {
      firstSpeakEntered.complete();
      return firstSpeakResult.future;
    }
    return Future.value(ReadAloudStartResult(startStatus));
  }
}
