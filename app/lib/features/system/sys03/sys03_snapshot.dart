import '../sys02/sys_system_foundation.dart';

class Sys03Check {
  const Sys03Check({
    required this.name,
    required this.result,
    required this.state,
  });

  final String name;
  final String result;
  final String state;
}

class Sys03TruthStage {
  const Sys03TruthStage({
    required this.name,
    required this.state,
    required this.detail,
  });

  final String name;
  final String state;
  final String detail;
}

class Sys03Snapshot {
  const Sys03Snapshot({
    required this.schemaVersions,
    required this.schemaState,
    required this.checks,
    required this.truthStages,
    required this.integrityState,
    required this.readabilityState,
    required this.identityState,
  });

  final int? schemaVersions;
  final String schemaState;
  final List<Sys03Check> checks;
  final List<Sys03TruthStage> truthStages;
  final String integrityState;
  final String readabilityState;
  final String identityState;

  factory Sys03Snapshot.fromResponse(Map<String, dynamic> response) {
    _validateEnvelope(response);
    final sections = sysMapList(response['sections']);
    final kpis = sysSection(sections, 'kpis');
    final table = sysSection(sections, 'table');
    final truth = sysMap(response['truth']);
    final schemaMetric = sysMapList(
      kpis?['items'],
    ).where((item) => item['id'] == 'sys03.schema_versions').firstOrNull;
    final schemaState = (sysString(schemaMetric?['state']) ?? 'unknown')
        .toLowerCase();
    final schemaVersions = schemaState == 'ready'
        ? sysInt(schemaMetric?['value'])
        : null;

    final checks = sysMapList(table?['rows'])
        .map((row) {
          final state = _verifiedCheckState(row);
          return Sys03Check(
            name: sysSafeDisplay(
              row['检查项'] ?? row['check'] ?? row['name'],
              fallback: '—',
            ),
            result: sysSafeDisplay(
              row['结果'] ?? row['result'] ?? row['detail'],
              fallback: '—',
            ),
            state: state,
          );
        })
        .toList(growable: false);

    final truthStages = _readTruthStages(truth, sections);
    final identity = sysMap(truth['db_identity']);
    final identityState = identity.isEmpty
        ? 'unknown'
        : (sysString(identity['state']) ?? 'ready').toLowerCase();
    final integrityState = _integrityState(checks);
    final readability =
        sysString(truth['application_readability']) ??
        sysString(truth['readability_state']);

    return Sys03Snapshot(
      schemaVersions: schemaVersions,
      schemaState: schemaState,
      checks: checks,
      truthStages: truthStages,
      integrityState: integrityState,
      readabilityState: (readability ?? 'notreturned').toLowerCase(),
      identityState: identityState,
    );
  }
}

String _verifiedCheckState(Map<String, Object?> row) {
  final rawState = (sysString(row['state'] ?? row['status']) ?? '')
      .toLowerCase();
  final passState = {'ready', 'ok', 'pass', 'passed', 'success', 'verified'};
  final explicitlyPass = passState.contains(rawState);
  final canonicalVerified =
      row['canonical_verified'] == true ||
      row['verified'] == true ||
      row['is_verified'] == true;
  final evidenceReference = _evidenceReference(row);

  if (explicitlyPass) {
    return canonicalVerified && evidenceReference != null ? 'ready' : 'unknown';
  }

  return switch (rawState) {
    'blocked' || 'denied' => 'blocked',
    'offline' => 'offline',
    'error' || 'failed' => 'error',
    'pending' || 'scheduled' => 'pending',
    'notcollected' ||
    'not_collected' ||
    'notreturned' ||
    'not_returned' => 'notcollected',
    _ => 'unknown',
  };
}

String? _evidenceReference(Map<String, Object?> row) {
  final direct = sysString(
    row['evidence_ref'] ?? row['evidence_id'] ?? row['evidence'],
  );
  if (direct != null) return direct;
  final evidence = sysMap(row['evidence']);
  return sysString(evidence['id'] ?? evidence['ref'] ?? evidence['reference']);
}

String _integrityState(List<Sys03Check> checks) {
  if (checks.isEmpty) return 'notcollected';
  if (checks.every((check) => check.state == 'ready')) return 'ready';
  if (checks.any((check) => check.state == 'blocked')) return 'blocked';
  if (checks.any((check) => check.state == 'offline')) return 'offline';
  if (checks.any((check) => check.state == 'error')) return 'error';
  if (checks.any((check) => check.state == 'pending')) return 'pending';
  return 'unknown';
}

List<Sys03TruthStage> _readTruthStages(
  Map<String, Object?> truth,
  List<Map<String, Object?>> sections,
) {
  final raw = truth['truth_chain'] ?? truth['chain'];
  final truthItems = sysMapList(raw);
  final section =
      sysSection(sections, 'timeline') ?? sysSection(sections, 'truth_chain');
  final items = truthItems.isNotEmpty
      ? truthItems
      : sysMapList(section?['items']);
  return items
      .map((item) {
        return Sys03TruthStage(
          name: sysSafeDisplay(
            item['stage'] ?? item['name'] ?? item['label'],
            fallback: '—',
          ),
          state: (sysString(item['state']) ?? 'unknown').toLowerCase(),
          detail: sysSafeDisplay(
            item['detail'] ?? item['result'],
            fallback: '—',
          ),
        );
      })
      .toList(growable: false);
}

void _validateEnvelope(Map<String, dynamic> response) {
  if (response['ok'] != true ||
      response['screen'] != 'SYS-03' ||
      response['bound'] != true ||
      response['source'] != 'runtime') {
    throw const FormatException(
      'SYS-03 database response identity is invalid.',
    );
  }
}
