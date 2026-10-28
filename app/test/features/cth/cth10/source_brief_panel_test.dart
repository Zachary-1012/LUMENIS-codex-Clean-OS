import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter/semantics.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences_platform_interface/in_memory_shared_preferences_async.dart';
import 'package:shared_preferences_platform_interface/shared_preferences_async_platform_interface.dart';
import 'package:shared_preferences_platform_interface/types.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/core/lumenis_theme.dart';
import 'package:lumenis_app/features/cth/cth10/cth10_repository.dart';
import 'package:lumenis_app/features/cth/cth10/cth10_screen.dart';
import 'package:lumenis_app/features/cth/cth10/source_brief_panel.dart';
import 'package:lumenis_app/l10n/lumenis_localizations.dart';

void main() {
  testWidgets('pending admission never renders a saved brief', (tester) async {
    final client = _SourceBriefClient()
      ..startResponse = _taskEnvelope(state: 'pending', canResume: false);

    await tester.pumpWidget(_panelApp(client));
    await tester.pumpAndSettle();
    await _tapCreate(tester);
    await tester.pumpAndSettle();

    expect(client.startCalls, [
      {'domainId': 'CTH', 'limit': 30, 'businessQuestion': null},
    ]);
    expect(client.jobReads, isEmpty);
    expect(find.text('已受理，等待整理'), findsOneWidget);
    expect(find.text('已保存并重新核验'), findsNothing);
    expect(find.text('来源记录'), findsNothing);
    await _expandRecovery(tester);
    expect(find.text(_taskId), findsOneWidget);
  });

  testWidgets('succeeded task needs a separate verified job readback', (
    tester,
  ) async {
    final client = _SourceBriefClient()
      ..startResponse = _taskEnvelope(state: 'succeeded', canResume: false)
      ..jobResponse = {
        'ok': true,
        'result': {'job_id': _jobId},
      };

    await tester.pumpWidget(_panelApp(client));
    await tester.pumpAndSettle();
    await _tapCreate(tester);
    await tester.pumpAndSettle();

    expect(client.jobReads, [_jobId]);
    expect(find.text('暂时无法确认任务状态'), findsOneWidget);
    expect(find.text('整理结束，正在核对已保存简报'), findsNothing);
    expect(find.text('暂时无法核验返回的简报，尚未显示为已完成。'), findsOneWidget);
    expect(find.text('已保存并重新核验'), findsNothing);
    expect(find.text('来源记录'), findsNothing);
  });

  testWidgets('source brief saves an editable result and can reopen it', (
    tester,
  ) async {
    final client = _SourceBriefClient()
      ..startResponse = _taskEnvelope(state: 'succeeded', canResume: false)
      ..jobResponse = _savedJobEnvelope();
    await _showCompletedResult(tester, client);

    final save = find.byKey(const ValueKey('source-brief/save-research'));
    await tester.ensureVisible(save);
    await tester.tap(save);
    await tester.pumpAndSettle();

    expect(client.saveCalls, hasLength(1));
    expect(client.saveCalls.single['jobId'], _jobId);
    expect(client.saveCalls.single['title'], '来源简报');
    expect(client.reopenArtifactIds, ['ART-0123456789abcdef']);
    expect(find.text('已保存，可在研究成果中继续修订'), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('source-brief/save-research')));
    await tester.pumpAndSettle();

    expect(client.reopenArtifactIds, [
      'ART-0123456789abcdef',
      'ART-0123456789abcdef',
    ]);
    expect(find.text('已重新打开保存的研究成果'), findsOneWidget);
    expect(
      find.byKey(const ValueKey('source-brief/reopened-research')),
      findsOneWidget,
    );
    expect(tester.takeException(), isNull);
  });

  testWidgets('shared adoption requires explicit confirmation and readback', (
    tester,
  ) async {
    final client = _SourceBriefClient()
      ..startResponse = _taskEnvelope(state: 'succeeded', canResume: false)
      ..jobResponse = _savedJobEnvelope()
      ..sharedAdoptionPrepareResponse = _sharedAdoptionPrepareEnvelope()
      ..sharedAdoptionApplyReplayed = false;
    await _showCompletedResult(tester, client);

    final action = find.byKey(const ValueKey('source-brief/adopt-to-shared'));
    await tester.ensureVisible(action);
    await tester.tap(action);
    await tester.pumpAndSettle();

    expect(client.sharedAdoptionCalls.map((call) => call['mode']), ['prepare']);
    expect(find.text('保存到共享成果？'), findsOneWidget);
    expect(find.text('将包含 1 条来源，展示 1 条引用。'), findsOneWidget);
    expect(client.sharedReopenArtifactIds, isEmpty);

    await tester.tap(
      find.byKey(const ValueKey('source-brief/shared-adoption/cancel')),
    );
    await tester.pumpAndSettle();
    expect(client.sharedAdoptionCalls.map((call) => call['mode']), ['prepare']);

    await tester.ensureVisible(action);
    await tester.tap(action);
    await tester.pumpAndSettle();
    await tester.tap(
      find.byKey(const ValueKey('source-brief/shared-adoption/confirm')),
    );
    await tester.pumpAndSettle();

    expect(client.sharedAdoptionCalls.map((call) => call['mode']), [
      'prepare',
      'apply',
    ]);
    final apply = client.sharedAdoptionCalls.last;
    expect(apply['confirm'], isTrue);
    expect(apply['confirmedResource'], 'resource:exact-approval');
    expect(apply['requestId'], client.sharedAdoptionCalls.first['requestId']);
    expect(client.sharedReopenArtifactIds, ['ART-2222222222222222']);
    expect(find.text('共享成果已保存并独立重开；原来源简报保持不变。'), findsOneWidget);
    expect(
      find.byKey(const ValueKey('source-brief/shared-adoption/reopened')),
      findsOneWidget,
    );
    expect(tester.takeException(), isNull);
  });

  testWidgets('new verified result reveals once and can be skipped', (
    tester,
  ) async {
    final client = _SourceBriefClient()
      ..startResponse = _taskEnvelope(state: 'succeeded', canResume: false)
      ..jobResponse = _savedJobEnvelope();

    await tester.pumpWidget(_panelApp(client));
    await tester.pumpAndSettle();
    await _tapCreate(tester);

    var started = false;
    for (var frame = 0; frame < 18; frame++) {
      await tester.pump(const Duration(milliseconds: 16));
      if (find
          .byKey(const ValueKey('generated-result-reveal/paint'))
          .evaluate()
          .isNotEmpty) {
        started = true;
        break;
      }
    }
    expect(started, isTrue, reason: 'The verified new result should reveal.');
    expect(
      find.byKey(const ValueKey('generated-result-reveal/paint')),
      findsOneWidget,
    );
    expect(find.text('可核验来源标题'), findsWidgets);

    await tester.tap(
      find.byKey(const ValueKey('generated-result-reveal/skip')),
    );
    await tester.pumpAndSettle();

    _expectSkipUnavailable(tester);
    expect(find.text('已保存并重新核验'), findsOneWidget);
  });

  testWidgets('scroll before motion preference loads suppresses late reveal', (
    tester,
  ) async {
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.binding.setSurfaceSize(const Size(390, 900));
    final previousPlatform = SharedPreferencesAsyncPlatform.instance;
    final preferences = _DelayedMotionPreferences();
    SharedPreferencesAsyncPlatform.instance = preferences;
    addTearDown(() {
      preferences.resolveRead(null);
      SharedPreferencesAsyncPlatform.instance = previousPlatform;
    });
    final client = _SourceBriefClient()
      ..startResponse = _taskEnvelope(state: 'succeeded', canResume: false)
      ..jobResponse = _savedJobEnvelope();

    await _showCompletedResult(tester, client);
    await tester.drag(
      find
          .descendant(
            of: find.byType(SourceBriefPanel),
            matching: find.byType(Scrollable),
          )
          .first,
      const Offset(0, 80),
    );
    await tester.pumpAndSettle();

    preferences.resolveRead(null);
    await tester.pumpAndSettle();

    _expectSkipUnavailable(tester);
  });

  testWidgets(
    'backgrounding before motion preference loads suppresses reveal',
    (tester) async {
      final previousPlatform = SharedPreferencesAsyncPlatform.instance;
      final preferences = _DelayedMotionPreferences();
      SharedPreferencesAsyncPlatform.instance = preferences;
      addTearDown(() {
        preferences.resolveRead(null);
        SharedPreferencesAsyncPlatform.instance = previousPlatform;
      });
      final client = _SourceBriefClient()
        ..startResponse = _taskEnvelope(state: 'succeeded', canResume: false)
        ..jobResponse = _savedJobEnvelope();

      await _showCompletedResult(tester, client);
      tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.inactive);
      preferences.resolveRead(null);
      await tester.pumpAndSettle();

      _expectSkipUnavailable(tester);
      tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
    },
  );

  testWidgets(
    'pointer interaction before motion preference loads suppresses reveal',
    (tester) async {
      final previousPlatform = SharedPreferencesAsyncPlatform.instance;
      final preferences = _DelayedMotionPreferences();
      SharedPreferencesAsyncPlatform.instance = preferences;
      addTearDown(() {
        preferences.resolveRead(null);
        SharedPreferencesAsyncPlatform.instance = previousPlatform;
      });
      final client = _SourceBriefClient()
        ..startResponse = _taskEnvelope(state: 'succeeded', canResume: false)
        ..jobResponse = _savedJobEnvelope();

      await _showCompletedResult(tester, client);
      await tester.tap(find.text('已保存并重新核验'));
      await tester.pump();
      preferences.resolveRead(null);
      await tester.pumpAndSettle();

      _expectSkipUnavailable(tester);
    },
  );

  testWidgets('semantic copy activation cancels pending result reveal', (
    tester,
  ) async {
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.binding.setSurfaceSize(const Size(1200, 2600));
    final previousPlatform = SharedPreferencesAsyncPlatform.instance;
    final preferences = _DelayedMotionPreferences();
    SharedPreferencesAsyncPlatform.instance = preferences;
    addTearDown(() {
      preferences.resolveRead(null);
      SharedPreferencesAsyncPlatform.instance = previousPlatform;
    });
    final client = _SourceBriefClient()
      ..startResponse = _taskEnvelope(state: 'succeeded', canResume: false)
      ..jobResponse = _savedJobEnvelope();

    await _showCompletedResult(tester, client);
    final semantics = tester.ensureSemantics();
    try {
      final copyNode = tester.getSemantics(
        find.byKey(const ValueKey('source-brief/copy-job')),
      );
      copyNode.owner!.performAction(copyNode.id, SemanticsAction.tap);
      await tester.pumpAndSettle();
      preferences.resolveRead(null);
      await tester.pumpAndSettle();

      _expectSkipUnavailable(tester);
    } finally {
      semantics.dispose();
    }
  });

  testWidgets('saved result effect can be disabled by the user', (
    tester,
  ) async {
    final client = _SourceBriefClient()
      ..startResponse = _taskEnvelope(state: 'succeeded', canResume: false)
      ..jobResponse = _savedJobEnvelope();

    await tester.pumpWidget(_panelApp(client));
    await tester.pumpAndSettle();
    await _expandPreferences(tester);
    await tester.tap(find.byKey(const ValueKey('source-brief/reveal/off')));
    await tester.pumpAndSettle();
    await _tapCreate(tester);
    await tester.pumpAndSettle();

    expect(find.text('已保存并重新核验'), findsOneWidget);
    _expectSkipUnavailable(tester);
  });

  testWidgets('failed refresh hides saved result and stops checking copy', (
    tester,
  ) async {
    final client = _SourceBriefClient()
      ..startResponse = _taskEnvelope(state: 'succeeded', canResume: false)
      ..jobResponse = _savedJobEnvelope()
      ..taskResponse = {'ok': false, 'code': 'ACCESS_DENIED'};
    await tester.pumpWidget(_panelApp(client));
    await tester.pumpAndSettle();
    await _tapCreate(tester);
    await tester.pumpAndSettle();
    expect(find.text('已保存并重新核验'), findsOneWidget);

    await tester.ensureVisible(find.text('刷新状态'));
    await tester.tap(find.text('刷新状态'));
    await tester.pumpAndSettle();
    expect(find.text('当前范围无法打开或整理这份简报。'), findsOneWidget);
    expect(find.text('暂时无法确认任务状态'), findsOneWidget);
    expect(find.text('整理结束，正在核对已保存简报'), findsNothing);
    expect(find.text('已保存并重新核验'), findsNothing);
    expect(find.text('来源记录'), findsNothing);
    await _expandRecovery(tester);
    expect(find.text(_taskId), findsOneWidget);

    client.taskResponse = _taskEnvelope(state: 'succeeded', canResume: false);
    await tester.ensureVisible(find.text('刷新状态'));
    await tester.tap(find.text('刷新状态'));
    await tester.pumpAndSettle();
    expect(find.text('已保存并重新核验'), findsOneWidget);
    expect(find.text('整理已完成'), findsOneWidget);
    expect(find.text('暂时无法确认任务状态'), findsNothing);
    expect(client.startCalls, hasLength(1));
    expect(client.jobReads, [_jobId, _jobId]);
    _expectSkipUnavailable(tester);
  });

  testWidgets('interrupted task resumes with the same task identifier', (
    tester,
  ) async {
    final client = _SourceBriefClient()
      ..startResponse = _taskEnvelope(state: 'interrupted', canResume: true)
      ..resumeResponse = _taskEnvelope(state: 'pending', canResume: true);

    await tester.pumpWidget(_panelApp(client));
    await tester.pumpAndSettle();
    await _tapCreate(tester);
    await tester.pumpAndSettle();

    expect(find.text('本次整理已中断'), findsOneWidget);
    await tester.ensureVisible(find.text('继续这次整理'));
    await tester.tap(find.text('继续这次整理'));
    await tester.pumpAndSettle();

    expect(client.startCalls, hasLength(1));
    expect(client.resumeCalls, [
      {'domainId': 'CTH', 'taskId': _taskId},
    ]);
    expect(client.jobReads, isEmpty);
    expect(find.text('已受理，等待整理'), findsOneWidget);
    await _expandRecovery(tester);
    expect(find.text(_taskId), findsOneWidget);
    expect(find.text('已保存并重新核验'), findsNothing);
  });

  testWidgets('brief reference opens the actual saved job', (tester) async {
    final client = _SourceBriefClient()..jobResponse = _savedJobEnvelope();

    await tester.pumpWidget(_panelApp(client));
    await tester.pumpAndSettle();
    await _expandRecovery(tester);
    await tester.enterText(
      find.byKey(const ValueKey('source-brief/reference')),
      _jobId,
    );
    final open = find.widgetWithText(OutlinedButton, '打开');
    await tester.ensureVisible(open);
    await tester.tap(open);
    await tester.pumpAndSettle();

    expect(client.jobReads, [_jobId]);
    expect(client.startCalls, isEmpty);
    expect(client.taskReads, isEmpty);
    expect(find.text('已保存并重新核验'), findsOneWidget);
    _expectSkipUnavailable(tester);
    expect(find.text('可核验来源标题'), findsWidgets);
    expect(find.widgetWithText(SelectableText, _jobId), findsOneWidget);
  });

  testWidgets(
    'panel fits 390 and 1440 widths in Chinese, English, and Korean',
    (tester) async {
      addTearDown(() => tester.binding.setSurfaceSize(null));
      const locales = [Locale('zh', 'CN'), Locale('en'), Locale('ko')];
      const expectedTitles = {
        'zh': '来源简报',
        'en': 'Source brief',
        'ko': '출처 브리프',
      };
      const openLabels = {'zh': '打开', 'en': 'Open', 'ko': '열기'};

      for (final locale in locales) {
        for (final width in [390.0, 1440.0]) {
          final client = _SourceBriefClient()
            ..jobResponse = _savedJobEnvelope();
          await tester.binding.setSurfaceSize(Size(width, 900));
          await tester.pumpWidget(_panelApp(client, locale: locale));
          await tester.pumpAndSettle();
          await _expandRecovery(tester);
          final reference = find.byKey(
            const ValueKey('source-brief/reference'),
          );
          await tester.ensureVisible(reference);
          await tester.enterText(reference, _jobId);
          await tester.tap(
            find.widgetWithText(
              OutlinedButton,
              openLabels[locale.languageCode]!,
            ),
          );
          await tester.pumpAndSettle();
          final source = find.byKey(
            const ValueKey('source-brief/source/SRC-001'),
          );
          await tester.ensureVisible(source);
          await tester.tap(source);
          await tester.pumpAndSettle();

          expect(
            find.text(expectedTitles[locale.languageCode]!),
            findsOneWidget,
            reason: '${locale.languageCode} at width $width',
          );
          expect(
            tester.takeException(),
            isNull,
            reason: '${locale.languageCode} at width $width',
          );
        }
      }
    },
  );

  testWidgets(
    'question goes to real route and research paper shows bound source statements',
    (tester) async {
      addTearDown(() => tester.binding.setSurfaceSize(null));
      for (final locale in [
        const Locale('zh', 'CN'),
        const Locale('en'),
        const Locale('ko'),
      ]) {
        for (final (width, textScale) in [
          (390.0, 1.0),
          (1440.0, 1.0),
          (390.0, 2.0),
        ]) {
          final client = _SourceBriefClient()
            ..startResponse = _taskEnvelope(
              state: 'succeeded',
              canResume: false,
            )
            ..jobResponse = _researchJobEnvelope();
          await tester.binding.setSurfaceSize(Size(width, 900));
          await tester.pumpWidget(
            _panelApp(client, locale: locale, textScale: textScale),
          );
          await tester.pumpAndSettle();
          final input = find.byKey(const ValueKey('source-brief/question'));
          await tester.ensureVisible(input);
          await tester.enterText(
            input,
            '  Which report claims need checking?  ',
          );
          await _tapCreate(tester);
          await tester.pumpAndSettle();
          expect(
            client.startCalls.single['businessQuestion'],
            'Which report claims need checking?',
          );
          expect(
            find.byKey(const ValueKey('source-brief/report-paper')),
            findsOneWidget,
          );
          final excerpt = find.byKey(
            const ValueKey('source-brief/finding/finding_1'),
          );
          await tester.ensureVisible(excerpt);
          expect(
            find.text('The secondary report mentioned 18% growth.'),
            findsOneWidget,
          );
          expect(
            find.text('Could the full source support this claim?'),
            findsOneWidget,
          );
          expect(
            find.text('18%'),
            findsNothing,
          ); // Numbers are folded with the comparability caveat.
          final limits = find.byKey(
            const ValueKey('source-brief/research-limits'),
          );
          await tester.ensureVisible(limits);
          await tester.tap(
            find.descendant(of: limits, matching: find.byType(ListTile)).first,
          );
          await tester.pumpAndSettle();
          expect(find.text('18%'), findsOneWidget);
          expect(
            tester.takeException(),
            isNull,
            reason: '${locale.languageCode} / $width / scale$textScale',
          );
        }
      }
    },
  );

  testWidgets('blocked CTH-10 still exposes a separate source-brief entry', (
    tester,
  ) async {
    final client = _SourceBriefClient();
    await tester.pumpWidget(
      _cth10App(client, repository: _BlockedCth10Repository()),
    );
    await tester.pumpAndSettle();

    expect(find.text('报告资料暂不可用'), findsOneWidget);
    final entry = find.byKey(const ValueKey('cth10/source-brief-entry'));
    expect(entry, findsOneWidget);
    await tester.tap(entry);
    await tester.pumpAndSettle();

    expect(find.text('来源简报'), findsOneWidget);
    expect(find.byKey(const ValueKey('source-brief/create')), findsOneWidget);
    expect(client.startCalls, isEmpty);
  });
}

