import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/core/lumenis_theme.dart';
import 'package:lumenis_app/features/cth/cth03/cth03_repository.dart';
import 'package:lumenis_app/features/cth/cth03/cth03_screen.dart';
import 'package:lumenis_app/features/cth/cth03/cth03_view_model.dart';
import 'package:lumenis_app/l10n/lumenis_localizations.dart';

import '../cth_test_support.dart';

void main() {
  testWidgets('loading hides stream values and announces the read state', (
    tester,
  ) async {
    final pending = Completer<Cth03ScreenData>();
    await tester.pumpWidget(_app(_PendingRepository(pending.future)));

    expect(find.text('线上服务反馈'), findsNothing);
    expect(find.byType(LinearProgressIndicator), findsOneWidget);
    expect(
      find.byWidgetPredicate(
        (widget) =>
            widget is Semantics &&
            widget.properties.liveRegion == true &&
            (widget.properties.label ?? '').isNotEmpty,
      ),
      findsOneWidget,
    );

    pending.complete(_data());
    await tester.pumpAndSettle();
    expect(find.text('线上服务反馈'), findsOneWidget);
  });

  testWidgets('desktop has separate pulse, channel and stream anatomy', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(_app(_PendingRepository(Future.value(_data()))));
    await tester.pumpAndSettle();

    expect(find.byKey(const ValueKey('cth03/desktop-layout')), findsOneWidget);
    expect(find.byKey(const ValueKey('cth03/pulse-band')), findsOneWidget);
    expect(find.byKey(const ValueKey('cth03/channel-lanes')), findsOneWidget);
    expect(find.byKey(const ValueKey('cth03/record-stream')), findsOneWidget);
    expect(find.text('线上服务反馈'), findsOneWidget);
    expect(find.text('EV-PRIVATE-7'), findsNothing);
    expect(find.text('database.get_notes'), findsNothing);
    _expectNoInternalCopy(tester);
    expect(tester.takeException(), isNull);
  });

  testWidgets('mobile filters the local stream without creating an effect', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(_app(_PendingRepository(Future.value(_data()))));
    await tester.pumpAndSettle();

    expect(find.byKey(const ValueKey('cth03/mobile-layout')), findsOneWidget);
    expect(find.text('线上服务反馈'), findsOneWidget);
    await tester.tap(find.text('社交平台').first);
    await tester.pumpAndSettle();
    expect(find.text('线上服务反馈'), findsNothing);
    expect(find.text('暂无数据'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('publication time keeps source precision and timezone', (
    tester,
  ) async {
    await tester.pumpWidget(
      _app(
        _PendingRepository(
          Future.value(
            _data(
              generatedAt: '2026-09-30T00:11:24',
              records: const [
                Cth03Record(
                  date: '2021-09-10',
                  title: 'date-only record',
                  channel: 'public_http',
                  sentiment: '',
                  risk: '',
                ),
                Cth03Record(
                  date: '2021-08-03T09:50:00Z',
                  title: 'UTC record',
                  channel: 'douyin',
                  sentiment: '',
                  risk: '',
                ),
                Cth03Record(
                  date: '2024-09-12T10:39:28.1234+08:00',
                  title: 'offset record',
                  channel: 'douyin',
                  sentiment: '',
                  risk: '',
                ),
                Cth03Record(
                  date: '2026-06-10T14:16:31.25',
                  title: 'no-zone record',
                  channel: 'public_http',
                  sentiment: '',
                  risk: '',
                ),
              ],
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.textContaining('2021-09-10'), findsOneWidget);
    expect(find.textContaining('2021-08-03 09:50:00 UTC'), findsOneWidget);
    expect(
      find.textContaining('2024-09-12 10:39:28.1234 +08:00'),
      findsOneWidget,
    );
    expect(find.textContaining('2026-06-10 14:16:31.25'), findsOneWidget);
    expect(find.textContaining('2026-09-30 00:11:24'), findsOneWidget);
    expect(find.textContaining('2026-09-30 08:11:24'), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets('missing and malformed publication dates stay explicit', (
    tester,
  ) async {
    await tester.pumpWidget(
      _app(
        _PendingRepository(
          Future.value(
            _data(
              records: const [
                Cth03Record(
                  date: '',
                  title: 'undated record',
                  channel: 'public_http',
                  sentiment: '',
                  risk: '',
                ),
                Cth03Record(
                  date: '2021-02-30T10:00:00Z',
                  title: 'invalid date record',
                  channel: 'public_http',
                  sentiment: '',
                  risk: '',
                ),
              ],
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.textContaining('发布时间 · 未提供'), findsOneWidget);
    expect(find.textContaining('发布时间 · 时间格式无法识别'), findsOneWidget);
    expect(find.textContaining('2021-03-02'), findsNothing);
    expect(
      find.byWidgetPredicate(
        (widget) =>
            widget is Tooltip && widget.message == '2021-02-30T10:00:00Z',
      ),
      findsOneWidget,
    );
    expect(tester.takeException(), isNull);
  });

  testWidgets('source labels are readable while filters retain source keys', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(
      _app(
        _PendingRepository(
          Future.value(
            _data(
              channels: const [
                Cth03Channel(name: 'public_http', status: '最近成功', detail: '只读'),
                Cth03Channel(name: 'douyin', status: '最近成功', detail: '只读'),
                Cth03Channel(name: '', status: '未知', detail: '只读'),
                Cth03Channel(name: '已有来源名称', status: '最近成功', detail: '只读'),
              ],
              records: const [
                Cth03Record(
                  date: '2026-09-10',
                  title: 'public web record',
                  channel: 'public_http',
                  sentiment: '',
                  risk: '',
                ),
                Cth03Record(
                  date: '2026-09-11',
                  title: 'douyin record',
                  channel: 'douyin',
                  sentiment: '',
                  risk: '',
                ),
                Cth03Record(
                  date: '2026-09-12',
                  title: 'unknown source record',
                  channel: '',
                  sentiment: '',
                  risk: '',
                ),
              ],
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('公开网页'), findsWidgets);
    expect(find.text('抖音'), findsWidgets);
    expect(find.text('来源未知'), findsWidgets);
    expect(find.text('已有来源名称'), findsWidgets);
    expect(find.text('public web record'), findsOneWidget);
    expect(find.text('douyin record'), findsOneWidget);
    expect(find.text('unknown source record'), findsOneWidget);

    await tester.tap(find.text('抖音').first);
    await tester.pumpAndSettle();

    expect(find.text('douyin record'), findsOneWidget);
    expect(find.text('public web record'), findsNothing);
    expect(find.text('unknown source record'), findsNothing);
    expect(tester.takeException(), isNull);
  });

  for (final copy in const [
    (
      locale: Locale('zh', 'CN'),
      scope: '查看当前范围内的已采集内容。',
      recent: '近期记录',
      stream: '已采集记录',
      publicWeb: '公开网页',
      douyin: '抖音',
    ),
    (
      locale: Locale('en'),
      scope: 'View collected content within the current scope.',
      recent: 'Recent records',
      stream: 'Collected records',
      publicWeb: 'Public web',
      douyin: 'Douyin',
    ),
    (
      locale: Locale('ko'),
      scope: '현재 범위에서 수집된 콘텐츠를 확인합니다.',
      recent: '최근 기록',
      stream: '수집된 기록',
      publicWeb: '공개 웹',
      douyin: '더우인',
    ),
  ]) {
    testWidgets('renders CTH-03 business copy in ${copy.locale}', (
      tester,
    ) async {
      await tester.pumpWidget(
        _app(
          _PendingRepository(
            Future.value(
              _data(
                channels: const [
                  Cth03Channel(
                    name: 'public_http',
                    status: '最近成功',
                    detail: '只读',
                  ),
                  Cth03Channel(name: 'douyin', status: '最近成功', detail: '只读'),
                ],
              ),
            ),
          ),
          locale: copy.locale,
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text(copy.scope), findsOneWidget);
      expect(find.text(copy.recent), findsOneWidget);
      expect(find.text(copy.stream), findsOneWidget);
      expect(find.text(copy.publicWeb), findsWidgets);
      expect(find.text(copy.douyin), findsWidgets);
      expect(tester.takeException(), isNull);
    });
  }

  testWidgets('focused subject without server binding stays unavailable', (
    tester,
  ) async {
    final failure = Completer<Cth03ScreenData>();
    await tester.pumpWidget(_app(_PendingRepository(failure.future)));
    await tester.pump();
    failure.completeError(
      const Cth03ContextUnavailable(Cth03BlockReason.focusNotBound),
    );
    await tester.pumpAndSettle();
    expect(find.text('经营主体信息暂不可用'), findsOneWidget);
    expect(find.text('线上服务反馈'), findsNothing);
    expect(find.textContaining('页面尚未接入所选范围的数据'), findsOneWidget);
    _expectNoInternalCopy(tester);
  });

  test(
    'the Core repository does not decode an unbound focused aggregate',
    () async {
      final client = _FakeClient(
        contextResponse: const {
          'ok': true,
          'contract': 'lumenis.context.v1',
          'context': {
            'mode': 'FOCUS',
            'domain_id': 'CTH',
            'subject_id': 'SUBJ-7',
          },
        },
        screenResponse: _screenResponse,
      );

      await expectLater(
        CoreCth03Repository(client: client).load(),
        throwsA(
          isA<Cth03ContextUnavailable>().having(
            (error) => error.reason,
            'reason',
            Cth03BlockReason.focusNotBound,
          ),
        ),
      );
    },
  );

  test(
    'a bound global aggregate without grant or lineage is withheld',
    () async {
      final client = _FakeClient(
        contextResponse: _globalContext,
        screenResponse: _screenResponse,
      );

      await expectLater(
        CoreCth03Repository(client: client).load(),
        throwsA(
          isA<Cth03ContextUnavailable>().having(
            (error) => error.reason,
            'reason',
            Cth03BlockReason.pageNotBound,
          ),
        ),
      );
    },
  );

  test('a server-authorized global aggregate can be consumed', () async {
    final client = _FakeClient(
      contextResponse: _globalContext,
      screenResponse: _globalScreenResponse,
    );

    final data = await CoreCth03Repository(client: client).load();

    expect(data.context.mode, 'GLOBAL_ALL');
    expect(data.recentCount.value, 2);
    expect(data.records, isNotEmpty);
  });

  test('an applied Guangzhou Taikoo Hui focus stays focused', () async {
    final client = _FakeClient(
      contextResponse: _guangzhouFocusContext,
      screenResponse: _focusedScreenResponse,
    );

    final data = await CoreCth03Repository(client: client).load();

    expect(data.context.mode, 'FOCUS');
    expect(data.context.subjectId, 'GUANGZHOU_TAIKOO_HUI');
    expect(data.context.displayName?['zh-CN'], '广州太古汇');
    expect(data.records, isNotEmpty);
  });

  test(
    'anonymous records retain partial coverage and uncollected metrics',
    () async {
      final data = await _loadAnonymous(_anonymousResponse());

      expect(data.context.mode, 'GLOBAL_ALL');
      expect(data.records.single.title, '线上服务反馈');
      expect(data.recordState, Cth03DataState.partial);
      expect(data.recentCount.state, Cth03DataState.notCollected);
      expect(data.recentCount.value, isNull);
    },
  );

  test(
    'local scope binding reads proved rows without borrowing a header proof',
    () async {
      final data = await _loadAnonymous(_localScopeResponse());
      expect(data.records.single.title, '线上服务反馈');
      expect(data.recordState, Cth03DataState.partial);
      expect(data.recentCount.value, isNull);
    },
  );

  test(
    'a confirmed empty local view does not need an arbitrary evidence row',
    () async {
      final response = _localScopeResponse();
      final table = (response['sections'] as List).last as Map;
      table['state'] = 'notcollected';
      table['rows'] = <Map<String, Object>>[];
      final data = await _loadAnonymous(response);
      expect(data.records, isEmpty);
      expect(data.recordState, Cth03DataState.notCollected);
      expect(data.recentCount.value, isNull);
    },
  );

  for (final field in [
    'contract',
    'module',
    'policy',
    'actor_scope',
    'subject_id',
    'read_allowed',
    'scope_verified',
    'global_all_granted',
  ]) {
    test('local scope binding rejects an invalid $field', () async {
      final response = _localScopeResponse();
      final binding = response['global_binding'] as Map;
      binding[field] = switch (field) {
        'read_allowed' || 'scope_verified' => false,
        'global_all_granted' => true,
        _ => 'WRONG',
      };
      await expectLater(
        _loadAnonymous(response),
        throwsA(isA<Cth03ContextUnavailable>()),
      );
    });
  }

  for (final subjectId in <String?>[null, 'SUBJECT-RETURNED']) {
    test(
      'existing actor scope reads only its proved view: $subjectId',
      () async {
        final response = _localScopeResponse(subjectId: subjectId);
        final isGlobal = subjectId == null;
        final binding =
            response[isGlobal ? 'global_binding' : 'focus_binding'] as Map;
        binding['policy'] = 'actor-exact-scope-v1';
        binding['actor_scope'] = 'authenticated';
        binding['global_all_granted'] = isGlobal;
        final row =
            (((response['sections'] as List).last as Map)['rows'] as List)
                    .single
                as Map;
        final projection = row['projection'] as Map;
        (projection['scope'] as Map)['global_all_granted'] = isGlobal;
        final repository = CoreCth03Repository(
          client: _FakeClient(
            contextResponse: {
              'ok': true,
              'contract': 'lumenis.context.v1',
              'context': {
                'mode': isGlobal ? 'GLOBAL_ALL' : 'FOCUS',
                if (!isGlobal) 'domain_id': 'CTH',
                if (!isGlobal) 'subject_id': subjectId,
              },
            },
            screenResponse: response,
          ),
        );
        expect((await repository.load()).records, hasLength(1));
        (projection['integrity'] as Map)['verified'] = false;
        expect((await repository.load()).records, isEmpty);
        binding['global_all_granted'] = !isGlobal;
        await expectLater(
          repository.load(),
          throwsA(isA<Cth03ContextUnavailable>()),
        );
        binding['global_all_granted'] = isGlobal;
        binding['actor_scope'] = 'anonymous_read';
        await expectLater(
          repository.load(),
          throwsA(isA<Cth03ContextUnavailable>()),
        );
      },
    );
  }

  test('local scope approval never replaces a row evidence proof', () async {
    final response = _localScopeResponse();
    final row =
        (((response['sections'] as List).last as Map)['rows'] as List).single
            as Map;
    row.remove('projection');
    final data = await _loadAnonymous(response);
    expect(data.records, isEmpty);
    expect(data.recordState, Cth03DataState.blocked);
  });

  test(
    'local focus requires the same subject in the view and stored projection',
    () async {
      const subjectId = 'SUBJECT-RETURNED';
      final response = _localScopeResponse(subjectId: subjectId);
      final client = _FakeClient(
        contextResponse: const {
          'ok': true,
          'contract': 'lumenis.context.v1',
          'context': {
            'mode': 'FOCUS',
            'domain_id': 'CTH',
            'subject_id': subjectId,
          },
        },
        screenResponse: response,
      );
      final repository = CoreCth03Repository(client: client);
      expect((await repository.load()).records, hasLength(1));
      final row =
          (((response['sections'] as List).last as Map)['rows'] as List).single
              as Map;
      ((row['projection'] as Map)['stored_scope'] as Map)['subject_id'] =
          'OTHER';
      expect((await repository.load()).records, isEmpty);
      (response['focus_binding'] as Map)['subject_id'] = 'OTHER';
      await expectLater(
        repository.load(),
        throwsA(isA<Cth03ContextUnavailable>()),
      );
    },
  );

  test(
    'row permission does not authorize a global aggregate or source health',
    () async {
      final response = _anonymousResponse();
      final sections = response['sections'] as List;
      (sections.first as Map)['items'] = [
        {
          'id': 'cth03.recent',
          'state': 'ready',
          'value': 999,
          'projection': _anonymousProjection(),
        },
      ];
      (sections[1] as Map)['items'] = [
        {
          'platform': '公开网页',
          'status': '正常',
          'projection': _anonymousProjection(),
        },
      ];
      final data = await _loadAnonymous(response);

      expect(data.records, hasLength(1));
      expect(data.recentCount.hasValue, isFalse);
      expect(data.recentCount.value, isNull);
      expect(data.channels, isEmpty);
    },
  );

  for (final width in [320.0, 390.0, 1440.0]) {
    for (final includeRejectedRow in [false, true]) {
      testWidgets(
        'partial records remain visibly partial at width $width, rejected=$includeRejectedRow',
        (tester) async {
          await tester.binding.setSurfaceSize(Size(width, 1000));
          addTearDown(() => tester.binding.setSurfaceSize(null));
          final response = _anonymousResponse();
          final table = (response['sections'] as List).last as Map;
          final rows = table['rows'] as List;
          if (includeRejectedRow) {
            rows.add(<String, Object>{
              ...Map<String, Object>.from(rows.single as Map),
              'title': '范围不匹配的记录',
              'subject_id': 'OTHER',
            });
          }

          await tester.pumpWidget(
            _app(
              _ReadRepository(() => _loadAnonymous(response)),
              textScale: 2.0,
            ),
          );
          await tester.pumpAndSettle();

          expect(find.text('部分可用'), findsOneWidget);
          expect(find.text('线上服务反馈'), findsOneWidget);
          expect(find.text('范围不匹配的记录'), findsNothing);
          expect(tester.takeException(), isNull);
        },
      );
    }
  }

  for (final mismatch in [
    'domain',
    'subject',
    'evidence',
    'read',
    'projection_scope',
  ]) {
    test(
      'anonymous stream withholds a row with mismatched $mismatch',
      () async {
        final response = _anonymousResponse();
        final table = (response['sections'] as List).last as Map;
        final row = (table['rows'] as List).single as Map;
        final projection = row['projection'] as Map;
        switch (mismatch) {
          case 'domain':
            (projection['stored_scope'] as Map)['domain_id'] = 'zbmp';
          case 'subject':
            row['subject_id'] = 'SUBJECT-OTHER';
          case 'evidence':
            (projection['integrity'] as Map)['verified'] = false;
          case 'read':
            row['read_allowed'] = false;
          case 'projection_scope':
            (projection['scope'] as Map)['subject_id'] = 'SUBJECT-OTHER';
        }
        final data = await _loadAnonymous(response);
        expect(data.records, isEmpty);
        expect(data.recordState, Cth03DataState.blocked);
      },
    );
  }

  test(
    'anonymous scope must be explicitly allowed and cannot satisfy FOCUS',
    () async {
      final response = _anonymousResponse();
      (response['global_binding'] as Map).remove('actor_scope');
      await expectLater(
        _loadAnonymous(response),
        throwsA(isA<Cth03ContextUnavailable>()),
      );

      await expectLater(
        CoreCth03Repository(
          client: _FakeClient(
            contextResponse: _guangzhouFocusContext,
            screenResponse: _anonymousResponse(),
          ),
        ).load(),
        throwsA(isA<Cth03ContextUnavailable>()),
      );
    },
  );

  for (final status in [401, 403]) {
    testWidgets('a $status response offers retry without a product account', (
      tester,
    ) async {
      var reads = 0;
      final repository = _ReadRepository(() async {
        reads++;
        if (reads == 1) {
          throw LumenisCoreException('withheld', statusCode: status);
        }
        return _data();
      });
      await tester.pumpWidget(_app(repository));
      await tester.pumpAndSettle();
      expect(find.textContaining('登录'), findsNothing);
      expect(find.textContaining('账号'), findsNothing);
      expect(
        find.text(status == 401 ? '运营信息暂不可用，请稍后重试。' : '暂时无法查看'),
        findsOneWidget,
      );
      expect(find.text('线上服务反馈'), findsNothing);
      expect(reads, 1);
      await tester.tap(find.byIcon(Icons.refresh_rounded));
      await tester.pumpAndSettle();
      expect(find.text('线上服务反馈'), findsOneWidget);
      expect(reads, 2);
      expect(tester.takeException(), isNull);
    });
  }

  test(
    'pending refresh is not duplicated and a late reply cannot revive a closed page',
    () async {
      final pending = Completer<Cth03ScreenData>();
      var reads = 0;
      final model = Cth03ViewModel(
        repository: _ReadRepository(() {
          reads++;
          return pending.future;
        }),
      );
      final first = model.refresh();
      final second = model.refresh();
      expect(reads, 1);
      model.dispose();
      pending.complete(_data());
      await Future.wait([first, second]);
      expect(model.data, isNull);
      await model.refresh();
      expect(reads, 1);
    },
  );

  test(
    'a failed refresh clears previous rows and a later retry can recover',
    () async {
      var reads = 0;
      final model = Cth03ViewModel(
        repository: _ReadRepository(() async {
          reads++;
          if (reads == 2) throw const LumenisCoreException('offline');
          return _data();
        }),
      );
      addTearDown(model.dispose);
      await model.refresh();
      expect(model.visibleRecords(), hasLength(1));
      await model.refresh();
      expect(model.failureKind, Cth03FailureKind.offline);
      expect(model.visibleRecords(), isEmpty);
      await model.refresh();
      expect(model.phase, Cth03LoadPhase.ready);
      expect(model.visibleRecords(), hasLength(1));
      expect(reads, 3);
    },
  );
}

class _ReadRepository implements Cth03Repository {
  const _ReadRepository(this.read);
  final Future<Cth03ScreenData> Function() read;

  @override
  Future<Cth03ScreenData> load() => read();
}

Future<Cth03ScreenData> _loadAnonymous(Map<String, dynamic> response) =>
    CoreCth03Repository(
      client: _FakeClient(
        contextResponse: _globalContext,
        screenResponse: response,
      ),
    ).load();

Map<String, dynamic> _anonymousProjection() => {
  ...cthGlobalProjection,
  'scope': {
    'mode': 'GLOBAL_ALL',
    'domain_id': 'CTH',
    'product_id': 'CTH',
    'global_all_granted': false,
  },
  'stored_scope': {
    'global': false,
    'domain_id': 'cth',
    'product_id': 'CTH',
    'subject_id': 'SUBJECT-RETURNED',
  },
  'integrity': {...cthGlobalProjection['integrity'] as Map},
};

Map<String, dynamic> _anonymousResponse() => {
  'ok': true,
  'screen': 'CTH-03',
  'bound': true,
  'global_binding': {
    'applied': true,
    'actor_scope': 'anonymous_read',
    'read_allowed': true,
    'scope_verified': true,
    'evidence_lineage': 'verified',
    'canonical_scope': 'GLOBAL_ALL',
    'domain_id': 'CTH',
    'product_id': 'CTH',
    'global_all_granted': false,
    'projection': _anonymousProjection(),
  },
  'truth': {'data_state': 'PARTIAL'},
  'sections': [
    {
      'type': 'kpis',
      'items': [
        {'id': 'cth03.recent', 'state': 'notcollected', 'value': null},
        {'id': 'cth03.negative', 'state': 'notcollected', 'value': null},
      ],
    },
    {'type': 'platforms', 'state': 'notcollected', 'items': <Object>[]},
    {
      'type': 'table',
      'state': 'ready',
      'rows': [
        {
          'title': '线上服务反馈',
          'date': '2026-09-22',
          'platform': '公开网页',
          'scope_mode': 'GLOBAL_ALL',
          'canonical_scope': 'GLOBAL_ALL',
          'subject_id': 'SUBJECT-RETURNED',
          'read_allowed': true,
          'projection': _anonymousProjection(),
        },
      ],
    },
  ],
};

Map<String, dynamic> _localScopeResponse({String? subjectId}) {
  final response = _anonymousResponse();
  response.remove('global_binding');
  final mode = subjectId == null ? 'GLOBAL_ALL' : 'FOCUS';
  response[subjectId == null
      ? 'global_binding'
      : 'focus_binding'] = <String, Object?>{
    'contract': 'lumenis.scope-read-binding.v1',
    'module': 'commercial_realtime_stream',
    'policy': 'local-workspace-read-v1',
    'domain_id': 'CTH',
    'product_id': 'CTH',
    'canonical_scope': mode,
    'subject_id': subjectId,
    'applied': true,
    'read_allowed': true,
    'scope_verified': true,
    'actor_scope': 'anonymous_read',
    'global_all_granted': false,
  };
  if (subjectId != null) {
    final row =
        (((response['sections'] as List).last as Map)['rows'] as List).single
            as Map;
    row['scope_mode'] = mode;
    row['canonical_scope'] = mode;
    row['subject_id'] = subjectId;
    final projection = row['projection'] as Map;
    (projection['scope'] as Map)['mode'] = mode;
    (projection['scope'] as Map)['subject_id'] = subjectId;
    (projection['stored_scope'] as Map)['subject_id'] = subjectId;
  }
  return response;
}

Widget _app(
  Cth03Repository repository, {
  Locale locale = const Locale('zh', 'CN'),
  double textScale = 1,
}) => MaterialApp(
  locale: locale,
  theme: LumenisTheme.dark,
  supportedLocales: LumenisLocalizations.supportedLocales,
  localizationsDelegates: const [
    LumenisLocalizations.delegate,
    GlobalMaterialLocalizations.delegate,
    GlobalWidgetsLocalizations.delegate,
    GlobalCupertinoLocalizations.delegate,
  ],
  builder: (context, child) => MediaQuery(
    data: MediaQuery.of(
      context,
    ).copyWith(textScaler: TextScaler.linear(textScale)),
    child: child!,
  ),
  home: Scaffold(
    body: Cth03Screen(client: LumenisCoreClient(), repository: repository),
  ),
);

class _PendingRepository implements Cth03Repository {
  const _PendingRepository(this.future);

  final Future<Cth03ScreenData> future;

  @override
  Future<Cth03ScreenData> load() => future;
}

class _FakeClient extends LumenisCoreClient {
  _FakeClient({required this.contextResponse, required this.screenResponse});

  final Map<String, dynamic> contextResponse;
  final Map<String, dynamic> screenResponse;

  @override
  Future<Map<String, dynamic>> settingsContext() async => contextResponse;

  @override
  Future<Map<String, dynamic>> screen(String screenId) async {
    expect(screenId, 'CTH-03');
    return screenResponse;
  }
}

Cth03ScreenData _data({
  String generatedAt = '2026-09-22T10:00:00',
  List<Cth03Channel>? channels,
  List<Cth03Record>? records,
}) => Cth03ScreenData(
  context: const Cth03Context(mode: 'GLOBAL_ALL'),
  generatedAt: generatedAt,
  recentCount: const Cth03Metric(
    id: 'cth03.recent',
    state: Cth03DataState.ready,
    value: 2,
  ),
  negativeCount: const Cth03Metric(
    id: 'cth03.negative',
    state: Cth03DataState.ready,
    value: 1,
  ),
  channels:
      channels ??
      const [
        Cth03Channel(name: '公开网页', status: '最近成功', detail: '只读'),
        Cth03Channel(name: '社交平台', status: '暂未返回', detail: '只读'),
      ],
  records:
      records ??
      const [
        Cth03Record(
          date: '2026-09-22',
          title: '线上服务反馈',
          channel: '公开网页',
          sentiment: '负面',
          risk: '中风险',
        ),
      ],
  recordState: Cth03DataState.ready,
);

const Map<String, dynamic> _screenResponse = {
  'ok': true,
  'screen': 'CTH-03',
  'bound': true,
  'generated_at': '2026-09-22T10:00:00',
  'sections': [
    {
      'type': 'kpis',
      'items': [
        {'id': 'cth03.recent', 'value': 2, 'state': 'ready'},
        {'id': 'cth03.negative', 'value': 1, 'state': 'ready'},
      ],
    },
    {
      'type': 'platforms',
      'items': [
        {
          'platform': '公开网页',
          'status': '最近成功',
          'schedule': '只读',
          'platform_id': 'PRIVATE-PLATFORM',
        },
      ],
    },
    {
      'type': 'table',
      'state': 'ready',
      'rows': [
        {
          'date': '2026-09-22',
          'title': '线上服务反馈',
          'platform': '公开网页',
          'sentiment': '负面',
          'risk': '中风险',
          'note_id': 'EV-PRIVATE-7',
        },
      ],
    },
  ],
};

const Map<String, dynamic> _guangzhouFocusContext = {
  'ok': true,
  'contract': 'lumenis.context.v1',
  'context': {
    'mode': 'FOCUS',
    'domain_id': 'CTH',
    'subject_id': 'GUANGZHOU_TAIKOO_HUI',
    'display_name': {'zh-CN': '广州太古汇'},
  },
};

const Map<String, dynamic> _globalContext = {
  'ok': true,
  'contract': 'lumenis.context.v1',
  'context': {'mode': 'GLOBAL_ALL'},
};

final Map<String, dynamic> _globalScreenResponse = _withTableRow(
  {
    ..._screenResponse,
    'global_binding': {
      'applied': true,
      'global_all_granted': true,
      'canonical_scope': 'GLOBAL_ALL',
      'scope_verified': true,
      'read_allowed': true,
      'domain_id': 'CTH',
      'product_id': 'CTH',
      'evidence_lineage': 'verified',
      'projection': cthGlobalProjection,
    },
  },
  {
    'date': '2026-09-22',
    'title': '线上服务反馈',
    'platform': '公开网页',
    'sentiment': '负面',
    'risk': '中风险',
    'scope_mode': 'GLOBAL_ALL',
    'canonical_scope': 'GLOBAL_ALL',
    'global_scope': true,
    'read_allowed': true,
    'evidence_lineage': 'verified',
    'trace_id': 'TRACE-CTH03-GLOBAL',
  },
);

final Map<String, dynamic> _focusedScreenResponse = _withTableRow(
  {
    ..._screenResponse,
    'focus_binding': {
      'applied': true,
      'subject_id': 'GUANGZHOU_TAIKOO_HUI',
      'canonical_scope': 'FOCUS',
      'scope_verified': true,
      'read_allowed': true,
      'domain_id': 'CTH',
      'product_id': 'CTH',
      'evidence_lineage': 'verified',
      'projection': cthGuangzhouFocusProjection,
    },
  },
  {
    'date': '2026-09-22',
    'title': '线上服务反馈',
    'platform': '公开网页',
    'sentiment': '负面',
    'risk': '中风险',
    'scope_mode': 'FOCUS',
    'canonical_scope': 'FOCUS',
    'subject_id': 'GUANGZHOU_TAIKOO_HUI',
    'read_allowed': true,
    'evidence_lineage': 'verified',
    'trace_id': 'TRACE-CTH03-GZ',
  },
);

Map<String, dynamic> _withTableRow(
  Map<String, dynamic> response,
  Map<String, dynamic> row,
) {
  final projection = row['scope_mode'] == 'FOCUS'
      ? cthGuangzhouFocusProjection
      : cthGlobalProjection;
  final sections = (response['sections'] as List)
      .map((section) {
        final copy = Map<String, dynamic>.from(section as Map);
        if (copy['type'] == 'table') {
          copy['rows'] = [
            <String, dynamic>{...row, 'projection': projection},
          ];
        } else if (copy['type'] == 'kpis' || copy['type'] == 'platforms') {
          copy['items'] = (copy['items'] as List)
              .map(
                (item) => <String, dynamic>{
                  ...(item as Map),
                  'projection': projection,
                },
              )
              .toList(growable: false);
        }
        return copy;
      })
      .toList(growable: false);
  return {...response, 'sections': sections};
}

void _expectNoInternalCopy(WidgetTester tester) {
  final rendered = tester
      .widgetList<Text>(find.byType(Text))
      .map((widget) => widget.data ?? widget.textSpan?.toPlainText() ?? '')
      .join(' ')
      .toLowerCase();
  for (final term in const [
    'api',
    'core',
    'database',
    'evidence',
    'permission',
    'provider',
    'owner',
    'subject_id',
    'note_id',
    'ev-',
  ]) {
    expect(rendered, isNot(contains(term)), reason: 'UI leaked $term');
  }
}
