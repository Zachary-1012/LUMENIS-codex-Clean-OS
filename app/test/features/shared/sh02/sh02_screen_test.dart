import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/features/shared/sh02/sh02_repository.dart';
import 'package:lumenis_app/features/shared/sh02/sh02_screen.dart';
import 'package:lumenis_app/features/shared/sh02/sh02_snapshot.dart';

import '../shared_test_support.dart';

void main() {
  testWidgets(
    'desktop library inspects verified material and stays responsive',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(1440, 1000));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      await tester.pumpWidget(_app(_FakeSh02Repository(_readyResponse)));
      await tester.pumpAndSettle();

      expect(find.text('证据库'), findsOneWidget);
      expect(find.text('资料空间'), findsOneWidget);
      expect(find.text('已核实的市场信号'), findsWidgets);
      expect(find.text('来源链路'), findsOneWidget);
      expect(find.byType(InteractiveViewer), findsOneWidget);
      expect(find.text('EV-PRIVATE-ID'), findsNothing);
      expectNoSharedRawMarkers(tester);
      expect(tester.takeException(), isNull);

      await tester.tap(find.text('列表'));
      await tester.pumpAndSettle();
      expect(find.text('已核实资料'), findsOneWidget);
      final listEntry = tester.widget<InkWell>(
        find.descendant(
          of: find.byKey(const Key('sh02-item-EV-PRIVATE-ID')),
          matching: find.byType(InkWell),
        ),
      );
      expect(listEntry.canRequestFocus, isTrue);
      expect(listEntry.onTap, isNotNull);

      await tester.binding.setSurfaceSize(const Size(390, 844));
      await tester.pumpAndSettle();
      expect(find.text('检索资料'), findsOneWidget);
      expect(find.text('来源链路'), findsOneWidget);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('space zoom and focused detail return to the same view', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(_app(_FakeSh02Repository(_readyResponse)));
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const Key('sh02-space-zoom-in')));
    await tester.pumpAndSettle();
    var controller = tester
        .widget<InteractiveViewer>(find.byType(InteractiveViewer))
        .transformationController!;
    final zoomedMatrix = controller.value.storage.toList();
    expect(controller.value.getMaxScaleOnAxis(), greaterThan(1));

    await tester.tap(find.byKey(const Key('sh02-space-reset')));
    await tester.pumpAndSettle();
    controller = tester
        .widget<InteractiveViewer>(find.byType(InteractiveViewer))
        .transformationController!;
    expect(controller.value.getMaxScaleOnAxis(), 1);
    await tester.tap(find.byKey(const Key('sh02-space-zoom-in')));
    await tester.pumpAndSettle();
    controller = tester
        .widget<InteractiveViewer>(find.byType(InteractiveViewer))
        .transformationController!;
    expect(controller.value.storage, zoomedMatrix);

    await tester.tap(find.text('列表'));
    await tester.pumpAndSettle();
    expect(find.byType(InteractiveViewer), findsNothing);
    await tester.tap(find.text('空间'));
    await tester.pumpAndSettle();
    controller = tester
        .widget<InteractiveViewer>(find.byType(InteractiveViewer))
        .transformationController!;
    expect(controller.value.storage, zoomedMatrix);

    final spaceItem = find.byKey(const Key('sh02-space-item-EV-PRIVATE-ID'));
    final spaceEntry = tester.widget<InkWell>(
      find.descendant(of: spaceItem, matching: find.byType(InkWell)),
    );
    final spaceFocusNode = spaceEntry.focusNode!;
    spaceFocusNode.requestFocus();
    await tester.pump();
    expect(spaceFocusNode.hasFocus, isTrue);

    await tester.tap(spaceItem);
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('sh02-focus-return')), findsOneWidget);
    expect(find.byType(InteractiveViewer), findsNothing);

    await tester.tap(find.byKey(const Key('sh02-focus-return')));
    await tester.pumpAndSettle();
    controller = tester
        .widget<InteractiveViewer>(find.byType(InteractiveViewer))
        .transformationController!;
    expect(controller.value.storage, zoomedMatrix);
    expect(spaceFocusNode.hasFocus, isTrue);
    expect(tester.takeException(), isNull);
  });

  testWidgets('list return restores scrolled row position and keyboard focus', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      _app(_FakeSh02Repository(_readyResponseWithItems(20))),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.text('列表'));
    await tester.pumpAndSettle();

    final scrollView = tester.widget<SingleChildScrollView>(
      find.byKey(const Key('sh02-workspace-scroll')),
    );
    final scrollController = scrollView.controller!;
    scrollController.jumpTo(scrollController.position.maxScrollExtent);
    await tester.pumpAndSettle();
    final priorOffset = scrollController.offset;
    expect(priorOffset, greaterThan(0));

    final lastRow = find.byKey(const Key('sh02-item-verified-19'));
    expect(lastRow, findsOneWidget);
    expect(tester.getRect(lastRow).bottom, lessThan(900));
    final listEntry = tester.widget<InkWell>(
      find.descendant(of: lastRow, matching: find.byType(InkWell)),
    );
    final rowFocusNode = listEntry.focusNode!;
    rowFocusNode.requestFocus();
    await tester.pump();
    expect(rowFocusNode.hasFocus, isTrue);

    await tester.tap(lastRow);
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('sh02-focus-return')), findsOneWidget);
    await tester.tap(find.byKey(const Key('sh02-focus-return')));
    await tester.pumpAndSettle();

    expect(scrollController.offset, priorOffset);
    expect(rowFocusNode.hasFocus, isTrue);
    expect(tester.takeException(), isNull);
  });

  testWidgets('material focus node survives list and space transitions', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(_app(_FakeSh02Repository(_readyResponse)));
    await tester.pumpAndSettle();
    await tester.tap(find.text('列表'));
    await tester.pumpAndSettle();

    final row = find.byKey(const Key('sh02-item-EV-PRIVATE-ID'));
    final rowEntry = tester.widget<InkWell>(
      find.descendant(of: row, matching: find.byType(InkWell)),
    );
    final materialFocusNode = rowEntry.focusNode!;
    expect(materialFocusNode.context, isNotNull);
    materialFocusNode.requestFocus();
    await tester.pump();
    expect(materialFocusNode.hasFocus, isTrue);

    Future<void> pumpTransitionFrames() async {
      for (var frame = 0; frame < 5; frame++) {
        await tester.pump(const Duration(milliseconds: 40));
        expect(tester.takeException(), isNull);
      }
    }

    await tester.tap(find.text('空间'));
    await pumpTransitionFrames();
    expect(
      find.byKey(const Key('sh02-space-item-EV-PRIVATE-ID')),
      findsOneWidget,
    );
    expect(materialFocusNode.context, isNotNull);
    materialFocusNode.requestFocus();
    await tester.pump();
    expect(materialFocusNode.hasFocus, isTrue);

    await tester.tap(find.text('列表'));
    await pumpTransitionFrames();
    expect(row, findsOneWidget);
    expect(materialFocusNode.context, isNotNull);
    materialFocusNode.requestFocus();
    await tester.pump();
    expect(materialFocusNode.hasFocus, isTrue);
    expect(tester.takeException(), isNull);
  });

  testWidgets('filtered invoking item returns focus to search safely', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1280, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(_app(_FakeSh02Repository(_readyResponse)));
    await tester.pumpAndSettle();
    await tester.tap(find.text('列表'));
    await tester.pumpAndSettle();

    final row = find.byKey(const Key('sh02-item-EV-PRIVATE-ID'));
    final rowEntry = tester.widget<InkWell>(
      find.descendant(of: row, matching: find.byType(InkWell)),
    );
    final rowFocusNode = rowEntry.focusNode!;
    rowFocusNode.requestFocus();
    await tester.pump();
    await tester.tap(row);
    await tester.pumpAndSettle();

    final search = find.byKey(const Key('sh02-search'));
    await tester.enterText(search, 'no matching material');
    await tester.pumpAndSettle();
    expect(find.text('资料已不在当前结果中'), findsOneWidget);

    await tester.tap(find.byKey(const Key('sh02-focus-return')));
    await tester.pumpAndSettle();

    final searchField = tester.widget<TextField>(search);
    expect(find.text('当前范围没有匹配的已核实资料。'), findsOneWidget);
    expect(searchField.controller?.text, 'no matching material');
    expect(searchField.focusNode?.hasFocus, isTrue);
    expect(rowFocusNode.hasFocus, isFalse);
    expect(tester.takeException(), isNull);
  });

  testWidgets('mobile focus return keeps query and avoids overflow', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(_app(_FakeSh02Repository(_readyResponse)));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('sh02-search')), '市场信号');
    await tester.pumpAndSettle();
    await tester.tap(find.text('列表'));
    await tester.pumpAndSettle();

    final row = find.byKey(const Key('sh02-item-EV-PRIVATE-ID'));
    await tester.ensureVisible(row);
    await tester.pumpAndSettle();
    await tester.tap(row);
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('sh02-focus-return')));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('sh02-search')), findsOneWidget);
    expect(
      tester
          .widget<TextField>(find.byKey(const Key('sh02-search')))
          .controller
          ?.text,
      '市场信号',
    );
    expect(tester.takeException(), isNull);
  });

  testWidgets('an empty verified range stays empty in space view', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    final emptyResponse = <String, dynamic>{
      ..._readyResponse,
      'data': {'evidence': <Object>[]},
    };
    await tester.pumpWidget(_app(_FakeSh02Repository(emptyResponse)));
    await tester.pumpAndSettle();

    expect(find.text('当前范围没有匹配的已核实资料。'), findsOneWidget);
    expect(find.byType(InteractiveViewer), findsNothing);
    expect(find.text('0 条结果'), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets('unscoped runtime data is blocked instead of rendered', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    final unscoped = <String, dynamic>{
      'ok': true,
      'screen': 'SH-02',
      'source': 'runtime',
      'bound': true,
      'sections': ['global'],
      'evidence': [
        {'id': 'EV-PRIVATE-ID', 'summary': 'should not render'},
      ],
    };
    await tester.pumpWidget(_app(_FakeSh02Repository(unscoped)));
    await tester.pumpAndSettle();

    expect(find.text('资料暂不显示'), findsOneWidget);
    expect(find.text('EV-PRIVATE-ID'), findsNothing);
    expectNoSharedRawMarkers(tester);
    expect(tester.takeException(), isNull);
  });

  testWidgets('English title comes from the existing integration key', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1024, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      _app(_FakeSh02Repository(_readyResponse), locale: const Locale('en')),
    );
    await tester.pumpAndSettle();

    expect(find.text('Evidence Library'), findsOneWidget);
    await tester.tap(find.text('List'));
    await tester.pumpAndSettle();
    expect(find.text('Verified material'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Korean space controls use the screen locale', (tester) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      _app(_FakeSh02Repository(_readyResponse), locale: const Locale('ko')),
    );
    await tester.pumpAndSettle();

    expect(find.text('증거 라이브러리'), findsOneWidget);
    expect(find.text('공간'), findsOneWidget);
    expect(find.text('자료 공간'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  test(
    'focus scope is exact and selection-only or denied scope is rejected',
    () {
      final focusPageScope = <String, dynamic>{
        'mode': 'FOCUS',
        'domain_id': 'CTH',
        'subject_id': 'subject-private-9',
        'display_name': '广州太古汇',
      };
      final focusRowScope = <String, dynamic>{
        'mode': 'FOCUS',
        'domain_id': 'CTH',
        'subject_id': 'subject-private-9',
      };
      final focusResponse = sharedResponseWithRowScopes(
        _readyResponse,
        pageScope: focusPageScope,
        rowScopes: {'evidence': focusRowScope},
      );
      final snapshot = Sh02Snapshot.fromResponse(focusResponse);
      expect(snapshot.scope.isGlobal, isFalse);
      expect(snapshot.scope.domain, 'CTH');
      expect(snapshot.scope.focusId, 'subject-private-9');
      expect(snapshot.scope.displayName, '广州太古汇');

      expect(
        () => Sh02Snapshot.fromResponse({
          ...focusResponse,
          'selection_only': true,
        }),
        throwsA(isA<Sh02ScopeError>()),
      );
      expect(
        () => Sh02Snapshot.fromResponse({
          ..._readyResponse,
          'permission': {'read': false, 'decision': 'DENY'},
        }),
        throwsA(isA<Sh02ScopeError>()),
      );

      final focusedRowInGlobal = <String, dynamic>{
        ..._readyResponse,
        'data': {
          'evidence': [
            {
              'id': 'focused-row',
              'kind': 'SOURCE',
              'summary': '聚焦范围资料',
              'projection': sharedProjection(
                scope: {
                  'mode': 'FOCUS',
                  'domain_id': 'CTH',
                  'subject_id': 'focused-subject',
                },
              ),
            },
          ],
        },
      };
      expect(Sh02Snapshot.fromResponse(focusedRowInGlobal).evidence, isEmpty);

      final missingScope = Map<String, dynamic>.from(_readyResponse);
      final missingScopeData = Map<String, dynamic>.from(
        _readyResponse['data'] as Map,
      );
      final missingScopeRow = Map<String, dynamic>.from(
        (missingScopeData['evidence'] as List).first as Map,
      )..remove('projection');
      missingScopeData['evidence'] = [missingScopeRow];
      missingScope['data'] = missingScopeData;
      expect(Sh02Snapshot.fromResponse(missingScope).evidence, isEmpty);

      final missingPermission = Map<String, dynamic>.from(_readyResponse);
      final missingPermissionData = Map<String, dynamic>.from(
        _readyResponse['data'] as Map,
      );
      final missingPermissionRow = Map<String, dynamic>.from(
        (missingPermissionData['evidence'] as List).first as Map,
      );
      final missingPermissionProjection = Map<String, dynamic>.from(
        missingPermissionRow['projection'] as Map,
      )..['read_allowed'] = false;
      missingPermissionRow['projection'] = missingPermissionProjection;
      missingPermissionData['evidence'] = [missingPermissionRow];
      missingPermission['data'] = missingPermissionData;
      expect(Sh02Snapshot.fromResponse(missingPermission).evidence, isEmpty);

      final missingIntegrity = Map<String, dynamic>.from(_readyResponse);
      final missingIntegrityData = Map<String, dynamic>.from(
        _readyResponse['data'] as Map,
      );
      final missingIntegrityRow = Map<String, dynamic>.from(
        (missingIntegrityData['evidence'] as List).first as Map,
      );
      final missingIntegrityProjection = Map<String, dynamic>.from(
        missingIntegrityRow['projection'] as Map,
      );
      missingIntegrityProjection['integrity'] = <String, dynamic>{
        ...(missingIntegrityProjection['integrity'] as Map),
        'integrity_version': 1,
      };
      missingIntegrityRow['projection'] = missingIntegrityProjection;
      missingIntegrityData['evidence'] = [missingIntegrityRow];
      missingIntegrity['data'] = missingIntegrityData;
      expect(Sh02Snapshot.fromResponse(missingIntegrity).evidence, isEmpty);

      final crossSubject = sharedResponseWithRowScopes(
        _readyResponse,
        pageScope: focusPageScope,
        rowScopes: {
          'evidence': {
            'mode': 'FOCUS',
            'domain_id': 'CTH',
            'subject_id': 'different-subject',
          },
        },
      );
      expect(Sh02Snapshot.fromResponse(crossSubject).evidence, isEmpty);
    },
  );
}

Widget _app(
  Sh02Repository repository, {
  Locale locale = const Locale('zh', 'CN'),
}) => sharedTestApp(
  Sh02Screen(client: LumenisCoreClient(), repository: repository),
  locale: locale,
);

class _FakeSh02Repository implements Sh02Repository {
  _FakeSh02Repository(this.response);

  final Map<String, dynamic> response;

  @override
  Future<Sh02Snapshot> loadLibrary() async =>
      Sh02Snapshot.fromResponse(response);
}

final _readyResponse = sharedRuntimeResponse('SH-02', {
  'evidence': [
    {
      'id': 'EV-PRIVATE-ID',
      'kind': 'SOURCE',
      'summary': '已核实的市场信号',
      'source': '公开报道',
      'captured_at': '2026-09-22',
      'freshness': 'FRESH',
      'projection': sharedProjection(scope: {'mode': 'GLOBAL_ALL'}),
      'scope_verified': true,
      'evidence_backed': true,
      'permission': {'read': true, 'decision': 'ALLOW'},
      'lineage_verified': true,
      'integrity_verified': true,
      'scope': {'mode': 'GLOBAL_ALL', 'global': true},
      'lineage': ['SOURCE', 'EVIDENCE', 'CANONICAL', 'METRIC'],
      'origin': '商业运营',
      'private_path': r'C:\private\path',
      'provider': 'provider-secret',
    },
    {
      'id': 'bad',
      'kind': 'SOURCE',
      'summary': '<script>raw-secret-marker</script>',
    },
  ],
});

Map<String, dynamic> _readyResponseWithItems(int count) {
  final response = Map<String, dynamic>.from(_readyResponse);
  final data = Map<String, dynamic>.from(response['data'] as Map);
  final template = Map<String, dynamic>.from(
    (data['evidence'] as List).first as Map,
  );
  data['evidence'] = [
    for (var index = 0; index < count; index++)
      {
        ...template,
        'id': index == 0 ? 'EV-PRIVATE-ID' : 'verified-$index',
        'summary': index == 0 ? '已核实的市场信号' : '已核实资料 $index',
      },
  ];
  response['data'] = data;
  return response;
}
