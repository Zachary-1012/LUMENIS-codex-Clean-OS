/// Immutable, local edit intent for the Shared Content & Creation timeline.
///
/// The Core timeline remains authoritative. This model contains no media paths,
/// rights grants, Evidence claims, networking, persistence, or rendering logic.
const int _maxTimelineVersion = 1000000000;
const double _maxEditTimeSec = 86400;
const Object _notProvided = Object();

FormatException _invalid(String message) => FormatException(message);

Map<String, Object?> _object(Object? value, Set<String> fields, String name) {
  if (value is! Map || value.keys.any((key) => key is! String)) {
    throw _invalid('$name must be an object');
  }
  final result = Map<String, Object?>.from(value);
  if (result.keys.toSet().difference(fields).isNotEmpty ||
      fields.difference(result.keys.toSet()).isNotEmpty) {
    throw _invalid('$name has unexpected or missing fields');
  }
  return result;
}

List<Object?> _array(Object? value, String name) {
  if (value is! List) throw _invalid('$name must be a list');
  return List<Object?>.from(value);
}

String _string(Object? value, String name, {bool allowEmpty = false}) {
  if (value is! String || (!allowEmpty && value.trim().isEmpty)) {
    throw _invalid(
      '$name must be a ${allowEmpty ? 'string' : 'non-empty string'}',
    );
  }
  return value;
}

int _integer(
  Object? value,
  String name, {
  int minimum = 0,
  int maximum = _maxTimelineVersion,
}) {
  if (value is! int || value < minimum || value > maximum) {
    throw _invalid('$name is outside its allowed range');
  }
  return value;
}

double _number(
  Object? value,
  String name, {
  double minimum = 0,
  double maximum = _maxEditTimeSec,
}) {
  if (value is! num || !value.isFinite || value < minimum || value > maximum) {
    throw _invalid('$name must be a finite number in range');
  }
  return value.toDouble();
}

bool _boolean(Object? value, String name) {
  if (value is! bool) throw _invalid('$name must be a boolean');
  return value;
}

List<String> _strings(Object? value, String name) {
  final values = _array(value, name);
  if (values.any((item) => item is! String)) {
    throw _invalid('$name must contain strings');
  }
  return List<String>.unmodifiable(values.cast<String>());
}

void _require(bool condition, String message) {
  if (!condition) throw _invalid(message);
}

/// Metadata returned by Core after inspecting a user-selected local asset.
/// These fields are read-only and deliberately carry no source path.
final class MediaProjectAsset {
  MediaProjectAsset({
    required this.assetId,
    required this.filename,
    required this.sha256,
    required this.durationSec,
    required this.mediaKind,
    required this.hasVideo,
    required this.audioStreamCount,
    List<String> evidenceRefs = const <String>[],
    this.rightsStatus = 'unknown',
  }) : evidenceRefs = List<String>.unmodifiable(evidenceRefs) {
    _validate();
  }

  final String assetId;
  final String filename;
  final String sha256;
  final double durationSec;
  final String mediaKind;
  final bool hasVideo;
  final int audioStreamCount;
  final List<String> evidenceRefs;
  final String rightsStatus;

  factory MediaProjectAsset.fromJson(Object? value) {
    final json = _object(value, {
      'asset_id',
      'filename',
      'sha256',
      'duration_sec',
      'media_kind',
      'has_video',
      'audio_stream_count',
      'evidence_refs',
      'rights_status',
    }, 'asset');
    return MediaProjectAsset(
      assetId: _string(json['asset_id'], 'asset_id'),
      filename: _string(json['filename'], 'filename'),
      sha256: _string(json['sha256'], 'sha256'),
      durationSec: _number(
        json['duration_sec'],
        'duration_sec',
        minimum: 0.000001,
      ),
      mediaKind: _string(json['media_kind'], 'media_kind'),
      hasVideo: _boolean(json['has_video'], 'has_video'),
      audioStreamCount: _integer(
        json['audio_stream_count'],
        'audio_stream_count',
        maximum: 256,
      ),
      evidenceRefs: _strings(json['evidence_refs'], 'evidence_refs'),
      rightsStatus: _string(json['rights_status'], 'rights_status'),
    );
  }

  void _validate() {
    _require(
      RegExp(r'^[0-9a-f]{64}$').hasMatch(sha256),
      'asset sha256 is invalid',
    );
    _require(
      assetId == 'MEDIA-${sha256.substring(0, 16)}',
      'asset fingerprint does not match',
    );
    _require(filename.trim().isNotEmpty, 'asset filename is required');
    _number(durationSec, 'duration_sec', minimum: 0.000001);
    _integer(audioStreamCount, 'audio_stream_count', maximum: 256);
    _require(
      hasVideo || audioStreamCount > 0,
      'asset has no supported media stream',
    );
    final derivedKind = !hasVideo
        ? 'audio'
        : audioStreamCount == 0
        ? 'video'
        : 'video_audio';
    _require(
      mediaKind == derivedKind,
      'media_kind does not match inspected streams',
    );
    _require(rightsStatus == 'unknown', 'rights status must remain unknown');
    _require(evidenceRefs.isEmpty, 'canonical Evidence is not available');
  }

  Map<String, Object?> toJson() => <String, Object?>{
    'asset_id': assetId,
    'filename': filename,
    'sha256': sha256,
    'duration_sec': durationSec,
    'media_kind': mediaKind,
    'has_video': hasVideo,
    'audio_stream_count': audioStreamCount,
    'evidence_refs': evidenceRefs,
    'rights_status': rightsStatus,
  };
}

final class MediaProjectAudioMix {
  const MediaProjectAudioMix({
    this.volume = 1,
    this.fadeInSec = 0,
    this.fadeOutSec = 0,
    this.ducking = false,
  });

  final double volume;
  final double fadeInSec;
  final double fadeOutSec;
  final bool ducking;

  factory MediaProjectAudioMix.fromJson(
    Object? value, {
    required double clipDuration,
  }) {
    final json = _object(value, {
      'volume',
      'fade_in_sec',
      'fade_out_sec',
      'ducking',
    }, 'audio_mix');
    final mix = MediaProjectAudioMix(
      volume: _number(json['volume'], 'volume', maximum: 2),
      fadeInSec: _number(json['fade_in_sec'], 'fade_in_sec'),
      fadeOutSec: _number(json['fade_out_sec'], 'fade_out_sec'),
      ducking: _boolean(json['ducking'], 'ducking'),
    );
    mix.validate(clipDuration);
    return mix;
  }

