import '../../../core/lumenis_core_client.dart';
import 'sys05_snapshot.dart';

abstract interface class Sys05Repository {
  Future<Sys05Snapshot> load();
}

class CoreSys05Repository implements Sys05Repository {
  CoreSys05Repository({required this._client});

  final LumenisCoreClient _client;

  @override
  Future<Sys05Snapshot> load() async {
    final response = await _client.screen('SYS-05');
    return Sys05Snapshot.fromResponse(response);
  }
}
