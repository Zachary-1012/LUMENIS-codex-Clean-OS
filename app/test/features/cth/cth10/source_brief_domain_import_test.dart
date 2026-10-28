// Isolated widget contracts; synthetic client bytes are not product acceptance.
import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/features/cth/cth10/source_brief_panel.dart';
import 'package:lumenis_app/features/shared/sh02/sh02_repository.dart';

import '../../shared/shared_test_support.dart';

void main() {
  for (final domain in ['CTH', 'BMP']) {
    testWidgets('$domain import retains scope and continues selected sources', (
      tester,
    ) async {
      final client = _ImportClient(domain);
      await _open(tester, client);
      await _prepare(tester);
      expect(client.imports, hasLength(1));
      expect(client.created, 0);
      await _confirm(tester);
      expect(client.imports.map((call) => call['mode']), ['prepare', 'import']);
      expect(client.imports.last['domainId'], domain);
      expect(client.imports.last['confirmedResource'], _resource);
      expect(client.starts.single['sourceIds'], [_sourceId]);
      expect(client.jobReads, 1);
      expect(find.text('Open business work'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
    testWidgets(
      '$domain foreign material scope is withheld from business work',
      (tester) async {
        final client = _ImportClient(domain)..foreignRecord = true;
        await _open(tester, client);
        await _prepare(tester);
        await _confirm(tester);
        expect(client.jobReads, 1);
        expect(find.text('Open business work'), findsNothing);
        expect(tester.takeException(), isNull);
      },
    );
  }

  testWidgets(
    'cancelled import preview does not admit bytes or start a brief',
    (tester) async {
      final client = _ImportClient('CTH');
      await _open(tester, client);
      await _prepare(tester);
      await tester.tap(
        find.descendant(
          of: find.byType(AlertDialog),
          matching: find.text('Cancel'),
        ),
      );
      await tester.pumpAndSettle();
      expect(client.imports, hasLength(1));
      expect(client.created, 0);
      expect(client.starts, isEmpty);
    },
  );

  testWidgets('denied import does not start work or display a saved brief', (
    tester,
  ) async {
    final client = _ImportClient('CTH')..denyImport = true;
    await _open(tester, client);
    await _prepare(tester);
    await _confirm(tester);
    expect(client.created, 0);
    expect(client.starts, isEmpty);
    expect(find.text('Open business work'), findsNothing);
    expect(find.textContaining('Access to the material'), findsOneWidget);
  });

  for (final stage in ['prepare', 'import']) {
    testWidgets(
      'missing signer during $stage reports failure without uncertainty',
      (tester) async {
        final client = _ImportClient('CTH');
        const failure = LumenisCoreException(
          'Signer unavailable',
          statusCode: 503,
          errorCode: 'DOCUMENT_EVIDENCE_SIGNING_UNAVAILABLE',
        );
        if (stage == 'prepare') {
          client.prepareFailure = failure;
        } else {
          client.importFailure = failure;
        }
        await _open(tester, client);
        await _prepare(tester, expectConfirmation: stage == 'import');
        if (stage == 'import') await _confirm(tester);
        expect(client.created, 0);
        expect(client.starts, isEmpty);
        expect(
          find.textContaining('Evidence signing is unavailable.'),
          findsOneWidget,
        );
        expect(find.textContaining('unconfirmed'), findsNothing);
        expect(find.text('Open business work'), findsNothing);
        expect(tester.takeException(), isNull);
      },
    );
  }

  testWidgets('preparation failure never implies an unknown import write', (
    tester,
  ) async {
    final client = _ImportClient('CTH')
      ..prepareFailure = const LumenisCoreException(
        'Service unavailable',
        statusCode: 503,
      );
    await _open(tester, client);
    await _prepare(tester, expectConfirmation: false);
    expect(client.created, 0);
    expect(client.imports, hasLength(1));
    expect(find.textContaining('Material was not imported.'), findsOneWidget);
    expect(find.textContaining('unconfirmed'), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets('explicit import validation rejection is not shown as unknown', (
    tester,
  ) async {
    final client = _ImportClient('CTH')
      ..importFailure = const LumenisCoreException(
        'Invalid file',
        statusCode: 400,
        errorCode: 'DOCUMENT_SOURCE_INVALID',
      );
    await _open(tester, client);
    await _prepare(tester);
    await _confirm(tester);
    expect(client.created, 0);
    expect(client.starts, isEmpty);
    expect(
      find.textContaining('This import request was rejected.'),
      findsOneWidget,
    );
    expect(find.textContaining('unconfirmed'), findsNothing);
    await tester.tap(
      find.byKey(const ValueKey('source-brief/import-domain-material')),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
    expect(find.byKey(const ValueKey('domain-import-prepare')), findsOneWidget);
    expect(client.imports, hasLength(2));
    await tester.tap(
      find.descendant(
        of: find.byType(AlertDialog),
        matching: find.text('Cancel'),
      ),
    );
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
  });

  testWidgets('rejected brief request preserves confirmed material import', (
    tester,
  ) async {
    final client = _ImportClient('CTH')
      ..briefFailure = const LumenisCoreException(
        'Invalid task',
        statusCode: 400,
      );
    await _open(tester, client);
    await _prepare(tester);
    await _confirm(tester);
    expect(client.created, 1);
    expect(client.starts, hasLength(1));
    expect(
      find.textContaining('Material imported. The brief request was rejected.'),
      findsOneWidget,
    );
    expect(find.textContaining('unconfirmed'), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets('lost import acknowledgement reuses exact bytes and provenance', (
    tester,
  ) async {
    final client = _ImportClient('CTH')..loseImportAck = true;
    await _open(tester, client);
    await _prepare(tester);
    await _confirm(tester);
    expect(client.created, 1);
    expect(client.starts, isEmpty);
    expect(find.textContaining('The result is unconfirmed.'), findsOneWidget);
    await tester.tap(
      find.byKey(const ValueKey('source-brief/import-domain-material')),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
    await _confirm(tester);
    final writes = client.imports
        .where((call) => call['mode'] == 'import')
        .toList();
    expect(writes, hasLength(2));
    expect(writes.first['bytes'], writes.last['bytes']);
    expect(writes.first['provenance'], writes.last['provenance']);
    expect(client.created, 1);
    expect(client.starts, hasLength(1));
  });

  testWidgets('uncertain task admission continues without importing again', (
    tester,
  ) async {
    final client = _ImportClient('CTH')..loseTaskAck = true;
    await _open(tester, client);
    await tester.enterText(
      find.byKey(const ValueKey('source-brief/question')),
      '  Which source claims need checking?  ',
    );
    await _prepare(tester);
    await _confirm(tester);
    expect(client.imports, hasLength(2));
    expect(
      find.textContaining('Material imported. The brief start is unconfirmed.'),
      findsOneWidget,
    );
    final requestId = client.starts.single['requestId'];
    expect(
      client.starts.single['businessQuestion'],
      'Which source claims need checking?',
    );
    expect(
      tester
          .widget<TextField>(
            find.byKey(const ValueKey('source-brief/question')),
          )
          .enabled,
      isFalse,
    );
    expect(
      tester
          .widget<FilledButton>(
            find.byKey(const ValueKey('source-brief/import-domain-material')),
          )
          .onPressed,
      isNull,
    );
    await tester.tap(
      find.byKey(const ValueKey('source-brief/continue-domain-material')),
    );
    await tester.pumpAndSettle();
    expect(client.imports, hasLength(2));
    expect(client.starts, hasLength(2));
    expect(client.starts.last['requestId'], requestId);
    expect(
      client.starts.last['businessQuestion'],
      client.starts.first['businessQuestion'],
    );
    expect(client.starts.last['sourceIds'], client.starts.first['sourceIds']);
    expect(find.text('Open business work'), findsOneWidget);
  });
}

Future<void> _open(WidgetTester tester, _ImportClient client) async {
  tester.view.physicalSize = const Size(1400, 1200);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  await tester.pumpWidget(
    sharedTestApp(
      SourceBriefPanel(
        client: client,
        domainId: client.domain,
        documentPicker: _Picker(),
        onReturn: () {},
      ),
      locale: const Locale('en'),
    ),
  );
  await tester.pumpAndSettle();
}

Future<void> _prepare(
  WidgetTester tester, {
  bool expectConfirmation = true,
}) async {
  await tester.tap(
    find.byKey(const ValueKey('source-brief/import-domain-material')),
  );
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 300));
  await tester.tap(find.byKey(const ValueKey('domain-import-rights')));
  await tester.pump(const Duration(milliseconds: 300));
  await tester.tap(find.text('Owned or explicitly authorized material').last);
  await tester.pump(const Duration(milliseconds: 300));
  await tester.enterText(
    find.byKey(const ValueKey('domain-import-rights-statement')),
    'Synthetic authorization statement for isolated tests only.',
  );
  await tester.pump();
  await tester.tap(find.byKey(const ValueKey('domain-import-prepare')));
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 300));
  expect(
    find.byKey(const ValueKey('domain-import-confirm')),
    expectConfirmation ? findsOneWidget : findsNothing,
  );
}

Future<void> _confirm(WidgetTester tester) async {
  await tester.tap(find.byKey(const ValueKey('domain-import-confirm')));
  await tester.pumpAndSettle();
}

const _sourceId = 'SRC-domain-widget';
const _taskId = 'rbrief_01234567-89ab-cdef-0123-456789abcdef';
const _jobId = 'brief-0123456789abcdef0123456789abcdef';
const _resource = 'document-import-widget-exact-resource';

class _Picker implements Sh02DocumentPicker {
  @override
  Future<Sh02PickedDocument?> pick() async => Sh02PickedDocument(
    filename: 'isolated-material.txt',
    bytes: Uint8List.fromList(utf8.encode('Isolated widget input.')),
  );
}

class _ImportClient extends LumenisCoreClient {
  _ImportClient(this.domain);
  final String domain;
  bool denyImport = false;
  bool loseImportAck = false;
  bool loseTaskAck = false;
  bool foreignRecord = false;
  LumenisCoreException? prepareFailure;
  LumenisCoreException? importFailure;
  LumenisCoreException? briefFailure;
  int created = 0;
  int jobReads = 0;
  final imports = <Map<String, Object?>>[];
  final starts = <Map<String, Object?>>[];

  @override
  Map<String, dynamic> get currentContextEnvelope => {
    'ok': true,
    'contract': 'lumenis.context.v1',
    'selection_only': true,
    'context': {
      'mode': 'FOCUS',
      'domain_id': domain,
      'subject_id': domain == 'CTH' ? 'SUBJ-domain-widget' : null,
      'brand_focus_id': domain == 'BMP' ? 'BRAND-domain-widget' : null,
      'display_name': {'en': 'Widget scope'},
    },
  };
  @override
  Future<Map<String, dynamic>> settingsContext() async =>
      currentContextEnvelope;

  @override
  Future<Map<String, dynamic>> importDomainDocument({
    required String domainId,
    required String filename,
    required Uint8List bytes,
    required Map<String, dynamic> provenance,
    String mode = 'prepare',
    String? confirmedResource,
  }) async {
    imports.add({
      'domainId': domainId,
      'filename': filename,
      'bytes': bytes.toList(),
      'provenance': jsonDecode(jsonEncode(provenance)),
      'mode': mode,
      'confirmedResource': confirmedResource,
    });
    if (mode == 'prepare') {
      if (prepareFailure case final failure?) throw failure;
      return {
        'ok': true,
        'result': {'state': 'PREPARED', 'resource': _resource},
      };
    }
    if (denyImport) throw const LumenisCoreException('Denied', statusCode: 403);
    if (importFailure case final failure?) throw failure;
    if (created == 0) created += 1;
    if (loseImportAck) {
      loseImportAck = false;
      throw const LumenisCoreException('Uncertain import');
    }
    return {
      'ok': true,
      'result': {
        'source_id': _sourceId,
        'evidence_id': 7,
        'scope_status': 'VERIFIED',
      },
    };
  }

  @override
  Future<Map<String, dynamic>> startDomainSourceBriefTask({
    required String domainId,
    required List<String> sourceIds,
    required String requestId,
    String? businessQuestion,
  }) async {
    starts.add({
      'domainId': domainId,
      'sourceIds': sourceIds,
      'requestId': requestId,
      'businessQuestion': businessQuestion,
    });
    if (briefFailure case final failure?) throw failure;
    if (loseTaskAck) {
      loseTaskAck = false;
      throw const LumenisCoreException('Uncertain task');
    }
    return _task();
  }

  @override
  Future<Map<String, dynamic>> sourceBriefTask({
    required String domainId,
    required String taskId,
  }) async => _task();

  Map<String, dynamic> _task() => {
    'ok': true,
    'task': {
      'task_id': _taskId,
      'job_id': _jobId,
      'state': 'succeeded',
      'can_resume': false,
      'error': null,
      'result': null,
      'review_status': 'HUMAN_PENDING',
      'publish_status': 'not_performed',
    },
  };

  @override
  Future<Map<String, dynamic>> sourceBriefJob({
    required String domainId,
    required String jobId,
  }) async {
    jobReads += 1;
    return {
      'ok': true,
      'result': {
        'job_id': _jobId,
        'job_state': 'completed',
        'artifact_outcome': {
          'state': 'persisted_and_reopened_verified',
          'report_id': _jobId,
          'artifact_hash': 'a' * 64,
          'source_count': 1,
        },
        'source_brief': {
          'scope': {
            'product_id': domain == 'CTH' ? 'CTH' : 'ZBMP',
            'domain_id': domain == 'CTH' ? 'cth' : 'zbmp',
            'global': false,
            'subject_id': domain == 'CTH' ? 'SUBJ-domain-widget' : null,
            'brand_focus_id': domain == 'BMP' ? 'BRAND-domain-widget' : null,
            'entity_label': 'Widget scope',
            'scope_key': 'b' * 64,
          },
          'records': [
            {
              'source_id': _sourceId,
              'scope_evidence_ref': 'EV-domain-widget',
              'evidence_id': 'EV-domain-widget',
              'subject_id': domain == 'CTH'
                  ? (foreignRecord ? 'SUBJ-other-widget' : 'SUBJ-domain-widget')
                  : null,
              'brand_focus_id': domain == 'BMP'
                  ? (foreignRecord
                        ? 'BRAND-other-widget'
                        : 'BRAND-domain-widget')
                  : null,
              'title': 'Isolated admitted original',
              'source_url': null,
              'publish_datetime': null,
              'captured_at': '2026-10-24T12:00:00Z',
            },
          ],
        },
        'business_question': null,
        'business_analysis': {'state': 'not_requested'},
        'review_status': 'HUMAN_PENDING',
      },
    };
  }
}