  void validate(double clipDuration) {
    _number(volume, 'volume', maximum: 2);
    _number(fadeInSec, 'fade_in_sec');
    _number(fadeOutSec, 'fade_out_sec');
    _require(
      fadeInSec <= clipDuration && fadeOutSec <= clipDuration,
      'audio fade exceeds clip',
    );
    _require(
      fadeInSec + fadeOutSec <= clipDuration,
      'audio fades exceed clip duration',
    );
  }

  MediaProjectAudioMix copyWith({
    double? volume,
    double? fadeInSec,
    double? fadeOutSec,
    bool? ducking,
  }) => MediaProjectAudioMix(
    volume: volume ?? this.volume,
    fadeInSec: fadeInSec ?? this.fadeInSec,
    fadeOutSec: fadeOutSec ?? this.fadeOutSec,
    ducking: ducking ?? this.ducking,
  );

  Map<String, Object?> toJson() => <String, Object?>{
    'volume': volume,
    'fade_in_sec': fadeInSec,
    'fade_out_sec': fadeOutSec,
    'ducking': ducking,
  };
}

final class MediaProjectClip {
  const MediaProjectClip({
    required this.clipId,
    required this.mediaAssetId,
    required this.sourceIn,
    required this.sourceOut,
    required this.timelineStart,
    required this.trackId,
    required this.purpose,
    required this.audioRole,
    required this.audioMix,
    required this.evidenceRefs,
    required this.audioStreamIndex,
  });

  final String clipId;
  final String mediaAssetId;
  final double sourceIn;
  final double sourceOut;
  final double timelineStart;
  final String trackId;
  final String purpose;
  final String audioRole;
  final MediaProjectAudioMix audioMix;
  final List<String> evidenceRefs;
  final int? audioStreamIndex;

  double get durationSec => sourceOut - sourceIn;

  factory MediaProjectClip.fromJson(Object? value) {
    final json = _object(value, {
      'clip_id',
      'media_asset_id',
      'source_in',
      'source_out',
      'timeline_start',
      'track_id',
      'purpose',
      'audio_role',
      'audio_mix',
      'evidence_refs',
      'audio_stream_index',
    }, 'clip');
    final sourceIn = _number(json['source_in'], 'source_in');
    final sourceOut = _number(json['source_out'], 'source_out');
    final audioIndexValue = json['audio_stream_index'];
    if (audioIndexValue != null && audioIndexValue is! int) {
      throw _invalid('audio_stream_index must be an integer or null');
    }
    final clip = MediaProjectClip(
      clipId: _string(json['clip_id'], 'clip_id'),
      mediaAssetId: _string(json['media_asset_id'], 'media_asset_id'),
      sourceIn: sourceIn,
      sourceOut: sourceOut,
      timelineStart: _number(json['timeline_start'], 'timeline_start'),
      trackId: _string(json['track_id'], 'track_id'),
      purpose: _string(json['purpose'], 'purpose', allowEmpty: true),
      audioRole: _string(json['audio_role'], 'audio_role'),
      audioMix: MediaProjectAudioMix.fromJson(
        json['audio_mix'],
        clipDuration: sourceOut - sourceIn,
      ),
      evidenceRefs: _strings(json['evidence_refs'], 'evidence_refs'),
      audioStreamIndex: audioIndexValue as int?,
    );
    clip._validate();
    return clip;
  }

  void _validate() {
    _require(
      sourceOut > sourceIn,
      'clip source range must have positive duration',
    );
    _require(
      timelineStart + durationSec <= _maxEditTimeSec,
      'clip timeline range is too long',
    );
    if (audioStreamIndex != null) {
      _integer(audioStreamIndex, 'audio_stream_index');
    }
    _require(evidenceRefs.isEmpty, 'canonical Evidence is not available');
    audioMix.validate(durationSec);
    _require(
      const {
        'original',
        'muted',
        'voiceover',
        'bgm',
        'sfx',
      }.contains(audioRole),
      'audio_role is unsupported',
    );
  }

  MediaProjectClip copyWith({
    String? clipId,
    String? mediaAssetId,
    double? sourceIn,
    double? sourceOut,
    double? timelineStart,
    String? trackId,
    String? purpose,
    String? audioRole,
    MediaProjectAudioMix? audioMix,
    Object? audioStreamIndex = _notProvided,
  }) => MediaProjectClip(
    clipId: clipId ?? this.clipId,
    mediaAssetId: mediaAssetId ?? this.mediaAssetId,
    sourceIn: sourceIn ?? this.sourceIn,
    sourceOut: sourceOut ?? this.sourceOut,
    timelineStart: timelineStart ?? this.timelineStart,
    trackId: trackId ?? this.trackId,
    purpose: purpose ?? this.purpose,
    audioRole: audioRole ?? this.audioRole,
    audioMix: audioMix ?? this.audioMix,
    evidenceRefs: evidenceRefs,
    audioStreamIndex: identical(audioStreamIndex, _notProvided)
        ? this.audioStreamIndex
        : audioStreamIndex as int?,
  );

  Map<String, Object?> toJson() => <String, Object?>{
    'clip_id': clipId,
    'media_asset_id': mediaAssetId,
    'source_in': sourceIn,
    'source_out': sourceOut,
    'timeline_start': timelineStart,
    'track_id': trackId,
    'purpose': purpose,
    'audio_role': audioRole,
    'audio_mix': audioMix.toJson(),
    'evidence_refs': evidenceRefs,
    'audio_stream_index': audioStreamIndex,
  };
}

final class MediaProjectTrack {
  MediaProjectTrack({
    required this.trackId,
    required this.kind,
    required List<MediaProjectClip> clips,
  }) : clips = List<MediaProjectClip>.unmodifiable(clips);

  final String trackId;
  final String kind;
  final List<MediaProjectClip> clips;

