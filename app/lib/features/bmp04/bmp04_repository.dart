import '../../core/lumenis_core_client.dart';
import 'bmp04_snapshot.dart';

abstract interface class Bmp04Repository {
  Future<Bmp04Snapshot> load();
}

class CoreBmp04Repository implements Bmp04Repository, Bmp04ClassificationRepository {
  CoreBmp04Repository({required this._client});

  final LumenisCoreClient _client;

  Future<Map<String, dynamic>> _classify(Bmp04ClassificationDraft draft,
      {String? resource}) => _client.classifyPropagationEvent(
    subjectId: draft.subjectId, sourceEventId: draft.eventId,
    category: draft.category, requestId: draft.requestId,
    confirmedResource: resource,
  );

  @override
  Future<String> previewClassification(Bmp04ClassificationDraft draft) async {
    final result = await _classify(draft);
    final resource = result['resource'];
    if (result['ok'] != true || result['state'] != 'PREPARED' ||
        result['approval_issued'] != false || resource is! String ||
        !RegExp(r'^propagation-classification:v1:[a-f0-9]{64}$').hasMatch(resource)) {
      throw const FormatException('Invalid classification preview.');
    }
    return resource;
  }

  @override
  Future<void> confirmClassification(Bmp04ClassificationDraft draft,
      String resource) async {
    final result = await _classify(draft, resource: resource);
    if (result['ok'] != true || result['source_event_id'] != draft.eventId ||
        result['category'] != draft.category ||
        result['claim_type'] != 'human_business_classification' ||
        result['classification_id'] is! String ||
        !RegExp(r'^PE-S-[a-f0-9]{32}$').hasMatch(result['classification_id'] as String)) {
      throw const FormatException('Classification save outcome is unverified.');
    }
  }

  @override
  Future<Bmp04Snapshot> load() async {
    final response = await _client.screen('BMP-04');
    return Bmp04Snapshot.fromResponse(response);
  }
}

/// Optional write capability keeps read-only repositories and old callers intact.
abstract interface class Bmp04ClassificationRepository {
  Future<String> previewClassification(Bmp04ClassificationDraft draft);
  Future<void> confirmClassification(Bmp04ClassificationDraft draft, String resource);
}

class Bmp04ClassificationDraft {
  const Bmp04ClassificationDraft({required this.subjectId, required this.eventId,
    required this.category, required this.requestId});
  final String subjectId;
  final int eventId;
  final String category;
  final String requestId;
}
