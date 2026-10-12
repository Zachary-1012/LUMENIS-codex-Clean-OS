import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/transport/lumenis_http_transport.dart';
import 'package:lumenis_app/features/ai01/ai01_intent.dart';
import 'package:lumenis_app/features/ai01/ai01_repository.dart';
import 'package:lumenis_app/features/ai01/ai01_snapshot.dart';
import 'package:lumenis_app/features/ai01/ai01_view_model.dart';

void main() {
  test(
    'loads aggregate; submission needs a ready read and a non-empty draft',
    () async {
      final repository = _FakeAi01Repository(snapshot: _snapshot());
      final viewModel = Ai01ViewModel(repository: repository);

      expect(viewModel.submitBlock, Ai01SubmitBlock.notReady);
      await viewModel.refresh();
      expect(viewModel.submitBlock, Ai01SubmitBlock.emptyDraft);
      viewModel.updateDraft('分析当前品牌风险');

      expect(viewModel.phase, Ai01LoadPhase.ready);
      expect(viewModel.snapshot?.isBound, isTrue);
      expect(viewModel.draft, '分析当前品牌风险');
      expect(viewModel.canSubmit, isTrue);
      expect(repository.loadCount, 1);
      expect(repository.submitted, isEmpty, reason: 'loading never submits');

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
      expect(viewModel.failureMessage, contains('不可访问'));

      viewModel.dispose();
    },
  );

  group('submit', () {
    const completed = Ai01IntentResult(
      kind: Ai01IntentKind.completed,
      status: 'completed',
      executionId: 'exec-1',
      evidenceRecorded: true,
    );

    Future<Ai01ViewModel> ready(_FakeAi01Repository repository) async {
      final viewModel = Ai01ViewModel(repository: repository);
      await viewModel.refresh();
      return viewModel;
    }

    test('sends the trimmed draft once and reports completion', () async {
      final repository = _FakeAi01Repository(
        snapshot: _snapshot(),
        onSubmit: (_) async => completed,
      );
      final viewModel = await ready(repository);
      viewModel.updateDraft('  检查本周风险变化  ');

      await viewModel.submit();

      expect(repository.submitted, ['检查本周风险变化']);
      expect(viewModel.submitPhase, Ai01SubmitPhase.completed);
      expect(viewModel.intentResult?.executionId, 'exec-1');
      expect(viewModel.latestSubmission?.task, '检查本周风险变化');
      expect(viewModel.submissions, hasLength(1));
      expect(viewModel.submissions.single.phase, Ai01SubmitPhase.completed);
      expect(viewModel.draft, '  检查本周风险变化  ', reason: 'draft is kept');
      expect(viewModel.submitBlock, Ai01SubmitBlock.alreadySubmitted);
      await viewModel.submit();
      expect(repository.submitted, hasLength(1), reason: 'no duplicate send');

      viewModel.updateDraft('检查本周风险变化，并列出来源');
      expect(viewModel.canSubmit, isTrue);
      expect(viewModel.latestSubmission?.task, '检查本周风险变化');
      expect(viewModel.intentResult?.executionId, 'exec-1');
      viewModel.dispose();
    });

    test(
      'keeps earlier task results when draft and later submissions change',
      () async {
        final repository = _FakeAi01Repository(
          snapshot: _snapshot(),
          onSubmit: (task) async => Ai01IntentResult(
            kind: task == 'task one'
                ? Ai01IntentKind.completed
                : Ai01IntentKind.notCompleted,
            status: task == 'task one' ? 'completed' : 'failed',
            executionId: task == 'task one' ? 'exec-1' : 'exec-2',
            evidenceRecorded: task == 'task one',
          ),
        );
        final viewModel = await ready(repository);

        viewModel.updateDraft(' task one ');
        await viewModel.submit();
        final first = viewModel.submissions.single;

        viewModel.updateDraft('task two');
        expect(viewModel.latestSubmission, same(first));
        expect(viewModel.intentResult?.executionId, 'exec-1');
        await viewModel.submit();

        expect(viewModel.submissions, hasLength(2));
        expect(viewModel.submissions[0].task, 'task one');
        expect(viewModel.submissions[0].result?.executionId, 'exec-1');
        expect(viewModel.submissions[0].phase, Ai01SubmitPhase.completed);
        expect(viewModel.submissions[1].task, 'task two');
        expect(viewModel.submissions[1].result?.executionId, 'exec-2');
        expect(viewModel.submissions[1].phase, Ai01SubmitPhase.notCompleted);
        expect(() => viewModel.submissions.add(first), throwsUnsupportedError);

        viewModel.dispose();
      },
    );

    test('does not submit without a read, a draft, or within limits', () async {
      final repository = _FakeAi01Repository(
        snapshot: _snapshot(),
        failures: [null, const _HttpFailure('GET screen failed with HTTP 503')],
        onSubmit: (_) async => completed,
      );
      final viewModel = Ai01ViewModel(repository: repository);
      viewModel.updateDraft('task');
      await viewModel.submit();
      expect(repository.submitted, isEmpty, reason: 'not read yet');

      await viewModel.refresh();
      viewModel.updateDraft('   ');
      expect(viewModel.submitBlock, Ai01SubmitBlock.emptyDraft);
      viewModel.updateDraft('字' * (ai01MaxTaskLength + 1));
      expect(viewModel.submitBlock, Ai01SubmitBlock.tooLong);
      viewModel.updateDraft('字' * ai01MaxTaskLength);
      expect(viewModel.canSubmit, isTrue);

      await viewModel.refresh(); // second read fails
      expect(viewModel.phase, Ai01LoadPhase.failed);
      expect(viewModel.submitBlock, Ai01SubmitBlock.notReady);
      await viewModel.submit();
      expect(repository.submitted, isEmpty);
      viewModel.dispose();
    });

    test('a failed execution (owned AI not bound) is never success', () async {
      final repository = _FakeAi01Repository(
        snapshot: _snapshot(),
        onSubmit: (_) async => const Ai01IntentResult(
          kind: Ai01IntentKind.notCompleted,
          status: 'failed',
          executionId: 'exec-2',
          evidenceRecorded: false,
        ),
      );
      final viewModel = await ready(repository);
      viewModel.updateDraft('task');

      await viewModel.submit();

      expect(viewModel.submitPhase, Ai01SubmitPhase.notCompleted);
      expect(viewModel.intentResult?.evidenceRecorded, isFalse);
      expect(viewModel.latestSubmission?.task, 'task');
      expect(viewModel.latestSubmission?.phase, Ai01SubmitPhase.notCompleted);
      viewModel.dispose();
    });

    test('pending approval stays pending and unexecuted', () async {
      final repository = _FakeAi01Repository(
        snapshot: _snapshot(),
        onSubmit: (_) async => const Ai01IntentResult(
          kind: Ai01IntentKind.pendingApproval,
          status: 'pending_approval',
          auditId: 'aud-1',
          requiresApproval: true,
        ),
      );
      final viewModel = await ready(repository);
      viewModel.updateDraft('task');

      await viewModel.submit();

      expect(viewModel.submitPhase, Ai01SubmitPhase.pendingApproval);
      expect(viewModel.intentResult?.executionId, isNull);
      expect(viewModel.latestSubmission?.task, 'task');
      expect(viewModel.latestSubmission?.result?.requiresApproval, isTrue);
      viewModel.dispose();
    });

    for (final failureCase in <({Object error, Ai01SubmitPhase phase})>[
      (
        error: const _HttpFailure('POST intent failed with HTTP 400'),
        phase: Ai01SubmitPhase.invalid,
      ),
      (
        error: const _HttpFailure('POST intent failed with HTTP 401'),
        phase: Ai01SubmitPhase.authentication,
      ),
      (
        error: const _HttpFailure('POST intent failed with HTTP 403'),
        phase: Ai01SubmitPhase.denied,
      ),
      (
        error: const _HttpFailure('POST intent failed with HTTP 500'),
        phase: Ai01SubmitPhase.failed,
      ),
      (
        error: const LumenisTransportException('connection reset'),
        phase: Ai01SubmitPhase.outcomeUnknown,
      ),
      (
        error: TimeoutException('request timed out'),
        phase: Ai01SubmitPhase.outcomeUnknown,
      ),
      (
        error: const FormatException('not a valid response'),
        phase: Ai01SubmitPhase.outcomeUnknown,
      ),
    ]) {
      test('classifies ${failureCase.error} as ${failureCase.phase.name} '
          'without automatic retry', () async {
        final repository = _FakeAi01Repository(
          snapshot: _snapshot(),
          onSubmit: (_) async => throw failureCase.error,
        );
        final viewModel = await ready(repository);
        viewModel.updateDraft('task');

        await viewModel.submit();
        await Future<void>.delayed(Duration.zero);

        expect(viewModel.submitPhase, failureCase.phase);
        expect(viewModel.intentResult, isNull);
        expect(viewModel.latestSubmission?.task, 'task');
        expect(viewModel.latestSubmission?.phase, failureCase.phase);
        expect(repository.submitted, hasLength(1), reason: 'no auto retry');
        viewModel.dispose();
      });
    }

    test('ignores a second submit while one is in flight', () async {
      final gate = Completer<Ai01IntentResult>();
      final repository = _FakeAi01Repository(
        snapshot: _snapshot(),
        onSubmit: (_) => gate.future,
      );
      final viewModel = await ready(repository);
      viewModel.updateDraft('task');

      final first = viewModel.submit();
      expect(viewModel.submitPhase, Ai01SubmitPhase.submitting);
      expect(viewModel.submitBlock, Ai01SubmitBlock.submitting);
      await viewModel.submit();
      expect(repository.submitted, hasLength(1));

      gate.complete(completed);
      await first;
      expect(viewModel.submitPhase, Ai01SubmitPhase.completed);
      viewModel.dispose();
    });

    test(
      'an old client result cannot update the next client ViewModel',
      () async {
        final gate = Completer<Ai01IntentResult>();
        final oldRepository = _FakeAi01Repository(
          snapshot: _snapshot(),
          onSubmit: (_) => gate.future,
        );
        final oldViewModel = await ready(oldRepository);
        oldViewModel.updateDraft('old client task');

        final pending = oldViewModel.submit();
        oldViewModel.dispose();

        final newRepository = _FakeAi01Repository(
          snapshot: _snapshot(),
          onSubmit: (_) async => completed,
        );
        final newViewModel = await ready(newRepository);
        newViewModel.updateDraft('new client task');
        await newViewModel.submit();

        gate.complete(completed);
        await pending;

        expect(
          oldViewModel.latestSubmission?.phase,
          Ai01SubmitPhase.outcomeUnknown,
        );
        expect(oldViewModel.latestSubmission?.task, 'old client task');
        expect(newViewModel.submissions, hasLength(1));
        expect(newViewModel.latestSubmission?.task, 'new client task');
        expect(newViewModel.latestSubmission?.result?.executionId, 'exec-1');
        newViewModel.dispose();
      },
    );
  });
}

class _FakeAi01Repository implements Ai01Repository {
  _FakeAi01Repository({
    required this.snapshot,
    this.failures = const [],
    this.onSubmit,
  });

  final Ai01Snapshot snapshot;
  final List<Object?> failures;
  final Future<Ai01IntentResult> Function(String task)? onSubmit;
  final submitted = <String>[];
  int loadCount = 0;

  @override
  Future<Ai01IntentResult> submitIntent(String task) {
    submitted.add(task);
    final handler = onSubmit;
    if (handler == null) throw StateError('unexpected submit');
    return handler(task);
  }

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

  @override
  Future<Ai01IntentResult> submitIntent(String task) =>
      throw StateError('unexpected submit');

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
