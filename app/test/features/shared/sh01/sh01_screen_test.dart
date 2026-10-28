import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/core/lumenis_theme.dart';
import 'package:lumenis_app/l10n/lumenis_localizations.dart';
import 'package:lumenis_app/features/shared/sh01/sh01_repository.dart';
import 'package:lumenis_app/features/shared/sh01/sh01_screen.dart';
import 'package:lumenis_app/features/shared/sh01/sh01_snapshot.dart';
import 'package:lumenis_app/features/shared/sh01/media_project_workbench.dart';
import 'package:lumenis_app/features/shared/sh01/manuscript_editor.dart';

void main() {
  testWidgets('new manuscript starts in independent Shared scope', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final client = _CatalogOnlyClient()
      ..contextEnvelope = {
        'contract': 'lumenis.context.v1',
        'selection_only': true,
        'context': {
          'mode': 'FOCUS',
          'domain_id': 'BMP',
          'brand_focus_id': 'brand-a',
        },
      };
    await tester.pumpWidget(
      _app(_FakeSh01Repository(_catalog), client: client),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('sh01-create-manuscript')));
    await tester.pumpAndSettle();

    final editor = tester.widget<ManuscriptEditor>(
      find.byType(ManuscriptEditor),
    );
    expect(editor.invokingDomain, isNull);
    expect(client.currentContextEnvelope!['context']['domain_id'], 'BMP');
    expect(find.byKey(const Key('manuscript-title')), findsOneWidget);
    expect(find.byKey(const Key('manuscript-summary')), findsOneWidget);
    expect(find.byKey(const Key('sh01-open-video-editor')), findsNothing);
    await tester.enterText(find.byKey(const Key('manuscript-title')), '独立提案');
    await tester.enterText(
      find.byKey(const Key('manuscript-summary')),
      '从用户自己的内容开始。',
    );
    await tester.enterText(find.byKey(const Key('manuscript-heading-0')), '方向');
    await tester.enterText(
      find.byKey(const Key('manuscript-body-0')),
      '先明确目标与受众。',
    );
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('manuscript-save')));
    await tester.pumpAndSettle();
    expect(client.manuscriptScope, isA<SharedWorkspaceScope>());
    expect(find.textContaining('文稿仍保留'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'Shared creation opens independently even with an existing business focus',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(1440, 1000));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      final client = _CatalogOnlyClient()
        ..contextEnvelope = {
          'contract': 'lumenis.context.v1',
          'selection_only': true,
          'context': {
            'mode': 'FOCUS',
            'domain_id': 'BMP',
            'subject_id': 'brand-a',
          },
        };
      await tester.pumpWidget(
        _app(CoreSh01Repository(client: client), client: client),
      );
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('sh01-open-video-editor')));
      await tester.pumpAndSettle();
      final editor = tester.widget<MediaProjectWorkbench>(
        find.byType(MediaProjectWorkbench),
      );
      expect(editor.sharedWorkspace, isTrue);
      expect(editor.invokingDomain, isNull);
      expect(find.text('独立作品'), findsOneWidget);
      expect(find.byKey(const Key('media-import')), findsOneWidget);
      expect(find.byKey(const Key('media-domain-bmp')), findsNothing);
      expect(client.contextEnvelope!['context']['domain_id'], 'BMP');
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('Shared entry retains the separate business-linked media path', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final client = _CatalogOnlyClient()
      ..contextEnvelope = {
        'contract': 'lumenis.context.v1',
        'selection_only': true,
        'context': {
          'mode': 'FOCUS',
          'domain_id': 'CTH',
          'subject_id': 'shop-1',
        },
      };
    await tester.pumpWidget(
      _app(CoreSh01Repository(client: client), client: client),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('sh01-open-linked-media')));
    await tester.pumpAndSettle();
    final editor = tester.widget<MediaProjectWorkbench>(
      find.byType(MediaProjectWorkbench),
    );
    expect(editor.sharedWorkspace, isFalse);
    expect(find.text('商业运营'), findsOneWidget);
    expect(find.byKey(const Key('media-import')), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('podcast media entry selects the existing audio export mode', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final client = _CatalogOnlyClient();
    await tester.pumpWidget(
      _app(
        _FakeSh01Repository(_catalog),
        client: client,
        initialWorkspaceEntry: 'media',
        returnScreenId: 'BMP-08',
      ),
    );
    await tester.pumpAndSettle();

    final workbench = tester.widget<MediaProjectWorkbench>(
      find.byType(MediaProjectWorkbench),
    );
    expect(workbench.initialOutputKind, 'audio');
    expect(find.byKey(const Key('media-import')), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'creation entry offers independent podcast and defers catalog reads',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(1440, 1000));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      final client = _CatalogOnlyClient();
      await tester.pumpWidget(
        _app(CoreSh01Repository(client: client), client: client),
      );
      await tester.pumpAndSettle();
      expect(client.catalogCalls, 0);
      expect(client.screenCalls, 0);
      expect(find.text('继续工作'), findsOneWidget);
      expect(find.text('研究与创作工具'), findsNothing);
      await tester.tap(find.byKey(const Key('sh01-open-podcast-editor')));
      await tester.pumpAndSettle();
      final editor = tester.widget<MediaProjectWorkbench>(
        find.byType(MediaProjectWorkbench),
      );
      expect(editor.sharedWorkspace, isTrue);
      expect(editor.invokingDomain, isNull);
      expect(editor.initialOutputKind, 'audio');
      expect(find.text('播客编辑'), findsOneWidget);
      expect(find.text('视频剪辑'), findsNothing);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('research entry navigates to actual materials workspace', (
    tester,
  ) async {
    String? destination;
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(
      _app(
        _FakeSh01Repository(_catalog),
        onNavigate: (value) => destination = value,
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('sh01-open-research')));
    await tester.pumpAndSettle();
    expect(destination, 'SH-02');
    expect(tester.takeException(), isNull);
  });

  for (final locale in [
    const Locale('zh'),
    const Locale('en'),
    const Locale('ko'),
  ]) {
    testWidgets('creation actions remain reachable at 200 percent in $locale', (
      tester,
    ) async {
      await tester.binding.setSurfaceSize(const Size(390, 844));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      await tester.pumpWidget(
        _app(_FakeSh01Repository(_catalog), locale: locale, scale: 2),
      );
      await tester.pumpAndSettle();
      final podcast = find.byKey(const Key('sh01-open-podcast-editor'));
      await tester.ensureVisible(podcast);
      await tester.tap(podcast);
      await tester.pumpAndSettle();
      expect(
        tester
            .widget<MediaProjectWorkbench>(find.byType(MediaProjectWorkbench))
            .initialOutputKind,
        'audio',
      );
      expect(tester.takeException(), isNull);
    });
  }

  testWidgets('desktop browses shared catalog and blocks unscoped Evidence', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final client = _CatalogOnlyClient();
    final repository = CoreSh01Repository(client: client);

    await tester.pumpWidget(_app(repository, client: client));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('sh01-open-catalog')));
    await tester.pumpAndSettle();

    expect(client.catalogCalls, 1);
    expect(client.screenCalls, 0);
    expect(client.detailCalls, 0);
    expect(find.text('研究与创作工具'), findsOneWidget);
    expect(find.text('共享内容与创作'), findsOneWidget);
    expect(find.text('跨平台选题搜索'), findsWidgets);
    expect(find.text('业务资料依据暂不显示'), findsOneWidget);
    expect(find.text('选择一个工具，查看用途与适用内容。'), findsOneWidget);
    expect(find.text('目录中暂时没有可查看的工具。'), findsNothing);
    expect(_visibleCopy(tester), isNot(contains('账号')));
    expect(_visibleCopy(tester), isNot(contains('登录')));
    _expectNoImplementationTerms(tester);
    expect(find.text('不归因到 CTH 或 BMP'), findsNothing);
    expect(find.text('CGE-PRIVATE-001'), findsNothing);
    expect(find.text('全局 Evidence 条数'), findsNothing);
    expect(find.text('运行能力'), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets('mobile changes from capability index to selected detail', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(_app(_FakeSh01Repository(_catalog)));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('sh01-open-catalog')));
    await tester.pumpAndSettle();

    expect(find.text('适用产品'), findsOneWidget);
    expect(find.text('Owner'), findsNothing);
    final capability = find.byKey(
      const Key('sh01-capability-shared.union_search'),
    );
    await tester.ensureVisible(capability);
    await tester.tap(capability);
    await tester.pumpAndSettle();

    expect(find.text('提供团队'), findsNothing);
    expect(find.text('共享内容与创作团队'), findsNothing);
    expect(find.text('CTH'), findsNothing);
    expect(find.text('BMP'), findsNothing);
    expect(find.text('商业运营'), findsWidgets);
    expect(find.text('品牌市场'), findsWidgets);
    expect(find.text('研究资料'), findsWidgets);
    expect(find.text('仅读取资料，不修改原始内容'), findsOneWidget);
    expect(find.text('执行此能力'), findsNothing);
    _expectNoImplementationTerms(tester);
    expect(tester.takeException(), isNull);
  });

  testWidgets('tablet uses the localized shared capability surface', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1024, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      _app(_FakeSh01Repository(_catalog), locale: const Locale('en')),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('sh01-open-catalog')));
    await tester.pumpAndSettle();

    expect(find.text('Research & creation tools'), findsOneWidget);
    expect(find.text('Available to'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('source-shaped cover description uses business language', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final cardSkill = <String, dynamic>{
      'skill_id': 'shared.social_card',
      'tool_name': 'quizang-social-card-skill',
      'name': '多平台封面生成',
      'description': '多平台封面生成：按 Brief 生成可审阅的本地 SVG 社交卡草稿，保留平台尺寸与人工审批边界。',
      'owner': 'Shared Capability / Content Studio',
      'product': 'SHARED',
      'domain': 'content',
      'consumers': ['CTH', 'BMP'],
      'category': '内容制作',
      'version': '1.0.0',
      'permission_level': 'SUGGEST',
      'risk_level': 'MEDIUM',
      'execution_policy': 'APPROVAL_REQUIRED',
      'evaluation_status': 'PARTIAL',
      'implementation_state': 'BOUND_LOCAL_DRAFT',
    };

    await tester.pumpWidget(
      _app(
        _FakeSh01Repository({
          ..._catalog,
          'skills': [cardSkill],
        }),
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('sh01-open-catalog')));
    await tester.pumpAndSettle();
    final capability = find.byKey(
      const Key('sh01-capability-shared.social_card'),
    );
    await tester.ensureVisible(capability);
    await tester.tap(capability);
    await tester.pumpAndSettle();

    expect(
      find.text('多平台封面生成：按需求说明生成可审阅的本地矢量图社交卡草稿，保留平台尺寸与人工审批边界。'),
      findsOneWidget,
    );
    expect(find.textContaining('SVG'), findsNothing);
    expect(find.textContaining('Brief'), findsNothing);
    _expectNoImplementationTerms(tester);
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'rejects API-shaped capability copy before Text or SelectableText',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(390, 844));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      final unsafeSkill = <String, dynamic>{
        'skill_id': 'shared.unsafe_copy',
        'tool_name': 'provider_internal_tool',
        'name': 'Provider model=ollama-prod',
        'description': 'DB Permission Evidence /api/v1 /private/path',
        'owner': 'internal owner',
        'product': 'SHARED',
        'domain': 'content',
        'consumers': ['CTH', 'BMP'],
        'category': 'Database Permission',
        'version': '1.0.0',
        'permission_level': 'READ',
        'risk_level': 'LOW',
        'execution_policy': 'READ_ONLY',
        'evaluation_status': 'PARTIAL',
        'implementation_state': 'BOUND_LOCAL_READ',
      };

      await tester.pumpWidget(
        _app(
          _FakeSh01Repository({
            ..._catalog,
            'skills': [unsafeSkill],
          }),
        ),
      );
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('sh01-open-catalog')));
      await tester.pumpAndSettle();

      final capability = find.byKey(
        const Key('sh01-capability-shared.unsafe_copy'),
      );
      await tester.ensureVisible(capability);
      await tester.tap(capability);
      await tester.pumpAndSettle();

      final selectableCopy = tester
          .widgetList<SelectableText>(find.byType(SelectableText))
          .map((widget) => widget.data)
          .join('\n');
      expect(find.textContaining('Provider'), findsNothing);
      expect(find.textContaining('ollama'), findsNothing);
      expect(selectableCopy, isNot(contains('/api/v1')));
      expect(selectableCopy, isNot(contains('Permission')));
      expect(selectableCopy, isNot(contains('private/path')));
      _expectNoImplementationTerms(tester);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('untrusted global Evidence output and identifiers never render', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(_app(_FakeSh01Repository(_catalog)));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('sh01-open-catalog')));
    await tester.pumpAndSettle();

    expect(find.text('PROMPT SECRET PRIVATE OUTPUT'), findsNothing);
    expect(find.text('<script>steal()</script>'), findsNothing);
    expect(find.text('CGE-PRIVATE-001'), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets('empty catalog is described without sample capabilities', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      _app(_FakeSh01Repository({..._catalog, 'skills': []})),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('sh01-open-catalog')));
    await tester.pumpAndSettle();

    expect(find.text('当前没有可展示的研究或创作工具。'), findsOneWidget);
    expect(find.text('跨平台选题搜索'), findsNothing);
    _expectNoImplementationTerms(tester);
  });

  for (final failureCase in _failureCases) {
    testWidgets('hides raw ${failureCase.name} failure details', (
      tester,
    ) async {
      await tester.pumpWidget(
        _app(_FakeSh01Repository(_catalog, failure: failureCase.error)),
      );
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('sh01-open-catalog')));
      await tester.pumpAndSettle();

      expect(find.text(failureCase.copy), findsOneWidget);
      expect(_visibleCopy(tester), isNot(contains('raw-diagnostic-marker')));
      _expectNoImplementationTerms(tester);
      expect(tester.takeException(), isNull);
    });
  }

  test('catalog parser accepts the current runtime field names', () {
    final catalog = Sh01Catalog.fromResponse(_catalog);

    expect(catalog.capability, 'Shared Content & Creation');
    expect(catalog.consumers, ['CTH', 'BMP']);
    expect(catalog.skills, hasLength(2));
    expect(catalog.skills.first.id, 'shared.union_search');
    expect(catalog.skills.first.permission, 'RESEARCH');
    expect(catalog.skills.first.risk, 'LOW');
  });

  test('catalog parser keeps compatibility with the earlier field names', () {
    final runtimeSkill = (_catalog['skills'] as List).first as Map;
    final skill = Map<String, dynamic>.from(runtimeSkill);
    skill
      ..remove('skill_id')
      ..remove('permission_level')
      ..remove('risk_level')
      ..['id'] = 'legacy.union_search'
      ..['permission'] = 'READ / ANALYZE'
      ..['risk'] = 'LOW';
    final legacyCatalog = <String, dynamic>{
      ..._catalog,
      'skills': [skill],
    };

    final catalog = Sh01Catalog.fromResponse(legacyCatalog);

    expect(catalog.skills.single.id, 'legacy.union_search');
    expect(catalog.skills.single.permission, 'READ / ANALYZE');
    expect(catalog.skills.single.risk, 'LOW');
  });

  test('catalog parser rejects another product or malformed skills', () {
    expect(
      () => Sh01Catalog.fromResponse(const {
        'ok': true,
        'product': 'ZBMP',
        'skills': [],
      }),
      throwsFormatException,
    );
    expect(
      () => Sh01Catalog.fromResponse(const {
        'ok': true,
        'product': 'LUMENIS',
        'skills': {},
      }),
      throwsFormatException,
    );
  });
}