Widget _panelApp(
  LumenisCoreClient client, {
  Locale locale = const Locale('zh', 'CN'),
  double textScale = 1,
}) => _app(
  locale: locale,
  textScale: textScale,
  child: SourceBriefPanel(
    key: ObjectKey(client),
    client: client,
    onReturn: () {},
  ),
);

void _expectSkipUnavailable(WidgetTester tester) {
  expect(
    find.byKey(const ValueKey('generated-result-reveal/skip')),
    findsOneWidget,
  );
  expect(
    tester
        .widget<Opacity>(
          find.byKey(const ValueKey('generated-result-reveal/skip-opacity')),
        )
        .opacity,
    0,
  );
  expect(
    tester
        .widget<ExcludeFocus>(
          find.byKey(const ValueKey('generated-result-reveal/skip-focus')),
        )
        .excluding,
    isTrue,
  );
  expect(
    tester
        .widget<ExcludeSemantics>(
          find.byKey(const ValueKey('generated-result-reveal/skip-semantics')),
        )
        .excluding,
    isTrue,
  );
  expect(
    tester
        .widget<IgnorePointer>(
          find.byKey(const ValueKey('generated-result-reveal/skip-pointer')),
        )
        .ignoring,
    isTrue,
  );
  expect(
    find.byKey(const ValueKey('generated-result-reveal/paint')),
    findsNothing,
  );
}

