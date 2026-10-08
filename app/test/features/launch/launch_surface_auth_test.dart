import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/core/lumenis_theme.dart';
import 'package:lumenis_app/features/cth/cth01/cth01_screen.dart';
import 'package:lumenis_app/features/launch/launch_surface.dart';
import 'package:lumenis_app/l10n/lumenis_localizations.dart';
import 'package:lumenis_app/navigation/lumenis_workspace_routes.dart';
import 'package:lumenis_app/shell/lumenis_workspace_shell.dart';

void main() {
  testWidgets(
    'Home task entry is available while runtime and context are pending',
    (tester) async {
      final client = _ControlledLaunchClient();

      await tester.pumpWidget(_app(client));
      await tester.pump();

      final shell = tester.widget<LumenisWorkspaceShell>(
        find.byType(LumenisWorkspaceShell),
      );
      expect(shell.initialScreenId, LumenisWorkspaceRoutes.rootScreenId);
      expect(shell.runtime['state'], 'LOADING');
      expect(shell.contextEnvelope, isNull);
      expect(client.identityCalls, 1);
      expect(client.contextCalls, 1);

      await tester.enterText(
        find.byKey(const ValueKey('ai01-task-input')),
        '整理本周客户风险变化',
      );
      expect(
        tester
            .widget<TextField>(find.byKey(const ValueKey('ai01-task-input')))
            .controller
            ?.text,
        '整理本周客户风险变化',
      );
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets(
    'runtime and context completing preserves Home draft and selection',
    (tester) async {
      final client = _ControlledLaunchClient();

      await tester.pumpWidget(_app(client));
      await tester.pump();
      await tester.enterText(
        find.byKey(const ValueKey('ai01-task-input')),
        '保留中的任务草稿',
      );

      final inputFinder = find.byKey(const ValueKey('ai01-task-input'));
      final controller = tester.widget<TextField>(inputFinder).controller!;
      controller.selection = const TextSelection.collapsed(offset: 4);

      client.identityResponses.single.complete(_healthyIdentity);
      await tester.pump();

      expect(
        tester.widget<TextField>(inputFinder).controller,
        same(controller),
      );
      expect(controller.text, '保留中的任务草稿');
      expect(controller.selection, const TextSelection.collapsed(offset: 4));
      expect(
        tester
            .widget<LumenisWorkspaceShell>(find.byType(LumenisWorkspaceShell))
            .runtime['state'],
        'CONNECTED',
      );

      client.contextResponses.single.complete(_globalContext);
      await tester.pumpAndSettle(const Duration(milliseconds: 180));

      final shell = tester.widget<LumenisWorkspaceShell>(
        find.byType(LumenisWorkspaceShell),
      );
      expect(shell.contextEnvelope, same(_globalContext));
      expect(inputFinder, findsOneWidget);
      expect(
        tester.widget<TextField>(inputFinder).controller,
        same(controller),
      );
      expect(controller.text, '保留中的任务草稿');
      expect(controller.selection, const TextSelection.collapsed(offset: 4));
      expect(tester.takeException(), isNull);
    },
  );

  for (final healthCase in [
    (guardian: 'degraded', expected: 'DEGRADED'),
    (guardian: 'offline', expected: 'OFFLINE'),
    (guardian: null, expected: 'UNKNOWN'),
  ]) {
    testWidgets('runtime ${healthCase.expected} state stays explicit', (
      tester,
    ) async {
      final client = _ControlledLaunchClient();

      await tester.pumpWidget(_app(client));
      await tester.pump();
      client.identityResponses.single.complete({
        'ok': true,
        if (healthCase.guardian != null)
          'runtime_guardian': {'overall': healthCase.guardian},
      });
      await tester.pump();

      final runtime = tester
          .widget<LumenisWorkspaceShell>(find.byType(LumenisWorkspaceShell))
          .runtime;
      expect(runtime['state'], healthCase.expected);
      expect(runtime['ok'], isFalse);
      expect(runtime['runtime_available'], isFalse);
      expect(tester.takeException(), isNull);
    });
  }

  testWidgets('offline Home stays editable and retry rereads runtime only', (
    tester,
  ) async {
    final client = _ControlledLaunchClient();

    await tester.pumpWidget(_app(client));
    await tester.pump();
    await tester.enterText(
      find.byKey(const ValueKey('ai01-task-input')),
      '离线时继续编辑',
    );
    final inputFinder = find.byKey(const ValueKey('ai01-task-input'));
    final controller = tester.widget<TextField>(inputFinder).controller!;
    controller.selection = const TextSelection.collapsed(offset: 3);

    client.contextResponses.single.complete(_globalContext);
    await tester.pumpAndSettle(const Duration(milliseconds: 180));
    expect(inputFinder, findsOneWidget);
    expect(tester.widget<TextField>(inputFinder).controller, same(controller));
    expect(controller.text, '离线时继续编辑');
    expect(controller.selection, const TextSelection.collapsed(offset: 3));

    client.identityResponses[0].completeError(
      const LumenisCoreException('Core is temporarily unavailable.'),
    );
    await tester.pumpAndSettle(const Duration(milliseconds: 180));

    var shell = tester.widget<LumenisWorkspaceShell>(
      find.byType(LumenisWorkspaceShell),
    );
    expect(shell.runtime['state'], 'OFFLINE');
    expect(shell.onRetryRuntime, isNotNull);
    expect(client.identityCalls, 1);
    expect(client.contextCalls, 1);
    expect(inputFinder, findsOneWidget);
    expect(tester.widget<TextField>(inputFinder).controller, same(controller));
    expect(controller.text, '离线时继续编辑');
    expect(controller.selection, const TextSelection.collapsed(offset: 3));

    await tester.tap(find.byKey(const ValueKey('workspace-runtime-retry')));
    await tester.pump();
    expect(client.identityCalls, 2);
    expect(client.contextCalls, 1);
    client.identityResponses[1].complete(_healthyIdentity);
    await tester.pumpAndSettle(const Duration(milliseconds: 180));

    shell = tester.widget<LumenisWorkspaceShell>(
      find.byType(LumenisWorkspaceShell),
    );
    expect(shell.runtime['state'], 'CONNECTED');
    expect(inputFinder, findsOneWidget);
    expect(tester.widget<TextField>(inputFinder).controller, same(controller));
    expect(controller.text, '离线时继续编辑');
    expect(controller.selection, const TextSelection.collapsed(offset: 3));
    expect(tester.takeException(), isNull);
  });

  testWidgets('late responses from a replaced Core client are ignored', (
    tester,
  ) async {
    final oldClient = _ControlledLaunchClient();
    final newClient = _ControlledLaunchClient();

    await tester.pumpWidget(_app(oldClient));
    await tester.pump();
    await tester.pumpWidget(_app(newClient));
    await tester.pump();

    newClient.identityResponses.single.complete(_healthyIdentity);
    newClient.contextResponses.single.complete(_contextNamed('新客户端范围'));
    await tester.pump();

    oldClient.identityResponses.single.completeError(
      const LumenisCoreException('old client failed', statusCode: 403),
    );
    oldClient.contextResponses.single.complete(_contextNamed('旧客户端范围'));
    await tester.pump();

    final shell = tester.widget<LumenisWorkspaceShell>(
      find.byType(LumenisWorkspaceShell),
    );
    expect(shell.client, same(newClient));
    expect(shell.runtime['state'], 'CONNECTED');
    expect(shell.contextEnvelope, same(newClient.completedContext));
    expect(shell.contextEnvelope, isNot(same(oldClient.completedContext)));
    expect(newClient.contextCalls, 1);
    expect(oldClient.contextCalls, 1);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Core 401 remains an access failure without an account wall', (
    tester,
  ) async {
    await _runWithRealHttp(() async {
      final server = await tester.runAsync(
        () => _TestCoreServer.start(identityStatus: HttpStatus.unauthorized),
      );
      expect(server, isNotNull);
      addTearDown(() => server!.close());

      await tester.pumpWidget(
        _app(LumenisCoreClient(baseUrl: server!.baseUrl)),
      );
      await _pumpNetwork(tester);

      final shell = tester.widget<LumenisWorkspaceShell>(
        find.byType(LumenisWorkspaceShell),
      );
      expect(shell.runtime['state'], 'AUTH_REQUIRED');
      expect(shell.runtime['status_code'], HttpStatus.unauthorized);
      expect(find.byKey(const ValueKey('ai01-task-input')), findsOneWidget);
      expect(find.text('登录序境'), findsNothing);
      expect(find.text('领域登录入口'), findsNothing);
      expect(
        server.requests.map((request) => request.path),
        contains('/api/experience/screen/AI-01'),
      );
      expect(
        server.requests.any((request) => request.path.startsWith('/v4/auth/')),
        isFalse,
      );
      expect(
        server.requests.every((request) => request.authorization == null),
        isTrue,
      );
      expect(tester.takeException(), isNull);
    });
  });

  testWidgets('Core 403 remains distinct and keeps Home available', (
    tester,
  ) async {
    await _runWithRealHttp(() async {
      final server = await tester.runAsync(
        () => _TestCoreServer.start(identityStatus: HttpStatus.forbidden),
      );
      expect(server, isNotNull);
      addTearDown(() => server!.close());

      await tester.pumpWidget(
        _app(LumenisCoreClient(baseUrl: server!.baseUrl)),
      );
      await _pumpNetwork(tester);

      final shell = tester.widget<LumenisWorkspaceShell>(
        find.byType(LumenisWorkspaceShell),
      );
      expect(shell.runtime['state'], 'ACCESS_UNAVAILABLE');
      expect(shell.runtime['status_code'], HttpStatus.forbidden);
      expect(find.byKey(const ValueKey('ai01-task-input')), findsOneWidget);
      expect(find.text('登录序境'), findsNothing);
      expect(find.text('领域登录入口'), findsNothing);
      expect(
        server.requests.every((request) => request.authorization == null),
        isTrue,
      );
      expect(tester.takeException(), isNull);
    });
  });

  testWidgets('local Core opens Home without a product account', (
    tester,
  ) async {
    await _runWithRealHttp(() async {
      final server = await tester.runAsync(() => _TestCoreServer.start());
      expect(server, isNotNull);
      addTearDown(() => server!.close());

      await tester.pumpWidget(
        _app(LumenisCoreClient(baseUrl: server!.baseUrl)),
      );
      await _pumpNetwork(tester);

      expect(find.byKey(const ValueKey('ai01-task-input')), findsOneWidget);
      expect(find.text('登录序境'), findsNothing);
      expect(find.byTooltip('退出登录'), findsNothing);
      expect(
        server.requests.map((request) => request.path),
        containsAll([
          '/api/experience/runtime/identity',
          '/api/settings/context',
          '/api/experience/screen/AI-01',
        ]),
      );
      expect(
        server.requests.any((request) => request.path.startsWith('/v4/auth/')),
        isFalse,
      );
      expect(
        server.requests.map((request) => request.path),
        isNot(contains('/api/auth/config')),
      );
      expect(
        server.requests.any(
          (request) => request.path == '/api/settings/subjects',
        ),
        isFalse,
      );
      expect(
        server.requests.every((request) => request.authorization == null),
        isTrue,
      );
      expect(tester.takeException(), isNull);
    });
  });

  testWidgets('auth-disabled Core opens Home without credentials', (
    tester,
  ) async {
    await _runWithRealHttp(() async {
      final server = await tester.runAsync(
        () => _TestCoreServer.start(authEnabled: false),
      );
      expect(server, isNotNull);
      addTearDown(() => server!.close());

      await tester.pumpWidget(
        _app(LumenisCoreClient(baseUrl: server!.baseUrl)),
      );
      await _pumpNetwork(tester);

      expect(find.byKey(const ValueKey('ai01-task-input')), findsOneWidget);
      expect(find.text('登录序境'), findsNothing);
      expect(
        server.requests.any(
          (request) => request.path == '/api/experience/screen/AI-01',
        ),
        isTrue,
      );
      expect(
        server.requests.every((request) => request.authorization == null),
        isTrue,
      );
      expect(tester.takeException(), isNull);
    });
  });

  testWidgets('explicit CTH deep link remains openable from LaunchSurface', (
    tester,
  ) async {
    await tester.pumpWidget(
      _app(_SuccessfulLaunchClient(), initialScreenId: 'CTH-01'),
    );
    await tester.pumpAndSettle();

    expect(find.byType(Cth01Screen), findsOneWidget);
    final cthScreen = find.byType(Cth01Screen);
    expect(
      find.descendant(of: cthScreen, matching: find.text('商业运营总览')),
      findsOneWidget,
    );
    expect(
      find
          .text('商业运营总览')
          .evaluate()
          .where(
            (element) =>
                element
                        .findAncestorWidgetOfExactType<
                          LumenisWorkspaceShell
                        >() !=
                    null &&
                element.findAncestorWidgetOfExactType<Cth01Screen>() == null,
          ),
      hasLength(1),
    );
    expect(tester.takeException(), isNull);
  });

  testWidgets('CTH directory denial stays on CTH-02 without ejecting the App', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final client = _DeniedDirectoryClient();

    await tester.pumpWidget(_app(client, initialScreenId: 'CTH-01'));
    await tester.pumpAndSettle();
    await tester.tap(find.byTooltip('查看经营主体目录'));
    await tester.pumpAndSettle();

    expect(find.text('经营主体目录 · 当前经营范围不变'), findsOneWidget);
    expect(find.textContaining('主体名单授权尚未接入'), findsOneWidget);
    expect(find.byType(Cth01Screen), findsNothing);
    expect(find.text('登录序境'), findsNothing);
    expect(find.byTooltip('返回商业运营总览'), findsOneWidget);
    expect(client.settingsSubjectsCalls, 1);
    expect(tester.takeException(), isNull);
  });
}

Widget _app(
  LumenisCoreClient client, {
  String initialScreenId = LumenisWorkspaceRoutes.rootScreenId,
  bool withScaffold = true,
}) => MaterialApp(
  locale: const Locale('zh', 'CN'),
  theme: LumenisTheme.dark,
  supportedLocales: LumenisLocalizations.supportedLocales,
  localizationsDelegates: const [
    LumenisLocalizations.delegate,
    GlobalMaterialLocalizations.delegate,
    GlobalWidgetsLocalizations.delegate,
    GlobalCupertinoLocalizations.delegate,
  ],
  home: withScaffold
      ? Scaffold(
          body: LaunchSurface(client: client, initialScreenId: initialScreenId),
        )
      : LaunchSurface(client: client, initialScreenId: initialScreenId),
);

class _ControlledLaunchClient extends LumenisCoreClient {
  final identityResponses = <Completer<Map<String, dynamic>>>[];
  final contextResponses = <Completer<Map<String, dynamic>>>[];
  int identityCalls = 0;
  int contextCalls = 0;
  Map<String, dynamic>? completedContext;

  @override
  Future<Map<String, dynamic>> runtimeIdentity() {
    identityCalls++;
    final response = Completer<Map<String, dynamic>>();
    identityResponses.add(response);
    return response.future;
  }

  @override
  Future<Map<String, dynamic>> settingsContext() {
    contextCalls++;
    final response = Completer<Map<String, dynamic>>();
    contextResponses.add(response);
    return response.future.then((value) {
      completedContext = value;
      return value;
    });
  }

  @override
  Future<Map<String, dynamic>> screen(String screenId) async =>
      screenId == 'AI-01' ? _ai01Screen : _cthScreen;
}

class _SuccessfulLaunchClient extends LumenisCoreClient {
  @override
  Future<Map<String, dynamic>> runtimeIdentity() async => _healthyIdentity;

  @override
  Future<Map<String, dynamic>> settingsContext() async => _globalContext;

  @override
  Future<Map<String, dynamic>> screen(String screenId) async =>
      screenId == 'AI-01' ? _ai01Screen : _cthScreen;
}

class _DeniedDirectoryClient extends _SuccessfulLaunchClient {
  int settingsSubjectsCalls = 0;

  @override
  Future<Map<String, dynamic>> settingsSubjects({
    String domainId = 'CTH',
  }) async {
    settingsSubjectsCalls++;
    throw const LumenisCoreException(
      'GET /api/settings/subjects?domain_id=CTH failed with HTTP 401',
      statusCode: HttpStatus.unauthorized,
    );
  }
}

Future<void> _runWithRealHttp(Future<void> Function() body) =>
    HttpOverrides.runZoned(
      body,
      createHttpClient: (context) =>
          _RealHttpOverrides().createHttpClient(context),
    );

class _RealHttpOverrides extends HttpOverrides {
  @override
  HttpClient createHttpClient(SecurityContext? context) {
    final client = super.createHttpClient(context);
    client.connectionTimeout = const Duration(seconds: 8);
    return client;
  }
}

Future<void> _pumpNetwork(WidgetTester tester) async {
  for (var attempt = 0; attempt < 12; attempt++) {
    await tester.runAsync(
      () => Future<void>.delayed(const Duration(milliseconds: 50)),
    );
    await tester.pump();
  }
  await tester.pumpAndSettle(const Duration(milliseconds: 180));
}

class _RecordedRequest {
  const _RecordedRequest({required this.path, required this.authorization});

  final String path;
  final String? authorization;
}

class _TestCoreServer {
  _TestCoreServer._({
    required this.server,
    required this.authEnabled,
    required this.identityStatus,
    required this.subjectStatus,
  }) {
    server.listen(_handle);
  }

  final HttpServer server;
  final bool authEnabled;
  final int? identityStatus;
  final int subjectStatus;
  final List<_RecordedRequest> requests = [];

  String get baseUrl => 'http://127.0.0.1:${server.port}';

  static Future<_TestCoreServer> start({
    bool authEnabled = true,
    int? identityStatus,
    int subjectStatus = HttpStatus.ok,
  }) async {
    final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    return _TestCoreServer._(
      server: server,
      authEnabled: authEnabled,
      identityStatus: identityStatus,
      subjectStatus: subjectStatus,
    );
  }

  Future<void> close() => server.close(force: true);

  Future<void> _handle(HttpRequest request) async {
    final path = request.uri.path;
    final authorization = request.headers.value(
      HttpHeaders.authorizationHeader,
    );
    requests.add(
      _RecordedRequest(
        path: request.uri.toString(),
        authorization: authorization,
      ),
    );

    if (path == '/api/auth/config') {
      await _reply(request, HttpStatus.ok, {
        'ok': true,
        'auth_enabled': authEnabled,
      });
      return;
    }

    final isLocalRequest = authorization == null;
    if (path == '/api/experience/runtime/identity') {
      final status =
          identityStatus ??
          (isLocalRequest ? HttpStatus.ok : HttpStatus.unauthorized);
      await _reply(
        request,
        status,
        status == HttpStatus.ok ? _healthyIdentity : const {'error': 'denied'},
      );
      return;
    }
    if (path == '/api/settings/context' && isLocalRequest) {
      await _reply(request, HttpStatus.ok, _globalContext);
      return;
    }
    if (path == '/api/experience/screen/AI-01' && isLocalRequest) {
      await _reply(request, HttpStatus.ok, _ai01Screen);
      return;
    }
    if (path == '/api/experience/screen/CTH-01' && isLocalRequest) {
      await _reply(request, HttpStatus.ok, _cthScreen);
      return;
    }
    if (path == '/api/settings/subjects' &&
        request.uri.queryParameters['domain_id'] == 'CTH') {
      await _reply(request, subjectStatus, const {
        'error': 'subject permission denied',
      });
      return;
    }
    await _reply(request, HttpStatus.notFound, const {'error': 'not found'});
  }

  Future<void> _reply(
    HttpRequest request,
    int status,
    Map<String, dynamic> body,
  ) async {
    request.response.statusCode = status;
    request.response.headers.contentType = ContentType.json;
    request.response.write(jsonEncode(body));
    await request.response.close();
  }
}

const Map<String, dynamic> _healthyIdentity = {
  'ok': true,
  'app': 'LUMENIS Core',
  'api': 'experience_runtime.v1',
  'runtime_guardian': {'overall': 'healthy'},
};

const Map<String, dynamic> _globalContext = {
  'ok': true,
  'contract': 'lumenis.context.v1',
  'context': {
    'mode': 'GLOBAL_ALL',
    'mode_label_key': 'context.mode.global_all',
    'domain_id': null,
    'product_id': null,
    'subject_id': null,
    'display_name': null,
    'display_state': 'not_applicable',
  },
  'authorized_domains': [
    {'id': 'CTH', 'name': 'Business', 'product': 'CTH'},
  ],
  'selection_only': true,
};

Map<String, dynamic> _contextNamed(String name) => {
  ..._globalContext,
  'context': {
    ...(_globalContext['context'] as Map<String, dynamic>),
    'display_name': {'zh-CN': name},
  },
};

const Map<String, dynamic> _ai01Screen = {
  'ok': true,
  'screen': 'AI-01',
  'bound': true,
  'source': 'runtime',
  'binding': {'unavailable': []},
  'sections': [
    {
      'type': 'split',
      'side': [
        {'type': 'runtime', 'items': []},
      ],
    },
    {'type': 'cards', 'items': []},
  ],
};

const Map<String, dynamic> _cthScreen = {
  'ok': true,
  'screen': 'CTH-01',
  'bound': true,
  'focus_binding': {'state': 'applied', 'applied': true},
  'sections': [
    {
      'type': 'kpis',
      'items': [
        {'id': 'cth.negative_voice', 'value': 1, 'unit': '条', 'state': 'ready'},
        {'id': 'cth.footfall', 'value': null, 'state': 'notcollected'},
        {'id': 'cth.member_sales', 'value': null, 'state': 'notcollected'},
      ],
    },
    {
      'type': 'split',
      'main': [
        {'type': 'events', 'state': 'empty', 'items': []},
      ],
      'side': [
        {'type': 'risks', 'state': 'empty', 'items': []},
      ],
    },
  ],
  'truth': {'canonical': {}},
};
