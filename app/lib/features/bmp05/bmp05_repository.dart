import '../../core/lumenis_core_client.dart';
import 'bmp05_snapshot.dart';

abstract interface class Bmp05Repository {
  Future<Bmp05Snapshot> load();
}

class CoreBmp05Repository implements Bmp05Repository {
  CoreBmp05Repository({required this._client});

  final LumenisCoreClient _client;

  @override
  Future<Bmp05Snapshot> load() async {
    final response = await _client.screen('BMP-05');
    return Bmp05Snapshot.fromResponse(response);
  }
}
