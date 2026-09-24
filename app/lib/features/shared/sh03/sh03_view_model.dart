import 'package:flutter/foundation.dart';

import '../../../core/lumenis_core_client.dart';
import 'sh03_repository.dart';
import 'sh03_snapshot.dart';

enum Sh03LoadPhase { loading, ready, blocked, failed }

enum Sh03FailureKind { authentication, permissionDenied, offline, response }

class Sh03ViewModel extends ChangeNotifier {
  Sh03ViewModel({required this._repository});

  final Sh03Repository _repository;
  Sh03LoadPhase _phase = Sh03LoadPhase.loading;
  Sh03FailureKind? _failureKind;
  Sh03ScopeErrorKind? _scopeError;
  Sh03Snapshot? _snapshot;
  String _query = '';
  int? _selectedIndex;
  bool _disposed = false;

  Sh03LoadPhase get phase => _phase;
  Sh03FailureKind? get failureKind => _failureKind;
  Sh03ScopeErrorKind? get scopeError => _scopeError;
  Sh03Snapshot? get snapshot => _snapshot;
  String get query => _query;

  List<Sh03Metric> get visibleMetrics {
    final items = _snapshot?.metrics ?? const <Sh03Metric>[];
    final needle = _query.trim().toLowerCase();
    return items
        .where(
          (item) =>
              needle.isEmpty ||
              item.name.toLowerCase().contains(needle) ||
              item.definition.toLowerCase().contains(needle),
        )
        .toList(growable: false);
  }

  Sh03Metric? get selected {
    final items = visibleMetrics;
    if (items.isEmpty) return null;
    return items[(_selectedIndex ?? 0).clamp(0, items.length - 1).toInt()];
  }

  Future<void> refresh() async {
    _phase = Sh03LoadPhase.loading;
    _failureKind = null;
    _scopeError = null;
    _snapshot = null;
    _selectedIndex = null;
    _notifyIfAlive();
    try {
      _snapshot = await _repository.loadBrowser();
      _phase = Sh03LoadPhase.ready;
    } on Sh03ScopeError catch (error) {
      _scopeError = error.kind;
      _phase = Sh03LoadPhase.blocked;
    } catch (error) {
      _failureKind = _classifyFailure(error);
      _phase = Sh03LoadPhase.failed;
    }
    _notifyIfAlive();
  }

  void setQuery(String value) {
    _query = value;
    _selectedIndex = null;
    _notifyIfAlive();
  }

  void select(Sh03Metric metric) {
    final index = visibleMetrics.indexOf(metric);
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

  static Sh03FailureKind _classifyFailure(Object error) {
    final message = error.toString().toLowerCase();
    if (message.contains('http 401')) return Sh03FailureKind.authentication;
    if (message.contains('http 403')) return Sh03FailureKind.permissionDenied;
    if (error is LumenisCoreException &&
        (message.contains('unavailable') || message.contains('timed out'))) {
      return Sh03FailureKind.offline;
    }
    return Sh03FailureKind.response;
  }
}
