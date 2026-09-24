import '../../../core/lumenis_core_client.dart';
import 'sh02_snapshot.dart';

typedef Sh02ScreenReader = Future<Map<String, dynamic>> Function();

abstract interface class Sh02Repository {
  Future<Sh02Snapshot> loadLibrary();
}

class CoreSh02Repository implements Sh02Repository {
  const CoreSh02Repository({
    required this._client,
    this.screenReader,
  });

  final LumenisCoreClient _client;
  final Sh02ScreenReader? screenReader;

  @override
  Future<Sh02Snapshot> loadLibrary() async {
    final reader = screenReader ?? () => _client.screen('SH-02');
    return Sh02Snapshot.fromResponse(await reader());
  }
}
