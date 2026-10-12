import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/features/ai01/ai01_repository.dart';

void main() {
  test('submits only task and ANALYZE to the verified intent route', () async {
    final server = await _IntentStub.start(
      status: HttpStatus.ok,
      body: const {
        'ok': true,
        'permission_status': 'granted',
        'status': 'failed',
        'execution_id': 'exec-9',
        'evidence_recorded': false,
        'ai_is_derivative': true,
        'note': '执行链已登记，但当前结果未完成。',
      },
    );
    addTearDown(server.close);
    final repository = CoreAi01Repository(
      client: LumenisCoreClient(baseUrl: server.baseUrl),
    );

    final result = await repository.submitIntent('检查本周风险变化');

    expect(result.status, 'failed');
    expect(result.permissionStatus, 'granted');
    expect(result.executionId, 'exec-9');
    expect(result.evidenceRecorded, isFalse);
    expect(result.aiIsDerivative, isTrue);
    expect(result.note, '执行链已登记，但当前结果未完成。');
    expect(server.requests, hasLength(1));
    final request = server.requests.single;
    expect(request.method, 'POST');
    expect(request.path, '/api/experience/ai/intent');
    expect(request.json, {'task': '检查本周风险变化', 'action_type': 'ANALYZE'});
    expect(request.json.containsKey('user_id'), isFalse);
    expect(request.json.containsKey('domain'), isFalse);
    expect(request.json.containsKey('product'), isFalse);
    expect(request.json.containsKey('skill_id'), isFalse);
  });

  for (final status in [400, 401, 403, 500]) {
    test('HTTP $status surfaces as a classified exception', () async {
      final server = await _IntentStub.start(
        status: status,
        body: const {'ok': false, 'status': 'denied'},
      );
      addTearDown(server.close);
      final repository = CoreAi01Repository(
        client: LumenisCoreClient(baseUrl: server.baseUrl),
      );

      await expectLater(
        repository.submitIntent('task'),
        throwsA(
          isA<LumenisCoreException>().having(
            (error) => error.toString().toLowerCase(),
            'message',
            contains('http $status'),
          ),
        ),
      );
    });
  }
}

class _Recorded {
  const _Recorded(this.method, this.path, this.json);
  final String method;
  final String path;
  final Map<String, dynamic> json;
}

class _IntentStub {
  _IntentStub._(this.server, this.status, this.body) {
    server.listen(_handle);
  }

  final HttpServer server;
  final int status;
  final Map<String, dynamic> body;
  final requests = <_Recorded>[];

  String get baseUrl => 'http://127.0.0.1:${server.port}';

  static Future<_IntentStub> start({
    required int status,
    required Map<String, dynamic> body,
  }) async => _IntentStub._(
    await HttpServer.bind(InternetAddress.loopbackIPv4, 0),
    status,
    body,
  );

  Future<void> close() => server.close(force: true);

  Future<void> _handle(HttpRequest request) async {
    final raw = await utf8.decoder.bind(request).join();
    if (request.uri.path == '/api/auth/config') {
      request.response
        ..statusCode = HttpStatus.ok
        ..headers.contentType = ContentType.json
        ..write(jsonEncode({'ok': true, 'auth_enabled': false}));
      await request.response.close();
      return;
    }
    requests.add(
      _Recorded(
        request.method,
        request.uri.path,
        raw.isEmpty ? const {} : jsonDecode(raw) as Map<String, dynamic>,
      ),
    );
    request.response
      ..statusCode = status
      ..headers.contentType = ContentType.json
      ..write(jsonEncode(body));
    await request.response.close();
  }
}
