import 'dart:async';
import 'dart:io';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/core/lumenis_theme.dart';
import 'package:lumenis_app/l10n/lumenis_localizations.dart';
import 'package:lumenis_app/features/ai01/ai01_draft_files.dart';
import 'package:lumenis_app/core/transport/lumenis_http_transport.dart';
import 'package:lumenis_app/features/ai01/ai01_intent.dart';
import 'package:lumenis_app/features/ai01/ai01_repository.dart';
import 'package:lumenis_app/features/ai01/ai01_screen.dart';
import 'package:lumenis_app/features/ai01/ai01_snapshot.dart';

void main() {
  testWidgets('captures desktop and phone widget renders when configured', (
    tester,
  ) async {
    final outputPath = Platform.environment['AI01_VISUAL_CAPTURE_DIR'];
    if (outputPath == null || outputPath.trim().isEmpty) return;
    addTearDown(() => _resetTestSurface(tester));

    final outputDirectory = Directory(outputPath);
    await tester.runAsync(() async {
      await outputDirectory.create(recursive: true);
      await (FontLoader(
        'LumenisSansSC',
      )..addFont(rootBundle.load('assets/fonts/NotoSansSC.ttf'))).load();
      await (FontLoader(
        'LumenisSansKR',
      )..addFont(rootBundle.load('assets/fonts/NotoSansKR.ttf'))).load();
    });
    const scenes = [
      (fileName: 'AI01-desktop-widget-not-live.png', size: Size(1440, 1000)),
      (
        fileName: 'AI01-phone-390x844-widget-not-live.png',
        size: Size(390, 844),
      ),
    ];

    for (final scene in scenes) {
      await _setTestSurface(tester, scene.size);
      await tester.pumpWidget(_app());
      await tester.pumpAndSettle();
      final boundary = tester.renderObject<RenderRepaintBoundary>(
        find.byKey(const ValueKey('ai01-capture-boundary')),
      );
      final png = await tester.runAsync(() async {
        final image = await boundary.toImage(pixelRatio: 1);
        try {
          final data = await image.toByteData(format: ui.ImageByteFormat.png);
          if (data == null) return null;
          return data.buffer.asUint8List(
            data.offsetInBytes,
            data.lengthInBytes,
          );
        } finally {
          image.dispose();
        }
      });
      expect(png, isNotNull);
      final file = File(
        '${outputDirectory.path}${Platform.pathSeparator}${scene.fileName}',
      );
      await tester.runAsync(() => file.writeAsBytes(png!, flush: true));
    }
  });

  testWidgets('phone keeps one task surface with optional global focus', (
    tester,
  ) async {
    await _setTestSurface(tester, const Size(390, 844));
    addTearDown(() => _resetTestSurface(tester));

    await tester.pumpWidget(_app());
    await tester.pumpAndSettle();

    expect(find.text('今天，想完成什么？'), findsOneWidget);
    expect(find.text('AI 助手'), findsNothing);
    expect(find.text('范围可选'), findsOneWidget);
    expect(
      find.text('请输入任务内容后再开始分析。'),
      findsNothing,
      reason: 'The unavailable reason belongs in the disabled action tooltip.',
    );
    expect(find.text('开始分析'), findsOneWidget);
    expect(find.text('查看资料依据'), findsOneWidget);
    expect(find.text('业务资料依据'), findsNothing);
    _expectComposerSurface(tester);
    final editorRect = tester.getRect(
      find.byKey(const ValueKey('ai01-task-input')),
    );
    expect(editorRect.top, lessThan(380));
    expect(editorRect.bottom, lessThan(420));
    _expectNoImplementationTerms(tester);

    final actionButtons = find.descendant(
      of: find.byKey(const ValueKey('ai01-draft-actions')),
      matching: find.byType(TextButton),
    );
    expect(actionButtons.evaluate().length, greaterThanOrEqualTo(2));
    for (var index = 0; index < actionButtons.evaluate().length; index++) {
      expect(
        tester.getSize(actionButtons.at(index)).height,
        greaterThanOrEqualTo(44),
      );
    }

    await tester.ensureVisible(find.text('查看风险变化'));
    await tester.tap(find.text('查看风险变化'));
    await tester.pumpAndSettle();
    expect(
      tester.widget<TextField>(find.byType(TextField)).controller?.text,
      isEmpty,
    );
    await tester.tap(find.byKey(const ValueKey('ai01-suggestion-adopt')));
    await tester.pumpAndSettle();
    expect(
      tester.widget<TextField>(find.byType(TextField)).controller?.text,
      '检查风险变化并列出已有来源',
    );

    final detailsOpener = find.byKey(const ValueKey('ai01-details-open'));
    await tester.ensureVisible(detailsOpener);
    await tester.tap(detailsOpener);
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('ai01-details-dialog')), findsOneWidget);
    expect(find.text('本页面尚未接入可核验的业务资料统计，因此不显示总数。'), findsOneWidget);
    expect(find.text('本页面尚未接入业务资料检索与明细，因此这里不会展示资料记录。'), findsOneWidget);
    expect(find.text('AI 模型服务'), findsOneWidget);
    expect(find.text('近期分析记录'), findsOneWidget);
    expect(find.text('全局私有任务'), findsNothing);
    expect(find.text('未启动'), findsOneWidget);
    expect(find.text('daemon/model not ready'), findsNothing);
    expect(find.text('本页面尚未接入近期分析记录，因此暂不显示历史内容。'), findsOneWidget);
    _expectNoImplementationTerms(tester);

    await tester.tap(find.byKey(const ValueKey('ai01-details-close')));
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('ai01-details-dialog')), findsNothing);
    expect(
      tester.widget<TextButton>(detailsOpener).focusNode!.hasFocus,
      isTrue,
    );

    final submit = tester.widget<FilledButton>(
      find.widgetWithText(FilledButton, '开始分析'),
    );
    expect(submit.onPressed, isNotNull); // ready read + non-empty draft
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'embedded composer defaults global and supports local draft open and save',
    (tester) async {
      await _setTestSurface(tester, const Size(390, 844));
      addTearDown(() => _resetTestSurface(tester));
      final files = _FakeScreenDraftFiles()..opened = '从文件恢复的草稿';

      await tester.pumpWidget(_app(embedded: true, draftFiles: files));
      await tester.pumpAndSettle();

      final embeddedContent = find.byKey(
        const ValueKey('ai01-embedded-content'),
      );
      expect(embeddedContent, findsOneWidget);
      final embeddedSize = tester.getSize(embeddedContent);
      expect(embeddedSize.width, lessThanOrEqualTo(820));
      expect(embeddedSize.height, lessThan(844));
      expect(
        find.descendant(
          of: embeddedContent,
          matching: find.byType(SingleChildScrollView),
        ),
        findsNothing,
      );
      expect(find.text('今天，想完成什么？'), findsNothing);
      expect(find.text('范围可选'), findsOneWidget);
      expect(find.textContaining('尚未确认可用'), findsNothing);
      expect(find.textContaining('暂不能开始分析'), findsNothing);
      expect(find.byTooltip('请输入任务内容后再开始分析。'), findsOneWidget);
      _expectSubmitDisabled(tester);

      final input = find.byKey(const ValueKey('ai01-task-input'));
      await tester.enterText(input, '先保存本地任务');
      expect(tester.widget<TextField>(input).controller!.text, '先保存本地任务');
      await tester.enterText(input, '');
      await tester.tap(find.text('打开文本草稿'));
      await tester.pumpAndSettle();
      expect(tester.widget<TextField>(input).controller!.text, '从文件恢复的草稿');
      expect(find.textContaining('当前内容不会发送或启动分析'), findsOneWidget);

      await tester.enterText(input, 'embedded local draft');
      await tester.pump();
      await tester.tap(find.text('保存文本草稿'));
      await tester.pumpAndSettle();
      expect(files.saved, ['embedded local draft']);
      expect(find.textContaining('文本草稿已保存'), findsOneWidget);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets(
    'uses an injected session draft controller and supplied scope label',
    (tester) async {
      await _setTestSurface(tester, const Size(390, 844));
      addTearDown(() => _resetTestSurface(tester));
      final sessionDraft = TextEditingController(
        text: 'restored session draft',
      );
      final nextSessionDraft = TextEditingController(text: 'scope reset draft');
      addTearDown(() async {
        await tester.pumpWidget(const SizedBox.shrink());
        await tester.pumpAndSettle();
        sessionDraft.dispose();
        nextSessionDraft.dispose();
      });

      await tester.pumpWidget(
        _app(
          embedded: true,
          draftController: sessionDraft,
          scopeLabel: 'GLOBAL_ALL',
        ),
      );
      await tester.pumpAndSettle();

      final input = find.byKey(const ValueKey('ai01-task-input'));
      expect(tester.widget<TextField>(input).controller, same(sessionDraft));
      expect(sessionDraft.text, 'restored session draft');
      expect(find.text('GLOBAL_ALL'), findsOneWidget);
      expect(find.byTooltip('无需先选择经营主体或品牌；焦点选择只会缩小当前任务范围。'), findsOneWidget);
      final submitRect = tester.getRect(
        find.widgetWithText(FilledButton, '开始分析'),
      );
      final scopeRect = tester.getRect(find.text('GLOBAL_ALL'));
      expect((submitRect.center.dy - scopeRect.center.dy).abs(), lessThan(18));

      await tester.enterText(input, 'edited through Home session');
      expect(sessionDraft.text, 'edited through Home session');

      await tester.pumpWidget(
        _app(
          embedded: true,
          draftController: nextSessionDraft,
          scopeLabel: '品牌焦点',
          textScale: 2,
        ),
      );
      await tester.pumpAndSettle();
      expect(
        tester.widget<TextField>(input).controller,
        same(nextSessionDraft),
      );
      expect(nextSessionDraft.text, 'scope reset draft');
      expect(find.text('品牌焦点'), findsOneWidget);
      expect(tester.takeException(), isNull);

      await tester.pumpWidget(const SizedBox.shrink());
      await tester.pumpAndSettle();
      void listener() {}

      sessionDraft.addListener(listener);
      sessionDraft.removeListener(listener);
      nextSessionDraft.addListener(listener);
      nextSessionDraft.removeListener(listener);
    },
  );

  testWidgets(
    'replacing the read owner clears stale results and retains the draft',
    (tester) async {
      final oldRead = Completer<Ai01Snapshot>();
      final currentRead = Completer<Ai01Snapshot>();
      final draft = TextEditingController.fromValue(
        const TextEditingValue(
          text: 'keep my current task',
          selection: TextSelection(baseOffset: 2, extentOffset: 7),
        ),
      );
      addTearDown(() async {
        await tester.pumpWidget(const SizedBox.shrink());
        draft.dispose();
      });
      final oldRepository = _ControlledAi01Repository([oldRead]);
      final currentRepository = _ControlledAi01Repository([currentRead]);
      await tester.pumpWidget(
        _app(repository: oldRepository, draftController: draft),
      );
      await tester.pumpWidget(
        _app(repository: currentRepository, draftController: draft),
      );
      expect(currentRepository._loadCount, 1);

      oldRead.complete(_readySnapshot());
      await tester.pump();
      expect(find.text('查看风险变化'), findsNothing);
      expect(find.text('正在读取 AI 服务状态'), findsOneWidget);

      currentRead.complete(
        const Ai01Snapshot(
          isBound: true,
          generatedAt: null,
          providers: [],
          suggestions: [],
          unavailableFields: [],
        ),
      );
      await tester.pumpAndSettle();
      expect(find.text('正在读取 AI 服务状态'), findsNothing);
      expect(find.text('查看风险变化'), findsNothing);
      expect(draft.text, 'keep my current task');
      expect(
        draft.selection,
        const TextSelection(baseOffset: 2, extentOffset: 7),
      );
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets(
    'a confirmed new draft closes the old focused editor without copying it',
    (tester) async {
      final repository = _FakeAi01Repository();
      final nextDraft = TextEditingController(text: 'new scope task');
      addTearDown(() async {
        await tester.pumpWidget(const SizedBox.shrink());
        await tester.pumpAndSettle();
        nextDraft.dispose();
      });
      await tester.pumpWidget(_app(repository: repository));
      await tester.pumpAndSettle();
      await tester.enterText(
        find.byKey(const ValueKey('ai01-task-input')),
        'old scope task',
      );
      await tester.tap(find.byKey(const ValueKey('ai01-focus-open')));
      await tester.pumpAndSettle();
      expect(find.byKey(const ValueKey('ai01-focus-dialog')), findsOneWidget);

      await tester.pumpWidget(
        _app(repository: repository, draftController: nextDraft),
      );
      await tester.pumpAndSettle();
      expect(find.byKey(const ValueKey('ai01-focus-dialog')), findsNothing);
      expect(
        tester
            .widget<TextField>(find.byKey(const ValueKey('ai01-task-input')))
            .controller,
        same(nextDraft),
      );
      expect(nextDraft.text, 'new scope task');
      expect(find.text('old scope task'), findsNothing);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('desktop centers the task field and opens details on demand', (
    tester,
  ) async {
    await _setTestSurface(tester, const Size(1440, 1000));
    addTearDown(() => _resetTestSurface(tester));

    await tester.pumpWidget(_app());
    await tester.pumpAndSettle();

    expect(find.text('写下你的任务'), findsNothing);
    expect(find.text('AI 助手'), findsNothing);
    expect(find.text('范围可选'), findsOneWidget);
    expect(find.textContaining('暂不能开始分析'), findsNothing);
    _expectComposerSurface(tester);
    expect(find.text('业务资料依据'), findsNothing);
    expect(find.text('模型服务状态'), findsNothing);
    expect(find.text('近期分析记录'), findsNothing);
    final composerRect = tester.getRect(
      find.byKey(const ValueKey('ai01-composer-surface')),
    );
    expect(composerRect.width, lessThanOrEqualTo(820));
    expect(composerRect.center.dx, closeTo(720, 1));
    await tester.tap(find.byKey(const ValueKey('ai01-details-open')));
    await tester.pumpAndSettle();
    final detailsSurface = find
        .ancestor(
          of: find.byKey(const ValueKey('ai01-details-panel')),
          matching: find.byType(Material),
        )
        .first;
    final detailsRect = tester.getRect(detailsSurface);
    expect(detailsRect.width, lessThanOrEqualTo(520));
    expect(find.text('业务资料依据'), findsOneWidget);
    expect(find.text('模型服务状态'), findsOneWidget);
    expect(find.text('近期分析记录'), findsOneWidget);
    _expectNoImplementationTerms(tester);
    expect(tester.takeException(), isNull);
  });

  _submitTests();

  for (final locale in [
    const Locale('zh', 'CN'),
    const Locale('en'),
    const Locale('ko'),
  ]) {
    testWidgets(
      'details opener and return action use ${locale.languageCode} copy',
      (tester) async {
        await _setTestSurface(tester, const Size(390, 844));
        addTearDown(() => _resetTestSurface(tester));
        await tester.pumpWidget(_app(locale: locale, textScale: 2));
        await tester.pumpAndSettle();

        final copy = LumenisLocalizations(locale);
        final openerLabel = copy.text('ai01.inspector.show');
        final closeLabel = copy.text('ai01.inspector.hide');
        expect(find.text(copy.text('ai01.context.label')), findsOneWidget);
        expect(find.text(copy.text('ai01.draft.notice')), findsOneWidget);
        expect(
          find.byTooltip(copy.text('ai01.submit.blocked.empty')),
          findsOneWidget,
        );
        final submit = tester.widget<FilledButton>(
          find.widgetWithText(FilledButton, copy.text('ai01.submit')),
        );
        expect(submit.onPressed, isNull);
        await tester.ensureVisible(find.text(openerLabel));
        await tester.tap(find.text(openerLabel));
        await tester.pumpAndSettle();

        expect(
          find.byKey(const ValueKey('ai01-details-dialog')),
          findsOneWidget,
        );
        expect(find.byTooltip(closeLabel), findsOneWidget);
        expect(find.text(copy.text('ai01.evidence.title')), findsOneWidget);
        expect(find.text(copy.text('ai01.providers.title')), findsOneWidget);
        expect(find.text(copy.text('ai01.executions.title')), findsOneWidget);
        expect(tester.takeException(), isNull);

        await tester.tap(find.byKey(const ValueKey('ai01-details-close')));
        await tester.pumpAndSettle();
        expect(find.byKey(const ValueKey('ai01-details-dialog')), findsNothing);
      },
    );
  }

  testWidgets(
    'details stays bounded and returns focus and draft on close, Escape, and Back',
    (tester) async {
      addTearDown(() => _resetTestSurface(tester));

      const widths = <double>[320, 390, 768, 1440];
      for (var index = 0; index < widths.length; index++) {
        final width = widths[index];
        await tester.pumpWidget(const SizedBox.shrink());
        await tester.pumpAndSettle();
        await _setTestSurface(tester, Size(width, 844));
        await tester.pumpWidget(_app(textScale: width <= 390 ? 2 : 1));
        await tester.pumpAndSettle();

        final inputFinder = find.byKey(const ValueKey('ai01-task-input'));
        final input = tester.widget<TextField>(inputFinder);
        final controller = input.controller!;
        controller.value = const TextEditingValue(
          text: 'local draft — 任务 👩🏻‍💻\nnotes',
          selection: TextSelection(baseOffset: 2, extentOffset: 9),
        );
        await tester.pump();
        final actionsFinder = find.byKey(
          const ValueKey('ai01-draft-actions'),
          skipOffstage: false,
        );
        final actionsState = tester.state(actionsFinder);
        final detailsOpener = find.byKey(const ValueKey('ai01-details-open'));
        await tester.ensureVisible(detailsOpener);
        await tester.tap(detailsOpener);
        await tester.pumpAndSettle();

        final dialog = find.byKey(const ValueKey('ai01-details-dialog'));
        expect(dialog, findsOneWidget);
        final detailsSurface = find
            .ancestor(
              of: find.byKey(const ValueKey('ai01-details-panel')),
              matching: find.byType(Material),
            )
            .first;
        final dialogRect = tester.getRect(detailsSurface);
        expect(dialogRect.width, lessThanOrEqualTo(width - 24));
        expect(dialogRect.width, lessThanOrEqualTo(520));
        expect(dialogRect.height, lessThanOrEqualTo(720));
        if (width < 768) {
          expect(dialogRect.width, closeTo(width - 24, 1));
        } else {
          expect(dialogRect.right, closeTo(width - 24, 1));
        }
        expect(
          find.byKey(const ValueKey('ai01-details-scroll')),
          findsOneWidget,
        );
        expect(controller.text, 'local draft — 任务 👩🏻‍💻\nnotes');
        expect(
          controller.selection,
          const TextSelection(baseOffset: 2, extentOffset: 9),
        );

        if (index == 0) {
          await tester.sendKeyEvent(LogicalKeyboardKey.escape);
        } else if (index == 1) {
          await tester.binding.handlePopRoute();
        } else {
          await tester.tap(find.byKey(const ValueKey('ai01-details-close')));
        }
        await tester.pumpAndSettle();

        expect(dialog, findsNothing);
        expect(controller.text, 'local draft — 任务 👩🏻‍💻\nnotes');
        expect(
          controller.selection,
          const TextSelection(baseOffset: 2, extentOffset: 9),
        );
        expect(tester.state(actionsFinder), same(actionsState));
        expect(
          tester.widget<TextButton>(detailsOpener).focusNode!.hasFocus,
          isTrue,
        );
        _expectSubmitEnabled(tester); // ready read + non-empty draft
        expect(tester.takeException(), isNull);
      }
    },
  );

  testWidgets(
    'details follows the current read through retry without replacing the draft',
    (tester) async {
      await _setTestSurface(tester, const Size(390, 844));
      addTearDown(() => _resetTestSurface(tester));
      final repository = _RecoveringAi01Repository(503);
      await tester.pumpWidget(_app(repository: repository));
      await tester.pumpAndSettle();

      final inputFinder = find.byKey(const ValueKey('ai01-task-input'));
      await tester.enterText(
        inputFinder,
        'keep this task while details refresh',
      );
      final input = tester.widget<TextField>(inputFinder);
      final controller = input.controller!;
      controller.selection = const TextSelection(
        baseOffset: 5,
        extentOffset: 9,
      );
      await tester.pump();
      final actionsFinder = find.byKey(
        const ValueKey('ai01-draft-actions'),
        skipOffstage: false,
      );
      final actionsState = tester.state(actionsFinder);

      await tester.tap(find.byKey(const ValueKey('ai01-details-open')));
      await tester.pumpAndSettle();
      final detailsDialog = find.byKey(const ValueKey('ai01-details-dialog'));
      expect(
        find.descendant(of: detailsDialog, matching: find.text('请稍后重新读取服务状态。')),
        findsOneWidget,
      );
      expect(
        find.descendant(of: detailsDialog, matching: find.text('AI 模型服务')),
        findsNothing,
      );

      await tester.tap(
        find.descendant(
          of: detailsDialog,
          matching: find.byKey(const ValueKey('ai01-read-retry')),
        ),
      );
      await tester.pumpAndSettle();
      expect(repository.calls, 2);
      expect(
        find.descendant(of: detailsDialog, matching: find.text('请稍后重新读取服务状态。')),
        findsNothing,
      );
      expect(
        find.descendant(of: detailsDialog, matching: find.text('暂未收到模型服务的状态。')),
        findsOneWidget,
      );
      expect(controller.text, 'keep this task while details refresh');
      expect(
        controller.selection,
        const TextSelection(baseOffset: 5, extentOffset: 9),
      );
      expect(tester.state(actionsFinder), same(actionsState));
      _expectSubmitEnabled(tester); // ready read + non-empty draft

      await tester.sendKeyEvent(LogicalKeyboardKey.escape);
      await tester.pumpAndSettle();
      expect(
        tester
            .widget<TextButton>(find.byKey(const ValueKey('ai01-details-open')))
            .focusNode!
            .hasFocus,
        isTrue,
      );
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('tablet uses the localized task shell', (tester) async {
    await _setTestSurface(tester, const Size(1024, 900));
    addTearDown(() => _resetTestSurface(tester));

    await tester.pumpWidget(_app(locale: const Locale('en')));
    await tester.pumpAndSettle();

    expect(find.text('What would you like to work on?'), findsOneWidget);
    expect(find.text('Describe your task'), findsNothing);
    expect(find.byType(TextField), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('narrow English phone keeps task editing available', (
    tester,
  ) async {
    await _setTestSurface(tester, const Size(360, 800));
    addTearDown(() => _resetTestSurface(tester));

    await tester.pumpWidget(_app(locale: const Locale('en')));
    await tester.pumpAndSettle();

    expect(find.text('What would you like to work on?'), findsOneWidget);
    expect(find.text('Optional focus'), findsOneWidget);
    expect(find.textContaining('analysis cannot start'), findsNothing);
    expect(find.text('AI assistant'), findsNothing);
    _expectComposerSurface(tester);
    expect(tester.takeException(), isNull);
  });

  testWidgets('never exposes arbitrary provider identifiers', (tester) async {
    await _setTestSurface(tester, const Size(390, 844));
    addTearDown(() => _resetTestSurface(tester));

    await tester.pumpWidget(
      _app(
        repository: _FakeAi01Repository(providerName: 'zhipu-private-prod-17'),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const ValueKey('ai01-details-open')));
    await tester.pumpAndSettle();

    expect(find.text('zhipu-private-prod-17'), findsNothing);
    expect(find.text('AI 模型服务'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('suggestions preview, append, and protect later edits on undo', (
    tester,
  ) async {
    final draft = TextEditingController(text: '保留原始问题');
    addTearDown(draft.dispose);
    final repository = _FakeAi01Repository();
    await tester.pumpWidget(
      _app(repository: repository, draftController: draft),
    );
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.widgetWithText(ActionChip, '查看风险变化'));
    await tester.tap(find.widgetWithText(ActionChip, '查看风险变化'));
    await tester.pumpAndSettle();
    expect(draft.text, '保留原始问题');
    expect(repository.submitted, isEmpty);
    await tester.tap(find.byKey(const ValueKey('ai01-suggestion-adopt')));
    await tester.pumpAndSettle();
    expect(draft.text, '保留原始问题\n检查风险变化并列出已有来源');
    draft.text += '\n后续手工修改';
    await tester.pump();
    await tester.ensureVisible(
      find.byKey(const ValueKey('ai01-suggestion-withdraw')),
    );
    await tester.tap(find.byKey(const ValueKey('ai01-suggestion-withdraw')));
    await tester.pumpAndSettle();
    expect(draft.text, contains('后续手工修改'));
    await tester.tap(find.text('保留编辑'));
    await tester.pumpAndSettle();
    expect(draft.text, contains('后续手工修改'));
    await tester.tap(find.byKey(const ValueKey('ai01-suggestion-withdraw')));
    await tester.pumpAndSettle();
    await tester.tap(
      find.byKey(const ValueKey('ai01-suggestion-withdraw-confirm')),
    );
    await tester.pumpAndSettle();
    expect(draft.text, '保留原始问题');
    expect(repository.submitted, isEmpty);
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'suggestions reject duplicates and overflow and close on owner replacement',
    (tester) async {
      final draft = TextEditingController(text: '检查风险变化并列出已有来源');
      addTearDown(draft.dispose);
      final repository = _FakeAi01Repository();
      await tester.pumpWidget(
        _app(repository: repository, draftController: draft),
      );
      await tester.pumpAndSettle();
      await tester.ensureVisible(find.widgetWithText(ActionChip, '查看风险变化'));
      await tester.tap(find.widgetWithText(ActionChip, '查看风险变化'));
      await tester.pumpAndSettle();
      FilledButton adopt() => tester.widget<FilledButton>(
        find.byKey(const ValueKey('ai01-suggestion-adopt')),
      );
      expect(adopt().onPressed, isNull);
      draft.text = '界' * 3999;
      await tester.pump();
      expect(adopt().onPressed, isNull);
      final replacement = TextEditingController(text: '新问题');
      addTearDown(replacement.dispose);
      await tester.pumpWidget(
        _app(repository: repository, draftController: replacement),
      );
      await tester.pumpAndSettle();
      expect(
        find.byKey(const ValueKey('ai01-suggestion-review')),
        findsNothing,
      );
      expect(replacement.text, '新问题');
      expect(draft.text, '界' * 3999);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('filters untrusted suggestions before Text and EditableText', (
    tester,
  ) async {
    await _setTestSurface(tester, const Size(390, 844));
    addTearDown(() => _resetTestSurface(tester));

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
    'authentication and access copy remain distinct and retry recovers in all locales',
    (tester) async {
      const recoveryLocales = [
        (
          locale: Locale('zh', 'CN'),
          authentication: 'AI 服务状态暂时无法打开',
          authenticationDetail: '可重试读取，或返回后稍后再试。',
          permission: 'AI 服务状态不可访问',
          permissionDetail: '当前页面无法读取该内容。',
          retry: '重新读取',
          forbiddenTerms: ['登录', '账号', '账户', '检查网络', '检查连接'],
        ),
        (
          locale: Locale('en'),
          authentication: 'AI service status cannot be opened right now',
          authenticationDetail:
              'You can retry reading it or return and try again later.',
          permission: 'AI service status is not accessible',
          permissionDetail: 'This content cannot be read on the current page.',
          retry: 'Read again',
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
          authentication: 'AI 서비스 상태를 지금 열 수 없습니다',
          authenticationDetail: '다시 읽기를 시도하거나 돌아간 뒤 나중에 다시 시도할 수 있습니다.',
          permission: 'AI 서비스 상태에 접근할 수 없습니다',
          permissionDetail: '현재 페이지에서 이 콘텐츠를 읽을 수 없습니다.',
          retry: '다시 읽기',
          forbiddenTerms: ['로그인', '계정', '연결을 확인'],
        ),
      ];

      for (final copy in recoveryLocales) {
        for (final statusCode in [401, 403]) {
          await tester.pumpWidget(const SizedBox.shrink());
          await tester.pump();
          final repository = _RecoveringAi01Repository(statusCode);
          await tester.pumpWidget(
            _app(repository: repository, locale: copy.locale),
          );
          await tester.pumpAndSettle();

          final title = statusCode == 401
              ? copy.authentication
              : copy.permission;
          final detail = statusCode == 401
              ? copy.authenticationDetail
              : copy.permissionDetail;
          expect(find.text(title), findsOneWidget);
          expect(find.text(detail), findsOneWidget);
          for (final term in copy.forbiddenTerms) {
            expect(
              _visibleCopy(tester).toLowerCase(),
              isNot(contains(term.toLowerCase())),
            );
          }
          expect(find.text(copy.retry), findsOneWidget);
          expect(
            _visibleCopy(tester),
            isNot(contains('raw-diagnostic-marker')),
          );

          await tester.ensureVisible(find.text(copy.retry));
          await tester.tap(find.text(copy.retry));
          await tester.pumpAndSettle();

          expect(repository.calls, 2);
          expect(find.text(title), findsNothing);
          expect(find.text(detail), findsNothing);
          expect(tester.takeException(), isNull);
        }
      }
    },
  );

  testWidgets(
    'keeps local draft and actions through read failure, retry, and recovery',
    (tester) async {
      await _setTestSurface(tester, const Size(390, 844));
      addTearDown(() => _resetTestSurface(tester));
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
      expect(find.text('草稿未提交。关闭或切换范围前请保存文本。'), findsOneWidget);
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
      _expectSubmitEnabled(tester); // ready read + non-empty draft
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets(
    'expanded draft returns exact text, selection, and focus at each width',
    (tester) async {
      addTearDown(() => _resetTestSurface(tester));

      for (final width in <double>[320, 390, 768, 1440]) {
        await tester.pumpWidget(const SizedBox.shrink());
        await tester.pumpAndSettle();
        await _setTestSurface(tester, Size(width, 900));
        await tester.pumpWidget(_app());
        await tester.pumpAndSettle();

        final sourceField = tester.widget<TextField>(
          find.byKey(const ValueKey('ai01-task-input')),
        );
        final controller = sourceField.controller!;
        final sourceFocus = sourceField.focusNode!;
        controller.value = const TextEditingValue(
          text: 'local draft — 任务 👩🏻‍💻\nnotes',
          selection: TextSelection(baseOffset: 2, extentOffset: 9),
        );
        await tester.pump();
        final draftActions = tester.state(
          find.byKey(const ValueKey('ai01-draft-actions'), skipOffstage: false),
        );

        await tester.tap(find.byKey(const ValueKey('ai01-focus-open')));
        await tester.pumpAndSettle();

        final dialog = find.byKey(const ValueKey('ai01-focus-dialog'));
        final focusedFieldFinder = find.byKey(
          const ValueKey('ai01-focus-input'),
        );
        final focusedField = tester.widget<TextField>(focusedFieldFinder);
        expect(dialog, findsOneWidget);
        expect(focusedField.controller, same(controller));
        expect(focusedField.maxLength, 4000);
        expect(focusedField.style?.fontSize, 16);
        expect(
          find.descendant(
            of: dialog,
            matching: find.byKey(const ValueKey('ai01-draft-actions')),
          ),
          findsNothing,
        );
        expect(
          tester.state(
            find.byKey(
              const ValueKey('ai01-draft-actions'),
              skipOffstage: false,
            ),
          ),
          same(draftActions),
        );

        const finalText = 'revised — exact text 你好\nnext line';
        const finalSelection = TextSelection(baseOffset: 4, extentOffset: 12);
        await tester.enterText(focusedFieldFinder, finalText);
        controller.selection = finalSelection;
        await tester.pump();

        if (width == 1440) {
          await _setTestSurface(tester, const Size(390, 900));
          await tester.pumpAndSettle();
          expect(controller.text, finalText);
          expect(controller.selection, finalSelection);
          expect(
            tester.state(
              find.byKey(
                const ValueKey('ai01-draft-actions'),
                skipOffstage: false,
              ),
            ),
            same(draftActions),
          );

          await _setTestSurface(tester, const Size(1440, 900));
          await tester.pumpAndSettle();
          expect(controller.text, finalText);
          expect(controller.selection, finalSelection);
          expect(
            tester.state(
              find.byKey(
                const ValueKey('ai01-draft-actions'),
                skipOffstage: false,
              ),
            ),
            same(draftActions),
          );
        }

        await tester.tap(find.byKey(const ValueKey('ai01-focus-return')));
        await tester.pumpAndSettle();

        expect(find.byKey(const ValueKey('ai01-focus-dialog')), findsNothing);
        expect(controller.text, finalText);
        expect(controller.selection, finalSelection);
        expect(sourceFocus.hasFocus, isTrue);
        expect(
          tester.state(
            find.byKey(
              const ValueKey('ai01-draft-actions'),
              skipOffstage: false,
            ),
          ),
          same(draftActions),
        );
        expect(tester.takeException(), isNull);
      }
    },
  );

  testWidgets(
    'Escape and system Back return without losing local draft state',
    (tester) async {
      await _setTestSurface(tester, const Size(390, 844));
      addTearDown(() => _resetTestSurface(tester));

      final initialRead = Completer<Ai01Snapshot>();
      final retryRead = Completer<Ai01Snapshot>();
      await tester.pumpWidget(
        _app(repository: _ControlledAi01Repository([initialRead, retryRead])),
      );
      await tester.pump();

      final sourceField = tester.widget<TextField>(
        find.byKey(const ValueKey('ai01-task-input')),
      );
      final controller = sourceField.controller!;
      final sourceFocus = sourceField.focusNode!;
      await tester.enterText(
        find.byKey(const ValueKey('ai01-task-input')),
        'local draft before failure',
      );
      controller.selection = const TextSelection(
        baseOffset: 6,
        extentOffset: 11,
      );
      await tester.pump();
      final draftActions = tester.state(
        find.byKey(const ValueKey('ai01-draft-actions'), skipOffstage: false),
      );

      await tester.tap(find.byKey(const ValueKey('ai01-focus-open')));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));
      await tester.enterText(
        find.byKey(const ValueKey('ai01-focus-input')),
        'local draft kept after service failure',
      );
      const finalSelection = TextSelection(baseOffset: 2, extentOffset: 17);
      controller.selection = finalSelection;
      await tester.pump();

      initialRead.completeError(Exception('Core unavailable'));
      await tester.pumpAndSettle();
      expect(find.byKey(const ValueKey('ai01-focus-dialog')), findsOneWidget);
      expect(find.text('AI 服务暂时无法连接', skipOffstage: false), findsOneWidget);
      expect(controller.text, 'local draft kept after service failure');
      expect(controller.selection, finalSelection);
      expect(
        tester.state(
          find.byKey(const ValueKey('ai01-draft-actions'), skipOffstage: false),
        ),
        same(draftActions),
      );

      await tester.sendKeyEvent(LogicalKeyboardKey.escape);
      await tester.pumpAndSettle();
      expect(find.byKey(const ValueKey('ai01-focus-dialog')), findsNothing);
      expect(controller.text, 'local draft kept after service failure');
      expect(controller.selection, finalSelection);
      expect(sourceFocus.hasFocus, isTrue);
      expect(
        tester.state(
          find.byKey(const ValueKey('ai01-draft-actions'), skipOffstage: false),
        ),
        same(draftActions),
      );

      await tester.tap(find.byKey(const ValueKey('ai01-focus-open')));
      await tester.pumpAndSettle();
      const backSelection = TextSelection(baseOffset: 5, extentOffset: 14);
      controller.selection = backSelection;
      await tester.pump();
      await tester.binding.handlePopRoute();
      await tester.pumpAndSettle();

      expect(find.byKey(const ValueKey('ai01-focus-dialog')), findsNothing);
      expect(controller.text, 'local draft kept after service failure');
      expect(controller.selection, backSelection);
      expect(sourceFocus.hasFocus, isTrue);
      expect(
        tester.state(
          find.byKey(const ValueKey('ai01-draft-actions'), skipOffstage: false),
        ),
        same(draftActions),
      );
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets(
    'expanded editor scales text and stays above phone keyboard insets',
    (tester) async {
      addTearDown(() async {
        await _resetTestSurface(tester);
        tester.view.resetViewInsets();
      });

      for (final width in <double>[320, 390, 768, 1440]) {
        await tester.pumpWidget(const SizedBox.shrink());
        await tester.pumpAndSettle();
        final height = width <= 390 ? 480.0 : 900.0;
        await _setTestSurface(tester, Size(width, height));
        tester.view.resetViewInsets();
        await tester.pumpWidget(_app(textScale: 2));
        await tester.pumpAndSettle();
        await tester.ensureVisible(
          find.byKey(const ValueKey('ai01-focus-open')),
        );
        await tester.tap(find.byKey(const ValueKey('ai01-focus-open')));
        await tester.pumpAndSettle();

        final keyboardInset = width <= 390 ? 220.0 : 0.0;
        if (keyboardInset > 0) {
          tester.view.viewInsets = FakeViewPadding(
            bottom: keyboardInset * tester.view.devicePixelRatio,
          );
          await tester.pumpAndSettle();
        }

        final dialog = find.byKey(const ValueKey('ai01-focus-dialog'));
        final input = find.byKey(const ValueKey('ai01-focus-input'));
        final returnButton = find.byKey(const ValueKey('ai01-focus-return'));
        final footerCopy = LumenisLocalizations(const Locale('zh', 'CN')).text(
          height - keyboardInset < 340
              ? 'ai01.focus.localOnly'
              : 'ai01.focus.notice',
        );
        final footerFinder = find.descendant(
          of: dialog,
          matching: find.text(footerCopy),
        );

        expect(dialog, findsOneWidget);
        expect(tester.widget<TextField>(input).style?.fontSize, 16);
        expect(MediaQuery.textScalerOf(tester.element(input)).scale(16), 32);
        expect(footerFinder, findsOneWidget);
        final returnRect = tester.getRect(returnButton);
        expect(returnRect.top, greaterThanOrEqualTo(0));
        if (keyboardInset > 0) {
          final availableBottom = height - keyboardInset;
          expect(
            tester.getRect(input).bottom,
            lessThanOrEqualTo(availableBottom),
          );
          expect(
            tester.getRect(footerFinder).bottom,
            lessThanOrEqualTo(availableBottom),
          );
          expect(returnRect.bottom, lessThanOrEqualTo(availableBottom));
        }
        expect(tester.takeException(), isNull);

        await tester.tap(returnButton);
        await tester.pumpAndSettle();
        expect(find.byKey(const ValueKey('ai01-focus-dialog')), findsNothing);
      }
    },
  );
}

Future<void> _setTestSurface(WidgetTester tester, Size size) async {
  tester.view.devicePixelRatio = 1;
  tester.view.physicalSize = size;
  await tester.binding.setSurfaceSize(size);
}

Future<void> _resetTestSurface(WidgetTester tester) async {
  await tester.binding.setSurfaceSize(null);
  tester.view.resetPhysicalSize();
  tester.view.resetDevicePixelRatio();
}

void _expectComposerSurface(WidgetTester tester) {
  final surface = tester.widget<Container>(
    find.byKey(const ValueKey('ai01-composer-surface')),
  );
  final decoration = surface.decoration! as BoxDecoration;
  expect(decoration.borderRadius, BorderRadius.circular(16));

  final editor = tester.widget<TextField>(
    find.byKey(const ValueKey('ai01-task-input')),
  );
  expect(editor.style?.fontSize, 16);
  expect(editor.style?.height, 1.5);
  expect(editor.decoration?.filled, isFalse);
  expect(editor.decoration?.border, InputBorder.none);
  expect(editor.decoration?.focusedBorder, InputBorder.none);
  expect(editor.minLines, 3);
  expect(editor.maxLines, 10);
}

void _submitTests() {
  FilledButton submitButton(WidgetTester tester) =>
      tester.widget<FilledButton>(find.byKey(const ValueKey('ai01-submit')));

  Future<void> pumpReady(
    WidgetTester tester,
    _FakeAi01Repository repository,
  ) async {
    await _setTestSurface(tester, const Size(390, 844));
    addTearDown(() => _resetTestSurface(tester));
    await tester.pumpWidget(_app(repository: repository));
    await tester.pumpAndSettle();
  }

  testWidgets('submit is enabled only with a valid draft and sends it once', (
    tester,
  ) async {
    final repository = _FakeAi01Repository(
      onSubmit: (_) async => const Ai01IntentResult(
        kind: Ai01IntentKind.completed,
        status: 'completed',
        executionId: 'exec-ui-1',
        evidenceRecorded: true,
      ),
    );
    await pumpReady(tester, repository);
    final input = find.byKey(const ValueKey('ai01-task-input'));

    expect(submitButton(tester).onPressed, isNull);
    await tester.enterText(input, '   ');
    await tester.pump();
    expect(submitButton(tester).onPressed, isNull);

    await tester.enterText(input, '  检查本周风险变化  ');
    await tester.pump();
    expect(submitButton(tester).onPressed, isNotNull);
    expect(find.byTooltip('请输入任务内容后再开始分析。'), findsNothing);

    await tester.ensureVisible(find.byKey(const ValueKey('ai01-submit')));
    await tester.tap(find.byKey(const ValueKey('ai01-submit')));
    await tester.pumpAndSettle();

    expect(repository.submitted, ['检查本周风险变化']);
    expect(
      find.byKey(const ValueKey('ai01-submit-status-completed')),
      findsOneWidget,
    );
    expect(find.textContaining('exec-ui-1'), findsOneWidget);
    expect(find.text('证据已记录'), findsOneWidget);
    expect(find.text('来源级追溯暂不可用。'), findsOneWidget);
    expect(
      tester.widget<TextField>(input).controller!.text,
      '  检查本周风险变化  ',
      reason: 'the draft is never cleared by submit',
    );
    expect(submitButton(tester).onPressed, isNull);
    expect(find.byTooltip('这段内容已经提交。修改内容后才能再次提交。'), findsOneWidget);

    await tester.enterText(input, '检查本周风险变化并列出来源');
    await tester.pump();
    expect(submitButton(tester).onPressed, isNotNull);
    expect(repository.submitted, hasLength(1));
    expect(tester.takeException(), isNull);
  });

  testWidgets('a failed execution is shown as not completed, never success', (
    tester,
  ) async {
    final repository = _FakeAi01Repository(
      onSubmit: (_) async => const Ai01IntentResult(
        kind: Ai01IntentKind.notCompleted,
        status: 'failed',
        executionId: 'exec-ui-2',
        evidenceRecorded: false,
      ),
    );
    await pumpReady(tester, repository);
    await tester.enterText(
      find.byKey(const ValueKey('ai01-task-input')),
      '检查风险',
    );
    await tester.pump();
    await tester.ensureVisible(find.byKey(const ValueKey('ai01-submit')));
    await tester.tap(find.byKey(const ValueKey('ai01-submit')));
    await tester.pumpAndSettle();

    expect(find.text('分析未完成，没有生成分析结果。'), findsOneWidget);
    expect(find.textContaining('分析已完成'), findsNothing);
    expect(find.text('服务返回状态: failed'), findsOneWidget);
    expect(find.text('证据未确认记录'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('pending approval is not described as executed', (tester) async {
    final repository = _FakeAi01Repository(
      onSubmit: (_) async => const Ai01IntentResult(
        kind: Ai01IntentKind.pendingApproval,
        status: 'pending_approval',
        auditId: 'aud-ui-1',
      ),
    );
    await pumpReady(tester, repository);
    await tester.enterText(
      find.byKey(const ValueKey('ai01-task-input')),
      '检查风险',
    );
    await tester.pump();
    await tester.ensureVisible(find.byKey(const ValueKey('ai01-submit')));
    await tester.tap(find.byKey(const ValueKey('ai01-submit')));
    await tester.pumpAndSettle();

    expect(find.text('该操作需要审批，尚未执行。'), findsOneWidget);
    expect(find.textContaining('aud-ui-1'), findsOneWidget);
    expect(find.text('来源级追溯暂不可用。'), findsNothing);
    expect(find.textContaining('证据'), findsNothing);
    expect(tester.takeException(), isNull);
  });

  for (final failureCase in <({String name, Object error, String message})>[
    (
      name: '400 invalid input',
      error: const LumenisCoreException(
        'POST failed with HTTP 400',
        statusCode: 400,
      ),
      message: '任务内容无效，未执行。请修改后再提交。',
    ),
    (
      name: '401 authentication',
      error: const LumenisCoreException(
        'POST failed with HTTP 401',
        statusCode: 401,
      ),
      message: '服务连接授权已失效，未执行。',
    ),
    (
      name: '403 permission denied',
      error: const LumenisCoreException(
        'POST failed with HTTP 403',
        statusCode: 403,
      ),
      message: '没有权限执行此分析，未执行任何操作。',
    ),
    (
      name: '500 server error',
      error: const LumenisCoreException(
        'POST failed with HTTP 500',
        statusCode: 500,
      ),
      message: '服务出错，无法确认是否已执行。请先核对，再决定是否重新提交。',
    ),
    (
      name: 'transport timeout',
      error: const LumenisTransportException('request timed out'),
      message: '无法确认分析是否已执行，系统不会自动重试。请先核对，再决定是否重新提交。',
    ),
  ]) {
    testWidgets('submit failure ${failureCase.name} keeps its own state', (
      tester,
    ) async {
      final repository = _FakeAi01Repository(
        onSubmit: (_) async => throw failureCase.error,
      );
      await pumpReady(tester, repository);
      await tester.enterText(
        find.byKey(const ValueKey('ai01-task-input')),
        '检查风险',
      );
      await tester.pump();
      await tester.ensureVisible(find.byKey(const ValueKey('ai01-submit')));
      await tester.tap(find.byKey(const ValueKey('ai01-submit')));
      await tester.pumpAndSettle();

      expect(find.text(failureCase.message), findsOneWidget);
      expect(find.textContaining('分析已完成'), findsNothing);
      expect(repository.submitted, hasLength(1), reason: 'no automatic retry');
      expect(tester.takeException(), isNull);
    });
  }

  testWidgets('read failure keeps submit disabled even with a draft', (
    tester,
  ) async {
    final repository = _FakeAi01Repository(
      failure: const LumenisCoreException(
        'GET screen failed with HTTP 503',
        statusCode: 503,
      ),
    );
    await pumpReady(tester, repository);
    await tester.enterText(
      find.byKey(const ValueKey('ai01-task-input')),
      '检查风险',
    );
    await tester.pump();

    expect(submitButton(tester).onPressed, isNull);
    expect(find.byTooltip('AI 服务状态尚未读取成功，暂不能提交。'), findsOneWidget);
    expect(repository.submitted, isEmpty);
  });
}

void _expectSubmitEnabled(WidgetTester tester) {
  final submit = tester.widget<FilledButton>(
    find.byKey(const ValueKey('ai01-submit')),
  );
  expect(submit.onPressed, isNotNull);
}

void _expectSubmitDisabled(WidgetTester tester) {
  final submit = tester.widget<FilledButton>(
    find.widgetWithText(FilledButton, '开始分析'),
  );
  expect(submit.onPressed, isNull);
}

Widget _app({
  Ai01Repository? repository,
  Ai01DraftFiles? draftFiles,
  TextEditingController? draftController,
  String? scopeLabel,
  bool embedded = false,
  Locale locale = const Locale('zh', 'CN'),
  double textScale = 1,
}) {
  final screen = Ai01Screen(
    client: LumenisCoreClient(),
    repository: repository ?? _FakeAi01Repository(),
    draftFiles: draftFiles,
    draftController: draftController,
    scopeLabel: scopeLabel,
    embedded: embedded,
  );
  return MaterialApp(
    theme: LumenisTheme.dark,
    locale: locale,
    builder: (context, child) => MediaQuery(
      data: MediaQuery.of(
        context,
      ).copyWith(textScaler: TextScaler.linear(textScale)),
      child: child ?? const SizedBox.shrink(),
    ),
    supportedLocales: LumenisLocalizations.supportedLocales,
    localizationsDelegates: const [
      LumenisLocalizations.delegate,
      GlobalMaterialLocalizations.delegate,
      GlobalWidgetsLocalizations.delegate,
      GlobalCupertinoLocalizations.delegate,
    ],
    home: Scaffold(
      body: RepaintBoundary(
        key: const ValueKey('ai01-capture-boundary'),
        child: embedded ? SingleChildScrollView(child: screen) : screen,
      ),
    ),
  );
}

class _FakeScreenDraftFiles extends Ai01DraftFiles {
  String? opened;
  final saved = <String>[];

  @override
  bool get canSave => true;

  @override
  Future<String?> open() async => opened;

  @override
  Future<bool> save(String text) async {
    saved.add(text);
    return true;
  }
}

class _FakeAi01Repository implements Ai01Repository {
  _FakeAi01Repository({
    this.failure,
    this.providerName = '本地模型',
    this.suggestions,
    this.onSubmit,
  });

  final Object? failure;
  final String providerName;
  final List<Ai01Suggestion>? suggestions;
  final Future<Ai01IntentResult> Function(String task)? onSubmit;
  final submitted = <String>[];

  @override
  Future<Ai01IntentResult> submitIntent(String task) {
    submitted.add(task);
    final handler = onSubmit;
    if (handler == null) throw StateError('unexpected submit');
    return handler(task);
  }

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

class _RecoveringAi01Repository implements Ai01Repository {
  _RecoveringAi01Repository(this.statusCode);

  @override
  Future<Ai01IntentResult> submitIntent(String task) =>
      throw StateError('unexpected submit');

  final int statusCode;
  int calls = 0;

  @override
  Future<Ai01Snapshot> load() async {
    calls++;
    if (calls == 1) {
      throw LumenisCoreException(
        'HTTP $statusCode private access failure',
        statusCode: statusCode,
      );
    }
    return _readySnapshot();
  }
}

class _ControlledAi01Repository implements Ai01Repository {
  _ControlledAi01Repository(this._responses);

  @override
  Future<Ai01IntentResult> submitIntent(String task) =>
      throw StateError('unexpected submit');

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
    message: '可重试读取，或返回后稍后再试。',
  ),
  (
    name: 'permission',
    error: 'HTTP 403 raw-diagnostic-marker ViewModel contract',
    message: '当前页面无法读取该内容。',
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
