import 'dart:async';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/features/shared/sh04/sh04_screen.dart';

import '../shared_test_support.dart';

import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/features/shared/sh04/sh04_repository.dart';
import 'package:lumenis_app/features/shared/sh04/sh04_snapshot.dart';
import 'package:lumenis_app/features/shared/sh04/sh04_view_model.dart';

void main() {
  late _ControlledRepository repository;
  late Sh04ViewModel model;
  setUp(() {
    repository = _ControlledRepository();
    model = Sh04ViewModel(repository: repository);
  });

  Future<void> seed({bool more = true}) async {
    final pending = model.refresh();
    repository.reads.last.complete(_snapshot('old', more: more));
    await pending;
  }

  test(
    'direct opening selects the exact version and clears previous selection',
    () async {
      await seed();
      final opening = model.openArtifact('chosen');
      expect(model.exports, isEmpty);
      repository.openings.single.complete(_item('chosen'));
      await opening;
      expect(model.selected?.internalId, 'chosen');
      expect(model.phase, Sh04LoadPhase.ready);
    },
  );

  test(
    'direct opening rejects a mismatched version and late denied-context results',
    () async {
      final first = model.openArtifact('old');
      final second = model.openArtifact('new');
      repository.openings[1].completeError(_denied);
      await second;
      repository.openings[0].complete(_item('old'));
      await first;
      expect(model.exports, isEmpty);
      expect(model.failureKind, Sh04FailureKind.permissionDenied);
      final mismatch = model.openArtifact('expected');
      repository.openings.last.complete(_item('wrong'));
      await mismatch;
      expect(model.exports, isEmpty);
      expect(model.phase, Sh04LoadPhase.failed);
    },
  );

  testWidgets(
    'screen client replacement hides old context and ignores its late read',
    (tester) async {
      final oldRepository = _ControlledRepository();
      final nextRepository = _ControlledRepository();
      final oldClient = LumenisCoreClient();
      final nextClient = LumenisCoreClient();
      await tester.pumpWidget(
        sharedTestApp(Sh04Screen(client: oldClient, repository: oldRepository)),
      );
      await tester.pumpWidget(
        sharedTestApp(
          Sh04Screen(client: nextClient, repository: nextRepository),
        ),
      );
      nextRepository.reads.single.complete(_snapshot('current-context'));
      await tester.pumpAndSettle();
      oldRepository.reads.single.complete(_snapshot('retired-context'));
      await tester.pumpAndSettle();
      expect(find.text('current-context'), findsOneWidget);
      expect(find.text('retired-context'), findsNothing);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('screen disposal ignores pending read without framework errors', (
    tester,
  ) async {
    final source = _ControlledRepository();
    await tester.pumpWidget(
      sharedTestApp(
        Sh04Screen(client: LumenisCoreClient(), repository: source),
      ),
    );
    await tester.pumpWidget(const SizedBox.shrink());
    source.reads.single.complete(_snapshot('late'));
    await tester.pumpAndSettle();
    expect(find.text('late'), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets('old editor cannot submit into a replaced repository', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1280, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final first = _ControlledRepository();
    final second = _ControlledRepository();
    await tester.pumpWidget(
      sharedTestApp(Sh04Screen(client: LumenisCoreClient(), repository: first)),
    );
    first.reads.single.complete(_snapshot('first'));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('sh04-create-report')));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('sh04-report-title')), 'draft');
    await tester.enterText(
      find.byKey(const Key('sh04-report-markdown')),
      'body',
    );
    await tester.pumpWidget(
      sharedTestApp(
        Sh04Screen(client: LumenisCoreClient(), repository: second),
      ),
    );
    second.reads.single.complete(_snapshot('second'));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('sh04-save-report')));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));
    expect(first.saves, isEmpty);
    expect(second.saves, isEmpty);
    expect(tester.takeException(), isNull);
  });

  test('late refresh success cannot replace the newest list', () async {
    final first = model.refresh();
    final second = model.refresh();
    repository.reads[1].complete(_snapshot('new'));
    await second;
    repository.reads[0].complete(_snapshot('old'));
    await first;
    expect(model.exports.single.internalId, 'new');
    expect(model.phase, Sh04LoadPhase.ready);
  });

  test('late refresh failure cannot replace newer success', () async {
    final first = model.refresh();
    final second = model.refresh();
    repository.reads[1].complete(_snapshot('new'));
    await second;
    repository.reads[0].completeError(const FormatException('old failure'));
    await first;
    expect(model.exports.single.internalId, 'new');
    expect(model.failureKind, isNull);
  });

  test('late success cannot undo current permission denial', () async {
    final first = model.refresh();
    final second = model.refresh();
    repository.reads[1].completeError(_denied);
    await second;
    repository.reads[0].complete(_snapshot('old'));
    await first;
    expect(model.exports, isEmpty);
    expect(model.failureKind, Sh04FailureKind.permissionDenied);
  });

  test(
    'old page cannot overwrite refresh or clear newer page busy state',
    () async {
      await seed();
      final page = model.loadMore();
      final refresh = model.refresh();
      repository.reads[2].complete(_snapshot('new', more: true));
      await refresh;
      final newerPage = model.loadMore();
      repository.reads[1].complete(_snapshot('old-page'));
      await page;
      expect(model.exports.single.internalId, 'new');
      expect(model.operationBusy, isTrue);
      repository.reads[3].complete(_snapshot('new-page'));
      await newerPage;
      expect(model.exports.map((e) => e.internalId), ['new', 'new-page']);
      expect(model.operationBusy, isFalse);
      expect(repository.cursors, [null, 'cursor-old', null, 'cursor-new']);
    },
  );

  test('late page error cannot poison refreshed state', () async {
    await seed();
    final page = model.loadMore();
    final refresh = model.refresh();
    repository.reads[2].complete(_snapshot('new'));
    await refresh;
    repository.reads[1].completeError(_denied);
    await page;
    expect(model.exports.single.internalId, 'new');
    expect(model.loadMoreFailureKind, isNull);
    expect(model.phase, Sh04LoadPhase.ready);
  });

  test('transient page failure preserves items and can retry', () async {
    await seed();
    final page = model.loadMore();
    repository.reads[1].completeError(const FormatException('bad page'));
    await page;
    expect(model.exports.single.internalId, 'old');
    expect(model.loadMoreFailureKind, Sh04FailureKind.response);
    final retry = model.loadMore();
    repository.reads[2].complete(_snapshot('next'));
    await retry;
    expect(model.exports.map((e) => e.internalId), ['old', 'next']);
    expect(model.loadMoreFailureKind, isNull);
  });

  for (final error in <Object>[
    _denied,
    const LumenisCoreException('denied', statusCode: 401),
    const Sh04ScopeError(Sh04ScopeErrorKind.denied),
  ]) {
    test(
      'page access failure hides previously shown content: $error',
      () async {
        await seed();
        final page = model.loadMore();
        repository.reads[1].completeError(error);
        await page;
        expect(model.exports, isEmpty);
        expect(model.selected, isNull);
        expect(model.operationBusy, isFalse);
        final retry = model.refresh();
        repository.reads[2].complete(_snapshot('recovered'));
        await retry;
        expect(model.phase, Sh04LoadPhase.ready);
        expect(model.exports.single.internalId, 'recovered');
      },
    );
  }

  test('reopen cannot restore old selection after refresh', () async {
    await seed();
    final item = model.exports.single;
    final opening = model.reopen(item);
    final assertion = expectLater(
      opening,
      throwsA(isA<LumenisCoreException>()),
    );
    final refresh = model.refresh();
    repository.reads[1].complete(_snapshot('new'));
    await refresh;
    repository.openings.single.complete(item);
    await assertion;
    expect(model.selected, isNull);
    expect(model.exports.single.internalId, 'new');
  });

  test(
    'selection changes are serialized and exact selected version is retained',
    () async {
      await seed();
      final item = model.exports.single;
      final opening = model.reopen(item);
      await expectLater(
        model.reopen(_item('other')),
        throwsA(isA<LumenisCoreException>()),
      );
      expect(repository.openings, hasLength(1));
      repository.openings.single.complete(item);
      await opening;
      expect(model.selected, item);
      final second = model.reopen(_item('other'));
      repository.openings.last.complete(_item('other'));
      await second;
      expect(model.selected!.internalId, 'other');
    },
  );

  test('reopen denial clears selected content', () async {
    await seed();
    final opening = model.reopen(model.exports.single);
    final assertion = expectLater(
      opening,
      throwsA(isA<LumenisCoreException>()),
    );
    repository.openings.single.completeError(_denied);
    await assertion;
    expect(model.exports, isEmpty);
    expect(model.failureKind, Sh04FailureKind.permissionDenied);
    expect(model.operationBusy, isFalse);
  });

  test('disposed pending read never publishes or notifies', () async {
    var notifications = 0;
    model.addListener(() => notifications++);
    final pending = model.refresh();
    final before = notifications;
    model.dispose();
    repository.reads.single.complete(_snapshot('late'));
    await pending;
    expect(model.snapshot, isNull);
    expect(notifications, before);
    await model.refresh();
    expect(repository.reads, hasLength(1));
  });

  test(
    'disposed pending reopen cannot return data or mutate selection',
    () async {
      await seed();
      final item = model.exports.single;
      final pending = model.reopen(item);
      final assertion = expectLater(
        pending,
        throwsA(isA<LumenisCoreException>()),
      );
      model.dispose();
      repository.openings.single.complete(item);
      await assertion;
      expect(model.selected, isNull);
    },
  );

  test('late export bytes cannot escape a refreshed context', () async {
    await seed();
    final exporting = model.export(model.exports.single, 'md');
    final assertion = expectLater(
      exporting,
      throwsA(isA<LumenisCoreException>()),
    );
    final refresh = model.refresh();
    repository.reads[1].complete(_snapshot('new'));
    await refresh;
    repository.exports.single.complete(
      SavedWorkExportFile(
        bytes: Uint8List.fromList([65]),
        mediaType: 'text/markdown',
        filename: 'report.md',
      ),
    );
    await assertion;
  });

  test(
    'save completed in old context is not published as current success',
    () async {
      await seed();
      final saving = model.saveReport(title: 'draft', markdown: 'body');
      final assertion = expectLater(
        saving,
        throwsA(isA<LumenisCoreException>()),
      );
      final refresh = model.refresh();
      repository.reads[1].complete(_snapshot('new'));
      await refresh;
      repository.saves.single.complete(_item('saved'));
      await assertion;
      expect(model.exports.single.internalId, 'new');
    },
  );
}

