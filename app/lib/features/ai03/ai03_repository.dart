import '../../core/lumenis_core_client.dart';
import 'ai03_snapshot.dart';

abstract interface class Ai03Repository {
  Future<Ai03Snapshot> load();
}

class CoreAi03Repository implements Ai03Repository {
  CoreAi03Repository({required this._client});

  final LumenisCoreClient _client;

  @override
  Future<Ai03Snapshot> load() async {
    final response = await _client.screen('AI-03');
    return Ai03Snapshot.fromResponse(response);
  }
}
