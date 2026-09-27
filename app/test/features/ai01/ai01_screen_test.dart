import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/core/lumenis_theme.dart';
import 'package:lumenis_app/l10n/lumenis_localizations.dart';
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

    expect(find.text('今天，想完成什么？'), findsOneWidget);
    expect(find.text('尚未确认可用的经营对象'), findsOneWidget);
    expect(find.text('开始分析'), findsOneWidget);
    expect(find.text('数据依据'), findsOneWidget);
    final editorRect = tester.getRect(find.byType(TextField));
    expect(editorRect.top, lessThan(380));
    expect(editorRect.bottom, lessThan(640));
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

    expect(find.text('写下你的任务'), findsOneWidget);
    expect(find.text('业务资料依据'), findsOneWidget);
    expect(find.text('模型服务状态'), findsOneWidget);
    expect(find.text('近期分析记录'), findsOneWidget);
    _expectNoImplementationTerms(tester);
    expect(tester.takeException(), isNull);
  });

  testWidgets('tablet uses the localized task shell', (tester) async {
    await tester.binding.setSurfaceSize(const Size(1024, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(_app(locale: const Locale('en')));
    await tester.pumpAndSettle();

    expect(find.text('What would you like to work on?'), findsOneWidget);
    expect(find.text('Describe your task'), findsOneWidget);
    expect(find.byType(TextField), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('never exposes arbitrary provider identifiers', (tester) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      _app(
        repository: _FakeAi01Repository(providerName: 'zhipu-private-prod-17'),
      ),
    );
    await tester.pumpAndSettle();

    await tester.ensureVisible(find.text('模型服务状态'));
    await tester.tap(find.text('模型服务状态'));
    await tester.pumpAndSettle();

    expect(find.text('zhipu-private-prod-17'), findsNothing);
    expect(find.text('AI 模型服务'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('filters untrusted suggestions before Text and EditableText', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      _app(
        repository: _FakeAi01Repository(
          suggestions: [
            const Ai01Suggestion(
              title: 'model=ollama-prod',
              description: 'DB Permission Evidence /private/path',
              intent: 'Call /api/v1 provider=internal model=secret',
            ),
          ],
        ),
      ),
    );
    await tester.pumpAndSettle();

    final editable = tester.widget<EditableText>(find.byType(EditableText));
    expect(editable.controller.text, isEmpty);
    expect(find.text('model=ollama-prod'), findsNothing);
    expect(find.textContaining('/api/v1'), findsNothing);
    expect(_visibleCopy(tester), isNot(contains('private/path')));
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

  testWidgets(
    'keeps local draft and actions through read failure, retry, and recovery',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(390, 844));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      final messenger =
          TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger;
      String? copiedText;
      messenger.setMockMethodCallHandler(SystemChannels.platform, (call) async {
        if (call.method == 'Clipboard.setData') {
          final arguments = call.arguments as Map<Object?, Object?>;
          copiedText = arguments['text'] as String?;
        }
        return null;
      });
      addTearDown(
        () => messenger.setMockMethodCallHandler(SystemChannels.platform, null),
      );

      final initialRead = Completer<Ai01Snapshot>();
      final retryRead = Completer<Ai01Snapshot>();
      final repository = _ControlledAi01Repository([initialRead, retryRead]);
      await tester.pumpWidget(_app(repository: repository));

      expect(find.text('今天，想完成什么？'), findsOneWidget);
      expect(find.text('正在读取 AI 服务状态'), findsOneWidget);
      expect(find.byType(TextField), findsOneWidget);
      _expectSubmitDisabled(tester);

      await tester.enterText(find.byType(TextField), '本地草稿待续');
      await tester.pump();
      final controller = tester
          .widget<TextField>(find.byType(TextField))
          .controller!;
      controller.selection = const TextSelection(
        baseOffset: 1,
        extentOffset: 4,
      );
      var editable = tester.widget<EditableText>(find.byType(EditableText));
      editable.focusNode.requestFocus();
      await tester.pump();

      await tester.ensureVisible(find.text('复制草稿'));
      await tester.tap(find.text('复制草稿'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));
      expect(find.text('草稿已复制，可粘贴到你选择的位置。'), findsOneWidget);
      expect(copiedText, '本地草稿待续');

      final actionsFinder = find.byKey(const ValueKey('ai01-draft-actions'));
      final actionsState = tester.state(actionsFinder);
      controller.selection = const TextSelection(
        baseOffset: 1,
        extentOffset: 4,
      );
      editable = tester.widget<EditableText>(find.byType(EditableText));
      editable.focusNode.requestFocus();
      await tester.pump();

      initialRead.completeError(Exception('Core unavailable'));
      await tester.pumpAndSettle();

      expect(find.text('AI 服务暂时无法连接'), findsOneWidget);
      expect(find.text('请检查网络连接后重试。'), findsOneWidget);
      expect(find.text('你仍可在本机打开、编辑和复制任务草稿。'), findsOneWidget);
      expect(find.text('草稿已复制，可粘贴到你选择的位置。'), findsOneWidget);
      expect(find.text('查看风险变化'), findsNothing);
      expect(find.text('近期分析记录'), findsNothing);
      expect(tester.state(actionsFinder), same(actionsState));
      expect(controller.text, '本地草稿待续');
      expect(
        controller.selection,
        const TextSelection(baseOffset: 1, extentOffset: 4),
      );
      expect(editable.focusNode.hasFocus, isTrue);
      _expectSubmitDisabled(tester);

      await tester.ensureVisible(find.text('重新读取'));
      await tester.tap(find.text('重新读取'));
      await tester.pump();

      expect(find.text('正在读取 AI 服务状态'), findsOneWidget);
      expect(find.text('草稿已复制，可粘贴到你选择的位置。'), findsOneWidget);
      expect(tester.state(actionsFinder), same(actionsState));
      expect(controller.text, '本地草稿待续');
      expect(
        controller.selection,
        const TextSelection(baseOffset: 1, extentOffset: 4),
      );
      _expectSubmitDisabled(tester);

      editable = tester.widget<EditableText>(find.byType(EditableText));
      editable.focusNode.requestFocus();
      await tester.pump();
      retryRead.complete(_readySnapshot());
      await tester.pumpAndSettle();

      editable = tester.widget<EditableText>(find.byType(EditableText));
      expect(find.text('查看风险变化'), findsOneWidget);
      expect(find.text('正在读取 AI 服务状态'), findsNothing);
      expect(find.text('草稿已复制，可粘贴到你选择的位置。'), findsOneWidget);
      expect(tester.state(actionsFinder), same(actionsState));
      expect(controller.text, '本地草稿待续');
      expect(
        controller.selection,
        const TextSelection(baseOffset: 1, extentOffset: 4),
      );
      expect(editable.focusNode.hasFocus, isTrue);
      _expectSubmitDisabled(tester);
      expect(tester.takeException(), isNull);
    },
  );
}

void _expectSubmitDisabled(WidgetTester tester) {
  final submit = tester.widget<FilledButton>(
    find.widgetWithText(FilledButton, '开始分析'),
  );
  expect(submit.onPressed, isNull);
}

Widget _app({
  Ai01Repository? repository,
  Locale locale = const Locale('zh', 'CN'),
}) {
  return MaterialApp(
    theme: LumenisTheme.dark,
    locale: locale,
    supportedLocales: LumenisLocalizations.supportedLocales,
    localizationsDelegates: const [
      LumenisLocalizations.delegate,
      GlobalMaterialLocalizations.delegate,
      GlobalWidgetsLocalizations.delegate,
      GlobalCupertinoLocalizations.delegate,
    ],
    home: Scaffold(
      body: Ai01Screen(
        client: LumenisCoreClient(),
        repository: repository ?? _FakeAi01Repository(),
      ),
    ),
  );
}

class _FakeAi01Repository implements Ai01Repository {
  _FakeAi01Repository({
    this.failure,
    this.providerName = '本地模型',
    this.suggestions,
  });

  final Object? failure;
  final String providerName;
  final List<Ai01Suggestion>? suggestions;

  @override
  Future<Ai01Snapshot> load() async {
    if (failure != null) throw failure!;
    return Ai01Snapshot(
      isBound: true,
      generatedAt: '2026-09-20T10:00:00',
      providers: [
        Ai01ProviderState(
          name: providerName,
          state: 'idle',
          detail: 'daemon/model not ready',
        ),
      ],
      suggestions:
          suggestions ??
          const [
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

class _ControlledAi01Repository implements Ai01Repository {
  _ControlledAi01Repository(this._responses);

  final List<Completer<Ai01Snapshot>> _responses;
  int _loadCount = 0;

  @override
  Future<Ai01Snapshot> load() => _responses[_loadCount++].future;
}

Ai01Snapshot _readySnapshot() => const Ai01Snapshot(
  isBound: true,
  generatedAt: '2026-09-27T10:00:00',
  providers: [],
  suggestions: [
    Ai01Suggestion(
      title: '查看风险变化',
      description: '查看变化和来源',
      intent: '检查风险变化并列出已有来源',
    ),
  ],
  unavailableFields: [],
);

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
