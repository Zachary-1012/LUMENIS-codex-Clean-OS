import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/core/lumenis_theme.dart';
import 'package:lumenis_app/features/bmp06/bmp06_repository.dart';
import 'package:lumenis_app/features/bmp06/bmp06_screen.dart';
import 'package:lumenis_app/features/bmp06/bmp06_snapshot.dart';
import 'package:lumenis_app/features/bmp07/bmp07_repository.dart';
import 'package:lumenis_app/features/bmp07/bmp07_screen.dart';
import 'package:lumenis_app/features/bmp07/bmp07_snapshot.dart';
import 'package:lumenis_app/features/bmp08/bmp08_repository.dart';
import 'package:lumenis_app/features/bmp08/bmp08_screen.dart';
import 'package:lumenis_app/features/bmp08/bmp08_snapshot.dart';
import 'package:lumenis_app/features/bmp09/bmp09_repository.dart';
import 'package:lumenis_app/features/bmp09/bmp09_screen.dart';
import 'package:lumenis_app/features/bmp09/bmp09_snapshot.dart';
import 'package:lumenis_app/features/bmp10/bmp10_repository.dart';
import 'package:lumenis_app/features/bmp10/bmp10_screen.dart';
import 'package:lumenis_app/features/bmp10/bmp10_snapshot.dart';
import 'package:lumenis_app/features/bmp11/bmp11_repository.dart';
import 'package:lumenis_app/features/bmp11/bmp11_screen.dart';
import 'package:lumenis_app/features/bmp11/bmp11_snapshot.dart';
import 'package:lumenis_app/l10n/lumenis_localizations.dart';

