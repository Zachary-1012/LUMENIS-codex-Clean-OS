import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/core/lumenis_theme.dart';
import 'package:lumenis_app/features/cth/cth03/cth03_repository.dart';
import 'package:lumenis_app/features/cth/cth03/cth03_screen.dart';
import 'package:lumenis_app/l10n/lumenis_localizations.dart';

import '../cth_test_support.dart';

void main() {
  testWidgets('loading hides stream values and announces the read state', (
    tester,
  ) async {
    final pending = Completer<Cth03ScreenData>();
    await tester.pumpWidget(_app(_PendingRepository(pending.future)));

    expect(find.text('线上服务反馈'), findsNothing);
    expect(find.byType(LinearProgressIndicator), findsOneWidget);
    expect(
      find.byWidgetPredicate(
        (widget) =>
            widget is Semantics &&
            widget.properties.liveRegion == true &&
            (widget.properties.label ?? '').isNotEmpty,
      ),
      findsOneWidget,
    );

    pending.complete(_data());
    await tester.pumpAndSettle();
    expect(find.text('线上服务反馈'), findsOneWidget);
  });

  testWidgets('desktop has separate pulse, channel and stream anatomy', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(_app(_PendingRepository(Future.value(_data()))));
    await tester.pumpAndSettle();

    expect(find.byKey(const ValueKey('cth03/desktop-layout')), findsOneWidget);
    expect(find.byKey(const ValueKey('cth03/pulse-band')), findsOneWidget);
    expect(find.byKey(const ValueKey('cth03/channel-lanes')), findsOneWidget);
    expect(find.byKey(const ValueKey('cth03/record-stream')), findsOneWidget);
    expect(find.text('线上服务反馈'), findsOneWidget);
    expect(find.text('EV-PRIVATE-7'), findsNothing);
    expect(find.text('database.get_notes'), findsNothing);
    _expectNoInternalCopy(tester);
    expect(tester.takeException(), isNull);
  });

  testWidgets('mobile filters the local stream without creating an effect', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(_app(_PendingRepository(Future.value(_data()))));
    await tester.pumpAndSettle();

    expect(find.byKey(const ValueKey('cth03/mobile-layout')), findsOneWidget);
    expect(find.text('线上服务反馈'), findsOneWidget);
    await tester.tap(find.text('社交平台').first);
    await tester.pumpAndSettle();
    expect(find.text('线上服务反馈'), findsNothing);
    expect(find.text('暂无数据'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('focused subject without server binding stays unavailable', (
    tester,
  ) async {
    final failure = Completer<Cth03ScreenData>();
    await tester.pumpWidget(_app(_PendingRepository(failure.future)));
    await tester.pump();
    failure.completeError(
      const Cth03ContextUnavailable(Cth03BlockReason.focusNotBound),
    );
    await tester.pumpAndSettle();
    expect(find.text('经营主体信息暂不可用'), findsOneWidget);
    expect(find.text('线上服务反馈'), findsNothing);
    expect(find.textContaining('页面尚未接入所选范围的数据'), findsOneWidget);
    _expectNoInternalCopy(tester);
  });

  test(
    'the Core repository does not decode an unbound focused aggregate',
    () async {
      final client = _FakeClient(
        contextResponse: const {
          'ok': true,
          'contract': 'lumenis.context.v1',
          'context': {
            'mode': 'FOCUS',
            'domain_id': 'CTH',
            'subject_id': 'SUBJ-7',
          },
        },
        screenResponse: _screenResponse,
      );

      await expectLater(
        CoreCth03Repository(client: client).load(),
        throwsA(
          isA<Cth03ContextUnavailable>().having(
            (error) => error.reason,
            'reason',
            Cth03BlockReason.focusNotBound,
          ),
        ),
      );
    },
  );

  test(
    'a bound global aggregate without grant or lineage is withheld',
    () async {
      final client = _FakeClient(
        contextResponse: _globalContext,
        screenResponse: _screenResponse,
      );

      await expectLater(
        CoreCth03Repository(client: client).load(),
        throwsA(
          isA<Cth03ContextUnavailable>().having(
            (error) => error.reason,
            'reason',
            Cth03BlockReason.pageNotBound,
          ),
        ),
      );
    },
  );

  test('a server-authorized global aggregate can be consumed', () async {
    final client = _FakeClient(
      contextResponse: _globalContext,
      screenResponse: _globalScreenResponse,
    );

    final data = await CoreCth03Repository(client: client).load();

    expect(data.context.mode, 'GLOBAL_ALL');
    expect(data.recentCount.value, 2);
    expect(data.records, isNotEmpty);
  });

  test('an applied Guangzhou Taikoo Hui focus stays focused', () async {
    final client = _FakeClient(
      contextResponse: _guangzhouFocusContext,
      screenResponse: _focusedScreenResponse,
    );

    final data = await CoreCth03Repository(client: client).load();

    expect(data.context.mode, 'FOCUS');
    expect(data.context.subjectId, 'GUANGZHOU_TAIKOO_HUI');
    expect(data.context.displayName?['zh-CN'], '广州太古汇');
    expect(data.records, isNotEmpty);
  });
}

Widget _app(Cth03Repository repository) => MaterialApp(
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
    body: Cth03Screen(client: LumenisCoreClient(), repository: repository),
  ),
);

class _PendingRepository implements Cth03Repository {
  const _PendingRepository(this.future);

  final Future<Cth03ScreenData> future;

  @override
  Future<Cth03ScreenData> load() => future;
}

class _FakeClient extends LumenisCoreClient {
  _FakeClient({required this.contextResponse, required this.screenResponse});

  final Map<String, dynamic> contextResponse;
  final Map<String, dynamic> screenResponse;

  @override
  Future<Map<String, dynamic>> settingsContext() async => contextResponse;

  @override
  Future<Map<String, dynamic>> screen(String screenId) async {
    expect(screenId, 'CTH-03');
    return screenResponse;
  }
}

Cth03ScreenData _data() => Cth03ScreenData(
  context: const Cth03Context(mode: 'GLOBAL_ALL'),
  generatedAt: '2026-09-22T10:00:00',
  recentCount: const Cth03Metric(
    id: 'cth03.recent',
    state: Cth03DataState.ready,
    value: 2,
  ),
  negativeCount: const Cth03Metric(
    id: 'cth03.negative',
    state: Cth03DataState.ready,
    value: 1,
  ),
  channels: const [
    Cth03Channel(name: '公开网页', status: '最近成功', detail: '只读'),
    Cth03Channel(name: '社交平台', status: '暂未返回', detail: '只读'),
  ],
  records: const [
    Cth03Record(
      date: '2026-09-22',
      title: '线上服务反馈',
      channel: '公开网页',
      sentiment: '负面',
      risk: '中风险',
    ),
  ],
  recordState: Cth03DataState.ready,
);

const Map<String, dynamic> _screenResponse = {
  'ok': true,
  'screen': 'CTH-03',
  'bound': true,
  'generated_at': '2026-09-22T10:00:00',
  'sections': [
    {
      'type': 'kpis',
      'items': [
        {'id': 'cth03.recent', 'value': 2, 'state': 'ready'},
        {'id': 'cth03.negative', 'value': 1, 'state': 'ready'},
      ],
    },
    {
      'type': 'platforms',
      'items': [
        {
          'platform': '公开网页',
          'status': '最近成功',
          'schedule': '只读',
          'platform_id': 'PRIVATE-PLATFORM',
        },
      ],
    },
    {
      'type': 'table',
      'state': 'ready',
      'rows': [
        {
          'date': '2026-09-22',
          'title': '线上服务反馈',
          'platform': '公开网页',
          'sentiment': '负面',
          'risk': '中风险',
          'note_id': 'EV-PRIVATE-7',
        },
      ],
    },
  ],
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

const Map<String, dynamic> _globalContext = {
  'ok': true,
  'contract': 'lumenis.context.v1',
  'context': {'mode': 'GLOBAL_ALL'},
};

final Map<String, dynamic> _globalScreenResponse = _withTableRow(
  {
    ..._screenResponse,
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
  },
  {
    'date': '2026-09-22',
    'title': '线上服务反馈',
    'platform': '公开网页',
    'sentiment': '负面',
    'risk': '中风险',
    'scope_mode': 'GLOBAL_ALL',
    'canonical_scope': 'GLOBAL_ALL',
    'global_scope': true,
    'read_allowed': true,
    'evidence_lineage': 'verified',
    'trace_id': 'TRACE-CTH03-GLOBAL',
  },
);

final Map<String, dynamic> _focusedScreenResponse = _withTableRow(
  {
    ..._screenResponse,
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
  },
  {
    'date': '2026-09-22',
    'title': '线上服务反馈',
    'platform': '公开网页',
    'sentiment': '负面',
    'risk': '中风险',
    'scope_mode': 'FOCUS',
    'canonical_scope': 'FOCUS',
    'subject_id': 'GUANGZHOU_TAIKOO_HUI',
    'read_allowed': true,
    'evidence_lineage': 'verified',
    'trace_id': 'TRACE-CTH03-GZ',
  },
);

Map<String, dynamic> _withTableRow(
  Map<String, dynamic> response,
  Map<String, dynamic> row,
) {
  final projection = row['scope_mode'] == 'FOCUS'
      ? cthGuangzhouFocusProjection
      : cthGlobalProjection;
  final sections = (response['sections'] as List)
      .map((section) {
        final copy = Map<String, dynamic>.from(section as Map);
        if (copy['type'] == 'table') {
          copy['rows'] = [
            <String, dynamic>{...row, 'projection': projection},
          ];
        } else if (copy['type'] == 'kpis' || copy['type'] == 'platforms') {
          copy['items'] = (copy['items'] as List)
              .map(
                (item) => <String, dynamic>{
                  ...(item as Map),
                  'projection': projection,
                },
              )
              .toList(growable: false);
        }
        return copy;
      })
      .toList(growable: false);
  return {...response, 'sections': sections};
}

void _expectNoInternalCopy(WidgetTester tester) {
  final rendered = tester
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
    'provider',
    'owner',
    'subject_id',
    'note_id',
    'ev-',
  ]) {
    expect(rendered, isNot(contains(term)), reason: 'UI leaked $term');
  }
}
