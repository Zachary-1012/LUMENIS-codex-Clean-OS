import '../../../core/lumenis_core_client.dart';
import 'sh04_snapshot.dart';

typedef Sh04ScreenReader = Future<Map<String, dynamic>> Function();

abstract interface class Sh04Repository {
  Future<Sh04Snapshot> loadExports();
}

class CoreSh04Repository implements Sh04Repository {
  const CoreSh04Repository({
    required this._client,
    this.screenReader,
  });

  final LumenisCoreClient _client;
  final Sh04ScreenReader? screenReader;

  @override
  Future<Sh04Snapshot> loadExports() async {
    final reader = screenReader ?? () => _client.screen('SH-04');
    return Sh04Snapshot.fromResponse(await reader());
  }
}
