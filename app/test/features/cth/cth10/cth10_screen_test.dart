import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/core/lumenis_theme.dart';
import 'package:lumenis_app/features/cth/cth10/cth10_repository.dart';
import 'package:lumenis_app/features/cth/cth10/cth10_screen.dart';
import 'package:lumenis_app/l10n/lumenis_localizations.dart';

void main() {
  testWidgets('loading keeps report material hidden', (tester) async {
    final pending = Completer<Cth10WorkspaceData>();
    await tester.pumpWidget(_app(_FakeRepository(() => pending.future)));

    expect(find.text('商业运营周报'), findsNothing);
    expect(find.byType(CircularProgressIndicator), findsOneWidget);
    expect(find.bySemanticsLabel('正在读取报告与运营简报'), findsOneWidget);

    pending.complete(_workspace());
    await tester.pumpAndSettle();
    expect(find.text('商业运营周报'), findsNWidgets(2));
  });

  testWidgets('blocked scope keeps report and source rows hidden', (
    tester,
  ) async {
    await tester.pumpWidget(
      _app(
        _FakeRepository(
          () => Future.error(
            const Cth10BlockedException(
              Cth10BlockedReason.reportScopeUnavailable,
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('报告资料暂不可用'), findsOneWidget);
    expect(find.text('当前范围或来源依据尚未完成核验，报告资料未显示。'), findsOneWidget);
    expect(find.text('商业运营周报'), findsNothing);
    _expectNoInternalCopy(tester);
  });

  testWidgets('empty and not-collected states remain distinct', (tester) async {
    await tester.pumpWidget(
      _app(
        _FakeRepository(
          () async => const Cth10WorkspaceData(
            context: Cth10Context(mode: Cth10ContextMode.globalAll),
            state: Cth10ContentState.empty,
            reports: [],
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('cth10/content-state')), findsOneWidget);
    expect(find.text('当前范围内暂无报告。'), findsOneWidget);

    await tester.pumpWidget(
      _app(
        _FakeRepository(
          () async => const Cth10WorkspaceData(
            context: Cth10Context(mode: Cth10ContextMode.globalAll),
            state: Cth10ContentState.notCollected,
            reports: [],
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('报告资料尚未接入，暂不能生成运营简报。'), findsOneWidget);
    _expectNoInternalCopy(tester);
  });

  testWidgets('desktop and mobile use storyboard compositions', (tester) async {
    await tester.binding.setSurfaceSize(const Size(1440, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(_app(_FakeRepository(() async => _workspace())));
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('cth10/desktop-layout')), findsOneWidget);
    expect(find.text('报告结构'), findsOneWidget);
    expect(find.text('报告预览'), findsOneWidget);
    expect(find.text('来源依据'), findsOneWidget);
    expect(find.textContaining('EV-7701'), findsOneWidget);

    await tester.binding.setSurfaceSize(const Size(390, 844));
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('cth10/mobile-layout')), findsOneWidget);
    expect(find.text('报告预览'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'generate and export stay disabled without write/effect contracts',
    (tester) async {
      await tester.pumpWidget(_app(_FakeRepository(() async => _workspace())));
      await tester.pumpAndSettle();

      final generate = tester.widget<FilledButton>(
        find.widgetWithText(FilledButton, '生成运营简报'),
      );
      final export = tester.widget<OutlinedButton>(
        find.widgetWithText(OutlinedButton, '导出 PDF / Excel'),
      );
      expect(generate.onPressed, isNull);
      expect(export.onPressed, isNull);
      expect(find.text('EV-PRIVATE-TOKEN'), findsNothing);
      _expectNoInternalCopy(tester);
    },
  );

  testWidgets('report selection and return remain local', (tester) async {
    await tester.pumpWidget(_app(_FakeRepository(() async => _workspace())));
    await tester.pumpAndSettle();

    await tester.tap(find.text('停车专题分析'));
    await tester.pumpAndSettle();
    expect(find.text('停车专题分析'), findsWidgets);
    expect(find.text('结论'), findsNWidgets(2));

    await tester.tap(find.text('清除选择'));
    await tester.pumpAndSettle();
    expect(find.text('报告预览'), findsOneWidget);
  });

  testWidgets('copy is available in English and Korean', (tester) async {
    for (final locale in const [Locale('en'), Locale('ko')]) {
      await tester.pumpWidget(
        _app(_FakeRepository(() async => _workspace()), locale: locale),
      );
      await tester.pumpAndSettle();
      expect(
        find.textContaining(locale.languageCode == 'en' ? 'Reports' : '리포트'),
        findsWidgets,
      );
      _expectNoInternalCopy(tester);
    }
  });
}

Widget _app(
  Cth10Repository repository, {
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
    body: Cth10Screen(client: LumenisCoreClient(), repository: repository),
  ),
);

class _FakeRepository implements Cth10Repository {
  const _FakeRepository(this._loader);

  final Future<Cth10WorkspaceData> Function() _loader;

  @override
  Future<Cth10WorkspaceData> load() => _loader();
}

Cth10WorkspaceData _workspace() => const Cth10WorkspaceData(
  context: Cth10Context(mode: Cth10ContextMode.globalAll),
  state: Cth10ContentState.ready,
  reports: [
    Cth10Report(
      id: 'REPORT-1',
      title: '商业运营周报',
      period: '09/02-09/08',
      state: 'confirmed',
      scopeLabel: 'GLOBAL / ALL',
      blocks: [
        Cth10ReportBlock(
          id: 'BLOCK-1',
          title: '本周结论',
          kind: 'conclusion',
          body: '客流与运营反馈显示，停车体验是本周需要关注的主要驱动。',
          status: 'confirmed',
        ),
        Cth10ReportBlock(
          id: 'BLOCK-2',
          title: '风险驱动',
          kind: 'driver',
          body: '晚高峰现场记录支持下一步运营调整。',
          status: 'confirmed',
        ),
      ],
      evidence: [
        Cth10EvidenceReference(
          id: 'EV-7701',
          quote: '运营指标记录',
          capturedAt: '09-09',
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
    Cth10Report(
      id: 'REPORT-2',
      title: '停车专题分析',
      period: '近30天',
      state: 'draft',
      scopeLabel: 'GLOBAL / ALL',
      blocks: [
        Cth10ReportBlock(
          id: 'BLOCK-3',
          title: '结论',
          kind: 'conclusion',
          body: '现场反馈仍在整理。',
          status: 'draft',
        ),
      ],
      evidence: [
        Cth10EvidenceReference(
          id: 'EV-7710',
          quote: '现场记录',
          capturedAt: '09-09',
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
