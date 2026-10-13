import 'dart:convert';

import '../../../core/lumenis_core_client.dart';
import 'sh04_snapshot.dart';

typedef Sh04ScreenReader = Future<Map<String, dynamic>> Function();

abstract interface class Sh04Repository {
  Future<Sh04Snapshot> loadExports();
}

/// Optional SavedWork operations. Keeping these outside [Sh04Repository]
/// preserves existing legacy adapters and isolated screen fakes.
abstract interface class Sh04SavedWorkRepository implements Sh04Repository {
  Future<Sh04Snapshot> search(String query);

  Future<Sh04Snapshot> loadMore(Sh04Snapshot current);

  Future<Sh04Export> reopen(
    Sh04Export item, {
    String? artifactId,
    String? expectedHash,
    int? expectedVersion,
  });
}

class CoreSh04Repository implements Sh04SavedWorkRepository {
  const CoreSh04Repository({
    required LumenisCoreClient client,
    this.screenReader,
  }) : _client = client;

  final LumenisCoreClient _client;
  final Sh04ScreenReader? screenReader;

  @override
  Future<Sh04Snapshot> loadExports() => search('');

  @override
  Future<Sh04Snapshot> search(String query) async {
    final reader = screenReader;
    if (reader != null) return Sh04Snapshot.fromResponse(await reader());
    if (query.runes.length > 200) {
      throw const FormatException('SavedWork search is too long.');
    }
    final selection = _selection();
    return _loadPage(
      selection: selection,
      query: query,
      previous: null,
      requestedDomains: selection.domains,
    );
  }

  @override
  Future<Sh04Snapshot> loadMore(Sh04Snapshot current) async {
    if (screenReader != null) return current;
    final selection = _selection();
    if (current.contextSignature != selection.signature) {
      throw const FormatException('The workspace context changed.');
    }
    final domains = selection.domains
        .where((domain) => current.hasMoreByDomain[domain] == true)
        .toList(growable: false);
    if (domains.isEmpty) return current;
    return _loadPage(
      selection: selection,
      query: current.query,
      previous: current,
      requestedDomains: domains,
    );
  }

  @override
  Future<Sh04Export> reopen(
    Sh04Export item, {
    String? artifactId,
    String? expectedHash,
    int? expectedVersion,
  }) async {
    final listed = item.savedWork;
    if (listed == null || !item.reopenable) {
      throw const FormatException('This result cannot be reopened.');
    }
    final selection = _selection();
    final targetId = artifactId ?? listed.artifactId;
    final targetHash = expectedHash ?? listed.hash;
    final targetVersion = expectedVersion ?? listed.version;
    final response = await _client.reopenSavedWork(
      domainId: listed.domainId,
      artifactId: targetId,
    );
    _ensureSameSelection(selection);
    final saved = _parseSavedWork(
      response,
      requestedDomain: listed.domainId,
      expectedScope: selection.scopeFor(listed.domainId),
      requireReceipt: true,
      expectedArtifactId: targetId,
      expectedHash: targetHash,
      expectedVersion: targetVersion,
    );
    if (saved.workId != listed.workId ||
        saved.kind != listed.kind ||
        saved.contractId != listed.contractId) {
      throw const FormatException(
        'The reopened result does not match its list row.',
      );
    }
    if (artifactId == null && !_sameListedVersion(listed, saved)) {
      throw const FormatException('The reopened result changed after listing.');
    }
    if (artifactId != null &&
        (targetVersion != listed.version - 1 ||
            listed.parentArtifactId != targetId ||
            listed.parentSha256 != targetHash)) {
      throw const FormatException(
        'The requested parent version is inconsistent.',
      );
    }
    return _export(saved);
  }

