import 'dart:async';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/transport/lumenis_http_transport.dart';

void main() {
  late HttpServer server;

  Future<Uri> startServer(Future<void> Function(HttpRequest) handle) async {
    server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    server.listen((request) {
      unawaited(handle(request));
    });
    return Uri.parse('http://${server.address.address}:${server.port}');
  }

  tearDown(() async {
    await server.close(force: true);
  });

  LumenisTransportRequest request(
    Uri uri, {
    Duration timeout = const Duration(seconds: 2),
    Map<String, String> headers = const {},
  }) => LumenisTransportRequest(
    method: 'GET',
    uri: uri,
    headers: headers,
    connectionTimeout: timeout,
  );

  test(
    'returns arbitrary bytes and preserves the supplied request headers',
    () async {
      final received = Completer<Map<String, String>>();
      final base = await startServer((incoming) async {
        received.complete({
          'method': incoming.method,
          'accept': incoming.headers.value(HttpHeaders.acceptHeader) ?? '',
          'x-media-token': incoming.headers.value('x-media-token') ?? '',
        });
        incoming.response
          ..headers.contentType = ContentType('audio', 'mpeg')
          ..add([0, 255, 195, 40]);
        await incoming.response.close();
      });

      final result = await sendLumenisBinaryRequest(
        request(
          base,
          headers: const {
            'accept': 'audio/mpeg',
            'x-media-token': 'opaque-value',
          },
        ),
        maxBytes: 4,
      );

      expect(result.statusCode, HttpStatus.ok);
      expect(result.bytes, [0, 255, 195, 40]);
      expect(result.contentType, startsWith('audio/mpeg'));
      expect(result.headers['content-type'], startsWith('audio/mpeg'));
      expect(await received.future, {
        'method': 'GET',
        'accept': 'audio/mpeg',
        'x-media-token': 'opaque-value',
      });
    },
  );

  test(
    'uploads exact binary bytes and returns the existing JSON text response',
    () async {
      final receivedBytes = Completer<List<int>>();
      final receivedContentType = Completer<String?>();
      final base = await startServer((incoming) async {
        receivedContentType.complete(
          incoming.headers.value(HttpHeaders.contentTypeHeader),
        );
        final bytes = await incoming.fold<List<int>>(
          <int>[],
          (all, chunk) => all..addAll(chunk),
        );
        receivedBytes.complete(bytes);
        incoming.response
          ..headers.contentType = ContentType.json
          ..write('{"uploaded":true}');
        await incoming.response.close();
      });
      final sourceBytes = Uint8List.fromList([0, 255, 195, 40, 10]);

      final result = await sendLumenisHttpRequest(
        LumenisTransportRequest(
          method: 'POST',
          uri: base,
          headers: const {
            HttpHeaders.contentTypeHeader: 'application/octet-stream',
            HttpHeaders.acceptHeader: 'application/json',
          },
          connectionTimeout: const Duration(seconds: 2),
          bodyBytes: sourceBytes,
        ),
      );

      expect(await receivedBytes.future, sourceBytes);
      expect(await receivedContentType.future, 'application/octet-stream');
      expect(result.statusCode, HttpStatus.ok);
      expect(result.body, '{"uploaded":true}');
    },
  );

  test('rejects an oversized chunked body without Content-Length', () async {
    final base = await startServer((incoming) async {
      incoming.response.headers.chunkedTransferEncoding = true;
      incoming.response.add([1, 2, 3]);
      await incoming.response.flush();
      try {
        incoming.response.add([4, 5]);
        await incoming.response.close();
      } on IOException {
        // The transport closes the connection as soon as the limit is crossed.
      }
    });

    await expectLater(
      sendLumenisBinaryRequest(request(base), maxBytes: 4),
      throwsA(isA<LumenisTransportException>()),
    );
  });

  test('rejects a declared Content-Length over the limit', () async {
    final base = await startServer((incoming) async {
      incoming.response.contentLength = 5;
      incoming.response.add([1, 2, 3, 4, 5]);
      try {
        await incoming.response.close();
      } on IOException {
        // The transport rejects the declared size before buffering the body.
      }
    });

    await expectLater(
      sendLumenisBinaryRequest(request(base), maxBytes: 4),
      throwsA(isA<LumenisTransportException>()),
    );
  });

  test('rejects redirects without requesting the redirect target', () async {
    var targetCalls = 0;
    late Uri base;
    base = await startServer((incoming) async {
      if (incoming.uri.path == '/redirect') {
        incoming.response
          ..statusCode = HttpStatus.found
          ..headers.set(HttpHeaders.locationHeader, '$base/target');
        await incoming.response.close();
        return;
      }
      targetCalls++;
      incoming.response.write('unexpected');
      await incoming.response.close();
    });

    await expectLater(
      sendLumenisBinaryRequest(
        request(base.replace(path: '/redirect')),
        maxBytes: 100,
      ),
      throwsA(isA<LumenisTransportException>()),
    );
    expect(targetCalls, 0);
  });

  test(
    'applies the timeout through a stalled response body and closes it',
    () async {
      final bodyStarted = Completer<void>();
      final base = await startServer((incoming) async {
        incoming.response.headers.chunkedTransferEncoding = true;
        incoming.response.add([1]);
        await incoming.response.flush();
        bodyStarted.complete();
        await Future<void>.delayed(const Duration(seconds: 1));
        try {
          incoming.response.add([2]);
          await incoming.response.close();
        } on IOException {
          // The client closes the stalled response when its total timeout expires.
        }
      });

      await expectLater(
        sendLumenisBinaryRequest(
          request(base, timeout: const Duration(milliseconds: 150)),
          maxBytes: 100,
        ),
        throwsA(isA<LumenisTransportException>()),
      );
      expect(bodyStarted.isCompleted, isTrue);
    },
  );

  test('invalid limits fail before opening a connection', () async {
    var calls = 0;
    final base = await startServer((incoming) async {
      calls++;
      incoming.response.close();
    });

    await expectLater(
      sendLumenisBinaryRequest(request(base), maxBytes: 0),
      throwsArgumentError,
    );
    expect(calls, 0);
  });

  test(
    'rejects simultaneous text and binary bodies before opening a connection',
    () async {
      var calls = 0;
      final base = await startServer((incoming) async {
        calls++;
        await incoming.response.close();
      });
      final invalidRequest = LumenisTransportRequest(
        method: 'POST',
        uri: base,
        headers: const {},
        connectionTimeout: const Duration(seconds: 2),
        body: 'text',
        bodyBytes: Uint8List.fromList([1]),
      );

      await expectLater(
        sendLumenisHttpRequest(invalidRequest),
        throwsArgumentError,
      );
      await expectLater(
        sendLumenisBinaryRequest(invalidRequest, maxBytes: 16),
        throwsArgumentError,
      );
      expect(calls, 0);
    },
  );
}
