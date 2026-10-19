import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/core/lumenis_theme.dart';
import 'package:lumenis_app/features/bmp09/bmp09_repository.dart';
import 'package:lumenis_app/features/bmp09/bmp09_screen.dart';
import 'package:lumenis_app/features/bmp09/bmp09_snapshot.dart';
import 'package:lumenis_app/l10n/lumenis_localizations.dart';

void main() {
  for (final locale in [const Locale('en'), const Locale('zh', 'CN'), const Locale('ko')]) {
    for (final width in [375.0, 1200.0]) {
      testWidgets('artifact contract renders ${locale.languageCode} at $width', (tester) async {
        await tester.binding.setSurfaceSize(Size(width, 900));
        addTearDown(() => tester.binding.setSurfaceSize(null));
        final snapshot = Bmp09Snapshot.fromResponse(_response());
        expect(snapshot.scopeApproved, isTrue);
        expect(snapshot.dimensions, isEmpty);
        expect(snapshot.sourceBriefArtifacts.single.allEvaluationsPassed, isFalse);
        await _pump(tester, snapshot, locale: locale);
        expect(find.text('Saved report A'), findsOneWidget);
        expect(find.text('brief-job-001'), findsOneWidget);
        expect(tester.takeException(), isNull);
      });
    }
  }

  testWidgets('failed check remains failed and saved work is not measured effect', (tester) async {
    await _pump(tester, Bmp09Snapshot.fromResponse(_response()));
    expect(find.textContaining('Source grounding: Fail'), findsOneWidget);
    expect(find.textContaining('saved does not mean evaluation passed'), findsOneWidget);
    expect(find.text('No actual result is ready for evaluation'), findsNothing);
    await tester.ensureVisible(find.text('Prepare report request'));
    await tester.tap(find.text('Prepare report request'));
    await tester.pump();
    expect(find.text('A report request cannot be prepared for the current brand scope or authorization state.'), findsOneWidget);
  });

  testWidgets('complete empty artifact read is distinct from legacy no measurements', (tester) async {
    final response = _response(empty: true);
    final snapshot = Bmp09Snapshot.fromResponse(response);
    expect(snapshot.dataState, 'EMPTY');
    await _pump(tester, snapshot);
    expect(find.text('This complete read found no artifacts.'), findsNWidgets(2));
    expect(find.text('No actual result is ready for evaluation'), findsNothing);
  });

  testWidgets('partial and unknown reads never claim verified empty', (tester) async {
    final response = _response(empty: true);
    (response['truth'] as Map<String, dynamic>)['has_more'] = true;
    (response['truth'] as Map<String, dynamic>)['next_cursor'] = 'next-page';
    (response['truth'] as Map<String, dynamic>).remove('source_brief_reports');
    final snapshot = Bmp09Snapshot.fromResponse(response);
    expect(snapshot.dataState, 'PARTIAL');
    await _pump(tester, snapshot);
    expect(find.text('Read is incomplete. Only verified items are shown below.'), findsOneWidget);
    expect(find.text('More artifacts have not yet been read.'), findsOneWidget);
    expect(find.text('Read status is unknown or unavailable; emptiness is not confirmed.'), findsOneWidget);
    expect(find.text('This complete read found no artifacts.'), findsNothing);
  });

  testWidgets('scope rejection hides artifact titles and checks', (tester) async {
    final response = _response();
    (response['report_screen_binding'] as Map<String, dynamic>)['read_allowed'] = false;
    final snapshot = Bmp09Snapshot.fromResponse(response);
    expect(snapshot.scopeApproved, isFalse);
    await _pump(tester, snapshot);
    expect(find.text('Saved report A'), findsNothing);
    expect(find.text('brief-job-001'), findsNothing);
    expect(find.text('Brand evaluation is unavailable'), findsOneWidget);
  });

  testWidgets('client rejection and missing evaluations remain visible as partial', (tester) async {
    final response = _response();
    (response['saved_artifacts'] as List).single['sha256'] = 'invalid';
    (response['source_brief_artifacts'] as List).single['evaluations'] = [];
    final snapshot = Bmp09Snapshot.fromResponse(response);
    expect(snapshot.savedArtifactRead!.readComplete, isFalse);
    await _pump(tester, snapshot);
    expect(find.text('Unverified artifacts omitted: 1'), findsOneWidget);
    expect(find.text('Checks are incomplete; missing results remain unknown.'), findsOneWidget);
    expect(find.text('Saved report A'), findsNothing);
  });

  testWidgets('legacy empty snapshot retains its existing view', (tester) async {
    await _pump(tester, const Bmp09Snapshot(
      contractBound: true,
      dataState: 'EMPTY',
      scope: Bmp09Scope(mode: 'GLOBAL_ALL', brandId: null, displayNames: {}),
      scopeApproved: true,
      dimensions: [], reports: [], grantedPermissions: {},
    ));
    expect(find.text('No actual result is ready for evaluation'), findsOneWidget);
    expect(find.text('Saved work'), findsNothing);
  });
}

