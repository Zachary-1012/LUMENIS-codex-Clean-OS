class Sys01Snapshot {
  const Sys01Snapshot({
    required this.overall,
    required this.overallState,
    required this.registeredWorkers,
    required this.failedWorkers,
    required this.dlqTotal,
    required this.sampleTimestamp,
    required this.observationAvailable,
    required this.observationTraceId,
    required this.guardianName,
    required this.reaperRunning,
    required this.openBreakers,
    required this.registeredBreakers,
    required this.hasCompleteRuntimeSample,
  });

  final String? overall;
  final String overallState;
  final Sys01Count registeredWorkers;
  final Sys01Count failedWorkers;
  final Sys01Count dlqTotal;
  final String? sampleTimestamp;
  final bool observationAvailable;
  final String? observationTraceId;
  final String? guardianName;
  final bool? reaperRunning;
  final int? openBreakers;
  final int? registeredBreakers;
  final bool hasCompleteRuntimeSample;

  factory Sys01Snapshot.fromResponse(Map<String, dynamic> response) {
    if (response['ok'] != true || response['screen'] != 'SYS-01') {
      throw const FormatException('SYS-01 response identity is invalid.');
    }
    if (response['bound'] != true || response['source'] != 'runtime') {
      throw const FormatException('SYS-01 runtime binding is unavailable.');
    }

    final sections = _asMapList(response['sections']);
    final kpis = _findSection(sections, 'kpis');
    final runtime = _findSection(sections, 'runtime');
    final truth = _asMap(response['truth']);
    final observation = _asMap(response['runtime_observation']);
    if (kpis == null ||
        runtime == null ||
        truth == null ||
        observation == null) {
      throw const FormatException('SYS-01 runtime response is incomplete.');
    }
    if (observation['source'] != 'runtime_guardian.legacy_health_check' ||
        observation['boundary'] != 'read_only') {
      throw const FormatException('SYS-01 observation provenance is invalid.');
    }
    final observationState = _asString(observation['state']);
    if (observationState != 'ready' && observationState != 'unavailable') {
      throw const FormatException('SYS-01 observation state is invalid.');
    }
    final observationAvailable = observationState == 'ready';
    final observationTimestamp = observationAvailable
        ? _asString(observation['captured_at'])
        : null;
    final traceId = observationAvailable
        ? _asString(observation['trace_id'])
        : null;
    if (observationAvailable &&
        (observationTimestamp == null ||
            traceId == null ||
            !RegExp(r'^sys01rt-[a-f0-9]{24}$').hasMatch(traceId))) {
      throw const FormatException('SYS-01 observation trace is incomplete.');
    }

    final metrics = _asMapList(kpis['items']);
    final runtimeItems = _asMapList(runtime['items']);
    final overallRow = _findRuntimeItem(runtimeItems, '总体状态');
    final reaperRow = _findRuntimeItem(runtimeItems, 'reaper');
    final breakerRow = _findRuntimeItem(runtimeItems, '熔断器');
    final guardianRow = _findRuntimeItem(runtimeItems, 'guardian');

    final overall = _asString(truth['overall']);
    final completeSample =
        overall != null &&
        overall.toLowerCase() != 'unknown' &&
        observationTimestamp != null &&
        traceId != null;

    final reaperRunning =
        completeSample &&
            const {'ok', 'idle'}.contains(_runtimeState(reaperRow))
        ? _parseRunning(_runtimeDetail(reaperRow))
        : null;
    final breakerCounts =
        completeSample && _runtimeState(breakerRow) != 'offline'
        ? _parseBreakerCounts(_runtimeDetail(breakerRow))
        : null;
    final guardian = completeSample && _runtimeState(guardianRow) == 'ready'
        ? _runtimeDetail(guardianRow)
        : null;

    return Sys01Snapshot(
      overall: overall,
      overallState: _runtimeState(overallRow),
      registeredWorkers: _findMetric(metrics, 'sys01.workers_total'),
      failedWorkers: _findMetric(metrics, 'sys01.workers_failed'),
      dlqTotal: _findMetric(metrics, 'sys01.dlq'),
      sampleTimestamp: observationTimestamp,
      observationAvailable: observationAvailable,
      observationTraceId: traceId,
      guardianName: guardian,
      reaperRunning: reaperRunning,
      openBreakers: breakerCounts?.$1,
      registeredBreakers: breakerCounts?.$2,
      hasCompleteRuntimeSample: completeSample,
    );
  }
}

class Sys01Count {
  const Sys01Count({required this.value, required this.state});

  final int? value;
  final String state;
}

Sys01Count _findMetric(List<Map<String, Object?>> metrics, String id) {
  for (final metric in metrics) {
    if (metric['id'] != id) continue;
    final state = _asString(metric['state']) ?? 'notcollected';
    final rawValue = metric['value'];
    final value = state == 'ready' && rawValue is int && rawValue >= 0
        ? rawValue
        : null;
    return Sys01Count(value: value, state: state);
  }
  return const Sys01Count(value: null, state: 'notcollected');
}

String? _runtimeDetail(Map<String, Object?>? item) {
  final detail = _asString(item?['detail']);
  if (detail == null || detail == '—' || detail == '状态不可用') return null;
  return detail;
}

String _runtimeState(Map<String, Object?>? item) =>
    _asString(item?['state']) ?? 'offline';

bool? _parseRunning(String? detail) {
  if (detail == 'running=True') return true;
  if (detail == 'running=False') return false;
  return null;
}

(int, int)? _parseBreakerCounts(String? detail) {
  if (detail == null) return null;
  final open = RegExp(r'(?:^|\s)open=(\d+)(?:\s|$|·)').firstMatch(detail);
  final registered = RegExp(
    r'(?:^|\s)registered=(\d+)(?:\s|$|·)',
  ).firstMatch(detail);
  if (open == null || registered == null) return null;
  return (int.parse(open.group(1)!), int.parse(registered.group(1)!));
}

Map<String, Object?>? _findSection(
  List<Map<String, Object?>> sections,
  String type,
) {
  for (final section in sections) {
    if (section['type'] == type) return section;
  }
  return null;
}

Map<String, Object?>? _findRuntimeItem(
  List<Map<String, Object?>> items,
  String name,
) {
  for (final item in items) {
    if (item['name'] == name) return item;
  }
  return null;
}

Map<String, Object?>? _asMap(Object? value) {
  if (value is! Map) return null;
  return value.map((key, value) => MapEntry('$key', value));
}

List<Map<String, Object?>> _asMapList(Object? value) {
  if (value is! List) return const [];
  return value.map(_asMap).whereType<Map<String, Object?>>().toList();
}

String? _asString(Object? value) =>
    value is String && value.isNotEmpty ? value : null;
