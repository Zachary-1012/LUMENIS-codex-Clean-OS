import 'package:flutter/foundation.dart';

import 'bmp06_repository.dart';
import 'bmp06_snapshot.dart';

enum Bmp06LoadPhase { loading, ready, failed }

enum Bmp06FailureKind { authentication, permissionDenied, offline, server }

enum Bmp06ActionState { idle, blocked, staged }

class Bmp06ViewModel extends ChangeNotifier {
  Bmp06ViewModel({required this._repository});

  final Bmp06Repository _repository;

  Bmp06LoadPhase _phase = Bmp06LoadPhase.loading;
  Bmp06FailureKind? _failureKind;
  Bmp06Snapshot? _snapshot;
  Bmp06ActionState _actionState = Bmp06ActionState.idle;
  String? _actionId;

  Bmp06LoadPhase get phase => _phase;
  Bmp06FailureKind? get failureKind => _failureKind;
  Bmp06Snapshot? get snapshot => _snapshot;
  Bmp06ActionState get actionState => _actionState;
  String? get actionId => _actionId;

  Future<void> refresh() async {
    _phase = Bmp06LoadPhase.loading;
    _failureKind = null;
    _snapshot = null;
    _actionState = Bmp06ActionState.idle;
    _actionId = null;
    notifyListeners();
    try {
      _snapshot = await _repository.load();
      _phase = Bmp06LoadPhase.ready;
    } catch (error) {
      _failureKind = _classify(error);
      _phase = Bmp06LoadPhase.failed;
    }
    notifyListeners();
  }

  void stageAction(String actionId, String permission) {
    _actionId = actionId;
    final snapshot = _snapshot;
    _actionState = snapshot != null && snapshot.canStage(permission)
        ? Bmp06ActionState.staged
        : Bmp06ActionState.blocked;
    notifyListeners();
  }

  static Bmp06FailureKind _classify(Object error) {
    final message = error.toString().toLowerCase();
    if (message.contains('http 401') || message.contains('auth_required')) {
      return Bmp06FailureKind.authentication;
    }
    if (message.contains('http 403')) return Bmp06FailureKind.permissionDenied;
    if (message.contains('core unavailable') ||
        message.contains('connection timed out')) {
      return Bmp06FailureKind.offline;
    }
    return Bmp06FailureKind.server;
  }
}
