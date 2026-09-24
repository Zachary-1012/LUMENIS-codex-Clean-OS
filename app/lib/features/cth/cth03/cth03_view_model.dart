import 'package:flutter/foundation.dart';

import '../../../core/lumenis_core_client.dart';
import 'cth03_repository.dart';

enum Cth03LoadPhase { loading, ready, unavailable }

enum Cth03FailureKind {
  contextUnavailable,
  pageNotBound,
  focusNotBound,
  authentication,
  permissionDenied,
  offline,
  server,
}

class Cth03ViewModel extends ChangeNotifier {
  Cth03ViewModel({required this._repository});

  final Cth03Repository _repository;

  Cth03LoadPhase phase = Cth03LoadPhase.loading;
  Cth03FailureKind? failureKind;
  Cth03ScreenData? data;
  String? selectedChannel;
  bool _disposed = false;

  Future<void> refresh() async {
    phase = Cth03LoadPhase.loading;
    failureKind = null;
    data = null;
    selectedChannel = null;
    _notify();

    try {
      data = await _repository.load();
      phase = Cth03LoadPhase.ready;
    } on Cth03ContextUnavailable catch (error) {
      failureKind = switch (error.reason) {
        Cth03BlockReason.contextUnavailable =>
          Cth03FailureKind.contextUnavailable,
        Cth03BlockReason.pageNotBound => Cth03FailureKind.pageNotBound,
        Cth03BlockReason.focusNotBound => Cth03FailureKind.focusNotBound,
      };
      phase = Cth03LoadPhase.unavailable;
    } on LumenisCoreException catch (error) {
      failureKind = _classify(error);
      phase = Cth03LoadPhase.unavailable;
    } on FormatException {
      failureKind = Cth03FailureKind.server;
      phase = Cth03LoadPhase.unavailable;
    } catch (_) {
      failureKind = Cth03FailureKind.server;
      phase = Cth03LoadPhase.unavailable;
    }

    _notify();
  }

  void chooseChannel(String? channel) {
    selectedChannel = channel;
    _notify();
  }

  List<Cth03Record> visibleRecords() {
    final records = data?.records ?? const <Cth03Record>[];
    if (selectedChannel == null) return records;
    return records
        .where((record) => record.channel == selectedChannel)
        .toList(growable: false);
  }

  void _notify() {
    if (!_disposed) notifyListeners();
  }

  static Cth03FailureKind _classify(LumenisCoreException error) {
    return switch (error.statusCode) {
      401 => Cth03FailureKind.authentication,
      403 => Cth03FailureKind.permissionDenied,
      null => Cth03FailureKind.offline,
      _ => Cth03FailureKind.server,
    };
  }

  @override
  void dispose() {
    _disposed = true;
    super.dispose();
  }
}
