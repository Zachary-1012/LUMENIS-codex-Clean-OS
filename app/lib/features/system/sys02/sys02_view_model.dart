import 'package:flutter/foundation.dart';

import 'sys02_repository.dart';
import 'sys02_snapshot.dart';
import 'sys_system_foundation.dart';

class Sys02ViewModel extends ChangeNotifier {
  Sys02ViewModel({required this._repository});

  final Sys02Repository _repository;
  SysLoadPhase _phase = SysLoadPhase.loading;
  SysFailureKind? _failureKind;
  Sys02Snapshot? _snapshot;
  bool _disposed = false;

  SysLoadPhase get phase => _phase;
  SysFailureKind? get failureKind => _failureKind;
  Sys02Snapshot? get snapshot => _snapshot;

  Future<void> refresh() async {
    _phase = SysLoadPhase.loading;
    _failureKind = null;
    _snapshot = null;
    _notifyIfAlive();
    try {
      _snapshot = await _repository.load();
      _phase = SysLoadPhase.ready;
    } catch (error) {
      _snapshot = null;
      _failureKind = classifySysFailure(error);
      _phase = SysLoadPhase.failed;
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
}