Widget _app(
  Sh01Repository repository, {
  LumenisCoreClient? client,
  Locale locale = const Locale('zh', 'CN'),
  double scale = 1,
  String? initialWorkspaceEntry,
  String? returnScreenId,
  ValueChanged<String>? onNavigate,
}) => MaterialApp(
  theme: LumenisTheme.dark,
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
    body: Sh01Screen(
      client: client ?? _CatalogOnlyClient(),
      repository: repository,
      initialWorkspaceEntry: initialWorkspaceEntry,
      returnScreenId: returnScreenId,
      onNavigate: onNavigate,
    ),
  ),
);

class _FakeSh01Repository implements Sh01Repository {
  _FakeSh01Repository(this.response, {this.failure});

  final Map<String, dynamic> response;
  final Object? failure;
  int catalogCalls = 0;

  @override
  Future<Sh01Catalog> loadCatalog() async {
    catalogCalls++;
    if (failure != null) throw failure!;
    return Sh01Catalog.fromResponse(response);
  }
}

class _CatalogOnlyClient extends LumenisCoreClient {
  Map<String, dynamic>? contextEnvelope;
  @override
  Map<String, dynamic>? get currentContextEnvelope => contextEnvelope;
  int catalogCalls = 0;
  int screenCalls = 0;
  int detailCalls = 0;
  LumenisWorkspaceScope? manuscriptScope;

