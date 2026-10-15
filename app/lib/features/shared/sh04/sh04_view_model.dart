import 'dart:convert';
import 'dart:math';

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
  Sh04FailureKind? _loadMoreFailureKind;
  Sh04ScopeErrorKind? _scopeError;
  Sh04Snapshot? _snapshot;
  String? _selectedArtifactId;
  bool _operationBusy = false;
  bool _disposed = false;
  String? _pendingCreateFingerprint;
  String? _pendingCreateRequestId;
  String? _pendingRevisionFingerprint;
  String? _pendingRevisionRequestId;

  Sh04LoadPhase get phase => _phase;
  Sh04FailureKind? get failureKind => _failureKind;
  Sh04FailureKind? get loadMoreFailureKind => _loadMoreFailureKind;
  Sh04ScopeErrorKind? get scopeError => _scopeError;
  Sh04Snapshot? get snapshot => _snapshot;
  List<Sh04Export> get exports => _snapshot?.exports ?? const <Sh04Export>[];
  Sh04Export? get selected => exports
      .where((item) => item.internalId == _selectedArtifactId)
      .firstOrNull;
  bool get operationBusy => _operationBusy;

  Future<void> refresh() async {
    _phase = Sh04LoadPhase.loading;
    _failureKind = null;
    _loadMoreFailureKind = null;
    _scopeError = null;
    _snapshot = null;
    _selectedArtifactId = null;
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

  Future<void> loadMore() async {
    final current = _snapshot;
    if (current == null || !current.hasMore || _operationBusy) return;
    _loadMoreFailureKind = null;
    _setOperationBusy(true);
    try {
      final next = await _repository.loadExports(cursor: current.nextCursor);
      final byId = <String, Sh04Export>{
        for (final item in current.exports) item.internalId: item,
        for (final item in next.exports) item.internalId: item,
      };
      _snapshot = Sh04Snapshot(
        scope: Sh04Scope.sharedWorkspace,
        exports: List.unmodifiable(byId.values),
        verificationComplete:
            current.verificationComplete && next.verificationComplete,
        unverifiedCandidates:
            current.unverifiedCandidates + next.unverifiedCandidates,
        hasMore: next.hasMore,
        nextCursor: next.nextCursor,
      );
    } catch (error) {
      _loadMoreFailureKind = _classifyFailure(error);
    } finally {
      _setOperationBusy(false);
    }
  }

  Future<Sh04Export> saveReport({
    required String title,
    required String markdown,
  }) async {
    _validateUserDraft(title, markdown);
    final fingerprint = jsonEncode([title, markdown]);
    if (_pendingCreateFingerprint != fingerprint) {
      _pendingCreateFingerprint = fingerprint;
      _pendingCreateRequestId = _newRequestId();
    }
    final requestId = _pendingCreateRequestId!;
    return _runOperation(() async {
      final saved = await _repository.saveReport(
        title: title,
        markdown: markdown,
        requestId: requestId,
      );
      _mergeItem(saved);
      _pendingCreateFingerprint = null;
      _pendingCreateRequestId = null;
      return saved;
    });
  }

  Future<Sh04Export> reopen(Sh04Export item) => _runOperation(() async {
    final reopened = await _repository.reopen(item.internalId);
    if (reopened.internalId != item.internalId ||
        reopened.sha256 != item.sha256 ||
        reopened.version != item.version) {
      throw const FormatException(
        'The reopened SavedWork version does not match the selected version.',
      );
    }
    _mergeItem(reopened);
    return reopened;
  });

  Future<Sh04Export> reviseReport({
    required Sh04Export parent,
    required String title,
    required String markdown,
    required String reason,
  }) async {
    _validateUserDraft(title, markdown);
    if (reason.trim().isEmpty || reason.length > 4000) {
      throw const FormatException('A revision reason is required.');
    }
    final fingerprint = jsonEncode([
      parent.internalId,
      parent.sha256,
      reason,
      title,
      markdown,
    ]);
    if (_pendingRevisionFingerprint != fingerprint) {
      _pendingRevisionFingerprint = fingerprint;
      _pendingRevisionRequestId = _newRequestId();
    }
    final requestId = _pendingRevisionRequestId!;
    return _runOperation(() async {
      final revised = await _repository.reviseReport(
        parent: parent,
        title: title,
        markdown: markdown,
        reason: reason,
        requestId: requestId,
      );
      if (revised.version != parent.version + 1 ||
          revised.parentArtifactId != parent.internalId ||
          revised.workId != parent.workId) {
        throw const FormatException(
          'The returned revision does not continue the selected version.',
        );
      }
      _mergeItem(revised);
      _pendingRevisionFingerprint = null;
      _pendingRevisionRequestId = null;
      return revised;
    });
  }

  Future<SavedWorkExportFile> export(Sh04Export item, String format) =>
      _runOperation(() async {
        final file = await _repository.export(
          artifactId: item.internalId,
          format: format,
        );
        if (file.bytes.isEmpty) {
          throw const FormatException('The exported file is empty.');
        }
        return file;
      });

  @override
  void dispose() {
    _disposed = true;
    super.dispose();
  }

  Future<T> _runOperation<T>(Future<T> Function() operation) async {
    if (_operationBusy) {
      throw const LumenisCoreException(
        'Another SavedWork operation is in progress.',
        errorCode: 'SAVED_WORK_OPERATION_BUSY',
      );
    }
    _setOperationBusy(true);
    try {
      return await operation();
    } finally {
      _setOperationBusy(false);
    }
  }

  void _mergeItem(Sh04Export item) {
    final current = _snapshot;
    final items = <String, Sh04Export>{
      if (current != null)
        for (final existing in current.exports) existing.internalId: existing,
      item.internalId: item,
    };
    _snapshot = Sh04Snapshot(
      scope: Sh04Scope.sharedWorkspace,
      exports: List.unmodifiable(items.values),
      verificationComplete: current?.verificationComplete ?? true,
      unverifiedCandidates: current?.unverifiedCandidates ?? 0,
      hasMore: current?.hasMore ?? false,
      nextCursor: current?.nextCursor,
    );
    _selectedArtifactId = item.internalId;
    _notifyIfAlive();
  }

  void _setOperationBusy(bool value) {
    _operationBusy = value;
    _notifyIfAlive();
  }

  void _notifyIfAlive() {
    if (!_disposed) notifyListeners();
  }

  static void _validateUserDraft(String title, String markdown) {
    if (title.trim().isEmpty || title.length > 300 || markdown.trim().isEmpty) {
      throw const FormatException('A title and report text are required.');
    }
  }

  static String _newRequestId() {
    final random = Random.secure();
    final suffix = List.generate(
      24,
      (_) => random.nextInt(16).toRadixString(16),
    ).join();
    return 'sh04_$suffix';
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
