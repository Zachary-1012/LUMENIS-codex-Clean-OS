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
      final repository = _FakeAcc02Repository(
        snapshot: _globalSnapshot,
        snapshotAfterSelection: _confirmedSubject1Snapshot,
      );
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
      snapshot: _globalSnapshot,
      selectionGate: gate.future,
      snapshotAfterSelection: _confirmedSubject1Snapshot,
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

  test(
    'ACC-02 does not refresh while Subject confirmation is pending',
    () async {
      final gate = Completer<void>();
      final repository = _FakeAcc02Repository(
        snapshot: _globalSnapshot,
        selectionGate: gate.future,
        snapshotAfterSelection: _confirmedSubject1Snapshot,
      );
      final viewModel = Acc02ViewModel(repository: repository);
      addTearDown(viewModel.dispose);

      await viewModel.refresh();
      final selection = viewModel.selectSubject(_subject1);
      expect(viewModel.selectingId, _subject1.id);

      await viewModel.refresh();
      expect(repository.loadCount, 1);
      expect(viewModel.selectingId, _subject1.id);

      gate.complete();
      await selection;
      expect(repository.loadCount, 2);
      expect(viewModel.actionError, isNull);
    },
  );

  test('ACC-02 coalesces overlapping refresh calls', () async {
    final gate = Completer<void>();
    final repository = _FakeAcc02Repository(
      snapshot: _readySnapshot,
      loadGate: gate.future,
    );
    final viewModel = Acc02ViewModel(repository: repository);
    addTearDown(viewModel.dispose);

    final firstRefresh = viewModel.refresh();
    expect(repository.loadCount, 1);
    await viewModel.refresh();
    expect(repository.loadCount, 1);
    expect(viewModel.phase, Acc02LoadPhase.loading);

    gate.complete();
    await firstRefresh;
    expect(repository.loadCount, 1);
    expect(viewModel.phase, Acc02LoadPhase.ready);
  });

  test(
    'ACC-02 refresh failure after confirmation blocks stale reuse',
    () async {
      final repository = _FakeAcc02Repository(
        snapshot: _globalSnapshot,
        loadSequence: [
          _globalSnapshot,
          _confirmedSubject1Snapshot,
          StateError('Core unavailable'),
          _confirmedSubject1Snapshot,
        ],
      );
      final viewModel = Acc02ViewModel(repository: repository);
      addTearDown(viewModel.dispose);

      await viewModel.refresh();
      await viewModel.selectSubject(_subject1);
      expect(
        viewModel.confirmationStatusFor(_subject1),
        Acc02ConfirmationStatus.confirmed,
      );

      await viewModel.refresh();
      expect(viewModel.phase, Acc02LoadPhase.ready);
      expect(viewModel.needsReadback, isTrue);
      expect(viewModel.isCandidateNavigationLocked, isTrue);
      expect(viewModel.canConfirm(_subject2), isFalse);
      expect(viewModel.actionErrorFor(_subject1), contains('变更结果待确认'));

      await viewModel.refresh();
      expect(viewModel.needsReadback, isFalse);
      expect(
        viewModel.confirmationStatusFor(_subject1),
        Acc02ConfirmationStatus.confirmed,
      );
      expect(viewModel.hasMatchingServerContext(_subject1), isTrue);
    },
  );

  test(
    'ACC-02 readback mismatch remains unconfirmed for the candidate',
    () async {
      const otherDomain = Acc02Snapshot(
        contextState: Acc02ContextState.focused,
        subjectState: Acc02SubjectState.ready,
        subjects: [_subject1, _subject2],
        selectionOnly: true,
        contextDomainId: 'BMP',
        selectedSubjectId: 'subject-1',
      );
      final repository = _FakeAcc02Repository(
        snapshot: _globalSnapshot,
        loadSequence: [
          _globalSnapshot,
          StateError('Core unavailable during readback'),
          otherDomain,
        ],
      );
      final viewModel = Acc02ViewModel(repository: repository);
      addTearDown(viewModel.dispose);

      await viewModel.refresh();
      await viewModel.selectSubject(_subject1);
      expect(viewModel.needsReadback, isTrue);
      expect(
        viewModel.confirmationStatusFor(_subject1),
        Acc02ConfirmationStatus.readbackUnavailable,
      );

      await viewModel.refresh();
      expect(viewModel.needsReadback, isFalse);
      expect(viewModel.hasMatchingServerContext(_subject1), isFalse);
      expect(
        viewModel.confirmationStatusFor(_subject1),
        Acc02ConfirmationStatus.mismatch,
      );
      expect(viewModel.actionErrorFor(_subject1), contains('不一致'));
    },
  );

  test(
    'ACC-02 uncertain write failure does not claim the server had no effect',
    () async {
      final repository = _FakeAcc02Repository(
        snapshot: _globalSnapshot,
        selectionError: StateError('Connection reset while posting context'),
      );
      final viewModel = Acc02ViewModel(repository: repository);
      addTearDown(viewModel.dispose);

      await viewModel.refresh();
      await viewModel.selectSubject(_subject1);

      expect(
        viewModel.confirmationStatusFor(_subject1),
        Acc02ConfirmationStatus.outcomeUnknown,
      );
      expect(viewModel.needsReadback, isTrue);
      expect(viewModel.actionErrorFor(_subject1), contains('变更结果待确认'));
      expect(viewModel.actionErrorFor(_subject1), isNot(contains('没有被切换')));
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

  testWidgets('ACC-02 long mobile list scrolls independently to the last row', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final subjects = List.generate(
      25,
      (index) => Acc02Subject(
        id: 'subject-${index + 1}',
        name: 'Subject ${index + 1}',
        domainId: 'CTH',
        subjectType: '商场',
        scope: 'focus',
      ),
    );
    final repository = _FakeAcc02Repository(
      snapshot: Acc02Snapshot(
        contextState: Acc02ContextState.globalAll,
        subjectState: Acc02SubjectState.ready,
        subjects: subjects,
        selectionOnly: true,
      ),
    );

    await tester.pumpWidget(
      sharedTestApp(
        Acc02Screen(client: LumenisCoreClient(), repository: repository),
      ),
    );
    await tester.pumpAndSettle();

    const listKey = ValueKey<String>('acc02-subject-list-scroll');
    final list = find.byKey(listKey);
    expect(list, findsOneWidget);
    final listScrollable = find.descendant(
      of: list,
      matching: find.byType(Scrollable),
    );
    final position = tester.state<ScrollableState>(listScrollable).position;
    expect(position.maxScrollExtent, greaterThan(0));

    await tester.drag(list, const Offset(0, -1600));
    await tester.pumpAndSettle();
    expect(position.pixels, greaterThan(0));

    final lastRow = find.byKey(
      const ValueKey<String>('acc02-subject-subject-25'),
    );
    expect(lastRow, findsOneWidget);
    await tester.ensureVisible(lastRow);
    await tester.tap(lastRow);
    await tester.pumpAndSettle();

    expect(tester.widget<ListTile>(lastRow).selected, isTrue);
    expect(
      find.byKey(const ValueKey<String>('acc02-candidate-page-view')),
      findsOneWidget,
    );
    await tester.tap(
      find.byKey(const ValueKey<String>('acc02-close-candidates')),
    );
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
  });

  testWidgets('ACC-02 candidate sheet preserves the query and list position', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final subjects = List.generate(
      25,
      (index) => Acc02Subject(
        id: 'subject-${index + 1}',
        name: 'Subject ${index + 1}',
        domainId: 'CTH',
        subjectType: '商场',
        scope: 'focus',
      ),
    );
    await tester.pumpWidget(
      sharedTestApp(
        Acc02Screen(
          client: LumenisCoreClient(),
          repository: _FakeAcc02Repository(
            snapshot: Acc02Snapshot(
              contextState: Acc02ContextState.globalAll,
              subjectState: Acc02SubjectState.ready,
              subjects: subjects,
              selectionOnly: true,
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    final search = find.byKey(
      const ValueKey<String>('acc02-subject-search-field'),
    );
    await tester.enterText(search, 'Subject');
    await tester.pumpAndSettle();
    final list = find.byKey(
      const ValueKey<String>('acc02-subject-list-scroll'),
    );
    await tester.drag(list, const Offset(0, -1600));
    await tester.pumpAndSettle();
    final listScrollable = find.descendant(
      of: list,
      matching: find.byType(Scrollable),
    );
    final position = tester.state<ScrollableState>(listScrollable).position;
    final lastRow = find.byKey(
      const ValueKey<String>('acc02-subject-subject-25'),
    );
    await tester.ensureVisible(lastRow);
    await tester.pumpAndSettle();
    final pixelsBeforeOpen = position.pixels;
    await tester.tap(lastRow);
    await tester.pumpAndSettle();
    expect(
      find.byKey(const ValueKey<String>('acc02-close-candidates')),
      findsOneWidget,
    );
    await tester.tap(
      find.byKey(const ValueKey<String>('acc02-close-candidates')),
    );
    await tester.pumpAndSettle();

    expect(tester.widget<TextField>(search).controller!.text, 'Subject');
    expect(position.pixels, pixelsBeforeOpen);
    expect(tester.widget<ListTile>(lastRow).selected, isTrue);
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'ACC-02 phone flow browses then confirms the displayed candidate',
    (tester) async {
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
      await tester.tap(
        find.byKey(const ValueKey<String>('acc02-subject-subject-1')),
      );
      await tester.pumpAndSettle();

      final pageView = find.byKey(
        const ValueKey<String>('acc02-candidate-page-view'),
      );
      await tester.drag(pageView, const Offset(-300, 0));
      await tester.pumpAndSettle();
      expect(find.text('候选 2 / 2'), findsOneWidget);
      expect(repository.selectedIds, isEmpty);

      await tester.tap(
        find.byKey(const ValueKey<String>('acc02-previous-candidate')),
      );
      await tester.pumpAndSettle();
      expect(find.text('候选 1 / 2'), findsOneWidget);
      await tester.tap(
        find.byKey(const ValueKey<String>('acc02-next-candidate')),
      );
      await tester.pumpAndSettle();
      expect(find.text('候选 2 / 2'), findsOneWidget);
      await tester.tap(
        find.byKey(const ValueKey<String>('acc02-confirm-candidate')),
      );
      await tester.pumpAndSettle();

      expect(repository.selectedIds, [_subject2.id]);
      final continueButton = find.byKey(
        const ValueKey<String>('acc02-continue-current'),
      );
      expect(
        tester.widget<OutlinedButton>(continueButton).onPressed,
        isNotNull,
      );
      await tester.tap(continueButton);
      await tester.pumpAndSettle();
      expect(continueCalls, 1);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('ACC-02 Previous and Next work with reduced motion enabled', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(
      sharedTestApp(
        Builder(
          builder: (context) => MediaQuery(
            data: MediaQuery.of(context).copyWith(disableAnimations: true),
            child: Acc02Screen(
              client: LumenisCoreClient(),
              repository: _FakeAcc02Repository(snapshot: _globalSnapshot),
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(
      find.byKey(const ValueKey<String>('acc02-subject-subject-1')),
    );
    await tester.pumpAndSettle();
    await tester.tap(
      find.byKey(const ValueKey<String>('acc02-next-candidate')),
    );
    await tester.pumpAndSettle();
    expect(find.text('候选 2 / 2'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'ACC-02 refreshes an uncertain result after closing and restores Continue',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(390, 844));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      var continueCalls = 0;
      final repository = _FakeAcc02Repository(
        snapshot: _globalSnapshot,
        loadSequence: [_globalSnapshot, _confirmedSubject1Snapshot],
        selectionError: StateError('Connection reset while posting context'),
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
      await tester.tap(
        find.byKey(const ValueKey<String>('acc02-subject-subject-1')),
      );
      await tester.pumpAndSettle();
      await tester.tap(
        find.byKey(const ValueKey<String>('acc02-confirm-candidate')),
      );
      await tester.pumpAndSettle();
      expect(find.textContaining('变更结果待确认'), findsOneWidget);

      await tester.tap(
        find.byKey(const ValueKey<String>('acc02-close-candidates')),
      );
      await tester.pumpAndSettle();
      expect(find.text('查看范围待确认'), findsOneWidget);
      expect(find.text('全局查看范围'), findsNothing);
      expect(
        tester
            .widget<ListTile>(
              find.byKey(const ValueKey<String>('acc02-subject-subject-1')),
            )
            .onTap,
        isNull,
      );

      await tester.tap(find.byIcon(Icons.refresh));
      await tester.pumpAndSettle();
      expect(repository.loadCount, 2);
      expect(find.text('查看范围待确认'), findsNothing);
      expect(
        tester
            .widget<ListTile>(
              find.byKey(const ValueKey<String>('acc02-subject-subject-1')),
            )
            .onTap,
        isNotNull,
      );

      await tester.tap(
        find.byKey(const ValueKey<String>('acc02-subject-subject-1')),
      );
      await tester.pumpAndSettle();
      final continueButton = find.byKey(
        const ValueKey<String>('acc02-continue-current'),
      );
      expect(
        tester.widget<OutlinedButton>(continueButton).onPressed,
        isNotNull,
      );
      await tester.tap(continueButton);
      await tester.pumpAndSettle();
      expect(continueCalls, 1);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('ACC-02 no-match search can be cleared to restore the rows', (
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

    final search = find.byKey(
      const ValueKey<String>('acc02-subject-search-field'),
    );
    await tester.enterText(search, 'no matching subject');
    await tester.pumpAndSettle();
    expect(find.text('没有匹配项'), findsOneWidget);
    expect(find.text(_subject1.name), findsNothing);

    await tester.tap(find.byTooltip('清除搜索'));
    await tester.pumpAndSettle();

    expect(tester.widget<TextField>(search).controller!.text, isEmpty);
    expect(find.text(_subject1.name), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'ACC-02 blocked, unavailable and unknown lists retry without zero',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(390, 844));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      for (final state in [
        Acc02SubjectState.blocked,
        Acc02SubjectState.unavailable,
        Acc02SubjectState.unknown,
      ]) {
        final repository = _FakeAcc02Repository(
          snapshot: Acc02Snapshot(
            contextState: Acc02ContextState.globalAll,
            subjectState: state,
            subjects: const [],
            selectionOnly: true,
          ),
        );
        await tester.pumpWidget(
          sharedTestApp(
            Acc02Screen(
              key: ValueKey<String>('acc02-error-${state.name}'),
              client: LumenisCoreClient(),
              repository: repository,
            ),
          ),
        );
        await tester.pumpAndSettle();

        expect(find.text('0'), findsNothing);
        expect(
          tester
              .widget<TextField>(
                find.byKey(
                  const ValueKey<String>('acc02-subject-search-field'),
                ),
              )
              .enabled,
          isFalse,
        );
        final retry = find.byIcon(Icons.refresh);
        expect(retry, findsOneWidget);
        await tester.tap(retry);
        await tester.pumpAndSettle();
        expect(repository.loadCount, 2);
        expect(tester.takeException(), isNull);
      }
    },
  );

  testWidgets('ACC-02 context refresh is disabled during confirmation', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final gate = Completer<void>();

    await tester.pumpWidget(
      sharedTestApp(
        Acc02Screen(
          client: LumenisCoreClient(),
          repository: _FakeAcc02Repository(
            snapshot: _snapshot(
              contextState: Acc02ContextState.unavailable,
              contextDomainId: null,
              selectedSubjectId: null,
            ),
            selectionGate: gate.future,
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(
      find.byKey(const ValueKey<String>('acc02-subject-subject-1')),
    );
    await tester.pump();
    await tester.ensureVisible(find.byType(FilledButton));
    await tester.pumpAndSettle();
    await tester.tap(find.byType(FilledButton));
    await tester.pump();

    final refreshButton = tester.widget<TextButton>(
      find.ancestor(
        of: find.byIcon(Icons.refresh),
        matching: find.byType(TextButton),
      ),
    );
    expect(refreshButton.onPressed, isNull);

    gate.complete();
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
  });

  testWidgets('ACC-02 failure panel stays usable at 320px and 200% text', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(320, 720));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final repository = _FakeAcc02Repository(
      snapshot: _readySnapshot,
      loadError: StateError('Core unavailable'),
    );

    await tester.pumpWidget(
      sharedTestApp(
        Builder(
          builder: (context) => MediaQuery(
            data: MediaQuery.of(
              context,
            ).copyWith(textScaler: const TextScaler.linear(2)),
            child: Acc02Screen(
              client: LumenisCoreClient(),
              repository: repository,
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('主体目录暂时离线'), findsOneWidget);
    expect(find.byIcon(Icons.refresh), findsOneWidget);
    expect(tester.takeException(), isNull);
    await tester.tap(find.byIcon(Icons.refresh));
    await tester.pumpAndSettle();
    expect(repository.loadCount, 2);
    expect(tester.takeException(), isNull);
  });

  testWidgets('ACC-02 list state and selected detail fit at 320px and 200%', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(320, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    Widget largeTextApp(Widget child) => sharedTestApp(
      Builder(
        builder: (context) => MediaQuery(
          data: MediaQuery.of(
            context,
          ).copyWith(textScaler: const TextScaler.linear(2)),
          child: child,
        ),
      ),
    );

    await tester.pumpWidget(
      largeTextApp(
        Acc02Screen(
          key: const ValueKey<String>('acc02-large-blocked'),
          client: LumenisCoreClient(),
          repository: _FakeAcc02Repository(
            snapshot: const Acc02Snapshot(
              contextState: Acc02ContextState.unavailable,
              subjectState: Acc02SubjectState.blocked,
              subjects: [],
              selectionOnly: true,
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('主体列表暂不可访问'), findsOneWidget);
    expect(tester.takeException(), isNull);

    final longSubject = Acc02Subject(
      id: 'subject-long-mobile',
      name: List.filled(5, 'Long selected Subject name').join(' '),
      domainId: 'CTH',
      subjectType: List.filled(3, '商场与商业运营类型').join(' '),
      scope: 'focus',
    );
    await tester.pumpWidget(
      largeTextApp(
        Acc02Screen(
          key: const ValueKey<String>('acc02-large-ready'),
          client: LumenisCoreClient(),
          repository: _FakeAcc02Repository(
            snapshot: Acc02Snapshot(
              contextState: Acc02ContextState.globalAll,
              subjectState: Acc02SubjectState.ready,
              subjects: [longSubject],
              selectionOnly: true,
            ),
          ),
          onContinue: () {},
        ),
      ),
    );
    await tester.pumpAndSettle();
    final row = find.byKey(
      const ValueKey<String>('acc02-subject-subject-long-mobile'),
    );
    final pageScroll = tester.widget<SingleChildScrollView>(
      find.byKey(const ValueKey<String>('acc02-page-scroll')),
    );
    final pageController = pageScroll.controller!;
    expect(pageController.position.maxScrollExtent, greaterThan(0));
    pageController.jumpTo(pageController.position.maxScrollExtent);
    await tester.pumpAndSettle();
    await tester.ensureVisible(row);
    await tester.pumpAndSettle();
    final rowRect = tester.getRect(row);
    expect(rowRect.overlaps(const Rect.fromLTWH(0, 0, 320, 900)), isTrue);
    await tester.tapAt(Offset(rowRect.center.dx, rowRect.top + 36));
    await tester.pumpAndSettle();

    expect(
      find.byKey(const ValueKey<String>('acc02-confirm-candidate')),
      findsOneWidget,
    );
    expect(find.text(longSubject.name), findsNWidgets(2));
    expect(tester.takeException(), isNull);
  });

  testWidgets('ACC-02 long selected Subject wraps in the desktop detail pane', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1280, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final longSubject = Acc02Subject(
      id: 'subject-long',
      name: List.filled(9, 'Long selected Subject name').join(' '),
      domainId: 'CTH',
      subjectType: List.filled(5, '商场与商业运营类型').join(' '),
      scope: 'focus',
    );

    await tester.pumpWidget(
      _largeTextApp(
        Acc02Screen(
          client: LumenisCoreClient(),
          repository: _FakeAcc02Repository(
            snapshot: Acc02Snapshot(
              contextState: Acc02ContextState.globalAll,
              subjectState: Acc02SubjectState.ready,
              subjects: [longSubject],
              selectionOnly: true,
            ),
          ),
          onContinue: () {},
        ),
      ),
    );
    await tester.pumpAndSettle();
    final longRow = find.byKey(
      const ValueKey<String>('acc02-subject-subject-long'),
    );
    final pageScroll = tester.widget<SingleChildScrollView>(
      find.byKey(const ValueKey<String>('acc02-page-scroll')),
    );
    pageScroll.controller!.jumpTo(
      pageScroll.controller!.position.maxScrollExtent,
    );
    await tester.pumpAndSettle();
    await tester.ensureVisible(longRow);
    await tester.pumpAndSettle();
    final rowRect = tester.getRect(longRow);
    expect(rowRect.overlaps(const Rect.fromLTWH(0, 0, 1280, 900)), isTrue);
    await tester.tapAt(Offset(rowRect.center.dx, rowRect.top + 36));
    await tester.pumpAndSettle();

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
        await tester.tap(
          find.byKey(const ValueKey<String>('acc02-subject-subject-1')),
        );
        await tester.pumpAndSettle();

        final button = tester.widget<OutlinedButton>(
          find.byType(OutlinedButton),
        );
        expect(button.onPressed, isNull);
        await tester.tap(
          find.byKey(const ValueKey<String>('acc02-close-candidates')),
        );
        await tester.pumpAndSettle();
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
        snapshot: _globalSnapshot,
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
      await tester.tap(
        find.byKey(const ValueKey<String>('acc02-subject-subject-1')),
      );
      await tester.pump();

      expect(
        tester.widget<OutlinedButton>(find.byType(OutlinedButton)).onPressed,
        isNull,
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

      final nextCandidate = tester.widget<TextButton>(
        find.byKey(const ValueKey<String>('acc02-next-candidate')),
      );
      expect(nextCandidate.onPressed, isNull);
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
      expect(find.textContaining('服务器拒绝了这次范围变更'), findsWidgets);
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
    await tester.tap(
      find.byKey(const ValueKey<String>('acc02-subject-subject-2')),
    );
    await tester.pumpAndSettle();
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
        snapshot: _globalSnapshot,
        selectionGate: gate.future,
        snapshotAfterSelection: _confirmedSubject1Snapshot,
      );

      await tester.pumpWidget(
        sharedTestApp(
          Acc02Screen(client: LumenisCoreClient(), repository: repository),
        ),
      );
      await tester.pumpAndSettle();
      await tester.tap(
        find.byKey(const ValueKey<String>('acc02-subject-subject-1')),
      );
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

const _confirmedSubject1Snapshot = Acc02Snapshot(
  contextState: Acc02ContextState.focused,
  subjectState: Acc02SubjectState.ready,
  subjects: [_subject1, _subject2],
  selectionOnly: true,
  contextDomainId: 'CTH',
  selectedSubjectId: 'subject-1',
);

Widget _largeTextApp(Widget child) => sharedTestApp(
  Builder(
    builder: (context) => MediaQuery(
      data: MediaQuery.of(
        context,
      ).copyWith(textScaler: const TextScaler.linear(2)),
      child: child,
    ),
  ),
);

class _FakeAcc02Repository implements Acc02Repository {
  _FakeAcc02Repository({
    required this.snapshot,
    this.selectionGate,
    this.snapshotAfterSelection,
    this.selectionError,
    this.loadGate,
    this.loadError,
    List<Object>? loadSequence,
  }) : _loadSequence = loadSequence == null
           ? null
           : List<Object>.of(loadSequence);

  Acc02Snapshot snapshot;
  final Future<void>? selectionGate;
  final Acc02Snapshot? snapshotAfterSelection;
  final Object? selectionError;
  final Future<void>? loadGate;
  final Object? loadError;
  final List<Object>? _loadSequence;
  final selectedIds = <String>[];
  int loadCount = 0;

  @override
  Future<Acc02Snapshot> load() async {
    loadCount++;
    final gate = loadGate;
    if (gate != null) await gate;
    if (_loadSequence != null && _loadSequence.isNotEmpty) {
      final result = _loadSequence.removeAt(0);
      if (result is Acc02Snapshot) {
        snapshot = result;
        return result;
      }
      throw result;
    }
    if (loadError != null) throw loadError!;
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