  @override
  Future<Map<String, dynamic>> listSharedAuthoredManuscripts({
    required SharedWorkspaceScope scope,
    int limit = 100,
    String? cursor,
  }) async => {'items': [], 'has_more': false, 'next_cursor': null};

  @override
  Future<Map<String, dynamic>> listContentProjects({
    required String? domainId,
    int limit = 20,
    String? cursor,
  }) async => {
    'ok': true,
    'publish_status': 'not_performed',
    'status': 'empty',
    'projects': [],
    'next_cursor': null,
  };

  @override
  Future<Map<String, dynamic>> sharedSkillsCatalog() async {
    catalogCalls++;
    return _catalog;
  }

  @override
  Future<Map<String, dynamic>> screen(String screenId) async {
    screenCalls++;
    throw StateError('SH-01 global screen must not be requested');
  }

  @override
  Future<Map<String, dynamic>> contentEvidence(String evidenceId) async {
    detailCalls++;
    throw StateError('global Evidence detail must not be requested');
  }

  @override
  Future<Map<String, dynamic>> prepareInternalPitch({
    required LumenisWorkspaceScope scope,
    required InternalPitchManuscript manuscript,
    required String requestId,
    InternalPitchRevision? revision,
    List<Map<String, dynamic>> citations = const [],
  }) async {
    manuscriptScope = scope;
    throw const LumenisCoreException('Save response unavailable');
  }
}

