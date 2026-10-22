import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/features/shared/research/shared_research_repository.dart';
import 'package:lumenis_app/features/shared/research/shared_research_workspace.dart';
import '../shared_test_support.dart';

const scope = {'scope_kind': 'shared_workspace', 'version': 1};
const id = 'ART-0000000000000001';
final digest = 'a' * 64;
Map<String, dynamic> saved({
  int version = 1,
  String markdown = '已核对 17 行；仍有缺项。',
}) => {
  'artifact': {
    'artifact_id': version == 1 ? id : 'ART-0000000000000002',
    'sha256': digest,
  },
  'document': {
    'work_id': 'WORK-research',
    'kind': 'research',
    'title': '来源目录',
    'markdown': markdown,
    'version': version,
    'created_at': '2026-10-23T02:00:00+08:00',
    'parent_artifact_id': version == 1 ? null : id,
    'parent_sha256': version == 1 ? null : digest,
    'payload': {
      'source_brief_reference': {'job_id': 'brief-${'a' * 32}', 'scope': scope},
    },
  },
  'return_ref': {'scope': scope},
  'receipt': {
    'ref': version == 1 ? id : 'ART-0000000000000002',
    'sha256': digest,
    'version': version,
    'work_id': 'WORK-research',
    'scope': scope,
    'constraint_observations': {
      'committed_bytes_match': true,
      'parent_chain_verified': true,
      'source_authorization': 'fresh-per-source',
    },
  },
};

class Repository implements SharedResearchRepository {
  List<SharedResearchDocument> versions = [
    SharedResearchDocument.fromResponse(saved()),
  ];
  bool loseWriteReply = false, denied = false;
  final requests = <String>[];
  @override
  Future<ResearchPage<SharedResearchDocument>> history({
    String? cursor,
  }) async => ResearchPage(versions.reversed.toList(), null, false);
  @override
  Future<ResearchPage<SharedResearchTask>> tasks({String? cursor}) async =>
      const ResearchPage([], null, false);
  @override
  Future<SharedResearchDocument> open(String value) async {
    if (denied) throw const LumenisCoreException('denied', statusCode: 403);
    return versions.firstWhere((v) => v.id == value);
  }

  @override
  Future<SharedResearchDocument> revise(
    SharedResearchDocument parent,
    String title,
    String markdown,
    String requestId,
  ) async {
    requests.add(requestId);
    if (versions.length == 1) {
      versions.add(
        SharedResearchDocument.fromResponse(
          saved(version: 2, markdown: markdown),
        ),
      );
    }
    if (loseWriteReply) {
      loseWriteReply = false;
      throw const LumenisCoreException('reply lost');
    }
    return versions.last;
  }

  @override
  Future<SharedResearchTask> start(
    String question,
    List<String> sources,
    String requestId,
  ) => throw UnimplementedError();
  @override
  Future<SharedResearchTask> task(String id, {bool resume = false}) =>
      throw UnimplementedError();
  @override
  Future<SharedResearchDocument> save(
    SharedResearchTask task,
    String requestId,
  ) => throw UnimplementedError();
}

void main() {
  testWidgets(
    'user-edited uneven table remains readable without losing source text',
    (tester) async {
      tester.view.physicalSize = const Size(1280, 900);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final repository = Repository()
        ..versions = [
          SharedResearchDocument.fromResponse(
            saved(
              markdown:
                  '# Results\n| Field | Value |\n| --- | --- |\n| Partial |\n| Value | 0 | extra |',
            ),
          ),
        ];
      await tester.pumpWidget(
        sharedTestApp(
          SharedResearchWorkspace(repository: repository, sources: const {}),
        ),
      );
      await tester.pumpAndSettle();
      await tester.tap(find.text('来源目录'));
      await tester.pumpAndSettle();
      expect(find.text('Results'), findsOneWidget);
      expect(find.byType(Table), findsOneWidget);
      expect(tester.takeException(), isNull);
      await tester.tap(find.text('编辑'));
      await tester.pumpAndSettle();
      expect(find.textContaining('| Value | 0 | extra |'), findsOneWidget);
    },
  );

  test(
    'fresh read rejects missing bytes, cross-scope and wrong version receipts',
    () {
      expect(
        SharedResearchDocument.fromResponse(saved(), reopened: true).version,
        1,
      );
      for (final key in ['sha256', 'version', 'scope']) {
        final value = saved();
        value['receipt'] = Map<String, dynamic>.from(value['receipt'] as Map)
          ..[key] = null;
        expect(
          () => SharedResearchDocument.fromResponse(value, reopened: true),
          throwsFormatException,
        );
      }
      final cross = saved();
      (cross['return_ref'] as Map)['scope'] = {'domain_id': 'cth'};
      expect(
        () => SharedResearchDocument.fromResponse(cross),
        throwsFormatException,
      );
    },
  );

  testWidgets(
    'lost save reply retains exact request and edited bytes for reconciliation',
    (tester) async {
      tester.view.physicalSize = const Size(1280, 900);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final repository = Repository()..loseWriteReply = true;
      await tester.pumpWidget(
        sharedTestApp(
          SharedResearchWorkspace(repository: repository, sources: const {}),
        ),
      );
      await tester.pumpAndSettle();
      await tester.tap(find.text('来源目录'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('编辑'));
      await tester.pumpAndSettle();
      await tester.enterText(
        find.widgetWithText(TextField, '正文'),
        '人工补充：这些来源需要逐一核对。',
      );
      await tester.pump();
      await tester.tap(find.text('保存新版本'));
      await tester.pumpAndSettle();
      expect(find.text('核对本次操作'), findsOneWidget);
      expect(find.text('人工补充：这些来源需要逐一核对。'), findsOneWidget);
      await tester.tap(find.text('核对本次操作'));
      await tester.pumpAndSettle();
      expect(repository.requests.length, 2);
      expect(repository.requests.toSet().length, 1);
      expect(repository.versions.length, 2);
      expect(find.text('版本 2'), findsOneWidget);
      expect(find.textContaining('未保存'), findsNothing);
    },
  );

  testWidgets('denied reopen removes previously visible research contents', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(1280, 900);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final repository = Repository();
    await tester.pumpWidget(
      sharedTestApp(
        SharedResearchWorkspace(repository: repository, sources: const {}),
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.text('来源目录'));
    await tester.pumpAndSettle();
    repository.denied = true;
    await tester.tap(find.text('来源目录').first);
    await tester.pumpAndSettle();
    expect(find.text('已核对 17 行；仍有缺项。'), findsNothing);
    expect(find.text('资料或版本已变化，请重新读取。'), findsOneWidget);
  });

  for (final locale in [
    const Locale('zh', 'CN'),
    const Locale('en'),
    const Locale('ko'),
  ]) {
    testWidgets(
      'narrow research retains source, history and work tabs: $locale',
      (tester) async {
        tester.view.physicalSize = const Size(390, 844);
        tester.view.devicePixelRatio = 1;
        addTearDown(tester.view.resetPhysicalSize);
        addTearDown(tester.view.resetDevicePixelRatio);
        await tester.pumpWidget(
          sharedTestApp(
            SharedResearchWorkspace(
              repository: Repository(),
              sources: const {id: '材料.csv'},
            ),
            locale: locale,
          ),
        );
        await tester.pumpAndSettle();
        expect(find.byType(Tab), findsNWidgets(2));
        expect(find.text('材料.csv'), findsOneWidget);
        expect(tester.takeException(), isNull);
      },
    );
  }
}
