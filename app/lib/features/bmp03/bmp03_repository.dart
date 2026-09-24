import '../../core/lumenis_core_client.dart';
import 'bmp03_snapshot.dart';

abstract interface class Bmp03Repository {
  Future<Bmp03Snapshot> load();
}

class CoreBmp03Repository implements Bmp03Repository {
  CoreBmp03Repository({required this._client});

  final LumenisCoreClient _client;

  @override
  Future<Bmp03Snapshot> load() async {
    final response = await _client.screen('BMP-03');
    return Bmp03Snapshot.fromResponse(response);
  }
}
