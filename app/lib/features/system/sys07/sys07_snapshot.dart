import '../sys02/sys_system_foundation.dart';

class Sys07Check {
  const Sys07Check({
    required this.name,
    required this.evidence,
    required this.state,
  });

  final String name;
  final String evidence;
  final String state;
}

class Sys07Gate {
  const Sys07Gate({
    required this.name,
    required this.evidence,
    required this.evidenceValid,
    required this.state,
  });

  final String name;
  final String evidence;
  final bool evidenceValid;
  final String state;
}

class Sys07Snapshot {
  const Sys07Snapshot({
    required this.checks,
    required this.gates,
    required this.owaspCheckCount,
    required this.skillCount,
    required this.sourceAvailable,
  });

  final List<Sys07Check> checks;
  final List<Sys07Gate> gates;
  final int? owaspCheckCount;
  final int? skillCount;
  final bool sourceAvailable;

  bool get hasReturnedChecks => checks.isNotEmpty;

  bool get hasCompleteGateEvidence {
    if (gates.isEmpty) return false;
    return gates.every((gate) {
      final state = gate.state.toLowerCase();
      return gate.evidenceValid &&
          (state == 'ready' ||
              state == 'pass' ||
              state == 'passed' ||
              state == 'verified');
    });
  }

  factory Sys07Snapshot.fromResponse(Map<String, dynamic> response) {
    _validateEnvelope(response);
    final sections = sysMapList(response['sections']);
    final kpis = sysMapList(sysSection(sections, 'kpis')?['items']);
    final table = sysSection(sections, 'table');
    final checks = sysMapList(table?['rows'])
        .map((row) {
          return Sys07Check(
            name: sysSafeDisplay(row['防护项'] ?? row['check'] ?? row['name']),
            evidence: sysSafeDisplay(
              row['参考'] ?? row['evidence'] ?? row['evidence_ref'],
            ),
            state: _safeCheckState(row['state']),
          );
        })
        .toList(growable: false);
    final gates = <Sys07Gate>[];
    for (final section in sections) {
      final type = sysString(section['type'])?.toLowerCase();
      if (type != 'gate' && type != 'gates' && type != 'acceptance') continue;
      for (final row in sysMapList(section['rows'])) {
        final evidence = _parseCanonicalEvidenceV2(
          row['evidence'] ??
              row['canonical_evidence'] ??
              row['evidence_ref'] ??
              row['reference'],
        );
        gates.add(
          Sys07Gate(
            name: sysSafeDisplay(row['name'] ?? row['gate'] ?? row['title']),
            evidence: evidence?.evidenceId ?? '—',
            evidenceValid: evidence != null,
            state: _safeGateState(row['state'], evidence != null),
          ),
        );
      }
    }
    return Sys07Snapshot(
      checks: checks,
      gates: List.unmodifiable(gates),
      owaspCheckCount: _metricValue(kpis, 'sys07.owasp_checks'),
      skillCount: _metricValue(kpis, 'sys07.skills'),
      sourceAvailable: true,
    );
  }
}

String _safeCheckState(Object? value) {
  final state = (sysString(value) ?? 'unknown').toLowerCase();
  return switch (state) {
    'ready' || 'ok' || 'pass' || 'passed' || 'success' || 'verified' => state,
    'blocked' || 'denied' => 'blocked',
    'offline' => 'offline',
    'error' || 'failed' => 'error',
    'pending' || 'scheduled' => 'pending',
    _ => 'unknown',
  };
}

String _safeGateState(Object? value, bool evidenceValid) {
  final state = (sysString(value) ?? 'unknown').toLowerCase();
  final safeState = switch (state) {
    'ready' || 'ok' || 'pass' || 'passed' || 'success' || 'verified' => state,
    'blocked' || 'denied' => 'blocked',
    'offline' => 'offline',
    'error' || 'failed' => 'error',
    'pending' || 'scheduled' => 'pending',
    _ => 'unknown',
  };
  final passState =
      safeState == 'ready' ||
      safeState == 'ok' ||
      safeState == 'pass' ||
      safeState == 'passed' ||
      safeState == 'success' ||
      safeState == 'verified';
  return passState && !evidenceValid ? 'unknown' : safeState;
}

class _CanonicalEvidenceV2 {
  const _CanonicalEvidenceV2({required this.evidenceId});

  final String evidenceId;
}

