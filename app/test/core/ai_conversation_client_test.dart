import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';

const _conversationId = 'conv_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa';
const _userTurnId = 'turn_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb';
const _responseTurnId = 'turn_cccccccccccccccccccccccccccccccc';

void main() {
  test(
    'AI conversation transport stays within the shared Core contract',
    () async {
      final server = await _AiConversationStub.start();
      addTearDown(server.close);
      final client = LumenisCoreClient(baseUrl: server.baseUrl);

      await client.listAiConversations(limit: 30, offset: 60);
      await client.createAiConversation();
      await client.readAiConversation(
        _conversationId,
        afterSequence: 30,
        limit: 30,
      );
      await client.appendAiConversationTurn(
        conversationId: _conversationId,
        text: '  keep exact user text  ',
        idempotencyKey: 'append-unique-key',
        expectedRevision: 1,
      );
      await client.attachAiConversationTask(
        conversationId: _conversationId,
        taskId: 'task-123',
        idempotencyKey: 'task-unique-key',
        expectedRevision: 2,
      );
      await client.respondToAiConversationTurn(
        conversationId: _conversationId,
        turnId: _userTurnId,
        idempotencyKey: 'reply-unique-key',
        expectedRevision: 3,
      );
      await client.interruptAiConversationResponse(
        conversationId: _conversationId,
        turnId: _responseTurnId,
        expectedRevision: 4,
      );

      expect(server.requests.map((request) => request.method), [
        'GET',
        'POST',
        'GET',
        'POST',
        'POST',
        'POST',
        'POST',
      ]);
      expect(server.requests.map((request) => request.path), [
        '/v4/ai/conversations',
        '/v4/ai/conversations',
        '/v4/ai/conversations/$_conversationId',
        '/v4/ai/conversations/$_conversationId/turns',
        '/v4/ai/conversations/$_conversationId/tasks',
        '/v4/ai/conversations/$_conversationId/turns/$_userTurnId/respond',
        '/v4/ai/conversations/$_conversationId/turns/$_responseTurnId/respond',
      ]);
      expect(server.requests[0].query, {'limit': '30', 'offset': '60'});
      expect(server.requests[2].query, {'after_sequence': '30', 'limit': '30'});
      expect(server.requests[3].body, {
        'text': '  keep exact user text  ',
        'idempotency_key': 'append-unique-key',
        'expected_revision': 1,
      });
      expect(server.requests[4].body, {
        'task_id': 'task-123',
        'idempotency_key': 'task-unique-key',
        'expected_revision': 2,
      });
      expect(server.requests[5].body, {
        'idempotency_key': 'reply-unique-key',
        'expected_revision': 3,
      });
      expect(server.requests[6].body, {
        'operation': 'interrupt',
        'expected_revision': 4,
        'confirmed': true,
      });
      for (final request in server.requests) {
        expect(
          request.headers['x-lumenis-workspace-scope'],
          '{"scope_kind":"shared_workspace","version":1}',
        );
        expect(request.headers['cache-control'], 'no-store');
        expect(request.headers['authorization'], isNull);
        expect(request.headers['cookie'], isNull);
        expect(request.headers['x-actor-id'], isNull);
        expect(request.headers['x-domain-id'], isNull);
        expect(request.headers['x-subject-id'], isNull);
        expect(request.headers['x-brand-focus-id'], isNull);
      }
    },
  );

  test(
    'conversation IDs and idempotency keys fail closed before transport',
    () async {
      final server = await _AiConversationStub.start();
      addTearDown(server.close);
      final client = LumenisCoreClient(baseUrl: server.baseUrl);

      expect(
        () => client.readAiConversation('../$_conversationId'),
        throwsFormatException,
      );
      expect(
        () => client.appendAiConversationTurn(
          conversationId: _conversationId,
          text: 'message',
          idempotencyKey: '../reuse',
          expectedRevision: 1,
        ),
        throwsFormatException,
      );
      expect(server.requests, isEmpty);
    },
  );
}

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

class _AiConversationStub {
  _AiConversationStub(this.server) {
    server.listen(_handle);
  }

  final HttpServer server;
  final requests = <_CapturedRequest>[];

  String get baseUrl => 'http://127.0.0.1:${server.port}';

  static Future<_AiConversationStub> start() async => _AiConversationStub(
    await HttpServer.bind(InternetAddress.loopbackIPv4, 0),
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

    final path = request.uri.path;
    final response = switch ((request.method, path)) {
      ('GET', '/v4/ai/conversations') => {
        'ok': true,
        'conversations': <Object?>[],
        'has_more': false,
        'next_offset': null,
      },
      ('POST', '/v4/ai/conversations') => {
        'ok': true,
        'conversation': _summary,
      },
      ('GET', '/v4/ai/conversations/$_conversationId') => {
        'ok': true,
        'conversation': {
          ..._summary,
          'turns': <Object?>[],
          'has_more': false,
          'next_sequence': null,
        },
      },
      ('POST', '/v4/ai/conversations/$_conversationId/turns') => {
        'ok': true,
        'turn': _turn(
          id: _userTurnId,
          role: 'user',
          origin: 'user_input',
          sequence: 1,
          content: const {'text': '  keep exact user text  '},
        ),
        'revision': 2,
        'idempotent_hit': false,
      },
      ('POST', '/v4/ai/conversations/$_conversationId/tasks') => {
        'ok': true,
        'turn': _turn(
          id: _responseTurnId,
          role: 'assistant',
          origin: 'task_projection',
          sequence: 2,
          content: const {'task_id': 'task-123'},
        ),
        'revision': 3,
        'idempotent_hit': false,
      },
      (
        'POST',
        '/v4/ai/conversations/$_conversationId/turns/$_userTurnId/respond',
      ) =>
        {
          'ok': true,
          'turn': _turn(
            id: _responseTurnId,
            role: 'assistant',
            origin: 'model_output',
            sequence: 2,
            state: 'reserved',
            content: const {'in_reply_to': _userTurnId},
          ),
          'revision': 4,
          'idempotent_hit': false,
        },
      (
        'POST',
        '/v4/ai/conversations/$_conversationId/turns/$_responseTurnId/respond',
      ) =>
        {
          'ok': true,
          'turn': _turn(
            id: _responseTurnId,
            role: 'assistant',
            origin: 'model_output',
            sequence: 2,
            state: 'interrupted',
            content: const {'in_reply_to': _userTurnId},
          ),
          'revision': 5,
          'idempotent_hit': false,
          'external_call_stopped': false,
          'prior_result_unknown': true,
        },
      _ => {'ok': false, 'code': 'UNEXPECTED_REQUEST'},
    };
    request.response
      ..statusCode = HttpStatus.ok
      ..headers.contentType = ContentType.json
      ..write(jsonEncode(response));
    await request.response.close();
  }
}

Map<String, Object?> get _summary => {
  'conversation_id': _conversationId,
  'title': '',
  'revision': 1,
  'state': 'active',
  'created_at': '2026-10-22T00:00:00Z',
  'updated_at': '2026-10-22T00:00:00Z',
};

Map<String, Object?> _turn({
  required String id,
  required String role,
  required String origin,
  required int sequence,
  required Map<String, Object?> content,
  String state = 'recorded',
}) => {
  'turn_id': id,
  'conversation_id': _conversationId,
  'sequence': sequence,
  'role': role,
  'origin_kind': origin,
  'state': state,
  'revision': 1,
  'content': content,
};
