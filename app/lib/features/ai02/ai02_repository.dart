import '../../core/lumenis_core_client.dart';
import 'ai02_snapshot.dart';

abstract interface class Ai02Repository {
  Future<Ai02Snapshot> load();
}

class CoreAi02Repository implements Ai02Repository {
  CoreAi02Repository({required this._client});

  final LumenisCoreClient _client;

  @override
  Future<Ai02Snapshot> load() async {
    final response = await _client.screen('AI-02');
    return Ai02Snapshot.fromResponse(response);
  }
}
