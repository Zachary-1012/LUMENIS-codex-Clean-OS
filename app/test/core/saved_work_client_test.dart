import 'dart:convert';
import 'dart:io';

import 'package:crypto/crypto.dart' as crypto;
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';

const _artifactId = 'ART-2222222222222222';
const _otherArtifactId = 'ART-3333333333333333';

const _authoredManuscriptV4 = {
  'id': 'lumenis.internal-pitch',
  'version': '4',
  'required_payload_paths': ['manuscript', 'truth_state'],
};

Map<String, dynamic> _savedManuscriptItem(Map<String, Object?> contract) => {
  'artifact': {'artifact_id': _artifactId},
  'document': {
    'contract': contract,
    'payload': {
      'manuscript': {'title': '独立文稿'},
    },
  },
};

void main() {
  test(
    'Shared SavedWork list, reopen and export use only the typed workspace header',
    () async {
      final response = jsonEncode({
        'ok': true,
        'result': {
          'items': [_savedManuscriptItem(_authoredManuscriptV4)],
          'unverified_candidates': 0,
          'has_more': false,
          'next_cursor': null,
          'verification_complete': true,
        },
      });
      final server = await _SavedWorkStub.start(
        listResponseBody: response,
        reopenResponseBody: jsonEncode({
          'ok': true,
          'result': _savedManuscriptItem(_authoredManuscriptV4),
        }),
      );
      addTearDown(server.close);
      final client = LumenisCoreClient(baseUrl: server.baseUrl);
      const scope = SharedWorkspaceScope();

      await client.listSharedSavedWorks(
        scope: scope,
        query: '独立提案',
        limit: 20,
        cursor: 'shared-next',
        kind: 'report',
      );
      final manuscripts = await client.listSharedAuthoredManuscripts(
        scope: scope,
        limit: 10,
      );
      expect(manuscripts['items'], hasLength(1));
      await client.reopenSharedSavedManuscript(
        scope: scope,
        artifactId: _artifactId,
      );
      final exported = await client.exportSharedSavedWork(
        scope: scope,
        artifactId: _artifactId,
        format: 'md',
      );

      expect(exported.mediaType, 'text/markdown');
      expect(server.requests.map((request) => request.path), [
        '/api/experience/saved-work',
        '/api/experience/saved-work',
        '/api/experience/saved-work/$_artifactId',
        '/api/experience/saved-work/$_artifactId/export',
      ]);
      expect(server.requests.first.query, {
        'query': '独立提案',
        'limit': '20',
        'cursor': 'shared-next',
        'kind': 'report',
      });
      expect(server.requests[1].query, {
        'query': '',
        'limit': '10',
        'kind': 'report',
      });
      expect(server.requests.last.query, {'format': 'md'});
      for (final request in server.requests) {
        expect(
          request.headers['x-lumenis-workspace-scope'],
          '{"scope_kind":"shared_workspace","version":1}',
        );
        expect(request.headers['x-lumenis-context-mode'], isNull);
        expect(request.headers['x-domain-id'], isNull);
        expect(request.headers['x-subject-id'], isNull);
        expect(request.headers['x-brand-focus-id'], isNull);
        expect(request.headers['x-product-id'], isNull);
        expect(request.headers['cookie'], isNull);
      }
    },
  );

  test('GLOBAL_ALL reads carry one explicit domain per request', () async {
    final server = await _SavedWorkStub.start();
    addTearDown(server.close);
    final client = LumenisCoreClient(baseUrl: server.baseUrl);

    // This is the set of domains the caller may ask the existing owner to
    // read; each request still names exactly one scope for Core to authorize.
    expect(client.savedWorkDomains, ['CTH', 'BMP']);
    for (final domainId in client.savedWorkDomains) {
      await client.listSavedWorks(domainId: domainId);
    }

    expect(server.requests, hasLength(2));
    for (var index = 0; index < server.requests.length; index++) {
      final request = server.requests[index];
      final domain = index == 0 ? 'CTH' : 'BMP';
      expect(request.method, 'GET');
      expect(request.path, '/api/experience/saved-work');
      expect(request.query, {'query': '', 'limit': '30'});
      expect(request.headers['x-lumenis-context-mode'], 'GLOBAL_ALL');
      expect(request.headers['x-domain-id'], domain);
      expect(request.headers['x-product-id'], domain == 'BMP' ? 'ZBMP' : 'CTH');
      expect(request.headers['cache-control'], 'no-store');
      _expectNoCredentials(request);
    }
  });

  test(
    'FOCUS lists only the selected domain and rejects cross-domain reads',
    () async {
      final server = await _SavedWorkStub.start();
      addTearDown(server.close);
      final client = LumenisCoreClient(baseUrl: server.baseUrl);
      await client.selectContext(domainId: 'CTH', subjectId: 'subject-7');

      expect(client.savedWorkDomains, ['CTH']);
      await client.listSavedWorks(domainId: 'CTH');
      await expectLater(
        client.listSavedWorks(domainId: 'BMP'),
        throwsA(
          isA<LumenisCoreException>().having(
            (error) => error.errorCode,
            'errorCode',
            'CONTENT_CONTEXT_MISMATCH',
          ),
        ),
      );

      final reads = server.requests
          .where((request) => request.path == '/api/experience/saved-work')
          .toList();
      expect(reads, hasLength(1));
      expect(reads.single.headers['x-lumenis-context-mode'], 'FOCUS');
      expect(reads.single.headers['x-domain-id'], 'CTH');
      expect(reads.single.headers['x-subject-id'], 'subject-7');
      expect(reads.single.headers['x-product-id'], 'CTH');
      _expectNoCredentials(reads.single);
    },
  );

  test(
    'search validates bounds locally and preserves Unicode query/cursor',
    () async {
      final server = await _SavedWorkStub.start();
      addTearDown(server.close);
      final client = LumenisCoreClient(baseUrl: server.baseUrl);

      await expectLater(
        client.listSavedWorks(domainId: 'CTH', query: '😀' * 201),
        throwsFormatException,
      );
      await expectLater(
        client.listSavedWorks(domainId: 'CTH', limit: 0),
        throwsFormatException,
      );
      await expectLater(
        client.listSavedWorks(domainId: 'CTH', limit: 101),
        throwsFormatException,
      );
      await expectLater(
        client.listSavedWorks(domainId: 'CTH', cursor: ''),
        throwsFormatException,
      );
      await expectLater(
        client.listSavedWorks(domainId: 'CTH', cursor: 'bad\nnext'),
        throwsFormatException,
      );
      await expectLater(
        client.listSavedWorks(domainId: 'CTH', cursor: 'x' * 4097),
        throwsFormatException,
      );
      expect(server.requests, isEmpty);

      final query = '品牌与市场 ' * 20;
      const cursor = 'page+2/opaque=';
      final result = await client.listSavedWorks(
        domainId: 'CTH',
        query: query,
        limit: 100,
        cursor: cursor,
      );
      expect(result['items'], isA<List>());
      expect(server.requests, hasLength(1));
      expect(server.requests.single.query, {
        'query': query,
        'limit': '100',
        'cursor': cursor,
      });
    },
  );

  test(
    'reopen validates artifact identity and returns the SavedWork result',
    () async {
      final server = await _SavedWorkStub.start();
      addTearDown(server.close);
      final client = LumenisCoreClient(baseUrl: server.baseUrl);

      await expectLater(
        client.reopenSavedWork(domainId: 'CTH', artifactId: '../$_artifactId'),
        throwsFormatException,
      );
      expect(server.requests, isEmpty);

      final result = await client.reopenSavedWork(
        domainId: 'BMP',
        artifactId: _artifactId,
      );
      expect(result['artifact'], {'artifact_id': _artifactId});
      expect(server.requests, hasLength(1));
      final request = server.requests.single;
      expect(request.path, '/api/experience/saved-work/$_artifactId');
      expect(request.headers['x-lumenis-context-mode'], 'GLOBAL_ALL');
      expect(request.headers['x-domain-id'], 'BMP');
      expect(request.headers['x-product-id'], 'ZBMP');
      _expectNoCredentials(request);
    },
  );

  test(
    'export accepts each supported format and returns validated UTF-8 files',
    () async {
      final cases = <String, _ExportCase>{
        'json': _ExportCase(
          mediaType: 'application/json',
          bytes: utf8.encode(
            jsonEncode({'schema': 'lumenis.saved-work/v1', 'title': '成果'}),
          ),
        ),
        'md': _ExportCase(
          mediaType: 'text/markdown',
          bytes: utf8.encode('# 成果\n正文已保存 ✅'),
        ),
        'txt': _ExportCase(
          mediaType: 'text/plain',
          bytes: utf8.encode('保存的成果内容'),
        ),
        'pdf': _ExportCase(
          mediaType: 'application/pdf',
          bytes: ascii.encode('%PDF-1.7\n'),
        ),
        'docx': _ExportCase(
          mediaType:
              'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
          bytes: [0x50, 0x4b, 0x03, 0x04, 0x10, 0x20],
        ),
        'xlsx': _ExportCase(
          mediaType:
              'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
          bytes: [0x50, 0x4b, 0x03, 0x04, 0x30, 0x40],
        ),
      };

      for (final entry in cases.entries) {
        final server = await _SavedWorkStub.start(
          exportMediaType: entry.value.mediaType,
          exportBytes: entry.value.bytes,
        );
        addTearDown(server.close);
        final client = LumenisCoreClient(baseUrl: server.baseUrl);

        final file = await client.exportSavedWork(
          domainId: 'BMP',
          artifactId: _artifactId,
          format: entry.key,
        );
        expect(file.filename, '$_artifactId.${entry.key}');
        expect(file.mediaType, entry.value.mediaType);
        expect(file.bytes, entry.value.bytes);

        final request = server.requests.single;
        expect(request.path, '/api/experience/saved-work/$_artifactId/export');
        expect(request.query, {'format': entry.key});
        expect(request.headers['accept'], entry.value.mediaType);
        expect(request.headers['cache-control'], 'no-store');
        expect(request.headers['x-lumenis-context-mode'], 'GLOBAL_ALL');
        expect(request.headers['x-domain-id'], 'BMP');
        expect(request.headers['x-product-id'], 'ZBMP');
        _expectNoCredentials(request);
      }
    },
  );

  test('export rejects unsupported format and non-200 response', () async {
    final unsupportedServer = await _SavedWorkStub.start();
    addTearDown(unsupportedServer.close);
    final unsupportedClient = LumenisCoreClient(
      baseUrl: unsupportedServer.baseUrl,
    );
    await expectLater(
      unsupportedClient.exportSavedWork(
        domainId: 'CTH',
        artifactId: _artifactId,
        format: 'html',
      ),
      throwsFormatException,
    );
    expect(unsupportedServer.requests, isEmpty);

    final failureServer = await _SavedWorkStub.start(
      exportStatus: HttpStatus.serviceUnavailable,
    );
    addTearDown(failureServer.close);
    final failureClient = LumenisCoreClient(baseUrl: failureServer.baseUrl);
    await expectLater(
      failureClient.exportSavedWork(
        domainId: 'CTH',
        artifactId: _artifactId,
        format: 'md',
      ),
      throwsA(
        isA<LumenisCoreException>().having(
          (error) => error.statusCode,
          'statusCode',
          HttpStatus.serviceUnavailable,
        ),
      ),
    );
  });

  test(
    'export rejects wrong MIME, artifact identity, digest, and JSON body',
    () async {
      final cases = <_RejectedExportCase>[
        _RejectedExportCase(
          name: 'wrong MIME',
          mediaType: 'application/json',
          bytes: utf8.encode('# Markdown'),
          format: 'md',
        ),
        _RejectedExportCase(
          name: 'wrong artifact identity',
          mediaType: 'text/markdown',
          bytes: utf8.encode('# Markdown'),
          format: 'md',
          artifactHeader: _otherArtifactId,
        ),
        _RejectedExportCase(
          name: 'missing digest',
          mediaType: 'text/markdown',
          bytes: utf8.encode('# Markdown'),
          format: 'md',
          omitDigestHeader: true,
        ),
        _RejectedExportCase(
          name: 'wrong digest',
          mediaType: 'text/markdown',
          bytes: utf8.encode('# Markdown'),
          format: 'md',
          wrongDigest: true,
        ),
        _RejectedExportCase(
          name: 'invalid saved-work JSON',
          mediaType: 'application/json',
          bytes: utf8.encode('{invalid json'),
          format: 'json',
        ),
      ];

      for (final scenario in cases) {
        final server = await _SavedWorkStub.start(
          exportMediaType: scenario.mediaType,
          exportBytes: scenario.bytes,
          exportArtifactHeader: scenario.artifactHeader ?? _artifactId,
          omitDigestHeader: scenario.omitDigestHeader,
          exportDigestHeader: scenario.wrongDigest
              ? _differentDigest(scenario.bytes)
              : null,
        );
        addTearDown(server.close);
        final client = LumenisCoreClient(baseUrl: server.baseUrl);

        await expectLater(
          client.exportSavedWork(
            domainId: 'CTH',
            artifactId: _artifactId,
            format: scenario.format,
          ),
          throwsFormatException,
          reason: scenario.name,
        );
        expect(server.requests, hasLength(1), reason: scenario.name);
      }
    },
  );

  test(
    'binary export redirects fail closed without following Location',
    () async {
      final server = await _SavedWorkStub.start(redirectExport: true);
      addTearDown(server.close);
      final client = LumenisCoreClient(baseUrl: server.baseUrl);

      await expectLater(
        client.exportSavedWork(
          domainId: 'CTH',
          artifactId: _artifactId,
          format: 'md',
        ),
        throwsA(
          isA<LumenisCoreException>().having(
            (error) => error.errorCode,
            'errorCode',
            'WORK_EXPORT_UNAVAILABLE',
          ),
        ),
      );
      expect(server.requests.map((request) => request.path), [
        '/api/experience/saved-work/$_artifactId/export',
      ]);
      _expectNoCredentials(server.requests.single);
    },
  );

  test(
    'malformed JSON and invalid SavedWork envelopes cannot return success',
    () async {
      final listServer = await _SavedWorkStub.start(
        listResponseBody: '{not json',
      );
      addTearDown(listServer.close);
      final listClient = LumenisCoreClient(baseUrl: listServer.baseUrl);
      await expectLater(
        listClient.listSavedWorks(domainId: 'CTH'),
        throwsFormatException,
      );

      final reopenServer = await _SavedWorkStub.start(
        reopenResponseBody: jsonEncode({'ok': true, 'result': []}),
      );
      addTearDown(reopenServer.close);
      final reopenClient = LumenisCoreClient(baseUrl: reopenServer.baseUrl);
      await expectLater(
        reopenClient.reopenSavedWork(domainId: 'CTH', artifactId: _artifactId),
        throwsFormatException,
      );
    },
  );
}

