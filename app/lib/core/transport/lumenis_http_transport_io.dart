import 'dart:async';
import 'dart:convert';
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
    if (request.upload case final upload?) {
      outgoing.contentLength = upload.length;
      await outgoing.addStream(upload.checkedStream());
    } else if (request.bodyBytes case final bodyBytes?) {
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
  if (request.method != 'HEAD' && incoming.contentLength > maxBytes) {
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

/// Opens a Server-Sent Events stream and yields each event's `data` payload.
/// Cancelling the subscription closes the connection.
Stream<String> openLumenisEventStream(
  LumenisTransportRequest request, {
  required int maxEventBytes,
}) async* {
  request.validateBody();
  final client = HttpClient()..connectionTimeout = request.connectionTimeout;
  try {
    final outgoing = await client.openUrl(request.method, request.uri);
    outgoing.followRedirects = false;
    request.headers.forEach(outgoing.headers.set);
    final incoming = await outgoing.close();
    if (incoming.statusCode != HttpStatus.ok ||
        incoming.headers.contentType?.mimeType != 'text/event-stream') {
      throw LumenisTransportException(
        'Event stream rejected (${incoming.statusCode}).',
      );
    }
    final data = StringBuffer();
    await for (final line
        in incoming
            .cast<List<int>>()
            .transform(utf8.decoder)
            .transform(const LineSplitter())) {
      if (line.isEmpty) {
        if (data.isNotEmpty) {
          yield data.toString();
          data.clear();
        }
        continue;
      }
      if (!line.startsWith('data:')) continue;
      final value = line.substring(5);
      if (data.isNotEmpty) data.write('\n');
      data.write(value.startsWith(' ') ? value.substring(1) : value);
      if (data.length > maxEventBytes) {
        throw const LumenisTransportException('Event exceeds maxEventBytes.');
      }
    }
  } on IOException catch (error) {
    throw LumenisTransportException(error.toString());
  } finally {
    client.close(force: true);
  }
}
