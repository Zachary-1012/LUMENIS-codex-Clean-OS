import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:video_player/video_player.dart';

import '../../../core/lumenis_core_client.dart';
import 'native_media_cache.dart';
import 'native_media_player.dart';

enum NativePreviewPhase {
  loading,
  ready,
  releasing,
  failed,
  cleanupFailed,
  closed,
}

/// Prevents a new mounted preview from overtaking an old native disposal.
/// This is an in-process presentation lease, not a media store or job queue.
class NativePlaybackSlot {
  Future<void> _tail = Future<void>.value();
  int _leases = 0;

  bool get occupied => _leases > 0;

  Future<VoidCallback> acquire() async {
    final previous = _tail;
    final released = Completer<void>();
    _leases++;
    _tail = released.future;
    await previous;
    return () {
      if (!released.isCompleted) {
        _leases--;
        released.complete();
      }
    };
  }
}

class NativeMediaPreviewController extends ChangeNotifier {
  NativeMediaPreviewController({
    required this.file,
    Future<NativeMediaFileLease> Function(ContentProjectFile)? createFile,
    NativeMediaPlayer Function(String)? createPlayer,
    NativePlaybackSlot? slot,
    this.initializationTimeout = const Duration(seconds: 15),
  }) : _createFile = createFile ?? NativeMediaCache().create,
       _createPlayer = createPlayer ?? WindowsMediaPlayer.new,
       _slot = slot ?? _sharedSlot;

  static final _sharedSlot = NativePlaybackSlot();
  final ContentProjectFile file;
  final Future<NativeMediaFileLease> Function(ContentProjectFile) _createFile;
  final NativeMediaPlayer Function(String) _createPlayer;
  final NativePlaybackSlot _slot;
  final Duration initializationTimeout;
  NativeMediaFileLease? _lease;
  NativeMediaPlayer? _player;
  VoidCallback? _releaseSlot;
  Future<void>? _opening;
  Future<void>? _closing;
  Future<void> _commands = Future<void>.value();
  bool _closeRequested = false;
  bool _notifierDisposed = false;
  bool _visible = true;
  bool _playIntent = false;
  bool _muted = false;
  NativePreviewPhase _phase = NativePreviewPhase.loading;

  NativePreviewPhase get phase => _phase;
  NativeMediaPlayer? get player => _player;
  VideoPlayerValue get value =>
      _player?.value ?? const VideoPlayerValue.uninitialized();
  bool get playing => _playIntent && value.isPlaying;
  bool get muted => _muted;
  bool get canRetry =>
      !_closeRequested &&
      (_phase == NativePreviewPhase.failed ||
          _phase == NativePreviewPhase.cleanupFailed);

  void _setPhase(NativePreviewPhase phase) {
    _phase = phase;
    _notify();
  }

  void _notify() {
    if (!_notifierDisposed) notifyListeners();
  }

  Future<void> start() => _opening ??= _open();

  Future<void> _open() async {
    _playIntent = false;
    _setPhase(
      _slot.occupied
          ? NativePreviewPhase.releasing
          : NativePreviewPhase.loading,
    );
    try {
      _releaseSlot = await _slot.acquire();
      if (_closeRequested) {
        await _releaseResources();
        return;
      }
      _setPhase(NativePreviewPhase.loading);
      _lease = await _createFile(file);
      if (_closeRequested) {
        await _releaseResources();
        return;
      }
      final player = _player = _createPlayer(_lease!.path);
      player.addListener(_playerChanged);
      await player.initialize().timeout(initializationTimeout);
      if (!player.value.isInitialized || player.value.hasError) {
        throw StateError('Native playback initialization failed');
      }
      if (_closeRequested) {
        await _releaseResources();
        return;
      }
      await player.pause();
      await player.setVolume(_muted ? 0 : 1);
      _setPhase(NativePreviewPhase.ready);
    } catch (_) {
      // A timeout never abandons native ownership. Disposal may still be waiting
      // for create; until it resolves the UI remains closing and retry is off.
      _setPhase(NativePreviewPhase.releasing);
      if (await _releaseResources()) _setPhase(NativePreviewPhase.failed);
    }
  }

