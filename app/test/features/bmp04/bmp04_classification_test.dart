import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/core/lumenis_theme.dart';
import 'package:lumenis_app/features/bmp04/bmp04_repository.dart';
import 'package:lumenis_app/features/bmp04/bmp04_snapshot.dart';
import 'package:lumenis_app/features/bmp04/bmp04_view_model.dart';
import 'package:lumenis_app/features/bmp04/bmp04_screen.dart';
import 'package:lumenis_app/l10n/lumenis_localizations.dart';

void main() {
  test('bound observation-only sources and events have a renderable presentation', () {
    for (final data in [response(), observationResponse()]) {
      final snapshot = Bmp04Snapshot.fromResponse(data);
      expect(snapshot.presentationState, Bmp04PresentationState.observationsOnly);
      expect(snapshot.channels, isEmpty);
      expect(snapshot.analysisState, 'NOT_COMPUTED');
      expect(snapshot.dashboards.every((d) => d.total == null), isTrue);
    }
    final snapshot = Bmp04Snapshot.fromResponse(observationResponse());
    expect(snapshot.sourceObservations.single.evidenceReference, 'EV-12');
  });
  for (final mode in ['sources', 'events', 'partial', 'denied']) {
    testWidgets('observation renderer preserves source evidence and $mode state', (tester) async {
      final data = mode == 'events' ? response() : observationResponse();
      if (mode == 'partial') {
        final truth = data['truth'] as Map;
        truth['source_read_complete'] = false;
        truth['source_truncated'] = true;
        truth['source_count'] = null;
        truth['data_state'] = 'PARTIAL';
      }
      if (mode == 'denied') {
        (data['observation_read_binding'] as Map)['read_allowed'] = false;
      }
      final repository = FakeRepository()..nextResponse = data;
      await tester.pumpWidget(MaterialApp(theme: LumenisTheme.dark,
        locale: const Locale('en'), supportedLocales: LumenisLocalizations.supportedLocales,
        localizationsDelegates: const [LumenisLocalizations.delegate,
          GlobalMaterialLocalizations.delegate, GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate],
        home: Scaffold(body: Bmp04Screen(client: LumenisCoreClient(), repository: repository))));
      await tester.pumpAndSettle();
      final panel = find.byKey(const Key('bmp04-source-observations'));
      if (mode == 'denied') {
        expect(panel, findsNothing);
        expect(find.text('Observed launch'), findsNothing);
      } else {
        expect(panel, findsOneWidget);
        expect(find.text('Source observations'), findsOneWidget);
        expect(find.textContaining('Propagation analysis has not been computed.'), findsOneWidget);
        final copy = tester.element(find.byType(Bmp04Screen)).lumenisL10n;
        expect(find.text(copy.text('state.error')), findsNothing);
        expect(find.text('Complete sample count: —'), findsOneWidget);
        if (mode != 'events') {
          expect(find.byKey(const Key('bmp04-observation-SRC-12')), findsOneWidget);
          expect(find.text('Observed launch'), findsOneWidget);
          expect(find.text('— · EV-12'), findsOneWidget);
        }
      }
      expect(repository.commits, 0);
      expect(tester.takeException(), isNull);
    });
  }
  test('three views retain unknown totals and only individual curated events', () {
    final snapshot = Bmp04Snapshot.fromResponse(response());
    expect(snapshot.scopeReady, isTrue);
    expect(snapshot.dashboards.length, 3);
    expect(snapshot.dashboards.every((d) => d.total == null), isTrue);
    expect(snapshot.curatedEvents.single.id, 21);
    expect(snapshot.unclassifiedEventCount, 1);
  });
  test('forged complete zero and malformed events fail closed', () {
    final data = response();
    final truth = data['truth'] as Map<String, dynamic>;
    (truth['dashboards'] as List).first['total_events'] = 0;
    expect(Bmp04Snapshot.fromResponse(data).dashboards, isEmpty);
    final bad = response();
    (bad['sections'] as List).first['items'] = [
      {'event_id': '21', 'title': 'Unverified', 'evidence_ref': 'EV-1', 'evidence_state': 'REFERENCED'},
      {'event_id': 22, 'title': 'No proof', 'evidence_ref': null},
    ];
    expect(Bmp04Snapshot.fromResponse(bad).curatedEvents, isEmpty);
  });
  test('classified views bind their displayed events to signed exact-focus references', () {
    final data = response();
    final dashboard = ((data['truth'] as Map)['dashboards'] as List).first as Map;
    dashboard['observed_events'] = 1;
    dashboard['events'] = [{'event_id': 21, 'title': 'Product launch',
      'evidence_ref': 'EV-10', 'evidence_state': 'REFERENCED'}];
    dashboard['source_refs'] = [{'event_id': 21, 'scope_evidence': {
      'id': 10, 'stored_scope': {'domain_id': 'zbmp', 'product_id': 'ZBMP',
        'global': false, 'brand_focus_id': 'BRAND-ONE'},
      'integrity': {'verified': true, 'assurance': 'writer-authenticated',
        'algorithm': 'hmac-sha256', 'digest': 'a' * 64}}}];
    expect(Bmp04Snapshot.fromResponse(data).dashboards.first.events.single.id, 21);
    (((dashboard['source_refs'] as List).first['scope_evidence'] as Map)['stored_scope'] as Map)['brand_focus_id'] = 'FOREIGN';
    expect(Bmp04Snapshot.fromResponse(data).dashboards, isEmpty);
  });
  test('classification permission unavailable never renders complete zero', () {
    final data = response();
    (data['truth'] as Map)['classification_state'] = 'UNAVAILABLE';
    expect(Bmp04Snapshot.fromResponse(data).dashboards, isEmpty);
  });
  test('scope denial hides event controls and dashboards', () {
    final data = response();
    (data['observation_read_binding'] as Map)['read_allowed'] = false;
    final snapshot = Bmp04Snapshot.fromResponse(data);
    expect(snapshot.scopeReady, isFalse);
    expect(snapshot.curatedEvents, isEmpty);
    expect(snapshot.dashboards, isEmpty);
  });
  test('preview is read-only, cancel never writes, confirm uses exact draft', () async {
    final repository = FakeRepository();
    final model = Bmp04ViewModel(repository: repository);
    await model.refresh();
    expect(await model.previewClassification(999, 'brand_event'), isFalse);
    expect(await model.previewClassification(21, 'brand_event'), isTrue);
    expect(repository.commits, 0);
    model.cancelClassification();
    await model.confirmClassification();
    expect(repository.commits, 0);
    expect(await model.previewClassification(21, 'product_event'), isTrue);
    final draft = repository.previewed;
    await model.confirmClassification();
    expect(repository.confirmed, same(draft));
    expect(repository.confirmedResource, resource);
    expect(repository.loads, 4);
    expect(repository.commits, 1);
    model.dispose();
  });
  for (final change in ['evidence', 'missing', 'scope']) {
    test('pre-preview $change change cannot confirm an unseen source', () async {
      final repository = FakeRepository();
      final model = Bmp04ViewModel(repository: repository);
      await model.refresh();
      final changed = response();
      if (change == 'evidence') {
        final event = ((changed['sections'] as List).first['items'] as List).first as Map;
        event['evidence_ref'] = 'EV-11';
        event['title'] = 'Revised launch';
      } else if (change == 'missing') {
        (changed['sections'] as List).first['items'] = [];
      } else {
        (changed['observation_context'] as Map)['brand_focus_id'] = 'BRAND-TWO';
        (changed['observation_read_binding'] as Map)['brand_focus_id'] = 'BRAND-TWO';
      }
      repository.nextResponse = changed;
      expect(await model.previewClassification(21, 'brand_event'), isFalse);
      await model.confirmClassification();
      expect(repository.commits, 0);
      expect(model.canClassify, isFalse);
      expect(model.snapshot!.curatedEvents.single.evidenceReference, 'EV-10');
      model.dispose();
    });
  }
  test('refresh invalidates pending preview and uncertain writes require readback', () async {
    final repository = FakeRepository();
    final model = Bmp04ViewModel(repository: repository);
    await model.refresh();
    await model.previewClassification(21, 'brand_event');
    await model.refresh();
    await model.confirmClassification();
    expect(repository.commits, 0);
    await model.previewClassification(21, 'industry_event');
    repository.failure = StateError('connection timed out');
    await model.confirmClassification();
    expect(model.classificationOutcomeUnknown, isTrue);
    expect(model.canClassify, isFalse);
    await model.confirmClassification();
    expect(repository.commits, 1);
    repository.failure = null;
    await model.refresh();
    expect(model.canClassify, isTrue);
    model.dispose();
  });
  test('dispose during preview cannot produce a confirmable write', () async {
    final repository = FakeRepository()..pending = Completer<String>();
    final model = Bmp04ViewModel(repository: repository);
    await model.refresh();
    final result = model.previewClassification(21, 'brand_event');
    model.dispose();
    repository.pending!.complete(resource);
    expect(await result, isFalse);
    expect(repository.commits, 0);
  });
  test('repository rejects malformed preview and mismatched save receipt', () async {
    final client = FakeClient();
    final repository = CoreBmp04Repository(client: client);
    const draft = Bmp04ClassificationDraft(subjectId: 'SUBJ-ONE', eventId: 21,
      category: 'brand_event', requestId: 'request-123');
    client.result = {'ok': true, 'state': 'PREPARED', 'resource': resource, 'approval_issued': false};
    expect(await repository.previewClassification(draft), resource);
    expect(client.lastResource, isNull);
    client.result = {'ok': true, 'state': 'PREPARED', 'resource': resource, 'approval_issued': true};
    await expectLater(repository.previewClassification(draft), throwsFormatException);
    client.result = {'ok': true, 'source_event_id': 22, 'category': 'brand_event',
      'claim_type': 'human_business_classification', 'classification_id': 'PE-S-${'a' * 32}'};
    await expectLater(repository.confirmClassification(draft, resource), throwsFormatException);
    expect(client.lastResource, resource);
  });
  for (final width in [390.0, 1440.0]) {
    testWidgets('three views and cancel/save at width $width', (tester) async {
      await tester.binding.setSurfaceSize(Size(width, 1200));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      final repository = FakeRepository();
      await tester.pumpWidget(MaterialApp(theme: LumenisTheme.dark,
        locale: const Locale('en'), supportedLocales: LumenisLocalizations.supportedLocales,
        localizationsDelegates: const [LumenisLocalizations.delegate,
          GlobalMaterialLocalizations.delegate, GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate],
        home: Scaffold(body: Bmp04Screen(client: LumenisCoreClient(), repository: repository))));
      await tester.pumpAndSettle();
      for (final category in bmp04Categories) {
        await tester.tap(find.byKey(Key('bmp04-view-$category')));
        await tester.pumpAndSettle();
        expect(tester.widget<ChoiceChip>(find.byKey(Key('bmp04-view-$category'))).selected, isTrue);
      }
      final edit = find.byKey(const Key('bmp04-classify-21'));
      await tester.ensureVisible(edit);
      await tester.tap(edit);
      await tester.pumpAndSettle();
      await tester.tap(find.text('Product events').last);
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('bmp04-confirm-classification')), findsOneWidget);
      expect(repository.commits, 0);
      await tester.tap(find.text('Cancel'));
      await tester.pumpAndSettle();
      expect(repository.commits, 0);
      await tester.tap(edit);
      await tester.pumpAndSettle();
      await tester.tap(find.text('Product events').last);
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('bmp04-confirm-classification')));
      await tester.pumpAndSettle();
      expect(repository.commits, 1);
      expect(tester.takeException(), isNull);
    });
  }
}

