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
    expect(find.text('授权上下文未连接'), findsOneWidget);
    expect(find.text('提交 AI 任务'), findsOneWidget);
    expect(find.text('Evidence 摘要'), findsOneWidget);

    await tester.ensureVisible(find.text('查看风险变化'));
    await tester.tap(find.text('查看风险变化'));
    await tester.pump();
    expect(
      tester.widget<TextField>(find.byType(TextField)).controller?.text,
      '检查风险变化并列出已有来源',
    );

    await tester.ensureVisible(find.text('Evidence 摘要'));
    await tester.tap(find.text('Evidence 摘要'));
    await tester.pumpAndSettle();
    expect(find.text('现有 Evidence 统计源是全库口径，服务端暂不读取；数量和分布不返回。'), findsOneWidget);
    expect(find.text('全局私有任务'), findsNothing);

    await tester.ensureVisible(find.text('最近执行'));
    await tester.tap(find.text('最近执行'));
    await tester.pumpAndSettle();
    expect(find.text('最近执行接口未绑定已授权产品上下文，记录暂不展示。'), findsOneWidget);

    final submit = tester.widget<FilledButton>(
      find.widgetWithText(FilledButton, '提交 AI 任务'),
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
    expect(find.text('EVIDENCE / SHARED'), findsOneWidget);
    expect(find.text('RUNTIME / PROVIDERS'), findsOneWidget);
    expect(find.text('AI EXECUTION / RECENT'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}

Widget _app() {
  return MaterialApp(
    theme: LumenisTheme.dark,
    home: Scaffold(
      body: Ai01Screen(
        client: LumenisCoreClient(),
        repository: _FakeAi01Repository(),
      ),
    ),
  );
}

class _FakeAi01Repository implements Ai01Repository {
  @override
  Future<Ai01Snapshot> load() async => const Ai01Snapshot(
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
