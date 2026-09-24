import 'package:flutter/foundation.dart';

import 'bmp07_repository.dart';
import 'bmp07_snapshot.dart';

enum Bmp07LoadPhase { loading, ready, failed }

enum Bmp07FailureKind { authentication, permissionDenied, offline, server }

enum Bmp07ActionState { idle, blocked, staged }

class Bmp07ViewModel extends ChangeNotifier {
  Bmp07ViewModel({required this._repository});

  final Bmp07Repository _repository;
  Bmp07LoadPhase _phase = Bmp07LoadPhase.loading;
  Bmp07FailureKind? _failureKind;
  Bmp07Snapshot? _snapshot;
  Bmp07ActionState _actionState = Bmp07ActionState.idle;
  String? _actionId;

  Bmp07LoadPhase get phase => _phase;
  Bmp07FailureKind? get failureKind => _failureKind;
  Bmp07Snapshot? get snapshot => _snapshot;
  Bmp07ActionState get actionState => _actionState;
  String? get actionId => _actionId;

  Future<void> refresh() async {
    _phase = Bmp07LoadPhase.loading;
    _failureKind = null;
    _snapshot = null;
    _actionState = Bmp07ActionState.idle;
    _actionId = null;
    notifyListeners();
    try {
      _snapshot = await _repository.load();
      _phase = Bmp07LoadPhase.ready;
    } catch (error) {
      _failureKind = _classify(error);
      _phase = Bmp07LoadPhase.failed;
    }
    notifyListeners();
  }

  void stageAction(String actionId, String permission) {
    _actionId = actionId;
    final snapshot = _snapshot;
    _actionState = snapshot != null && snapshot.canStage(permission)
        ? Bmp07ActionState.staged
        : Bmp07ActionState.blocked;
    notifyListeners();
  }

  static Bmp07FailureKind _classify(Object error) {
    final message = error.toString().toLowerCase();
    if (message.contains('http 401') || message.contains('auth_required')) {
      return Bmp07FailureKind.authentication;
    }
    if (message.contains('http 403')) return Bmp07FailureKind.permissionDenied;
    if (message.contains('core unavailable') ||
        message.contains('connection timed out')) {
      return Bmp07FailureKind.offline;
    }
    return Bmp07FailureKind.server;
  }
}
