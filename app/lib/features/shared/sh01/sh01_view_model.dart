import 'package:flutter/foundation.dart';

import 'sh01_repository.dart';
import 'sh01_snapshot.dart';

enum Sh01LoadPhase { loading, ready, failed }

class Sh01ViewModel extends ChangeNotifier {
  Sh01ViewModel({required this._repository});

  final Sh01Repository _repository;

  Sh01LoadPhase _phase = Sh01LoadPhase.loading;
  Sh01Catalog? _catalog;
  Sh01Capability? _selected;
  String? _error;
  bool _disposed = false;
  int _refreshGeneration = 0;

  Sh01LoadPhase get phase => _phase;
  Sh01Catalog? get catalog => _catalog;
  Sh01Capability? get selected => _selected;
  String? get error => _error;

  Future<void> refresh() async {
    if (_disposed) return;
    final generation = ++_refreshGeneration;
    _phase = Sh01LoadPhase.loading;
    _catalog = null;
    _selected = null;
    _error = null;
    notifyListeners();
    if (_disposed || generation != _refreshGeneration) return;
    try {
      final catalog = await _repository.loadCatalog();
      if (_disposed || generation != _refreshGeneration) return;
      _catalog = catalog;
      _selected = null;
      _phase = Sh01LoadPhase.ready;
    } catch (error) {
      if (_disposed || generation != _refreshGeneration) return;
      _error = _message(error);
      _phase = Sh01LoadPhase.failed;
    }
    notifyListeners();
  }

  void select(Sh01Capability capability) {
    if (_disposed) return;
    _selected = capability;
    notifyListeners();
  }

  @override
  void dispose() {
    _disposed = true;
    _refreshGeneration++;
    super.dispose();
  }

  static String _message(Object error) {
    final text = error.toString();
    if (text.contains('HTTP 401')) return '登录已失效，请重新登录后读取。';
    if (text.contains('HTTP 403')) return '当前账号无权读取共享能力目录。';
    if (text.contains('unavailable') || text.contains('timed out')) {
      return 'Product Core 暂时不可用。';
    }
    return '共享能力目录没有返回可验证的数据。';
  }
}
