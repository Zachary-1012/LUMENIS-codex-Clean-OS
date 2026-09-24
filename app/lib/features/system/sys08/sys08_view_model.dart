import 'package:flutter/foundation.dart';

import '../sys02/sys_system_foundation.dart';
import 'sys08_repository.dart';
import 'sys08_snapshot.dart';

class Sys08ViewModel extends ChangeNotifier {
  Sys08ViewModel({required this._repository});

  final Sys08Repository _repository;
  SysLoadPhase _phase = SysLoadPhase.loading;
  SysFailureKind? _failureKind;
  Sys08Snapshot? _snapshot;
  bool _disposed = false;

  SysLoadPhase get phase => _phase;
  SysFailureKind? get failureKind => _failureKind;
  Sys08Snapshot? get snapshot => _snapshot;

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
