import '../../../core/lumenis_core_client.dart';
import 'sh06_snapshot.dart';

typedef Sh06ScreenReader = Future<Map<String, dynamic>> Function();

abstract interface class Sh06Repository {
  Future<Sh06Snapshot> loadInbox();
}

class CoreSh06Repository implements Sh06Repository {
  const CoreSh06Repository({
    required this._client,
    this.screenReader,
  });

  final LumenisCoreClient _client;
  final Sh06ScreenReader? screenReader;

  @override
  Future<Sh06Snapshot> loadInbox() async {
    final reader = screenReader ?? () => _client.screen('SH-06');
    return Sh06Snapshot.fromResponse(await reader());
  }
}
