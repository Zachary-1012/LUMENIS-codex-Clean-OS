import 'package:flutter/foundation.dart';

import '../../../core/lumenis_core_client.dart';
import 'cth01_repository.dart';

enum Cth01LoadStatus { loading, loaded, blocked, failed }

class Cth01ViewModel extends ChangeNotifier {
  Cth01ViewModel(this._repository);

  final Cth01Repository _repository;
  Cth01LoadStatus status = Cth01LoadStatus.loading;
  Cth01ScreenData? data;
  String? message;
  int? selectedSignalIndex;
  bool _disposed = false;

  Future<void> load() async {
    status = Cth01LoadStatus.loading;
    message = null;
    data = null;
    selectedSignalIndex = null;
    _notify();

    try {
      data = await _repository.load();
      status = Cth01LoadStatus.loaded;
    } on Cth01ContextUnavailable catch (error) {
      status = Cth01LoadStatus.blocked;
      message = error.message;
    } on LumenisCoreException catch (error) {
      status = Cth01LoadStatus.failed;
      message = _messageForCoreError(error.message);
    } on FormatException {
      status = Cth01LoadStatus.failed;
      message = 'LUMENIS Core 返回了当前页面无法读取的响应。';
    } catch (_) {
      status = Cth01LoadStatus.failed;
      message = '暂时无法读取 LUMENIS Core 的 CTH-01 数据。';
    }

    _notify();
  }

  void selectSignal(int index) {
    if (data == null || index < 0 || index >= data!.signals.length) return;
    selectedSignalIndex = index;
    _notify();
  }

  void returnToSignals() {
    selectedSignalIndex = null;
    _notify();
  }

  void _notify() {
    if (!_disposed) notifyListeners();
  }

  static String _messageForCoreError(String message) {
    if (message.contains('HTTP 401')) {
      return 'LUMENIS Core 要求完成身份验证后才能读取 CTH 数据。';
    }
    if (message.contains('HTTP 403')) {
      return 'LUMENIS Core 拒绝了本次 CTH 数据读取请求。';
    }
    return '无法连接 LUMENIS Core，请检查连接后重试。';
  }

  @override
  void dispose() {
    _disposed = true;
    super.dispose();
  }
}
