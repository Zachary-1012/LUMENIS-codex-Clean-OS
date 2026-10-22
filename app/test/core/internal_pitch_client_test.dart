import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';

const _taskId = 'task-pitch-0123456789abcdef01234567';
const _docxMediaType =
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
const _docxBytes = <int>[0x50, 0x4b, 0x03, 0x04, 0x10, 0x20, 0x30, 0x40];

void main() {
  test(
    'authored manuscript task methods preserve exact scope and input',
    () async {
      final server = await _InternalPitchStub.start(
        taskState: 'failed',
        taskError: 'INTERNAL_PITCH_EXECUTION_FAILED',
      );
      addTearDown(server.close);
      final client = LumenisCoreClient(baseUrl: server.baseUrl);
      const scope = InternalPitchScope(
        domainId: 'CTH',
        subjectId: 'subject/with space',
        brandFocusId: null,
        globalScope: false,
      );
      final manuscript = InternalPitchManuscript(
        title: '用户提供的提案',
        summary: '用户提交的摘要。',
        sections: const [InternalPitchSection(heading: '目标', body: '说明预期结果。')],
        language: 'zh',
        authorship: 'user_supplied',
      );
      const revision = InternalPitchRevision(
        workId: 'WORK-0123456789abcdef01234567',
        previousArtifactId: 'ART-0123456789abcdef',
        expectedDraftDigest:
            'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
      );

      final prepared = await client.prepareInternalPitch(
        scope: scope,
        manuscript: manuscript,
        requestId: 'request-12345678',
        revision: revision,
      );
      final read = await client.readInternalPitch(
        taskId: _taskId,
        scope: scope,
      );
      final run = await client.runInternalPitch(taskId: _taskId, scope: scope);
      final cancel = await client.cancelInternalPitch(
        taskId: _taskId,
        scope: scope,
      );

      expect(prepared['task_id'], _taskId);
      expect(read['state'], 'failed');
      expect(read['error'], 'INTERNAL_PITCH_EXECUTION_FAILED');
      expect(run['task_id'], _taskId);
      expect(cancel['task_id'], _taskId);
      expect(server.requests.map((request) => request.method), [
        'POST',
        'GET',
        'POST',
        'POST',
      ]);
      expect(server.requests.map((request) => request.path), [
        '/api/experience/creation/internal-pitches',
        '/api/experience/creation/internal-pitches/$_taskId',
        '/api/experience/creation/internal-pitches/$_taskId/run',
        '/api/experience/creation/internal-pitches/$_taskId/cancel',
      ]);
      expect(server.requests[0].body, {
        'scope': scope.toJson(),
        'manuscript': manuscript.toJson(),
        'request_id': 'request-12345678',
        'profile': 'authored-manuscript/v4',
        'work_id': 'WORK-0123456789abcdef01234567',
        'previous_artifact_id': 'ART-0123456789abcdef',
        'expected_draft_digest': revision.expectedDraftDigest,
      });
      expect(server.requests[0].body!.containsKey('actor'), isFalse);
      expect(server.requests[0].body!.containsKey('citations'), isFalse);
      expect(server.requests[0].body!.containsKey('shot_plan'), isFalse);
      expect(server.requests[0].body!.containsKey('upstream_ref'), isFalse);
      expect(server.requests[1].query, scope.toQueryParameters());
      expect(server.requests[2].body, {'scope': scope.toJson()});
      expect(server.requests[3].body, {'scope': scope.toJson()});
      for (final request in server.requests) {
        expect(request.headers['authorization'], isNull);
        expect(request.headers['cookie'], isNull);
        expect(request.headers['x-lumenis-context-mode'], isNull);
        expect(request.headers['x-domain-id'], isNull);
        expect(request.headers['x-subject-id'], isNull);
        expect(request.headers['x-brand-focus-id'], isNull);
      }
    },
  );

  test(
    'Shared pitch uses body scope for writes and the typed header for reads/export',
    () async {
      final server = await _InternalPitchStub.start();
      addTearDown(server.close);
      final client = LumenisCoreClient(baseUrl: server.baseUrl);
      const scope = SharedWorkspaceScope();
      final manuscript = InternalPitchManuscript(
        title: '独立提案',
        summary: '从用户自己的创作要求开始。',
        sections: const [InternalPitchSection(heading: '方向', body: '具体内容。')],
        language: 'zh',
        authorship: 'user_supplied',
      );

      await client.prepareInternalPitch(
        scope: scope,
        manuscript: manuscript,
        requestId: 'shared-request-1234',
      );
      await client.readInternalPitch(taskId: _taskId, scope: scope);
      await client.runInternalPitch(taskId: _taskId, scope: scope);
      await client.cancelInternalPitch(taskId: _taskId, scope: scope);
      await client.exportInternalPitch(taskId: _taskId, scope: scope);

      expect(server.requests.map((request) => request.path), [
        '/api/experience/creation/internal-pitches',
        '/api/experience/creation/internal-pitches/$_taskId',
        '/api/experience/creation/internal-pitches/$_taskId/run',
        '/api/experience/creation/internal-pitches/$_taskId/cancel',
        '/api/experience/creation/internal-pitches/$_taskId/export',
      ]);
      expect(server.requests.first.body!['scope'], {
        'scope_kind': 'shared_workspace',
        'version': 1,
      });
      expect(server.requests[2].body, {
        'scope': {'scope_kind': 'shared_workspace', 'version': 1},
      });
      expect(server.requests[3].body, {
        'scope': {'scope_kind': 'shared_workspace', 'version': 1},
      });
      expect(server.requests[1].query, isEmpty);
      expect(server.requests.last.query, isEmpty);
      for (final request in [server.requests[1], server.requests.last]) {
        expect(
          request.headers['x-lumenis-workspace-scope'],
          '{"scope_kind":"shared_workspace","version":1}',
        );
      }
      for (final request in server.requests) {
        expect(request.headers['x-lumenis-context-mode'], isNull);
        expect(request.headers['x-domain-id'], isNull);
        expect(request.headers['x-subject-id'], isNull);
        expect(request.headers['x-brand-focus-id'], isNull);
        expect(request.headers['cookie'], isNull);
      }
    },
  );

  test(
    'invalid IDs fail locally and write errors are returned without retry',
    () async {
      final server = await _InternalPitchStub.start(
        runStatus: HttpStatus.conflict,
        runErrorCode: 'INTERNAL_PITCH_RUN_CONFLICT',
      );
      addTearDown(server.close);
      final client = LumenisCoreClient(baseUrl: server.baseUrl);
      const scope = InternalPitchScope(
        domainId: 'CTH',
        subjectId: 'subject-1',
        brandFocusId: null,
        globalScope: false,
      );

      await expectLater(
        client.readInternalPitch(taskId: '../$_taskId', scope: scope),
        throwsFormatException,
      );
      expect(server.requests, isEmpty);

      await expectLater(
        client.runInternalPitch(taskId: _taskId, scope: scope),
        throwsA(
          isA<LumenisCoreException>()
              .having((error) => error.statusCode, 'statusCode', 409)
              .having(
                (error) => error.errorCode,
                'errorCode',
                'INTERNAL_PITCH_RUN_CONFLICT',
              ),
        ),
      );
      expect(server.requests, hasLength(1));
      expect(server.requests.single.body, {'scope': scope.toJson()});
    },
  );

  test(
    'export returns guarded DOCX bytes and rejects JSON or wrong media',
    () async {
      final server = await _InternalPitchStub.start();
      addTearDown(server.close);
      final client = LumenisCoreClient(baseUrl: server.baseUrl);
      const scope = InternalPitchScope(
        domainId: 'CTH',
        subjectId: 'subject-1',
        brandFocusId: null,
        globalScope: false,
      );

      final file = await client.exportInternalPitch(
        taskId: _taskId,
        scope: scope,
      );
      expect(file.filename, 'document.docx');
      expect(file.mediaType, _docxMediaType);
      expect(file.bytes, _docxBytes);
      expect(
        server.requests.single.path,
        '/api/experience/creation/internal-pitches/$_taskId/export',
      );
      expect(server.requests.single.query, scope.toQueryParameters());
      expect(server.requests.single.headers['authorization'], isNull);
      expect(server.requests.single.headers['x-lumenis-context-mode'], isNull);

      final errorServer = await _InternalPitchStub.start(
        exportStatus: HttpStatus.serviceUnavailable,
        exportErrorCode: 'INTERNAL_PITCH_OWNER_UNAVAILABLE',
      );
      addTearDown(errorServer.close);
      final errorClient = LumenisCoreClient(baseUrl: errorServer.baseUrl);
      await expectLater(
        errorClient.exportInternalPitch(taskId: _taskId, scope: scope),
        throwsA(
          isA<LumenisCoreException>()
              .having((error) => error.statusCode, 'statusCode', 503)
              .having(
                (error) => error.errorCode,
                'errorCode',
                'INTERNAL_PITCH_OWNER_UNAVAILABLE',
              ),
        ),
      );

      final jsonServer = await _InternalPitchStub.start(
        exportMediaType: 'application/json',
        exportBytes: utf8.encode(' {"ok":false,"code":"NOT_A_FILE"}'),
      );
      addTearDown(jsonServer.close);
      final jsonClient = LumenisCoreClient(baseUrl: jsonServer.baseUrl);
      await expectLater(
        jsonClient.exportInternalPitch(taskId: _taskId, scope: scope),
        throwsFormatException,
      );

      final wrongTypeServer = await _InternalPitchStub.start(
        exportMediaType: 'application/pdf',
      );
      addTearDown(wrongTypeServer.close);
      final wrongTypeClient = LumenisCoreClient(
        baseUrl: wrongTypeServer.baseUrl,
      );
      await expectLater(
        wrongTypeClient.exportInternalPitch(taskId: _taskId, scope: scope),
        throwsFormatException,
      );
    },
  );

  test(
    'SavedWork pages and reopen expose only authored-manuscript/v4',
    () async {
      final server = await _InternalPitchStub.start();
      addTearDown(server.close);
      final client = LumenisCoreClient(baseUrl: server.baseUrl);

      final firstPage = await client.listAuthoredManuscripts(
        domainId: 'BMP',
        limit: 20,
      );
      expect(firstPage['items'], hasLength(1));
      expect(firstPage['has_more'], isTrue);
      expect(firstPage['next_cursor'], 'next-cursor-123');
      final secondPage = await client.listAuthoredManuscripts(
        domainId: 'BMP',
        limit: 20,
        cursor: firstPage['next_cursor'] as String,
      );
      expect(secondPage['items'], isEmpty);
      expect(secondPage['has_more'], isTrue);
      expect(secondPage['next_cursor'], 'third-page-cursor');

      final reopened = await client.reopenSavedManuscript(
        domainId: 'BMP',
        artifactId: 'ART-2222222222222222',
      );
      expect(
        (reopened['document'] as Map<String, dynamic>)['contract'],
        _authoredManuscriptV4,
      );
      await expectLater(
        client.reopenSavedManuscript(
          domainId: 'BMP',
          artifactId: 'ART-1111111111111111',
        ),
        throwsFormatException,
      );

      expect(server.requests.map((request) => request.path), [
        '/api/experience/saved-work',
        '/api/experience/saved-work',
        '/api/experience/saved-work/ART-2222222222222222',
        '/api/experience/saved-work/ART-1111111111111111',
      ]);
      expect(server.requests[0].query, {'kind': 'report', 'limit': '20'});
      expect(server.requests[1].query, {
        'kind': 'report',
        'limit': '20',
        'cursor': 'next-cursor-123',
      });
      for (final request in server.requests) {
        expect(request.headers['authorization'], isNull);
        expect(request.headers['cookie'], isNull);
        expect(request.headers['x-domain-id'], 'BMP');
      }
    },
  );
}

