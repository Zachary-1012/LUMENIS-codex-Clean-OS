import 'dart:async';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/features/shared/sh02/sh02_office_controller.dart';
import 'package:lumenis_app/features/shared/sh02/sh02_snapshot.dart';
import 'office_test_support.dart';

void main() {
  for (final status in [401, 403, 404, 410]) {
    test('save rejection $status clears source and pending recovery', () async {
      final repo = _FailingOffice();
      final controller = _controller(repo);
      addTearDown(controller.dispose);
      await controller.load();
      controller.change(controller.objects.first, 'Private correction');
      repo.saveFailure = _rejected(status);
      await controller.save('Correct the original');
      _expectUnavailable(controller);
      await controller.checkSave();
      expect(repo.historyCalls, 0);
      expect(repo.latest, 1);
      expect(repo.saveCalls, 1);
    });

    test(
      'post-commit readback rejection $status hides the unconfirmed version',
      () async {
        final repo = _FailingOffice();
        final controller = _controller(repo);
        addTearDown(controller.dispose);
        await controller.load();
        controller.change(controller.objects.first, 'Committed correction');
        repo.reopenFailure = _rejected(status);
        await controller.save('Correct the original');
        expect(repo.latest, 2);
        expect(controller.source.version, 1);
        _expectUnavailable(controller);
        final priorReopens = repo.reopenCalls;
        repo.reopenFailure = null;
        await controller.checkSave();
        expect(repo.reopenCalls, priorReopens);
        expect(repo.saveCalls, 1);
      },
    );

    test(
      'download rejection $status clears original and comparison content',
      () async {
        final repo = _FailingOffice();
        final controller = _controller(repo);
        addTearDown(controller.dispose);
        await controller.load();
        controller.change(controller.objects.first, 'Private correction');
        repo.externalRevision('Newer private original');
        await controller.save('Correct the original');
        await controller.compareLatest();
        expect(controller.comparisons, isNotEmpty);
        expect(controller.comparisonSource, isNotNull);
        repo.downloadFailure = _rejected(status);
        expect(await controller.download(), isNull);
        _expectUnavailable(controller);
        controller.adoptComparison({officeObjectId(1)});
        _expectUnavailable(controller);
        expect(controller.source.version, 1);
      },
    );
  }

  test(
    'revocation while checking unknown save clears its pending receipt',
    () async {
      final repo = _FailingOffice()..loseAcknowledgement = true;
      final controller = _controller(repo);
      addTearDown(controller.dispose);
      await controller.load();
      controller.change(controller.objects.first, 'Private correction');
      await controller.save('Correct the original');
      expect(controller.saveUnknown, isTrue);
      expect(controller.dirty, isTrue);
      repo.historyFailure = _rejected(403);
      await controller.checkSave();
      _expectUnavailable(controller);
      repo.historyFailure = null;
      await controller.checkSave();
      expect(repo.historyCalls, 1);
      expect(repo.saveCalls, 1);
    },
  );

  test(
    'object read denied after save acknowledgement clears the pending save',
    () async {
      final repo = _FailingOffice();
      final controller = _controller(repo);
      addTearDown(controller.dispose);
      await controller.load();
      controller.change(controller.objects.first, 'Private correction');
      repo.readFailure = _rejected(410);
      await controller.save('Correct the original');
      expect(repo.latest, 2);
      _expectUnavailable(controller);
      final priorReads = repo.readCalls;
      repo.readFailure = null;
      await controller.checkSave();
      expect(repo.readCalls, priorReads);
      expect(repo.saveCalls, 1);
    },
  );

  test(
    'confirmed absence retries the frozen request and keeps uncertainty until readback',
    () async {
      final repo = _FailingOffice()
        ..saveFailure = TimeoutException('Response lost');
      final controller = _controller(repo);
      addTearDown(controller.dispose);
      await controller.load();
      controller.change(controller.objects.first, 'Retained correction');
      await controller.save('Correct the original');
      expect(controller.saveUnknown, isTrue);
      expect(controller.problem, 'unknownSave');
      expect(controller.edits.values.single, 'Retained correction');
      expect(controller.page, isNotNull);
      await controller.save('Do not replay');
      await controller.checkSave();
      expect(repo.saveCalls, 1);
      expect(repo.historyCalls, 1);
      expect(controller.saveUnknown, isTrue);
      expect(controller.notice, 'notFound');
      expect(controller.edits.values.single, 'Retained correction');
      repo.saveFailure = null;
      repo.saveEntered = Completer<void>();
      repo.saveRelease = Completer<void>();
      final retry = controller.checkSave();
      await repo.saveEntered!.future.timeout(const Duration(seconds: 2));
      expect(controller.busy, isTrue);
      expect(controller.saveUnknown, isTrue);
      expect(controller.canSave, isFalse);
      expect(controller.canEdit, isFalse);
      expect(controller.edits.values.single, 'Retained correction');
      expect(repo.attempts.last, repo.attempts.first);
      repo.saveRelease!.complete();
      await retry;
      expect(repo.saveCalls, 2);
      expect(repo.historyCalls, 2);
      expect(repo.latest, 2);
      expect(controller.source.version, 2);
      expect(controller.notice, 'saved');
      expect(controller.saveUnknown, isFalse);
      expect(controller.edits, isEmpty);
      expect(repo.values[2]!.first['value'], 'Retained correction');
      expect(repo.values[1]!.first['value'], 'Original writing 1');
    },
  );

  test(
    'repeated lost retries retain request, commands, reason and signature consent',
    () async {
      final repo = _FailingOffice()
        ..signed = true
        ..saveFailure = TimeoutException('Not submitted');
      final controller = _controller(repo);
      addTearDown(controller.dispose);
      await controller.load();
      controller.change(controller.objects.first, 'Exact original correction');
      await controller.save('  Original reason  ', invalidateSignature: true);
      await controller.checkSave();
      await controller.checkSave();
      expect(repo.saveCalls, 2);
      expect(controller.saveUnknown, isTrue);
      expect(controller.notice, isNull);
      controller.change(
        controller.objects.first,
        'Blocked different correction',
      );
      await controller.save('Different reason');
      expect(repo.saveCalls, 2);
      await controller.checkSave();
      expect(repo.saveCalls, 2); // Reconcile again before another exact replay.
      repo.saveFailure = null;
      await controller.checkSave();
      expect(repo.saveCalls, 3);
      expect(
        repo.attempts.every(
          (attempt) => attempt['requestId'] == repo.attempts.first['requestId'],
        ),
        isTrue,
      );
      expect(repo.attempts[1], repo.attempts.first);
      expect(repo.attempts[2], repo.attempts.first);
      expect(repo.attempts.last['reason'], 'Original reason');
      expect(repo.invalidateSignature, isTrue);
      expect(repo.latest, 2);
      expect(controller.notice, 'saved');
    },
  );

  test(
    'an incomplete history scan never authorizes an uncertain request replay',
    () async {
      final repo = _FailingOffice()
        ..historyComplete = false
        ..saveFailure = TimeoutException('No response');
      final controller = _controller(repo);
      addTearDown(controller.dispose);
      await controller.load();
      controller.change(controller.objects.first, 'Preserved correction');
      await controller.save('Original reason');
      await controller.checkSave();
      await controller.checkSave();
      expect(repo.saveCalls, 1);
      expect(controller.saveUnknown, isTrue);
      expect(controller.edits.values.single, 'Preserved correction');
      repo.historyComplete = true;
      repo.saveFailure = null;
      await controller.checkSave();
      expect(repo.saveCalls, 1);
      await controller.checkSave();
      expect(repo.saveCalls, 2);
      expect(controller.source.version, 2);
    },
  );

  test(
    'history verification covers every page before a missing request can replay',
    () async {
      final repo = _FailingOffice()
        ..saveFailure = TimeoutException('No response');
      final controller = _controller(repo);
      addTearDown(controller.dispose);
      await controller.load();
      controller.change(controller.objects.first, 'Paginated correction');
      await controller.save('Original reason');
      repo.historyScript.addAll([
        const Sh02OfficeHistoryPage([], 'page-2', false),
        const Sh02OfficeHistoryPage([], null, true),
      ]);
      await controller.checkSave();
      expect(controller.notice, 'checkMore');
      await controller.checkSave();
      expect(controller.notice, 'notFound');
      expect(repo.saveCalls, 1);
      expect(repo.historyCursors, [null, 'page-2']);
      repo.saveFailure = null;
      await controller.checkSave();
      expect(repo.saveCalls, 1); // Prior page was not fully verified.
      await controller.checkSave();
      expect(repo.saveCalls, 2);
      expect(controller.notice, 'saved');
    },
  );

  test(
    'a late original commit is reopened on the next check without replay',
    () async {
      final repo = _FailingOffice()
        ..saveFailure = TimeoutException('No response');
      final controller = _controller(repo);
      addTearDown(controller.dispose);
      await controller.load();
      controller.change(controller.objects.first, 'Late original correction');
      await controller.save('Original reason');
      await controller.checkSave();
      expect(controller.notice, 'notFound');
      await repo.commitAttempt(0);
      await controller.checkSave();
      expect(repo.saveCalls, 1);
      expect(repo.latest, 2);
      expect(controller.source.version, 2);
      expect(controller.notice, 'saved');
      expect(controller.saveUnknown, isFalse);
    },
  );

  for (final status in [401, 403, 404, 410]) {
    test(
      'original replay still enforces permission rejection $status',
      () async {
        final repo = _FailingOffice()
          ..saveFailure = TimeoutException('No response');
        final controller = _controller(repo);
        addTearDown(controller.dispose);
        await controller.load();
        controller.change(controller.objects.first, 'Private correction');
        await controller.save('Original reason');
        await controller.checkSave();
        repo.saveFailure = _rejected(status);
        await controller.checkSave();
        expect(repo.saveCalls, 2);
        expect(repo.attempts.last, repo.attempts.first);
        expect(repo.latest, 1);
        _expectUnavailable(controller);
        await controller.checkSave();
        expect(repo.saveCalls, 2);
      },
    );
  }

  test(
    'replayed acknowledgement still requires independent readback',
    () async {
      final repo = _FailingOffice()
        ..saveFailure = TimeoutException('No response');
      final controller = _controller(repo);
      addTearDown(controller.dispose);
      await controller.load();
      controller.change(controller.objects.first, 'Unconfirmed correction');
      await controller.save('Original reason');
      await controller.checkSave();
      repo.saveFailure = null;
      repo.reopenFailure = const LumenisCoreException(
        'Readback offline',
        statusCode: 503,
      );
      await controller.checkSave();
      expect(repo.latest, 2);
      expect(controller.source.version, 1);
      expect(controller.saveUnknown, isTrue);
      expect(controller.problem, 'unknownSave');
      expect(controller.notice, isNull);
      repo.reopenFailure = null;
      await controller.checkSave();
      expect(repo.saveCalls, 2);
      expect(controller.source.version, 2);
      expect(controller.notice, 'saved');
    },
  );

  test(
    'server readback failure keeps the committed candidate for read-only recovery',
    () async {
      final repo = _FailingOffice()
        ..reopenFailure = const LumenisCoreException(
          'Temporarily unavailable',
          statusCode: 503,
        );
      final controller = _controller(repo);
      addTearDown(controller.dispose);
      await controller.load();
      controller.change(controller.objects.first, 'Retained correction');
      await controller.save('Correct the original');
      expect(repo.latest, 2);
      expect(controller.saveUnknown, isTrue);
      expect(controller.edits.values.single, 'Retained correction');
      repo.reopenFailure = null;
      await controller.checkSave();
      expect(controller.source.version, 2);
      expect(controller.notice, 'saved');
      expect(controller.saveUnknown, isFalse);
      expect(repo.saveCalls, 1);
      expect(repo.historyCalls, 0);
    },
  );

  test('download transport failure preserves current writing', () async {
    final repo = _FailingOffice()
      ..downloadFailure = TimeoutException('Download lost');
    final controller = _controller(repo);
    addTearDown(controller.dispose);
    await controller.load();
    controller.change(controller.objects.first, 'Retained correction');
    expect(await controller.download(), isNull);
    expect(controller.problem, 'downloadFailed');
    expect(controller.page, isNotNull);
    expect(controller.edits.values.single, 'Retained correction');
    expect(controller.canSave, isTrue);
    expect(controller.saveUnknown, isFalse);
  });

  test(
    'edits on multiple object pages remain one atomic versioned save',
    () async {
      final repo = OfficeTestRepository(count: 101);
      final controller = Sh02OfficeController(
        repository: repo,
        source: repo.original,
      );
      addTearDown(controller.dispose);
      await controller.load();
      controller.change(controller.objects.first, 'First revision');
      await controller.load(more: true);
      controller.change(controller.objects.last, 'Last revision');
      expect(controller.objects, hasLength(101));
      expect(repo.readOffsets, [0, 100]);
      expect(controller.edits, hasLength(2));
      await controller.save('Correct two passages');
      expect(controller.source.version, 2);
      expect(controller.dirty, isFalse);
      expect(controller.notice, 'saved');
      expect(repo.requests.single, hasLength(2));
      expect(repo.requests.single.first, {
        'object_id': officeObjectId(1),
        'operation': 'replace_text',
        'expected_value': 'Original writing 1',
        'value': 'First revision',
      });
      expect(repo.values[1]!.first['value'], 'Original writing 1');
      expect(repo.values[2]!.last['value'], 'Last revision');
    },
  );

  test(
    'number boolean and formula commands keep their exact value types',
    () async {
      final repo = OfficeTestRepository(format: 'xlsx');
      repo.values[1] = [
        officeObject(
          1,
          kind: 'cell_number',
          value: '12',
          location: {'cell': 'B1', 'sheet_name': 'Original data'},
        ),
        officeObject(2, kind: 'cell_boolean', value: '0'),
        officeObject(3, kind: 'cell_formula', value: 'SUM(B1:B2)'),
      ];
      final controller = Sh02OfficeController(
        repository: repo,
        source: repo.original,
      );
      addTearDown(controller.dispose);
      await controller.load();
      controller.change(controller.objects[0], 'NaN');
      expect(controller.valid, isFalse);
      await controller.save('Invalid numeric value');
      expect(repo.requests, isEmpty);
      controller.change(controller.objects[0], '21.5');
      controller.change(controller.objects[1], true);
      controller.change(controller.objects[2], '=SUM(B1:B2)*2');
      await controller.save('Update inputs and formula');
      expect(repo.requests.single.map((c) => c['operation']), [
        'set_number',
        'set_boolean',
        'replace_formula',
      ]);
      expect(repo.requests.single[1]['expected_value'], '0');
      expect(repo.requests.single[1]['value'], true);
      expect(controller.page!.formulaRecalculationNeeded, isTrue);
    },
  );

  test(
    'an unconfirmed write is recovered by reading history and never re-posted',
    () async {
      final repo = OfficeTestRepository()..loseAcknowledgement = true;
      final controller = Sh02OfficeController(
        repository: repo,
        source: repo.original,
      );
      addTearDown(controller.dispose);
      await controller.load();
      controller.change(controller.objects.first, 'Retained writing');
      await controller.save('Correct a passage');
      expect(controller.saveUnknown, isTrue);
      expect(controller.dirty, isTrue);
      expect(controller.canSave, isFalse);
      await controller.save('Do not replay');
      await controller.checkSave();
      expect(repo.requests, hasLength(1));
      expect(controller.source.version, 2);
      expect(controller.saveUnknown, isFalse);
      expect(controller.notice, 'saved');
    },
  );

  test(
    '409 retains edits until the latest source is compared and explicitly adopted',
    () async {
      final repo = OfficeTestRepository();
      final controller = Sh02OfficeController(
        repository: repo,
        source: repo.original,
      );
      addTearDown(controller.dispose);
      await controller.load();
      controller.change(controller.objects.first, 'My writing');
      repo.externalRevision('Other window writing');
      await controller.save('My correction');
      expect(controller.conflict, isTrue);
      expect(controller.edits.values.single, 'My writing');
      await controller.compareLatest();
      expect(controller.source.version, 1);
      expect(
        controller.comparisons.single.previous.value,
        'Original writing 1',
      );
      expect(
        controller.comparisons.single.latest!.value,
        'Other window writing',
      );
      expect(repo.requests, hasLength(1));
      controller.adoptComparison({officeObjectId(1)});
      expect(controller.source.version, 2);
      await controller.save('Adopt after comparison');
      expect(controller.source.version, 3);
      expect(
        repo.requests.last.single['expected_value'],
        'Other window writing',
      );
      expect(repo.requests.last.single['value'], 'My writing');
    },
  );

  test(
    'undo and previous-version reading preserve committed history and exact attachment target',
    () async {
      final repo = OfficeTestRepository();
      final controller = Sh02OfficeController(
        repository: repo,
        source: repo.original,
      );
      addTearDown(controller.dispose);
      await controller.load();
      controller.change(controller.objects.first, 'Discard');
      controller.undo(controller.objects.first.id);
      expect(controller.canSave, isFalse);
      controller.change(controller.objects.first, 'Saved correction');
      await controller.save('A checked correction');
      await controller.openVersion(controller.source.parentArtifactId!);
      expect(controller.page!.current, isFalse);
      expect(controller.canEdit, isFalse);
      await controller.download();
      expect(repo.downloaded.single, '${officeId(1)}/source-original.docx');
      await controller.openNewer();
      expect(controller.source.version, 2);
      expect(controller.objects.first.value, 'Saved correction');
      expect(repo.values[1]!.first['value'], 'Original writing 1');
    },
  );

  test(
    'signature acknowledgement is explicit while active content stays read-only',
    () async {
      final repo = OfficeTestRepository()..signed = true;
      final controller = Sh02OfficeController(
        repository: repo,
        source: repo.original,
      );
      addTearDown(controller.dispose);
      await controller.load();
      controller.change(controller.objects.first, 'Revision');
      await controller.save('Update signed writing');
      expect(repo.requests, isEmpty);
      await controller.save(
        'Invalidate the signature explicitly',
        invalidateSignature: true,
      );
      expect(repo.invalidateSignature, isTrue);
      repo.active = true;
      await controller.load();
      expect(controller.canEdit, isFalse);
      await controller.download();
      expect(repo.downloaded, hasLength(1));
    },
  );

  test('a late projection cannot restore a disposed reader', () async {
    final repo = _DelayedOffice();
    final controller = Sh02OfficeController(
      repository: repo,
      source: repo.original,
    );
    final loading = controller.load();
    controller.dispose();
    repo.pending.complete(repo.project(repo.original, 0));
    await loading;
    expect(controller.objects, isEmpty);
    expect(controller.page, isNull);
  });

  test(
    'edited original admission requires matching parent and package lineage',
    () {
      final raw = officeSavedRaw(2);
      expect(Sh02ImportedMaterial.tryParse(raw)?.version, 2);
      final document = raw['document'] as Map;
      document['parent_sha256'] = 'f' * 64;
      expect(Sh02ImportedMaterial.tryParse(raw), isNull);
    },
  );
}