Future<void> _expandRecovery(WidgetTester tester) async {
  final input = find.byKey(const ValueKey('source-brief/reference'));
  if (input.evaluate().isNotEmpty) return;
  final section = find.byKey(const ValueKey('source-brief/recovery-options'));
  final header = find
      .descendant(of: section, matching: find.byType(ListTile))
      .first;
  await tester.ensureVisible(header);
  await tester.tap(header);
  await tester.pumpAndSettle();
}

Future<void> _expandPreferences(WidgetTester tester) async {
  final choice = find.byKey(const ValueKey('source-brief/reveal/off'));
  if (choice.evaluate().isNotEmpty) return;
  final section = find.byKey(const ValueKey('source-brief/preferences'));
  final header = find
      .descendant(of: section, matching: find.byType(ListTile))
      .first;
  await tester.ensureVisible(header);
  await tester.tap(header);
  await tester.pumpAndSettle();
}

Future<void> _tapCreate(WidgetTester tester) async {
  final create = find.byKey(const ValueKey('source-brief/create'));
  await tester.ensureVisible(create);
  await tester.tap(create);
}

Future<void> _showCompletedResult(
  WidgetTester tester,
  _SourceBriefClient client,
) async {
  await tester.pumpWidget(_panelApp(client));
  await tester.pumpAndSettle();
  await _tapCreate(tester);
  await tester.pumpAndSettle();
  expect(find.text('已保存并重新核验'), findsOneWidget);
}

