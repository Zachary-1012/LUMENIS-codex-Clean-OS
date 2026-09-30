import 'dart:async';
import 'dart:typed_data';

import 'package:http/http.dart' as http;

import 'lumenis_http_transport_types.dart';

const supportsLocalCoreCredentialBootstrap = false;

Future<LumenisTransportResponse> sendLumenisHttpRequest(
  LumenisTransportRequest request,
) async {
  request.validateBody();
  final client = http.Client();
  try {
    final outgoing = http.Request(request.method, request.uri)
      ..followRedirects = request.followRedirects
      ..headers.addAll(request.headers);
    if (request.bodyBytes case final bodyBytes?) {
      outgoing.bodyBytes = bodyBytes;
    } else if (request.body case final body?) {
      outgoing.body = body;
    }
    final incoming = await client
        .send(outgoing)
        .timeout(request.connectionTimeout);
    return LumenisTransportResponse.bytes(
      statusCode: incoming.statusCode,
      bodyBytes: await incoming.stream.toBytes(),
      headers: incoming.headers,
    );
  } on http.ClientException catch (error) {
    throw LumenisTransportException(error.toString());
  } on TimeoutException catch (error) {
    throw LumenisTransportException(error.toString());
  } finally {
    client.close();
  }
}

Future<LumenisBinaryTransportResponse> sendLumenisBinaryRequest(
  LumenisTransportRequest request, {
  required int maxBytes,
}) async {
  request.validateBody();
  if (maxBytes <= 0) {
    throw ArgumentError.value(maxBytes, 'maxBytes', 'Must be positive.');
  }

  final client = http.Client();
  try {
    return await _sendBinaryRequest(
      client,
      request,
      maxBytes,
    ).timeout(request.connectionTimeout);
  } on http.ClientException catch (error) {
    throw LumenisTransportException(error.toString());
  } on TimeoutException catch (error) {
    throw LumenisTransportException(error.toString());
  } finally {
    client.close();
  }
}

Future<LumenisBinaryTransportResponse> _sendBinaryRequest(
  http.Client client,
  LumenisTransportRequest request,
  int maxBytes,
) async {
  final outgoing = http.Request(request.method, request.uri)
    ..followRedirects = false
    ..headers.addAll(request.headers);
  if (request.bodyBytes case final bodyBytes?) {
    outgoing.bodyBytes = bodyBytes;
  } else if (request.body case final body?) {
    outgoing.body = body;
  }

  final incoming = await client.send(outgoing);
  if (incoming.statusCode >= 300 &&
      incoming.statusCode < 400 &&
      incoming.statusCode != 304) {
    throw const LumenisTransportException(
      'Binary response redirects are rejected.',
    );
  }
  if ((incoming.contentLength ?? -1) > maxBytes) {
    throw const LumenisTransportException('Binary response exceeds maxBytes.');
  }

  final builder = BytesBuilder(copy: false);
  var byteCount = 0;
  await for (final chunk in incoming.stream) {
    byteCount += chunk.length;
    if (byteCount > maxBytes) {
      throw const LumenisTransportException('Binary response exceeds maxBytes.');
    }
    builder.add(chunk);
  }

  return LumenisBinaryTransportResponse(
    statusCode: incoming.statusCode,
    bytes: builder.takeBytes(),
    contentType: incoming.headers['content-type'],
  );
}