LumenisCoreException _rejected(int status) =>
    LumenisCoreException('Original unavailable', statusCode: status);

Sh02OfficeController _controller(OfficeTestRepository repo) =>
    Sh02OfficeController(repository: repo, source: repo.original);

void _expectUnavailable(Sh02OfficeController controller) {
  expect(controller.problem, 'editUnavailable');
  expect(controller.page, isNull);
  expect(controller.objects, isEmpty);
  expect(controller.edits, isEmpty);
  expect(controller.comparisons, isEmpty);
  expect(controller.comparisonPage, isNull);
  expect(controller.comparisonSource, isNull);
  expect(controller.nextOffset, isNull);
  expect(controller.notice, isNull);
  expect(controller.saveUnknown, isFalse);
  expect(controller.conflict, isFalse);
  expect(controller.canEdit, isFalse);
  expect(controller.canSave, isFalse);
  expect(controller.canOpenNewer, isFalse);
}

class _FailingOffice extends OfficeTestRepository {
  Object? saveFailure,
      reopenFailure,
      readFailure,
      historyFailure,
      downloadFailure;
  int saveCalls = 0, reopenCalls = 0, readCalls = 0, historyCalls = 0;
  final attempts = <Map<String, dynamic>>[];
  final historyScript = <Sh02OfficeHistoryPage>[];
  final historyCursors = <String?>[];
  bool historyComplete = true;
  Completer<void>? saveEntered, saveRelease;

