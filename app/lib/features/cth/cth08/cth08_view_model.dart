import 'package:flutter/foundation.dart';

import '../../../core/lumenis_core_client.dart';
import 'cth08_repository.dart';

enum Cth08LoadPhase {
  loading,
  ready,
  empty,
  notCollected,
  partial,
  blocked,
  failed,
}

enum Cth08FailureKind {
  contextUnavailable,
  pageBindingUnavailable,
  evidenceBindingUnavailable,
  authentication,
  permissionDenied,
  offline,
  invalidResponse,
  server,
}

class Cth08ViewModel extends ChangeNotifier {
  Cth08ViewModel({required this._repository});

  final Cth08Repository _repository;

  Cth08LoadPhase phase = Cth08LoadPhase.loading;
  Cth08FailureKind? failureKind;
  Cth08WorkspaceData? data;
  String? selectedCaseId;
  bool _disposed = false;

  Future<void> load() async {
    phase = Cth08LoadPhase.loading;
    failureKind = null;
    data = null;
    selectedCaseId = null;
    _notify();

    try {
      data = await _repository.load();
      phase = switch (data!.state) {
        Cth08ContentState.ready => Cth08LoadPhase.ready,
        Cth08ContentState.empty => Cth08LoadPhase.empty,
        Cth08ContentState.notCollected => Cth08LoadPhase.notCollected,
        Cth08ContentState.partial => Cth08LoadPhase.partial,
      };
    } on Cth08BlockedException catch (error) {
      phase = Cth08LoadPhase.blocked;
      failureKind = switch (error.reason) {
        Cth08BlockedReason.contextUnavailable =>
          Cth08FailureKind.contextUnavailable,
        Cth08BlockedReason.pageBindingUnavailable =>
          Cth08FailureKind.pageBindingUnavailable,
        Cth08BlockedReason.evidenceBindingUnavailable =>
          Cth08FailureKind.evidenceBindingUnavailable,
      };
    } on LumenisCoreException catch (error) {
      phase = Cth08LoadPhase.failed;
      failureKind = switch (error.statusCode) {
        401 => Cth08FailureKind.authentication,
        403 => Cth08FailureKind.permissionDenied,
        null => Cth08FailureKind.offline,
        _ => Cth08FailureKind.server,
      };
    } on FormatException {
      phase = Cth08LoadPhase.failed;
      failureKind = Cth08FailureKind.invalidResponse;
    } catch (_) {
      phase = Cth08LoadPhase.failed;
      failureKind = Cth08FailureKind.server;
    }

    _notify();
  }

  void selectCase(String id) {
    if (data == null || !data!.cases.any((item) => item.id == id)) return;
    selectedCaseId = id;
    _notify();
  }

  void clearSelection() {
    selectedCaseId = null;
    _notify();
  }

  Cth08Case? get selectedCase {
    final id = selectedCaseId;
    if (id == null || data == null) return null;
    for (final item in data!.cases) {
      if (item.id == id) return item;
    }
    return null;
  }

  void _notify() {
    if (!_disposed) notifyListeners();
  }

  @override
  void dispose() {
    _disposed = true;
    super.dispose();
  }
}
