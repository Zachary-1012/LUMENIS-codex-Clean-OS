import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/core/lumenis_theme.dart';
import 'package:lumenis_app/features/bmp02/bmp02_repository.dart';
import 'package:lumenis_app/features/bmp02/bmp02_screen.dart';
import 'package:lumenis_app/features/bmp02/bmp02_snapshot.dart';
import 'package:lumenis_app/l10n/lumenis_localizations.dart';
import '../shared/bmp_scope_test_support.dart';

void main() {
  test('keeps BrandFocus separate from Subject and drops cross-focus rows', () {
    final snapshot = Bmp02Snapshot.fromResponse(
      _response(
        brands: [
          _brand('BRAND-ONE', 'Primary'),
          _brand('BRAND-TWO', 'Other brand', scopeId: 'BRAND-TWO'),
          {
            ..._brand('SUBJ-ONE', 'Compatibility alias'),
            'brand_focus_id': 'SUBJ-ONE',
          },
        ],
      ),
    );

    expect(snapshot.scopeReady, isTrue);
    expect(snapshot.canDisplayBrands, isTrue);
    expect(snapshot.brands.map((brand) => brand.name), ['Primary']);
    expect(snapshot.rejectedCrossFocusCount, 2);
  });

  test(
    'drops missing-scope and forged-integrity rows without blocking valid rows',
    () {
      final response = _response(
        brands: [
          _brand('BRAND-ONE', 'Primary'),
          {..._brand('BRAND-MISSING', 'Missing scope'), 'scope': null},
          {
            ..._brand('BRAND-FORGED', 'Forged evidence'),
            'evidence': bmpTestEvidence(
              bmpFocusScope(),
              verified: false,
              assurance: 'tampered',
            ),
          },
        ],
      );

      final snapshot = Bmp02Snapshot.fromResponse(response);

      expect(snapshot.brands.map((brand) => brand.name), ['Primary']);
      expect(snapshot.rejectedUnscopedCount, 2);
      expect(snapshot.presentationState, Bmp02PresentationState.ready);
    },
  );

  test('global view rejects focused rows without a global contract', () {
    final response = _response(brands: [_brand('BRAND-ONE', 'Primary')]);
    response['focus_context'] = {
      'mode': 'GLOBAL_ALL',
      'domain_id': 'BMP',
      'product_id': 'ZBMP',
      'subject_id': null,
      'brand_focus_id': null,
    };

    final snapshot = Bmp02Snapshot.fromResponse(response);

    expect(snapshot.presentationState, Bmp02PresentationState.blocked);
    expect(snapshot.brands, isEmpty);
    expect(snapshot.canDisplayBrands, isFalse);
  });

  test('global rows still require a response-level global binding', () {
    final response = _response(
      brands: [_globalBrand(_brand('BRAND-GLOBAL', 'Global brand'))],
    );
    response['focus_context'] = {
      'mode': 'GLOBAL_ALL',
      'domain_id': 'BMP',
      'product_id': 'ZBMP',
      'subject_id': null,
      'brand_focus_id': null,
    };

    final snapshot = Bmp02Snapshot.fromResponse(response);

    expect(snapshot.presentationState, Bmp02PresentationState.blocked);
    expect(snapshot.brands, isEmpty);
  });

  test('authorized global rows enter the same portfolio workspace', () {
    final response = _response(
      brands: [_globalBrand(_brand('BRAND-ONE', 'Primary'))],
    );
    _makeGlobal(response);

    final snapshot = Bmp02Snapshot.fromResponse(response);

    expect(snapshot.globalScopeReady, isTrue);
    expect(snapshot.scopeReady, isTrue);
    expect(snapshot.presentationState, Bmp02PresentationState.ready);
    expect(snapshot.brands.map((brand) => brand.name), ['Primary']);
  });

  testWidgets('authorized global rows render the portfolio workspace', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    final response = _response(
      brands: [_globalBrand(_brand('BRAND-ONE', 'Primary'))],
    );
    _makeGlobal(response);
    await tester.pumpWidget(_app(_FakeRepository(response)));
    await tester.pumpAndSettle();

    expect(
      find.byKey(const Key('bmp02-brand-BRAND-ONE-ENTITY')),
      findsOneWidget,
    );
    expect(find.text('品牌中心 / 多品牌与竞品'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('desktop portfolio flow is scoped and accessible', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      _app(
        _FakeRepository(
          _response(
            brands: [
              _brand(
                'BRAND-ONE',
                'Primary',
                roleLabel: {'zh-CN': '自有品牌', 'en': 'Owned', 'ko': '자체 브랜드'},
              ),
              _brand(
                'BRAND-COMP',
                'Competitor',
                role: 'competitor',
                roleLabel: {'zh-CN': '竞品', 'en': 'Competitor', 'ko': '경쟁 브랜드'},
              ),
            ],
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('品牌中心 / 多品牌与竞品'), findsOneWidget);
    expect(find.text('Primary'), findsWidgets);
    expect(
      find.byKey(const Key('bmp02-brand-BRAND-COMP-ENTITY')),
      findsOneWidget,
    );
    expect(find.bySemanticsLabel(RegExp('品牌：主品牌')), findsOneWidget);
    expect(_visibleCopy(tester), isNot(contains('Evidence')));
    expect(_visibleCopy(tester), isNot(contains('Permission')));
    expect(tester.takeException(), isNull);
  });

  testWidgets('mobile portfolio reflows without leaking hostile text', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      _app(
        _FakeRepository(
          _response(
            brands: [
              _brand('BRAND-ONE', 'Primary'),
              {
                ..._brand('BRAND-ONE', '<script>steal()</script>'),
                'source': 'private path',
              },
            ],
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Primary'), findsWidgets);
    expect(find.textContaining('<script>'), findsNothing);
    expect(find.textContaining('private path'), findsNothing);
    expect(
      find.byKey(const Key('bmp02-brand-BRAND-ONE-ENTITY')),
      findsOneWidget,
    );
    expect(tester.takeException(), isNull);
  });

  testWidgets('portfolio filters keep roles, selection, and a clear path', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      _app(
        _FakeRepository(
          _response(
            brands: [
              _brand('BRAND-ONE', 'Primary'),
              _brand(
                'BRAND-COMP',
                'Competitor',
                role: 'competitor',
                roleLabel: {
                  'zh-CN': '竞品',
                  'en': 'Competitor',
                  'ko': '경쟁 브랜드',
                },
              ),
            ],
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    final competitorTile = find.byKey(
      const Key('bmp02-brand-BRAND-COMP-ENTITY'),
    );
    await tester.ensureVisible(competitorTile);
    await tester.tap(competitorTile);
    await tester.pumpAndSettle();

    final ownedRole = find.widgetWithText(FilterChip, '自有品牌');
    await tester.ensureVisible(ownedRole);
    await tester.tap(ownedRole);
    await tester.pumpAndSettle();

    expect(find.widgetWithText(FilterChip, '竞品'), findsOneWidget);
    expect(competitorTile, findsNothing);
    final primaryTile = find.byKey(const Key('bmp02-brand-BRAND-ONE-ENTITY'));
    expect(primaryTile, findsOneWidget);
    expect(
      find.ancestor(
        of: primaryTile,
        matching: find.byWidgetPredicate(
          (widget) =>
              widget is Semantics && widget.properties.selected == true,
        ),
      ),
      findsOneWidget,
    );
    expect(find.text('Primary'), findsWidgets);

    await tester.enterText(find.byType(TextField), 'no matching brand');
    await tester.pumpAndSettle();
    expect(primaryTile, findsNothing);
    expect(find.text('Primary'), findsNothing);
    final clearFilters = find.text('清除筛选');
    expect(clearFilters, findsOneWidget);
    await tester.ensureVisible(clearFilters);

    await tester.tap(clearFilters);
    await tester.pumpAndSettle();

    expect(find.widgetWithText(FilterChip, '自有品牌'), findsOneWidget);
    expect(find.widgetWithText(FilterChip, '竞品'), findsOneWidget);
    expect(competitorTile, findsOneWidget);
    expect(
      find.ancestor(
        of: competitorTile,
        matching: find.byWidgetPredicate(
          (widget) =>
              widget is Semantics && widget.properties.selected == true,
        ),
      ),
      findsOneWidget,
    );
    expect(find.text('Competitor'), findsWidgets);
    expect(tester.takeException(), isNull);
  });

  test('not collected remains distinct from an empty ready response', () {
    final notCollected = Bmp02Snapshot.fromResponse(
      _response(dataState: 'NOT_COLLECTED', brands: []),
    );
    final empty = Bmp02Snapshot.fromResponse(
      _response(dataState: 'READY', brands: []),
    );

    expect(notCollected.presentationState, Bmp02PresentationState.notCollected);
    expect(empty.presentationState, Bmp02PresentationState.empty);
  });
}

Widget _app(
  Bmp02Repository repository, {
  Locale locale = const Locale('zh', 'CN'),
}) {
  return MaterialApp(
    theme: LumenisTheme.dark,
    locale: locale,
    supportedLocales: LumenisLocalizations.supportedLocales,
    localizationsDelegates: const [
      LumenisLocalizations.delegate,
      GlobalMaterialLocalizations.delegate,
      GlobalWidgetsLocalizations.delegate,
      GlobalCupertinoLocalizations.delegate,
    ],
    home: Scaffold(
      body: Bmp02Screen(client: LumenisCoreClient(), repository: repository),
    ),
  );
}

class _FakeRepository implements Bmp02Repository {
  _FakeRepository(this.response);

  final Map<String, dynamic> response;

  @override
  Future<Bmp02Snapshot> load() async {
    return Bmp02Snapshot.fromResponse(response);
  }
}

Map<String, dynamic> _response({
  required List<Map<String, dynamic>> brands,
  String dataState = 'READY',
}) {
  return {
    'ok': true,
    'screen': 'BMP-02',
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
      'display_name': {'zh-CN': '主品牌', 'en': 'Primary', 'ko': '주요 브랜드'},
    },
    'focus_binding': bmpFocusBinding(),
    'sections': [
      {'type': 'brands', 'state': dataState, 'items': brands},
    ],
  };
}

Map<String, dynamic> _brand(
  String brandFocusId,
  String name, {
  String role = 'owned',
  Map<String, String>? roleLabel,
  String? scopeId,
}) {
  return {
    'id': '$brandFocusId-ENTITY',
    'brand_focus_id': scopeId ?? 'BRAND-ONE',
    'name': name,
    'role': role,
    'role_label': roleLabel ?? const {'zh-CN': '自有品牌', 'en': 'Owned'},
    'evidence': bmpTestEvidence(
      bmpFocusScope(brandFocusId: scopeId ?? 'BRAND-ONE'),
    ),
    'scope': bmpFocusScope(brandFocusId: scopeId ?? 'BRAND-ONE'),
    'read_allowed': true,
    'permission': bmpTestPermission(
      bmpFocusScope(brandFocusId: scopeId ?? 'BRAND-ONE'),
    ),
    'source': 'brand-source',
  };
}

Map<String, dynamic> _globalBrand(Map<String, dynamic> brand) => {
  ...brand,
  'brand_focus_id': null,
  'scope': bmpGlobalScope(),
  'permission': bmpTestPermission(bmpGlobalScope()),
  'evidence': bmpTestEvidence(bmpGlobalScope()),
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
  response['focus_binding'] = bmpGlobalBinding();
}

String _visibleCopy(WidgetTester tester) => <String>[
  ...tester
      .widgetList<Text>(find.byType(Text))
      .map((widget) => widget.data ?? widget.semanticsLabel ?? ''),
  ...tester
      .widgetList<Semantics>(find.byType(Semantics))
      .map((widget) => widget.properties.label ?? ''),
].join('\n');