String _differentDigest(List<int> bytes) {
  final digest = crypto.sha256.convert(bytes).toString();
  final replacement = digest[0] == '0' ? '1' : '0';
  return '$replacement${digest.substring(1)}';
}

void _expectNoCredentials(_CapturedRequest request) {
  expect(request.headers['authorization'], isNull);
  expect(request.headers['cookie'], isNull);
}

class _ExportCase {
  const _ExportCase({required this.mediaType, required this.bytes});

  final String mediaType;
  final List<int> bytes;
}

class _RejectedExportCase {
  const _RejectedExportCase({
    required this.name,
    required this.mediaType,
    required this.bytes,
    required this.format,
    this.artifactHeader,
    this.omitDigestHeader = false,
    this.wrongDigest = false,
  });

  final String name;
  final String mediaType;
  final List<int> bytes;
  final String format;
  final String? artifactHeader;
  final bool omitDigestHeader;
  final bool wrongDigest;
}

class _CapturedRequest {
  const _CapturedRequest({
    required this.method,
    required this.path,
    required this.query,
    required this.headers,
    required this.body,
  });

  final String method;
  final String path;
  final Map<String, String> query;
  final Map<String, String> headers;
  final Map<String, dynamic>? body;
}

class _SavedWorkStub {
  _SavedWorkStub._({
    required this.server,
    required this.listStatus,
    required this.listResponseBody,
    required this.reopenStatus,
    required this.reopenResponseBody,
    required this.exportStatus,
    required this.exportMediaType,
    required this.exportBytes,
    required this.exportArtifactHeader,
    required this.omitDigestHeader,
    required this.exportDigestHeader,
    required this.redirectExport,
  }) {
    server.listen(_handle);
  }