base class _DelayedMotionPreferences extends InMemorySharedPreferencesAsync {
  _DelayedMotionPreferences() : super.empty();

  final Completer<String?> _motionPreference = Completer<String?>();

  @override
  Future<String?> getString(String key, SharedPreferencesOptions options) {
    if (key == 'lumenis.source_brief.result_reveal.choice.v1') {
      return _motionPreference.future;
    }
    return super.getString(key, options);
  }

  void resolveRead(String? value) {
    if (!_motionPreference.isCompleted) _motionPreference.complete(value);
  }
}

Widget _cth10App(
  LumenisCoreClient client, {
  required Cth10Repository repository,
  Locale locale = const Locale('zh', 'CN'),
}) => _app(
  locale: locale,
  child: Cth10Screen(client: client, repository: repository),
);

Widget _app({
  required Widget child,
  Locale locale = const Locale('zh', 'CN'),
  double textScale = 1,
}) => MaterialApp(
  locale: locale,
  supportedLocales: const [Locale('zh', 'CN'), Locale('en'), Locale('ko')],
  localizationsDelegates: const [
    GlobalMaterialLocalizations.delegate,
    GlobalWidgetsLocalizations.delegate,
    GlobalCupertinoLocalizations.delegate,
    LumenisLocalizations.delegate,
  ],
  theme: LumenisTheme.dark,
  builder: (context, child) => MediaQuery(
    data: MediaQuery.of(
      context,
    ).copyWith(textScaler: TextScaler.linear(textScale)),
    child: child!,
  ),
  home: Scaffold(body: child),
);