const _authoredManuscriptV4 = {
  'id': 'lumenis.internal-pitch',
  'version': '4',
  'required_payload_paths': ['manuscript', 'truth_state'],
};

const _sourceBoundPitchV3 = {
  'id': 'lumenis.internal-pitch',
  'version': '3',
  'required_payload_paths': ['manuscript', 'upstream_binding', 'truth_state'],
};

Map<String, dynamic> _savedManuscriptItem(Map<String, Object?> contract) => {
  'artifact': {'artifact_id': 'ART-2222222222222222'},
  'document': {
    'contract': contract,
    'payload': {
      'manuscript': {
        'title': 'A saved manuscript',
        'summary': 'Saved by the user.',
        'sections': [
          {'heading': 'Section', 'body': 'Body'},
        ],
        'language': 'en',
        'authorship': 'user_supplied',
      },
      'truth_state': {
        'source_admission': 'USER_AUTHORED_CONTENT',
        'external_fact_verification': 'NOT_INFERRED_FROM_AUTHORSHIP',
      },
    },
  },
};

class _CapturedRequest {
  const _CapturedRequest({
    required this.method,
    required this.path,
    required this.query,
    required this.headers,
    required this.body,
  });

  final String method;
  final String path;
  final Map<String, String> query;
  final Map<String, String> headers;
  final Map<String, dynamic>? body;
}

