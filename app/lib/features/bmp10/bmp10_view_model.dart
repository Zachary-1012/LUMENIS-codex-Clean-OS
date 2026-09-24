import 'package:flutter/foundation.dart';

import 'bmp10_repository.dart';
import 'bmp10_snapshot.dart';

enum Bmp10LoadPhase { loading, ready, failed }

enum Bmp10FailureKind { authentication, permissionDenied, offline, server }

enum Bmp10ActionState { idle, blocked, staged }

class Bmp10ViewModel extends ChangeNotifier {
  Bmp10ViewModel({required this._repository});

  final Bmp10Repository _repository;
  Bmp10LoadPhase _phase = Bmp10LoadPhase.loading;
  Bmp10FailureKind? _failureKind;
  Bmp10Snapshot? _snapshot;
  Bmp10ActionState _actionState = Bmp10ActionState.idle;
  String? _actionId;

  Bmp10LoadPhase get phase => _phase;
  Bmp10FailureKind? get failureKind => _failureKind;
  Bmp10Snapshot? get snapshot => _snapshot;
  Bmp10ActionState get actionState => _actionState;
  String? get actionId => _actionId;

  Future<void> refresh() async {
    _phase = Bmp10LoadPhase.loading;
    _failureKind = null;
    _snapshot = null;
    _actionState = Bmp10ActionState.idle;
    _actionId = null;
    notifyListeners();
    try {
      _snapshot = await _repository.load();
      _phase = Bmp10LoadPhase.ready;
    } catch (error) {
      _failureKind = _classify(error);
      _phase = Bmp10LoadPhase.failed;
    }
    notifyListeners();
  }

  void stageAction(String actionId, String permission) {
    _actionId = actionId;
    final snapshot = _snapshot;
    _actionState = snapshot != null && snapshot.canStage(permission)
        ? Bmp10ActionState.staged
        : Bmp10ActionState.blocked;
    notifyListeners();
  }

  static Bmp10FailureKind _classify(Object error) {
    final message = error.toString().toLowerCase();
    if (message.contains('http 401') || message.contains('auth_required')) {
      return Bmp10FailureKind.authentication;
    }
    if (message.contains('http 403')) return Bmp10FailureKind.permissionDenied;
    if (message.contains('core unavailable') ||
        message.contains('connection timed out')) {
      return Bmp10FailureKind.offline;
    }
    return Bmp10FailureKind.server;
  }
}
