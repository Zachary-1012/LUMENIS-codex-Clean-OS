@TestOn('browser')
library;

import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/core/transport/lumenis_http_transport.dart';

void main() {
  test('Web Workspace uses its hosting origin, not the visitor loopback', () {
    expect(LumenisCoreClient().baseUrl, Uri.base.origin);
    expect(supportsLocalCoreCredentialBootstrap, isFalse);
  });

  test('an explicit Core deployment URL is preserved', () {
    final client = LumenisCoreClient(baseUrl: 'https://core.example.test');
    expect(client.baseUrl, 'https://core.example.test');
  });
}
