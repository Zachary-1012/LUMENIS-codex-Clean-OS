import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/features/cth/cth10/source_brief_view_model.dart';

void main() {
  test(
    'source brief save is permission-scoped and independently reopened',
    () async {
      final client = _SourceBriefClient()
        ..startResponse = _taskResponse(
          taskId: 'TASK-1',
          jobId: 'JOB-1',
          state: 'succeeded',
        );
      final model = SourceBriefViewModel(client: client);
      await model.start();

      await model.saveAsEditableResearch(title: '来源简报');

      expect(model.savedWorkState, SourceBriefSavedWorkState.saved);
      expect(model.savedWorkErrorKind, isNull);
      expect(client.saveCalls, hasLength(1));
      expect(client.saveCalls.single['domainId'], 'CTH');
      expect(client.saveCalls.single['jobId'], 'JOB-1');
      expect(client.saveCalls.single['title'], '来源简报');
      final requestId = client.saveCalls.single['requestId']! as String;
      expect(requestId, matches(RegExp(r'^[A-Za-z0-9_-]{8,128}$')));
      expect(client.reopenArtifactIds, ['ART-0123456789abcdef']);
      expect(model.savedWorkMarkdown, contains('已核验来源'));

      await model.reopenSavedResearch();

      expect(model.savedWorkState, SourceBriefSavedWorkState.reopened);
      expect(client.reopenArtifactIds, [
        'ART-0123456789abcdef',
        'ART-0123456789abcdef',
      ]);
      model.dispose();
    },
  );

  test(
    'denied save remains honest and retries with the same request identity',
    () async {
      final client = _SourceBriefClient()
        ..startResponse = _taskResponse(
          taskId: 'TASK-1',
          jobId: 'JOB-1',
          state: 'succeeded',
        )
        ..saveResponseOverride = {'ok': false, 'code': 'ACCESS_DENIED'};
      final model = SourceBriefViewModel(client: client);
      await model.start();

      await model.saveAsEditableResearch(title: '来源简报');

      expect(model.savedWorkState, SourceBriefSavedWorkState.failed);
      expect(model.savedWorkErrorKind, SourceBriefErrorKind.accessDenied);
      expect(client.reopenArtifactIds, isEmpty);
      final firstRequestId = client.saveCalls.single['requestId'];
      client.saveResponseOverride = null;

      await model.saveAsEditableResearch(title: 'changed title is ignored');

      expect(model.savedWorkState, SourceBriefSavedWorkState.saved);
      expect(client.saveCalls, hasLength(2));
      expect(client.saveCalls.last['requestId'], firstRequestId);
      expect(client.saveCalls.last['title'], '来源简报');
      model.dispose();
    },
  );

  test(
    'changed SavedWork hash is rejected during independent reopen',
    () async {
      final client = _SourceBriefClient()
        ..startResponse = _taskResponse(
          taskId: 'TASK-1',
          jobId: 'JOB-1',
          state: 'succeeded',
        )
        ..reopenShaOverride = List.filled(64, 'f').join();
      final model = SourceBriefViewModel(client: client);
      await model.start();

      await model.saveAsEditableResearch(title: '来源简报');

      expect(model.savedWorkState, SourceBriefSavedWorkState.failed);
      expect(model.savedWorkErrorKind, SourceBriefErrorKind.invalidResponse);
      expect(model.savedWorkMarkdown, isNull);
      model.dispose();
    },
  );

  test(
    'shared adoption requires prepare, explicit apply, and independent reopen',
    () async {
      final client = _SourceBriefClient()
        ..startResponse = _taskResponse(
          taskId: 'TASK-1',
          jobId: 'JOB-1',
          state: 'succeeded',
        )
        ..sharedAdoptionPrepareResponse = _sharedAdoptionPrepareResponse()
        ..sharedAdoptionApplyReplayed = false;
      final model = SourceBriefViewModel(client: client);
      await model.start();

      await model.prepareSharedAdoption();

      expect(
        model.sharedAdoptionState,
        SourceBriefSharedAdoptionState.prepared,
      );
      expect(client.sharedAdoptionCalls, hasLength(1));
      expect(client.sharedAdoptionCalls.single['mode'], 'prepare');
      expect(client.sharedReopenArtifactIds, isEmpty);

      await model.applySharedAdoption();

      expect(
        model.sharedAdoptionState,
        SourceBriefSharedAdoptionState.reopened,
      );
      expect(client.sharedAdoptionCalls, hasLength(2));
      final apply = client.sharedAdoptionCalls.last;
      expect(apply['mode'], 'apply');
      expect(apply['confirm'], isTrue);
      expect(apply['confirmedResource'], 'resource:exact-approval');
      expect(apply['requestId'], client.sharedAdoptionCalls.first['requestId']);
      expect(client.sharedReopenArtifactIds, ['ART-2222222222222222']);
      expect(model.sharedAdoptedWork?.markdown, contains('独立成果'));
      model.dispose();
    },
  );

  test(
    'uncertain shared apply retries the same approval and reopens replay',
    () async {
      final client = _SourceBriefClient()
        ..startResponse = _taskResponse(
          taskId: 'TASK-1',
          jobId: 'JOB-1',
          state: 'succeeded',
        )
        ..sharedAdoptionPrepareResponse = _sharedAdoptionPrepareResponse()
        ..sharedAdoptionApplyFailures.add(
          const LumenisCoreException('response timed out'),
        )
        ..sharedAdoptionApplyReplayed = true;
      final model = SourceBriefViewModel(client: client);
      await model.start();
      await model.prepareSharedAdoption();
      final preview = model.sharedAdoptionPreview!;

      await model.applySharedAdoption();

      expect(model.sharedAdoptionState, SourceBriefSharedAdoptionState.failed);
      expect(model.sharedAdoptionErrorKind, SourceBriefErrorKind.unavailable);
      expect(model.sharedAdoptionPreview?.requestId, preview.requestId);
      expect(client.sharedReopenArtifactIds, isEmpty);

      await model.applySharedAdoption();

      expect(
        model.sharedAdoptionState,
        SourceBriefSharedAdoptionState.reopened,
      );
      expect(client.sharedAdoptionCalls, hasLength(3));
      expect(
        client.sharedAdoptionCalls[1]['requestId'],
        client.sharedAdoptionCalls[2]['requestId'],
      );
      expect(
        client.sharedAdoptionCalls[1]['confirmedResource'],
        client.sharedAdoptionCalls[2]['confirmedResource'],
      );
      expect(client.sharedReopenArtifactIds, ['ART-2222222222222222']);
      model.dispose();
    },
  );

  test('scope change after shared preview prevents apply', () async {
    final client = _SourceBriefClient()
      ..startResponse = _taskResponse(
        taskId: 'TASK-1',
        jobId: 'JOB-1',
        state: 'succeeded',
      )
      ..sharedAdoptionPrepareResponse = _sharedAdoptionPrepareResponse();
    final model = SourceBriefViewModel(client: client);
    await model.start();
    await model.prepareSharedAdoption();
    client.contextResponse = _focusContext();

    await model.applySharedAdoption();

    expect(client.sharedAdoptionCalls.map((call) => call['mode']), ['prepare']);
    expect(model.sharedAdoptionPreview, isNull);
    expect(model.errorKind, SourceBriefErrorKind.contextChanged);
    model.dispose();
  });

  test(
    'offline context read does not leave SourceBrief save pending',
    () async {
      final client = _SourceBriefClient()
        ..startResponse = _taskResponse(
          taskId: 'TASK-1',
          jobId: 'JOB-1',
          state: 'succeeded',
        );
      final model = SourceBriefViewModel(client: client);
      await model.start();
      client.settingsError = const LumenisCoreException('offline');

      await model.saveAsEditableResearch(title: '来源简报');

      expect(model.busy, isFalse);
      expect(model.savedWorkState, SourceBriefSavedWorkState.failed);
      expect(model.savedWorkErrorKind, SourceBriefErrorKind.unavailable);
      expect(client.saveCalls, isEmpty);
      model.dispose();
    },
  );

  test('offline context read reports SavedWork reopen failure', () async {
    final client = _SourceBriefClient()
      ..startResponse = _taskResponse(
        taskId: 'TASK-1',
        jobId: 'JOB-1',
        state: 'succeeded',
      );
    final model = SourceBriefViewModel(client: client);
    await model.start();
    await model.saveAsEditableResearch(title: '来源简报');
    expect(model.savedWorkState, SourceBriefSavedWorkState.saved);
    client.settingsError = const LumenisCoreException('offline');

    await model.reopenSavedResearch();

    expect(model.busy, isFalse);
    expect(model.savedWorkState, SourceBriefSavedWorkState.failed);
    expect(model.savedWorkErrorKind, SourceBriefErrorKind.unavailable);
    expect(client.reopenArtifactIds, ['ART-0123456789abcdef']);
    model.dispose();
  });

  test(
    'saved research history opens and revises through immutable versions',
    () async {
      final first = _historicalResearchWork(
        version: 1,
        artifactId: 'ART-1111111111111111',
        sha256: List.filled(64, '1').join(),
        requestId: 'research-v1',
      );
      final revised = _historicalResearchWork(
        version: 2,
        artifactId: 'ART-2222222222222222',
        sha256: List.filled(64, '2').join(),
        requestId: 'pending-revision-id',
        parentArtifactId: 'ART-1111111111111111',
        parentSha256: List.filled(64, '1').join(),
        title: '修订后的来源简报',
        markdown: '# 修订版\n\n保留原版本并追加新判断。',
      );
      final client = _SourceBriefClient()
        ..startResponse = _taskResponse(
          taskId: 'TASK-1',
          jobId: 'JOB-1',
          state: 'succeeded',
        )
        ..savedResearchHistory = _savedResearchHistory([first])
        ..savedResearchByArtifact = {
          'ART-1111111111111111': {'ok': true, 'result': first},
          'ART-2222222222222222': {'ok': true, 'result': revised},
        }
        ..revisionResponseFactory = (call) => {
          'ok': true,
          'result': _historicalResearchWork(
            version: 2,
            artifactId: 'ART-2222222222222222',
            sha256: List.filled(64, '2').join(),
            requestId: call['requestId']! as String,
            parentArtifactId: 'ART-1111111111111111',
            parentSha256: List.filled(64, '1').join(),
            title: '修订后的来源简报',
            markdown: '# 修订版\n\n保留原版本并追加新判断。',
          ),
        };
      final model = SourceBriefViewModel(client: client);
      await model.start();

      await model.loadSavedResearchHistory();
      expect(model.savedHistoryState, SourceBriefHistoryState.loaded);
      expect(model.savedHistory.single.artifactId, 'ART-1111111111111111');

      final parent = model.savedHistory.single;
      await model.reopenSavedResearchVersion(parent);
      expect(model.openedHistoryWork?.markdown, contains('第一版'));

      await model.reviseSavedResearchVersion(
        parent: parent,
        title: '修订后的来源简报',
        reason: '补充核验结果',
        markdown: '# 修订版\n\n保留原版本并追加新判断。',
      );

      expect(client.revisionCalls, hasLength(1));
      expect(client.revisionCalls.single['artifactId'], parent.artifactId);
      expect(client.revisionCalls.single['expectedSha256'], parent.sha256);
      expect(client.revisionCalls.single['reason'], '补充核验结果');
      expect(
        client.revisionCalls.single['requestId'],
        startsWith('sourcebriefrev_'),
      );
      expect(client.reopenResearchArtifactIds.last, 'ART-2222222222222222');
      expect(model.openedHistoryWork?.version, 2);
      expect(model.openedHistoryWork?.parentArtifactId, parent.artifactId);
      expect(model.openedHistoryWork?.markdown, contains('修订版'));
      expect(model.savedHistory.map((work) => work.version), [2, 1]);
      model.dispose();
    },
  );

  test(
    'uncertain revision reuses request identity and rejects changed draft',
    () async {
      final first = _historicalResearchWork(
        version: 1,
        artifactId: 'ART-1111111111111111',
        sha256: List.filled(64, '1').join(),
        requestId: 'research-v1',
      );
      final revised = _historicalResearchWork(
        version: 2,
        artifactId: 'ART-2222222222222222',
        sha256: List.filled(64, '2').join(),
        requestId: 'pending-revision-id',
        parentArtifactId: 'ART-1111111111111111',
        parentSha256: List.filled(64, '1').join(),
        title: '修订后的来源简报',
        markdown: '# 修订版\n\n保留原版本并追加新判断。',
      );
      final client = _SourceBriefClient()
        ..startResponse = _taskResponse(
          taskId: 'TASK-1',
          jobId: 'JOB-1',
          state: 'succeeded',
        )
        ..savedResearchHistory = _savedResearchHistory([first])
        ..savedResearchByArtifact = {
          'ART-1111111111111111': {'ok': true, 'result': first},
          'ART-2222222222222222': {'ok': true, 'result': revised},
        }
        ..revisionError = const LumenisCoreException('response timed out');
      final model = SourceBriefViewModel(client: client);
      await model.start();
      await model.loadSavedResearchHistory();
      final parent = model.savedHistory.single;
      const exactDraft = '# 修订版\n\n保留原版本并追加新判断。';

      Future<void> revise(String markdown) => model.reviseSavedResearchVersion(
        parent: parent,
        title: '修订后的来源简报',
        reason: '补充核验结果',
        markdown: markdown,
      );

      await revise(exactDraft);
      final requestId = client.revisionCalls.single['requestId'];
      expect(model.savedHistoryErrorKind, SourceBriefErrorKind.unavailable);

      await revise('# 不同草稿\n\n不得覆盖未知结果。');
      expect(client.revisionCalls, hasLength(1));
      expect(model.pendingRevisionDraftFor(parent)?.markdown, exactDraft);

      client
        ..revisionError = null
        ..revisionResponseFactory = (call) => {
          'ok': true,
          'result': _historicalResearchWork(
            version: 2,
            artifactId: 'ART-2222222222222222',
            sha256: List.filled(64, '2').join(),
            requestId: call['requestId']! as String,
            parentArtifactId: 'ART-1111111111111111',
            parentSha256: List.filled(64, '1').join(),
            title: '修订后的来源简报',
            markdown: exactDraft,
          ),
        };
      await revise(exactDraft);

      expect(client.revisionCalls, hasLength(2));
      expect(client.revisionCalls.last['requestId'], requestId);
      expect(client.reopenResearchArtifactIds.last, 'ART-2222222222222222');
      expect(model.openedHistoryWork?.version, 2);
      expect(model.pendingRevisionDraftFor(parent), isNull);
      model.dispose();
    },
  );

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
    'question uses the existing source brief route without external analysis',
    () async {
      final client = _SourceBriefClient();
      final model = SourceBriefViewModel(client: client);

      await model.start(businessQuestion: '  请分析这些来源  ');

      expect(client.startCalls, 1);
      expect(client.startQuestion, '请分析这些来源');
      expect(client.jobCalls, 0);
      expect(model.errorKind, isNull);
      expect(model.taskId, isNotNull);
      expect(model.result, isNull);

      model.dispose();
    },
  );

  for (final question in ['abc', 'a' * 1501, 'abcd\u0001']) {
    test('invalid question is rejected before task submission', () async {
      final client = _SourceBriefClient();
      final model = SourceBriefViewModel(client: client);
      await model.start(businessQuestion: question);
      expect(client.startCalls, 0);
      expect(model.errorKind, SourceBriefErrorKind.invalidResponse);
      model.dispose();
    });
  }

  test(
    'real source-bound research preserves excerpts, questions and unknown numbers',
    () async {
      final client = _SourceBriefClient()
        ..jobResponse = _jobResponse(
          jobId: 'JOB-1',
          researchAnalysis: _researchAnalysis(),
        );
      final model = SourceBriefViewModel(client: client);
      await model.reopenJob('JOB-1');
      expect(model.errorKind, isNull);
      final research = model.result!.researchAnalysis!;
      expect(
        research.findings.single.content,
        'A secondary report mentioned 18% growth.',
      );
      expect(research.findings.single.evidenceRef, 'EVIDENCE-1');
      expect(research.questions.single.status, 'proposed');
      expect(research.numberChecks.single.literals, ['18%']);
      expect(model.result!.analysis, isNull);
      model.dispose();
    },
  );

  final corruptions = <String, void Function(Map<String, dynamic>)>{
    'foreign source': (r) =>
        (r['ranked_findings'] as List).first['source_id'] = 'OTHER',
    'foreign citation': (r) =>
        (r['ranked_findings'] as List).first['evidence_refs'] = ['OTHER'],
    'verified claim': (r) =>
        (r['ranked_findings'] as List).first['fact_verified'] = true,
    'foreign lineage': (r) =>
        (r['evidence_lineage'] as List).first['source'] = 'OTHER',
    'foreign hypothesis': (r) =>
        (r['hypotheses'] as List).first['source_set_sha256'] = 'e' * 64,
    'invented numeric unit': (r) =>
        (r['comparisons'] as List).first['unit'] = 'verified growth',
    'permission promotion': (r) => r['permission_granted'] = true,
    'foreign scope': (r) => (r['scope'] as Map)['scope_key'] = 'e' * 64,
    'question mismatch': (r) => r['goal'] = 'Different question',
  };
  for (final corruption in corruptions.entries) {
    test('withholds research with ${corruption.key}', () async {
      final research = _researchAnalysis();
      corruption.value(research);
      final client = _SourceBriefClient()
        ..jobResponse = _jobResponse(
          jobId: 'JOB-1',
          researchAnalysis: research,
        );
      final model = SourceBriefViewModel(client: client);
      await model.reopenJob('JOB-1');
      expect(model.result, isNull);
      expect(model.errorKind, isNotNull);
      model.dispose();
    });
  }

  test(
    'unavailable original source use exposes no stale research body',
    () async {
      final client = _SourceBriefClient()
        ..jobResponse = _jobResponse(
          jobId: 'JOB-1',
          researchAnalysis: {
            'status': 'source_use_unavailable',
            'ranked_findings': [],
            'fact_verified': false,
            'limitations': ['Original content use could not be verified.'],
          },
        );
      final model = SourceBriefViewModel(client: client);
      await model.reopenJob('JOB-1');
      expect(model.result!.researchAnalysis!.findings, isEmpty);
      expect(model.result!.researchAnalysis!.status, 'source_use_unavailable');
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
  final List<Map<String, Object?>> saveCalls = [];
  final List<String> reopenArtifactIds = [];
  Map<String, dynamic>? saveResponseOverride;
  Map<String, dynamic>? reopenResponseOverride;
  String? reopenShaOverride;
  Map<String, dynamic> savedResearchHistory = _savedResearchHistory(const []);
  Map<String, dynamic> revisionResponseOverride = {'ok': false};
  Map<String, dynamic> Function(Map<String, Object?> call)?
  revisionResponseFactory;
  Object? revisionError;
  Map<String, dynamic> savedResearchByArtifact = {};
  String? startDomain;
  int? startLimit;
  String? startQuestion;
  final List<String> taskIds = [];
  final List<String> resumeIds = [];
  final List<String> jobIds = [];
  final List<Map<String, Object?>> revisionCalls = [];
  final List<String> reopenResearchArtifactIds = [];
  final List<Map<String, Object?>> sharedAdoptionCalls = [];
  final List<String> sharedReopenArtifactIds = [];
  Map<String, dynamic> sharedAdoptionPrepareResponse = {
    'ok': false,
    'code': 'NOT_CONFIGURED',
  };
  bool sharedAdoptionApplyReplayed = false;
  final List<Object> sharedAdoptionApplyFailures = [];
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
        _savedWorkResponse(requestId: requestId, title: title);
  }

  @override
  Future<Map<String, dynamic>> reopenSourceBriefSavedWork({
    required String domainId,
    required String artifactId,
  }) async {
    reopenArtifactIds.add(artifactId);
    return reopenResponseOverride ??
        _savedWorkResponse(
          requestId: saveCalls.last['requestId']! as String,
          title: saveCalls.last['title']! as String,
          sha256: reopenShaOverride,
        );
  }

  @override
  Future<Map<String, dynamic>> listBrowserResearchNotes({
    required String? domainId,
    int limit = 100,
    String? cursor,
  }) async => savedResearchHistory;

  @override
  Future<Map<String, dynamic>> reopenBrowserResearchNote({
    required String? domainId,
    required String artifactId,
  }) async {
    reopenResearchArtifactIds.add(artifactId);
    return savedResearchByArtifact[artifactId] as Map<String, dynamic>? ??
        {'ok': false, 'code': 'NOT_FOUND'};
  }

  @override
  Future<Map<String, dynamic>> reviseBrowserResearchNote({
    required String? domainId,
    required String artifactId,
    required String requestId,
    required String expectedSha256,
    required String reason,
    required String expectedTitle,
    required String title,
    required String expectedMarkdown,
    required String markdown,
  }) async {
    revisionCalls.add({
      'domainId': domainId,
      'artifactId': artifactId,
      'requestId': requestId,
      'expectedSha256': expectedSha256,
      'reason': reason,
      'expectedTitle': expectedTitle,
      'title': title,
      'expectedMarkdown': expectedMarkdown,
      'markdown': markdown,
    });
    final error = revisionError;
    if (error != null) throw error;
    final response =
        revisionResponseFactory?.call(revisionCalls.last) ??
        revisionResponseOverride;
    final result = response['result'];
    final artifact = result is Map<String, dynamic>
        ? result['artifact'] as Map<String, dynamic>?
        : null;
    final returnedArtifactId = artifact?['artifact_id'];
    if (response['ok'] == true && returnedArtifactId is String) {
      savedResearchByArtifact[returnedArtifactId] = response;
    }
    return response;
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
    if (sharedAdoptionApplyFailures.isNotEmpty) {
      throw sharedAdoptionApplyFailures.removeAt(0);
    }
    return _sharedAdoptionWorkResponse(
      requestId: requestId,
      replayed: sharedAdoptionApplyReplayed,
    );
  }

  @override
  Future<Map<String, dynamic>> reopenSharedSavedWork(String artifactId) async {
    sharedReopenArtifactIds.add(artifactId);
    return _sharedAdoptionWorkResponse(
      requestId: sharedAdoptionCalls.last['requestId']! as String,
      replayed: null,
    );
  }
}