class _InternalPitchStub {
  _InternalPitchStub._({
    required this.server,
    required this.runStatus,
    required this.runErrorCode,
    required this.exportStatus,
    required this.exportErrorCode,
    required this.exportMediaType,
    required this.exportBytes,
    required this.taskState,
    required this.taskError,
  }) {
    server.listen(_handle);
  }

  final HttpServer server;
  final int runStatus;
  final String runErrorCode;
  final int exportStatus;
  final String exportErrorCode;
  final String exportMediaType;
  final List<int> exportBytes;
  final String taskState;
  final String? taskError;
  final List<_CapturedRequest> requests = [];

  String get baseUrl => 'http://127.0.0.1:${server.port}';

  static Future<_InternalPitchStub> start({
    int runStatus = HttpStatus.ok,
    String runErrorCode = 'INTERNAL_PITCH_RUN_FAILED',
    int exportStatus = HttpStatus.ok,
    String exportErrorCode = 'INTERNAL_PITCH_EXPORT_FAILED',
    String exportMediaType = _docxMediaType,
    List<int> exportBytes = _docxBytes,
    String taskState = 'pending',
    String? taskError,
  }) async => _InternalPitchStub._(
    server: await HttpServer.bind(InternetAddress.loopbackIPv4, 0),
    runStatus: runStatus,
    runErrorCode: runErrorCode,
    exportStatus: exportStatus,
    exportErrorCode: exportErrorCode,
    exportMediaType: exportMediaType,
    exportBytes: exportBytes,
    taskState: taskState,
    taskError: taskError,
  );

