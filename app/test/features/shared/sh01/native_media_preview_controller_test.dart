import 'dart:async';
import 'dart:typed_data';

import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/features/shared/sh01/native_media_cache.dart';
import 'package:lumenis_app/features/shared/sh01/native_media_player.dart';
import 'package:lumenis_app/features/shared/sh01/native_media_preview_controller.dart';
import 'package:video_player/video_player.dart';

const _duration = Duration(seconds: 30);
const _inputBytes = <int>[1, 2, 3, 4];

VideoPlayerValue _initializedValue({
  Duration position = Duration.zero,
  bool isPlaying = false,
  bool isCompleted = false,
}) => VideoPlayerValue(
  duration: _duration,
  position: position,
  isInitialized: true,
  isPlaying: isPlaying,
  isCompleted: isCompleted,
);

final class _Lease implements NativeMediaFileLease {
  _Lease(this.path, {this.releaseFailuresRemaining = 0});

  @override
  final String path;
  int releaseFailuresRemaining;
  int releaseCalls = 0;

  @override
  Future<void> release() async {
    releaseCalls++;
    if (releaseFailuresRemaining > 0) {
      releaseFailuresRemaining--;
      throw StateError('Owned temporary file cleanup failed');
    }
  }
}

final class _FakePlayer extends NativeMediaPlayer {
  Completer<void>? initializeGate;
  final initializeStarted = Completer<void>();
  Object? initializeFailure;

  Completer<void>? releaseGate;
  final releaseStarted = Completer<void>();
  Object? releaseFailure;

  Completer<void>? firstSeekGate;
  final firstSeekStarted = Completer<void>();
  bool seekAutoplays = false;

  int? failPauseOnCall;
  int? failPlayOnCall;
  int pauseCalls = 0;
  int playCalls = 0;
  int releaseCalls = 0;
  int volumeCalls = 0;
  Future<void>? _release;
  final seekPositions = <Duration>[];
  final volumes = <double>[];

  @override
  Future<void> initialize() async {
    if (!initializeStarted.isCompleted) initializeStarted.complete();
    await initializeGate?.future;
    final failure = initializeFailure;
    if (failure != null) throw failure;
    value = _initializedValue();
  }

  @override
  Future<void> play() async {
    playCalls++;
    if (playCalls == failPlayOnCall) {
      throw StateError('Native play failed');
    }
    value = value.copyWith(isPlaying: true, isCompleted: false);
  }

  @override
  Future<void> pause() async {
    pauseCalls++;
    if (pauseCalls == failPauseOnCall) {
      throw StateError('Native pause failed');
    }
    value = value.copyWith(isPlaying: false);
  }

  @override
  Future<void> seekTo(Duration position) async {
    seekPositions.add(position);
    if (seekPositions.length == 1) {
      if (!firstSeekStarted.isCompleted) firstSeekStarted.complete();
      await firstSeekGate?.future;
    }
    value = value.copyWith(
      position: position,
      isPlaying: seekAutoplays || value.isPlaying,
      isCompleted: position >= _duration,
    );
  }

  @override
  Future<void> setVolume(double volume) async {
    volumeCalls++;
    volumes.add(volume);
    value = value.copyWith(volume: volume);
  }

  @override
  Future<void> release() => _release ??= _releaseOnce();

  Future<void> _releaseOnce() async {
    releaseCalls++;
    if (!releaseStarted.isCompleted) releaseStarted.complete();
    await releaseGate?.future;
    final failure = releaseFailure;
    if (failure != null) throw failure;
  }

  @override
  Widget buildView() =>
      throw UnimplementedError('Controller tests do not build views');
}

final class _Harness {
  _Harness({
    List<_FakePlayer>? players,
    NativePlaybackSlot? slot,
    this.leaseReleaseFailures,
  }) : players = players ?? <_FakePlayer>[],
       slot = slot ?? NativePlaybackSlot();

  final List<_FakePlayer> players;
  final NativePlaybackSlot slot;
  final int Function(int leaseIndex)? leaseReleaseFailures;
  final leases = <_Lease>[];
  final seenSourceBytes = <Uint8List>[];
  final playerPaths = <String>[];
  int _nextPlayer = 0;

  NativeMediaPreviewController createController({
    Duration timeout = const Duration(seconds: 15),
  }) => NativeMediaPreviewController(
    file: ContentProjectFile(
      bytes: Uint8List.fromList(_inputBytes),
      filename: 'selected-video.mp4',
      mediaType: 'video/mp4',
    ),
    createFile: (file) async {
      seenSourceBytes.add(Uint8List.fromList(file.bytes));
      final index = leases.length;
      final lease = _Lease(
        'owned-preview-$index.mp4',
        releaseFailuresRemaining: leaseReleaseFailures?.call(index) ?? 0,
      );
      leases.add(lease);
      return lease;
    },
    createPlayer: (path) {
      playerPaths.add(path);
      return players[_nextPlayer++];
    },
    slot: slot,
    initializationTimeout: timeout,
  );
}

Future<void> _close(NativeMediaPreviewController controller) async {
  await controller.close();
  controller.dispose();
}

