import 'package:flutter/foundation.dart';

import '../../../core/lumenis_core_client.dart';
import 'sh02_repository.dart';
import 'sh02_snapshot.dart';

enum Sh02LoadPhase { loading, ready, blocked, failed }

enum Sh02FailureKind { authentication, permissionDenied, offline, response }

class Sh02ViewModel extends ChangeNotifier {
  Sh02ViewModel({required this._repository});

  final Sh02Repository _repository;
  Sh02LoadPhase _phase = Sh02LoadPhase.loading;
  Sh02FailureKind? _failureKind;
  Sh02ScopeErrorKind? _scopeError;
  Sh02Snapshot? _snapshot;
  Sh02EvidenceKind? _kindFilter;
  String _query = '';
  int? _selectedIndex;
  bool _disposed = false;

  Sh02LoadPhase get phase => _phase;
  Sh02FailureKind? get failureKind => _failureKind;
  Sh02ScopeErrorKind? get scopeError => _scopeError;
  Sh02Snapshot? get snapshot => _snapshot;
  Sh02EvidenceKind? get kindFilter => _kindFilter;
  String get query => _query;

  List<Sh02Evidence> get visibleEvidence {
    final items = _snapshot?.evidence ?? const <Sh02Evidence>[];
    final needle = _query.trim().toLowerCase();
    return items
        .where(
          (item) =>
              (_kindFilter == null || item.kind == _kindFilter) &&
              (needle.isEmpty ||
                  item.summary.toLowerCase().contains(needle) ||
                  item.source.toLowerCase().contains(needle)),
        )
        .toList(growable: false);
  }

  Sh02Evidence? get selected {
    final items = visibleEvidence;
    if (items.isEmpty) return null;
    final index = _selectedIndex ?? 0;
    return items[index.clamp(0, items.length - 1).toInt()];
  }

  Future<void> refresh() async {
    _phase = Sh02LoadPhase.loading;
    _failureKind = null;
    _scopeError = null;
    _snapshot = null;
    _selectedIndex = null;
    _notifyIfAlive();
    try {
      _snapshot = await _repository.loadLibrary();
      _phase = Sh02LoadPhase.ready;
    } on Sh02ScopeError catch (error) {
      _scopeError = error.kind;
      _phase = Sh02LoadPhase.blocked;
    } catch (error) {
      _failureKind = _classifyFailure(error);
      _phase = Sh02LoadPhase.failed;
    }
    _notifyIfAlive();
  }

  void setQuery(String value) {
    _query = value;
    _selectedIndex = null;
    _notifyIfAlive();
  }

  void setKindFilter(Sh02EvidenceKind? value) {
    _kindFilter = value;
    _selectedIndex = null;
    _notifyIfAlive();
  }

  void select(Sh02Evidence item) {
    final index = visibleEvidence.indexOf(item);
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

  static Sh02FailureKind _classifyFailure(Object error) {
    final message = error.toString().toLowerCase();
    if (message.contains('http 401')) return Sh02FailureKind.authentication;
    if (message.contains('http 403')) return Sh02FailureKind.permissionDenied;
    if (error is LumenisCoreException &&
        (message.contains('unavailable') || message.contains('timed out'))) {
      return Sh02FailureKind.offline;
    }
    return Sh02FailureKind.response;
  }
}
