import 'dart:async';
import 'dart:js_interop';
import 'dart:typed_data';

import 'package:http/http.dart' as http;
import 'package:web/web.dart' as web;

import 'lumenis_http_transport_types.dart';

const supportsLocalCoreCredentialBootstrap = false;

Future<LumenisTransportResponse> sendLumenisHttpRequest(
  LumenisTransportRequest request,
) async {
  request.validateBody();
  if (request.upload != null) return _sendFile(request);
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

Future<LumenisTransportResponse> _sendFile(
  LumenisTransportRequest request,
) async {
  final upload = request.upload!;
  final uri = upload.browserBlobUri;
  if (uri == null ||
      uri.scheme != 'blob' ||
      !uri.toString().startsWith('blob:${web.window.location.origin}/')) {
    throw const LumenisTransportException(
      'The selected browser file is unavailable.',
    );
  }
  final abort = web.AbortController();
  final timer = Timer(request.connectionTimeout, () => abort.abort());
  try {
    final local = await web.window
        .fetch(uri.toString().toJS, web.RequestInit(signal: abort.signal))
        .toDart;
    if (!local.ok) {
      throw const LumenisTransportException(
        'The selected file could not be read.',
      );
    }
    final blob = await local.blob().toDart;
    if (blob.size != upload.length) {
      throw const LumenisTransportException('The selected file changed.');
    }
    final headers = web.Headers();
    request.headers.forEach((name, value) => headers.set(name, value));
    final response = await web.window
        .fetch(
          request.uri.toString().toJS,
          web.RequestInit(
            method: request.method,
            headers: headers,
            body: blob,
            redirect: 'error',
            credentials: 'same-origin',
            signal: abort.signal,
          ),
        )
        .toDart;
    return LumenisTransportResponse(
      statusCode: response.status,
      body: await response.text().toDart.then((value) => value.toDart),
    );
  } catch (_) {
    throw const LumenisTransportException(
      'File transfer interrupted; completion is unknown.',
    );
  } finally {
    timer.cancel();
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
  if (request.method != 'HEAD' && (incoming.contentLength ?? -1) > maxBytes) {
    throw const LumenisTransportException('Binary response exceeds maxBytes.');
  }

  final builder = BytesBuilder(copy: false);
  var byteCount = 0;
  await for (final chunk in incoming.stream) {
    byteCount += chunk.length;
    if (byteCount > maxBytes) {
      throw const LumenisTransportException(
        'Binary response exceeds maxBytes.',
      );
    }
    builder.add(chunk);
  }

  return LumenisBinaryTransportResponse(
    statusCode: incoming.statusCode,
    bytes: builder.takeBytes(),
    contentType: incoming.headers['content-type'],
    headers: incoming.headers,
  );
}

/// Server-Sent Events on Web through the browser's native EventSource.
/// Cancelling the subscription closes the connection.
Stream<String> openLumenisEventStream(
  LumenisTransportRequest request, {
  required int maxEventBytes,
}) {
  web.EventSource? source;
  late final StreamController<String> controller;
  void finish([Object? error]) {
    source?.close();
    source = null;
    if (controller.isClosed) return;
    if (error != null) controller.addError(error);
    controller.close();
  }

  controller = StreamController<String>(
    onListen: () {
      final opened = web.EventSource(
        request.uri.toString(),
        web.EventSourceInit(withCredentials: true),
      );
      source = opened;
      opened.onmessage = ((web.MessageEvent event) {
        final data = event.data;
        if (data == null || !data.typeofEquals('string')) return;
        final text = (data as JSString).toDart;
        if (text.length > maxEventBytes) {
          finish(
            const LumenisTransportException('Event exceeds maxEventBytes.'),
          );
          return;
        }
        controller.add(text);
      }).toJS;
      // EventSource would silently reconnect; the product ends the stream
      // instead and lets the screen re-establish it with fresh bindings.
      opened.onerror = ((web.Event _) => finish()).toJS;
    },
    onCancel: () => finish(),
  );
  return controller.stream;
}
