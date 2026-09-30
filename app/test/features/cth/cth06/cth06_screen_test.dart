import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/core/lumenis_theme.dart';
import 'package:lumenis_app/features/cth/cth06/cth06_repository.dart';
import 'package:lumenis_app/features/cth/cth06/cth06_screen.dart';
import 'package:lumenis_app/l10n/lumenis_localizations.dart';

import '../cth_test_support.dart';

void main() {
  testWidgets('loading keeps feedback hidden and announces progress', (
    tester,
  ) async {
    final pending = Completer<Cth06ScreenData>();
    await tester.pumpWidget(_app(_FakeRepository(pending.future)));
    expect(find.text('门店服务反馈'), findsNothing);
    expect(find.byType(CircularProgressIndicator), findsOneWidget);
    pending.complete(_data());
    await tester.pumpAndSettle();
    expect(find.text('门店服务反馈'), findsOneWidget);
  });

  testWidgets('desktop separates triage queue from source-first reading', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(_app(_FakeRepository(Future.value(_data()))));
    await tester.pumpAndSettle();

    expect(find.byKey(const ValueKey('cth06/desktop-layout')), findsOneWidget);
    expect(find.byKey(const ValueKey('cth06/triage-queue')), findsOneWidget);
    expect(find.byKey(const ValueKey('cth06/reading-pane')), findsOneWidget);
    expect(find.text('NOTE-PRIVATE-6'), findsNothing);
    expect(find.text('database.get_negative_comments'), findsNothing);

    await tester.tap(find.text('公众意见').first);
    await tester.pumpAndSettle();
    expect(find.text('门店服务反馈'), findsOneWidget);
    await tester.tap(find.text('门店服务反馈'));
    await tester.pumpAndSettle();
    expect(find.text('状态'), findsOneWidget);
    expect(find.text('负面'), findsOneWidget);
    expect(find.text('暂时无法提供可核实的来源信息。'), findsOneWidget);
    _expectNoInternalCopy(tester);
    expect(tester.takeException(), isNull);
  });

  testWidgets('mobile stacks queue before reading and keeps empty distinct', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(
      _app(
        _FakeRepository(
          Future.value(
            Cth06ScreenData(
              context: const Cth06Context(mode: 'GLOBAL_ALL'),
              generatedAt: '2026-09-22T10:00:00',
              items: const [],
              itemsState: Cth06DataState.empty,
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('cth06/mobile-layout')), findsOneWidget);
    expect(find.text('暂无记录'), findsOneWidget);
    expect(find.text('门店服务反馈'), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets('server failures do not expose raw details', (tester) async {
    final failure = Completer<Cth06ScreenData>();
    await tester.pumpWidget(_app(_FakeRepository(failure.future)));
    await tester.pump();
    failure.completeError(
      const LumenisCoreException('private feedback SQL', statusCode: 500),
    );
    await tester.pumpAndSettle();
    expect(find.text('运营信息暂不可用'), findsOneWidget);
    expect(find.textContaining('private feedback SQL'), findsNothing);
    _expectNoInternalCopy(tester);
  });

  test(
    'a bound global feedback list without grant or lineage is withheld',
    () async {
      final hostile = Map<String, dynamic>.from(_screenResponse)
        ..remove('global_binding');
      final client = _FakeClient(
        contextResponse: _globalContext,
        screenResponse: hostile,
      );

      await expectLater(
        CoreCth06Repository(client: client).load(),
        throwsA(
          isA<Cth06ContextUnavailable>().having(
            (error) => error.reason,
            'reason',
            Cth06BlockReason.pageNotBound,
          ),
        ),
      );
    },
  );

  test('a server-authorized global feedback list can be consumed', () async {
    final client = _FakeClient(
      contextResponse: _globalContext,
      screenResponse: _screenResponse,
    );

    final data = await CoreCth06Repository(client: client).load();

    expect(data.context.mode, 'GLOBAL_ALL');
    expect(data.items, isNotEmpty);
  });

  testWidgets(
    'authentication and access failures remain distinct and retryable',
    (tester) async {
      for (final statusCode in [401, 403]) {
        await tester.pumpWidget(const SizedBox.shrink());
        await tester.pump();
        final repository = _RecoveringCth06Repository(statusCode, _data());
        await tester.pumpWidget(_app(repository));
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

Widget _app(Cth06Repository repository, {LumenisCoreClient? client}) =>
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
        body: Cth06Screen(
          client: client ?? LumenisCoreClient(),
          repository: repository,
        ),
      ),
    );

class _FakeRepository implements Cth06Repository {
  const _FakeRepository(this.future);

  final Future<Cth06ScreenData> future;

  @override
  Future<Cth06ScreenData> load() => future;
}

class _RecoveringCth06Repository implements Cth06Repository {
  _RecoveringCth06Repository(this.statusCode, this.data);

  final int statusCode;
  final Cth06ScreenData data;
  int calls = 0;

  @override
  Future<Cth06ScreenData> load() async {
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
    expect(screenId, 'CTH-06');
    return screenResponse;
  }
}

Cth06ScreenData _data() => const Cth06ScreenData(
  context: Cth06Context(mode: 'GLOBAL_ALL'),
  generatedAt: '2026-09-22T10:00:00',
  items: [
    Cth06Feedback(
      date: '2026-09-22',
      channel: '公开网页',
      summary: '门店服务反馈',
      sentiment: '负面',
      category: Cth06Category.publicOpinion,
      risk: '中风险',
    ),
  ],
  itemsState: Cth06DataState.ready,
);

const Map<String, dynamic> _globalContext = {
  'ok': true,
  'contract': 'lumenis.context.v1',
  'context': {'mode': 'GLOBAL_ALL'},
};

const Map<String, dynamic> _screenResponse = {
  'ok': true,
  'screen': 'CTH-06',
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
      'type': 'table',
      'state': 'ready',
      'rows': [
        {
          'time': '2026-09-22',
          'channel': '公开网页',
          'summary': '门店服务反馈',
          'sentiment': '负面',
          'category': 'public_opinion',
          'risk': '中风险',
          'scope_mode': 'GLOBAL_ALL',
          'canonical_scope': 'GLOBAL_ALL',
          'global_scope': true,
          'read_allowed': true,
          'evidence_lineage': 'verified',
          'trace_id': 'TRACE-CTH06-GLOBAL',
          'projection': cthGlobalProjection,
        },
      ],
    },
  ],
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
    'sql',
    'note-',
  ]) {
    expect(text, isNot(contains(term)), reason: 'UI leaked $term');
  }
}
