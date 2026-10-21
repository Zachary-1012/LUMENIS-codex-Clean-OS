@TestOn('browser')
library;

import 'dart:async';
import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:lumenis_app/core/transport/lumenis_http_transport_types.dart';
import 'package:lumenis_app/core/transport/lumenis_http_transport_web.dart';

void main() {
  LumenisTransportRequest request({String? body}) => LumenisTransportRequest(
    method: body == null ? 'GET' : 'POST',
    uri: Uri.parse('https://transport.test/frame'),
    headers: {'content-type': 'application/json; charset=utf-8'},
    connectionTimeout: const Duration(seconds: 5),
    followRedirects: false,
    body: body,
  );

  test('web adapter keeps bootstrap disabled', () {
    expect(supportsLocalCoreCredentialBootstrap, isFalse);
  });

  test('streamed PNG is exact binary and exposes only safe metadata', () async {
    final png = base64Decode(
      'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDw'
      'AEhQGAhKmMIQAAAABJRU5ErkJggg==',
    );
    final response = await http.runWithClient(
      () => sendLumenisHttpRequest(request()),
      () => MockClient.streaming((incoming, body) async {
        expect(incoming.method, 'GET');
        expect(incoming.followRedirects, isFalse);
        expect(await body.toBytes(), isEmpty);
        return http.StreamedResponse(
          Stream.fromIterable([png.sublist(0, 20), png.sublist(20)]),
          200,
          headers: {
            'Content-Type': 'image/png',
            'Cache-Control': 'no-store, private',
            'X-LUMENIS-Frame-Id': 'frame-1',
            'X-LUMENIS-Target-Id': 'target-1',
            'X-LUMENIS-Page-Revision': '7',
            'X-LUMENIS-Captured-At': '2026-09-28T00:00:00Z',
            'X-LUMENIS-Frame-Width': '1',
            'X-LUMENIS-Frame-Height': '1',
            'Set-Cookie': 'test-session=private',
            'Authorization': 'test-private-value',
            'X-LUMENIS-Debug-Port': '1234',
          },
        );
      }),
    );
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
    test(
      'web adapter preserves Unicode request, JSON and status $status',
      () async {
        final response = await http.runWithClient(
          () => sendLumenisHttpRequest(request(body: '{"query":"序境"}')),
          () => MockClient((incoming) async {
            expect(incoming.method, 'POST');
            expect(incoming.body, '{"query":"序境"}');
            expect(incoming.followRedirects, isFalse);
            return http.Response.bytes(
              utf8.encode('{"message":"尚无画面 🌊"}'),
              status,
              headers: {'content-type': 'application/json'},
            );
          }),
        );
        expect(response.statusCode, status);
        expect(jsonDecode(response.body), {'message': '尚无画面 🌊'});
      },
    );
  }

  test(
    'web request failures retain the transport exception boundary',
    () async {
      for (final error in [
        http.ClientException('unavailable'),
        TimeoutException('timed out'),
      ]) {
        await expectLater(
          http.runWithClient(
            () => sendLumenisHttpRequest(request()),
            () => MockClient((_) async => throw error),
          ),
          throwsA(isA<LumenisTransportException>()),
        );
      }
    },
  );
}
