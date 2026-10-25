import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/core/lumenis_theme.dart';
import 'package:lumenis_app/features/shared/sh01/manuscript_draft_files.dart';
import 'package:lumenis_app/features/shared/sh01/manuscript_controller.dart';
import 'package:lumenis_app/features/shared/sh01/manuscript_editor.dart';
import 'package:lumenis_app/l10n/lumenis_localizations.dart';
import 'package:lumenis_app/navigation/lumenis_leave_guard.dart';

const _draft = <String, dynamic>{
  'title': '周末街区声音计划',
  'summary': '记录街区的声音，整理成一期五分钟播客。',
  'sections': [
    {'heading': '开场', 'body': '周六清晨的街道。\n保留现场声音。'},
    {'heading': '访谈', 'body': '店主的一天。'},
  ],
  'language': 'zh',
  'authorship': 'user_supplied',
};

class _DraftFiles extends ManuscriptDraftFiles {
  Map<String, dynamic>? saved;
  Map<String, dynamic>? returned = _draft;
  @override
  bool get canSave => true;
  @override
  Future<Map<String, dynamic>?> open() async => returned;
  @override
  Future<bool> save(Map<String, dynamic> value) async {
    saved = value;
    return true;
  }
}

class _LostSaveClient extends LumenisCoreClient {
  _LostSaveClient() : super(baseUrl: 'http://127.0.0.1:1');

  LumenisWorkspaceScope? lastScope;

  @override
  Future<Map<String, dynamic>> prepareInternalPitch({
    required LumenisWorkspaceScope scope,
    required InternalPitchManuscript manuscript,
    required String requestId,
    InternalPitchRevision? revision,
    List<Map<String, dynamic>> citations = const [],
  }) async {
    lastScope = scope;
    throw const LumenisCoreException('Save response unavailable');
  }
}

Widget _app({
  _DraftFiles? files,
  LumenisLeaveGuard? guard,
  VoidCallback? onBack,
  Locale locale = const Locale('zh'),
  double scale = 1,
  ManuscriptController? controller,
  LumenisCoreClient? client,
}) => MaterialApp(
  theme: LumenisTheme.light,
  locale: locale,
  supportedLocales: LumenisLocalizations.supportedLocales,
  localizationsDelegates: const [
    LumenisLocalizations.delegate,
    GlobalMaterialLocalizations.delegate,
    GlobalWidgetsLocalizations.delegate,
    GlobalCupertinoLocalizations.delegate,
  ],
  builder: (context, child) => MediaQuery(
    data: MediaQuery.of(context).copyWith(textScaler: TextScaler.linear(scale)),
    child: child!,
  ),
  home: Scaffold(
    body: LumenisLeaveScope(
      guard: guard ?? LumenisLeaveGuard(),
      child: ManuscriptEditor(
        client: client ?? LumenisCoreClient(baseUrl: 'http://127.0.0.1:1'),
        onBack: onBack ?? () {},
        draftFiles: files,
        controller: controller,
      ),
    ),
  ),
);

Future<void> _menu(WidgetTester tester, String label) async {
  await tester.tap(find.byType(PopupMenuButton<String>));
  await tester.pumpAndSettle();
  await tester.tap(find.text(label));
  await tester.pumpAndSettle();
}

String _value(WidgetTester tester, String key) =>
    tester.widget<TextField>(find.byKey(Key(key))).controller!.text;

