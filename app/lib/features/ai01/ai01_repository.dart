import '../../core/lumenis_core_client.dart';
import 'ai01_intent.dart';
import 'ai01_snapshot.dart';

abstract interface class Ai01Repository {
  Future<Ai01Snapshot> load();

  Future<Ai01IntentResult> submitIntent(String task);
}

class CoreAi01Repository implements Ai01Repository {
  CoreAi01Repository({required this._client});

  final LumenisCoreClient _client;

  @override
  Future<Ai01Snapshot> load() async {
    final response = await _client.screen('AI-01');
    return Ai01Snapshot.fromResponse(response);
  }

  @override
  Future<Ai01IntentResult> submitIntent(String task) async {
    final response = await _client.submitAiIntent(task: task);
    return Ai01IntentResult.fromResponse(response);
  }
}
