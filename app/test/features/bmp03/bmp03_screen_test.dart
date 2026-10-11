import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/core/lumenis_theme.dart';
import 'package:lumenis_app/features/bmp03/bmp03_repository.dart';
import 'package:lumenis_app/features/bmp03/bmp03_screen.dart';
import 'package:lumenis_app/features/bmp03/bmp03_snapshot.dart';
import 'package:lumenis_app/l10n/lumenis_localizations.dart';
import '../shared/bmp_scope_test_support.dart';

void main() {
  test('market signals stay inside the selected BrandFocus', () {
    final snapshot = Bmp03Snapshot.fromResponse(
      _response(
        signals: [
          _signal('SIG-ONE', '体验机会', scopeId: 'BRAND-ONE'),
          _signal('SIG-TWO', '其他品牌机会', scopeId: 'BRAND-TWO'),
          _signal('SIG-SUBJECT', '兼容主体值', scopeId: 'SUBJ-ONE'),
        ],
      ),
    );

    expect(snapshot.scopeReady, isTrue);
    expect(snapshot.signals.map((signal) => signal.id), ['SIG-ONE']);
    expect(snapshot.rejectedCrossFocusCount, 1);
    expect(
      snapshot.rejectedCrossFocusCount + snapshot.rejectedUnscopedCount,
      2,
    );
  });

  test(
    'drops missing-scope and forged-integrity signals without hiding valid ones',
    () {
      final response = _response(
        signals: [
          _signal('SIG-ONE', '体验机会'),
          {..._signal('SIG-MISSING', 'Missing scope'), 'scope': null},
          {
            ..._signal('SIG-FORGED', 'Forged evidence'),
            'evidence': bmpTestEvidence(
              bmpFocusScope(),
              verified: false,
              assurance: 'tampered',
            ),
          },
        ],
      );

      final snapshot = Bmp03Snapshot.fromResponse(response);

      expect(snapshot.signals.map((signal) => signal.id), ['SIG-ONE']);
      expect(snapshot.rejectedUnscopedCount, 2);
      expect(snapshot.presentationState, Bmp03PresentationState.ready);
    },
  );

  test('global view rejects focused rows without a global contract', () {
    final response = _response(signals: [_signal('SIG-ONE', '体验机会')]);
    _makeGlobal(response);

    final snapshot = Bmp03Snapshot.fromResponse(response);

    expect(snapshot.presentationState, Bmp03PresentationState.blocked);
    expect(snapshot.signals, isEmpty);
  });

  test('global rows still require a response-level global binding', () {
    final response = _response(
      signals: [_globalSignal(_signal('SIG-GLOBAL', '全球机会'))],
    );
    _makeGlobal(response);
    response['focus_binding'] = {'applied': true, 'read_allowed': true};

    final snapshot = Bmp03Snapshot.fromResponse(response);

    expect(snapshot.presentationState, Bmp03PresentationState.blocked);
    expect(snapshot.signals, isEmpty);
  });

  test('authorized global rows enter the market intelligence workspace', () {
    final response = _response(
      signals: [_globalSignal(_signal('SIG-GLOBAL', '全球机会'))],
    );
    _makeGlobal(response);

    final snapshot = Bmp03Snapshot.fromResponse(response);

    expect(snapshot.globalScopeReady, isTrue);
    expect(snapshot.scopeReady, isTrue);
    expect(snapshot.presentationState, Bmp03PresentationState.ready);
    expect(snapshot.signals.map((signal) => signal.id), ['SIG-GLOBAL']);
  });

  testWidgets('authorized global rows render the market workspace', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    final response = _response(
      signals: [_globalSignal(_signal('SIG-GLOBAL', '全球机会'))],
    );
    _makeGlobal(response);
    await tester.pumpWidget(_app(_FakeRepository(response)));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('bmp03-signal-SIG-GLOBAL')), findsOneWidget);
    expect(find.text('市场情报'), findsWidgets);
    expect(tester.takeException(), isNull);
  });

  test('unknown and not-collected states do not become zero opportunities', () {
    final unknown = Bmp03Snapshot.fromResponse(
      _response(dataState: 'UNKNOWN', signals: []),
    );
    final notCollected = Bmp03Snapshot.fromResponse(
      _response(dataState: 'NOT_COLLECTED', signals: []),
    );

    expect(unknown.presentationState, Bmp03PresentationState.unknown);
    expect(notCollected.presentationState, Bmp03PresentationState.notCollected);
  });

  testWidgets('desktop market intelligence exposes the source brief', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      _app(
        _FakeRepository(
          _response(
            signals: [
              _signal(
                'SIG-ONE',
                '体验机会',
                kindLabel: {'zh-CN': '机会', 'en': 'Opportunity', 'ko': '기회'},
              ),
              _signal('SIG-TWO', '渠道变化', momentum: 46),
            ],
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('市场情报'), findsWidgets);
    expect(find.text('体验机会'), findsWidgets);
    // The source is shown on each signal card and in the selected-signal detail.
    expect(find.text('market.report'), findsWidgets);
    expect(find.byKey(const Key('bmp03-signal-SIG-TWO')), findsOneWidget);
    expect(_visibleCopy(tester), isNot(contains('Evidence')));
    expect(_visibleCopy(tester), isNot(contains('runtime')));
    expect(tester.takeException(), isNull);
  });

  testWidgets('mobile market intelligence reflows and filters hostile rows', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      _app(
        _FakeRepository(
          _response(
            signals: [
              _signal('SIG-ONE', '体验机会'),
              {
                ..._signal('SIG-BAD', 'Core owner Evidence /private/path'),
                'source': 'https://unsafe',
              },
            ],
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('体验机会'), findsWidgets);
    expect(find.textContaining('Core owner'), findsNothing);
    expect(find.textContaining('unsafe'), findsNothing);
    expect(tester.takeException(), isNull);
  });
}

Widget _app(Bmp03Repository repository) {
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
      body: Bmp03Screen(client: LumenisCoreClient(), repository: repository),
    ),
  );
}

class _FakeRepository implements Bmp03Repository {
  _FakeRepository(this.response);

  final Map<String, dynamic> response;

  @override
  Future<Bmp03Snapshot> load() async {
    return Bmp03Snapshot.fromResponse(response);
  }
}

Map<String, dynamic> _response({
  required List<Map<String, dynamic>> signals,
  String dataState = 'READY',
}) {
  return {
    'ok': true,
    'screen': 'BMP-03',
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
    'focus_binding': bmpFocusBinding(),
    'sections': [
      {'type': 'signals', 'state': dataState, 'items': signals},
    ],
  };
}

Map<String, dynamic> _signal(
  String id,
  String title, {
  String scopeId = 'BRAND-ONE',
  num confidence = 82,
  num momentum = 74,
  Map<String, String>? kindLabel,
}) {
  return {
    'id': id,
    'brand_focus_id': scopeId,
    'title': title,
    'kind': 'opportunity',
    'kind_label': kindLabel ?? const {'zh-CN': '机会', 'en': 'Opportunity'},
    'confidence': confidence,
    'momentum': momentum,
    'source': 'market.report',
    'evidence': bmpTestEvidence(bmpFocusScope(brandFocusId: scopeId)),
    'scope': bmpFocusScope(brandFocusId: scopeId),
    'read_allowed': true,
    'permission': bmpTestPermission(bmpFocusScope(brandFocusId: scopeId)),
    'captured_at': '2026-09-22',
    'time_window': '最近 30 天',
    'summary': '已标记为待复核的市场信号。',
  };
}

Map<String, dynamic> _globalSignal(Map<String, dynamic> signal) => {
  ...signal,
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
