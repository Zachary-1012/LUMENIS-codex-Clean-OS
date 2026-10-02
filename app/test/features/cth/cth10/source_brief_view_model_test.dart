import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/features/cth/cth10/source_brief_view_model.dart';

void main() {
  test('failed task revalidation hides prior result and can recover', () async {
    for (final denied in [true, false]) {
      final completed = _taskResponse(
        taskId: 'TASK-1',
        jobId: 'JOB-1',
        state: 'succeeded',
      );
      final client = _SourceBriefClient()..startResponse = completed;
      final model = SourceBriefViewModel(client: client);
      await model.start();
      expect(model.result, isNotNull);

      if (denied) {
        client.taskError = const LumenisCoreException(
          'denied',
          statusCode: 403,
        );
      } else {
        client.startResponse = {'ok': true, 'task': null};
      }
      await model.refreshTask();
      expect(
        model.errorKind,
        denied
            ? SourceBriefErrorKind.accessDenied
            : SourceBriefErrorKind.invalidResponse,
      );
      expect(
        model.result,
        isNull,
        reason: 'A failed fresh read is not verified output.',
      );
      expect(model.taskId, 'TASK-1');
      expect(model.canResume, isFalse);

      client
        ..taskError = null
        ..startResponse = completed;
      await model.refreshTask();
      expect(model.result?.jobId, 'JOB-1');
      expect(client.jobCalls, 2);
      model.dispose();
    }
  });

  test(
    '202 admission remains pending and retains recovery identifiers',
    () async {
      final client = _SourceBriefClient()
        ..startResponse = _taskResponse(
          taskId: 'TASK-1',
          jobId: 'JOB-1',
          state: 'pending',
          canResume: true,
        );
      final model = SourceBriefViewModel(client: client);

      await model.start();

      expect(client.startCalls, 1);
      expect(client.startDomain, 'CTH');
      expect(client.startLimit, 30);
      expect(client.startQuestion, isNull);
      expect(model.phase, SourceBriefPhase.ready);
      expect(model.busy, isFalse);
      expect(model.taskId, 'TASK-1');
      expect(model.jobId, 'JOB-1');
      expect(model.taskState, SourceBriefTaskState.pending);
      expect(model.canResume, isTrue);
      expect(model.result, isNull);
      expect(client.jobCalls, 0);

      model.dispose();
    },
  );

  test(
    'success requires verified job readback and exposes typed draft fields',
    () async {
      final client = _SourceBriefClient()
        ..startResponse = _taskResponse(
          taskId: 'TASK-2',
          jobId: 'JOB-2',
          state: 'succeeded',
        )
        ..jobResponse = _jobResponse(
          jobId: 'JOB-2',
          businessAnalysis: _draftAnalysis(),
        );
      final model = SourceBriefViewModel(client: client);

      await model.start();

      expect(client.jobCalls, 1);
      expect(client.jobIds, ['JOB-2']);
      expect(model.phase, SourceBriefPhase.ready);
      expect(model.taskState, SourceBriefTaskState.succeeded);
      expect(model.canResume, isFalse);
      expect(model.result, isNotNull);
      expect(model.result!.jobId, 'JOB-2');
      expect(model.result!.reportId, 'JOB-2');
      expect(model.result!.sourceCount, 1);
      expect(model.result!.records.single.evidenceRef, 'EVIDENCE-1');
      expect(
        model.result!.businessAnalysisState,
        SourceBriefBusinessAnalysisState.draft,
      );
      expect(model.result!.businessQuestion, '检查本周运营变化');
      expect(
        model.result!.analysis!.sourceObservations.single.excerpt,
        '来源中的原始摘录。',
      );
      expect(model.result!.analysis!.interpretations.single.text, '待验证的解释。');
      expect(
        model.result!.analysis!.proposedActions.single.pilot!.stopIf,
        '反馈不支持时停止。',
      );
      expect(model.result!.analysis!.unknowns, ['缺少独立验证。']);

      model.dispose();
    },
  );

  test(
    'scope mismatch in the persisted job is not surfaced as a result',
    () async {
      final client = _SourceBriefClient()
        ..startResponse = _taskResponse(
          taskId: 'TASK-3',
          jobId: 'JOB-3',
          state: 'succeeded',
        )
        ..jobResponse = _jobResponse(jobId: 'JOB-3', scope: _focusScope());
      final model = SourceBriefViewModel(client: client);

      await model.start();

      expect(model.phase, SourceBriefPhase.failed);
      expect(model.errorKind, SourceBriefErrorKind.contextChanged);
      expect(model.taskId, 'TASK-3');
      expect(model.jobId, 'JOB-3');
      expect(model.result, isNull);

      model.dispose();
    },
  );

  test(
    'an unsupported business-analysis route is not called or implied',
    () async {
      final client = _SourceBriefClient();
      final model = SourceBriefViewModel(client: client);

      await model.start(businessQuestion: '请分析这些来源');

      expect(client.startCalls, 0);
      expect(client.jobCalls, 0);
      expect(model.phase, SourceBriefPhase.failed);
      expect(model.errorKind, SourceBriefErrorKind.analysisUnavailable);
      expect(model.taskId, isNull);
      expect(model.result, isNull);

      model.dispose();
    },
  );

  test(
    '403 remains denied and does not leave a resume action enabled',
    () async {
      final client = _SourceBriefClient()
        ..startResponse = _taskResponse(
          taskId: 'TASK-4',
          jobId: 'JOB-4',
          state: 'pending',
          canResume: true,
        );
      final model = SourceBriefViewModel(client: client);
      await model.start();
      client.taskError = const LumenisCoreException(
        'private transport detail',
        statusCode: 403,
      );

      await model.refreshTask();

      expect(client.taskIds, ['TASK-4']);
      expect(model.phase, SourceBriefPhase.failed);
      expect(model.errorKind, SourceBriefErrorKind.accessDenied);
      expect(model.taskId, 'TASK-4');
      expect(model.canResume, isFalse);
      expect(model.result, isNull);

      model.dispose();
    },
  );

  test('unknown task state cannot become success', () async {
    final client = _SourceBriefClient()
      ..startResponse = _taskResponse(
        taskId: 'TASK-5',
        jobId: 'JOB-5',
        state: 'completed-ish',
        canResume: true,
      );
    final model = SourceBriefViewModel(client: client);

    await model.start();

    expect(model.phase, SourceBriefPhase.failed);
    expect(model.errorKind, SourceBriefErrorKind.invalidResponse);
    expect(model.taskState, SourceBriefTaskState.unknown);
    expect(model.result, isNull);
    expect(client.jobCalls, 0);

    model.dispose();
  });

  test('resume reuses the interrupted task id', () async {
    final client = _SourceBriefClient()
      ..startResponse = _taskResponse(
        taskId: 'TASK-6',
        jobId: 'JOB-6',
        state: 'interrupted',
        canResume: true,
      )
      ..resumeResponse = _taskResponse(
        taskId: 'TASK-6',
        jobId: 'JOB-6',
        state: 'running',
      );
    final model = SourceBriefViewModel(client: client);
    await model.start();

    await model.resume();

    expect(client.resumeIds, ['TASK-6']);
    expect(client.startCalls, 1);
    expect(model.taskId, 'TASK-6');
    expect(model.jobId, 'JOB-6');
    expect(model.taskState, SourceBriefTaskState.running);
    expect(model.canResume, isFalse);
    expect(model.result, isNull);

    model.dispose();
  });

  test(
    'fresh scope change clears the old task before status is read',
    () async {
      final client = _SourceBriefClient()
        ..startResponse = _taskResponse(
          taskId: 'TASK-7',
          jobId: 'JOB-7',
          state: 'pending',
          canResume: true,
        );
      final model = SourceBriefViewModel(client: client);
      await model.start();
      client.contextResponse = _focusContext();

      await model.refreshTask();

      expect(client.taskCalls, 0);
      expect(model.errorKind, SourceBriefErrorKind.contextChanged);
      expect(model.taskId, isNull);
      expect(model.jobId, isNull);
      expect(model.globalScope, isFalse);
      expect(model.scopeLabel, '焦点主体');

      model.dispose();
    },
  );

  test(
    'syncContext clears stale identifiers immediately on shell scope change',
    () async {
      final client = _SourceBriefClient()
        ..startResponse = _taskResponse(
          taskId: 'TASK-8',
          jobId: 'JOB-8',
          state: 'pending',
          canResume: true,
        );
      final model = SourceBriefViewModel(client: client);
      await model.start();
      client.setShellContext(_focusContext());

      model.syncContext();

      expect(model.errorKind, SourceBriefErrorKind.contextChanged);
      expect(model.taskId, isNull);
      expect(model.jobId, isNull);
      expect(model.canResume, isFalse);
      expect(model.globalScope, isFalse);
      expect(model.scopeLabel, '焦点主体');

      model.dispose();
    },
  );

  test('an in-flight response after shell change is discarded', () async {
    final client = _SourceBriefClient()
      ..startResponse = _taskResponse(
        taskId: 'TASK-9',
        jobId: 'JOB-9',
        state: 'pending',
        canResume: true,
      );
    final model = SourceBriefViewModel(client: client);
    await model.start();
    client.taskGate = Completer<Map<String, dynamic>>();
    client.taskEntered = Completer<void>();

    final refresh = model.refreshTask();
    await client.taskEntered!.future;
    client.setShellContext(_focusContext());
    client.taskGate!.complete(
      _taskResponse(
        taskId: 'TASK-9',
        jobId: 'JOB-9',
        state: 'pending',
        canResume: true,
      ),
    );
    await refresh;

    expect(model.errorKind, SourceBriefErrorKind.contextChanged);
    expect(model.taskId, isNull);
    expect(model.jobId, isNull);
    expect(model.result, isNull);

    model.dispose();
  });

  test(
    'offline context read hides result but preserves recovery references',
    () async {
      final client = _SourceBriefClient()
        ..startResponse = _taskResponse(
          taskId: 'TASK-10',
          jobId: 'JOB-10',
          state: 'succeeded',
        )
        ..jobResponse = _jobResponse(jobId: 'JOB-10');
      final model = SourceBriefViewModel(client: client);
      await model.start();
      expect(model.result, isNotNull);
      client.settingsError = const LumenisCoreException('offline');

      await model.reopenJob('JOB-10');

      expect(model.errorKind, SourceBriefErrorKind.unavailable);
      expect(model.taskId, 'TASK-10');
      expect(model.jobId, 'JOB-10');
      expect(model.result, isNull);
      expect(model.scopeLabel, isNull);

      client
        ..settingsError = null
        ..contextResponse = _focusContext();
      await model.reopenJob('JOB-10');

      expect(model.errorKind, SourceBriefErrorKind.contextChanged);
      expect(model.taskId, isNull);
      expect(client.jobCalls, 1);

      model.dispose();
    },
  );

  test('an older failed request cannot overwrite a newer result', () async {
    final client = _SourceBriefClient()
      ..startResponse = _taskResponse(
        taskId: 'TASK-OLD',
        jobId: 'JOB-OLD',
        state: 'pending',
        canResume: true,
      );
    final model = SourceBriefViewModel(client: client);
    await model.start();
    final staleTaskGate = Completer<Map<String, dynamic>>();
    client.taskGate = staleTaskGate;
    client.taskEntered = Completer<void>();
    final staleRefresh = model.refreshTask();
    await client.taskEntered!.future;

    model.clear();
    client
      ..taskGate = null
      ..startResponse = _taskResponse(
        taskId: 'TASK-NEW',
        jobId: 'JOB-NEW',
        state: 'succeeded',
      )
      ..jobResponse = _jobResponse(jobId: 'JOB-NEW');
    await model.start();
    staleTaskGate.completeError(
      const LumenisCoreException('private stale error', statusCode: 403),
    );
    await staleRefresh;

    expect(model.phase, SourceBriefPhase.ready);
    expect(model.errorKind, isNull);
    expect(model.taskId, 'TASK-NEW');
    expect(model.jobId, 'JOB-NEW');
    expect(model.result!.jobId, 'JOB-NEW');
    expect(model.canResume, isFalse);

    model.dispose();
  });

  test(
    'disposed view model ignores later calls and in-flight failures',
    () async {
      final client = _SourceBriefClient()
        ..startGate = Completer<Map<String, dynamic>>()
        ..startEntered = Completer<void>();
      final model = SourceBriefViewModel(client: client);
      final pendingStart = model.start();
      await client.startEntered!.future;
      model.dispose();
      client.startGate!.completeError(StateError('private failure'));
      await pendingStart;
      final settingsCallsAtDispose = client.settingsCalls;

      await model.initialize();

      expect(client.settingsCalls, settingsCallsAtDispose);
      expect(model.taskId, isNull);
      expect(model.result, isNull);
    },
  );
}

