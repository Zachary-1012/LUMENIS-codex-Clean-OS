import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/features/account/acc02/acc02_repository.dart';
import 'package:lumenis_app/features/account/acc02/acc02_screen.dart';
import 'package:lumenis_app/features/account/acc02/acc02_snapshot.dart';
import 'package:lumenis_app/features/account/acc02/acc02_view_model.dart';

import '../../shared/shared_test_support.dart';

void main() {
  test('ACC-02 keeps only server-safe Subject rows', () {
    final snapshot = Acc02Snapshot.fromResponses(
      contextResponse: {
        'ok': true,
        'contract': 'lumenis.context.v1',
        'selection_only': true,
        'context': {
          'mode': 'FOCUS',
          'domain_id': 'CTH',
          'subject_id': 'subject-1',
          'display_name': {'zh': '经营主体一'},
        },
      },
      subjectsResponse: {
        'ok': true,
        'selection_only': true,
        'subjects': [
          {
            'subject_id': 'subject-1',
            'name_zh': '经营主体一',
            'domain_id': 'CTH',
            'subject_type': '商场',
          },
          {
            'subject_id': 'subject-2',
            'name_zh': 'token=secret /private/path',
            'domain_id': 'CTH',
          },
          {
            'subject_id': 'subject-3',
            'name_zh': 'wrong-domain',
            'domain_id': 'SYSTEM',
          },
        ],
      },
    );

    expect(snapshot.contextState, Acc02ContextState.focused);
    expect(snapshot.subjectState, Acc02SubjectState.ready);
    expect(snapshot.subjects, hasLength(1));
    expect(snapshot.subjects.single.id, 'subject-1');
  });

  test('ACC-02 distinguishes a confirmed empty list from access failure', () {
    final empty = Acc02Snapshot.fromResponses(
      subjectsResponse: {'ok': true, 'subjects': []},
    );
    final blocked = Acc02Snapshot.fromResponses(
      subjectsError: 'HTTP 403 permission denied',
    );

    expect(empty.subjectState, Acc02SubjectState.empty);
    expect(blocked.subjectState, Acc02SubjectState.blocked);
  });

  test('ACC-02 preserves GLOBAL_ALL as a real global lens', () {
    final snapshot = Acc02Snapshot.fromResponses(
      contextResponse: {
        'ok': true,
        'contract': 'lumenis.context.v1',
        'selection_only': true,
        'context': {'mode': 'GLOBAL_ALL', 'domain_id': 'CTH'},
      },
      subjectsResponse: {'ok': true, 'subjects': []},
    );

    expect(snapshot.contextState, Acc02ContextState.globalAll);
    expect(snapshot.contextName, isNull);
    expect(snapshot.subjectState, Acc02SubjectState.empty);
  });

  test(
    'ACC-02 selection refreshes from the repository after server confirmation',
    () async {
      final subject = Acc02Subject(
        id: 'subject-1',
        name: '经营主体一',
        domainId: 'CTH',
        subjectType: '商场',
        scope: 'focus',
      );
      final repository = _FakeAcc02Repository(snapshot: _readySnapshot);
      final viewModel = Acc02ViewModel(repository: repository);
      addTearDown(viewModel.dispose);

      await viewModel.refresh();
      await viewModel.selectSubject(subject);

      expect(repository.selectedIds, ['subject-1']);
      expect(repository.loadCount, 2);
      expect(viewModel.actionError, isNull);
    },
  );

  test('ACC-02 rejects duplicate confirmation while one is pending', () async {
    final gate = Completer<void>();
    final repository = _FakeAcc02Repository(
      snapshot: _readySnapshot,
      selectionGate: gate.future,
    );
    final viewModel = Acc02ViewModel(repository: repository);
    addTearDown(viewModel.dispose);

    await viewModel.refresh();
    final firstSelection = viewModel.selectSubject(_subject1);
    expect(viewModel.selectingId, _subject1.id);
    expect(viewModel.canSelect, isFalse);

    await viewModel.selectSubject(_subject2);

    expect(repository.selectedIds, [_subject1.id]);
    gate.complete();
    await firstSelection;
    expect(repository.selectedIds, [_subject1.id]);
    expect(viewModel.actionError, isNull);
  });

  testWidgets('ACC-02 mobile list stays bounded inside the scroll surface', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      sharedTestApp(
        Acc02Screen(
          client: LumenisCoreClient(),
          repository: _FakeAcc02Repository(snapshot: _readySnapshot),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('经营主体一'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'ACC-02 continuation requires focused server context with matching domain and Subject',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(390, 844));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      final snapshots = [
        _snapshot(
          contextState: Acc02ContextState.unavailable,
          contextDomainId: 'CTH',
          selectedSubjectId: _subject1.id,
        ),
        _snapshot(
          contextState: Acc02ContextState.focused,
          contextDomainId: 'BMP',
          selectedSubjectId: _subject1.id,
        ),
        _snapshot(
          contextState: Acc02ContextState.focused,
          contextDomainId: 'CTH',
          selectedSubjectId: 'stale-subject',
        ),
      ];

      for (final snapshot in snapshots) {
        await tester.pumpWidget(
          sharedTestApp(
            Acc02Screen(
              key: ValueKey(snapshot),
              client: LumenisCoreClient(),
              repository: _FakeAcc02Repository(snapshot: snapshot),
              onContinue: () {},
            ),
          ),
        );
        await tester.pumpAndSettle();
        await tester.tap(find.text(_subject1.name).first);
        await tester.pump();

        final button = tester.widget<OutlinedButton>(
          find.byType(OutlinedButton),
        );
        expect(button.onPressed, isNull);
      }

      await tester.pumpWidget(const SizedBox.shrink());
    },
  );

  testWidgets(
    'ACC-02 keeps confirm and continue disabled while pending and after failure',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(390, 844));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      final gate = Completer<void>();
      var continueCalls = 0;
      final repository = _FakeAcc02Repository(
        snapshot: _readySnapshot,
        selectionGate: gate.future,
        selectionError: StateError('HTTP 403 permission denied'),
      );

      await tester.pumpWidget(
        sharedTestApp(
          Acc02Screen(
            client: LumenisCoreClient(),
            repository: repository,
            onContinue: () => continueCalls++,
          ),
        ),
      );
      await tester.pumpAndSettle();
      await tester.tap(find.text(_subject1.name).first);
      await tester.pump();

      expect(
        tester.widget<OutlinedButton>(find.byType(OutlinedButton)).onPressed,
        isNotNull,
      );
      await tester.ensureVisible(find.byType(FilledButton));
      await tester.pumpAndSettle();
      await tester.tap(find.byType(FilledButton));
      await tester.pump();
      expect(
        tester.widget<FilledButton>(find.byType(FilledButton)).onPressed,
        isNull,
      );
      expect(
        tester.widget<OutlinedButton>(find.byType(OutlinedButton)).onPressed,
        isNull,
      );

      await tester.ensureVisible(find.text(_subject2.name).first);
      await tester.pump();
      await tester.tap(find.text(_subject2.name).first);
      await tester.pump();
      expect(
        tester.widget<FilledButton>(find.byType(FilledButton)).onPressed,
        isNull,
      );
      expect(
        tester.widget<OutlinedButton>(find.byType(OutlinedButton)).onPressed,
        isNull,
      );

      gate.complete();
      await tester.pumpAndSettle();

      expect(repository.selectedIds, [_subject1.id]);
      expect(find.textContaining('主体没有被切换'), findsWidgets);
      expect(
        tester.widget<OutlinedButton>(find.byType(OutlinedButton)).onPressed,
        isNull,
      );
      expect(continueCalls, 0);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('ACC-02 continues after matching server confirmation', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    var continueCalls = 0;
    final repository = _FakeAcc02Repository(
      snapshot: _globalSnapshot,
      snapshotAfterSelection: _confirmedSubject2Snapshot,
    );

    await tester.pumpWidget(
      sharedTestApp(
        Acc02Screen(
          client: LumenisCoreClient(),
          repository: repository,
          onContinue: () => continueCalls++,
        ),
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.text(_subject2.name).first);
    await tester.pump();
    expect(
      tester.widget<OutlinedButton>(find.byType(OutlinedButton)).onPressed,
      isNull,
    );

    await tester.ensureVisible(find.byType(FilledButton));
    await tester.pumpAndSettle();
    await tester.tap(find.byType(FilledButton));
    await tester.pumpAndSettle();
    expect(repository.selectedIds, [_subject2.id]);
    expect(
      tester.widget<OutlinedButton>(find.byType(OutlinedButton)).onPressed,
      isNotNull,
    );

    await tester.ensureVisible(find.byType(OutlinedButton));
    await tester.pumpAndSettle();
    await tester.tap(find.byType(OutlinedButton));
    expect(continueCalls, 1);
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'ACC-02 selection completion after leaving does not notify disposed model',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(390, 844));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      final gate = Completer<void>();
      final repository = _FakeAcc02Repository(
        snapshot: _readySnapshot,
        selectionGate: gate.future,
      );

      await tester.pumpWidget(
        sharedTestApp(
          Acc02Screen(client: LumenisCoreClient(), repository: repository),
        ),
      );
      await tester.pumpAndSettle();
      await tester.tap(find.text(_subject1.name).first);
      await tester.pump();
      await tester.ensureVisible(find.byType(FilledButton));
      await tester.pumpAndSettle();
      await tester.tap(find.byType(FilledButton));
      await tester.pump();
      expect(repository.selectedIds, [_subject1.id]);

      await tester.pumpWidget(const SizedBox.shrink());
      gate.complete();
      await tester.pump();
      await tester.pump();

      expect(repository.loadCount, 1);
      expect(tester.takeException(), isNull);
    },
  );
}

