import '../../../core/lumenis_core_client.dart';
import 'acc01_snapshot.dart';

abstract interface class Acc01Repository {
  Future<Acc01Snapshot> load();
}

class CoreAcc01Repository implements Acc01Repository {
  CoreAcc01Repository({required this._client});

  final LumenisCoreClient _client;

  @override
  Future<Acc01Snapshot> load() async {
    final response = await _client.runtimeIdentity();
    return Acc01Snapshot.fromIdentity(response);
  }
}
