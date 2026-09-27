import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/core/lumenis_theme.dart';
import 'package:lumenis_app/features/account/acc01/acc01_screen.dart';
import 'package:lumenis_app/features/account/acc03/acc03_screen.dart';
import 'package:lumenis_app/features/account/acc04/acc04_screen.dart';
import 'package:lumenis_app/features/ai01/ai01_screen.dart';
import 'package:lumenis_app/features/ai04/ai04_screen.dart';
import 'package:lumenis_app/features/bmp01/bmp01_screen.dart';
import 'package:lumenis_app/features/cth/cth01/cth01_screen.dart';
import 'package:lumenis_app/features/cth/cth02/cth02_screen.dart';
import 'package:lumenis_app/features/system/sys05/sys05_appearance_controller.dart';
import 'package:lumenis_app/features/system/sys06/sys06_screen.dart';
import 'package:lumenis_app/l10n/lumenis_localizations.dart';
import 'package:lumenis_app/navigation/lumenis_router.dart';
import 'package:lumenis_app/navigation/lumenis_workspace_routes.dart';

void main() {
  test('workflow regrouping preserves every legacy capability deep link', () {
    final grouped = LumenisWorkspaceRoutes.workflowsByGroup.values
        .expand((workflows) => workflows.values)
        .expand((screens) => screens)
        .toList();
    expect(grouped.toSet(), LumenisWorkspaceRoutes.screenIds);
    expect(grouped.length, grouped.toSet().length);
    for (final id in grouped) {
      expect(
        LumenisWorkspaceRoutes.workflowForScreen(id),
        startsWith('workflow.'),
      );
    }
  });

  test('legacy canonical IDs retain unique reachable workspace paths', () {
    expect(LumenisWorkspaceRoutes.screenIds, _canonicalScreenIds);
    expect(LumenisWorkspaceRoutes.screenIds, hasLength(44));
    expect(LumenisWorkspaceRoutes.workspaceScreenIds, hasLength(43));
    expect(LumenisWorkspaceRoutes.unavailableScreenIds, {'SYS-06'});
    expect(
      LumenisWorkspaceRoutes.workspaceScreenIds,
      isNot(contains('SYS-06')),
    );
    expect(
      LumenisWorkspaceRoutes.screenIdsByGroup.map(
        (group, screenIds) => MapEntry(group, screenIds.length),
      ),
      const {'ACC': 4, 'AI': 5, 'CTH': 10, 'BMP': 11, 'SH': 6, 'SYS': 8},
    );

    final paths = LumenisWorkspaceRoutes.screenIds
        .map(LumenisWorkspaceRoutes.pathForScreen)
        .toSet();
    expect(paths, hasLength(44));
    expect(LumenisWorkspaceRoutes.pathForScreen('CTH-01'), '/workspace/CTH-01');
    expect(
      LumenisWorkspaceRoutes.pathForScreen('CTH-02'),
      '/workspace/CTH-01/CTH-02',
    );
    expect(LumenisWorkspaceRoutes.pathForScreen('BMP-01'), '/workspace/BMP-01');
    expect(LumenisWorkspaceRoutes.pathForScreen('AI-01'), '/workspace/AI-01');
    expect(LumenisWorkspaceRoutes.pathForScreen('SH-01'), '/workspace/SH-01');
    expect(LumenisWorkspaceRoutes.pathForScreen('SYS-01'), '/workspace/SYS-01');
    expect(
      () => LumenisWorkspaceRoutes.pathForScreen('UNKNOWN-99'),
      throwsArgumentError,
    );
  });

  testWidgets(
    'deep links and incoming history locations select the shell page',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(1440, 960));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      final router = createLumenisRouter(
        client: _RouterClient(),
        onLocaleChanged: (_) {},
        initialLocation: LumenisWorkspaceRoutes.bmp01,
      );
      addTearDown(router.dispose);

      await tester.pumpWidget(_app(router));
      await tester.pumpAndSettle();
      expect(find.byType(Bmp01Screen), findsOneWidget);
      expect(
        router.routeInformationProvider.value.uri.path,
        LumenisWorkspaceRoutes.bmp01,
      );

      router.go(LumenisWorkspaceRoutes.cth02);
      await tester.pumpAndSettle();
      expect(find.byType(Cth02Screen), findsOneWidget);

      router.go(LumenisWorkspaceRoutes.ai01);
      await tester.pumpAndSettle();
      expect(find.byType(Ai01Screen), findsOneWidget);
      expect(
        router.routeInformationProvider.value.uri.path,
        LumenisWorkspaceRoutes.ai01,
      );
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('shell navigation updates the browser-facing URL', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 960));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final router = createLumenisRouter(
      client: _RouterClient(),
      onLocaleChanged: (_) {},
    );
    addTearDown(router.dispose);

    await tester.pumpWidget(_app(router));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('workspace-navigation-open')));
    await tester.pumpAndSettle();
    final aiDomain = find.byKey(const ValueKey('workspace-domain-AI'));
    await tester.ensureVisible(aiDomain);
    await tester.tap(aiDomain);
    await tester.pumpAndSettle();
    final aiEntry = find.byKey(const ValueKey('workspace-nav-AI-01'));
    await tester.ensureVisible(aiEntry);
    await tester.tap(aiEntry);
    await tester.pumpAndSettle();

    expect(
      router.routeInformationProvider.value.uri.path,
      LumenisWorkspaceRoutes.ai01,
    );
    expect(find.byType(Ai01Screen), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('workspace-navigation-open')));
    await tester.pumpAndSettle();
    final tools = find.byKey(
      const ValueKey('workflow-group-workflow.assist_tools'),
    );
    await tester.ensureVisible(tools);
    await tester.tap(tools);
    await tester.pumpAndSettle();
    final aiTools = find.byKey(const ValueKey('workspace-nav-AI-04'));
    await tester.ensureVisible(aiTools);
    await tester.tap(aiTools);
    await tester.pumpAndSettle();
    expect(router.routeInformationProvider.value.uri.path, '/workspace/AI-04');
    expect(find.byType(Ai04Screen), findsOneWidget);

    await tester.tap(
      find.byKey(const ValueKey('workspace-account-navigation')),
    );
    await tester.pumpAndSettle();
    expect(router.routeInformationProvider.value.uri.path, '/workspace/ACC-01');
    expect(find.byType(Acc01Screen), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('workspace-navigation-open')));
    await tester.pumpAndSettle();
    final accountHistory = find.byKey(const ValueKey('workspace-nav-ACC-04'));
    await tester.ensureVisible(accountHistory);
    await tester.tap(accountHistory);
    await tester.pumpAndSettle();
    expect(router.routeInformationProvider.value.uri.path, '/workspace/ACC-04');
    expect(find.byType(Acc04Screen), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  for (final width in [390.0, 1440.0]) {
    testWidgets('restricted scope keeps the launch map usable at $width', (
      tester,
    ) async {
      await tester.binding.setSurfaceSize(Size(width, 960));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      final router = createLumenisRouter(
        client: _RouterClient(denyContext: true),
        onLocaleChanged: (_) {},
        initialLocation: '/workspace/ACC-03',
      );
      addTearDown(router.dispose);
      await tester.pumpWidget(_app(router));
      await tester.pumpAndSettle();
      expect(find.text('访问受限'), findsOneWidget);
      expect(find.text('查看范围访问受限'), findsOneWidget);
      expect(find.text('全局查看范围（未命名）'), findsNothing);
      final aiEntry = find.widgetWithText(OutlinedButton, '继续').last;
      await tester.ensureVisible(aiEntry);
      await tester.tap(aiEntry);
      await tester.pumpAndSettle();
      expect(find.byType(Ai01Screen), findsOneWidget);
      expect(
        router.routeInformationProvider.value.uri.path,
        '/workspace/AI-01',
      );
      expect(tester.takeException(), isNull);
    });

    testWidgets(
      'unbound access guard can return without changing access at $width',
      (tester) async {
        await tester.binding.setSurfaceSize(Size(width, 960));
        addTearDown(() => tester.binding.setSurfaceSize(null));
        final router = createLumenisRouter(
          client: _RouterClient(),
          onLocaleChanged: (_) {},
          initialLocation: '/workspace/ACC-04',
        );
        addTearDown(router.dispose);
        await tester.pumpWidget(_app(router));
        await tester.pumpAndSettle();
        expect(find.byType(Acc04Screen), findsOneWidget);
        expect(find.text('切换查看范围'), findsNothing);
        final back = find.widgetWithText(TextButton, '返回');
        await tester.ensureVisible(back);
        await tester.tap(back);
        await tester.pumpAndSettle();
        expect(
          router.routeInformationProvider.value.uri.path,
          '/workspace/ACC-03',
        );
        expect(find.byType(Acc03Screen), findsOneWidget);
        expect(tester.takeException(), isNull);
      },
    );

    testWidgets('entry and launch map navigate and return at width $width', (
      tester,
    ) async {
      await tester.binding.setSurfaceSize(Size(width, 960));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      final router = createLumenisRouter(
        client: _RouterClient(),
        onLocaleChanged: (_) {},
        initialLocation: '/workspace/ACC-01',
      );
      addTearDown(router.dispose);
      await tester.pumpWidget(_app(router));
      await tester.pumpAndSettle();
      final enter = find.widgetWithText(FilledButton, '进入工作区');
      await tester.ensureVisible(enter);
      await tester.tap(enter);
      await tester.pumpAndSettle();
      expect(
        router.routeInformationProvider.value.uri.path,
        '/workspace/ACC-03',
      );
      expect(find.byType(Acc03Screen), findsOneWidget);

      final destinations = [
        ('/workspace/CTH-01', Cth01Screen),
        ('/workspace/BMP-01', Bmp01Screen),
        ('/workspace/AI-01', Ai01Screen),
      ];
      for (var index = 0; index < destinations.length; index++) {
        if (index > 0) {
          if (width < 768) {
            await tester.tap(
              find.byKey(const ValueKey('workspace-phone-tools')),
            );
            await tester.pumpAndSettle();
          }
          await tester.tap(
            find.byKey(const ValueKey('workspace-account-navigation')),
          );
          await tester.pumpAndSettle();
          await tester.ensureVisible(enter);
          await tester.tap(enter);
          await tester.pumpAndSettle();
        }
        final open = find.widgetWithText(OutlinedButton, '继续').at(index);
        await tester.ensureVisible(open);
        await tester.tap(open);
        await tester.pumpAndSettle();
        expect(
          router.routeInformationProvider.value.uri.path,
          destinations[index].$1,
        );
        expect(find.byType(destinations[index].$2), findsOneWidget);
        expect(tester.takeException(), isNull);
      }
    });
  }

  testWidgets(
    'SYS-06 shows the truthful unavailable boundary on phone and PC',
    (tester) async {
      addTearDown(() => tester.binding.setSurfaceSize(null));
      for (final size in const [Size(390, 844), Size(1440, 960)]) {
        await tester.binding.setSurfaceSize(size);
        final router = createLumenisRouter(
          client: _RouterClient(),
          onLocaleChanged: (_) {},
          initialLocation: LumenisWorkspaceRoutes.pathForScreen('SYS-06'),
        );

        await tester.pumpWidget(_app(router));
        await tester.pumpAndSettle();

        expect(find.text('内置浏览暂不可用'), findsOneWidget);
        expect(find.text('当前工作区尚未接通浏览页面。你可以返回继续原来的工作。'), findsOneWidget);
        expect(find.byType(Sys06Screen), findsNothing);
        expect(tester.takeException(), isNull);

        await tester.pumpWidget(const SizedBox.shrink());
        router.dispose();
      }
    },
  );

  testWidgets('unknown IDs fail safely without querying Product Core', (
    tester,
  ) async {
    final client = _RouterClient();
    final router = createLumenisRouter(
      client: client,
      onLocaleChanged: (_) {},
      initialLocation: '/workspace/UNKNOWN-99',
    );
    addTearDown(router.dispose);

    await tester.pumpWidget(_app(router));
    await tester.pumpAndSettle();

    expect(find.text('无法打开该工作区页面'), findsOneWidget);
    expect(find.text('返回工作区'), findsOneWidget);
    expect(find.byType(Cth01Screen), findsNothing);
    expect(client.runtimeIdentityCalls, 0);
    expect(tester.takeException(), isNull);
  });

  testWidgets('a direct SYS-06 link returns to the workspace root', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final client = _RouterClient();
    final router = createLumenisRouter(
      client: client,
      onLocaleChanged: (_) {},
      initialLocation: LumenisWorkspaceRoutes.pathForScreen('SYS-06'),
    );
    addTearDown(router.dispose);

    await tester.pumpWidget(_app(router));
    await tester.pumpAndSettle();

    expect(find.text('内置浏览暂不可用'), findsOneWidget);
    expect(find.byType(Sys06Screen), findsNothing);
    expect(client.runtimeIdentityCalls, 0);

    await tester.tap(find.widgetWithText(OutlinedButton, '返回工作区'));
    await tester.pumpAndSettle();

    expect(
      router.routerDelegate.currentConfiguration.uri.path,
      LumenisWorkspaceRoutes.root,
    );
    expect(tester.takeException(), isNull);
  });

  testWidgets('SYS-05 un-applied local editor input survives SYS-06 return', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 960));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final appearance = Sys05AppearanceController()
      ..loaded = true
      ..mode = WorkspaceBackdrop.solid;
    final router = createLumenisRouter(
      client: _RouterClient(),
      onLocaleChanged: (_) {},
      initialLocation: LumenisWorkspaceRoutes.pathForScreen('SYS-05'),
    );

    await tester.pumpWidget(_app(router, appearanceController: appearance));
    await tester.pumpAndSettle();
    final hexField = find.byKey(const ValueKey('appearance/hex'));
    expect(hexField, findsOneWidget);
    await tester.enterText(hexField, 'A1F');
    expect(
      tester
          .widget<EditableText>(
            find.descendant(of: hexField, matching: find.byType(EditableText)),
          )
          .focusNode
          .hasFocus,
      isTrue,
    );

    await tester.tap(find.byKey(const ValueKey('workspace-navigation-open')));
    await tester.pumpAndSettle();
    final operationsGroup = find.byKey(
      const ValueKey('workflow-group-workflow.operations'),
    );
    await tester.ensureVisible(operationsGroup);
    await tester.tap(operationsGroup);
    await tester.pumpAndSettle();
    final sys06Navigation = find.byKey(const ValueKey('workspace-nav-SYS-06'));
    await tester.ensureVisible(sys06Navigation);
    await tester.tap(sys06Navigation);
    await tester.pumpAndSettle();

    expect(
      GoRouterState.of(
        tester.element(find.byType(LumenisRouteBoundary)),
      ).uri.path,
      LumenisWorkspaceRoutes.pathForScreen('SYS-06'),
    );
    expect(find.text('内置浏览暂不可用'), findsOneWidget);
    expect(find.byType(Sys06Screen), findsNothing);

    await tester.tap(find.widgetWithText(OutlinedButton, '返回工作区'));
    await tester.pumpAndSettle();

    expect(
      router.routerDelegate.currentConfiguration.uri.path,
      LumenisWorkspaceRoutes.pathForScreen('SYS-05'),
    );
    expect(tester.widget<TextField>(hexField).controller!.text, 'A1F');
    expect(appearance.solidColor, const Color(0xFFE8E4EC));
    expect(
      tester
          .widget<EditableText>(
            find.descendant(of: hexField, matching: find.byType(EditableText)),
          )
          .focusNode
          .hasFocus,
      isTrue,
    );
    expect(tester.takeException(), isNull);

    await tester.pumpWidget(const SizedBox.shrink());
    router.dispose();
    appearance.dispose();
  });

  testWidgets('browser boundary scrolls to Return at 320px and 200% text', (
    tester,
  ) async {
    tester.view.devicePixelRatio = 1;
    tester.view.physicalSize = const Size(320, 420);
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final router = createLumenisRouter(
      client: _RouterClient(),
      onLocaleChanged: (_) {},
      initialLocation: LumenisWorkspaceRoutes.pathForScreen('SYS-06'),
    );
    addTearDown(router.dispose);

    await tester.pumpWidget(_app(router, textScaler: TextScaler.linear(2)));
    await tester.pumpAndSettle();

    final returnButton = find.widgetWithText(OutlinedButton, '返回工作区');
    expect(
      find.byKey(const ValueKey('workspace-route-boundary-scroll')),
      findsOneWidget,
    );
    expect(tester.getRect(returnButton).bottom, greaterThan(420));
    await tester.ensureVisible(returnButton);
    await tester.pumpAndSettle();

    expect(tester.getRect(returnButton).bottom, lessThanOrEqualTo(420));
    expect(tester.takeException(), isNull);
  });
}

