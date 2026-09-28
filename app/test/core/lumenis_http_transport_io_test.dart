import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/transport/lumenis_http_transport_io.dart';
import 'package:lumenis_app/core/transport/lumenis_http_transport_types.dart';

void main() {
  late HttpServer server;

  setUp(() async {
    server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    addTearDown(() => server.close(force: true));
  });

  LumenisTransportRequest request(String path, {String? body}) =>
      LumenisTransportRequest(
        method: body == null ? 'GET' : 'POST',
        uri: Uri.parse('http://127.0.0.1:${server.port}$path'),
        headers: body == null
            ? {}
            : {'content-type': 'application/json; charset=utf-8'},
        connectionTimeout: const Duration(seconds: 5),
        followRedirects: false,
        body: body,
      );

  test('loopback PNG retains bytes and allowed frame metadata', () async {
    final png = base64Decode(
      'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDw'
      'AEhQGAhKmMIQAAAABJRU5ErkJggg==',
    );
    server.listen((incoming) async {
      incoming.response.headers
        ..set('content-type', 'image/png')
        ..set('cache-control', 'no-store, private')
        ..set('x-lumenis-frame-id', 'frame-1')
        ..set('x-lumenis-target-id', 'target-1')
        ..set('x-lumenis-page-revision', '7')
        ..set('x-lumenis-captured-at', '2026-09-28T00:00:00Z')
        ..set('x-lumenis-frame-width', '1')
        ..set('x-lumenis-frame-height', '1')
        ..set('set-cookie', 'test-session=private')
        ..set('x-lumenis-debug-port', '1234');
      incoming.response.add(png.sublist(0, 20));
      incoming.response.add(png.sublist(20));
      await incoming.response.close();
    });

    final response = await sendLumenisHttpRequest(request('/frame'));
    expect(response.statusCode, 200);
    expect(response.bodyBytes, png);
    expect(response.headers, {
      'content-type': 'image/png',
      'cache-control': 'no-store, private',
      'x-lumenis-frame-id': 'frame-1',
      'x-lumenis-target-id': 'target-1',
      'x-lumenis-page-revision': '7',
      'x-lumenis-captured-at': '2026-09-28T00:00:00Z',
      'x-lumenis-frame-width': '1',
      'x-lumenis-frame-height': '1',
    });
    expect(() => response.body, throwsFormatException);
  });

  for (final status in [202, 503]) {
    test('loopback preserves JSON and status $status', () async {
      server.listen((incoming) async {
        expect(incoming.method, 'POST');
        expect(incoming.uri.path, '/state');
        expect(await utf8.decoder.bind(incoming).join(), '{"query":"序境"}');
        incoming.response
          ..statusCode = status
          ..headers.contentType = ContentType.json
          ..write('{"message":"尚无画面 🌊"}');
        await incoming.response.close();
      });
      final response = await sendLumenisHttpRequest(
        request('/state', body: '{"query":"序境"}'),
      );
      expect(response.statusCode, status);
      expect(jsonDecode(response.body), {'message': '尚无画面 🌊'});
      expect(response.bodyBytes, utf8.encode(response.body));
    });
  }

  test(
    'no-follow redirect returns status and discards private location',
    () async {
      var requests = 0;
      server.listen((incoming) async {
        requests++;
        incoming.response
          ..statusCode = 302
          ..headers.set('location', '/private')
          ..write('redirect');
        await incoming.response.close();
      });
      final response = await sendLumenisHttpRequest(request('/redirect'));
      expect(response.statusCode, 302);
      expect(response.body, 'redirect');
      expect(response.headers.containsKey('location'), isFalse);
      expect(requests, 1);
    },
  );
}
