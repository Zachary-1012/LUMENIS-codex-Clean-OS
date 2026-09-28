import 'dart:async';
import 'dart:io';
import 'dart:typed_data';

import 'lumenis_http_transport_types.dart';

const supportsLocalCoreCredentialBootstrap = true;

Future<LumenisTransportResponse> sendLumenisHttpRequest(
  LumenisTransportRequest request,
) async {
  final client = HttpClient()..connectionTimeout = request.connectionTimeout;
  try {
    final outgoing = await client.openUrl(request.method, request.uri);
    outgoing.followRedirects = request.followRedirects;
    request.headers.forEach(outgoing.headers.set);
    if (request.body case final body?) {
      outgoing.write(body);
    }
    final incoming = await outgoing.close();
    final bytes = BytesBuilder(copy: false);
    await for (final chunk in incoming) {
      bytes.add(chunk);
    }
    final headers = <String, String>{};
    incoming.headers.forEach((name, values) {
      headers[name] = values.join(', ');
    });
    return LumenisTransportResponse.bytes(
      statusCode: incoming.statusCode,
      bodyBytes: bytes.takeBytes(),
      headers: headers,
    );
  } on IOException catch (error) {
    throw LumenisTransportException(error.toString());
  } on TimeoutException catch (error) {
    throw LumenisTransportException(error.toString());
  } finally {
    client.close(force: true);
  }
}
