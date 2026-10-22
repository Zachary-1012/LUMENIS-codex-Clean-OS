import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/core/lumenis_theme.dart';
import 'package:lumenis_app/features/bmp03/bmp03_repository.dart';
import 'package:lumenis_app/features/bmp03/bmp03_screen.dart';
import 'package:lumenis_app/features/bmp03/bmp03_snapshot.dart';
import 'package:lumenis_app/features/bmp03/bmp03_view_model.dart';
import 'package:lumenis_app/l10n/lumenis_localizations.dart';
import '../shared/bmp_scope_test_support.dart';

void main() {
  test(
    'absent and malformed metrics remain unknown while explicit zero stays zero',
    () {
      for (final value in [null, 'unknown', -1, 101, double.nan]) {
        final row = {..._signal('SIG-ONE', '有来源的资讯'), 'momentum': value};
        final signal = Bmp03Snapshot.fromResponse(
          _response(signals: [row]),
        ).signals.single;
        expect(signal.momentum, isNull);
        expect(signal.confidence, 82);
        expect(signal.summary, isNotNull);
      }

      final missingBoth = {
        ..._signal('SIG-MISSING', '指标待补充'),
        'confidence': null,
        'momentum': null,
      };
      final missing = Bmp03Snapshot.fromResponse(
        _response(signals: [missingBoth]),
      ).signals.single;
      expect(missing.confidence, isNull);
      expect(missing.momentum, isNull);

      final zero = Bmp03Snapshot.fromResponse(
        _response(
          signals: [_signal('SIG-ZERO', '实际为零', confidence: 0, momentum: 0)],
        ),
      ).signals.single;
      expect(zero.confidence, 0);
      expect(zero.momentum, 0);

      final legacy = {..._signal('SIG-LEGACY', '旧字段'), 'momentum_score': 43}
        ..remove('momentum');
      expect(Bmp03Signal.fromJson(legacy)!.momentum, 43);
      expect(
        Bmp03Signal.fromJson({...legacy, 'momentum': null})!.momentum,
        isNull,
      );
    },
  );

  testWidgets(
    'mobile reading restores filtered row, scroll and keyboard focus',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(390, 844));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      final rows = List.generate(22, (i) => _signal('SIG-$i', '资讯 $i'));
      rows.add({
        ..._signal('SIG-RISK', '其他分类'),
        'kind': 'risk',
        'kind_label': {'zh-CN': '风险', 'en': 'Risk', 'ko': '위험'},
      });
      await tester.pumpWidget(_app(_FakeRepository(_response(signals: rows))));
      await tester.pumpAndSettle();
      await tester.tap(find.widgetWithText(FilterChip, '机会'));
      await tester.pumpAndSettle();

      final browse = tester
          .widget<SingleChildScrollView>(
            find.byKey(const PageStorageKey('bmp03-browse')),
          )
          .controller!;
      browse.jumpTo(browse.position.maxScrollExtent);
      await tester.pumpAndSettle();
      final oldOffset = browse.offset;
      final row = find.byKey(const Key('bmp03-signal-SIG-21'));
      final rowFocus = tester.widget<InkWell>(row).focusNode!;
      await tester.tap(row);
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('bmp03-brief-return')), findsOneWidget);
      expect(find.byKey(const PageStorageKey('bmp03-browse')), findsNothing);
      expect(find.byType(SelectableText), findsOneWidget);
      await tester.sendKeyEvent(LogicalKeyboardKey.escape);
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('bmp03-brief-return')), findsNothing);
      expect(browse.offset, closeTo(oldOffset, .1));
      expect(rowFocus.hasFocus, isTrue);
      expect(
        tester
            .widget<FilterChip>(find.widgetWithText(FilterChip, '机会'))
            .selected,
        isTrue,
      );
      expect(find.byKey(const Key('bmp03-signal-SIG-RISK')), findsNothing);

      await tester.sendKeyEvent(LogicalKeyboardKey.enter);
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('bmp03-brief-return')), findsOneWidget);
      await tester.tap(find.byKey(const Key('bmp03-brief-return')));
      await tester.pumpAndSettle();
      expect(rowFocus.hasFocus, isTrue);
      expect(tester.takeException(), isNull);
    },
  );

  for (final locale in [
    const Locale('zh', 'CN'),
    const Locale('en'),
    const Locale('ko'),
  ]) {
    testWidgets(
      'short viewport and large text keep reading and return reachable ${locale.languageCode}',
      (tester) async {
        await tester.binding.setSurfaceSize(const Size(360, 560));
        addTearDown(() => tester.binding.setSurfaceSize(null));
        final row = {
          ..._signal('SIG-ONE', '市场材料 / Market material'),
          'summary': List.filled(
            18,
            '一段需要完整阅读的材料。 A source paragraph.',
          ).join('\n'),
          'momentum': null,
        };
        await tester.pumpWidget(
          _app(
            _FakeRepository(_response(signals: [row])),
            locale: locale,
            textScale: 2,
          ),
        );
        await tester.pumpAndSettle();
        await tester.tap(find.byKey(const Key('bmp03-signal-SIG-ONE')));
        await tester.pumpAndSettle();

        final brief = tester
            .widget<SingleChildScrollView>(
              find.byKey(const Key('bmp03-brief-scroll')),
            )
            .controller!;
        brief.jumpTo(brief.position.maxScrollExtent);
        await tester.pumpAndSettle();
        expect(
          find.byKey(const Key('bmp03-brief-return')).hitTestable(),
          findsOneWidget,
        );
        expect(
          find.text(
            locale.languageCode == 'zh'
                ? '未提供'
                : locale.languageCode == 'ko'
                ? '제공되지 않음'
                : 'Not provided',
          ),
          findsOneWidget,
        );
        await tester.tap(find.byKey(const Key('bmp03-brief-return')));
        await tester.pumpAndSettle();
        expect(find.byKey(const Key('bmp03-signal-SIG-ONE')), findsOneWidget);
        expect(tester.takeException(), isNull);
      },
    );
  }

  testWidgets('a denied replacement scope clears the previously opened brief', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(
      _app(_FakeRepository(_response(signals: [_signal('SIG-ONE', '旧范围内容')]))),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('bmp03-signal-SIG-ONE')));
    await tester.pumpAndSettle();

    final denied = _response(signals: [_signal('SIG-ONE', '不应显示')]);
    denied['focus_binding'] = {'read_allowed': false};
    await tester.pumpWidget(_app(_FakeRepository(denied)));
    await tester.pumpAndSettle();
    expect(find.text('旧范围内容'), findsNothing);
    expect(find.text('不应显示'), findsNothing);
    expect(find.byType(SelectableText), findsNothing);
    expect(find.byKey(const Key('bmp03-brief-return')), findsNothing);
    expect(tester.takeException(), isNull);
  });

  test('filtering keeps the selected signal inside the visible set', () async {
    final viewModel = Bmp03ViewModel(
      repository: _FakeRepository(
        _response(
          signals: [
            _signal('SIG-OPPORTUNITY', '机会'),
            {..._signal('SIG-RISK', '风险'), 'kind': 'risk'},
          ],
        ),
      ),
    );
    addTearDown(viewModel.dispose);
    await viewModel.refresh();
    viewModel.selectSignal('SIG-OPPORTUNITY');
    viewModel.setKindFilter('risk');
    expect(viewModel.selectedSignalId, 'SIG-RISK');
    expect(viewModel.selectedSignal!.id, 'SIG-RISK');
    viewModel.setKindFilter('absent');
    expect(viewModel.selectedSignalId, isNull);
    expect(viewModel.selectedSignal, isNull);
  });

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

Widget _app(
  Bmp03Repository repository, {
  Locale locale = const Locale('zh', 'CN'),
  double textScale = 1,
}) {
  return MaterialApp(
    theme: LumenisTheme.dark,
    locale: locale,
    builder: (context, child) => MediaQuery(
      data: MediaQuery.of(
        context,
      ).copyWith(textScaler: TextScaler.linear(textScale)),
      child: child!,
    ),
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
  num? confidence = 82,
  num? momentum = 74,
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
