import 'package:flutter/foundation.dart';

import '../../core/transport/lumenis_http_transport.dart';
import 'ai01_repository.dart';
import 'ai01_snapshot.dart';

enum Ai01LoadPhase { loading, ready, failed }

enum Ai01FailureKind { authentication, permissionDenied, offline, server }

class Ai01ViewModel extends ChangeNotifier {
  Ai01ViewModel({required this._repository});

  final Ai01Repository _repository;

  Ai01LoadPhase _phase = Ai01LoadPhase.loading;
  Ai01FailureKind? _failureKind;
  Ai01Snapshot? _snapshot;
  String? _failureMessage;
  String _draft = '';
  int _requestGeneration = 0;
  bool _disposed = false;

  Ai01LoadPhase get phase => _phase;
  Ai01FailureKind? get failureKind => _failureKind;
  Ai01Snapshot? get snapshot => _snapshot;
  String? get failureMessage => _failureMessage;
  String get draft => _draft;

  String get submitBlockedReason => 'AI 任务提交能力尚未接入；当前草稿可以编辑，但不会发送。';

  Future<void> refresh() async {
    if (_disposed) return;

    final requestGeneration = ++_requestGeneration;
    _phase = Ai01LoadPhase.loading;
    _failureKind = null;
    _failureMessage = null;
    _snapshot = null;
    _notifyIfAlive();

    try {
      final snapshot = await _repository.load();
      if (_isStale(requestGeneration)) return;

      _snapshot = snapshot;
      _phase = Ai01LoadPhase.ready;
    } catch (error) {
      if (_isStale(requestGeneration)) return;

      _snapshot = null;
      _failureKind = _classifyFailure(error);
      _failureMessage = _failureText(_failureKind!);
      _phase = Ai01LoadPhase.failed;
    }

    _notifyIfAlive();
  }

  void updateDraft(String value) {
    if (_disposed || value == _draft) return;
    _draft = value;
    _notifyIfAlive();
  }

  void useSuggestion(Ai01Suggestion suggestion) {
    final intent = suggestion.safeIntent;
    if (intent == null || intent.isEmpty) return;
    updateDraft(intent);
  }

  bool _isStale(int requestGeneration) =>
      _disposed || requestGeneration != _requestGeneration;

  void _notifyIfAlive() {
    if (!_disposed) notifyListeners();
  }

  @override
  void dispose() {
    _disposed = true;
    _requestGeneration++;
    super.dispose();
  }

  static Ai01FailureKind _classifyFailure(Object error) {
    final message = error.toString().toLowerCase();
    if (message.contains('http 401') || message.contains('auth_required')) {
      return Ai01FailureKind.authentication;
    }
    if (message.contains('http 403')) {
      return Ai01FailureKind.permissionDenied;
    }
    if (isLumenisConnectionError(error) ||
        message.contains('core unavailable') ||
        message.contains('connection timed out')) {
      return Ai01FailureKind.offline;
    }
    return Ai01FailureKind.server;
  }

  static String _failureText(Ai01FailureKind kind) => switch (kind) {
    Ai01FailureKind.authentication => '服务连接授权已失效，无法读取 AI-01 实时状态。',
    Ai01FailureKind.permissionDenied => '此操作不可访问 AI-01 实时状态。',
    Ai01FailureKind.offline => '暂时无法连接 AI 服务。',
    Ai01FailureKind.server => 'AI-01 实时数据读取失败。',
  };
}
