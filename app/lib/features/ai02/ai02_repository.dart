import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../../core/lumenis_core_client.dart';
import 'ai02_snapshot.dart';

abstract interface class Ai02Repository {
  Future<Ai02Snapshot> load({int offset = 0});
  Future<Ai02Task> read(String taskId);
  Future<Ai02Task> start(String input, {required String requestId});
  Future<Ai02Task?> readRequest(String requestId);
  Future<String?> pendingRequest();
  Future<void> retainRequest(String requestId);
  Future<void> forgetRequest(String requestId);
  Future<Ai02Task> act(String taskId, String action);
}

class CoreAi02Repository implements Ai02Repository {
  CoreAi02Repository({required this.client}) {
    final raw = client.currentContextEnvelope?['context'];
    final context = raw is Map ? raw : const <String, dynamic>{};
    _pendingKey =
        'lumenis.ai02.pending-request.v1.${base64Url.encode(utf8.encode(jsonEncode([client.baseUrl, context['mode'] ?? 'GLOBAL_ALL', context['domain_id'], context['subject_id'], context['brand_focus_id']])))}';
  }
  final LumenisCoreClient client;
  final _storage = SharedPreferencesAsync();
  late final String _pendingKey;
  Ai02Task _task(Map<String, dynamic> response) {
    if (response['ok'] != true || response['task'] is! Map) {
      throw const FormatException('Task was not confirmed.');
    }
    return Ai02Task.fromJson(
      Map<String, dynamic>.from(response['task'] as Map),
    );
  }

  @override
  Future<Ai02Snapshot> load({int offset = 0}) async =>
      Ai02Snapshot.fromResponse(await client.agentTasks(offset: offset));
  @override
  Future<Ai02Task> read(String taskId) async =>
      _task(await client.agentTask(taskId));
  @override
  Future<Ai02Task> start(String input, {required String requestId}) async =>
      _requestTask(
        await client.startAgentTask(input, requestId: requestId),
        requestId,
      );

  Ai02Task _requestTask(Map<String, dynamic> response, String requestId) {
    final task = _task(response);
    if (response['request_id'] != requestId || task.requestId != requestId) {
      throw const FormatException('Task request identity changed.');
    }
    return task;
  }

  @override
  Future<Ai02Task?> readRequest(String requestId) async {
    final response = await client.agentTaskForRequest(requestId);
    if (response['ok'] != true ||
        response['request_id'] != requestId ||
        response['found'] is! bool) {
      throw const FormatException('Request lookup was not confirmed.');
    }
    return response['found'] == true ? _requestTask(response, requestId) : null;
  }

  @override
  Future<String?> pendingRequest() async {
    final legacy = await _storage.getString(_pendingKey);
    if (legacy != null) {
      await retainRequest(legacy);
      await _storage.remove(_pendingKey);
    }
    final keys = await _storage.getKeys();
    final pending =
        keys.where((key) => key.startsWith('$_pendingKey.')).toList()..sort();
    if (pending.isEmpty) return null;
    final id = pending.first.substring(_pendingKey.length + 1);
    _validateRequestId(id);
    return id;
  }

  @override
  Future<void> retainRequest(String requestId) async {
    _validateRequestId(requestId);
    await _storage.setBool('$_pendingKey.$requestId', true);
  }

  @override
  Future<void> forgetRequest(String requestId) async {
    _validateRequestId(requestId);
    await _storage.remove('$_pendingKey.$requestId');
  }

  void _validateRequestId(String requestId) {
    if (!RegExp(r'^[0-9a-f]{32}$').hasMatch(requestId)) {
      throw const FormatException('Invalid pending request identity.');
    }
  }

  @override
  Future<Ai02Task> act(String taskId, String action) async {
    return _task(await client.agentTaskAction(taskId, action));
  }
}
