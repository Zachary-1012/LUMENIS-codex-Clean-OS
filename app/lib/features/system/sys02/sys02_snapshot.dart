import 'sys_system_foundation.dart';

class Sys02Metric {
  const Sys02Metric({
    required this.id,
    required this.label,
    required this.value,
    required this.state,
  });

  final String id;
  final String label;
  final int? value;
  final String state;
}

class Sys02CollectorLane {
  const Sys02CollectorLane({
    required this.platform,
    required this.status,
    required this.parsedRecords,
    required this.detail,
  });

  final String platform;
  final String status;
  final int? parsedRecords;
  final String detail;
}

class Sys02Snapshot {
  const Sys02Snapshot({
    required this.metrics,
    required this.collectors,
    required this.note,
    required this.sourceAvailable,
  });

  final List<Sys02Metric> metrics;
  final List<Sys02CollectorLane> collectors;
  final String? note;
  final bool sourceAvailable;

  factory Sys02Snapshot.fromResponse(Map<String, dynamic> response) {
    _validateEnvelope(response);
    final sections = sysMapList(response['sections']);
    final kpis = sysSection(sections, 'kpis');
    final table = sysSection(sections, 'table');
    final noteSection = sysSection(sections, 'note');

    final metrics = sysMapList(kpis?['items'])
        .map((item) {
          final state = (sysString(item['state']) ?? 'unknown').toLowerCase();
          return Sys02Metric(
            id: sysString(item['id']) ?? 'sys02.unknown',
            label: sysSafeDisplay(item['title'], fallback: '—'),
            value: state == 'ready' ? sysInt(item['value']) : null,
            state: state,
          );
        })
        .toList(growable: false);

    final collectors = sysMapList(table?['rows'])
        .map((row) {
          final status = sysSafeDisplay(
            row['状态'] ?? row['status'] ?? row['state'],
            fallback: 'unknown',
          );
          return Sys02CollectorLane(
            platform: sysSafeDisplay(
              row['平台'] ?? row['platform'] ?? row['name'],
              fallback: '—',
            ),
            status: status,
            parsedRecords: sysInt(row['解析记录'] ?? row['records_parsed']),
            detail: sysSafeDisplay(
              row['说明'] ?? row['detail'] ?? row['error'],
              fallback: '—',
            ),
          );
        })
        .toList(growable: false);

    return Sys02Snapshot(
      metrics: metrics,
      collectors: collectors,
      note: sysSafeDisplay(noteSection?['text'], fallback: ''),
      sourceAvailable:
          response['bound'] == true && response['source'] == 'runtime',
    );
  }
}

void _validateEnvelope(Map<String, dynamic> response) {
  if (response['ok'] != true ||
      response['screen'] != 'SYS-02' ||
      response['bound'] != true ||
      response['source'] != 'runtime') {
    throw const FormatException(
      'SYS-02 collector response identity is invalid.',
    );
  }
}
