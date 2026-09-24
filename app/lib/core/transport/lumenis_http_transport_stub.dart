import 'lumenis_http_transport_types.dart';

const supportsLocalCoreCredentialBootstrap = false;

Future<LumenisTransportResponse> sendLumenisHttpRequest(
  LumenisTransportRequest request,
) => throw const LumenisTransportException(
  'HTTP transport is unavailable on this platform.',
);
