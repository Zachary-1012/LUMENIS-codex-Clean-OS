import '../../core/lumenis_core_client.dart';
import 'bmp09_snapshot.dart';

abstract interface class Bmp09Repository {
  Future<Bmp09Snapshot> load();
}

class CoreBmp09Repository implements Bmp09Repository {
  CoreBmp09Repository({required this._client});

  final LumenisCoreClient _client;

  @override
  Future<Bmp09Snapshot> load() async {
    final response = await _client.screen('BMP-09');
    return Bmp09Snapshot.fromResponse(response);
  }
}
