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
}

const _readySnapshot = Acc02Snapshot(
  contextState: Acc02ContextState.focused,
  subjectState: Acc02SubjectState.ready,
  subjects: [
    Acc02Subject(
      id: 'subject-1',
      name: '经营主体一',
      domainId: 'CTH',
      subjectType: '商场',
      scope: 'focus',
    ),
  ],
  selectionOnly: true,
);

class _FakeAcc02Repository implements Acc02Repository {
  _FakeAcc02Repository({required this.snapshot});

  final Acc02Snapshot snapshot;
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
  }
}