void main() {
  group('BMP creation snapshot boundaries', () {
    test('BMP-06 filters foreign and internal content records', () {
      final response = _envelope('BMP-06');
      response['assets'] = [
        {
          'id': 'asset-a',
          'title': '春季主视觉',
          'kind': 'IMAGE',
          'state': 'REVIEW',
          'approval': 'PENDING',
          'brand_id': 'brand-a',
          'evidence_ref': 'source-a',
        },
        {
          'id': 'asset-b',
          'title': '另一个品牌内容',
          'kind': 'IMAGE',
          'state': 'REVIEW',
          'approval': 'PENDING',
          'brand_id': 'brand-b',
          'evidence_ref': 'source-b',
        },
        {
          'id': 'asset-c',
          'title': 'provider status',
          'kind': 'IMAGE',
          'state': 'REVIEW',
          'approval': 'PENDING',
          'brand_id': 'brand-a',
          'evidence_ref': 'source-c',
        },
      ];

      final snapshot = Bmp06Snapshot.fromResponse(response);

      expect(snapshot.assets, hasLength(1));
      expect(snapshot.assets.single.title, '春季主视觉');
      expect(snapshot.canStage('content:publish'), isTrue);
    });

    test('BMP-07 keeps only the focused campaign timeline', () {
      final response = _envelope('BMP-07');
      response['campaign'] = {
        'goal': '春季新品曝光',
        'stage': 'OBSERVED',
        'brand_id': 'brand-a',
        'timeline': [
          {
            'label': '首发',
            'date': '2026-09-20',
            'stage': 'LAUNCHED',
            'brand_id': 'brand-a',
            'evidence_ref': 'source-a',
          },
          {
            'label': '外部活动',
            'date': '2026-09-20',
            'stage': 'LAUNCHED',
            'brand_id': 'brand-b',
            'evidence_ref': 'source-b',
          },
        ],
        'channels': [
          {'name': '短视频', 'brand_id': 'brand-a', 'planned': true},
          {'name': '外部渠道', 'brand_id': 'brand-b', 'planned': true},
        ],
        'planned_roi': 1.4,
        'actual_result': true,
        'actual_evidence_ref': 'result-a',
        'roi': 1.1,
      };

      final campaign = Bmp07Snapshot.fromResponse(response).campaign!;

      expect(campaign.milestones, hasLength(1));
      expect(campaign.channels, hasLength(1));
      expect(campaign.actualRoi, 1.1);
    });

    test(
      'BMP-08 rejects unscoped material and keeps rights gates separate',
      () {
        final response = _envelope('BMP-08');
        response['audio'] = {
          'available': true,
          'brand_id': 'brand-a',
          'evidence_ref': 'audio-a',
        };
        response['versioned'] = true;
        response['rights_ready'] = true;
        response['materials'] = [
          {
            'name': '春季录音',
            'kind': 'AUDIO',
            'brand_id': 'brand-a',
            'evidence_ref': 'source-a',
          },
          {
            'name': '另一个品牌录音',
            'kind': 'AUDIO',
            'brand_id': 'brand-b',
            'evidence_ref': 'source-b',
          },
        ];
        response['outline'] = [
          {
            'title': '开场',
            'timecode': '00:00',
            'brand_id': 'brand-a',
            'evidence_ref': 'source-a',
            'source_evidence_ref': 'source-a',
          },
        ];

        final snapshot = Bmp08Snapshot.fromResponse(response);

        expect(snapshot.materials, hasLength(1));
        expect(snapshot.outline.single.hasSource, isTrue);
        expect(snapshot.audioAvailable, isTrue);
        expect(snapshot.canStage('podcast:render'), isTrue);
      },
    );

    test('BMP-09 accepts actual-result evaluation only', () {
      final response = _envelope('BMP-09');
      response['dimensions'] = [
        {
          'name': '声量',
          'score': 76,
          'movement': 'UP',
          'confidence': 'HIGH',
          'evidence_coverage': 'FULL',
          'source': 'actual_result',
          'brand_id': 'brand-a',
          'evidence_ref': 'result-a',
        },
        {
          'name': '生成建议',
          'score': 100,
          'movement': 'UP',
          'confidence': 'HIGH',
          'evidence_coverage': 'FULL',
          'source': 'ai_opinion',
          'brand_id': 'brand-a',
          'evidence_ref': 'result-b',
        },
      ];
      response['reports'] = [
        {
          'title': '九月评估',
          'period': '2026-09',
          'brand_id': 'brand-a',
          'evidence_ref': 'result-a',
        },
      ];

      final snapshot = Bmp09Snapshot.fromResponse(response);

      expect(snapshot.dimensions, hasLength(1));
      expect(snapshot.dimensions.single.score, 76);
      expect(snapshot.reports, hasLength(1));
      expect(snapshot.canStage('report:write'), isTrue);
    });

    test('BMP-10 never relabels another brand risk as current risk', () {
      final response = _envelope('BMP-10');
      response['risks'] = [
        {
          'title': '负面传播',
          'severity': 'HIGH',
          'recency': '今天',
          'brand_id': 'brand-a',
          'evidence_ref': 'risk-a',
        },
        {
          'title': '其他品牌事件',
          'severity': 'CRITICAL',
          'recency': '今天',
          'brand_id': 'brand-b',
          'evidence_ref': 'risk-b',
        },
      ];
      response['events'] = [
        {
          'title': '已回应',
          'date': '2026-09-21',
          'state': 'MONITORING',
          'brand_id': 'brand-a',
          'evidence_ref': 'event-a',
        },
      ];

      final snapshot = Bmp10Snapshot.fromResponse(response);

      expect(snapshot.risks, hasLength(1));
      expect(snapshot.events, hasLength(1));
      expect(snapshot.canStage('creator:hold'), isTrue);
    });

    test(
      'BMP-11 withholds mismatched benchmark definitions and global scope',
      () {
        final response = _envelope('BMP-11');
        response['rows'] = [
          {
            'dimension': '声量',
            'definition': '同周期公开提及量',
            'self': 76,
            'comparable': true,
            'brand_id': 'brand-a',
            'evidence_ref': 'self-a',
            'competitors': [
              {
                'brand_id': 'brand-b',
                'name': '品牌乙',
                'value': 61,
                'comparable': true,
                'definition': '同周期公开提及量',
                'evidence_ref': 'competitor-b',
              },
              {
                'brand_id': 'brand-c',
                'name': '品牌丙',
                'value': 99,
                'comparable': true,
                'definition': '不同口径',
                'evidence_ref': 'competitor-c',
              },
            ],
          },
          {
            'dimension': '外部指标',
            'definition': '另一个范围',
            'self': 900,
            'comparable': true,
            'brand_id': 'brand-b',
            'evidence_ref': 'foreign',
            'competitors': [],
          },
        ];

        final snapshot = Bmp11Snapshot.fromResponse(response);

        expect(snapshot.rows, hasLength(1));
        expect(snapshot.rows.single.competitors, hasLength(1));
        expect(snapshot.rows.single.competitors.single.name, '品牌乙');
      },
    );

    test('every slice fails closed when read authorization is incomplete', () {
      final response = _envelope('BMP-06');
      response['assets'] = [
        {
          'id': 'asset-a',
          'title': '不应展示',
          'kind': 'IMAGE',
          'state': 'REVIEW',
          'approval': 'PENDING',
          'brand_id': 'brand-a',
          'evidence_ref': 'source-a',
        },
      ];
      (response['binding'] as Map<String, dynamic>)['read_access'] = 'PENDING';

      final snapshot = Bmp06Snapshot.fromResponse(response);

      expect(snapshot.isScopeApproved, isFalse);
      expect(snapshot.assets, isEmpty);
      expect(snapshot.canStage('content:publish'), isFalse);
    });

    test('v2 scope, read and Evidence contract is mandatory', () {
      final response = _envelope('BMP-06');
      final binding = response['binding'] as Map<String, dynamic>;

      binding['scope_read_evidence_version'] = 'v1';
      expect(Bmp06Snapshot.fromResponse(response).isScopeApproved, isFalse);

      binding['scope_read_evidence_version'] = 'v2';
      binding['read_access'] = 'PENDING';
      expect(Bmp06Snapshot.fromResponse(response).isScopeApproved, isFalse);
    });

    test(
      'explicit GLOBAL_ALL keeps a global collection separate from focus data',
      () {
        final bmp06Response = _globalEnvelope('BMP-06');
        bmp06Response['assets'] = [
          {
            'id': 'global-asset',
            'title': '全球内容版本',
            'kind': 'COPY',
            'state': 'APPROVED',
            'approval': 'APPROVED',
            'brand_id': null,
            'scope': 'GLOBAL_ALL',
            'evidence_ref': 'global-source',
          },
        ];
        final global06 = Bmp06Snapshot.fromResponse(bmp06Response);
        expect(global06.scope.isGlobal, isTrue);
        expect(global06.assets, hasLength(1));

        final bmp07Response = _globalEnvelope('BMP-07');
        bmp07Response['campaign'] = {
          'scope': 'GLOBAL_ALL',
          'brand_id': null,
          'goal': '全球品牌活动',
          'stage': 'MEASURED',
          'timeline': [
            {
              'label': '全球观察',
              'date': '2026-09-20',
              'stage': 'OBSERVED',
              'brand_id': null,
              'scope': 'GLOBAL_ALL',
              'evidence_ref': 'global-source',
            },
          ],
          'channels': [
            {
              'name': '全球渠道',
              'brand_id': null,
              'scope': 'GLOBAL_ALL',
              'planned': true,
              'budgeted': true,
            },
          ],
        };
        final global07 = Bmp07Snapshot.fromResponse(bmp07Response);
        expect(global07.scope.isGlobal, isTrue);
        expect(global07.campaign!.milestones, hasLength(1));
        expect(global07.campaign!.channels, hasLength(1));

        final bmp08Response = _globalEnvelope('BMP-08');
        bmp08Response['audio'] = {
          'available': true,
          'brand_id': null,
          'scope': 'GLOBAL_ALL',
          'evidence_ref': 'global-audio',
        };
        bmp08Response['materials'] = [
          {
            'name': '全球音频',
            'kind': 'AUDIO',
            'brand_id': null,
            'scope': 'GLOBAL_ALL',
            'evidence_ref': 'global-source',
          },
        ];
        bmp08Response['outline'] = [
          {
            'title': '全球开场',
            'timecode': '00:00',
            'brand_id': null,
            'scope': 'GLOBAL_ALL',
            'evidence_ref': 'global-source',
            'source_evidence_ref': 'global-source',
          },
        ];
        final global08 = Bmp08Snapshot.fromResponse(bmp08Response);
        expect(global08.scope.isGlobal, isTrue);
        expect(global08.audioAvailable, isTrue);
        expect(global08.materials, hasLength(1));
        expect(global08.outline, hasLength(1));

        final bmp09Response = _globalEnvelope('BMP-09');
        bmp09Response['dimensions'] = [
          {
            'name': '全球声量',
            'score': 72,
            'movement': 'FLAT',
            'confidence': 'MEDIUM',
            'evidence_coverage': 'FULL',
            'source': 'verified_result',
            'brand_id': null,
            'scope': 'GLOBAL_ALL',
            'evidence_ref': 'global-result',
          },
        ];
        bmp09Response['reports'] = [
          {
            'title': '全球评估',
            'period': '2026-09',
            'brand_id': null,
            'scope': 'GLOBAL_ALL',
            'evidence_ref': 'global-result',
          },
        ];
        final global09 = Bmp09Snapshot.fromResponse(bmp09Response);
        expect(global09.scope.isGlobal, isTrue);
        expect(global09.dimensions, hasLength(1));
        expect(global09.reports, hasLength(1));

        final bmp10Response = _globalEnvelope('BMP-10');
        bmp10Response['risks'] = [
          {
            'title': '全球风险',
            'severity': 'MEDIUM',
            'recency': '本周',
            'brand_id': null,
            'scope': 'GLOBAL_ALL',
            'evidence_ref': 'global-risk',
          },
        ];
        bmp10Response['events'] = [
          {
            'title': '全球回应',
            'date': '2026-09-21',
            'state': 'MONITORING',
            'brand_id': null,
            'scope': 'GLOBAL_ALL',
            'evidence_ref': 'global-event',
          },
        ];
        final global10 = Bmp10Snapshot.fromResponse(bmp10Response);
        expect(global10.scope.isGlobal, isTrue);
        expect(global10.risks, hasLength(1));
        expect(global10.events, hasLength(1));

        final bmp11Response = _globalEnvelope('BMP-11');
        bmp11Response['rows'] = [
          {
            'dimension': '全球声量',
            'definition': '同周期全球公开提及量',
            'self': 72,
            'comparable': true,
            'brand_id': null,
            'scope_mode': 'GLOBAL_ALL',
            'evidence_ref': 'global-result',
            'competitors': [
              {
                'brand_id': 'brand-b',
                'name': '品牌乙',
                'value': 68,
                'comparable': true,
                'definition': '同周期全球公开提及量',
                'evidence_ref': 'global-competitor',
              },
            ],
          },
        ];
        final global11 = Bmp11Snapshot.fromResponse(bmp11Response);
        expect(global11.scope.isGlobal, isTrue);
        expect(global11.rows, hasLength(1));
        expect(global11.rows.single.hasComparableCompetitors, isTrue);
      },
    );
  });

  testWidgets('BMP-06 wide production board stages publish without writing', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1280, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      _app(
        Bmp06Screen(
          client: LumenisCoreClient(),
          repository: _Bmp06Fake(_approvedBmp06),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('草稿'), findsOneWidget);
    expect(find.text('版本检查'), findsOneWidget);
    expect(find.text('春季主视觉'), findsNWidgets(2));
    expect(find.text('已交付'), findsOneWidget);

    await tester.tap(find.text('保存发布请求草稿'));
    await tester.pump();

    expect(find.text('本地内容请求草稿已保存；尚未创建、提交或发布任何内容。'), findsOneWidget);
    expect(find.text('这里仅保存本地请求草稿；内容不会发布，直到授权、审批与明确结果都准备好。'), findsOneWidget);
    expect(find.text('已发布'), findsNothing);
    expect(find.textContaining('发布成功'), findsNothing);
    _expectNoDeveloperCopy(tester);
  });

  testWidgets('BMP-07 mobile keeps lifecycle and actual outcome separate', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      _app(
        Bmp07Screen(
          client: LumenisCoreClient(),
          repository: _Bmp07Fake(_approvedBmp07),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('活动目标'), findsOneWidget);
    expect(find.text('活动推进'), findsOneWidget);
    expect(find.text('计划结果'), findsOneWidget);
    expect(find.text('实际结果'), findsOneWidget);
    expect(find.text('等待真实结果'), findsNothing);

    await tester.ensureVisible(find.text('保存结束活动草稿'));
    await tester.tap(find.text('保存结束活动草稿'));
    await tester.pump();

    expect(find.text('本地活动请求草稿已保存；尚未追加内容或结束活动。'), findsOneWidget);
    expect(find.text('活动已结束'), findsNothing);
    expect(find.textContaining('结束成功'), findsNothing);
    _expectNoDeveloperCopy(tester);
  });

  testWidgets(
    'BMP-08 desktop exposes audio, script and rights as separate work',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(1280, 900));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      await tester.pumpWidget(
        _app(
          Bmp08Screen(
            client: LumenisCoreClient(),
            repository: _Bmp08Fake(_approvedBmp08),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('音频舞台'), findsOneWidget);
      expect(find.text('逐字稿与分段'), findsOneWidget);
      expect(find.text('版权与版本'), findsOneWidget);
      expect(find.textContaining('春季录音'), findsOneWidget);

      await tester.tap(find.text('保存渲染请求草稿'));
      await tester.pump();

      expect(find.text('本地制作请求草稿已保存；尚未生成脚本或渲染成片。'), findsOneWidget);
      expect(find.text('成片已生成'), findsNothing);
      expect(find.textContaining('已渲染'), findsNothing);
      _expectNoDeveloperCopy(tester);
    },
  );

  testWidgets('BMP-09 wide evaluation keeps report request staged', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1200, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      _app(
        Bmp09Screen(
          client: LumenisCoreClient(),
          repository: _Bmp09Fake(_approvedBmp09),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('品牌评估矩阵'), findsOneWidget);
    expect(find.text('评估报告'), findsOneWidget);
    expect(find.text('声量'), findsOneWidget);

    await tester.tap(find.text('准备评估报告请求'));
    await tester.pump();

    expect(
      find.text('评估报告请求仅在当前页面暂时准备；刷新或离开后会清除，尚未生成或写入任何报告。'),
      findsOneWidget,
    );
    expect(find.text('评估报告已生成'), findsNothing);
    expect(find.textContaining('报告已写入'), findsNothing);
    _expectNoDeveloperCopy(tester);
  });

  testWidgets('BMP-10 mobile recomposes risk field into queue and timeline', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      _app(
        Bmp10Screen(
          client: LumenisCoreClient(),
          repository: _Bmp10Fake(_approvedBmp10),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('事件现场'), findsOneWidget);
    expect(find.text('回应时间线'), findsOneWidget);
    expect(find.text('负面传播'), findsOneWidget);
    expect(find.textContaining('高风险'), findsOneWidget);

    await tester.ensureVisible(find.text('保存暂停合作草稿'));
    await tester.tap(find.text('保存暂停合作草稿'));
    await tester.pump();

    expect(find.text('本地处置请求草稿已保存；尚未暂停合作或发送回应。'), findsOneWidget);
    expect(find.text('合作已暂停'), findsNothing);
    expect(find.textContaining('回应已发送'), findsNothing);
    _expectNoDeveloperCopy(tester);
  });

  testWidgets(
    'BMP-11 mobile shows definition-led comparison and withheld row',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(390, 844));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      await tester.pumpWidget(
        _app(
          Bmp11Screen(
            client: LumenisCoreClient(),
            repository: _Bmp11Fake(_approvedBmp11),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('品牌对比'), findsOneWidget);
      expect(find.text('声量'), findsOneWidget);
      expect(find.text('同周期公开提及量'), findsOneWidget);
      expect(find.text('该项目的定义或记录来源尚未对齐，暂不比较。'), findsOneWidget);
      _expectNoDeveloperCopy(tester);
    },
  );

  testWidgets('BMP-11 global collection does not require a brand selection', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      _app(
        Bmp11Screen(
          client: LumenisCoreClient(),
          repository: _Bmp11Fake(_approvedGlobalBmp11),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('全球品牌范围'), findsOneWidget);
    expect(find.text('全球品牌集合'), findsOneWidget);
    expect(find.text('当前品牌'), findsNothing);
    _expectNoDeveloperCopy(tester);
  });

  final recoveryCases = <_RecoveryCase>[
    (
      name: 'BMP-06',
      create: (statusCode) {
        final repository = _Bmp06Fake(
          _approvedBmp06,
          firstFailureStatus: statusCode,
        );
        return (
          screen: Bmp06Screen(
            client: LumenisCoreClient(),
            repository: repository,
          ),
          repository: repository,
        );
      },
    ),
    (
      name: 'BMP-07',
      create: (statusCode) {
        final repository = _Bmp07Fake(
          _approvedBmp07,
          firstFailureStatus: statusCode,
        );
        return (
          screen: Bmp07Screen(
            client: LumenisCoreClient(),
            repository: repository,
          ),
          repository: repository,
        );
      },
    ),
    (
      name: 'BMP-08',
      create: (statusCode) {
        final repository = _Bmp08Fake(
          _approvedBmp08,
          firstFailureStatus: statusCode,
        );
        return (
          screen: Bmp08Screen(
            client: LumenisCoreClient(),
            repository: repository,
          ),
          repository: repository,
        );
      },
    ),
    (
      name: 'BMP-09',
      create: (statusCode) {
        final repository = _Bmp09Fake(
          _approvedBmp09,
          firstFailureStatus: statusCode,
        );
        return (
          screen: Bmp09Screen(
            client: LumenisCoreClient(),
            repository: repository,
          ),
          repository: repository,
        );
      },
    ),
    (
      name: 'BMP-10',
      create: (statusCode) {
        final repository = _Bmp10Fake(
          _approvedBmp10,
          firstFailureStatus: statusCode,
        );
        return (
          screen: Bmp10Screen(
            client: LumenisCoreClient(),
            repository: repository,
          ),
          repository: repository,
        );
      },
    ),
    (
      name: 'BMP-11',
      create: (statusCode) {
        final repository = _Bmp11Fake(
          _approvedBmp11,
          firstFailureStatus: statusCode,
        );
        return (
          screen: Bmp11Screen(
            client: LumenisCoreClient(),
            repository: repository,
          ),
          repository: repository,
        );
      },
    ),
  ];

  const recoveryLocales = [
    (
      locale: Locale('zh', 'CN'),
      authentication: '当前内容暂时无法打开',
      permission: '当前内容不可访问',
      detail: '可重试读取，或返回后稍后再试。',
      forbiddenTerms: ['登录', '账号', '账户', '检查连接', '检查网络'],
    ),
    (
      locale: Locale('en'),
      authentication: 'This content cannot be opened right now.',
      permission: 'This content is not accessible.',
      detail: 'You can retry reading it or return and try again later.',
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
      authentication: '현재 콘텐츠를 지금 열 수 없습니다.',
      permission: '현재 콘텐츠에 접근할 수 없습니다.',
      detail: '다시 읽기를 시도하거나 돌아간 뒤 나중에 다시 시도할 수 있습니다.',
      forbiddenTerms: ['로그인', '계정', '연결을 확인'],
    ),
  ];

  for (final recoveryCase in recoveryCases) {
    testWidgets(
      '${recoveryCase.name} distinguishes access failures and recovers on retry in all locales',
      (tester) async {
        for (final copy in recoveryLocales) {
          for (final statusCode in [401, 403]) {
            await tester.pumpWidget(const SizedBox.shrink());
            await tester.pump();
            final attempt = recoveryCase.create(statusCode);
            await tester.pumpWidget(_app(attempt.screen, locale: copy.locale));
            await tester.pumpAndSettle();

            final expectedTitle = statusCode == 401
                ? copy.authentication
                : copy.permission;
            expect(find.text(expectedTitle), findsOneWidget);
            expect(find.text(copy.detail), findsOneWidget);
            _expectNoAuthOrNetworkAdvice(tester, copy.forbiddenTerms);
            final retryAction = find.byType(OutlinedButton);
            expect(retryAction, findsOneWidget);

            await tester.ensureVisible(retryAction);
            await tester.tap(retryAction);
            await tester.pumpAndSettle();

            expect(attempt.repository.calls, 2);
            expect(find.text(expectedTitle), findsNothing);
            expect(find.text(copy.detail), findsNothing);
            expect(tester.takeException(), isNull);
          }
        }
      },
    );
  }
}

