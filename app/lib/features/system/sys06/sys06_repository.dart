import '../../../core/lumenis_core_client.dart';
import 'sys06_snapshot.dart';

abstract interface class Sys06Repository {
  Future<Sys06Snapshot> load();
}

class CoreSys06Repository implements Sys06Repository {
  CoreSys06Repository({required this._client});

  final LumenisCoreClient _client;

  @override
  Future<Sys06Snapshot> load() async {
    final response = await _client.screen('SYS-06');
    return Sys06Snapshot.fromResponse(response);
  }
}
