enum Sh04ScopeErrorKind { unavailable, denied, malformed }

class Sh04ScopeError implements Exception {
  const Sh04ScopeError(this.kind);

  final Sh04ScopeErrorKind kind;
}

class Sh04Scope {
  const Sh04Scope._();

  static const sharedWorkspace = Sh04Scope._();
  String get wireScopeKind => 'shared_workspace';
}

enum Sh04ExportState { ready, unavailable }

enum Sh04Format { markdown }

class Sh04Export {
  const Sh04Export({
    required this.internalId,
    required this.title,
    required this.state,
    required this.markdown,
    required this.sha256,
    required this.workId,
    required this.version,
    required this.parentArtifactId,
    required this.citations,
    required this.generatedAt,
    this.contractId = 'lumenis.saved-work',
    this.contractVersion = '1',
  });

  /// Used for API calls only. The screen must not render internal identifiers.
  final String internalId;
  final String title;
  final Sh04ExportState state;
  final String markdown;
  final String sha256;
  final String workId;
  final int version;
  final String? parentArtifactId;

  /// Kept intact so a local revision never silently drops original source
  /// scopes or rights. The revision endpoint omits citations and preserves
  /// them from its immutable parent after server-side reauthorization.
  final List<Map<String, dynamic>> citations;
  final String generatedAt;
  final String contractId;
  final String contractVersion;

  bool get canReviseHere =>
      contractId == 'lumenis.saved-work' && contractVersion == '1';
  bool get isManuscript =>
      contractId == 'lumenis.internal-pitch' && contractVersion == '4';

  Sh04Format get format => Sh04Format.markdown;
  bool get scopeVerified => true;
  bool get reopenable => state == Sh04ExportState.ready;
  String get preview => markdown;
  int get evidenceCount => citations.length;
  String get failureReason => '';

  String get formatLabel => 'Markdown';

  static Sh04Export fromResponse(Map<String, dynamic> response) {
    if (response['ok'] != true) {
      throw const FormatException(
        'Shared SavedWork operation was not accepted.',
      );
    }
    return Sh04Export.fromSavedWorkItem(response['result']);
  }

  static Sh04Export fromSavedWorkItem(Object? value) {
    final item = _asMap(value);
    final artifact = _asMap(item?['artifact']);
    final document = _asMap(item?['document']);
    final returnRef = _asMap(item?['return_ref']);
    final artifactId = _string(artifact?['artifact_id']);
    final digest = _string(artifact?['sha256']);
    final title = _userText(document?['title'], maxLength: 300);
    final markdown = _userText(
      document?['markdown'],
      maxLength: 8 * 1024 * 1024,
    );
    final workId = _string(document?['work_id']);
    final rawVersion = document?['version'];
    final version = rawVersion is int ? rawVersion : null;
    final context = _asMap(document?['context']);
    final scope = _asMap(returnRef?['scope']);
    final citations = document?['citations'];
    final contract = _asMap(document?['contract']);
    final parentArtifactId = document?['parent_artifact_id'];
    final parentSha256 = document?['parent_sha256'];
    final createdAt = _string(artifact?['created_at']) ?? '';

    if (artifactId == null ||
        !RegExp(r'^ART-[0-9a-f]{16}$').hasMatch(artifactId) ||
        digest == null ||
        !RegExp(r'^[0-9a-f]{64}$').hasMatch(digest) ||
        title == null ||
        markdown == null ||
        markdown.trim().isEmpty ||
        workId == null ||
        version == null ||
        version < 1 ||
        document?['schema'] != 'lumenis.saved-work/v1' ||
        document?['kind'] != 'report' ||
        !RegExp(r'^WORK-[0-9a-f]{24}$').hasMatch(workId) ||
        returnRef?['artifact_id'] != artifactId ||
        returnRef?['work_id'] != workId ||
        returnRef?['version'] != version ||
        !_isServerSharedContext(context) ||
        !_isSharedScope(scope) ||
        !_isReportContract(contract, _asMap(document?['payload'])) ||
        citations is! List ||
        citations.any((item) => item is! Map) ||
        (version == 1 && (parentArtifactId != null || parentSha256 != null)) ||
        (version > 1 &&
            (parentArtifactId is! String ||
                !RegExp(r'^ART-[0-9a-f]{16}$').hasMatch(parentArtifactId) ||
                parentSha256 is! String ||
                !RegExp(r'^[0-9a-f]{64}$').hasMatch(parentSha256)))) {
      throw const FormatException(
        'The SavedWork version is not a verified Shared report.',
      );
    }
    return Sh04Export(
      internalId: artifactId,
      title: title,
      state: Sh04ExportState.ready,
      markdown: markdown,
      sha256: digest,
      workId: workId,
      version: version,
      parentArtifactId: parentArtifactId as String?,
      citations: citations
          .map((citation) => _asMap(citation)!)
          .map((citation) => Map<String, dynamic>.unmodifiable(citation))
          .toList(growable: false),
      generatedAt: createdAt,
      contractId: contract!['id'] as String,
      contractVersion: contract['version'] as String,
    );
  }
}

