import '../../core/lumenis_core_client.dart';
import 'bmp10_snapshot.dart';

abstract interface class Bmp10Repository {
  Future<Bmp10Snapshot> load();
}

class CoreBmp10Repository implements Bmp10Repository {
  CoreBmp10Repository({required this._client});

  final LumenisCoreClient _client;

  @override
  Future<Bmp10Snapshot> load() async {
    final response = await _client.screen('BMP-10');
    return Bmp10Snapshot.fromResponse(response);
  }
}
