import 'dart:convert';
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
    final context = _client.currentContextEnvelope?['context'];
    final signature = jsonEncode(context);
    final response = await _client.screen('BMP-01');
    if (signature != jsonEncode(_client.currentContextEnvelope?['context'])) {
      throw const FormatException('Brand context changed during read.');
    }
    final scope = response['focus_context'] ?? response['global_context'];
    if (context is! Map ||
        scope is! Map ||
        scope['mode'] != context['mode'] ||
        scope['subject_id'] != context['subject_id'] ||
        (context['mode'] == 'FOCUS' && context['domain_id'] != 'BMP')) {
      throw const FormatException(
        'Brand response does not match the selected scope.',
      );
    }
    return Bmp01Snapshot.fromResponse(response);
  }
}
