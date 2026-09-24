import 'package:flutter/foundation.dart';

import '../../core/transport/lumenis_http_transport.dart';
import 'ai03_repository.dart';
import 'ai03_snapshot.dart';

enum Ai03LoadPhase { loading, ready, failed }

enum Ai03FailureKind { authentication, permissionDenied, offline, server }

class Ai03ViewModel extends ChangeNotifier {
  Ai03ViewModel({required this._repository});

  final Ai03Repository _repository;
  Ai03LoadPhase _phase = Ai03LoadPhase.loading;
  Ai03FailureKind? _failureKind;
  Ai03Snapshot? _snapshot;
  String? _selectedCitationId;

  Ai03LoadPhase get phase => _phase;
  Ai03FailureKind? get failureKind => _failureKind;
  Ai03Snapshot? get snapshot => _snapshot;
  String? get selectedCitationId => _selectedCitationId;

  Ai03Citation? get selectedCitation {
    final id = _selectedCitationId;
    if (id == null) return null;
    for (final entry in _snapshot?.thread ?? const <Ai03ThreadEntry>[]) {
      for (final citation in entry.citations) {
        if (citation.id == id) return citation;
      }
    }
    return null;
  }

  Future<void> refresh() async {
    _phase = Ai03LoadPhase.loading;
    _failureKind = null;
    _selectedCitationId = null;
    notifyListeners();
    try {
      _snapshot = await _repository.load();
      _phase = Ai03LoadPhase.ready;
    } catch (error) {
      _snapshot = null;
      _failureKind = _classifyFailure(error);
      _phase = Ai03LoadPhase.failed;
    }
    notifyListeners();
  }

  void selectCitation(String id) {
    if (_snapshot?.thread
            .expand((entry) => entry.citations)
            .any((item) => item.id == id) !=
        true) {
      return;
    }
    _selectedCitationId = id;
    notifyListeners();
  }

  static Ai03FailureKind _classifyFailure(Object error) {
    final message = error.toString().toLowerCase();
    if (message.contains('http 401') || message.contains('auth_required')) {
      return Ai03FailureKind.authentication;
    }
    if (message.contains('http 403') || message.contains('permission')) {
      return Ai03FailureKind.permissionDenied;
    }
    if (isLumenisConnectionError(error) ||
        message.contains('core unavailable') ||
        message.contains('timed out')) {
      return Ai03FailureKind.offline;
    }
    return Ai03FailureKind.server;
  }
}
