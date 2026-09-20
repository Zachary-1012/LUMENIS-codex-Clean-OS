import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/core/lumenis_theme.dart';
import 'package:lumenis_app/features/ai01/ai01_repository.dart';
import 'package:lumenis_app/features/ai01/ai01_screen.dart';
import 'package:lumenis_app/features/ai01/ai01_snapshot.dart';

void main() {
  testWidgets('phone keeps one task surface and shows the scope boundary', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(_app());
    await tester.pumpAndSettle();

    expect(find.text('AI 意图入口'), findsOneWidget);
    expect(find.text('尚未确认可用的经营对象'), findsOneWidget);
    expect(find.text('开始分析'), findsOneWidget);
    expect(find.text('数据依据'), findsOneWidget);
    _expectNoImplementationTerms(tester);

    await tester.ensureVisible(find.text('查看风险变化'));
    await tester.tap(find.text('查看风险变化'));
    await tester.pump();
    expect(
      tester.widget<TextField>(find.byType(TextField)).controller?.text,
      '检查风险变化并列出已有来源',
    );

    await tester.ensureVisible(find.text('数据依据'));
    await tester.tap(find.text('数据依据'));
    await tester.pumpAndSettle();
    expect(find.text('当前账号与经营主体或品牌的查看权限尚未确认，因此暂不展示资料总数或历史内容。'), findsOneWidget);
    expect(find.text('全局私有任务'), findsNothing);

    await tester.ensureVisible(find.text('模型服务状态'));
    await tester.tap(find.text('模型服务状态'));
    await tester.pumpAndSettle();
    expect(find.text('未启动'), findsOneWidget);
    expect(find.text('daemon/model not ready'), findsNothing);

    await tester.ensureVisible(find.text('近期分析记录'));
    await tester.tap(find.text('近期分析记录'));
    await tester.pumpAndSettle();
    expect(find.text('当前账号可查看的经营范围尚未确认，暂时无法显示近期分析记录。'), findsOneWidget);
    _expectNoImplementationTerms(tester);

    final submit = tester.widget<FilledButton>(
      find.widgetWithText(FilledButton, '开始分析'),
    );
    expect(submit.onPressed, isNull);
    expect(tester.takeException(), isNull);
  });

  testWidgets('desktop keeps the Evidence inspector beside the composer', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(_app());
    await tester.pumpAndSettle();

    expect(find.text('意图草稿'), findsOneWidget);
    expect(find.text('业务资料依据'), findsOneWidget);
    expect(find.text('模型服务状态'), findsOneWidget);
    expect(find.text('近期分析记录'), findsOneWidget);
    _expectNoImplementationTerms(tester);
    expect(tester.takeException(), isNull);
  });

  for (final failureCase in _failureCases) {
    testWidgets('shows safe user copy for ${failureCase.name} failures', (
      tester,
    ) async {
      await tester.pumpWidget(
        _app(repository: _FakeAi01Repository(failure: failureCase.error)),
      );
      await tester.pumpAndSettle();

      expect(find.text(failureCase.message), findsOneWidget);
      _expectNoImplementationTerms(tester);
      expect(_visibleCopy(tester), isNot(contains('raw-diagnostic-marker')));
      expect(tester.takeException(), isNull);
    });
  }
}

Widget _app({Ai01Repository? repository}) {
  return MaterialApp(
    theme: LumenisTheme.dark,
    home: Scaffold(
      body: Ai01Screen(
        client: LumenisCoreClient(),
        repository: repository ?? _FakeAi01Repository(),
      ),
    ),
  );
}

class _FakeAi01Repository implements Ai01Repository {
  _FakeAi01Repository({this.failure});

  final Object? failure;

  @override
  Future<Ai01Snapshot> load() async {
    if (failure != null) throw failure!;
    return const Ai01Snapshot(
      isBound: true,
      generatedAt: '2026-09-20T10:00:00',
      providers: [
        Ai01ProviderState(
          name: '本地模型',
          state: 'idle',
          detail: 'daemon/model not ready',
        ),
      ],
      suggestions: [
        Ai01Suggestion(
          title: '查看风险变化',
          description: '查看变化和来源',
          intent: '检查风险变化并列出已有来源',
        ),
      ],
      unavailableFields: [],
    );
  }
}

const _failureCases = <({String name, String error, String message})>[
  (
    name: 'authentication',
    error: 'HTTP 401 raw-diagnostic-marker token=secret Core scope',
    message: '请登录后再查看 AI 服务状态。',
  ),
  (
    name: 'permission',
    error: 'HTTP 403 raw-diagnostic-marker ViewModel contract',
    message: '当前账号没有查看 AI 服务状态的权限。',
  ),
  (
    name: 'offline',
    error: 'Core unavailable raw-diagnostic-marker provider',
    message: '请检查网络连接后重试。',
  ),
  (
    name: 'service error',
    error: 'SQLite trace raw-diagnostic-marker /private/path',
    message: '请稍后重新读取服务状态。',
  ),
];

String _visibleCopy(WidgetTester tester) => <String>[
  ...tester
      .widgetList<Text>(find.byType(Text))
      .map((widget) => widget.data ?? widget.semanticsLabel ?? ''),
  ...tester
      .widgetList<Semantics>(find.byType(Semantics))
      .map((widget) => widget.properties.label ?? ''),
].join('\n');

void _expectNoImplementationTerms(WidgetTester tester) {
  expect(
    _visibleCopy(tester),
    isNot(
      matches(
        RegExp(
          r'\b(core|viewmodel|evidence|owner|scope|contract|provider|runtime|subject|brandfocus|canonical|permission|shared capability|execution policy|registered consumers)\b',
          caseSensitive: false,
        ),
      ),
    ),
  );
}
