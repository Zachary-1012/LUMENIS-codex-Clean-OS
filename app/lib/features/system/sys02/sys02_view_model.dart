import 'package:flutter/foundation.dart';
import '../../../core/lumenis_core_client.dart';

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
  bool _refreshing = false;

  SysLoadPhase get phase => _phase;
  SysFailureKind? get failureKind => _failureKind;
  Sys02Snapshot? get snapshot => _snapshot;
  bool get refreshing => _refreshing;

  Future<void> refresh() async {
    if (_refreshing || _disposed) return;
    _refreshing = true;
    if (_snapshot == null) _phase = SysLoadPhase.loading;
    _failureKind = null;
    _notifyIfAlive();
    try {
      _snapshot = await _repository.load();
      _phase = SysLoadPhase.ready;
    } catch (error) {
      _failureKind = classifySysFailure(error);
      if (error is LumenisCoreException &&
          const {401, 403, 404, 410}.contains(error.statusCode)) {
        _snapshot = null;
        _failureKind = error.statusCode == 401
            ? SysFailureKind.authentication
            : SysFailureKind.permissionDenied;
      }
      _phase = _snapshot == null ? SysLoadPhase.failed : SysLoadPhase.ready;
    }
    _refreshing = false;
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
