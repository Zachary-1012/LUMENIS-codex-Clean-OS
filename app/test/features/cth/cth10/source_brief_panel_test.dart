import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
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
    expect(find.text('可核验来源标题'), findsOneWidget);

    await tester.tap(
      find.byKey(const ValueKey('generated-result-reveal/skip')),
    );
    await tester.pumpAndSettle();

    _expectSkipUnavailable(tester);
    expect(find.text('已保存并重新核验'), findsOneWidget);
  });

  testWidgets('saved result effect can be disabled by the user', (
    tester,
  ) async {
    final client = _SourceBriefClient()
      ..startResponse = _taskEnvelope(state: 'succeeded', canResume: false)
      ..jobResponse = _savedJobEnvelope();

    await tester.pumpWidget(_panelApp(client));
    await tester.pumpAndSettle();
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

    await tester.tap(find.text('刷新状态'));
    await tester.pumpAndSettle();
    expect(find.text('当前范围无法打开或整理这份简报。'), findsOneWidget);
    expect(find.text('暂时无法确认任务状态'), findsOneWidget);
    expect(find.text('整理结束，正在核对已保存简报'), findsNothing);
    expect(find.text('已保存并重新核验'), findsNothing);
    expect(find.text('来源记录'), findsNothing);
    expect(find.text(_taskId), findsOneWidget);

    client.taskResponse = _taskEnvelope(state: 'succeeded', canResume: false);
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
    await tester.tap(find.text('继续这次整理'));
    await tester.pumpAndSettle();

    expect(client.startCalls, hasLength(1));
    expect(client.resumeCalls, [
      {'domainId': 'CTH', 'taskId': _taskId},
    ]);
    expect(client.jobReads, isEmpty);
    expect(find.text('已受理，等待整理'), findsOneWidget);
    expect(find.text(_taskId), findsOneWidget);
    expect(find.text('已保存并重新核验'), findsNothing);
  });

  testWidgets('brief reference opens the actual saved job', (tester) async {
    final client = _SourceBriefClient()..jobResponse = _savedJobEnvelope();

    await tester.pumpWidget(_panelApp(client));
    await tester.pumpAndSettle();
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
    expect(find.text('可核验来源标题'), findsOneWidget);
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
}) => _app(
  locale: locale,
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

Future<void> _tapCreate(WidgetTester tester) async {
  final create = find.byKey(const ValueKey('source-brief/create'));
  await tester.ensureVisible(create);
  await tester.tap(create);
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
  home: Scaffold(body: child),
);

class _SourceBriefClient extends LumenisCoreClient {
  final Map<String, dynamic> contextResponse = _globalContext;
  final List<Map<String, Object?>> startCalls = [];
  final List<String> taskReads = [];
  final List<Map<String, String>> resumeCalls = [];
  final List<String> jobReads = [];

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
}

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
