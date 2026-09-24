enum Ai04CatalogState { ready, empty, unavailable, blocked }

class Ai04SkillCapability {
  const Ai04SkillCapability({
    required this.skillId,
    required this.name,
    required this.description,
    required this.version,
    required this.owner,
    required this.category,
    required this.permissionLevel,
    required this.riskLevel,
    required this.executionPolicy,
    required this.evaluationStatus,
    required this.inputHint,
    required this.outputHint,
    required this.consumers,
    required this.evaluationEvidenceV2,
    required this.actorAccessGranted,
    required this.verified,
  });

  final String skillId;
  final String name;
  final String description;
  final String version;
  final String owner;
  final String category;
  final String permissionLevel;
  final String riskLevel;
  final String executionPolicy;
  final String evaluationStatus;
  final String inputHint;
  final String outputHint;
  final List<String> consumers;
  final bool evaluationEvidenceV2;
  final bool actorAccessGranted;
  final bool verified;

  bool get isReadOnly => executionPolicy == 'READ_ONLY';
  bool get canRunReadOnly =>
      isReadOnly && evaluationEvidenceV2 && actorAccessGranted;
}

class Ai04Snapshot {
  const Ai04Snapshot({
    required this.state,
    required this.skills,
    required this.rejectedCount,
    this.generatedAt,
  });

  final Ai04CatalogState state;
  final List<Ai04SkillCapability> skills;
  final int rejectedCount;
  final String? generatedAt;

  factory Ai04Snapshot.fromResponse(Map<String, dynamic> response) {
    if (response['ok'] != true) {
      throw const FormatException('AI-04 catalog response is not valid.');
    }
    final rawSkills = response['skills'];
    if (rawSkills is! List) {
      throw const FormatException('AI-04 catalog did not return a skill list.');
    }
    final skills = <Ai04SkillCapability>[];
    var rejected = 0;
    for (final item in rawSkills) {
      if (item is! Map) {
        rejected++;
        continue;
      }
      final skill = _parseSkill(
        item.map((key, value) => MapEntry('$key', value)),
      );
      if (skill == null || !skill.verified) {
        rejected++;
        continue;
      }
      skills.add(skill);
    }
    return Ai04Snapshot(
      state: skills.isEmpty ? Ai04CatalogState.empty : Ai04CatalogState.ready,
      skills: skills,
      rejectedCount: rejected,
      generatedAt: _safeText(response['generated_at']),
    );
  }
}

Ai04SkillCapability? _parseSkill(Map<String, dynamic> json) {
  final skillId = _safeId(json['skill_id']);
  final version = _safeVersion(json['version']);
  final name = _safeText(json['name']);
  final description = _safeText(json['description']);
  final category = _safeText(json['category']) ?? '共享能力';
  final permissionLevel = _known(json['permission_level'], const {
    'READ',
    'RESEARCH',
    'ANALYZE',
    'SUGGEST',
    'AUDIT',
    'PLAN',
    'APPROVAL_REQUIRED',
  });
  final riskLevel = _known(json['risk_level'], const {
    'LOW',
    'MEDIUM',
    'HIGH',
    'CRITICAL',
  });
  final executionPolicy = _known(json['execution_policy'], const {
    'READ_ONLY',
    'AUDIT_ONLY',
    'APPROVAL_REQUIRED',
    'AUTO_EXECUTE',
  });
  final evaluationStatus = _known(json['evaluation_status'], const {
    'PLANNED',
    'PARTIAL',
    'EVALUATED',
    'DEPRECATED',
  });
  final inputHint = _safeText(json['input_hint']);
  final outputHint = _safeText(json['output_hint']);
  final binding = _asMap(json['binding']);
  final evaluationEvidenceV2 = _validEvaluationEvidenceV2(
    _asMap(json['evaluation_evidence']),
    skillId: skillId,
    version: version,
  );
  final actorAccessGranted = _validActorAccess(
    _asMap(json['actor_access']),
    skillId: skillId,
  );
  final implementationState = _safeId(json['implementation_state']);
  final available = binding?['available'] == true;
  final verified =
      skillId != null &&
      version != null &&
      name != null &&
      description != null &&
      permissionLevel != null &&
      riskLevel != null &&
      executionPolicy != null &&
      evaluationStatus != null &&
      inputHint != null &&
      outputHint != null &&
      available &&
      implementationState != null &&
      implementationState.startsWith('BOUND_') &&
      evaluationStatus != 'DEPRECATED';
  if (!verified) return null;

  return Ai04SkillCapability(
    skillId: skillId,
    name: name,
    description: description,
    version: version,
    owner: _safeOwner(json['owner']),
    category: category,
    permissionLevel: permissionLevel,
    riskLevel: riskLevel,
    executionPolicy: executionPolicy,
    evaluationStatus: evaluationStatus,
    inputHint: inputHint,
    outputHint: outputHint,
    consumers: _safeConsumers(json['consumers']),
    evaluationEvidenceV2: evaluationEvidenceV2,
    actorAccessGranted: actorAccessGranted,
    verified: true,
  );
}

