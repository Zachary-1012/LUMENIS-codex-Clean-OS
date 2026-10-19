import 'dart:convert';
import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/features/bmp08/bmp08_repository.dart';

Map<String, dynamic> fixture({int version = 1, String corrected = 'Reviewed'}) {
  final id = version == 1 ? 'ART-0000000000000001' : 'ART-0000000000000002';
  final digest = List.filled(64, version == 1 ? 'a' : 'b').join();
  return {'ok': true, 'result': {
    'artifact': {'artifact_id': id, 'sha256': digest},
    'document': {
      'kind': 'podcast_episode', 'work_id': 'WORK-owned', 'title': 'Episode',
      'version': version, 'draft_digest': digest,
      'parent_artifact_id': version == 1 ? null : 'ART-0000000000000001',
      'markdown': 'Episode\nDescription\n\n[00:00:00.000] Host $corrected',
      'citations': [],
      'contract': {'id': 'lumenis.podcast-plan', 'version': '1', 'required_payload_paths': ['podcast_plan']},
      'payload': {'preserved': 'User note', 'podcast_plan': {
        'version': 1, 'title': 'Episode', 'description': 'Description', 'language': 'en',
        'revision': version, 'segments': [{
          'segment_id': 'stable-a', 'media_asset_id': 'MEDIA-owned', 'source_in': 3.0, 'source_out': 7.0,
          'original_text': 'Original', 'corrected_text': corrected,
          'speaker': 'Host', 'chapter_title': 'Opening', 'evidence_refs': [],
        }],
      }},
    },
    'receipt': {'ref': id, 'sha256': digest, 'work_id': 'WORK-owned', 'version': version, 'draft_digest': digest,
      'constraint_observations': {'committed_bytes_match': true, 'parent_chain_verified': true,
        'media_lineage': 'W4_W6_NOT_VERIFIED'}},
  }};
}

