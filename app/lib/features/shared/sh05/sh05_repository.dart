import '../../../core/lumenis_core_client.dart';
import 'sh05_snapshot.dart';

typedef Sh05ScreenReader = Future<Map<String, dynamic>> Function();

abstract interface class Sh05Repository {
  Future<Sh05Snapshot> loadAssets();
}

class CoreSh05Repository implements Sh05Repository {
  const CoreSh05Repository({
    required this._client,
    this.screenReader,
  });

  final LumenisCoreClient _client;
  final Sh05ScreenReader? screenReader;

  @override
  Future<Sh05Snapshot> loadAssets() async {
    final reader = screenReader ?? () => _client.screen('SH-05');
    return Sh05Snapshot.fromResponse(await reader());
  }
}
