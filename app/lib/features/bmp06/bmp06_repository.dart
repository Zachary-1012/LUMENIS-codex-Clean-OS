import '../../core/lumenis_core_client.dart';
import 'bmp06_snapshot.dart';

abstract interface class Bmp06Repository {
  Future<Bmp06Snapshot> load();
}

class CoreBmp06Repository implements Bmp06Repository {
  CoreBmp06Repository({required this._client});

  final LumenisCoreClient _client;

  @override
  Future<Bmp06Snapshot> load() async {
    final response = await _client.screen('BMP-06');
    return Bmp06Snapshot.fromResponse(response);
  }
}
