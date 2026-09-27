import 'package:flutter/foundation.dart';

import '../../../core/transport/lumenis_http_transport.dart';
import 'acc02_repository.dart';
import 'acc02_snapshot.dart';

enum Acc02LoadPhase { loading, ready, failed }

enum Acc02FailureKind { authentication, permissionDenied, offline, server }

enum Acc02ConfirmationStatus {
  idle,
  submitting,
  confirmed,
  denied,
  outcomeUnknown,
  readbackUnavailable,
  mismatch,
}

class Acc02ViewModel extends ChangeNotifier {
  Acc02ViewModel({required this._repository});

  final Acc02Repository _repository;

  Acc02LoadPhase _phase = Acc02LoadPhase.loading;
  Acc02FailureKind? _failureKind;
  Acc02Snapshot? _snapshot;
  String? _selectingId;
  String? _actionError;
  String? _confirmationSubjectId;
  String? _confirmationDomainId;
  Acc02ConfirmationStatus _confirmationStatus = Acc02ConfirmationStatus.idle;
  bool _disposed = false;
  bool _isRefreshing = false;
  bool _needsReadback = false;

  Acc02LoadPhase get phase => _phase;
  Acc02FailureKind? get failureKind => _failureKind;
  Acc02Snapshot? get snapshot => _snapshot;
  String? get selectingId => _selectingId;
  String? get actionError => _actionError;
  bool get isRefreshing => _isRefreshing;
  bool get isSelectionPending => _selectingId != null;
  bool get isCandidateNavigationLocked =>
      isSelectionPending || _isRefreshing || _needsReadback;
  bool get needsReadback => _needsReadback;

  bool get canSelect =>
      !_disposed &&
      _selectingId == null &&
      !_isRefreshing &&
      !_needsReadback &&
      _phase == Acc02LoadPhase.ready &&
      _snapshot?.subjectState == Acc02SubjectState.ready;

  Acc02ConfirmationStatus confirmationStatusFor(Acc02Subject subject) =>
      _confirmationSubjectId == subject.id &&
          _confirmationDomainId == subject.domainId
      ? _confirmationStatus
      : Acc02ConfirmationStatus.idle;

  String? actionErrorFor(Acc02Subject subject) =>
      _confirmationSubjectId == subject.id &&
          _confirmationDomainId == subject.domainId
      ? _actionError
      : null;

  bool canConfirm(Acc02Subject subject) {
    final status = confirmationStatusFor(subject);
    final snapshot = _snapshot;
    return canSelect &&
        !_needsReadback &&
        status != Acc02ConfirmationStatus.confirmed &&
        !(snapshot?.contextState == Acc02ContextState.focused &&
            snapshot?.contextDomainId == subject.domainId &&
            snapshot?.selectedSubjectId == subject.id);
  }

  bool hasMatchingServerContext(Acc02Subject subject) {
    final snapshot = _snapshot;
    return _phase == Acc02LoadPhase.ready &&
        snapshot != null &&
        snapshot.contextState == Acc02ContextState.focused &&
        snapshot.contextDomainId == subject.domainId &&
        snapshot.selectedSubjectId == subject.id;
  }

  Future<void> refresh() async {
    if (_disposed || _selectingId != null || _isRefreshing) return;
    _isRefreshing = true;
    final checkingOutcome =
        _confirmationSubjectId != null &&
        _confirmationStatus != Acc02ConfirmationStatus.idle &&
        _confirmationStatus != Acc02ConfirmationStatus.submitting;
    if (!checkingOutcome) {
      _phase = Acc02LoadPhase.loading;
      _failureKind = null;
      if (_confirmationSubjectId == null) _actionError = null;
    }
    notifyListeners();
    try {
      final snapshot = await _repository.load();
      if (_disposed) return;
      _snapshot = snapshot;
      _phase = Acc02LoadPhase.ready;
      _failureKind = null;
      if (checkingOutcome) _resolvePendingReadback(snapshot);
    } catch (error) {
      if (_disposed) return;
      if (checkingOutcome) {
        _confirmationStatus = Acc02ConfirmationStatus.readbackUnavailable;
        _needsReadback = true;
        _actionError = _readbackPendingMessage;
        if (_snapshot != null) {
          _phase = Acc02LoadPhase.ready;
        } else {
          _failureKind = _classifyFailure(error);
          _phase = Acc02LoadPhase.failed;
        }
      } else {
        _snapshot = null;
        _failureKind = _classifyFailure(error);
        _phase = Acc02LoadPhase.failed;
      }
    } finally {
      _isRefreshing = false;
      if (!_disposed) notifyListeners();
    }
  }

