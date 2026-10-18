class Bmp09Scope {
  const Bmp09Scope({
    required this.mode,
    required this.brandId,
    required this.displayNames,
  });

  final String mode;
  final String? brandId;
  final Map<String, String> displayNames;

  bool get isFocus => mode == 'FOCUS' && brandId != null;
  bool get isGlobal => mode == 'GLOBAL_ALL' && brandId == null;

  String? localizedName(String languageCode) =>
      displayNames[languageCode] ??
      displayNames['en'] ??
      displayNames['zh-CN'] ??
      displayNames['ko'];

  factory Bmp09Scope.fromJson(Object? value) {
    final map = _asMap(value) ?? const <String, Object?>{};
    final rawNames = _asMap(map['display_name'] ?? map['brand_name']);
    final names = <String, String>{};
    for (final entry
        in rawNames?.entries ?? const <MapEntry<String, Object?>>[]) {
      final text = _safeText(entry.value);
      if (text != null) names[entry.key] = text;
    }
    return Bmp09Scope(
      mode: (_asString(map['mode']) ?? 'UNKNOWN').toUpperCase(),
      brandId: _safeId(map['brand_id']),
      displayNames: names,
    );
  }
}

class Bmp09Dimension {
  const Bmp09Dimension({
    required this.name,
    required this.score,
    required this.movement,
    required this.confidence,
    required this.evidenceCoverage,
  });

  final String name;
  final num score;
  final String movement;
  final String confidence;
  final String evidenceCoverage;
}

class Bmp09Report {
  const Bmp09Report({required this.title, required this.period});

  final String title;
  final String period;
}

class Bmp09Snapshot {
  const Bmp09Snapshot({
    required this.contractBound,
    required this.dataState,
    required this.scope,
    required this.scopeApproved,
    required this.dimensions,
    required this.reports,
    required this.grantedPermissions,
    this.savedArtifacts = const [],
    this.sourceBriefArtifacts = const [],
    this.savedArtifactRead,
    this.sourceBriefRead,
  });

  final bool contractBound;
  final String dataState;
  final Bmp09Scope scope;
  final bool scopeApproved;
  final List<Bmp09Dimension> dimensions;
  final List<Bmp09Report> reports;
  final Set<String> grantedPermissions;
  final List<Bmp09SavedArtifact> savedArtifacts;
  final List<Bmp09SourceBriefArtifact> sourceBriefArtifacts;
  final Bmp09ArtifactRead? savedArtifactRead;
  final Bmp09ArtifactRead? sourceBriefRead;

  bool get hasMeasuredResults => dimensions.isNotEmpty;

  bool canStage(String permission) =>
      scopeApproved && grantedPermissions.contains(permission);

  factory Bmp09Snapshot.fromResponse(Map<String, dynamic> response) {
    if (response['ok'] != true || response['screen'] != 'BMP-09') {
      throw const FormatException('BMP-09 runtime response is not valid.');
    }
    if (const [
      'report_artifact_contract',
      'report_screen_binding',
      'report_authorization',
      'saved_artifacts',
      'source_brief_artifacts',
    ].any(response.containsKey)) {
      return _reportArtifactSnapshot(response);
    }
    final scope = Bmp09Scope.fromJson(
      response['focus_context'] ?? response['scope'],
    );
    final binding = _asMap(response['binding']) ?? const <String, Object?>{};
    final truth = _asMap(response['truth']) ?? const <String, Object?>{};
    final contractBound =
        response['bound'] == true && response['source'] == 'runtime';
    final readContractV2 =
        binding['scope_read_evidence_version'] == 'v2' &&
        binding['evidence_lineage_version'] == 'v2';
    final scopeMatches =
        (_asString(binding['scope_mode'])?.toUpperCase() == scope.mode) &&
        ((scope.isFocus && binding['brand_id'] == scope.brandId) ||
            (scope.isGlobal &&
                binding['brand_id'] == null &&
                binding['global_read'] == 'ALL_GRANTED'));
    final scopeApproved =
        contractBound &&
        readContractV2 &&
        binding['read_access'] == 'ALLOWED' &&
        scopeMatches;
    return Bmp09Snapshot(
      contractBound: contractBound,
      dataState: (_asString(truth['data_state']) ?? 'UNKNOWN').toUpperCase(),
      scope: scope,
      scopeApproved: scopeApproved,
      dimensions: scopeApproved
          ? _dimensions(response['dimensions'], scope)
          : const [],
      reports: scopeApproved ? _reports(response['reports'], scope) : const [],
      grantedPermissions: _asStringList(binding['granted_permissions']).toSet(),
    );
  }
}

