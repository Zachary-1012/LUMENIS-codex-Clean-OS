import 'package:flutter/foundation.dart';

import 'bmp08_repository.dart';
import 'bmp08_snapshot.dart';

enum Bmp08LoadPhase { loading, ready, failed }

enum Bmp08FailureKind { authentication, permissionDenied, offline, server }

enum Bmp08ActionState { idle, blocked, staged }

class Bmp08ViewModel extends ChangeNotifier {
  Bmp08ViewModel({required this._repository});

  final Bmp08Repository _repository;
  Bmp08LoadPhase _phase = Bmp08LoadPhase.loading;
  Bmp08FailureKind? _failureKind;
  Bmp08Snapshot? _snapshot;
  Bmp08ActionState _actionState = Bmp08ActionState.idle;
  String? _actionId;

  Bmp08LoadPhase get phase => _phase;
  Bmp08FailureKind? get failureKind => _failureKind;
  Bmp08Snapshot? get snapshot => _snapshot;
  Bmp08ActionState get actionState => _actionState;
  String? get actionId => _actionId;

  Future<void> refresh() async {
    _phase = Bmp08LoadPhase.loading;
    _failureKind = null;
    _snapshot = null;
    _actionState = Bmp08ActionState.idle;
    _actionId = null;
    notifyListeners();
    try {
      _snapshot = await _repository.load();
      _phase = Bmp08LoadPhase.ready;
    } catch (error) {
      _failureKind = _classify(error);
      _phase = Bmp08LoadPhase.failed;
    }
    notifyListeners();
  }

  void stageAction(String actionId, String permission) {
    _actionId = actionId;
    final snapshot = _snapshot;
    _actionState = snapshot != null && snapshot.canStage(permission)
        ? Bmp08ActionState.staged
        : Bmp08ActionState.blocked;
    notifyListeners();
  }

  static Bmp08FailureKind _classify(Object error) {
    final message = error.toString().toLowerCase();
    if (message.contains('http 401') || message.contains('auth_required')) {
      return Bmp08FailureKind.authentication;
    }
    if (message.contains('http 403')) return Bmp08FailureKind.permissionDenied;
    if (message.contains('core unavailable') ||
        message.contains('connection timed out')) {
      return Bmp08FailureKind.offline;
    }
    return Bmp08FailureKind.server;
  }
}