  factory MediaProjectTrack.fromJson(Object? value) {
    final json = _object(value, {'track_id', 'kind', 'clips'}, 'track');
    return MediaProjectTrack(
      trackId: _string(json['track_id'], 'track_id'),
      kind: _string(json['kind'], 'kind'),
      clips: _array(
        json['clips'],
        'clips',
      ).map(MediaProjectClip.fromJson).toList(),
    );
  }

  Map<String, Object?> toJson() => <String, Object?>{
    'track_id': trackId,
    'kind': kind,
    'clips': clips.map((clip) => clip.toJson()).toList(growable: false),
  };
}

/// A read-only transition record. Unknown transition types are retained exactly
/// so Core can reject them explicitly.
final class MediaProjectTransition {
  const MediaProjectTransition({
    required this.fromClip,
    required this.toClip,
    required this.transitionType,
    required this.durationSec,
    required this.reason,
  });

  final String fromClip;
  final String toClip;
  final String transitionType;
  final double durationSec;
  final String reason;

  factory MediaProjectTransition.fromJson(Object? value) {
    final json = _object(value, {
      'from_clip',
      'to_clip',
      'transition_type',
      'duration_sec',
      'reason',
    }, 'transition');
    return MediaProjectTransition(
      fromClip: _string(json['from_clip'], 'from_clip'),
      toClip: _string(json['to_clip'], 'to_clip'),
      transitionType: _string(json['transition_type'], 'transition_type'),
      durationSec: _number(json['duration_sec'], 'duration_sec', maximum: 30),
      reason: _string(json['reason'], 'reason', allowEmpty: true),
    );
  }

  Map<String, Object?> toJson() => <String, Object?>{
    'from_clip': fromClip,
    'to_clip': toClip,
    'transition_type': transitionType,
    'duration_sec': durationSec,
    'reason': reason,
  };
}

final class MediaProjectOverlay {
  const MediaProjectOverlay({
    required this.overlayId,
    required this.kind,
    required this.startSec,
    required this.endSec,
    required this.text,
    this.layoutProfile,
  });

  final String overlayId;
  final String kind;
  final double startSec;
  final double endSec;
  final String text;
  final String? layoutProfile;

  factory MediaProjectOverlay.fromJson(Object? value) {
    final json = _object(value, {
      'overlay_id',
      'kind',
      'start_sec',
      'end_sec',
      'text',
      if (value is Map && value.containsKey('layout_profile')) 'layout_profile',
    }, 'overlay');
    final overlay = MediaProjectOverlay(
      overlayId: _string(json['overlay_id'], 'overlay_id'),
      kind: _string(json['kind'], 'kind'),
      startSec: _number(json['start_sec'], 'start_sec'),
      endSec: _number(json['end_sec'], 'end_sec'),
      text: _string(json['text'], 'text'),
      layoutProfile: json.containsKey('layout_profile')
          ? _string(json['layout_profile'], 'layout_profile')
          : null,
    );
    overlay._validate();
    return overlay;
  }

  void _validate() {
    _require(
      layoutProfile == null ||
          (kind == 'caption' && layoutProfile == 'literal-wide-720p-v2'),
      'overlay layout profile is unsupported',
    );
    _require(
      kind == 'caption' || kind == 'text',
      'overlay kind is unsupported',
    );
    _require(endSec > startSec, 'overlay range must have positive duration');
  }

  Map<String, Object?> toJson() => <String, Object?>{
    'overlay_id': overlayId,
    'kind': kind,
    'start_sec': startSec,
    'end_sec': endSec,
    'text': text,
    if (layoutProfile != null) 'layout_profile': layoutProfile,
  };
}

final class _SnapshotState {
  _SnapshotState({
    required this.tracks,
    required this.transitions,
    required this.overlays,
    required this.formatRatio,
  });

  final List<MediaProjectTrack> tracks;
  final List<MediaProjectTransition> transitions;
  final List<MediaProjectOverlay> overlays;
  final String formatRatio;
}

/// Client-side edit intent matching Python `Timeline.to_dict()` field names.
final class MediaProjectSnapshot {
  MediaProjectSnapshot._({
    required List<MediaProjectAsset> assets,
    required List<MediaProjectTrack> tracks,
    required List<MediaProjectTransition> transitions,
    required List<MediaProjectOverlay> overlays,
    required this.formatRatio,
    required this.version,
    List<_SnapshotState> history = const <_SnapshotState>[],
  }) : assets = List<MediaProjectAsset>.unmodifiable(assets),
       tracks = List<MediaProjectTrack>.unmodifiable(tracks),
       transitions = List<MediaProjectTransition>.unmodifiable(transitions),
       overlays = List<MediaProjectOverlay>.unmodifiable(overlays),
       _history = List<_SnapshotState>.unmodifiable(history) {
    _validate();
  }

  final List<MediaProjectAsset> assets;
  final List<MediaProjectTrack> tracks;
  final List<MediaProjectTransition> transitions;
  final List<MediaProjectOverlay> overlays;
  final String formatRatio;
  final int version;
  final List<_SnapshotState> _history;

  /// Append freshly inspected media without rewriting any existing source.
  MediaProjectSnapshot addInspectedAsset(MediaProjectAsset asset) {
    _require(
      assets.every((item) => item.assetId != asset.assetId),
      'asset already exists',
    );
    return MediaProjectSnapshot._(
      assets: [...assets, asset],
      tracks: tracks,
      transitions: transitions,
      overlays: overlays,
      formatRatio: formatRatio,
      version: version + 1,
      history: _history,
    );
  }

  /// Adopt one inspected batch as one local undo step, retaining earlier edits.
  /// The preview's version and stable IDs are preserved exactly.
  MediaProjectSnapshot adoptInspectedPreview(MediaProjectSnapshot preview) {
    _require(preview.version > version, 'preview must advance the timeline');
    MediaProjectSnapshot.fromJson(toJson(), inspectedAssets: preview.assets);
    return MediaProjectSnapshot._(
      assets: preview.assets,
      tracks: preview.tracks,
      transitions: preview.transitions,
      overlays: preview.overlays,
      formatRatio: preview.formatRatio,
      version: preview.version,
      history: [
        ..._history,
        _SnapshotState(
          tracks: tracks,
          transitions: transitions,
          overlays: overlays,
          formatRatio: formatRatio,
        ),
      ],
    );
  }

  bool get canUndo => _history.isNotEmpty;