List<Bmp09Dimension> _dimensions(Object? value, Bmp09Scope scope) {
  final result = <Bmp09Dimension>[];
  for (final item in _asMapList(value)) {
    final name = _safeText(item['name']);
    final brandId = _safeId(item['brand_id']);
    final score = item['score'];
    final source = _asString(item['source'])?.toLowerCase();
    final evidence = _safeEvidenceRef(item['evidence_ref']);
    final movement = _allowed(item['movement'], const {'UP', 'DOWN', 'FLAT'});
    final confidence = _allowed(item['confidence'], const {
      'HIGH',
      'MEDIUM',
      'LOW',
    });
    final coverage = _allowed(item['evidence_coverage'], const {
      'FULL',
      'PARTIAL',
    });
    final matchesScope = scope.isFocus
        ? brandId == scope.brandId
        : scope.isGlobal && brandId == null && item['scope'] == 'GLOBAL_ALL';
    if (name == null ||
        !matchesScope ||
        score is! num ||
        !score.isFinite ||
        score < 0 ||
        score > 100 ||
        (source != 'actual_result' && source != 'verified_result') ||
        evidence == null ||
        movement == null ||
        confidence == null ||
        coverage == null) {
      continue;
    }
    result.add(
      Bmp09Dimension(
        name: name,
        score: score,
        movement: movement,
        confidence: confidence,
        evidenceCoverage: coverage,
      ),
    );
  }
  return result;
}

List<Bmp09Report> _reports(Object? value, Bmp09Scope scope) {
  final result = <Bmp09Report>[];
  for (final item in _asMapList(value)) {
    final title = _safeText(item['title']);
    final period = _safeText(item['period']);
    final brandId = _safeId(item['brand_id']);
    final evidence = _safeEvidenceRef(item['evidence_ref']);
    final matchesScope = scope.isFocus
        ? brandId == scope.brandId
        : scope.isGlobal && brandId == null && item['scope'] == 'GLOBAL_ALL';
    if (title != null && period != null && matchesScope && evidence != null) {
      result.add(Bmp09Report(title: title, period: period));
    }
  }
  return result;
}

String? _allowed(Object? value, Set<String> allowed) {
  final text = _asString(value)?.trim().toUpperCase();
  return text != null && allowed.contains(text) ? text : null;
}

String? _safeEvidenceRef(Object? value) {
  final text = _asString(value)?.trim();
  return text != null && text.length <= 120 && !_containsInternalWord(text)
      ? text
      : null;
}

String? _safeId(Object? value) {
  final text = _asString(value)?.trim();
  return text != null && text.length <= 120 && !_containsInternalWord(text)
      ? text
      : null;
}

String? _safeText(Object? value) {
  final text = _asString(value)?.trim();
  if (text == null ||
      text.length > 120 ||
      text.contains(RegExp(r'[\r\n]')) ||
      _containsInternalWord(text)) {
    return null;
  }
  return text;
}

bool _containsInternalWord(String value) {
  final normalized = value.toLowerCase();
  return <String>[
    'api',
    'canonical',
    'database',
    'evidence',
    'permission',
    'provider',
    'binding',
    'actor',
    'scope',
    'http',
    'sql',
    'token',
  ].any(normalized.contains);
}

