import 'lumenis_http_transport_types.dart';

const supportsLocalCoreCredentialBootstrap = false;

Future<LumenisTransportResponse> sendLumenisHttpRequest(
  LumenisTransportRequest request,
) => throw const LumenisTransportException(
  'HTTP transport is unavailable on this platform.',
);

Future<LumenisBinaryTransportResponse> sendLumenisBinaryRequest(
  LumenisTransportRequest request, {
  required int maxBytes,
}) => throw const LumenisTransportException(
  'HTTP transport is unavailable on this platform.',
);

Stream<String> openLumenisEventStream(
  LumenisTransportRequest request, {
  required int maxEventBytes,
}) => Stream<String>.error(
  const LumenisTransportException(
    'Event stream transport is unavailable on this platform.',
  ),
);
