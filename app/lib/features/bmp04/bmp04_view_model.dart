import 'dart:math';
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
  int _generation = 0;
  bool classificationBusy = false;
  Bmp04FailureKind? classificationFailure;
  bool classificationOutcomeUnknown = false;
  bool _requiresRefresh = false;
  String selectedCategory = 'brand_event';
  Bmp04ClassificationDraft? _draft;
  String? _resource;

  bool get canClassify => !_disposed && _phase == Bmp04LoadPhase.ready && _repository is Bmp04ClassificationRepository &&
      _snapshot?.scopeReady == true && _snapshot?.focus.isFocused == true &&
      _snapshot?.classificationState != 'UNAVAILABLE' && !classificationBusy && !_requiresRefresh;

  void selectCategory(String category) {
    if (_disposed || !bmp04Categories.contains(category)) return;
    selectedCategory = category;
    notifyListeners();
  }

  Future<bool> previewClassification(int eventId, String category) async {
    if (!canClassify || !bmp04Categories.contains(category) ||
        !(_snapshot?.curatedEvents.any((event) => event.id == eventId) ?? false)) return false;
    final original = _snapshot!;
    final displayedEvent = original.curatedEvents.firstWhere((event) => event.id == eventId);
    final generation = ++_generation;
    final random = Random.secure();
    final draft = Bmp04ClassificationDraft(
      subjectId: _snapshot!.focus.subjectId!, eventId: eventId, category: category,
      requestId: List.generate(24, (_) => random.nextInt(256).toRadixString(16).padLeft(2, '0')).join(),
    );
    _draft = null;
    _resource = null;
    classificationBusy = true;
    classificationFailure = null;
    classificationOutcomeUnknown = false;
    notifyListeners();
    try {
      final resource = await (_repository as Bmp04ClassificationRepository).previewClassification(draft);
      if (_disposed || generation != _generation) return false;
      // The preview binds the server's current source version. Read it back
      // before showing confirmation so an earlier screen cannot approve an
      // unseen revision that changed between GET and preview.
      final current = await _repository.load();
      if (_disposed || generation != _generation) return false;
      final unchangedEvent = current.curatedEvents.any((event) =>
          event.id == displayedEvent.id &&
          event.evidenceReference == displayedEvent.evidenceReference &&
          event.title == displayedEvent.title);
      if (!current.scopeReady || !current.focus.isFocused ||
          current.focus.subjectId != original.focus.subjectId ||
          current.focus.brandFocusId != original.focus.brandFocusId ||
          current.classificationState == 'UNAVAILABLE' || !unchangedEvent) {
        _requiresRefresh = true;
        throw const FormatException('Displayed classification source changed.');
      }
      _draft = draft;
      _resource = resource;
      return true;
    } catch (error) {
      if (!_disposed && generation == _generation) classificationFailure = _classify(error);
      return false;
    } finally {
      if (!_disposed && generation == _generation) {
        classificationBusy = false;
        notifyListeners();
      }
    }
  }

  void cancelClassification() {
    if (_disposed || classificationBusy) return;
    _generation++;
    _draft = null;
    _resource = null;
  }

  Future<void> confirmClassification() async {
    final draft = _draft;
    final resource = _resource;
    if (!canClassify || draft == null || resource == null) return;
    final generation = ++_generation;
    classificationBusy = true;
    classificationFailure = null;
    notifyListeners();
    try {
      await (_repository as Bmp04ClassificationRepository).confirmClassification(draft, resource);
      if (_disposed || generation != _generation) return;
      _draft = null;
      _resource = null;
      classificationBusy = false;
      await refresh();
    } catch (error) {
      if (_disposed || generation != _generation) return;
      classificationFailure = _classify(error);
      _requiresRefresh = true;
      classificationOutcomeUnknown = classificationFailure == Bmp04FailureKind.offline ||
          classificationFailure == Bmp04FailureKind.server;
      // Never automatically replay a possibly committed write. Refresh then
      // obtain a new exact preview before another explicit human decision.
      _draft = null;
      _resource = null;
      classificationBusy = false;
      notifyListeners();
    }
  }


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
    if (_disposed || classificationBusy) return;
    final generation = ++_generation;
    _draft = null;
    _resource = null;
    _phase = Bmp04LoadPhase.loading;
    _failureKind = null;
    notifyListeners();
    if (_disposed) return;
    try {
      final snapshot = await _repository.load();
      if (_disposed || generation != _generation) return;
      _snapshot = snapshot;
      _requiresRefresh = false;
      classificationFailure = null;
      classificationOutcomeUnknown = false;
      _phase = Bmp04LoadPhase.ready;
      if (!_snapshot!.channels.any(
        (channel) => channel.id == _selectedChannelId,
      )) {
        _selectedChannelId = _snapshot!.channels.isEmpty
            ? null
            : _snapshot!.channels.first.id;
      }
    } catch (error) {
      if (_disposed || generation != _generation) return;
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