_CanonicalEvidenceV2? _parseCanonicalEvidenceV2(Object? raw) {
  final payload = sysMap(raw);
  if (payload.isEmpty) return null;

  final version = payload['version'] ??
      payload['schema_version'] ??
      payload['evidence_version'];
  if (!_isV2(version)) return null;

  final type = sysString(payload['type'] ?? payload['kind'])?.toUpperCase();
  final canonical = payload['canonical'] == true ||
      type == 'CANONICAL' ||
      type == 'CANONICAL_EVIDENCE' ||
      type == 'CANONICAL_DATA';
  if (!canonical || !_isKnownCanonicalEvidenceType(type)) return null;

  final evidenceId = sysString(
    payload['evidence_id'] ?? payload['canonical_ref'] ?? payload['id'],
  );
  if (evidenceId == null || !_isNamespacedId(evidenceId, 'EV')) return null;
  if (sysSafeDisplay(evidenceId) == '—') return null;

  final integrity = sysMap(payload['integrity']);
  final integrityVersion = integrity['version'] ??
      integrity['integrity_version'] ??
      payload['integrity_version'];
  final algorithm = sysString(
    integrity['algorithm'] ??
        integrity['hash_algorithm'] ??
        payload['integrity_algorithm'],
  )?.toLowerCase();
  final digest = sysString(
    integrity['digest'] ??
        integrity['hash'] ??
        payload['integrity_digest'],
  )?.toLowerCase();
  final integrityStatus = sysString(
    integrity['status'] ??
        integrity['state'] ??
        payload['integrity_status'],
  )?.toLowerCase();
  final integrityValid = _isV2(integrityVersion) &&
      integrity['verified'] == true &&
      (integrityStatus == 'verified' ||
          integrityStatus == 'valid' ||
          integrityStatus == 'passed') &&
      (algorithm == 'sha256' ||
          algorithm == 'sha-256' ||
          algorithm == 'hmac-sha256') &&
      digest != null &&
      RegExp(r'^[0-9a-f]{64}$').hasMatch(digest) &&
      (!integrity.containsKey('tampered') || integrity['tampered'] == false) &&
      (!integrity.containsKey('match') || integrity['match'] == true) &&
      (!integrity.containsKey('valid') || integrity['valid'] == true);
  if (!integrityValid) return null;

  if (!_hasValidLineage(payload)) return null;

  final verification = sysMap(payload['verification']);
  final explicitVerification = verification.isNotEmpty
      ? verification['verified'] == true &&
          _isPassState(verification['state'] ?? verification['status'])
      : payload['scope_verified'] == true &&
          payload['lineage_verified'] == true;
  if (!explicitVerification) return null;

  final readPolicy = sysMap(
    payload['read_policy'] ?? payload['readPolicy'],
  );
  final readMode = sysString(readPolicy['mode'])?.toLowerCase();
  final readScope = sysString(
    readPolicy['scope'] ?? readPolicy['actor_scope'],
  );
  final readPolicyValid = readPolicy['allowed'] == true &&
      readMode == 'read' &&
      readScope != null &&
      readScope.isNotEmpty;

  final permission = sysMap(payload['permission']);
  final canonicalReadValid = payload['read_allowed'] == true &&
      permission['read'] == true &&
      sysString(permission['decision'])?.toUpperCase() == 'ALLOW';
  if (!readPolicyValid && !canonicalReadValid) return null;

  return _CanonicalEvidenceV2(evidenceId: evidenceId);
}

bool _isV2(Object? value) =>
    value == 2 || sysString(value)?.toLowerCase() == 'v2';

bool _isKnownCanonicalEvidenceType(String? type) => switch (type) {
  'COMMENT' ||
  'CLUSTER' ||
  'FINDING' ||
  'METRIC' ||
  'RISK' ||
  'SOURCE' ||
  'CANONICAL' ||
  'CANONICAL_EVIDENCE' ||
  'CANONICAL_DATA' => true,
  _ => false,
};

bool _isPassState(Object? value) {
  final state = sysString(value)?.toLowerCase();
  return state == 'ready' ||
      state == 'ok' ||
      state == 'pass' ||
      state == 'passed' ||
      state == 'success' ||
      state == 'verified' ||
      state == 'valid';
}

bool _hasValidLineage(Map<String, Object?> payload) {
  final lineage = payload['lineage'];
  if (lineage is List) {
    if (payload['lineage_verified'] != true || lineage.length < 3) {
      return false;
    }
    return lineage.every((item) {
      final value = sysString(item);
      return value != null &&
          value.length <= 100 &&
          RegExp(r'^[A-Za-z][A-Za-z0-9 _:-]*$').hasMatch(value);
    });
  }

  final lineageMap = sysMap(lineage);
  final sourceId = sysString(
    lineageMap['source_id'] ?? lineageMap['source'],
  );
  final canonicalId = sysString(
    lineageMap['canonical_id'] ?? lineageMap['canonical'],
  );
  final lineageId = sysString(lineageMap['lineage_id'] ?? lineageMap['id']);
  final path = lineageMap['path'] ?? lineageMap['chain'];
  final lineagePath = path is List
      ? path.map(sysString).toList(growable: false)
      : const <String?>[];
  if (lineageMap['verified'] != true &&
      payload['lineage_verified'] != true) {
    return false;
  }
  final evidenceId = sysString(
    payload['evidence_id'] ?? payload['canonical_ref'] ?? payload['id'],
  );
  return sourceId != null &&
      canonicalId != null &&
      evidenceId != null &&
      lineageId != null &&
      _isNamespacedId(sourceId, 'SRC') &&
      _isNamespacedId(canonicalId, 'CAN') &&
      _isNamespacedId(lineageId, 'LIN') &&
      lineagePath.length >= 3 &&
      lineagePath.every((item) => item != null) &&
      lineagePath.contains(sourceId) &&
      lineagePath.contains(evidenceId) &&
      lineagePath.contains(canonicalId);
}

bool _isNamespacedId(String value, String namespace) {
  final match = RegExp(
    '^${RegExp.escape(namespace)}(?:[-_:])[A-Za-z0-9][A-Za-z0-9._:-]*',
  ).firstMatch(value);
  return match?.group(0) == value;
}

int? _metricValue(List<Map<String, Object?>> items, String id) {
  for (final item in items) {
    if (item['id'] == id &&
        (sysString(item['state']) ?? '').toLowerCase() == 'ready') {
      return sysInt(item['value']);
    }
  }
  return null;
}

void _validateEnvelope(Map<String, dynamic> response) {
  if (response['ok'] != true ||
      response['screen'] != 'SYS-07' ||
      response['bound'] != true ||
      response['source'] != 'runtime') {
    throw const FormatException(
      'SYS-07 evaluation response identity is invalid.',
    );
  }
}
