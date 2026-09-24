import '../../core/lumenis_core_client.dart';
import 'bmp07_snapshot.dart';

abstract interface class Bmp07Repository {
  Future<Bmp07Snapshot> load();
}

class CoreBmp07Repository implements Bmp07Repository {
  CoreBmp07Repository({required this._client});

  final LumenisCoreClient _client;

  @override
  Future<Bmp07Snapshot> load() async {
    final response = await _client.screen('BMP-07');
    return Bmp07Snapshot.fromResponse(response);
  }
}