  final HttpServer server;
  final int listStatus;
  final String? listResponseBody;
  final int reopenStatus;
  final String? reopenResponseBody;
  final int exportStatus;
  final String exportMediaType;
  final List<int> exportBytes;
  final String? exportArtifactHeader;
  final bool omitDigestHeader;
  final String? exportDigestHeader;
  final bool redirectExport;
  final List<_CapturedRequest> requests = [];

  String get baseUrl => 'http://127.0.0.1:${server.port}';

  static Future<_SavedWorkStub> start({
    int listStatus = HttpStatus.ok,
    String? listResponseBody,
    int reopenStatus = HttpStatus.ok,
    String? reopenResponseBody,
    int exportStatus = HttpStatus.ok,
    String exportMediaType = 'text/markdown',
    List<int> exportBytes = const [0x23, 0x20, 0x53, 0x61, 0x76, 0x65, 0x64],
    String? exportArtifactHeader = _artifactId,
    bool omitDigestHeader = false,
    String? exportDigestHeader,
    bool redirectExport = false,
  }) async => _SavedWorkStub._(
    server: await HttpServer.bind(InternetAddress.loopbackIPv4, 0),
    listStatus: listStatus,
    listResponseBody: listResponseBody,
    reopenStatus: reopenStatus,
    reopenResponseBody: reopenResponseBody,
    exportStatus: exportStatus,
    exportMediaType: exportMediaType,
    exportBytes: exportBytes,
    exportArtifactHeader: exportArtifactHeader,
    omitDigestHeader: omitDigestHeader,
    exportDigestHeader: exportDigestHeader,
    redirectExport: redirectExport,
  );

