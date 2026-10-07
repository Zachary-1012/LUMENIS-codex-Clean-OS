import 'package:flutter/foundation.dart';

enum ReadAloudStatus {
  ready,
  starting,
  playing,
  paused,
  stopped,
  completed,
  unavailable,
  failed,
}

enum ReadAloudErrorCode {
  voiceUnavailable,
  localeUnavailable,
  platformUnsupported,
  playbackFailed,
  textEmpty,
  sessionSuperseded,
  contextChanged,
}

enum ReadAloudLocale {
  zhCn('zh-CN'),
  enUs('en-US'),
  koKr('ko-KR');

  const ReadAloudLocale(this.tag);

  final String tag;

  static ReadAloudLocale? fromPlatformTag(String? tag) {
    final normalized = tag?.replaceAll('_', '-').toLowerCase();
    return switch (normalized) {
      'zh-cn' => ReadAloudLocale.zhCn,
      'en-us' => ReadAloudLocale.enUs,
      'ko-kr' => ReadAloudLocale.koKr,
      _ => null,
    };
  }
}

enum ReadAloudRate {
  slow(0.75),
  normal(1.0),
  fast(1.25);

  const ReadAloudRate(this.multiplier);

  final double multiplier;
}

@immutable
class ReadAloudRequest {
  const ReadAloudRequest({
    required this.sessionId,
    required this.scopeVersion,
    required this.text,
    required this.locale,
    required this.rate,
  });

  final String sessionId;
  final String scopeVersion;
  final String text;
  final ReadAloudLocale locale;
  final ReadAloudRate rate;
}

@immutable
class ReadAloudState {
  const ReadAloudState({
    this.status = ReadAloudStatus.ready,
    this.errorCode,
    this.locale = ReadAloudLocale.zhCn,
    this.rate = ReadAloudRate.normal,
  });

  final ReadAloudStatus status;
  final ReadAloudErrorCode? errorCode;
  final ReadAloudLocale locale;
  final ReadAloudRate rate;
}

@immutable
class ReadAloudAvailability {
  const ReadAloudAvailability({
    required this.supported,
    required this.localLocales,
  });

  final bool supported;
  final Set<String> localLocales;
}

@immutable
class ReadAloudStartResult {
  /// Result of submitting text to the local platform voice.
  ///
  /// A `starting` or `playing` result only confirms that the request was
  /// accepted; the service waits for [ReadAloudPlatform.observe] to report
  /// actual playback before exposing the `playing` state to the UI.
  const ReadAloudStartResult(this.status, [this.errorCode]);

  final ReadAloudStatus status;
  final ReadAloudErrorCode? errorCode;
}

enum ReadAloudPlaybackObservation {
  starting,
  playing,
  paused,
  completed,
  failed,
}

abstract interface class ReadAloudPlatform {
  Future<ReadAloudAvailability> availableLocales();

  Future<ReadAloudStartResult> speak(ReadAloudRequest request);

  Future<void> stop();

  Future<ReadAloudPlaybackObservation> observe();
}