  /// End time of the latest clip or overlay in timeline coordinates.
  double get durationSec {
    var end = 0.0;
    for (final track in tracks) {
      for (final clip in track.clips) {
        end = end > clip.timelineStart + clip.durationSec
            ? end
            : clip.timelineStart + clip.durationSec;
      }
    }
    for (final overlay in overlays) {
      end = end > overlay.endSec ? end : overlay.endSec;
    }
    return end;
  }

  factory MediaProjectSnapshot.empty({
    required Iterable<MediaProjectAsset> inspectedAssets,
    String formatRatio = '9:16',
  }) => MediaProjectSnapshot._(
    assets: inspectedAssets.toList(),
    tracks: <MediaProjectTrack>[
      MediaProjectTrack(trackId: 'video', kind: 'video', clips: const []),
    ],
    transitions: const <MediaProjectTransition>[],
    overlays: const <MediaProjectOverlay>[],
    formatRatio: formatRatio,
    version: 1,
  );

  /// Reopening requires fresh Core-inspected metadata; serialized asset claims
  /// are compared against it and never become trusted merely by deserialization.
  factory MediaProjectSnapshot.fromJson(
    Object? value, {
    required Iterable<MediaProjectAsset> inspectedAssets,
  }) {
    final json = _object(value, {
      'version',
      'format_ratio',
      'assets',
      'tracks',
      'transitions',
      'overlays',
      'approval_required',
    }, 'timeline');
    _require(
      _boolean(json['approval_required'], 'approval_required'),
      'approval is required',
    );
    final actualAssets = List<MediaProjectAsset>.unmodifiable(inspectedAssets);
    final storedAssets = _array(
      json['assets'],
      'assets',
    ).map(MediaProjectAsset.fromJson).toList();
    _require(
      actualAssets.length == storedAssets.length,
      'inspected assets do not match timeline',
    );
    final actualById = <String, MediaProjectAsset>{};
    for (final asset in actualAssets) {
      _require(
        !actualById.containsKey(asset.assetId),
        'duplicate inspected asset',
      );
      actualById[asset.assetId] = asset;
    }
    final storedIds = <String>{};
    for (final stored in storedAssets) {
      _require(storedIds.add(stored.assetId), 'duplicate serialized asset');
      final fresh = actualById[stored.assetId];
      _require(
        fresh != null && _mapsEqual(fresh.toJson(), stored.toJson()),
        'asset metadata does not match inspection',
      );
    }
    return MediaProjectSnapshot._(
      assets: actualAssets,
      tracks: _array(
        json['tracks'],
        'tracks',
      ).map(MediaProjectTrack.fromJson).toList(),
      transitions: _array(
        json['transitions'],
        'transitions',
      ).map(MediaProjectTransition.fromJson).toList(),
      overlays: _array(
        json['overlays'],
        'overlays',
      ).map(MediaProjectOverlay.fromJson).toList(),
      formatRatio: _string(json['format_ratio'], 'format_ratio'),
      version: _integer(json['version'], 'version', minimum: 1),
    );
  }

  static bool _mapsEqual(
    Map<String, Object?> left,
    Map<String, Object?> right,
  ) {
    if (left.length != right.length) return false;
    for (final key in left.keys) {
      final a = left[key];
      final b = right[key];
      if (a is List && b is List) {
        if (a.length != b.length ||
            List.generate(a.length, (i) => a[i] == b[i]).contains(false)) {
          return false;
        }
      } else if (a != b) {
        return false;
      }
    }
    return true;
  }

  void _validate() {
    _integer(version, 'version', minimum: 1);
    _require(
      const {'9:16', '4:5', '3:4', '16:9'}.contains(formatRatio),
      'format ratio is unsupported',
    );
    _require(
      assets.isNotEmpty && tracks.isNotEmpty,
      'timeline requires assets and tracks',
    );
    final assetsById = <String, MediaProjectAsset>{};
    for (final asset in assets) {
      _require(!assetsById.containsKey(asset.assetId), 'duplicate asset');
      assetsById[asset.assetId] = asset;
    }
    final tracksById = <String, MediaProjectTrack>{};
    final clipsById = <String, MediaProjectClip>{};
    for (final track in tracks) {
      _require(!tracksById.containsKey(track.trackId), 'duplicate track');
      _require(
        const {'video', 'voiceover', 'bgm', 'sfx'}.contains(track.kind),
        'track kind is unsupported',
      );
      tracksById[track.trackId] = track;
      for (final clip in track.clips) {
        clip._validate();
        final asset = assetsById[clip.mediaAssetId];
        if (asset == null || clip.trackId != track.trackId) {
          throw _invalid('clip source or track is invalid');
        }
        _require(
          clip.sourceOut <= asset.durationSec,
          'clip exceeds inspected media duration',
        );
        _require(!clipsById.containsKey(clip.clipId), 'duplicate clip');
        if (track.kind == 'video') {
          _require(asset.hasVideo, 'video track requires video media');
          _require(
            clip.audioRole == 'original' || clip.audioRole == 'muted',
            'video audio role is invalid',
          );
          _require(
            clip.audioRole != 'muted' || clip.audioStreamIndex == null,
            'muted clip cannot select audio',
          );
          _require(
            clip.audioRole != 'original' ||
                asset.audioStreamCount <= 1 ||
                clip.audioStreamIndex != null,
            'multi-stream video requires explicit audio selection',
          );
        } else {
          _require(
            asset.audioStreamCount > 0,
            'audio track requires audio media',
          );
          _require(
            clip.audioRole == track.kind,
            'audio role must match track kind',
          );
          _require(
            clip.audioStreamIndex != null,
            'audio stream selection is required',
          );
        }
        if (clip.audioStreamIndex != null) {
          _require(
            clip.audioStreamIndex! < asset.audioStreamCount,
            'audio stream index is out of range',
          );
        }
        clipsById[clip.clipId] = clip;
      }
    }
    for (final transition in transitions) {
      final from = clipsById[transition.fromClip];
      final to = clipsById[transition.toClip];
      if (from == null || to == null || from.clipId == to.clipId) {
        throw _invalid('transition references missing clips');
      }
      _require(
        transition.durationSec <= from.durationSec &&
            transition.durationSec <= to.durationSec,
        'transition exceeds clip duration',
      );
      _require(
        transition.transitionType == 'cut' ||
            (transition.durationSec > 0 && transition.reason.trim().isNotEmpty),
        'transition is malformed',
      );
    }
    for (final overlay in overlays) {
      overlay._validate();
    }
  }

