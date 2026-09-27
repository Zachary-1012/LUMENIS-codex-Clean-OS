import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/features/account/acc04/acc04_repository.dart';
import 'package:lumenis_app/features/account/acc04/acc04_snapshot.dart';
import 'package:lumenis_app/features/account/acc04/acc04_view_model.dart';

void main() {
  test('ACC-04 keeps unbound guard state and safe recovery paths honest', () {
    final snapshot = Acc04Snapshot.fromResponse({
      'ok': true,
      'screen': 'ACC-04',
      'source': 'runtime',
      'bound': false,
      'guard': {
        'recovery_paths': [
          'retry',
          'switch_context',
          'request_access',
          'return',
        ],
        'reason': 'token=secret /private/path',
      },
    });

    expect(snapshot.guardState, Acc04GuardState.unavailable);
    expect(snapshot.productAccountDeferred, isTrue);
    expect(snapshot.recoveryPaths, contains(Acc04RecoveryPath.recheck));
    expect(snapshot.reason, isNull);
  });

  test('ACC-04 rejects a response for another screen', () {
    expect(
      () => Acc04Snapshot.fromResponse({'ok': true, 'screen': 'ACC-03'}),
      throwsFormatException,
    );
  });

  for (final fails in [false, true]) {
    test(
      'late ${fails ? 'failure' : 'success'} after dispose is ignored',
      () async {
        final repository = _ControlledAcc04Repository();
        final viewModel = Acc04ViewModel(repository: repository);
        var notifications = 0;
        viewModel.addListener(() => notifications++);

        final pending = viewModel.refresh();
        expect(repository.requests, hasLength(1));
        expect(notifications, 1);
        viewModel.dispose();

        if (fails) {
          repository.requests.single.completeError(Exception('HTTP 403'));
        } else {
          repository.requests.single.complete(_snapshot('late result'));
        }
        await pending;

        expect(notifications, 1);
        expect(viewModel.snapshot, isNull);
        expect(viewModel.phase, Acc04LoadPhase.loading);
        await viewModel.refresh();
        expect(repository.requests, hasLength(1));
        expect(notifications, 1);
      },
    );
  }

  test(
    'an older failure cannot replace the latest successful guard read',
    () async {
      final repository = _ControlledAcc04Repository();
      final viewModel = Acc04ViewModel(repository: repository);
      addTearDown(viewModel.dispose);

      final oldRead = viewModel.refresh();
      final latestRead = viewModel.refresh();
      expect(repository.requests, hasLength(2));
      final latest = _snapshot('latest result');
      repository.requests[1].complete(latest);
      await latestRead;
      expect(viewModel.phase, Acc04LoadPhase.ready);
      expect(viewModel.snapshot, same(latest));

      repository.requests[0].completeError(Exception('HTTP 403'));
      await oldRead;
      expect(viewModel.phase, Acc04LoadPhase.ready);
      expect(viewModel.failureKind, isNull);
      expect(viewModel.snapshot, same(latest));
    },
  );

  test('an older success cannot reopen data after the latest denial', () async {
    final repository = _ControlledAcc04Repository();
    final viewModel = Acc04ViewModel(repository: repository);
    addTearDown(viewModel.dispose);

    final oldRead = viewModel.refresh();
    final latestRead = viewModel.refresh();
    expect(repository.requests, hasLength(2));
    repository.requests[1].completeError(Exception('HTTP 403'));
    await latestRead;
    expect(viewModel.phase, Acc04LoadPhase.failed);
    expect(viewModel.failureKind, Acc04FailureKind.permissionDenied);
    expect(viewModel.snapshot, isNull);

    repository.requests[0].complete(_snapshot('old result'));
    await oldRead;
    expect(viewModel.phase, Acc04LoadPhase.failed);
    expect(viewModel.failureKind, Acc04FailureKind.permissionDenied);
    expect(viewModel.snapshot, isNull);
  });
}

class _ControlledAcc04Repository implements Acc04Repository {
  final requests = <Completer<Acc04Snapshot>>[];

  @override
  Future<Acc04Snapshot> load() {
    final request = Completer<Acc04Snapshot>();
    requests.add(request);
    return request.future;
  }
}

Acc04Snapshot _snapshot(String generatedAt) => Acc04Snapshot(
  guardState: Acc04GuardState.available,
  productAccountDeferred: true,
  recoveryPaths: const [Acc04RecoveryPath.recheck],
  generatedAt: generatedAt,
);
