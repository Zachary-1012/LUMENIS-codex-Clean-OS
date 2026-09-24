import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/features/shared/sh04/sh04_repository.dart';
import 'package:lumenis_app/features/shared/sh04/sh04_screen.dart';
import 'package:lumenis_app/features/shared/sh04/sh04_snapshot.dart';

import '../shared_test_support.dart';

void main() {
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

final _readyResponse = sharedRuntimeResponse('SH-04', {
  'exports': [
    {
      'id': 'export-private-id',
      'title': '周报预览',
      'format': 'markdown',
      'state': 'READY',
      'projection': sharedProjection(
        scope: {'mode': 'GLOBAL_ALL'},
      ),
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
      'projection': sharedProjection(
        scope: {'mode': 'GLOBAL_ALL'},
      ),
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
        scope: {
          'mode': 'FOCUS',
          'domain_id': 'CTH',
          'subject_id': 'x',
        },
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