class _SourceBriefClient extends LumenisCoreClient {
  final Map<String, dynamic> contextResponse = _globalContext;
  final List<Map<String, Object?>> startCalls = [];
  final List<String> taskReads = [];
  final List<Map<String, String>> resumeCalls = [];
  final List<String> jobReads = [];
  final List<Map<String, Object?>> saveCalls = [];
  final List<String> reopenArtifactIds = [];
  final List<Map<String, Object?>> sharedAdoptionCalls = [];
  final List<String> sharedReopenArtifactIds = [];

  Map<String, dynamic> startResponse = _taskEnvelope(
    state: 'pending',
    canResume: false,
  );
  Map<String, dynamic> taskResponse = _taskEnvelope(
    state: 'pending',
    canResume: false,
  );
  Map<String, dynamic> resumeResponse = _taskEnvelope(
    state: 'pending',
    canResume: false,
  );
  Map<String, dynamic> jobResponse = {
    'ok': false,
    'code': 'JOB_NOT_CONFIGURED',
  };

  Map<String, dynamic>? saveResponseOverride;
  Map<String, dynamic> sharedAdoptionPrepareResponse = {
    'ok': false,
    'code': 'NOT_CONFIGURED',
  };
  bool sharedAdoptionApplyReplayed = false;

  @override
  Map<String, dynamic>? get currentContextEnvelope => contextResponse;

