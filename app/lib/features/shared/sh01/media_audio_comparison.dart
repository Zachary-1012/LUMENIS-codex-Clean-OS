import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../../l10n/lumenis_localizations.dart';
import 'media_preview.dart';
import 'media_project_controller.dart';

Future<void> showAudioProcessingDialog(
  BuildContext context,
  MediaProjectController controller, {
  double startSec = 0,
}) => showDialog<void>(
  context: context,
  builder: (_) =>
      _AudioComparisonDialog(controller: controller, startSec: startSec),
);

class _AudioComparisonDialog extends StatefulWidget {
  const _AudioComparisonDialog({
    required this.controller,
    required this.startSec,
  });
  final MediaProjectController controller;
  final double startSec;
  @override
  State<_AudioComparisonDialog> createState() => _AudioComparisonState();
}

class _AudioComparisonState extends State<_AudioComparisonDialog> {
  late Map<String, double> _options;
  late final double _duration;
  late RangeValues _range;
  MediaAudioComparison? _comparison;
  bool _loading = false;
  bool _failed = false;
  bool _processed = false;
  Duration _position = Duration.zero;
  int _seekRequest = 0;

  String text(String key) => context.lumenisL10n.text('sh01.media.$key');

  @override
  void initState() {
    super.initState();
    _options = Map.of(widget.controller.renderOptions);
    _duration = widget.controller.timeline!.durationSec;
    final start = widget.startSec
        .clamp(0.0, math.max(0.0, _duration - .01))
        .toDouble();
    _range = RangeValues(start, math.min(_duration, start + 60));
    widget.controller.addListener(_contextChanged);
  }

  void _contextChanged() {
    if (!mounted) return;
    setState(() {
      if (_comparison != null &&
          !widget.controller.canAdoptAudioProcessing(_comparison!)) {
        _comparison = null;
        _failed = true;
      }
    });
  }

  @override
  void dispose() {
    widget.controller.removeListener(_contextChanged);
    super.dispose();
  }

  void _change(VoidCallback action) => setState(() {
    action();
    _comparison = null;
    _failed = false;
    _position = Duration.zero;
  });

