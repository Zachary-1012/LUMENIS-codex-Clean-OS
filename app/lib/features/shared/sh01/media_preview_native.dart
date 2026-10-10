import 'dart:async';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import '../../../core/lumenis_icon.dart';

import '../../../core/lumenis_core_client.dart';
import '../../../l10n/lumenis_localizations.dart';
import 'native_media_preview_controller.dart';

class MediaPreview extends StatelessWidget {
  const MediaPreview({
    required this.file,
    this.onPositionChanged,
    this.seekPosition,
    this.seekRequest,
    super.key,
  });
  final ContentProjectFile file;
  final ValueChanged<Duration>? onPositionChanged;
  final Duration? seekPosition;
  final int? seekRequest;

  @override
  Widget build(BuildContext context) {
    if (!Platform.isWindows ||
        defaultTargetPlatform != TargetPlatform.windows) {
      return Padding(
        padding: const EdgeInsets.all(24),
        child: Text(context.lumenisL10n.text('sh01.media.native_preview')),
      );
    }
    return WindowsMediaPreview(
      file: file,
      onPositionChanged: onPositionChanged,
      seekPosition: seekPosition,
      seekRequest: seekRequest,
    );
  }
}

class WindowsMediaPreview extends StatefulWidget {
  const WindowsMediaPreview({
    required this.file,
    this.onPositionChanged,
    this.seekPosition,
    this.seekRequest,
    this.controllerFactory,
    super.key,
  });

  final ContentProjectFile file;
  final ValueChanged<Duration>? onPositionChanged;
  final Duration? seekPosition;
  final int? seekRequest;
  @visibleForTesting
  final NativeMediaPreviewController Function(ContentProjectFile)?
  controllerFactory;

  @override
  State<WindowsMediaPreview> createState() => _WindowsMediaPreviewState();
}

