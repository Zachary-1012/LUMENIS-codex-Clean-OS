import 'package:flutter/foundation.dart';

import '../../core/transport/lumenis_http_transport.dart';
import 'bmp03_repository.dart';
import 'bmp03_snapshot.dart';

enum Bmp03LoadPhase { loading, ready, failed }

enum Bmp03FailureKind { authentication, permissionDenied, offline, server }

class Bmp03ViewModel extends ChangeNotifier {
  Bmp03ViewModel({required this._repository});

  final Bmp03Repository _repository;
  bool _disposed = false;

  Bmp03LoadPhase _phase = Bmp03LoadPhase.loading;
  Bmp03FailureKind? _failureKind;
  Bmp03Snapshot? _snapshot;
  String? _kindFilter;
  String? _selectedSignalId;

  Bmp03LoadPhase get phase => _phase;
  Bmp03FailureKind? get failureKind => _failureKind;
  Bmp03Snapshot? get snapshot => _snapshot;
  String? get kindFilter => _kindFilter;
  String? get selectedSignalId => _selectedSignalId;

  List<Bmp03Signal> get filteredSignals {
    final signals = _snapshot?.signals ?? const <Bmp03Signal>[];
    return signals
        .where((signal) => _kindFilter == null || signal.kind == _kindFilter)
        .toList(growable: false);
  }

  Bmp03Signal? get selectedSignal {
    for (final signal in filteredSignals) {
      if (signal.id == _selectedSignalId) return signal;
    }
    return filteredSignals.isEmpty ? null : filteredSignals.first;
  }

  Future<void> refresh() async {
    if (_disposed) return;
    _phase = Bmp03LoadPhase.loading;
    _failureKind = null;
    notifyListeners();
    if (_disposed) return;
    try {
      final snapshot = await _repository.load();
      if (_disposed) return;
      final previousFocus = _snapshot?.focus;
      final focus = snapshot.focus;
      if (previousFocus == null ||
          previousFocus.mode != focus.mode ||
          previousFocus.subjectId != focus.subjectId ||
          previousFocus.brandFocusId != focus.brandFocusId ||
          !snapshot.scopeReady) {
        _kindFilter = null;
        _selectedSignalId = null;
      }
      _snapshot = snapshot;
      _phase = Bmp03LoadPhase.ready;
      if (!_snapshot!.signals.any((signal) => signal.id == _selectedSignalId)) {
        _selectedSignalId = _snapshot!.signals.isEmpty
            ? null
            : _snapshot!.signals.first.id;
      }
    } catch (error) {
      if (_disposed) return;
      _snapshot = null;
      _failureKind = _classify(error);
      _phase = Bmp03LoadPhase.failed;
    }
    if (_disposed) return;
    notifyListeners();
  }

  void setKindFilter(String? kind) {
    if (_kindFilter == kind) return;
    _kindFilter = kind;
    if (!filteredSignals.any((signal) => signal.id == _selectedSignalId)) {
      _selectedSignalId = filteredSignals.isEmpty
          ? null
          : filteredSignals.first.id;
    }
    notifyListeners();
  }

  void selectSignal(String id) {
    if (_selectedSignalId == id) return;
    if (!(filteredSignals.any((signal) => signal.id == id))) return;
    _selectedSignalId = id;
    notifyListeners();
  }

  static Bmp03FailureKind _classify(Object error) {
    final message = error.toString().toLowerCase();
    if (message.contains('http 401') || message.contains('auth_required')) {
      return Bmp03FailureKind.authentication;
    }
    if (message.contains('http 403')) {
      return Bmp03FailureKind.permissionDenied;
    }
    if (isLumenisConnectionError(error) ||
        message.contains('core unavailable') ||
        message.contains('connection timed out')) {
      return Bmp03FailureKind.offline;
    }
    return Bmp03FailureKind.server;
  }

  @override
  void dispose() {
    _disposed = true;
    super.dispose();
  }
}
