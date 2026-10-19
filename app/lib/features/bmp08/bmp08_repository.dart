import 'dart:convert';
import 'package:flutter/foundation.dart' show mapEquals, listEquals;
import '../../core/lumenis_core_client.dart';
import 'bmp08_snapshot.dart';

abstract interface class Bmp08Repository {
  Future<Bmp08Snapshot> load();
}

class CoreBmp08Repository implements Bmp08Repository, Bmp08SavedWorkRepository {
  CoreBmp08Repository({required this._client});

  final LumenisCoreClient _client;

  @override
  Future<Map<String, dynamic>> listEpisodes({String? domainId, String? cursor}) =>
      _client.listPodcastWork(domainId: domainId, cursor: cursor);

  @override
  Future<Bmp08SavedEpisode> reopenEpisode(String artifactId, {String? domainId}) async {
    final episode = Bmp08SavedEpisode.fromResponse(
      await _client.reopenPodcastWork(artifactId, domainId: domainId));
    if (episode.artifactId != artifactId) {
      throw const FormatException('Podcast readback identity mismatch.');
    }
    return episode;
  }

  @override
  Future<Bmp08SavedEpisode> saveEpisode(Bmp08SavedEpisode parent,
      Map<String, String> edits, String requestId, {String? domainId}) async {
    final body = parent.revisionBody(edits, requestId);
    final saved = Bmp08SavedEpisode.fromResponse(
      await _client.savePodcastWork(body: body, domainId: domainId));
    final reopened = await reopenEpisode(saved.artifactId, domainId: domainId);
    if (reopened.workId != parent.workId || reopened.version != parent.version + 1 ||
        reopened.document['parent_artifact_id'] != parent.artifactId ||
        !_sameJson(reopened.document['payload'], body['payload']) ||
        reopened.document['markdown'] != body['markdown'] ||
        !_sameJson(reopened.document, saved.document)) {
      throw const FormatException('Podcast committed revision mismatch.');
    }
    return reopened;
  }

  @override
  Future<Bmp08Snapshot> load() async {
    final response = await _client.screen('BMP-08');
    return Bmp08Snapshot.fromResponse(response);
  }
}


/// Optional persistence capability keeps read-only/legacy screen adapters valid.
abstract interface class Bmp08SavedWorkRepository {
  Future<Map<String, dynamic>> listEpisodes({String? domainId, String? cursor});
  Future<Bmp08SavedEpisode> reopenEpisode(String artifactId, {String? domainId});
  Future<Bmp08SavedEpisode> saveEpisode(Bmp08SavedEpisode parent,
      Map<String, String> edits, String requestId, {String? domainId});
}

bool _sameJson(Object? a, Object? b) {
  if (a is Map && b is Map) {
    return mapEquals(a.map((k, v) => MapEntry(k, true)), b.map((k, v) => MapEntry(k, true))) &&
        a.keys.every((key) => _sameJson(a[key], b[key]));
  }
  if (a is List && b is List) {
    return a.length == b.length && List.generate(a.length, (i) => _sameJson(a[i], b[i])).every((v) => v);
  }
  return a == b;
}

Map<String, dynamic> _podcastMap(Object? value) {
  if (value is! Map<String, dynamic>) throw const FormatException('Invalid podcast object.');
  return value;
}

String _podcastText(Object? value) {
  if (value is! String || value.trim().isEmpty) throw const FormatException('Invalid podcast text.');
  return value;
}

/// Only a fresh SavedWork read authorizes presentation. Storage is not audio
/// rendering, source-fact validation, or a grant to publish/train.
class Bmp08SavedEpisode {
  Bmp08SavedEpisode._(this._document, this.artifactId);
  final Map<String, dynamic> _document;
  final String artifactId;
  // Return detached JSON so UI edits cannot mutate the optimistic parent.
  Map<String, dynamic> get document => jsonDecode(jsonEncode(_document)) as Map<String, dynamic>;
  Map<String, dynamic> get plan => _podcastMap(_podcastMap(document['payload'])['podcast_plan']);
  List<Map<String, dynamic>> get segments => (plan['segments'] as List).map(_podcastMap).toList();
  String get title => _document['title'] as String;
  String get workId => _document['work_id'] as String;
  int get version => _document['version'] as int;
  String get draftDigest => _document['draft_digest'] as String;

