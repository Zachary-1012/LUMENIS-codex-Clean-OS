import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/features/shared/sh01/media_project_snapshot.dart';

MediaProjectAsset videoAsset({int audioStreams = 2}) {
  const sha =
      'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa';
  return MediaProjectAsset(
    assetId: 'MEDIA-${sha.substring(0, 16)}',
    filename: 'interview.mp4',
    sha256: sha,
    durationSec: 20,
    mediaKind: audioStreams == 0 ? 'video' : 'video_audio',
    hasVideo: true,
    audioStreamCount: audioStreams,
  );
}

MediaProjectAsset audioAsset() {
  const sha =
      'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb';
  return MediaProjectAsset(
    assetId: 'MEDIA-${sha.substring(0, 16)}',
    filename: 'music.wav',
    sha256: sha,
    durationSec: 20,
    mediaKind: 'audio',
    hasVideo: false,
    audioStreamCount: 1,
  );
}

MediaProjectAsset replacementVideoAsset() {
  const sha =
      'cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc';
  return MediaProjectAsset(
    assetId: 'MEDIA-${sha.substring(0, 16)}',
    filename: 'replacement.mp4',
    sha256: sha,
    durationSec: 20,
    mediaKind: 'video_audio',
    hasVideo: true,
    audioStreamCount: 2,
  );
}

MediaProjectSnapshot _videoProject({int clipCount = 3}) {
  final asset = videoAsset();
  var snapshot = MediaProjectSnapshot.empty(inspectedAssets: [asset]);
  for (var index = 0; index < clipCount; index++) {
    snapshot = snapshot.addClip(
      asset.assetId,
      trackId: 'video',
      sourceIn: 1,
      sourceOut: 6,
      audioRole: 'muted',
      clipId: 'video-$index',
    );
  }
  return snapshot;
}

MediaProjectTransition _dissolve(String from, String to) =>
    MediaProjectTransition(
      fromClip: from,
      toClip: to,
      transitionType: 'dissolve',
      durationSec: 0.5,
      reason: 'soft scene change',
    );

MediaProjectSnapshot _withTransitions(
  MediaProjectSnapshot snapshot,
  List<MediaProjectTransition> transitions,
) {
  final payload = snapshot.toJson();
  payload['transitions'] = transitions
      .map((transition) => transition.toJson())
      .toList();
  return MediaProjectSnapshot.fromJson(
    payload,
    inspectedAssets: snapshot.assets,
  );
}

Map<String, Object?> pythonTimelinePayload() => <String, Object?>{
  'version': 7,
  'format_ratio': '16:9',
  'assets': [
    <String, Object?>{
      'asset_id': 'MEDIA-aaaaaaaaaaaaaaaa',
      'filename': 'interview.mp4',
      'sha256':
          'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
      'duration_sec': 20.0,
      'media_kind': 'video_audio',
      'has_video': true,
      'audio_stream_count': 2,
      'evidence_refs': <String>[],
      'rights_status': 'unknown',
    },
    <String, Object?>{
      'asset_id': 'MEDIA-bbbbbbbbbbbbbbbb',
      'filename': 'music.wav',
      'sha256':
          'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
      'duration_sec': 20.0,
      'media_kind': 'audio',
      'has_video': false,
      'audio_stream_count': 1,
      'evidence_refs': <String>[],
      'rights_status': 'unknown',
    },
  ],
  'tracks': [
    <String, Object?>{
      'track_id': 'video',
      'kind': 'video',
      'clips': [
        <String, Object?>{
          'clip_id': 'clip-server-01',
          'media_asset_id': 'MEDIA-aaaaaaaaaaaaaaaa',
          'source_in': 1.0,
          'source_out': 9.0,
          'timeline_start': 0.0,
          'track_id': 'video',
          'purpose': '',
          'audio_role': 'muted',
          'audio_mix': <String, Object?>{
            'volume': 1.0,
            'fade_in_sec': 0.0,
            'fade_out_sec': 0.0,
            'ducking': false,
          },
          'evidence_refs': <String>[],
          'audio_stream_index': null,
        },
        <String, Object?>{
          'clip_id': 'clip-server-02',
          'media_asset_id': 'MEDIA-aaaaaaaaaaaaaaaa',
          'source_in': 9.0,
          'source_out': 17.0,
          'timeline_start': 8.0,
          'track_id': 'video',
          'purpose': '',
          'audio_role': 'muted',
          'audio_mix': <String, Object?>{
            'volume': 1.0,
            'fade_in_sec': 0.0,
            'fade_out_sec': 0.0,
            'ducking': false,
          },
          'evidence_refs': <String>[],
          'audio_stream_index': null,
        },
      ],
    },
    <String, Object?>{
      'track_id': 'music',
      'kind': 'bgm',
      'clips': [
        <String, Object?>{
          'clip_id': 'clip-audio-01',
          'media_asset_id': 'MEDIA-bbbbbbbbbbbbbbbb',
          'source_in': 1.0,
          'source_out': 9.0,
          'timeline_start': 3.25,
          'track_id': 'music',
          'purpose': '',
          'audio_role': 'bgm',
          'audio_mix': <String, Object?>{
            'volume': 0.4,
            'fade_in_sec': 0.5,
            'fade_out_sec': 0.75,
            'ducking': false,
          },
          'evidence_refs': <String>[],
          'audio_stream_index': 0,
        },
      ],
    },
  ],
  'transitions': [
    <String, Object?>{
      'from_clip': 'clip-server-01',
      'to_clip': 'clip-server-02',
      'transition_type': 'future_wipe',
      'duration_sec': 0.5,
      'reason': 'retain for explicit Core validation',
    },
  ],
  'overlays': [
    <String, Object?>{
      'overlay_id': 'overlay-server-01',
      'kind': 'caption',
      'start_sec': 1.0,
      'end_sec': 2.0,
      'text': 'Verified caption',
    },
  ],
  'approval_required': true,
};

