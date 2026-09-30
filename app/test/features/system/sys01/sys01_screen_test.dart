import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/core/lumenis_theme.dart';
import 'package:lumenis_app/l10n/lumenis_localizations.dart';
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
    expect(find.text('正常'), findsNWidgets(2));
    expect(find.text('2'), findsOneWidget);
    expect(find.text('0'), findsNWidgets(2));
    expect(find.text('异常后台进程'), findsOneWidget);
    expect(find.text('失败队列记录总数'), findsOneWidget);
    expect(find.text('后台进程总数'), findsOneWidget);

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
    final countOrigin = tester.getTopLeft(
      find.byKey(const ValueKey('sys01/counts')),
    );
    final guardrailOrigin = tester.getTopLeft(
      find.byKey(const ValueKey('sys01/guardrails')),
    );
    final sourceOrigin = tester.getTopLeft(
      find.byKey(const ValueKey('sys01/source-rail')),
    );
    final countWidth = tester
        .getSize(find.byKey(const ValueKey('sys01/counts')))
        .width;
    final guardrailWidth = tester
        .getSize(find.byKey(const ValueKey('sys01/guardrails')))
        .width;
    expect(countOrigin.dx, lessThan(guardrailOrigin.dx));
    expect(guardrailOrigin.dx, lessThan(sourceOrigin.dx));
    expect(guardrailWidth, lessThan(countWidth));
    expect(find.text('状态检查时间'), findsOneWidget);
    expect(find.text('系统运行监测'), findsOneWidget);
    expect(find.text('观测编号'), findsOneWidget);
    expect(find.text('sys01rt-0123456789abcdef01234567'), findsOneWidget);
    expect(find.text('只读，不修改运行状态'), findsOneWidget);
    expect(find.text('已识别'), findsOneWidget);
    expect(find.text('legacy'), findsNothing);
    for (final internalTerm in [
      'RuntimeGuardian',
      'Runtime',
      'Worker',
      'DLQ',
      'Reaper',
      '熔断器',
      'Owner',
      'SYSTEM /',
      'Evidence',
      'Core',
      'SYS-01',
      'ready',
    ]) {
      expect(find.textContaining(internalTerm), findsNothing);
    }
    expect(tester.takeException(), isNull);
  });

  testWidgets('tablet keeps the operational status readable in English', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1024, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      _app(_FakeSys01Repository(_snapshot()), locale: const Locale('en')),
    );
    await tester.pumpAndSettle();

    expect(find.text('Runtime status'), findsOneWidget);
    expect(find.byKey(const ValueKey('sys01/layout-tablet')), findsOneWidget);
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
            observationAvailable: false,
            observationTraceId: null,
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
    expect(find.text('暂不可用'), findsWidgets);
    expect(find.text('暂无可用观测'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'authentication, access, offline, and response failures use safe copy',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(390, 844));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      final failures = [
        (
          error: Exception('HTTP 401 private authentication response'),
          title: '系统运行状态暂时无法打开',
          detail: '可重试读取，或返回后稍后再试。',
          canRetry: false,
        ),
        (
          error: Exception('HTTP 403 private permission response'),
          title: '系统运行状态不可访问',
          detail: '当前页面无法读取该内容。',
          canRetry: false,
        ),
        (
          error: const SocketException('private.internal service unavailable'),
          title: '系统服务暂不可用',
          detail: '暂时无法读取当前运行状态。请检查连接后重试。',
          canRetry: true,
        ),
        (
          error: const FormatException('Core HTTP 500 runtime contract detail'),
          title: '运行状态暂不可用',
          detail: '系统暂时无法提供有效状态，请稍后重试。',
          canRetry: true,
        ),
      ];

      for (final failure in failures) {
        await tester.pumpWidget(const SizedBox.shrink());
        await tester.pumpWidget(_app(_FailingSys01Repository(failure.error)));
        await tester.pumpAndSettle();

        expect(find.text(failure.title), findsOneWidget);
        expect(find.text(failure.detail), findsOneWidget);
        if (failure.error.toString().contains('401') ||
            failure.error.toString().contains('403')) {
          final visibleText = tester
              .widgetList<Text>(find.byType(Text))
              .map((text) => text.data ?? text.textSpan?.toPlainText() ?? '')
              .join('\n')
              .toLowerCase();
          for (final term in ['登录', '账号', '账户', '管理员', '检查连接', '检查网络']) {
            expect(visibleText, isNot(contains(term)));
          }
        }
        expect(
          find.text('重新检查'),
          failure.canRetry ? findsOneWidget : findsNothing,
        );
        for (final internalTerm in [
          'Core',
          'RuntimeGuardian',
          'HTTP',
          'private',
          'contract',
          'SYS-01',
        ]) {
          expect(find.textContaining(internalTerm), findsNothing);
        }
        expect(tester.takeException(), isNull);
      }
    },
  );
}

Widget _app(
  Sys01Repository repository, {
  Locale locale = const Locale('zh', 'CN'),
}) => MaterialApp(
  theme: LumenisTheme.dark,
  locale: locale,
  supportedLocales: LumenisLocalizations.supportedLocales,
  localizationsDelegates: const [
    LumenisLocalizations.delegate,
    GlobalMaterialLocalizations.delegate,
    GlobalWidgetsLocalizations.delegate,
    GlobalCupertinoLocalizations.delegate,
  ],
  home: Scaffold(
    body: Sys01Screen(client: LumenisCoreClient(), repository: repository),
  ),
);

class _FakeSys01Repository implements Sys01Repository {
  const _FakeSys01Repository(this.snapshot);

  final Sys01Snapshot snapshot;

  @override
  Future<Sys01Snapshot> load() async => snapshot;
}

class _FailingSys01Repository implements Sys01Repository {
  const _FailingSys01Repository(this.error);

  final Object error;

  @override
  Future<Sys01Snapshot> load() async => throw error;
}

Sys01Snapshot _snapshot({
  Sys01Count registeredWorkers = const Sys01Count(value: 3, state: 'ready'),
  Sys01Count failedWorkers = const Sys01Count(value: 2, state: 'ready'),
  Sys01Count dlqTotal = const Sys01Count(value: 0, state: 'ready'),
  String? overall = 'healthy',
  String overallState = 'ok',
  String? sampleTimestamp = '2026-09-20T09:30:00Z',
  bool observationAvailable = true,
  String? observationTraceId = 'sys01rt-0123456789abcdef01234567',
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
  observationAvailable: observationAvailable,
  observationTraceId: observationTraceId,
  guardianName: guardianName,
  reaperRunning: reaperRunning,
  openBreakers: openBreakers,
  registeredBreakers: registeredBreakers,
  hasCompleteRuntimeSample: hasCompleteRuntimeSample,
);
