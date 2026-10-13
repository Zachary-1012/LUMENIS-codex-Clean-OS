import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/core/lumenis_theme.dart';
import 'package:lumenis_app/features/bmp08/bmp08_repository.dart';
import 'package:lumenis_app/features/bmp08/bmp08_screen.dart';
import 'package:lumenis_app/features/bmp08/bmp08_snapshot.dart';
import 'package:lumenis_app/l10n/lumenis_localizations.dart';
import 'package:lumenis_app/navigation/lumenis_leave_guard.dart';

void main() {
  testWidgets(
    'desktop studio aligns sources, script, properties and empty audio',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(1360, 900));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      await tester.pumpWidget(_app(_approvedSnapshot(audioAvailable: true)));
      await tester.pumpAndSettle();

      expect(find.text('制作资料'), findsWidgets);
      expect(find.text('逐字稿与分段'), findsWidgets);
      expect(find.text('属性'), findsOneWidget);
      await tester.tap(find.byKey(const ValueKey('podcast-audio-view')));
      await tester.pumpAndSettle();
      expect(find.text('音频舞台'), findsOneWidget);
      expect(find.text('音频来源已登记；可播放音频与真实波形尚未提供。'), findsOneWidget);
      await tester.tap(find.byKey(const ValueKey('podcast-script-view')));
      await tester.pumpAndSettle();

      await tester.tap(find.text('访谈').last);
      await tester.pumpAndSettle();
      expect(find.text('00:42'), findsWidgets);

      final draft = find.byType(TextFormField);
      await tester.enterText(draft, '本地修订，不发送到服务端');
      await tester.pumpAndSettle();
      expect(find.text('本地修订，不发送到服务端'), findsOneWidget);

      final scriptDraftAction = find.text('保存脚本请求草稿');
      await tester.ensureVisible(scriptDraftAction);
      await tester.tap(scriptDraftAction);
      await tester.pumpAndSettle();
      expect(find.text('本地制作请求草稿已保存；尚未生成脚本或渲染成片。'), findsOneWidget);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('mobile studio switches one task at a time without overflow', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(_app(_approvedSnapshot(audioAvailable: false)));
    await tester.pumpAndSettle();

    expect(find.text('选择要处理的工作区'), findsOneWidget);
    expect(find.text('访谈'), findsOneWidget);
    final lastTask = tester.getBottomLeft(
      find.widgetWithText(ChoiceChip, '属性'),
    );
    final activePane = tester.getTopLeft(find.text('逐字稿与分段'));
    expect(activePane.dy - lastTask.dy, lessThan(42));

    await tester.tap(find.text('音频').first);
    await tester.pumpAndSettle();
    expect(find.text('音频舞台'), findsOneWidget);
    expect(find.textContaining('未确认音频'), findsOneWidget);
    expect(find.text('音频待提供'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'route leave protects local text and cancellation retains editing',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(1360, 900));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      final guard = LumenisLeaveGuard();
      addTearDown(guard.dispose);
      await tester.pumpWidget(
        _app(_approvedSnapshot(audioAvailable: false), guard: guard),
      );
      await tester.pumpAndSettle();
      expect(guard.needsProtection, isFalse);
      await tester.enterText(find.byType(TextFormField), '保留访谈修订');
      await tester.pump();
      expect(guard.needsProtection, isTrue);
      final cancelled = guard.requestLeave();
      await tester.pumpAndSettle();
      await tester.tap(find.widgetWithText(TextButton, '取消'));
      await tester.pumpAndSettle();
      expect(await cancelled, isFalse);
      expect(find.text('保留访谈修订'), findsOneWidget);
      final leaving = guard.requestLeave();
      await tester.pumpAndSettle();
      await tester.tap(find.widgetWithText(FilledButton, '放弃修订并离开'));
      await tester.pumpAndSettle();
      expect(await leaving, isTrue);
      // The navigation owner decides the exit; confirming never claims a save.
      expect(guard.needsProtection, isTrue);
      await tester.pumpWidget(const SizedBox());
      expect(guard.needsProtection, isFalse);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets(
    'unconfirmed scope keeps the studio skeleton and hides raw data',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(1360, 900));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      final restricted = Bmp08Snapshot(
        contractBound: true,
        dataState: 'READY',
        scope: const Bmp08Scope(
          mode: 'FOCUS',
          brandId: 'unverified-brand',
          displayNames: {'zh-CN': '不得显示的品牌'},
        ),
        scopeApproved: false,
        audioAvailable: true,
        versioned: true,
        rightsReady: true,
        materials: const [
          Bmp08Material(
            name: '受限资料名称',
            kind: 'AUDIO',
            brandId: 'unverified-brand',
          ),
        ],
        outline: const [
          Bmp08OutlineSection(
            title: '受限脚本段落',
            timecode: '00:12',
            hasSource: true,
          ),
        ],
        grantedPermissions: const {'podcast:draft', 'podcast:render'},
      );

      await tester.pumpWidget(_app(restricted));
      await tester.pumpAndSettle();

      expect(find.text('制作资料'), findsWidgets);
      expect(find.text('逐字稿与分段'), findsWidgets);
      expect(find.text('属性'), findsOneWidget);
      expect(find.byKey(const ValueKey('podcast-audio-view')), findsOneWidget);
      expect(find.text('播客范围尚未确认'), findsOneWidget);
      expect(find.text('范围与来源验证完成前，资料、脚本、音频和版权信息均保持隐藏。'), findsOneWidget);
      expect(find.text('经确认的逐字稿会按时间码显示在这里。'), findsOneWidget);
      expect(find.text('—'), findsWidgets);
      expect(find.text('共 0 项'), findsNothing);
      expect(find.text('共 0 段'), findsNothing);
      expect(find.text('保存脚本请求草稿'), findsOneWidget);
      expect(find.text('保存渲染请求草稿'), findsOneWidget);
      expect(find.text('不得显示的品牌'), findsNothing);
      expect(find.text('受限资料名称'), findsNothing);
      expect(find.text('受限脚本段落'), findsNothing);
      expect(tester.takeException(), isNull);
    },
  );
  testWidgets(
    'desktop task changes and resize preserve per-segment draft intent',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(1440, 900));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      await tester.pumpWidget(_app(_approvedSnapshot(audioAvailable: true)));
      await tester.pumpAndSettle();
      await tester.enterText(find.byType(TextFormField), '开场修订');
      await tester.tap(find.text('访谈').first);
      await tester.pumpAndSettle();
      await tester.enterText(find.byType(TextFormField), '访谈修订');
      await tester.tap(find.byKey(const ValueKey('podcast-audio-view')));
      await tester.pumpAndSettle();
      expect(find.byType(TextFormField), findsNothing);
      expect(find.text('00:42  访谈'), findsOneWidget);
      expect(find.text('音频来源已登记；可播放音频与真实波形尚未提供。'), findsOneWidget);
      await tester.tap(find.byKey(const ValueKey('podcast-script-view')));
      await tester.pumpAndSettle();
      expect(find.text('访谈修订'), findsOneWidget);
      await tester.tap(find.text('开场').first);
      await tester.pumpAndSettle();
      expect(find.text('开场修订'), findsOneWidget);
      final pane = tester.getRect(
        find.byKey(const PageStorageKey('podcast-active-pane')),
      );
      expect(pane.height, greaterThan(450));
      expect(pane.bottom, lessThan(900));
      await tester.binding.setSurfaceSize(const Size(390, 844));
      await tester.pumpAndSettle();
      expect(find.text('开场修订'), findsOneWidget);
      await tester.tap(find.text('音频').first);
      await tester.pumpAndSettle();
      await tester.tap(find.text('脚本').first);
      await tester.pumpAndSettle();
      expect(find.text('开场修订'), findsOneWidget);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets(
    'refresh cancellation protects pending text and confirmed refresh resets it',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(1440, 900));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      await tester.pumpWidget(_app(_approvedSnapshot(audioAvailable: true)));
      await tester.pumpAndSettle();
      await tester.enterText(find.byType(TextFormField), '不要丢失这段修订');
      await tester.tap(find.byTooltip('刷新播客工作台'));
      await tester.pumpAndSettle();
      expect(find.text('放弃本次文字修订并刷新？'), findsOneWidget);
      await tester.tap(find.text('取消'));
      await tester.pumpAndSettle();
      expect(find.text('不要丢失这段修订'), findsOneWidget);
      await tester.tap(find.byTooltip('刷新播客工作台'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('放弃修订并刷新'));
      await tester.pumpAndSettle();
      expect(find.text('不要丢失这段修订'), findsNothing);
      expect(find.byType(TextFormField), findsOneWidget);
      expect(tester.takeException(), isNull);
    },
  );

  for (final language in ['zh', 'en', 'ko']) {
    testWidgets(
      '$language small screen and large text keep all work areas reachable',
      (tester) async {
        await tester.binding.setSurfaceSize(const Size(320, 568));
        addTearDown(() => tester.binding.setSurfaceSize(null));
        await tester.pumpWidget(
          _app(
            _approvedSnapshot(audioAvailable: false),
            language: language,
            textScale: 2,
          ),
        );
        await tester.pumpAndSettle();
        final selector = find.byKey(
          const ValueKey('podcast-work-area-selector'),
        );
        expect(selector, findsOneWidget);
        for (var i = 0; i < 4; i++) {
          await tester.ensureVisible(selector);
          await tester.tap(selector);
          await tester.pumpAndSettle();
          final labels = switch (language) {
            'en' => ['Script', 'Sources', 'Audio', 'Properties'],
            'ko' => ['스크립트', '자료', '오디오', '속성'],
            _ => ['脚本', '资料', '音频', '属性'],
          };
          final option = find.text(labels[i]).last;
          await tester.ensureVisible(option);
          await tester.tap(option);
          await tester.pumpAndSettle();
          expect(
            find.byWidgetPredicate((widget) => widget is DropdownMenuItem),
            findsOneWidget,
          );
          await tester.pumpAndSettle();
          expect(tester.takeException(), isNull);
        }
      },
    );
  }
}

