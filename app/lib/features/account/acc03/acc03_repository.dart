import '../../../core/lumenis_core_client.dart';
import 'acc03_snapshot.dart';

abstract interface class Acc03Repository {
  Future<Acc03Snapshot> load();
}

class CoreAcc03Repository implements Acc03Repository {
  CoreAcc03Repository({required this._client});

  final LumenisCoreClient _client;

  @override
  Future<Acc03Snapshot> load() async {
    final identity = await _client.runtimeIdentity();
    Map<String, dynamic>? context;
    try {
      context = await _client.settingsContext();
    } on LumenisCoreException catch (error) {
      if (error.statusCode == 401 || error.statusCode == 403) rethrow;
    }
    return Acc03Snapshot.fromResponses(identity: identity, context: context);
  }
}
