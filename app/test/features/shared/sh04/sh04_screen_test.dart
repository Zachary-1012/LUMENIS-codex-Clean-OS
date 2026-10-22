import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/features/shared/sh04/sh04_repository.dart';
import 'package:lumenis_app/features/shared/sh04/sh04_screen.dart';
import 'package:lumenis_app/features/shared/sh04/sh04_snapshot.dart';

import '../shared_test_support.dart';

void main() {
  testWidgets('file export format picker includes PPTX on desktop', (
    tester,
  ) async {
    final priorPlatform = debugDefaultTargetPlatformOverride;
    debugDefaultTargetPlatformOverride = TargetPlatform.macOS;
    try {
      await tester.binding.setSurfaceSize(const Size(1280, 900));
      final repository = _FakeSh04Repository()
        ..items.add(
          _makeExport(index: 1, title: '季度复盘', markdown: '# 季度复盘', version: 1),
        );
      await tester.pumpWidget(_app(repository));
      await tester.pumpAndSettle();
      await tester.tap(find.text('季度复盘').first);
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('sh04-export-report')));
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('sh04-export-pptx')), findsOneWidget);
      expect(find.byKey(const Key('sh04-export-docx')), findsOneWidget);
      expect(tester.takeException(), isNull);
    } finally {
      await tester.binding.setSurfaceSize(null);
      debugDefaultTargetPlatformOverride = priorPlatform;
    }
  });

  testWidgets('writes, reopens and revises a Shared report version', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1280, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final repository = _FakeSh04Repository();
    await tester.pumpWidget(_app(repository));
    await tester.pumpAndSettle();

    expect(find.text('共享工作区'), findsOneWidget);
    expect(find.text('共享工作区中还没有保存的报告。'), findsOneWidget);
    await tester.tap(find.byKey(const Key('sh04-create-report')));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('sh04-report-title')), '季度复盘');
    await tester.enterText(
      find.byKey(const Key('sh04-report-markdown')),
      '# 复盘\n\n这是用户撰写的报告。',
    );
    await tester.tap(find.byKey(const Key('sh04-save-report')));
    await tester.pumpAndSettle();

    expect(repository.saveCount, 1);
    expect(repository.items.single.version, 1);
    expect(find.text('季度复盘'), findsWidgets);
    expect(find.textContaining('这是用户撰写的报告。'), findsOneWidget);

    await tester.tap(find.text('季度复盘').first);
    await tester.pumpAndSettle();
    expect(repository.reopenCount, 1);

    await tester.tap(find.byKey(const Key('sh04-revise-report')));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byKey(const Key('sh04-report-title')),
      '季度复盘（修订）',
    );
    await tester.enterText(
      find.byKey(const Key('sh04-report-markdown')),
      '# 复盘\n\n补充了用户确认的结论。',
    );
    await tester.enterText(
      find.byKey(const Key('sh04-revision-reason')),
      '补充已确认的结论',
    );
    await tester.tap(find.byKey(const Key('sh04-save-report')));
    await tester.pumpAndSettle();

    expect(repository.revisionCount, 1);
    expect(repository.items, hasLength(2));
    expect(repository.items.first.version, 1);
    expect(repository.items.last.version, 2);
    expect(
      repository.items.last.parentArtifactId,
      repository.items.first.internalId,
    );
    expect(find.text('季度复盘'), findsOneWidget);
    expect(find.text('季度复盘（修订）'), findsWidgets);
    expect(find.textContaining('补充了用户确认的结论。'), findsOneWidget);

    await tester.tap(find.text('季度复盘').first);
    await tester.pumpAndSettle();
    expect(repository.reopenCount, 2);
    expect(find.text('季度复盘'), findsWidgets);
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'authentication and access failures remain distinct and retryable in all locales',
    (tester) async {
      const recoveryLocales = [
        (
          locale: Locale('zh', 'CN'),
          authentication: '当前内容暂时无法打开。可重试读取，或返回后稍后再试。',
          permission: '当前内容不可访问。',
          retry: '重新读取',
          forbiddenTerms: ['登录', '账号', '账户', '检查连接', '检查网络'],
        ),
        (
          locale: Locale('en'),
          authentication:
              'This content cannot be opened right now. You can retry reading it or return and try again later.',
          permission: 'This content is not accessible.',
          retry: 'Read again',
          forbiddenTerms: [
            'sign in',
            'login',
            'account',
            'check the connection',
            'check connection',
          ],
        ),
        (
          locale: Locale('ko'),
          authentication:
              '현재 콘텐츠를 지금 열 수 없습니다. 다시 읽기를 시도하거나 돌아간 뒤 나중에 다시 시도할 수 있습니다.',
          permission: '현재 콘텐츠에 접근할 수 없습니다.',
          retry: '다시 읽기',
          forbiddenTerms: ['로그인', '계정', '연결을 확인'],
        ),
      ];

      for (final copy in recoveryLocales) {
        for (final statusCode in [401, 403]) {
          await tester.pumpWidget(const SizedBox.shrink());
          await tester.pump();
          final repository = _RecoveringSh04Repository(statusCode);
          await tester.pumpWidget(_app(repository, locale: copy.locale));
          await tester.pumpAndSettle();

          final expected = statusCode == 401
              ? copy.authentication
              : copy.permission;
          expect(find.text(expected), findsOneWidget);
          _expectNoAuthOrNetworkAdvice(tester, copy.forbiddenTerms);
          expect(find.text(copy.retry), findsOneWidget);
          expect(find.textContaining('private access failure'), findsNothing);

          await tester.tap(find.text(copy.retry));
          await tester.pumpAndSettle();

          expect(repository.calls, 2);
          expect(find.text(expected), findsNothing);
          expect(tester.takeException(), isNull);
        }
      }
    },
  );

  testWidgets('legacy unscoped response fails closed without output', (
    tester,
  ) async {
    final repository = _FakeSh04Repository()
      ..loadError = const FormatException('unscoped legacy response');
    await tester.pumpWidget(_app(repository));
    await tester.pumpAndSettle();

    expect(find.text('成果中心暂不可用'), findsOneWidget);
    expect(find.text('unscoped legacy response'), findsNothing);
    expect(find.text('下载'), findsNothing);
    expectNoSharedRawMarkers(tester);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Korean title uses the shared localization integration key', (
    tester,
  ) async {
    await tester.pumpWidget(
      _app(_FakeSh04Repository(), locale: const Locale('ko')),
    );
    await tester.pumpAndSettle();

    expect(find.text('리포트 내보내기'), findsOneWidget);
    expect(find.text('결과물 대기열'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Shared scope and saved states use the selected locale', (
    tester,
  ) async {
    const locales = [
      (
        locale: Locale('zh', 'CN'),
        scope: '共享工作区',
        saved: '已保存',
        unavailable: '暂不可用',
      ),
      (
        locale: Locale('en'),
        scope: 'Shared workspace',
        saved: 'Saved',
        unavailable: 'Unavailable',
      ),
      (
        locale: Locale('ko'),
        scope: '공유 작업 공간',
        saved: '저장됨',
        unavailable: '사용할 수 없음',
      ),
    ];

    for (final copy in locales) {
      await tester.pumpWidget(const SizedBox.shrink());
      await tester.pump();
      final repository = _FakeSh04Repository()
        ..items.addAll([
          _makeExport(
            index: 1,
            title: 'Saved report',
            markdown: '# Saved report',
            version: 1,
          ),
          _makeExport(
            index: 2,
            title: 'Unavailable report',
            markdown: '# Unavailable report',
            version: 1,
            state: Sh04ExportState.unavailable,
          ),
        ]);
      await tester.pumpWidget(_app(repository, locale: copy.locale));
      await tester.pumpAndSettle();

      expect(find.text(copy.scope), findsOneWidget);
      expect(find.text(copy.saved), findsOneWidget);
      expect(find.text(copy.unavailable), findsOneWidget);
      if (copy.locale.languageCode != 'zh') {
        expect(find.text('共享工作区'), findsNothing);
        expect(find.text('已保存'), findsNothing);
        expect(find.text('暂不可用'), findsNothing);
      }
      expect(tester.takeException(), isNull);
    }
  });

  test(
    'SavedWork parser requires exact Shared scope and preserves citations',
    () {
      final citation = <String, dynamic>{
        'source_id': 'SRC-100',
        'source_scope': {'domain_id': 'CTH', 'subject_id': 'subject-1'},
      };
      final item = _savedWorkItem(citations: [citation]);
      final parsed = Sh04Export.fromSavedWorkItem(item);
      expect(parsed.title, 'Shared report');
      expect(parsed.workId, 'WORK-000000000000000000000001');
      expect(parsed.citations.single, citation);
      expect(parsed.citations.single['source_scope'], citation['source_scope']);

      final mixedContext = _savedWorkItem()
        ..['document']['context']['domain_id'] = 'CTH';
      expect(
        () => Sh04Export.fromSavedWorkItem(mixedContext),
        throwsFormatException,
      );

      final mixedReturnScope = _savedWorkItem()
        ..['return_ref']['scope']['product_id'] = 'ZBMP';
      expect(
        () => Sh04Export.fromSavedWorkItem(mixedReturnScope),
        throwsFormatException,
      );

      final missingParent = _savedWorkItem(version: 2);
      expect(
        () => Sh04Export.fromSavedWorkItem(missingParent),
        throwsFormatException,
      );

      final response = <String, dynamic>{
        'ok': true,
        'result': {
          'items': [item],
          'verification_complete': true,
          'unverified_candidates': 0,
          'has_more': false,
          'next_cursor': null,
        },
      };
      final snapshot = Sh04Snapshot.fromResponse(response);
      expect(snapshot.scope, Sh04Scope.sharedWorkspace);
      expect(snapshot.exports.single.citations.single, citation);
    },
  );
}

Widget _app(
  Sh04Repository repository, {
  Locale locale = const Locale('zh', 'CN'),
}) => sharedTestApp(
  Sh04Screen(client: LumenisCoreClient(), repository: repository),
  locale: locale,
);

class _FakeSh04Repository implements Sh04Repository {
  final List<Sh04Export> items = [];
  Object? loadError;
  int saveCount = 0;
  int reopenCount = 0;
  int revisionCount = 0;

  @override
  Future<Sh04Snapshot> loadExports({String? cursor}) async {
    if (loadError != null) throw loadError!;
    return Sh04Snapshot(
      scope: Sh04Scope.sharedWorkspace,
      exports: List.unmodifiable(items),
      verificationComplete: true,
      unverifiedCandidates: 0,
      hasMore: false,
      nextCursor: null,
    );
  }

  @override
  Future<Sh04Export> saveReport({
    required String title,
    required String markdown,
    required String requestId,
  }) async {
    saveCount++;
    final item = _makeExport(
      index: 1,
      title: title,
      markdown: markdown,
      version: 1,
    );
    items.add(item);
    return item;
  }

  @override
  Future<Sh04Export> reopen(String artifactId) async {
    reopenCount++;
    return items.singleWhere((item) => item.internalId == artifactId);
  }

  @override
  Future<Sh04Export> reviseReport({
    required Sh04Export parent,
    required String title,
    required String markdown,
    required String reason,
    required String requestId,
  }) async {
    revisionCount++;
    final revised = _makeExport(
      index: 2,
      title: title,
      markdown: markdown,
      version: parent.version + 1,
      workId: parent.workId,
      parentArtifactId: parent.internalId,
    );
    items.add(revised);
    return revised;
  }

  @override
  Future<SavedWorkExportFile> export({
    required String artifactId,
    required String format,
  }) async => SavedWorkExportFile(
    bytes: Uint8List.fromList(utf8.encode('exported $format')),
    filename: 'report.$format',
    mediaType: 'text/markdown; charset=utf-8',
  );
}

class _RecoveringSh04Repository extends _FakeSh04Repository {
  _RecoveringSh04Repository(this.statusCode);

  final int statusCode;
  int calls = 0;

  @override
  Future<Sh04Snapshot> loadExports({String? cursor}) async {
    calls++;
    if (calls == 1) {
      throw LumenisCoreException(
        'HTTP $statusCode private access failure',
        statusCode: statusCode,
      );
    }
    return super.loadExports(cursor: cursor);
  }
}

Sh04Export _makeExport({
  required int index,
  required String title,
  required String markdown,
  required int version,
  Sh04ExportState state = Sh04ExportState.ready,
  String workId = 'WORK-000000000000000000000001',
  String? parentArtifactId,
}) => Sh04Export(
  internalId: 'ART-${index.toString().padLeft(16, '0')}',
  title: title,
  state: state,
  markdown: markdown,
  sha256: index.toString().padLeft(64, '0'),
  workId: workId,
  version: version,
  parentArtifactId: parentArtifactId,
  citations: const [],
  generatedAt: '2026-10-16T00:00:00Z',
);

Map<String, dynamic> _savedWorkItem({
  int version = 1,
  String? parentArtifactId,
  String? parentSha256,
  List<Map<String, dynamic>> citations = const [],
}) => {
  'artifact': {
    'artifact_id': 'ART-0000000000000001',
    'sha256':
        '0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef',
    'created_at': '2026-10-16T00:00:00Z',
  },
  'document': {
    'schema': 'lumenis.saved-work/v1',
    'kind': 'report',
    'work_id': 'WORK-000000000000000000000001',
    'version': version,
    'title': 'Shared report',
    'markdown': '# Shared report\n\nSaved content.',
    'context': {'scope_kind': 'shared_workspace', 'version': 1, 'actor_id': 19},
    'contract': {
      'id': 'lumenis.saved-work',
      'version': '1',
      'required_payload_paths': <String>[],
    },
    'citations': citations,
    'parent_artifact_id': parentArtifactId,
    'parent_sha256': parentSha256,
  },
  'return_ref': {
    'artifact_id': 'ART-0000000000000001',
    'work_id': 'WORK-000000000000000000000001',
    'version': version,
    'scope': {'scope_kind': 'shared_workspace', 'version': 1},
  },
};

void _expectNoAuthOrNetworkAdvice(
  WidgetTester tester,
  List<String> forbiddenTerms,
) {
  final visibleText = visibleSharedCopy(tester).toLowerCase();
  for (final term in forbiddenTerms) {
    expect(visibleText, isNot(contains(term.toLowerCase())));
  }
}