Future<void> _pump(WidgetTester tester) async {
  await tester.pump();
  await tester.pump();
}

void main() {
  test('initialization exposes a paused first frame', () async {
    final player = _FakePlayer();
    final harness = _Harness(players: [player]);
    final controller = harness.createController();

    await controller.start();

    expect(controller.phase, NativePreviewPhase.ready);
    expect(controller.value.isInitialized, isTrue);
    expect(controller.value.isPlaying, isFalse);
    expect(controller.playing, isFalse);
    expect(player.pauseCalls, 1);
    expect(player.volumes, [1]);
    await _close(controller);
  });

  test(
    'native seeks serialize and restore pause after an autoplaying seek',
    () async {
      final player = _FakePlayer()
        ..seekAutoplays = true
        ..firstSeekGate = Completer<void>();
      final harness = _Harness(players: [player]);
      final controller = harness.createController();
      await controller.start();

      final firstSeek = controller.seek(const Duration(seconds: 3));
      await player.firstSeekStarted.future;
      final secondSeek = controller.seek(const Duration(seconds: 8));
      expect(player.seekPositions, [const Duration(seconds: 3)]);

      player.firstSeekGate!.complete();
      await Future.wait([firstSeek, secondSeek]);

      expect(player.seekPositions, [
        const Duration(seconds: 3),
        const Duration(seconds: 8),
      ]);
      expect(player.pauseCalls, 3);
      expect(player.value.isPlaying, isFalse);
      expect(controller.playing, isFalse);
      await _close(controller);
    },
  );

  test('a pending seek followed by cover and return stays paused', () async {
    final player = _FakePlayer()
      ..seekAutoplays = true
      ..firstSeekGate = Completer<void>();
    final harness = _Harness(players: [player]);
    final controller = harness.createController();
    await controller.start();

    final seeking = controller.seek(const Duration(seconds: 5));
    await player.firstSeekStarted.future;
    controller.setVisible(false);
    controller.setVisible(true);
    player.firstSeekGate!.complete();
    await seeking;
    await controller.toggleMute();

    expect(player.value.isPlaying, isFalse);
    expect(controller.playing, isFalse);
    expect(player.playCalls, 0);
    expect(player.pauseCalls, greaterThanOrEqualTo(3));
    await _close(controller);
  });

  test(
    'covering a playing preview and returning never resumes playback',
    () async {
      final player = _FakePlayer();
      final harness = _Harness(players: [player]);
      final controller = harness.createController();
      await controller.start();
      await controller.togglePlayback();
      expect(controller.playing, isTrue);

      controller.setVisible(false);
      controller.setVisible(true);
      await controller.toggleMute();

      expect(player.playCalls, 1);
      expect(player.value.isPlaying, isFalse);
      expect(controller.playing, isFalse);
      await _close(controller);
    },
  );

  testWidgets(
    'initialization timeout retains the slot and lease until actual release completes',
    (tester) async {
      final pendingPlayer = _FakePlayer()
        ..initializeGate = Completer<void>()
        ..releaseGate = Completer<void>();
      final nextPlayer = _FakePlayer();
      final harness = _Harness(players: [pendingPlayer, nextPlayer]);
      final first = harness.createController(
        timeout: const Duration(milliseconds: 20),
      );
      final openingFirst = first.start();
      await pendingPlayer.initializeStarted.future;
      expect(harness.slot.occupied, isTrue);

      await tester.pump(const Duration(milliseconds: 21));
      await _pump(tester);

      expect(first.phase, NativePreviewPhase.releasing);
      expect(first.canRetry, isFalse);
      expect(pendingPlayer.releaseCalls, 1);
      expect(harness.leases.single.releaseCalls, 0);
      expect(harness.slot.occupied, isTrue);

      final second = harness.createController();
      final openingSecond = second.start();
      await _pump(tester);
      expect(second.phase, NativePreviewPhase.releasing);
      expect(harness.playerPaths, ['owned-preview-0.mp4']);
      expect(harness.slot.occupied, isTrue);

      pendingPlayer.initializeGate!.complete();
      pendingPlayer.releaseGate!.complete();
      await _pump(tester);
      await Future.wait([openingFirst, openingSecond]);

      expect(first.phase, NativePreviewPhase.failed);
      expect(first.canRetry, isTrue);
      expect(harness.leases.first.releaseCalls, 1);
      expect(harness.playerPaths, [
        'owned-preview-0.mp4',
        'owned-preview-1.mp4',
      ]);
      expect(second.phase, NativePreviewPhase.ready);
      expect(harness.slot.occupied, isTrue);
      await _close(first);
      await _close(second);
    },
  );

  test(
    'closing during initialization cleans a late player without becoming ready',
    () async {
      final player = _FakePlayer()..initializeGate = Completer<void>();
      final harness = _Harness(players: [player]);
      final controller = harness.createController();
      final phases = <NativePreviewPhase>[];
      controller.addListener(() => phases.add(controller.phase));
      final opening = controller.start();
      await player.initializeStarted.future;

      final closing = controller.close();
      expect(controller.phase, NativePreviewPhase.releasing);
      player.initializeGate!.complete();
      await Future.wait([opening, closing]);

      expect(phases, isNot(contains(NativePreviewPhase.ready)));
      expect(controller.phase, NativePreviewPhase.closed);
      expect(player.releaseCalls, 1);
      expect(player.pauseCalls, 0);
      expect(harness.leases.single.releaseCalls, 1);
      controller.dispose();
    },
  );

  test(
    'failed initialization retries from the same bytes without playback effects',
    () async {
      final failedPlayer = _FakePlayer()
        ..initializeFailure = StateError('Decoder unavailable');
      final retryPlayer = _FakePlayer();
      final harness = _Harness(players: [failedPlayer, retryPlayer]);
      final controller = harness.createController();

      await controller.start();
      expect(controller.phase, NativePreviewPhase.failed);
      expect(controller.canRetry, isTrue);
      expect(failedPlayer.releaseCalls, 1);
      expect(harness.leases.first.releaseCalls, 1);

      await controller.retry();

      expect(controller.phase, NativePreviewPhase.ready);
      expect(harness.seenSourceBytes.map((bytes) => bytes.toList()), [
        _inputBytes,
        _inputBytes,
      ]);
      expect(failedPlayer.playCalls, 0);
      expect(retryPlayer.playCalls, 0);
      expect(retryPlayer.seekPositions, isEmpty);
      expect(retryPlayer.value.isPlaying, isFalse);
      await _close(controller);
    },
  );

  test(
    'play failure releases native and file resources before reporting failed',
    () async {
      final player = _FakePlayer()..failPlayOnCall = 1;
      final harness = _Harness(players: [player]);
      final controller = harness.createController();
      await controller.start();

      await controller.togglePlayback();

      expect(controller.phase, NativePreviewPhase.failed);
      expect(controller.canRetry, isTrue);
      expect(controller.playing, isFalse);
      expect(controller.player, isNull);
      expect(player.releaseCalls, 1);
      expect(harness.leases.single.releaseCalls, 1);
      await _close(controller);
    },
  );

  test(
    'pause failure releases native and file resources before reporting failed',
    () async {
      final player = _FakePlayer()..failPauseOnCall = 2;
      final harness = _Harness(players: [player]);
      final controller = harness.createController();
      await controller.start();
      await controller.togglePlayback();

      controller.setVisible(false);
      await controller.toggleMute();

      expect(controller.phase, NativePreviewPhase.failed);
      expect(controller.canRetry, isTrue);
      expect(controller.playing, isFalse);
      expect(controller.player, isNull);
      expect(player.releaseCalls, 1);
      expect(harness.leases.single.releaseCalls, 1);
      await _close(controller);
    },
  );

  test(
    'failed file cleanup stays distinct and retry cleans it before reopening',
    () async {
      final failedPlayer = _FakePlayer()
        ..initializeFailure = StateError('Decoder unavailable');
      final retryPlayer = _FakePlayer();
      final harness = _Harness(
        players: [failedPlayer, retryPlayer],
        leaseReleaseFailures: (index) => index == 0 ? 1 : 0,
      );
      final controller = harness.createController();

      await controller.start();
      expect(controller.phase, NativePreviewPhase.cleanupFailed);
      expect(controller.canRetry, isTrue);
      expect(failedPlayer.releaseCalls, 1);
      expect(harness.leases.first.releaseCalls, 1);
      expect(harness.slot.occupied, isFalse);

      await controller.retry();

      expect(harness.leases.first.releaseCalls, 2);
      expect(controller.phase, NativePreviewPhase.ready);
      expect(retryPlayer.value.isPlaying, isFalse);
      await _close(controller);
    },
  );

  test(
    'completed playback pauses at the end and replay seeks back to zero',
    () async {
      final player = _FakePlayer();
      final harness = _Harness(players: [player]);
      final controller = harness.createController();
      await controller.start();
      await controller.togglePlayback();
      expect(controller.playing, isTrue);

      player.value = _initializedValue(position: _duration, isCompleted: true);
      await controller.toggleMute();

      expect(controller.playing, isFalse);
      expect(player.value.isPlaying, isFalse);
      expect(player.seekPositions, [_duration]);

      await controller.togglePlayback();
      expect(player.seekPositions, [_duration, Duration.zero]);
      expect(player.playCalls, 2);
      expect(controller.playing, isTrue);
      await _close(controller);
    },
  );

  test(
    'uncertain native release retains the slot and temporary file lease',
    () async {
      final player = _FakePlayer()
        ..failPlayOnCall = 1
        ..releaseFailure = StateError('Native disposal is uncertain');
      final harness = _Harness(players: [player]);
      final controller = harness.createController();
      await controller.start();

      await controller.togglePlayback();
      await controller.close();

      expect(controller.phase, NativePreviewPhase.releasing);
      expect(controller.canRetry, isFalse);
      expect(controller.player, same(player));
      expect(player.releaseCalls, 1);
      expect(harness.leases.single.releaseCalls, 0);
      expect(harness.slot.occupied, isTrue);
      controller.dispose();
    },
  );
}
