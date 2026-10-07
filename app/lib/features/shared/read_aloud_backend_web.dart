import 'dart:async';
import 'dart:js_interop';

import 'package:web/web.dart' as web;

import 'read_aloud_contract.dart';

ReadAloudPlatform createReadAloudPlatform() => _WebReadAloudPlatform();

class _WebReadAloudPlatform implements ReadAloudPlatform {
  web.SpeechSynthesisUtterance? _utterance;
  ReadAloudPlaybackObservation _status = ReadAloudPlaybackObservation.failed;
  bool _started = false;

  @override
  Future<ReadAloudAvailability> availableLocales() async {
    late List<web.SpeechSynthesisVoice> voices;
    try {
      voices = web.window.speechSynthesis.getVoices().toDart;
    } catch (_) {
      return const ReadAloudAvailability(supported: false, localLocales: {});
    }
    if (voices.isEmpty) {
      // Browsers may populate the system voice list asynchronously. Wait only
      // for the local list; no remote voice or network fetch is requested.
      await Future<void>.delayed(const Duration(milliseconds: 250));
      try {
        voices = web.window.speechSynthesis.getVoices().toDart;
      } catch (_) {
        return const ReadAloudAvailability(supported: false, localLocales: {});
      }
    }
    final localLocales = voices
        .where((voice) => voice.localService)
        .map((voice) => _canonicalLocale(voice.lang))
        .whereType<String>()
        .toSet();
    return ReadAloudAvailability(supported: true, localLocales: localLocales);
  }

  @override
  Future<ReadAloudStartResult> speak(ReadAloudRequest request) async {
    final availability = await availableLocales();
    if (!availability.supported) {
      return const ReadAloudStartResult(
        ReadAloudStatus.unavailable,
        ReadAloudErrorCode.platformUnsupported,
      );
    }
    web.SpeechSynthesisVoice? voice;
    for (final candidate in web.window.speechSynthesis.getVoices().toDart) {
      if (candidate.localService &&
          _canonicalLocale(candidate.lang) == request.locale.tag) {
        voice = candidate;
        break;
      }
    }
    if (voice == null) {
      return const ReadAloudStartResult(
        ReadAloudStatus.unavailable,
        ReadAloudErrorCode.voiceUnavailable,
      );
    }
    await stop();
    final utterance = web.SpeechSynthesisUtterance(request.text);
    utterance.lang = request.locale.tag;
    utterance.voice = voice;
    utterance.rate = request.rate.multiplier;
    utterance.onstart = ((web.Event _) {
      if (!identical(_utterance, utterance)) return;
      _started = true;
      _status = ReadAloudPlaybackObservation.playing;
    }).toJS;
    utterance.onend = ((web.Event _) {
      if (!identical(_utterance, utterance)) return;
      _status = ReadAloudPlaybackObservation.completed;
    }).toJS;
    utterance.onerror = ((web.SpeechSynthesisErrorEvent _) {
      if (!identical(_utterance, utterance)) return;
      _status = ReadAloudPlaybackObservation.failed;
    }).toJS;
    _utterance = utterance;
    _started = false;
    _status = ReadAloudPlaybackObservation.starting;
    web.window.speechSynthesis.speak(utterance);
    return const ReadAloudStartResult(ReadAloudStatus.starting);
  }

  @override
  Future<void> stop() async {
    web.window.speechSynthesis.cancel();
    _utterance = null;
    _started = false;
    _status = ReadAloudPlaybackObservation.failed;
  }

  @override
  Future<ReadAloudPlaybackObservation> observe() async {
    if (_utterance == null) return _status;
    if (_started && web.window.speechSynthesis.paused) {
      return ReadAloudPlaybackObservation.paused;
    }
    return _status;
  }

  String? _canonicalLocale(String raw) {
    final normalized = raw.replaceAll('_', '-').toLowerCase();
    return switch (normalized) {
      'zh-cn' => ReadAloudLocale.zhCn.tag,
      'en-us' => ReadAloudLocale.enUs.tag,
      'ko-kr' => ReadAloudLocale.koKr.tag,
      _ => null,
    };
  }
}
