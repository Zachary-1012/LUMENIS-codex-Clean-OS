import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/core/transport/lumenis_http_transport.dart';

void main() {
  late HttpServer server;
  late LumenisCoreClient client;
  late List<Map<String, Object?>> calls;
  var responseStatus = 200;
  Map<String, Object?> response = {};
  List<int>? responseBytes;
  String responseType = 'application/json';

  setUp(() async {
    server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    client = LumenisCoreClient(baseUrl: 'http://127.0.0.1:${server.port}');
    calls = [];
    responseStatus = 200;
    response = {'ok': true};
    responseBytes = null;
    responseType = 'application/json';
    server.listen((request) async {
      final bytes = await request.fold<List<int>>(
        [],
        (all, chunk) => all..addAll(chunk),
      );
      final binary =
          request.headers.contentType?.mimeType == 'application/octet-stream';
      final body = binary ? '' : utf8.decode(bytes);
      calls.add({
        'path': request.uri.path,
        'query': request.uri.queryParameters,
        'method': request.method,
        'action': request.headers.value('X-Lumenis-Action'),
        'type': request.headers.contentType?.mimeType,
        'domain': request.headers.value('X-Domain-Id'),
        'product': request.headers.value('X-Product-Id'),
        'mode': request.headers.value('X-Lumenis-Context-Mode'),
        'subject': request.headers.value('X-Subject-ID'),
        'approval': request.headers.value('X-Approval-Token'),
        'authorization': request.headers.value('Authorization'),
        'body': body.isEmpty ? null : jsonDecode(body),
        'bytes': bytes,
      });
      request.response.statusCode = responseStatus;
      request.response.headers.contentType = ContentType.parse(responseType);
      if (responseBytes != null) {
        request.response.contentLength = responseBytes!.length;
        request.response.headers.set('Accept-Ranges', 'bytes');
        if (request.method != 'HEAD') request.response.add(responseBytes!);
      } else {
        request.response.write(jsonEncode(response));
      }
      await request.response.close();
    });
    response = {
      'ok': true,
      'contract': 'lumenis.context.v1',
      'selection_only': true,
      'context': {
        'mode': 'FOCUS',
        'domain_id': 'BMP',
        'subject_id': 'brand-one',
      },
    };
    await client.selectContext(domainId: 'BMP', subjectId: 'brand-one');
    calls.clear();
    response = {'ok': true};
  });
  tearDown(() => server.close(force: true));

  test(
    'saved project listing retains exact focus and opaque page cursor',
    () async {
      final cursor = 'a' * 43;
      await client.listContentProjects(
        domainId: 'BMP',
        cursor: cursor,
        limit: 7,
      );
      expect(calls.single['path'], '/api/experience/content-projects');
      expect(calls.single['query'], {'limit': '7', 'cursor': cursor});
      expect(calls.single['method'], 'GET');
      expect(calls.single['domain'], 'BMP');
      expect(calls.single['subject'], 'brand-one');
      expect(calls.single['mode'], 'FOCUS');
      expect(calls.single['action'], isNull);
      expect(calls.single['body'], isNull);
      expect(calls.single['approval'], isNull);
    },
  );

  test(
    'invalid paging and incompatible scope make no listing request',
    () async {
      for (final limit in [0, 21]) {
        expect(
          () => client.listContentProjects(domainId: 'BMP', limit: limit),
          throwsArgumentError,
        );
      }
      expect(
        () => client.listContentProjects(domainId: 'BMP', cursor: '../unknown'),
        throwsFormatException,
      );
      expect(
        () => client.listContentProjects(domainId: 'CTH'),
        throwsA(isA<LumenisCoreException>()),
      );
      expect(calls, isEmpty);
    },
  );

  test(
    'source import sends exact bytes with a write action and scoped filename',
    () async {
      final bytes = Uint8List.fromList([0, 255, 128, 10]);
      await client.importContentSource(
        domainId: 'BMP',
        filename: '原声 & take.wav',
        bytes: bytes,
      );
      expect(calls.single['path'], '/api/experience/content-sources');
      expect(calls.single['query'], {'filename': '原声 & take.wav'});
      expect(calls.single['bytes'], bytes);
      expect(calls.single['action'], 'WRITE');
      expect(calls.single['type'], 'application/octet-stream');
      expect(calls.single['domain'], 'BMP');
      expect(calls.single['product'], 'ZBMP');
      expect(calls.single['authorization'], isNull);
      expect(calls.single['approval'], isNull);
      expect(
        () => client.importContentSource(
          domainId: 'BMP',
          filename: '../bad.wav',
          bytes: bytes,
        ),
        throwsFormatException,
      );
      expect(
        () => client.importContentSource(
          domainId: 'BMP',
          filename: 'empty.wav',
          bytes: Uint8List(0),
        ),
        throwsFormatException,
      );
      expect(calls, hasLength(1));
    },
  );

  test(
    'approval response is allowlisted and confirmation is explicit',
    () async {
      responseStatus = 403;
      response = {
        'ok': false,
        'code': 'CONTENT_SOURCE_APPROVAL_REQUIRED',
        'requires_approval': true,
        'diagnostic': r'C:\private\must-not-leak',
        'confirmation': {
          'confirmation_id': 'CONF-123',
          'resource': 'content-source-import:v1:${'b' * 64}',
          'expires_at': '2026-09-28T12:00:00Z',
          'filename': 'voice.wav',
          'size_bytes': 4,
          'body_sha256': 'a' * 64,
          'extra': r'C:\private\must-not-leak',
        },
      };
      await expectLater(
        client.importContentSource(
          domainId: 'BMP',
          filename: 'voice.wav',
          bytes: Uint8List.fromList([1, 2, 3, 4]),
        ),
        throwsA(
          isA<LumenisCoreException>()
              .having((error) => error.statusCode, 'status', 403)
              .having(
                (error) => error.errorCode,
                'code',
                'CONTENT_SOURCE_APPROVAL_REQUIRED',
              )
              .having(
                (error) => error.sourceConfirmation?.bodySha256,
                'hash',
                'a' * 64,
              )
              .having(
                (error) => error.sourceConfirmation?.resource,
                'exact resource',
                'content-source-import:v1:${'b' * 64}',
              ),
        ),
      );
      expect(calls.single['approval'], isNull);
      expect(calls.single['subject'], 'brand-one');

      responseStatus = 200;
      response = {
        'ok': true,
        'status': 'ready_for_retry',
        'purpose': 'local_content_draft',
      };
      await client.confirmContentSource(
        domainId: 'BMP',
        confirmationId: 'CONF-123',
        confirmed: true,
      );
      expect(
        calls.last['path'],
        '/api/experience/content-source-confirmations/CONF-123',
      );
      expect(calls.last['method'], 'POST');
      expect(calls.last['body'], {'confirmed': true});
      expect(calls.last['domain'], 'BMP');
      expect(calls.last['subject'], 'brand-one');
    },
  );

  test('confirmation rejects malformed resources from the server', () {
    final confirmation = <String, Object>{
      'confirmation_id': 'CONF-123',
      'expires_at': '2026-09-30T12:00:00',
      'filename': 'voice.wav',
      'size_bytes': 4,
      'body_sha256': 'a' * 64,
    };
    for (final resource in [
      'content_source',
      'content-source-import:v1:${'b' * 63}',
      'content-source-import:v1:${'b' * 65}',
      'content-source-import:v1:${'B' * 64}',
      'content-source-import:v2:${'b' * 64}',
      'content-source-import:v1:${'b' * 64}\n',
      'https://example.invalid/${'b' * 64}',
    ]) {
      expect(
        ContentSourceConfirmation.tryParse({
          ...confirmation,
          'resource': resource,
        }),
        isNull,
        reason: resource,
      );
    }
  });

  test(
    'registered source references stay distinct from Core-local paths',
    () async {
      await client.inspectContentMedia(
        domainId: 'BMP',
        assetRefs: ['ART-source'],
      );
      expect(calls.single['body'], {
        'action_type': 'READ',
        'input': {
          'asset_refs': ['ART-source'],
        },
      });
      await client.exportContentProject(
        domainId: 'BMP',
        assetRefs: ['ART-source'],
        timeline: {'version': 1},
        outputKind: 'video',
        demoAcknowledged: true,
        renderOptions: {'loudness_target_lufs': -16},
        deliveryOptions: {
          'audio_formats': ['mp3', 'm4a'],
        },
      );
      final input = (calls.last['body'] as Map)['input'] as Map;
      expect(input['asset_refs'], ['ART-source']);
      expect(input['render_options'], {'loudness_target_lufs': -16});
      expect(input['delivery_options'], {
        'audio_formats': ['mp3', 'm4a'],
      });
      expect(input.containsKey('asset_paths'), isFalse);
      expect(
        () => client.inspectContentMedia(
          domainId: 'BMP',
          assetPaths: ['local.mp4'],
          assetRefs: ['ART-source'],
        ),
        throwsFormatException,
      );
      expect(
        () => client.inspectContentMedia(
          domainId: 'BMP',
          assetRefs: ['../source'],
        ),
        throwsFormatException,
      );
      expect(calls, hasLength(2));
    },
  );

  test(
    'artifact download validates scoped stream metadata and rejects wrong media type or denial',
    () async {
      responseBytes = [80, 75, 0, 255, 128];
      responseType = 'application/zip';
      final file = await client.contentProjectFile(
        domainId: 'BMP',
        artifactId: 'ART-version',
        package: true,
      );
      expect(file.bytes, isEmpty);
      expect(calls.single['method'], 'HEAD');
      expect(file.streamUri?.path, '/api/experience/content-projects/ART-version/package');
      expect(file.streamUri?.queryParameters['format'], 'package');
      expect(jsonDecode(file.streamUri!.queryParameters['context']!)['X-Subject-ID'], 'brand-one');
      expect(file.filename, 'ART-version.zip');
      expect(file.mediaType, 'application/zip');
      expect(
        calls.single['path'],
        '/api/experience/content-projects/ART-version/package',
      );
      expect(calls.single['domain'], 'BMP');
      responseType = 'text/html';
      await expectLater(
        client.contentProjectFile(
          domainId: 'BMP',
          artifactId: 'ART-version',
          package: false,
        ),
        throwsFormatException,
      );
      responseStatus = 403;
      await expectLater(
        client.contentProjectFile(
          domainId: 'BMP',
          artifactId: 'ART-version',
          package: true,
        ),
        throwsA(
          isA<LumenisCoreException>().having(
            (e) => e.statusCode,
            'status',
            403,
          ),
        ),
      );
    },
  );

  test(
    'global media actions require explicit CTH or BMP invoking domain',
    () async {
      response = {
        'ok': true,
        'contract': 'lumenis.context.v1',
        'selection_only': true,
        'context': {'mode': 'GLOBAL_ALL', 'subject_id': null},
      };
      await client.clearContext();
      calls.clear();
      response = {'ok': true};
      await client.inspectContentMedia(
        domainId: 'BMP',
        assetPaths: ['local.mp4'],
      );
      expect(
        calls.single['path'],
        '/api/experience/shared-skills/shared.content_project/inspect',
      );
      expect(calls.single['domain'], 'BMP');
      expect(calls.single['product'], 'ZBMP');
      expect(calls.single['mode'], 'GLOBAL_ALL');
      expect(calls.single['subject'], isNull);
      expect(calls.single['authorization'], isNull);
      expect(calls.single['body'], {
        'action_type': 'READ',
        'input': {
          'asset_paths': ['local.mp4'],
        },
      });
      calls.clear();
      await client.inspectContentMedia(
        domainId: 'CTH',
        assetPaths: ['local.wav'],
      );
      expect(calls.last['domain'], 'CTH');
      expect(calls.last['product'], 'CTH');
      expect(calls.last['subject'], isNull);
      await client.sharedSkillsCatalog();
      expect(calls.last['domain'], isNull);
      expect(calls.last['mode'], 'GLOBAL_ALL');
    },
  );

  test(
    'export sends edit intent and demo choice, never publish or actor claims',
    () async {
      response = {
        'ok': true,
        'contract': 'lumenis.context.v1',
        'selection_only': true,
        'context': {
          'mode': 'FOCUS',
          'domain_id': 'CTH',
          'subject_id': 'subject-one',
        },
      };
      await client.selectContext(domainId: 'CTH', subjectId: 'subject-one');
      calls.clear();
      response = {'ok': true};
      await client.exportContentProject(
        domainId: 'CTH',
        assetPaths: ['local.wav'],
        timeline: {'version': 3},
        outputKind: 'audio',
        demoAcknowledged: true,
        previousArtifactId: 'ART-parent',
      );
      expect(calls.single['domain'], 'CTH');
      expect(calls.single['product'], 'CTH');
      expect(calls.single['subject'], 'subject-one');
      expect(calls.single['path'], '/api/experience/content-projects/export');
      expect(calls.single['body'], {
        'action_type': 'EXPORT',
        'input': {
          'asset_paths': ['local.wav'],
          'timeline': {'version': 3},
          'output_kind': 'audio',
          'demo_acknowledged': true,
          'previous_artifact_id': 'ART-parent',
        },
      });
    },
  );

  test('reopen uses only the registered project identity', () async {
    await client.reopenContentProject(domainId: 'BMP', artifactId: 'ART-123');
    expect(calls.single['path'], '/api/experience/content-projects/ART-123');
    expect(calls.single['method'], 'GET');
    expect(calls.single['body'], isNull);
    expect(
      () => client.reopenContentProject(
        domainId: 'BMP',
        artifactId: '../../private',
      ),
      throwsFormatException,
    );
    expect(calls, hasLength(1));
  });

  test('mismatching focused domain never sends a content request', () async {
    response = {
      'ok': true,
      'contract': 'lumenis.context.v1',
      'selection_only': true,
      'context': {
        'mode': 'FOCUS',
        'domain_id': 'BMP',
        'subject_id': 'brand-one',
      },
    };
    await client.selectContext(domainId: 'BMP', subjectId: 'brand-one');
    expect(
      () => client.inspectContentMedia(domainId: 'CTH', assetPaths: []),
      throwsA(
        isA<LumenisCoreException>().having(
          (error) => error.errorCode,
          'errorCode',
          'CONTENT_CONTEXT_MISMATCH',
        ),
      ),
    );
    expect(
      () => client.exportContentProject(
        domainId: 'CTH',
        assetPaths: ['local.wav'],
        timeline: {'version': 1},
        outputKind: 'audio',
        demoAcknowledged: true,
      ),
      throwsA(
        isA<LumenisCoreException>().having(
          (error) => error.errorCode,
          'errorCode',
          'CONTENT_CONTEXT_MISMATCH',
        ),
      ),
    );
    expect(calls, hasLength(1));
    await client.inspectContentMedia(
      domainId: 'BMP',
      assetPaths: ['local.mp4'],
    );
    expect(calls.last['subject'], 'brand-one');
    expect(calls.last['mode'], 'FOCUS');
  });

  test(
    'denial retains a safe recovery code, not arbitrary diagnostics',
    () async {
      responseStatus = 403;
      response = {'ok': false, 'code': 'CONTENT_SCOPE_DENIED'};
      await expectLater(
        client.inspectContentMedia(domainId: 'BMP', assetPaths: []),
        throwsA(
          isA<LumenisCoreException>()
              .having((e) => e.statusCode, 'status', 403)
              .having((e) => e.errorCode, 'code', 'CONTENT_SCOPE_DENIED'),
        ),
      );
      response = {'ok': false, 'code': 'C:\\private\\do-not-display'};
      await expectLater(
        client.inspectContentMedia(domainId: 'BMP', assetPaths: []),
        throwsA(
          isA<LumenisCoreException>().having(
            (e) => e.errorCode,
            'code',
            isNull,
          ),
        ),
      );
    },
  );

  test('file stream upload preserves bytes, scope and explicit write with no file path disclosure', () async {
    final chunks = [List<int>.generate(65536, (i) => i % 256), [0, 255, 128, 4]];
    await client.importContentSourceStream(domainId: 'BMP', filename: 'large.wav',
      upload: LumenisUploadBody(length: chunks.fold<int>(0, (n, c) => n + c.length),
        openRead: () => Stream.fromIterable(chunks)));
    expect(calls.single['bytes'], chunks.expand((c) => c).toList());
    expect(calls.single['action'], 'WRITE');
    expect(calls.single['subject'], 'brand-one');
    expect(calls.single['query'], {'filename': 'large.wav'});
  });
}