  Future<Sh04Snapshot> _loadPage({
    required _Selection selection,
    required String query,
    required Sh04Snapshot? previous,
    required List<String> requestedDomains,
  }) async {
    final results = await Future.wait(
      requestedDomains.map((domain) async {
        try {
          final response = await _client.listSavedWorks(
            domainId: domain,
            query: query,
            limit: 30,
            cursor: previous?.cursors[domain],
          );
          _ensureSameSelection(selection);
          return _DomainPage.success(domain, response);
        } catch (error) {
          return _DomainPage.failure(domain, error);
        }
      }),
    );
    _ensureSameSelection(selection);

    final failures = <String, Object>{};
    for (final result in results) {
      if (result.error != null) failures[result.domain] = result.error!;
    }
    if (failures.length == requestedDomains.length) {
      throw failures.values.first;
    }

    final exports = <Sh04Export>[...?previous?.exports];
    final failedDomains = <String>{...?previous?.failedDomains};
    final cursors = <String, String?>{...?previous?.cursors};
    final hasMoreByDomain = <String, bool>{...?previous?.hasMoreByDomain};
    var incomplete = previous?.incomplete ?? false;
    for (final result in results) {
      final domain = result.domain;
      final error = result.error;
      if (error != null) {
        failedDomains.add(domain);
        incomplete = true;
        continue;
      }
      failedDomains.remove(domain);
      try {
        final response = result.response!;
        final page = _parsePage(response, domain: domain, selection: selection);
        exports.addAll(page.exports);
        incomplete = incomplete || page.incomplete;
        cursors[domain] = page.nextCursor;
        hasMoreByDomain[domain] = page.hasMore;
      } catch (error) {
        failures[domain] = error;
        failedDomains.add(domain);
        incomplete = true;
      }
    }
    if (previous == null && failures.length == requestedDomains.length) {
      throw failures.values.first;
    }

    final merged = <String, Sh04Export>{};
    for (final export in exports) {
      final prior = merged[export.internalId];
      if (prior == null) {
        merged[export.internalId] = export;
      } else if (!_sameExportIdentity(prior, export)) {
        incomplete = true;
        merged['unverified-duplicate-${merged.length}'] = _unverifiedExport(
          'unverified-duplicate-${merged.length}',
        );
      }
    }
    final ordered = merged.values.toList(growable: false)
      ..sort((left, right) => right.generatedAt.compareTo(left.generatedAt));
    return Sh04Snapshot(
      scope: selection.displayScope,
      exports: ordered,
      failedDomains: failedDomains.toList()..sort(),
      incomplete: incomplete || failedDomains.isNotEmpty,
      hasMore: hasMoreByDomain.values.any((value) => value),
      cursors: cursors,
      hasMoreByDomain: hasMoreByDomain,
      query: query,
      contextSignature: selection.signature,
    );
  }

  _ParsedPage _parsePage(
    Map<String, dynamic> response, {
    required String domain,
    required _Selection selection,
  }) {
    final rawItems = response['items'];
    final hasMore = response['has_more'];
    final rawCursor = response['next_cursor'];
    final verificationComplete = response['verification_complete'];
    final unverifiedCandidates = response['unverified_candidates'];
    if (rawItems is! List ||
        hasMore is! bool ||
        verificationComplete is! bool ||
        unverifiedCandidates is! int ||
        unverifiedCandidates < 0 ||
        (hasMore && (rawCursor is! String || rawCursor.isEmpty)) ||
        (!hasMore && rawCursor != null && rawCursor is! String)) {
      throw const FormatException('SavedWork page metadata is invalid.');
    }
    final nextCursor = rawCursor is String ? rawCursor : null;
    final expectedScope = selection.scopeFor(domain);
    final exports = <Sh04Export>[];
    var incomplete = !verificationComplete || unverifiedCandidates > 0;
    for (var index = 0; index < rawItems.length; index++) {
      try {
        final saved = _parseSavedWork(
          rawItems[index],
          requestedDomain: domain,
          expectedScope: expectedScope,
          requireReceipt: false,
        );
        exports.add(_export(saved));
      } catch (_) {
        incomplete = true;
        exports.add(
          _unverifiedExport('unverified-${domain.toLowerCase()}-$index'),
        );
      }
    }
    return _ParsedPage(
      exports: exports,
      hasMore: hasMore,
      nextCursor: nextCursor,
      incomplete: incomplete,
    );
  }

