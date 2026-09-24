import 'package:flutter/foundation.dart';

import '../../core/transport/lumenis_http_transport.dart';
import 'ai05_repository.dart';
import 'ai05_snapshot.dart';

enum Ai05LoadPhase { loading, ready, failed }

enum Ai05FailureKind { authentication, permissionDenied, offline, server }

class Ai05ViewModel extends ChangeNotifier {
  Ai05ViewModel({required this._repository});

  final Ai05Repository _repository;
  Ai05LoadPhase _phase = Ai05LoadPhase.loading;
  Ai05FailureKind? _failureKind;
  Ai05Snapshot? _snapshot;

  Ai05LoadPhase get phase => _phase;
  Ai05FailureKind? get failureKind => _failureKind;
  Ai05Snapshot? get snapshot => _snapshot;

  Future<void> refresh() async {
    _phase = Ai05LoadPhase.loading;
    _failureKind = null;
    notifyListeners();
    try {
      _snapshot = await _repository.load();
      _phase = Ai05LoadPhase.ready;
    } catch (error) {
      _snapshot = null;
      _failureKind = _classifyFailure(error);
      _phase = Ai05LoadPhase.failed;
    }
    notifyListeners();
  }

  static Ai05FailureKind _classifyFailure(Object error) {
    final message = error.toString().toLowerCase();
    if (message.contains('http 401') || message.contains('auth_required')) {
      return Ai05FailureKind.authentication;
    }
    if (message.contains('http 403') || message.contains('permission')) {
      return Ai05FailureKind.permissionDenied;
    }
    if (isLumenisConnectionError(error) ||
        message.contains('core unavailable') ||
        message.contains('timed out')) {
      return Ai05FailureKind.offline;
    }
    return Ai05FailureKind.server;
  }
}
