import 'package:flutter/foundation.dart';

import '../../../core/lumenis_core_client.dart';
import 'cth09_repository.dart';

enum Cth09LoadPhase {
  loading,
  ready,
  empty,
  notCollected,
  partial,
  blocked,
  failed,
}

enum Cth09FailureKind {
  contextUnavailable,
  pageBindingUnavailable,
  evidenceBindingUnavailable,
  authentication,
  permissionDenied,
  offline,
  invalidResponse,
  server,
}

class Cth09ViewModel extends ChangeNotifier {
  Cth09ViewModel({required this._repository});

  final Cth09Repository _repository;

  Cth09LoadPhase phase = Cth09LoadPhase.loading;
  Cth09FailureKind? failureKind;
  Cth09WorkbenchData? data;
  String? selectedRiskId;
  String? selectedDecisionId;
  bool _disposed = false;

  Future<void> load() async {
    phase = Cth09LoadPhase.loading;
    failureKind = null;
    data = null;
    selectedRiskId = null;
    selectedDecisionId = null;
    _notify();

    try {
      data = await _repository.load();
      phase = switch (data!.state) {
        Cth09ContentState.ready => Cth09LoadPhase.ready,
        Cth09ContentState.empty => Cth09LoadPhase.empty,
        Cth09ContentState.notCollected => Cth09LoadPhase.notCollected,
        Cth09ContentState.partial => Cth09LoadPhase.partial,
      };
    } on Cth09BlockedException catch (error) {
      phase = Cth09LoadPhase.blocked;
      failureKind = switch (error.reason) {
        Cth09BlockedReason.contextUnavailable =>
          Cth09FailureKind.contextUnavailable,
        Cth09BlockedReason.pageBindingUnavailable =>
          Cth09FailureKind.pageBindingUnavailable,
        Cth09BlockedReason.evidenceBindingUnavailable =>
          Cth09FailureKind.evidenceBindingUnavailable,
      };
    } on LumenisCoreException catch (error) {
      phase = Cth09LoadPhase.failed;
      failureKind = switch (error.statusCode) {
        401 => Cth09FailureKind.authentication,
        403 => Cth09FailureKind.permissionDenied,
        null => Cth09FailureKind.offline,
        _ => Cth09FailureKind.server,
      };
    } on FormatException {
      phase = Cth09LoadPhase.failed;
      failureKind = Cth09FailureKind.invalidResponse;
    } catch (_) {
      phase = Cth09LoadPhase.failed;
      failureKind = Cth09FailureKind.server;
    }

    _notify();
  }

  void selectRisk(String id) {
    if (data == null || !data!.risks.any((item) => item.id == id)) return;
    selectedRiskId = id;
    _notify();
  }

  void selectDecision(String id) {
    if (data == null || !data!.decisions.any((item) => item.id == id)) return;
    selectedDecisionId = id;
    _notify();
  }

  void clearSelection() {
    selectedRiskId = null;
    selectedDecisionId = null;
    _notify();
  }

  Cth09Risk? get selectedRisk {
    final id = selectedRiskId;
    if (id == null || data == null) return null;
    for (final item in data!.risks) {
      if (item.id == id) return item;
    }
    return null;
  }

  Cth09Decision? get selectedDecision {
    final id = selectedDecisionId;
    if (id == null || data == null) return null;
    for (final item in data!.decisions) {
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
