import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/core/lumenis_theme.dart';
import 'package:lumenis_app/features/system/sys01/sys01_repository.dart';
import 'package:lumenis_app/features/system/sys01/sys01_screen.dart';
import 'package:lumenis_app/features/system/sys01/sys01_snapshot.dart';

void main() {
  testWidgets('mobile prioritizes failed Worker and DLQ before total Workers', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(_app(_FakeSys01Repository(_snapshot())));
    await tester.pumpAndSettle();

    expect(find.byKey(const ValueKey('sys01/layout-mobile')), findsOneWidget);
    expect(find.text('健康'), findsNWidgets(2));
    expect(find.text('2'), findsOneWidget);
    expect(find.text('0'), findsNWidgets(2));

    final failedY = tester
        .getTopLeft(find.byKey(const ValueKey('sys01/count-failed-workers')))
        .dy;
    final dlqY = tester
        .getTopLeft(find.byKey(const ValueKey('sys01/count-dlq')))
        .dy;
    final totalY = tester
        .getTopLeft(
          find.byKey(const ValueKey('sys01/count-registered-workers')),
        )
        .dy;
    expect(failedY, lessThan(dlqY));
    expect(dlqY, lessThan(totalY));
    expect(tester.takeException(), isNull);
  });

  testWidgets('desktop places operational spine beside the source rail', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(_app(_FakeSys01Repository(_snapshot())));
    await tester.pumpAndSettle();

    expect(find.byKey(const ValueKey('sys01/layout-desktop')), findsOneWidget);
    expect(find.byKey(const ValueKey('sys01/counts')), findsOneWidget);
    expect(find.byKey(const ValueKey('sys01/guardrails')), findsOneWidget);
    expect(find.byKey(const ValueKey('sys01/source-rail')), findsOneWidget);
    expect(find.text('Runtime 样本时间'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('unavailable counts do not render as zero', (tester) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      _app(
        _FakeSys01Repository(
          _snapshot(
            registeredWorkers: const Sys01Count(value: null, state: 'offline'),
            failedWorkers: const Sys01Count(value: null, state: 'offline'),
            dlqTotal: const Sys01Count(value: null, state: 'offline'),
            overall: null,
            overallState: 'offline',
            sampleTimestamp: null,
            guardianName: null,
            reaperRunning: null,
            openBreakers: null,
            registeredBreakers: null,
            hasCompleteRuntimeSample: false,
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('0'), findsNothing);
    expect(find.text('当前不可用'), findsNWidgets(3));
    expect(find.text('状态不可用'), findsOneWidget);
    expect(find.text('未提供'), findsWidgets);
    expect(tester.takeException(), isNull);
  });
}

Widget _app(Sys01Repository repository) => MaterialApp(
  theme: LumenisTheme.dark,
  home: Sys01Screen(client: LumenisCoreClient(), repository: repository),
);

class _FakeSys01Repository implements Sys01Repository {
  const _FakeSys01Repository(this.snapshot);

  final Sys01Snapshot snapshot;

  @override
  Future<Sys01Snapshot> load() async => snapshot;
}

Sys01Snapshot _snapshot({
  Sys01Count registeredWorkers = const Sys01Count(value: 3, state: 'ready'),
  Sys01Count failedWorkers = const Sys01Count(value: 2, state: 'ready'),
  Sys01Count dlqTotal = const Sys01Count(value: 0, state: 'ready'),
  String? overall = 'healthy',
  String overallState = 'ok',
  String? sampleTimestamp = '2026-09-20T09:30:00Z',
  String? guardianName = 'legacy',
  bool? reaperRunning = true,
  int? openBreakers = 0,
  int? registeredBreakers = 5,
  bool hasCompleteRuntimeSample = true,
}) => Sys01Snapshot(
  overall: overall,
  overallState: overallState,
  registeredWorkers: registeredWorkers,
  failedWorkers: failedWorkers,
  dlqTotal: dlqTotal,
  sampleTimestamp: sampleTimestamp,
  guardianName: guardianName,
  reaperRunning: reaperRunning,
  openBreakers: openBreakers,
  registeredBreakers: registeredBreakers,
  hasCompleteRuntimeSample: hasCompleteRuntimeSample,
);
