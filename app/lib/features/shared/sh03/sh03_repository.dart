import '../../../core/lumenis_core_client.dart';
import 'sh03_snapshot.dart';

typedef Sh03ScreenReader = Future<Map<String, dynamic>> Function();

abstract interface class Sh03Repository {
  Future<Sh03Snapshot> loadBrowser();
}

class CoreSh03Repository implements Sh03Repository {
  const CoreSh03Repository({
    required this._client,
    this.screenReader,
  });

  final LumenisCoreClient _client;
  final Sh03ScreenReader? screenReader;

  @override
  Future<Sh03Snapshot> loadBrowser() async {
    final reader = screenReader ?? () => _client.screen('SH-03');
    return Sh03Snapshot.fromResponse(await reader());
  }
}
