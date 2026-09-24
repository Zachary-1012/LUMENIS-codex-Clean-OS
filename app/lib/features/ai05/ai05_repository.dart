import '../../core/lumenis_core_client.dart';
import 'ai05_snapshot.dart';

abstract interface class Ai05Repository {
  Future<Ai05Snapshot> load();
}

class CoreAi05Repository implements Ai05Repository {
  CoreAi05Repository({required this._client});

  final LumenisCoreClient _client;

  @override
  Future<Ai05Snapshot> load() async {
    final response = await _client.screen('AI-05');
    if (response['ok'] != true || response['screen'] != 'AI-05') {
      throw const FormatException('AI-05 response is not valid.');
    }
    if (response['bound'] == true) {
      return Ai05Snapshot.fromResponse(response);
    }
    // AI-05 is not independently bound today. Reuse the existing provider
    // observation from AI-01, but label the result as diagnostic fallback.
    final diagnostic = await _client.screen('AI-01');
    return Ai05Snapshot.fromAi01Diagnostic(diagnostic);
  }
}
