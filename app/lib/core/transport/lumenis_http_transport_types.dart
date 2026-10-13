import 'dart:convert';
import 'dart:typed_data';

class LumenisTransportRequest {
  const LumenisTransportRequest({
    required this.method,
    required this.uri,
    required this.headers,
    required this.connectionTimeout,
    this.body,
    this.bodyBytes,
    this.followRedirects = true,
  });

  final String method;
  final Uri uri;
  final Map<String, String> headers;
  final Duration connectionTimeout;
  final String? body;
  final Uint8List? bodyBytes;
  final bool followRedirects;

  void validateBody() {
    if (body != null && bodyBytes != null) {
      throw ArgumentError('Specify either body or bodyBytes, not both.');
    }
  }
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
    'x-source-artifact-id',
    'x-content-sha256',
    'x-lumenis-frame-id',
    'x-lumenis-target-id',
    'x-lumenis-page-revision',
    'x-lumenis-captured-at',
    'x-lumenis-frame-width',
    'x-lumenis-frame-height',
    'x-lumenis-viewport-width',
    'x-lumenis-viewport-height',
    'x-lumenis-viewport-dpr',
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

class LumenisBinaryTransportResponse {
  LumenisBinaryTransportResponse({
    required this.statusCode,
    required this.bytes,
    required this.contentType,
    Map<String, String> headers = const {},
  }) : headers = Map.unmodifiable({
         for (final entry in headers.entries)
           if (_allowedHeaders.contains(entry.key.toLowerCase()))
             entry.key.toLowerCase(): entry.value,
       });

  static const _allowedHeaders = {
    'content-type',
    'cache-control',
    'x-source-artifact-id',
    'x-content-sha256',
    'x-lumenis-frame-id',
    'x-lumenis-target-id',
    'x-lumenis-page-revision',
    'x-lumenis-captured-at',
    'x-lumenis-frame-width',
    'x-lumenis-frame-height',
    'x-lumenis-viewport-width',
    'x-lumenis-viewport-height',
    'x-lumenis-viewport-dpr',
  };

  final int statusCode;
  final Uint8List bytes;
  final String? contentType;
  final Map<String, String> headers;
}

class LumenisTransportException implements Exception {
  const LumenisTransportException(this.message);

  final String message;

  @override
  String toString() => 'LumenisTransportException: $message';
}