class _SourceBriefClient extends LumenisCoreClient {
  _SourceBriefClient() : super(baseUrl: 'http://127.0.0.1:8201');

  Map<String, dynamic> contextResponse = _globalContext();
  Object? settingsError;
  Map<String, dynamic> startResponse = _taskResponse(
    taskId: 'TASK-1',
    jobId: 'JOB-1',
    state: 'pending',
    canResume: true,
  );
  Map<String, dynamic> resumeResponse = _taskResponse(
    taskId: 'TASK-1',
    jobId: 'JOB-1',
    state: 'running',
  );
  Map<String, dynamic> jobResponse = _jobResponse(jobId: 'JOB-1');
  Object? taskError;
  Completer<Map<String, dynamic>>? startGate;
  Completer<void>? startEntered;
  Completer<Map<String, dynamic>>? taskGate;
  Completer<void>? taskEntered;
  int settingsCalls = 0;
  int startCalls = 0;
  int taskCalls = 0;
  int resumeCalls = 0;
  int jobCalls = 0;
  String? startDomain;
  int? startLimit;
  String? startQuestion;
  final List<String> taskIds = [];
  final List<String> resumeIds = [];
  final List<String> jobIds = [];
  Map<String, dynamic>? _currentEnvelope;

  @override
  Map<String, dynamic>? get currentContextEnvelope => _currentEnvelope;