Map<String, Object?>? _asMap(Object? value) {
  if (value is! Map) return null;
  return value.map((key, value) => MapEntry('$key', value));
}

List<Map<String, Object?>> _asMapList(Object? value) {
  if (value is! List) return const [];
  return value.map(_asMap).whereType<Map<String, Object?>>().toList();
}

List<String> _asStringList(Object? value) {
  if (value is! List) return const [];
  return value
      .whereType<String>()
      .map((item) => item.trim())
      .where((item) {
        return item.isNotEmpty &&
            item.length <= 80 &&
            !_containsInternalWord(item);
      })
      .toList(growable: false);
}

String? _asString(Object? value) =>
    value is String && value.isNotEmpty ? value : null;

/// SavedWork storage and SourceBrief evaluation are distinct resource owners.
class Bmp09SavedArtifact {
  const Bmp09SavedArtifact({
    required this.id,
    required this.title,
    required this.kind,
    required this.version,
    required this.sha256,
    required this.sourceCount,
    required this.assessment,
  });
  final String id;
  final String title;
  final String kind;
  final int version;
  final String sha256;
  final int sourceCount;
  final String assessment;
  String get resourceType => 'saved_work';
}

class Bmp09ReportEvaluation {
  const Bmp09ReportEvaluation({
    required this.id,
    required this.metricName,
    required this.status,
    required this.evaluatedAt,
    required this.evidenceRef,
  });
  final String id;
  final String metricName;
  final String status;
  final String evaluatedAt;
  final String evidenceRef;
}

class Bmp09SourceBriefRevision {
  const Bmp09SourceBriefRevision({
    required this.parentJobId,
    required this.parentArtifactHash,
    required this.reviewId,
    required this.reviewEvidenceRef,
  });
  final String parentJobId;
  final String parentArtifactHash;
  final String reviewId;
  final String reviewEvidenceRef;
}

class Bmp09SourceBriefArtifact {
  const Bmp09SourceBriefArtifact({
    required this.jobId,
    required this.artifactHash,
    required this.revision,
    required this.sourceCount,
    required this.reviewStatus,
    required this.evaluationState,
    required this.evaluations,
    required this.rejectedEvaluationCount,
  });
  final String jobId;
  final String artifactHash;
  final Bmp09SourceBriefRevision? revision;
  final int sourceCount;
  final String reviewStatus;
  final String evaluationState;
  final List<Bmp09ReportEvaluation> evaluations;
  final int rejectedEvaluationCount;
  String get resourceType => 'source_brief_job';

  /// Complete recording is not a passing result or a measured market effect.
  bool get allEvaluationsPassed =>
      evaluationState == 'recorded' &&
      evaluations.isNotEmpty &&
      evaluations.every((item) => item.status == 'pass');
}

/// Server pagination/rejection metadata stays separate from client rejections.
/// Null metadata means unavailable or invalid, never a verified empty list.
class Bmp09ArtifactRead {
  const Bmp09ArtifactRead({
    required this.state,
    required this.returnedCount,
    required this.rejectedCount,
    required this.clientRejectedCount,
    required this.serverReadComplete,
    required this.hasMore,
    this.scannedCount,
    this.limit,
    this.nextCursor,
    this.verificationComplete,
    this.rejectedEvaluationCount = 0,
  });
  final String state;
  final int returnedCount;
  final int rejectedCount;
  final int clientRejectedCount;
  final bool serverReadComplete;
  final bool? hasMore;
  final int? scannedCount;
  final int? limit;
  final String? nextCursor;
  final bool? verificationComplete;
  final int rejectedEvaluationCount;
  bool get readComplete =>
      serverReadComplete &&
      clientRejectedCount == 0 &&
      rejectedEvaluationCount == 0;
}

