import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/features/shared/sh04/sh04_repository.dart';
import 'package:lumenis_app/features/shared/sh04/sh04_snapshot.dart';
import 'package:lumenis_app/features/shared/sh04/sh04_view_model.dart';

void main() {
  late _SavedWorkClient client;
  late CoreSh04Repository repository;

  setUp(() {
    client = _SavedWorkClient();
    repository = CoreSh04Repository(client: client);
  });

  test(
    'GLOBAL lists each domain and preserves partial nonempty results',
    () async {
      client.useGlobalContext();
      client.listResults['CTH'] = LumenisCoreException(
        'HTTP 403 SavedWork read denied',
        statusCode: 403,
      );
      client.listResults['BMP'] = _page(
        [_record(domain: 'BMP', kind: 'research')],
        hasMore: true,
        cursor: 'opaque:bmp/next?x=1',
      );

      final snapshot = await repository.loadExports();

      expect(client.listCalls.map((call) => call.domain), ['CTH', 'BMP']);
      expect(snapshot.exports, hasLength(1));
      expect(snapshot.exports.single.savedWork?.kind, 'research');
      expect(snapshot.exports.single.preview, isEmpty);
      expect(snapshot.failedDomains, ['CTH']);
      expect(snapshot.incomplete, isTrue);
      expect(snapshot.hasMore, isTrue);
      expect(snapshot.cursors['BMP'], 'opaque:bmp/next?x=1');
    },
  );

  test(
    'FOCUS enforces the selected subject on document and return scope',
    () async {
      client.useFocusContext(domain: 'CTH', focusId: 'subject-one');
      client.listResults['CTH'] = _page([
        _record(domain: 'CTH', focusId: 'subject-one'),
        _record(
          domain: 'CTH',
          focusId: 'subject-two',
          artifactSuffix: '0000000000000002',
        ),
      ]);

      final snapshot = await repository.loadExports();

      expect(snapshot.exports, hasLength(2));
      expect(snapshot.exports.first.savedWork, isNotNull);
      expect(
        snapshot.exports.first.savedWork!.returnScope['subject_id'],
        'subject-one',
      );
      expect(snapshot.exports.last.savedWork, isNull);
      expect(snapshot.exports.last.state, Sh04ExportState.unavailable);
      expect(snapshot.exports.last.preview, isEmpty);
      expect(snapshot.incomplete, isTrue);
      expect(client.listCalls.single.domain, 'CTH');
    },
  );

  test(
    'list visibility is not a commit; exact reopen receipt unlocks detail',
    () async {
      final row = _record(domain: 'CTH', focusId: 'subject-one');
      client.listResults['CTH'] = _page([row]);
      final listed = (await repository.loadExports()).exports.single;
      expect(listed.savedWork!.committed, isFalse);
      expect(listed.savedWork!.sources, isEmpty);
      expect(listed.preview, isEmpty);
      client.reopenResults['ART-0000000000000001'] = _withReceipt(row);

      final opened = await repository.reopen(listed);

      expect(opened.savedWork!.committed, isTrue);
      expect(opened.preview, 'Grounded working notes');
      expect(opened.savedWork!.sources, isEmpty);
      expect(opened.savedWork!.artifactId, listed.internalId);
      expect(opened.savedWork!.hash, listed.savedWork!.hash);
      expect(client.reopenCalls.single.artifactId, listed.internalId);
    },
  );

  test(
    'mismatched receipt never promotes a list row to committed detail',
    () async {
      final row = _record(domain: 'CTH', focusId: 'subject-one');
      client.listResults['CTH'] = _page([row]);
      final listed = (await repository.loadExports()).exports.single;
      final invalid = _withReceipt(row);
      (invalid['receipt'] as Map<String, dynamic>)['sha256'] = 'f' * 64;
      client.reopenResults[listed.internalId] = invalid;

      await expectLater(repository.reopen(listed), throwsFormatException);
      expect(listed.savedWork!.committed, isFalse);
      expect(listed.preview, isEmpty);
    },
  );

  test(
    'view model keeps list visible after reopen failure and retries read',
    () async {
      final row = _record(domain: 'CTH', focusId: 'subject-one');
      client.listResults['CTH'] = _page([row]);
      client.reopenQueues['ART-0000000000000001'] = [
        LumenisCoreException('Source validation denied', statusCode: 403),
        _withReceipt(row),
      ];
      final viewModel = Sh04ViewModel(repository: repository);
      addTearDown(viewModel.dispose);

      await viewModel.refresh();
      final item = viewModel.exports.single;
      await viewModel.open(item);

      expect(viewModel.actionFailure, Sh04FailureKind.permissionDenied);
      expect(viewModel.opened, isNull);
      expect(viewModel.exports.single.internalId, item.internalId);
      expect(viewModel.exports.single.preview, isEmpty);

      await viewModel.retrySelected();

      expect(viewModel.actionFailure, isNull);
      expect(viewModel.opened?.savedWork?.committed, isTrue);
      expect(viewModel.opened?.preview, 'Grounded working notes');
    },
  );

  test(
    'parent comparison fresh reads version minus one and keeps current open',
    () async {
      client.useFocusContext(domain: 'BMP', focusId: 'brand-one');
      final parent = _record(
        domain: 'BMP',
        focusId: 'brand-one',
        artifactSuffix: '0000000000000001',
        workSuffix: '000000000000000000000001',
      );
      final child = _record(
        domain: 'BMP',
        focusId: 'brand-one',
        artifactSuffix: '0000000000000002',
        workSuffix: '000000000000000000000001',
        version: 2,
        parentArtifactId: 'ART-0000000000000001',
        parentSha256: 'a' * 64,
      );
      client.listResults['BMP'] = _page([child]);
      client.reopenResults[child['artifact']['artifact_id'] as String] =
          _withReceipt(child);
      client.reopenResults[parent['artifact']['artifact_id'] as String] =
          _withReceipt(parent);
      final viewModel = Sh04ViewModel(repository: repository);
      addTearDown(viewModel.dispose);

      await viewModel.refresh();
      final item = viewModel.exports.single;
      await viewModel.open(item);
      final current = viewModel.opened;
      await viewModel.compareParent();

      expect(viewModel.opened, same(current));
      expect(viewModel.comparedParent?.savedWork?.version, 1);
      expect(viewModel.comparedParent?.savedWork?.hash, 'a' * 64);
      expect(client.reopenCalls.map((call) => call.artifactId), [
        'ART-0000000000000002',
        'ART-0000000000000001',
      ]);
      expect(client.reopenCalls.last.domain, 'BMP');
    },
  );

  test('back to list fences a late reopen response', () async {
    final row = _record(domain: 'CTH', focusId: 'subject-one');
    client.listResults['CTH'] = _page([row]);
    client.reopenResults['ART-0000000000000001'] = _withReceipt(row);
    client.reopenStarted = Completer<void>();
    client.reopenGate = Completer<void>();
    final viewModel = Sh04ViewModel(repository: repository);
    addTearDown(viewModel.dispose);

    await viewModel.refresh();
    final opening = viewModel.open(viewModel.exports.single);
    await client.reopenStarted!.future;
    viewModel.backToList();
    client.reopenGate!.complete();
    await opening;

    expect(viewModel.opened, isNull);
    expect(viewModel.opening, isFalse);
    expect(viewModel.exports, hasLength(1));
  });

  test(
    'load more carries each domain opaque cursor and merges results',
    () async {
      client.useGlobalContext();
      client.listResults['CTH'] = _page(
        [_record(domain: 'CTH')],
        hasMore: true,
        cursor: 'cth:cursor/opaque',
      );
      client.listResults['BMP'] = _page([_record(domain: 'BMP')]);
      final viewModel = Sh04ViewModel(repository: repository);
      addTearDown(viewModel.dispose);

      await viewModel.refresh();
      client.nextListResults['CTH'] = _page([
        _record(domain: 'CTH', artifactSuffix: '0000000000000003'),
      ]);
      await viewModel.loadMore();

      expect(client.listCalls.last.cursor, 'cth:cursor/opaque');
      expect(viewModel.exports, hasLength(3));
      expect(viewModel.hasMore, isFalse);
    },
  );
}

