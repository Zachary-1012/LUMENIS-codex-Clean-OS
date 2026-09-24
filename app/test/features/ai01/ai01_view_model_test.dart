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

class _HttpFailure implements Exception {
  const _HttpFailure(this.message);
  final String message;

  @override
  String toString() => message;
}

Ai01Snapshot _snapshot() => const Ai01Snapshot(
  isBound: true,
  generatedAt: '2026-09-20T10:00:00',
  providers: [],
  suggestions: [],
  unavailableFields: [],
);