  @override
  Future<Map<String, dynamic>> settingsContext() async => contextResponse;

  @override
  Future<Map<String, dynamic>> startSourceBriefTask({
    required String domainId,
    int limit = 30,
    String? businessQuestion,
  }) async {
    startCalls.add({
      'domainId': domainId,
      'limit': limit,
      'businessQuestion': businessQuestion,
    });
    return startResponse;
  }

  @override
  Future<Map<String, dynamic>> sourceBriefTask({
    required String domainId,
    required String taskId,
  }) async {
    taskReads.add(taskId);
    return taskResponse;
  }

  @override
  Future<Map<String, dynamic>> resumeSourceBriefTask({
    required String domainId,
    required String taskId,
  }) async {
    resumeCalls.add({'domainId': domainId, 'taskId': taskId});
    return resumeResponse;
  }

  @override
  Future<Map<String, dynamic>> sourceBriefJob({
    required String domainId,
    required String jobId,
  }) async {
    jobReads.add(jobId);
    return jobResponse;
  }

  @override
  Future<Map<String, dynamic>> saveSourceBriefResult({
    required String domainId,
    required String jobId,
    required String requestId,
    required String title,
  }) async {
    saveCalls.add({
      'domainId': domainId,
      'jobId': jobId,
      'requestId': requestId,
      'title': title,
    });
    return saveResponseOverride ??
        _savedWorkEnvelope(requestId: requestId, title: title);
  }

