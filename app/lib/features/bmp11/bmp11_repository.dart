import '../../core/lumenis_core_client.dart';
import 'bmp11_snapshot.dart';

abstract interface class Bmp11Repository {
  Future<Bmp11Snapshot> load();
}

class CoreBmp11Repository implements Bmp11Repository {
  CoreBmp11Repository({required this._client});

  final LumenisCoreClient _client;

  @override
  Future<Bmp11Snapshot> load() async {
    final response = await _client.screen('BMP-11');
    return Bmp11Snapshot.fromResponse(response);
  }
}
