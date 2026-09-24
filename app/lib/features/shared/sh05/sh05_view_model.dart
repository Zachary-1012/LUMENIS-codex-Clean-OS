import 'package:flutter/foundation.dart';

import '../../../core/lumenis_core_client.dart';
import 'sh05_repository.dart';
import 'sh05_snapshot.dart';

enum Sh05LoadPhase { loading, ready, blocked, failed }

enum Sh05FailureKind { authentication, permissionDenied, offline, response }

enum Sh05Shelf { all, verified, candidates, retired }

class Sh05ViewModel extends ChangeNotifier {
  Sh05ViewModel({required this._repository});

  final Sh05Repository _repository;
  Sh05LoadPhase _phase = Sh05LoadPhase.loading;
  Sh05FailureKind? _failureKind;
  Sh05ScopeErrorKind? _scopeError;
  Sh05Snapshot? _snapshot;
  Sh05Shelf _shelf = Sh05Shelf.all;
  int? _selectedIndex;
  bool _disposed = false;

  Sh05LoadPhase get phase => _phase;
  Sh05FailureKind? get failureKind => _failureKind;
  Sh05ScopeErrorKind? get scopeError => _scopeError;
  Sh05Snapshot? get snapshot => _snapshot;
  Sh05Shelf get shelf => _shelf;

  List<Sh05Asset> get visibleAssets {
    final items = _snapshot?.assets ?? const <Sh05Asset>[];
    return items
        .where((item) {
          return switch (_shelf) {
            Sh05Shelf.all => true,
            Sh05Shelf.verified =>
              item.promotionStatus == Sh05PromotionStatus.domainVerified ||
                  item.promotionStatus == Sh05PromotionStatus.coreVerified ||
                  item.promotionStatus == Sh05PromotionStatus.repaired,
            Sh05Shelf.candidates =>
              item.promotionStatus == Sh05PromotionStatus.candidate ||
                  item.promotionStatus ==
                      Sh05PromotionStatus.transferCandidate ||
                  item.promotionStatus == Sh05PromotionStatus.observed,
            Sh05Shelf.retired =>
              item.promotionStatus == Sh05PromotionStatus.retired ||
                  item.promotionStatus == Sh05PromotionStatus.rejected,
          };
        })
        .toList(growable: false);
  }

  Sh05Asset? get selected {
    final items = visibleAssets;
    if (items.isEmpty) return null;
    return items[(_selectedIndex ?? 0).clamp(0, items.length - 1).toInt()];
  }

  Future<void> refresh() async {
    _phase = Sh05LoadPhase.loading;
    _failureKind = null;
    _scopeError = null;
    _snapshot = null;
    _selectedIndex = null;
    _notifyIfAlive();
    try {
      _snapshot = await _repository.loadAssets();
      _phase = Sh05LoadPhase.ready;
    } on Sh05ScopeError catch (error) {
      _scopeError = error.kind;
      _phase = Sh05LoadPhase.blocked;
    } catch (error) {
      _failureKind = _classifyFailure(error);
      _phase = Sh05LoadPhase.failed;
    }
    _notifyIfAlive();
  }

  void setShelf(Sh05Shelf value) {
    _shelf = value;
    _selectedIndex = null;
    _notifyIfAlive();
  }

  void select(Sh05Asset asset) {
    final index = visibleAssets.indexOf(asset);
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

  static Sh05FailureKind _classifyFailure(Object error) {
    final message = error.toString().toLowerCase();
    if (message.contains('http 401')) return Sh05FailureKind.authentication;
    if (message.contains('http 403')) return Sh05FailureKind.permissionDenied;
    if (error is LumenisCoreException &&
        (message.contains('unavailable') || message.contains('timed out'))) {
      return Sh05FailureKind.offline;
    }
    return Sh05FailureKind.response;
  }
}
