import 'dart:async';

import 'package:flutter/foundation.dart';

import 'read_aloud_backend.dart';
import 'read_aloud_contract.dart';

/// One ephemeral local speech session for the current Flutter surface.
/// Text and voice output are never persisted or sent through the Core API.
class ReadAloudService extends ChangeNotifier {
  ReadAloudService({
    ReadAloudPlatform? platform,
    this.startupTimeout = const Duration(seconds: 8),
  }) : _platform = platform ?? createReadAloudPlatform();

  static final ReadAloudService instance = ReadAloudService();

  final ReadAloudPlatform _platform;
  final Duration startupTimeout;
  ReadAloudRequest? _request;
  ReadAloudState _state = const ReadAloudState();
  ReadAloudAvailability? _availability;
  Timer? _poll;
  Timer? _startupTimer;
  Future<void> _backendTail = Future<void>.value();
  int _generation = 0;
  bool _disposed = false;

  ReadAloudAvailability? get availability => _availability;

  ReadAloudState stateFor({
    required String sessionId,
    required String scopeVersion,
  }) {
    final request = _request;
    if (request?.sessionId != sessionId ||
        request?.scopeVersion != scopeVersion) {
      return const ReadAloudState();
    }
    return _state;
  }

  Future<ReadAloudAvailability> refreshAvailability() async {
    final availability = await _platform.availableLocales();
    _availability = availability;
    if (!_disposed) notifyListeners();
    return availability;
  }

  Future<void> start(ReadAloudRequest request) async {
    final generation = ++_generation;
    _poll?.cancel();
    _poll = null;
    _startupTimer?.cancel();
    _startupTimer = null;
    final normalizedText = request.text.trim();
    if (normalizedText.isEmpty) {
      _request = request;
      final stopped = await _stopPlatform();
      if (!_isCurrent(generation)) return;
      _setState(
        ReadAloudState(
          status: ReadAloudStatus.failed,
          errorCode: stopped
              ? ReadAloudErrorCode.textEmpty
              : ReadAloudErrorCode.playbackFailed,
        ),
      );
      return;
    }
    _request = ReadAloudRequest(
      sessionId: request.sessionId,
      scopeVersion: request.scopeVersion,
      text: normalizedText,
      locale: request.locale,
      rate: request.rate,
    );
    final stopped = await _stopPlatform();
    if (!_isCurrent(generation)) return;
    if (!stopped) {
      _setState(
        ReadAloudState(
          status: ReadAloudStatus.failed,
          errorCode: ReadAloudErrorCode.playbackFailed,
          locale: request.locale,
          rate: request.rate,
        ),
      );
      return;
    }
    late ReadAloudAvailability availability;
    try {
      availability = await refreshAvailability();
    } catch (_) {
      if (!_isCurrent(generation)) return;
      _setState(
        ReadAloudState(
          status: ReadAloudStatus.failed,
          errorCode: ReadAloudErrorCode.playbackFailed,
          locale: request.locale,
          rate: request.rate,
        ),
      );
      return;
    }
    if (!_isCurrent(generation)) return;
    if (!availability.supported) {
      _setState(
        const ReadAloudState(
          status: ReadAloudStatus.unavailable,
          errorCode: ReadAloudErrorCode.platformUnsupported,
        ),
      );
      return;
    }
    if (!availability.localLocales.contains(request.locale.tag)) {
      _setState(
        ReadAloudState(
          status: ReadAloudStatus.unavailable,
          errorCode: ReadAloudErrorCode.voiceUnavailable,
          locale: request.locale,
          rate: request.rate,
        ),
      );
      return;
    }
    late ReadAloudStartResult result;
    try {
      result = await _withBackendLock(() {
        if (!_isCurrent(generation)) {
          return Future.value(
            const ReadAloudStartResult(ReadAloudStatus.stopped),
          );
        }
        return _platform.speak(_request!);
      });
    } catch (_) {
      result = const ReadAloudStartResult(
        ReadAloudStatus.failed,
        ReadAloudErrorCode.playbackFailed,
      );
    }
    if (!_isCurrent(generation)) return;
    final requestAccepted =
        result.status == ReadAloudStatus.starting ||
        result.status == ReadAloudStatus.playing;
    _setState(
      ReadAloudState(
        status: requestAccepted ? ReadAloudStatus.starting : result.status,
        errorCode: result.errorCode,
        locale: request.locale,
        rate: request.rate,
      ),
    );
    if (requestAccepted) {
      _startupTimer = Timer(startupTimeout, () {
        unawaited(_failUnstartedPlayback(generation));
      });
      _poll = Timer.periodic(const Duration(milliseconds: 250), (_) {
        unawaited(_refreshPlayback(generation));
      });
    }
  }

