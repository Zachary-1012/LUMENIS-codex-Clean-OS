import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/core/lumenis_theme.dart';
import 'package:lumenis_app/features/bmp04/bmp04_repository.dart';
import 'package:lumenis_app/features/bmp04/bmp04_screen.dart';
import 'package:lumenis_app/features/bmp04/bmp04_snapshot.dart';
import 'package:lumenis_app/l10n/lumenis_localizations.dart';
import '../shared/bmp_scope_test_support.dart';

void main() {
  for (final state in ['READY', 'PARTIAL', 'STALE', 'DENIED']) {
    testWidgets('source observations preserve existing channel workspace in $state', (tester) async {
      await tester.binding.setSurfaceSize(const Size(1440, 1000));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      final parsed = Bmp04Snapshot.fromResponse(_response(
        dataState: state == 'DENIED' ? 'READY' : state,
        channels: [_channel('CH-ONE', 'Short video')],
      ));
      final snapshot = Bmp04Snapshot(
        contractBound: parsed.contractBound, isBmpOwner: parsed.isBmpOwner,
        dataState: parsed.dataState, focus: parsed.focus,
        focusBindingApplied: state != 'DENIED' && parsed.focusBindingApplied,
        readAllowed: state != 'DENIED' && parsed.readAllowed,
        globalScopeReady: parsed.globalScopeReady, channels: parsed.channels,
        rejectedCrossFocusCount: 0, rejectedUnscopedCount: 0,
        sourceObservations: const [Bmp04SourceObservation(
          id: 'SRC-12', evidenceReference: 'EV-12', title: 'Observed launch')],
      );
      await tester.pumpWidget(_app(_SnapshotRepository(snapshot)));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('bmp04-source-observations')),
        state == 'DENIED' ? findsNothing : findsOneWidget);
      expect(find.byKey(const Key('bmp04-channel-CH-ONE')),
        state == 'DENIED' ? findsNothing : findsOneWidget);
      expect(find.text('Observed launch'), state == 'DENIED' ? findsNothing : findsOneWidget);
      expect(find.text('传播分析尚未计算。'), findsNothing);
      expect(tester.takeException(), isNull);
    });
  }
  test(
    'propagation rows require the selected BrandFocus and metric lineage',
    () {
      final snapshot = Bmp04Snapshot.fromResponse(
        _response(
          channels: [
            _channel('CH-ONE', 'Short video'),
            _channel('CH-TWO', 'Other focus', scopeId: 'BRAND-TWO'),
            {
              'id': 'CH-UNSCOPED',
              'brand_focus_id': 'BRAND-ONE',
              'name': 'No metric definition',
              'exposure': 0,
            },
          ],
        ),
      );

      expect(snapshot.scopeReady, isTrue);
      expect(snapshot.channels.map((channel) => channel.id), ['CH-ONE']);
      expect(snapshot.rejectedCrossFocusCount, 1);
      expect(snapshot.rejectedUnscopedCount, 1);
      expect(snapshot.channels.single.exposure!.value, 1200);
    },
  );

  test(
    'drops missing-scope and forged-integrity channels without hiding valid ones',
    () {
      final response = _response(
        channels: [
          _channel('CH-ONE', 'Short video'),
          {..._channel('CH-MISSING', 'Missing scope'), 'scope': null},
          {
            ..._channel('CH-FORGED', 'Forged evidence'),
            'evidence': bmpTestEvidence(
              bmpFocusScope(),
              verified: false,
              assurance: 'tampered',
            ),
          },
        ],
      );

      final snapshot = Bmp04Snapshot.fromResponse(response);

      expect(snapshot.channels.map((channel) => channel.id), ['CH-ONE']);
      expect(snapshot.rejectedUnscopedCount, 2);
      expect(snapshot.presentationState, Bmp04PresentationState.ready);
    },
  );

  test('global view rejects focused rows without a global contract', () {
    final response = _response(channels: [_channel('CH-ONE', 'Short video')]);
    _makeGlobal(response);

    final snapshot = Bmp04Snapshot.fromResponse(response);

    expect(snapshot.presentationState, Bmp04PresentationState.blocked);
    expect(snapshot.channels, isEmpty);
  });

  test('global rows still require a response-level global binding', () {
    final response = _response(
      channels: [_globalChannel(_channel('CH-GLOBAL', 'Global video'))],
    );
    _makeGlobal(response);
    response['focus_binding'] = {'applied': true, 'read_allowed': true};

    final snapshot = Bmp04Snapshot.fromResponse(response);

    expect(snapshot.presentationState, Bmp04PresentationState.blocked);
    expect(snapshot.channels, isEmpty);
  });

  test('authorized global rows enter the propagation workspace', () {
    final response = _response(
      channels: [_globalChannel(_channel('CH-GLOBAL', 'Global video'))],
    );
    _makeGlobal(response);

    final snapshot = Bmp04Snapshot.fromResponse(response);

    expect(snapshot.globalScopeReady, isTrue);
    expect(snapshot.scopeReady, isTrue);
    expect(snapshot.presentationState, Bmp04PresentationState.ready);
    expect(snapshot.channels.map((channel) => channel.id), ['CH-GLOBAL']);
  });

  testWidgets('authorized global rows render the propagation workspace', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    final response = _response(
      channels: [_globalChannel(_channel('CH-GLOBAL', 'Global video'))],
    );
    _makeGlobal(response);
    await tester.pumpWidget(_app(_FakeRepository(response)));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('bmp04-channel-CH-GLOBAL')), findsOneWidget);
    expect(find.text('传播分析'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  test('not collected, empty and blocked remain different states', () {
    final notCollected = Bmp04Snapshot.fromResponse(
      _response(dataState: 'NOT_COLLECTED', channels: []),
    );
    final empty = Bmp04Snapshot.fromResponse(
      _response(dataState: 'READY', channels: []),
    );
    final blockedResponse = _response(channels: []);
    blockedResponse['focus_binding'] = {
      'applied': false,
      'read_allowed': false,
    };
    final blocked = Bmp04Snapshot.fromResponse(blockedResponse);

    expect(notCollected.presentationState, Bmp04PresentationState.notCollected);
    expect(empty.presentationState, Bmp04PresentationState.empty);
    expect(blocked.presentationState, Bmp04PresentationState.blocked);
  });

  testWidgets('desktop propagation view shows a source-backed river', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      _app(
        _FakeRepository(
          _response(
            channels: [
              _channel('CH-ONE', 'Short video'),
              _channel('CH-TWO', 'Live stream', exposureValue: 860),
            ],
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('传播分析'), findsOneWidget);
    expect(find.text('Short video'), findsWidgets);
    expect(find.byKey(const Key('bmp04-channel-CH-TWO')), findsOneWidget);
    expect(find.text('1200'), findsWidgets);
    expect(_visibleCopy(tester), isNot(contains('Evidence')));
    expect(_visibleCopy(tester), isNot(contains('Permission')));
    expect(tester.takeException(), isNull);
  });

  testWidgets('mobile propagation view uses a channel selector', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      _app(
        _FakeRepository(
          _response(channels: [_channel('CH-ONE', 'Short video')]),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Short video'), findsWidgets);
    expect(find.text('曝光'), findsWidgets);
    expect(find.textContaining('https://'), findsNothing);
    expect(tester.takeException(), isNull);
  });
}

Widget _app(Bmp04Repository repository) {
  return MaterialApp(
    theme: LumenisTheme.dark,
    locale: const Locale('zh', 'CN'),
    supportedLocales: LumenisLocalizations.supportedLocales,
    localizationsDelegates: const [
      LumenisLocalizations.delegate,
      GlobalMaterialLocalizations.delegate,
      GlobalWidgetsLocalizations.delegate,
      GlobalCupertinoLocalizations.delegate,
    ],
    home: Scaffold(
      body: Bmp04Screen(client: LumenisCoreClient(), repository: repository),
    ),
  );
}

class _FakeRepository implements Bmp04Repository {
  _FakeRepository(this.response);

  final Map<String, dynamic> response;

  @override
  Future<Bmp04Snapshot> load() async {
    return Bmp04Snapshot.fromResponse(response);
  }
}

Map<String, dynamic> _response({
  required List<Map<String, dynamic>> channels,
  String dataState = 'READY',
}) {
  return {
    'ok': true,
    'screen': 'BMP-04',
    'source': 'runtime',
    'bound': true,
    'truth': {
      'product_id': 'ZBMP',
      'domain_id': 'zbmp',
      'data_state': dataState,
    },
    'focus_context': {
      'mode': 'FOCUS',
      'domain_id': 'BMP',
      'product_id': 'ZBMP',
      'subject_id': 'SUBJ-ONE',
      'brand_focus_id': 'BRAND-ONE',
      'display_name': {'zh-CN': '主品牌', 'en': 'Primary'},
    },
    'focus_binding': bmpFocusBinding(),
    'sections': [
      {'type': 'channels', 'state': dataState, 'items': channels},
    ],
  };
}

Map<String, dynamic> _channel(
  String id,
  String name, {
  String scopeId = 'BRAND-ONE',
  num exposureValue = 1200,
}) {
  return {
    'id': id,
    'brand_focus_id': scopeId,
    'scope': bmpFocusScope(brandFocusId: scopeId),
    'read_allowed': true,
    'permission': bmpTestPermission(bmpFocusScope(brandFocusId: scopeId)),
    'evidence': bmpTestEvidence(bmpFocusScope(brandFocusId: scopeId)),
    'name': name,
    'content': _metric('内容数', 12, '条'),
    'exposure': _metric('曝光', exposureValue, '次'),
    'response': _metric('互动', 84, '次'),
    'conversion': _metric('转化', 9, '次'),
  };
}

Map<String, dynamic> _metric(String label, num value, String unit) {
  return {
    'value': value,
    'unit': unit,
    'label': {'zh-CN': label, 'en': label},
    'definition': '按来源记录统计',
    'window': '最近 30 天',
    'source': 'channel.report',
    'evidence_ref': 'EV-BMP04-1',
    'freshness': '2026-09-22',
  };
}

Map<String, dynamic> _globalChannel(Map<String, dynamic> channel) => {
  ...channel,
  'brand_focus_id': null,
  'scope': bmpGlobalScope(),
  'permission': bmpTestPermission(bmpGlobalScope()),
  'evidence': bmpTestEvidence(bmpGlobalScope()),
  'scope_mode': 'GLOBAL_ALL',
  'canonical_scope': 'GLOBAL_ALL',
  'global_scope': true,
  'read_allowed': true,
  'lineage': {
    'scope_mode': 'GLOBAL_ALL',
    'status': 'VERIFIED',
    'canonical': true,
  },
};

void _makeGlobal(Map<String, dynamic> response) {
  response['focus_context'] = {
    'mode': 'GLOBAL_ALL',
    'domain_id': 'BMP',
    'product_id': 'ZBMP',
    'subject_id': null,
    'brand_focus_id': null,
  };
  response['focus_binding'] = bmpGlobalBinding();
}

String _visibleCopy(WidgetTester tester) => <String>[
  ...tester
      .widgetList<Text>(find.byType(Text))
      .map((widget) => widget.data ?? widget.semanticsLabel ?? ''),
  ...tester
      .widgetList<Semantics>(find.byType(Semantics))
      .map((widget) => widget.properties.label ?? ''),
].join('\n');

class _SnapshotRepository implements Bmp04Repository {
  const _SnapshotRepository(this.snapshot);
  final Bmp04Snapshot snapshot;
  @override
  Future<Bmp04Snapshot> load() async => snapshot;
}