  Sh04SavedWork _parseSavedWork(
    Object? value, {
    required String requestedDomain,
    required Map<String, dynamic> expectedScope,
    required bool requireReceipt,
    String? expectedArtifactId,
    String? expectedHash,
    int? expectedVersion,
  }) {
    final row = _map(value);
    final artifact = _map(row?['artifact']);
    final document = _map(row?['document']);
    final returnRef = _map(row?['return_ref']);
    if (row == null ||
        artifact == null ||
        document == null ||
        returnRef == null) {
      throw const FormatException('SavedWork record is incomplete.');
    }
    final artifactId = _requiredString(artifact['artifact_id']);
    final artifactHash = _sha256(artifact['sha256']);
    final artifactSize = artifact['size_bytes'];
    final artifactKind = artifact['kind'];
    final storageDomain = _storageDomain(requestedDomain);
    if (!RegExp(r'^ART-[0-9a-f]{16}$').hasMatch(artifactId) ||
        artifactHash == null ||
        artifactSize is! int ||
        artifactSize < 1 ||
        artifactKind != 'saved_document' ||
        artifact['domain_id'] != storageDomain ||
        artifact['product_id'] != _productId(requestedDomain) ||
        artifact['source_execution_id'] != document['work_id'] ||
        (expectedArtifactId != null && artifactId != expectedArtifactId) ||
        (expectedHash != null && artifactHash != expectedHash)) {
      throw const FormatException('SavedWork artifact identity is invalid.');
    }
    if (document['schema'] != 'lumenis.saved-work/v1') {
      throw const FormatException('SavedWork document schema is unsupported.');
    }
    final documentContext = _map(document['context']);
    final scope = _scopeFromContext(documentContext);
    if (!_sameJson(scope, expectedScope) ||
        !_validContextIdentity(documentContext, expectedScope)) {
      throw const FormatException('SavedWork document context is invalid.');
    }
    final version = document['version'];
    final workId = _requiredString(document['work_id']);
    final title = document['title'];
    final markdown = document['markdown'];
    final kind = document['kind'];
    final createdAt = document['created_at'];
    final draftDigest = _sha256(document['draft_digest']);
    final parentArtifactId = document['parent_artifact_id'];
    final parentSha256 = document['parent_sha256'];
    final taskId = document['task_id'];
    final contract = _map(document['contract']);
    final payload = _map(document['payload']);
    final citations = _maps(document['citations']);
    if (!RegExp(r'^WORK-[0-9a-f]{24}$').hasMatch(workId) ||
        version is! int ||
        version < 1 ||
        (expectedVersion != null && version != expectedVersion) ||
        title is! String ||
        title.trim().isEmpty ||
        markdown is! String ||
        markdown.trim().isEmpty ||
        kind is! String ||
        !const {
          'research',
          'report',
          'podcast_episode',
          'delivery_preferences',
        }.contains(kind) ||
        createdAt is! String ||
        createdAt.isEmpty ||
        draftDigest == null ||
        !_validParent(version, parentArtifactId, parentSha256) ||
        (taskId != null && (taskId is! String || taskId.isEmpty)) ||
        contract == null ||
        payload == null ||
        citations == null ||
        !_validContract(contract, payload)) {
      throw const FormatException('SavedWork document fields are invalid.');
    }
    final returnScope = _map(returnRef['scope']);
    if (returnRef.keys.toSet().difference(const {
          'artifact_id',
          'work_id',
          'version',
          'scope',
        }).isNotEmpty ||
        returnRef.length != 4 ||
        returnRef['artifact_id'] != artifactId ||
        returnRef['work_id'] != workId ||
        returnRef['version'] != version ||
        returnScope == null ||
        !_sameJson(returnScope, expectedScope)) {
      throw const FormatException('SavedWork return reference is invalid.');
    }

    var sources = <Map<String, dynamic>>[];
    var committed = false;
    if (requireReceipt) {
      final receipt = _map(row['receipt']);
      if (receipt == null) {
        throw const FormatException('SavedWork commit receipt is missing.');
      }
      sources = _validateReceipt(
        receipt,
        artifactId: artifactId,
        artifactHash: artifactHash,
        artifactSize: artifactSize,
        workId: workId,
        version: version,
        draftDigest: draftDigest,
        parentArtifactId: parentArtifactId as String?,
        parentSha256: parentSha256 as String?,
        expectedScope: expectedScope,
        contract: contract,
        citations: citations,
        taskId: taskId as String?,
        document: document,
      );
      committed = true;
    }

    final immutableDocument = _deepMap(document);
    final immutableScope = _deepMap(expectedScope);
    return Sh04SavedWork(
      artifactId: artifactId,
      domainId: _publicDomain(requestedDomain),
      hash: artifactHash,
      sizeBytes: artifactSize,
      workId: workId,
      version: version,
      title: title,
      markdown: markdown,
      kind: kind,
      createdAt: createdAt,
      parentArtifactId: parentArtifactId as String?,
      parentSha256: parentSha256 as String?,
      draftDigest: draftDigest,
      taskId: taskId as String?,
      contractId: _requiredString(contract['id']),
      contractVersion: _requiredString(contract['version']),
      citations: citations,
      sources: sources,
      document: immutableDocument,
      returnScope: immutableScope,
      committed: committed,
    );
  }