  void setShellContext(Map<String, dynamic> value) {
    _currentEnvelope = value;
  }

  @override
  Future<Map<String, dynamic>> settingsContext() async {
    settingsCalls += 1;
    final error = settingsError;
    if (error != null) throw error;
    _currentEnvelope = contextResponse;
    return contextResponse;
  }

  @override
  Future<Map<String, dynamic>> startSourceBriefTask({
    required String domainId,
    int limit = 30,
    String? businessQuestion,
  }) async {
    startCalls += 1;
    startDomain = domainId;
    startLimit = limit;
    startQuestion = businessQuestion;
    final entered = startEntered;
    if (entered != null && !entered.isCompleted) entered.complete();
    final gate = startGate;
    return gate == null ? startResponse : await gate.future;
  }

  @override
  Future<Map<String, dynamic>> sourceBriefTask({
    required String domainId,
    required String taskId,
  }) async {
    taskCalls += 1;
    taskIds.add(taskId);
    final error = taskError;
    if (error != null) throw error;
    final entered = taskEntered;
    if (entered != null && !entered.isCompleted) entered.complete();
    final gate = taskGate;
    return gate == null ? startResponse : await gate.future;
  }

  @override
  Future<Map<String, dynamic>> resumeSourceBriefTask({
    required String domainId,
    required String taskId,
  }) async {
    resumeCalls += 1;
    resumeIds.add(taskId);
    return resumeResponse;
  }