bool _validEvaluationEvidenceV2(
  Map<String, Object?>? evidence, {
  required String? skillId,
  required String? version,
}) {
  if (evidence == null ||
      skillId == null ||
      version == null ||
      evidence['evidence_version'] != 2 ||
      evidence['type'] != 'EVALUATION' ||
      evidence['canonical'] != true ||
      evidence['skill_id'] != skillId ||
      evidence['skill_version'] != version ||
      evidence['lineage_verified'] != true) {
    return false;
  }
  final evidenceId = _safeId(
    evidence['evidence_id'] ?? evidence['canonical_ref'],
  );
  final lineage = evidence['lineage'];
  final integrity = _asMap(evidence['integrity']);
  final integrityVersion =
      integrity?['version'] ?? evidence['integrity_version'];
  final integrityStatus = integrity?['status'] ?? evidence['integrity_status'];
  final integrityAlgorithm =
      integrity?['algorithm'] ?? evidence['integrity_algorithm'];
  final integrityDigest = integrity?['digest'] ?? evidence['integrity_digest'];
  return evidenceId != null &&
      lineage is List &&
      lineage.whereType<String>().isNotEmpty &&
      integrityVersion == 2 &&
      (integrity?['verified'] == true || integrityStatus == 'verified') &&
      (integrityAlgorithm == 'sha256' || integrityAlgorithm == 'hmac-sha256') &&
      _isDigest(integrityDigest);
}

bool _validActorAccess(
  Map<String, Object?>? access, {
  required String? skillId,
}) {
  final actor = _asMap(access?['actor']);
  return skillId != null &&
      actor?['bound'] == true &&
      actor?['source'] == 'server' &&
      _safeId(actor?['id']) != null &&
      access?['skill_id'] == skillId &&
      access?['read'] == true &&
      access?['decision'] == 'ALLOW';
}

Map<String, Object?>? _asMap(Object? value) {
  if (value is! Map) return null;
  return value.map((key, value) => MapEntry('$key', value));
}

String? _known(Object? value, Set<String> allowed) {
  final text = value is String ? value.trim().toUpperCase() : '';
  return allowed.contains(text) ? text : null;
}

String? _safeId(Object? value) {
  if (value is! String || value.trim().isEmpty || value.length > 100) {
    return null;
  }
  final text = value.trim();
  return RegExp(r'^[A-Za-z0-9_.:-]+$').hasMatch(text) ? text : null;
}

String? _safeVersion(Object? value) {
  if (value is! String || value.trim().isEmpty || value.length > 30) {
    return null;
  }
  final text = value.trim();
  return RegExp(r'^\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.-]+)?$').hasMatch(text)
      ? text
      : null;
}

String _safeOwner(Object? value) {
  final text = value is String ? value.trim().toLowerCase() : '';
  if (text.contains('shared capability')) return 'Shared Capability';
  return 'Registered capability';
}

List<String> _safeConsumers(Object? value) {
  if (value is! List) return const [];
  return value
      .whereType<String>()
      .map((item) => item.trim().toUpperCase())
      .where((item) => item == 'CTH' || item == 'BMP')
      .toSet()
      .toList(growable: false);
}

String? _safeText(Object? value) {
  if (value is! String || value.trim().isEmpty || value.length > 320) {
    return null;
  }
  final text = value.trim();
  final lower = text.toLowerCase();
  if (text.contains(RegExp(r'[\r\n\x00]')) ||
      text.contains('/') ||
      text.contains('\\') ||
      lower.contains('token') ||
      lower.contains('secret') ||
      lower.contains('password') ||
      lower.contains('provider=') ||
      lower.contains('model=') ||
      lower.contains('http://') ||
      lower.contains('https://')) {
    return null;
  }
  return text;
}

bool _isDigest(Object? value) =>
    value is String && RegExp(r'^[0-9a-f]{64}$').hasMatch(value);
