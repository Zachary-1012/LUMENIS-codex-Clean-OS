import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/core/lumenis_theme.dart';
import 'package:lumenis_app/shell/lumenis_workspace_shell.dart';

void main() {
  testWidgets(
    '1440 wide CTH-02 stays nested in CTH and returns without switching context',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(1440, 1000));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      await tester.pumpWidget(_app());
      await tester.pumpAndSettle();

      final openDirectory = find.byTooltip('查看经营主体目录');
      expect(openDirectory, findsOneWidget);
      await tester.tap(openDirectory);
      await tester.pumpAndSettle();

      expect(
        find.byKey(const ValueKey('cth02/desktop-layout')),
        findsOneWidget,
      );
      expect(find.text('经营主体目录 · 当前经营主体不变'), findsOneWidget);
      expect(find.text('CTH 测试主体'), findsOneWidget);
      expect(find.byTooltip('返回商业运营总览'), findsOneWidget);
      expect(find.byTooltip('查看经营主体目录'), findsNothing);

      await tester.tap(find.byTooltip('返回商业运营总览'));
      await tester.pumpAndSettle();

      expect(find.byTooltip('查看经营主体目录'), findsOneWidget);
      expect(find.text('经营主体目录 · 当前经营主体不变'), findsNothing);
      expect(find.text('当前经营主体：CTH-SUBJECT-7'), findsOneWidget);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets(
    '390 phone CTH-02 is a nested browse flow, not a sixth destination',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(390, 844));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      await tester.pumpWidget(_app());
      await tester.pumpAndSettle();
      expect(find.byType(NavigationDestination), findsNWidgets(5));

      await tester.tap(find.byTooltip('查看经营主体目录'));
      await tester.pumpAndSettle();

      expect(find.byKey(const ValueKey('cth02/mobile-layout')), findsOneWidget);
      expect(find.text('经营主体目录 · 当前经营主体不变'), findsOneWidget);
      expect(find.byType(NavigationDestination), findsNWidgets(5));
      await tester.tap(find.byTooltip('返回商业运营总览'));
      await tester.pumpAndSettle();
      expect(find.byTooltip('查看经营主体目录'), findsOneWidget);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('1440 wide shell keeps the CTH brand key out of BMP context', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(_app());
    await tester.pumpAndSettle();
    await tester.tap(find.text('品牌市场'));
    await tester.pumpAndSettle();

    expect(find.text('服务已连接'), findsOneWidget);
    expect(find.textContaining('online'), findsNothing);
    expect(find.text('当前品牌尚未确认'), findsOneWidget);
    expect(find.text('当前经营主体尚未确认'), findsNothing);
    expect(find.textContaining('BrandFocus · cth-brand'), findsNothing);
    expect(find.byTooltip('查看经营主体目录'), findsNothing);
    expect(find.text('Core · 启动身份已读取'), findsNothing);
    expect(find.text('ACTIVE CONTEXT'), findsNothing);
    expect(find.text('TRUTH PATH'), findsNothing);
    expect(
      find.text('Source → Evidence → Canonical Data → Metric → View'),
      findsNothing,
    );
    expect(find.text('WORKSPACES'), findsNothing);
    expect(find.textContaining('PRODUCTION CORE'), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets('390 phone shell hides the CTH directory in BMP without logout', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(_app());
    await tester.pumpAndSettle();
    await tester.tap(find.text('品牌'));
    await tester.pumpAndSettle();

    final startupIdentity = find.byTooltip('服务已连接');
    expect(startupIdentity, findsOneWidget);
    final indicator = tester.widget<Icon>(
      find.descendant(of: startupIdentity, matching: find.byIcon(Icons.circle)),
    );
    expect(indicator.color, LumenisTheme.quiet);
    expect(find.text('当前品牌尚未确认'), findsOneWidget);
    expect(find.textContaining('BrandFocus · cth-brand'), findsNothing);
    expect(find.byTooltip('查看经营主体目录'), findsNothing);
    expect(find.byTooltip('退出登录'), findsNothing);
    expect(find.text('登录'), findsNothing);
    expect(find.byType(NavigationDestination), findsNWidgets(5));
    expect(find.text('Core · 启动身份已读取'), findsNothing);
    expect(find.text('PRODUCTION CORE'), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets('wide Context Inspector reports product, not false BrandFocus', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1720, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(_app());
    await tester.pumpAndSettle();
    await tester.tap(find.text('品牌市场'));
    await tester.pumpAndSettle();

    expect(find.text('当前品牌尚未确认'), findsNWidgets(2));
    expect(find.text('产品：CTH'), findsOneWidget);
    expect(find.text('当前工作对象'), findsOneWidget);
    expect(find.text('Core product · CTH'), findsNothing);
    expect(find.textContaining('BrandFocus · cth-brand'), findsNothing);
    expect(find.textContaining('REGISTERED SUBJECTS'), findsNothing);
    expect(find.text('TRUTH PATH'), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets('BMP context shows BMP and keeps the selected brand visible', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1720, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      _app(
        runtime: const {
          'ok': true,
          'domain': 'zbmp',
          'subject': {'brand_key': 'BMP-BRAND-7', 'product': 'ZBMP'},
        },
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.text('品牌市场'));
    await tester.pumpAndSettle();

    expect(find.text('当前品牌：BMP-BRAND-7'), findsNWidgets(2));
    expect(find.text('产品：BMP'), findsOneWidget);
    expect(find.text('服务已连接'), findsOneWidget);
    expect(find.textContaining('ZBMP'), findsNothing);
    expect(find.text('当前 BrandFocus 尚未确认'), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets('shell uses user copy for an unavailable subject directory', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1720, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      _app(
        subjects: const [],
        subjectDirectoryMessage: 'Core returned an invalid registry contract.',
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('经营主体列表暂不可用。请打开经营主体目录查看详情。'), findsOneWidget);
    expect(
      find.text('Core returned an invalid registry contract.'),
      findsNothing,
    );
    expect(tester.takeException(), isNull);
  });

  testWidgets('shell keeps connection status readable when not confirmed', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      _app(runtime: const {'ok': false, 'domain': 'cth', 'subject': {}}),
    );
    await tester.pumpAndSettle();

    expect(find.text('连接状态待确认'), findsOneWidget);
    expect(find.text('Core · 启动身份未确认'), findsNothing);
    expect(tester.takeException(), isNull);
  });
}

Widget _app({
  Map<String, dynamic>? runtime,
  List<Map<String, dynamic>>? subjects,
  String? subjectDirectoryMessage,
}) => MaterialApp(
  theme: LumenisTheme.dark,
  home: LumenisWorkspaceShell(
    client: _ShellClient(),
    runtime:
        runtime ??
        const {
          'ok': true,
          'domain': 'cth',
          'subject': {
            'subject_id': 'CTH-SUBJECT-7',
            'brand_key': 'cth-brand',
            'product': 'CTH',
          },
        },
    subjects:
        subjects ??
        const [
          {'subject_id': 'CTH-SUBJECT-7', 'name': 'CTH test subject'},
        ],
    subjectDirectoryMessage: subjectDirectoryMessage,
  ),
);

class _ShellClient extends LumenisCoreClient {
  @override
  Future<Map<String, dynamic>> runtimeIdentity() async => const {
    'ok': true,
    'domain': 'cth',
    'subject': {
      'subject_id': 'CTH-SUBJECT-7',
      'brand_key': 'cth-brand',
      'product': 'CTH',
    },
  };

  @override
  Future<Map<String, dynamic>> screen(String screenId) async => {
    'ok': true,
    'screen': screenId,
    'bound': true,
    'generated_at': '2026-09-20T10:00:00',
    'sections': const [],
    'truth': const {},
  };

  @override
  Future<Map<String, dynamic>> settingsSubjects() async => const {
    'ok': true,
    'source': 'lumenis_subject_registry',
    'selection_only': true,
    'domains': [
      {'id': 'CTH', 'name': '商业运营', 'product': 'CTH'},
    ],
    'subjects': [
      {
        'subject_id': 'CTH-TEST-01',
        'domain_id': 'CTH',
        'name_zh': 'CTH 测试主体',
        'subject_type_name': '商业主体',
        'industry': '测试行业',
      },
    ],
  };
}