  @override
  Future<Map<String, dynamic>> sourceBriefJob({
    required String domainId,
    required String jobId,
  }) async {
    jobCalls += 1;
    jobIds.add(jobId);
    return jobResponse;
  }
}

Map<String, dynamic> _taskResponse({
  required String taskId,
  required String jobId,
  required String state,
  bool canResume = false,
}) => {
  'ok': true,
  'task': {
    'task_id': taskId,
    'job_id': jobId,
    'state': state,
    'can_resume': canResume,
    'error': null,
    'result': null,
  },
  'publish_status': 'not_performed',
};

Map<String, dynamic> _jobResponse({
  required String jobId,
  Map<String, dynamic>? scope,
  Map<String, dynamic>? businessAnalysis,
}) => {
  'ok': true,
  'result': {
    'job_id': jobId,
    'job_state': 'completed',
    'artifact_outcome': {
      'state': 'persisted_and_reopened_verified',
      'report_id': jobId,
      'artifact_hash': List.filled(64, 'a').join(),
      'source_count': 1,
    },
    'source_brief': {
      'scope': scope ?? _globalScope(),
      'records': [_sourceRecord()],
    },
    'business_analysis': businessAnalysis ?? {'state': 'not_requested'},
    'business_question': businessAnalysis == null ? null : '检查本周运营变化',
    'review_status': 'HUMAN_PENDING',
  },
};

