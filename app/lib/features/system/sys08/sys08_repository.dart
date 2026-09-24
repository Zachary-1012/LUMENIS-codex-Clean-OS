import '../../../core/lumenis_core_client.dart';
import 'sys08_snapshot.dart';

abstract interface class Sys08Repository {
  Future<Sys08Snapshot> load();
}

class CoreSys08Repository implements Sys08Repository {
  CoreSys08Repository({required this._client});

  final LumenisCoreClient _client;

  @override
  Future<Sys08Snapshot> load() async {
    final response = await _client.screen('SYS-08');
    return Sys08Snapshot.fromResponse(response);
  }
}
