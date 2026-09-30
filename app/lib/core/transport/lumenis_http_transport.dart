import 'lumenis_http_transport_stub.dart'
    if (dart.library.io) 'lumenis_http_transport_io.dart'
    if (dart.library.js_interop) 'lumenis_http_transport_web.dart'
    as platform;
import 'lumenis_http_transport_types.dart';

export 'lumenis_http_transport_types.dart';

/// Whether this platform may consume the loopback-only Core bootstrap header.
///
/// Browser clients never receive that reusable local credential. Protected Web
/// Workspace access remains a server-owned product capability, not a client
/// shortcut around Permission.
bool get supportsLocalCoreCredentialBootstrap =>
    platform.supportsLocalCoreCredentialBootstrap;

Future<LumenisTransportResponse> sendLumenisHttpRequest(
  LumenisTransportRequest request,
) => platform.sendLumenisHttpRequest(request);

Future<LumenisBinaryTransportResponse> sendLumenisBinaryRequest(
  LumenisTransportRequest request, {
  required int maxBytes,
}) => platform.sendLumenisBinaryRequest(request, maxBytes: maxBytes);

bool isLumenisConnectionError(Object error) =>
    error is LumenisTransportException;