Map<String, dynamic> _draftAnalysis() => {
  'state': 'draft',
  'provider': 'must-not-be-exposed',
  'model': 'must-not-be-exposed',
  'analysis': {
    'source_observations': [
      {'source_id': 'SRC-1', 'excerpt': '来源中的原始摘录。'},
    ],
    'interpretations': [
      {
        'text': '待验证的解释。',
        'source_ids': ['SRC-1'],
      },
    ],
    'proposed_actions': [
      {
        'action': '提出可逆的小规模尝试。',
        'reason': '依据已有来源。',
        'check': '记录真实反馈。',
        'source_ids': ['SRC-1'],
        'pilot': {
          'audience': '受邀参与者',
          'procedure': '比较两种内容',
          'measure': '记录可见反馈',
          'continue_if': '反馈支持假设',
          'stop_if': '反馈不支持时停止。',
        },
      },
    ],
    'unknowns': ['缺少独立验证。'],
  },
};

Map<String, dynamic> _sourceRecord({
  String subjectId = '',
  String brandFocusId = '',
}) => {
  'source_id': 'SRC-1',
  'title': '可核验来源',
  'source_url': 'https://example.com/source',
  'publish_datetime': '2026-10-01T09:00:00Z',
  'captured_at': '2026-10-02T00:00:00Z',
  'subject_id': subjectId.isEmpty ? null : subjectId,
  'brand_focus_id': brandFocusId.isEmpty ? null : brandFocusId,
  'scope_evidence_ref': 'EVIDENCE-1',
  'evidence_id': 'EVIDENCE-1',
};

Map<String, dynamic> _globalScope() => {
  'product_id': 'CTH',
  'domain_id': 'cth',
  'global': true,
  'subject_id': null,
  'brand_focus_id': null,
  'entity_label': 'GLOBAL / ALL',
  'scope_key': List.filled(64, 'b').join(),
};

Map<String, dynamic> _focusScope() => {
  'product_id': 'CTH',
  'domain_id': 'cth',
  'global': false,
  'subject_id': 'SUBJECT-1',
  'brand_focus_id': null,
  'entity_label': '焦点主体',
  'scope_key': List.filled(64, 'c').join(),
};

Map<String, dynamic> _globalContext() => {
  'ok': true,
  'contract': 'lumenis.context.v1',
  'selection_only': true,
  'context': {
    'mode': 'GLOBAL_ALL',
    'domain_id': null,
    'subject_id': null,
    'brand_focus_id': null,
    'display_name': {'zh-CN': '全局范围'},
  },
};

Map<String, dynamic> _focusContext() => {
  'ok': true,
  'contract': 'lumenis.context.v1',
  'selection_only': true,
  'context': {
    'mode': 'FOCUS',
    'domain_id': 'CTH',
    'subject_id': 'SUBJECT-1',
    'brand_focus_id': null,
    'display_name': {'zh-CN': '焦点主体'},
  },
};