const _canonicalScreenIds = <String>{
  'ACC-01',
  'ACC-02',
  'ACC-03',
  'ACC-04',
  'AI-01',
  'AI-02',
  'AI-03',
  'AI-04',
  'AI-05',
  'CTH-01',
  'CTH-02',
  'CTH-03',
  'CTH-04',
  'CTH-05',
  'CTH-06',
  'CTH-07',
  'CTH-08',
  'CTH-09',
  'CTH-10',
  'BMP-01',
  'BMP-02',
  'BMP-03',
  'BMP-04',
  'BMP-05',
  'BMP-06',
  'BMP-07',
  'BMP-08',
  'BMP-09',
  'BMP-10',
  'BMP-11',
  'SH-01',
  'SH-02',
  'SH-03',
  'SH-04',
  'SH-05',
  'SH-06',
  'SYS-01',
  'SYS-02',
  'SYS-03',
  'SYS-04',
  'SYS-05',
  'SYS-06',
  'SYS-07',
  'SYS-08',
};

Widget _app(
  GoRouter router, {
  Sys05AppearanceController? appearanceController,
  TextScaler? textScaler,
}) => MaterialApp.router(
  routerConfig: router,
  locale: const Locale('zh', 'CN'),
  theme: LumenisTheme.dark,
  builder: (context, child) {
    Widget result = child ?? const SizedBox.shrink();
    if (appearanceController != null) {
      result = Sys05AppearanceScope(
        controller: appearanceController,
        child: result,
      );
    }
    if (textScaler != null) {
      result = MediaQuery(
        data: MediaQuery.of(context).copyWith(textScaler: textScaler),
        child: result,
      );
    }
    return result;
  },
  supportedLocales: LumenisLocalizations.supportedLocales,
  localizationsDelegates: const [
    LumenisLocalizations.delegate,
    GlobalMaterialLocalizations.delegate,
    GlobalWidgetsLocalizations.delegate,
    GlobalCupertinoLocalizations.delegate,
  ],
);