const _reportScopeKeys = {
  'domain_id',
  'subject_id',
  'brand_focus_id',
  'global_scope',
};
const _reportScreenKeys = {
  'contract',
  'module',
  'policy',
  'domain_id',
  'product_id',
  'canonical_scope',
  'subject_id',
  'brand_focus_id',
  'applied',
  'read_allowed',
  'scope_verified',
  'actor_scope',
  'global_all_granted',
};
const _requiredReportMetrics = {
  'report_artifact_integrity',
  'source_evidence_grounding',
  'multimodal_analysis_integrity',
};

Bmp09Snapshot _reportArtifactSnapshot(Map<String, dynamic> response) {
  final bound = response['bound'] == true && response['source'] == 'runtime';
  final truth = _asMap(response['truth']) ?? {};
  final screen = _asMap(response['report_screen_binding']) ?? {};
  final authorization = _asMap(response['report_authorization']) ?? {};
  final context = _asMap(authorization['context']) ?? {};
  final reportScope = _asMap(truth['scope']) ?? {};
  final mode = screen['canonical_scope'];
  final subject = _reportId(screen['subject_id']);
  final brand = _reportId(screen['brand_focus_id']);
  final focused =
      mode == 'FOCUS' &&
      subject != null &&
      brand != null &&
      subject != brand &&
      screen['global_all_granted'] == false;
  final global =
      mode == 'GLOBAL_ALL' &&
      screen['subject_id'] == null &&
      screen['brand_focus_id'] == null &&
      screen['global_all_granted'] == true;
  final primary = _asMap(response[global ? 'global_binding' : 'focus_binding']);
  final actor = context['actor_id'];
  // This v1 consumer supports the authenticated actor projection. A local
  // principal string is not interchangeable with a server-verified actor.
  final approved =
      bound &&
      response['report_artifact_contract'] ==
          'lumenis.bmp09-report-artifacts.v1' &&
      screen.keys.toSet().containsAll(_reportScreenKeys) &&
      screen['contract'] == 'lumenis.scope-read-binding.v1' &&
      screen['module'] == 'brand_market_overview' &&
      screen['policy'] == 'actor-exact-scope-v1' &&
      screen['actor_scope'] == 'authenticated' &&
      screen['domain_id'] == 'BMP' &&
      screen['product_id'] == 'ZBMP' &&
      screen['applied'] == true &&
      screen['read_allowed'] == true &&
      screen['scope_verified'] == true &&
      (focused || global) &&
      primary != null &&
      primary.keys.toSet().containsAll(_reportScreenKeys) &&
      _reportScreenKeys.every((key) => primary[key] == screen[key]) &&
      response[global ? 'focus_binding' : 'global_binding'] == null &&
      authorization['module'] == 'reports' &&
      authorization['action'] == 'read' &&
      context.length == _reportScopeKeys.length + 1 &&
      context.keys.toSet().containsAll({..._reportScopeKeys, 'actor_id'}) &&
      actor is int &&
      actor > 0 &&
      (!screen.containsKey('actor_id') ||
          (screen['actor_id'] is int && screen['actor_id'] == actor)) &&
      (!primary.containsKey('actor_id') ||
          (primary['actor_id'] is int && primary['actor_id'] == actor)) &&
      reportScope.length == _reportScopeKeys.length &&
      reportScope.keys.toSet().containsAll(_reportScopeKeys) &&
      _reportScopeKeys.every((key) => reportScope[key] == context[key]) &&
      context['domain_id'] == 'zbmp' &&
      context['subject_id'] == null &&
      context['brand_focus_id'] == (global ? null : brand) &&
      context['global_scope'] == global;
  final scope = Bmp09Scope(
    mode: mode is String ? mode : 'UNKNOWN',
    brandId: brand,
    displayNames: const {},
  );
  final saved = <Bmp09SavedArtifact>[];
  final briefs = <Bmp09SourceBriefArtifact>[];
  Bmp09ArtifactRead? savedRead;
  Bmp09ArtifactRead? briefRead;
  if (approved) {
    final rawSaved = response['saved_artifacts'];
    final rawBriefs = response['source_brief_artifacts'];
    savedRead = _savedArtifactRead(truth, rawSaved);
    briefRead = _sourceBriefRead(truth['source_brief_reports'], rawBriefs);
    if (savedRead != null && rawSaved is List) {
      final parsed = rawSaved.map(_savedArtifact).toList();
      final ids = <String, int>{};
      for (final item in parsed.whereType<Bmp09SavedArtifact>()) {
        ids[item.id] = (ids[item.id] ?? 0) + 1;
      }
      saved.addAll(
        parsed.whereType<Bmp09SavedArtifact>().where(
          (item) => ids[item.id] == 1,
        ),
      );
      savedRead = _withClientRejections(
        savedRead,
        rawSaved.length - saved.length,
      );
    }
    if (briefRead != null && rawBriefs is List) {
      final parsed = rawBriefs.map(_sourceBriefArtifact).toList();
      final ids = <String, int>{};
      for (final item in parsed.whereType<Bmp09SourceBriefArtifact>()) {
        ids[item.jobId] = (ids[item.jobId] ?? 0) + 1;
      }
      briefs.addAll(
        parsed.whereType<Bmp09SourceBriefArtifact>().where(
          (item) => ids[item.jobId] == 1,
        ),
      );
      briefRead = _withClientRejections(
        briefRead,
        rawBriefs.length - briefs.length,
        evaluations: briefs.fold(
          0,
          (sum, item) => sum + item.rejectedEvaluationCount,
        ),
      );
    }
  }
  final complete =
      savedRead?.readComplete == true && briefRead?.readComplete == true;
  final state = !approved || (savedRead == null && briefRead == null)
      ? 'UNKNOWN'
      : !complete
      ? 'PARTIAL'
      : saved.isEmpty && briefs.isEmpty
      ? 'EMPTY'
      : 'ARTIFACTS_ONLY';
  return Bmp09Snapshot(
    contractBound: bound,
    dataState: state,
    scope: scope,
    scopeApproved: approved,
    dimensions: const [],
    reports: const [],
    grantedPermissions: const {},
    savedArtifacts: List.unmodifiable(saved),
    sourceBriefArtifacts: List.unmodifiable(briefs),
    savedArtifactRead: savedRead,
    sourceBriefRead: briefRead,
  );
}

