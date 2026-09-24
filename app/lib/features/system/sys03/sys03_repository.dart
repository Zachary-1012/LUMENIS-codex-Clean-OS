import '../../../core/lumenis_core_client.dart';
import 'sys03_snapshot.dart';

abstract interface class Sys03Repository {
  Future<Sys03Snapshot> load();
}

class CoreSys03Repository implements Sys03Repository {
  CoreSys03Repository({required this._client});

  final LumenisCoreClient _client;

  @override
  Future<Sys03Snapshot> load() async {
    final response = await _client.screen('SYS-03');
    return Sys03Snapshot.fromResponse(response);
  }
}