  factory Bmp08SavedEpisode.fromResponse(Map<String, dynamic> response) {
    if (response['ok'] != true) throw const FormatException('Podcast result unavailable.');
    final result = _podcastMap(response['result']);
    final doc = _podcastMap(result['document']);
    final artifact = _podcastMap(result['artifact']);
    final receipt = _podcastMap(result['receipt']);
    final observations = _podcastMap(receipt['constraint_observations']);
    final contract = _podcastMap(doc['contract']);
    final id = _podcastText(artifact['artifact_id']);
    final digest = RegExp(r'^[0-9a-f]{64}$');
    if (!RegExp(r'^ART-[0-9a-f]{16}$').hasMatch(id) ||
        doc['kind'] != 'podcast_episode' || doc['version'] is! int || (doc['version'] as int) < 1 ||
        !digest.hasMatch(_podcastText(doc['draft_digest'])) ||
        !digest.hasMatch(_podcastText(artifact['sha256'])) ||
        receipt['ref'] != id || receipt['sha256'] != artifact['sha256'] ||
        receipt['work_id'] != doc['work_id'] || receipt['version'] != doc['version'] ||
        receipt['draft_digest'] != doc['draft_digest'] ||
        observations['committed_bytes_match'] != true || observations['parent_chain_verified'] != true ||
        observations['media_lineage'] != 'W4_W6_NOT_VERIFIED' ||
        contract['id'] != 'lumenis.podcast-plan' || contract['version'] != '1' ||
        !listEquals(contract['required_payload_paths'] as List?, ['podcast_plan']) ||
        doc['citations'] is! List) {
      throw const FormatException('Invalid podcast receipt or contract.');
    }
    _podcastText(doc['work_id']); _podcastText(doc['title']); _podcastText(doc['markdown']);
    final plan = _podcastMap(_podcastMap(doc['payload'])['podcast_plan']);
    if (!listEquals((plan.keys.toList()..sort()),
        (['version', 'title', 'description', 'language', 'revision', 'segments']..sort())) ||
        plan['version'] is! int || ![1, 2].contains(plan['version']) || plan['revision'] is! int || (plan['revision'] as int) < 1 ||
        plan['segments'] is! List || (plan['segments'] as List).isEmpty || (plan['segments'] as List).length > 512) {
      throw const FormatException('Invalid podcast plan.');
    }
    for (final key in ['title', 'description', 'language']) { _podcastText(plan[key]); }
    final ids = <String>{};
    num duration = 0;
    var hasStream = false;
    for (final raw in plan['segments'] as List) {
      final segment = _podcastMap(raw);
      final requiredKeys = <String>{'segment_id', 'media_asset_id', 'source_in', 'source_out',
        'original_text', 'corrected_text', 'speaker', 'chapter_title', 'evidence_refs'};
      if (!segment.keys.toSet().containsAll(requiredKeys) ||
          segment.keys.any((key) => !requiredKeys.contains(key) && key != 'audio_stream_index')) {
        throw const FormatException('Invalid podcast segment fields.');
      }
      if (segment.containsKey('audio_stream_index')) {
        if (segment['audio_stream_index'] != null &&
            (segment['audio_stream_index'] is! int || (segment['audio_stream_index'] as int) < 0)) {
          throw const FormatException('Invalid podcast stream.');
        }
        hasStream = true;
      }
      for (final key in ['segment_id', 'media_asset_id', 'original_text', 'corrected_text', 'speaker', 'chapter_title']) {
        _podcastText(segment[key]);
      }
      if (!ids.add(segment['segment_id'] as String) || segment['evidence_refs'] is! List ||
          (segment['evidence_refs'] as List).any((v) => v is! String || v.trim().isEmpty)) {
        throw const FormatException('Invalid podcast segment identity.');
      }
      final start = segment['source_in']; final end = segment['source_out'];
      if (start is! num || end is! num || !start.isFinite || !end.isFinite || start < 0 || end <= start || end > 86400) {
        throw const FormatException('Invalid podcast source range.');
      }
      duration += end - start;
    }
    if (duration > 86400 || (hasStream && plan['version'] != 2)) {
      throw const FormatException('Invalid podcast duration or version.');
    }
    return Bmp08SavedEpisode._(jsonDecode(jsonEncode(doc)) as Map<String, dynamic>, id);
  }

  Map<String, Object?> revisionBody(Map<String, String> edits, String requestId) {
    if (edits.isEmpty) throw const FormatException('No podcast changes.');
    final doc = document;
    final payload = _podcastMap(doc['payload']);
    final next = _podcastMap(payload['podcast_plan']);
    final segments = (next['segments'] as List).map(_podcastMap).toList();
    if (edits.keys.any((id) => !segments.any((s) => s['segment_id'] == id))) {
      throw const FormatException('Unknown podcast segment.');
    }
    for (final segment in segments) {
      final text = edits[segment['segment_id']];
      if (text != null) segment['corrected_text'] = _podcastText(text);
    }
    next['revision'] = (next['revision'] as int) + 1;
    final lines = <String>[next['title'] as String, next['description'] as String, ''];
    num time = 0;
    for (final segment in segments) {
      final ms = (time * 1000).round();
      String pad(int value, int width) => value.toString().padLeft(width, '0');
      final code = '${pad(ms ~/ 3600000, 2)}:${pad(ms ~/ 60000 % 60, 2)}:${pad(ms ~/ 1000 % 60, 2)}.${pad(ms % 1000, 3)}';
      lines.add('[$code] ${segment['speaker']} ${segment['corrected_text']}');
      time += (segment['source_out'] as num) - (segment['source_in'] as num);
    }
    return {
      'title': doc['title'], 'markdown': lines.join('\n'), 'kind': 'podcast_episode',
      'payload': payload, 'citations': doc['citations'], 'contract': doc['contract'],
      'request_id': requestId, 'work_id': workId, 'previous_artifact_id': artifactId,
      'expected_draft_digest': draftDigest,
    };
  }
}
