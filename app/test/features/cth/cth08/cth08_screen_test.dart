import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/core/lumenis_theme.dart';
import 'package:lumenis_app/features/cth/cth08/cth08_repository.dart';
import 'package:lumenis_app/features/cth/cth08/cth08_screen.dart';
import 'package:lumenis_app/l10n/lumenis_localizations.dart';

void main() {
  testWidgets('loading keeps case and knowledge rows hidden', (tester) async {
    final pending = Completer<Cth08WorkspaceData>();
    await tester.pumpWidget(_app(_FakeRepository(() => pending.future)));

    expect(find.text('停车摩擦处置'), findsNothing);
    expect(find.byType(CircularProgressIndicator), findsOneWidget);
    expect(find.bySemanticsLabel('正在读取案例工作台'), findsOneWidget);

    pending.complete(_workspace());
    await tester.pumpAndSettle();
    expect(find.text('停车摩擦处置'), findsOneWidget);
  });

  testWidgets('blocked binding shows recovery and no case data', (
    tester,
  ) async {
    await tester.pumpWidget(
      _app(
        _FakeRepository(
          () => Future.error(
            const Cth08BlockedException(
              Cth08BlockedReason.pageBindingUnavailable,
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('案例工作台暂不可用'), findsOneWidget);
    expect(find.text('当前范围和来源依据尚未完成核验，案例资料未显示。'), findsOneWidget);
    expect(find.text('停车摩擦处置'), findsNothing);
    expect(find.text('新建案例'), findsNothing);
    _expectNoInternalCopy(tester);
  });

  testWidgets('empty and not-collected states remain distinct', (tester) async {
    await tester.pumpWidget(
      _app(
        _FakeRepository(
          () async => const Cth08WorkspaceData(
            context: Cth08Context(mode: Cth08ContextMode.globalAll),
            state: Cth08ContentState.empty,
            cases: [],
            knowledge: [],
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('cth08/content-state')), findsOneWidget);
    expect(find.text('当前范围内暂无可查看案例。'), findsNWidgets(2));

    await tester.pumpWidget(
      _app(
        _FakeRepository(
          () async => const Cth08WorkspaceData(
            context: Cth08Context(mode: Cth08ContextMode.globalAll),
            state: Cth08ContentState.notCollected,
            cases: [],
            knowledge: [],
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('案例资料尚未接入，暂无可核验的生命周期记录。'), findsOneWidget);
    _expectNoInternalCopy(tester);
  });

  testWidgets('desktop and mobile keep distinct case compositions', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(_app(_FakeRepository(() async => _workspace())));
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('cth08/desktop-layout')), findsOneWidget);
    expect(find.byKey(const ValueKey('cth08/case-inspector')), findsNothing);
    expect(find.text('来源依据'), findsOneWidget);
    await tester.tap(find.text('停车摩擦处置'));
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('cth08/case-inspector')), findsOneWidget);
    expect(find.text('现场执行'), findsOneWidget);
    expect(find.textContaining('CASE-221'), findsOneWidget);
    expect(find.textContaining('EV-7710'), findsNWidgets(2));
    await tester.tap(find.text('返回案例列表'));
    await tester.pumpAndSettle();

    await tester.binding.setSurfaceSize(const Size(390, 844));
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('cth08/mobile-layout')), findsOneWidget);
    expect(find.text('案例收件箱'), findsNothing);
    expect(find.text('停车摩擦处置'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('select and return preserve the case trace locally', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(_app(_FakeRepository(() async => _workspace())));
    await tester.pumpAndSettle();

    await tester.tap(find.text('停车摩擦处置'));
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('cth08/case-inspector')), findsOneWidget);
    expect(find.text('现场执行'), findsOneWidget);
    expect(find.text('EV-PRIVATE-TOKEN'), findsNothing);
    _expectNoInternalCopy(tester);

    await tester.tap(find.text('返回案例列表'));
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('cth08/case-inspector')), findsNothing);
    expect(find.text('停车摩擦处置'), findsOneWidget);
  });

  testWidgets('new case remains disabled without a write contract', (
    tester,
  ) async {
    await tester.pumpWidget(_app(_FakeRepository(() async => _workspace())));
    await tester.pumpAndSettle();

    final button = tester.widget<FilledButton>(
      find.widgetWithText(FilledButton, '新建案例'),
    );
    expect(button.onPressed, isNull);
    expect(tester.takeException(), isNull);
  });

  testWidgets('copy is available in English and Korean', (tester) async {
    for (final locale in const [Locale('en'), Locale('ko')]) {
      await tester.pumpWidget(
        _app(_FakeRepository(() async => _workspace()), locale: locale),
      );
      await tester.pumpAndSettle();
      expect(find.text('停車摩擦處置'), findsNothing);
      expect(
        find.textContaining(locale.languageCode == 'en' ? 'Case' : '케이스'),
        findsWidgets,
      );
      _expectNoInternalCopy(tester);
    }
  });
}

Widget _app(
  Cth08Repository repository, {
  Locale locale = const Locale('zh', 'CN'),
}) => MaterialApp(
  locale: locale,
  supportedLocales: const [Locale('zh', 'CN'), Locale('en'), Locale('ko')],
  localizationsDelegates: const [
    GlobalMaterialLocalizations.delegate,
    GlobalWidgetsLocalizations.delegate,
    GlobalCupertinoLocalizations.delegate,
    LumenisLocalizations.delegate,
  ],
  theme: LumenisTheme.dark,
  home: Scaffold(
    body: Cth08Screen(client: LumenisCoreClient(), repository: repository),
  ),
);

class _FakeRepository implements Cth08Repository {
  const _FakeRepository(this._loader);

  final Future<Cth08WorkspaceData> Function() _loader;

  @override
  Future<Cth08WorkspaceData> load() => _loader();
}

Cth08WorkspaceData _workspace() => Cth08WorkspaceData(
  context: const Cth08Context(mode: Cth08ContextMode.globalAll),
  state: Cth08ContentState.ready,
  cases: const [
    Cth08Case(
      id: 'CASE-1',
      title: '停车摩擦处置',
      state: 'open',
      summary: '晚高峰现场观察中的处置工作。',
      risk: 'high',
      timeline: [
        Cth08TimelineStep(
          label: '现场执行',
          detail: '观察中',
          occurredAt: '10:40',
          state: Cth08TimelineState.current,
        ),
      ],
      evidence: [
        Cth08EvidenceReference(
          id: 'EV-CASE-221',
          quote: '已核验案例记录',
          capturedAt: '10:22',
          integrityStatus: 'verified',
          integrityVersion: 'evidence-v1',
          scopeMode: 'GLOBAL_ALL',
          domainId: 'CTH',
          productId: 'CTH',
          subjectId: null,
          readAllowed: true,
        ),
        Cth08EvidenceReference(
          id: 'EV-7710',
          quote: '现场记录与反馈',
          capturedAt: '10:22',
          integrityStatus: 'verified',
          integrityVersion: 'evidence-v1',
          scopeMode: 'GLOBAL_ALL',
          domainId: 'CTH',
          productId: 'CTH',
          subjectId: null,
          readAllowed: true,
        ),
      ],
    ),
  ],
  knowledge: const [
    Cth08KnowledgeItem(
      id: 'KN-1',
      title: '高峰疏导复盘',
      summary: '经复核的现场处理方法。',
      caseId: 'CASE-1',
      evidence: [
        Cth08EvidenceReference(
          id: 'EV-7710',
          quote: '来源已核验',
          capturedAt: '10:22',
          integrityStatus: 'verified',
          integrityVersion: 'evidence-v1',
          scopeMode: 'GLOBAL_ALL',
          domainId: 'CTH',
          productId: 'CTH',
          subjectId: null,
          readAllowed: true,
        ),
      ],
    ),
  ],
);

void _expectNoInternalCopy(WidgetTester tester) {
  final text = tester
      .widgetList<Text>(find.byType(Text))
      .map((widget) => widget.data ?? widget.textSpan?.toPlainText() ?? '')
      .join(' ');
  final labels = tester
      .widgetList<Semantics>(find.byType(Semantics))
      .map((widget) => widget.properties.label ?? '')
      .join(' ');
  final copy = '$text $labels'.toLowerCase();
  for (final term in const [
    'api',
    'core',
    'permission',
    'provider',
    'database',
    'owner',
    'token',
    'cookie',
    'http',
    'internal',
  ]) {
    expect(copy, isNot(contains(term)), reason: 'UI leaked "$term".');
  }
}
