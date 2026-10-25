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
    expect(find.textContaining('EV-7701'), findsNothing);
    await tester.tap(find.text('运营指标记录'));
    await tester.pumpAndSettle();
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

    await tester.ensureVisible(find.text('清除选择'));
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

  testWidgets(
    '1280 window with shell shows source brief reading and source rail without raw diagnostics',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(1280, 720));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      await tester.pumpWidget(
        _app(_FakeRepository(() async => _sourceWorkspace()), sidebar: 248),
      );
      await tester.pumpAndSettle();
      expect(
        find.byKey(const ValueKey('cth10/desktop-layout')),
        findsOneWidget,
      );
      expect(find.text('广州商场'), findsWidgets);
      expect(find.text('已收录 1 份资料'), findsOneWidget);
      expect(find.text('发布时间未知 · 收录于 2026-10-25'), findsOneWidget);
      for (final raw in [
        'GLOBAL / ALL',
        'SUBJECT-42',
        '# 来源简报',
        'UNKNOWN',
        "{'document': 1}",
        'evidence:canonical:1',
      ]) {
        expect(find.textContaining(raw), findsNothing);
      }
      expect(tester.getTopLeft(find.text('来源依据')).dy, lessThan(720));
      expect(tester.getTopLeft(find.text('已收录 1 份资料')).dy, lessThan(720));
      final source = find.byKey(
        const ValueKey('cth10/source/evidence:canonical:1'),
      );
      await tester.ensureVisible(source);
      await tester.tap(source);
      await tester.pumpAndSettle();
      expect(find.text('未提供原文链接'), findsOneWidget);
      expect(find.textContaining('evidence:canonical:1'), findsOneWidget);
    },
  );

  testWidgets(
    'source brief keeps unknowns and method details readable in all locales at narrow large text',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(390, 844));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      for (final locale in const [
        Locale('zh', 'CN'),
        Locale('en'),
        Locale('ko'),
      ]) {
        await tester.pumpWidget(
          _app(
            _FakeRepository(() async => _sourceWorkspace()),
            locale: locale,
            textScale: 2,
          ),
        );
        await tester.pumpAndSettle();
        expect(
          find.byKey(const ValueKey('cth10/mobile-layout')),
          findsOneWidget,
        );
        final method = find.byKey(const ValueKey('cth10/source-method'));
        await tester.ensureVisible(method);
        await tester.tap(method);
        await tester.pumpAndSettle();
        expect(
          find.text(
            locale.languageCode == 'en'
                ? 'Not yet established'
                : locale.languageCode == 'ko'
                ? '아직 확인되지 않음'
                : '尚未确认',
          ),
          findsNWidgets(3),
        );
        expect(
          find.text(
            locale.languageCode == 'en'
                ? 'Source types · Document'
                : locale.languageCode == 'ko'
                ? '출처 유형 · 문서'
                : '来源类型 · 文档',
          ),
          findsOneWidget,
        );
        expect(find.textContaining('GLOBAL / ALL'), findsNothing);
        expect(tester.takeException(), isNull);
      }
    },
  );

  testWidgets(
    'existing report headings lists and original text remain readable',
    (tester) async {
      final data = _workspace();
      final original = data.reports.first;
      final report = Cth10Report(
        id: original.id,
        title: original.title,
        period: original.period,
        state: original.state,
        scopeLabel: original.scopeLabel,
        evidence: original.evidence,
        blocks: const [
          Cth10ReportBlock(
            id: 'body',
            title: '原报告',
            kind: 'conclusion',
            status: 'confirmed',
            body: '## 经营观察\n- 保留完整原文及限制。\n**下一步**：核对来源。',
          ),
        ],
      );
      await tester.pumpWidget(
        _app(
          _FakeRepository(
            () async => Cth10WorkspaceData(
              context: data.context,
              state: data.state,
              reports: [report],
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(find.text('经营观察'), findsOneWidget);
      expect(find.text('• 保留完整原文及限制。'), findsOneWidget);
      expect(find.text('下一步：核对来源。'), findsOneWidget);
    },
  );
}

Widget _app(
  Cth10Repository repository, {
  Locale locale = const Locale('zh', 'CN'),
  double sidebar = 0,
  double textScale = 1,
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
    body: MediaQuery(
      data: MediaQueryData(textScaler: TextScaler.linear(textScale)),
      child: Row(
        children: [
          if (sidebar > 0) SizedBox(width: sidebar),
          Expanded(
            child: Cth10Screen(
              client: LumenisCoreClient(),
              repository: repository,
            ),
          ),
        ],
      ),
    ),
  ),
);

Cth10WorkspaceData _sourceWorkspace() => Cth10WorkspaceData(
  context: const Cth10Context(
    mode: Cth10ContextMode.focused,
    subjectId: 'SUBJECT-42',
    displayName: '广州商场',
  ),
  state: Cth10ContentState.ready,
  reports: [
    Cth10Report(
      id: 'source-brief:${List.filled(64, 'a').join()}',
      title: '资料来源简报',
      period: '当前已收录资料',
      state: 'derived_preview_not_saved',
      scopeLabel: 'SUBJECT-42',
      blocks: const [
        Cth10ReportBlock(
          id: 'source-summary',
          title: '来源与覆盖',
          kind: 'source_brief',
          body: "# 来源简报\n- 覆盖：UNKNOWN\n{'document': 1}\nscope:SUBJECT-42",
          status: 'AVAILABLE',
        ),
      ],
      evidence: const [
        Cth10EvidenceReference(
          id: 'evidence:canonical:1',
          quote: '实际交付稿',
          capturedAt: '2026-10-25',
          integrityStatus: 'verified',
          integrityVersion: '1',
          scopeMode: 'FOCUS',
          domainId: 'CTH',
          productId: 'CTH',
          subjectId: 'SUBJECT-42',
          readAllowed: true,
        ),
      ],
      sourceBrief: Cth10SourceBrief(
        contentHash: List.filled(64, 'a').join(),
        status: 'AVAILABLE',
        coverage: 'UNKNOWN',
        freshness: 'UNKNOWN',
        collectionState: 'UNKNOWN',
        sample: const {
          'candidate_count': 1,
          'scanned_count': 1,
          'rejected_count': 0,
          'withheld_count': 0,
          'returned_verified_count': 1,
          'truncated': false,
          'withheld': false,
          'source_type_counts_sample': {'document': 1},
          'platform_counts_sample': {'UNKNOWN': 1},
        },
        records: const [
          {
            'title': '实际交付稿',
            'evidence_id': '1',
            'source_type': 'document',
            'source_platform': 'UNKNOWN',
            'captured_at': '2026-10-25',
            'publish_datetime': null,
            'source_url': null,
            'source_link_status': 'UNKNOWN',
          },
        ],
      ),
    ),
  ],
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
