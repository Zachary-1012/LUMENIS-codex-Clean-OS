import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/features/shared/sh06/sh06_repository.dart';
import 'package:lumenis_app/features/shared/sh06/sh06_screen.dart';
import 'package:lumenis_app/features/shared/sh06/sh06_snapshot.dart';

import '../shared_test_support.dart';

void main() {
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
