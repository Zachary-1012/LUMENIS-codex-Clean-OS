import 'dart:async';
import 'dart:convert';
import 'dart:io';

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
    return LumenisTransportResponse(
      statusCode: incoming.statusCode,
      body: await utf8.decoder.bind(incoming).join(),
    );
  } on IOException catch (error) {
    throw LumenisTransportException(error.toString());
  } on TimeoutException catch (error) {
    throw LumenisTransportException(error.toString());
  } finally {
    client.close(force: true);
  }
}
