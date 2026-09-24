import '../../core/lumenis_core_client.dart';
import 'bmp04_snapshot.dart';

abstract interface class Bmp04Repository {
  Future<Bmp04Snapshot> load();
}

class CoreBmp04Repository implements Bmp04Repository {
  CoreBmp04Repository({required this._client});

  final LumenisCoreClient _client;

  @override
  Future<Bmp04Snapshot> load() async {
    final response = await _client.screen('BMP-04');
    return Bmp04Snapshot.fromResponse(response);
  }
}
