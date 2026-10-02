import 'dart:js_interop';

import 'package:flutter/material.dart';
import 'package:web/web.dart' as web;

import '../../../core/lumenis_core_client.dart';
import '../../../l10n/lumenis_localizations.dart';

/// Playback consumes only bytes already authorized through Product Core. No
/// credential or external URL is handed to an HTML media element.
class MediaPreview extends StatefulWidget {
  const MediaPreview({required this.file, super.key});
  final ContentProjectFile file;

  @override
  State<MediaPreview> createState() => _MediaPreviewState();
}

class _MediaPreviewState extends State<MediaPreview> {
  String? _objectUrl;
  web.HTMLMediaElement? _element;
  bool _failed = false;
  bool _routeIsCurrent = true;
  int _generation = 0;

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
    }
  }

  @override
  void dispose() {
    _release();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_failed) return Text(context.lumenisL10n.text('sh01.media.failure'));
    final file = widget.file;
    final generation = _generation;
    return HtmlElementView.fromTagName(
      key: ObjectKey(file),
      tagName: file.mediaType == 'video/mp4' ? 'video' : 'audio',
      onElementCreated: (Object element) {
        if (!mounted || generation != _generation) return;
        final media = element as web.HTMLMediaElement;
        _element = media;
        _objectUrl = web.URL.createObjectURL(
          web.Blob(
            [file.bytes.toJS].toJS,
            web.BlobPropertyBag(type: file.mediaType),
          ),
        );
        media
          ..controls = true
          ..preload = 'metadata'
          ..src = _objectUrl!
          ..setAttribute(
            'aria-label',
            context.lumenisL10n.text('sh01.media.preview'),
          );
        media.style
          ..width = '100%'
          ..height = '100%'
          ..objectFit = 'contain';
        if (file.mediaType == 'video/mp4') {
          (media as web.HTMLVideoElement).playsInline = true;
        }
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
    );
  }
}
