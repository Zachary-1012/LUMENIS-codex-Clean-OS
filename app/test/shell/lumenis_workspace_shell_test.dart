import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/core/lumenis_theme.dart';
import 'package:lumenis_app/features/account/acc03/acc03_screen.dart';
import 'package:lumenis_app/features/cth/cth01/cth01_screen.dart';
import 'package:lumenis_app/features/ai04/ai04_screen.dart';
import 'package:lumenis_app/l10n/lumenis_localizations.dart';
import 'package:lumenis_app/navigation/lumenis_workspace_routes.dart';
import 'package:lumenis_app/shell/lumenis_workspace_shell.dart';

void main() {
  test('all non-desktop Screen IDs have one unique concrete screen widget', () {
    final client = _ShellClient();
    final widgets = {
      for (final screenId in LumenisWorkspaceRoutes.workspaceScreenIds)
        screenId: buildLumenisWorkspaceScreen(
          screenId: screenId,
          client: client,
        ),
    };

    expect(widgets, hasLength(43));
    expect(
      widgets.values.map((widget) => widget.runtimeType).toSet(),
      hasLength(43),
    );
    for (final widget in widgets.values) {
      expect((widget as dynamic).client, same(client));
    }
    expect(
      () => buildLumenisWorkspaceScreen(screenId: 'SYS-06', client: client),
      throwsArgumentError,
    );
  });

  testWidgets('grouped secondary navigation selects a screen and reports it', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1280, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final selected = <String>[];

    await tester.pumpWidget(
      _app(
        _ShellClient(),
        initialScreenId: 'AI-01',
        onScreenSelected: selected.add,
      ),
    );
    await tester.pumpAndSettle();

    expect(
      find.byKey(const ValueKey('workspace-secondary-AI')),
      findsOneWidget,
    );
    await tester.tap(find.text('能力与服务'));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('workspace-nav-AI-04')));
    await tester.pumpAndSettle();

    expect(selected, ['AI-04']);
    expect(find.byType(Ai04Screen), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('desktop shell keeps the business directory nested in CTH', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final client = _ShellClient();

    await tester.pumpWidget(_app(client));
    await tester.pumpAndSettle();

    expect(find.text('全部可访问范围'), findsOneWidget);
    await tester.tap(find.byTooltip('查看经营主体目录'));
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('cth02/desktop-layout')), findsOneWidget);
    expect(find.byTooltip('返回商业运营总览'), findsOneWidget);
    expect(find.text('INTERNAL-SUBJECT-ID'), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets('mobile keeps five surfaces and exposes scope selection', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(_app(_ShellClient()));
    await tester.pumpAndSettle();

    expect(find.byType(NavigationDestination), findsNWidgets(5));
    expect(find.byTooltip('选择查看范围'), findsOneWidget);
    expect(find.text('全部可访问范围'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('subject selection and clearing use server-confirmed context', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final client = _ShellClient();

    await tester.pumpWidget(_app(client));
    await tester.pumpAndSettle();
    await tester.tap(find.byTooltip('选择查看范围'));
    await tester.pumpAndSettle(const Duration(milliseconds: 100));
    await tester.pump(const Duration(milliseconds: 250));

    expect(find.text('示例商业主体'), findsOneWidget);
    expect(find.text('INTERNAL-SUBJECT-ID'), findsNothing);
    await tester.tap(find.text('示例商业主体'));
    await tester.pumpAndSettle();

    expect(client.lastSelectedDomain, 'CTH');
    expect(client.lastSelectedSubject, 'INTERNAL-SUBJECT-ID');
    expect(find.text('示例商业主体'), findsOneWidget);
    expect(find.text('INTERNAL-SUBJECT-ID'), findsNothing);

    await tester.tap(find.byTooltip('选择查看范围'));
    await tester.pumpAndSettle();
    final clearButton = find.widgetWithText(TextButton, '全部可访问范围');
    expect(clearButton, findsOneWidget);
    await tester.tap(clearButton);
    await tester.pumpAndSettle();
    expect(find.text('全部可访问范围'), findsOneWidget);
    expect(client.clearCalls, 1);
    expect(tester.takeException(), isNull);
  });

  testWidgets('stale CTH and BMP focus can recover only through server clear', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    for (final domain in const ['CTH', 'BMP']) {
      final name = domain == 'BMP' ? '示例品牌' : '示例商业主体';
      final client = _ShellClient(
        envelope: _focusEnvelope(
          domain: domain,
          subjectId: domain == 'BMP'
              ? 'INTERNAL-BRAND-ID'
              : 'INTERNAL-SUBJECT-ID',
          nameZh: name,
          nameEn: domain == 'BMP' ? 'Example Brand' : 'Example Business',
        ),
        settingsContextError: const LumenisCoreException(
          'subject missing',
          statusCode: 404,
          messageKey: 'context.error.subject_unavailable',
        ),
      );

      await tester.pumpWidget(_app(client));
      await tester.pumpAndSettle();
      await tester.tap(find.byTooltip('选择查看范围'));
      await tester.pumpAndSettle();

      expect(
        find.byKey(const ValueKey('context-picker-return-global')),
        findsOneWidget,
      );
      expect(find.text(name), findsNothing);
      expect(client.subjectReads, 0);

      await tester.tap(
        find.byKey(const ValueKey('context-picker-return-global')),
      );
      await tester.pumpAndSettle();

      expect(client.clearCalls, 1);
      expect(client.envelope['context']['mode'], 'GLOBAL_ALL');
      expect(find.text('全部可访问范围'), findsOneWidget);
      expect(tester.takeException(), isNull);
      await tester.pumpWidget(const SizedBox.shrink());
      await tester.pumpAndSettle();
    }
  });

  testWidgets('denied stale-focus clear stays unavailable and offers retry', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final client = _ShellClient(
      envelope: _focusEnvelope(
        domain: 'CTH',
        subjectId: 'INTERNAL-SUBJECT-ID',
        nameZh: '示例商业主体',
        nameEn: 'Example Business',
      ),
      settingsContextError: const LumenisCoreException(
        'subject missing',
        statusCode: 404,
        messageKey: 'context.error.subject_unavailable',
      ),
      clearContextError: const LumenisCoreException(
        'permission denied',
        statusCode: 403,
        messageKey: 'context.error.permission_denied',
      ),
    );

    await tester.pumpWidget(_app(client));
    await tester.pumpAndSettle();
    await tester.tap(find.byTooltip('选择查看范围'));
    await tester.pumpAndSettle();
    await tester.tap(
      find.byKey(const ValueKey('context-picker-return-global')),
    );
    await tester.pumpAndSettle();

    expect(client.clearCalls, 1);
    expect(client.envelope['context']['mode'], 'FOCUS');
    expect(
      find.byKey(const ValueKey('context-picker-return-global')),
      findsOneWidget,
    );
    expect(find.text('示例商业主体'), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'context read failure without a confirmed focus has no clear action',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(390, 844));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      final client = _ShellClient(
        hasConfirmedContext: false,
        settingsContextError: const LumenisCoreException(
          'context unavailable',
          statusCode: 503,
          messageKey: 'context.error.unavailable',
        ),
      );

      await tester.pumpWidget(_app(client));
      await tester.pumpAndSettle();
      await tester.tap(find.byTooltip('选择查看范围'));
      await tester.pumpAndSettle();

      expect(
        find.byKey(const ValueKey('context-picker-return-global')),
        findsNothing,
      );
      expect(find.text('示例商业主体'), findsNothing);
      expect(client.subjectReads, 0);
      expect(client.clearCalls, 0);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('stale-focus recovery disables clear and retry while pending', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final clearGate = Completer<Map<String, dynamic>>();
    final client = _ShellClient(
      envelope: _focusEnvelope(
        domain: 'CTH',
        subjectId: 'INTERNAL-SUBJECT-ID',
        nameZh: '示例商业主体',
        nameEn: 'Example Business',
      ),
      settingsContextError: const LumenisCoreException(
        'subject missing',
        statusCode: 404,
        messageKey: 'context.error.subject_unavailable',
      ),
      clearContextGate: clearGate.future,
    );

    await tester.pumpWidget(_app(client));
    await tester.pumpAndSettle();
    await tester.tap(find.byTooltip('选择查看范围'));
    await tester.pumpAndSettle();
    final recovery = find.byKey(const ValueKey('context-picker-return-global'));
    await tester.tap(recovery);
    await tester.pump();

    expect(client.clearCalls, 1);
    expect(tester.widget<TextButton>(recovery).onPressed, isNull);
    final retry = find.byKey(const ValueKey('context-picker-retry'));
    expect(retry, findsOneWidget);
    expect(tester.widget<TextButton>(retry).onPressed, isNull);

    clearGate.complete(_globalEnvelope);
    await tester.pumpAndSettle();
    expect(client.envelope['context']['mode'], 'GLOBAL_ALL');
    expect(recovery, findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'late context failure after closing picker does not erase scope',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(390, 844));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      final contextGate = Completer<Map<String, dynamic>>();
      final client = _ShellClient(
        envelope: _focusEnvelope(
          domain: 'CTH',
          subjectId: 'INTERNAL-SUBJECT-ID',
          nameZh: '已确认主体',
          nameEn: 'Confirmed Subject',
        ),
        settingsContextGate: contextGate.future,
      );

      await tester.pumpWidget(_app(client));
      await tester.pumpAndSettle();
      await tester.tap(find.byTooltip('选择查看范围'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 400));
      await tester.tap(find.byKey(const ValueKey('context-picker-close')));
      await tester.pumpAndSettle();

      contextGate.completeError(
        const LumenisCoreException(
          'context unavailable',
          statusCode: 503,
          messageKey: 'context.error.unavailable',
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('已确认主体'), findsOneWidget);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('repeated failed reads keep the original stale scope blocked', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 960));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final client = _ShellClient(
      envelope: _focusEnvelope(
        domain: 'CTH',
        subjectId: 'STALE-SUBJECT',
        nameZh: '旧查看范围',
        nameEn: 'Old scope',
      ),
      settingsContextError: const LumenisCoreException(
        'context unavailable',
        statusCode: 404,
        messageKey: 'context.error.subject_unavailable',
      ),
    );

    await tester.pumpWidget(_app(client));
    await tester.pumpAndSettle();
    for (var attempt = 0; attempt < 2; attempt++) {
      await tester.tap(find.byTooltip('选择查看范围'));
      await tester.pumpAndSettle();
      expect(
        find.byKey(const ValueKey('context-picker-return-global')),
        findsOneWidget,
      );
      await tester.tap(find.byKey(const ValueKey('context-picker-close')));
      await tester.pumpAndSettle();
    }

    await tester.tap(find.text('工作助手'));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('workspace-nav-AI-01')));
    await tester.pumpAndSettle();

    expect(find.text('查看范围暂不可用'), findsOneWidget);
    expect(find.text('旧查看范围'), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'new ACC-02 confirmation restores shell scope after failed read',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(1440, 960));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      final client = _ShellClient(
        envelope: _focusEnvelope(
          domain: 'CTH',
          subjectId: 'STALE-SUBJECT',
          nameZh: '旧查看范围',
          nameEn: 'Old scope',
        ),
        settingsContextError: const LumenisCoreException(
          'context unavailable',
          statusCode: 404,
          messageKey: 'context.error.subject_unavailable',
        ),
        settingsContextErrorCount: 2,
      );

      await tester.pumpWidget(_app(client, initialScreenId: 'ACC-02'));
      await tester.pumpAndSettle();
      await tester.tap(find.byTooltip('选择查看范围'));
      await tester.pumpAndSettle();
      expect(
        find.byKey(const ValueKey('context-picker-return-global')),
        findsOneWidget,
      );
      await tester.tap(find.byKey(const ValueKey('context-picker-close')));
      await tester.pumpAndSettle();

      await tester.tap(find.text('示例商业主体').last);
      await tester.pumpAndSettle();
      await tester.tap(find.widgetWithText(FilledButton, '设为当前范围'));
      await tester.pumpAndSettle();
      await tester.tap(find.widgetWithText(OutlinedButton, '继续'));
      await tester.pumpAndSettle();

      expect(find.byType(Acc03Screen), findsOneWidget);
      expect(find.text('示例商业主体'), findsOneWidget);
      expect(find.text('旧查看范围'), findsNothing);
      expect(client.lastSelectedSubject, 'INTERNAL-SUBJECT-ID');
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets(
    'BMP focus displays its official name, never runtime identifiers',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(1720, 1000));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      final client = _ShellClient(
        envelope: _focusEnvelope(
          domain: 'BMP',
          subjectId: 'INTERNAL-BRAND-ID',
          nameZh: '示例品牌',
          nameEn: 'Example Brand',
        ),
      );

      await tester.pumpWidget(
        _app(client, locale: const Locale('en'), runtime: _legacyRuntime),
      );
      await tester.pumpAndSettle();
      await tester.tap(find.text('Brand & Market').first);
      await tester.pumpAndSettle();

      expect(find.text('Example Brand'), findsNWidgets(2));
      expect(find.text('INTERNAL-BRAND-ID'), findsNothing);
      expect(find.text('LEGACY-INTERNAL-KEY'), findsNothing);
      expect(find.text('FOCUSED SCOPE'), findsNothing);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('Korean copy remains available and hides machine context keys', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1280, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(_app(_ShellClient(), locale: const Locale('ko')));
    await tester.pumpAndSettle();

    expect(find.text('접근 가능한 전체 범위'), findsOneWidget);
    expect(find.textContaining('GLOBAL_ALL'), findsNothing);
    expect(find.textContaining('CTH'), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'confirmed account selection reaches the map and workspace header',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(1440, 960));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      final client = _ShellClient();
      final selected = <String>[];
      await tester.pumpWidget(
        _app(client, initialScreenId: 'ACC-02', onScreenSelected: selected.add),
      );
      await tester.pumpAndSettle();
      await tester.tap(find.text('示例商业主体'));
      await tester.pumpAndSettle();
      final continueButton = find.widgetWithText(OutlinedButton, '继续');
      expect(tester.widget<OutlinedButton>(continueButton).onPressed, isNull);
      await tester.tap(find.widgetWithText(FilledButton, '设为当前范围'));
      await tester.pumpAndSettle();
      await tester.tap(continueButton);
      await tester.pumpAndSettle();
      expect(find.byType(Acc03Screen), findsOneWidget);
      expect(find.text('全部可访问范围'), findsNothing);
      expect(find.text('示例商业主体'), findsOneWidget);
      await tester.tap(find.widgetWithText(OutlinedButton, '继续').first);
      await tester.pumpAndSettle();
      expect(find.byType(Cth01Screen), findsOneWidget);
      expect(find.text('示例商业主体'), findsOneWidget);
      expect(selected, ['ACC-03', 'CTH-01']);
      expect(client.lastSelectedSubject, 'INTERNAL-SUBJECT-ID');
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('runtime connection state stays honest', (tester) async {
    await tester.binding.setSurfaceSize(const Size(1440, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      _app(_ShellClient(), runtime: const {'ok': false, 'subject': {}}),
    );
    await tester.pumpAndSettle();

    expect(find.text('连接状态待确认'), findsOneWidget);
    expect(find.textContaining('Core ·'), findsNothing);
    expect(tester.takeException(), isNull);
  });
}

Widget _app(
  _ShellClient client, {
  Locale locale = const Locale('zh', 'CN'),
  Map<String, dynamic> runtime = _legacyRuntime,
  String initialScreenId = 'CTH-01',
  ValueChanged<String>? onScreenSelected,
}) => MaterialApp(
  locale: locale,
  theme: LumenisTheme.dark,
  supportedLocales: LumenisLocalizations.supportedLocales,
  localizationsDelegates: const [
    LumenisLocalizations.delegate,
    GlobalMaterialLocalizations.delegate,
    GlobalWidgetsLocalizations.delegate,
    GlobalCupertinoLocalizations.delegate,
  ],
  home: LumenisWorkspaceShell(
    client: client,
    runtime: runtime,
    contextEnvelope: client.shellEnvelope,
    subjects: const [],
    initialScreenId: initialScreenId,
    onScreenSelected: onScreenSelected,
  ),
);

const _legacyRuntime = {
  'ok': true,
  'domain': 'cth',
  'subject': {
    'subject_id': 'LEGACY-INTERNAL-KEY',
    'brand_key': 'legacy-brand',
    'product': 'CTH',
  },
};

class _ShellClient extends LumenisCoreClient {
  _ShellClient({
    Map<String, dynamic>? envelope,
    this.settingsContextError,
    this.settingsContextErrorCount,
    this.settingsContextGate,
    this.clearContextError,
    this.clearContextGate,
    this.hasConfirmedContext = true,
  }) : _envelope = envelope ?? _globalEnvelope;

  Map<String, dynamic> _envelope;
  final Object? settingsContextError;
  final int? settingsContextErrorCount;
  final Future<Map<String, dynamic>>? settingsContextGate;
  final Object? clearContextError;
  final Future<Map<String, dynamic>>? clearContextGate;
  bool hasConfirmedContext;
  String? lastSelectedDomain;
  String? lastSelectedSubject;
  int clearCalls = 0;
  int subjectReads = 0;
  int _settingsContextErrorsThrown = 0;

  Map<String, dynamic> get envelope => _envelope;
  Map<String, dynamic>? get shellEnvelope =>
      hasConfirmedContext ? _envelope : null;

  @override
  Map<String, dynamic>? get currentContextEnvelope => shellEnvelope;

  @override
  Future<Map<String, dynamic>> runtimeIdentity() async => _legacyRuntime;

  @override
  Future<Map<String, dynamic>> settingsContext() async {
    final gate = settingsContextGate;
    if (gate != null) return await gate;
    final error = settingsContextError;
    final errorCount = settingsContextErrorCount;
    if (error != null &&
        (errorCount == null || _settingsContextErrorsThrown < errorCount)) {
      _settingsContextErrorsThrown++;
      throw error;
    }
    hasConfirmedContext = true;
    return _envelope;
  }

  @override
  Future<Map<String, dynamic>> screen(String screenId) async => {
    'ok': true,
    'screen': screenId,
    'bound': false,
    'focus_binding': {
      'state': 'unavailable',
      'applied': false,
      'message_key': 'context.screen_binding_unavailable',
    },
    'generated_at': '2026-09-20T10:00:00',
    'sections': const [],
    'truth': const {},
  };

  @override
  Future<Map<String, dynamic>> settingsSubjects({
    String domainId = 'CTH',
  }) async {
    subjectReads++;
    return {
      'ok': true,
      'source': 'lumenis_subject_registry',
      'selection_only': true,
      'domains': [
        {
          'id': domainId,
          'name': domainId,
          'product': domainId == 'BMP' ? 'ZBMP' : 'CTH',
        },
      ],
      'subjects': [
        {
          'subject_id': domainId == 'BMP'
              ? 'INTERNAL-BRAND-ID'
              : 'INTERNAL-SUBJECT-ID',
          'domain_id': domainId,
          'name_zh': domainId == 'BMP' ? '示例品牌' : '示例商业主体',
          'name_en': domainId == 'BMP' ? 'Example Brand' : 'Example Business',
          'subject_type_name': domainId == 'BMP' ? '品牌主体' : '商业主体',
          'industry': '测试行业',
        },
      ],
    };
  }

  @override
  Future<Map<String, dynamic>> selectContext({
    required String domainId,
    required String subjectId,
  }) async {
    lastSelectedDomain = domainId;
    lastSelectedSubject = subjectId;
    _envelope = _focusEnvelope(
      domain: domainId,
      subjectId: subjectId,
      nameZh: domainId == 'BMP' ? '示例品牌' : '示例商业主体',
      nameEn: domainId == 'BMP' ? 'Example Brand' : 'Example Business',
    );
    hasConfirmedContext = true;
    return _envelope;
  }

  @override
  Future<Map<String, dynamic>> clearContext() async {
    clearCalls++;
    final error = clearContextError;
    if (error != null) throw error;
    _envelope = await (clearContextGate ?? Future.value(_globalEnvelope));
    hasConfirmedContext = true;
    return _envelope;
  }
}

Map<String, dynamic> _focusEnvelope({
  required String domain,
  required String subjectId,
  required String nameZh,
  required String nameEn,
}) => {
  'ok': true,
  'contract': 'lumenis.context.v1',
  'context': {
    'mode': 'FOCUS',
    'mode_label_key': 'context.mode.focus',
    'domain_id': domain,
    'product_id': domain == 'BMP' ? 'ZBMP' : 'CTH',
    'subject_id': subjectId,
    'subject_type': domain == 'BMP' ? 'brand' : 'company',
    'display_name': {'zh-CN': nameZh, 'en': nameEn},
    'display_state': 'available',
  },
  'authorized_domains': const [
    {'id': 'CTH', 'name': 'Business', 'product': 'CTH'},
    {'id': 'BMP', 'name': 'Brand', 'product': 'ZBMP'},
  ],
  'selection_only': true,
};

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