Widget _app(Widget child, {Locale locale = const Locale('zh', 'CN')}) {
  return MaterialApp(
    theme: LumenisTheme.dark,
    locale: locale,
    supportedLocales: LumenisLocalizations.supportedLocales,
    localizationsDelegates: const [
      LumenisLocalizations.delegate,
      GlobalMaterialLocalizations.delegate,
      GlobalWidgetsLocalizations.delegate,
      GlobalCupertinoLocalizations.delegate,
    ],
    home: Scaffold(body: child),
  );
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

void _expectNoDeveloperCopy(WidgetTester tester) {
  for (final term in const [
    'Core',
    'Canonical Data',
    'Evidence',
    'Permission',
    'BrandFocus',
    'binding',
    'actor',
    'scope',
    'provider',
    'API',
  ]) {
    expect(find.textContaining(term), findsNothing, reason: 'UI leaked $term');
  }
}

Map<String, dynamic> _envelope(String screen) => {
  'ok': true,
  'screen': screen,
  'source': 'runtime',
  'bound': true,
  'truth': {'data_state': 'READY'},
  'focus_context': {
    'mode': 'FOCUS',
    'brand_id': 'brand-a',
    'display_name': {'zh-CN': '山海品牌'},
  },
  'binding': {
    'scope_read_evidence_version': 'v2',
    'evidence_lineage_version': 'v2',
    'scope_mode': 'FOCUS',
    'brand_id': 'brand-a',
    'read_access': 'ALLOWED',
    'global_read': 'NONE',
    'granted_permissions': [
      'content:publish',
      'campaign:write',
      'campaign:close',
      'podcast:render',
      'podcast:draft',
      'report:write',
      'creator:hold',
      'response:draft',
    ],
  },
};

Map<String, dynamic> _globalEnvelope(String screen) {
  final response = _envelope(screen);
  response['focus_context'] = {
    'mode': 'GLOBAL_ALL',
    'brand_id': null,
    'display_name': {'zh-CN': '全球品牌集合'},
  };
  final binding = Map<String, dynamic>.from(response['binding'] as Map);
  binding['scope_mode'] = 'GLOBAL_ALL';
  binding['brand_id'] = null;
  binding['global_read'] = 'ALL_GRANTED';
  response['binding'] = binding;
  return response;
}

final _focus06 = const Bmp06Scope(
  mode: 'FOCUS',
  brandId: 'brand-a',
  displayNames: {'zh-CN': '山海品牌'},
);

final _focus07 = const Bmp07Scope(
  mode: 'FOCUS',
  brandId: 'brand-a',
  displayNames: {'zh-CN': '山海品牌'},
);

final _focus08 = const Bmp08Scope(
  mode: 'FOCUS',
  brandId: 'brand-a',
  displayNames: {'zh-CN': '山海品牌'},
);

final _focus09 = const Bmp09Scope(
  mode: 'FOCUS',
  brandId: 'brand-a',
  displayNames: {'zh-CN': '山海品牌'},
);

final _focus10 = const Bmp10Scope(
  mode: 'FOCUS',
  brandId: 'brand-a',
  displayNames: {'zh-CN': '山海品牌'},
);

final _focus11 = const Bmp11Scope(
  mode: 'FOCUS',
  brandId: 'brand-a',
  displayNames: {'zh-CN': '山海品牌'},
);

final _approvedBmp06 = Bmp06Snapshot(
  contractBound: true,
  dataState: 'READY',
  scope: _focus06,
  scopeVerified: true,
  permissionGranted: true,
  evidenceLineageVerified: true,
  globalAllGranted: false,
  grantedPermissions: const {'content:publish'},
  assets: const [
    Bmp06Asset(
      id: 'asset-a',
      title: '春季主视觉',
      kind: 'IMAGE',
      state: 'REVIEW',
      approval: 'PENDING',
      brandId: 'brand-a',
    ),
  ],
);

final _approvedBmp07 = Bmp07Snapshot(
  contractBound: true,
  dataState: 'READY',
  scope: _focus07,
  scopeApproved: true,
  grantedPermissions: const {'campaign:write', 'campaign:close'},
  campaign: Bmp07Campaign(
    goal: '春季新品曝光',
    stage: 'OBSERVED',
    milestones: const [
      Bmp07Milestone(label: '首发', date: '2026-09-20', stage: 'LAUNCHED'),
    ],
    channels: const [Bmp07Channel(name: '短视频', planned: true, budgeted: true)],
    plannedRoi: 1.4,
    actualRoi: 1.1,
  ),
);

final _approvedBmp08 = Bmp08Snapshot(
  contractBound: true,
  dataState: 'READY',
  scope: _focus08,
  scopeApproved: true,
  audioAvailable: true,
  versioned: true,
  rightsReady: true,
  materials: const [
    Bmp08Material(name: '春季录音', kind: 'AUDIO', brandId: 'brand-a'),
  ],
  outline: const [
    Bmp08OutlineSection(title: '开场', timecode: '00:00', hasSource: true),
  ],
  grantedPermissions: const {'podcast:draft', 'podcast:render'},
);

final _approvedBmp09 = Bmp09Snapshot(
  contractBound: true,
  dataState: 'READY',
  scope: _focus09,
  scopeApproved: true,
  dimensions: const [
    Bmp09Dimension(
      name: '声量',
      score: 76,
      movement: 'UP',
      confidence: 'HIGH',
      evidenceCoverage: 'FULL',
    ),
  ],
  reports: const [Bmp09Report(title: '九月评估', period: '2026-09')],
  grantedPermissions: const {'report:write'},
);

final _approvedBmp10 = Bmp10Snapshot(
  contractBound: true,
  dataState: 'READY',
  scope: _focus10,
  scopeApproved: true,
  risks: const [Bmp10Risk(title: '负面传播', severity: 'HIGH', recency: '今天')],
  events: const [
    Bmp10Event(title: '已回应', date: '2026-09-21', state: 'MONITORING'),
  ],
  grantedPermissions: const {'creator:hold', 'response:draft'},
);

final _approvedBmp11 = Bmp11Snapshot(
  contractBound: true,
  dataState: 'READY',
  scope: _focus11,
  scopeApproved: true,
  rows: const [
    Bmp11BenchmarkRow(
      dimension: '声量',
      definition: '同周期公开提及量',
      selfValue: 76,
      comparable: true,
      competitors: [
        Bmp11Competitor(
          brandId: 'brand-b',
          name: '品牌乙',
          value: 61,
          comparable: true,
        ),
      ],
    ),
    Bmp11BenchmarkRow(
      dimension: '口碑',
      definition: '同周期正向反馈比例',
      selfValue: 0,
      comparable: false,
      competitors: [
        Bmp11Competitor(
          brandId: 'brand-b',
          name: '品牌乙',
          value: 70,
          comparable: false,
        ),
      ],
    ),
  ],
);

final _approvedGlobalBmp11 = Bmp11Snapshot(
  contractBound: true,
  dataState: 'READY',
  scope: const Bmp11Scope(
    mode: 'GLOBAL_ALL',
    brandId: null,
    displayNames: {'zh-CN': '全球品牌集合'},
  ),
  scopeApproved: true,
  rows: const [
    Bmp11BenchmarkRow(
      dimension: '全球声量',
      definition: '同周期全球公开提及量',
      selfValue: 72,
      comparable: true,
      competitors: [
        Bmp11Competitor(
          brandId: 'brand-b',
          name: '品牌乙',
          value: 68,
          comparable: true,
        ),
      ],
    ),
  ],
);

typedef _RecoveryCase = ({
  String name,
  ({Widget screen, _RecoveryRepository repository}) Function(int statusCode)
  create,
});

abstract interface class _RecoveryRepository {
  int get calls;
}

abstract class _ScriptedRead<T> implements _RecoveryRepository {
  _ScriptedRead(this.snapshot, {this.firstFailureStatus});

  final T snapshot;
  final int? firstFailureStatus;
  @override
  int calls = 0;

  Future<T> load() async {
    calls++;
    final statusCode = firstFailureStatus;
    if (calls == 1 && statusCode != null) {
      throw LumenisCoreException(
        'HTTP $statusCode private access failure',
        statusCode: statusCode,
      );
    }
    return snapshot;
  }
}

class _Bmp06Fake extends _ScriptedRead<Bmp06Snapshot>
    implements Bmp06Repository {
  _Bmp06Fake(super.snapshot, {super.firstFailureStatus});
}

class _Bmp07Fake extends _ScriptedRead<Bmp07Snapshot>
    implements Bmp07Repository {
  _Bmp07Fake(super.snapshot, {super.firstFailureStatus});
}

class _Bmp08Fake extends _ScriptedRead<Bmp08Snapshot>
    implements Bmp08Repository {
  _Bmp08Fake(super.snapshot, {super.firstFailureStatus});
}

class _Bmp09Fake extends _ScriptedRead<Bmp09Snapshot>
    implements Bmp09Repository {
  _Bmp09Fake(super.snapshot, {super.firstFailureStatus});
}

class _Bmp10Fake extends _ScriptedRead<Bmp10Snapshot>
    implements Bmp10Repository {
  _Bmp10Fake(super.snapshot, {super.firstFailureStatus});
}

class _Bmp11Fake extends _ScriptedRead<Bmp11Snapshot>
    implements Bmp11Repository {
  _Bmp11Fake(super.snapshot, {super.firstFailureStatus});
}