class _SavedWorkClient extends LumenisCoreClient {
  _SavedWorkClient() : super(baseUrl: 'http://127.0.0.1:1');

  Map<String, dynamic> _envelope = _focusEnvelope('CTH', 'subject-one');
  List<String> _domains = ['CTH'];
  final Map<String, Object> listResults = {};
  final Map<String, Object> nextListResults = {};
  final Map<String, Object> reopenResults = {};
  final Map<String, List<Object>> reopenQueues = {};
  final List<({String domain, String query, String? cursor})> listCalls = [];
  final List<({String domain, String artifactId})> reopenCalls = [];
  Completer<void>? reopenStarted;
  Completer<void>? reopenGate;

  @override
  Map<String, dynamic>? get currentContextEnvelope => _envelope;

  @override
  List<String> get savedWorkDomains => List<String>.unmodifiable(_domains);

  void useGlobalContext() {
    _envelope = const {
      'ok': true,
      'contract': 'lumenis.context.v1',
      'selection_only': true,
      'context': {'mode': 'GLOBAL_ALL', 'subject_id': null},
    };
    _domains = ['CTH', 'BMP'];
  }

  void useFocusContext({required String domain, required String focusId}) {
    _envelope = _focusEnvelope(domain, focusId);
    _domains = [domain];
  }

