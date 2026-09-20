import 'dart:io';

import 'package:flutter/foundation.dart';

import '../../../core/lumenis_core_client.dart';
import 'sys01_repository.dart';
import 'sys01_snapshot.dart';

enum Sys01LoadPhase { loading, ready, failed }

enum Sys01FailureKind { authentication, permissionDenied, offline, response }

class Sys01ViewModel extends ChangeNotifier {
  Sys01ViewModel({required Sys01Repository repository})
    : _repository = repository;

  final Sys01Repository _repository;
  Sys01LoadPhase _phase = Sys01LoadPhase.loading;
  Sys01FailureKind? _failureKind;
  Sys01Snapshot? _snapshot;
  bool _disposed = false;

  Sys01LoadPhase get phase => _phase;
  Sys01FailureKind? get failureKind => _failureKind;
  Sys01Snapshot? get snapshot => _snapshot;

  Future<void> refresh() async {
    _phase = Sys01LoadPhase.loading;
    _failureKind = null;
    _snapshot = null;
    _notifyIfAlive();

    try {
      _snapshot = await _repository.load();
      _phase = Sys01LoadPhase.ready;
    } catch (error) {
      _snapshot = null;
      _failureKind = _classifyFailure(error);
      _phase = Sys01LoadPhase.failed;
    }

    _notifyIfAlive();
  }

  @override
  void dispose() {
    _disposed = true;
    super.dispose();
  }

  void _notifyIfAlive() {
    if (!_disposed) notifyListeners();
  }

  static Sys01FailureKind _classifyFailure(Object error) {
    final message = error.toString().toLowerCase();
    if (message.contains('http 401')) {
      return Sys01FailureKind.authentication;
    }
    if (message.contains('http 403')) {
      return Sys01FailureKind.permissionDenied;
    }
    if (error is SocketException ||
        (error is LumenisCoreException &&
            (message.contains('core unavailable') ||
                message.contains('connection timed out')))) {
      return Sys01FailureKind.offline;
    }
    return Sys01FailureKind.response;
  }
}
