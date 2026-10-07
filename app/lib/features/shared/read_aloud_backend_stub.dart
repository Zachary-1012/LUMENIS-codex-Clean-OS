import 'read_aloud_contract.dart';

ReadAloudPlatform createReadAloudPlatform() => _UnsupportedReadAloudPlatform();

class _UnsupportedReadAloudPlatform implements ReadAloudPlatform {
  @override
  Future<ReadAloudAvailability> availableLocales() async =>
      const ReadAloudAvailability(supported: false, localLocales: {});

  @override
  Future<ReadAloudStartResult> speak(ReadAloudRequest request) async =>
      const ReadAloudStartResult(
        ReadAloudStatus.unavailable,
        ReadAloudErrorCode.platformUnsupported,
      );

  @override
  Future<void> stop() async {}

  @override
  Future<ReadAloudPlaybackObservation> observe() async =>
      ReadAloudPlaybackObservation.failed;
}
