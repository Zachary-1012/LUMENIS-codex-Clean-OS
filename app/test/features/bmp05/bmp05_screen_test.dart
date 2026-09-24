import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/core/lumenis_theme.dart';
import 'package:lumenis_app/features/bmp05/bmp05_repository.dart';
import 'package:lumenis_app/features/bmp05/bmp05_screen.dart';
import 'package:lumenis_app/features/bmp05/bmp05_snapshot.dart';
import 'package:lumenis_app/l10n/lumenis_localizations.dart';

void main() {
  test('creator profiles reject cross-focus and compatibility identities', () {
    final snapshot = Bmp05Snapshot.fromResponse(
      _response(
        creators: [
          _creator('CREATOR-ONE', 'Creator One'),
          _creator('CREATOR-TWO', 'Other focus creator', scopeId: 'BRAND-TWO'),
          _creator('SUBJ-ONE', 'Subject-shaped creator', scopeId: 'SUBJ-ONE'),
        ],
      ),
    );

    expect(snapshot.scopeReady, isTrue);
    expect(snapshot.creators.map((creator) => creator.id), ['CREATOR-ONE']);
    expect(snapshot.rejectedCrossFocusCount, 1);
    expect(
      snapshot.rejectedCrossFocusCount + snapshot.rejectedUnscopedCount,
      2,
    );
  });

  test('global view rejects focused rows without a global contract', () {
    final response = _response(
      creators: [_creator('CREATOR-ONE', 'Creator One')],
    );
    _makeGlobal(response);

    final snapshot = Bmp05Snapshot.fromResponse(response);

    expect(snapshot.presentationState, Bmp05PresentationState.blocked);
    expect(snapshot.creators, isEmpty);
  });

  test('global rows still require a response-level global binding', () {
    final response = _response(
      creators: [_globalCreator(_creator('CREATOR-GLOBAL', 'Global Creator'))],
    );
    _makeGlobal(response);
    response['focus_binding'] = {'applied': true, 'read_allowed': true};

    final snapshot = Bmp05Snapshot.fromResponse(response);

    expect(snapshot.presentationState, Bmp05PresentationState.blocked);
    expect(snapshot.creators, isEmpty);
  });

  test('authorized global rows enter the creator ecosystem workspace', () {
    final response = _response(
      creators: [_globalCreator(_creator('CREATOR-GLOBAL', 'Global Creator'))],
    );
    _makeGlobal(response);

    final snapshot = Bmp05Snapshot.fromResponse(response);

    expect(snapshot.globalScopeReady, isTrue);
    expect(snapshot.scopeReady, isTrue);
    expect(snapshot.presentationState, Bmp05PresentationState.ready);
    expect(snapshot.creators.map((creator) => creator.id), ['CREATOR-GLOBAL']);
  });

  testWidgets('authorized global rows render the creator workspace', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    final response = _response(
      creators: [_globalCreator(_creator('CREATOR-GLOBAL', 'Global Creator'))],
    );
    _makeGlobal(response);
    await tester.pumpWidget(_app(_FakeRepository(response)));
    await tester.pumpAndSettle();

    expect(
      find.byKey(const Key('bmp05-creator-CREATOR-GLOBAL')),
      findsOneWidget,
    );
    expect(find.text('创作者 KOS/KOL/KOC/UGC'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  test('creator metrics never turn missing data into zero', () {
    final snapshot = Bmp05Snapshot.fromResponse(
      _response(
        creators: [
          {..._creator('CREATOR-ONE', 'Creator One'), 'engagement': null},
        ],
      ),
    );

    expect(snapshot.creators.single.engagement, isNull);
    expect(snapshot.creators.single.posts!.value, 18);
  });

  testWidgets('desktop creator ecosystem opens a source-backed dossier', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      _app(
        _FakeRepository(
          _response(
            creators: [
              _creator('CREATOR-ONE', 'Creator One'),
              _creator('CREATOR-TWO', 'Creator Two', tier: 'KOS'),
            ],
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('创作者 KOS/KOL/KOC/UGC'), findsOneWidget);
    expect(find.text('Creator One'), findsWidgets);
    expect(find.byKey(const Key('bmp05-creator-CREATOR-TWO')), findsOneWidget);
    expect(find.text('低风险'), findsWidgets);
    expect(_visibleCopy(tester), isNot(contains('Evidence')));
    expect(_visibleCopy(tester), isNot(contains('provider')));
    expect(tester.takeException(), isNull);
  });

  testWidgets('mobile creator ecosystem keeps touch-safe dossier flow', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      _app(
        _FakeRepository(
          _response(
            creators: [
              _creator('CREATOR-ONE', 'Creator One'),
              {
                ..._creator('CREATOR-BAD', 'Core Evidence /private/path'),
                'source': 'provider://unsafe',
              },
            ],
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Creator One'), findsWidgets);
    expect(find.textContaining('Core Evidence'), findsNothing);
    expect(find.textContaining('unsafe'), findsNothing);
    expect(tester.takeException(), isNull);
  });
}

Widget _app(Bmp05Repository repository) {
  return MaterialApp(
    theme: LumenisTheme.dark,
    locale: const Locale('zh', 'CN'),
    supportedLocales: LumenisLocalizations.supportedLocales,
    localizationsDelegates: const [
      LumenisLocalizations.delegate,
      GlobalMaterialLocalizations.delegate,
      GlobalWidgetsLocalizations.delegate,
      GlobalCupertinoLocalizations.delegate,
    ],
    home: Scaffold(
      body: Bmp05Screen(client: LumenisCoreClient(), repository: repository),
    ),
  );
}

class _FakeRepository implements Bmp05Repository {
  _FakeRepository(this.response);

  final Map<String, dynamic> response;

  @override
  Future<Bmp05Snapshot> load() async {
    return Bmp05Snapshot.fromResponse(response);
  }
}

Map<String, dynamic> _response({
  required List<Map<String, dynamic>> creators,
  String dataState = 'READY',
}) {
  return {
    'ok': true,
    'screen': 'BMP-05',
    'source': 'runtime',
    'bound': true,
    'truth': {
      'product_id': 'ZBMP',
      'domain_id': 'zbmp',
      'data_state': dataState,
    },
    'focus_context': {
      'mode': 'FOCUS',
      'domain_id': 'BMP',
      'product_id': 'ZBMP',
      'subject_id': 'SUBJ-ONE',
      'brand_focus_id': 'BRAND-ONE',
      'display_name': {'zh-CN': '主品牌', 'en': 'Primary'},
    },
    'focus_binding': {'applied': true, 'read_allowed': true},
    'sections': [
      {'type': 'creators', 'state': dataState, 'items': creators},
    ],
  };
}

Map<String, dynamic> _creator(
  String id,
  String name, {
  String scopeId = 'BRAND-ONE',
  String tier = 'KOL',
}) {
  return {
    'id': id,
    'brand_focus_id': scopeId,
    'name': name,
    'tier': tier,
    'platform': '小红书',
    'posts': _metric(18, '条'),
    'engagement': _metric(6.8, '%'),
    'conversion': _metric(3.2, '%'),
    'risk': {'level': 'low', 'label': '低风险', 'score': 12},
    'evidence_ref': 'EV-BMP05-1',
    'source': 'creator.report',
  };
}

Map<String, dynamic> _metric(num value, String unit) {
  return {
    'value': value,
    'unit': unit,
    'definition': '按来源记录统计',
    'window': '最近 30 天',
  };
}

Map<String, dynamic> _globalCreator(Map<String, dynamic> creator) => {
  ...creator,
  'scope_mode': 'GLOBAL_ALL',
  'canonical_scope': 'GLOBAL_ALL',
  'global_scope': true,
  'read_allowed': true,
  'lineage': {
    'scope_mode': 'GLOBAL_ALL',
    'status': 'VERIFIED',
    'canonical': true,
  },
};

void _makeGlobal(Map<String, dynamic> response) {
  response['focus_context'] = {
    'mode': 'GLOBAL_ALL',
    'domain_id': 'BMP',
    'product_id': 'ZBMP',
    'subject_id': null,
    'brand_focus_id': null,
  };
  response['focus_binding'] = {
    'applied': true,
    'read_allowed': true,
    'scope_verified': true,
    'global_all_granted': true,
    'evidence_lineage': 'verified',
    'canonical_scope': 'GLOBAL_ALL',
  };
}

String _visibleCopy(WidgetTester tester) => <String>[
  ...tester
      .widgetList<Text>(find.byType(Text))
      .map((widget) => widget.data ?? widget.semanticsLabel ?? ''),
  ...tester
      .widgetList<Semantics>(find.byType(Semantics))
      .map((widget) => widget.properties.label ?? ''),
].join('\n');