  Future<void> close() => server.close(force: true);

  Future<void> _handle(HttpRequest request) async {
    final rawBody = await request.fold<List<int>>(
      <int>[],
      (bytes, chunk) => bytes..addAll(chunk),
    );
    final headers = <String, String>{};
    request.headers.forEach((name, values) {
      headers[name.toLowerCase()] = values.join(', ');
    });
    final decoded = rawBody.isEmpty ? null : jsonDecode(utf8.decode(rawBody));
    requests.add(
      _CapturedRequest(
        method: request.method,
        path: request.uri.path,
        query: Map.unmodifiable(request.uri.queryParameters),
        headers: Map.unmodifiable(headers),
        body: decoded is Map<String, dynamic> ? decoded : null,
      ),
    );

    if (request.uri.path == '/api/settings/context' &&
        request.method == 'PUT') {
      await _replyJson(request, HttpStatus.ok, {
        'ok': true,
        'contract': 'lumenis.context.v1',
        'selection_only': true,
        'context': {
          'mode': 'FOCUS',
          'domain_id': 'CTH',
          'subject_id': 'subject-7',
        },
      });
      return;
    }

    if (request.uri.path == '/api/experience/saved-work' &&
        request.method == 'GET') {
      await _replyJson(
        request,
        listStatus,
        listResponseBody ??
            jsonEncode(
              listStatus == HttpStatus.ok
                  ? {
                      'ok': true,
                      'result': {
                        'items': [
                          {
                            'artifact': {'artifact_id': _artifactId},
                          },
                        ],
                        'has_more': false,
                        'next_cursor': null,
                      },
                    }
                  : {'ok': false, 'code': 'SAVED_WORK_UNAVAILABLE'},
            ),
      );
      return;
    }

    if (request.uri.path == '/api/experience/saved-work/$_artifactId' &&
        request.method == 'GET') {
      await _replyJson(
        request,
        reopenStatus,
        reopenResponseBody ??
            jsonEncode(
              reopenStatus == HttpStatus.ok
                  ? {
                      'ok': true,
                      'result': {
                        'artifact': {'artifact_id': _artifactId},
                        'document': {'title': 'Saved document'},
                      },
                    }
                  : {'ok': false, 'code': 'SAVED_WORK_UNAVAILABLE'},
            ),
      );
      return;
    }

    if (request.uri.path == '/api/experience/saved-work/$_artifactId/export' &&
        request.method == 'GET') {
      if (redirectExport) {
        request.response
          ..statusCode = HttpStatus.found
          ..headers.set(HttpHeaders.locationHeader, '/redirect-target');
        await request.response.close();
        return;
      }
      if (exportStatus != HttpStatus.ok) {
        await _replyJson(request, exportStatus, {
          'ok': false,
          'code': 'SAVED_WORK_EXPORT_UNAVAILABLE',
        });
        return;
      }
      final response = request.response
        ..statusCode = HttpStatus.ok
        ..headers.contentType = ContentType.parse(exportMediaType);
      if (exportArtifactHeader != null) {
        response.headers.set('X-Source-Artifact-Id', exportArtifactHeader!);
      }
      if (!omitDigestHeader) {
        response.headers.set(
          'X-Content-SHA256',
          exportDigestHeader ?? crypto.sha256.convert(exportBytes).toString(),
        );
      }
      response.add(exportBytes);
      await response.close();
      return;
    }

    await _replyJson(request, HttpStatus.notFound, {'ok': false});
  }

  Future<void> _replyJson(HttpRequest request, int status, Object body) async {
    request.response
      ..statusCode = status
      ..headers.contentType = ContentType.json
      ..write(body is String ? body : jsonEncode(body));
    await request.response.close();
  }
}
