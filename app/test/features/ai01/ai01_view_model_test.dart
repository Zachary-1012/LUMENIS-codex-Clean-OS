import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/transport/lumenis_http_transport.dart';
import 'package:lumenis_app/features/ai01/ai01_repository.dart';
import 'package:lumenis_app/features/ai01/ai01_snapshot.dart';
import 'package:lumenis_app/features/ai01/ai01_view_model.dart';

void main() {
  test(
    'loads aggregate and keeps intent submission blocked without scope',
    () async {
      final repository = _FakeAi01Repository(snapshot: _snapshot());
      final viewModel = Ai01ViewModel(repository: repository);

      await viewModel.refresh();
      viewModel.updateDraft('分析当前品牌风险');

      expect(viewModel.phase, Ai01LoadPhase.ready);
      expect(viewModel.snapshot?.isBound, isTrue);
      expect(viewModel.draft, '分析当前品牌风险');
      expect(viewModel.submitBlockedReason, contains('服务端确认'));
      expect(repository.loadCount, 1);

      viewModel.dispose();
    },
  );

  test('classifies an auth failure and retries the read', () async {
    final repository = _FakeAi01Repository(
      failures: [const _HttpFailure('GET screen failed with HTTP 401'), null],
      snapshot: _snapshot(),
    );
    final viewModel = Ai01ViewModel(repository: repository);

    await viewModel.refresh();
    expect(viewModel.phase, Ai01LoadPhase.failed);
    expect(viewModel.failureKind, Ai01FailureKind.authentication);

    await viewModel.refresh();
    expect(viewModel.phase, Ai01LoadPhase.ready);
    expect(repository.loadCount, 2);

    viewModel.dispose();
  });

  test('classifies an offline failure distinctly', () async {
    final viewModel = Ai01ViewModel(
      repository: _FakeAi01Repository(
        failures: [const LumenisTransportException('connection refused')],
        snapshot: _snapshot(),
      ),
    );

    await viewModel.refresh();

    expect(viewModel.phase, Ai01LoadPhase.failed);
    expect(viewModel.failureKind, Ai01FailureKind.offline);

    viewModel.dispose();
  });

  for (final failureCase in <({String error, Ai01FailureKind kind})>[
    (
      error: 'GET screen failed with HTTP 401',
      kind: Ai01FailureKind.authentication,
    ),
    (
      error: 'GET screen failed with HTTP 403',
      kind: Ai01FailureKind.permissionDenied,
    ),
  ]) {
    test(
      'clears a prior snapshot before a ${failureCase.kind.name} read',
      () async {
        final viewModel = Ai01ViewModel(
          repository: _FakeAi01Repository(
            failures: [null, _HttpFailure(failureCase.error)],
            snapshot: _snapshot(generatedAt: 'previous remote snapshot'),
          ),
        );

        await viewModel.refresh();
        expect(viewModel.snapshot?.generatedAt, 'previous remote snapshot');

        final retry = viewModel.refresh();
        expect(viewModel.phase, Ai01LoadPhase.loading);
        expect(viewModel.snapshot, isNull);
        await retry;

        expect(viewModel.phase, Ai01LoadPhase.failed);
        expect(viewModel.failureKind, failureCase.kind);
        expect(viewModel.snapshot, isNull);
        viewModel.dispose();
      },
    );
  }

  test('ignores an older response when refresh requests overlap', () async {
    final first = Completer<Ai01Snapshot>();
    final second = Completer<Ai01Snapshot>();
    final repository = _QueuedAi01Repository([first, second]);
    final viewModel = Ai01ViewModel(repository: repository);
    var notifications = 0;
    viewModel.addListener(() => notifications++);

    final firstRequest = viewModel.refresh();
    final secondRequest = viewModel.refresh();
    expect(repository.loadCount, 2);
    expect(viewModel.snapshot, isNull);

    second.complete(_snapshot(generatedAt: 'newest response'));
    await secondRequest;
    expect(viewModel.snapshot?.generatedAt, 'newest response');
    final notificationsAfterNewest = notifications;

    first.complete(_snapshot(generatedAt: 'stale response'));
    await firstRequest;

    expect(viewModel.phase, Ai01LoadPhase.ready);
    expect(viewModel.snapshot?.generatedAt, 'newest response');
    expect(notifications, notificationsAfterNewest);
    viewModel.dispose();
  });

  test('a read completing after dispose does not notify or throw', () async {
    final pending = Completer<Ai01Snapshot>();
    final viewModel = Ai01ViewModel(
      repository: _QueuedAi01Repository([pending]),
    );
    var notifications = 0;
    viewModel.addListener(() => notifications++);

    final request = viewModel.refresh();
    expect(notifications, 1);
    viewModel.dispose();
    pending.complete(_snapshot());

    await expectLater(request, completes);
    expect(notifications, 1);
  });

  test(
    'keeps permission denial distinct from an authentication failure',
    () async {
      final viewModel = Ai01ViewModel(
        repository: _FakeAi01Repository(
          failures: [const _HttpFailure('GET screen failed with HTTP 403')],
          snapshot: _snapshot(),
        ),
      );

      await viewModel.refresh();

      expect(viewModel.failureKind, Ai01FailureKind.permissionDenied);
      expect(viewModel.failureMessage, contains('无权读取'));

      viewModel.dispose();
    },
  );
}

class _FakeAi01Repository implements Ai01Repository {
  _FakeAi01Repository({required this.snapshot, this.failures = const []});

  final Ai01Snapshot snapshot;
  final List<Object?> failures;
  int loadCount = 0;

  @override
  Future<Ai01Snapshot> load() async {
    final index = loadCount++;
    if (index < failures.length) {
      final error = failures[index];
      if (error != null) throw error;
    }
    return snapshot;
  }
}

class _QueuedAi01Repository implements Ai01Repository {
  _QueuedAi01Repository(this._responses);

  final List<Completer<Ai01Snapshot>> _responses;
  int loadCount = 0;

  @override
  Future<Ai01Snapshot> load() {
    return _responses[loadCount++].future;
  }
}

class _HttpFailure implements Exception {
  const _HttpFailure(this.message);
  final String message;

  @override
  String toString() => message;
}

Ai01Snapshot _snapshot({String generatedAt = '2026-09-20T10:00:00'}) =>
    Ai01Snapshot(
      isBound: true,
      generatedAt: generatedAt,
      providers: [],
      suggestions: [],
      unavailableFields: [],
    );