void main() {
  test('stable ID revisions preserve source text, metadata and parent snapshot', () {
    final original = Bmp08SavedEpisode.fromResponse(fixture());
    final body = original.revisionBody({'stable-a': 'Corrected'}, 'podcast-request-001');
    final plan = (body['payload'] as Map)['podcast_plan'] as Map;
    expect(body.keys.toSet(), {'title','markdown','kind','payload','citations','contract','request_id',
      'work_id','previous_artifact_id','expected_draft_digest'});
    expect(body['previous_artifact_id'], original.artifactId);
    expect(body['expected_draft_digest'], original.draftDigest);
    expect(body['markdown'], 'Episode\nDescription\n\n[00:00:00.000] Host Corrected');
    expect(plan['revision'], 2);
    expect(plan['segments'][0]['original_text'], 'Original');
    expect(plan['segments'][0]['corrected_text'], 'Corrected');
    expect((body['payload'] as Map)['preserved'], 'User note');
    expect(original.segments[0]['corrected_text'], 'Reviewed');
    expect(() => original.revisionBody({'missing': 'Text'}, 'request-002'), throwsFormatException);
    expect(() => original.revisionBody({'stable-a': ' '}, 'request-003'), throwsFormatException);
  });

  test('malformed results and duplicate stable identities fail closed', () {
    final mutations = <void Function(Map<String, dynamic>)>[
      (v) => v['ok'] = false,
      (v) => v['result']['document']['payload']['podcast_plan']['version'] = 1.0,
      (v) => v['result']['document']['payload']['podcast_plan']['segments'][0]['extra'] = true,
      (v) => v['result']['document']['payload']['podcast_plan']['segments'][0]['audio_stream_index'] = 0,
      (v) { v['result']['document']['payload']['podcast_plan']['version'] = 2;
        v['result']['document']['payload']['podcast_plan']['segments'][0]['audio_stream_index'] = -1; },
      (v) { v['result']['document']['payload']['podcast_plan']['version'] = 2;
        v['result']['document']['payload']['podcast_plan']['segments'][0]['audio_stream_index'] = 1.0; },
      (v) => v['result']['receipt']['draft_digest'] = 'stale',
      (v) => v['result']['receipt']['constraint_observations']['committed_bytes_match'] = false,
      (v) => v['result']['receipt']['constraint_observations']['media_lineage'] = 'verified',
      (v) => v['result']['document']['payload']['podcast_plan']['segments'][0]['source_out'] = 0,
      (v) { final list = v['result']['document']['payload']['podcast_plan']['segments'] as List; list.add(Map.of(list.first)); },
    ];
    for (final mutate in mutations) {
      final value = fixture(); mutate(value);
      expect(() => Bmp08SavedEpisode.fromResponse(value), throwsFormatException);
    }
  });

  test('version 2 preserves explicit source audio stream during revision', () {
    final value = fixture();
    value['result']['document']['payload']['podcast_plan']['version'] = 2;
    value['result']['document']['payload']['podcast_plan']['segments'][0]['audio_stream_index'] = 3;
    final original = Bmp08SavedEpisode.fromResponse(value);
    final body = original.revisionBody({'stable-a': 'Corrected'}, 'podcast-stream-001');
    final plan = (body['payload'] as Map)['podcast_plan'] as Map;
    expect(plan['version'], 2);
    expect(plan['segments'][0]['audio_stream_index'], 3);
    expect(plan['segments'][0]['source_in'], 3.0);
    expect(plan['segments'][0]['original_text'], 'Original');
  });

  test('repository sends exact Shared revision then reopens committed artifact', () async {
    final requests = <Map<String, dynamic>>[];
    final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    addTearDown(() => server.close(force: true));
    server.listen((request) async {
      final text = await utf8.decoder.bind(request).join();
      requests.add({'method': request.method, 'path': request.uri.path,
        'scope': request.headers.value('X-Lumenis-Workspace-Scope'),
        'body': text.isEmpty ? null : jsonDecode(text)});
      request.response.headers.contentType = ContentType.json;
      request.response.write(jsonEncode(fixture(version: 2, corrected: 'Corrected')));
      await request.response.close();
    });
    final repository = CoreBmp08Repository(client: LumenisCoreClient(baseUrl: 'http://127.0.0.1:${server.port}'));
    final parent = Bmp08SavedEpisode.fromResponse(fixture());
    final saved = await repository.saveEpisode(parent, {'stable-a': 'Corrected'}, 'podcast-request-001');
    expect(saved.version, 2);
    expect(requests.map((r) => r['method']), ['POST', 'GET']);
    expect(requests[0]['path'], '/api/experience/saved-work');
    expect(requests[1]['path'], '/api/experience/saved-work/ART-0000000000000002');
    expect(requests[0]['body'], parent.revisionBody({'stable-a': 'Corrected'}, 'podcast-request-001'));
    for (final request in requests) {
      expect(jsonDecode(request['scope'] as String), {'scope_kind': 'shared_workspace', 'version': 1});
    }
  });

  test('repository propagates denial and never claims a readback on failed save', () async {
    final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    addTearDown(() => server.close(force: true));
    var calls = 0;
    server.listen((request) async {
      calls++; await request.drain<void>();
      request.response.statusCode = 403;
      request.response.headers.contentType = ContentType.json;
      request.response.write(jsonEncode({'ok': false, 'error': 'WORK_PERMISSION_DENIED'}));
      await request.response.close();
    });
    final repository = CoreBmp08Repository(client: LumenisCoreClient(baseUrl: 'http://127.0.0.1:${server.port}'));
    await expectLater(repository.saveEpisode(Bmp08SavedEpisode.fromResponse(fixture()),
      {'stable-a': 'Corrected'}, 'podcast-request-002'), throwsA(isA<LumenisCoreException>()));
    expect(calls, 1);
  });

  test('mismatched committed payload is not a successful save', () async {
    final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    addTearDown(() => server.close(force: true));
    server.listen((request) async {
      await request.drain<void>();
      request.response.headers.contentType = ContentType.json;
      request.response.write(jsonEncode(fixture(version: 2, corrected: 'Wrong payload')));
      await request.response.close();
    });
    final repository = CoreBmp08Repository(client: LumenisCoreClient(baseUrl: 'http://127.0.0.1:${server.port}'));
    await expectLater(repository.saveEpisode(Bmp08SavedEpisode.fromResponse(fixture()),
      {'stable-a': 'Corrected'}, 'podcast-request-003'), throwsFormatException);
  });
}
