import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/transport/lumenis_http_transport.dart';

void main() {
  test('native transport does not expose Core credential bootstrap', () {
    expect(supportsLocalCoreCredentialBootstrap, isFalse);
  });

  test('connection failures use a platform-neutral transport error', () {
    const error = LumenisTransportException('connection refused');

    expect(isLumenisConnectionError(error), isTrue);
    expect(
      isLumenisConnectionError(const FormatException('bad payload')),
      isFalse,
    );
  });
}
