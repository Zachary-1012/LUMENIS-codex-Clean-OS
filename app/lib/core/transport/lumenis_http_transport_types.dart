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
    required this.body,
  });

  final int statusCode;
  final String body;
}

class LumenisTransportException implements Exception {
  const LumenisTransportException(this.message);

  final String message;

  @override
  String toString() => 'LumenisTransportException: $message';
}
