import 'dart:math' as math;
import 'dart:convert';

import 'package:flutter/material.dart';

import '../../../core/lumenis_core_client.dart';
import '../../../core/lumenis_theme.dart';
import '../../../l10n/lumenis_localizations.dart';
import 'media_project_snapshot.dart';

class MediaSourceWaveform extends StatefulWidget {
  const MediaSourceWaveform({
    required this.client,
    required this.domain,
    required this.asset,
    required this.assetRef,
    required this.sourceIn,
    required this.sourceOut,
    required this.streamIndex,
    super.key,
  });

  final LumenisCoreClient client;
  final String? domain;
  final MediaProjectAsset asset;
  final String assetRef;
  final double sourceIn;
  final double sourceOut;
  final int streamIndex;

  @override
  State<MediaSourceWaveform> createState() => _MediaSourceWaveformState();
}

class _MediaSourceWaveformState extends State<MediaSourceWaveform> {
  late double _start;
  List<({double min, double max})>? _bins;
  bool _loading = true;
  int _request = 0;

  double get _end => math.min(widget.sourceOut, _start + 60);
  String _text(String key) => context.lumenisL10n.text('sh01.media.$key');

  @override
  void initState() {
    super.initState();
    _start = widget.sourceIn;
    _load();
  }

  @override
  void didUpdateWidget(covariant MediaSourceWaveform oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.assetRef != widget.assetRef ||
        oldWidget.asset.sha256 != widget.asset.sha256 ||
        oldWidget.sourceIn != widget.sourceIn ||
        oldWidget.sourceOut != widget.sourceOut ||
        oldWidget.streamIndex != widget.streamIndex ||
        oldWidget.domain != widget.domain ||
        !identical(oldWidget.client, widget.client)) {
      _start = widget.sourceIn;
      _load();
    }
  }

  Future<void> _load() async {
    final request = ++_request;
    final scope = jsonEncode(widget.client.currentContextEnvelope);
    final start = _start, end = _end;
    setState(() {
      _loading = true;
      _bins = null;
    });
    try {
      final response = await widget.client.inspectContentWaveform(
        domainId: widget.domain,
        assetRef: widget.assetRef,
        startSec: start,
        endSec: end,
        audioStreamIndex: widget.streamIndex,
      );
      if (!mounted || request != _request) return;
      if (jsonEncode(widget.client.currentContextEnvelope) != scope) {
        throw const FormatException('Waveform context changed');
      }
      final assets = response['assets'],
          refs = response['source_artifact_refs'];
      final values = response['waveforms'];
      if (response['ok'] != true ||
          assets is! List ||
          assets.length != 1 ||
          MediaProjectAsset.fromJson(assets.single).sha256 !=
              widget.asset.sha256 ||
          refs is! List ||
          refs.length != 1 ||
          refs.single != widget.assetRef ||
          values is! List ||
          values.length != 1 ||
          values.single is! Map) {
        throw const FormatException('Waveform source mismatch');
      }
      final wave = values.single as Map;
      final bins = wave['bins'];
      if (wave['state'] != 'measured' ||
          wave['stage'] != 'source_pre_mix' ||
          wave['source_sha256'] != widget.asset.sha256 ||
          wave['audio_stream_index'] != widget.streamIndex ||
          wave['start_sec'] != start ||
          wave['end_sec'] != end ||
          wave['sample_rate'] != 8000 ||
          wave['decoded_samples'] is! int ||
          (wave['decoded_samples'] as int) <= 0 ||
          bins is! List ||
          bins.isEmpty ||
          bins.length > 256) {
        throw const FormatException('Waveform measurement mismatch');
      }
      final peaks = <({double min, double max})>[];
      for (final bin in bins) {
        if (bin is! Map) throw const FormatException('Invalid waveform bin');
        final low = bin['min'], high = bin['max'], rms = bin['rms'];
        if (low is! num ||
            high is! num ||
            rms is! num ||
            !low.isFinite ||
            !high.isFinite ||
            !rms.isFinite ||
            low > high ||
            rms < 0) {
          throw const FormatException('Invalid waveform amplitude');
        }
        peaks.add((min: low.toDouble(), max: high.toDouble()));
      }
      setState(() {
        _bins = List.unmodifiable(peaks);
        _loading = false;
      });
    } catch (_) {
      if (mounted && request == _request) {
        setState(() {
          _bins = null;
          _loading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final palette = LumenisTheme.of(context);
    return LayoutBuilder(
      builder: (context, constraints) {
        final compact = constraints.maxHeight < 170;
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              widget.asset.filename,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.titleMedium,
            ),
            if (!compact)
              Text(
                '${_text('waveform_source')} · ${widget.streamIndex + 1}',
                style: Theme.of(context).textTheme.bodySmall,
              ),
            const SizedBox(height: 8),
            Expanded(
              child: DecoratedBox(
                decoration: BoxDecoration(
                  color: palette.surface,
                  border: Border.all(color: palette.line),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: _bins != null
                    ? Semantics(
                        label:
                            '${_text('waveform_source')}, ${_start.toStringAsFixed(2)}–${_end.toStringAsFixed(2)} s',
                        child: CustomPaint(
                          key: const Key('media-source-waveform'),
                          painter: _WaveformPainter(
                            _bins!,
                            palette.foreground,
                            palette.line,
                          ),
                          child: const SizedBox.expand(),
                        ),
                      )
                    : Center(
                        child: _loading
                            ? const SizedBox(
                                width: 24,
                                height: 24,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                ),
                              )
                            : TextButton.icon(
                                key: const Key('media-waveform-retry'),
                                onPressed: _load,
                                icon: const Icon(Icons.refresh),
                                label: Text(_text('waveform_retry')),
                              ),
                      ),
              ),
            ),
            Row(
              children: [
                Expanded(
                  child: Text(
                    '${_start.toStringAsFixed(2)}–${_end.toStringAsFixed(2)} s',
                  ),
                ),
                if (widget.sourceOut - widget.sourceIn > 60) ...[
                  IconButton(
                    key: const Key('media-waveform-previous'),
                    tooltip: _text('waveform_previous'),
                    onPressed: _loading || _start <= widget.sourceIn
                        ? null
                        : () {
                            _start = math.max(widget.sourceIn, _start - 60);
                            _load();
                          },
                    icon: const Icon(Icons.chevron_left),
                  ),
                  IconButton(
                    key: const Key('media-waveform-next'),
                    tooltip: _text('waveform_next'),
                    onPressed: _loading || _end >= widget.sourceOut
                        ? null
                        : () {
                            _start = _end;
                            _load();
                          },
                    icon: const Icon(Icons.chevron_right),
                  ),
                ],
              ],
            ),
          ],
        );
      },
    );
  }
}

class _WaveformPainter extends CustomPainter {
  _WaveformPainter(this.bins, this.ink, this.line);
  final List<({double min, double max})> bins;
  final Color ink, line;

  @override
  void paint(Canvas canvas, Size size) {
    final center = size.height / 2, amplitude = math.max(0.0, center - 8);
    canvas.drawLine(
      Offset(0, center),
      Offset(size.width, center),
      Paint()..color = line,
    );
    final paint = Paint()
      ..color = ink
      ..strokeWidth = math.max(.7, size.width / bins.length * .65);
    for (var i = 0; i < bins.length; i++) {
      final x = (i + .5) * size.width / bins.length;
      canvas.drawLine(
        Offset(x, center - bins[i].max.clamp(-1, 1) * amplitude),
        Offset(x, center - bins[i].min.clamp(-1, 1) * amplitude),
        paint,
      );
    }
  }

  @override
  bool shouldRepaint(covariant _WaveformPainter oldDelegate) =>
      oldDelegate.bins != bins ||
      oldDelegate.ink != ink ||
      oldDelegate.line != line;
}
