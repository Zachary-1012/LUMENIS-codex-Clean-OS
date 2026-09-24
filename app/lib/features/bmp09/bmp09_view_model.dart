import 'package:flutter/foundation.dart';

import 'bmp09_repository.dart';
import 'bmp09_snapshot.dart';

enum Bmp09LoadPhase { loading, ready, failed }

enum Bmp09FailureKind { authentication, permissionDenied, offline, server }

enum Bmp09ActionState { idle, blocked, staged }

class Bmp09ViewModel extends ChangeNotifier {
  Bmp09ViewModel({required this._repository});

  final Bmp09Repository _repository;
  Bmp09LoadPhase _phase = Bmp09LoadPhase.loading;
  Bmp09FailureKind? _failureKind;
  Bmp09Snapshot? _snapshot;
  Bmp09ActionState _actionState = Bmp09ActionState.idle;

  Bmp09LoadPhase get phase => _phase;
  Bmp09FailureKind? get failureKind => _failureKind;
  Bmp09Snapshot? get snapshot => _snapshot;
  Bmp09ActionState get actionState => _actionState;

  Future<void> refresh() async {
    _phase = Bmp09LoadPhase.loading;
    _failureKind = null;
    _snapshot = null;
    _actionState = Bmp09ActionState.idle;
    notifyListeners();
    try {
      _snapshot = await _repository.load();
      _phase = Bmp09LoadPhase.ready;
    } catch (error) {
      _failureKind = _classify(error);
      _phase = Bmp09LoadPhase.failed;
    }
    notifyListeners();
  }

  void stageReportRequest() {
    final snapshot = _snapshot;
    _actionState = snapshot != null && snapshot.canStage('report:write')
        ? Bmp09ActionState.staged
        : Bmp09ActionState.blocked;
    notifyListeners();
  }

  static Bmp09FailureKind _classify(Object error) {
    final message = error.toString().toLowerCase();
    if (message.contains('http 401') || message.contains('auth_required')) {
      return Bmp09FailureKind.authentication;
    }
    if (message.contains('http 403')) return Bmp09FailureKind.permissionDenied;
    if (message.contains('core unavailable') ||
        message.contains('connection timed out')) {
      return Bmp09FailureKind.offline;
    }
    return Bmp09FailureKind.server;
  }
}
