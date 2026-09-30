import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/core/lumenis_theme.dart';
import 'package:lumenis_app/features/cth/cth05/cth05_repository.dart';
import 'package:lumenis_app/features/cth/cth05/cth05_screen.dart';
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

    expect(find.text('尚未采集'), findsOneWidget);
    expect(find.text('09-21'), findsNothing);
    expect(find.text('database.get_stats_by_date_range'), findsNothing);
    _expectNoInternalCopy(tester);
  });

  testWidgets(
    'authentication and access failures remain distinct and retryable',
    (tester) async {
      for (final statusCode in [401, 403]) {
        await tester.pumpWidget(const SizedBox.shrink());
        await tester.pump();
        final repository = _RecoveringCth05Repository(
          statusCode,
          _calendarData(),
        );
        await tester.pumpWidget(_app(repository: repository));
        await tester.pumpAndSettle();

        final expected = statusCode == 401
            ? '当前内容暂时无法打开。可重试读取，或返回后稍后再试。'
            : '当前内容不可访问。';
        expect(find.text(expected), findsOneWidget);
        final visibleText = tester
            .widgetList<Text>(find.byType(Text))
            .map((text) => text.data ?? text.textSpan?.toPlainText() ?? '')
            .join('\n');
        for (final term in ['登录', '账号', '账户', '检查连接', '检查网络']) {
          expect(visibleText, isNot(contains(term)));
        }
        final refreshAction = find.ancestor(
          of: find.byIcon(Icons.refresh_rounded),
          matching: find.byType(FilledButton),
        );
        expect(refreshAction, findsOneWidget);

        await tester.ensureVisible(refreshAction);
        await tester.tap(refreshAction);
        await tester.pumpAndSettle();

        expect(repository.calls, 2);
        expect(find.text(expected), findsNothing);
        expect(tester.takeException(), isNull);
      }
    },
  );

  test('a bound global chart without grant or lineage is withheld', () async {
    final hostile = Map<String, dynamic>.from(_chartResponse)
      ..remove('global_binding');
    final client = _FakeClient(
      contextResponse: _globalContext,
      screenResponse: hostile,
    );

    await expectLater(
      CoreCth05Repository(client: client).load(),
      throwsA(
        isA<Cth05ContextUnavailable>().having(
          (error) => error.reason,
          'reason',
          Cth05BlockReason.pageNotBound,
        ),
      ),
    );
  });

  test('a server-authorized global chart can be consumed', () async {
    final client = _FakeClient(
      contextResponse: _globalContext,
      screenResponse: _globalCalendarResponse,
    );

    final data = await CoreCth05Repository(client: client).load();

    expect(data.context.mode, 'GLOBAL_ALL');
    expect(data.calendarAvailable, isTrue);
    expect(data.definition?.subject, 'GLOBAL/ALL');
  });

  test(
    'an applied Guangzhou Taikoo Hui focus is not promoted to global',
    () async {
      final client = _FakeClient(
        contextResponse: _guangzhouFocusContext,
        screenResponse: _focusedCalendarResponse,
      );

      final data = await CoreCth05Repository(client: client).load();

      expect(data.context.mode, 'FOCUS');
      expect(data.context.subjectId, 'GUANGZHOU_TAIKOO_HUI');
      expect(data.calendarAvailable, isTrue);
      expect(data.definition?.subject, 'GUANGZHOU_TAIKOO_HUI');
    },
  );

  testWidgets('desktop calendar has heatfield, detail rail and list mode', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(
      _app(repository: _FakeRepository(Future.value(_calendarData()))),
    );
    await tester.pumpAndSettle();

    expect(find.byKey(const ValueKey('cth05/desktop-layout')), findsOneWidget);
    expect(find.byKey(const ValueKey('cth05/calendar-panel')), findsOneWidget);
    expect(find.byKey(const ValueKey('cth05/day-detail')), findsOneWidget);
    expect(find.text('09-21'), findsOneWidget);
    expect(find.text('指标口径'), findsNothing);

    await tester.tap(find.text('09-21'));
    await tester.pumpAndSettle();
    expect(find.text('在线负面记录 0'), findsOneWidget);
    expect(find.text('暂时无法提供可核实的来源信息。'), findsOneWidget);

    await tester.tap(find.text('查看全部'));
    await tester.pumpAndSettle();
    expect(find.byType(ListTile), findsNWidgets(2));
    _expectNoInternalCopy(tester);
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'mobile preserves a selectable day and accessible density labels',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(390, 844));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      await tester.pumpWidget(
        _app(repository: _FakeRepository(Future.value(_calendarData()))),
      );
      await tester.pumpAndSettle();

      expect(find.byKey(const ValueKey('cth05/mobile-layout')), findsOneWidget);
      expect(
        find.byWidgetPredicate(
          (widget) =>
              widget is Semantics &&
              (widget.properties.label ?? '').contains('09-21'),
        ),
        findsOneWidget,
      );
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('empty calendar does not become zero-filled', (tester) async {
    await tester.pumpWidget(
      _app(
        repository: _FakeRepository(
          Future.value(
            Cth05ScreenData(
              context: const Cth05Context(mode: 'GLOBAL_ALL'),
              generatedAt: '2026-09-22T10:00:00',
              state: Cth05DataState.empty,
              days: const [],
              definition: _definition,
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('暂无记录'), findsOneWidget);
    expect(find.text('0'), findsNothing);
  });
}

Widget _app({Cth05Repository? repository, LumenisCoreClient? client}) =>
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
        body: Cth05Screen(
          client: client ?? LumenisCoreClient(),
          repository: repository,
        ),
      ),
    );

class _FakeRepository implements Cth05Repository {
  const _FakeRepository(this.future);

  final Future<Cth05ScreenData> future;

  @override
  Future<Cth05ScreenData> load() => future;
}

class _RecoveringCth05Repository implements Cth05Repository {
  _RecoveringCth05Repository(this.statusCode, this.data);

  final int statusCode;
  final Cth05ScreenData data;
  int calls = 0;

  @override
  Future<Cth05ScreenData> load() async {
    calls++;
    if (calls == 1) {
      throw LumenisCoreException(
        'HTTP $statusCode private access failure',
        statusCode: statusCode,
      );
    }
    return data;
  }
}

class _FakeClient extends LumenisCoreClient {
  _FakeClient({required this.contextResponse, required this.screenResponse});

  final Map<String, dynamic> contextResponse;
  final Map<String, dynamic> screenResponse;

  @override
  Future<Map<String, dynamic>> settingsContext() async => contextResponse;

  @override
  Future<Map<String, dynamic>> screen(String screenId) async {
    expect(screenId, 'CTH-05');
    return screenResponse;
  }
}

Cth05ScreenData _calendarData() => const Cth05ScreenData(
  context: Cth05Context(mode: 'GLOBAL_ALL'),
  generatedAt: '2026-09-22T10:00:00',
  state: Cth05DataState.ready,
  days: [
    Cth05CalendarDay(label: '09-20', negative: 2, highRisk: 1),
    Cth05CalendarDay(label: '09-21', negative: 0, highRisk: 0),
  ],
  definition: _definition,
);

const Cth05TrendDefinition _definition = Cth05TrendDefinition(
  numerator: '负面记录数',
  denominator: '全部返回记录数',
  timeWindow: '2026-09-20 至 2026-09-21',
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
  'screen': 'CTH-05',
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
          'name': '负面',
          'data': [2, 0],
        },
        {
          'name': '高风险',
          'data': [1, 0],
        },
      ],
    },
  ],
};

final Map<String, dynamic> _focusedCalendarResponse = {
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
    'numerator': '负面记录数',
    'denominator': '全部返回记录数',
    'time_window': '2026-09-20 至 2026-09-21',
    'subject': 'GUANGZHOU_TAIKOO_HUI',
    'source': 'verified notes',
    'freshness': '2026-09-22T10:00:00',
    'projection': cthGuangzhouFocusProjection,
  },
};

final Map<String, dynamic> _globalCalendarResponse = {
  ..._chartResponse,
  'trend_metadata': {
    'numerator': '负面记录数',
    'denominator': '全部返回记录数',
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