class Sh04Snapshot {
  const Sh04Snapshot({
    required this.scope,
    required this.exports,
    required this.verificationComplete,
    required this.unverifiedCandidates,
    required this.hasMore,
    required this.nextCursor,
  });

  final Sh04Scope scope;
  final List<Sh04Export> exports;
  final bool verificationComplete;
  final int unverifiedCandidates;
  final bool hasMore;
  final String? nextCursor;

  factory Sh04Snapshot.fromResponse(Map<String, dynamic> response) {
    final result = _asMap(response['result']);
    final rawItems = result?['items'];
    final complete = result?['verification_complete'];
    final unverified = result?['unverified_candidates'];
    final hasMore = result?['has_more'];
    final cursor = result?['next_cursor'];
    if (response['ok'] != true ||
        result == null ||
        rawItems is! List ||
        complete is! bool ||
        unverified is! int ||
        unverified < 0 ||
        hasMore is! bool ||
        (cursor != null && cursor is! String) ||
        (hasMore && (cursor is! String || cursor.isEmpty))) {
      throw const FormatException('Shared SavedWork search is incomplete.');
    }
    final exports = <Sh04Export>[];
    for (final item in rawItems) {
      exports.add(Sh04Export.fromSavedWorkItem(item));
    }
    return Sh04Snapshot(
      scope: Sh04Scope.sharedWorkspace,
      exports: List.unmodifiable(exports),
      verificationComplete: complete,
      unverifiedCandidates: unverified,
      hasMore: hasMore,
      nextCursor: cursor as String?,
    );
  }
}

bool _isSharedScope(Map<String, dynamic>? value) =>
    value != null &&
    value.length == 2 &&
    value['scope_kind'] == 'shared_workspace' &&
    value['version'] == 1;

bool _isServerSharedContext(Map<String, dynamic>? value) {
  if (value == null ||
      value['scope_kind'] != 'shared_workspace' ||
      value['version'] != 1 ||
      value.keys.any(
        (key) => const {
          'domain_id',
          'product_id',
          'subject_id',
          'brand_focus_id',
          'global_scope',
        }.contains(key),
      )) {
    return false;
  }
  final actorContext =
      value.keys.toSet().difference(const {
        'scope_kind',
        'version',
        'actor_id',
      }).isEmpty &&
      value['actor_id'] is int &&
      value['actor_id'] > 0;
  final localPrincipalContext =
      value.keys.toSet().difference(const {
        'scope_kind',
        'version',
        'principal_kind',
        'principal_ref',
      }).isEmpty &&
      value['principal_kind'] is String &&
      (value['principal_kind'] as String).isNotEmpty &&
      value['principal_ref'] is String &&
      (value['principal_ref'] as String).isNotEmpty;
  return actorContext || localPrincipalContext;
}

bool _isGenericReportContract(Map<String, dynamic>? value) =>
    value != null &&
    value.length == 3 &&
    value['id'] == 'lumenis.saved-work' &&
    value['version'] == '1' &&
    value['required_payload_paths'] is List &&
    (value['required_payload_paths'] as List).isEmpty;

bool _isReportContract(
  Map<String, dynamic>? contract,
  Map<String, dynamic>? payload,
) {
  if (_isGenericReportContract(contract)) return true;
  if (contract == null ||
      contract.length != 3 ||
      _string(contract['id']) == null ||
      _string(contract['version']) == null ||
      contract['required_payload_paths'] is! List ||
      payload == null) {
    return false;
  }
  final paths = contract['required_payload_paths'] as List;
  if (paths.length > 100) return false;
  for (final path in paths) {
    if (path is! String || path.isEmpty) return false;
    Object? value = payload;
    for (final segment in path.split('.')) {
      if (segment.isEmpty || value is! Map || !value.containsKey(segment)) {
        return false;
      }
      value = value[segment];
    }
    if (value == null) return false;
  }
  return true;
}

Map<String, dynamic>? _asMap(Object? value) {
  if (value is! Map) return null;
  return value.map((key, value) => MapEntry('$key', value));
}

String? _string(Object? value) =>
    value is String && value.trim().isNotEmpty ? value.trim() : null;

String? _userText(Object? value, {required int maxLength}) {
  final text = value is String ? value : null;
  if (text == null ||
      text.trim().isEmpty ||
      text.length > maxLength ||
      RegExp(r'[\x00-\x08\x0B\x0C\x0E-\x1F]').hasMatch(text)) {
    return null;
  }
  return text;
}
