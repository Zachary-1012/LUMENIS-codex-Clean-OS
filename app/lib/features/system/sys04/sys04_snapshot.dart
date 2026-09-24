import '../sys02/sys_system_foundation.dart';

class Sys04PermissionRow {
  const Sys04PermissionRow({
    required this.level,
    required this.scope,
    required this.state,
  });

  final String level;
  final String scope;
  final String state;
}

class Sys04Snapshot {
  const Sys04Snapshot({
    required this.rows,
    required this.operationCount,
    required this.auditAvailable,
    required this.sourceAvailable,
  });

  final List<Sys04PermissionRow> rows;
  final int? operationCount;
  final bool auditAvailable;
  final bool sourceAvailable;

  factory Sys04Snapshot.fromResponse(Map<String, dynamic> response) {
    _validateEnvelope(response);
    final sections = sysMapList(response['sections']);
    final table = sysSection(sections, 'table');
    final truth = sysMap(response['truth']);
    final operations = truth['operation_types'];
    final operationCount = operations is List ? operations.length : null;
    final auditAvailable = truth['audit_available'] == true;
    final rows = sysMapList(table?['rows'])
        .map((row) {
          return Sys04PermissionRow(
            level: _safePermissionLevel(
              row['权限级别'] ?? row['level'] ?? row['name'],
            ),
            scope: _safeScope(row['范围'] ?? row['scope']),
            state: (sysString(row['state']) ?? 'ready').toLowerCase(),
          );
        })
        .toList(growable: false);
    return Sys04Snapshot(
      rows: rows,
      operationCount: operationCount,
      auditAvailable: auditAvailable,
      sourceAvailable: true,
    );
  }
}

String _safePermissionLevel(Object? value) {
  final text = sysString(value)?.toUpperCase();
  return switch (text) {
    'READ' || 'TASK' || 'AUDIT' || 'WRITE' || 'DEPLOY' => text!,
    _ => 'UNKNOWN',
  };
}

String _safeScope(Object? value) {
  final text = sysString(value)?.toUpperCase();
  return switch (text) {
    'CONTROLLED' || 'READ/TASK/AUDIT/WRITE/DEPLOY' => 'CONTROLLED',
    _ => 'UNKNOWN',
  };
}

void _validateEnvelope(Map<String, dynamic> response) {
  if (response['ok'] != true ||
      response['screen'] != 'SYS-04' ||
      response['bound'] != true ||
      response['source'] != 'runtime') {
    throw const FormatException(
      'SYS-04 permission response identity is invalid.',
    );
  }
}