  @override
  Future<Map<String, dynamic>> reopenSourceBriefSavedWork({
    required String domainId,
    required String artifactId,
  }) async {
    reopenArtifactIds.add(artifactId);
    return _savedWorkEnvelope(
      requestId: saveCalls.last['requestId']! as String,
      title: saveCalls.last['title']! as String,
    );
  }

  @override
  Future<Map<String, dynamic>> adoptSourceBriefToShared({
    required String jobId,
    required String requestId,
    required String mode,
    String? title,
    bool confirm = false,
    String? confirmedResource,
  }) async {
    sharedAdoptionCalls.add({
      'jobId': jobId,
      'requestId': requestId,
      'mode': mode,
      'title': title,
      'confirm': confirm,
      'confirmedResource': confirmedResource,
    });
    if (mode == 'prepare') return sharedAdoptionPrepareResponse;
    return _sharedAdoptionWorkEnvelope(
      requestId: requestId,
      replayed: sharedAdoptionApplyReplayed,
    );
  }

  @override
  Future<Map<String, dynamic>> reopenSharedSavedWork(String artifactId) async {
    sharedReopenArtifactIds.add(artifactId);
    return _sharedAdoptionWorkEnvelope(
      requestId: sharedAdoptionCalls.last['requestId']! as String,
    );
  }
}

Map<String, dynamic> _sharedAdoptionBinding() => {
  'schema': 'domain-report-adoption/v1',
  'job_id': _jobId,
  'actor_id': 'principal:local-test',
  'source_scope': {
    'domain_id': 'cth',
    'subject_id': null,
    'brand_focus_id': null,
    'global_scope': true,
  },
  'target_scope': {'scope_kind': 'shared_workspace', 'version': 1},
  'report_hash': 'a' * 64,
  'source_count': 1,
  'sources_sha256': 'c' * 64,
  'authority': 'SOURCE_REFERENCE_ONLY',
  'semantic_verification': 'NOT_PERFORMED',
};

Map<String, dynamic> _sharedAdoptionPrepareEnvelope() => {
  'ok': true,
  'result': {
    'state': 'requires_explicit_export_approval',
    'resource': 'resource:exact-approval',
    'operation': 'data_export',
    'binding': _sharedAdoptionBinding(),
    'displayed_citations': 1,
    'guarded_source_count': 1,
    'title': 'CTH 来源简报',
  },
};

Map<String, dynamic> _sharedAdoptionWorkEnvelope({
  required String requestId,
  bool? replayed,
}) => {
  'ok': true,
  'result': {
    'artifact': {'artifact_id': 'ART-2222222222222222', 'sha256': 'e' * 64},
    'document': {
      'kind': 'report',
      'title': 'CTH 来源简报',
      'markdown': '# 独立共享成果\n\n来源绑定已核验。',
      'request_id': requestId,
      'payload': {'domain_report_adoption': _sharedAdoptionBinding()},
    },
    'return_ref': {
      'artifact_id': 'ART-2222222222222222',
      'work_id': 'WORK-222222222222222222222222',
      'version': 1,
      'scope': {'scope_kind': 'shared_workspace', 'version': 1},
    },
    'replayed': ?replayed,
  },
};

Map<String, dynamic> _savedWorkEnvelope({
  required String requestId,
  required String title,
}) => {
  'ok': true,
  'result': {
    'artifact': {
      'artifact_id': 'ART-0123456789abcdef',
      'sha256': List.filled(64, 'd').join(),
    },
    'document': {
      'kind': 'research',
      'title': title,
      'markdown': '# 来源简报\n\n已核验来源与范围。',
      'request_id': requestId,
      'payload': {
        'source_brief_reference': {
          'job_id': _jobId,
          'actor_id': 'principal:local-test',
          'artifact_hash': List.filled(64, 'a').join(),
          'scope': {
            'domain_id': 'cth',
            'subject_id': null,
            'brand_focus_id': null,
            'global_scope': true,
          },
        },
      },
    },
    'return_ref': {
      'artifact_id': 'ART-0123456789abcdef',
      'work_id': 'WORK-0123456789abcdef01234567',
      'version': 1,
      'scope': {
        'domain_id': 'cth',
        'subject_id': null,
        'brand_focus_id': null,
        'global_scope': true,
      },
    },
  },
};

