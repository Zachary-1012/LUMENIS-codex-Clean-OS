import '../../core/lumenis_core_client.dart';
import 'ai04_snapshot.dart';

abstract interface class Ai04Repository {
  Future<Ai04Snapshot> load();
}

class CoreAi04Repository implements Ai04Repository {
  CoreAi04Repository({required this._client});

  final LumenisCoreClient _client;

  @override
  Future<Ai04Snapshot> load() async {
    final response = await _client.sharedSkillsCatalog();
    return Ai04Snapshot.fromResponse(response);
  }
}
