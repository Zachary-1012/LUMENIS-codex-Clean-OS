import 'package:flutter/foundation.dart';

import '../../../core/transport/lumenis_http_transport.dart';
import 'acc01_repository.dart';
import 'acc01_snapshot.dart';

enum Acc01LoadPhase { loading, ready, failed }

enum Acc01FailureKind { authentication, permissionDenied, offline, server }

class Acc01ViewModel extends ChangeNotifier {
  Acc01ViewModel({required this._repository});

  final Acc01Repository _repository;

  Acc01LoadPhase _phase = Acc01LoadPhase.loading;
  Acc01FailureKind? _failureKind;
  Acc01Snapshot? _snapshot;
  bool _disposed = false;
  int _refreshGeneration = 0;

  Acc01LoadPhase get phase => _phase;
  Acc01FailureKind? get failureKind => _failureKind;
  Acc01Snapshot? get snapshot => _snapshot;

  Future<void> refresh() async {
    if (_disposed) return;
    final generation = ++_refreshGeneration;
    _phase = Acc01LoadPhase.loading;
    _failureKind = null;
    notifyListeners();
    if (_disposed || generation != _refreshGeneration) return;

    try {
      final snapshot = await _repository.load();
      if (_disposed || generation != _refreshGeneration) return;
      _snapshot = snapshot;
      _phase = Acc01LoadPhase.ready;
    } catch (error) {
      if (_disposed || generation != _refreshGeneration) return;
      _snapshot = null;
      _failureKind = _classifyFailure(error);
      _phase = Acc01LoadPhase.failed;
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

  static Acc01FailureKind _classifyFailure(Object error) {
    final message = error.toString().toLowerCase();
    if (message.contains('http 401') || message.contains('auth_required')) {
      return Acc01FailureKind.authentication;
    }
    if (message.contains('http 403')) {
      return Acc01FailureKind.permissionDenied;
    }
    if (isLumenisConnectionError(error) ||
        message.contains('core unavailable') ||
        message.contains('connection timed out')) {
      return Acc01FailureKind.offline;
    }
    return Acc01FailureKind.server;
  }
}