  @override
  Future<Map<String, dynamic>> listSavedWorks({
    required String domainId,
    String query = '',
    int limit = 30,
    String? cursor,
  }) async {
    listCalls.add((domain: domainId, query: query, cursor: cursor));
    final result = cursor == null
        ? listResults[domainId]
        : nextListResults[domainId];
    if (result == null) return _page(const []);
    if (result is LumenisCoreException) throw result;
    if (result is Exception) throw result;
    return Map<String, dynamic>.from(result as Map);
  }

  @override
  Future<Map<String, dynamic>> reopenSavedWork({
    required String domainId,
    required String artifactId,
  }) async {
    reopenCalls.add((domain: domainId, artifactId: artifactId));
    final started = reopenStarted;
    if (started != null && !started.isCompleted) started.complete();
    await reopenGate?.future;
    final queue = reopenQueues[artifactId];
    final result = queue != null && queue.isNotEmpty
        ? queue.removeAt(0)
        : reopenResults[artifactId];
    if (result == null) throw StateError('Missing reopen response.');
    if (result is LumenisCoreException) throw result;
    if (result is Exception) throw result;
    return Map<String, dynamic>.from(result as Map);
  }
}

Map<String, dynamic> _focusEnvelope(String domain, String focusId) => {
  'ok': true,
  'contract': 'lumenis.context.v1',
  'selection_only': true,
  'context': {'mode': 'FOCUS', 'domain_id': domain, 'subject_id': focusId},
};

Map<String, dynamic> _page(
  List<Map<String, dynamic>> items, {
  bool hasMore = false,
  String? cursor,
}) => {
  'items': items,
  'has_more': hasMore,
  'next_cursor': cursor,
  'verification_complete': true,
  'unverified_candidates': 0,
};

