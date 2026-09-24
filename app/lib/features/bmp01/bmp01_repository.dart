import '../../core/lumenis_core_client.dart';
import 'bmp01_snapshot.dart';

abstract interface class Bmp01Repository {
  Future<Bmp01Snapshot> load();
}

class CoreBmp01Repository implements Bmp01Repository {
  CoreBmp01Repository({required this._client});

  final LumenisCoreClient _client;

  @override
  Future<Bmp01Snapshot> load() async {
    final response = await _client.screen('BMP-01');
    return Bmp01Snapshot.fromResponse(response);
  }
}