const _subject1 = Acc02Subject(
  id: 'subject-1',
  name: '经营主体一',
  domainId: 'CTH',
  subjectType: '商场',
  scope: 'focus',
);

const _subject2 = Acc02Subject(
  id: 'subject-2',
  name: '经营主体二',
  domainId: 'CTH',
  subjectType: '商场',
  scope: 'focus',
);

Acc02Snapshot _snapshot({
  required Acc02ContextState contextState,
  required String? contextDomainId,
  required String? selectedSubjectId,
}) => Acc02Snapshot(
  contextState: contextState,
  subjectState: Acc02SubjectState.ready,
  subjects: const [_subject1, _subject2],
  selectionOnly: true,
  contextDomainId: contextDomainId,
  selectedSubjectId: selectedSubjectId,
);

const _readySnapshot = Acc02Snapshot(
  contextState: Acc02ContextState.focused,
  subjectState: Acc02SubjectState.ready,
  subjects: [_subject1, _subject2],
  selectionOnly: true,
  contextDomainId: 'CTH',
  selectedSubjectId: 'subject-1',
);

const _globalSnapshot = Acc02Snapshot(
  contextState: Acc02ContextState.globalAll,
  subjectState: Acc02SubjectState.ready,
  subjects: [_subject1, _subject2],
  selectionOnly: true,
);

const _confirmedSubject2Snapshot = Acc02Snapshot(
  contextState: Acc02ContextState.focused,
  subjectState: Acc02SubjectState.ready,
  subjects: [_subject1, _subject2],
  selectionOnly: true,
  contextDomainId: 'CTH',
  selectedSubjectId: 'subject-2',
);

class _FakeAcc02Repository implements Acc02Repository {
  _FakeAcc02Repository({
    required this.snapshot,
    this.selectionGate,
    this.snapshotAfterSelection,
    this.selectionError,
  });

  Acc02Snapshot snapshot;
  final Future<void>? selectionGate;
  final Acc02Snapshot? snapshotAfterSelection;
  final Object? selectionError;
  final selectedIds = <String>[];
  int loadCount = 0;

  @override
  Future<Acc02Snapshot> load() async {
    loadCount++;
    return snapshot;
  }

  @override
  Future<void> selectSubject(Acc02Subject subject) async {
    selectedIds.add(subject.id);
    final gate = selectionGate;
    if (gate != null) await gate;
    if (selectionError != null) throw selectionError!;
    if (snapshotAfterSelection != null) snapshot = snapshotAfterSelection!;
  }
}