  MediaProjectAsset _asset(String assetId) => assets.firstWhere(
    (asset) => asset.assetId == assetId,
    orElse: () => throw StateError('unknown media asset'),
  );

  MediaProjectTrack _track(String trackId) => tracks.firstWhere(
    (track) => track.trackId == trackId,
    orElse: () => throw StateError('unknown track'),
  );

  (MediaProjectTrack, MediaProjectClip) _clip(String clipId) {
    for (final track in tracks) {
      for (final clip in track.clips) {
        if (clip.clipId == clipId) return (track, clip);
      }
    }
    throw StateError('unknown clip');
  }

  MediaProjectSnapshot addAudioTrack(
    String trackId, {
    required String audioRole,
  }) {
    _require(
      const {'voiceover', 'bgm', 'sfx'}.contains(audioRole),
      'audio track kind is unsupported',
    );
    _require(
      tracks.every((track) => track.trackId != trackId),
      'track already exists',
    );
    _require(trackId.trim().isNotEmpty, 'track id is required');
    return _commit(
      tracks: [
        ...tracks,
        MediaProjectTrack(trackId: trackId, kind: audioRole, clips: const []),
      ],
    );
  }

  MediaProjectSnapshot addClip(
    String mediaAssetId, {
    required String trackId,
    double sourceIn = 0,
    double? sourceOut,
    double timelineStart = 0,
    String purpose = '',
    String? audioRole,
    int? audioStreamIndex,
    String? clipId,
  }) {
    final asset = _asset(mediaAssetId);
    final track = _track(trackId);
    final end = sourceOut ?? asset.durationSec;
    _number(sourceIn, 'source_in');
    _number(end, 'source_out');
    _require(
      end > sourceIn && end <= asset.durationSec,
      'clip range is outside inspected media',
    );
    final isVideo = track.kind == 'video';
    final role = isVideo ? (audioRole ?? 'original') : track.kind;
    if (isVideo) {
      _require(asset.hasVideo, 'video track requires video media');
      _require(
        audioRole == null || audioRole == 'original' || audioRole == 'muted',
        'video audio role is invalid',
      );
      if (role == 'muted') {
        _require(audioStreamIndex == null, 'muted video cannot select audio');
      } else if (audioStreamIndex == null && asset.audioStreamCount == 1) {
        audioStreamIndex = 0;
      }
      _require(
        asset.audioStreamCount <= 1 ||
            role == 'muted' ||
            audioStreamIndex != null,
        'multi-stream video requires explicit audio selection',
      );
    } else {
      _require(asset.audioStreamCount > 0, 'audio track requires audio media');
      _require(
        audioRole == null || audioRole == 'original' || audioRole == track.kind,
        'audio role must match track kind',
      );
      audioStreamIndex ??= asset.audioStreamCount == 1 ? 0 : null;
      _require(
        audioStreamIndex != null,
        'multi-stream audio requires explicit selection',
      );
      _number(timelineStart, 'timeline_start');
    }
    if (audioStreamIndex != null) {
      _integer(audioStreamIndex, 'audio_stream_index', maximum: 255);
      _require(
        audioStreamIndex < asset.audioStreamCount,
        'audio stream index is out of range',
      );
    }
    final id = clipId ?? _localId('CLIP');
    _require(
      tracks.every((item) => item.clips.every((clip) => clip.clipId != id)),
      'clip id already exists',
    );
    final clip = MediaProjectClip(
      clipId: id,
      mediaAssetId: mediaAssetId,
      sourceIn: sourceIn,
      sourceOut: end,
      timelineStart: isVideo ? 0 : timelineStart,
      trackId: trackId,
      purpose: purpose,
      audioRole: role,
      audioMix: const MediaProjectAudioMix(),
      evidenceRefs: const <String>[],
      audioStreamIndex: audioStreamIndex,
    );
    final changed = track.kind == 'video'
        ? _reflow(track, [...track.clips, clip])
        : MediaProjectTrack(
            trackId: track.trackId,
            kind: track.kind,
            clips: [...track.clips, clip],
          );
    return _commit(
      tracks: tracks
          .map((item) => item.trackId == trackId ? changed : item)
          .toList(),
    );
  }

  MediaProjectSnapshot replaceClipSource(
    String clipId, {
    required String mediaAssetId,
    required double sourceIn,
    required String audioRole,
    required int? audioStreamIndex,
  }) {
    final (track, clip) = _clip(clipId);
    final asset = _asset(mediaAssetId);
    final video = track.kind == 'video';
    _number(sourceIn, 'source_in');
    final sourceOut = sourceIn + clip.durationSec;
    _number(sourceOut, 'source_out');
    _require(
      sourceOut > sourceIn && sourceOut <= asset.durationSec,
      'replacement is outside inspected media',
    );
    if (video) {
      _require(asset.hasVideo, 'video track requires video media');
      _require(
        audioRole == 'original' || audioRole == 'muted',
        'video audio role is invalid',
      );
      if (audioRole == 'muted') {
        _require(audioStreamIndex == null, 'muted video cannot select audio');
      } else {
        audioStreamIndex ??= asset.audioStreamCount == 1 ? 0 : null;
        _require(
          asset.audioStreamCount <= 1 || audioStreamIndex != null,
          'multi-stream video requires explicit audio selection',
        );
      }
    } else {
      _require(asset.audioStreamCount > 0, 'audio track requires audio media');
      _require(audioRole == track.kind, 'audio role must match track kind');
      audioStreamIndex ??= asset.audioStreamCount == 1 ? 0 : null;
      _require(audioStreamIndex != null, 'audio stream selection is required');
    }
    if (audioStreamIndex != null) {
      _integer(audioStreamIndex, 'audio_stream_index', maximum: 255);
      _require(
        audioStreamIndex < asset.audioStreamCount,
        'audio stream index is out of range',
      );
    }
    final replaced = clip.copyWith(
      mediaAssetId: mediaAssetId,
      sourceIn: sourceIn,
      sourceOut: sourceOut,
      audioRole: audioRole,
      audioStreamIndex: audioStreamIndex,
    );
    // A fixed-window replacement must not reflow neighboring clips.
    final changedTracks = [
      for (final item in tracks)
        if (item.trackId == track.trackId)
          MediaProjectTrack(
            trackId: item.trackId,
            kind: item.kind,
            clips: [
              for (final original in item.clips)
                original.clipId == clipId ? replaced : original,
            ],
          )
        else
          item,
    ];
    if (video) _validateVideoTransitionEdits(changedTracks, transitions);
    return _commit(tracks: changedTracks);
  }