  Future<void> selectSubject(Acc02Subject subject) async {
    if (_disposed || !canConfirm(subject)) {
      return;
    }
    _selectingId = subject.id;
    _confirmationSubjectId = subject.id;
    _confirmationDomainId = subject.domainId;
    _confirmationStatus = Acc02ConfirmationStatus.submitting;
    _needsReadback = false;
    _actionError = null;
    notifyListeners();
    try {
      try {
        await _repository.selectSubject(subject);
      } catch (error) {
        if (_disposed) return;
        final kind = _classifyFailure(error);
        if (kind == Acc02FailureKind.authentication ||
            kind == Acc02FailureKind.permissionDenied) {
          _confirmationStatus = Acc02ConfirmationStatus.denied;
          _needsReadback = false;
          _actionError = _deniedMessage(kind);
        } else {
          _confirmationStatus = Acc02ConfirmationStatus.outcomeUnknown;
          _needsReadback = true;
          _actionError = _readbackPendingMessage;
        }
        return;
      }
      if (_disposed) return;
      Acc02Snapshot snapshot;
      try {
        snapshot = await _repository.load();
      } catch (_) {
        if (_disposed) return;
        _confirmationStatus = Acc02ConfirmationStatus.readbackUnavailable;
        _needsReadback = true;
        _actionError = _readbackPendingMessage;
        if (_snapshot == null) {
          _phase = Acc02LoadPhase.failed;
          _failureKind = Acc02FailureKind.offline;
        } else {
          _phase = Acc02LoadPhase.ready;
        }
        return;
      }
      if (_disposed) return;
      _snapshot = snapshot;
      _phase = Acc02LoadPhase.ready;
      _failureKind = null;
      _resolvePendingReadback(snapshot);
    } finally {
      _selectingId = null;
      if (!_disposed) notifyListeners();
    }
  }

  void _resolvePendingReadback(Acc02Snapshot snapshot) {
    if (_confirmationSubjectId == null || _confirmationDomainId == null) {
      return;
    }
    if (snapshot.contextState == Acc02ContextState.unavailable) {
      _confirmationStatus = Acc02ConfirmationStatus.readbackUnavailable;
      _needsReadback = true;
      _actionError = _readbackPendingMessage;
      return;
    }

    _needsReadback = false;
    if (snapshot.contextState == Acc02ContextState.focused &&
        snapshot.contextDomainId == _confirmationDomainId &&
        snapshot.selectedSubjectId == _confirmationSubjectId) {
      _confirmationStatus = Acc02ConfirmationStatus.confirmed;
      _actionError = null;
      return;
    }

    _confirmationStatus = Acc02ConfirmationStatus.mismatch;
    _actionError = _mismatchMessage;
  }

  @override
  void dispose() {
    _disposed = true;
    super.dispose();
  }

  static Acc02FailureKind _classifyFailure(Object error) {
    final message = error.toString().toLowerCase();
    if (message.contains('http 401') || message.contains('auth_required')) {
      return Acc02FailureKind.authentication;
    }
    if (message.contains('http 403') || message.contains('permission')) {
      return Acc02FailureKind.permissionDenied;
    }
    if (isLumenisConnectionError(error) ||
        message.contains('core unavailable') ||
        message.contains('timed out')) {
      return Acc02FailureKind.offline;
    }
    return Acc02FailureKind.server;
  }

  static String _deniedMessage(Acc02FailureKind kind) => switch (kind) {
    Acc02FailureKind.authentication => '服务器拒绝了当前访问身份；查看范围未获确认。',
    Acc02FailureKind.permissionDenied => '服务器拒绝了这次范围变更；查看范围未获确认。',
    Acc02FailureKind.offline ||
    Acc02FailureKind.server => _readbackPendingMessage,
  };

  static const String _readbackPendingMessage = '变更结果待确认；请刷新查看服务器当前范围。';
  static const String _mismatchMessage = '服务器返回的范围与当前主体不一致；当前主体尚未获确认。';
}
