import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/core/lumenis_theme.dart';
import 'package:lumenis_app/features/bmp03/bmp03_repository.dart';
import 'package:lumenis_app/features/bmp03/bmp03_screen.dart';
import 'package:lumenis_app/features/bmp03/bmp03_snapshot.dart';
import 'package:lumenis_app/features/bmp10/bmp10_repository.dart';
import 'package:lumenis_app/features/bmp10/bmp10_screen.dart';
import 'package:lumenis_app/features/bmp10/bmp10_snapshot.dart';
import 'package:lumenis_app/l10n/lumenis_localizations.dart';

void main() {
  test('BMP03 observation contract preserves source/insight distinction and empty state', () {
    final result = Bmp03Snapshot.fromResponse(_bmp03());
    expect(result.sourceObservationContract, isTrue);
    expect(result.scopeReady, isTrue);
    expect(result.presentationState, Bmp03PresentationState.observations);
    expect(result.signals, isEmpty);
    expect(result.sourceObservations.single.title, 'Market source');
    final empty = Bmp03Snapshot.fromResponse(_bmp03(empty: true));
    expect(empty.presentationState, Bmp03PresentationState.empty);
    final partial = Bmp03Snapshot.fromResponse(_bmp03(empty: true, partial: true));
    expect(partial.presentationState, Bmp03PresentationState.partial);
  });

  test('BMP03/BMP10 reject cross-focus observations without promoting them', () {
    final three = _bmp03();
    final row = (three['source_observations'] as List).single as Map;
    ((row['scope_evidence'] as Map)['stored_scope'] as Map)['brand_focus_id'] = 'OTHER';
    final parsed = Bmp03Snapshot.fromResponse(three);
    expect(parsed.sourceObservations, isEmpty);
    expect(parsed.dataState, 'PARTIAL');
    final ten = _bmp10();
    final event = (ten['observed_events'] as List).single as Map;
    ((event['scope_evidence'] as Map)['stored_scope'] as Map)['brand_focus_id'] = 'OTHER';
    final parsedTen = Bmp10Snapshot.fromResponse(ten);
    expect(parsedTen.observedEvents, isEmpty);
    expect(parsedTen.observedRisks, hasLength(1));
    expect(parsedTen.dataState, 'PARTIAL');
    expect(parsedTen.events, isEmpty);
    expect(parsedTen.risks, isEmpty);
    expect(parsedTen.grantedPermissions, isEmpty);
  });

  test('global scope requires explicit global permission for observations', () {
    final three = _bmp03();
    final threeBinding = three['source_read_binding'] as Map;
    threeBinding.addAll({'canonical_scope': 'GLOBAL_ALL', 'subject_id': null,
      'brand_focus_id': null, 'global_all_granted': true});
    (three['source_context'] as Map).addAll({'mode': 'GLOBAL_ALL',
      'subject_id': null, 'brand_focus_id': null});
    expect(Bmp03Snapshot.fromResponse(three).sourceObservations, hasLength(1));
    threeBinding['global_all_granted'] = false;
    expect(Bmp03Snapshot.fromResponse(three).scopeReady, isFalse);
    final ten = _bmp10();
    final tenBinding = ten['observation_read_binding'] as Map;
    tenBinding.addAll({'canonical_scope': 'GLOBAL_ALL', 'subject_id': null,
      'brand_focus_id': null, 'global_all_granted': true});
    (ten['observation_context'] as Map).addAll({'canonical_scope': 'GLOBAL_ALL',
      'subject_id': null, 'brand_focus_id': null});
    expect(Bmp10Snapshot.fromResponse(ten).observedEvents, hasLength(1));
    tenBinding['global_all_granted'] = false;
    expect(Bmp10Snapshot.fromResponse(ten).scopeApproved, isFalse);
  });

  for (final width in [390.0, 1280.0]) {
    for (final locale in [const Locale('en'), const Locale('zh', 'CN'), const Locale('ko')]) {
      testWidgets('source and observation UI renders at $width in $locale', (tester) async {
        tester.view.physicalSize = Size(width, 900);
        tester.view.devicePixelRatio = 1;
        addTearDown(tester.view.resetPhysicalSize);
        addTearDown(tester.view.resetDevicePixelRatio);
        await tester.pumpWidget(_app(Bmp03Screen(client: LumenisCoreClient(),
          repository: _Three(_bmp03())), locale));
        await tester.pumpAndSettle();
        expect(find.byKey(const Key('bmp03-source-observations')), findsOneWidget);
        expect(find.text('Market source'), findsOneWidget);
        expect(find.textContaining('EV-7'), findsOneWidget);
        expect(tester.takeException(), isNull);
        await tester.pumpWidget(_app(Bmp10Screen(client: LumenisCoreClient(),
          repository: _Ten(_bmp10())), locale));
        await tester.pumpAndSettle();
        expect(find.byKey(const Key('bmp10-observations')), findsOneWidget);
        expect(find.text('Observed event'), findsOneWidget);
        expect(find.text('Observed risk'), findsOneWidget);
        expect(find.textContaining('EV-7'), findsNWidgets(2));
        expect(tester.takeException(), isNull);
      });
    }
  }

  testWidgets('partial empty BMP03 is not presented as complete empty', (tester) async {
    await tester.pumpWidget(_app(Bmp03Screen(client: LumenisCoreClient(),
      repository: _Three(_bmp03(empty: true, partial: true))), const Locale('en')));
    await tester.pumpAndSettle();
    expect(find.textContaining('source read is incomplete'), findsOneWidget);
    expect(find.textContaining('does not establish an empty source'), findsOneWidget);
    expect(find.text('No source observations in this scope.'), findsNothing);
  });

  testWidgets('BMP10 partial reads preserve unknown risk values and real zero', (tester) async {
    final response = _bmp10(partial: true);
    final risk = (response['observed_risks'] as List).single as Map;
    risk['score'] = 0;
    await tester.pumpWidget(_app(Bmp10Screen(client: LumenisCoreClient(),
      repository: _Ten(response)), const Locale('en')));
    await tester.pumpAndSettle();
    expect(find.textContaining('read is incomplete'), findsOneWidget);
    expect(find.text('Source risk score: 0'), findsOneWidget);
    expect(find.text('Source risk level: —'), findsOneWidget);
    expect(find.text('Date: —'), findsNWidgets(2));
  });

  testWidgets('BMP10 complete empty remains an observation view without false risk analysis', (tester) async {
    await tester.pumpWidget(_app(Bmp10Screen(client: LumenisCoreClient(),
      repository: _Ten(_bmp10(empty: true))), const Locale('en')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('bmp10-observations')), findsOneWidget);
    expect(find.textContaining('Risk analysis has not been computed'), findsOneWidget);
    expect(find.text('No observations of this type were returned.'), findsNWidgets(2));
  });

  testWidgets('denied scope never renders source titles in either screen', (tester) async {
    final three = _bmp03();
    (three['source_read_binding'] as Map)['read_allowed'] = false;
    await tester.pumpWidget(_app(Bmp03Screen(client: LumenisCoreClient(),
      repository: _Three(three)), const Locale('en')));
    await tester.pumpAndSettle();
    expect(find.text('Market source'), findsNothing);
    expect(find.byKey(const Key('bmp03-source-observations')), findsNothing);
    final ten = _bmp10();
    (ten['observation_read_binding'] as Map)['read_allowed'] = false;
    await tester.pumpWidget(_app(Bmp10Screen(client: LumenisCoreClient(),
      repository: _Ten(ten)), const Locale('en')));
    await tester.pumpAndSettle();
    expect(find.text('Observed event'), findsNothing);
    expect(find.byKey(const Key('bmp10-observations')), findsNothing);
  });
}

