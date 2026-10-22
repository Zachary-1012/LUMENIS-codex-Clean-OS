import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/core/lumenis_theme.dart';
import 'package:lumenis_app/features/cth/cth07/cth07_repository.dart';
import 'package:lumenis_app/features/cth/cth07/cth07_screen.dart';
import 'package:lumenis_app/l10n/lumenis_localizations.dart';

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
    expect(data.definition?.freshness, 'UNKNOWN');
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

  test('partial temporal metrics preserve null values and scope', () async {
    final response = _trendResponse(
      global: true,
      state: 'partial',
      total: [6, null, 4],
      negative: [2, null, 1],
      high: [0, null, 1],
    );
    final client = _FakeClient(
      contextResponse: _globalContext,
      screenResponse: response,
    );

    final data = await CoreCth07Repository(client: client).load();

    expect(data.state, Cth07DataState.partial);
    expect(data.trendAvailable, isTrue);
    expect(data.series.first.values, [6, null, 4]);
  });

  test(
    'chart values that diverge from the bound metric snapshot are withheld',
    () async {
      final response = Map<String, dynamic>.from(_globalTrendResponse);
      final sections = List<dynamic>.from(response['sections'] as List);
      final chart = Map<String, dynamic>.from(sections.last as Map);
      chart['series'] = [
        {
          'name': '总量',
          'metric': 'total',
          'data': [6, 999, 4],
        },
        {
          'name': '负面',
          'metric': 'negative',
          'data': [2, 1, 1],
        },
        {
          'name': '高风险',
          'metric': 'high',
          'data': [0, 1, 0],
        },
      ];
      sections[sections.length - 1] = chart;
      response['sections'] = sections;
      final client = _FakeClient(
        contextResponse: _globalContext,
        screenResponse: response,
      );

      final data = await CoreCth07Repository(client: client).load();

      expect(data.state, Cth07DataState.notCollected);
      expect(data.trendAvailable, isFalse);
      expect(data.labels, isEmpty);
    },
  );

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

  testWidgets('partial trend shows missing days as gaps and dashes', (
    tester,
  ) async {
    final response = _trendResponse(
      global: true,
      state: 'partial',
      total: [6, null, 4],
      negative: [2, null, 1],
      high: [0, null, 1],
    );
    final data = await CoreCth07Repository(
      client: _FakeClient(
        contextResponse: _globalContext,
        screenResponse: response,
      ),
    ).load();
    await tester.pumpWidget(
      _app(repository: _FakeRepository(Future.value(data))),
    );
    await tester.pumpAndSettle();

    expect(find.text('—'), findsOneWidget);
    expect(find.text('状态: -2'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'authentication and access failures remain distinct and retryable',
    (tester) async {
      for (final statusCode in [401, 403]) {
        await tester.pumpWidget(const SizedBox.shrink());
        await tester.pump();
        final repository = _RecoveringCth07Repository(statusCode, _trendData());
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

class _RecoveringCth07Repository implements Cth07Repository {
  _RecoveringCth07Repository(this.statusCode, this.data);

  final int statusCode;
  final Cth07ScreenData data;
  int calls = 0;

  @override
  Future<Cth07ScreenData> load() async {
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
    'contract': 'lumenis.scope-read-binding.v1',
    'policy': 'actor-exact-scope-v1',
    'actor_scope': 'authenticated',
    'applied': true,
    'global_all_granted': true,
    'canonical_scope': 'GLOBAL_ALL',
    'scope_verified': true,
    'read_allowed': true,
    'domain_id': 'CTH',
    'product_id': 'CTH',
    'subject_id': null,
  },
  'generated_at': '2026-09-22T10:00:00',
  'sections': [
    {
      'type': 'chart',
      'state': 'ready',
      'labels': ['09-20', '09-21'],
      'series': [
        {
          'name': '总量',
          'metric': 'total',
          'data': [6, 5],
        },
      ],
    },
  ],
};

Map<String, dynamic> _scopeBinding({
  required bool global,
  required bool authenticated,
}) => {
  'contract': 'lumenis.scope-read-binding.v1',
  'policy': authenticated ? 'actor-exact-scope-v1' : 'local-workspace-read-v1',
  'actor_scope': authenticated ? 'authenticated' : 'anonymous_read',
  'applied': true,
  'read_allowed': true,
  'scope_verified': true,
  'product_id': 'CTH',
  'domain_id': 'CTH',
  'canonical_scope': global ? 'GLOBAL_ALL' : 'FOCUS',
  'subject_id': global ? null : 'GUANGZHOU_TAIKOO_HUI',
  'global_all_granted': global && authenticated,
};

Map<String, dynamic> _trendResponse({
  required bool global,
  required String state,
  required List<num?> total,
  required List<num?> negative,
  required List<num?> high,
}) {
  const labels = ['2026-09-20', '2026-09-21', '2026-09-22'];
  const snapshotHash =
      '0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef';
  final binding = _scopeBinding(global: global, authenticated: true);
  final fields = <String, List<num?>>{
    'total': total,
    'negative': negative,
    'high': high,
  };
  final days = [
    for (var index = 0; index < labels.length; index++)
      {
        'date': labels[index],
        for (final entry in fields.entries)
          entry.key: {
            'value': entry.value[index],
            'state': entry.value[index] == null
                ? 'partial'
                : state == 'partial'
                ? 'partial'
                : 'ready',
          },
      },
  ];
  final subject = global ? 'GLOBAL/ALL' : 'GUANGZHOU_TAIKOO_HUI';
  final source = global ? '总范围已获准资料' : '已获准资料';
  final metadata = {
    'numerator': '所选原生发布时间内的已收录资料数量',
    'denominator': '计数，不使用市场总体分母',
    'time_window': '2026-09-20 / 2026-09-22',
    'subject': subject,
    'source': source,
    'freshness': 'UNKNOWN',
    'recipe': 'CTH_NATIVE_PUBLICATION_COUNTS_V1',
    'snapshot_sha256': snapshotHash,
  };
  final metrics = {
    'state': state,
    'binding': binding,
    'recipe': 'CTH_NATIVE_PUBLICATION_COUNTS_V1',
    'snapshot_sha256': snapshotHash,
    'coverage': 'NOT_VERIFIED',
    'source_freshness': 'UNKNOWN',
    'days': days,
    'totals': {
      for (final entry in fields.entries)
        entry.key: {'value': entry.value.first},
    },
    'contributions': const [],
  };
  return {
    ..._chartResponse,
    if (global) 'global_binding': binding else 'focus_binding': binding,
    'temporal_metrics': metrics,
    'trend_metadata': metadata,
    'sections': [
      {
        'type': 'chart',
        'state': state,
        'labels': labels,
        'series': [
          for (final entry in fields.entries)
            {
              'name': entry.key == 'total'
                  ? '总量'
                  : entry.key == 'negative'
                  ? '负面'
                  : '高风险',
              'metric': entry.key,
              'data': entry.value,
            },
        ],
      },
    ],
  };
}

final Map<String, dynamic> _focusedTrendResponse = _trendResponse(
  global: false,
  state: 'ready',
  total: [6, 5, 4],
  negative: [2, 1, 1],
  high: [0, 1, 0],
);

final Map<String, dynamic> _globalTrendResponse = _trendResponse(
  global: true,
  state: 'ready',
  total: [6, 5, 4],
  negative: [2, 1, 1],
  high: [0, 1, 0],
);

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
