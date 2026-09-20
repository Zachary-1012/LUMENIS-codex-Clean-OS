import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';

void main() {
  test(
    'account-scoped subject reads use the canonical Bearer session',
    () async {
      final server = await _CoreStub.start();
      addTearDown(server.close);
      final client = LumenisCoreClient(baseUrl: server.baseUrl);

      await client.authenticate(username: _username, password: _password);
      await client.authenticateAccount(
        username: _username,
        password: _password,
      );
      final subjects = await client.subjects();

      expect(subjects, isEmpty);
      expect(client.hasAccountSession, isTrue);
      expect(server.requests.map((request) => request.path), [
        '/api/experience/runtime/identity',
        '/v4/auth/login',
        '/api/settings/subjects?domain_id=CTH',
      ]);
      expect(server.requests[1].authorization, isNull);
      expect(server.requests[2].authorization, 'Bearer test-session-token');
    },
  );

  test(
    'Shared GET helpers use the authenticated Core transport and safe paths',
    () async {
      final server = await _CoreStub.start();
      addTearDown(server.close);
      final client = LumenisCoreClient(baseUrl: server.baseUrl);

      await client.authenticate(username: 'operator', password: 'secret');
      final catalog = await client.sharedSkillsCatalog();
      final evidence = await client.contentEvidence('CGE-contract %?value');

      expect(catalog['capability'], 'Shared Content & Creation');
      expect(evidence['evidence']['evidence_id'], 'CGE-contract %?value');
      expect(server.requests.map((request) => request.path), [
        '/api/experience/runtime/identity',
        '/api/experience/shared-skills',
        '/api/experience/content/evidence/CGE-contract%20%25%3Fvalue',
      ]);
      expect(
        server.requests.every(
          (request) => request.authorization == _authorization,
        ),
        isTrue,
      );
    },
  );

  test('Shared GET helper preserves HTTP status on backend failure', () async {
    final server = await _CoreStub.start(
      catalogStatus: HttpStatus.serviceUnavailable,
    );
    addTearDown(server.close);
    final client = LumenisCoreClient(baseUrl: server.baseUrl);

    await client.authenticate(username: 'operator', password: 'secret');
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
  _CoreStub._({required this.server, required this.catalogStatus}) {
    server.listen(_handle);
  }

  final HttpServer server;
  final int catalogStatus;
  final List<_RecordedRequest> requests = [];

  String get baseUrl => 'http://127.0.0.1:${server.port}';

  static Future<_CoreStub> start({int catalogStatus = HttpStatus.ok}) async {
    final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    return _CoreStub._(server: server, catalogStatus: catalogStatus);
  }

  Future<void> close() => server.close(force: true);

  Future<void> _handle(HttpRequest request) async {
    final path = request.uri.toString();
    final authorization = request.headers.value(
      HttpHeaders.authorizationHeader,
    );
    requests.add(_RecordedRequest(path: path, authorization: authorization));

    if (path == '/v4/auth/login' && request.method == 'POST') {
      await _reply(request, HttpStatus.ok, const {
        'success': true,
        'token': 'test-session-token',
        'user': {'id': 1, 'username': _username},
      });
      return;
    }
    if (path == '/api/settings/subjects?domain_id=CTH') {
      await _reply(
        request,
        authorization == 'Bearer test-session-token'
            ? HttpStatus.ok
            : HttpStatus.unauthorized,
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
    if (path == '/api/experience/runtime/identity') {
      await _reply(request, HttpStatus.ok, const {'ok': true});
      return;
    }
    if (path == '/api/experience/shared-skills') {
      await _reply(request, catalogStatus, const {
        'ok': true,
        'product': 'LUMENIS',
        'capability': 'Shared Content & Creation',
        'consumers': ['CTH', 'BMP'],
        'skills': [],
      });
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
