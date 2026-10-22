import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';

void main() {
  test(
    'source waveform uses the existing independent Shared inspection route',
    () async {
      final server = await _CoreStub.start();
      addTearDown(server.close);
      final client = LumenisCoreClient(baseUrl: server.baseUrl);
      await client.inspectContentWaveform(
        domainId: null,
        assetRef: 'ART-source',
        startSec: 12,
        endSec: 34,
        audioStreamIndex: 1,
      );
      final request = server.requests.single;
      expect(request.method, 'POST');
      expect(
        request.path,
        '/api/experience/shared-skills/shared.content_project/inspect',
      );
      expect(
        request.workspaceScope,
        '{"scope_kind":"shared_workspace","version":1}',
      );
      expect(jsonDecode(request.body!), {
        'action_type': 'READ',
        'input': {
          'asset_refs': ['ART-source'],
          'waveform': {
            'start_sec': 12.0,
            'end_sec': 34.0,
            'audio_stream_index': 1,
            'bins': 256,
          },
        },
      });
    },
  );
  test(
    'SH-02 uploads one selected file through the exact Shared route',
    () async {
      final server = await _CoreStub.start();
      addTearDown(server.close);
      final client = LumenisCoreClient(baseUrl: server.baseUrl);

      final response = await client.importSharedDocument(
        filename: '研究材料.txt',
        bytes: Uint8List.fromList(utf8.encode('原始资料')),
        requestId: 'sh02-request-001',
      );

      expect(response['ok'], isTrue);
      final request = server.requests.single;
      expect(request.method, 'POST');
      expect(request.path, '/api/experience/materials/documents');
      expect(
        request.workspaceScope,
        '{"scope_kind":"shared_workspace","version":1}',
      );
      expect(request.contextMode, isNull);
      expect(request.domainId, isNull);
      expect(request.authorization, isNull);
      expect(
        request.headers['content-type'],
        startsWith('multipart/form-data; boundary=lumenis-sh02-'),
      );
      expect(request.body, contains('name="file"'));
      expect(
        request.body,
        contains("filename*=UTF-8''%E7%A0%94%E7%A9%B6%E6%9D%90%E6%96%99.txt"),
      );
      expect(request.body, contains('原始资料'));
      expect(request.body, contains('sh02-request-001'));
    },
  );

  test(
    'SH-02 rejects unsupported and oversized files before a request',
    () async {
      final server = await _CoreStub.start();
      addTearDown(server.close);
      final client = LumenisCoreClient(baseUrl: server.baseUrl);

      expect(
        () => client.importSharedDocument(
          filename: 'script.exe',
          bytes: Uint8List.fromList([1]),
          requestId: 'sh02-request-002',
        ),
        throwsFormatException,
      );
      expect(
        () => client.importSharedDocument(
          filename: 'source.txt',
          bytes: Uint8List(8 * 1024 * 1024 + 1),
          requestId: 'sh02-request-003',
        ),
        throwsFormatException,
      );
      expect(server.requests, isEmpty);
    },
  );

  test(
    'SH-02 recent imports use the existing scoped SavedWork search',
    () async {
      final server = await _CoreStub.start();
      addTearDown(server.close);
      final client = LumenisCoreClient(baseUrl: server.baseUrl);

      await client.listSharedDocumentImports();
      final request = server.requests.single;
      expect(request.method, 'GET');
      expect(request.path, startsWith('/api/experience/saved-work?'));
      expect(
        request.workspaceScope,
        '{"scope_kind":"shared_workspace","version":1}',
      );
      final query = Uri.parse(
        'http://localhost${request.path}',
      ).queryParameters;
      expect(query['kind'], 'research');
      expect(query['query'], 'Private uploaded source analysis');
      expect(query['latest_only'], 'true');
      expect(query['limit'], '30');
    },
  );

  test(
    'SourceBrief SavedWork uses its scoped save and canonical readback routes',
    () async {
      final server = await _CoreStub.start(
        contextResponses: [_contextEnvelope('GLOBAL_ALL')],
      );
      addTearDown(server.close);
      final client = LumenisCoreClient(baseUrl: server.baseUrl);
      await client.settingsContext();

      final saved = await client.saveSourceBriefResult(
        domainId: 'CTH',
        jobId: 'brief-0123456789abcdef0123456789abcdef',
        requestId: 'sourcebrief-request-01',
        title: '来源简报',
      );
      final reopened = await client.reopenSourceBriefSavedWork(
        domainId: 'CTH',
        artifactId: 'ART-0123456789abcdef',
      );

      expect(saved['ok'], isTrue);
      expect(reopened['ok'], isTrue);
      final saveRequest = server.requests.singleWhere(
        (request) => request.path.endsWith('/save'),
      );
      expect(saveRequest.method, 'POST');
      expect(saveRequest.path, contains('/source-brief/jobs/'));
      expect(jsonDecode(saveRequest.body!) as Map<String, dynamic>, {
        'request_id': 'sourcebrief-request-01',
        'title': '来源简报',
      });
      expect(saveRequest.contextMode, 'GLOBAL_ALL');
      expect(saveRequest.domainId, 'CTH');
      expect(saveRequest.headers['x-product-id'], 'CTH');
      final reopenRequest = server.requests.singleWhere(
        (request) =>
            request.method == 'GET' &&
            request.path == '/api/experience/saved-work/ART-0123456789abcdef',
      );
      expect(reopenRequest.contextMode, 'GLOBAL_ALL');
      expect(reopenRequest.domainId, 'CTH');
      expect(reopenRequest.headers['cache-control'], 'no-store');
    },
  );

  test(
    'media confirmation accepts exact Shared resource without widening its schema',
    () {
      final value = <String, Object?>{
        'confirmation_id': 'CONF-shared',
        'resource': 'content-source-import:shared-workspace:v1:${'a' * 64}',
        'expires_at': '2027-01-01T00:00:00Z',
        'filename': 'voice.wav',
        'size_bytes': 2,
        'body_sha256': 'b' * 64,
      };
      expect(
        ContentSourceConfirmation.tryParse(value)?.resource,
        value['resource'],
      );
      expect(
        ContentSourceConfirmation.tryParse({
          ...value,
          'resource': 'content-source-import:v1:${'a' * 64}',
        }),
        isNotNull,
      );
      for (final resource in [
        'content-source-import:SHARED:v1:${'a' * 64}',
        'content-source-import:shared-workspace:v2:${'a' * 64}',
        'content-source-import:shared-workspace:v1:${'a' * 63}',
      ]) {
        expect(
          ContentSourceConfirmation.tryParse({...value, 'resource': resource}),
          isNull,
        );
      }
    },
  );

  test(
    'independent media actions never inherit focused business headers',
    () async {
      final server = await _CoreStub.start(
        contextResponses: [
          _contextEnvelope('FOCUS', domainId: 'CTH', subjectId: 'shop-1'),
        ],
      );
      addTearDown(server.close);
      final client = LumenisCoreClient(baseUrl: server.baseUrl);
      await client.selectContext(domainId: 'CTH', subjectId: 'shop-1');
      await client.inspectContentMedia(
        domainId: null,
        assetRefs: ['ART-source'],
      );
      await client.inspectContentEditBatch(
        domainId: null,
        assetRefs: ['ART-source'],
        timeline: {'version': 1},
        commands: [],
        expectedVersion: 1,
      );
      await client.importContentSource(
        domainId: null,
        filename: 'voice.wav',
        bytes: Uint8List.fromList([1, 2]),
      );
      await client.confirmContentSource(
        domainId: null,
        confirmationId: 'CONF-shared',
        confirmed: true,
      );
      await client.exportContentProject(
        domainId: null,
        assetRefs: ['ART-source'],
        timeline: {'version': 1},
        outputKind: 'audio',
      );
      await client.listContentProjects(domainId: null);
      await client.reopenContentProject(
        domainId: null,
        artifactId: 'ART-contract',
      );
      await client.contentProjectFile(
        domainId: null,
        artifactId: 'ART-contract',
        package: true,
      );
      final requests = server.requests.skip(1).toList();
      expect(requests, hasLength(8));
      for (final request in requests) {
        expect(
          request.workspaceScope,
          '{"scope_kind":"shared_workspace","version":1}',
        );
        expect(request.contextMode, isNull);
        expect(request.domainId, isNull);
        expect(request.subjectId, isNull);
        expect(request.headers['x-product-id'], isNull);
        expect(request.headers['x-brand-focus-id'], isNull);
        expect(request.authorization, isNull);
      }
      // Selecting Shared neither changes the business view nor expands its grant.
      expect(client.currentContextEnvelope!['context']['domain_id'], 'CTH');
      final count = server.requests.length;
      expect(
        () => client.inspectContentMedia(
          domainId: 'SHARED',
          assetRefs: ['ART-source'],
        ),
        throwsFormatException,
      );
      expect(
        () => client.inspectContentMedia(
          domainId: 'BMP',
          assetRefs: ['ART-source'],
        ),
        throwsA(
          isA<LumenisCoreException>().having(
            (error) => error.errorCode,
            'errorCode',
            'CONTENT_CONTEXT_MISMATCH',
          ),
        ),
      );
      expect(server.requests.length, count);
    },
  );

  for (final status in [HttpStatus.unauthorized, HttpStatus.forbidden]) {
    test(
      'independent media HTTP $status is not retried or domain-fallbacked',
      () async {
        final server = await _CoreStub.start(fileStatus: status);
        addTearDown(server.close);
        final client = LumenisCoreClient(baseUrl: server.baseUrl);
        await expectLater(
          client.contentProjectFile(
            domainId: null,
            artifactId: 'ART-contract',
            package: true,
          ),
          throwsA(
            isA<LumenisCoreException>().having(
              (error) => error.statusCode,
              'statusCode',
              status,
            ),
          ),
        );
        expect(server.requests, hasLength(1));
        expect(
          server.requests.single.workspaceScope,
          '{"scope_kind":"shared_workspace","version":1}',
        );
        expect(server.requests.single.domainId, isNull);
        expect(server.requests.single.authorization, isNull);
      },
    );
  }

  test(
    'batch preview uses existing READ inspect scope and exact command envelope',
    () async {
      final server = await _CoreStub.start(
        contextResponses: [_contextEnvelope('GLOBAL_ALL')],
      );
      addTearDown(server.close);
      final client = LumenisCoreClient(baseUrl: server.baseUrl);
      await client.settingsContext();
      final timeline = <String, dynamic>{'version': 4};
      final commands = <Map<String, dynamic>>[
        {
          'op': 'trim',
          'clip_id': 'CLIP-stable',
          'source_in': 0.0,
          'source_out': 3.0,
        },
      ];
      await client.inspectContentEditBatch(
        domainId: 'BMP',
        assetRefs: ['ART-source'],
        timeline: timeline,
        commands: commands,
        expectedVersion: 4,
      );
      final request = server.requests.last;
      expect(request.method, 'POST');
      expect(
        request.path,
        '/api/experience/shared-skills/shared.content_project/inspect',
      );
      expect(request.domainId, 'BMP');
      expect(request.authorization, isNull);
      expect(jsonDecode(request.body!), {
        'action_type': 'READ',
        'input': {
          'asset_refs': ['ART-source'],
          'timeline': timeline,
          'edit_batch': {'commands': commands, 'expected_version': 4},
        },
      });
    },
  );

  test(
    'reads the open workspace without fetching or forwarding Core credentials',
    () async {
      final server = await _CoreStub.start();
      addTearDown(server.close);
      final client = LumenisCoreClient(baseUrl: server.baseUrl);

      await client.runtimeIdentity();
      final catalog = await client.sharedSkillsCatalog();
      final evidence = await client.contentEvidence('CGE-contract %?value');

      expect(catalog['capability'], 'Shared Content & Creation');
      expect(evidence['evidence']['evidence_id'], 'CGE-contract %?value');
      expect(server.requests.map((request) => request.path), [
        '/api/experience/runtime/identity',
        '/api/experience/shared-skills',
        '/api/experience/content/evidence/CGE-contract%20%25%3Fvalue',
      ]);
      expect(
        server.requests.every((request) => request.authorization == null),
        isTrue,
      );
      expect(
        server.requests.any((request) => request.path.startsWith('/v4/auth/')),
        isFalse,
      );
    },
  );

  test('Shared SavedWork calls use only the exact workspace scope', () async {
    final server = await _CoreStub.start(
      contextResponses: [
        _contextEnvelope('FOCUS', domainId: 'CTH', subjectId: 'shop-1'),
      ],
    );
    addTearDown(server.close);
    final client = LumenisCoreClient(baseUrl: server.baseUrl);

    await client.selectContext(domainId: 'CTH', subjectId: 'shop-1');
    final search = await client.listSharedSavedWork();
    expect(search['ok'], isTrue);
    await client.saveSharedReport(
      title: 'User report',
      markdown: 'User-authored text',
      requestId: 'sh04_test_0001',
    );
    await client.reopenSharedSavedWork('ART-0123456789abcdef');
    await client.reviseSharedReport(
      artifactId: 'ART-0123456789abcdef',
      requestId: 'sh04_test_0002',
      expectedSha256: List.filled(64, 'a').join(),
      reason: 'Clarified one paragraph',
      expectedTitle: 'User report',
      title: 'User report revised',
      expectedMarkdown: 'User-authored text',
      markdown: 'Revised user-authored text',
    );
    final exported = await client.exportSharedSavedWork(
      artifactId: 'ART-0123456789abcdef',
      format: 'md',
    );

    expect(utf8.decode(exported.bytes), 'Shared report export');
    expect(exported.mediaType, 'text/markdown');
    expect(exported.filename, 'ART-0123456789abcdef.md');
    final savedRequests = server.requests.where(
      (request) => request.path.startsWith('/api/experience/saved-work'),
    );
    expect(savedRequests, hasLength(5));
    for (final request in savedRequests) {
      expect(
        request.workspaceScope,
        '{"scope_kind":"shared_workspace","version":1}',
      );
      expect(request.authorization, isNull);
      expect(request.headers.keys, isNot(contains('x-lumenis-context-mode')));
      expect(request.headers.keys, isNot(contains('x-domain-id')));
      expect(request.headers.keys, isNot(contains('x-subject-id')));
      expect(request.headers.keys, isNot(contains('x-product-id')));
    }
    final saveBody = jsonDecode(server.requests[2].body!) as Map;
    expect(saveBody['kind'], 'report');
    expect(saveBody['citations'], isEmpty);
    final revisionBody = jsonDecode(server.requests[4].body!) as Map;
    expect(revisionBody['expected_sha256'], List.filled(64, 'a').join());
    expect(revisionBody.containsKey('citations'), isFalse);
    expect(
      (revisionBody['edits'] as List).map((edit) => edit['pointer']).toList(),
      ['/title', '/markdown'],
    );
  });

  test('Shared SavedWork accepts only a guarded PPTX export response', () async {
    final server = await _CoreStub.start();
    addTearDown(server.close);
    final client = LumenisCoreClient(baseUrl: server.baseUrl);

    final file = await client.exportSharedSavedWork(
      artifactId: 'ART-0123456789abcdef',
      format: 'pptx',
    );

    expect(file.filename, 'ART-0123456789abcdef.pptx');
    expect(
      file.mediaType,
      'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    );
    expect(file.bytes, [0x50, 0x4b, 0x03, 0x04]);
    expect(
      server.requests.single.path,
      '/api/experience/saved-work/ART-0123456789abcdef/export?format=pptx',
    );
    expect(
      server.requests.single.workspaceScope,
      '{"scope_kind":"shared_workspace","version":1}',
    );
  });

  test(
    'mismatched context responses preserve the confirmed selection',
    () async {
      final server = await _CoreStub.start(
        contextResponses: [
          _contextEnvelope('FOCUS', domainId: 'CTH', subjectId: 'shop-1'),
          _contextEnvelope('FOCUS', domainId: 'CTH', subjectId: 'other-shop'),
          _contextEnvelope('FOCUS', domainId: 'BMP', subjectId: 'next-shop'),
          _contextEnvelope('GLOBAL_ALL'),
          _contextEnvelope('FOCUS', domainId: 'CTH', subjectId: 'other-shop'),
          _contextEnvelope('GLOBAL_ALL'),
        ],
      );
      addTearDown(server.close);
      final client = LumenisCoreClient(baseUrl: server.baseUrl);

      await client.runtimeIdentity();
      final confirmedFocus = await client.selectContext(
        domainId: 'CTH',
        subjectId: 'shop-1',
      );

      Future<void> expectConfirmedFocusRemains() async {
        expect(client.currentContextEnvelope, same(confirmedFocus));
        expect((await client.sharedSkillsCatalog())['ok'], isTrue);
        final request = server.requests.last;
        expect(request.path, '/api/experience/shared-skills');
        expect(request.contextMode, 'FOCUS');
        expect(request.domainId, 'CTH');
        expect(request.subjectId, 'shop-1');
      }

      await expectLater(
        client.selectContext(domainId: 'CTH', subjectId: 'next-shop'),
        throwsA(isA<FormatException>()),
      );
      await expectConfirmedFocusRemains();

      await expectLater(
        client.selectContext(domainId: 'CTH', subjectId: 'next-shop'),
        throwsA(isA<FormatException>()),
      );
      await expectConfirmedFocusRemains();

      await expectLater(
        client.selectContext(domainId: 'CTH', subjectId: 'next-shop'),
        throwsA(isA<FormatException>()),
      );
      await expectConfirmedFocusRemains();

      await expectLater(client.clearContext(), throwsA(isA<FormatException>()));
      await expectConfirmedFocusRemains();

      final cleared = await client.clearContext();
      expect((cleared['context'] as Map)['mode'], 'GLOBAL_ALL');
      expect(client.currentContextEnvelope, same(cleared));
      expect((await client.sharedSkillsCatalog())['ok'], isTrue);
      final globalRequest = server.requests.last;
      expect(globalRequest.contextMode, 'GLOBAL_ALL');
      expect(globalRequest.domainId, isNull);
      expect(globalRequest.subjectId, isNull);
    },
  );

  test(
    'client cleanup does not request or recreate a Core credential',
    () async {
      final server = await _CoreStub.start();
      addTearDown(server.close);
      final client = LumenisCoreClient(baseUrl: server.baseUrl);

      expect((await client.runtimeIdentity())['ok'], isTrue);
      client.clearCredentials();
      expect((await client.runtimeIdentity())['ok'], isTrue);
      expect(server.requests.map((request) => request.path), [
        '/api/experience/runtime/identity',
        '/api/experience/runtime/identity',
      ]);
      expect(server.requests.last.authorization, isNull);
    },
  );

  for (final status in [HttpStatus.unauthorized, HttpStatus.forbidden]) {
    test(
      'runtime HTTP $status is preserved without credential recovery',
      () async {
        final server = await _CoreStub.start(runtimeStatus: status);
        addTearDown(server.close);
        final client = LumenisCoreClient(baseUrl: server.baseUrl);

        await expectLater(
          client.runtimeIdentity(),
          throwsA(
            isA<LumenisCoreException>().having(
              (error) => error.statusCode,
              'statusCode',
              status,
            ),
          ),
        );
        expect(server.requests.map((request) => request.path), [
          '/api/experience/runtime/identity',
        ]);
        expect(server.requests.single.authorization, isNull);
      },
    );
  }

  test('media file read never inherits a runtime credential', () async {
    final server = await _CoreStub.start();
    addTearDown(server.close);
    final client = LumenisCoreClient(baseUrl: server.baseUrl);

    await client.runtimeIdentity();
    final file = await client.contentProjectFile(
      domainId: 'CTH',
      artifactId: 'ART-contract',
      package: true,
    );

    expect(file.filename, 'ART-contract.zip');
    expect(file.mediaType, 'application/zip');
    expect(file.bytes, [80, 75, 5, 6, ...List<int>.filled(18, 0)]);
    expect(server.requests.map((request) => request.path), [
      '/api/experience/runtime/identity',
      '/api/experience/content-projects/ART-contract/package',
    ]);
    expect(
      server.requests.every((request) => request.authorization == null),
      isTrue,
    );
    expect(server.requests.last.domainId, 'CTH');
  });

  for (final status in [HttpStatus.unauthorized, HttpStatus.forbidden]) {
    test(
      'media HTTP $status remains denied without bootstrap or retry',
      () async {
        final server = await _CoreStub.start(fileStatus: status);
        addTearDown(server.close);
        final client = LumenisCoreClient(baseUrl: server.baseUrl);

        await expectLater(
          client.contentProjectFile(
            domainId: 'CTH',
            artifactId: 'ART-contract',
            package: true,
          ),
          throwsA(
            isA<LumenisCoreException>().having(
              (error) => error.statusCode,
              'statusCode',
              status,
            ),
          ),
        );
        expect(server.requests.map((request) => request.path), [
          '/api/experience/content-projects/ART-contract/package',
        ]);
        expect(server.requests.single.authorization, isNull);
      },
    );
  }

  test(
    'controlled browser transport omits bootstrap credentials and context headers',
    () async {
      final server = await _CoreStub.start();
      addTearDown(server.close);
      final client = LumenisCoreClient(baseUrl: server.baseUrl);

      final session = await client.openBrowserSession();
      final frame = await client.browserFrame('bs_0123456789ab');

      expect(session['session_id'], 'bs_0123456789ab');
      expect(frame.targetId, 'target_approved');
      expect(frame.pageRevision, 1);
      expect(server.requests.map((request) => request.path), [
        '/api/browser/sessions',
        '/api/browser/sessions/bs_0123456789ab/frame',
      ]);
      for (final request in server.requests) {
        expect(request.authorization, isNull);
        expect(request.contextMode, isNull);
        expect(request.domainId, isNull);
        expect(request.subjectId, isNull);
      }
    },
  );

  test(
    'controlled browser refuses a non-loopback Core before issuing a request',
    () async {
      final client = LumenisCoreClient(
        baseUrl: 'https://core.example.invalid:8201',
      );

      expect(
        () => client.openBrowserSession(),
        throwsA(
          isA<LumenisCoreException>().having(
            (error) => error.errorCode,
            'errorCode',
            'BROWSER_LOCAL_CORE_REQUIRED',
          ),
        ),
      );
    },
  );

  test(
    'CTH registry denial stays local and preserves the HTTP status',
    () async {
      final server = await _CoreStub.start(
        subjectStatus: HttpStatus.unauthorized,
      );
      addTearDown(server.close);
      final client = LumenisCoreClient(baseUrl: server.baseUrl);

      await client.runtimeIdentity();
      await expectLater(
        client.settingsSubjects(),
        throwsA(
          isA<LumenisCoreException>().having(
            (error) => error.statusCode,
            'statusCode',
            HttpStatus.unauthorized,
          ),
        ),
      );
      expect((await client.sharedSkillsCatalog())['ok'], isTrue);
      expect(server.requests.last.path, '/api/experience/shared-skills');
      expect(server.requests.last.authorization, isNull);
      expect(
        server.requests.any((request) => request.path.startsWith('/v4/auth/')),
        isFalse,
      );
    },
  );

  test('shared GET helpers preserve backend status on failure', () async {
    final server = await _CoreStub.start(
      catalogStatus: HttpStatus.serviceUnavailable,
    );
    addTearDown(server.close);
    final client = LumenisCoreClient(baseUrl: server.baseUrl);

    await client.runtimeIdentity();
    await expectLater(
      client.sharedSkillsCatalog(),
      throwsA(
        isA<LumenisCoreException>().having(
          (error) => error.statusCode,
          'statusCode',
          HttpStatus.serviceUnavailable,
        ),
      ),
    );
    expect(server.requests.last.authorization, isNull);
  });

  test('Core redirects fail closed without forwarding context', () async {
    final server = await _CoreStub.start(redirectCatalog: true);
    addTearDown(server.close);
    final client = LumenisCoreClient(baseUrl: server.baseUrl);

    await client.runtimeIdentity();
    await expectLater(
      client.sharedSkillsCatalog(),
      throwsA(
        isA<LumenisCoreException>().having(
          (error) => error.statusCode,
          'statusCode',
          HttpStatus.found,
        ),
      ),
    );
    expect(
      server.requests.where(
        (request) => request.path == '/api/experience/shared-skills',
      ),
      hasLength(1),
    );
    expect(
      server.requests.any((request) => request.path == '/redirected'),
      isFalse,
    );
  });

  for (final scheme in ['http', 'https']) {
    test(
      'remote $scheme skips config and never sends Core credentials',
      () async {
        final client = LumenisCoreClient(
          baseUrl: '$scheme://core.example.invalid:8201',
        );

        await expectLater(
          client.runtimeIdentity(),
          throwsA(
            isA<LumenisCoreException>()
                .having(
                  (error) => error.message,
                  'attempted request',
                  contains('GET /api/experience/runtime/identity'),
                )
                .having(
                  (error) => error.message,
                  'config bootstrap',
                  isNot(contains('/api/auth/config')),
                ),
          ),
        );
      },
    );
  }
}

const _browserPng = <int>[
  137,
  80,
  78,
  71,
  13,
  10,
  26,
  10,
  0,
  0,
  0,
  13,
  73,
  72,
  68,
  82,
  0,
  0,
  0,
  1,
  0,
  0,
  0,
  1,
  8,
  6,
  0,
  0,
  0,
  31,
  21,
  196,
  137,
  0,
  0,
  0,
  13,
  73,
  68,
  65,
  84,
  8,
  215,
  99,
  248,
  207,
  192,
  240,
  31,
  0,
  5,
  0,
  1,
  255,
  137,
  153,
  61,
  29,
  0,
  0,
  0,
  0,
  73,
  69,
  78,
  68,
  174,
  66,
  96,
  130,
];

Map<String, dynamic> _contextEnvelope(
  String mode, {
  String? domainId,
  String? subjectId,
}) => {
  'ok': true,
  'contract': 'lumenis.context.v1',
  'selection_only': true,
  'context': {'mode': mode, 'domain_id': ?domainId, 'subject_id': ?subjectId},
};

class _RecordedRequest {
  const _RecordedRequest({
    required this.method,
    required this.path,
    required this.authorization,
    required this.contextMode,
    required this.domainId,
    required this.subjectId,
    required this.workspaceScope,
    required this.headers,
    required this.body,
  });

  final String method;
  final String path;
  final String? authorization;
  final String? contextMode;
  final String? domainId;
  final String? subjectId;
  final String? workspaceScope;
  final Map<String, String> headers;
  final String? body;
}

class _CoreStub {
  _CoreStub._({
    required this.server,
    required this.runtimeStatus,
    required this.fileStatus,
    required this.catalogStatus,
    required this.subjectStatus,
    required this.redirectCatalog,
    required List<Map<String, dynamic>> contextResponses,
  }) {
    _contextResponses = List.of(contextResponses);
    server.listen(_handle);
  }

  final HttpServer server;
  final int runtimeStatus;
  final int fileStatus;
  final int catalogStatus;
  final int subjectStatus;
  final bool redirectCatalog;
  final List<_RecordedRequest> requests = [];
  late final List<Map<String, dynamic>> _contextResponses;

  String get baseUrl => 'http://127.0.0.1:${server.port}';

  static Future<_CoreStub> start({
    int runtimeStatus = HttpStatus.ok,
    int fileStatus = HttpStatus.ok,
    int catalogStatus = HttpStatus.ok,
    int subjectStatus = HttpStatus.ok,
    bool redirectCatalog = false,
    List<Map<String, dynamic>> contextResponses = const [],
  }) async {
    final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    return _CoreStub._(
      server: server,
      runtimeStatus: runtimeStatus,
      fileStatus: fileStatus,
      catalogStatus: catalogStatus,
      subjectStatus: subjectStatus,
      redirectCatalog: redirectCatalog,
      contextResponses: contextResponses,
    );
  }

  Future<void> close() => server.close(force: true);

  Future<void> _handle(HttpRequest request) async {
    final path = request.uri.toString();
    final requestBody = await utf8.decoder.bind(request).join();
    final authorization = request.headers.value(
      HttpHeaders.authorizationHeader,
    );
    requests.add(
      _RecordedRequest(
        method: request.method,
        path: path,
        authorization: authorization,
        contextMode: request.headers.value('X-Lumenis-Context-Mode'),
        domainId: request.headers.value('X-Domain-Id'),
        subjectId: request.headers.value('X-Subject-ID'),
        workspaceScope: request.headers.value('X-Lumenis-Workspace-Scope'),
        headers: _lowercaseHeaders(request.headers),
        body: requestBody.isEmpty ? null : requestBody,
      ),
    );

    if (request.uri.path == '/api/experience/materials/documents' &&
        request.method == 'POST') {
      await _reply(request, HttpStatus.ok, const {
        'ok': true,
        'result': {},
        'publish_status': 'not_performed',
      });
      return;
    }

    if (request.uri.path.startsWith(
          '/api/experience/reports/source-brief/jobs/',
        ) &&
        request.method == 'POST' &&
        request.uri.path.endsWith('/save')) {
      await _reply(request, HttpStatus.ok, const {'ok': true, 'result': {}});
      return;
    }
    if (request.uri.path.startsWith('/api/experience/saved-work')) {
      if (request.uri.path.endsWith('/export')) {
        final isPptx = request.uri.queryParameters['format'] == 'pptx';
        request.response
          ..statusCode = HttpStatus.ok
          ..headers.set(
            HttpHeaders.contentTypeHeader,
            isPptx
                ? 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
                : 'text/markdown; charset=utf-8',
          )
          ..headers.set('X-Source-Artifact-ID', 'ART-0123456789abcdef')
          ..headers.set('X-Content-SHA256', List.filled(64, 'b').join())
          ..add(
            isPptx
                ? [0x50, 0x4b, 0x03, 0x04]
                : utf8.encode('Shared report export'),
          );
        await request.response.close();
        return;
      }
      final item = _savedWorkItem();
      final result =
          request.method == 'GET' &&
              request.uri.path == '/api/experience/saved-work'
          ? {
              'items': [item],
              'unverified_candidates': 0,
              'has_more': false,
              'next_cursor': null,
              'verification_complete': true,
            }
          : item;
      await _reply(request, HttpStatus.ok, {
        'ok': true,
        'result': result,
        'publish_status': 'not_performed',
      });
      return;
    }

    if (path ==
        '/api/experience/shared-skills/shared.content_project/inspect') {
      await _reply(request, HttpStatus.ok, const {'ok': true});
      return;
    }
    if (path == '/api/auth/config') {
      await _reply(request, HttpStatus.ok, {'ok': true, 'auth_enabled': true});
      return;
    }
    // Simulate the server-owned open-workspace boundary, which rejects any
    // client-supplied identity credential. This is contract evidence only.
    final authorized = authorization == null;
    if (path == '/api/experience/content-projects/ART-contract/package') {
      request.response
        ..statusCode = authorized ? fileStatus : HttpStatus.unauthorized
        ..headers.contentType = ContentType('application', 'zip')
        ..add([80, 75, 5, 6, ...List<int>.filled(18, 0)]);
      await request.response.close();
      return;
    }
    // Transport-contract fixture only; backend media semantics are covered by
    // the real isolated Python import/edit/export/reopen regression.
    if (request.uri.path.startsWith('/api/experience/content-projects') ||
        request.uri.path.startsWith('/api/experience/content-sources') ||
        request.uri.path.startsWith(
          '/api/experience/content-source-confirmations',
        )) {
      await _reply(request, HttpStatus.ok, const {'ok': true});
      return;
    }
    if (path == '/api/settings/context') {
      if (!authorized) {
        await _reply(request, HttpStatus.unauthorized, const {'ok': false});
        return;
      }
      await _reply(request, HttpStatus.ok, _contextResponses.removeAt(0));
      return;
    }
    if (path == '/api/experience/runtime/identity') {
      await _reply(
        request,
        authorized ? runtimeStatus : HttpStatus.unauthorized,
        const {'ok': true},
      );
      return;
    }
    if (path == '/api/browser/sessions' && request.method == 'POST') {
      await _reply(request, HttpStatus.ok, const {
        'ok': true,
        'session_id': 'bs_0123456789ab',
        'status': 'running',
        'engine_label': 'Controlled Browser',
        'target_id': 'target_approved',
        'page_revision': 1,
        'current_title': 'Example',
        'current_url': 'https://example.com',
        'allowed_actions': ['navigate', 'reload', 'frame'],
      });
      return;
    }
    if (path == '/api/browser/sessions/bs_0123456789ab/frame' &&
        request.method == 'GET') {
      request.response
        ..statusCode = HttpStatus.ok
        ..headers.contentType = ContentType('image', 'png')
        ..headers.set('X-LUMENIS-Frame-Id', 'frame_approved')
        ..headers.set('X-LUMENIS-Target-Id', 'target_approved')
        ..headers.set('X-LUMENIS-Page-Revision', '1')
        ..headers.set('X-LUMENIS-Captured-At', '2026-10-05T10:00:00Z')
        ..headers.set('X-LUMENIS-Frame-Width', '1')
        ..headers.set('X-LUMENIS-Viewport-Width', '1280')
        ..headers.set('X-LUMENIS-Viewport-Height', '720')
        ..headers.set('X-LUMENIS-Viewport-DPR', '1')
        ..headers.set('X-LUMENIS-Frame-Height', '1')
        ..add(_browserPng);
      await request.response.close();
      return;
    }
    if (path == '/api/settings/subjects?domain_id=CTH') {
      await _reply(
        request,
        authorized ? subjectStatus : HttpStatus.unauthorized,
        const {
          'ok': true,
          'source': 'lumenis_subject_registry',
          'selection_only': true,
          'domains': [
            {'id': 'CTH', 'product': 'CTH'},
          ],
          'subjects': [],
        },
      );
      return;
    }
    if (path == '/api/experience/shared-skills') {
      if (redirectCatalog) {
        request.response.statusCode = HttpStatus.found;
        request.response.headers.set(HttpHeaders.locationHeader, '/redirected');
        await request.response.close();
        return;
      }
      await _reply(
        request,
        authorized ? catalogStatus : HttpStatus.unauthorized,
        const {
          'ok': true,
          'product': 'LUMENIS',
          'capability': 'Shared Content & Creation',
          'consumers': ['CTH', 'BMP'],
          'skills': [],
        },
      );
      return;
    }
    if (path == '/redirected') {
      await _reply(request, HttpStatus.ok, const {'ok': true});
      return;
    }
    if (path.startsWith('/api/experience/content/evidence/')) {
      await _reply(request, HttpStatus.ok, const {
        'ok': true,
        'evidence': {'evidence_id': 'CGE-contract %?value'},
      });
      return;
    }
    await _reply(request, HttpStatus.notFound, const {'ok': false});
  }

  Future<void> _reply(
    HttpRequest request,
    int status,
    Map<String, dynamic> body,
  ) async {
    request.response.statusCode = status;
    request.response.headers.contentType = ContentType.json;
    request.response.write(jsonEncode(body));
    await request.response.close();
  }
}

Map<String, String> _lowercaseHeaders(HttpHeaders headers) {
  final result = <String, String>{};
  headers.forEach((name, values) {
    result[name.toLowerCase()] = values.join(', ');
  });
  return result;
}

Map<String, dynamic> _savedWorkItem() => {
  'artifact': {
    'artifact_id': 'ART-0123456789abcdef',
    'sha256': List.filled(64, 'a').join(),
    'created_at': '2026-10-16T10:30:00Z',
  },
  'document': {
    'schema': 'lumenis.saved-work/v1',
    'context': {'scope_kind': 'shared_workspace', 'version': 1, 'actor_id': 42},
    'work_id': 'WORK-0123456789abcdef01234567',
    'version': 1,
    'parent_artifact_id': null,
    'parent_sha256': null,
    'contract': {
      'id': 'lumenis.saved-work',
      'version': '1',
      'required_payload_paths': <String>[],
    },
    'kind': 'report',
    'title': 'User report',
    'markdown': 'User-authored text',
    'citations': [
      {
        'evidence_id': 77,
        'start': 0,
        'end': 6,
        'quote': 'Source',
        'source_scope': {
          'domain_id': 'cth',
          'subject_id': 'shop-1',
          'brand_focus_id': null,
          'global_scope': false,
        },
      },
    ],
  },
  'return_ref': {
    'artifact_id': 'ART-0123456789abcdef',
    'work_id': 'WORK-0123456789abcdef01234567',
    'version': 1,
    'scope': {'scope_kind': 'shared_workspace', 'version': 1},
  },
};
