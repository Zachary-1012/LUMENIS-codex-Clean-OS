import 'package:flutter/foundation.dart';

import '../../core/transport/lumenis_http_transport.dart';
import 'bmp04_repository.dart';
import 'bmp04_snapshot.dart';

enum Bmp04LoadPhase { loading, ready, failed }

enum Bmp04FailureKind { authentication, permissionDenied, offline, server }

class Bmp04ViewModel extends ChangeNotifier {
  Bmp04ViewModel({required this._repository});

  final Bmp04Repository _repository;
  bool _disposed = false;

  Bmp04LoadPhase _phase = Bmp04LoadPhase.loading;
  Bmp04FailureKind? _failureKind;
  Bmp04Snapshot? _snapshot;
  String? _selectedChannelId;

  Bmp04LoadPhase get phase => _phase;
  Bmp04FailureKind? get failureKind => _failureKind;
  Bmp04Snapshot? get snapshot => _snapshot;
  String? get selectedChannelId => _selectedChannelId;

  Bmp04Channel? get selectedChannel {
    final channels = _snapshot?.channels ?? const <Bmp04Channel>[];
    for (final channel in channels) {
      if (channel.id == _selectedChannelId) return channel;
    }
    return channels.isEmpty ? null : channels.first;
  }

  Future<void> refresh() async {
    if (_disposed) return;
    _phase = Bmp04LoadPhase.loading;
    _failureKind = null;
    notifyListeners();
    if (_disposed) return;
    try {
      final snapshot = await _repository.load();
      if (_disposed) return;
      _snapshot = snapshot;
      _phase = Bmp04LoadPhase.ready;
      if (!_snapshot!.channels.any(
        (channel) => channel.id == _selectedChannelId,
      )) {
        _selectedChannelId = _snapshot!.channels.isEmpty
            ? null
            : _snapshot!.channels.first.id;
      }
    } catch (error) {
      if (_disposed) return;
      _snapshot = null;
      _failureKind = _classify(error);
      _phase = Bmp04LoadPhase.failed;
    }
    if (_disposed) return;
    notifyListeners();
  }

  void selectChannel(String id) {
    if (_selectedChannelId == id) return;
    if (!(_snapshot?.channels.any((channel) => channel.id == id) ?? false)) {
      return;
    }
    _selectedChannelId = id;
    notifyListeners();
  }

  static Bmp04FailureKind _classify(Object error) {
    final message = error.toString().toLowerCase();
    if (message.contains('http 401') || message.contains('auth_required')) {
      return Bmp04FailureKind.authentication;
    }
    if (message.contains('http 403')) {
      return Bmp04FailureKind.permissionDenied;
    }
    if (isLumenisConnectionError(error) ||
        message.contains('core unavailable') ||
        message.contains('connection timed out')) {
      return Bmp04FailureKind.offline;
    }
    return Bmp04FailureKind.server;
  }

  @override
  void dispose() {
    _disposed = true;
    super.dispose();
  }
}
