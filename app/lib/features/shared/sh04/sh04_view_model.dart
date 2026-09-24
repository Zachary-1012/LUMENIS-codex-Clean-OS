import 'package:flutter/foundation.dart';

import '../../../core/lumenis_core_client.dart';
import 'sh04_repository.dart';
import 'sh04_snapshot.dart';

enum Sh04LoadPhase { loading, ready, blocked, failed }

enum Sh04FailureKind { authentication, permissionDenied, offline, response }

class Sh04ViewModel extends ChangeNotifier {
  Sh04ViewModel({required this._repository});

  final Sh04Repository _repository;
  Sh04LoadPhase _phase = Sh04LoadPhase.loading;
  Sh04FailureKind? _failureKind;
  Sh04ScopeErrorKind? _scopeError;
  Sh04Snapshot? _snapshot;
  int? _selectedIndex;
  bool _disposed = false;

  Sh04LoadPhase get phase => _phase;
  Sh04FailureKind? get failureKind => _failureKind;
  Sh04ScopeErrorKind? get scopeError => _scopeError;
  Sh04Snapshot? get snapshot => _snapshot;
  List<Sh04Export> get exports => _snapshot?.exports ?? const <Sh04Export>[];
  Sh04Export? get selected => exports.isEmpty
      ? null
      : exports[(_selectedIndex ?? 0).clamp(0, exports.length - 1).toInt()];

  Future<void> refresh() async {
    _phase = Sh04LoadPhase.loading;
    _failureKind = null;
    _scopeError = null;
    _snapshot = null;
    _selectedIndex = null;
    _notifyIfAlive();
    try {
      _snapshot = await _repository.loadExports();
      _phase = Sh04LoadPhase.ready;
    } on Sh04ScopeError catch (error) {
      _scopeError = error.kind;
      _phase = Sh04LoadPhase.blocked;
    } catch (error) {
      _failureKind = _classifyFailure(error);
      _phase = Sh04LoadPhase.failed;
    }
    _notifyIfAlive();
  }

  void select(Sh04Export item) {
    final index = exports.indexOf(item);
    if (index >= 0) {
      _selectedIndex = index;
      _notifyIfAlive();
    }
  }

  @override
  void dispose() {
    _disposed = true;
    super.dispose();
  }

  void _notifyIfAlive() {
    if (!_disposed) notifyListeners();
  }

  static Sh04FailureKind _classifyFailure(Object error) {
    final message = error.toString().toLowerCase();
    if (message.contains('http 401')) return Sh04FailureKind.authentication;
    if (message.contains('http 403')) return Sh04FailureKind.permissionDenied;
    if (error is LumenisCoreException &&
        (message.contains('unavailable') || message.contains('timed out'))) {
      return Sh04FailureKind.offline;
    }
    return Sh04FailureKind.response;
  }
}