  MediaProjectSnapshot trimClip(
    String clipId, {
    required double sourceIn,
    required double sourceOut,
  }) {
    final (track, clip) = _clip(clipId);
    final asset = _asset(clip.mediaAssetId);
    _number(sourceIn, 'source_in');
    _number(sourceOut, 'source_out');
    _require(
      sourceOut > sourceIn && sourceOut <= asset.durationSec,
      'trim is outside inspected media',
    );
    return _replaceClip(
      track,
      clip.copyWith(sourceIn: sourceIn, sourceOut: sourceOut),
      validateVideoTransitions: track.kind == 'video',
    );
  }

  MediaProjectSnapshot splitClip(String clipId, {required double atSec}) {
    final (track, clip) = _clip(clipId);
    _number(atSec, 'split time');
    _require(
      atSec > clip.sourceIn && atSec < clip.sourceOut,
      'split must be inside clip source range',
    );
    final firstDuration = double.parse(
      (atSec - clip.sourceIn).toStringAsFixed(6),
    );
    final secondDuration = double.parse(
      (clip.sourceOut - atSec).toStringAsFixed(6),
    );
    final first = clip.copyWith(
      clipId: '$clipId-a',
      sourceOut: atSec,
      audioMix: clip.audioMix.copyWith(
        fadeInSec: clip.audioMix.fadeInSec.clamp(0, firstDuration).toDouble(),
        fadeOutSec: 0,
      ),
    );
    final second = clip.copyWith(
      clipId: '$clipId-b',
      sourceIn: atSec,
      timelineStart: clip.timelineStart + atSec - clip.sourceIn,
      audioMix: clip.audioMix.copyWith(
        fadeInSec: 0,
        fadeOutSec: clip.audioMix.fadeOutSec
            .clamp(0, secondDuration)
            .toDouble(),
      ),
    );
    final split = <MediaProjectClip>[];
    for (final item in track.clips) {
      if (item.clipId == clipId) {
        split
          ..add(first)
          ..add(second);
      } else {
        split.add(item);
      }
    }
    final changed = track.kind == 'video'
        ? _reflow(track, split)
        : MediaProjectTrack(
            trackId: track.trackId,
            kind: track.kind,
            clips: split,
          );
    final changedTracks = tracks
        .map((item) => item.trackId == track.trackId ? changed : item)
        .toList();
    final changedTransitions = track.kind == 'video'
        ? transitions
              .where(
                (transition) =>
                    transition.fromClip != clipId &&
                    transition.toClip != clipId,
              )
              .toList()
        : transitions;
    if (track.kind == 'video') {
      _validateVideoTransitionEdits(changedTracks, changedTransitions);
    }
    return _commit(tracks: changedTracks, transitions: changedTransitions);
  }

  MediaProjectSnapshot reorderVideoClip(
    String clipId, {
    required int newIndex,
  }) {
    final (track, clip) = _clip(clipId);
    _require(track.kind == 'video', 'only video clips can be reordered');
    final remaining = track.clips
        .where((item) => item.clipId != clipId)
        .toList();
    _require(
      newIndex >= 0 && newIndex <= remaining.length,
      'video clip order is out of range',
    );
    remaining.insert(newIndex, clip);
    final changed = _reflow(track, remaining);
    final changedTracks = tracks
        .map((item) => item.trackId == track.trackId ? changed : item)
        .toList();
    _validateVideoTransitionEdits(changedTracks, transitions);
    return _commit(tracks: changedTracks);
  }

  MediaProjectSnapshot deleteVideoClip(String clipId) {
    final (track, _) = _clip(clipId);
    _require(track.kind == 'video', 'only video clips can be deleted');
    final changed = _reflow(
      track,
      track.clips.where((clip) => clip.clipId != clipId).toList(),
    );
    final changedTracks = tracks
        .map((item) => item.trackId == track.trackId ? changed : item)
        .toList();
    final changedTransitions = transitions
        .where(
          (transition) =>
              transition.fromClip != clipId && transition.toClip != clipId,
        )
        .toList();
    _validateVideoTransitionEdits(changedTracks, changedTransitions);
    return _commit(tracks: changedTracks, transitions: changedTransitions);
  }

  MediaProjectSnapshot deleteAudioClip(String clipId) {
    final (track, _) = _clip(clipId);
    _require(track.kind != 'video', 'deleteAudioClip only accepts audio clips');
    final changed = MediaProjectTrack(
      trackId: track.trackId,
      kind: track.kind,
      clips: track.clips.where((clip) => clip.clipId != clipId).toList(),
    );
    return _commit(
      tracks: tracks
          .map((item) => item.trackId == track.trackId ? changed : item)
          .toList(),
    );
  }

  MediaProjectSnapshot moveAudioClip(
    String clipId, {
    required double timelineStart,
  }) {
    final (track, clip) = _clip(clipId);
    _require(track.kind != 'video', 'only audio clips can be positioned');
    _number(timelineStart, 'timeline_start');
    _require(
      timelineStart + clip.durationSec <= _maxEditTimeSec,
      'audio clip exceeds timeline limit',
    );
    return _replaceClip(track, clip.copyWith(timelineStart: timelineStart));
  }

  MediaProjectSnapshot setAudioMix(String clipId, MediaProjectAudioMix mix) {
    final (track, clip) = _clip(clipId);
    mix.validate(clip.durationSec);
    return _replaceClip(track, clip.copyWith(audioMix: mix));
  }

