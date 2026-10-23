import 'dart:math' as math;

import 'package:flutter/foundation.dart';

import '../../../core/lumenis_core_client.dart';
import 'sh02_repository.dart';
import 'sh02_snapshot.dart';

enum Sh02LoadPhase { loading, ready, blocked, failed }

enum Sh02FailureKind { authentication, permissionDenied, offline, response }

enum Sh02ImportStatus { idle, uploading, uncertain, failed }

class Sh02ViewModel extends ChangeNotifier {
  Sh02ViewModel({required this._repository, required this._documentPicker});

  final Sh02Repository _repository;
  final Sh02DocumentPicker _documentPicker;
  Sh02LoadPhase _phase = Sh02LoadPhase.loading;
  Sh02FailureKind? _failureKind;
  Sh02ScopeErrorKind? _scopeError;
  Sh02Snapshot? _snapshot;
  Sh02EvidenceKind? _kindFilter;
  String _query = '';
  int? _selectedIndex;
  List<Sh02ImportedMaterial> _recentImports = const [];
  bool _importsLoading = false;
  bool _importsFailed = false;
  bool _importsHaveMore = false;
  bool _importsVerificationComplete = true;
  int _unverifiedImportCandidates = 0;
  int _malformedImportItems = 0;
  String? _importsCursor;
  Sh02ImportStatus _importStatus = Sh02ImportStatus.idle;
  Sh02ImportedMaterial? _openedImport;
  bool _openingImport = false;
  bool _importOpenFailed = false;
  String? _pendingImportRequestId;
  String? _pendingImportSearchRequestId;
  String? _pendingImportSearchCursor;
  bool _pendingImportSearchStarted = false;
  bool _pendingImportSearchExhausted = false;
  bool _reconcilingImport = false;
  Sh02ImportedMaterial? _pendingImportCandidate;
  bool _disposed = false;
  int _readGeneration = 0;
  Sh02SourcePage? _sourcePage;
  bool _rowsLoading = false;
  bool _rowsFailed = false;
  Sh02SourcePage? get sourcePage => _sourcePage;
  bool get rowsLoading => _rowsLoading;
  bool get rowsFailed => _rowsFailed;