class _WindowsMediaPreviewState extends State<WindowsMediaPreview>
    with WidgetsBindingObserver {
  late NativeMediaPreviewController _controller;
  bool _routeCurrent = true;
  bool _appActive = true;
  double? _dragPosition;
  Duration? _pendingExternalSeek;

  bool get _visible => _routeCurrent && _appActive;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    final lifecycle = WidgetsBinding.instance.lifecycleState;
    _appActive = lifecycle == null || lifecycle == AppLifecycleState.resumed;
    _createController();
  }

  void _createController() {
    _controller =
        widget.controllerFactory?.call(widget.file) ??
        NativeMediaPreviewController(file: widget.file);
    _controller.setVisible(_visible);
    _controller.addListener(_changed);
    _pendingExternalSeek = widget.seekPosition;
    unawaited(_controller.start());
  }

  void _changed() {
    if (!mounted) return;
    final value = _controller.value;
    widget.onPositionChanged?.call(value.position);
    if (_controller.phase == NativePreviewPhase.ready &&
        _pendingExternalSeek != null) {
      final requested = _pendingExternalSeek;
      _pendingExternalSeek = null;
      if (requested != null) unawaited(_controller.seek(requested));
    }
    setState(() {});
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _routeCurrent = ModalRoute.isCurrentOf(context) ?? true;
    _controller.setVisible(_visible);
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    _appActive = state == AppLifecycleState.resumed;
    _controller.setVisible(_visible);
  }

  @override
  void didUpdateWidget(covariant WindowsMediaPreview oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (!identical(oldWidget.file, widget.file)) {
      _controller.removeListener(_changed);
      _controller.dispose();
      _dragPosition = null;
      _createController();
    } else if (oldWidget.seekRequest != widget.seekRequest &&
        widget.seekPosition != null) {
      _pendingExternalSeek = widget.seekPosition;
      if (_controller.phase == NativePreviewPhase.ready) {
        final requested = _pendingExternalSeek;
        _pendingExternalSeek = null;
        if (requested != null) unawaited(_controller.seek(requested));
      }
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _controller.removeListener(_changed);
    _controller.dispose();
    super.dispose();
  }

  String _copy(String key) =>
      context.lumenisL10n.text('sh01.media.player.$key');

  Widget _status() {
    final phase = _controller.phase;
    final message = switch (phase) {
      NativePreviewPhase.loading => 'loading',
      NativePreviewPhase.releasing || NativePreviewPhase.closed => 'releasing',
      NativePreviewPhase.cleanupFailed => 'cleanup_failure',
      _ => 'failure',
    };
    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Semantics(liveRegion: true, child: Text(_copy(message))),
            if (_controller.canRetry) ...[
              const SizedBox(height: 12),
              OutlinedButton.icon(
                style: OutlinedButton.styleFrom(
                  minimumSize: const Size(48, 48),
                ),
                onPressed: () => unawaited(_controller.retry()),
                icon: const LumenisIcon(Icons.refresh_rounded),
                label: Text(_copy('retry')),
              ),
            ],
          ],
        ),
      ),
    );
  }

  static String _time(Duration duration) {
    final seconds = duration.inSeconds;
    final minutes = (seconds ~/ 60).toString().padLeft(2, '0');
    final remainder = (seconds % 60).toString().padLeft(2, '0');
    return '$minutes:$remainder';
  }

  Widget _controls() {
    final state = _controller.value;
    final duration = state.duration.inMilliseconds.toDouble();
    final position = (_dragPosition ?? state.position.inMilliseconds.toDouble())
        .clamp(0.0, duration);
    final atEnd =
        state.isCompleted || (duration > 0 && state.position >= state.duration);
    final playLabel = _controller.playing
        ? 'pause'
        : atEnd
        ? 'replay'
        : 'play';
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 8),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              IconButton(
                constraints: const BoxConstraints(minWidth: 48, minHeight: 48),
                tooltip: _copy(playLabel),
                onPressed: () => unawaited(_controller.togglePlayback()),
                icon: Icon(
                  _controller.playing
                      ? Icons.pause_rounded
                      : atEnd
                      ? Icons.replay_rounded
                      : Icons.play_arrow_rounded,
                  semanticLabel: _copy(playLabel),
                ),
              ),
              Expanded(
                child: Text(
                  '${_time(Duration(milliseconds: position.round()))} / '
                  '${_time(state.duration)}',
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ),
              IconButton(
                constraints: const BoxConstraints(minWidth: 48, minHeight: 48),
                tooltip: _copy(_controller.muted ? 'unmute' : 'mute'),
                onPressed: () => unawaited(_controller.toggleMute()),
                icon: Icon(
                  _controller.muted
                      ? Icons.volume_off_rounded
                      : Icons.volume_up_rounded,
                  semanticLabel: _copy(_controller.muted ? 'unmute' : 'mute'),
                ),
              ),
            ],
          ),
          Semantics(
            label: _copy('seek'),
            child: Slider(
              value: position,
              max: duration > 0 ? duration : 1,
              semanticFormatterCallback: (value) =>
                  _time(Duration(milliseconds: value.round())),
              onChanged: duration <= 0
                  ? null
                  : (value) {
                      setState(() => _dragPosition = value);
                    },
              onChangeEnd: duration <= 0
                  ? null
                  : (value) {
                      setState(() => _dragPosition = null);
                      unawaited(
                        _controller.seek(Duration(milliseconds: value.round())),
                      );
                    },
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final player = _controller.player;
    final ready =
        _controller.phase == NativePreviewPhase.ready && player != null;
    return ExcludeSemantics(
      excluding: !_visible,
      child: IgnorePointer(
        ignoring: !_visible,
        child: Opacity(
          opacity: _visible ? 1 : 0,
          child: Semantics(
            label: context.lumenisL10n.text('sh01.media.preview'),
            child: !ready
                ? _status()
                : Column(
                    children: [
                      Expanded(
                        child: Center(
                          child: player.value.size.isEmpty
                              ? LumenisIcon(
                                  Icons.audiotrack_rounded,
                                  size: 48,
                                  color: Theme.of(
                                    context,
                                  ).colorScheme.onSurfaceVariant,
                                )
                              : AspectRatio(
                                  aspectRatio: player.value.aspectRatio,
                                  child: player.buildView(),
                                ),
                        ),
                      ),
                      _controls(),
                    ],
                  ),
          ),
        ),
      ),
    );
  }
}
