import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/features/ai02/ai02_repository.dart';
import 'package:lumenis_app/features/ai02/ai02_screen.dart';
import 'package:lumenis_app/features/ai02/ai02_snapshot.dart';
import 'package:lumenis_app/features/ai02/ai02_view_model.dart';
import '../shared/shared_test_support.dart';

Map<String, dynamic> row(
  String id, {
  String status = 'pending',
  String input = '整理资料',
  String? requestId,
}) => {
  'task_id': id,
  'request_id': ?requestId,
  'context': {'secret': 'MUST_NOT_RENDER'},
  'result': {'internal_reasoning': 'MUST_NOT_RENDER'},
  'workspace_view': {
    'title': input,
    'input': input,
    'status': status,
    'can_cancel': status == 'pending',
    'can_resume': false,
    'output_text': '资料整理结果',
    'work_refs': [],
    'steps': [],
  },
};
Ai02Task task(
  String id, {
  String status = 'pending',
  String input = '整理资料',
  String? requestId,
}) => Ai02Task.fromJson(
  row(id, status: status, input: input, requestId: requestId),
);

class FakeRepository implements Ai02Repository {
  Ai02Snapshot page = const Ai02Snapshot(tasks: []);
  Ai02Task selected = task('task_0123456789abcdef');
  Object? startError, readError;
  final starts = <String>[];
  final actions = <String>[];
  final submittedIds = <String>[];
  String? pendingId;
  String? otherPendingId;
  Ai02Task? recovered;
  bool failPendingWrite = false;
  Completer<Ai02Snapshot>? pendingLoad;
  final reads = <String, Completer<Ai02Task>>{};
  @override
  Future<Ai02Snapshot> load({int offset = 0}) async =>
      pendingLoad == null ? page : pendingLoad!.future;
  @override
  Future<Ai02Task> read(String id) async {
    if (readError case final error?) throw error;
    return reads[id]?.future ?? selected;
  }

  @override
  Future<Ai02Task> start(String input, {required String requestId}) async {
    starts.add(input);
    submittedIds.add(requestId);
    if (startError case final error?) throw error;
    return task('task_0123456789abcdef', input: input, requestId: requestId);
  }

  @override
  Future<Ai02Task?> readRequest(String requestId) async => recovered;
  @override
  Future<String?> pendingRequest() async => pendingId;
  @override
  Future<void> retainRequest(String requestId) async {
    if (failPendingWrite) throw StateError('Device storage unavailable');
    pendingId = requestId;
  }

  @override
  Future<void> forgetRequest(String requestId) async {
    if (pendingId == requestId) {
      pendingId = otherPendingId;
      otherPendingId = null;
    }
  }

  @override
  Future<Ai02Task> act(String id, String action) async {
    actions.add(action);
    return selected;
  }
}

