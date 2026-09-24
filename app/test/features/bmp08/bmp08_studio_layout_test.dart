import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/core/lumenis_theme.dart';
import 'package:lumenis_app/features/bmp08/bmp08_repository.dart';
import 'package:lumenis_app/features/bmp08/bmp08_screen.dart';
import 'package:lumenis_app/features/bmp08/bmp08_snapshot.dart';
import 'package:lumenis_app/l10n/lumenis_localizations.dart';

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
      expect(find.text('音频舞台'), findsOneWidget);
      expect(find.text('音频来源已登记；可播放音频与真实波形尚未提供。'), findsOneWidget);

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

    await tester.tap(find.text('音频').first);
    await tester.pumpAndSettle();
    expect(find.text('音频舞台'), findsOneWidget);
    expect(find.textContaining('未确认音频'), findsOneWidget);
    expect(find.text('音频待提供'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

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
      expect(find.text('音频舞台'), findsOneWidget);
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
}

Widget _app(Bmp08Snapshot snapshot) => MaterialApp(
  theme: LumenisTheme.light,
  locale: const Locale('zh', 'CN'),
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
