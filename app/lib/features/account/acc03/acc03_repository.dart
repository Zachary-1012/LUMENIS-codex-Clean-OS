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
    Acc03RuntimeState? contextFailure;
    try {
      context = await _client.settingsContext();
    } catch (error) {
      contextFailure =
          error is LumenisCoreException &&
              (error.statusCode == 401 || error.statusCode == 403)
          ? Acc03RuntimeState.restricted
          : Acc03RuntimeState.unavailable;
    }
    return Acc03Snapshot.fromResponses(
      identity: identity,
      context: context,
      contextFailure: contextFailure,
    );
  }
}
