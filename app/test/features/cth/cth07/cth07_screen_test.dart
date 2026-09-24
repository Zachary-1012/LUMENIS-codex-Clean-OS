import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/core/lumenis_theme.dart';
import 'package:lumenis_app/features/cth/cth07/cth07_repository.dart';
import 'package:lumenis_app/features/cth/cth07/cth07_screen.dart';
import 'package:lumenis_app/l10n/lumenis_localizations.dart';

import '../cth_test_support.dart';

void main() {
  testWidgets('raw arrays without a trend definition stay unavailable', (
    tester,
  ) async {
    final client = _FakeClient(
      contextResponse: _globalContext,
      screenResponse: _chartResponse,
    );
    await tester.pumpWidget(_app(client: client));
    await tester.pumpAndSettle();

    expect(find.text('尚未采集'), findsNWidgets(2));
    expect(find.text('09-21'), findsNothing);
    expect(find.text('database.get_stats_by_date_range'), findsNothing);
    _expectNoInternalCopy(tester);
  });

  test('a bound global trend without grant or lineage is withheld', () async {
    final hostile = Map<String, dynamic>.from(_chartResponse)
      ..remove('global_binding');
    final client = _FakeClient(
      contextResponse: _globalContext,
      screenResponse: hostile,
    );

    await expectLater(
      CoreCth07Repository(client: client).load(),
      throwsA(
        isA<Cth07ContextUnavailable>().having(
          (error) => error.reason,
          'reason',
          Cth07BlockReason.pageNotBound,
        ),
      ),
    );
  });

  test('a server-authorized global trend can be consumed', () async {
    final client = _FakeClient(
      contextResponse: _globalContext,
      screenResponse: _globalTrendResponse,
    );

    final data = await CoreCth07Repository(client: client).load();

    expect(data.context.mode, 'GLOBAL_ALL');
    expect(data.trendAvailable, isTrue);
    expect(data.definition?.subject, 'GLOBAL/ALL');
  });

  test('an applied Guangzhou Taikoo Hui focus keeps the trend scope', () async {
    final client = _FakeClient(
      contextResponse: _guangzhouFocusContext,
      screenResponse: _focusedTrendResponse,
    );

    final data = await CoreCth07Repository(client: client).load();

    expect(data.context.mode, 'FOCUS');
    expect(data.context.subjectId, 'GUANGZHOU_TAIKOO_HUI');
    expect(data.trendAvailable, isTrue);
    expect(data.definition?.subject, 'GUANGZHOU_TAIKOO_HUI');
  });

  testWidgets('desktop trend preserves definition, chart and decomposition', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(
      _app(repository: _FakeRepository(Future.value(_trendData()))),
    );
    await tester.pumpAndSettle();

    expect(find.byKey(const ValueKey('cth07/desktop-layout')), findsOneWidget);
    expect(find.byKey(const ValueKey('cth07/definition-rail')), findsOneWidget);
    expect(find.byKey(const ValueKey('cth07/trend-canvas')), findsOneWidget);
    expect(find.byKey(const ValueKey('cth07/decomposition')), findsOneWidget);
    expect(find.byKey(const ValueKey('cth07/definition-rail')), findsOneWidget);
    expect(find.text('总量'), findsNWidgets(2));
    expect(
      find.byWidgetPredicate(
        (widget) =>
            widget is Semantics &&
            (widget.properties.label ?? '').contains('总量, 3 时间'),
      ),
      findsOneWidget,
    );

    await tester.tap(find.text('负面'));
    await tester.pumpAndSettle();
    expect(
      find.byWidgetPredicate(
        (widget) =>
            widget is Semantics &&
            (widget.properties.label ?? '').contains('负面, 3 时间'),
      ),
      findsOneWidget,
    );
    _expectNoInternalCopy(tester);
    expect(tester.takeException(), isNull);
  });

  testWidgets('mobile keeps the trend workflow readable without overflow', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(
      _app(repository: _FakeRepository(Future.value(_trendData()))),
    );
    await tester.pumpAndSettle();

    expect(find.byKey(const ValueKey('cth07/mobile-layout')), findsOneWidget);
    expect(find.text('状态'), findsOneWidget);
    expect(find.text('状态: -2'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('empty trend does not become an invented zero series', (
    tester,
  ) async {
    await tester.pumpWidget(
      _app(
        repository: _FakeRepository(
          Future.value(
            Cth07ScreenData(
              context: const Cth07Context(mode: 'GLOBAL_ALL'),
              generatedAt: '2026-09-22T10:00:00',
              labels: const [],
              series: const [],
              state: Cth07DataState.empty,
              definition: _definition,
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('尚未采集'), findsOneWidget);
    expect(find.text('0'), findsNothing);
  });
}

Widget _app({Cth07Repository? repository, LumenisCoreClient? client}) =>
    MaterialApp(
      locale: const Locale('zh', 'CN'),
      theme: LumenisTheme.dark,
      supportedLocales: LumenisLocalizations.supportedLocales,
      localizationsDelegates: const [
        LumenisLocalizations.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      home: Scaffold(
        body: Cth07Screen(
          client: client ?? LumenisCoreClient(),
          repository: repository,
        ),
      ),
    );

class _FakeRepository implements Cth07Repository {
  const _FakeRepository(this.future);

  final Future<Cth07ScreenData> future;

  @override
  Future<Cth07ScreenData> load() => future;
}

class _FakeClient extends LumenisCoreClient {
  _FakeClient({required this.contextResponse, required this.screenResponse});

  final Map<String, dynamic> contextResponse;
  final Map<String, dynamic> screenResponse;

  @override
  Future<Map<String, dynamic>> settingsContext() async => contextResponse;

  @override
  Future<Map<String, dynamic>> screen(String screenId) async {
    expect(screenId, 'CTH-07');
    return screenResponse;
  }
}

Cth07ScreenData _trendData() => const Cth07ScreenData(
  context: Cth07Context(mode: 'GLOBAL_ALL'),
  generatedAt: '2026-09-22T10:00:00',
  labels: ['09-20', '09-21', '09-22'],
  series: [
    Cth07Series(label: '总量', values: [6, 5, 4]),
    Cth07Series(label: '负面', values: [2, 1, 1]),
  ],
  state: Cth07DataState.ready,
  definition: _definition,
);

const Cth07TrendDefinition _definition = Cth07TrendDefinition(
  numerator: '返回记录数',
  denominator: '全部可用记录数',
  timeWindow: '2026-09-20 至 2026-09-22',
  subject: 'GLOBAL/ALL',
  source: 'verified notes',
  freshness: '2026-09-22T10:00:00',
);

const Map<String, dynamic> _globalContext = {
  'ok': true,
  'contract': 'lumenis.context.v1',
  'context': {'mode': 'GLOBAL_ALL'},
};

const Map<String, dynamic> _guangzhouFocusContext = {
  'ok': true,
  'contract': 'lumenis.context.v1',
  'context': {
    'mode': 'FOCUS',
    'domain_id': 'CTH',
    'subject_id': 'GUANGZHOU_TAIKOO_HUI',
    'display_name': {'zh-CN': '广州太古汇'},
  },
};

const Map<String, dynamic> _chartResponse = {
  'ok': true,
  'screen': 'CTH-07',
  'bound': true,
  'global_binding': {
    'applied': true,
    'global_all_granted': true,
    'canonical_scope': 'GLOBAL_ALL',
    'scope_verified': true,
    'read_allowed': true,
    'domain_id': 'CTH',
    'product_id': 'CTH',
    'evidence_lineage': 'verified',
    'projection': cthGlobalProjection,
  },
  'generated_at': '2026-09-22T10:00:00',
  'sections': [
    {
      'type': 'chart',
      'state': 'ready',
      'projection': cthGlobalProjection,
      'labels': ['09-20', '09-21'],
      'series': [
        {
          'name': '总量',
          'data': [6, 5],
        },
      ],
    },
  ],
};

final Map<String, dynamic> _focusedTrendResponse = {
  ..._chartResponse,
  'sections': [
    {
      ...(_chartResponse['sections'] as List).first as Map,
      'projection': cthGuangzhouFocusProjection,
    },
  ],
  'focus_binding': {
    'applied': true,
    'subject_id': 'GUANGZHOU_TAIKOO_HUI',
    'canonical_scope': 'FOCUS',
    'scope_verified': true,
    'read_allowed': true,
    'domain_id': 'CTH',
    'product_id': 'CTH',
    'evidence_lineage': 'verified',
    'projection': cthGuangzhouFocusProjection,
  },
  'trend_metadata': {
    'numerator': '返回记录数',
    'denominator': '全部可用记录数',
    'time_window': '2026-09-20 至 2026-09-22',
    'subject': 'GUANGZHOU_TAIKOO_HUI',
    'source': 'verified notes',
    'freshness': '2026-09-22T10:00:00',
    'projection': cthGuangzhouFocusProjection,
  },
};

final Map<String, dynamic> _globalTrendResponse = {
  ..._chartResponse,
  'trend_metadata': {
    'numerator': '返回记录数',
    'denominator': '全部可用记录数',
    'time_window': '2026-09-20 至 2026-09-21',
    'subject': 'GLOBAL/ALL',
    'source': 'verified notes',
    'freshness': '2026-09-22T10:00:00',
    'projection': cthGlobalProjection,
  },
};

void _expectNoInternalCopy(WidgetTester tester) {
  final text = tester
      .widgetList<Text>(find.byType(Text))
      .map((widget) => widget.data ?? widget.textSpan?.toPlainText() ?? '')
      .join(' ')
      .toLowerCase();
  for (final term in const [
    'api',
    'core',
    'database',
    'evidence',
    'permission',
    'owner',
    'canonical',
    'unknown',
  ]) {
    expect(text, isNot(contains(term)), reason: 'UI leaked $term');
  }
}
