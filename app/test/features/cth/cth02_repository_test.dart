import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/features/cth/cth02/cth02_repository.dart';

void main() {
  test('repository preserves the existing server Permission denial', () async {
    final requests = <String>[];
    final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    addTearDown(() => server.close(force: true));
    server.listen((request) async {
      requests.add(request.uri.toString());
      expect(request.headers.value(HttpHeaders.authorizationHeader), isNull);
      request.response.statusCode = HttpStatus.unauthorized;
      request.response.headers.contentType = ContentType.json;
      request.response.write(jsonEncode({'subject_id': 'MUST_NOT_BE_EXPOSED'}));
      await request.response.close();
    });

    final client = LumenisCoreClient(
      baseUrl: 'http://127.0.0.1:${server.port}',
    );
    final repository = CoreCth02Repository(client: client);

    await expectLater(
      repository.loadDirectory(),
      throwsA(
        isA<LumenisCoreException>().having(
          (error) => error.statusCode,
          'statusCode',
          HttpStatus.unauthorized,
        ),
      ),
    );
    expect(requests, ['/api/settings/subjects?domain_id=CTH']);
    expect(requests, isNot(contains('/api/experience/screen/CTH-02')));
  });
}
