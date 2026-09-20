import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/core/lumenis_theme.dart';
import 'package:lumenis_app/features/shared/sh01/sh01_repository.dart';
import 'package:lumenis_app/features/shared/sh01/sh01_screen.dart';
import 'package:lumenis_app/features/shared/sh01/sh01_snapshot.dart';

void main() {
  testWidgets('desktop browses shared catalog and blocks unscoped Evidence', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final client = _CatalogOnlyClient();
    final repository = CoreSh01Repository(client: client);

    await tester.pumpWidget(_app(repository, client: client));
    await tester.pumpAndSettle();

    expect(client.catalogCalls, 1);
    expect(client.screenCalls, 0);
    expect(client.detailCalls, 0);
    expect(find.text('共享能力目录'), findsOneWidget);
    expect(find.text('Shared Content & Creation'), findsOneWidget);
    expect(find.text('AI 研究助手'), findsWidgets);
    expect(find.text('Evidence 读取受 scope contract 阻断'), findsOneWidget);
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

    expect(find.text('REGISTERED CONSUMERS'), findsOneWidget);
    expect(find.text('Owner'), findsNothing);
    final capability = find.byKey(const Key('sh01-capability-ai.research'));
    await tester.ensureVisible(capability);
    await tester.tap(capability);
    await tester.pumpAndSettle();

    expect(find.text('Owner'), findsOneWidget);
    expect(find.text('catalog-owner'), findsOneWidget);
    expect(find.text('READ / ANALYZE'), findsOneWidget);
    expect(find.text('执行此能力'), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets('untrusted global Evidence output and identifiers never render', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(_app(_FakeSh01Repository(_catalog)));
    await tester.pumpAndSettle();

    expect(find.text('PROMPT SECRET PRIVATE OUTPUT'), findsNothing);
    expect(find.text('<script>steal()</script>'), findsNothing);
    expect(find.text('CGE-PRIVATE-001'), findsNothing);
    expect(tester.takeException(), isNull);
  });

  test('catalog parser accepts the current response and safe metadata', () {
    final catalog = Sh01Catalog.fromResponse(_catalog);

    expect(catalog.capability, 'Shared Content & Creation');
    expect(catalog.consumers, ['CTH', 'BMP']);
    expect(catalog.skills, hasLength(2));
    expect(catalog.skills.first.permission, 'READ / ANALYZE');
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

Widget _app(Sh01Repository repository, {LumenisCoreClient? client}) =>
    MaterialApp(
      theme: LumenisTheme.dark,
      home: Scaffold(
        body: Sh01Screen(
          client: client ?? LumenisCoreClient(),
          repository: repository,
        ),
      ),
    );

class _FakeSh01Repository implements Sh01Repository {
  _FakeSh01Repository(this.response);

  final Map<String, dynamic> response;
  int catalogCalls = 0;

  @override
  Future<Sh01Catalog> loadCatalog() async {
    catalogCalls++;
    return Sh01Catalog.fromResponse(response);
  }
}

class _CatalogOnlyClient extends LumenisCoreClient {
  int catalogCalls = 0;
  int screenCalls = 0;
  int detailCalls = 0;

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
}

final _catalog = <String, dynamic>{
  'ok': true,
  'product': 'LUMENIS',
  'capability': 'Shared Content & Creation',
  'consumers': ['CTH', 'BMP'],
  'skills': [
    {
      'id': 'ai.research',
      'name': 'AI 研究助手',
      'description': '汇总经过授权的研究资料。',
      'owner': 'catalog-owner',
      'consumers': ['CTH', 'BMP'],
      'category': 'RESEARCH',
      'version': '1.2',
      'permission': 'READ / ANALYZE',
      'risk': 'LOW',
      'execution_policy': 'NO_EXTERNAL_WRITE',
      'evaluation_status': 'REGISTERED',
      'implementation_state': 'IMPLEMENTED',
      'binding': r'C:\private\path\must-not-render',
      'input_hint': 'PROMPT SECRET PRIVATE OUTPUT',
    },
    {
      'id': 'content.copy',
      'name': '内容草稿器',
      'description': '提供草稿整理能力。',
      'owner': 'catalog-owner',
      'consumers': ['CTH', 'BMP'],
      'category': 'CONTENT',
      'version': '2.0',
      'permission': 'READ / SUGGEST',
      'risk': 'MEDIUM',
      'execution_policy': 'NO_EXTERNAL_WRITE',
      'evaluation_status': 'REGISTERED',
      'implementation_state': 'IMPLEMENTED',
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
