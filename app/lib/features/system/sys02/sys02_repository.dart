import '../../../core/lumenis_core_client.dart';
import 'sys02_snapshot.dart';

abstract interface class Sys02Repository {
  Future<Sys02Snapshot> load();
}

class CoreSys02Repository implements Sys02Repository {
  CoreSys02Repository({required this._client});

  final LumenisCoreClient _client;

  @override
  Future<Sys02Snapshot> load() async {
    final response = await _client.screen('SYS-02');
    return Sys02Snapshot.fromResponse(response);
  }
}
