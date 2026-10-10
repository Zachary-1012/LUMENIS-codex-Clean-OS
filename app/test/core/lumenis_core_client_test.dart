import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';

void main() {
  test(
    'reads the open workspace without fetching or forwarding Core credentials',
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
        '/api/experience/runtime/identity',
        '/api/experience/shared-skills',
        '/api/experience/content/evidence/CGE-contract%20%25%3Fvalue',
      ]);
      expect(
        server.requests.every((request) => request.authorization == null),
        isTrue,
      );
      expect(
        server.requests.any((request) => request.path.startsWith('/v4/auth/')),
        isFalse,
      );
    },
  );

  test(
    'mismatched context responses preserve the confirmed selection',
    () async {
      final server = await _CoreStub.start(
        contextResponses: [
          _contextEnvelope('FOCUS', domainId: 'CTH', subjectId: 'shop-1'),
          _contextEnvelope('FOCUS', domainId: 'CTH', subjectId: 'other-shop'),
          _contextEnvelope('FOCUS', domainId: 'BMP', subjectId: 'next-shop'),
          _contextEnvelope('GLOBAL_ALL'),
          _contextEnvelope('FOCUS', domainId: 'CTH', subjectId: 'other-shop'),
          _contextEnvelope('GLOBAL_ALL'),
        ],
      );
      addTearDown(server.close);
      final client = LumenisCoreClient(baseUrl: server.baseUrl);

      await client.runtimeIdentity();
      final confirmedFocus = await client.selectContext(
        domainId: 'CTH',
        subjectId: 'shop-1',
      );

      Future<void> expectConfirmedFocusRemains() async {
        expect(client.currentContextEnvelope, same(confirmedFocus));
        expect((await client.sharedSkillsCatalog())['ok'], isTrue);
        final request = server.requests.last;
        expect(request.path, '/api/experience/shared-skills');
        expect(request.contextMode, 'FOCUS');
        expect(request.domainId, 'CTH');
        expect(request.subjectId, 'shop-1');
      }

      await expectLater(
        client.selectContext(domainId: 'CTH', subjectId: 'next-shop'),
        throwsA(isA<FormatException>()),
      );
      await expectConfirmedFocusRemains();

      await expectLater(
        client.selectContext(domainId: 'CTH', subjectId: 'next-shop'),
        throwsA(isA<FormatException>()),
      );
      await expectConfirmedFocusRemains();

      await expectLater(
        client.selectContext(domainId: 'CTH', subjectId: 'next-shop'),
        throwsA(isA<FormatException>()),
      );
      await expectConfirmedFocusRemains();

      await expectLater(client.clearContext(), throwsA(isA<FormatException>()));
      await expectConfirmedFocusRemains();

      final cleared = await client.clearContext();
      expect((cleared['context'] as Map)['mode'], 'GLOBAL_ALL');
      expect(client.currentContextEnvelope, same(cleared));
      expect((await client.sharedSkillsCatalog())['ok'], isTrue);
      final globalRequest = server.requests.last;
      expect(globalRequest.contextMode, 'GLOBAL_ALL');
      expect(globalRequest.domainId, isNull);
      expect(globalRequest.subjectId, isNull);
    },
  );

  test(
    'client cleanup does not request or recreate a Core credential',
    () async {
      final server = await _CoreStub.start();
      addTearDown(server.close);
      final client = LumenisCoreClient(baseUrl: server.baseUrl);

      expect((await client.runtimeIdentity())['ok'], isTrue);
      client.clearCredentials();
      expect((await client.runtimeIdentity())['ok'], isTrue);
      expect(server.requests.map((request) => request.path), [
        '/api/experience/runtime/identity',
        '/api/experience/runtime/identity',
      ]);
      expect(server.requests.last.authorization, isNull);
    },
  );

  for (final status in [HttpStatus.unauthorized, HttpStatus.forbidden]) {
    test(
      'runtime HTTP $status is preserved without credential recovery',
      () async {
        final server = await _CoreStub.start(runtimeStatus: status);
        addTearDown(server.close);
        final client = LumenisCoreClient(baseUrl: server.baseUrl);

        await expectLater(
          client.runtimeIdentity(),
          throwsA(
            isA<LumenisCoreException>().having(
              (error) => error.statusCode,
              'statusCode',
              status,
            ),
          ),
        );
        expect(server.requests.map((request) => request.path), [
          '/api/experience/runtime/identity',
        ]);
        expect(server.requests.single.authorization, isNull);
      },
    );
  }

  test('media file read never inherits a runtime credential', () async {
    final server = await _CoreStub.start();
    addTearDown(server.close);
    final client = LumenisCoreClient(baseUrl: server.baseUrl);

    await client.runtimeIdentity();
    final file = await client.contentProjectFile(
      domainId: 'CTH',
      artifactId: 'ART-contract',
      package: true,
    );

    expect(file.filename, 'ART-contract.zip');
    expect(file.mediaType, 'application/zip');
    expect(file.bytes, [80, 75, 5, 6, ...List<int>.filled(18, 0)]);
    expect(server.requests.map((request) => request.path), [
      '/api/experience/runtime/identity',
      '/api/experience/content-projects/ART-contract/package',
    ]);
    expect(
      server.requests.every((request) => request.authorization == null),
      isTrue,
    );
    expect(server.requests.last.domainId, 'CTH');
  });

  for (final status in [HttpStatus.unauthorized, HttpStatus.forbidden]) {
    test(
      'media HTTP $status remains denied without bootstrap or retry',
      () async {
        final server = await _CoreStub.start(fileStatus: status);
        addTearDown(server.close);
        final client = LumenisCoreClient(baseUrl: server.baseUrl);

        await expectLater(
          client.contentProjectFile(
            domainId: 'CTH',
            artifactId: 'ART-contract',
            package: true,
          ),
          throwsA(
            isA<LumenisCoreException>().having(
              (error) => error.statusCode,
              'statusCode',
              status,
            ),
          ),
        );
        expect(server.requests.map((request) => request.path), [
          '/api/experience/content-projects/ART-contract/package',
        ]);
        expect(server.requests.single.authorization, isNull);
      },
    );
  }

  test(
    'controlled browser transport omits bootstrap credentials and context headers',
    () async {
      final server = await _CoreStub.start();
      addTearDown(server.close);
      final client = LumenisCoreClient(baseUrl: server.baseUrl);

      final session = await client.openBrowserSession();
      final frame = await client.browserFrame('bs_0123456789ab');

      expect(session['session_id'], 'bs_0123456789ab');
      expect(frame.targetId, 'target_approved');
      expect(frame.pageRevision, 1);
      expect(server.requests.map((request) => request.path), [
        '/api/browser/sessions',
        '/api/browser/sessions/bs_0123456789ab/frame',
      ]);
      for (final request in server.requests) {
        expect(request.authorization, isNull);
        expect(request.contextMode, isNull);
        expect(request.domainId, isNull);
        expect(request.subjectId, isNull);
      }
    },
  );

  test(
    'controlled browser refuses a non-loopback Core before issuing a request',
    () async {
      final client = LumenisCoreClient(
        baseUrl: 'https://core.example.invalid:8201',
      );

      expect(
        () => client.openBrowserSession(),
        throwsA(
          isA<LumenisCoreException>().having(
            (error) => error.errorCode,
            'errorCode',
            'BROWSER_LOCAL_CORE_REQUIRED',
          ),
        ),
      );
    },
  );

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
      expect(server.requests.last.authorization, isNull);
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
    expect(server.requests.last.authorization, isNull);
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