  List<Map<String, dynamic>> _validateReceipt(
    Map<String, dynamic> receipt, {
    required String artifactId,
    required String artifactHash,
    required int artifactSize,
    required String workId,
    required int version,
    required String draftDigest,
    required String? parentArtifactId,
    required String? parentSha256,
    required Map<String, dynamic> expectedScope,
    required Map<String, dynamic> contract,
    required List<Map<String, dynamic>> citations,
    required String? taskId,
    required Map<String, dynamic> document,
  }) {
    const receiptKeys = {
      'schema',
      'task_id',
      'assertion_id',
      'contract',
      'scope',
      'ref',
      'work_id',
      'version',
      'parent',
      'sha256',
      'size_bytes',
      'draft_digest',
      'sources',
      'constraint_observations',
      'commit_state',
    };
    final parent = _map(receipt['parent']);
    final receiptScope = _map(receipt['scope']);
    final observations = _map(receipt['constraint_observations']);
    final rawSources = _maps(receipt['sources']);
    if (receipt.keys.toSet().length != receiptKeys.length ||
        !receipt.keys.toSet().containsAll(receiptKeys) ||
        receipt['schema'] != 'lumenis.committed-saved-work/v1' ||
        receipt['ref'] != artifactId ||
        receipt['work_id'] != workId ||
        receipt['version'] != version ||
        receipt['sha256'] != artifactHash ||
        receipt['size_bytes'] != artifactSize ||
        receipt['draft_digest'] != draftDigest ||
        receipt['task_id'] != taskId ||
        !_sameJson(receipt['contract'], contract) ||
        receiptScope == null ||
        !_sameJson(receiptScope, expectedScope) ||
        parent == null ||
        parent.length != 2 ||
        parent['ref'] != parentArtifactId ||
        parent['sha256'] != parentSha256 ||
        rawSources == null ||
        observations == null ||
        receipt['commit_state'] != 'registry_committed_artifact_staged' ||
        observations['committed_bytes_match'] != true ||
        observations['parent_chain_verified'] != true ||
        observations['source_authorization'] != 'fresh-per-source' ||
        observations['source_count'] != rawSources.length ||
        observations['required_payload_paths_present'] is! List ||
        !_sameJson(
          observations['required_payload_paths_present'],
          contract['required_payload_paths'],
        ) ||
        observations['training_eligible'] != false ||
        observations['held_out'] != false ||
        observations['factual_verification'] != 'NOT_ESTABLISHED_BY_STORAGE' ||
        observations['learning_admission'] != 'NOT_ESTABLISHED_BY_STORAGE' ||
        !_sameSourceIds(citations, rawSources) ||
        document['assertion_id'] != receipt['assertion_id']) {
      throw const FormatException('SavedWork commit receipt does not match.');
    }
    for (final source in rawSources) {
      final sourceScope = _map(source['scope']);
      if (sourceScope == null || !_validScopeShape(sourceScope)) {
        throw const FormatException('SavedWork source receipt is invalid.');
      }
    }
    return rawSources;
  }