final _catalog = <String, dynamic>{
  'ok': true,
  'product': 'LUMENIS',
  'capability': 'Shared Content & Creation',
  'consumers': ['CTH', 'BMP'],
  'skills': [
    {
      'skill_id': 'shared.union_search',
      'tool_name': 'union-search-skill',
      'name': '跨平台选题搜索',
      'description': '跨平台选题搜索：在本地研究资料与已入库 Evidence 中做受限检索，不访问站外平台。',
      'owner': 'Shared Capability / Content Studio',
      'product': 'SHARED',
      'domain': 'content',
      'consumers': ['CTH', 'BMP'],
      'category': '研究与证据',
      'version': '1.0.0',
      'permission_level': 'RESEARCH',
      'risk_level': 'LOW',
      'execution_policy': 'READ_ONLY',
      'evaluation_status': 'PARTIAL',
      'implementation_state': 'BOUND_LOCAL_READ',
      'binding': r'C:\private\path\must-not-render',
      'input_hint': 'PROMPT SECRET PRIVATE OUTPUT',
    },
    {
      'skill_id': 'shared.video_shotcraft',
      'tool_name': 'video-shotcraft',
      'name': '专业级片头与转场',
      'description': '专业级片头与转场：依据 Brief 生成可审阅镜头草案，并在提供 Evidence 时复用本地视频分析规范。',
      'owner': 'Shared Capability / Content Studio',
      'product': 'SHARED',
      'domain': 'content',
      'consumers': ['CTH', 'BMP'],
      'category': '内容制作',
      'version': '1.0.0',
      'permission_level': 'ANALYZE',
      'risk_level': 'MEDIUM',
      'execution_policy': 'APPROVAL_REQUIRED',
      'evaluation_status': 'PARTIAL',
      'implementation_state': 'BOUND_LOCAL_DRAFT',
    },
  ],
  'unscoped_evidence': [
    {
      'evidence_id': 'CGE-PRIVATE-001',
      'output_json': {
        'body': '<script>steal()</script> PROMPT SECRET PRIVATE OUTPUT',
      },
    },
  ],
};