void main() {
  test('format edits preserve sources and survive serialization and undo', () {
    final original = _videoProject();
    for (final ratio in MediaProjectSnapshot.formatRatios) {
      final changed = original.setFormatRatio(ratio);
      final reopened = MediaProjectSnapshot.fromJson(
        changed.toJson(),
        inspectedAssets: original.assets,
      );
      expect(reopened.formatRatio, ratio);
      expect(reopened.durationSec, original.durationSec);
      expect(reopened.toJson()['tracks'], original.toJson()['tracks']);
      expect(reopened.toJson()['assets'], original.toJson()['assets']);
      if (ratio == original.formatRatio) {
        expect(identical(changed, original), isTrue);
      } else {
        expect(changed.version, original.version + 1);
        expect(changed.undo().formatRatio, original.formatRatio);
      }
    }
    expect(() => original.setFormatRatio('0:0'), throwsFormatException);
    expect(original.formatRatio, '9:16');
  });

  test(
    'inspector adjustment is atomic and one undo restores the prior edit',
    () {
      final before = MediaProjectSnapshot.empty(inspectedAssets: [audioAsset()])
          .addAudioTrack('music', audioRole: 'bgm')
          .addClip('MEDIA-bbbbbbbbbbbbbbbb', trackId: 'music', sourceOut: 8);
      final id = before.tracks.last.clips.single.clipId;
      final after = before.adjustClip(
        id,
        sourceIn: 2,
        sourceOut: 6,
        timelineStart: 3.25,
        audioMix: const MediaProjectAudioMix(volume: 0.25, fadeInSec: 0.5),
        audioRole: 'bgm',
        audioStreamIndex: 0,
      );
      final changed = after.tracks.last.clips.single;
      expect(changed.sourceIn, 2);
      expect(changed.sourceOut, 6);
      expect(changed.timelineStart, 3.25);
      expect(changed.audioMix.volume, 0.25);
      expect(after.version, before.version + 1);
      expect(after.undo().tracks.last.toJson(), before.tracks.last.toJson());
      expect(
        () => before.adjustClip(
          id,
          sourceIn: 2,
          sourceOut: 6,
          timelineStart: 3.25,
          audioMix: const MediaProjectAudioMix(fadeInSec: 5),
          audioRole: 'bgm',
          audioStreamIndex: 0,
        ),
        throwsFormatException,
      );
      expect(before.tracks.last.clips.single.sourceIn, 0);
    },
  );

  test(
    'adding an inspected source preserves history and cannot replace one',
    () {
      final before = MediaProjectSnapshot.empty(inspectedAssets: [videoAsset()])
          .addClip(
            'MEDIA-aaaaaaaaaaaaaaaa',
            trackId: 'video',
            sourceOut: 5,
            audioRole: 'muted',
          );
      final appended = before.addInspectedAsset(audioAsset());
      expect(appended.assets, hasLength(2));
      expect(appended.tracks.single.toJson(), before.tracks.single.toJson());
      expect(appended.undo().tracks.single.clips, isEmpty);
      // Undoing timeline edits never drops registered source provenance.
      expect(appended.undo().assets, hasLength(2));
      expect(
        () => appended.addInspectedAsset(videoAsset()),
        throwsFormatException,
      );
      expect(before.assets, hasLength(1));
    },
  );

  test(
    'round-trips the sanitized Python timeline schema and keeps unknown transitions',
    () {
      final payload = pythonTimelinePayload();
      final snapshot = MediaProjectSnapshot.fromJson(
        payload,
        inspectedAssets: [videoAsset(), audioAsset()],
      );

      expect(snapshot.toJson(), equals(payload));
      expect(snapshot.transitions.single.transitionType, 'future_wipe');
      expect(
        snapshot.assets.every(
          (asset) =>
              asset.rightsStatus == 'unknown' && asset.evidenceRefs.isEmpty,
        ),
        isTrue,
      );
      expect(snapshot.toJson().toString(), isNot(contains(r'C:\')));
      final deleted = snapshot.deleteVideoClip('clip-server-01');
      expect(deleted.tracks.first.clips.map((clip) => clip.clipId), [
        'clip-server-02',
      ]);
      expect(deleted.transitions, isEmpty);
      expect(deleted.undo().transitions.single.transitionType, 'future_wipe');
    },
  );

  test(
    'supports manual video edits, audio offsets, split fades, stream selection and overlays',
    () {
      var snapshot = MediaProjectSnapshot.empty(
        inspectedAssets: [videoAsset(), audioAsset()],
      );
      snapshot = snapshot.addClip(
        'MEDIA-aaaaaaaaaaaaaaaa',
        trackId: 'video',
        sourceOut: 12,
        audioRole: 'muted',
      );
      final firstId = snapshot.tracks.first.clips.first.clipId;
      snapshot = snapshot.addClip(
        'MEDIA-aaaaaaaaaaaaaaaa',
        trackId: 'video',
        sourceOut: 8,
        audioRole: 'muted',
      );
      final secondId = snapshot.tracks.first.clips.last.clipId;
      snapshot = snapshot.trimClip(firstId, sourceIn: 1, sourceOut: 11);
      snapshot = snapshot.splitClip(firstId, atSec: 6);
      expect(snapshot.tracks.first.clips.map((clip) => clip.clipId), [
        '$firstId-a',
        '$firstId-b',
        secondId,
      ]);
      snapshot = snapshot.reorderVideoClip(secondId, newIndex: 0);
      snapshot = snapshot.deleteVideoClip(secondId);
      expect(snapshot.tracks.first.clips.map((clip) => clip.clipId), [
        '$firstId-a',
        '$firstId-b',
      ]);

      snapshot = snapshot.addAudioTrack('music', audioRole: 'bgm');
      snapshot = snapshot.addClip(
        'MEDIA-bbbbbbbbbbbbbbbb',
        trackId: 'music',
        sourceIn: 1,
        sourceOut: 9,
        timelineStart: 3,
      );
      final audioId = snapshot.tracks.last.clips.single.clipId;
      snapshot = snapshot.setAudioMix(
        audioId,
        const MediaProjectAudioMix(volume: 0.35, fadeInSec: 2, fadeOutSec: 3),
      );
      snapshot = snapshot.splitClip(audioId, atSec: 5);
      final audioClips = snapshot.tracks.last.clips;
      expect(audioClips.map((clip) => clip.timelineStart), [3, 7]);
      expect(audioClips.map((clip) => clip.audioStreamIndex), [0, 0]);
      expect(audioClips.map((clip) => clip.audioMix.volume), [0.35, 0.35]);
      expect(audioClips.map((clip) => clip.audioMix.fadeInSec), [2, 0]);
      expect(audioClips.map((clip) => clip.audioMix.fadeOutSec), [0, 3]);

      snapshot = snapshot.addOverlay(
        kind: 'caption',
        startSec: 1,
        endSec: 2,
        text: 'Manual caption',
      );
      expect(snapshot.overlays.single.text, 'Manual caption');
    },
  );

  test(
    'video edits preserve valid transitions and reject broken handles or adjacency atomically',
    () {
      final initial = _videoProject();
      final clips = initial.tracks.first.clips;
      final before = _withTransitions(initial, [
        _dissolve(clips[0].clipId, clips[1].clipId),
      ]);

      final trimmed = before.trimClip(
        clips[1].clipId,
        sourceIn: 0.5,
        sourceOut: 5.5,
      );
      expect(trimmed.transitions, before.transitions);
      expect(trimmed.tracks.first.clips[1].sourceIn, 0.5);

      expect(
        () => before.trimClip(clips[1].clipId, sourceIn: 0.1, sourceOut: 5.1),
        throwsFormatException,
      );
      expect(
        before.toJson(),
        equals(
          _withTransitions(initial, [
            _dissolve(clips[0].clipId, clips[1].clipId),
          ]).toJson(),
        ),
      );

      final shiftedPair = before.reorderVideoClip(clips[2].clipId, newIndex: 0);
      expect(shiftedPair.transitions, before.transitions);
      expect(
        () => before.reorderVideoClip(clips[1].clipId, newIndex: 2),
        throwsFormatException,
      );
      expect(before.tracks.first.clips.map((clip) => clip.clipId), [
        'video-0',
        'video-1',
        'video-2',
      ]);
    },
  );

  test(
    'free video layers preserve positions, placement, crop, and saved versions',
    () {
      final asset = videoAsset();
      final before = _videoProject().addVideoTrack('inset');
      final placed = before
          .addClip(
            asset.assetId,
            trackId: 'inset',
            sourceIn: 1,
            sourceOut: 5,
            timelineStart: 2,
            audioRole: 'muted',
            clipId: 'inset-clip',
          )
          .setVideoPlacement(
            'inset-clip',
            const MediaVideoPlacement(
              x: 0.5,
              y: 0.5,
              width: 0.5,
              height: 0.5,
              opacity: 0.75,
            ),
          );
      final payload = placed.toJson();
      final restored = MediaProjectSnapshot.fromJson(
        payload,
        inspectedAssets: placed.assets,
      );
      expect(restored.toJson(), payload);
      expect(restored.tracks.last.layout, 'free');
      expect(restored.tracks.last.clips.single.timelineStart, 2);
      expect(restored.tracks.last.clips.single.videoPlacement!.opacity, 0.75);
      final split = restored.splitClip('inset-clip', atSec: 3);
      expect(split.tracks.last.clips.map((c) => c.timelineStart), [2, 4]);
      expect(split.tracks.last.clips.map((c) => c.videoPlacement!.opacity), [
        0.75,
        0.75,
      ]);
      expect(split.undo().tracks.last.toJson(), restored.tracks.last.toJson());
      expect(
        () => restored.reorderVideoClip('inset-clip', newIndex: 0),
        throwsFormatException,
      );
      expect(before.tracks.last.clips, isEmpty);
    },
  );

  test('split, delete, and undo keep transition references coherent', () {
    final initial = _videoProject(clipCount: 4);
    final clips = initial.tracks.first.clips;
    final before = _withTransitions(initial, [
      _dissolve(clips[0].clipId, clips[1].clipId),
      _dissolve(clips[2].clipId, clips[3].clipId),
    ]);

    final split = before.splitClip(clips[1].clipId, atSec: 3);
    expect(split.transitions.length, 2);
    expect(split.transitions[0].fromClip, 'video-0');
    expect(split.transitions[0].toClip, 'video-1-a');
    expect(split.transitions[0].durationSec, before.transitions[0].durationSec);
    expect(split.transitions[1], before.transitions[1]);
    expect(split.tracks.first.clips.map((clip) => clip.clipId), [
      'video-0',
      'video-1-a',
      'video-1-b',
      'video-2',
      'video-3',
    ]);
    final undone = split.undo();
    expect(undone.tracks.first.toJson(), before.tracks.first.toJson());
    expect(undone.transitions, before.transitions);

    final deleted = before.deleteVideoClip(clips[1].clipId);
    expect(deleted.transitions, [before.transitions[1]]);
    expect(
      deleted.transitions.every(
        (transition) =>
            transition.fromClip != clips[1].clipId &&
            transition.toClip != clips[1].clipId,
      ),
      isTrue,
    );
  });

  test(
    'source replacement preserves valid transition handles and undo state',
    () {
      final initial = _videoProject();
      final clips = initial.tracks.first.clips;
      final before = _withTransitions(initial, [
        _dissolve(clips[0].clipId, clips[1].clipId),
        _dissolve(clips[1].clipId, clips[2].clipId),
      ]).addInspectedAsset(replacementVideoAsset());
      final targetBefore = before.tracks.first.clips[1];

      final replaced = before.replaceClipSource(
        targetBefore.clipId,
        mediaAssetId: 'MEDIA-cccccccccccccccc',
        sourceIn: 0.5,
        audioRole: 'muted',
        audioStreamIndex: null,
      );
      final targetAfter = replaced.tracks.first.clips[1];
      expect(targetAfter.mediaAssetId, 'MEDIA-cccccccccccccccc');
      expect(targetAfter.durationSec, targetBefore.durationSec);
      expect(targetAfter.timelineStart, targetBefore.timelineStart);
      expect(replaced.transitions, before.transitions);
      expect(
        replaced.undo().tracks.first.toJson(),
        before.tracks.first.toJson(),
      );
      expect(replaced.undo().transitions, before.transitions);

      expect(
        () => before.replaceClipSource(
          targetBefore.clipId,
          mediaAssetId: 'MEDIA-cccccccccccccccc',
          sourceIn: 0.1,
          audioRole: 'muted',
          audioStreamIndex: null,
        ),
        throwsFormatException,
      );
      expect(
        before.tracks.first.toJson(),
        _withTransitions(initial, [
          _dissolve(clips[0].clipId, clips[1].clipId),
          _dissolve(clips[1].clipId, clips[2].clipId),
        ]).tracks.first.toJson(),
      );
    },
  );

  test(
    'exposes undo and duration state with audio delete and stream/role changes',
    () {
      var snapshot = MediaProjectSnapshot.empty(
        inspectedAssets: [videoAsset(), audioAsset()],
      );
      expect(snapshot.canUndo, isFalse);
      snapshot = snapshot.addAudioTrack('music', audioRole: 'bgm');
      snapshot = snapshot.addClip(
        'MEDIA-bbbbbbbbbbbbbbbb',
        trackId: 'music',
        sourceOut: 4,
        timelineStart: 5,
      );
      final audioId = snapshot.tracks.last.clips.single.clipId;
      expect(snapshot.canUndo, isTrue);
      expect(snapshot.durationSec, 9);
      snapshot = snapshot.deleteAudioClip(audioId);
      expect(snapshot.tracks.last.clips, isEmpty);

      snapshot = snapshot.addClip(
        'MEDIA-aaaaaaaaaaaaaaaa',
        trackId: 'video',
        sourceOut: 8,
        audioStreamIndex: 1,
      );
      final videoId = snapshot.tracks.first.clips.single.clipId;
      snapshot = snapshot.setAudioStreamIndex(videoId, audioStreamIndex: 0);
      expect(snapshot.tracks.first.clips.single.audioStreamIndex, 0);
      snapshot = snapshot.setAudioRole(videoId, audioRole: 'muted');
      expect(snapshot.tracks.first.clips.single.audioStreamIndex, isNull);
      snapshot = snapshot.setAudioRole(
        videoId,
        audioRole: 'original',
        audioStreamIndex: 1,
      );
      expect(snapshot.tracks.first.clips.single.audioStreamIndex, 1);
    },
  );

  test(
    'rejects malformed, non-finite, negative, out-of-range and forged metadata',
    () {
      final base = pythonTimelinePayload();
      final inspected = [videoAsset(), audioAsset()];

      void rejects(Map<String, Object?> payload) {
        expect(
          () => MediaProjectSnapshot.fromJson(
            payload,
            inspectedAssets: inspected,
          ),
          throwsFormatException,
        );
      }

      final unknownField = Map<String, Object?>.from(base)
        ..['source_path'] = r'C:\private\clip.mp4';
      rejects(unknownField);

      final badTime = pythonTimelinePayload();
      (((badTime['tracks'] as List).first as Map)['clips'] as List)
              .first['source_in'] =
          double.infinity;
      rejects(badTime);

      final negative = pythonTimelinePayload();
      (((negative['tracks'] as List).first as Map)['clips'] as List)
              .first['timeline_start'] =
          -1;
      rejects(negative);

      final tooLong = pythonTimelinePayload();
      (((tooLong['tracks'] as List).first as Map)['clips'] as List)
              .first['source_out'] =
          21;
      rejects(tooLong);

      final forgedRights = pythonTimelinePayload();
      ((forgedRights['assets'] as List).first as Map)['rights_status'] =
          'cleared';
      rejects(forgedRights);
    },
  );

  test('undo restores edits while advancing the serialized version', () {
    final initial = MediaProjectSnapshot.empty(inspectedAssets: [videoAsset()]);
    final edited = initial.addClip(
      'MEDIA-aaaaaaaaaaaaaaaa',
      trackId: 'video',
      sourceOut: 5,
      audioRole: 'muted',
    );
    final undone = edited.undo();

    expect(edited.version, 2);
    expect(undone.version, 3);
    expect(undone.tracks.first.clips, isEmpty);
    expect(undone.toJson()['version'], 3);
  });
}
