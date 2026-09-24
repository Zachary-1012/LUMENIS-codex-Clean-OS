import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/features/shared/sh03/sh03_repository.dart';
import 'package:lumenis_app/features/shared/sh03/sh03_screen.dart';
import 'package:lumenis_app/features/shared/sh03/sh03_snapshot.dart';

import '../shared_test_support.dart';

void main() {
  testWidgets('metric explorer has a distinct definition and sample view', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(_app(_FakeSh03Repository(_readyResponse)));
    await tester.pumpAndSettle();

    expect(find.text('Canonical 数据 / 指标浏览器'), findsOneWidget);
    expect(find.text('指标目录'), findsOneWidget);
    expect(find.text('每周有效提及'), findsWidgets);
    expect(find.text('口径与来源'), findsOneWidget);
    expect(find.text('weekly_signal'), findsNothing);
    expect(find.text('METRIC_PRIVATE-ID'), findsNothing);
    expectNoSharedRawMarkers(tester);
    expect(tester.takeException(), isNull);

    await tester.binding.setSurfaceSize(const Size(390, 844));
    await tester.pumpAndSettle();
    expect(find.text('指标目录'), findsOneWidget);
    expect(find.text('口径与来源'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('unscoped metric payload becomes a blocked state', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    final unscoped = <String, dynamic>{
      'ok': true,
      'screen': 'SH-03',
      'source': 'runtime',
      'bound': true,
      'data': {
        'metrics': [
          {
            'name': 'weekly_signal',
            'display_name': '不应显示',
            'definition': '不应显示',
          },
        ],
      },
    };
    await tester.pumpWidget(_app(_FakeSh03Repository(unscoped)));
    await tester.pumpAndSettle();

    expect(find.text('正式数据暂不显示'), findsOneWidget);
    expect(find.text('不应显示'), findsNothing);
    expectNoSharedRawMarkers(tester);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Korean title uses the shared localization integration key', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1024, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      _app(_FakeSh03Repository(_readyResponse), locale: const Locale('ko')),
    );
    await tester.pumpAndSettle();

    expect(find.text('캐노니컬 데이터·지표'), findsOneWidget);
    expect(find.text('지표 목록'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  test('metric parser keeps exact focus and rejects selection-only scope', () {
    final focusPageScope = <String, dynamic>{
      'mode': 'FOCUS',
      'domain_id': 'BMP',
      'brand_focus_id': 'brand-private-4',
      'display_name': '北极星品牌',
    };
    final focusRowScope = <String, dynamic>{
      'mode': 'FOCUS',
      'domain_id': 'BMP',
      'brand_focus_id': 'brand-private-4',
    };
    final focusResponse = sharedResponseWithRowScopes(
      _readyResponse,
      pageScope: focusPageScope,
      rowScopes: {'metrics': focusRowScope},
    );
    final snapshot = Sh03Snapshot.fromResponse(focusResponse);
    expect(snapshot.scope.domain, 'BMP');
    expect(snapshot.scope.focusId, 'brand-private-4');
    expect(snapshot.metrics.single.samples.single.value, '12');
    expect(snapshot.metrics.single.lineage, contains('正式记录'));

    expect(
      () => Sh03Snapshot.fromResponse({
        ...focusResponse,
        'scope': {
          ...focusResponse['scope'] as Map<String, dynamic>,
          'selection_only': true,
        },
      }),
      throwsA(isA<Sh03ScopeError>()),
    );

    final focusedRowInGlobal = <String, dynamic>{
      ..._readyResponse,
      'data': {
        'metrics': [
          {
            'name': 'focused_metric',
            'display_name': '聚焦指标',
            'definition': '聚焦范围定义',
            'projection': sharedProjection(
              scope: {
                'mode': 'FOCUS',
                'domain_id': 'BMP',
                'brand_focus_id': 'focused-brand',
              },
            ),
          },
        ],
      },
    };
    expect(Sh03Snapshot.fromResponse(focusedRowInGlobal).metrics, isEmpty);

    final missingScope = Map<String, dynamic>.from(_readyResponse);
    final missingScopeData = Map<String, dynamic>.from(
      _readyResponse['data'] as Map,
    );
    final missingScopeRow = Map<String, dynamic>.from(
      (missingScopeData['metrics'] as List).first as Map,
    )..remove('projection');
    missingScopeData['metrics'] = [missingScopeRow];
    missingScope['data'] = missingScopeData;
    expect(Sh03Snapshot.fromResponse(missingScope).metrics, isEmpty);

    final missingPermission = Map<String, dynamic>.from(_readyResponse);
    final missingPermissionData = Map<String, dynamic>.from(
      _readyResponse['data'] as Map,
    );
    final missingPermissionRow = Map<String, dynamic>.from(
      (missingPermissionData['metrics'] as List).first as Map,
    );
    final missingPermissionProjection = Map<String, dynamic>.from(
      missingPermissionRow['projection'] as Map,
    )..['read_allowed'] = false;
    missingPermissionRow['projection'] = missingPermissionProjection;
    missingPermissionData['metrics'] = [missingPermissionRow];
    missingPermission['data'] = missingPermissionData;
    expect(Sh03Snapshot.fromResponse(missingPermission).metrics, isEmpty);

    final missingIntegrity = Map<String, dynamic>.from(_readyResponse);
    final missingIntegrityData = Map<String, dynamic>.from(
      _readyResponse['data'] as Map,
    );
    final missingIntegrityRow = Map<String, dynamic>.from(
      (missingIntegrityData['metrics'] as List).first as Map,
    );
    final missingIntegrityProjection = Map<String, dynamic>.from(
      missingIntegrityRow['projection'] as Map,
    );
    missingIntegrityProjection['integrity'] = <String, dynamic>{
      ...(missingIntegrityProjection['integrity'] as Map),
      'integrity_version': 1,
    };
    missingIntegrityRow['projection'] = missingIntegrityProjection;
    missingIntegrityData['metrics'] = [missingIntegrityRow];
    missingIntegrity['data'] = missingIntegrityData;
    expect(Sh03Snapshot.fromResponse(missingIntegrity).metrics, isEmpty);

    final crossSubject = sharedResponseWithRowScopes(
      _readyResponse,
      pageScope: focusPageScope,
      rowScopes: {
        'metrics': {
          'mode': 'FOCUS',
          'domain_id': 'BMP',
          'brand_focus_id': 'different-brand',
        },
      },
    );
    expect(Sh03Snapshot.fromResponse(crossSubject).metrics, isEmpty);
  });
}

Widget _app(
  Sh03Repository repository, {
  Locale locale = const Locale('zh', 'CN'),
}) => sharedTestApp(
  Sh03Screen(client: LumenisCoreClient(), repository: repository),
  locale: locale,
);

class _FakeSh03Repository implements Sh03Repository {
  _FakeSh03Repository(this.response);

  final Map<String, dynamic> response;

  @override
  Future<Sh03Snapshot> loadBrowser() async =>
      Sh03Snapshot.fromResponse(response);
}

final _readyResponse = sharedRuntimeResponse('SH-03', {
  'metrics': [
    {
      'name': 'weekly_signal',
      'metric_id': 'METRIC_PRIVATE-ID',
      'display_name': '每周有效提及',
      'definition': '在确认资料中统计可复核提及的数量',
      'cadence': '每日更新',
      'state': 'READY',
      'derived': true,
      'projection': sharedProjection(
        scope: {'mode': 'GLOBAL_ALL'},
      ),
      'scope_verified': true,
      'evidence_backed': true,
      'permission': {'read': true, 'decision': 'ALLOW'},
      'lineage_verified': true,
      'integrity_verified': true,
      'scope': {'mode': 'GLOBAL_ALL', 'global': true},
      'lineage': ['SOURCE', 'EVIDENCE', 'CANONICAL', 'METRIC', 'VIEWMODEL'],
      'samples': [
        {'label': '本周', 'value': '12', 'time': '2026-09-22'},
      ],
      'provider': 'provider-secret',
    },
    {
      'name': 'bad_metric',
      'display_name': '不应出现',
      'definition': '<script>raw-secret-marker</script>',
    },
  ],
});