const _failureCases = <({String name, String error, String copy})>[
  (
    name: 'authentication',
    error: 'HTTP 401 raw-diagnostic-marker token=secret Core scope',
    copy: '当前请求暂时无法读取工具目录，请重试。',
  ),
  (
    name: 'permission',
    error: 'HTTP 403 raw-diagnostic-marker ViewModel contract',
    copy: '当前范围暂时无法读取工具目录，请重试。',
  ),
  (
    name: 'offline',
    error: 'Core unavailable raw-diagnostic-marker provider',
    copy: '工具目录服务暂时无法连接，请检查网络后重试。',
  ),
  (
    name: 'invalid response',
    error: 'schema mismatch raw-diagnostic-marker /private/path',
    copy: '工具目录数据暂不可用，请稍后重试。',
  ),
];

String _visibleCopy(WidgetTester tester) => <String>[
  ...tester
      .widgetList<Text>(find.byType(Text))
      .map((widget) => widget.data ?? widget.semanticsLabel ?? ''),
  ...tester
      .widgetList<Semantics>(find.byType(Semantics))
      .map((widget) => widget.properties.label ?? ''),
  ...tester
      .widgetList<SelectableText>(find.byType(SelectableText))
      .map((widget) => widget.data ?? ''),
].join('\n');

void _expectNoImplementationTerms(WidgetTester tester) {
  expect(
    _visibleCopy(tester),
    isNot(
      matches(
        RegExp(
          r'\b(core|viewmodel|evidence|owner|scope|contract|provider|runtime|subject|brandfocus|canonical|permission|shared capability|service owner|service team|content studio|cth|bmp|execution policy|registered consumers)\b',
          caseSensitive: false,
        ),
      ),
    ),
  );
}
