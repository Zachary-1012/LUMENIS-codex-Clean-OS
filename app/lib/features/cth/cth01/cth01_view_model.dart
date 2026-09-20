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
      message = '运营信息暂不可用，请稍后重试。';
    } catch (_) {
      status = Cth01LoadStatus.failed;
      message = '运营信息暂不可用，请稍后重试。';
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
      return '请登录后查看商业运营信息。';
    }
    if (message.contains('HTTP 403')) {
      return '当前账号暂时无法查看商业运营信息。';
    }
    return '暂时无法连接，请检查网络后重试。';
  }

  @override
  void dispose() {
    _disposed = true;
    super.dispose();
  }
}
