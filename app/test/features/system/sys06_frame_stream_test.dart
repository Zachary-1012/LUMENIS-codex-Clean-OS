import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/core/lumenis_theme.dart';
import 'package:lumenis_app/features/system/sys06/sys06_browser_repository.dart';
import 'package:lumenis_app/features/system/sys06/sys06_screen.dart';
import 'package:lumenis_app/l10n/lumenis_localizations.dart';

void main() {
  testWidgets('SYS-06 shows pushed stream frames gaplessly in place', (
    tester,
  ) async {
    final repository = _StreamRepository();
    await tester.binding.setSurfaceSize(const Size(1280, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(
      _host(
        Sys06Screen(client: LumenisCoreClient(), browserRepository: repository),
      ),
    );
    await tester.tap(find.byKey(const ValueKey('sys06-open')));
    await tester.pumpAndSettle();

    expect(repository.watchCalls, 1);
    expect(repository.frames.hasListener, isTrue);
    Image image() =>
        tester.widget<Image>(find.byKey(const ValueKey('sys06-frame')));
    expect(image().gaplessPlayback, isTrue);
    expect((image().image as MemoryImage).bytes, same(repository.firstBytes));

    final pushed = Uint8List.fromList(_png);
    repository.frames.add(_frame(pushed, 'frame_live_2'));
    await tester.pump();
    await tester.pump();
    expect(find.byKey(const ValueKey('sys06-frame')), findsOneWidget);
    expect((image().image as MemoryImage).bytes, same(pushed));
    expect(image().gaplessPlayback, isTrue);

    // A frame of another page revision is never shown.
    final stale = Uint8List.fromList(_png);
    repository.frames.add(_frame(stale, 'frame_live_3', revision: 7));
    await tester.pump();
    await tester.pump();
    expect((image().image as MemoryImage).bytes, same(pushed));

    await tester.pumpWidget(const SizedBox());
    await tester.pump();
    await tester.pump();
    expect(repository.frames.hasListener, isFalse);
  });

  testWidgets('SYS-06 clears the preview when the live stream ends', (
    tester,
  ) async {
    final repository = _StreamRepository();
    await tester.binding.setSurfaceSize(const Size(1280, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(
      _host(
        Sys06Screen(client: LumenisCoreClient(), browserRepository: repository),
      ),
    );
    await tester.tap(find.byKey(const ValueKey('sys06-open')));
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('sys06-frame')), findsOneWidget);
    await repository.frames.close();
    await tester.pump();
    await tester.pump();
    expect(find.byKey(const ValueKey('sys06-frame')), findsNothing);
  });

  testWidgets('SYS-06 stops the stream when the app leaves the view', (
    tester,
  ) async {
    final repository = _StreamRepository();
    await tester.binding.setSurfaceSize(const Size(1280, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(
      _host(
        Sys06Screen(client: LumenisCoreClient(), browserRepository: repository),
      ),
    );
    await tester.tap(find.byKey(const ValueKey('sys06-open')));
    await tester.pumpAndSettle();
    expect(repository.frames.hasListener, isTrue);
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.inactive);
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.hidden);
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.paused);
    await tester.pump();
    expect(repository.frames.hasListener, isFalse);
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.hidden);
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.inactive);
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
    await tester.pump();
    expect(repository.frames.hasListener, isTrue);
    expect(repository.watchCalls, 2);
  });

  testWidgets('SYS-06 stops the stream when another route covers it', (
    tester,
  ) async {
    final repository = _StreamRepository();
    await tester.binding.setSurfaceSize(const Size(1280, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final navigatorKey = GlobalKey<NavigatorState>();
    await tester.pumpWidget(
      _host(
        Sys06Screen(client: LumenisCoreClient(), browserRepository: repository),
        navigatorKey: navigatorKey,
      ),
    );
    await tester.tap(find.byKey(const ValueKey('sys06-open')));
    await tester.pumpAndSettle();
    expect(repository.frames.hasListener, isTrue);
    navigatorKey.currentState!.push(
      MaterialPageRoute<void>(builder: (_) => const Scaffold(body: Text('x'))),
    );
    await tester.pumpAndSettle();
    expect(repository.frames.hasListener, isFalse);
  });

  test('SSE frame event parses into a bound PNG frame', () {
    final event = jsonEncode({
      't': 'frame',
      'frame_id': 'bf_1',
      'target_id': 't1',
      'page_revision': 2,
      'captured_at': '2026-10-13T08:00:00+00:00',
      'width': 1,
      'height': 1,
      'viewport': {'width': 1280, 'height': 720, 'dpr': 1.0},
      'mime': 'image/png',
      'data': base64Encode(_png),
      'stored': false,
      'ai_readable': false,
    });
    final frame = LumenisCoreClient.parseBrowserStreamEvent(event)!;
    expect(frame.frameId, 'bf_1');
    expect(frame.pageRevision, 2);
    expect(frame.binding.viewportWidth, 1280);
    expect(frame.bytes, _png);
    expect(
      LumenisCoreClient.parseBrowserStreamEvent(
        '{"t":"state","state":"PENDING"}',
      ),
      isNull,
    );
    expect(
      () => LumenisCoreClient.parseBrowserStreamEvent(
        jsonEncode({'t': 'frame', 'mime': 'image/png'}),
      ),
      throwsFormatException,
    );
  });
}

Sys06BrowserFrame _frame(Uint8List bytes, String id, {int revision = 0}) =>
    Sys06BrowserFrame(
      frame: LumenisBrowserFrame(
        bytes: bytes,
        frameId: id,
        targetId: 'target_approved',
        pageRevision: revision,
        capturedAt: DateTime.utc(2026, 10, 13, 8),
        width: 1,
        height: 1,
        viewportWidth: 1280,
        viewportHeight: 720,
        devicePixelRatio: 1,
      ),
    );

Widget _host(Widget child, {GlobalKey<NavigatorState>? navigatorKey}) =>
    MaterialApp(
      navigatorKey: navigatorKey,
      theme: LumenisTheme.dark,
      locale: const Locale('zh', 'CN'),
      supportedLocales: const [Locale('zh', 'CN'), Locale('en'), Locale('ko')],
      localizationsDelegates: const [
        LumenisLocalizations.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      home: Scaffold(body: child),
    );

class _StreamRepository
    implements Sys06BrowserRepository, Sys06BrowserFrameStreamRepository {
  final frames = StreamController<Sys06BrowserFrame>.broadcast(sync: true);
  final firstBytes = Uint8List.fromList(_png);
  int watchCalls = 0;
  static const _session = Sys06BrowserSession(
    sessionId: 'bs_0123456789ab',
    status: 'running',
    engineLabel: 'Controlled browser',
    targetId: 'target_approved',
    pageRevision: 0,
    currentTitle: '',
    currentUrl: '',
    allowedActions: {'navigate', 'reload', 'frame'},
    humanControlActive: false,
    humanActionsRequireLease: true,
    humanActions: {'navigate'},
  );

  @override
  Stream<Sys06BrowserFrame> watchFrames(String sessionId) {
    watchCalls++;
    return frames.stream;
  }

  @override
  Future<Sys06BrowserSession> open() async => _session;

  @override
  Future<Sys06BrowserSession> readSession(String sessionId) async => _session;

  @override
  Future<Sys06BrowserSession> navigate({
    required String sessionId,
    required String url,
  }) async => _session;

  @override
  Future<Sys06BrowserSession> reload(String sessionId) async => _session;

  @override
  Future<Sys06BrowserFrame> readFrame(String sessionId) async =>
      _frame(firstBytes, 'frame_first');

  @override
  Future<void> stop(String sessionId) async {}
}

const _png = <int>[
  137, 80, 78, 71, 13, 10, 26, 10, 0, 0, 0, 13, 73, 72, 68, 82, 0, 0, 0, 1, //
  0, 0, 0, 1, 8, 6, 0, 0, 0, 31, 21, 196, 137, 0, 0, 0, 13, 73, 68, 65, 84, //
  8, 215, 99, 248, 207, 192, 240, 31, 0, 5, 0, 1, 255, 137, 153, 61, 29, 0, //
  0, 0, 0, 73, 69, 78, 68, 174, 66, 96, 130,
];
