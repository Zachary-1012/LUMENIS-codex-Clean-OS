import 'dart:async';

import 'package:http/http.dart' as http;

import 'lumenis_http_transport_types.dart';

const supportsLocalCoreCredentialBootstrap = false;

Future<LumenisTransportResponse> sendLumenisHttpRequest(
  LumenisTransportRequest request,
) async {
  final client = http.Client();
  try {
    final outgoing = http.Request(request.method, request.uri)
      ..followRedirects = request.followRedirects
      ..headers.addAll(request.headers);
    if (request.body case final body?) {
      outgoing.body = body;
    }
    final incoming = await client
        .send(outgoing)
        .timeout(request.connectionTimeout);
    return LumenisTransportResponse(
      statusCode: incoming.statusCode,
      body: await incoming.stream.bytesToString(),
    );
  } on http.ClientException catch (error) {
    throw LumenisTransportException(error.toString());
  } on TimeoutException catch (error) {
    throw LumenisTransportException(error.toString());
  } finally {
    client.close();
  }
}