Bmp09ArtifactRead _withClientRejections(
  Bmp09ArtifactRead read,
  int rejected, {
  int evaluations = 0,
}) => Bmp09ArtifactRead(
  state: rejected > 0 || evaluations > 0 ? 'PARTIAL' : read.state,
  returnedCount: read.returnedCount,
  rejectedCount: read.rejectedCount,
  clientRejectedCount: rejected,
  serverReadComplete: read.serverReadComplete,
  hasMore: read.hasMore,
  scannedCount: read.scannedCount,
  limit: read.limit,
  nextCursor: read.nextCursor,
  verificationComplete: read.verificationComplete,
  rejectedEvaluationCount: evaluations,
);

Bmp09ArtifactRead? _savedArtifactRead(Map<String, Object?> truth, Object? raw) {
  final count = _reportCount(truth['saved_count']);
  final rejected = _reportCount(truth['unverified_candidates']);
  final more = truth['has_more'];
  final verified = truth['verification_complete'];
  final cursor = truth['next_cursor'];
  if (raw is! List ||
      raw.length > 100 ||
      count != raw.length ||
      rejected == null ||
      more is! bool ||
      verified is! bool ||
      verified != (rejected == 0) ||
      !truth.containsKey('next_cursor') ||
      (more ? _reportText(cursor, maxLength: 4096) == null : cursor != null)) {
    return null;
  }
  final complete = verified && !more;
  return Bmp09ArtifactRead(
    state: !complete
        ? 'PARTIAL'
        : count == 0
        ? 'EMPTY'
        : 'READY',
    returnedCount: count!,
    rejectedCount: rejected,
    clientRejectedCount: 0,
    serverReadComplete: complete,
    hasMore: more,
    nextCursor: cursor as String?,
    verificationComplete: verified,
  );
}

