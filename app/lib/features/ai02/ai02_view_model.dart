import 'package:flutter/foundation.dart';

import '../../core/transport/lumenis_http_transport.dart';
import 'ai02_repository.dart';
import 'ai02_snapshot.dart';

enum Ai02LoadPhase { loading, ready, failed }

enum Ai02FailureKind { authentication, permissionDenied, offline, server }

class Ai02ViewModel extends ChangeNotifier {
  Ai02ViewModel({required this._repository});

  final Ai02Repository _repository;
  Ai02LoadPhase _phase = Ai02LoadPhase.loading;
  Ai02FailureKind? _failureKind;
  Ai02Snapshot? _snapshot;
  String _draft = '';
  bool _disposed = false;
  int _refreshGeneration = 0;

  Ai02LoadPhase get phase => _phase;
  Ai02FailureKind? get failureKind => _failureKind;
  Ai02Snapshot? get snapshot => _snapshot;
  String get draft => _draft;
  bool get canStart =>
      _snapshot?.isBound == true && _snapshot!.executionProof.ready;

  Future<void> refresh() async {
    if (_disposed) return;
    final generation = ++_refreshGeneration;
    _phase = Ai02LoadPhase.loading;
    _failureKind = null;
    notifyListeners();

    if (_disposed || generation != _refreshGeneration) return;

    try {
      final snapshot = await _repository.load();
      if (_disposed || generation != _refreshGeneration) return;
      _snapshot = snapshot;
      _phase = Ai02LoadPhase.ready;
    } catch (error) {
      if (_disposed || generation != _refreshGeneration) return;
      _snapshot = null;
      _failureKind = _classifyFailure(error);
      _phase = Ai02LoadPhase.failed;
    }

    if (_disposed || generation != _refreshGeneration) return;
    notifyListeners();
  }

  void updateDraft(String value) {
    if (_disposed || value == _draft) return;
    _draft = value;
    notifyListeners();
  }

  @override
  void dispose() {
    _disposed = true;
    _refreshGeneration++;
    super.dispose();
  }

  String get blockedReason {
    final snapshot = _snapshot;
    if (snapshot == null || !snapshot.isBound) {
      return '任务编排服务尚未绑定，当前只显示已确认的阶段。';
    }
    final proof = snapshot.executionProof;
    if (!proof.actorBound) {
      return '服务器尚未确认当前操作身份。';
    }
    if (!proof.exactScope) {
      return '服务器尚未返回精确的全局或主体查看范围。';
    }
    if (!proof.readAllowed || !proof.executeAllowed) {
      return '当前查看或执行权限尚未由服务器确认。';
    }
    if (!proof.evidenceRefsPresent ||
        !proof.evidenceLineageVerified ||
        !proof.evidenceIntegrityVerified) {
      return '任务依据的来源链尚未完成核验。';
    }
    return '服务器尚未返回真实可调用的受控任务入口。';
  }

  static Ai02FailureKind _classifyFailure(Object error) {
    final message = error.toString().toLowerCase();
    if (message.contains('http 401') || message.contains('auth_required')) {
      return Ai02FailureKind.authentication;
    }
    if (message.contains('http 403') || message.contains('permission')) {
      return Ai02FailureKind.permissionDenied;
    }
    if (isLumenisConnectionError(error) ||
        message.contains('core unavailable') ||
        message.contains('timed out')) {
      return Ai02FailureKind.offline;
    }
    return Ai02FailureKind.server;
  }
}
