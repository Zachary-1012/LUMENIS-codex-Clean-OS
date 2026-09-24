import '../../../core/lumenis_core_client.dart';
import 'sys01_snapshot.dart';

abstract interface class Sys01Repository {
  Future<Sys01Snapshot> load();
}

class CoreSys01Repository implements Sys01Repository {
  CoreSys01Repository({required this._client});

  final LumenisCoreClient _client;

  @override
  Future<Sys01Snapshot> load() async {
    final response = await _client.screen('SYS-01');
    return Sys01Snapshot.fromResponse(response);
  }
}
