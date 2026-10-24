import 'dart:js_interop';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:web/web.dart' as web;

import '../../../core/lumenis_core_client.dart';
import '../../../l10n/lumenis_localizations.dart';

class MediaPreview extends StatefulWidget {
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
  State<MediaPreview> createState() => _MediaPreviewState();
}

class _MediaPreviewState extends State<MediaPreview> {
  final _mediaFocus = FocusNode(debugLabel: 'content-media-preview');
  String? _objectUrl;
  web.HTMLMediaElement? _element;
  bool _failed = false;
  bool _routeIsCurrent = true;
  int _generation = 0;
  Duration? _pendingSeek;

  void _emitPosition() {
    final media = _element;
    if (media == null || !media.currentTime.isFinite || media.currentTime < 0) {
      return;
    }
    widget.onPositionChanged?.call(
      Duration(
        microseconds: (media.currentTime * Duration.microsecondsPerSecond)
            .round(),
      ),
    );
  }

  void _applyPendingSeek() {
    final media = _element;
    final requested = _pendingSeek;
    if (media == null || requested == null || !media.duration.isFinite) return;
    final seconds = requested.inMicroseconds / Duration.microsecondsPerSecond;
    media.currentTime = seconds.clamp(0, media.duration);
    _pendingSeek = null;
    _emitPosition();
  }

  void _updateRouteVisibility() {
    final media = _element;
    if (media == null) return;
    if (!_routeIsCurrent) media.pause();
    // HTML media sits outside Flutter's canvas. Keep it behind modal routes
    // without recreating the source or losing the user's playback position.
    media.style
      ..visibility = _routeIsCurrent ? 'visible' : 'hidden'
      ..pointerEvents = _routeIsCurrent ? 'auto' : 'none';
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _routeIsCurrent = ModalRoute.isCurrentOf(context) ?? true;
    _element?.setAttribute(
      'aria-label',
      context.lumenisL10n.text('sh01.media.preview'),
    );
    _updateRouteVisibility();
  }

  void _release() {
    _generation++;
    if (_mediaFocus.hasFocus) _mediaFocus.unfocus();
    _element?.pause();
    _element?.removeAttribute('src');
    _element?.load();
    _element = null;
    if (_objectUrl != null) web.URL.revokeObjectURL(_objectUrl!);
    _objectUrl = null;
  }

  @override
  void didUpdateWidget(covariant MediaPreview oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (!identical(oldWidget.file, widget.file)) {
      _release();
      _failed = false;
      _pendingSeek = null;
    } else if (oldWidget.seekRequest != widget.seekRequest &&
        widget.seekPosition != null) {
      _pendingSeek = widget.seekPosition;
      _applyPendingSeek();
    }
  }

  @override
  void dispose() {
    _release();
    _mediaFocus.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_failed) return Text(context.lumenisL10n.text('sh01.media.failure'));
    final file = widget.file;
    final generation = _generation;
    return Focus(
      focusNode: _mediaFocus,
      skipTraversal: true,
      includeSemantics: false,
      onKeyEvent: (node, event) {
        // Flutter's web keyboard listener runs during capture. A DOM listener
        // on the media element is too late to protect a formerly focused button.
        // Leave native playback keys and Tab to the focused browser control.
        final media = _element;
        final keyboard = HardwareKeyboard.instance;
        final nativeKey = const [
          LogicalKeyboardKey.space,
          LogicalKeyboardKey.enter,
          LogicalKeyboardKey.numpadEnter,
          LogicalKeyboardKey.tab,
          LogicalKeyboardKey.arrowLeft,
          LogicalKeyboardKey.arrowRight,
          LogicalKeyboardKey.arrowUp,
          LogicalKeyboardKey.arrowDown,
          LogicalKeyboardKey.home,
          LogicalKeyboardKey.end,
          LogicalKeyboardKey.pageUp,
          LogicalKeyboardKey.pageDown,
          LogicalKeyboardKey.keyM,
          LogicalKeyboardKey.keyF,
          LogicalKeyboardKey.escape,
        ].contains(event.logicalKey);
        return _routeIsCurrent &&
                media != null &&
                media == web.document.activeElement &&
                nativeKey &&
                !keyboard.isAltPressed &&
                !keyboard.isControlPressed &&
                !keyboard.isMetaPressed
            ? KeyEventResult.skipRemainingHandlers
            : KeyEventResult.ignored;
      },
      child: HtmlElementView.fromTagName(
        key: ObjectKey(file),
        tagName: file.mediaType.startsWith('video/') ? 'video' : 'audio',
        onElementCreated: (Object element) {
          if (!mounted || generation != _generation) return;
          final media = element as web.HTMLMediaElement;
          _element = media;
          final stream = file.streamUri;
          if (stream != null && stream.origin != Uri.base.origin) {
            _failed = true;
            WidgetsBinding.instance.addPostFrameCallback((_) {
              if (mounted) setState(() {});
            });
            return;
          }
          if (stream == null) {
            _objectUrl = web.URL.createObjectURL(
              web.Blob(
                [file.bytes.toJS].toJS,
                web.BlobPropertyBag(type: file.mediaType),
              ),
            );
          }
          media
            ..controls = true
            ..preload = 'metadata'
            ..src = stream?.toString() ?? _objectUrl!
            ..setAttribute(
              'aria-label',
              context.lumenisL10n.text('sh01.media.preview'),
            );
          media.style
            ..width = '100%'
            ..height = '100%'
            ..objectFit = 'contain';
          if (file.mediaType.startsWith('video/')) {
            (media as web.HTMLVideoElement).playsInline = true;
          }
          final takeMediaFocus = ((web.Event event) {
            if (mounted && _routeIsCurrent && identical(_element, media)) {
              _mediaFocus.requestFocus();
            }
          }).toJS;
          media.addEventListener('focusin', takeMediaFocus);
          media.addEventListener('pointerdown', takeMediaFocus);
          final emitPosition = ((web.Event event) {
            if (mounted && identical(_element, media)) {
              _applyPendingSeek();
              _emitPosition();
            }
          }).toJS;
          for (final type in [
            'timeupdate',
            'loadedmetadata',
            'durationchange',
            'seeking',
            'seeked',
          ]) {
            media.addEventListener(type, emitPosition);
          }
          _pendingSeek = widget.seekPosition;
          _applyPendingSeek();
          _updateRouteVisibility();
          media.addEventListener(
            'error',
            ((web.Event event) {
              if (mounted && identical(_element, media)) {
                setState(() => _failed = true);
              }
            }).toJS,
          );
        },
      ),
    );
  }
}
