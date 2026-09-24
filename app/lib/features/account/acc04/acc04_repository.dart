import '../../../core/lumenis_core_client.dart';
import 'acc04_snapshot.dart';

abstract interface class Acc04Repository {
  Future<Acc04Snapshot> load();
}

class CoreAcc04Repository implements Acc04Repository {
  CoreAcc04Repository({required this._client});

  final LumenisCoreClient _client;

  @override
  Future<Acc04Snapshot> load() async {
    final response = await _client.screen('ACC-04');
    return Acc04Snapshot.fromResponse(response);
  }
}
