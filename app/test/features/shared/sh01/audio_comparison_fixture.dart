import 'dart:convert';

Map<String, dynamic> audioComparisonFixture(
  Map<String, dynamic> timeline,
  List<String>? refs,
  Map<String, double> options,
  double start,
  double end,
) {
  final bytes = List<int>.filled(48, 0);
  bytes.setRange(0, 4, ascii.encode('RIFF'));
  bytes.setRange(8, 12, ascii.encode('WAVE'));
  final sample = {
    'wav_base64': base64Encode(bytes),
    'size_bytes': bytes.length,
    'sha256': 'a' * 64,
  };
  final tracks = timeline['tracks'] as List;
  var duration = 0.0;
  for (final track in tracks) {
    for (final clip in (track as Map)['clips'] as List) {
      final stop =
          (clip['timeline_start'] as num).toDouble() +
          (clip['source_out'] as num).toDouble() -
          (clip['source_in'] as num).toDouble();
      if (stop > duration) duration = stop;
    }
  }
  return {
    'ok': true,
    'assets': timeline['assets'],
    'source_artifact_refs': refs ?? <String>[],
    'rights_state': 'unknown',
    'external_fetch': false,
    'audio_comparison': {
      'state': 'preview',
      'base_version': timeline['version'],
      'base_digest': 'b' * 64,
      'persisted': false,
      'export_performed': false,
      'approval_required': true,
      'start_sec': start,
      'end_sec': end,
      'programme_duration_sec': duration,
      'render_options': options,
      'samples': {'original': sample, 'processed': sample},
      'programme_measurements': {
        'original': {'integrated_lufs': -20, 'true_peak_dbtp': -5},
        'processed': {'integrated_lufs': -16, 'true_peak_dbtp': -1},
      },
    },
  };
}
