import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/features/shared/sh04/sh04_repository.dart';
import 'package:lumenis_app/features/shared/sh04/sh04_screen.dart';
import 'package:lumenis_app/features/shared/sh04/sh04_snapshot.dart';

import '../shared_test_support.dart';

void main() {
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

          await tester.ensureVisible(find.text(copy.retry));
          await tester.tap(find.text(copy.retry));
          await tester.pumpAndSettle();

          expect(repository.calls, 2);
          expect(find.text(expected), findsNothing);
          expect(tester.takeException(), isNull);
        }
      }
    },
  );
  testWidgets('output center shows only reopenable exact-scope artifacts', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(_app(_FakeSh04Repository(_readyResponse)));
    await tester.pumpAndSettle();

    expect(find.text('报告导出中心'), findsOneWidget);
    expect(find.text('成果队列'), findsOneWidget);
    expect(find.text('成果预览'), findsOneWidget);
    expect(find.text('周报预览'), findsWidgets);
    expect(find.text('公开资料摘要'), findsOneWidget);
    expect(find.text('export-private-id'), findsNothing);
    expect(find.text('wrong-scope'), findsNothing);
    expectNoSharedRawMarkers(tester);
    expect(tester.takeException(), isNull);

    await tester.binding.setSurfaceSize(const Size(390, 844));
    await tester.pumpAndSettle();
    expect(find.text('成果预览'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('legacy unscoped reports are blocked without a fake download', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    final unscoped = <String, dynamic>{
      'ok': true,
      'screen': 'SH-04',
      'source': 'runtime',
      'bound': true,
      'reports': [
        {'report': 'not-scoped', 'state': 'READY'},
      ],
    };
    await tester.pumpWidget(_app(_FakeSh04Repository(unscoped)));
    await tester.pumpAndSettle();

    expect(find.text('成果中心暂不显示'), findsOneWidget);
    expect(find.text('not-scoped'), findsNothing);
    expect(find.text('下载'), findsNothing);
    expectNoSharedRawMarkers(tester);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Korean title uses the shared localization integration key', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1024, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      _app(_FakeSh04Repository(_readyResponse), locale: const Locale('ko')),
    );
    await tester.pumpAndSettle();

    expect(find.text('리포트 내보내기'), findsOneWidget);
    expect(find.text('결과물 대기열'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  test('export parser requires exact scope and a reopenable artifact', () {
    final focusResponse = <String, dynamic>{
      ..._readyResponse,
      'scope': {
        'mode': 'FOCUS',
        'domain_id': 'CTH',
        'subject_id': 'subject-private-2',
        'display_name': '广州太古汇',
      },
      'data': {
        'exports': [
          {
            'id': 'focus-export',
            'title': '焦点周报',
            'format': 'markdown',
            'state': 'READY',
            'projection': sharedProjection(
              scope: {
                'mode': 'FOCUS',
                'domain_id': 'CTH',
                'subject_id': 'subject-private-2',
              },
            ),
            'scope_verified': true,
            'evidence_backed': true,
            'permission': {'read': true, 'decision': 'ALLOW'},
            'lineage_verified': true,
            'integrity_verified': true,
            'scope': {
              'mode': 'FOCUS',
              'domain_id': 'CTH',
              'subject_id': 'subject-private-2',
            },
            'artifact': {'reopenable': true, 'preview': '焦点摘要'},
          },
          {
            'id': 'not-exact',
            'title': '不应显示',
            'format': 'markdown',
            'state': 'READY',
            'projection': sharedProjection(
              scope: {
                'mode': 'FOCUS',
                'domain_id': 'CTH',
                'subject_id': 'other-subject',
              },
            ),
            'scope_verified': true,
            'evidence_backed': true,
            'permission': {'read': true, 'decision': 'ALLOW'},
            'lineage_verified': true,
            'integrity_verified': true,
            'scope': {
              'mode': 'FOCUS',
              'domain_id': 'CTH',
              'subject_id': 'other-subject',
            },
            'artifact': {'reopenable': true, 'preview': 'wrong-scope'},
          },
        ],
      },
    };
    final snapshot = Sh04Snapshot.fromResponse(focusResponse);
    expect(snapshot.scope.focusId, 'subject-private-2');
    expect(snapshot.exports.single.internalId, 'focus-export');
    expect(snapshot.exports.single.reopenable, isTrue);
    expect(snapshot.exports.single.preview, '焦点摘要');

    final missingScope = Map<String, dynamic>.from(_readyResponse);
    final missingScopeData = Map<String, dynamic>.from(
      _readyResponse['data'] as Map,
    );
    final missingScopeRow = Map<String, dynamic>.from(
      (missingScopeData['exports'] as List).first as Map,
    )..remove('projection');
    missingScopeData['exports'] = [missingScopeRow];
    missingScope['data'] = missingScopeData;
    expect(Sh04Snapshot.fromResponse(missingScope).exports, isEmpty);

    final missingPermission = Map<String, dynamic>.from(_readyResponse);
    final missingPermissionData = Map<String, dynamic>.from(
      _readyResponse['data'] as Map,
    );
    final missingPermissionRow = Map<String, dynamic>.from(
      (missingPermissionData['exports'] as List).first as Map,
    );
    final missingPermissionProjection = Map<String, dynamic>.from(
      missingPermissionRow['projection'] as Map,
    )..['read_allowed'] = false;
    missingPermissionRow['projection'] = missingPermissionProjection;
    missingPermissionData['exports'] = [missingPermissionRow];
    missingPermission['data'] = missingPermissionData;
    expect(Sh04Snapshot.fromResponse(missingPermission).exports, isEmpty);

    final missingIntegrity = Map<String, dynamic>.from(_readyResponse);
    final missingIntegrityData = Map<String, dynamic>.from(
      _readyResponse['data'] as Map,
    );
    final missingIntegrityRow = Map<String, dynamic>.from(
      (missingIntegrityData['exports'] as List).first as Map,
    );
    final missingIntegrityProjection = Map<String, dynamic>.from(
      missingIntegrityRow['projection'] as Map,
    );
    missingIntegrityProjection['integrity'] = <String, dynamic>{
      ...(missingIntegrityProjection['integrity'] as Map),
      'integrity_version': 1,
    };
    missingIntegrityRow['projection'] = missingIntegrityProjection;
    missingIntegrityData['exports'] = [missingIntegrityRow];
    missingIntegrity['data'] = missingIntegrityData;
    expect(Sh04Snapshot.fromResponse(missingIntegrity).exports, isEmpty);
  });
}

Widget _app(
  Sh04Repository repository, {
  Locale locale = const Locale('zh', 'CN'),
}) => sharedTestApp(
  Sh04Screen(client: LumenisCoreClient(), repository: repository),
  locale: locale,
);

class _FakeSh04Repository implements Sh04Repository {
  _FakeSh04Repository(this.response);

  final Map<String, dynamic> response;

  @override
  Future<Sh04Snapshot> loadExports() async =>
      Sh04Snapshot.fromResponse(response);
}

class _RecoveringSh04Repository implements Sh04Repository {
  _RecoveringSh04Repository(this.statusCode);

  final int statusCode;
  int calls = 0;

  @override
  Future<Sh04Snapshot> loadExports() async {
    calls++;
    if (calls == 1) {
      throw LumenisCoreException(
        'HTTP $statusCode private access failure',
        statusCode: statusCode,
      );
    }
    return Sh04Snapshot.fromResponse(_readyResponse);
  }
}

void _expectNoAuthOrNetworkAdvice(
  WidgetTester tester,
  List<String> forbiddenTerms,
) {
  final visibleText = tester
      .widgetList<Text>(find.byType(Text))
      .map((text) => text.data ?? text.textSpan?.toPlainText() ?? '')
      .join('\n')
      .toLowerCase();
  for (final term in forbiddenTerms) {
    expect(visibleText, isNot(contains(term.toLowerCase())));
  }
}

final _readyResponse = sharedRuntimeResponse('SH-04', {
  'exports': [
    {
      'id': 'export-private-id',
      'title': '周报预览',
      'format': 'markdown',
      'state': 'READY',
      'projection': sharedProjection(scope: {'mode': 'GLOBAL_ALL'}),
      'scope_verified': true,
      'evidence_backed': true,
      'permission': {'read': true, 'decision': 'ALLOW'},
      'lineage_verified': true,
      'integrity_verified': true,
      'scope': {'mode': 'GLOBAL_ALL', 'global': true},
      'artifact': {
        'reopenable': true,
        'preview': '公开资料摘要',
        'private_path': r'C:\private\path',
      },
      'evidence_count': 2,
      'generated_at': '2026-09-22',
    },
    {
      'id': 'not-reopenable',
      'title': '暂不可重新打开',
      'format': 'csv',
      'state': 'READY',
      'projection': sharedProjection(scope: {'mode': 'GLOBAL_ALL'}),
      'scope_verified': true,
      'evidence_backed': true,
      'permission': {'read': true, 'decision': 'ALLOW'},
      'lineage_verified': true,
      'integrity_verified': true,
      'scope': {'mode': 'GLOBAL_ALL', 'global': true},
      'artifact': {'reopenable': false, 'preview': 'raw-secret-marker'},
    },
    {
      'id': 'wrong-scope',
      'title': '不应显示',
      'format': 'pdf',
      'state': 'READY',
      'projection': sharedProjection(
        scope: {'mode': 'FOCUS', 'domain_id': 'CTH', 'subject_id': 'x'},
      ),
      'scope_verified': true,
      'evidence_backed': true,
      'permission': {'read': true, 'decision': 'ALLOW'},
      'lineage_verified': true,
      'integrity_verified': true,
      'scope': {'mode': 'FOCUS', 'domain_id': 'CTH', 'subject_id': 'x'},
      'artifact': {'reopenable': true, 'preview': 'wrong-scope'},
    },
  ],
});
