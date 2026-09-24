import '../../../core/lumenis_core_client.dart';
import 'sys07_snapshot.dart';

abstract interface class Sys07Repository {
  Future<Sys07Snapshot> load();
}

class CoreSys07Repository implements Sys07Repository {
  CoreSys07Repository({required this._client});

  final LumenisCoreClient _client;

  @override
  Future<Sys07Snapshot> load() async {
    final response = await _client.screen('SYS-07');
    return Sys07Snapshot.fromResponse(response);
  }
}
