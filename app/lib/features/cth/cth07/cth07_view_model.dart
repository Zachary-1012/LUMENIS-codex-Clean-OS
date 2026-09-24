import 'package:flutter/foundation.dart';

import '../../../core/lumenis_core_client.dart';
import 'cth07_repository.dart';

enum Cth07LoadPhase { loading, ready, unavailable }

enum Cth07FailureKind {
  contextUnavailable,
  pageNotBound,
  focusNotBound,
  authentication,
  permissionDenied,
  offline,
  server,
}

class Cth07ViewModel extends ChangeNotifier {
  Cth07ViewModel({required this._repository});

  final Cth07Repository _repository;

  Cth07LoadPhase phase = Cth07LoadPhase.loading;
  Cth07FailureKind? failureKind;
  Cth07ScreenData? data;
  int selectedSeriesIndex = 0;
  bool _disposed = false;

  Future<void> refresh() async {
    phase = Cth07LoadPhase.loading;
    failureKind = null;
    data = null;
    selectedSeriesIndex = 0;
    _notify();
    try {
      data = await _repository.load();
      phase = Cth07LoadPhase.ready;
    } on Cth07ContextUnavailable catch (error) {
      failureKind = switch (error.reason) {
        Cth07BlockReason.contextUnavailable =>
          Cth07FailureKind.contextUnavailable,
        Cth07BlockReason.pageNotBound => Cth07FailureKind.pageNotBound,
        Cth07BlockReason.focusNotBound => Cth07FailureKind.focusNotBound,
      };
      phase = Cth07LoadPhase.unavailable;
    } on LumenisCoreException catch (error) {
      failureKind = _classify(error);
      phase = Cth07LoadPhase.unavailable;
    } on FormatException {
      failureKind = Cth07FailureKind.server;
      phase = Cth07LoadPhase.unavailable;
    } catch (_) {
      failureKind = Cth07FailureKind.server;
      phase = Cth07LoadPhase.unavailable;
    }
    _notify();
  }

  void selectSeries(int index) {
    if (data == null || index < 0 || index >= data!.series.length) return;
    selectedSeriesIndex = index;
    _notify();
  }

  Cth07Series? get selectedSeries {
    final series = data?.series ?? const <Cth07Series>[];
    return selectedSeriesIndex < series.length
        ? series[selectedSeriesIndex]
        : null;
  }

  void _notify() {
    if (!_disposed) notifyListeners();
  }

  static Cth07FailureKind _classify(LumenisCoreException error) =>
      switch (error.statusCode) {
        401 => Cth07FailureKind.authentication,
        403 => Cth07FailureKind.permissionDenied,
        null => Cth07FailureKind.offline,
        _ => Cth07FailureKind.server,
      };

  @override
  void dispose() {
    _disposed = true;
    super.dispose();
  }
}
