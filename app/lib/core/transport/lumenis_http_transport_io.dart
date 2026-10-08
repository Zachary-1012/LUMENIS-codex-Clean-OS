import 'dart:async';
import 'dart:io';
import 'dart:typed_data';

import 'lumenis_http_transport_types.dart';

const supportsLocalCoreCredentialBootstrap = false;

Future<LumenisTransportResponse> sendLumenisHttpRequest(
  LumenisTransportRequest request,
) async {
  request.validateBody();
  final client = HttpClient()..connectionTimeout = request.connectionTimeout;
  try {
    final outgoing = await client.openUrl(request.method, request.uri);
    outgoing.followRedirects = request.followRedirects;
    request.headers.forEach(outgoing.headers.set);
    if (request.bodyBytes case final bodyBytes?) {
      outgoing.add(bodyBytes);
    } else if (request.body case final body?) {
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

Future<LumenisBinaryTransportResponse> sendLumenisBinaryRequest(
  LumenisTransportRequest request, {
  required int maxBytes,
}) async {
  request.validateBody();
  if (maxBytes <= 0) {
    throw ArgumentError.value(maxBytes, 'maxBytes', 'Must be positive.');
  }

  final client = HttpClient()..connectionTimeout = request.connectionTimeout;
  try {
    return await _sendBinaryRequest(
      client,
      request,
      maxBytes,
    ).timeout(request.connectionTimeout);
  } on IOException catch (error) {
    throw LumenisTransportException(error.toString());
  } on TimeoutException catch (error) {
    throw LumenisTransportException(error.toString());
  } finally {
    client.close(force: true);
  }
}

Future<LumenisBinaryTransportResponse> _sendBinaryRequest(
  HttpClient client,
  LumenisTransportRequest request,
  int maxBytes,
) async {
  final outgoing = await client.openUrl(request.method, request.uri);
  outgoing.followRedirects = false;
  request.headers.forEach(outgoing.headers.set);
  if (request.bodyBytes case final bodyBytes?) {
    outgoing.add(bodyBytes);
  } else if (request.body case final body?) {
    outgoing.write(body);
  }

  final incoming = await outgoing.close();
  if (incoming.statusCode >= 300 &&
      incoming.statusCode < 400 &&
      incoming.statusCode != HttpStatus.notModified) {
    throw const LumenisTransportException(
      'Binary response redirects are rejected.',
    );
  }
  if (incoming.contentLength > maxBytes) {
    throw const LumenisTransportException('Binary response exceeds maxBytes.');
  }

  final builder = BytesBuilder(copy: false);
  var byteCount = 0;
  await for (final chunk in incoming) {
    byteCount += chunk.length;
    if (byteCount > maxBytes) {
      throw const LumenisTransportException(
        'Binary response exceeds maxBytes.',
      );
    }
    builder.add(chunk);
  }

  final headers = <String, String>{};
  incoming.headers.forEach((name, values) {
    headers[name] = values.join(', ');
  });

  return LumenisBinaryTransportResponse(
    statusCode: incoming.statusCode,
    bytes: builder.takeBytes(),
    contentType: incoming.headers.value(HttpHeaders.contentTypeHeader),
    headers: headers,
  );
}
