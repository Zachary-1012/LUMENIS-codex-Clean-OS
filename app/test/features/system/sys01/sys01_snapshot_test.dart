import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/features/system/sys01/sys01_repository.dart';
import 'package:lumenis_app/features/system/sys01/sys01_snapshot.dart';

void main() {
  test('repository reads the existing SYS-01 screen endpoint', () async {
    final client = _RecordingCoreClient(_response());
    final snapshot = await CoreSys01Repository(client: client).load();

    expect(client.requestedScreen, 'SYS-01');
    expect(snapshot.registeredWorkers.value, 3);
  });

  test('keeps ready zero counts and parses live RuntimeGuardian fields', () {
    final snapshot = Sys01Snapshot.fromResponse(
      _response(
        overall: 'healthy',
        workersTotal: 0,
        workersFailed: 2,
        dlqTotal: 0,
        breakerDetail: 'open=2 · registered=5',
      ),
    );

    expect(snapshot.overall, 'healthy');
    expect(snapshot.registeredWorkers.value, 0);
    expect(snapshot.failedWorkers.value, 2);
    expect(snapshot.dlqTotal.value, 0);
    expect(snapshot.hasCompleteRuntimeSample, isTrue);
    expect(snapshot.reaperRunning, isTrue);
    expect(snapshot.openBreakers, 2);
    expect(snapshot.registeredBreakers, 5);
    expect(snapshot.guardianName, 'legacy');
    expect(snapshot.sampleTimestamp, '2026-09-20T09:30:00Z');
    expect(snapshot.observationAvailable, isTrue);
    expect(snapshot.observationTraceId, 'sys01rt-0123456789abcdef01234567');
  });

  test('does not turn offline and null metrics into zero', () {
    final response = _response(
      overall: 'healthy',
      workersTotal: 0,
      workersTotalState: 'offline',
      workersFailed: null,
      dlqTotal: 0,
      dlqState: 'offline',
    );
    final snapshot = Sys01Snapshot.fromResponse(response);

    expect(snapshot.registeredWorkers.value, isNull);
    expect(snapshot.failedWorkers.value, isNull);
    expect(snapshot.dlqTotal.value, isNull);
  });

  test('does not accept a boolean as a worker count', () {
    final snapshot = Sys01Snapshot.fromResponse(_response(workersTotal: true));

    expect(snapshot.registeredWorkers.value, isNull);
  });

  test(
    'masks normalized runtime defaults when the source sample is incomplete',
    () {
      final snapshot = Sys01Snapshot.fromResponse(
        _response(
          overall: null,
          timestamp: '状态不可用',
          reaperDetail: 'running=False',
          breakerDetail: 'open=0 · registered=0',
        ),
      );

      expect(snapshot.hasCompleteRuntimeSample, isFalse);
      expect(snapshot.sampleTimestamp, isNull);
      expect(snapshot.observationAvailable, isFalse);
      expect(snapshot.observationTraceId, isNull);
      expect(snapshot.reaperRunning, isNull);
      expect(snapshot.openBreakers, isNull);
      expect(snapshot.registeredBreakers, isNull);
      expect(snapshot.guardianName, isNull);
      expect(snapshot.registeredWorkers.value, 3);
    },
  );

  test('rejects a response for a different screen or an unbound source', () {
    expect(
      () => Sys01Snapshot.fromResponse(_response()..['screen'] = 'AI-01'),
      throwsFormatException,
    );
    expect(
      () => Sys01Snapshot.fromResponse(_response()..['bound'] = false),
      throwsFormatException,
    );
  });
}

class _RecordingCoreClient extends LumenisCoreClient {
  _RecordingCoreClient(this.response);

  final Map<String, dynamic> response;
  String? requestedScreen;

  @override
  Future<Map<String, dynamic>> screen(String screenId) async {
    requestedScreen = screenId;
    return response;
  }
}

Map<String, dynamic> _response({
  String? overall = 'healthy',
  String timestamp = '2026-09-20T09:30:00Z',
  String reaperDetail = 'running=True',
  String breakerDetail = 'open=0 · registered=5',
  Object? workersTotal = 3,
  String workersTotalState = 'ready',
  Object? workersFailed = 0,
  String workersFailedState = 'ready',
  Object? dlqTotal = 0,
  String dlqState = 'ready',
}) {
  return {
    'ok': true,
    'screen': 'SYS-01',
    'source': 'runtime',
    'bound': true,
    'generated_at': '2026-09-20T09:31:00Z',
    'runtime_observation': {
      'state': overall != null && timestamp != '状态不可用'
          ? 'ready'
          : 'unavailable',
      'source': 'runtime_guardian.legacy_health_check',
      'captured_at': overall != null && timestamp != '状态不可用' ? timestamp : null,
      'trace_id': overall != null && timestamp != '状态不可用'
          ? 'sys01rt-0123456789abcdef01234567'
          : null,
      'boundary': 'read_only',
    },
    'truth': {'overall': overall},
    'sections': [
      {
        'type': 'kpis',
        'items': [
          {
            'id': 'sys01.workers_total',
            'value': workersTotal,
            'state': workersTotalState,
          },
          {
            'id': 'sys01.workers_failed',
            'value': workersFailed,
            'state': workersFailedState,
          },
          {'id': 'sys01.dlq', 'value': dlqTotal, 'state': dlqState},
        ],
      },
      {
        'type': 'runtime',
        'items': [
          {
            'name': '总体状态',
            'state': overall == null ? 'offline' : 'ok',
            'detail': overall ?? 'unknown',
          },
          {'name': 'reaper', 'state': 'ok', 'detail': reaperDetail},
          {'name': '熔断器', 'state': 'ok', 'detail': breakerDetail},
          {'name': 'guardian', 'state': 'ready', 'detail': 'legacy'},
          {'name': '时间戳', 'state': 'ready', 'detail': timestamp},
        ],
      },
    ],
  };
}
