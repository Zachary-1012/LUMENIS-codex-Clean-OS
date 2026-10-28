import 'package:flutter/foundation.dart';

import '../../../core/lumenis_core_client.dart';
import 'cth01_repository.dart';

enum Cth01LoadStatus { loading, loaded, blocked, failed }

enum Cth01LoadMessage {
  contextUnavailable,
  pageNotBound,
  loginRequired,
  accessUnavailable,
  connectionUnavailable,
  genericUnavailable,
}

class Cth01ViewModel extends ChangeNotifier {
  Cth01ViewModel(this._repository);

  final Cth01Repository _repository;
  Cth01LoadStatus status = Cth01LoadStatus.loading;
  Cth01ScreenData? data;
  Cth01LoadMessage? message;
  int? selectedSignalIndex;
  bool _disposed = false;
  int _generation = 0;

  Future<void> load() async {
    if (_disposed) return;
    final generation = ++_generation;
    status = Cth01LoadStatus.loading;
    message = null;
    data = null;
    selectedSignalIndex = null;
    _notify();

    try {
      final result = await _repository.load();
      if (_disposed || generation != _generation) return;
      data = result;
      status = Cth01LoadStatus.loaded;
    } on Cth01ContextUnavailable catch (error) {
      if (_disposed || generation != _generation) return;
      status = Cth01LoadStatus.blocked;
      message = switch (error.reason) {
        Cth01BlockReason.contextUnavailable =>
          Cth01LoadMessage.contextUnavailable,
        Cth01BlockReason.pageNotBound => Cth01LoadMessage.pageNotBound,
      };
    } on LumenisCoreException catch (error) {
      if (_disposed || generation != _generation) return;
      status = Cth01LoadStatus.failed;
      message = _messageForCoreError(error);
    } on FormatException {
      if (_disposed || generation != _generation) return;
      status = Cth01LoadStatus.failed;
      message = Cth01LoadMessage.genericUnavailable;
    } catch (_) {
      if (_disposed || generation != _generation) return;
      status = Cth01LoadStatus.failed;
      message = Cth01LoadMessage.genericUnavailable;
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

  static Cth01LoadMessage _messageForCoreError(LumenisCoreException error) {
    return switch (error.statusCode) {
      401 => Cth01LoadMessage.loginRequired,
      403 => Cth01LoadMessage.accessUnavailable,
      null => Cth01LoadMessage.connectionUnavailable,
      _ => Cth01LoadMessage.genericUnavailable,
    };
  }

  @override
  void dispose() {
    _disposed = true;
    _generation++;
    super.dispose();
  }
}