final resource = 'propagation-classification:v1:${'a' * 64}';
class FakeClient extends LumenisCoreClient {
  Map<String, dynamic> result = {};
  String? lastResource;
  @override
  Future<Map<String, dynamic>> classifyPropagationEvent({required String subjectId,
    required int sourceEventId, required String category, required String requestId,
    String? confirmedResource}) async {
    lastResource = confirmedResource;
    return result;
  }
}
class FakeRepository implements Bmp04Repository, Bmp04ClassificationRepository {
  Map<String, dynamic>? nextResponse;
  int loads = 0;
  int commits = 0;
  Object? failure;
  Completer<String>? pending;
  Bmp04ClassificationDraft? previewed;
  Bmp04ClassificationDraft? confirmed;
  String? confirmedResource;
  @override
  Future<Bmp04Snapshot> load() async { loads++; return Bmp04Snapshot.fromResponse(nextResponse ?? response()); }
  @override
  Future<String> previewClassification(Bmp04ClassificationDraft draft) async {
    previewed = draft;
    return pending == null ? resource : await pending!.future;
  }
  @override
  Future<void> confirmClassification(Bmp04ClassificationDraft draft, String value) async {
    commits++; confirmed = draft; confirmedResource = value;
    if (failure != null) throw failure!;
  }
}
Map<String, dynamic> response() {
  final context = {'actor_id': 7, 'domain_id': 'BMP', 'product_id': 'ZBMP',
    'canonical_scope': 'FOCUS', 'subject_id': 'SUBJ-ONE', 'brand_focus_id': 'BRAND-ONE'};
  return {'ok': true, 'screen': 'BMP-04', 'bound': true, 'source': 'runtime',
    'observation_contract': 'lumenis.bmp04-source-observations.v1',
    'observation_context': context,
    'observation_read_binding': {...context, 'contract': 'lumenis.scope-read-binding.v1',
      'module': 'brand_market_overview', 'policy': 'actor-exact-scope-v1',
      'actor_scope': 'authenticated', 'applied': true, 'read_allowed': true,
      'scope_verified': true, 'global_all_granted': false},
    'source_observations': [],
    'truth': <String, dynamic>{'domain_id': 'zbmp', 'product_id': 'ZBMP', 'source_read_complete': true,
      'event_read_complete': true, 'rejected_source_count': 0, 'source_truncated': false,
      'observed_source_count': 0, 'source_count': 0, 'event_returned_count': 1,
      'data_state': 'READY', 'analysis_state': 'NOT_COMPUTED',
      'classification_state': 'EMPTY', 'classification_rejected': 0, 'unclassified_event_count': 1,
      'total_events_semantics': 'current_verified_curated_sample_not_population',
      'dashboards': [for (final category in bmp04Categories)
        {'category': category, 'claim_type': 'human_business_classification',
          'observed_events': 0, 'total_events': null, 'events': [], 'source_refs': []}]},
    'sections': [{'type': 'events', 'items': [{'event_id': 21, 'title': 'Product launch',
      'evidence_ref': 'EV-10', 'evidence_state': 'REFERENCED'}]}]};
}

Map<String, dynamic> observationResponse() {
  final data = response();
  (data['truth'] as Map)['observed_source_count'] = 1;
  (data['truth'] as Map)['source_count'] = 1;
  data['source_observations'] = [{
    'id': 'SRC-12', 'title': 'Observed launch', 'platform': null,
    'scope_evidence': {
      'id': 12,
      'stored_scope': {'domain_id': 'zbmp', 'product_id': 'ZBMP',
        'scope_status': 'VERIFIED', 'subject_id': null, 'brand_focus_id': 'BRAND-ONE'},
      'integrity': {'verified': true, 'lineage_verified': true,
        'assurance': 'writer-authenticated', 'algorithm': 'hmac-sha256', 'digest': 'a' * 64},
    },
  }];
  return data;
}