void main() {
  test('Restricted results remain distinct from missing results', () {
    final source = row('task_0123456789abcdef', status: 'succeeded');
    final view = Map<String, dynamic>.from(source['workspace_view'] as Map);
    source['workspace_view'] = view;
    view['output_text'] = null;
    view['result_access_state'] = 'RESTRICTED';
    final parsed = Ai02Task.fromJson(source);
    expect(parsed.resultRestricted, isTrue);
    expect(parsed.output, isNull);
    expect(parsed.works, isEmpty);
    expect(parsed.input, '整理资料');
  });

  test('Task parsing consumes only the server workspace projection', () {
    final source = row('task_0123456789abcdef');
    final parsed = Ai02Task.fromJson(source);
    expect(parsed.output, '资料整理结果');
    expect(parsed.input, '整理资料');
    expect(parsed.canResume, false);
    source.remove('workspace_view');
    expect(() => Ai02Task.fromJson(source), throwsFormatException);
    expect(
      () => Ai02Snapshot.fromResponse({
        'ok': true,
        'tasks': [],
        'has_more': true,
      }),
      throwsFormatException,
    );
  });

  test(
    'Uncertain creation is read back, never automatically submitted twice',
    () async {
      final repository = FakeRepository()
        ..startError = TimeoutException('lost acknowledgement');
      final vm = Ai02ViewModel(repository: repository);
      addTearDown(vm.dispose);
      await vm.refresh();
      expect(await vm.start('整理资料'), false);
      expect(vm.creationUncertain, true);
      expect(vm.canStart, false);
      expect(await vm.start('整理资料'), false);
      repository.page = Ai02Snapshot(tasks: [repository.selected]);
      await vm.refresh();
      expect(repository.starts, ['整理资料']);
      expect(vm.selected, null);
      expect(vm.creationUncertain, true);
      await vm.select(repository.selected.id);
      expect(vm.canStart, false);
      expect(vm.creationUncertain, true);
      repository.recovered = task(
        'task_fedcba9876543210',
        requestId: repository.pendingId,
      );
      await vm.refresh();
      expect(vm.selected?.id, 'task_fedcba9876543210');
      expect(vm.creationUncertain, false);
      expect(repository.pendingId, null);
    },
  );

  test(
    'Cold reopening reconciles the same persisted request without another POST',
    () async {
      final repository = FakeRepository()
        ..startError = TimeoutException('lost acknowledgement');
      final first = Ai02ViewModel(repository: repository);
      await first.refresh();
      await first.start('整理资料');
      final identity = repository.pendingId!;
      first.dispose();
      repository.recovered = task('task_fedcba9876543210', requestId: identity);
      final reopened = Ai02ViewModel(repository: repository);
      addTearDown(reopened.dispose);
      await reopened.refresh();
      expect(reopened.selected?.requestId, identity);
      expect(repository.starts, ['整理资料']);
      expect(repository.pendingId, null);
    },
  );

  test(
    'Explicit retry retains request identity and cannot create another intent',
    () async {
      final repository = FakeRepository()
        ..startError = TimeoutException('lost acknowledgement');
      final vm = Ai02ViewModel(repository: repository);
      addTearDown(vm.dispose);
      await vm.refresh();
      await vm.start('整理资料');
      expect(vm.canRetrySubmission, true);
      repository.startError = null;
      expect(await vm.start('整理资料', retryUnconfirmed: true), true);
      expect(repository.submittedIds, hasLength(2));
      expect(repository.submittedIds[0], repository.submittedIds[1]);
      expect(vm.creationUncertain, false);
    },
  );

  test(
    'A request is never sent when its recovery identity cannot be saved',
    () async {
      final repository = FakeRepository()..failPendingWrite = true;
      final vm = Ai02ViewModel(repository: repository);
      addTearDown(vm.dispose);
      await vm.refresh();
      expect(await vm.start('整理资料'), false);
      expect(repository.starts, isEmpty);
    },
  );

  test('Reconciling one window retains another pending request', () async {
    const first = '11111111111111111111111111111111';
    const second = '22222222222222222222222222222222';
    final repository = FakeRepository()
      ..pendingId = first
      ..otherPendingId = second
      ..recovered = task('task_0123456789abcdef', requestId: first);
    final vm = Ai02ViewModel(repository: repository);
    addTearDown(vm.dispose);
    await vm.refresh();
    expect(repository.pendingId, second);
    expect(vm.creationUncertain, true);
    expect(vm.canStart, false);
    expect(repository.starts, isEmpty);
  });

  test(
    'A mismatched request lookup cannot unlock an uncertain submission',
    () async {
      final repository = FakeRepository()
        ..startError = TimeoutException('lost acknowledgement');
      final vm = Ai02ViewModel(repository: repository);
      addTearDown(vm.dispose);
      await vm.refresh();
      await vm.start('整理资料');
      repository.recovered = task(
        'task_fedcba9876543210',
        requestId: '00000000000000000000000000000000',
      );
      await vm.refresh();
      expect(vm.creationUncertain, true);
      expect(vm.canStart, false);
      expect(repository.pendingId, isNotNull);
    },
  );

  test(
    'A denied reread clears cached task and list instead of leaking the old output',
    () async {
      final repository = FakeRepository();
      final vm = Ai02ViewModel(repository: repository);
      addTearDown(vm.dispose);
      await vm.refresh();
      await vm.select(repository.selected.id);
      repository.readError = const LumenisCoreException(
        'denied',
        statusCode: 403,
      );
      await vm.select(repository.selected.id);
      expect(vm.selected, null);
      expect(vm.snapshot, null);
      expect(vm.canStart, false);
      expect(vm.failureKind, Ai02FailureKind.permissionDenied);
    },
  );

  test('A late result cannot overwrite a newer selected task', () async {
    final repository = FakeRepository();
    final vm = Ai02ViewModel(repository: repository);
    addTearDown(vm.dispose);
    repository.reads['task_aaaaaaaaaaaaaaaa'] = Completer();
    repository.reads['task_bbbbbbbbbbbbbbbb'] = Completer();
    final a = vm.select('task_aaaaaaaaaaaaaaaa');
    final b = vm.select('task_bbbbbbbbbbbbbbbb');
    repository.reads['task_bbbbbbbbbbbbbbbb']!.complete(
      task('task_bbbbbbbbbbbbbbbb'),
    );
    await b;
    repository.reads['task_aaaaaaaaaaaaaaaa']!.complete(
      task('task_aaaaaaaaaaaaaaaa'),
    );
    await a;
    expect(vm.selected?.id, 'task_bbbbbbbbbbbbbbbb');
  });

  test('Disposed views cannot be repopulated by an in-flight list', () async {
    final repository = FakeRepository()..pendingLoad = Completer();
    final vm = Ai02ViewModel(repository: repository);
    final pending = vm.refresh();
    vm.dispose();
    repository.pendingLoad!.complete(
      Ai02Snapshot(tasks: [repository.selected]),
    );
    await pending;
    expect(vm.snapshot, null);
  });

  test('Terminal tasks without server recovery do not execute again', () async {
    final repository = FakeRepository()
      ..selected = task('task_0123456789abcdef', status: 'succeeded');
    final vm = Ai02ViewModel(repository: repository);
    addTearDown(vm.dispose);
    await vm.select(repository.selected.id);
    await vm.act('run');
    await vm.act('cancel');
    expect(repository.actions, isEmpty);
  });

  testWidgets(
    'Task start calls the real repository once and shows the returned work',
    (tester) async {
      final repository = FakeRepository();
      final draft = TextEditingController(text: '整理资料');
      addTearDown(draft.dispose);
      await tester.pumpWidget(
        sharedTestApp(
          Ai02Screen(
            client: LumenisCoreClient(),
            repository: repository,
            draftController: draft,
          ),
        ),
      );
      await tester.pumpAndSettle();
      await tester.tap(find.widgetWithText(FilledButton, '开始'));
      await tester.pumpAndSettle();
      expect(repository.starts, ['整理资料']);
      expect(find.text('资料整理结果'), findsOneWidget);
      expect(find.textContaining('MUST_NOT_RENDER'), findsNothing);
      expect(draft.text, isEmpty);
      await tester.pumpWidget(const SizedBox.shrink());
    },
  );
}
