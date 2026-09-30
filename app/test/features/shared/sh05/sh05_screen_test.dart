import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/features/shared/sh05/sh05_repository.dart';
import 'package:lumenis_app/features/shared/sh05/sh05_screen.dart';
import 'package:lumenis_app/features/shared/sh05/sh05_snapshot.dart';

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
          final repository = _RecoveringSh05Repository(statusCode);
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
  testWidgets('learning shelves keep version and rollback state visible', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(_app(_FakeSh05Repository(_readyResponse)));
    await tester.pumpAndSettle();

    expect(find.text('学习与评估资产'), findsOneWidget);
    expect(find.text('资产货架'), findsOneWidget);
    expect(find.text('版本档案'), findsOneWidget);
    expect(find.text('内容复盘模板'), findsWidgets);
    expect(find.text('v1.2.0'), findsWidgets);
    expect(find.text('已有可回退版本，但回退仍需人工确认。'), findsOneWidget);
    expect(find.text('learning-private-id'), findsNothing);
    expectNoSharedRawMarkers(tester);
    expect(tester.takeException(), isNull);

    await tester.binding.setSurfaceSize(const Size(390, 844));
    await tester.pumpAndSettle();
    expect(find.text('版本档案'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('unscoped learning history is blocked', (tester) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    final unscoped = <String, dynamic>{
      'ok': true,
      'screen': 'SH-05',
      'source': 'runtime',
      'bound': true,
      'data': {
        'assets': [
          {'id': 'learning-private-id', 'title': '不应显示', 'version': '1.0.0'},
        ],
      },
    };
    await tester.pumpWidget(_app(_FakeSh05Repository(unscoped)));
    await tester.pumpAndSettle();

    expect(find.text('学习资产暂不显示'), findsOneWidget);
    expect(find.text('不应显示'), findsNothing);
    expectNoSharedRawMarkers(tester);
    expect(tester.takeException(), isNull);
  });

  testWidgets('English title uses the existing integration key', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1024, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      _app(_FakeSh05Repository(_readyResponse), locale: const Locale('en')),
    );
    await tester.pumpAndSettle();

    expect(find.text('Learning & Evaluation Assets'), findsOneWidget);
    expect(find.text('Version record'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  test('asset parser requires versioned promotion state and exact focus', () {
    final focusPageScope = <String, dynamic>{
      'mode': 'FOCUS',
      'domain_id': 'BMP',
      'brand_focus_id': 'brand-private-5',
      'display_name': '北极星品牌',
    };
    final focusRowScope = <String, dynamic>{
      'mode': 'FOCUS',
      'domain_id': 'BMP',
      'brand_focus_id': 'brand-private-5',
    };
    final focusResponse = sharedResponseWithRowScopes(
      _readyResponse,
      pageScope: focusPageScope,
      rowScopes: {'assets': focusRowScope},
    );
    final snapshot = Sh05Snapshot.fromResponse(focusResponse);
    expect(snapshot.scope.focusId, 'brand-private-5');
    expect(snapshot.assets.first.version, '1.2.0');
    expect(
      snapshot.assets.first.promotionStatus,
      Sh05PromotionStatus.domainVerified,
    );
    expect(snapshot.assets.first.rollbackAvailable, isTrue);

    expect(
      () =>
          Sh05Snapshot.fromResponse({...focusResponse, 'selection_only': true}),
      throwsA(isA<Sh05ScopeError>()),
    );

    final missingScope = Map<String, dynamic>.from(_readyResponse);
    final missingScopeData = Map<String, dynamic>.from(
      _readyResponse['data'] as Map,
    );
    final missingScopeRow = Map<String, dynamic>.from(
      (missingScopeData['assets'] as List).first as Map,
    )..remove('projection');
    missingScopeData['assets'] = [missingScopeRow];
    missingScope['data'] = missingScopeData;
    expect(Sh05Snapshot.fromResponse(missingScope).assets, isEmpty);

    final missingPermission = Map<String, dynamic>.from(_readyResponse);
    final missingPermissionData = Map<String, dynamic>.from(
      _readyResponse['data'] as Map,
    );
    final missingPermissionRow = Map<String, dynamic>.from(
      (missingPermissionData['assets'] as List).first as Map,
    );
    final missingPermissionProjection = Map<String, dynamic>.from(
      missingPermissionRow['projection'] as Map,
    )..['read_allowed'] = false;
    missingPermissionRow['projection'] = missingPermissionProjection;
    missingPermissionData['assets'] = [missingPermissionRow];
    missingPermission['data'] = missingPermissionData;
    expect(Sh05Snapshot.fromResponse(missingPermission).assets, isEmpty);

    final missingIntegrity = Map<String, dynamic>.from(_readyResponse);
    final missingIntegrityData = Map<String, dynamic>.from(
      _readyResponse['data'] as Map,
    );
    final missingIntegrityRow = Map<String, dynamic>.from(
      (missingIntegrityData['assets'] as List).first as Map,
    );
    final missingIntegrityProjection = Map<String, dynamic>.from(
      missingIntegrityRow['projection'] as Map,
    );
    missingIntegrityProjection['integrity'] = <String, dynamic>{
      ...(missingIntegrityProjection['integrity'] as Map),
      'integrity_version': 1,
    };
    missingIntegrityRow['projection'] = missingIntegrityProjection;
    missingIntegrityData['assets'] = [missingIntegrityRow];
    missingIntegrity['data'] = missingIntegrityData;
    expect(Sh05Snapshot.fromResponse(missingIntegrity).assets, isEmpty);

    final crossSubject = sharedResponseWithRowScopes(
      _readyResponse,
      pageScope: focusPageScope,
      rowScopes: {
        'assets': {
          'mode': 'FOCUS',
          'domain_id': 'BMP',
          'brand_focus_id': 'different-brand',
        },
      },
    );
    expect(Sh05Snapshot.fromResponse(crossSubject).assets, isEmpty);
  });
}

Widget _app(
  Sh05Repository repository, {
  Locale locale = const Locale('zh', 'CN'),
}) => sharedTestApp(
  Sh05Screen(client: LumenisCoreClient(), repository: repository),
  locale: locale,
);

class _FakeSh05Repository implements Sh05Repository {
  _FakeSh05Repository(this.response);

  final Map<String, dynamic> response;

  @override
  Future<Sh05Snapshot> loadAssets() async =>
      Sh05Snapshot.fromResponse(response);
}

class _RecoveringSh05Repository implements Sh05Repository {
  _RecoveringSh05Repository(this.statusCode);

  final int statusCode;
  int calls = 0;

  @override
  Future<Sh05Snapshot> loadAssets() async {
    calls++;
    if (calls == 1) {
      throw LumenisCoreException(
        'HTTP $statusCode private access failure',
        statusCode: statusCode,
      );
    }
    return Sh05Snapshot.fromResponse(_readyResponse);
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

final _readyResponse = sharedRuntimeResponse('SH-05', {
  'assets': [
    {
      'id': 'learning-private-id',
      'title': '内容复盘模板',
      'description': '用于复盘已完成工作的可审阅模板。',
      'kind': 'SOP',
      'version': '1.2.0',
      'promotion_status': 'DOMAIN_VERIFIED',
      'projection': sharedProjection(scope: {'mode': 'GLOBAL_ALL'}),
      'scope_verified': true,
      'evidence_backed': true,
      'permission': {'read': true, 'decision': 'ALLOW'},
      'lineage_verified': true,
      'integrity_verified': true,
      'scope': {'mode': 'GLOBAL_ALL', 'global': true},
      'rollback': {'available': true},
      'review_state': 'VERIFIED',
      'reviewed_at': '2026-09-21',
      'provenance': '人工复核',
      'private_path': r'C:\private\path',
    },
    {
      'id': 'candidate-id',
      'title': '待评估模式',
      'description': '仍需评估的候选模式。',
      'kind': 'PATTERN',
      'version': '0.3.0',
      'promotion_status': 'CANDIDATE',
      'projection': sharedProjection(scope: {'mode': 'GLOBAL_ALL'}),
      'scope_verified': true,
      'evidence_backed': true,
      'permission': {'read': true, 'decision': 'ALLOW'},
      'lineage_verified': true,
      'integrity_verified': true,
      'scope': {'mode': 'GLOBAL_ALL', 'global': true},
      'review_state': 'PENDING',
    },
    {
      'id': 'bad',
      'title': '<script>raw-secret-marker</script>',
      'version': '9.9.9',
      'promotion_status': 'CORE_VERIFIED',
    },
  ],
});
