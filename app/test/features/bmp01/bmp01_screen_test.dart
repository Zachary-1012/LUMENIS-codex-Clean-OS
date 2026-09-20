import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/core/lumenis_theme.dart';
import 'package:lumenis_app/features/bmp01/bmp01_repository.dart';
import 'package:lumenis_app/features/bmp01/bmp01_screen.dart';
import 'package:lumenis_app/features/bmp01/bmp01_snapshot.dart';

void main() {
  testWidgets(
    'desktop keeps brand context beside market information and hides unscoped aggregates',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(1440, 1000));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      await tester.pumpWidget(_app(_FakeRepository(_readySnapshot)));
      await tester.pumpAndSettle();

      expect(find.text('BMP · 品牌市场'), findsOneWidget);
      expect(find.text('品牌市场动态'), findsOneWidget);
      expect(find.text('尚未选择关注品牌'), findsOneWidget);
      expect(find.text('当前没有已确认的关注品牌，因此暂不展示品牌表现或竞品数据。'), findsOneWidget);
      _expectNoDeveloperCopy(tester);
      expect(find.text('99999'), findsNothing);
      expect(find.text('CANONICAL:UNSCOPED-RECORD'), findsNothing);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('mobile recomposes the brand gate as a single vertical task', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(_app(_FakeRepository(_notCollectedSnapshot)));
    await tester.pumpAndSettle();

    expect(find.text('暂无可展示的品牌信息'), findsOneWidget);
    expect(find.text('暂时没有品牌市场数据'), findsOneWidget);
    expect(find.text('品牌表现、竞品动态与市场变化会在数据可用后呈现。'), findsOneWidget);
    _expectNoDeveloperCopy(tester);
    expect(find.textContaining('ZBMP'), findsNothing);
    expect(find.text('99999'), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets('refresh reads the contract again without unlocking brand data', (
    tester,
  ) async {
    final repository = _FakeRepository(_readySnapshot);
    await tester.pumpWidget(_app(repository));
    await tester.pumpAndSettle();
    expect(repository.calls, 1);

    await tester.ensureVisible(find.text('刷新数据'));
    await tester.tap(find.text('刷新数据'));
    await tester.pumpAndSettle();

    expect(repository.calls, 2);
    expect(find.text('尚未选择关注品牌'), findsOneWidget);
    _expectNoDeveloperCopy(tester);
    expect(find.text('99999'), findsNothing);
  });

  test('snapshot parser rejects another screen response', () {
    expect(
      () => Bmp01Snapshot.fromResponse(const {'ok': true, 'screen': 'CTH-01'}),
      throwsFormatException,
    );
  });
}

void _expectNoDeveloperCopy(WidgetTester tester) {
  for (final term in const [
    'Core',
    'Canonical Data',
    'Evidence',
    'Permission',
    'BrandFocus',
    '契约',
    'lineage',
    'binding',
    'actor',
    'scope',
  ]) {
    expect(find.textContaining(term), findsNothing, reason: 'UI leaked $term');
  }
}

Widget _app(Bmp01Repository repository) {
  return MaterialApp(
    theme: LumenisTheme.dark,
    home: Scaffold(
      body: Bmp01Screen(client: LumenisCoreClient(), repository: repository),
    ),
  );
}

class _FakeRepository implements Bmp01Repository {
  _FakeRepository(this.response);

  final Map<String, dynamic> response;
  int calls = 0;

  @override
  Future<Bmp01Snapshot> load() async {
    calls++;
    return Bmp01Snapshot.fromResponse(response);
  }
}

final _readySnapshot = <String, dynamic>{
  'ok': true,
  'screen': 'BMP-01',
  'source': 'runtime',
  'bound': true,
  'generated_at': '2026-09-20T10:00:00',
  'truth': {
    'product_id': 'ZBMP',
    'domain_id': 'zbmp',
    'data_state': 'READY',
    'canonical_count': 99999,
  },
  'binding': {
    'blocked': [
      {
        'field': 'risk_index',
        'reason': 'ZBMP 专属风险指标尚无真值源。',
        'required': 'ZBMP canonical metric',
      },
    ],
  },
  'sections': [
    {
      'type': 'kpis',
      'items': [
        {'id': 'bmp01.total', 'label': '总声量', 'value': 99999},
      ],
    },
    {
      'type': 'risks',
      'items': [
        {'title': '未授权风险', 'evidence': 'CANONICAL:UNSCOPED-RECORD'},
      ],
    },
  ],
};

final _notCollectedSnapshot = <String, dynamic>{
  'ok': true,
  'screen': 'BMP-01',
  'source': 'runtime',
  'bound': true,
  'truth': {
    'product_id': 'ZBMP',
    'domain_id': 'zbmp',
    'data_state': 'NOT_COLLECTED',
    'canonical_count': 0,
  },
  'binding': {'blocked': []},
  'sections': [],
};
