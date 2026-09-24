import '../sys02/sys_system_foundation.dart';

class Sys08LogFile {
  const Sys08LogFile({
    required this.name,
    required this.sizeMb,
    required this.modified,
  });

  final String name;
  final double? sizeMb;
  final String modified;
}

class Sys08LogRecord {
  const Sys08LogRecord({
    required this.time,
    required this.level,
    required this.module,
    required this.message,
    required this.trace,
  });

  final String time;
  final String level;
  final String module;
  final String message;
  final String trace;
}

class Sys08Snapshot {
  const Sys08Snapshot({
    required this.files,
    required this.records,
    required this.totalFiles,
    required this.totalSizeMb,
    required this.sourceAvailable,
  });

  final List<Sys08LogFile> files;
  final List<Sys08LogRecord> records;
  final int? totalFiles;
  final double? totalSizeMb;
  final bool sourceAvailable;

  factory Sys08Snapshot.fromResponse(Map<String, dynamic> response) {
    _validateEnvelope(response);
    final sections = sysMapList(response['sections']);
    final kpis = sysMapList(sysSection(sections, 'kpis')?['items']);
    final table = sysSection(sections, 'table');
    final files = sysMapList(table?['rows'])
        .map((row) {
          return Sys08LogFile(
            name: sysSafeDisplay(row['文件'] ?? row['name']),
            sizeMb: _doubleOrNull(row['大小MB'] ?? row['size_mb']),
            modified: sysSafeDisplay(row['修改'] ?? row['modified']),
          );
        })
        .toList(growable: false);
    final records = <Sys08LogRecord>[];
    for (final section in sections) {
      final type = sysString(section['type'])?.toLowerCase();
      if (type != 'logs' && type != 'log_records' && type != 'entries') {
        continue;
      }
      for (final row in sysMapList(section['rows'])) {
        records.add(
          Sys08LogRecord(
            time: sysSafeDisplay(row['time'] ?? row['timestamp']),
            level: sysSafeDisplay(row['level']),
            module: sysSafeDisplay(row['module']),
            message: sysSafeDisplay(row['message']),
            trace: sysSafeDisplay(row['trace_id'] ?? row['trace']),
          ),
        );
      }
    }
    return Sys08Snapshot(
      files: files,
      records: List.unmodifiable(records),
      totalFiles: _metricInt(kpis, 'sys08.files'),
      totalSizeMb: _metricDouble(kpis, 'sys08.size_mb'),
      sourceAvailable: true,
    );
  }
}

double? _doubleOrNull(Object? value) {
  if (value is num && value >= 0) return value.toDouble();
  if (value is String) return double.tryParse(value);
  return null;
}

int? _metricInt(List<Map<String, Object?>> items, String id) {
  for (final item in items) {
    if (item['id'] == id &&
        (sysString(item['state']) ?? '').toLowerCase() == 'ready') {
      return sysInt(item['value']);
    }
  }
  return null;
}

double? _metricDouble(List<Map<String, Object?>> items, String id) {
  for (final item in items) {
    if (item['id'] == id &&
        (sysString(item['state']) ?? '').toLowerCase() == 'ready') {
      return _doubleOrNull(item['value']);
    }
  }
  return null;
}

void _validateEnvelope(Map<String, dynamic> response) {
  if (response['ok'] != true ||
      response['screen'] != 'SYS-08' ||
      response['bound'] != true ||
      response['source'] != 'runtime') {
    throw const FormatException(
      'SYS-08 observability response identity is invalid.',
    );
  }
}
