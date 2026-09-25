import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/features/account/acc03/acc03_repository.dart';
import 'package:lumenis_app/features/account/acc03/acc03_snapshot.dart';
import 'package:lumenis_app/features/account/acc03/acc03_view_model.dart';

void main() {
  for (final code in [401, 403, 503]) {
    test('ACC-03 isolates context HTTP $code from the runtime entry', () async {
      final result = await CoreAcc03Repository(
        client: _ContextFailureClient(code),
      ).load();
      expect(result.runtimeState, Acc03RuntimeState.connected);
      expect(
        result.contextState,
        code == 503
            ? Acc03RuntimeState.unavailable
            : Acc03RuntimeState.restricted,
      );
      expect(result.currentView, isNull);
      expect(result.launchCards, hasLength(3));
    });
  }

  test('ACC-03 still propagates runtime identity denial', () async {
    await expectLater(
      CoreAcc03Repository(
        client: _ContextFailureClient(403, denyIdentity: true),
      ).load(),
      throwsA(isA<LumenisCoreException>()),
    );
  });

  test(
    'ACC-03 builds distinct workspace destinations from safe context data',
    () {
      final snapshot = Acc03Snapshot.fromResponses(
        identity: {
          'ok': true,
          'runtime_guardian': {'overall': 'healthy'},
        },
        context: {
          'ok': true,
          'contract': 'lumenis.context.v1',
          'selection_only': true,
          'context': {
            'mode': 'GLOBAL_ALL',
            'display_name': {'zh': '全局查看'},
          },
        },
      );

      expect(snapshot.runtimeState, Acc03RuntimeState.connected);
      expect(snapshot.contextState, Acc03RuntimeState.connected);
      expect(snapshot.launchCards.map((card) => card.domain), [
        'CTH',
        'BMP',
        'AI',
      ]);
    },
  );

  test('ACC-03 does not surface path or secret-like context labels', () {
    final snapshot = Acc03Snapshot.fromResponses(
      identity: {
        'ok': true,
        'runtime_guardian': {'overall': 'healthy'},
      },
      context: {
        'ok': true,
        'contract': 'lumenis.context.v1',
        'selection_only': true,
        'context': {
          'mode': 'FOCUS',
          'display_name': {'zh': 'provider=internal /private/path'},
        },
      },
    );

    expect(snapshot.currentView, isNull);
  });

  test(
    'ACC-03 preserves unknown when runtime or context evidence is missing',
    () {
      final snapshot = Acc03Snapshot.fromResponses(identity: {'ok': true});

      expect(snapshot.runtimeState, Acc03RuntimeState.unknown);
      expect(snapshot.startupChecks.first.state, Acc03RuntimeState.unknown);
      expect(snapshot.contextState, Acc03RuntimeState.unknown);
    },
  );

  test('ACC-03 does not treat an invalid context envelope as connected', () {
    final snapshot = Acc03Snapshot.fromResponses(
      identity: {
        'ok': true,
        'runtime_guardian': {'overall': 'healthy'},
      },
      context: {
        'context': {
          'mode': 'FOCUS',
          'display_name': {'zh': '未确认范围'},
        },
      },
    );

    expect(snapshot.runtimeState, Acc03RuntimeState.connected);
    expect(snapshot.contextState, Acc03RuntimeState.unavailable);
    expect(snapshot.currentView, isNull);
  });

  test('ACC-03 ignores a delayed success after disposal', () async {
    final repository = _ControlledAcc03Repository();
    final viewModel = Acc03ViewModel(repository: repository);
    final refresh = viewModel.refresh();

    expect(repository.pending, hasLength(1));
    viewModel.dispose();
    repository.pending.single.complete(_acc03Snapshot('过期结果'));

    await expectLater(refresh, completes);
    expect(viewModel.snapshot, isNull);
    expect(viewModel.phase, Acc03LoadPhase.loading);
  });

  test('ACC-03 ignores a delayed failure after disposal', () async {
    final repository = _ControlledAcc03Repository();
    final viewModel = Acc03ViewModel(repository: repository);
    final refresh = viewModel.refresh();

    expect(repository.pending, hasLength(1));
    viewModel.dispose();
    repository.pending.single.completeError(StateError('HTTP 403'));

    await expectLater(refresh, completes);
    expect(viewModel.failureKind, isNull);
    expect(viewModel.phase, Acc03LoadPhase.loading);
  });

  test('ACC-03 keeps the latest overlapping refresh result', () async {
    final repository = _ControlledAcc03Repository();
    final viewModel = Acc03ViewModel(repository: repository);
    final olderRefresh = viewModel.refresh();
    final latestRefresh = viewModel.refresh();

    expect(repository.pending, hasLength(2));
    repository.pending[1].complete(_acc03Snapshot('最新结果'));
    await latestRefresh;
    repository.pending[0].completeError(StateError('HTTP 403'));
    await olderRefresh;

    expect(viewModel.phase, Acc03LoadPhase.ready);
    expect(viewModel.failureKind, isNull);
    expect(viewModel.snapshot?.currentView, '最新结果');
    viewModel.dispose();
  });

  test(
    'ACC-03 ignores an older refresh triggered around a re-entrant retry',
    () async {
      final repository = _ControlledAcc03Repository();
      final viewModel = Acc03ViewModel(repository: repository);
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
      repository.pending.single.complete(_acc03Snapshot('重试结果'));
      await retry;

      expect(viewModel.phase, Acc03LoadPhase.ready);
      expect(viewModel.snapshot?.currentView, '重试结果');
      viewModel.dispose();
    },
  );
}

class _ContextFailureClient extends LumenisCoreClient {
  _ContextFailureClient(this.code, {this.denyIdentity = false});
  final int code;
  final bool denyIdentity;

  @override
  Future<Map<String, dynamic>> runtimeIdentity() async {
    if (denyIdentity) {
      throw const LumenisCoreException('denied', statusCode: 403);
    }
    return {
      'ok': true,
      'runtime_guardian': {'overall': 'healthy'},
    };
  }

  @override
  Future<Map<String, dynamic>> settingsContext() async =>
      throw LumenisCoreException('context unavailable', statusCode: code);
}

class _ControlledAcc03Repository implements Acc03Repository {
  final List<Completer<Acc03Snapshot>> pending = [];

  @override
  Future<Acc03Snapshot> load() {
    final completer = Completer<Acc03Snapshot>();
    pending.add(completer);
    return completer.future;
  }
}

Acc03Snapshot _acc03Snapshot(String currentView) => Acc03Snapshot.fromResponses(
  identity: {
    'ok': true,
    'runtime_guardian': {'overall': 'healthy'},
  },
  context: {
    'ok': true,
    'contract': 'lumenis.context.v1',
    'selection_only': true,
    'context': {
      'mode': 'GLOBAL_ALL',
      'display_name': {'zh': currentView},
    },
  },
);