  /// One inspector submission is one undo step, including the range and mix.
  MediaProjectSnapshot adjustClip(
    String clipId, {
    required double sourceIn,
    required double sourceOut,
    required double timelineStart,
    required MediaProjectAudioMix audioMix,
    required String audioRole,
    required int? audioStreamIndex,
  }) {
    final (track, clip) = _clip(clipId);
    // A video source-range edit can change transition handles. Validate the
    // whole candidate against Core's frame and media-handle rules.
    final validateVideoTransitions =
        track.kind == 'video' &&
        (clip.sourceIn != sourceIn || clip.sourceOut != sourceOut);
    return _replaceClip(
      track,
      clip.copyWith(
        sourceIn: sourceIn,
        sourceOut: sourceOut,
        timelineStart: track.kind == 'video'
            ? clip.timelineStart
            : timelineStart,
        audioMix: audioMix,
        audioRole: audioRole,
        audioStreamIndex: audioStreamIndex,
      ),
      validateVideoTransitions: validateVideoTransitions,
    );
  }

  MediaProjectSnapshot setAudioStreamIndex(
    String clipId, {
    required int audioStreamIndex,
  }) {
    final (track, clip) = _clip(clipId);
    _require(clip.audioRole != 'muted', 'muted clips cannot select audio');
    final asset = _asset(clip.mediaAssetId);
    _integer(audioStreamIndex, 'audio_stream_index', maximum: 255);
    _require(
      audioStreamIndex < asset.audioStreamCount,
      'audio stream index is out of range',
    );
    return _replaceClip(
      track,
      clip.copyWith(audioStreamIndex: audioStreamIndex),
    );
  }

  MediaProjectSnapshot setAudioRole(
    String clipId, {
    required String audioRole,
    int? audioStreamIndex,
  }) {
    final (track, clip) = _clip(clipId);
    final asset = _asset(clip.mediaAssetId);
    if (track.kind == 'video') {
      _require(
        audioRole == 'original' || audioRole == 'muted',
        'video audio role is unsupported',
      );
      if (audioRole == 'muted') {
        _require(audioStreamIndex == null, 'muted clips cannot select audio');
        return _replaceClip(
          track,
          clip.copyWith(audioRole: audioRole, audioStreamIndex: null),
        );
      }
      final selectedIndex =
          audioStreamIndex ??
          clip.audioStreamIndex ??
          (asset.audioStreamCount == 1 ? 0 : null);
      if (asset.audioStreamCount > 1) {
        _require(
          selectedIndex != null,
          'multi-stream video requires explicit audio selection',
        );
      }
      if (selectedIndex != null) {
        _integer(selectedIndex, 'audio_stream_index', maximum: 255);
        _require(
          selectedIndex < asset.audioStreamCount,
          'audio stream index is out of range',
        );
      }
      return _replaceClip(
        track,
        clip.copyWith(audioRole: audioRole, audioStreamIndex: selectedIndex),
      );
    }

    _require(
      audioRole == 'original' || audioRole == track.kind,
      'audio role must match track kind',
    );
    _require(asset.audioStreamCount > 0, 'audio track requires audio media');
    final selectedIndex =
        audioStreamIndex ??
        clip.audioStreamIndex ??
        (asset.audioStreamCount == 1 ? 0 : null);
    if (selectedIndex == null) {
      throw _invalid('multi-stream audio requires explicit selection');
    }
    _integer(selectedIndex, 'audio_stream_index', maximum: 255);
    _require(
      selectedIndex < asset.audioStreamCount,
      'audio stream index is out of range',
    );
    return _replaceClip(
      track,
      clip.copyWith(audioRole: track.kind, audioStreamIndex: selectedIndex),
    );
  }

  MediaProjectSnapshot addOverlay({
    required String kind,
    required double startSec,
    required double endSec,
    required String text,
  }) {
    _number(startSec, 'overlay start');
    _number(endSec, 'overlay end');
    _require(endSec > startSec && text.trim().isNotEmpty, 'overlay is invalid');
    _require(
      kind == 'caption' || kind == 'text',
      'overlay kind is unsupported',
    );
    final overlay = MediaProjectOverlay(
      overlayId: _localId('OVERLAY'),
      kind: kind,
      startSec: startSec,
      endSec: endSec,
      text: text,
    );
    return _commit(overlays: [...overlays, overlay]);
  }

  MediaProjectSnapshot updateOverlay(
    String overlayId, {
    required double startSec,
    required double endSec,
    required String text,
  }) {
    final index = overlays.indexWhere(
      (overlay) => overlay.overlayId == overlayId,
    );
    _require(index >= 0, 'overlay not found');
    _number(startSec, 'overlay start');
    _number(endSec, 'overlay end');
    _require(endSec > startSec, 'overlay range must have positive duration');
    _require(text.trim().isNotEmpty, 'overlay text is required');

    final current = overlays[index];
    final changed = overlays.toList();
    changed[index] = MediaProjectOverlay(
      overlayId: current.overlayId,
      kind: current.kind,
      startSec: startSec,
      endSec: endSec,
      text: text,
      layoutProfile: current.layoutProfile,
    );
    return _commit(overlays: changed);
  }

  MediaProjectSnapshot deleteOverlay(String overlayId) {
    final index = overlays.indexWhere(
      (overlay) => overlay.overlayId == overlayId,
    );
    _require(index >= 0, 'overlay not found');
    final changed = overlays.toList()..removeAt(index);
    return _commit(overlays: changed);
  }

  MediaProjectSnapshot _replaceClip(
    MediaProjectTrack track,
    MediaProjectClip clip, {
    bool validateVideoTransitions = false,
  }) {
    final clips = track.clips
        .map((item) => item.clipId == clip.clipId ? clip : item)
        .toList();
    final changed = track.kind == 'video'
        ? _reflow(track, clips)
        : MediaProjectTrack(
            trackId: track.trackId,
            kind: track.kind,
            clips: clips,
          );
    final changedTracks = tracks
        .map((item) => item.trackId == track.trackId ? changed : item)
        .toList();
    if (validateVideoTransitions) {
      _validateVideoTransitionEdits(changedTracks, transitions);
    }
    return _commit(tracks: changedTracks);
  }