Map<String, dynamic> _record({
  required String domain,
  String? focusId,
  String artifactSuffix = '0000000000000001',
  String workSuffix = '000000000000000000000001',
  int version = 1,
  String? parentArtifactId,
  String? parentSha256,
  String kind = 'report',
}) {
  final publicDomain = domain.toUpperCase() == 'BMP' ? 'BMP' : 'CTH';
  final storageDomain = publicDomain == 'BMP' ? 'zbmp' : 'cth';
  final workId = 'WORK-$workSuffix';
  final artifactId = 'ART-$artifactSuffix';
  final scope = <String, dynamic>{
    'domain_id': storageDomain,
    'subject_id': publicDomain == 'CTH' ? focusId : null,
    'brand_focus_id': publicDomain == 'BMP' ? focusId : null,
    'global_scope': focusId == null,
  };
  final title = 'Research working notes';
  final markdown = version == 1
      ? 'Grounded working notes'
      : 'Revised working notes';
  final contract = <String, dynamic>{
    'id': 'lumenis.saved-work',
    'version': '1',
    'required_payload_paths': <String>[],
  };
  final document = <String, dynamic>{
    'schema': 'lumenis.saved-work/v1',
    'context': {...scope, 'actor_id': 'actor-1'},
    'work_id': workId,
    'version': version,
    'parent_artifact_id': parentArtifactId,
    'parent_sha256': parentSha256,
    'request_id': 'request-$artifactSuffix',
    'input_hash': 'b' * 64,
    'draft_digest': 'c' * 64,
    'contract': contract,
    'task_id': null,
    'assertion_id': null,
    'kind': kind,
    'title': title,
    'markdown': markdown,
    'payload': <String, dynamic>{},
    'citations': <Map<String, dynamic>>[],
    'created_at': '2026-10-11T00:00:00+00:00',
    'authorship': 'user-supplied; source facts require citations',
  };
  final artifact = <String, dynamic>{
    'artifact_id': artifactId,
    'kind': 'saved_document',
    'product_id': publicDomain == 'BMP' ? 'ZBMP' : 'CTH',
    'domain_id': storageDomain,
    'source_execution_id': workId,
    'sha256': 'a' * 64,
    'size_bytes': 100,
    'created_at': '2026-10-11T00:00:00+00:00',
    'status': 'staged',
    'approval_required': true,
    'approval_status': 'pending',
  };
  return {
    'artifact': artifact,
    'document': document,
    'return_ref': {
      'artifact_id': artifactId,
      'work_id': workId,
      'version': version,
      'scope': scope,
    },
  };
}

Map<String, dynamic> _withReceipt(Map<String, dynamic> source) {
  final row = _clone(source);
  final artifact = row['artifact'] as Map<String, dynamic>;
  final document = row['document'] as Map<String, dynamic>;
  final returnRef = row['return_ref'] as Map<String, dynamic>;
  final contract = document['contract'] as Map<String, dynamic>;
  final scope = returnRef['scope'] as Map<String, dynamic>;
  row['receipt'] = {
    'schema': 'lumenis.committed-saved-work/v1',
    'task_id': document['task_id'],
    'assertion_id': document['assertion_id'],
    'contract': contract,
    'scope': scope,
    'ref': artifact['artifact_id'],
    'work_id': document['work_id'],
    'version': document['version'],
    'parent': {
      'ref': document['parent_artifact_id'],
      'sha256': document['parent_sha256'],
    },
    'sha256': artifact['sha256'],
    'size_bytes': artifact['size_bytes'],
    'draft_digest': document['draft_digest'],
    'sources': <Map<String, dynamic>>[],
    'constraint_observations': {
      'committed_bytes_match': true,
      'parent_chain_verified': true,
      'required_payload_paths_present': contract['required_payload_paths'],
      'source_authorization': 'fresh-per-source',
      'source_count': 0,
      'factual_verification': 'NOT_ESTABLISHED_BY_STORAGE',
      'learning_admission': 'NOT_ESTABLISHED_BY_STORAGE',
      'training_eligible': false,
      'held_out': false,
      'assertion_binding': 'absent',
      'media_lineage': 'not_applicable',
    },
    'commit_state': 'registry_committed_artifact_staged',
  };
  return row;
}

Map<String, dynamic> _clone(Map<String, dynamic> value) => {
  for (final entry in value.entries)
    entry.key: entry.value is Map<String, dynamic>
        ? _clone(entry.value as Map<String, dynamic>)
        : entry.value is List
        ? (entry.value as List)
              .map((item) => item is Map<String, dynamic> ? _clone(item) : item)
              .toList()
        : entry.value,
};