  Future<void> commitAttempt(int index) async {
    final attempt = attempts[index];
    await super.save(
      attempt['parent'] as Sh02OfficePage,
      requestId: attempt['requestId'] as String,
      reason: attempt['reason'] as String,
      commands: attempt['commands'] as List<Map<String, dynamic>>,
      invalidateSignature: attempt['invalidateSignature'] as bool,
    );
  }

  @override
  Future<Sh02OfficeSaved> save(
    Sh02OfficePage parent, {
    required String requestId,
    required String reason,
    required List<Map<String, dynamic>> commands,
    required bool invalidateSignature,
  }) async {
    saveCalls++;
    attempts.add({
      'parent': parent,
      'requestId': requestId,
      'reason': reason,
      'commands': commands
          .map((command) => Map<String, dynamic>.from(command))
          .toList(),
      'invalidateSignature': invalidateSignature,
    });
    if (saveEntered case final entered?) {
      if (!entered.isCompleted) entered.complete();
    }
    if (saveFailure case final failure?) throw failure;
    if (saveRelease case final release?) await release.future;
    return super.save(
      parent,
      requestId: requestId,
      reason: reason,
      commands: commands,
      invalidateSignature: invalidateSignature,
    );
  }

  @override
  Future<Sh02ImportedMaterial> reopen(String artifactId) async {
    reopenCalls++;
    if (reopenFailure case final failure?) throw failure;
    return super.reopen(artifactId);
  }

  @override
  Future<Sh02OfficePage> read(
    Sh02ImportedMaterial source, {
    int offset = 0,
  }) async {
    readCalls++;
    if (readFailure case final failure?) throw failure;
    return super.read(source, offset: offset);
  }

  @override
  Future<Sh02OfficeHistoryPage> history(String workId, {String? cursor}) async {
    historyCalls++;
    historyCursors.add(cursor);
    if (historyFailure case final failure?) throw failure;
    if (historyScript.isNotEmpty) return historyScript.removeAt(0);
    final page = await super.history(workId, cursor: cursor);
    return Sh02OfficeHistoryPage(
      page.items,
      page.cursor,
      page.complete && historyComplete,
    );
  }

  @override
  Future<SavedWorkExportFile> download(Sh02OfficePage page) async {
    if (downloadFailure case final failure?) throw failure;
    return super.download(page);
  }
}

class _DelayedOffice extends OfficeTestRepository {
  final pending = Completer<Sh02OfficePage>();
  @override
  Future<Sh02OfficePage> read(Sh02ImportedMaterial source, {int offset = 0}) =>
      pending.future;
}
