import 'package:flutter/foundation.dart';

import 'bmp11_repository.dart';
import 'bmp11_snapshot.dart';

enum Bmp11LoadPhase { loading, ready, failed }

enum Bmp11FailureKind { authentication, permissionDenied, offline, server }

class Bmp11ViewModel extends ChangeNotifier {
  Bmp11ViewModel({required this._repository});

  final Bmp11Repository _repository;
  bool _disposed = false;
  Bmp11LoadPhase _phase = Bmp11LoadPhase.loading;
  Bmp11FailureKind? _failureKind;
  Bmp11Snapshot? _snapshot;

  Bmp11LoadPhase get phase => _phase;
  Bmp11FailureKind? get failureKind => _failureKind;
  Bmp11Snapshot? get snapshot => _snapshot;

  Future<void> refresh() async {
    if (_disposed) return;
    _phase = Bmp11LoadPhase.loading;
    _failureKind = null;
    _snapshot = null;
    notifyListeners();
    if (_disposed) return;
    try {
      final snapshot = await _repository.load();
      if (_disposed) return;
      _snapshot = snapshot;
      _phase = Bmp11LoadPhase.ready;
    } catch (error) {
      if (_disposed) return;
      _failureKind = _classify(error);
      _phase = Bmp11LoadPhase.failed;
    }
    if (_disposed) return;
    notifyListeners();
  }

  static Bmp11FailureKind _classify(Object error) {
    final message = error.toString().toLowerCase();
    if (message.contains('http 401') || message.contains('auth_required')) {
      return Bmp11FailureKind.authentication;
    }
    if (message.contains('http 403')) return Bmp11FailureKind.permissionDenied;
    if (message.contains('core unavailable') ||
        message.contains('connection timed out')) {
      return Bmp11FailureKind.offline;
    }
    return Bmp11FailureKind.server;
  }

  @override
  void dispose() {
    _disposed = true;
    super.dispose();
  }
}
