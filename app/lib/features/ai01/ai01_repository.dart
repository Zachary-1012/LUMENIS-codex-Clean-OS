import '../../core/lumenis_core_client.dart';
import 'ai01_snapshot.dart';

abstract interface class Ai01Repository {
  Future<Ai01Snapshot> load();
}

class CoreAi01Repository implements Ai01Repository {
  CoreAi01Repository({required this._client});

  final LumenisCoreClient _client;

  @override
  Future<Ai01Snapshot> load() async {
    final response = await _client.screen('AI-01');
    return Ai01Snapshot.fromResponse(response);
  }
}
