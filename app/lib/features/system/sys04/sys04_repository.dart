import '../../../core/lumenis_core_client.dart';
import 'sys04_snapshot.dart';

abstract interface class Sys04Repository {
  Future<Sys04Snapshot> load();
}

class CoreSys04Repository implements Sys04Repository {
  CoreSys04Repository({required this._client});

  final LumenisCoreClient _client;

  @override
  Future<Sys04Snapshot> load() async {
    final response = await _client.screen('SYS-04');
    return Sys04Snapshot.fromResponse(response);
  }
}
