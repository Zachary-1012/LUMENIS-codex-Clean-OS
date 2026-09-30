import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/core/lumenis_theme.dart';
import 'package:lumenis_app/features/cth/cth04/cth04_repository.dart';
import 'package:lumenis_app/features/cth/cth04/cth04_screen.dart';
import 'package:lumenis_app/l10n/lumenis_localizations.dart';

import '../cth_test_support.dart';

void main() {
  testWidgets('loading, empty and unavailable remain distinct', (tester) async {
    final pending = Completer<Cth04ScreenData>();
    await tester.pumpWidget(_app(_FakeRepository(pending.future)));
    expect(find.byType(CircularProgressIndicator), findsOneWidget);
    expect(find.text('门店服务波动'), findsNothing);

    pending.complete(_data(events: const []));
    await tester.pumpAndSettle();
    expect(find.text('暂无记录'), findsOneWidget);
    expect(find.text('部分指标尚不可用。未返回的数据不会按零展示。'), findsOneWidget);

    final failure = Completer<Cth04ScreenData>();
    await tester.pumpWidget(_app(_FakeRepository(failure.future)));
    await tester.pump();
    failure.completeError(
      const LumenisCoreException('private server detail', statusCode: 503),
    );
    await tester.pumpAndSettle();
    expect(find.text('运营信息暂不可用'), findsOneWidget);
    expect(find.textContaining('private server detail'), findsNothing);
  });

  testWidgets(
    'authentication and access copy stay distinct and refresh recovers in all locales',
    (tester) async {
      const recoveryLocales = [
        (
          locale: Locale('zh', 'CN'),
          authentication: '当前内容暂时无法打开。可重试读取，或返回后稍后再试。',
          permission: '当前内容不可访问。',
          forbiddenTerms: ['登录', '账号', '账户', '检查连接', '检查网络'],
        ),
        (
          locale: Locale('en'),
          authentication:
              'This content cannot be opened right now. You can retry reading it or return and try again later.',
          permission: 'This content is not accessible.',
          forbiddenTerms: [
            'sign in',
            'login',
            'account',
            'check the connection',
            'check connection',
          ],
        ),
        (
          locale: Locale('ko'),
          authentication:
              '현재 콘텐츠를 지금 열 수 없습니다. 다시 읽기를 시도하거나 돌아간 뒤 나중에 다시 시도할 수 있습니다.',
          permission: '현재 콘텐츠에 접근할 수 없습니다.',
          forbiddenTerms: ['로그인', '계정', '연결을 확인'],
        ),
      ];

      for (final copy in recoveryLocales) {
        for (final statusCode in [401, 403]) {
          await tester.pumpWidget(const SizedBox.shrink());
          await tester.pump();
          final repository = _RecoveringCth04Repository(statusCode, _data());
          await tester.pumpWidget(_app(repository, locale: copy.locale));
          await tester.pumpAndSettle();

          final expected = statusCode == 401
              ? copy.authentication
              : copy.permission;
          expect(find.text(expected), findsOneWidget);
          _expectNoAuthOrNetworkAdvice(tester, copy.forbiddenTerms);
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
      }
    },
  );

  testWidgets(
    'desktop keeps the relationship map honest and supports local trace return',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(1440, 1000));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      await tester.pumpWidget(_app(_FakeRepository(Future.value(_data()))));
      await tester.pumpAndSettle();

      expect(
        find.byKey(const ValueKey('cth04/desktop-layout')),
        findsOneWidget,
      );
      expect(find.byKey(const ValueKey('cth04/constellation')), findsOneWidget);
      expect(
        find.byKey(const ValueKey('cth04/event-timeline')),
        findsOneWidget,
      );
      expect(find.text('部分指标尚不可用。未返回的数据不会按零展示。'), findsOneWidget);
      expect(find.text('EV-PRIVATE-9'), findsNothing);

      await tester.tap(find.text('门店服务波动').first);
      await tester.pumpAndSettle();
      expect(
        find.byKey(const ValueKey('cth04/event-inspection')),
        findsOneWidget,
      );
      expect(find.text('返回'), findsOneWidget);
      await tester.tap(find.text('返回'));
      await tester.pumpAndSettle();
      expect(
        find.byKey(const ValueKey('cth04/event-inspection')),
        findsNothing,
      );
      _expectNoInternalCopy(tester);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets(
    'mobile recomposes as timeline first and has accessible event labels',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(390, 844));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      await tester.pumpWidget(_app(_FakeRepository(Future.value(_data()))));
      await tester.pumpAndSettle();

      expect(find.byKey(const ValueKey('cth04/mobile-layout')), findsOneWidget);
      expect(
        find.byWidgetPredicate(
          (widget) =>
              widget is Semantics &&
              (widget.properties.label ?? '').contains('门店服务波动'),
        ),
        findsOneWidget,
      );
      expect(tester.takeException(), isNull);
    },
  );

  test(
    'a focused context is not allowed to reuse a global event list',
    () async {
      final client = _FakeClient(
        contextResponse: const {
          'ok': true,
          'contract': 'lumenis.context.v1',
          'context': {
            'mode': 'FOCUS',
            'domain_id': 'CTH',
            'subject_id': 'SUBJ-04',
          },
        },
        screenResponse: _screenResponse,
      );
      await expectLater(
        CoreCth04Repository(client: client).load(),
        throwsA(
          isA<Cth04ContextUnavailable>().having(
            (error) => error.reason,
            'reason',
            Cth04BlockReason.focusNotBound,
          ),
        ),
      );
    },
  );

  test(
    'a bound global event list without grant or lineage is withheld',
    () async {
      final hostile = Map<String, dynamic>.from(_screenResponse)
        ..remove('global_binding');
      final client = _FakeClient(
        contextResponse: _globalContext,
        screenResponse: hostile,
      );

      await expectLater(
        CoreCth04Repository(client: client).load(),
        throwsA(
          isA<Cth04ContextUnavailable>().having(
            (error) => error.reason,
            'reason',
            Cth04BlockReason.pageNotBound,
          ),
        ),
      );
    },
  );

  test('a server-authorized global event list can be consumed', () async {
    final client = _FakeClient(
      contextResponse: _globalContext,
      screenResponse: _screenResponse,
    );

    final data = await CoreCth04Repository(client: client).load();

    expect(data.context.mode, 'GLOBAL_ALL');
    expect(data.events, isNotEmpty);
  });
}

