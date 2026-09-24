import '../../core/lumenis_core_client.dart';
import 'bmp08_snapshot.dart';

abstract interface class Bmp08Repository {
  Future<Bmp08Snapshot> load();
}

class CoreBmp08Repository implements Bmp08Repository {
  CoreBmp08Repository({required this._client});

  final LumenisCoreClient _client;

  @override
  Future<Bmp08Snapshot> load() async {
    final response = await _client.screen('BMP-08');
    return Bmp08Snapshot.fromResponse(response);
  }
}