  _Selection _selection() {
    final envelope = _client.currentContextEnvelope;
    final context = _map(envelope?['context']);
    if (envelope == null ||
        envelope['ok'] != true ||
        envelope['contract'] != 'lumenis.context.v1' ||
        envelope['selection_only'] != true ||
        context == null) {
      throw const Sh04ScopeError(Sh04ScopeErrorKind.unavailable);
    }
    final mode = context['mode'];
    final domains = _client.savedWorkDomains.map(_publicDomain).toList();
    if (mode == 'GLOBAL_ALL') {
      if (context['subject_id'] != null ||
          context['brand_focus_id'] != null ||
          domains.toSet().length != 2 ||
          !domains.toSet().containsAll(const {'CTH', 'BMP'})) {
        throw const Sh04ScopeError(Sh04ScopeErrorKind.malformed);
      }
      return _Selection.global(domains);
    }
    final domain = _publicDomain(context['domain_id'] as String? ?? '');
    final focusId = context['subject_id'];
    if (mode != 'FOCUS' ||
        (domain != 'CTH' && domain != 'BMP') ||
        focusId is! String ||
        focusId.trim().isEmpty ||
        domains.length != 1 ||
        domains.single != domain) {
      throw const Sh04ScopeError(Sh04ScopeErrorKind.malformed);
    }
    return _Selection.focus(domain, focusId);
  }

  void _ensureSameSelection(_Selection expected) {
    if (_selection().signature != expected.signature) {
      throw const FormatException('The workspace context changed.');
    }
  }

  Sh04Export _export(Sh04SavedWork saved) => Sh04Export(
    internalId: saved.artifactId,
    title: saved.title,
    format: Sh04Format.markdown,
    state: Sh04ExportState.ready,
    scopeVerified: true,
    reopenable: true,
    preview: saved.committed ? saved.markdown : '',
    evidenceCount: saved.committed ? saved.sources.length : null,
    generatedAt: saved.createdAt,
    failureReason: '',
    savedWork: saved,
  );

  Sh04Export _unverifiedExport(String id) => Sh04Export(
    internalId: id,
    title: '成果暂不可验证',
    format: Sh04Format.unknown,
    state: Sh04ExportState.unavailable,
    scopeVerified: false,
    reopenable: false,
    preview: '',
    evidenceCount: null,
    generatedAt: '',
    failureReason: 'SAVED_WORK_RECORD_UNVERIFIED',
  );
}

class _Selection {
  const _Selection._({
    required this.mode,
    required this.focusDomain,
    required this.focusId,
    required this.domains,
    required this.signature,
    required this.displayScope,
  });

  factory _Selection.global(List<String> domains) => _Selection._(
    mode: Sh04ScopeMode.globalAll,
    focusDomain: null,
    focusId: null,
    domains: List<String>.unmodifiable(domains),
    signature: 'GLOBAL_ALL',
    displayScope: const Sh04Scope(
      mode: Sh04ScopeMode.globalAll,
      domain: null,
      focusId: null,
      displayName: '全部范围',
    ),
  );

  factory _Selection.focus(String domain, String focusId) => _Selection._(
    mode: Sh04ScopeMode.focus,
    focusDomain: domain,
    focusId: focusId,
    domains: List<String>.unmodifiable([domain]),
    signature: 'FOCUS:$domain:$focusId',
    displayScope: Sh04Scope(
      mode: Sh04ScopeMode.focus,
      domain: domain,
      focusId: focusId,
      displayName: focusId,
    ),
  );

  final Sh04ScopeMode mode;
  final String? focusDomain;
  final String? focusId;
  final List<String> domains;
  final String signature;
  final Sh04Scope displayScope;

  Map<String, dynamic> scopeFor(String requestedDomain) {
    final domain = _publicDomain(requestedDomain);
    if (!domains.contains(domain)) {
      throw const FormatException('SavedWork domain is outside this view.');
    }
    final storageDomain = _storageDomain(domain);
    final focused = mode == Sh04ScopeMode.focus;
    return <String, dynamic>{
      'domain_id': storageDomain,
      'subject_id': focused && domain == 'CTH' ? focusId : null,
      'brand_focus_id': focused && domain == 'BMP' ? focusId : null,
      'global_scope': !focused,
    };
  }
}

class _DomainPage {
  const _DomainPage._(this.domain, this.response, this.error);

  factory _DomainPage.success(String domain, Map<String, dynamic> response) =>
      _DomainPage._(domain, response, null);

