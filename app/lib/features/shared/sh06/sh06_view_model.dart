import 'package:flutter/foundation.dart';

import '../../../core/lumenis_core_client.dart';
import 'sh06_repository.dart';
import 'sh06_snapshot.dart';

enum Sh06LoadPhase { loading, ready, blocked, failed }

enum Sh06FailureKind { authentication, permissionDenied, offline, response }

enum Sh06Lane { tasks, notifications, alerts }

class Sh06ViewModel extends ChangeNotifier {
  Sh06ViewModel({required this._repository});

  final Sh06Repository _repository;
  Sh06LoadPhase _phase = Sh06LoadPhase.loading;
  Sh06FailureKind? _failureKind;
  Sh06ScopeErrorKind? _scopeError;
  Sh06Snapshot? _snapshot;
  Sh06Lane _lane = Sh06Lane.tasks;
  int? _selectedIndex;
  bool _disposed = false;

  Sh06LoadPhase get phase => _phase;
  Sh06FailureKind? get failureKind => _failureKind;
  Sh06ScopeErrorKind? get scopeError => _scopeError;
  Sh06Snapshot? get snapshot => _snapshot;
  Sh06Lane get lane => _lane;
  String get operationalState => _snapshot?.operationalState ?? '运行状态未确认';

  List<Sh06Item> get visibleItems {
    final items = _snapshot?.items ?? const <Sh06Item>[];
    final kind = switch (_lane) {
      Sh06Lane.tasks => Sh06ItemKind.task,
      Sh06Lane.notifications => Sh06ItemKind.notification,
      Sh06Lane.alerts => Sh06ItemKind.alert,
    };
    return items.where((item) => item.kind == kind).toList(growable: false);
  }

  Sh06Item? get selected {
    final items = visibleItems;
    if (items.isEmpty) return null;
    return items[(_selectedIndex ?? 0).clamp(0, items.length - 1).toInt()];
  }

  Future<void> refresh() async {
    _phase = Sh06LoadPhase.loading;
    _failureKind = null;
    _scopeError = null;
    _snapshot = null;
    _selectedIndex = null;
    _notifyIfAlive();
    try {
      _snapshot = await _repository.loadInbox();
      _phase = Sh06LoadPhase.ready;
    } on Sh06ScopeError catch (error) {
      _scopeError = error.kind;
      _phase = Sh06LoadPhase.blocked;
    } catch (error) {
      _failureKind = _classifyFailure(error);
      _phase = Sh06LoadPhase.failed;
    }
    _notifyIfAlive();
  }

  void setLane(Sh06Lane value) {
    _lane = value;
    _selectedIndex = null;
    _notifyIfAlive();
  }

  void select(Sh06Item item) {
    final index = visibleItems.indexOf(item);
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

  static Sh06FailureKind _classifyFailure(Object error) {
    final message = error.toString().toLowerCase();
    if (message.contains('http 401')) return Sh06FailureKind.authentication;
    if (message.contains('http 403')) return Sh06FailureKind.permissionDenied;
    if (error is LumenisCoreException &&
        (message.contains('unavailable') || message.contains('timed out'))) {
      return Sh06FailureKind.offline;
    }
    return Sh06FailureKind.response;
  }
}
