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
  testWidgets(
    'SYS-06 reads an authorized frame inside the product without exposing browser identity',
    (tester) async {
      final repository = _ReaderRepository();
      await tester.binding.setSurfaceSize(const Size(1280, 900));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      await tester.pumpWidget(
        _host(
          Sys06Screen(
            client: LumenisCoreClient(),
            browserRepository: repository,
          ),
        ),
      );

      expect(find.byKey(const ValueKey('sys06-open')), findsOneWidget);
      expect(repository.openCalls, 0);
      await tester.tap(find.byKey(const ValueKey('sys06-open')));
      await tester.pumpAndSettle();

      final address = find.byKey(const ValueKey('sys06-address'));
      expect(address, findsOneWidget);
      await tester.enterText(
        address,
        'https://example.com/article?temporary=keep-local',
      );
      await tester.tap(find.byKey(const ValueKey('sys06-go')));
      await tester.pumpAndSettle();

      expect(repository.openCalls, 1);
      expect(repository.navigateCalls, 1);
      expect(find.byKey(const ValueKey('sys06-frame')), findsOneWidget);
      expect(
        tester.widget<TextField>(address).controller!.text,
        'https://example.com/article',
      );
      for (final forbidden in const [
        'private-profile',
        '9222',
        r'C:\\private',
        'secret-session',
        'temporary=keep-local',
      ]) {
        expect(find.textContaining(forbidden), findsNothing);
      }
      expect(
        find.byKey(const ValueKey('sys06-preview-readonly')),
        findsOneWidget,
      );
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('SYS-06 rejects invalid addresses without issuing navigation', (
    tester,
  ) async {
    final repository = _ReaderRepository();
    await tester.pumpWidget(
      _host(
        Sys06Screen(client: LumenisCoreClient(), browserRepository: repository),
      ),
    );
    await tester.tap(find.byKey(const ValueKey('sys06-open')));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byKey(const ValueKey('sys06-address')),
      'javascript:alert(1)',
    );
    await tester.tap(find.byKey(const ValueKey('sys06-go')));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 120));

    expect(repository.navigateCalls, 0);
    expect(find.text('请输入一个有效的 http 或 https 地址。'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('SYS-06 discards a stale frame after a newer page revision', (
    tester,
  ) async {
    final repository = _ReaderRepository(staleFrame: true);
    await tester.pumpWidget(
      _host(
        Sys06Screen(client: LumenisCoreClient(), browserRepository: repository),
      ),
    );
    await tester.tap(find.byKey(const ValueKey('sys06-open')));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byKey(const ValueKey('sys06-address')),
      'https://example.com/newer',
    );
    await tester.tap(find.byKey(const ValueKey('sys06-go')));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 120));

    expect(find.byKey(const ValueKey('sys06-frame')), findsNothing);
    expect(find.text('正在读取已授权页面。'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'SYS-06 only stops the current controlled session after an explicit action',
    (tester) async {
      final repository = _ReaderRepository();
      await tester.pumpWidget(
        _host(
          Sys06Screen(
            client: LumenisCoreClient(),
            browserRepository: repository,
          ),
        ),
      );
      await tester.tap(find.byKey(const ValueKey('sys06-open')));
      await tester.pumpAndSettle();
      expect(repository.stopCalls, 0);
      await tester.tap(find.byKey(const ValueKey('sys06-stop')));
      await tester.pumpAndSettle();

      expect(repository.stopCalls, 1);
      expect(find.byKey(const ValueKey('sys06-open')), findsOneWidget);
      expect(tester.takeException(), isNull);
    },
  );
}

Widget _host(Widget child) => MaterialApp(
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

class _ReaderRepository implements Sys06BrowserRepository {
  _ReaderRepository({this.staleFrame = false});

  final bool staleFrame;
  int openCalls = 0;
  int navigateCalls = 0;
  int stopCalls = 0;
  var _session = const Sys06BrowserSession(
    sessionId: 'bs_0123456789ab',
    status: 'running',
    engineLabel: 'Controlled browser',
    targetId: null,
    pageRevision: 0,
    currentTitle: '',
    currentUrl: '',
    allowedActions: {'navigate', 'reload', 'frame'},
  );

  @override
  Future<Sys06BrowserSession> open() async {
    openCalls++;
    return _session;
  }

  @override
  Future<Sys06BrowserSession> navigate({
    required String sessionId,
    required String url,
  }) async {
    navigateCalls++;
    _session = const Sys06BrowserSession(
      sessionId: 'bs_0123456789ab',
      status: 'running',
      engineLabel: 'private-profile 9222 secret-session',
      targetId: 'target_approved',
      pageRevision: 1,
      currentTitle: 'Example source',
      currentUrl: 'https://example.com/article',
      allowedActions: {'navigate', 'reload', 'frame'},
    );
    return _session;
  }

  @override
  Future<Sys06BrowserFrame> readFrame(String sessionId) async =>
      Sys06BrowserFrame(
        frame: LumenisBrowserFrame(
          bytes: Uint8List.fromList(_png),
          frameId: 'frame_approved',
          targetId: 'target_approved',
          pageRevision: staleFrame ? 0 : 1,
          capturedAt: DateTime.utc(2026, 10, 5, 10),
          width: 1,
          height: 1,
        ),
      );

  @override
  Future<Sys06BrowserSession> readSession(String sessionId) async => _session;

  @override
  Future<Sys06BrowserSession> reload(String sessionId) async => _session;

  @override
  Future<void> stop(String sessionId) async {
    stopCalls++;
  }
}

const _png = <int>[
  137,
  80,
  78,
  71,
  13,
  10,
  26,
  10,
  0,
  0,
  0,
  13,
  73,
  72,
  68,
  82,
  0,
  0,
  0,
  1,
  0,
  0,
  0,
  1,
  8,
  6,
  0,
  0,
  0,
  31,
  21,
  196,
  137,
  0,
  0,
  0,
  13,
  73,
  68,
  65,
  84,
  8,
  215,
  99,
  248,
  207,
  192,
  240,
  31,
  0,
  5,
  0,
  1,
  255,
  137,
  153,
  61,
  29,
  0,
  0,
  0,
  0,
  73,
  69,
  78,
  68,
  174,
  66,
  96,
  130,
];
