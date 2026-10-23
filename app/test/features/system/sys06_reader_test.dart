import 'dart:async';
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
  testWidgets('a policy refusal preserves the typed address without retrying', (
    tester,
  ) async {
    final repository = _ReaderRepository()
      ..navigationError = const LumenisCoreException(
        'Navigation denied',
        errorCode: 'BROWSER_NAVIGATION_POLICY_DENIED',
      );
    await tester.pumpWidget(
      _host(
        Sys06Screen(client: LumenisCoreClient(), browserRepository: repository),
      ),
    );
    await tester.enterText(
      find.byKey(const ValueKey('sys06-address')),
      'https://example.com/blocked',
    );
    await tester.tap(find.byKey(const ValueKey('sys06-go')));
    await tester.pumpAndSettle();
    expect(
      tester
          .widget<TextField>(find.byKey(const ValueKey('sys06-address')))
          .controller!
          .text,
      'https://example.com/blocked',
    );
    expect(find.text('当前浏览访问规则未允许此地址。网址已保留，请核对地址或联系管理员。'), findsOneWidget);
    expect(repository.navigateCalls, 1);
  });

  testWidgets('entering an address opens the page with exclusive control', (
    tester,
  ) async {
    final repository = _ReaderRepository();
    await tester.pumpWidget(
      _host(
        Sys06Screen(client: LumenisCoreClient(), browserRepository: repository),
      ),
    );
    await tester.enterText(
      find.byKey(const ValueKey('sys06-address')),
      'https://example.com/article',
    );
    await tester.tap(find.byKey(const ValueKey('sys06-go')));
    await tester.pumpAndSettle();
    expect(repository.openCalls, 1);
    expect(repository.acquireCalls, 1);
    expect(repository.navigateCalls, 1);
    expect(find.byKey(const ValueKey('sys06-frame')), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
  testWidgets(
    'narrow browser retains the question when the sidebar is closed',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(390, 844));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      final repository = _ReaderRepository();
      await tester.pumpWidget(
        _host(
          Sys06Screen(
            client: LumenisCoreClient(),
            browserRepository: repository,
          ),
        ),
      );
      await tester.tap(find.byKey(const ValueKey('sys06-read-page')));
      await tester.pumpAndSettle();
      await tester.enterText(
        find.byKey(const ValueKey('sys06-context-question')),
        'Find opening hours',
      );
      await tester.tap(find.byKey(const ValueKey('sys06-read-page')));
      await tester.pumpAndSettle();
      expect(
        find.byKey(const ValueKey('sys06-context-question')),
        findsNothing,
      );
      await tester.tap(find.byKey(const ValueKey('sys06-read-page')));
      await tester.pumpAndSettle();
      expect(find.text('Find opening hours'), findsOneWidget);
      expect(tester.takeException(), isNull);
    },
  );
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
      await tester.tap(find.byKey(const ValueKey('sys06-acquire-control')));
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
    await tester.tap(find.byKey(const ValueKey('sys06-acquire-control')));
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
    await tester.tap(find.byKey(const ValueKey('sys06-acquire-control')));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byKey(const ValueKey('sys06-address')),
      'https://example.com/newer',
    );
    await tester.tap(find.byKey(const ValueKey('sys06-go')));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 120));

    expect(find.byKey(const ValueKey('sys06-frame')), findsNothing);
    expect(find.byType(CircularProgressIndicator), findsOneWidget);
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

  testWidgets('SYS-06 can stop while navigation is pending', (tester) async {
    final repository = _ReaderRepository()
      ..navigatePending = Completer<Sys06BrowserSession>();
    await tester.pumpWidget(
      _host(
        Sys06Screen(client: LumenisCoreClient(), browserRepository: repository),
      ),
    );
    await tester.tap(find.byKey(const ValueKey('sys06-open')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('sys06-acquire-control')));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byKey(const ValueKey('sys06-address')),
      'https://example.com/pending',
    );
    await tester.tap(find.byKey(const ValueKey('sys06-go')));
    await tester.pump();

    final stop = tester.widget<IconButton>(
      find.byKey(const ValueKey('sys06-stop')),
    );
    expect(stop.onPressed, isNotNull);
    await tester.tap(find.byKey(const ValueKey('sys06-stop')));
    await tester.pump();
    expect(repository.stopCalls, 1);
    expect(repository.stoppedSessionId, 'bs_0123456789ab');

    repository.navigatePending!.complete(_readerPageSession);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 120));
    expect(find.byKey(const ValueKey('sys06-open')), findsOneWidget);
    expect(find.byKey(const ValueKey('sys06-frame')), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets('SYS-06 can stop while control acquisition is pending', (
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
    repository.acquirePending = Completer<Sys06BrowserLease>();
    await tester.tap(find.byKey(const ValueKey('sys06-acquire-control')));
    await tester.pump();

    final stop = tester.widget<IconButton>(
      find.byKey(const ValueKey('sys06-stop')),
    );
    expect(stop.onPressed, isNotNull);
    await tester.tap(find.byKey(const ValueKey('sys06-stop')));
    await tester.pump();
    expect(repository.stopCalls, 1);
    expect(repository.stoppedSessionId, 'bs_0123456789ab');

    repository.acquirePending!.complete(
      Sys06BrowserLease(
        token: 'late-lease-token-for-test',
        expiresAt: DateTime.now().add(const Duration(minutes: 10)),
        ttlSeconds: 600,
        humanActions: const {'navigate'},
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 120));
    expect(find.byKey(const ValueKey('sys06-open')), findsOneWidget);
    expect(find.byKey(const ValueKey('sys06-frame')), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets('SYS-06 can stop while a frame read is pending', (tester) async {
    final repository = _ReaderRepository();
    await _openReaderPage(tester, repository);
    repository.framePending = Completer<Sys06BrowserFrame>();
    await tester.tap(find.byKey(const ValueKey('sys06-more')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('sys06-refresh-frame')));
    await tester.pump();

    final stop = tester.widget<IconButton>(
      find.byKey(const ValueKey('sys06-stop')),
    );
    expect(stop.onPressed, isNotNull);
    await tester.tap(find.byKey(const ValueKey('sys06-stop')));
    await tester.pump();
    expect(repository.stopCalls, 1);
    expect(repository.stoppedSessionId, 'bs_0123456789ab');

    repository.framePending!.complete(_readerFrame);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 120));
    expect(find.byKey(const ValueKey('sys06-open')), findsOneWidget);
    expect(find.byKey(const ValueKey('sys06-frame')), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'SYS-06 keeps a failed stop honest and recovers after a late failure',
    (tester) async {
      final repository = _ReaderRepository();
      await _openReaderPage(tester, repository);
      repository.framePending = Completer<Sys06BrowserFrame>();
      await tester.tap(find.byKey(const ValueKey('sys06-more')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const ValueKey('sys06-refresh-frame')));
      await tester.pump();
      repository.stopPending = Completer<void>();

      await tester.tap(find.byKey(const ValueKey('sys06-stop')));
      await tester.pump();
      repository.stopPending!.completeError(
        const LumenisCoreException(
          'Stop was not confirmed.',
          errorCode: 'BROWSER_STOP_UNCONFIRMED',
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 120));

      expect(repository.stopCalls, 1);
      expect(find.byKey(const ValueKey('sys06-address')), findsOneWidget);
      expect(find.text('网页暂时无法打开，请重试。'), findsOneWidget);
      expect(find.byKey(const ValueKey('sys06-frame')), findsNothing);

      repository.framePending!.completeError(
        const LumenisCoreException(
          'Frame read was rejected.',
          errorCode: 'BROWSER_ACTION_REJECTED',
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 120));
      expect(find.text('网页暂时无法打开，请重试。'), findsOneWidget);
      expect(find.byKey(const ValueKey('sys06-frame')), findsNothing);

      repository.stopPending = null;
      await tester.tap(find.byKey(const ValueKey('sys06-stop')));
      await tester.pumpAndSettle();
      expect(repository.stopCalls, 2);
      expect(find.byKey(const ValueKey('sys06-open')), findsOneWidget);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('SYS-06 clears the old session when its repository is replaced', (
    tester,
  ) async {
    final oldRepository = _ReaderRepository()
      ..navigatePending = Completer<Sys06BrowserSession>();
    final newRepository = _ReaderRepository();
    await tester.pumpWidget(
      _host(
        Sys06Screen(
          key: const ValueKey('sys06-reader'),
          client: LumenisCoreClient(),
          browserRepository: oldRepository,
        ),
      ),
    );
    await tester.tap(find.byKey(const ValueKey('sys06-open')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('sys06-acquire-control')));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byKey(const ValueKey('sys06-address')),
      'https://example.com/old',
    );
    await tester.tap(find.byKey(const ValueKey('sys06-go')));
    await tester.pump();

    await tester.pumpWidget(
      _host(
        Sys06Screen(
          key: const ValueKey('sys06-reader'),
          client: LumenisCoreClient(),
          browserRepository: newRepository,
        ),
      ),
    );
    expect(find.byKey(const ValueKey('sys06-open')), findsOneWidget);
    expect(newRepository.openCalls, 0);

    await tester.tap(find.byKey(const ValueKey('sys06-open')));
    await tester.pumpAndSettle();
    expect(newRepository.openCalls, 1);
    oldRepository.navigatePending!.complete(_readerPageSession);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 120));

    expect(find.byKey(const ValueKey('sys06-open')), findsNothing);
    expect(newRepository.navigateCalls, 0);
    expect(
      find.byKey(const ValueKey('sys06-frame')),
      findsOneWidget,
      reason: 'the late old navigation must not replace the new session',
    );
    expect(tester.takeException(), isNull);
  });
}

Future<void> _openReaderPage(
  WidgetTester tester,
  _ReaderRepository repository,
) async {
  await tester.pumpWidget(
    _host(
      Sys06Screen(client: LumenisCoreClient(), browserRepository: repository),
    ),
  );
  await tester.tap(find.byKey(const ValueKey('sys06-open')));
  await tester.pumpAndSettle();
  await tester.tap(find.byKey(const ValueKey('sys06-acquire-control')));
  await tester.pumpAndSettle();
  await tester.enterText(
    find.byKey(const ValueKey('sys06-address')),
    'https://example.com/article',
  );
  await tester.tap(find.byKey(const ValueKey('sys06-go')));
  await tester.pumpAndSettle();
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

class _ReaderRepository
    implements Sys06BrowserRepository, Sys06BrowserHumanControlRepository {
  _ReaderRepository({this.staleFrame = false});

  final bool staleFrame;
  int openCalls = 0;
  int navigateCalls = 0;
  Object? navigationError;
  int reloadCalls = 0;
  int frameCalls = 0;
  int stopCalls = 0;
  String? stoppedSessionId;
  Completer<Sys06BrowserSession>? navigatePending;
  Completer<Sys06BrowserSession>? reloadPending;
  Completer<Sys06BrowserFrame>? framePending;
  Completer<void>? stopPending;
  var _session = const Sys06BrowserSession(
    sessionId: 'bs_0123456789ab',
    status: 'running',
    engineLabel: 'Controlled browser',
    targetId: 'target_approved',
    pageRevision: 0,
    currentTitle: '',
    currentUrl: 'about:blank',
    allowedActions: {'navigate', 'reload', 'frame'},
    humanControlActive: false,
    humanActionsRequireLease: true,
    humanActions: {'navigate'},
  );
  int acquireCalls = 0;
  Completer<Sys06BrowserLease>? acquirePending;

  @override
  Future<Sys06BrowserLease> acquireHumanControl(String sessionId) async {
    acquireCalls++;
    if (acquirePending != null) return acquirePending!.future;
    _session = const Sys06BrowserSession(
      sessionId: 'bs_0123456789ab',
      status: 'running',
      engineLabel: 'Controlled browser',
      targetId: 'target_approved',
      pageRevision: 0,
      currentTitle: '',
      currentUrl: 'about:blank',
      allowedActions: {'navigate', 'reload', 'frame'},
      humanControlActive: true,
      humanActionsRequireLease: true,
      humanActions: {'navigate'},
    );
    return Sys06BrowserLease(
      token: 'lease-token-for-test',
      expiresAt: DateTime.now().add(const Duration(minutes: 10)),
      ttlSeconds: 600,
      humanActions: const {'navigate'},
    );
  }

  @override
  Future<void> releaseHumanControl({
    required String sessionId,
    required String leaseToken,
  }) async {}

  @override
  Future<void> humanNavigate({
    required String sessionId,
    required String url,
    required String leaseToken,
    required LumenisBrowserFrameBinding frameBinding,
  }) async {
    navigateCalls++;
    if (navigationError != null) throw navigationError!;
    if (navigatePending != null) {
      await navigatePending!.future;
      return;
    }
    _session = _readerPageSession;
  }

  @override
  Future<void> humanAction({
    required String sessionId,
    required String action,
    required String leaseToken,
    required LumenisBrowserFrameBinding frameBinding,
    String value = '',
  }) async {}

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
    throw StateError('direct navigation is not allowed without human control');
  }

  @override
  Future<Sys06BrowserFrame> readFrame(String sessionId) async {
    frameCalls++;
    if (framePending != null) return framePending!.future;
    final revision = staleFrame
        ? (_session.pageRevision > 0 ? _session.pageRevision - 1 : 0)
        : _session.pageRevision;
    return Sys06BrowserFrame(
      frame: LumenisBrowserFrame(
        bytes: Uint8List.fromList(_png),
        frameId: 'frame_approved',
        targetId: 'target_approved',
        pageRevision: revision,
        capturedAt: DateTime.utc(2026, 10, 5, 10),
        width: 1,
        height: 1,
        viewportWidth: 1280,
        viewportHeight: 720,
        devicePixelRatio: 1,
      ),
    );
  }

  @override
  Future<Sys06BrowserSession> readSession(String sessionId) async => _session;

  @override
  Future<Sys06BrowserSession> reload(String sessionId) async {
    reloadCalls++;
    if (reloadPending != null) return reloadPending!.future;
    return _session;
  }

  @override
  Future<void> stop(String sessionId) async {
    stopCalls++;
    stoppedSessionId = sessionId;
    if (stopPending != null) await stopPending!.future;
  }
}

const _readerPageSession = Sys06BrowserSession(
  sessionId: 'bs_0123456789ab',
  status: 'running',
  engineLabel: 'private-profile 9222 secret-session',
  targetId: 'target_approved',
  pageRevision: 1,
  currentTitle: 'Example source',
  currentUrl: 'https://example.com/article',
  allowedActions: {'navigate', 'reload', 'frame'},
  humanControlActive: true,
  humanActionsRequireLease: true,
  humanActions: {'navigate'},
);

final _readerFrame = Sys06BrowserFrame(
  frame: LumenisBrowserFrame(
    bytes: Uint8List.fromList(_png),
    frameId: 'frame_approved',
    targetId: 'target_approved',
    pageRevision: 1,
    capturedAt: DateTime.utc(2026, 10, 5, 10),
    width: 1,
    height: 1,
    viewportWidth: 1280,
    viewportHeight: 720,
    devicePixelRatio: 1,
  ),
);

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