void main() {
  testWidgets(
    'writing keeps the page wide and makes outline and preview optional',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(1280, 850));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      await tester.pumpWidget(_app(files: _DraftFiles()));
      await tester.pumpAndSettle();
      await _menu(tester, '打开草稿文件');
      final body = find.byKey(const Key('manuscript-body-0'));
      expect(tester.getSize(body).width, greaterThan(650));
      expect(find.text('阅读预览'), findsNothing);
      await tester.tap(find.byKey(const Key('manuscript-preview-toggle')));
      await tester.pumpAndSettle();
      expect(find.text('阅读预览'), findsOneWidget);
      expect(find.byKey(const Key('manuscript-title')), findsNothing);
      await tester.tap(find.byKey(const Key('manuscript-preview-toggle')));
      await tester.pumpAndSettle();
      expect(_value(tester, 'manuscript-body-0'), '周六清晨的街道。\n保留现场声音。');
      await tester.tap(find.byKey(const Key('manuscript-outline-toggle')));
      await tester.pumpAndSettle();
      expect(find.widgetWithText(ListTile, '访谈'), findsOneWidget);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('independent writing works without a selected business scope', (
    tester,
  ) async {
    final client = _LostSaveClient();
    await tester.binding.setSurfaceSize(const Size(1280, 850));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(_app(client: client));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('manuscript-title')), '手写方案');
    await tester.enterText(
      find.byKey(const Key('manuscript-summary')),
      '由自己的内容开始。',
    );
    await tester.enterText(find.byKey(const Key('manuscript-heading-0')), '行动');
    await tester.enterText(
      find.byKey(const Key('manuscript-body-0')),
      '今天整理想法，明天继续。',
    );
    await tester.pumpAndSettle();
    expect(_value(tester, 'manuscript-body-0'), '今天整理想法，明天继续。');
    expect(
      tester
          .widget<FilledButton>(find.byKey(const Key('manuscript-save')))
          .onPressed,
      isNotNull,
    );
    await tester.tap(find.byKey(const Key('manuscript-save')));
    await tester.pumpAndSettle();
    expect(client.lastScope?.toJson(), {
      'scope_kind': 'shared_workspace',
      'version': 1,
    });
    expect(find.textContaining('登录'), findsNothing);
    expect(find.textContaining('选择主体'), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'local draft opens exact text and saves all sections without server identity',
    (tester) async {
      final files = _DraftFiles();
      await tester.binding.setSurfaceSize(const Size(1280, 850));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      await tester.pumpWidget(_app(files: files));
      await tester.pumpAndSettle();
      await _menu(tester, '打开草稿文件');
      expect(_value(tester, 'manuscript-title'), _draft['title']);
      expect(_value(tester, 'manuscript-body-0'), '周六清晨的街道。\n保留现场声音。');
      await _menu(tester, '保存草稿文件');
      expect(files.saved, _draft);
      expect(files.saved!.containsKey('scope'), isFalse);
      expect(files.saved!.containsKey('task_id'), isFalse);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('outline removal is reversible and preserves exact paragraph', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1280, 850));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(_app(files: _DraftFiles()));
    await tester.pumpAndSettle();
    await _menu(tester, '打开草稿文件');
    await tester.tap(find.byTooltip('移除段落'));
    await tester.pumpAndSettle();
    expect(_value(tester, 'manuscript-heading-0'), '访谈');
    await tester.tap(find.text('撤销移除'));
    await tester.pumpAndSettle();
    expect(_value(tester, 'manuscript-heading-0'), '开场');
    expect(_value(tester, 'manuscript-body-0'), '周六清晨的街道。\n保留现场声音。');
    await tester.tap(find.byTooltip('向后移动'));
    await tester.pumpAndSettle();
    expect(_value(tester, 'manuscript-heading-1'), '开场');
    expect(_value(tester, 'manuscript-body-1'), '周六清晨的街道。\n保留现场声音。');
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'route leave protects unsaved writing and cancelled exit keeps content',
    (tester) async {
      final guard = LumenisLeaveGuard();
      await tester.pumpWidget(_app(guard: guard));
      await tester.pumpAndSettle();
      await tester.enterText(find.byKey(const Key('manuscript-title')), '尚未保存');
      await tester.pumpAndSettle();
      expect(guard.needsProtection, isTrue);
      final leaving = guard.requestLeave();
      await tester.pumpAndSettle();
      await tester.tap(find.text('继续编辑'));
      await tester.pumpAndSettle();
      expect(await leaving, isFalse);
      expect(_value(tester, 'manuscript-title'), '尚未保存');
      await tester.pumpWidget(const SizedBox());
      guard.dispose();
    },
  );

  testWidgets('the section limit reserves space for undo without losing text', (
    tester,
  ) async {
    final files = _DraftFiles()
      ..returned = {
        ..._draft,
        'sections': List.generate(
          64,
          (index) => {'heading': '段落 $index', 'body': '原稿 $index'},
        ),
      };
    await tester.binding.setSurfaceSize(const Size(1280, 850));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(_app(files: files));
    await tester.pumpAndSettle();
    await _menu(tester, '打开草稿文件');
    await tester.tap(find.byTooltip('移除段落'));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('manuscript-outline-toggle')));
    await tester.pumpAndSettle();
    final add = find.byKey(const Key('manuscript-outline-add'));
    expect(tester.widget<TextButton>(add).onPressed, isNull);
    await tester.tap(find.text('撤销移除'));
    await tester.pumpAndSettle();
    expect(_value(tester, 'manuscript-body-0'), '原稿 0');
    await _menu(tester, '保存草稿文件');
    expect((files.saved!['sections'] as List).length, 64);
    expect((files.saved!['sections'] as List).first['body'], '原稿 0');
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'a clean imported draft retains uncertain save recovery on exit',
    (tester) async {
      final guard = LumenisLeaveGuard();
      final controller = ManuscriptController(
        client: _LostSaveClient(),
        scope: const SharedWorkspaceScope(),
        draft: InternalPitchManuscript(
          title: '',
          summary: '',
          sections: [],
          language: 'zh',
          authorship: 'user_supplied',
        ),
      );
      await tester.binding.setSurfaceSize(const Size(1280, 850));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      await tester.pumpWidget(
        _app(files: _DraftFiles(), guard: guard, controller: controller),
      );
      await tester.pumpAndSettle();
      await _menu(tester, '打开草稿文件');
      expect(guard.needsProtection, isFalse);
      await tester.tap(find.byKey(const Key('manuscript-save')));
      await tester.pumpAndSettle();
      expect(controller.prepareAcknowledgementLost, isTrue);
      expect(guard.needsProtection, isTrue);
      expect(await guard.requestLeave(), isFalse);
      await tester.pumpAndSettle();
      expect(find.text('恢复本次保存'), findsOneWidget);
      expect(_value(tester, 'manuscript-title'), _draft['title']);
      expect(tester.takeException(), isNull);
      await tester.pumpWidget(const SizedBox());
      guard.dispose();
      controller.dispose();
    },
  );

  for (final locale in ['zh', 'en', 'ko']) {
    testWidgets('$locale narrow writing at 200 percent remains operable', (
      tester,
    ) async {
      await tester.binding.setSurfaceSize(const Size(320, 640));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      await tester.pumpWidget(_app(locale: Locale(locale), scale: 2));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('manuscript-title')), findsOneWidget);
      expect(find.byKey(const Key('manuscript-back')), findsOneWidget);
      expect(tester.takeException(), isNull);
      final preview = locale == 'zh'
          ? '预览'
          : locale == 'ko'
          ? '미리보기'
          : 'Preview';
      await tester.tap(find.text(preview));
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
    });
  }
}
