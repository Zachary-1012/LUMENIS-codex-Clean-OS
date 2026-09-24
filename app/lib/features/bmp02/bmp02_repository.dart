import '../../core/lumenis_core_client.dart';
import 'bmp02_snapshot.dart';

abstract interface class Bmp02Repository {
  Future<Bmp02Snapshot> load();
}

class CoreBmp02Repository implements Bmp02Repository {
  CoreBmp02Repository({required this._client});

  final LumenisCoreClient _client;

  @override
  Future<Bmp02Snapshot> load() async {
    final response = await _client.screen('BMP-02');
    return Bmp02Snapshot.fromResponse(response);
  }
}
