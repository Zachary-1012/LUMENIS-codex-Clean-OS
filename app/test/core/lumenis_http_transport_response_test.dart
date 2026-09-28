import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/transport/lumenis_http_transport_types.dart';

void main() {
  test(
    'legacy const responses preserve text and expose immutable UTF-8 bytes',
    () {
      const response = LumenisTransportResponse(
        statusCode: 202,
        body: '{"state":"等待中"}',
      );
      expect(response.statusCode, 202);
      expect(jsonDecode(response.body), {'state': '等待中'});
      expect(response.bodyBytes, utf8.encode(response.body));
      expect(() => response.bodyBytes[0] = 0, throwsUnsupportedError);
      expect(response.headers, isEmpty);
    },
  );

  test('PNG remains exact binary and is not decoded implicitly', () {
    final original = base64Decode(
      'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDw'
      'AEhQGAhKmMIQAAAABJRU5ErkJggg==',
    );
    final input = Uint8List.fromList(original);
    final response = LumenisTransportResponse.bytes(
      statusCode: 200,
      bodyBytes: input,
    );
    input[0] = 0;
    expect(response.bodyBytes, original);
    expect(() => response.bodyBytes[0] = 0, throwsUnsupportedError);
    expect(
      () => response.bodyBytes.buffer.asUint8List()[0] = 0,
      throwsUnsupportedError,
    );
    expect(() => response.body, throwsFormatException);
    expect(response.bodyBytes, original);
  });

  test(
    'byte responses retain Unicode JSON, empty bodies and HTTP error status',
    () {
      final response = LumenisTransportResponse.bytes(
        statusCode: 503,
        bodyBytes: utf8.encode('{"message":"暂无画面 🌊"}'),
      );
      expect(response.statusCode, 503);
      expect(jsonDecode(response.body), {'message': '暂无画面 🌊'});
      final empty = LumenisTransportResponse.bytes(
        statusCode: 204,
        bodyBytes: [],
      );
      expect(empty.body, '');
      expect(empty.bodyBytes, isEmpty);
    },
  );

  test('only named response metadata is retained and cannot be changed', () {
    final metadata = <String, String>{
      'Content-Type': 'image/png',
      'Cache-Control': 'no-store, private',
      'X-LUMENIS-Frame-Id': 'frame-1',
      'X-LUMENIS-Target-Id': 'target-1',
      'X-LUMENIS-Page-Revision': '3',
      'X-LUMENIS-Captured-At': '2026-09-28T00:00:00Z',
      'X-LUMENIS-Frame-Width': '800',
      'X-LUMENIS-Frame-Height': '600',
    };
    final input = {
      ...metadata,
      'Set-Cookie': 'test-session=private',
      'Authorization': 'test-private-value',
      'Location': '/private',
      'X-LUMENIS-Session-Id': 'private-session',
      'X-LUMENIS-Account-Id': 'private-account',
      'X-LUMENIS-Debug-Port': '1234',
      'X-Other': 'not-allowed',
    };
    final response = LumenisTransportResponse.bytes(
      statusCode: 200,
      bodyBytes: [],
      headers: input,
    );
    input.clear();
    expect(response.headers, {
      for (final entry in metadata.entries)
        entry.key.toLowerCase(): entry.value,
    });
    expect(
      () => response.headers['content-type'] = 'text/plain',
      throwsUnsupportedError,
    );
  });
}