  static MediaProjectTrack _reflow(
    MediaProjectTrack track,
    List<MediaProjectClip> clips,
  ) {
    var cursor = 0.0;
    final positioned = <MediaProjectClip>[];
    for (final clip in clips) {
      positioned.add(clip.copyWith(timelineStart: cursor));
      cursor += clip.durationSec;
      _require(
        cursor.isFinite && cursor <= _maxEditTimeSec,
        'video timeline exceeds duration limit',
      );
    }
    return MediaProjectTrack(
      trackId: track.trackId,
      kind: track.kind,
      clips: positioned,
    );
  }

  /// Keep video edits aligned with Core's 30fps transition render preflight.
  /// Split/delete remove transitions that name the changed clip, matching
  /// Timeline.split/delete. Other edits retain their authored transition data
  /// and fail atomically if they would break adjacency, duration, or handles.
  /// Opaque future transition types are retained for Core to report explicitly.
  void _validateVideoTransitionEdits(
    List<MediaProjectTrack> candidateTracks,
    List<MediaProjectTransition> candidateTransitions,
  ) {
    if (candidateTransitions.isEmpty) return;
    final videoTracks = candidateTracks
        .where((track) => track.kind == 'video')
        .toList();
    if (videoTracks.isEmpty) {
      throw _invalid('TRANSITION_REQUIRES_ADJACENT_VIDEO_CLIPS');
    }

    // Core's renderer currently plans transitions against the first video
    // track. A transition outside that sequence cannot be exported safely.
    final clips = videoTracks.first.clips;
    final indexes = <String, int>{
      for (var index = 0; index < clips.length; index++)
        clips[index].clipId: index,
    };
    final assetsById = <String, MediaProjectAsset>{
      for (final asset in assets) asset.assetId: asset,
    };
    final seenBoundaries = <int>{};
    final windows = <(int, int)>[];

    for (final transition in candidateTransitions) {
      final fromIndex = indexes[transition.fromClip];
      final toIndex = indexes[transition.toClip];
      if (fromIndex == null ||
          toIndex == null ||
          toIndex != fromIndex + 1) {
        throw _invalid('TRANSITION_REQUIRES_ADJACENT_VIDEO_CLIPS');
      }
      if (!seenBoundaries.add(toIndex)) {
        throw _invalid('TRANSITION_BOUNDARY_CONFLICT');
      }

      final from = clips[fromIndex];
      final to = clips[toIndex];
      if (transition.durationSec > from.durationSec ||
          transition.durationSec > to.durationSec) {
        throw _invalid('TRANSITION_DURATION_EXCEEDS_CLIP');
      }
      if (transition.transitionType == 'cut') continue;
      if (transition.transitionType != 'dissolve') continue;
      if (transition.durationSec < 1 / 30) {
        throw _invalid('TRANSITION_SHORTER_THAN_OUTPUT_FRAME');
      }

      final frameCount = _frameAt(transition.durationSec);
      final beforeCut = frameCount ~/ 2;
      final afterCut = frameCount - beforeCut;
      final cutFrame = _frameAt(to.timelineStart);
      final startFrame = cutFrame - beforeCut;
      final endFrame = cutFrame + afterCut;
      if (startFrame < _frameAt(from.timelineStart) ||
          endFrame > _frameAt(to.timelineStart + to.durationSec)) {
        throw _invalid('TRANSITION_WINDOW_EXCEEDS_CLIP');
      }

      final leftFrames = cutFrame - _frameAt(from.timelineStart);
      final fromAsset = assetsById[from.mediaAssetId];
      if (fromAsset == null ||
          from.sourceIn + (leftFrames + afterCut) / 30 >
              fromAsset.durationSec ||
          to.sourceIn < beforeCut / 30) {
        throw _invalid('TRANSITION_MEDIA_HANDLES_UNAVAILABLE');
      }
      windows.add((startFrame, endFrame));
    }

    windows.sort((left, right) => left.$1.compareTo(right.$1));
    var previousEnd = -1;
    for (final window in windows) {
      if (window.$1 < previousEnd) {
        throw _invalid('TRANSITION_WINDOWS_OVERLAP');
      }
      previousEnd = window.$2;
    }
  }

  static int _frameAt(double seconds) =>
      double.parse((seconds * 30).toStringAsFixed(6)).round();

  String _localId(String prefix) {
    final used = <String>{
      ...tracks.expand((track) => track.clips.map((clip) => clip.clipId)),
      ...overlays.map((overlay) => overlay.overlayId),
    };
    var index = version + 1;
    var candidate = '$prefix-LOCAL-$index';
    while (used.contains(candidate)) {
      index++;
      candidate = '$prefix-LOCAL-$index';
    }
    return candidate;
  }

  MediaProjectSnapshot _commit({
    List<MediaProjectTrack>? tracks,
    List<MediaProjectTransition>? transitions,
    List<MediaProjectOverlay>? overlays,
    String? formatRatio,
  }) {
    _require(version < _maxTimelineVersion, 'timeline version limit reached');
    final previous = _SnapshotState(
      tracks: this.tracks,
      transitions: this.transitions,
      overlays: this.overlays,
      formatRatio: this.formatRatio,
    );
    return MediaProjectSnapshot._(
      assets: assets,
      tracks: tracks ?? this.tracks,
      transitions: transitions ?? this.transitions,
      overlays: overlays ?? this.overlays,
      formatRatio: formatRatio ?? this.formatRatio,
      version: version + 1,
      history: [..._history, previous],
    );
  }

  MediaProjectSnapshot undo() {
    _require(_history.isNotEmpty, 'there is no local edit to undo');
    _require(version < _maxTimelineVersion, 'timeline version limit reached');
    final previous = _history.last;
    return MediaProjectSnapshot._(
      assets: assets,
      tracks: previous.tracks,
      transitions: previous.transitions,
      overlays: previous.overlays,
      formatRatio: previous.formatRatio,
      version: version + 1,
      history: _history.take(_history.length - 1).toList(),
    );
  }

  Map<String, Object?> toJson() => <String, Object?>{
    'version': version,
    'format_ratio': formatRatio,
    'assets': assets.map((asset) => asset.toJson()).toList(growable: false),
    'tracks': tracks.map((track) => track.toJson()).toList(growable: false),
    'transitions': transitions
        .map((transition) => transition.toJson())
        .toList(growable: false),
    'overlays': overlays
        .map((overlay) => overlay.toJson())
        .toList(growable: false),
    'approval_required': true,
  };
}