const _browserPng = <int>[
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

Map<String, dynamic> _contextEnvelope(
  String mode, {
  String? domainId,
  String? subjectId,
}) => {
  'ok': true,
  'contract': 'lumenis.context.v1',
  'selection_only': true,
  'context': {'mode': mode, 'domain_id': ?domainId, 'subject_id': ?subjectId},
};

class _RecordedRequest {
  const _RecordedRequest({
    required this.method,
    required this.path,
    required this.authorization,
    required this.contextMode,
    required this.domainId,
    required this.subjectId,
  });

  final String method;
  final String path;
  final String? authorization;
  final String? contextMode;
  final String? domainId;
  final String? subjectId;
}

class _CoreStub {
  _CoreStub._({
    required this.server,
    required this.runtimeStatus,
    required this.fileStatus,
    required this.catalogStatus,
    required this.subjectStatus,
    required this.redirectCatalog,
    required List<Map<String, dynamic>> contextResponses,
  }) {
    _contextResponses = List.of(contextResponses);
    server.listen(_handle);
  }

  final HttpServer server;
  final int runtimeStatus;
  final int fileStatus;
  final int catalogStatus;
  final int subjectStatus;
  final bool redirectCatalog;
  final List<_RecordedRequest> requests = [];
  late final List<Map<String, dynamic>> _contextResponses;

  String get baseUrl => 'http://127.0.0.1:${server.port}';

  static Future<_CoreStub> start({
    int runtimeStatus = HttpStatus.ok,
    int fileStatus = HttpStatus.ok,
    int catalogStatus = HttpStatus.ok,
    int subjectStatus = HttpStatus.ok,
    bool redirectCatalog = false,
    List<Map<String, dynamic>> contextResponses = const [],
  }) async {
    final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    return _CoreStub._(
      server: server,
      runtimeStatus: runtimeStatus,
      fileStatus: fileStatus,
      catalogStatus: catalogStatus,
      subjectStatus: subjectStatus,
      redirectCatalog: redirectCatalog,
      contextResponses: contextResponses,
    );
  }

  Future<void> close() => server.close(force: true);

  Future<void> _handle(HttpRequest request) async {
    final path = request.uri.toString();
    final authorization = request.headers.value(
      HttpHeaders.authorizationHeader,
    );
    requests.add(
      _RecordedRequest(
        method: request.method,
        path: path,
        authorization: authorization,
        contextMode: request.headers.value('X-Lumenis-Context-Mode'),
        domainId: request.headers.value('X-Domain-Id'),
        subjectId: request.headers.value('X-Subject-ID'),
      ),
    );

    if (path == '/api/auth/config') {
      await _reply(request, HttpStatus.ok, {'ok': true, 'auth_enabled': true});
      return;
    }
    // Simulate the server-owned open-workspace boundary, which rejects any
    // client-supplied identity credential. This is contract evidence only.
    final authorized = authorization == null;
    if (path == '/api/experience/content-projects/ART-contract/package') {
      request.response
        ..statusCode = authorized ? fileStatus : HttpStatus.unauthorized
        ..headers.contentType = ContentType('application', 'zip')
        ..add([80, 75, 5, 6, ...List<int>.filled(18, 0)]);
      await request.response.close();
      return;
    }
    if (path == '/api/settings/context') {
      if (!authorized) {
        await _reply(request, HttpStatus.unauthorized, const {'ok': false});
        return;
      }
      await _reply(request, HttpStatus.ok, _contextResponses.removeAt(0));
      return;
    }
    if (path == '/api/experience/runtime/identity') {
      await _reply(
        request,
        authorized ? runtimeStatus : HttpStatus.unauthorized,
        const {'ok': true},
      );
      return;
    }
    if (path == '/api/browser/sessions' && request.method == 'POST') {
      await _reply(request, HttpStatus.ok, const {
        'ok': true,
        'session_id': 'bs_0123456789ab',
        'status': 'running',
        'engine_label': 'Controlled Browser',
        'target_id': 'target_approved',
        'page_revision': 1,
        'current_title': 'Example',
        'current_url': 'https://example.com',
        'allowed_actions': ['navigate', 'reload', 'frame'],
      });
      return;
    }
    if (path == '/api/browser/sessions/bs_0123456789ab/frame' &&
        request.method == 'GET') {
      request.response
        ..statusCode = HttpStatus.ok
        ..headers.contentType = ContentType('image', 'png')
        ..headers.set('X-LUMENIS-Frame-Id', 'frame_approved')
        ..headers.set('X-LUMENIS-Target-Id', 'target_approved')
        ..headers.set('X-LUMENIS-Page-Revision', '1')
        ..headers.set('X-LUMENIS-Captured-At', '2026-10-05T10:00:00Z')
        ..headers.set('X-LUMENIS-Frame-Width', '1')
        ..headers.set('X-LUMENIS-Viewport-Width', '1280')
        ..headers.set('X-LUMENIS-Viewport-Height', '720')
        ..headers.set('X-LUMENIS-Viewport-DPR', '1')
        ..headers.set('X-LUMENIS-Frame-Height', '1')
        ..add(_browserPng);
      await request.response.close();
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
