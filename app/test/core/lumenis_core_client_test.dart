import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';

void main() {
  test(
    'bootstraps existing Core transport without a product account',
    () async {
      final server = await _CoreStub.start();
      addTearDown(server.close);
      final client = LumenisCoreClient(baseUrl: server.baseUrl);

      await client.runtimeIdentity();
      final catalog = await client.sharedSkillsCatalog();
      final evidence = await client.contentEvidence('CGE-contract %?value');

      expect(catalog['capability'], 'Shared Content & Creation');
      expect(evidence['evidence']['evidence_id'], 'CGE-contract %?value');
      expect(server.requests.map((request) => request.path), [
        '/api/auth/config',
        '/api/experience/runtime/identity',
        '/api/experience/shared-skills',
        '/api/experience/content/evidence/CGE-contract%20%25%3Fvalue',
      ]);
      expect(server.requests.first.authorization, isNull);
      expect(
        server.requests
            .skip(1)
            .every((request) => request.authorization == _authorization),
        isTrue,
      );
      expect(
        server.requests.any((request) => request.path.startsWith('/v4/auth/')),
        isFalse,
      );
    },
  );

  test('Core auth disabled keeps existing public runtime access', () async {
    final server = await _CoreStub.start(authEnabled: false);
    addTearDown(server.close);
    final client = LumenisCoreClient(baseUrl: server.baseUrl);

    expect((await client.runtimeIdentity())['ok'], isTrue);
    expect(server.requests.map((request) => request.path), [
      '/api/auth/config',
      '/api/experience/runtime/identity',
    ]);
    expect(server.requests.last.authorization, isNull);
  });

  test(
    'CTH registry denial stays local and preserves the HTTP status',
    () async {
      final server = await _CoreStub.start(
        subjectStatus: HttpStatus.unauthorized,
      );
      addTearDown(server.close);
      final client = LumenisCoreClient(baseUrl: server.baseUrl);

      await client.runtimeIdentity();
      await expectLater(
        client.settingsSubjects(),
        throwsA(
          isA<LumenisCoreException>().having(
            (error) => error.statusCode,
            'statusCode',
            HttpStatus.unauthorized,
          ),
        ),
      );
      expect((await client.sharedSkillsCatalog())['ok'], isTrue);
      expect(server.requests.last.path, '/api/experience/shared-skills');
      expect(server.requests.last.authorization, _authorization);
      expect(
        server.requests.any((request) => request.path.startsWith('/v4/auth/')),
        isFalse,
      );
    },
  );

  test('shared GET helpers preserve backend status on failure', () async {
    final server = await _CoreStub.start(
      catalogStatus: HttpStatus.serviceUnavailable,
    );
    addTearDown(server.close);
    final client = LumenisCoreClient(baseUrl: server.baseUrl);

    await client.runtimeIdentity();
    await expectLater(
      client.sharedSkillsCatalog(),
      throwsA(
        isA<LumenisCoreException>().having(
          (error) => error.statusCode,
          'statusCode',
          HttpStatus.serviceUnavailable,
        ),
      ),
    );
    expect(server.requests.last.authorization, _authorization);
  });

  test('Core redirects fail closed without forwarding context', () async {
    final server = await _CoreStub.start(redirectCatalog: true);
    addTearDown(server.close);
    final client = LumenisCoreClient(baseUrl: server.baseUrl);

    await client.runtimeIdentity();
    await expectLater(
      client.sharedSkillsCatalog(),
      throwsA(
        isA<LumenisCoreException>().having(
          (error) => error.statusCode,
          'statusCode',
          HttpStatus.found,
        ),
      ),
    );
    expect(
      server.requests.where(
        (request) => request.path == '/api/experience/shared-skills',
      ),
      hasLength(1),
    );
    expect(
      server.requests.any((request) => request.path == '/redirected'),
      isFalse,
    );
  });

  for (final scheme in ['http', 'https']) {
    test(
      'remote $scheme skips config and never sends Core credentials',
      () async {
        final client = LumenisCoreClient(
          baseUrl: '$scheme://core.example.invalid:8201',
        );

        await expectLater(
          client.runtimeIdentity(),
          throwsA(
            isA<LumenisCoreException>()
                .having(
                  (error) => error.message,
                  'attempted request',
                  contains('GET /api/experience/runtime/identity'),
                )
                .having(
                  (error) => error.message,
                  'config bootstrap',
                  isNot(contains('/api/auth/config')),
                ),
          ),
        );
      },
    );
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

class _CoreStub {
  _CoreStub._({
    required this.server,
    required this.authEnabled,
    required this.catalogStatus,
    required this.subjectStatus,
    required this.redirectCatalog,
  }) {
    server.listen(_handle);
  }

  final HttpServer server;
  final bool authEnabled;
  final int catalogStatus;
  final int subjectStatus;
  final bool redirectCatalog;
  final List<_RecordedRequest> requests = [];

  String get baseUrl => 'http://127.0.0.1:${server.port}';

  static Future<_CoreStub> start({
    bool authEnabled = true,
    int catalogStatus = HttpStatus.ok,
    int subjectStatus = HttpStatus.ok,
    bool redirectCatalog = false,
  }) async {
    final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    return _CoreStub._(
      server: server,
      authEnabled: authEnabled,
      catalogStatus: catalogStatus,
      subjectStatus: subjectStatus,
      redirectCatalog: redirectCatalog,
    );
  }

  Future<void> close() => server.close(force: true);

  Future<void> _handle(HttpRequest request) async {
    final path = request.uri.toString();
    final authorization = request.headers.value(
      HttpHeaders.authorizationHeader,
    );
    requests.add(_RecordedRequest(path: path, authorization: authorization));

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
      await _reply(
        request,
        authorized ? HttpStatus.ok : HttpStatus.unauthorized,
        const {'ok': true},
      );
      return;
    }
    if (path == '/api/settings/subjects?domain_id=CTH') {
      await _reply(
        request,
        authorized ? subjectStatus : HttpStatus.unauthorized,
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
    if (path == '/api/experience/shared-skills') {
      if (redirectCatalog) {
        request.response.statusCode = HttpStatus.found;
        request.response.headers.set(HttpHeaders.locationHeader, '/redirected');
        await request.response.close();
        return;
      }
      await _reply(
        request,
        authorized ? catalogStatus : HttpStatus.unauthorized,
        const {
          'ok': true,
          'product': 'LUMENIS',
          'capability': 'Shared Content & Creation',
          'consumers': ['CTH', 'BMP'],
          'skills': [],
        },
      );
      return;
    }
    if (path == '/redirected') {
      await _reply(request, HttpStatus.ok, const {'ok': true});
      return;
    }
    if (path.startsWith('/api/experience/content/evidence/')) {
      await _reply(request, HttpStatus.ok, const {
        'ok': true,
        'evidence': {'evidence_id': 'CGE-contract %?value'},
      });
      return;
    }
    await _reply(request, HttpStatus.notFound, const {'ok': false});
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
