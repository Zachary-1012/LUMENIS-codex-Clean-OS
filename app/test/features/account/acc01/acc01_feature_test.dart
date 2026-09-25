import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/features/account/acc01/acc01_repository.dart';
import 'package:lumenis_app/features/account/acc01/acc01_screen.dart';
import 'package:lumenis_app/features/account/acc01/acc01_snapshot.dart';
import 'package:lumenis_app/features/account/acc01/acc01_view_model.dart';

import '../../shared/shared_test_support.dart';

void main() {
  test(
    'ACC-01 keeps the product-account boundary separate from runtime state',
    () {
      final snapshot = Acc01Snapshot.fromIdentity({
        'ok': true,
        'generated_at': '2026-09-22T09:00:00',
        'runtime_guardian': {'overall': 'healthy'},
        'focus_context': {'display_name': '广州太古汇'},
        'product_account': {'email': 'secret@example.com'},
      });

      expect(snapshot.runtimeConnected, isTrue);
      expect(snapshot.runtimeHealth, Acc01RuntimeHealth.healthy);
      expect(snapshot.productAccountDeferred, isTrue);
      expect(snapshot.focusName, '广州太古汇');
    },
  );

  test('ACC-01 drops hostile display metadata instead of exposing it', () {
    final snapshot = Acc01Snapshot.fromIdentity({
      'ok': true,
      'runtime_guardian': {'overall': 'ok'},
      'focus_context': {'display_name': '/private/path token=secret'},
    });

    expect(snapshot.focusName, isNull);
  });

  test('ACC-01 does not infer runtime connectivity from identity.ok', () {
    final snapshot = Acc01Snapshot.fromIdentity({'ok': true});

    expect(snapshot.runtimeConnected, isFalse);
    expect(snapshot.runtimeHealth, Acc01RuntimeHealth.unknown);
  });

  test(
    'ACC-01 accepts only an explicit connected or healthy guardian state',
    () {
      final connected = Acc01Snapshot.fromIdentity({
        'ok': true,
        'runtime_guardian': {'overall': 'connected'},
      });
      final degraded = Acc01Snapshot.fromIdentity({
        'ok': true,
        'runtime_guardian': {'overall': 'degraded'},
      });

      expect(connected.runtimeConnected, isTrue);
      expect(connected.runtimeHealth, Acc01RuntimeHealth.healthy);
      expect(degraded.runtimeConnected, isFalse);
      expect(degraded.runtimeHealth, Acc01RuntimeHealth.degraded);
    },
  );

  testWidgets('ACC-01 remains usable without a product account wall', (
    tester,
  ) async {
    await tester.pumpWidget(
      sharedTestApp(
        Acc01Screen(
          client: LumenisCoreClient(),
          repository: _FakeAcc01Repository(),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('内部 Beta 入口'), findsOneWidget);
    expect(find.text('产品账号：Beta 后接入'), findsOneWidget);
    expect(find.text('进入工作区'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  test('ACC-01 ignores a delayed success after disposal', () async {
    final repository = _ControlledAcc01Repository();
    final viewModel = Acc01ViewModel(repository: repository);
    final refresh = viewModel.refresh();

    expect(repository.pending, hasLength(1));
    viewModel.dispose();
    repository.pending.single.complete(_acc01Snapshot('过期结果'));

    await expectLater(refresh, completes);
    expect(viewModel.snapshot, isNull);
    expect(viewModel.phase, Acc01LoadPhase.loading);
  });

  test('ACC-01 ignores a delayed failure after disposal', () async {
    final repository = _ControlledAcc01Repository();
    final viewModel = Acc01ViewModel(repository: repository);
    final refresh = viewModel.refresh();

    expect(repository.pending, hasLength(1));
    viewModel.dispose();
    repository.pending.single.completeError(StateError('HTTP 401'));

    await expectLater(refresh, completes);
    expect(viewModel.failureKind, isNull);
    expect(viewModel.phase, Acc01LoadPhase.loading);
  });

  test('ACC-01 keeps the latest overlapping refresh result', () async {
    final repository = _ControlledAcc01Repository();
    final viewModel = Acc01ViewModel(repository: repository);
    final olderRefresh = viewModel.refresh();
    final latestRefresh = viewModel.refresh();

    expect(repository.pending, hasLength(2));
    repository.pending[1].complete(_acc01Snapshot('最新结果'));
    await latestRefresh;
    repository.pending[0].completeError(StateError('HTTP 401'));
    await olderRefresh;

    expect(viewModel.phase, Acc01LoadPhase.ready);
    expect(viewModel.failureKind, isNull);
    expect(viewModel.snapshot?.focusName, '最新结果');
    viewModel.dispose();
  });

  test(
    'ACC-01 ignores an older refresh triggered around a re-entrant retry',
    () async {
      final repository = _ControlledAcc01Repository();
      final viewModel = Acc01ViewModel(repository: repository);
      var retried = false;
      Future<void>? retry;
      viewModel.addListener(() {
        if (retried) return;
        retried = true;
        retry = viewModel.refresh();
      });

      final initialRefresh = viewModel.refresh();
      expect(repository.pending, hasLength(1));
      await initialRefresh;
      repository.pending.single.complete(_acc01Snapshot('重试结果'));
      await retry;

      expect(viewModel.phase, Acc01LoadPhase.ready);
      expect(viewModel.snapshot?.focusName, '重试结果');
      viewModel.dispose();
    },
  );
}

class _FakeAcc01Repository implements Acc01Repository {
  @override
  Future<Acc01Snapshot> load() async => const Acc01Snapshot(
    runtimeConnected: true,
    runtimeHealth: Acc01RuntimeHealth.healthy,
    productAccountDeferred: true,
    generatedAt: null,
    focusName: '当前工作区',
  );
}

class _ControlledAcc01Repository implements Acc01Repository {
  final List<Completer<Acc01Snapshot>> pending = [];

  @override
  Future<Acc01Snapshot> load() {
    final completer = Completer<Acc01Snapshot>();
    pending.add(completer);
    return completer.future;
  }
}

Acc01Snapshot _acc01Snapshot(String focusName) => Acc01Snapshot(
  runtimeConnected: true,
  runtimeHealth: Acc01RuntimeHealth.healthy,
  productAccountDeferred: true,
  generatedAt: null,
  focusName: focusName,
);
