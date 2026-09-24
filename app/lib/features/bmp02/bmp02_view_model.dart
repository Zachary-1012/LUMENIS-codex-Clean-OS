import 'package:flutter/foundation.dart';

import '../../core/transport/lumenis_http_transport.dart';
import 'bmp02_repository.dart';
import 'bmp02_snapshot.dart';

enum Bmp02LoadPhase { loading, ready, failed }

enum Bmp02FailureKind { authentication, permissionDenied, offline, server }

class Bmp02ViewModel extends ChangeNotifier {
  Bmp02ViewModel({required this._repository});

  final Bmp02Repository _repository;

  Bmp02LoadPhase _phase = Bmp02LoadPhase.loading;
  Bmp02FailureKind? _failureKind;
  Bmp02Snapshot? _snapshot;
  String _query = '';
  String? _roleFilter;
  String? _selectedBrandId;

  Bmp02LoadPhase get phase => _phase;
  Bmp02FailureKind? get failureKind => _failureKind;
  Bmp02Snapshot? get snapshot => _snapshot;
  String get query => _query;
  String? get roleFilter => _roleFilter;
  String? get selectedBrandId => _selectedBrandId;

  List<Bmp02Brand> get filteredBrands {
    final brands = _snapshot?.brands ?? const <Bmp02Brand>[];
    final query = _query.trim().toLowerCase();
    return brands
        .where(
          (brand) =>
              (_roleFilter == null || brand.role == _roleFilter) &&
              (query.isEmpty ||
                  brand.name.toLowerCase().contains(query) ||
                  (brand.category ?? '').toLowerCase().contains(query)),
        )
        .toList(growable: false);
  }

  Bmp02Brand? get selectedBrand {
    final brands = filteredBrands;
    for (final brand in brands) {
      if (brand.id == _selectedBrandId) return brand;
    }
    return brands.isEmpty ? null : brands.first;
  }

  Future<void> refresh() async {
    _phase = Bmp02LoadPhase.loading;
    _failureKind = null;
    notifyListeners();
    try {
      _snapshot = await _repository.load();
      _phase = Bmp02LoadPhase.ready;
      if (!_snapshot!.brands.any((brand) => brand.id == _selectedBrandId)) {
        _selectedBrandId = _snapshot!.brands.firstOrNull?.id;
      }
    } catch (error) {
      _snapshot = null;
      _failureKind = _classify(error);
      _phase = Bmp02LoadPhase.failed;
    }
    notifyListeners();
  }

  void updateQuery(String value) {
    if (_query == value) return;
    _query = value;
    notifyListeners();
  }

  void setRoleFilter(String? role) {
    if (_roleFilter == role) return;
    _roleFilter = role;
    notifyListeners();
  }

  void selectBrand(String id) {
    if (_selectedBrandId == id) return;
    if (!(_snapshot?.brands.any((brand) => brand.id == id) ?? false)) return;
    _selectedBrandId = id;
    notifyListeners();
  }

  static Bmp02FailureKind _classify(Object error) {
    final message = error.toString().toLowerCase();
    if (message.contains('http 401') || message.contains('auth_required')) {
      return Bmp02FailureKind.authentication;
    }
    if (message.contains('http 403')) {
      return Bmp02FailureKind.permissionDenied;
    }
    if (isLumenisConnectionError(error) ||
        message.contains('core unavailable') ||
        message.contains('connection timed out')) {
      return Bmp02FailureKind.offline;
    }
    return Bmp02FailureKind.server;
  }
}

extension<T> on List<T> {
  T? get firstOrNull => isEmpty ? null : first;
}