Bmp09ArtifactRead? _sourceBriefRead(Object? value, Object? raw) {
  final meta = _asMap(value) ?? {};
  final returned = _reportCount(meta['returned_count']);
  final rejected = _reportCount(meta['rejected_count']);
  final scanned = _reportCount(meta['scanned_count']);
  final limit = _reportCount(meta['limit']);
  final more = meta['has_more'];
  final complete = meta['read_complete'];
  final state = meta['state'];
  if (raw is! List ||
      meta['resource_type'] != 'source_brief_job' ||
      returned != raw.length ||
      rejected == null ||
      scanned == null ||
      limit == null ||
      limit < 1 ||
      limit > 100 ||
      scanned > limit ||
      scanned != returned! + rejected ||
      complete is! bool ||
      !meta.containsKey('has_more')) {
    return null;
  }
  if (state == 'UNAVAILABLE') {
    if (returned != 0 ||
        scanned != 0 ||
        complete ||
        more != null ||
        _reportText(meta['reason']) == null) {
      return null;
    }
  } else {
    if (more is! bool ||
        complete != (!more && rejected == 0) ||
        state !=
            (!complete
                ? 'PARTIAL'
                : returned > 0
                ? 'READY'
                : 'EMPTY')) {
      return null;
    }
  }
  return Bmp09ArtifactRead(
    state: state as String,
    returnedCount: returned,
    rejectedCount: rejected,
    scannedCount: scanned,
    limit: limit,
    clientRejectedCount: 0,
    serverReadComplete: complete,
    hasMore: more as bool?,
  );
}

Bmp09SavedArtifact? _savedArtifact(Object? value) {
  final row = _asMap(value) ?? {};
  final id = _reportId(row['id']);
  final title = _reportText(row['title'], maxLength: 240);
  final kind = row['kind'];
  final version = _reportCount(row['version']);
  final hash = _reportHash(row['sha256']);
  final count = _reportCount(row['source_count']);
  if (row['resource_type'] != 'saved_work' ||
      id == null ||
      title == null ||
      !const {
        'research',
        'report',
        'podcast_episode',
        'delivery_preferences',
      }.contains(kind) ||
      version == null ||
      version < 1 ||
      hash == null ||
      count == null ||
      row['assessment'] != 'NOT_ESTABLISHED_BY_STORAGE') {
    return null;
  }
  return Bmp09SavedArtifact(
    id: id,
    title: title,
    kind: kind as String,
    version: version,
    sha256: hash,
    sourceCount: count,
    assessment: 'NOT_ESTABLISHED_BY_STORAGE',
  );
}

