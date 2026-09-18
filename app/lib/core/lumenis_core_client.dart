import 'dart:convert';
import 'dart:io';

class LumenisCoreException implements Exception {
  const LumenisCoreException(this.message);
  final String message;

  @override
  String toString() => 'LumenisCoreException: $message';
}

class LumenisCoreClient {
  LumenisCoreClient({String? baseUrl})
      : baseUrl = baseUrl ??
            const String.fromEnvironment(
              'LUMENIS_CORE_URL',
              defaultValue: 'http://127.0.0.1:8201',
            );

  final String baseUrl;

  Future<Map<String, dynamic>> runtimeIdentity() =>
      _get('/api/experience/runtime/identity');

  Future<List<Map<String, dynamic>>> subjects() async {
    final payload = await _get('/api/experience/subjects');
    final raw = payload['subjects'];
    if (raw is! List) {
      throw const LumenisCoreException('subjects response is not a list');
    }
    return raw
        .whereType<Map>()
        .map((item) => item.map((key, value) => MapEntry('$key', value)))
        .toList(growable: false);
  }

  Future<Map<String, dynamic>> screen(String screenId) =>
      _get('/api/experience/screen/${Uri.encodeComponent(screenId)}');

  Future<Map<String, dynamic>> _get(String path) async {
    final http = HttpClient();
    try {
      http.connectionTimeout = const Duration(seconds: 8);
      final request = await http.getUrl(Uri.parse('$baseUrl$path'));
      request.headers.set(HttpHeaders.acceptHeader, 'application/json');
      final reply = await request.close();
      final body = await utf8.decoder.bind(reply).join();
      if (reply.statusCode < 200 || reply.statusCode >= 300) {
        throw LumenisCoreException(
          'GET $path failed with HTTP ${reply.statusCode}',
        );
      }
      final decoded = jsonDecode(body);
      if (decoded is! Map<String, dynamic>) {
        throw LumenisCoreException('GET $path returned non-object JSON');
      }
      return decoded;
    } on SocketException catch (error) {
      throw LumenisCoreException(
        'LUMENIS Core unavailable at $baseUrl: ${error.message}',
      );
    } finally {
      http.close(force: true);
    }
  }
}
