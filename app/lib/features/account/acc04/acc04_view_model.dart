import 'package:flutter/foundation.dart';

import '../../../core/transport/lumenis_http_transport.dart';
import 'acc04_repository.dart';
import 'acc04_snapshot.dart';

enum Acc04LoadPhase { loading, ready, failed }

enum Acc04FailureKind { authentication, permissionDenied, offline, server }

class Acc04ViewModel extends ChangeNotifier {
  Acc04ViewModel({required this._repository});

  final Acc04Repository _repository;
  Acc04LoadPhase _phase = Acc04LoadPhase.loading;
  Acc04FailureKind? _failureKind;
  Acc04Snapshot? _snapshot;
  bool _disposed = false;
  int _refreshGeneration = 0;

  Acc04LoadPhase get phase => _phase;
  Acc04FailureKind? get failureKind => _failureKind;
  Acc04Snapshot? get snapshot => _snapshot;

  Future<void> refresh() async {
    if (_disposed) return;
    final generation = ++_refreshGeneration;
    _phase = Acc04LoadPhase.loading;
    _failureKind = null;
    notifyListeners();
    if (_disposed || generation != _refreshGeneration) return;

    try {
      final snapshot = await _repository.load();
      if (_disposed || generation != _refreshGeneration) return;
      _snapshot = snapshot;
      _phase = Acc04LoadPhase.ready;
    } catch (error) {
      if (_disposed || generation != _refreshGeneration) return;
      _snapshot = null;
      _failureKind = _classifyFailure(error);
      _phase = Acc04LoadPhase.failed;
    }

    if (_disposed || generation != _refreshGeneration) return;
    notifyListeners();
  }

  @override
  void dispose() {
    _disposed = true;
    _refreshGeneration++;
    super.dispose();
  }

  static Acc04FailureKind _classifyFailure(Object error) {
    final message = error.toString().toLowerCase();
    if (message.contains('http 401') || message.contains('auth_required')) {
      return Acc04FailureKind.authentication;
    }
    if (message.contains('http 403') || message.contains('permission')) {
      return Acc04FailureKind.permissionDenied;
    }
    if (isLumenisConnectionError(error) ||
        message.contains('core unavailable') ||
        message.contains('timed out')) {
      return Acc04FailureKind.offline;
    }
    return Acc04FailureKind.server;
  }
}