Widget _app(
  Cth04Repository repository, {
  Locale locale = const Locale('zh', 'CN'),
}) => MaterialApp(
  locale: locale,
  theme: LumenisTheme.dark,
  supportedLocales: LumenisLocalizations.supportedLocales,
  localizationsDelegates: const [
    LumenisLocalizations.delegate,
    GlobalMaterialLocalizations.delegate,
    GlobalWidgetsLocalizations.delegate,
    GlobalCupertinoLocalizations.delegate,
  ],
  home: Scaffold(
    body: Cth04Screen(client: LumenisCoreClient(), repository: repository),
  ),
);

void _expectNoAuthOrNetworkAdvice(
  WidgetTester tester,
  List<String> forbiddenTerms,
) {
  final visibleText = tester
      .widgetList<Text>(find.byType(Text))
      .map((text) => text.data ?? text.textSpan?.toPlainText() ?? '')
      .join('\n')
      .toLowerCase();
  for (final term in forbiddenTerms) {
    expect(visibleText, isNot(contains(term.toLowerCase())));
  }
}

class _FakeRepository implements Cth04Repository {
  const _FakeRepository(this.future);

  final Future<Cth04ScreenData> future;

  @override
  Future<Cth04ScreenData> load() => future;
}

class _RecoveringCth04Repository implements Cth04Repository {
  _RecoveringCth04Repository(this.statusCode, this.data);

  final int statusCode;
  final Cth04ScreenData data;
  int calls = 0;

  @override
  Future<Cth04ScreenData> load() async {
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
    expect(screenId, 'CTH-04');
    return screenResponse;
  }
}

Cth04ScreenData _data({List<Cth04Event>? events}) {
  final resolved =
      events ??
      const [
        Cth04Event(
          title: '门店服务波动',
          date: '2026-09-22',
          time: '09:30',
          description: '近期返回的服务反馈出现变化。',
          level: '高风险',
          tags: ['提及 3'],
        ),
      ];
  return Cth04ScreenData(
    context: const Cth04Context(mode: 'GLOBAL_ALL'),
    generatedAt: '2026-09-22T10:00:00',
    events: resolved,
    eventsState: resolved.isEmpty ? Cth04DataState.empty : Cth04DataState.ready,
    graph: const Cth04Graph(
      state: Cth04DataState.notCollected,
      nodes: [],
      edgeCount: 0,
    ),
  );
}

const Map<String, dynamic> _screenResponse = {
  'ok': true,
  'screen': 'CTH-04',
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
  'sections': [
    {
      'type': 'events',
      'state': 'ready',
      'items': [
        {
          'title': '门店服务波动',
          'date': '2026-09-22',
          'time': '09:30',
          'desc': '近期返回的服务反馈出现变化。',
          'level': '高风险',
          'tags': ['提及 3'],
          'evidence': 'EV-PRIVATE-9',
          'scope_mode': 'GLOBAL_ALL',
          'canonical_scope': 'GLOBAL_ALL',
          'global_scope': true,
          'read_allowed': true,
          'evidence_lineage': 'verified',
          'trace_id': 'TRACE-CTH04-GLOBAL',
          'projection': cthGlobalProjection,
        },
      ],
    },
    {
      'type': 'kpis',
      'items': [
        {
          'id': 'cth04.graph',
          'value': null,
          'state': 'notcollected',
          'projection': cthGlobalProjection,
        },
      ],
    },
  ],
};

const Map<String, dynamic> _globalContext = {
  'ok': true,
  'contract': 'lumenis.context.v1',
  'context': {'mode': 'GLOBAL_ALL'},
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
    'ev-',
    'event_id',
  ]) {
    expect(text, isNot(contains(term)), reason: 'UI leaked $term');
  }
}