  Future<void> close() => server.close(force: true);

  Future<void> _handle(HttpRequest request) async {
    final rawBody = await request.fold<List<int>>(
      <int>[],
      (bytes, chunk) => bytes..addAll(chunk),
    );
    final headers = <String, String>{};
    request.headers.forEach((name, values) {
      headers[name.toLowerCase()] = values.join(', ');
    });
    final decoded = rawBody.isEmpty ? null : jsonDecode(utf8.decode(rawBody));
    requests.add(
      _CapturedRequest(
        method: request.method,
        path: request.uri.path,
        query: Map.unmodifiable(request.uri.queryParameters),
        headers: Map.unmodifiable(headers),
        body: decoded is Map<String, dynamic> ? decoded : null,
      ),
    );

    if (request.uri.path.endsWith('/export')) {
      if (exportStatus != HttpStatus.ok) {
        await _reply(request, exportStatus, {
          'ok': false,
          'code': exportErrorCode,
        });
        return;
      }
      request.response
        ..statusCode = HttpStatus.ok
        ..headers.contentType = ContentType.parse(exportMediaType)
        ..headers.set(
          'Content-Disposition',
          'attachment; filename="document.docx"',
        )
        ..add(exportBytes);
      await request.response.close();
      return;
    }
    if (request.uri.path == '/api/experience/saved-work' &&
        request.method == 'GET') {
      final isSecondPage = request.uri.queryParameters.containsKey('cursor');
      await _reply(request, HttpStatus.ok, {
        'ok': true,
        'result': {
          'items': isSecondPage
              ? [_savedManuscriptItem(_sourceBoundPitchV3)]
              : [
                  _savedManuscriptItem(_authoredManuscriptV4),
                  _savedManuscriptItem(_sourceBoundPitchV3),
                ],
          'unverified_candidates': 0,
          'has_more': true,
          'next_cursor': isSecondPage ? 'third-page-cursor' : 'next-cursor-123',
          'verification_complete': true,
        },
      });
      return;
    }
    if (request.uri.path.startsWith('/api/experience/saved-work/')) {
      final isAuthored = request.uri.path.endsWith('ART-2222222222222222');
      await _reply(request, HttpStatus.ok, {
        'ok': true,
        'result': _savedManuscriptItem(
          isAuthored ? _authoredManuscriptV4 : _sourceBoundPitchV3,
        ),
      });
      return;
    }
    if (request.uri.path.endsWith('/run') && runStatus != HttpStatus.ok) {
      await _reply(request, runStatus, {'ok': false, 'code': runErrorCode});
      return;
    }
    await _reply(
      request,
      request.uri.path.endsWith('/internal-pitches')
          ? HttpStatus.accepted
          : HttpStatus.ok,
      {
        'ok': true,
        'contract': 'lumenis.internal-pitch.v1',
        'result': {
          'task_id': _taskId,
          'state': taskState,
          'error': taskError,
          'action_receipt': null,
          'work': null,
        },
      },
    );
  }

  Future<void> _reply(
    HttpRequest request,
    int status,
    Map<String, dynamic> body,
  ) async {
    request.response
      ..statusCode = status
      ..headers.contentType = ContentType.json
      ..write(jsonEncode(body));
    await request.response.close();
  }
}
