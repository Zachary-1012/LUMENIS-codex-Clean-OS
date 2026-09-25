import 'package:flutter/foundation.dart';

import '../../../core/transport/lumenis_http_transport.dart';
import 'acc02_repository.dart';
import 'acc02_snapshot.dart';

enum Acc02LoadPhase { loading, ready, failed }

enum Acc02FailureKind { authentication, permissionDenied, offline, server }

class Acc02ViewModel extends ChangeNotifier {
  Acc02ViewModel({required this._repository});

  final Acc02Repository _repository;

  Acc02LoadPhase _phase = Acc02LoadPhase.loading;
  Acc02FailureKind? _failureKind;
  Acc02Snapshot? _snapshot;
  String? _selectingId;
  String? _actionError;
  bool _disposed = false;

  Acc02LoadPhase get phase => _phase;
  Acc02FailureKind? get failureKind => _failureKind;
  Acc02Snapshot? get snapshot => _snapshot;
  String? get selectingId => _selectingId;
  String? get actionError => _actionError;

  bool get canSelect =>
      !_disposed &&
      _selectingId == null &&
      _phase == Acc02LoadPhase.ready &&
      _snapshot?.subjectState == Acc02SubjectState.ready;

  Future<void> refresh() async {
    if (_disposed) return;
    _phase = Acc02LoadPhase.loading;
    _failureKind = null;
    _actionError = null;
    notifyListeners();
    try {
      final snapshot = await _repository.load();
      if (_disposed) return;
      _snapshot = snapshot;
      _phase = Acc02LoadPhase.ready;
    } catch (error) {
      if (_disposed) return;
      _snapshot = null;
      _failureKind = _classifyFailure(error);
      _phase = Acc02LoadPhase.failed;
    }
    if (!_disposed) notifyListeners();
  }

  Future<void> selectSubject(Acc02Subject subject) async {
    if (_disposed || _selectingId != null || !canSelect) return;
    _selectingId = subject.id;
    _actionError = null;
    notifyListeners();
    try {
      await _repository.selectSubject(subject);
      if (_disposed) return;
      final snapshot = await _repository.load();
      if (_disposed) return;
      _snapshot = snapshot;
    } catch (error) {
      if (_disposed) return;
      _actionError = _actionMessage(_classifyFailure(error));
    } finally {
      _selectingId = null;
      if (!_disposed) notifyListeners();
    }
  }

  @override
  void dispose() {
    _disposed = true;
    super.dispose();
  }

  static Acc02FailureKind _classifyFailure(Object error) {
    final message = error.toString().toLowerCase();
    if (message.contains('http 401') || message.contains('auth_required')) {
      return Acc02FailureKind.authentication;
    }
    if (message.contains('http 403') || message.contains('permission')) {
      return Acc02FailureKind.permissionDenied;
    }
    if (isLumenisConnectionError(error) ||
        message.contains('core unavailable') ||
        message.contains('timed out')) {
      return Acc02FailureKind.offline;
    }
    return Acc02FailureKind.server;
  }

  static String _actionMessage(Acc02FailureKind kind) => switch (kind) {
    Acc02FailureKind.authentication => '当前访问身份尚未确认。',
    Acc02FailureKind.permissionDenied => '当前范围未获服务器确认，主体没有被切换。',
    Acc02FailureKind.offline => '暂时无法保存当前查看范围。',
    Acc02FailureKind.server => '当前查看范围未能保存，请稍后重试。',
  };
}
