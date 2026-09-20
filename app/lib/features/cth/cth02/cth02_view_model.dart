import 'package:flutter/foundation.dart';

import '../../../core/lumenis_core_client.dart';
import 'cth02_repository.dart';

enum Cth02LoadPhase { loading, ready, failed }

enum Cth02FailureKind {
  authentication,
  permissionDenied,
  permissionUnavailable,
  offline,
  server,
  invalidResponse,
}

class Cth02ViewModel extends ChangeNotifier {
  Cth02ViewModel({required Cth02Repository repository})
    : _repository = repository;

  final Cth02Repository _repository;

  Cth02LoadPhase phase = Cth02LoadPhase.loading;
  Cth02FailureKind? failureKind;
  Cth02Directory? directory;
  bool _disposed = false;

  Future<void> refresh() async {
    phase = Cth02LoadPhase.loading;
    failureKind = null;
    directory = null;
    _notify();

    try {
      directory = await _repository.loadDirectory();
      phase = Cth02LoadPhase.ready;
    } on LumenisCoreException catch (error) {
      failureKind = _classifyCoreError(error);
      phase = Cth02LoadPhase.failed;
    } on FormatException {
      failureKind = Cth02FailureKind.invalidResponse;
      phase = Cth02LoadPhase.failed;
    } catch (_) {
      failureKind = Cth02FailureKind.server;
      phase = Cth02LoadPhase.failed;
    }

    _notify();
  }

  void _notify() {
    if (!_disposed) notifyListeners();
  }

  static Cth02FailureKind _classifyCoreError(LumenisCoreException error) {
    return switch (error.statusCode) {
      401 => Cth02FailureKind.authentication,
      403 => Cth02FailureKind.permissionDenied,
      503 => Cth02FailureKind.permissionUnavailable,
      _ when error.message.toLowerCase().contains('core unavailable') =>
        Cth02FailureKind.offline,
      _ => Cth02FailureKind.server,
    };
  }

  @override
  void dispose() {
    _disposed = true;
    super.dispose();
  }
}
