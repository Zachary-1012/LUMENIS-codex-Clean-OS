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

  setUp(() async {
    server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    client = LumenisCoreClient(baseUrl: 'http://127.0.0.1:${server.port}');
    calls = [];
    responseStatus = 200;
    response = {'ok': true};
    server.listen((request) async {
      final bytes = await request.fold<List<int>>(
        [],
        (all, chunk) => all..addAll(chunk),
      );
      final body = bytes.isEmpty ? null : jsonDecode(utf8.decode(bytes));
      calls.add({
        'path': request.uri.path,
        'method': request.method,
        'type': request.headers.contentType?.mimeType,
        'domain': request.headers.value('X-Domain-Id'),
        'product': request.headers.value('X-Product-Id'),
        'mode': request.headers.value('X-Lumenis-Context-Mode'),
        'subject': request.headers.value('X-Subject-ID'),
        'authorization': request.headers.value('Authorization'),
        'body': body,
      });
      request.response.statusCode = responseStatus;
      request.response.headers.contentType = ContentType.json;
      request.response.write(jsonEncode(response));
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
      response = {'ok': true, 'task': {'state': 'pending'}};
      await client.startSourceBriefTask(domainId: 'BMP');
      expect(calls.single['body'], {'limit': 30});
      expect(calls.single['domain'], 'BMP');
      expect(calls.single['product'], 'ZBMP');
    },
  );

  test(
    'task read, resume, and job readback use distinct existing routes',
    () async {
      const taskId = 'rbrief_01234567-89ab-cdef-0123-456789abcdef';
      const jobId = 'brief-0123456789abcdef0123456789abcdef';

      response = {
        'ok': true,
        'task': {
          'task_id': taskId,
          'state': 'interrupted',
          'can_resume': true,
        },
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
        'result': {'job_id': jobId, 'artifact_outcome': {'state': 'ready'}},
        'publish_status': 'not_performed',
      };
      final job = await client.sourceBriefJob(
        domainId: 'CTH',
        jobId: jobId,
      );
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
    expect(
      calls.single['path'],
      '/api/experience/reports/source-brief/start',
    );
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
}