Bmp09SourceBriefArtifact? _sourceBriefArtifact(Object? value) {
  final row = _asMap(value) ?? {};
  final job = _reportJobId(row['job_id']);
  final hash = _reportHash(row['artifact_hash']);
  final count = _reportCount(row['source_count']);
  final rawEvaluations = row['evaluations'];
  final revision = _reportRevision(row['revision']);
  if (row['resource_type'] != 'source_brief_job' ||
      job == null ||
      hash == null ||
      count == null ||
      row['review_status'] != 'HUMAN_PENDING' ||
      !row.containsKey('revision') ||
      (row['revision'] != null && revision == null) ||
      (revision != null && revision.parentJobId == job) ||
      !const {'recorded', 'partial'}.contains(row['evaluation_state']) ||
      rawEvaluations is! List) {
    return null;
  }
  final evaluations = <Bmp09ReportEvaluation>[];
  final ids = <String, int>{};
  final metrics = <String, int>{};
  final parsed = rawEvaluations
      .map((value) => _reportEvaluation(value, job, hash))
      .toList();
  for (final evaluation in parsed.whereType<Bmp09ReportEvaluation>()) {
    ids[evaluation.id] = (ids[evaluation.id] ?? 0) + 1;
    metrics[evaluation.metricName] = (metrics[evaluation.metricName] ?? 0) + 1;
  }
  evaluations.addAll(
    parsed.whereType<Bmp09ReportEvaluation>().where(
      (item) =>
          ids[item.id] == 1 &&
          (!_requiredReportMetrics.contains(item.metricName) ||
              metrics[item.metricName] == 1),
    ),
  );
  final rejected = rawEvaluations.length - evaluations.length;
  final recorded =
      row['evaluation_state'] == 'recorded' &&
      rejected == 0 &&
      evaluations
          .map((item) => item.metricName)
          .toSet()
          .containsAll(_requiredReportMetrics);
  return Bmp09SourceBriefArtifact(
    jobId: job,
    artifactHash: hash,
    revision: revision,
    sourceCount: count,
    reviewStatus: 'HUMAN_PENDING',
    evaluationState: recorded ? 'recorded' : 'partial',
    evaluations: List.unmodifiable(evaluations),
    rejectedEvaluationCount: rejected,
  );
}

Bmp09ReportEvaluation? _reportEvaluation(
  Object? value,
  String job,
  String hash,
) {
  final row = _asMap(value) ?? {};
  final id = _reportHash(row['evaluation_id']);
  final metric = _reportId(row['metric_name']);
  final status = row['status'];
  final time = _reportText(row['evaluated_at']);
  final expected = 'daily_reports:$job:$hash';
  if (id == null ||
      metric == null ||
      time == null ||
      DateTime.tryParse(time) == null ||
      row['evidence_ref'] != expected ||
      (row.containsKey('resource_type') &&
          row['resource_type'] != 'source_brief_job') ||
      !const {'pass', 'warn', 'fail', 'unknown'}.contains(status)) {
    return null;
  }
  return Bmp09ReportEvaluation(
    id: id,
    metricName: metric,
    status: status as String,
    evaluatedAt: time,
    evidenceRef: expected,
  );
}

Bmp09SourceBriefRevision? _reportRevision(Object? value) {
  final row = _asMap(value);
  if (row == null) return null;
  final parent = _reportJobId(row['parent_job_id']);
  final hash = _reportHash(row['parent_artifact_hash']);
  final review = _reportHash(row['review_id']);
  final evidence = row['review_evidence_ref'];
  if (parent == null ||
      hash == null ||
      review == null ||
      evidence is! String ||
      evidence != evidence.trim() ||
      !RegExp(r'^app_evidence_records:[1-9][0-9]*$').hasMatch(evidence)) {
    return null;
  }
  return Bmp09SourceBriefRevision(
    parentJobId: parent,
    parentArtifactHash: hash,
    reviewId: review,
    reviewEvidenceRef: evidence,
  );
}

String? _reportJobId(Object? value) =>
    value is String &&
        value == value.trim() &&
        value.length <= 128 &&
        RegExp(r'^[A-Za-z0-9][A-Za-z0-9_-]{7,127}$').hasMatch(value)
    ? value
    : null;

int? _reportCount(Object? value) => value is int && value >= 0 ? value : null;
String? _reportHash(Object? value) =>
    value is String &&
        value.length == 64 &&
        RegExp(r'^[0-9a-f]{64}$').hasMatch(value)
    ? value
    : null;
String? _reportId(Object? value) =>
    value is String &&
        value == value.trim() &&
        value.length <= 120 &&
        RegExp(r'^[A-Za-z0-9][A-Za-z0-9._:-]*$').hasMatch(value)
    ? value
    : null;
String? _reportText(Object? value, {int maxLength = 120}) =>
    value is String &&
        value.isNotEmpty &&
        value == value.trim() &&
        value.length <= maxLength &&
        !RegExp(r'[\x00-\x1F<>]').hasMatch(value)
    ? value
    : null;
