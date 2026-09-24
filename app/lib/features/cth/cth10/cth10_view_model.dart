import 'package:flutter/foundation.dart';

import '../../../core/lumenis_core_client.dart';
import 'cth10_repository.dart';

enum Cth10LoadPhase {
  loading,
  ready,
  empty,
  notCollected,
  partial,
  blocked,
  failed,
}

enum Cth10FailureKind {
  contextUnavailable,
  pageBindingUnavailable,
  evidenceBindingUnavailable,
  reportScopeUnavailable,
  authentication,
  permissionDenied,
  offline,
  invalidResponse,
  server,
}

class Cth10ViewModel extends ChangeNotifier {
  Cth10ViewModel({required this._repository});

  final Cth10Repository _repository;

  Cth10LoadPhase phase = Cth10LoadPhase.loading;
  Cth10FailureKind? failureKind;
  Cth10WorkspaceData? data;
  String? selectedReportId;
  bool _disposed = false;

  Future<void> load() async {
    phase = Cth10LoadPhase.loading;
    failureKind = null;
    data = null;
    selectedReportId = null;
    _notify();

    try {
      data = await _repository.load();
      phase = switch (data!.state) {
        Cth10ContentState.ready => Cth10LoadPhase.ready,
        Cth10ContentState.empty => Cth10LoadPhase.empty,
        Cth10ContentState.notCollected => Cth10LoadPhase.notCollected,
        Cth10ContentState.partial => Cth10LoadPhase.partial,
      };
    } on Cth10BlockedException catch (error) {
      phase = Cth10LoadPhase.blocked;
      failureKind = switch (error.reason) {
        Cth10BlockedReason.contextUnavailable =>
          Cth10FailureKind.contextUnavailable,
        Cth10BlockedReason.pageBindingUnavailable =>
          Cth10FailureKind.pageBindingUnavailable,
        Cth10BlockedReason.evidenceBindingUnavailable =>
          Cth10FailureKind.evidenceBindingUnavailable,
        Cth10BlockedReason.reportScopeUnavailable =>
          Cth10FailureKind.reportScopeUnavailable,
      };
    } on LumenisCoreException catch (error) {
      phase = Cth10LoadPhase.failed;
      failureKind = switch (error.statusCode) {
        401 => Cth10FailureKind.authentication,
        403 => Cth10FailureKind.permissionDenied,
        null => Cth10FailureKind.offline,
        _ => Cth10FailureKind.server,
      };
    } on FormatException {
      phase = Cth10LoadPhase.failed;
      failureKind = Cth10FailureKind.invalidResponse;
    } catch (_) {
      phase = Cth10LoadPhase.failed;
      failureKind = Cth10FailureKind.server;
    }

    _notify();
  }

  void selectReport(String id) {
    if (data == null || !data!.reports.any((item) => item.id == id)) return;
    selectedReportId = id;
    _notify();
  }

  void clearSelection() {
    selectedReportId = null;
    _notify();
  }

  Cth10Report? get selectedReport {
    final id = selectedReportId;
    if (id == null || data == null) return null;
    for (final item in data!.reports) {
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