  Future<void> _prepare() async {
    setState(() {
      _loading = true;
      _failed = false;
      _comparison = null;
    });
    try {
      final result = await widget.controller.previewAudioProcessing(
        _options,
        startSec: _range.start,
        endSec: _range.end,
      );
      if (mounted) {
        setState(() {
          _comparison = result;
          _processed = false;
          _position = Duration.zero;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _failed = true);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final enabled = !_loading && widget.controller.contextMatches;
    final denoise = _options.containsKey('noise_reduction_db');
    final comparison = _comparison;
    return AlertDialog(
      title: Text(text('audio_adjust')),
      content: SizedBox(
        width: 560,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              DropdownButtonFormField<double>(
                key: const Key('audio-preview-target'),
                initialValue: _options['loudness_target_lufs'] ?? 0,
                decoration: InputDecoration(labelText: text('loudness_target')),
                items: [
                  DropdownMenuItem(value: 0, child: Text(text('master_off'))),
                  for (final value in [-16.0, -14.0, -23.0])
                    DropdownMenuItem(
                      value: value,
                      child: Text('${value.toInt()} LUFS'),
                    ),
                ],
                onChanged: !enabled
                    ? null
                    : (value) => _change(() {
                        if (value == null || value == 0) {
                          _options.remove('loudness_target_lufs');
                        } else {
                          _options['loudness_target_lufs'] = value;
                        }
                      }),
              ),
              SwitchListTile.adaptive(
                key: const Key('audio-preview-denoise'),
                contentPadding: EdgeInsets.zero,
                title: Text(text('denoise_enable')),
                value: denoise,
                onChanged: !enabled
                    ? null
                    : (value) => _change(() {
                        if (value) {
                          _options['noise_reduction_db'] = 12;
                          _options['noise_floor_db'] = -50;
                        } else {
                          _options.remove('noise_reduction_db');
                          _options.remove('noise_floor_db');
                        }
                      }),
              ),
              if (denoise) ...[
                Text(
                  '${text('denoise_amount')} · ${_options['noise_reduction_db']!.toStringAsFixed(0)} dB',
                ),
                Slider(
                  key: const Key('audio-preview-amount'),
                  value: _options['noise_reduction_db']!,
                  min: 3,
                  max: 18,
                  divisions: 15,
                  label: '${_options['noise_reduction_db']} dB',
                  semanticFormatterCallback: (value) =>
                      '${text('denoise_amount')} $value dB',
                  onChanged: !enabled
                      ? null
                      : (value) => _change(
                          () => _options['noise_reduction_db'] = value,
                        ),
                ),
                Text(
                  '${text('denoise_floor')} · ${_options['noise_floor_db']!.toStringAsFixed(0)} dB',
                ),
                Slider(
                  key: const Key('audio-preview-floor'),
                  value: _options['noise_floor_db']!,
                  min: -80,
                  max: -20,
                  divisions: 60,
                  label: '${_options['noise_floor_db']} dB',
                  semanticFormatterCallback: (value) =>
                      '${text('denoise_floor')} $value dB',
                  onChanged: !enabled
                      ? null
                      : (value) =>
                            _change(() => _options['noise_floor_db'] = value),
                ),
              ],
              Text(
                '${text('audio_sample_range')} · ${_range.start.toStringAsFixed(2)}–${_range.end.toStringAsFixed(2)} s',
              ),
              RangeSlider(
                key: const Key('audio-preview-range'),
                values: _range,
                min: 0,
                max: _duration,
                labels: RangeLabels(
                  '${_range.start.toStringAsFixed(2)} s',
                  '${_range.end.toStringAsFixed(2)} s',
                ),
                onChanged: !enabled
                    ? null
                    : (value) {
                        if (value.end - value.start < .01) return;
                        _change(
                          () => _range = value.end - value.start <= 60
                              ? value
                              : value.start != _range.start
                              ? RangeValues(value.start, value.start + 60)
                              : RangeValues(value.end - 60, value.end),
                        );
                      },
              ),
              Text(text('audio_sample_hint')),
              const SizedBox(height: 12),
              FilledButton.tonal(
                key: const Key('audio-preview-prepare'),
                onPressed: enabled ? _prepare : null,
                child: Text(
                  text(_loading ? 'audio_preparing' : 'audio_prepare'),
                ),
              ),
              if (_loading)
                const Padding(
                  padding: EdgeInsets.all(12),
                  child: Center(child: CircularProgressIndicator()),
                ),
              if (_failed)
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  child: Text(text('audio_preview_failed')),
                ),
              if (comparison != null) ...[
                const SizedBox(height: 16),
                SegmentedButton<bool>(
                  key: const Key('audio-preview-select'),
                  segments: [
                    ButtonSegment(
                      value: false,
                      label: Text(text('audio_unprocessed')),
                    ),
                    ButtonSegment(
                      value: true,
                      label: Text(text('audio_processed')),
                    ),
                  ],
                  selected: {_processed},
                  onSelectionChanged: (values) => setState(() {
                    _processed = values.single;
                    _seekRequest++;
                  }),
                ),
                const SizedBox(height: 12),
                SizedBox(
                  height: 60,
                  child: MediaPreview(
                    file: _processed
                        ? comparison.processed
                        : comparison.original,
                    seekPosition: _position,
                    seekRequest: _seekRequest,
                    onPositionChanged: (value) => _position = value,
                  ),
                ),
                const SizedBox(height: 12),
                Text(text('audio_programme_measurement')),
                for (final key in ['original', 'processed'])
                  Text(_measurement(comparison, key)),
              ],
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
          key: const Key('audio-preview-cancel'),
          onPressed: () => Navigator.of(context).pop(),
          child: Text(text('cancel')),
        ),
        FilledButton(
          key: const Key('audio-preview-adopt'),
          onPressed:
              comparison == null ||
                  !widget.controller.canAdoptAudioProcessing(comparison)
              ? null
              : () {
                  if (widget.controller.adoptAudioProcessing(comparison)) {
                    Navigator.of(context).pop();
                  }
                },
          child: Text(text('audio_adopt')),
        ),
      ],
    );
  }

  String _measurement(MediaAudioComparison comparison, String key) {
    final row = comparison.measurements[key];
    String value(String name) => row is Map && row[name] is num
        ? (row[name] as num).toStringAsFixed(2)
        : '—';
    return '${text(key == 'original' ? 'audio_unprocessed' : 'audio_processed')} · ${value('integrated_lufs')} LUFS · ${value('true_peak_dbtp')} dBTP';
  }
}
