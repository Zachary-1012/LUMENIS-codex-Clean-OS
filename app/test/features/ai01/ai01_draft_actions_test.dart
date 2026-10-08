import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/features/ai01/ai01_draft_actions.dart';
import 'package:lumenis_app/features/ai01/ai01_draft_files.dart';
import 'package:lumenis_app/l10n/lumenis_localizations.dart';

void main() {
  testWidgets('late file selection preserves newer edits', (tester) async {
    final controller = TextEditingController(text: 'original');
    final pending = Completer<String?>();
    final files = _Files()..pendingOpen = pending;
    addTearDown(controller.dispose);
    await tester.pumpWidget(_app(controller, files));
    await tester.tap(find.text('打开文本草稿'));
    await tester.pump();
    controller.text = 'newer work';
    pending.complete('old file');
    await tester.pumpAndSettle();
    expect(controller.text, 'newer work');
    expect(find.byType(AlertDialog), findsNothing);
    expect(find.textContaining('发生了变化'), findsOneWidget);
  });

  testWidgets('late file selection cannot enter a replacement draft', (
    tester,
  ) async {
    final previous = TextEditingController();
    final replacement = TextEditingController();
    final pending = Completer<String?>();
    final files = _Files()..pendingOpen = pending;
    addTearDown(previous.dispose);
    addTearDown(replacement.dispose);
    await tester.pumpWidget(_app(previous, files));
    await tester.tap(find.text('打开文本草稿'));
    await tester.pump();
    await tester.pumpWidget(_app(replacement, files));
    pending.complete('previous task file');
    await tester.pumpAndSettle();
    expect(replacement.text, isEmpty);
    expect(previous.text, isEmpty);
    expect(tester.takeException(), isNull);
  });

  testWidgets('opening or replacing a file returns typing to the composer', (
    tester,
  ) async {
    final controller = TextEditingController();
    final focusNode = FocusNode();
    final files = _Files()..opened = '恢复的草稿';
    addTearDown(controller.dispose);
    addTearDown(focusNode.dispose);
    await tester.pumpWidget(
      _app(controller, files, const Locale('zh', 'CN'), focusNode),
    );
    for (final needsConfirmation in [false, true]) {
      if (needsConfirmation) controller.text = '更新过的草稿';
      await tester.tap(find.text('打开文本草稿'));
      await tester.pumpAndSettle();
      if (needsConfirmation) {
        await tester.tap(find.text('打开并替换'));
        await tester.pumpAndSettle();
      }
      expect(focusNode.hasFocus, isTrue);
      expect(controller.text, '恢复的草稿');
      expect(
        controller.selection,
        TextSelection.collapsed(offset: controller.text.length),
      );
    }
  });

  test(
    'text import preserves Unicode and rejects damaged or oversized input',
    () {
      const text = '序境：比较真实活动结果。\nBrand review 👩‍💻\n브랜드';
      expect(
        Ai01DraftFiles.decode(Uint8List.fromList(utf8.encode('\uFEFF$text'))),
        text,
      );
      for (final bytes in [
        Uint8List.fromList([0xc3, 0x28]),
        Uint8List.fromList(utf8.encode('valid\u0000hidden')),
        Uint8List.fromList(utf8.encode('字' * 4001)),
        Uint8List(Ai01DraftFiles.maxBytes + 1),
      ]) {
        expect(() => Ai01DraftFiles.decode(bytes), throwsFormatException);
      }
      expect(
        Ai01DraftFiles.decode(Uint8List.fromList(utf8.encode('👩‍💻' * 4000))),
        '👩‍💻' * 4000,
      );
    },
  );

  testWidgets('save exports exact unsent text and canceled open preserves it', (
    tester,
  ) async {
    final controller = TextEditingController(text: '原始草稿\n第二行');
    final files = _Files();
    addTearDown(controller.dispose);
    await tester.pumpWidget(_app(controller, files));
    await tester.tap(find.text('保存文本草稿'));
    await tester.pumpAndSettle();
    expect(files.saved, ['原始草稿\n第二行']);
    expect(find.textContaining('文本草稿已保存'), findsOneWidget);
    await tester.tap(find.text('打开文本草稿'));
    await tester.pumpAndSettle();
    expect(controller.text, '原始草稿\n第二行');
    expect(find.byType(AlertDialog), findsNothing);
  });

  testWidgets(
    'opening different text needs confirmation; decline retains draft',
    (tester) async {
      final controller = TextEditingController(text: '未保存的工作');
      final files = _Files()..opened = '从文件恢复';
      addTearDown(controller.dispose);
      await tester.pumpWidget(_app(controller, files));
      await tester.tap(find.text('打开文本草稿'));
      await tester.pumpAndSettle();
      expect(find.text('替换当前草稿？'), findsOneWidget);
      await tester.tap(find.text('保留当前内容'));
      await tester.pumpAndSettle();
      expect(controller.text, '未保存的工作');
      await tester.tap(find.text('打开文本草稿'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('打开并替换'));
      await tester.pumpAndSettle();
      expect(controller.text, '从文件恢复');
      expect(find.textContaining('尚未提交'), findsOneWidget);
      expect(find.textContaining('不会发送或启动分析'), findsOneWidget);
    },
  );

  testWidgets('write failure and chooser failure preserve current text', (
    tester,
  ) async {
    final controller = TextEditingController(text: '必须保留');
    final files = _Files()..fail = true;
    addTearDown(controller.dispose);
    await tester.pumpWidget(_app(controller, files));
    for (final label in ['保存文本草稿', '打开文本草稿']) {
      await tester.tap(find.text(label));
      await tester.pumpAndSettle();
      expect(controller.text, '必须保留');
      expect(find.textContaining('操作未完成'), findsOneWidget);
    }
  });

  testWidgets(
    'async replacement cannot overwrite text changed during confirmation',
    (tester) async {
      final controller = TextEditingController(text: 'original');
      final files = _Files()..opened = 'file';
      addTearDown(controller.dispose);
      await tester.pumpWidget(_app(controller, files));
      await tester.tap(find.text('打开文本草稿'));
      await tester.pumpAndSettle();
      controller.text = 'newer edit';
      await tester.tap(find.text('打开并替换'));
      await tester.pumpAndSettle();
      expect(controller.text, 'newer edit');
      expect(find.textContaining('发生了变化'), findsOneWidget);
    },
  );

  testWidgets(
    'mobile keeps copy/open without unsupported save; busy prevents duplicates',
    (tester) async {
      final controller = TextEditingController(text: 'draft');
      final pending = Completer<String?>();
      final files = _Files()
        ..saveSupported = false
        ..pendingOpen = pending;
      addTearDown(controller.dispose);
      await tester.binding.setSurfaceSize(const Size(390, 844));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      await tester.pumpWidget(_app(controller, files, const Locale('en')));
      expect(find.text('Save text draft'), findsNothing);
      expect(find.text('Copy draft'), findsOneWidget);
      await tester.tap(find.text('Open text draft'));
      await tester.pump();
      expect(
        tester
            .widget<TextButton>(
              find.widgetWithText(TextButton, 'Open text draft'),
            )
            .onPressed,
        isNull,
      );
      pending.complete(null);
      await tester.pumpAndSettle();
      expect(controller.text, 'draft');
      expect(tester.takeException(), isNull);
    },
  );
}

Widget _app(
  TextEditingController controller,
  Ai01DraftFiles files, [
  Locale locale = const Locale('zh', 'CN'),
  FocusNode? focusNode,
]) => MaterialApp(
  locale: locale,
  supportedLocales: LumenisLocalizations.supportedLocales,
  localizationsDelegates: const [
    LumenisLocalizations.delegate,
    GlobalMaterialLocalizations.delegate,
    GlobalWidgetsLocalizations.delegate,
    GlobalCupertinoLocalizations.delegate,
  ],
  home: Scaffold(
    body: Column(
      children: [
        if (focusNode != null)
          TextField(controller: controller, focusNode: focusNode),
        Ai01DraftActions(
          controller: controller,
          files: files,
          focusNode: focusNode,
        ),
      ],
    ),
  ),
);

class _Files extends Ai01DraftFiles {
  String? opened;
  bool fail = false;
  bool saveSupported = true;
  Completer<String?>? pendingOpen;
  final List<String> saved = [];
  @override
  bool get canSave => saveSupported;
  @override
  Future<String?> open() async {
    if (fail) throw StateError('read refused');
    if (pendingOpen != null) return pendingOpen!.future;
    return opened;
  }

  @override
  Future<bool> save(String text) async {
    if (fail) throw StateError('write refused');
    saved.add(text);
    return true;
  }
}
