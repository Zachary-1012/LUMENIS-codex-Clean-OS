import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/features/shared/sh06/sh06_repository.dart';
import 'package:lumenis_app/features/shared/sh06/sh06_screen.dart';
import 'package:lumenis_app/features/shared/sh06/sh06_snapshot.dart';

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
          final repository = _RecoveringSh06Repository(statusCode);
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
  testWidgets('inbox separates tasks from notifications and alerts', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(_app(_FakeSh06Repository(_readyResponse)));
    await tester.pumpAndSettle();

    expect(find.text('通知 / 任务中心'), findsOneWidget);
    expect(find.text('处理通道'), findsOneWidget);
    expect(find.text('核对一条资料'), findsWidgets);
    expect(find.text('待处理'), findsWidgets);
    expect(find.text('PRIVATE-ID'), findsNothing);
    expect(find.text('内部服务'), findsNothing);
    expectNoSharedRawMarkers(tester);
    expect(tester.takeException(), isNull);

    await tester.binding.setSurfaceSize(const Size(390, 844));
    await tester.pumpAndSettle();
    expect(find.text('事项详情'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('unscoped operational items are blocked', (tester) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    final unscoped = <String, dynamic>{
      'ok': true,
      'screen': 'SH-06',
      'source': 'runtime',
      'bound': true,
      'data': {
        'tasks': [
          {'id': 'PRIVATE-ID', 'title': '不应显示'},
        ],
      },
    };
    await tester.pumpWidget(_app(_FakeSh06Repository(unscoped)));
    await tester.pumpAndSettle();

    expect(find.text('通知与待办暂不显示'), findsOneWidget);
    expect(find.text('不应显示'), findsNothing);
    expectNoSharedRawMarkers(tester);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Korean title uses the existing integration key', (tester) async {
    await tester.binding.setSurfaceSize(const Size(1024, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      _app(_FakeSh06Repository(_readyResponse), locale: const Locale('ko')),
    );
    await tester.pumpAndSettle();

    expect(find.text('알림·작업 센터'), findsOneWidget);
    expect(find.text('처리 채널'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  test('inbox parser infers lanes, keeps exact focus, and links evidence', () {
    final focusPageScope = <String, dynamic>{
      'mode': 'FOCUS',
      'domain_id': 'CTH',
      'subject_id': 'subject-private-6',
      'display_name': '广州太古汇',
    };
    final focusRowScope = <String, dynamic>{
      'mode': 'FOCUS',
      'domain_id': 'CTH',
      'subject_id': 'subject-private-6',
    };
    final focusResponse = sharedResponseWithRowScopes(
      _readyResponse,
      pageScope: focusPageScope,
      rowScopes: {
        'tasks': focusRowScope,
        'notifications': focusRowScope,
        'alerts': focusRowScope,
      },
    );
    final snapshot = Sh06Snapshot.fromResponse(focusResponse);
    expect(snapshot.scope.focusId, 'subject-private-6');
    expect(snapshot.items, hasLength(3));
    expect(snapshot.items[0].kind, Sh06ItemKind.task);
    expect(snapshot.items[1].kind, Sh06ItemKind.notification);
    expect(snapshot.items[2].kind, Sh06ItemKind.alert);
    expect(snapshot.items[0].evidenceLinked, isTrue);

    final focusedRowInGlobal = <String, dynamic>{
      ..._readyResponse,
      'data': {
        'tasks': [
          {
            'id': 'focused-task',
            'title': '聚焦范围待办',
            'projection': sharedProjection(
              scope: {
                'mode': 'FOCUS',
                'domain_id': 'CTH',
                'subject_id': 'focused-subject',
              },
              originVerified: true,
            ),
          },
        ],
      },
    };
    expect(Sh06Snapshot.fromResponse(focusedRowInGlobal).items, isEmpty);

    final missingScope = Map<String, dynamic>.from(_readyResponse);
    final missingScopeData = Map<String, dynamic>.from(
      _readyResponse['data'] as Map,
    );
    final missingScopeRow = Map<String, dynamic>.from(
      (missingScopeData['tasks'] as List).first as Map,
    )..remove('projection');
    missingScopeData['tasks'] = [missingScopeRow];
    missingScopeData['notifications'] = <Map<String, dynamic>>[];
    missingScopeData['alerts'] = <Map<String, dynamic>>[];
    missingScope['data'] = missingScopeData;
    expect(Sh06Snapshot.fromResponse(missingScope).items, isEmpty);

    final missingPermission = Map<String, dynamic>.from(_readyResponse);
    final missingPermissionData = Map<String, dynamic>.from(
      _readyResponse['data'] as Map,
    );
    final missingPermissionRow = Map<String, dynamic>.from(
      (missingPermissionData['tasks'] as List).first as Map,
    );
    final missingPermissionProjection = Map<String, dynamic>.from(
      missingPermissionRow['projection'] as Map,
    )..['read_allowed'] = false;
    missingPermissionRow['projection'] = missingPermissionProjection;
    missingPermissionData['tasks'] = [missingPermissionRow];
    missingPermissionData['notifications'] = <Map<String, dynamic>>[];
    missingPermissionData['alerts'] = <Map<String, dynamic>>[];
    missingPermission['data'] = missingPermissionData;
    expect(Sh06Snapshot.fromResponse(missingPermission).items, isEmpty);

    final missingIntegrity = Map<String, dynamic>.from(_readyResponse);
    final missingIntegrityData = Map<String, dynamic>.from(
      _readyResponse['data'] as Map,
    );
    final missingIntegrityRow = Map<String, dynamic>.from(
      (missingIntegrityData['tasks'] as List).first as Map,
    );
    final missingIntegrityProjection = Map<String, dynamic>.from(
      missingIntegrityRow['projection'] as Map,
    );
    missingIntegrityProjection['integrity'] = <String, dynamic>{
      ...(missingIntegrityProjection['integrity'] as Map),
      'integrity_version': 1,
    };
    missingIntegrityRow['projection'] = missingIntegrityProjection;
    missingIntegrityData['tasks'] = [missingIntegrityRow];
    missingIntegrityData['notifications'] = <Map<String, dynamic>>[];
    missingIntegrityData['alerts'] = <Map<String, dynamic>>[];
    missingIntegrity['data'] = missingIntegrityData;
    expect(Sh06Snapshot.fromResponse(missingIntegrity).items, isEmpty);

    final crossSubject = sharedResponseWithRowScopes(
      _readyResponse,
      pageScope: focusPageScope,
      rowScopes: {
        'tasks': {
          'mode': 'FOCUS',
          'domain_id': 'CTH',
          'subject_id': 'different-subject',
        },
      },
    );
    expect(Sh06Snapshot.fromResponse(crossSubject).items, isEmpty);
  });
}

Widget _app(
  Sh06Repository repository, {
  Locale locale = const Locale('zh', 'CN'),
}) => sharedTestApp(
  Sh06Screen(client: LumenisCoreClient(), repository: repository),
  locale: locale,
);

class _FakeSh06Repository implements Sh06Repository {
  _FakeSh06Repository(this.response);

  final Map<String, dynamic> response;

  @override
  Future<Sh06Snapshot> loadInbox() async => Sh06Snapshot.fromResponse(response);
}

class _RecoveringSh06Repository implements Sh06Repository {
  _RecoveringSh06Repository(this.statusCode);

  final int statusCode;
  int calls = 0;

  @override
  Future<Sh06Snapshot> loadInbox() async {
    calls++;
    if (calls == 1) {
      throw LumenisCoreException(
        'HTTP $statusCode private access failure',
        statusCode: statusCode,
      );
    }
    return Sh06Snapshot.fromResponse(_readyResponse);
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

final _readyResponse = sharedRuntimeResponse('SH-06', {
  'operational_state': 'READY',
  'tasks': [
    {
      'id': 'PRIVATE-ID',
      'title': '核对一条资料',
      'detail': '确认资料是否已经完成来源核对。',
      'source_label': '资料收集',
      'priority': 'HIGH',
      'state': 'OPEN',
      'due': '2026-09-23',
      'projection': sharedProjection(
        scope: {'mode': 'GLOBAL_ALL'},
        originVerified: true,
      ),
      'origin_verified': true,
      'scope_verified': true,
      'evidence_linked': true,
      'permission': {'read': true, 'decision': 'ALLOW'},
      'lineage_verified': true,
      'integrity_verified': true,
      'scope': {'mode': 'GLOBAL_ALL', 'global': true},
      'provider': '内部服务',
    },
  ],
  'notifications': [
    {
      'id': 'notification-private',
      'title': '资料已更新',
      'detail': '有一条已核实资料可以查看。',
      'source_label': '资料收集',
      'priority': 'LOW',
      'state': 'OPEN',
      'projection': sharedProjection(
        scope: {'mode': 'GLOBAL_ALL'},
        originVerified: true,
      ),
      'origin_verified': true,
      'scope_verified': true,
      'evidence_linked': true,
      'permission': {'read': true, 'decision': 'ALLOW'},
      'lineage_verified': true,
      'integrity_verified': true,
      'scope': {'mode': 'GLOBAL_ALL', 'global': true},
    },
  ],
  'alerts': [
    {
      'id': 'alert-private',
      'title': '一项资料暂时离线',
      'detail': '资料源暂时离线，稍后再试。',
      'source_label': '资料收集',
      'priority': 'MEDIUM',
      'state': 'BLOCKED',
      'projection': sharedProjection(
        scope: {'mode': 'GLOBAL_ALL'},
        originVerified: true,
      ),
      'origin_verified': true,
      'scope_verified': true,
      'evidence_linked': true,
      'permission': {'read': true, 'decision': 'ALLOW'},
      'lineage_verified': true,
      'integrity_verified': true,
      'scope': {'mode': 'GLOBAL_ALL', 'global': true},
    },
  ],
});
