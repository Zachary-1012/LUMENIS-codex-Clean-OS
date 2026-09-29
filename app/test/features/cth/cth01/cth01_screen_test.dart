import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/core/lumenis_theme.dart';
import 'package:lumenis_app/features/cth/cth01/cth01_screen.dart';
import 'package:lumenis_app/l10n/lumenis_localizations.dart';

void main() {
  testWidgets('desktop leads with the real signal stream and returned fields', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    final client = _ContractClient();
    await tester.pumpWidget(_app(client));
    await tester.pumpAndSettle();

    expect(find.text('全部可访问范围'), findsOneWidget);
    expect(find.text('商业运营总览'), findsOneWidget);
    expect(find.text('在线负面记录'), findsOneWidget);
    expect(find.text('2条'), findsOneWidget);
    expect(find.text('尚未采集'), findsNWidgets(2));
    expect(find.textContaining('到店客流'), findsOneWidget);
    expect(find.text('部分指标尚不可用。未返回的数据不会按零展示。'), findsOneWidget);
    expect(find.textContaining('CTH-SUBJECT-7'), findsNothing);
    expect(find.text('线上负面反馈增加'), findsOneWidget);
    expect(find.byKey(const ValueKey('cth01/layout-desktop')), findsOneWidget);
    expect(find.text('41.8'), findsNothing);
    expect(find.text('38214'), findsNothing);
    expect(client.identityCalls, 0);
    expect(client.contextCalls, 1);
    expect(client.screenCalls, 1);
    _expectNoImplementationCopy(tester);
    expect(tester.takeException(), isNull);
  });

  testWidgets('invalid context contract blocks the aggregate request', (
    tester,
  ) async {
    final client = _ContractClient(
      contextResponse: const {'ok': true, 'context': null},
    );
    await tester.pumpWidget(_app(client));
    await tester.pumpAndSettle();

    expect(find.text('经营主体信息暂不可用'), findsOneWidget);
    expect(find.textContaining('当前经营主体暂不可用'), findsOneWidget);
    expect(client.identityCalls, 0);
    expect(client.screenCalls, 0);
    expect(tester.takeException(), isNull);
  });

  testWidgets('non-CTH context and unbound page stay blocked', (tester) async {
    final otherProduct = _ContractClient(
      contextResponse: const {
        'ok': true,
        'contract': 'lumenis.context.v1',
        'context': {'mode': 'FOCUS', 'domain_id': 'BMP'},
      },
    );
    await tester.pumpWidget(_app(otherProduct));
    await tester.pumpAndSettle();
    expect(find.text('经营主体信息暂不可用'), findsOneWidget);
    expect(otherProduct.screenCalls, 0);

    final unbound = _ContractClient(
      response: {..._screenResponse, 'bound': false},
    );
    await tester.pumpWidget(_app(unbound));
    await tester.pumpAndSettle();
    expect(find.text('经营主体信息暂不可用'), findsOneWidget);
    expect(find.textContaining('页面尚未接入所选范围的数据'), findsOneWidget);
    expect(unbound.screenCalls, 1);
    expect(tester.takeException(), isNull);
  });

  testWidgets('authentication failures are shown without server internals', (
    tester,
  ) async {
    for (final status in [401, 403]) {
      final client = _ContractClient(
        screenError: LumenisCoreException(
          'HTTP $status private server detail',
          statusCode: status,
        ),
      );
      await tester.pumpWidget(_app(client));
      await tester.pumpAndSettle();

      expect(find.text('运营信息暂不可用'), findsOneWidget);
      expect(find.text('运营信息暂不可用，请稍后重试。'), findsOneWidget);
      expect(find.textContaining('请登录后查看商业运营信息'), findsNothing);
      expect(find.textContaining('当前账号暂时无法查看商业运营信息'), findsNothing);
      expect(find.textContaining('private server detail'), findsNothing);
      expect(client.screenCalls, 1);
      _expectNoImplementationCopy(tester);
    }
    expect(tester.takeException(), isNull);
  });

  testWidgets('authentication failure stays inside the open workspace', (
    tester,
  ) async {
    final client = _ContractClient(
      screenError: LumenisCoreException(
        'HTTP 401 private server detail',
        statusCode: 401,
      ),
    );
    await tester.pumpWidget(_app(client));
    await tester.pumpAndSettle();

    expect(find.text('请登录后查看商业运营信息。'), findsNothing);
    expect(find.text('当前账号暂时无法查看商业运营信息。'), findsNothing);
    expect(find.text('运营信息暂不可用，请稍后重试。'), findsOneWidget);
    expect(find.text('领域登录入口'), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets('signal inspection returns to the same stream without Evidence', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(_app(_ContractClient()));
    await tester.pumpAndSettle();

    expect(
      find.byKey(const ValueKey('cth01/layout-single-task')),
      findsOneWidget,
    );
    expect(find.byKey(const ValueKey('cth01/signal-inspection')), findsNothing);
    expect(find.text('Subject-linked evidence fixture'), findsNothing);
    expect(
      find.byKey(const ValueKey('cth01/evidence-scope-blocked')),
      findsOneWidget,
    );
    expect(find.byKey(const ValueKey('cth01/trend-blocked')), findsOneWidget);

    final firstSignal = find.byKey(const ValueKey('cth01/signal-0'));
    await tester.ensureVisible(firstSignal);
    await tester.tap(firstSignal);
    await tester.pumpAndSettle();
    expect(
      find.byKey(const ValueKey('cth01/signal-inspection')),
      findsOneWidget,
    );
    expect(find.text('线上负面反馈增加'), findsNWidgets(2));
    expect(find.text('EV:EVENT-7'), findsNothing);
    expect(find.text('Subject-linked evidence fixture'), findsNothing);
    _expectNoImplementationCopy(tester);

    await tester.ensureVisible(find.text('返回运营动态'));
    await tester.tap(find.text('返回运营动态'));
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('cth01/signal-inspection')), findsNothing);
    expect(find.text('全部可访问范围'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('empty activity is distinct from unavailable activity', (
    tester,
  ) async {
    for (final (state, title, detail) in [
      ('empty', '暂无运营动态', '当前没有可展示的运营动态。'),
      ('offline', '暂时无法获取运营动态', '请检查连接后重试。'),
    ]) {
      final client = _ContractClient(
        response: _screenResponseWithEmptyEvents(state),
      );
      await tester.pumpWidget(_app(client));
      await tester.pumpAndSettle();

      expect(find.text(title), findsOneWidget);
      expect(find.text(detail), findsOneWidget);
      _expectNoImplementationCopy(tester);
      expect(tester.takeException(), isNull);
    }
  });

  testWidgets('layout recomposes across desktop, tablet and phone widths', (
    tester,
  ) async {
    final client = _ContractClient();
    await tester.binding.setSurfaceSize(const Size(1440, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(_app(client));
    await tester.pumpAndSettle();

    for (final width in [1440.0, 1280, 1024, 768, 430, 390, 360]) {
      await tester.binding.setSurfaceSize(Size(width.toDouble(), 1000));
      await tester.pumpAndSettle();
      if (width >= 1100) {
        expect(
          find.byKey(const ValueKey('cth01/layout-desktop')),
          findsOneWidget,
          reason: 'expected desktop composition at $width logical px',
        );
      } else {
        expect(
          find.byKey(const ValueKey('cth01/layout-single-task')),
          findsOneWidget,
          reason: 'expected single task composition at $width logical px',
        );
      }
      expect(find.text('尚未采集'), findsNWidgets(2));
      expect(tester.takeException(), isNull, reason: 'overflow at $width px');
    }
  });
}

Widget _app(
  LumenisCoreClient client, {
  Locale locale = const Locale('zh', 'CN'),
  ValueChanged<String>? onNavigate,
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
  home: Scaffold(
    body: Cth01Screen(client: client, onNavigate: onNavigate),
  ),
);

void _expectNoImplementationCopy(WidgetTester tester) {
  for (final term in const [
    'Core',
    'Subject',
    'Canonical Data',
    'Evidence',
    'Permission',
    'ViewModel',
    'BrandFocus',
    'actor',
    'scope',
    '接口',
    '契约',
    '证据关联',
    'LUMENIS Core',
  ]) {
    expect(find.textContaining(term), findsNothing, reason: 'UI leaked $term');
  }
}

/// Contract-shaped data for widget assertions; the screen never ships it.
class _ContractClient extends LumenisCoreClient {
  _ContractClient({this._contextResponse, this._response, this._screenError});

  final Map<String, dynamic>? _contextResponse;
  final Map<String, dynamic>? _response;
  final Object? _screenError;
  int identityCalls = 0;
  int contextCalls = 0;
  int screenCalls = 0;

  @override
  Future<Map<String, dynamic>> runtimeIdentity() async {
    identityCalls++;
    return const {'ok': true};
  }

  @override
  Future<Map<String, dynamic>> settingsContext() async {
    contextCalls++;
    return _contextResponse ??
        const {
          'ok': true,
          'contract': 'lumenis.context.v1',
          'context': {
            'mode': 'GLOBAL_ALL',
            'mode_label_key': 'context.mode.global_all',
            'domain_id': null,
            'subject_id': null,
          },
        };
  }

  @override
  Future<Map<String, dynamic>> screen(String screenId) async {
    screenCalls++;
    expect(screenId, 'CTH-01');
    final error = _screenError;
    if (error != null) throw error;
    return _response ?? _screenResponse;
  }
}

const Map<String, dynamic> _screenResponse = {
  'ok': true,
  'screen': 'CTH-01',
  'bound': true,
  'focus_binding': {'state': 'applied', 'applied': true},
  'generated_at': '2026-09-20T10:00:00',
  'sections': [
    {
      'type': 'kpis',
      'items': [
        {
          'id': 'cth.negative_voice',
          'value': 2,
          'unit': '条',
          'state': 'ready',
          'source': 'CTH verified notes',
        },
        {
          'id': 'cth.footfall',
          'value': null,
          'unit': '人次',
          'state': 'notcollected',
          'source': 'POS integration unavailable',
        },
        {
          'id': 'cth.member_sales',
          'value': null,
          'unit': '%',
          'state': 'notcollected',
          'source': 'Sales integration unavailable',
        },
      ],
    },
    {
      'type': 'split',
      'main': [
        {
          'type': 'events',
          'state': 'ready',
          'items': [
            {
              'title': '线上负面反馈增加',
              'level': 'high',
              'date': '2026-09-20',
              'time': '09:30',
              'desc': '近期关于门店服务的负面反馈增加',
              'tags': ['service'],
              'evidence': 'EV:EVENT-7',
            },
          ],
        },
        {
          'type': 'evidence',
          'state': 'ready',
          'items': [
            {'title': 'Subject-linked evidence fixture'},
          ],
        },
      ],
      'side': [
        {'type': 'risks', 'state': 'ready', 'items': []},
      ],
    },
  ],
  'truth': {
    'canonical': {'risk_index': 42, 'brand_health_score': 75, 'risk_count': 1},
  },
};

Map<String, dynamic> _screenResponseWithEmptyEvents(String state) {
  final response = Map<String, dynamic>.from(_screenResponse);
  response['sections'] = (response['sections'] as List)
      .map((section) {
        if (section is! Map || section['type'] != 'split') return section;
        final split = Map<String, dynamic>.from(section);
        split['main'] = (split['main'] as List)
            .map((mainSection) {
              if (mainSection is! Map || mainSection['type'] != 'events') {
                return mainSection;
              }
              return {...mainSection, 'state': state, 'items': const []};
            })
            .toList(growable: false);
        return split;
      })
      .toList(growable: false);
  return response;
}
