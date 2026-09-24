import 'package:flutter/foundation.dart';

import '../sys02/sys_system_foundation.dart';
import 'sys05_repository.dart';
import 'sys05_snapshot.dart';

class Sys05ViewModel extends ChangeNotifier {
  Sys05ViewModel({required this._repository});

  final Sys05Repository _repository;
  SysLoadPhase _phase = SysLoadPhase.loading;
  SysFailureKind? _failureKind;
  Sys05Snapshot? _snapshot;
  Sys05Preferences _preferences = const Sys05Preferences();
  Sys05Preferences _savedPreferences = const Sys05Preferences();
  bool _savedInSession = false;
  bool _disposed = false;

  SysLoadPhase get phase => _phase;
  SysFailureKind? get failureKind => _failureKind;
  Sys05Snapshot? get snapshot => _snapshot;
  Sys05Preferences get preferences => _preferences;
  bool get hasUnsavedChanges => _preferences != _savedPreferences;
  bool get savedInSession => _savedInSession;

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

  void update({
    String? theme,
    String? optical,
    String? density,
    String? reducedMotion,
    String? locale,
  }) {
    _preferences = _preferences.copyWith(
      theme: theme,
      optical: optical,
      density: density,
      reducedMotion: reducedMotion,
      locale: locale,
    );
    _savedInSession = false;
    _notifyIfAlive();
  }

  void saveLocal() {
    _savedPreferences = _preferences;
    _savedInSession = true;
    _notifyIfAlive();
  }

  void restoreDefaults() {
    _preferences = const Sys05Preferences();
    _savedPreferences = const Sys05Preferences();
    _savedInSession = false;
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
