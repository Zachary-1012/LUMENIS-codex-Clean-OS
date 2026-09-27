import 'package:flutter/foundation.dart';

import '../../core/transport/lumenis_http_transport.dart';
import 'bmp05_repository.dart';
import 'bmp05_snapshot.dart';

enum Bmp05LoadPhase { loading, ready, failed }

enum Bmp05FailureKind { authentication, permissionDenied, offline, server }

class Bmp05ViewModel extends ChangeNotifier {
  Bmp05ViewModel({required this._repository});

  final Bmp05Repository _repository;
  bool _disposed = false;

  Bmp05LoadPhase _phase = Bmp05LoadPhase.loading;
  Bmp05FailureKind? _failureKind;
  Bmp05Snapshot? _snapshot;
  String? _tierFilter;
  String? _riskFilter;
  String? _selectedCreatorId;

  Bmp05LoadPhase get phase => _phase;
  Bmp05FailureKind? get failureKind => _failureKind;
  Bmp05Snapshot? get snapshot => _snapshot;
  String? get tierFilter => _tierFilter;
  String? get riskFilter => _riskFilter;
  String? get selectedCreatorId => _selectedCreatorId;

  List<Bmp05Creator> get filteredCreators {
    final creators = _snapshot?.creators ?? const <Bmp05Creator>[];
    return creators
        .where(
          (creator) =>
              (_tierFilter == null || creator.tier == _tierFilter) &&
              (_riskFilter == null || creator.risk?.level == _riskFilter),
        )
        .toList(growable: false);
  }

  Bmp05Creator? get selectedCreator {
    for (final creator in filteredCreators) {
      if (creator.id == _selectedCreatorId) return creator;
    }
    return filteredCreators.isEmpty ? null : filteredCreators.first;
  }

  Future<void> refresh() async {
    if (_disposed) return;
    _phase = Bmp05LoadPhase.loading;
    _failureKind = null;
    notifyListeners();
    if (_disposed) return;
    try {
      final snapshot = await _repository.load();
      if (_disposed) return;
      _snapshot = snapshot;
      _phase = Bmp05LoadPhase.ready;
      if (!_snapshot!.creators.any(
        (creator) => creator.id == _selectedCreatorId,
      )) {
        _selectedCreatorId = _snapshot!.creators.isEmpty
            ? null
            : _snapshot!.creators.first.id;
      }
    } catch (error) {
      if (_disposed) return;
      _snapshot = null;
      _failureKind = _classify(error);
      _phase = Bmp05LoadPhase.failed;
    }
    if (_disposed) return;
    notifyListeners();
  }

  void setTierFilter(String? tier) {
    if (_tierFilter == tier) return;
    _tierFilter = tier;
    notifyListeners();
  }

  void setRiskFilter(String? risk) {
    if (_riskFilter == risk) return;
    _riskFilter = risk;
    notifyListeners();
  }

  void selectCreator(String id) {
    if (_selectedCreatorId == id) return;
    if (!(filteredCreators.any((creator) => creator.id == id))) return;
    _selectedCreatorId = id;
    notifyListeners();
  }

  static Bmp05FailureKind _classify(Object error) {
    final message = error.toString().toLowerCase();
    if (message.contains('http 401') || message.contains('auth_required')) {
      return Bmp05FailureKind.authentication;
    }
    if (message.contains('http 403')) {
      return Bmp05FailureKind.permissionDenied;
    }
    if (isLumenisConnectionError(error) ||
        message.contains('core unavailable') ||
        message.contains('connection timed out')) {
      return Bmp05FailureKind.offline;
    }
    return Bmp05FailureKind.server;
  }

  @override
  void dispose() {
    _disposed = true;
    super.dispose();
  }
}
