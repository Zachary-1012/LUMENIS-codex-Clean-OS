import 'package:flutter/foundation.dart';

import '../../../core/lumenis_core_client.dart';
import 'cth05_repository.dart';

enum Cth05LoadPhase { loading, ready, unavailable }

enum Cth05FailureKind {
  contextUnavailable,
  pageNotBound,
  focusNotBound,
  authentication,
  permissionDenied,
  offline,
  server,
}

class Cth05ViewModel extends ChangeNotifier {
  Cth05ViewModel({required this._repository});

  final Cth05Repository _repository;

  Cth05LoadPhase phase = Cth05LoadPhase.loading;
  Cth05FailureKind? failureKind;
  Cth05ScreenData? data;
  int? selectedDayIndex;
  bool listMode = false;
  bool _disposed = false;

  Future<void> refresh() async {
    phase = Cth05LoadPhase.loading;
    failureKind = null;
    data = null;
    selectedDayIndex = null;
    _notify();
    try {
      data = await _repository.load();
      phase = Cth05LoadPhase.ready;
    } on Cth05ContextUnavailable catch (error) {
      failureKind = switch (error.reason) {
        Cth05BlockReason.contextUnavailable =>
          Cth05FailureKind.contextUnavailable,
        Cth05BlockReason.pageNotBound => Cth05FailureKind.pageNotBound,
        Cth05BlockReason.focusNotBound => Cth05FailureKind.focusNotBound,
      };
      phase = Cth05LoadPhase.unavailable;
    } on LumenisCoreException catch (error) {
      failureKind = _classify(error);
      phase = Cth05LoadPhase.unavailable;
    } on FormatException {
      failureKind = Cth05FailureKind.server;
      phase = Cth05LoadPhase.unavailable;
    } catch (_) {
      failureKind = Cth05FailureKind.server;
      phase = Cth05LoadPhase.unavailable;
    }
    _notify();
  }

  void selectDay(int index) {
    if (data == null || index < 0 || index >= data!.days.length) return;
    selectedDayIndex = index;
    _notify();
  }

  void toggleListMode() {
    listMode = !listMode;
    _notify();
  }

  void _notify() {
    if (!_disposed) notifyListeners();
  }

  static Cth05FailureKind _classify(LumenisCoreException error) =>
      switch (error.statusCode) {
        401 => Cth05FailureKind.authentication,
        403 => Cth05FailureKind.permissionDenied,
        null => Cth05FailureKind.offline,
        _ => Cth05FailureKind.server,
      };

  @override
  void dispose() {
    _disposed = true;
    super.dispose();
  }
}
