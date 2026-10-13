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
  Sh04Export? _opened;
  Sh04Export? _comparedParent;
  Sh04FailureKind? _actionFailure;
  Sh04FailureKind? _comparisonFailure;
  bool _opening = false;
  bool _loadingMore = false;
  bool _disposed = false;
  String _query = '';
  int _loadGeneration = 0;
  int _actionGeneration = 0;
  int _comparisonGeneration = 0;
  Sh04Export? _pendingItem;
  bool _pendingParent = false;

  Sh04LoadPhase get phase => _phase;
  Sh04FailureKind? get failureKind => _failureKind;
  Sh04ScopeErrorKind? get scopeError => _scopeError;
  Sh04Snapshot? get snapshot => _snapshot;
  List<Sh04Export> get exports => _snapshot?.exports ?? const <Sh04Export>[];
  Sh04Export? get selected => exports.isEmpty
      ? null
      : exports[(_selectedIndex ?? 0).clamp(0, exports.length - 1).toInt()];
  Sh04Export? get opened => _opened;
  Sh04Export? get comparedParent => _comparedParent;
  bool get opening => _opening;
  bool get loadingMore => _loadingMore;
  bool get hasMore => _snapshot?.hasMore ?? false;
  Sh04FailureKind? get actionFailure => _actionFailure;
  Sh04FailureKind? get comparisonFailure => _comparisonFailure;

  Future<void> refresh() => _refresh(_query);

  Future<void> search(String query) => _refresh(query.trim());

  Future<void> _refresh(String query) async {
    final generation = ++_loadGeneration;
    ++_actionGeneration;
    ++_comparisonGeneration;
    _query = query;
    _phase = Sh04LoadPhase.loading;
    _failureKind = null;
    _scopeError = null;
    _snapshot = null;
    _selectedIndex = null;
    _opened = null;
    _comparedParent = null;
    _actionFailure = null;
    _comparisonFailure = null;
    _opening = false;
    _loadingMore = false;
    _pendingItem = null;
    _pendingParent = false;
    _notifyIfAlive();
    try {
      final snapshot = _repository is Sh04SavedWorkRepository
          ? await _repository.search(query)
          : await _repository.loadExports();
      if (_disposed || generation != _loadGeneration) return;
      _snapshot = snapshot;
      _phase = Sh04LoadPhase.ready;
    } on Sh04ScopeError catch (error) {
      if (_disposed || generation != _loadGeneration) return;
      _scopeError = error.kind;
      _phase = Sh04LoadPhase.blocked;
    } catch (error) {
      if (_disposed || generation != _loadGeneration) return;
      _failureKind = _classifyFailure(error);
      _phase = Sh04LoadPhase.failed;
    }
    _notifyIfAlive();
  }

  Future<void> loadMore() async {
    final snapshot = _snapshot;
    final repository = _repository;
    if (_disposed ||
        _phase != Sh04LoadPhase.ready ||
        _loadingMore ||
        snapshot == null ||
        !snapshot.hasMore ||
        repository is! Sh04SavedWorkRepository) {
      return;
    }
    final generation = _loadGeneration;
    _loadingMore = true;
    _notifyIfAlive();
    try {
      final updated = await repository.loadMore(snapshot);
      if (_disposed || generation != _loadGeneration) return;
      _snapshot = updated;
      _phase = Sh04LoadPhase.ready;
    } catch (error) {
      if (_disposed || generation != _loadGeneration) return;
      final failed = _classifyFailure(error);
      _snapshot = Sh04Snapshot(
        scope: snapshot.scope,
        exports: snapshot.exports,
        failedDomains: snapshot.failedDomains,
        incomplete: true,
        hasMore: snapshot.hasMore,
        cursors: snapshot.cursors,
        hasMoreByDomain: snapshot.hasMoreByDomain,
        query: snapshot.query,
        contextSignature: snapshot.contextSignature,
      );
      _failureKind = failed;
    } finally {
      if (!_disposed && generation == _loadGeneration) {
        _loadingMore = false;
        _notifyIfAlive();
      }
    }
  }

  void select(Sh04Export item) {
    final index = exports.indexOf(item);
    if (index >= 0) {
      _selectedIndex = index;
      _notifyIfAlive();
    }
  }

  Future<void> open(Sh04Export item) async {
    final index = exports.indexOf(item);
    if (index >= 0) _selectedIndex = index;
    ++_comparisonGeneration;
    _comparedParent = null;
    _comparisonFailure = null;
    _pendingItem = item;
    _pendingParent = false;
    if (item.savedWork == null) {
      ++_actionGeneration;
      _opening = false;
      _opened = item;
      _actionFailure = null;
      _notifyIfAlive();
      return;
    }
    await _performOpen(item);
  }

  Future<void> openParent() async {
    final item = _opened ?? selected;
    final saved = item?.savedWork;
    if (_disposed ||
        item == null ||
        saved == null ||
        !saved.committed ||
        saved.parentArtifactId == null ||
        saved.parentSha256 == null ||
        saved.version < 2) {
      return;
    }
    _pendingItem = item;
    _pendingParent = true;
    ++_comparisonGeneration;
    _comparedParent = null;
    _comparisonFailure = null;
    await _performOpen(
      item,
      artifactId: saved.parentArtifactId,
      expectedHash: saved.parentSha256,
      expectedVersion: saved.version - 1,
    );
  }

  Future<void> compareParent() async {
    final item = _opened;
    final saved = item?.savedWork;
    final repository = _repository;
    if (_disposed ||
        item == null ||
        saved == null ||
        !saved.committed ||
        saved.parentArtifactId == null ||
        saved.parentSha256 == null ||
        saved.version < 2 ||
        repository is! Sh04SavedWorkRepository) {
      return;
    }
    final generation = ++_comparisonGeneration;
    final openedId = item.internalId;
    _comparisonFailure = null;
    _comparedParent = null;
    _notifyIfAlive();
    try {
      final parent = await repository.reopen(
        item,
        artifactId: saved.parentArtifactId,
        expectedHash: saved.parentSha256,
        expectedVersion: saved.version - 1,
      );
      if (_disposed ||
          generation != _comparisonGeneration ||
          _opened?.internalId != openedId) {
        return;
      }
      if (parent.savedWork?.committed != true) {
        throw const FormatException('The parent commit is not verified.');
      }
      _comparedParent = parent;
    } catch (error) {
      if (_disposed ||
          generation != _comparisonGeneration ||
          _opened?.internalId != openedId) {
        return;
      }
      _comparisonFailure = _classifyFailure(error);
      _comparedParent = null;
    }
    _notifyIfAlive();
  }

  Future<void> retryComparison() => compareParent();

  Future<void> retrySelected() async {
    final item = _pendingItem ?? selected;
    if (item == null) return;
    final saved = item.savedWork;
    if (_pendingParent && saved != null) {
      await _performOpen(
        item,
        artifactId: saved.parentArtifactId,
        expectedHash: saved.parentSha256,
        expectedVersion: saved.version - 1,
      );
    } else {
      await open(item);
    }
  }

  void backToList() {
    ++_actionGeneration;
    ++_comparisonGeneration;
    _opening = false;
    _opened = null;
    _comparedParent = null;
    _actionFailure = null;
    _comparisonFailure = null;
    _pendingItem = null;
    _pendingParent = false;
    _notifyIfAlive();
  }

  Future<void> _performOpen(
    Sh04Export item, {
    String? artifactId,
    String? expectedHash,
    int? expectedVersion,
  }) async {
    final repository = _repository;
    final generation = ++_actionGeneration;
    _opening = true;
    _opened = null;
    _actionFailure = null;
    _notifyIfAlive();
    try {
      if (repository is! Sh04SavedWorkRepository) {
        throw const FormatException('SavedWork reopen is unavailable.');
      }
      final opened = await repository.reopen(
        item,
        artifactId: artifactId,
        expectedHash: expectedHash,
        expectedVersion: expectedVersion,
      );
      if (_disposed || generation != _actionGeneration) return;
      if (opened.savedWork?.committed != true) {
        throw const FormatException('The saved result is not verified.');
      }
      _opened = opened;
    } catch (error) {
      if (_disposed || generation != _actionGeneration) return;
      _actionFailure = _classifyFailure(error);
      _opened = null;
    } finally {
      if (!_disposed && generation == _actionGeneration) {
        _opening = false;
        _notifyIfAlive();
      }
    }
  }

  @override
  void dispose() {
    _disposed = true;
    ++_loadGeneration;
    ++_actionGeneration;
    ++_comparisonGeneration;
    super.dispose();
  }

  void _notifyIfAlive() {
    if (!_disposed) notifyListeners();
  }

  static Sh04FailureKind _classifyFailure(Object error) {
    if (error is LumenisCoreException) {
      if (error.statusCode == 401) return Sh04FailureKind.authentication;
      if (error.statusCode == 403) return Sh04FailureKind.permissionDenied;
    }
    final message = error.toString().toLowerCase();
    if (message.contains('http 401')) return Sh04FailureKind.authentication;
    if (message.contains('http 403') || message.contains('permission denied')) {
      return Sh04FailureKind.permissionDenied;
    }
    if (error is LumenisCoreException &&
        (message.contains('unavailable') || message.contains('timed out'))) {
      return Sh04FailureKind.offline;
    }
    return Sh04FailureKind.response;
  }
}
