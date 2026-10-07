import 'package:flutter/services.dart';

import 'read_aloud_contract.dart';

const _channel = MethodChannel('lumenis/read_aloud');

ReadAloudPlatform createReadAloudPlatform() => _NativeReadAloudPlatform();

class _NativeReadAloudPlatform implements ReadAloudPlatform {
  @override
  Future<ReadAloudAvailability> availableLocales() async {
    try {
      final result = await _channel.invokeMapMethod<String, Object?>(
        'availableLocales',
      );
      return ReadAloudAvailability(
        supported: result?['supported'] == true,
        localLocales: _localeSet(result?['localLocales']),
      );
    } on MissingPluginException {
      return const ReadAloudAvailability(supported: false, localLocales: {});
    } on PlatformException {
      return const ReadAloudAvailability(supported: false, localLocales: {});
    }
  }

  @override
  Future<ReadAloudStartResult> speak(ReadAloudRequest request) async {
    try {
      final result = await _channel
          .invokeMapMethod<String, Object?>('speak', <String, Object?>{
            'text': request.text,
            'locale': request.locale.tag,
            'rate': request.rate.multiplier,
          });
      if (result?['status'] == 'PLAYING' || result?['status'] == 'STARTING') {
        // `speak` confirms that the native queue accepted the request. Only
        // `observe` can confirm that audible playback has actually started.
        return const ReadAloudStartResult(ReadAloudStatus.starting);
      }
      if (result?['status'] == 'UNAVAILABLE') {
        return const ReadAloudStartResult(
          ReadAloudStatus.unavailable,
          ReadAloudErrorCode.voiceUnavailable,
        );
      }
      return const ReadAloudStartResult(
        ReadAloudStatus.failed,
        ReadAloudErrorCode.playbackFailed,
      );
    } on MissingPluginException {
      return const ReadAloudStartResult(
        ReadAloudStatus.unavailable,
        ReadAloudErrorCode.platformUnsupported,
      );
    } on PlatformException {
      return const ReadAloudStartResult(
        ReadAloudStatus.failed,
        ReadAloudErrorCode.playbackFailed,
      );
    }
  }

  @override
  Future<void> stop() async {
    try {
      await _channel.invokeMethod<void>('stop');
    } on MissingPluginException {
      // Unsupported IO targets have no native playback session to stop.
    }
  }

  @override
  Future<ReadAloudPlaybackObservation> observe() async {
    try {
      final result = await _channel.invokeMapMethod<String, Object?>('observe');
      return switch (result?['status']) {
        'PLAYING' => ReadAloudPlaybackObservation.playing,
        'PAUSED' => ReadAloudPlaybackObservation.paused,
        'COMPLETED' => ReadAloudPlaybackObservation.completed,
        'STARTING' => ReadAloudPlaybackObservation.starting,
        _ => ReadAloudPlaybackObservation.failed,
      };
    } on MissingPluginException {
      return ReadAloudPlaybackObservation.failed;
    } on PlatformException {
      return ReadAloudPlaybackObservation.failed;
    }
  }

  Set<String> _localeSet(Object? value) {
    if (value is! Iterable) return const {};
    return value.whereType<String>().toSet();
  }
}
