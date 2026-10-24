import 'dart:io';

import 'package:flutter/widgets.dart';
import 'package:video_player/video_player.dart';

abstract class NativeMediaPlayer extends ValueNotifier<VideoPlayerValue> {
  NativeMediaPlayer() : super(const VideoPlayerValue.uninitialized());

  Future<void> initialize();
  Future<void> play();
  Future<void> pause();
  Future<void> seekTo(Duration position);
  Future<void> setVolume(double volume);
  Future<void> release();
  Widget buildView();
}

class WindowsMediaPlayer extends NativeMediaPlayer {
  WindowsMediaPlayer(String path)
    : _controller = VideoPlayerController.file(
        File(path),
        // Disable the package's automatic resume. The preview owns all pause
        // decisions, including inactive/covered states; background play is off.
        videoPlayerOptions: VideoPlayerOptions(allowBackgroundPlayback: true),
      ) {
    _controller.addListener(_changed);
  }

  WindowsMediaPlayer.stream(Uri uri)
    : _controller = VideoPlayerController.networkUrl(
        uri,
        videoPlayerOptions: VideoPlayerOptions(allowBackgroundPlayback: true),
      ) {
    _controller.addListener(_changed);
  }

  final VideoPlayerController _controller;
  Future<void>? _release;

  void _changed() => value = _controller.value;

  @override
  Future<void> initialize() => _controller.initialize();
  @override
  Future<void> play() => _controller.play();
  @override
  Future<void> pause() => _controller.pause();
  @override
  Future<void> seekTo(Duration position) => _controller.seekTo(position);
  @override
  Future<void> setVolume(double volume) => _controller.setVolume(volume);
  @override
  Widget buildView() => VideoPlayer(_controller);

  @override
  Future<void> release() => _release ??= _disposePlayer();

  Future<void> _disposePlayer() async {
    // In particular, dispose waits for a still-pending native create operation.
    await _controller.dispose();
    super.dispose();
  }
}
