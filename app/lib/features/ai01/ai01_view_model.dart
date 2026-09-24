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

  Ai01LoadPhase get phase => _phase;
  Ai01FailureKind? get failureKind => _failureKind;
  Ai01Snapshot? get snapshot => _snapshot;
  String? get failureMessage => _failureMessage;
  String get draft => _draft;

  String get submitBlockedReason =>
      '当前没有服务端确认的 Subject 或 Brand Lens，暂不提交 AI 意图。';

  Future<void> refresh() async {
    _phase = Ai01LoadPhase.loading;
    _failureKind = null;
    _failureMessage = null;
    notifyListeners();

    try {
      _snapshot = await _repository.load();
      _phase = Ai01LoadPhase.ready;
    } catch (error) {
      _snapshot = null;
      _failureKind = _classifyFailure(error);
      _failureMessage = _failureText(_failureKind!);
      _phase = Ai01LoadPhase.failed;
    }

    notifyListeners();
  }

  void updateDraft(String value) {
    if (value == _draft) return;
    _draft = value;
    notifyListeners();
  }

  void useSuggestion(Ai01Suggestion suggestion) {
    final intent = suggestion.safeIntent;
    if (intent == null || intent.isEmpty) return;
    updateDraft(intent);
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
    Ai01FailureKind.authentication => '需要登录后才能读取 AI-01 实时状态。',
    Ai01FailureKind.permissionDenied => '当前账号无权读取 AI-01 实时状态。',
    Ai01FailureKind.offline => '暂时无法连接 Production Core。',
    Ai01FailureKind.server => 'AI-01 实时数据读取失败。',
  };
}
