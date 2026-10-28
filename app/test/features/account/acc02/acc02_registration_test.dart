// Isolated consumer tests; directory registration is not live data collection.
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/features/account/acc02/acc02_screen.dart';

import '../../shared/shared_test_support.dart';

void main() {
  testWidgets(
    'empty directory registers first subject and verifies selection',
    (tester) async {
      final client = _RegistrationClient();
      await _open(tester, client);
      await _prepare(tester);
      expect(client.calls.map((call) => call['mode']), ['prepare']);
      expect(client.created, 0);
      await _confirm(tester);
      expect(client.calls.map((call) => call['mode']), ['prepare', 'apply']);
      expect(client.calls.last['confirmedResource'], _resource);
      expect(client.created, 1);
      expect(client.selections, ['CTH:SUBJ-widget-created']);
      expect(find.text('Registered and selected.'), findsOneWidget);
      expect(find.text('Registered sample mall'), findsWidgets);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('cancelled preview never applies registration or selects scope', (
    tester,
  ) async {
    final client = _RegistrationClient();
    await _open(tester, client);
    await _prepare(tester);
    await tester.tap(
      find.descendant(
        of: find.byType(AlertDialog),
        matching: find.text('Cancel'),
      ),
    );
    await tester.pumpAndSettle();
    expect(client.calls.map((call) => call['mode']), ['prepare']);
    expect(client.created, 0);
    expect(client.selections, isEmpty);
    expect(
      find.byKey(const ValueKey('acc02-retry-registration')),
      findsNothing,
    );
  });

  testWidgets('denied apply never reports registration or changes scope', (
    tester,
  ) async {
    final client = _RegistrationClient()..denyApply = true;
    await _open(tester, client);
    await _prepare(tester);
    await _confirm(tester);
    expect(client.created, 0);
    expect(client.selections, isEmpty);
    expect(
      find.text('Current permissions do not allow registration.'),
      findsOneWidget,
    );
    expect(find.text('Registered and selected.'), findsNothing);
  });

  testWidgets('lost apply acknowledgement reconciles the same identity once', (
    tester,
  ) async {
    final client = _RegistrationClient()..loseApplyAck = true;
    await _open(tester, client);
    await _prepare(tester);
    await _confirm(tester);
    expect(client.created, 1);
    expect(client.selections, isEmpty);
    expect(
      find.byKey(const ValueKey('acc02-retry-registration')),
      findsOneWidget,
    );
    await tester.tap(find.byKey(const ValueKey('acc02-retry-registration')));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
    await _confirm(tester);
    final applied = client.calls
        .where((call) => call['mode'] == 'apply')
        .toList();
    expect(applied, hasLength(2));
    expect(applied.first['entries'], applied.last['entries']);
    expect(client.created, 1);
    expect(client.selections, ['CTH:SUBJ-widget-created']);
    expect(find.text('Registered and selected.'), findsOneWidget);
  });

  testWidgets('brand directory uses the existing BMP brand identity contract', (
    tester,
  ) async {
    final client = _RegistrationClient();
    await _open(tester, client);
    await tester.tap(find.byKey(const ValueKey('acc02-directory-domain')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Brands').last);
    await tester.pumpAndSettle();
    await _prepare(tester);
    await _confirm(tester);
    final entry = (client.calls.first['entries'] as List).single as Map;
    expect((entry['identity'] as Map)['domain_id'], 'BMP');
    expect((entry['identity'] as Map)['subject_type'], 'brand');
    expect(client.selections, ['BMP:SUBJ-widget-created']);
    expect(client.directoryReads, contains('BMP'));
  });
}

Future<void> _open(WidgetTester tester, _RegistrationClient client) async {
  tester.view.physicalSize = const Size(1400, 1100);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  await tester.pumpWidget(
    sharedTestApp(Acc02Screen(client: client), locale: const Locale('en')),
  );
  await tester.pumpAndSettle();
}

Future<void> _prepare(WidgetTester tester) async {
  await tester.tap(find.byKey(const ValueKey('acc02-add-subject')));
  await tester.pumpAndSettle();
  await tester.enterText(
    find.byKey(const ValueKey('acc02-register-name_zh')),
    '注册示例商场',
  );
  await tester.enterText(
    find.byKey(const ValueKey('acc02-register-name_en')),
    'Registered sample mall',
  );
  await tester.pump();
  await tester.tap(find.byKey(const ValueKey('acc02-prepare-registration')));
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 300));
  expect(
    find.byKey(const ValueKey('acc02-confirm-registration')),
    findsOneWidget,
  );
}

Future<void> _confirm(WidgetTester tester) async {
  await tester.tap(find.byKey(const ValueKey('acc02-confirm-registration')));
  await tester.pumpAndSettle();
}

const _resource =
    'subject-registry-batch:v1:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa';

class _RegistrationClient extends LumenisCoreClient {
  final calls = <Map<String, Object?>>[];
  final selections = <String>[];
  final directoryReads = <String>[];
  Map<String, dynamic>? subject;
  int created = 0;
  bool denyApply = false;
  bool loseApplyAck = false;
  Map<String, dynamic> context = {'mode': 'GLOBAL_ALL', 'domain_id': 'CTH'};

  @override
  Future<Map<String, dynamic>> settingsContext() async => {
    'ok': true,
    'contract': 'lumenis.context.v1',
    'selection_only': true,
    'context': context,
  };

  @override
  Future<Map<String, dynamic>> settingsSubjects({
    String domainId = 'CTH',
  }) async {
    directoryReads.add(domainId);
    return {
      'ok': true,
      'selection_only': true,
      'subjects': [if (subject?['domain_id'] == domainId) subject!],
    };
  }

  @override
  Future<Map<String, dynamic>> subjectBatch({
    required List<Map<String, dynamic>> entries,
    String mode = 'prepare',
    String? confirmedResource,
    int resumeIndex = 0,
  }) async {
    final cloned = jsonDecode(jsonEncode(entries)) as List;
    calls.add({
      'mode': mode,
      'entries': cloned,
      'confirmedResource': confirmedResource,
    });
    if (mode == 'prepare') {
      return {
        'ok': true,
        'state': 'PREPARED',
        'resource': _resource,
        'entries': cloned,
      };
    }
    if (denyApply) {
      throw const LumenisCoreException('Denied', statusCode: 403);
    }
    final existing = subject != null;
    if (!existing) {
      created += 1;
      final identity = (cloned.single as Map)['identity'] as Map;
      subject = {
        ...Map<String, dynamic>.from(identity),
        'subject_id': 'SUBJ-widget-created',
      };
    }
    if (loseApplyAck) {
      loseApplyAck = false;
      throw const LumenisCoreException('Lost acknowledgement', statusCode: 503);
    }
    return {
      'ok': true,
      'state': 'COMPLETED',
      'results': [
        {'status': existing ? 'EXISTING' : 'CREATED', 'subject': subject},
      ],
    };
  }

  @override
  Future<Map<String, dynamic>> selectContext({
    required String domainId,
    required String subjectId,
  }) async {
    selections.add('$domainId:$subjectId');
    context = {
      'mode': 'FOCUS',
      'domain_id': domainId,
      'subject_id': subjectId,
      'display_name': {'en': subject?['name_en']},
    };
    return settingsContext();
  }
}
