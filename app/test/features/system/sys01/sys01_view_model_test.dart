import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/features/system/sys01/sys01_repository.dart';
import 'package:lumenis_app/features/system/sys01/sys01_snapshot.dart';
import 'package:lumenis_app/features/system/sys01/sys01_view_model.dart';

void main() {
  test('keeps authentication and permission denial distinct', () async {
    final repository = _FakeSys01Repository(
      failures: [
        const LumenisCoreException('GET /screen failed with HTTP 401'),
        const LumenisCoreException('GET /screen failed with HTTP 403'),
      ],
    );
    final viewModel = Sys01ViewModel(repository: repository);
    addTearDown(viewModel.dispose);

    await viewModel.refresh();
    expect(viewModel.failureKind, Sys01FailureKind.authentication);

    await viewModel.refresh();
    expect(viewModel.failureKind, Sys01FailureKind.permissionDenied);
  });

  test('classifies wrapped Core unavailability as offline', () async {
    final viewModel = Sys01ViewModel(
      repository: _FakeSys01Repository(
        failures: [
          const LumenisCoreException(
            'LUMENIS Core unavailable at http://127.0.0.1:8201: refused',
          ),
        ],
      ),
    );
    addTearDown(viewModel.dispose);

    await viewModel.refresh();

    expect(viewModel.phase, Sys01LoadPhase.failed);
    expect(viewModel.failureKind, Sys01FailureKind.offline);
    expect(viewModel.snapshot, isNull);
  });

  test(
    'classifies malformed response as response failure and clears old data',
    () async {
      final viewModel = Sys01ViewModel(
        repository: _FakeSys01Repository(
          snapshot: _readySnapshot(),
          failures: [null, const FormatException('bad envelope')],
        ),
      );
      addTearDown(viewModel.dispose);

      await viewModel.refresh();
      expect(viewModel.snapshot, isNotNull);

      await viewModel.refresh();
      expect(viewModel.phase, Sys01LoadPhase.failed);
      expect(viewModel.failureKind, Sys01FailureKind.response);
      expect(viewModel.snapshot, isNull);
    },
  );

  test('classifies a raw socket failure as offline', () async {
    final viewModel = Sys01ViewModel(
      repository: _FakeSys01Repository(
        failures: [const SocketException('connection refused')],
      ),
    );
    addTearDown(viewModel.dispose);

    await viewModel.refresh();

    expect(viewModel.failureKind, Sys01FailureKind.offline);
  });
}

class _FakeSys01Repository implements Sys01Repository {
  _FakeSys01Repository({this.snapshot, this.failures = const []});

  final Sys01Snapshot? snapshot;
  final List<Object?> failures;
  int _index = 0;

  @override
  Future<Sys01Snapshot> load() async {
    if (_index < failures.length) {
      final failure = failures[_index++];
      if (failure != null) throw failure;
    }
    return snapshot ?? _readySnapshot();
  }
}

Sys01Snapshot _readySnapshot() => const Sys01Snapshot(
  overall: 'healthy',
  overallState: 'ok',
  registeredWorkers: Sys01Count(value: 3, state: 'ready'),
  failedWorkers: Sys01Count(value: 0, state: 'ready'),
  dlqTotal: Sys01Count(value: 0, state: 'ready'),
  sampleTimestamp: '2026-09-20T09:30:00Z',
  observationAvailable: true,
  observationTraceId: 'sys01rt-0123456789abcdef01234567',
  guardianName: 'legacy',
  reaperRunning: true,
  openBreakers: 0,
  registeredBreakers: 5,
  hasCompleteRuntimeSample: true,
);
