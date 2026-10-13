import 'lumenis_http_transport_stub.dart'
    if (dart.library.io) 'lumenis_http_transport_io.dart'
    if (dart.library.js_interop) 'lumenis_http_transport_web.dart'
    as platform;
import 'lumenis_http_transport_types.dart';

export 'lumenis_http_transport_types.dart';

/// Retained compatibility capability; all platforms return false.
///
/// No client may fetch the server's reusable credential. Workspace and session
/// authorization remain server-owned on every platform.
bool get supportsLocalCoreCredentialBootstrap =>
    platform.supportsLocalCoreCredentialBootstrap;

Future<LumenisTransportResponse> sendLumenisHttpRequest(
  LumenisTransportRequest request,
) => platform.sendLumenisHttpRequest(request);

Future<LumenisBinaryTransportResponse> sendLumenisBinaryRequest(
  LumenisTransportRequest request, {
  required int maxBytes,
}) => platform.sendLumenisBinaryRequest(request, maxBytes: maxBytes);

Stream<String> openLumenisEventStream(
  LumenisTransportRequest request, {
  required int maxEventBytes,
}) => platform.openLumenisEventStream(request, maxEventBytes: maxEventBytes);

bool isLumenisConnectionError(Object error) =>
    error is LumenisTransportException;