Widget _app(
  Bmp08Snapshot snapshot, {
  String language = 'zh',
  double textScale = 1,
  LumenisLeaveGuard? guard,
}) => MaterialApp(
  theme: LumenisTheme.light,
  locale: Locale(language),
  builder: (context, child) => MediaQuery(
    data: MediaQuery.of(
      context,
    ).copyWith(textScaler: TextScaler.linear(textScale)),
    child: guard == null
        ? child!
        : LumenisLeaveScope(guard: guard, child: child!),
  ),
  supportedLocales: LumenisLocalizations.supportedLocales,
  localizationsDelegates: const [
    LumenisLocalizations.delegate,
    GlobalMaterialLocalizations.delegate,
    GlobalWidgetsLocalizations.delegate,
    GlobalCupertinoLocalizations.delegate,
  ],
  home: Scaffold(
    body: Bmp08Screen(
      client: LumenisCoreClient(),
      repository: _FakeBmp08Repository(snapshot),
    ),
  ),
);

class _FakeBmp08Repository implements Bmp08Repository {
  const _FakeBmp08Repository(this.snapshot);

  final Bmp08Snapshot snapshot;

  @override
  Future<Bmp08Snapshot> load() async => snapshot;
}

Bmp08Snapshot _approvedSnapshot({required bool audioAvailable}) =>
    Bmp08Snapshot(
      contractBound: true,
      dataState: 'READY',
      scope: const Bmp08Scope(
        mode: 'FOCUS',
        brandId: 'brand-a',
        displayNames: {'zh-CN': '山海品牌'},
      ),
      scopeApproved: true,
      audioAvailable: audioAvailable,
      versioned: false,
      rightsReady: false,
      materials: const [
        Bmp08Material(name: '品牌简报', kind: 'BRIEF', brandId: 'brand-a'),
      ],
      outline: const [
        Bmp08OutlineSection(title: '开场', timecode: '00:00', hasSource: true),
        Bmp08OutlineSection(title: '访谈', timecode: '00:42', hasSource: false),
      ],
      grantedPermissions: const {'podcast:draft', 'podcast:render'},
    );