class _BlockedCth10Repository implements Cth10Repository {
  @override
  Future<Cth10WorkspaceData> load() async {
    throw const Cth10BlockedException(
      Cth10BlockedReason.reportScopeUnavailable,
    );
  }
}

Map<String, dynamic> _taskEnvelope({
  required String state,
  required bool canResume,
}) => {
  'ok': true,
  'task': {
    'task_id': _taskId,
    'job_id': _jobId,
    'state': state,
    'can_resume': canResume,
    'error': null,
    'result': null,
    'review_status': 'HUMAN_PENDING',
    'publish_status': 'not_performed',
  },
  'publish_status': 'not_performed',
};

Map<String, dynamic> _savedJobEnvelope() => {
  'ok': true,
  'result': {
    'job_id': _jobId,
    'job_state': 'completed',
    'artifact_outcome': {
      'state': 'persisted_and_reopened_verified',
      'report_id': _jobId,
      'artifact_hash': 'a' * 64,
      'source_count': 1,
    },
    'source_brief': {
      'scope': {
        'product_id': 'CTH',
        'domain_id': 'cth',
        'global': true,
        'subject_id': null,
        'brand_focus_id': null,
        'entity_label': '全球商业',
        'scope_key': 'b' * 64,
      },
      'records': [
        {
          'source_id': 'SRC-001',
          'scope_evidence_ref': 'EV-001',
          'evidence_id': 'EV-001',
          'title': '可核验来源标题',
          'source_url': 'https://example.test/source/1',
          'publish_datetime': '2026-10-01T08:00:00Z',
          'captured_at': '2026-10-01T08:05:00Z',
        },
      ],
    },
    'business_question': null,
    'business_analysis': {'state': 'not_requested'},
    'review_status': 'HUMAN_PENDING',
  },
  'publish_status': 'not_performed',
};

Map<String, dynamic> _researchJobEnvelope() {
  final envelope = _savedJobEnvelope();
  final result = envelope['result'] as Map<String, dynamic>;
  result['business_question'] = 'Which report claims need checking?';
  result['research_analysis'] = {
    'schema': 'source_bound_research.v1',
    'status': 'research_draft',
    'scope': (result['source_brief'] as Map)['scope'],
    'goal': 'Which report claims need checking?',
    'summary': 'Source-bound reading draft.',
    'source_set_sha256': 'c' * 64,
    'permission_granted': false,
    'canonical_promotion': false,
    'ranked_findings': [
      {
        'finding_id': 'finding_1',
        'source_id': 'SRC-001',
        'lineage_id': 'lineage_1',
        'content': 'The secondary report mentioned 18% growth.',
        'title': '可核验来源标题',
        'evidence_refs': ['EV-001'],
        'claim_type': 'source_statement',
        'validated': false,
        'fact_verified': false,
        'confidence': null,
        'excerpt_truncated': true,
      },
    ],
    'evidence_lineage': [
      {
        'lineage_id': 'lineage_1',
        'source': 'SRC-001',
        'evidence_id': 'EV-001',
        'provenance': {'fact_verified': false},
      },
    ],
    'hypotheses': [
      {
        'statement': 'Could the full source support this claim?',
        'status': 'proposed',
        'claim_type': 'hypothesis',
        'confidence': null,
        'source_set_sha256': 'c' * 64,
        'finding_ids': ['finding_1'],
        'evidence_refs': ['EV-001'],
        'validation_needed': ['Check time, scope and independent evidence.'],
      },
    ],
    'comparisons': [
      {
        'source_id': 'SRC-001',
        'evidence_refs': ['EV-001'],
        'numeric_literals': ['18%'],
        'comparison_status': 'NOT_COMPARABLE_WITHOUT_MEASURE_DEFINITIONS',
        'unit': null,
        'currency': null,
        'period': null,
        'denominator': null,
      },
    ],
    'limitations': [
      'The report does not establish an observed business result.',
    ],
  };
  return envelope;
}

const String _taskId = 'rbrief_01234567-89ab-cdef-0123-456789abcdef';
const String _jobId = 'brief-0123456789abcdef0123456789abcdef';

const Map<String, dynamic> _globalContext = {
  'ok': true,
  'contract': 'lumenis.context.v1',
  'selection_only': true,
  'context': {
    'mode': 'GLOBAL_ALL',
    'domain_id': null,
    'subject_id': null,
    'display_name': {'zh-CN': '全球商业', 'en': 'Global commerce', 'ko': '전체 상업'},
  },
};