Widget _app(Widget screen, Locale locale) => MaterialApp(
  theme: LumenisTheme.dark, locale: locale,
  supportedLocales: LumenisLocalizations.supportedLocales,
  localizationsDelegates: const [LumenisLocalizations.delegate,
    GlobalMaterialLocalizations.delegate, GlobalWidgetsLocalizations.delegate,
    GlobalCupertinoLocalizations.delegate],
  home: Scaffold(body: screen),
);

class _Three implements Bmp03Repository {
  _Three(this.response);
  final Map<String, dynamic> response;
  @override
  Future<Bmp03Snapshot> load() async => Bmp03Snapshot.fromResponse(response);
}
class _Ten implements Bmp10Repository {
  _Ten(this.response);
  final Map<String, dynamic> response;
  @override
  Future<Bmp10Snapshot> load() async => Bmp10Snapshot.fromResponse(response);
}

Map<String, dynamic> _binding() => {
  'contract': 'lumenis.scope-read-binding.v1',
  'module': 'brand_market_overview', 'policy': 'actor-exact-scope-v1',
  'actor_scope': 'authenticated', 'actor_id': 1,
  'applied': true, 'read_allowed': true, 'scope_verified': true,
  'domain_id': 'BMP', 'product_id': 'ZBMP', 'canonical_scope': 'FOCUS',
  'subject_id': 'SUBJECT', 'brand_focus_id': 'BRAND', 'global_all_granted': false,
};
Map<String, dynamic> _proof() => {
  'id': 7, 'source_id': 'SOURCE',
  'stored_scope': {'domain_id': 'zbmp', 'product_id': 'ZBMP',
    'scope_status': 'VERIFIED', 'subject_id': null, 'brand_focus_id': 'BRAND', 'global': false},
  'integrity': {'integrity_version': 2, 'verified': true, 'lineage_verified': true,
    'assurance': 'writer-authenticated', 'algorithm': 'hmac-sha256',
    'digest': List.filled(64, 'a').join()},
};
Map<String, dynamic> _bmp03({bool empty = false, bool partial = false}) => {
  'ok': true, 'screen': 'BMP-03', 'bound': true, 'source': 'runtime',
  'source_observation_contract': 'lumenis.bmp03-source-observations.v1',
  'source_read_binding': _binding(),
  'source_context': {'mode': 'FOCUS', 'domain_id': 'BMP', 'product_id': 'ZBMP',
    'subject_id': 'SUBJECT', 'brand_focus_id': 'BRAND'},
  'truth': {'product_id': 'ZBMP', 'domain_id': 'zbmp', 'source_count': empty ? 0 : 1,
    'rejected_count': 0, 'truncated': partial,
    'data_state': partial ? 'PARTIAL' : empty ? 'EMPTY' : 'READY'},
  'source_observations': empty ? [] : [
    {'id': 'SOURCE', 'title': 'Market source', 'platform': 'Platform', 'scope_evidence': _proof()}],
};
Map<String, dynamic> _bmp10({bool empty = false, bool partial = false}) => {
  'ok': true, 'screen': 'BMP-10', 'bound': true, 'source': 'runtime',
  'observation_contract': 'lumenis.bmp10-observations.v1',
  'observation_read_binding': _binding(),
  'observation_context': {'canonical_scope': 'FOCUS', 'domain_id': 'BMP',
    'product_id': 'ZBMP', 'subject_id': 'SUBJECT', 'brand_focus_id': 'BRAND', 'actor_id': 1},
  'truth': {'domain_id': 'zbmp', 'product_id': 'ZBMP', 'analysis_state': 'NOT_COMPUTED',
    'data_state': partial ? 'PARTIAL' : empty ? 'EMPTY' : 'READY',
    'event_read': {'observed_returned_count': empty ? 0 : 1, 'rejected_count': 0,
      'truncated': partial, 'read_complete': !partial},
    'coverage': {'risk_returned_count': empty ? 0 : 1, 'risk_observed_count': empty ? 0 : 1,
      'rejected_sources': 0, 'source_truncated': false, 'risk_truncated': false,
      'source_read_complete': true, 'risk_read_complete': true}},
  'observed_events': empty ? [] : [{'id': 1, 'title': 'Observed event', 'scope_evidence': _proof()}],
  'observed_risks': empty ? [] : [{'id': 'RISK', 'title': 'Observed risk', 'scope_evidence': _proof()}],
};