  Future<void> stopSession({
    required String sessionId,
    required String scopeVersion,
  }) async {
    final current = _request;
    if (current?.sessionId != sessionId ||
        current?.scopeVersion != scopeVersion) {
      return;
    }
    ++_generation;
    final generation = _generation;
    _poll?.cancel();
    _poll = null;
    _startupTimer?.cancel();
    _startupTimer = null;
    final stopped = await _stopPlatform();
    if (!_isCurrent(generation)) return;
    _setState(
      ReadAloudState(
        status: stopped ? ReadAloudStatus.stopped : ReadAloudStatus.failed,
        errorCode: stopped ? null : ReadAloudErrorCode.playbackFailed,
        locale: _state.locale,
        rate: _state.rate,
      ),
    );
  }

  Future<void> _refreshPlayback(int generation) async {
    if (!_isCurrent(generation)) return;
    late ReadAloudPlaybackObservation observation;
    try {
      observation = await _platform.observe();
    } catch (_) {
      observation = ReadAloudPlaybackObservation.failed;
    }
    if (!_isCurrent(generation)) return;
    switch (observation) {
      case ReadAloudPlaybackObservation.starting:
        break;
      case ReadAloudPlaybackObservation.playing:
        _startupTimer?.cancel();
        _startupTimer = null;
        if (_state.status != ReadAloudStatus.playing) {
          _setState(_stateWith(ReadAloudStatus.playing));
        }
        break;
      case ReadAloudPlaybackObservation.paused:
        _startupTimer?.cancel();
        _startupTimer = null;
        _setState(_stateWith(ReadAloudStatus.paused));
        break;
      case ReadAloudPlaybackObservation.completed:
        _poll?.cancel();
        _poll = null;
        _startupTimer?.cancel();
        _startupTimer = null;
        _setState(_stateWith(ReadAloudStatus.completed));
        break;
      case ReadAloudPlaybackObservation.failed:
        _poll?.cancel();
        _poll = null;
        _startupTimer?.cancel();
        _startupTimer = null;
        _setState(
          ReadAloudState(
            status: ReadAloudStatus.failed,
            errorCode: ReadAloudErrorCode.playbackFailed,
            locale: _state.locale,
            rate: _state.rate,
          ),
        );
        break;
    }
  }

  Future<void> _failUnstartedPlayback(int generation) async {
    if (!_isCurrent(generation) || _state.status != ReadAloudStatus.starting) {
      return;
    }
    final timeoutGeneration = ++_generation;
    _poll?.cancel();
    _poll = null;
    _startupTimer?.cancel();
    _startupTimer = null;
    await _stopPlatform();
    if (!_isCurrent(timeoutGeneration)) return;
    _setState(
      ReadAloudState(
        status: ReadAloudStatus.failed,
        errorCode: ReadAloudErrorCode.playbackFailed,
        locale: _state.locale,
        rate: _state.rate,
      ),
    );
  }

  ReadAloudState _stateWith(ReadAloudStatus status) =>
      ReadAloudState(status: status, locale: _state.locale, rate: _state.rate);

  bool _isCurrent(int generation) => !_disposed && generation == _generation;

  Future<T> _withBackendLock<T>(Future<T> Function() action) async {
    final previous = _backendTail;
    final done = Completer<void>();
    _backendTail = done.future;
    try {
      await previous;
      return await action();
    } finally {
      done.complete();
    }
  }

  Future<bool> _stopPlatform() async {
    try {
      await _withBackendLock(_platform.stop);
      return true;
    } catch (_) {
      return false;
    }
  }

  void _setState(ReadAloudState state) {
    _state = state;
    if (!_disposed) notifyListeners();
  }

  @override
  void dispose() {
    ++_generation;
    _disposed = true;
    _poll?.cancel();
    _startupTimer?.cancel();
    unawaited(_stopPlatform());
    super.dispose();
  }
}
