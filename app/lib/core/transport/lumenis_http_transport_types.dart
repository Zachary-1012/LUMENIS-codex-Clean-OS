import 'dart:convert';
import 'dart:typed_data';

class LumenisTransportRequest {
  const LumenisTransportRequest({
    required this.method,
    required this.uri,
    required this.headers,
    required this.connectionTimeout,
    this.body,
    this.followRedirects = true,
  });

  final String method;
  final Uri uri;
  final Map<String, String> headers;
  final Duration connectionTimeout;
  final String? body;
  final bool followRedirects;
}

class LumenisTransportResponse {
  const LumenisTransportResponse({
    required this.statusCode,
    required String this._body,
  }) : _bodyBytes = null,
       headers = const {};

  LumenisTransportResponse.bytes({
    required this.statusCode,
    required List<int> bodyBytes,
    Map<String, String> headers = const {},
  }) : _body = null,
       _bodyBytes = Uint8List.fromList(bodyBytes).asUnmodifiableView(),
       headers = Map.unmodifiable({
         for (final entry in headers.entries)
           if (_allowedHeaders.contains(entry.key.toLowerCase()))
             entry.key.toLowerCase(): entry.value,
       });

  static const _allowedHeaders = {
    'content-type',
    'cache-control',
    'x-lumenis-frame-id',
    'x-lumenis-target-id',
    'x-lumenis-page-revision',
    'x-lumenis-captured-at',
    'x-lumenis-frame-width',
    'x-lumenis-frame-height',
  };

  final int statusCode;
  final String? _body;
  final Uint8List? _bodyBytes;
  final Map<String, String> headers;

  /// Text callers retain strict UTF-8 decoding; binary callers use [bodyBytes].
  String get body => _body ?? utf8.decode(_bodyBytes!);

  Uint8List get bodyBytes =>
      _bodyBytes ??
      Uint8List.fromList(utf8.encode(_body!)).asUnmodifiableView();
}

class LumenisTransportException implements Exception {
  const LumenisTransportException(this.message);

  final String message;

  @override
  String toString() => 'LumenisTransportException: $message';
}
