import 'package:flutter/foundation.dart';

import 'bmp01_repository.dart';
import 'bmp01_snapshot.dart';

enum Bmp01LoadPhase { loading, ready, failed }

enum Bmp01FailureKind { authentication, permissionDenied, offline, server }

class Bmp01ViewModel extends ChangeNotifier {
  Bmp01ViewModel({required Bmp01Repository repository})
    : _repository = repository;

  final Bmp01Repository _repository;

  Bmp01LoadPhase _phase = Bmp01LoadPhase.loading;
  Bmp01FailureKind? _failureKind;
  Bmp01Snapshot? _snapshot;

  Bmp01LoadPhase get phase => _phase;
  Bmp01FailureKind? get failureKind => _failureKind;
  Bmp01Snapshot? get snapshot => _snapshot;

  Future<void> refresh() async {
    _phase = Bmp01LoadPhase.loading;
    _failureKind = null;
    notifyListeners();

    try {
      _snapshot = await _repository.load();
      _phase = Bmp01LoadPhase.ready;
    } catch (error) {
      _snapshot = null;
      _failureKind = _classify(error);
      _phase = Bmp01LoadPhase.failed;
    }

    notifyListeners();
  }

  static Bmp01FailureKind _classify(Object error) {
    final message = error.toString().toLowerCase();
    if (message.contains('http 401') || message.contains('auth_required')) {
      return Bmp01FailureKind.authentication;
    }
    if (message.contains('http 403')) {
      return Bmp01FailureKind.permissionDenied;
    }
    if (message.contains('core unavailable') ||
        message.contains('connection timed out')) {
      return Bmp01FailureKind.offline;
    }
    return Bmp01FailureKind.server;
  }
}
