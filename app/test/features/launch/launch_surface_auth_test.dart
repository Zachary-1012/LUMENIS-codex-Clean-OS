import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/core/lumenis_theme.dart';
import 'package:lumenis_app/features/launch/launch_surface.dart';

void main() {
  testWidgets('opens the existing workspace without a product account', (
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

      expect(find.text('商业运营总览'), findsOneWidget);
      expect(find.text('登录序境'), findsNothing);
      expect(find.byTooltip('退出登录'), findsNothing);
      expect(
        server.requests.map((request) => request.path),
        containsAllInOrder([
          '/api/auth/config',
          '/api/experience/runtime/identity',
          '/api/experience/screen/CTH-01',
        ]),
      );
      expect(
        server.requests.any((request) => request.path.startsWith('/v4/auth/')),
        isFalse,
      );
      expect(
        server.requests.any(
          (request) => request.path == '/api/settings/subjects',
        ),
        isFalse,
      );
      expect(server.requests.first.authorization, isNull);
      expect(
        server.requests
            .where((request) => request.path != '/api/auth/config')
            .every((request) => request.authorization == _authorization),
        isTrue,
      );
      expect(tester.takeException(), isNull);
    });
  });

  testWidgets('auth-disabled Core also opens without a product account', (
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

      expect(find.text('商业运营总览'), findsOneWidget);
      expect(find.text('登录序境'), findsNothing);
      expect(server.requests.last.path, '/api/experience/screen/CTH-01');
      expect(
        server.requests.every((request) => request.authorization == null),
        isTrue,
      );
      expect(tester.takeException(), isNull);
    });
  });

  testWidgets('CTH directory denial stays on CTH-02 without ejecting the App', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final client = _DeniedDirectoryClient();

    await tester.pumpWidget(_app(client));
    await tester.pumpAndSettle();
    await tester.tap(find.byTooltip('查看经营主体目录'));
    await tester.pumpAndSettle();

    expect(find.text('经营主体目录 · 当前经营主体不变'), findsOneWidget);
    expect(find.textContaining('主体名单授权尚未接入'), findsOneWidget);
    expect(find.text('商业运营总览'), findsNothing);
    expect(find.text('登录序境'), findsNothing);
    expect(find.byTooltip('返回商业运营总览'), findsOneWidget);
    expect(client.settingsSubjectsCalls, 1);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Core 401 shows recoverable connection state, never login form', (
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

      expect(find.text('序境核心暂不可访问'), findsOneWidget);
      expect(find.text('登录序境'), findsNothing);
      expect(find.text('重新连接'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  });

  testWidgets('Core 403 remains distinct and does not ask for an account', (
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

      expect(find.text('当前核心请求被拒绝'), findsOneWidget);
      expect(find.textContaining('HTTP 403'), findsOneWidget);
      expect(find.text('登录序境'), findsNothing);
      expect(tester.takeException(), isNull);
    });
  });
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

Widget _app(LumenisCoreClient client) => MaterialApp(
  theme: LumenisTheme.dark,
  home: Scaffold(body: LaunchSurface(client: client)),
);

Future<void> _pumpNetwork(WidgetTester tester) async {
  for (var attempt = 0; attempt < 12; attempt++) {
    await tester.runAsync(
      () => Future<void>.delayed(const Duration(milliseconds: 50)),
    );
    await tester.pump();
  }
}

const _username = 'operator';
const _password = 'secret';
final _authorization =
    'Basic ${base64Encode(utf8.encode('$_username:$_password'))}';

class _RecordedRequest {
  const _RecordedRequest({required this.path, required this.authorization});

  final String path;
  final String? authorization;
}

class _DeniedDirectoryClient extends LumenisCoreClient {
  int settingsSubjectsCalls = 0;

  @override
  Future<Map<String, dynamic>> runtimeIdentity() async => _identity;

  @override
  Future<Map<String, dynamic>> screen(String screenId) async => _cthScreen;

  @override
  Future<Map<String, dynamic>> settingsSubjects() async {
    settingsSubjectsCalls += 1;
    throw const LumenisCoreException(
      'GET /api/settings/subjects?domain_id=CTH failed with HTTP 401',
      statusCode: HttpStatus.unauthorized,
    );
  }
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
        'auth_header': authEnabled ? _authorization : '',
      });
      return;
    }

    final authorized = !authEnabled || authorization == _authorization;
    if (path == '/api/experience/runtime/identity') {
      final status =
          identityStatus ??
          (authorized ? HttpStatus.ok : HttpStatus.unauthorized);
      await _reply(
        request,
        status,
        status == HttpStatus.ok ? _identity : const {'error': 'denied'},
      );
      return;
    }
    if (path == '/api/experience/screen/CTH-01' && authorized) {
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

const Map<String, dynamic> _identity = {
  'ok': true,
  'app': 'LUMENIS Core',
  'api': 'experience_runtime.v1',
  'domain': 'cth',
  'subject': {
    'subject_id': 'CTH-SUBJECT-7',
    'brand_key': 'cth-brand',
    'product': 'CTH',
  },
};

const Map<String, dynamic> _cthScreen = {
  'ok': true,
  'screen': 'CTH-01',
  'bound': true,
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
