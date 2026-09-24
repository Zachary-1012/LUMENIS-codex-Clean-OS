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

  Sh01LoadPhase get phase => _phase;
  Sh01Catalog? get catalog => _catalog;
  Sh01Capability? get selected => _selected;
  String? get error => _error;

  Future<void> refresh() async {
    _phase = Sh01LoadPhase.loading;
    _catalog = null;
    _selected = null;
    _error = null;
    notifyListeners();
    try {
      _catalog = await _repository.loadCatalog();
      _selected = null;
      _phase = Sh01LoadPhase.ready;
    } catch (error) {
      _error = _message(error);
      _phase = Sh01LoadPhase.failed;
    }
    notifyListeners();
  }

  void select(Sh01Capability capability) {
    _selected = capability;
    notifyListeners();
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