  factory _DomainPage.failure(String domain, Object error) =>
      _DomainPage._(domain, null, error);

  final String domain;
  final Map<String, dynamic>? response;
  final Object? error;
}

class _ParsedPage {
  const _ParsedPage({
    required this.exports,
    required this.hasMore,
    required this.nextCursor,
    required this.incomplete,
  });

  final List<Sh04Export> exports;
  final bool hasMore;
  final String? nextCursor;
  final bool incomplete;
}

bool _sameListedVersion(Sh04SavedWork listed, Sh04SavedWork reopened) =>
    listed.artifactId == reopened.artifactId &&
    listed.domainId == reopened.domainId &&
    listed.hash == reopened.hash &&
    listed.sizeBytes == reopened.sizeBytes &&
    listed.workId == reopened.workId &&
    listed.version == reopened.version &&
    listed.title == reopened.title &&
    listed.markdown == reopened.markdown &&
    listed.kind == reopened.kind &&
    listed.createdAt == reopened.createdAt &&
    listed.parentArtifactId == reopened.parentArtifactId &&
    listed.parentSha256 == reopened.parentSha256 &&
    listed.draftDigest == reopened.draftDigest &&
    listed.contractId == reopened.contractId &&
    listed.contractVersion == reopened.contractVersion;

bool _sameExportIdentity(Sh04Export left, Sh04Export right) {
  final a = left.savedWork;
  final b = right.savedWork;
  return a != null && b != null && a.hash == b.hash && a.domainId == b.domainId;
}

bool _sameSourceIds(
  List<Map<String, dynamic>> citations,
  List<Map<String, dynamic>> sources,
) {
  final cited = <int>{};
  for (final citation in citations) {
    final id = citation['evidence_id'];
    if (id is! int || id < 1) return false;
    cited.add(id);
  }
  final returned = <int>{};
  for (final source in sources) {
    final id = source['evidence_id'];
    if (id is! int || id < 1) return false;
    returned.add(id);
  }
  return cited.length == returned.length && cited.containsAll(returned);
}

bool _validParent(int version, Object? artifactId, Object? sha256) {
  if (version == 1) return artifactId == null && sha256 == null;
  return artifactId is String &&
      RegExp(r'^ART-[0-9a-f]{16}$').hasMatch(artifactId) &&
      _sha256(sha256) != null;
}

bool _validContract(
  Map<String, dynamic> contract,
  Map<String, dynamic> payload,
) {
  if (contract.keys.toSet().length != 3 ||
      !contract.keys.toSet().containsAll(const {
        'id',
        'version',
        'required_payload_paths',
      }) ||
      _nonEmpty(contract['id']) == null ||
      _nonEmpty(contract['version']) == null ||
      contract['required_payload_paths'] is! List) {
    return false;
  }
  for (final path in contract['required_payload_paths'] as List) {
    if (path is! String ||
        !RegExp(r'^[A-Za-z_][A-Za-z0-9_.]{0,199}$').hasMatch(path)) {
      return false;
    }
    Object? value = payload;
    for (final key in path.split('.')) {
      if (value is! Map || !value.containsKey(key)) return false;
      value = value[key];
    }
  }
  return true;
}

bool _validContextIdentity(
  Map<String, dynamic>? context,
  Map<String, dynamic> expectedScope,
) {
  if (context == null) return false;
  const scopeKeys = {
    'domain_id',
    'subject_id',
    'brand_focus_id',
    'global_scope',
  };
  final keys = context.keys.toSet();
  final suffix = keys.difference(scopeKeys);
  final actor = suffix.length == 1 && suffix.contains('actor_id');
  final principal =
      suffix.length == 2 &&
      suffix.contains('principal_kind') &&
      suffix.contains('principal_ref');
  if (!actor && !principal) return false;
  if (actor && _nonEmpty(context['actor_id']) == null) return false;
  if (principal &&
      (_nonEmpty(context['principal_kind']) == null ||
          _nonEmpty(context['principal_ref']) == null)) {
    return false;
  }
  return _sameJson(_scopeFromContext(context), expectedScope);
}