  Sh02LoadPhase get phase => _phase;
  Sh02FailureKind? get failureKind => _failureKind;
  Sh02ScopeErrorKind? get scopeError => _scopeError;
  Sh02Snapshot? get snapshot => _snapshot;
  Sh02EvidenceKind? get kindFilter => _kindFilter;
  String get query => _query;
  List<Sh02ImportedMaterial> get recentImports => _recentImports;
  bool get importsLoading => _importsLoading;
  bool get importsFailed => _importsFailed;
  bool get importsHaveMore => _importsHaveMore;
  bool get importsVerificationComplete => _importsVerificationComplete;
  int get unverifiedImportCandidates => _unverifiedImportCandidates;
  int get malformedImportItems => _malformedImportItems;
  Sh02ImportStatus get importStatus => _importStatus;
  Sh02ImportedMaterial? get openedImport => _openedImport;
  bool get openingImport => _openingImport;
  bool get importOpenFailed => _importOpenFailed;

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
    _readGeneration++;
    _sourcePage = null;
    _rowsLoading = false;
    _rowsFailed = false;
    _openingImport = false;
    _phase = Sh02LoadPhase.loading;
    _failureKind = null;
    _scopeError = null;
    _snapshot = null;
    _selectedIndex = null;
    _openedImport = null;
    _importOpenFailed = false;
    _notifyIfAlive();
    final library = _loadLibrary();
    final imports = loadRecentImports();
    await Future.wait([library, imports]);
  }

  Future<void> _loadLibrary() async {
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

  Future<void> loadRecentImports({String? cursor}) async {
    if (_importsLoading) return;
    _importsLoading = true;
    _importsFailed = false;
    _notifyIfAlive();
    try {
      final page = await _repository.loadRecentImports(cursor: cursor);
      final items = cursor == null
          ? page.items
          : [..._recentImports, ...page.items];
      _recentImports = [
        for (final item in {
          for (final value in items) value.artifactId: value,
        }.values)
          item,
      ];
      _importsHaveMore = page.hasMore;
      _importsCursor = page.nextCursor;
      _importsVerificationComplete = cursor == null
          ? page.verificationComplete
          : _importsVerificationComplete && page.verificationComplete;
      _unverifiedImportCandidates = cursor == null
          ? page.unverifiedCandidates
          : _unverifiedImportCandidates + page.unverifiedCandidates;
      _malformedImportItems = cursor == null
          ? page.malformedItems
          : _malformedImportItems + page.malformedItems;
      _importsFailed = false;
    } catch (_) {
      _importsFailed = true;
    } finally {
      _importsLoading = false;
      _notifyIfAlive();
    }
  }

  Future<void> loadMoreImports() async {
    final cursor = _importsCursor;
    if (!_importsHaveMore || cursor == null) return;
    await loadRecentImports(cursor: cursor);
  }

  Future<void> importDocument() async {
    if (_importStatus == Sh02ImportStatus.uncertain &&
        _pendingImportRequestId != null) {
      await _reconcilePendingImport();
      return;
    }
    if (_importStatus == Sh02ImportStatus.uploading) return;
    Sh02PickedDocument? picked;
    try {
      picked = await _documentPicker.pick();
    } on FormatException {
      _importStatus = Sh02ImportStatus.failed;
      _notifyIfAlive();
      return;
    } catch (_) {
      _importStatus = Sh02ImportStatus.failed;
      _notifyIfAlive();
      return;
    }
    if (picked == null) return;
    final filename = picked.filename;
    final bytes = picked.bytes;
    if (filename.isEmpty || bytes.isEmpty || bytes.length > 8 * 1024 * 1024) {
      _importStatus = Sh02ImportStatus.failed;
      _notifyIfAlive();
      return;
    }
    final requestId = _pendingImportRequestId ?? _newRequestId();
    _pendingImportRequestId = requestId;
    _readGeneration++;
    _sourcePage = null;
    _rowsLoading = false;
    _rowsFailed = false;
    _openingImport = false;
    _openedImport = null;
    _importOpenFailed = false;
    _importStatus = Sh02ImportStatus.uploading;
    _notifyIfAlive();
    try {
      final uploaded = await _repository.importDocument(
        filename: filename,
        bytes: bytes,
        requestId: requestId,
      );
      await _verifyAndOpen(uploaded);
    } catch (error) {
      if (error is LumenisCoreException &&
          error.statusCode != null &&
          error.statusCode! >= 400 &&
          error.statusCode! < 500) {
        _importStatus = Sh02ImportStatus.failed;
        _pendingImportRequestId = null;
        _resetPendingImportSearch();
      } else {
        _importStatus = Sh02ImportStatus.uncertain;
        await _reconcilePendingImport();
      }
      _notifyIfAlive();
    }
  }

  Future<void> checkImportStatus() => _reconcilePendingImport();

  Future<void> _reconcilePendingImport() async {
    final requestId = _pendingImportRequestId;
    if (requestId == null || _importsLoading || _reconcilingImport) return;
    if (_pendingImportCandidate != null) {
      _reconcilingImport = true;
      try {
        await _verifyAndOpen(_pendingImportCandidate!);
      } catch (_) {
        _importStatus = Sh02ImportStatus.uncertain;
        _notifyIfAlive();
      } finally {
        _reconcilingImport = false;
      }
      return;
    }

    if (_pendingImportSearchRequestId != requestId) {
      _pendingImportSearchRequestId = requestId;
      _pendingImportSearchCursor = null;
      _pendingImportSearchStarted = false;
      _pendingImportSearchExhausted = false;
    } else if (_pendingImportSearchExhausted) {
      _pendingImportSearchCursor = null;
      _pendingImportSearchStarted = false;
      _pendingImportSearchExhausted = false;
    }

    final cursor = _pendingImportSearchStarted
        ? _pendingImportSearchCursor
        : null;
    _reconcilingImport = true;
    _importStatus = Sh02ImportStatus.uncertain;
    _notifyIfAlive();
    try {
      await loadRecentImports(cursor: cursor);
      if (_importsFailed) return;

      _pendingImportSearchStarted = true;
      _pendingImportSearchCursor = _importsCursor;
      _pendingImportSearchExhausted =
          !_importsHaveMore || _pendingImportSearchCursor == null;

      Sh02ImportedMaterial? match;
      for (final item in _recentImports) {
        if (item.requestId == requestId) {
          match = item;
          break;
        }
      }
      if (match != null) {
        _pendingImportCandidate = match;
        try {
          await _verifyAndOpen(match);
        } catch (_) {
          _importStatus = Sh02ImportStatus.uncertain;
        }
      }
    } finally {
      _reconcilingImport = false;
      _notifyIfAlive();
    }
  }

  Future<void> _verifyAndOpen(Sh02ImportedMaterial uploaded) async {
    final generation = ++_readGeneration;
    _sourcePage = null;
    _rowsLoading = false;
    _rowsFailed = false;
    _openingImport = false;
    _openedImport = null;
    _notifyIfAlive();
    final reopened = await _repository.reopenImport(uploaded.artifactId);
    if (reopened.artifactId != uploaded.artifactId ||
        reopened.artifactSha256 != uploaded.artifactSha256 ||
        reopened.requestId != uploaded.requestId ||
        reopened.filename != uploaded.filename ||
        reopened.sourceSha256 != uploaded.sourceSha256 ||
        reopened.sizeBytes != uploaded.sizeBytes) {
      throw const FormatException('Imported document readback changed.');
    }
    if (!_disposed && generation == _readGeneration) {
      _openedImport = reopened;
      if (const {
        'xlsx',
        'xls',
        'docx',
        'doc',
        'pdf',
        'csv',
      }.contains(reopened.filename.split('.').last.toLowerCase())) {
        await loadSourcePage(0);
      }
    }
    _pendingImportRequestId = null;
    _resetPendingImportSearch();
    _importStatus = Sh02ImportStatus.idle;
    _recentImports = [
      reopened,
      ..._recentImports.where((item) => item.artifactId != reopened.artifactId),
    ];
    _notifyIfAlive();
    await loadRecentImports();
  }

  Future<void> openImport(Sh02ImportedMaterial item) =>
      _openImport(item.artifactId, expected: item);

  Future<void> openImportById(String artifactId) => _openImport(artifactId);

  Future<void> _openImport(
    String artifactId, {
    Sh02ImportedMaterial? expected,
  }) async {
    final generation = ++_readGeneration;
    _sourcePage = null;
    _rowsLoading = false;
    _rowsFailed = false;
    _openedImport = null;
    _importOpenFailed = false;
    _openingImport = true;
    _notifyIfAlive();
    try {
      final reopened = await _repository.reopenImport(artifactId);
      if (_disposed || generation != _readGeneration) return;
      if (reopened.artifactId != artifactId ||
          (expected != null &&
              (reopened.artifactSha256 != expected.artifactSha256 ||
                  reopened.requestId != expected.requestId ||
                  reopened.filename != expected.filename ||
                  reopened.sizeBytes != expected.sizeBytes ||
                  reopened.sourceSha256 != expected.sourceSha256))) {
        throw const FormatException('Imported document version changed.');
      }
      _openedImport = reopened;
      if (const {
        'xlsx',
        'xls',
        'docx',
        'doc',
        'pdf',
        'csv',
      }.contains(reopened.filename.split('.').last.toLowerCase())) {
        await loadSourcePage(0);
      }
      if (_pendingImportRequestId == reopened.requestId) {
        _pendingImportRequestId = null;
        _resetPendingImportSearch();
        _importStatus = Sh02ImportStatus.idle;
      }
    } catch (_) {
      if (_disposed || generation != _readGeneration) return;
      _importOpenFailed = true;
    } finally {
      if (!_disposed && generation == _readGeneration) {
        _openingImport = false;
        _notifyIfAlive();
      }
    }
  }

  Future<void> loadSourcePage(int offset) async {
    final item = _openedImport;
    if (item == null || _rowsLoading) return;
    final generation = _readGeneration;
    _rowsLoading = true;
    _rowsFailed = false;
    _sourcePage = null;
    _notifyIfAlive();
    try {
      final page = await _repository.readSourceRows(item, offset);
      if (!_disposed && generation == _readGeneration) _sourcePage = page;
    } catch (error) {
      if (!_disposed && generation == _readGeneration) {
        _rowsFailed = true;
        if (error is LumenisCoreException &&
            {401, 403, 404, 409, 410}.contains(error.statusCode)) {
          _openedImport = null;
          _importOpenFailed = true;
        }
      }
    } finally {
      if (!_disposed && generation == _readGeneration) {
        _rowsLoading = false;
        _notifyIfAlive();
      }
    }
  }

  void closeImport() {
    _readGeneration++;
    _sourcePage = null;
    _rowsLoading = false;
    _rowsFailed = false;
    _openingImport = false;
    _openedImport = null;
    _notifyIfAlive();
  }

  void _resetPendingImportSearch() {
    _pendingImportSearchRequestId = null;
    _pendingImportSearchCursor = null;
    _pendingImportSearchStarted = false;
    _pendingImportSearchExhausted = false;
    _pendingImportCandidate = null;
  }

  String _newRequestId() {
    final random = math.Random.secure();
    final suffix = List.generate(
      24,
      (_) => random.nextInt(256).toRadixString(16).padLeft(2, '0'),
    ).join();
    return 'sh02-$suffix';
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
