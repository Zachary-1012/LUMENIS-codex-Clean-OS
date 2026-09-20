import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/core/lumenis_theme.dart';
import 'package:lumenis_app/features/launch/launch_surface.dart';

void main() {
  testWidgets('401 opens login and rejected credentials remain in the form', (
    tester,
  ) async {
    await _runWithRealHttp(() async {
      final server = await tester.runAsync(
        () => _TestCoreServer.start(username: 'operator', password: 'correct'),
      );
      expect(server, isNotNull);
      addTearDown(() => server!.close());

      final client = LumenisCoreClient(baseUrl: server!.baseUrl);
      await tester.pumpWidget(_app(client));
      await _pumpNetwork(tester);

      expect(find.text('登录序境'), findsOneWidget);
      expect(find.textContaining('CTH · 序境·商业运营'), findsOneWidget);
      expect(find.textContaining('BMP · 序境·品牌市场'), findsOneWidget);
      expect(find.textContaining('SHARED · 共享能力'), findsOneWidget);
      expect(find.textContaining('SYSTEM · 系统'), findsOneWidget);
      expect(
        find.textContaining('Agent Groups · Cross-Product Execution'),
        findsOneWidget,
      );
      expect(server.requests.first.authorization, isNull);

      await tester.enterText(
        find.byKey(const ValueKey('auth/username')),
        'operator',
      );
      await tester.enterText(
        find.byKey(const ValueKey('auth/password')),
        'wrong',
      );
      await tester.tap(find.byKey(const ValueKey('auth/submit')));
      await tester.pump();
      await _pumpNetwork(tester);

      expect(find.text('账号凭证无效或未获准登录，请重试。'), findsOneWidget);
      expect(find.text('商业运营总览'), findsNothing);
      expect(server.requests.last.authorization, isNotNull);
      expect(client.hasSession, isFalse);
      expect(
        server.requests.any((request) => request.path == '/api/auth/config'),
        isFalse,
      );
      expect(tester.takeException(), isNull);
    });
  });

  testWidgets('403 shows the separate access-denied state', (tester) async {
    await _runWithRealHttp(() async {
      final server = await tester.runAsync(
        () => _TestCoreServer.start(
          username: 'operator',
          password: 'correct',
          identityStatus: HttpStatus.forbidden,
        ),
      );
      expect(server, isNotNull);
      addTearDown(() => server!.close());

      await tester.pumpWidget(
        _app(LumenisCoreClient(baseUrl: server!.baseUrl)),
      );
      await _pumpNetwork(tester);

      expect(find.text('当前账号没有访问权限'), findsOneWidget);
      expect(find.text('登录序境'), findsNothing);
      expect(find.textContaining('HTTP 403'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  });

  testWidgets('logout clears memory credentials before the next Core request', (
    tester,
  ) async {
    await _runWithRealHttp(() async {
      final server = await tester.runAsync(
        () => _TestCoreServer.start(username: 'operator', password: 'correct'),
      );
      expect(server, isNotNull);
      addTearDown(() => server!.close());

      final client = LumenisCoreClient(baseUrl: server!.baseUrl);
      await tester.pumpWidget(_app(client));
      await _pumpNetwork(tester);
      await tester.enterText(
        find.byKey(const ValueKey('auth/username')),
        'operator',
      );
      await tester.enterText(
        find.byKey(const ValueKey('auth/password')),
        'correct',
      );
      await tester.tap(find.byKey(const ValueKey('auth/submit')));
      await tester.pump();
      await _pumpNetwork(tester);

      expect(find.text('商业运营总览'), findsOneWidget);
      expect(client.hasSession, isTrue);
      expect(
        server.requests.any((request) => request.authorization != null),
        isTrue,
      );

      await tester.tap(find.byKey(const ValueKey('shell/logout')));
      await tester.pump();
      await _pumpNetwork(tester);

      expect(client.hasSession, isFalse);
      expect(find.text('登录序境'), findsOneWidget);

      LumenisCoreException? responseWithoutCredentials;
      await tester.runAsync(() async {
        try {
          await client.runtimeIdentity();
        } on LumenisCoreException catch (error) {
          responseWithoutCredentials = error;
        }
      });
      expect(responseWithoutCredentials?.statusCode, HttpStatus.unauthorized);
      expect(server.requests.last.path, '/api/experience/runtime/identity');
      expect(server.requests.last.authorization, isNull);

      // A fresh client has no persisted credentials to restore.
      await tester.pumpWidget(const SizedBox.shrink());
      final freshClient = LumenisCoreClient(baseUrl: server.baseUrl);
      await tester.pumpWidget(_app(freshClient));
      await _pumpNetwork(tester);
      expect(freshClient.hasSession, isFalse);
      expect(server.requests.last.authorization, isNull);
      expect(find.text('登录序境'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  });

  test(
    'Basic Auth is refused for non-loopback HTTP before any request',
    () async {
      final client = LumenisCoreClient(
        baseUrl: 'http://core.example.invalid:8201',
      );

      await expectLater(
        client.authenticate(username: 'operator', password: 'secret'),
        throwsA(
          isA<LumenisCoreException>().having(
            (error) => error.statusCode,
            'statusCode',
            isNull,
          ),
        ),
      );
      expect(client.hasSession, isFalse);
    },
  );
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

class _RecordedRequest {
  const _RecordedRequest({required this.path, required this.authorization});

  final String path;
  final String? authorization;
}

class _TestCoreServer {
  _TestCoreServer._({
    required this.server,
    required this.username,
    required this.password,
    required this.identityStatus,
  }) {
    server.listen(_handle);
  }

  final HttpServer server;
  final String username;
  final String password;
  final int? identityStatus;
  final List<_RecordedRequest> requests = [];
  static const _accountToken = 'test-session-token';

  String get baseUrl => 'http://127.0.0.1:${server.port}';

  static Future<_TestCoreServer> start({
    required String username,
    required String password,
    int? identityStatus,
  }) async {
    final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    return _TestCoreServer._(
      server: server,
      username: username,
      password: password,
      identityStatus: identityStatus,
    );
  }

  Future<void> close() => server.close(force: true);

  Future<void> _handle(HttpRequest request) async {
    final authorization = request.headers.value(
      HttpHeaders.authorizationHeader,
    );
    requests.add(
      _RecordedRequest(path: request.uri.path, authorization: authorization),
    );

    final expected =
        'Basic ${base64Encode(utf8.encode('$username:$password'))}';
    final authorized = authorization == expected;
    final path = request.uri.path;
    if (path == '/v4/auth/login' && request.method == 'POST') {
      final credentials = jsonDecode(await utf8.decoder.bind(request).join());
      final accountAuthorized =
          credentials is Map &&
          credentials['username'] == username &&
          credentials['password'] == password;
      await _reply(
        request,
        HttpStatus.ok,
        accountAuthorized
            ? const {
                'success': true,
                'token': _accountToken,
                'user': {'id': 1, 'username': 'operator'},
              }
            : const {'success': false, 'message': 'rejected'},
      );
      return;
    }
    if (path == '/v4/auth/logout' && request.method == 'POST') {
      await _reply(
        request,
        authorization == 'Bearer $_accountToken'
            ? HttpStatus.ok
            : HttpStatus.unauthorized,
        const {'success': true},
      );
      return;
    }
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
    if (path == '/api/settings/subjects') {
      final accountAuthorized = authorization == 'Bearer $_accountToken';
      await _reply(
        request,
        accountAuthorized ? HttpStatus.ok : HttpStatus.unauthorized,
        const {
          'ok': true,
          'source': 'lumenis_subject_registry',
          'selection_only': true,
          'domains': [
            {'id': 'CTH', 'product': 'CTH'},
          ],
          'subjects': [],
        },
      );
      return;
    }
    if (path == '/api/experience/screen/CTH-01' && authorized) {
      await _reply(request, HttpStatus.ok, _cthScreen);
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
