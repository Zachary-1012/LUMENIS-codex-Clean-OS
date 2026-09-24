import 'package:flutter/foundation.dart';

import '../../../core/lumenis_core_client.dart';
import 'cth04_repository.dart';

enum Cth04LoadPhase { loading, ready, unavailable }

enum Cth04FailureKind {
  contextUnavailable,
  pageNotBound,
  focusNotBound,
  authentication,
  permissionDenied,
  offline,
  server,
}

class Cth04ViewModel extends ChangeNotifier {
  Cth04ViewModel({required this._repository});

  final Cth04Repository _repository;

  Cth04LoadPhase phase = Cth04LoadPhase.loading;
  Cth04FailureKind? failureKind;
  Cth04ScreenData? data;
  int? selectedEventIndex;
  bool _disposed = false;

  Future<void> refresh() async {
    phase = Cth04LoadPhase.loading;
    failureKind = null;
    data = null;
    selectedEventIndex = null;
    _notify();

    try {
      data = await _repository.load();
      phase = Cth04LoadPhase.ready;
    } on Cth04ContextUnavailable catch (error) {
      failureKind = switch (error.reason) {
        Cth04BlockReason.contextUnavailable =>
          Cth04FailureKind.contextUnavailable,
        Cth04BlockReason.pageNotBound => Cth04FailureKind.pageNotBound,
        Cth04BlockReason.focusNotBound => Cth04FailureKind.focusNotBound,
      };
      phase = Cth04LoadPhase.unavailable;
    } on LumenisCoreException catch (error) {
      failureKind = _classify(error);
      phase = Cth04LoadPhase.unavailable;
    } on FormatException {
      failureKind = Cth04FailureKind.server;
      phase = Cth04LoadPhase.unavailable;
    } catch (_) {
      failureKind = Cth04FailureKind.server;
      phase = Cth04LoadPhase.unavailable;
    }
    _notify();
  }

  void selectEvent(int index) {
    if (data == null || index < 0 || index >= data!.events.length) return;
    selectedEventIndex = index;
    _notify();
  }

  void returnToTimeline() {
    selectedEventIndex = null;
    _notify();
  }

  void _notify() {
    if (!_disposed) notifyListeners();
  }

  static Cth04FailureKind _classify(LumenisCoreException error) {
    return switch (error.statusCode) {
      401 => Cth04FailureKind.authentication,
      403 => Cth04FailureKind.permissionDenied,
      null => Cth04FailureKind.offline,
      _ => Cth04FailureKind.server,
    };
  }

  @override
  void dispose() {
    _disposed = true;
    super.dispose();
  }
}
