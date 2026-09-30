import 'dart:async';
import 'dart:ui' show AppExitResponse;

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/core/lumenis_theme.dart';
import 'package:lumenis_app/features/shared/sh01/sh01_screen.dart';
import 'package:lumenis_app/l10n/lumenis_localizations.dart';
import 'package:lumenis_app/navigation/lumenis_leave_guard.dart';
import 'package:lumenis_app/navigation/lumenis_router.dart';
import 'package:lumenis_app/shell/lumenis_workspace_shell.dart';

void main() {
  test(
    'concurrent exits share one decision and a cancel permits a new attempt',
    () async {
      final guard = LumenisLeaveGuard();
      final owner = Object();
      var calls = 0;
      var reply = Completer<bool>();
      guard.register(
        owner,
        needsProtection: () => true,
        requestLeave: () {
          calls++;
          return reply.future;
        },
      );
      final first = guard.requestLeave();
      expect(guard.requestLeave(), same(first));
      expect(calls, 1);
      reply.complete(false);
      expect(await first, isFalse);
      reply = Completer<bool>()..complete(true);
      expect(await guard.requestLeave(), isTrue);
      expect(calls, 2);
      guard.unregister(owner);
      expect(guard.needsProtection, isFalse);
      expect(await guard.requestLeave(), isTrue);
      guard.dispose();
    },
  );

  test('old owners cannot unregister a newer editor', () async {
    final guard = LumenisLeaveGuard();
    final old = Object();
    final current = Object();
    guard.register(
      old,
      needsProtection: () => true,
      requestLeave: () async => true,
    );
    guard.register(
      current,
      needsProtection: () => true,
      requestLeave: () async => false,
    );
    guard.unregister(old);
    expect(await guard.requestLeave(), isFalse);
    guard.unregister(current);
    expect(await guard.requestLeave(), isTrue);
    guard.dispose();
  });

  testWidgets('cancelable native app exit follows the same editor decision', (
    tester,
  ) async {
    final guard = LumenisLeaveGuard();
    final owner = Object();
    guard.register(
      owner,
      needsProtection: () => true,
      requestLeave: () async => false,
    );
    await tester.pumpWidget(
      LumenisLeaveScope(guard: guard, child: const SizedBox()),
    );
    expect(await tester.binding.handleRequestAppExit(), AppExitResponse.cancel);
    guard.unregister(owner);
    expect(await tester.binding.handleRequestAppExit(), AppExitResponse.exit);
    await tester.pumpWidget(const SizedBox());
    guard.dispose();
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'same route different screen waits and cancellation preserves URL and page',
    (tester) async {
      final client = _Client();
      final router = createLumenisRouter(
        client: client,
        onLocaleChanged: (_) {},
        initialLocation: '/workspace/SH-01',
      );
      addTearDown(router.dispose);
      await tester.binding.setSurfaceSize(const Size(1366, 900));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      await tester.pumpWidget(_routedApp(router));
      await tester.pumpAndSettle();
      final guard = LumenisLeaveScope.maybeOf(
        tester.element(find.byType(Sh01Screen)),
      )!;
      final owner = Object();
      var reply = Completer<bool>();
      guard.register(
        owner,
        needsProtection: () => true,
        requestLeave: () => reply.future,
      );
      router.go('/workspace/AI-01');
      await tester.pump();
      expect(find.byType(Sh01Screen), findsOneWidget);
      reply.complete(false);
      await tester.pumpAndSettle();
      expect(
        router.routerDelegate.currentConfiguration.uri.path,
        '/workspace/SH-01',
      );
      expect(find.byType(Sh01Screen), findsOneWidget);
      expect(
        find.byKey(const ValueKey('workspace-account-navigation')),
        findsNothing,
      );
      expect(find.byKey(const ValueKey('workspace-nav-ACC-04')), findsNothing);
      reply = Completer<bool>();
      unawaited(
        router.routeInformationProvider.didPushRouteInformation(
          RouteInformation(uri: Uri.parse('/workspace/AI-01')),
        ),
      );
      await tester.pump();
      reply.complete(false);
      await tester.pumpAndSettle();
      expect(
        router.routerDelegate.currentConfiguration.uri.path,
        '/workspace/SH-01',
      );
      expect(find.byType(Sh01Screen), findsOneWidget);
      reply = Completer<bool>();
      router.go('/workspace/AI-01');
      await tester.pump();
      reply.complete(true);
      await tester.pumpAndSettle();
      expect(
        router.routerDelegate.currentConfiguration.uri.path,
        '/workspace/AI-01',
      );
      expect(find.byType(Sh01Screen), findsNothing);
      guard.unregister(owner);
      expect(tester.takeException(), isNull);
    },
  );

  for (final focused in [false, true]) {
    testWidgets(
      'cancel scope ${focused ? 'clear' : 'selection'} sends no mutation',
      (tester) async {
        final client = _Client(focused: focused);
        final guard = LumenisLeaveGuard();
        final owner = Object();
        var asks = 0;
        guard.register(
          owner,
          needsProtection: () => true,
          requestLeave: () async {
            asks++;
            return false;
          },
        );
        await tester.binding.setSurfaceSize(const Size(1366, 900));
        addTearDown(() => tester.binding.setSurfaceSize(null));
        await tester.pumpWidget(_shellApp(client, guard));
        await tester.pumpAndSettle();
        final editorState = tester.state(find.byType(Sh01Screen));
        await tester.tap(find.byTooltip('选择查看范围'));
        await tester.pumpAndSettle();
        await tester.tap(
          focused
              ? find.widgetWithText(TextButton, '全部可访问范围')
              : find.text('测试商业主体'),
        );
        await tester.pumpAndSettle();
        expect(asks, 1);
        expect(client.selectCalls, 0);
        expect(client.clearCalls, 0);
        expect(tester.state(find.byType(Sh01Screen)), same(editorState));
        expect(
          client.currentContextEnvelope['context']['mode'],
          focused ? 'FOCUS' : 'GLOBAL_ALL',
        );
        await tester.pumpWidget(const SizedBox());
        guard.unregister(owner);
        guard.dispose();
        expect(tester.takeException(), isNull);
      },
    );
  }

  testWidgets(
    'failed scope refresh retains the editor and marks its content unavailable',
    (tester) async {
      final client = _Client()..failRead = true;
      final guard = LumenisLeaveGuard();
      await tester.binding.setSurfaceSize(const Size(1366, 900));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      await tester.pumpWidget(_shellApp(client, guard));
      await tester.pumpAndSettle();
      final editorState = tester.state(find.byType(Sh01Screen));
      await tester.tap(find.byTooltip('选择查看范围'));
      await tester.pumpAndSettle();
      expect(tester.state(find.byType(Sh01Screen)), same(editorState));
      expect(
        tester.widget<Sh01Screen>(find.byType(Sh01Screen)).contextAvailable,
        isFalse,
      );
      expect(client.selectCalls + client.clearCalls, 0);
      await tester.tap(find.byKey(const ValueKey('context-picker-close')));
      await tester.pumpAndSettle();
      expect(tester.state(find.byType(Sh01Screen)), same(editorState));
      await tester.pumpWidget(const SizedBox());
      guard.dispose();
      expect(tester.takeException(), isNull);
    },
  );
}

const _delegates = [
  LumenisLocalizations.delegate,
  GlobalMaterialLocalizations.delegate,
  GlobalWidgetsLocalizations.delegate,
  GlobalCupertinoLocalizations.delegate,
];

Widget _routedApp(GoRouter router) => MaterialApp.router(
  routerConfig: router,
  theme: LumenisTheme.dark,
  locale: const Locale('zh', 'CN'),
  supportedLocales: LumenisLocalizations.supportedLocales,
  localizationsDelegates: _delegates,
);

Widget _shellApp(_Client client, LumenisLeaveGuard guard) => MaterialApp(
  theme: LumenisTheme.dark,
  locale: const Locale('zh', 'CN'),
  supportedLocales: LumenisLocalizations.supportedLocales,
  localizationsDelegates: _delegates,
  home: LumenisLeaveScope(
    guard: guard,
    child: LumenisWorkspaceShell(
      client: client,
      runtime: const {'ok': true},
      subjects: const [],
      contextEnvelope: client.currentContextEnvelope,
      initialScreenId: 'SH-01',
    ),
  ),
);

class _Client extends LumenisCoreClient {
  _Client({bool focused = false}) : envelope = _envelope(focused);
  Map<String, dynamic> envelope;
  bool failRead = false;
  int selectCalls = 0;
  int clearCalls = 0;

  @override
  Map<String, dynamic> get currentContextEnvelope => envelope;
  @override
  Future<Map<String, dynamic>> runtimeIdentity() async => {'ok': true};
  @override
  Future<Map<String, dynamic>> settingsContext() async {
    if (failRead) {
      throw const LumenisCoreException('Unavailable', statusCode: 503);
    }
    return envelope;
  }

  @override
  Future<Map<String, dynamic>> selectContext({
    required String domainId,
    required String subjectId,
  }) async {
    selectCalls++;
    return envelope = _envelope(true);
  }

  @override
  Future<Map<String, dynamic>> clearContext() async {
    clearCalls++;
    return envelope = _envelope(false);
  }

  @override
  Future<Map<String, dynamic>> settingsSubjects({
    String domainId = 'CTH',
  }) async => {
    'ok': true,
    'source': 'lumenis_subject_registry',
    'selection_only': true,
    'domains': [
      {'id': 'CTH', 'product': 'CTH'},
    ],
    'subjects': [
      {
        'subject_id': 'TEST-SUBJECT',
        'domain_id': 'CTH',
        'name_zh': '测试商业主体',
        'name_en': 'Test subject',
        'subject_type': 'company',
      },
    ],
  };
  @override
  Future<Map<String, dynamic>> screen(String screenId) async => {
    'ok': true,
    'screen': screenId,
    'bound': false,
    'focus_binding': {
      'state': 'unavailable',
      'applied': false,
      'message_key': 'context.screen_binding_unavailable',
    },
    'sections': [],
    'truth': {},
  };
}

Map<String, dynamic> _envelope(bool focused) => {
  'ok': true,
  'contract': 'lumenis.context.v1',
  'selection_only': true,
  'context': {
    'mode': focused ? 'FOCUS' : 'GLOBAL_ALL',
    'domain_id': focused ? 'CTH' : null,
    'subject_id': focused ? 'OLD-SUBJECT' : null,
    'display_name': focused ? {'zh-CN': '原商业主体'} : null,
  },
  'authorized_domains': [
    {'id': 'CTH', 'product': 'CTH'},
  ],
};