const _denied = LumenisCoreException('access denied', statusCode: 403);
Sh04Export _item(String id) => Sh04Export(
  internalId: id,
  title: id,
  state: Sh04ExportState.ready,
  markdown: 'Synthetic $id',
  sha256: id,
  workId: 'work-$id',
  version: 1,
  parentArtifactId: null,
  citations: const [],
  generatedAt: '',
);
Sh04Snapshot _snapshot(String id, {bool more = false}) => Sh04Snapshot(
  scope: Sh04Scope.sharedWorkspace,
  exports: [_item(id)],
  verificationComplete: true,
  unverifiedCandidates: 0,
  hasMore: more,
  nextCursor: more ? 'cursor-$id' : null,
);

class _ControlledRepository implements Sh04Repository {
  final reads = <Completer<Sh04Snapshot>>[];
  final cursors = <String?>[];
  final openings = <Completer<Sh04Export>>[];
  final saves = <Completer<Sh04Export>>[];
  final exports = <Completer<SavedWorkExportFile>>[];
  @override
  Future<Sh04Snapshot> loadExports({String? cursor}) {
    cursors.add(cursor);
    final pending = Completer<Sh04Snapshot>();
    reads.add(pending);
    return pending.future;
  }

  @override
  Future<Sh04Export> reopen(String artifactId) {
    final pending = Completer<Sh04Export>();
    openings.add(pending);
    return pending.future;
  }

  @override
  Future<Sh04Export> saveReport({
    required String title,
    required String markdown,
    required String requestId,
  }) {
    final pending = Completer<Sh04Export>();
    saves.add(pending);
    return pending.future;
  }

  @override
  Future<Sh04Export> reviseReport({
    required Sh04Export parent,
    required String title,
    required String markdown,
    required String reason,
    required String requestId,
  }) => throw UnimplementedError();
  @override
  Future<SavedWorkExportFile> export({
    required String artifactId,
    required String format,
  }) {
    final pending = Completer<SavedWorkExportFile>();
    exports.add(pending);
    return pending.future;
  }
}