Future<void> _pump(WidgetTester tester, Bmp09Snapshot snapshot, {Locale locale = const Locale('en')}) async {
  await tester.pumpWidget(MaterialApp(
    theme: LumenisTheme.dark,
    locale: locale,
    supportedLocales: LumenisLocalizations.supportedLocales,
    localizationsDelegates: const [
      LumenisLocalizations.delegate,
      GlobalMaterialLocalizations.delegate,
      GlobalWidgetsLocalizations.delegate,
      GlobalCupertinoLocalizations.delegate,
    ],
    home: Scaffold(body: Bmp09Screen(
      client: LumenisCoreClient(), repository: _Repository(snapshot),
    )),
  ));
  await tester.pumpAndSettle();
}

class _Repository implements Bmp09Repository {
  _Repository(this.snapshot);
  final Bmp09Snapshot snapshot;
  @override
  Future<Bmp09Snapshot> load() async => snapshot;
}

// Contract-shaped fixture, intentionally parsed via production fromResponse.
// This is not a captured production response or live runtime acceptance.
Map<String, dynamic> _response({bool empty = false}) {
  final hash = List.filled(64, 'a').join();
  final screen = <String, dynamic>{
    'contract': 'lumenis.scope-read-binding.v1',
    'module': 'brand_market_overview', 'policy': 'actor-exact-scope-v1',
    'domain_id': 'BMP', 'product_id': 'ZBMP', 'canonical_scope': 'GLOBAL_ALL',
    'subject_id': null, 'brand_focus_id': null, 'applied': true,
    'read_allowed': true, 'scope_verified': true, 'actor_scope': 'authenticated',
    'global_all_granted': true,
  };
  final scope = <String, dynamic>{
    'domain_id': 'zbmp', 'subject_id': null,
    'brand_focus_id': null, 'global_scope': true,
  };
  return {
    'ok': true, 'screen': 'BMP-09', 'bound': true, 'source': 'runtime',
    'report_artifact_contract': 'lumenis.bmp09-report-artifacts.v1',
    'report_screen_binding': screen, 'global_binding': {...screen},
    'report_authorization': {
      'module': 'reports', 'action': 'read', 'context': {...scope, 'actor_id': 1},
    },
    'truth': <String, dynamic>{
      'scope': scope, 'saved_count': empty ? 0 : 1,
      'unverified_candidates': 0, 'has_more': false,
      'verification_complete': true, 'next_cursor': null,
      'source_brief_reports': {
        'resource_type': 'source_brief_job', 'returned_count': empty ? 0 : 1,
        'rejected_count': 0, 'scanned_count': empty ? 0 : 1, 'limit': 100,
        'has_more': false, 'read_complete': true, 'state': empty ? 'EMPTY' : 'READY',
      },
    },
    'saved_artifacts': [if (!empty) {
      'resource_type': 'saved_work', 'id': 'saved-001', 'title': 'Saved report A',
      'kind': 'report', 'version': 2, 'sha256': hash, 'source_count': 0,
      'assessment': 'NOT_ESTABLISHED_BY_STORAGE',
    }],
    'source_brief_artifacts': [if (!empty) {
      'resource_type': 'source_brief_job', 'job_id': 'brief-job-001',
      'artifact_hash': hash, 'revision': null, 'source_count': 3,
      'review_status': 'HUMAN_PENDING', 'evaluation_state': 'recorded',
      'evaluations': [
        for (final entry in {
          'report_artifact_integrity': 'pass',
          'source_evidence_grounding': 'fail',
          'multimodal_analysis_integrity': 'unknown',
        }.entries)
          {
            'evaluation_id': List.filled(64, entry.value == 'pass' ? 'b' : entry.value == 'fail' ? 'c' : 'd').join(),
            'metric_name': entry.key, 'status': entry.value,
            'evaluated_at': '2026-10-19T00:00:00Z',
            'evidence_ref': 'daily_reports:brief-job-001:$hash',
          },
      ],
    }],
  };
}