Map<String, dynamic> _scopeFromContext(Map<String, dynamic>? context) {
  if (context == null) {
    throw const FormatException('SavedWork scope is malformed.');
  }
  final scope = <String, dynamic>{
    for (final key in const [
      'domain_id',
      'subject_id',
      'brand_focus_id',
      'global_scope',
    ])
      if (context.containsKey(key)) key: context[key],
  };
  if (!_validScopeShape(scope)) {
    throw const FormatException('SavedWork scope is malformed.');
  }
  return scope;
}

bool _validScopeShape(Map<String, dynamic> scope) =>
    scope.keys.toSet().length == 4 &&
    scope.keys.toSet().containsAll(const {
      'domain_id',
      'subject_id',
      'brand_focus_id',
      'global_scope',
    }) &&
    (scope['domain_id'] == 'cth' || scope['domain_id'] == 'zbmp') &&
    (scope['subject_id'] == null || scope['subject_id'] is String) &&
    (scope['brand_focus_id'] == null || scope['brand_focus_id'] is String) &&
    scope['global_scope'] is bool &&
    ((scope['global_scope'] == true &&
            scope['subject_id'] == null &&
            scope['brand_focus_id'] == null) ||
        (scope['global_scope'] == false &&
            ((scope['domain_id'] == 'cth' &&
                    scope['subject_id'] is String &&
                    scope['brand_focus_id'] == null) ||
                (scope['domain_id'] == 'zbmp' &&
                    scope['subject_id'] == null &&
                    scope['brand_focus_id'] is String))));

String _storageDomain(String value) => switch (_publicDomain(value)) {
  'CTH' => 'cth',
  'BMP' => 'zbmp',
  _ => throw const FormatException('SavedWork domain is invalid.'),
};

String _productId(String value) =>
    _publicDomain(value) == 'BMP' ? 'ZBMP' : 'CTH';

String _publicDomain(Object? value) {
  final text = value is String ? value.trim().toUpperCase() : '';
  return switch (text) {
    'CTH' => 'CTH',
    'BMP' || 'ZBMP' => 'BMP',
    _ => throw const FormatException('SavedWork domain is invalid.'),
  };
}

Map<String, dynamic>? _map(Object? value) {
  if (value is! Map) return null;
  final result = <String, dynamic>{};
  for (final entry in value.entries) {
    if (entry.key is! String) return null;
    result[entry.key as String] = entry.value;
  }
  return result;
}

List<Map<String, dynamic>>? _maps(Object? value) {
  if (value is! List) return null;
  final result = <Map<String, dynamic>>[];
  for (final entry in value) {
    final map = _map(entry);
    if (map == null) return null;
    result.add(map);
  }
  return result;
}

Map<String, dynamic> _deepMap(Map<String, dynamic> value) =>
    Map<String, dynamic>.unmodifiable(
      value.map((key, value) => MapEntry(key, _deepFreeze(value))),
    );

Object? _deepFreeze(Object? value) {
  if (value is Map) {
    final map = _map(value);
    if (map == null) throw const FormatException('SavedWork JSON is invalid.');
    return _deepMap(map);
  }
  if (value is List) {
    return List<Object?>.unmodifiable(value.map(_deepFreeze));
  }
  if (value is num && !value.isFinite) {
    throw const FormatException('SavedWork JSON is invalid.');
  }
  if (value == null || value is String || value is bool || value is num) {
    return value;
  }
  throw const FormatException('SavedWork JSON is invalid.');
}

String _requiredString(Object? value) {
  final text = _nonEmpty(value);
  if (text == null) throw const FormatException('SavedWork string is invalid.');
  return text;
}

String? _nonEmpty(Object? value) =>
    value is String && value.trim().isNotEmpty ? value.trim() : null;

String? _sha256(Object? value) =>
    value is String && RegExp(r'^[a-f0-9]{64}$').hasMatch(value) ? value : null;

bool _sameJson(Object? left, Object? right) =>
    jsonEncode(_sortedJson(left)) == jsonEncode(_sortedJson(right));

Object? _sortedJson(Object? value) {
  if (value is Map) {
    final keys = value.keys.whereType<String>().toList()..sort();
    return <String, Object?>{
      for (final key in keys) key: _sortedJson(value[key]),
    };
  }
  if (value is List) return value.map(_sortedJson).toList(growable: false);
  return value;
}
