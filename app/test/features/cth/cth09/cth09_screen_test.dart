import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/core/lumenis_theme.dart';
import 'package:lumenis_app/features/cth/cth09/cth09_repository.dart';
import 'package:lumenis_app/features/cth/cth09/cth09_screen.dart';
import 'package:lumenis_app/l10n/lumenis_localizations.dart';

void main() {
  testWidgets('loading keeps risk and decision rows hidden', (tester) async {
    final pending = Completer<Cth09WorkbenchData>();
    await tester.pumpWidget(_app(_FakeRepository(() => pending.future)));

    expect(find.text('晚高峰停车摩擦'), findsNothing);
    expect(find.byType(CircularProgressIndicator), findsOneWidget);
    expect(find.bySemanticsLabel('正在读取风险与决策'), findsOneWidget);

    pending.complete(_workbench());
    await tester.pumpAndSettle();
    expect(find.text('晚高峰停车摩擦'), findsOneWidget);
  });

  testWidgets('blocked binding keeps the decision loop unavailable', (
    tester,
  ) async {
    await tester.pumpWidget(
      _app(
        _FakeRepository(
          () => Future.error(
            const Cth09BlockedException(
              Cth09BlockedReason.evidenceBindingUnavailable,
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('风险与决策资料暂不可用'), findsOneWidget);
    expect(find.text('当前范围或来源依据尚未完成核验，风险与决策资料未显示。'), findsOneWidget);
    expect(find.text('晚高峰停车摩擦'), findsNothing);
    _expectNoInternalCopy(tester);
  });

  testWidgets('empty and not-collected states remain distinct', (tester) async {
    await tester.pumpWidget(
      _app(
        _FakeRepository(
          () async => const Cth09WorkbenchData(
            context: Cth09Context(mode: Cth09ContextMode.globalAll),
            state: Cth09ContentState.empty,
            risks: [],
            decisions: [],
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('cth09/content-state')), findsOneWidget);
    expect(find.text('当前范围内暂无待处理风险或决策。'), findsOneWidget);

    await tester.pumpWidget(
      _app(
        _FakeRepository(
          () async => const Cth09WorkbenchData(
            context: Cth09Context(mode: Cth09ContextMode.globalAll),
            state: Cth09ContentState.notCollected,
            risks: [],
            decisions: [],
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('风险或决策资料尚未接入。'), findsOneWidget);
    _expectNoInternalCopy(tester);
  });

  testWidgets('desktop and mobile use different risk compositions', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(_app(_FakeRepository(() async => _workbench())));
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('cth09/desktop-layout')), findsOneWidget);
    expect(find.text('风险登记'), findsOneWidget);
    expect(find.text('决策台账'), findsOneWidget);
    await tester.tap(find.text('晚高峰停车摩擦'));
    await tester.pumpAndSettle();
    expect(find.textContaining('EV-7710'), findsOneWidget);
    await tester.tap(find.text('清除选择'));
    await tester.pumpAndSettle();

    await tester.binding.setSurfaceSize(const Size(390, 844));
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('cth09/mobile-layout')), findsOneWidget);
    expect(find.text('风险登记'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'decision controls stay disabled without all gates and a callable',
    (tester) async {
      await tester.pumpWidget(_app(_FakeRepository(() async => _workbench())));
      await tester.pumpAndSettle();

      final buttons = tester.widgetList<OutlinedButton>(
        find.byType(OutlinedButton),
      );
      expect(buttons, isNotEmpty);
      expect(buttons.every((button) => button.onPressed == null), isTrue);
      expect(find.text('当前工作区暂不能执行此操作'), findsOneWidget);
      expect(find.text('NOTE:777'), findsNothing);
      _expectNoInternalCopy(tester);
    },
  );

  testWidgets('select and clear risk basis locally', (tester) async {
    await tester.pumpWidget(_app(_FakeRepository(() async => _workbench())));
    await tester.pumpAndSettle();

    await tester.tap(find.text('晚高峰停车摩擦'));
    await tester.pumpAndSettle();
    expect(find.text('决策依据'), findsWidgets);
    expect(find.textContaining('EV-7710'), findsOneWidget);

    await tester.tap(find.text('清除选择'));
    await tester.pumpAndSettle();
    expect(find.text('暂无已核验风险。'), findsOneWidget);
  });

  testWidgets('copy is available in English and Korean', (tester) async {
    for (final locale in const [Locale('en'), Locale('ko')]) {
      await tester.pumpWidget(
        _app(_FakeRepository(() async => _workbench()), locale: locale),
      );
      await tester.pumpAndSettle();
      expect(
        find.textContaining(locale.languageCode == 'en' ? 'Risk' : '리스크'),
        findsWidgets,
      );
      _expectNoInternalCopy(tester);
    }
  });
}

Widget _app(
  Cth09Repository repository, {
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
    body: Cth09Screen(client: LumenisCoreClient(), repository: repository),
  ),
);

class _FakeRepository implements Cth09Repository {
  const _FakeRepository(this._loader);

  final Future<Cth09WorkbenchData> Function() _loader;

  @override
  Future<Cth09WorkbenchData> load() => _loader();
}

Cth09WorkbenchData _workbench() => const Cth09WorkbenchData(
  context: Cth09Context(mode: Cth09ContextMode.globalAll),
  state: Cth09ContentState.ready,
  risks: [
    Cth09Risk(
      id: 'RISK-1',
      title: '晚高峰停车摩擦',
      level: 'critical',
      score: 84,
      summary: '现场反馈显示到店体验受到影响。',
      evidence: [
        Cth09EvidenceReference(
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
  decisions: [
    Cth09Decision(
      id: 'DEC-1',
      title: '开放备用通道',
      owner: '运营值班',
      status: 'pending',
      actionLabel: '开放 B3 备用通道（18-21点）',
      gate: Cth09ActionGate(
        permission: 'unknown',
        effectFence: 'unknown',
        resultContract: 'unknown',
        callable: false,
        approval: 'required',
      ),
      evidence: [
        Cth09EvidenceReference(
          id: 'EV-DECISION-1',
          quote: '决策依据',
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
    'note:',
  ]) {
    expect(copy, isNot(contains(term)), reason: 'UI leaked "$term".');
  }
}