class _RouterClient extends LumenisCoreClient {
  _RouterClient({this.denyContext = false});
  final bool denyContext;
  int runtimeIdentityCalls = 0;

  @override
  Future<Map<String, dynamic>> runtimeIdentity() async {
    runtimeIdentityCalls += 1;
    return const {'ok': true, 'app': 'LUMENIS Core'};
  }

  @override
  Future<Map<String, dynamic>> settingsContext() async {
    if (denyContext) {
      throw const LumenisCoreException('context denied', statusCode: 403);
    }
    return _globalEnvelope;
  }

  @override
  Future<Map<String, dynamic>> screen(String screenId) async => {
    'ok': true,
    'screen': screenId,
    'bound': false,
    'focus_binding': const {
      'state': 'unavailable',
      'applied': false,
      'message_key': 'context.screen_binding_unavailable',
    },
    'generated_at': '2026-09-22T00:00:00Z',
    'sections': const [],
    'truth': const {},
  };

  @override
  Future<Map<String, dynamic>> settingsSubjects({
    String domainId = 'CTH',
  }) async => {
    'ok': true,
    'source': 'lumenis_subject_registry',
    'selection_only': true,
    'domains': [
      {'id': domainId, 'product': domainId == 'BMP' ? 'ZBMP' : 'CTH'},
    ],
    'subjects': const [],
  };
}

const _globalEnvelope = {
  'ok': true,
  'contract': 'lumenis.context.v1',
  'context': {
    'mode': 'GLOBAL_ALL',
    'mode_label_key': 'context.mode.global_all',
    'domain_id': null,
    'product_id': null,
    'subject_id': null,
    'subject_type': null,
    'display_name': null,
    'display_state': 'not_applicable',
  },
  'authorized_domains': [
    {'id': 'CTH', 'name': 'Business', 'product': 'CTH'},
    {'id': 'BMP', 'name': 'Brand', 'product': 'ZBMP'},
  ],
  'selection_only': true,
};
