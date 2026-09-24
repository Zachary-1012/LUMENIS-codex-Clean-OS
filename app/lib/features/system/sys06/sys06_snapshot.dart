import '../sys02/sys_system_foundation.dart';

class Sys06InstanceState {
  const Sys06InstanceState({required this.state});

  final String state;
}

class Sys06Snapshot {
  const Sys06Snapshot({
    required this.instances,
    required this.onlineCount,
    required this.capabilityCount,
    required this.instanceStates,
    required this.sourceAvailable,
  });

  final int? instances;
  final int? onlineCount;
  final int? capabilityCount;
  final List<Sys06InstanceState> instanceStates;
  final bool sourceAvailable;

  factory Sys06Snapshot.fromResponse(Map<String, dynamic> response) {
    _validateEnvelope(response);
    final sections = sysMapList(response['sections']);
    final kpis = sysSection(sections, 'kpis');
    final table = sysSection(sections, 'table');
    int? metric(String id) {
      for (final item in sysMapList(kpis?['items'])) {
        if (item['id'] == id &&
            (sysString(item['state']) ?? '').toLowerCase() == 'ready') {
          return sysInt(item['value']);
        }
      }
      return null;
    }

    final states = sysMapList(table?['rows'])
        .map((row) {
          return Sys06InstanceState(
            state: sysSafeDisplay(
              row['state'] ?? row['状态'],
              fallback: 'unknown',
            ),
          );
        })
        .toList(growable: false);
    return Sys06Snapshot(
      instances: metric('sys06.instances'),
      onlineCount: metric('sys06.online'),
      capabilityCount: metric('sys06.capabilities'),
      instanceStates: states,
      sourceAvailable: true,
    );
  }
}

void _validateEnvelope(Map<String, dynamic> response) {
  if (response['ok'] != true ||
      response['screen'] != 'SYS-06' ||
      response['bound'] != true ||
      response['source'] != 'runtime') {
    throw const FormatException('SYS-06 browser response identity is invalid.');
  }
}
