import 'package:flutter/foundation.dart';

import '../../../core/transport/lumenis_http_transport.dart';
import 'acc03_repository.dart';
import 'acc03_snapshot.dart';

enum Acc03LoadPhase { loading, ready, failed }

enum Acc03FailureKind { authentication, permissionDenied, offline, server }

class Acc03ViewModel extends ChangeNotifier {
  Acc03ViewModel({required this._repository});

  final Acc03Repository _repository;
  Acc03LoadPhase _phase = Acc03LoadPhase.loading;
  Acc03FailureKind? _failureKind;
  Acc03Snapshot? _snapshot;
  bool _disposed = false;
  int _refreshGeneration = 0;

  Acc03LoadPhase get phase => _phase;
  Acc03FailureKind? get failureKind => _failureKind;
  Acc03Snapshot? get snapshot => _snapshot;

  Future<void> refresh() async {
    if (_disposed) return;
    final generation = ++_refreshGeneration;
    _phase = Acc03LoadPhase.loading;
    _failureKind = null;
    notifyListeners();
    if (_disposed || generation != _refreshGeneration) return;

    try {
      final snapshot = await _repository.load();
      if (_disposed || generation != _refreshGeneration) return;
      _snapshot = snapshot;
      _phase = Acc03LoadPhase.ready;
    } catch (error) {
      if (_disposed || generation != _refreshGeneration) return;
      _snapshot = null;
      _failureKind = _classifyFailure(error);
      _phase = Acc03LoadPhase.failed;
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

  static Acc03FailureKind _classifyFailure(Object error) {
    final message = error.toString().toLowerCase();
    if (message.contains('http 401') || message.contains('auth_required')) {
      return Acc03FailureKind.authentication;
    }
    if (message.contains('http 403') || message.contains('permission')) {
      return Acc03FailureKind.permissionDenied;
    }
    if (isLumenisConnectionError(error) ||
        message.contains('core unavailable') ||
        message.contains('timed out')) {
      return Acc03FailureKind.offline;
    }
    return Acc03FailureKind.server;
  }
}