Map<String, dynamic> _sharedAdoptionBinding() => {
  'schema': 'domain-report-adoption/v1',
  'job_id': 'JOB-1',
  'actor_id': 'principal:local-test',
  'source_scope': {
    'domain_id': 'cth',
    'subject_id': null,
    'brand_focus_id': null,
    'global_scope': true,
  },
  'target_scope': {'scope_kind': 'shared_workspace', 'version': 1},
  'report_hash': List.filled(64, 'a').join(),
  'source_count': 1,
  'sources_sha256': List.filled(64, 'c').join(),
  'authority': 'SOURCE_REFERENCE_ONLY',
  'semantic_verification': 'NOT_PERFORMED',
};

Map<String, dynamic> _sharedAdoptionPrepareResponse() => {
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

Map<String, dynamic> _sharedAdoptionWorkResponse({
  required String requestId,
  required bool? replayed,
}) => {
  'ok': true,
  'result': {
    'artifact': {
      'artifact_id': 'ART-2222222222222222',
      'sha256': List.filled(64, 'e').join(),
    },
    'document': {
      'kind': 'report',
      'title': 'CTH 来源简报',
      'markdown': '# 独立成果\n\n保留原简报与来源绑定。',
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

Map<String, dynamic> _savedResearchHistory(List<Map<String, dynamic>> items) =>
    {
      'ok': true,
      'result': {
        'items': items,
        'has_more': false,
        'next_cursor': null,
        'verification_complete': true,
        'unverified_candidates': 0,
      },
    };

Map<String, dynamic> _historicalResearchWork({
  required int version,
  required String artifactId,
  required String sha256,
  required String requestId,
  String title = '来源简报',
  String markdown = '# 第一版\n\n来源分析结果。',
  String? parentArtifactId,
  String? parentSha256,
}) => {
  'artifact': {'artifact_id': artifactId, 'sha256': sha256},
  'document': {
    'kind': 'research',
    'title': title,
    'markdown': markdown,
    'request_id': requestId,
    'version': version,
    'parent_artifact_id': ?parentArtifactId,
    'parent_sha256': ?parentSha256,
    'payload': {
      'source_brief_reference': {
        'job_id': 'JOB-1',
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
    'artifact_id': artifactId,
    'work_id': 'WORK-0123456789abcdef01234567',
    'version': version,
    'scope': {
      'domain_id': 'cth',
      'subject_id': null,
      'brand_focus_id': null,
      'global_scope': true,
    },
  },
};

Map<String, dynamic> _savedWorkResponse({
  required String requestId,
  required String title,
  String? sha256,
}) => {
  'ok': true,
  'result': {
    'artifact': {
      'artifact_id': 'ART-0123456789abcdef',
      'sha256': sha256 ?? List.filled(64, 'd').join(),
    },
    'document': {
      'kind': 'research',
      'title': title,
      'markdown': '# 来源简报\n\n已核验来源与范围。',
      'request_id': requestId,
      'payload': {
        'source_brief_reference': {
          'job_id': 'JOB-1',
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
  Map<String, dynamic>? researchAnalysis,
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
    'business_question': businessAnalysis == null && researchAnalysis == null
        ? null
        : '检查本周运营变化',
    'research_analysis': ?researchAnalysis,
    'review_status': 'HUMAN_PENDING',
  },
};

Map<String, dynamic> _researchAnalysis() => {
  'schema': 'source_bound_research.v1',
  'status': 'research_draft',
  'scope': _globalScope(),
  'goal': '检查本周运营变化',
  'summary': 'Source excerpts and questions for further verification.',
  'source_set_sha256': 'd' * 64,
  'permission_granted': false,
  'canonical_promotion': false,
  'ranked_findings': [
    {
      'finding_id': 'finding_1',
      'source_id': 'SRC-1',
      'lineage_id': 'lineage_1',
      'content': 'A secondary report mentioned 18% growth.',
      'title': '可核验来源',
      'evidence_refs': ['EVIDENCE-1'],
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
      'source': 'SRC-1',
      'evidence_id': 'EVIDENCE-1',
      'provenance': {'fact_verified': false},
    },
  ],
  'hypotheses': [
    {
      'statement': 'Does the full report support the question?',
      'status': 'proposed',
      'finding_ids': ['finding_1'],
      'evidence_refs': ['EVIDENCE-1'],
      'claim_type': 'hypothesis',
      'confidence': null,
      'source_set_sha256': 'd' * 64,
      'validation_needed': ['Check time, scope and independent evidence.'],
    },
  ],
  'comparisons': [
    {
      'source_id': 'SRC-1',
      'evidence_refs': ['EVIDENCE-1'],
      'numeric_literals': ['18%'],
      'comparison_status': 'NOT_COMPARABLE_WITHOUT_MEASURE_DEFINITIONS',
      'unit': null,
      'currency': null,
      'period': null,
      'denominator': null,
    },
  ],
  'limitations': ['Source statements are not verified effects.'],
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