  void _playerChanged() {
    final state = value;
    if (_phase == NativePreviewPhase.ready && state.hasError) {
      _playIntent = false;
      unawaited(
        _enqueue((_) async {
          _setPhase(NativePreviewPhase.releasing);
          if (await _releaseResources()) _setPhase(NativePreviewPhase.failed);
        }),
      );
    } else if (state.isCompleted && _playIntent) {
      _playIntent = false;
      // video_player itself seeks to the end after completion. Serialize our
      // final seek and pause so the Windows seek does not restart playback.
      unawaited(
        _enqueue((player) async {
          await player.seekTo(player.value.duration);
          await player.pause();
        }),
      );
    }
    _notify();
  }

  Future<void> _enqueue(Future<void> Function(NativeMediaPlayer) action) {
    _commands = _commands.then((_) async {
      final player = _player;
      if (_closeRequested ||
          _phase != NativePreviewPhase.ready ||
          player == null) {
        return;
      }
      try {
        await action(player);
      } catch (_) {
        _playIntent = false;
        _setPhase(NativePreviewPhase.releasing);
        if (await _releaseResources()) _setPhase(NativePreviewPhase.failed);
      }
      _notify();
    });
    return _commands;
  }

  Future<void> togglePlayback() {
    if (_phase != NativePreviewPhase.ready || !_visible || _closeRequested) {
      return Future<void>.value();
    }
    _playIntent = !_playIntent;
    return _enqueue((player) async {
      if (_playIntent && _visible) {
        if (player.value.position >= player.value.duration) {
          await player.seekTo(Duration.zero);
        }
        if (_playIntent && _visible) {
          await player.play();
        } else {
          await player.pause();
        }
      } else {
        await player.pause();
      }
      // Cover/pause may arrive while native play is pending.
      if (!_playIntent || !_visible || _closeRequested) await player.pause();
    });
  }

  Future<void> seek(Duration position) => _enqueue((player) async {
    final clamped = Duration(
      microseconds: position.inMicroseconds.clamp(
        0,
        player.value.duration.inMicroseconds,
      ),
    );
    await player.seekTo(clamped);
    // Native Windows seek can autoplay even though the Dart value says paused.
    // Always send the current intent, including changes during the pending seek.
    if (_playIntent && _visible && !_closeRequested) {
      await player.play();
    } else {
      await player.pause();
    }
  });

  Future<void> toggleMute() => _enqueue((player) async {
    _muted = !_muted;
    await player.setVolume(_muted ? 0 : 1);
  });

  void setVisible(bool visible) {
    _visible = visible;
    if (!visible) {
      _playIntent = false;
      unawaited(_enqueue((player) => player.pause()));
    }
    // Becoming visible never restores playback intent.
    _notify();
  }

  Future<void> retry() async {
    if (!canRetry) return;
    _setPhase(NativePreviewPhase.releasing);
    if (!await _releaseResources()) return;
    _opening = _open();
    await _opening;
  }

  Future<bool> _releaseResources() async {
    final player = _player;
    if (player != null) {
      player.removeListener(_playerChanged);
      try {
        await player.release();
      } catch (_) {
        // No slot transfer when native release is uncertain.
        debugPrint('SH01 native playback: native release is unconfirmed.');
        _setPhase(NativePreviewPhase.releasing);
        return false;
      }
      _player = null;
    }
    try {
      await _lease?.release();
      _lease = null;
      _releaseSlot?.call();
      _releaseSlot = null;
      return true;
    } catch (_) {
      // Native disposal is proven; retain this failed file lease for an explicit
      // cleanup retry without blocking another source's independent playback.
      _releaseSlot?.call();
      _releaseSlot = null;
      debugPrint('SH01 native playback: temporary-file cleanup is incomplete.');
      _setPhase(NativePreviewPhase.cleanupFailed);
      return false;
    }
  }

  Future<void> close() {
    if (_closing case final closing?) return closing;
    _closeRequested = true;
    _playIntent = false;
    _setPhase(NativePreviewPhase.releasing);
    return _closing = _close();
  }

  Future<void> _close() async {
    await _opening;
    await _commands;
    if (await _releaseResources()) _setPhase(NativePreviewPhase.closed);
  }

  @override
  void dispose() {
    _notifierDisposed = true;
    unawaited(close());
    super.dispose();
  }
}
