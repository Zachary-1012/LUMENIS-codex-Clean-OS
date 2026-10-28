import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';

void main() {
  late HttpServer server;
  late LumenisCoreClient client;
  late List<Map<String, Object?>> calls;
  var responseStatus = 200;
  Map<String, Object?> response = {};
  List<int>? responseBytes;
  String? responseMediaType;

  setUp(() async {
    server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    client = LumenisCoreClient(baseUrl: 'http://127.0.0.1:${server.port}');
    calls = [];
    responseStatus = 200;
    response = {'ok': true};
    responseBytes = null;
    responseMediaType = null;
    server.listen((request) async {
      final bytes = await request.fold<List<int>>(
        [],
        (all, chunk) => all..addAll(chunk),
      );
      final body = bytes.isEmpty ? null : jsonDecode(utf8.decode(bytes));
      calls.add({
        'path': request.uri.path,
        'query': request.uri.queryParameters,
        'method': request.method,
        'type': request.headers.contentType?.mimeType,
        'domain': request.headers.value('X-Domain-Id'),
        'product': request.headers.value('X-Product-Id'),
        'mode': request.headers.value('X-Lumenis-Context-Mode'),
        'subject': request.headers.value('X-Subject-ID'),
        'workspace': request.headers.value('X-Lumenis-Workspace-Scope'),
        'authorization': request.headers.value('Authorization'),
        'body': body,
      });
      request.response.statusCode = responseStatus;
      request.response.headers.contentType = responseMediaType == null
          ? ContentType.json
          : ContentType.parse(responseMediaType!);
      if (responseBytes case final bytes?) {
        request.response.add(bytes);
      } else {
        request.response.write(jsonEncode(response));
      }
      await request.response.close();
    });
  });

  tearDown(() => server.close(force: true));

  test(
    'start sends only supported input and preserves pending admission state',
    () async {
      responseStatus = 202;
      response = {
        'ok': true,
        'task': {
          'task_id': 'rbrief_01234567-89ab-cdef-0123-456789abcdef',
          'state': 'pending',
          'can_resume': true,
        },
        'publish_status': 'not_performed',
      };

      final admitted = await client.startSourceBriefTask(
        domainId: 'CTH',
        businessQuestion: 'Which sources changed this week?',
      );

      expect(admitted, response);
      expect((admitted['task'] as Map)['state'], 'pending');
      expect(calls.single['method'], 'POST');
      expect(
        calls.single['path'],
        '/api/experience/reports/source-brief/start',
      );
      expect(calls.single['type'], 'application/json');
      expect(calls.single['body'], {
        'limit': 30,
        'business_question': 'Which sources changed this week?',
      });
      expect(calls.single['domain'], 'CTH');
      expect(calls.single['product'], 'CTH');
      expect(calls.single['mode'], 'GLOBAL_ALL');
      expect(calls.single['subject'], isNull);
      expect(calls.single['authorization'], isNull);

      calls.clear();
      response = {
        'ok': true,
        'task': {'state': 'pending'},
      };
      await client.startSourceBriefTask(domainId: 'BMP');
      expect(calls.single['body'], {'limit': 30});
      expect(calls.single['domain'], 'BMP');
      expect(calls.single['product'], 'ZBMP');
    },
  );

  test(
    'selected material request keeps question, source IDs and replay identity',
    () async {
      await client.startDomainSourceBriefTask(
        domainId: 'CTH',
        sourceIds: ['SRC-1'],
        requestId: 'research-request-1',
        businessQuestion: '  Which claims need checking?  ',
      );
      expect(calls.single['body'], {
        'source_ids': ['SRC-1'],
        'limit': 1,
        'request_id': 'research-request-1',
        'business_question': 'Which claims need checking?',
      });
      expect(calls.single['domain'], 'CTH');
      calls.clear();
      await client.startDomainSourceBriefTask(
        domainId: 'BMP',
        sourceIds: ['SRC-2'],
        requestId: 'research-request-2',
        businessQuestion: '   ',
      );
      expect(calls.single['body'], {
        'source_ids': ['SRC-2'],
        'limit': 1,
        'request_id': 'research-request-2',
      });
    },
  );

  test(
    'task read, resume, and job readback use distinct existing routes',
    () async {
      const taskId = 'rbrief_01234567-89ab-cdef-0123-456789abcdef';
      const jobId = 'brief-0123456789abcdef0123456789abcdef';

      response = {
        'ok': true,
        'task': {'task_id': taskId, 'state': 'interrupted', 'can_resume': true},
        'publish_status': 'not_performed',
      };
      final task = await client.sourceBriefTask(
        domainId: 'BMP',
        taskId: taskId,
      );
      expect(task, response);
      expect(calls.single['method'], 'GET');
      expect(
        calls.single['path'],
        '/api/experience/reports/source-brief/tasks/$taskId',
      );
      expect(calls.single['body'], isNull);
      expect(calls.single['domain'], 'BMP');
      expect(calls.single['product'], 'ZBMP');

      calls.clear();
      response = {
        'ok': true,
        'task': {'task_id': taskId, 'state': 'pending', 'can_resume': true},
        'publish_status': 'not_performed',
      };
      final resumed = await client.resumeSourceBriefTask(
        domainId: 'BMP',
        taskId: taskId,
      );
      expect(resumed, response);
      expect(calls.single['method'], 'POST');
      expect(
        calls.single['path'],
        '/api/experience/reports/source-brief/tasks/$taskId/resume',
      );
      expect(calls.single['body'], <String, Object?>{});
      expect(resumed['task'], containsPair('task_id', taskId));

      calls.clear();
      response = {
        'ok': true,
        'result': {
          'job_id': jobId,
          'artifact_outcome': {'state': 'ready'},
        },
        'publish_status': 'not_performed',
      };
      final job = await client.sourceBriefJob(domainId: 'CTH', jobId: jobId);
      expect(job, response);
      expect(calls.single['method'], 'GET');
      expect(
        calls.single['path'],
        '/api/experience/reports/source-brief/jobs/$jobId',
      );
      expect(calls.single['body'], isNull);
      expect(calls.single['domain'], 'CTH');
      expect(calls.single['product'], 'CTH');
    },
  );

  test('denial remains an HTTP permission error', () async {
    responseStatus = 403;
    response = {'ok': false, 'code': 'SOURCE_BRIEF_GENERATE_DENIED'};

    await expectLater(
      client.startSourceBriefTask(domainId: 'CTH'),
      throwsA(
        isA<LumenisCoreException>()
            .having((error) => error.statusCode, 'status', 403)
            .having(
              (error) => error.errorCode,
              'code',
              'SOURCE_BRIEF_GENERATE_DENIED',
            ),
      ),
    );
    expect(calls.single['path'], '/api/experience/reports/source-brief/start');
    expect(calls.single['body'], {'limit': 30});
  });

  test('task and job identifiers cannot escape their route', () {
    expect(
      () => client.sourceBriefTask(domainId: 'CTH', taskId: '../private'),
      throwsFormatException,
    );
    expect(
      () => client.sourceBriefJob(domainId: 'CTH', jobId: '../private'),
      throwsFormatException,
    );
    expect(calls, isEmpty);
  });

  test(
    'saved domain exports preserve exact CTH and BMP focused scopes',
    () async {
      for (final domain in ['CTH', 'BMP']) {
        responseBytes = null;
        responseMediaType = null;
        response = {
          'ok': true,
          'contract': 'lumenis.context.v1',
          'selection_only': true,
          'context': {
            'mode': 'FOCUS',
            'domain_id': domain,
            'subject_id': 'selected-report-focus',
          },
        };
        await client.selectContext(
          domainId: domain,
          subjectId: 'selected-report-focus',
        );
        calls.clear();
        responseMediaType = 'text/markdown; charset=utf-8';
        responseBytes = utf8.encode('A saved $domain report.');
        final file = await client.exportSourceBriefSavedWork(
          domainId: domain,
          artifactId: 'ART-0123456789abcdef',
          format: 'md',
        );
        expect(utf8.decode(file.bytes), 'A saved $domain report.');
        expect(
          calls.single['path'],
          '/api/experience/saved-work/ART-0123456789abcdef/export',
        );
        expect(calls.single['query'], {'format': 'md', 'purpose': 'delivery'});
        expect(calls.single['domain'], domain);
        expect(calls.single['product'], domain == 'BMP' ? 'ZBMP' : 'CTH');
        expect(calls.single['mode'], 'FOCUS');
        expect(calls.single['subject'], 'selected-report-focus');
        expect(calls.single['workspace'], isNull);
        expect(calls.single['authorization'], isNull);

        calls.clear();
        await client.exportSharedSavedWork(
          artifactId: 'ART-0123456789abcdef',
          format: 'md',
        );
        expect(
          calls.single['workspace'],
          '{"scope_kind":"shared_workspace","version":1}',
        );
        for (final key in [
          'domain',
          'product',
          'mode',
          'subject',
          'authorization',
        ]) {
          expect(calls.single[key], isNull, reason: key);
        }
        calls.clear();
        expect(
          () => client.exportSourceBriefSavedWork(
            domainId: domain == 'CTH' ? 'BMP' : 'CTH',
            artifactId: 'ART-0123456789abcdef',
            format: 'md',
          ),
          throwsA(isA<LumenisCoreException>()),
        );
        expect(calls, isEmpty);
      }
    },
  );

  test('saved domain exports share all format and purpose validation', () async {
    const formats = {
      'md': 'text/markdown',
      'txt': 'text/plain',
      'docx':
          'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'pdf': 'application/pdf',
      'xlsx':
          'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'pptx':
          'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    };
    for (final entry in formats.entries) {
      calls.clear();
      responseMediaType = entry.value;
      responseBytes = [1, 2, 3];
      final file = await client.exportSourceBriefSavedWork(
        domainId: 'CTH',
        artifactId: 'ART-0123456789abcdef',
        format: entry.key,
        purpose: 'audit_snapshot',
      );
      expect(file.bytes, [1, 2, 3]);
      expect(file.mediaType, entry.value);
      expect(file.filename, 'ART-0123456789abcdef.${entry.key}');
      expect(calls.single['query'], {
        'format': entry.key,
        'purpose': 'audit_snapshot',
      });
      expect(calls.single['mode'], 'GLOBAL_ALL');
      expect(calls.single['domain'], 'CTH');
      expect(calls.single['subject'], isNull);
      expect(calls.single['workspace'], isNull);
    }
    calls.clear();
    await expectLater(
      client.exportSourceBriefSavedWork(
        domainId: 'CTH',
        artifactId: '../private',
        format: 'md',
      ),
      throwsFormatException,
    );
    await expectLater(
      client.exportSourceBriefSavedWork(
        domainId: 'CTH',
        artifactId: 'ART-0123456789abcdef',
        format: 'exe',
      ),
      throwsArgumentError,
    );
    await expectLater(
      client.exportSourceBriefSavedWork(
        domainId: 'CTH',
        artifactId: 'ART-0123456789abcdef',
        format: 'md',
        purpose: 'publish',
      ),
      throwsArgumentError,
    );
    expect(calls, isEmpty);
  });

  test(
    'saved domain export rejects denial wrong MIME and empty bytes',
    () async {
      responseStatus = 403;
      response = {'ok': false, 'code': 'WORK_PERMISSION_DENIED'};
      await expectLater(
        client.exportSourceBriefSavedWork(
          domainId: 'BMP',
          artifactId: 'ART-0123456789abcdef',
          format: 'docx',
        ),
        throwsA(
          isA<LumenisCoreException>()
              .having((error) => error.statusCode, 'status', 403)
              .having(
                (error) => error.errorCode,
                'code',
                'WORK_PERMISSION_DENIED',
              ),
        ),
      );
      responseStatus = 200;
      responseBytes = [1, 2, 3];
      responseMediaType = 'text/html';
      await expectLater(
        client.exportSourceBriefSavedWork(
          domainId: 'CTH',
          artifactId: 'ART-0123456789abcdef',
          format: 'pdf',
        ),
        throwsFormatException,
      );
      responseBytes = [];
      responseMediaType = 'application/pdf';
      await expectLater(
        client.exportSourceBriefSavedWork(
          domainId: 'CTH',
          artifactId: 'ART-0123456789abcdef',
          format: 'pdf',
        ),
        throwsFormatException,
      );
    },
  );
}
