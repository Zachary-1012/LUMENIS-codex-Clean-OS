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
      expect(
        () => snapshot.deleteVideoClip('clip-server-01'),
        throwsFormatException,
      );
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
