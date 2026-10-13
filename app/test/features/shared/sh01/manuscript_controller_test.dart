import 'dart:async';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/features/shared/sh01/manuscript_controller.dart';

const _docxMediaType =
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
const _scope = InternalPitchScope(
  domainId: 'cth',
  subjectId: 'subject-a',
  brandFocusId: null,
  globalScope: false,
);
const _otherScope = InternalPitchScope(
  domainId: 'cth',
  subjectId: 'subject-b',
  brandFocusId: null,
  globalScope: false,
);
const _bmpScope = InternalPitchScope(
  domainId: 'bmp',
  subjectId: 'brand-subject',
  brandFocusId: null,
  globalScope: false,
);
const _sharedScope = SharedWorkspaceScope();

void main() {
  late _PitchClient client;
  late ManuscriptController controller;

  setUp(() {
    client = _PitchClient();
    controller = ManuscriptController(
      client: client,
      scope: _scope,
      draft: _manuscript('First draft'),
    );
  });

  tearDown(() => controller.dispose());

  test('saves a normal revision against the verified parent version', () async {
    await controller.save();
    final first = controller.savedWork!;
    expect(first.version, 1);
    expect(first.parentVersion, 1);
    expect(first.previousArtifactId, isNull);
    expect(first.manuscript.title, 'First draft');

    final edited = _manuscript('Revised draft');
    controller.updateDraft(edited);
    expect(controller.canSave, isTrue);
    await controller.save();

    final second = controller.savedWork!;
    expect(client.prepareCalls, hasLength(2));
    expect(client.prepareCalls[1].revision?.workId, first.workId);
    expect(
      client.prepareCalls[1].revision?.previousArtifactId,
      first.artifactId,
    );
    expect(
      client.prepareCalls[1].revision?.expectedDraftDigest,
      first.draftDigest,
    );
    expect(second.version, first.version + 1);
    expect(second.previousArtifactId, first.artifactId);
    expect(second.parentSha256, first.artifactSha256);
    expect(second.manuscript.title, 'Revised draft');
    expect(controller.draft.title, 'Revised draft');
    expect(controller.canSave, isFalse);
  });

  test(
    'Shared workspace proposal can save, list, reopen, revise and export',
    () async {
      final sharedController = ManuscriptController(
        client: client,
        scope: _sharedScope,
        draft: _manuscript('Independent Shared proposal'),
      );
      addTearDown(sharedController.dispose);

      await sharedController.save();
      final first = sharedController.savedWork!;
      final firstRow = client.savedRow(first.artifactId);
      sharedController.updateDraft(_manuscript('Independent Shared revision'));
      await sharedController.save();
      final second = sharedController.savedWork!;

      expect(client.prepareCalls.map((call) => call.scope.toJson()), [
        _sharedScope.toJson(),
        _sharedScope.toJson(),
      ]);
      expect(client.prepareCalls[1].revision?.workId, first.workId);
      expect(
        client.prepareCalls[1].revision?.previousArtifactId,
        first.artifactId,
      );

      client.listReplies.add({
        'items': [client.savedRow(second.artifactId)],
        'has_more': false,
        'next_cursor': null,
      });
      await sharedController.list();
      expect(sharedController.items.single.artifactId, second.artifactId);
      expect(client.sharedListScopes.single.toJson(), _sharedScope.toJson());

      await sharedController.reopen(second.artifactId);
      expect(sharedController.savedWork?.artifactId, second.artifactId);
      expect(client.sharedReopenScopes.single.toJson(), _sharedScope.toJson());

      sharedController.updateDraft(_manuscript('Second Shared revision'));
      await sharedController.save();
      expect(
        client.prepareCalls.last.revision?.previousArtifactId,
        second.artifactId,
      );
      final file = await sharedController.export();
      expect(file?.mediaType, _docxMediaType);
      expect(client.lastExportScope?.toJson(), _sharedScope.toJson());
      expect(firstRow['document']['context'], {
        ..._sharedScope.toJson(),
        'actor_id': 'actor-test',
      });
    },
  );

  test(
    'accepts the existing BMP to ZBMP SavedWork context normalization',
    () async {
      controller.updateScope(_bmpScope);
      client.normalizeBmpReadback = true;

      await controller.save();

      expect(client.prepareCalls.single.scope.toJson(), _bmpScope.toJson());
      expect(controller.savedWork, isNotNull);
      expect(controller.savedWork!.version, 1);
      expect(controller.errorCode, isNull);
    },
  );

  test(
    'lost prepare acknowledgement retries the immutable request once',
    () async {
      client.loseFirstPrepareAcknowledgement = true;

      await controller.save();
      expect(controller.prepareAcknowledgementLost, isTrue);
      expect(controller.taskId, isNull);
      expect(client.runCalls, 0);
      final firstRequestId = client.prepareCalls.single.requestId;
      final firstInput = client.prepareCalls.single.manuscript.toJson();

      await controller.retryPrepare();

      expect(client.prepareCalls, hasLength(2));
      expect(client.prepareCalls[1].requestId, firstRequestId);
      expect(client.prepareCalls[1].manuscript.toJson(), firstInput);
      expect(client.prepareCalls[1].scope.toJson(), _scope.toJson());
      expect(client.runCalls, 1);
      expect(controller.prepareAcknowledgementLost, isFalse);
      expect(controller.savedWork?.version, 1);
    },
  );

  test(
    'lost run acknowledgement reads first and only explicit retry writes',
    () async {
      client.loseFirstRunAcknowledgement = true;
      client.commitFirstLostRun = false;

      await controller.save();

      expect(client.runCalls, 1);
      expect(client.readCalls, 1);
      expect(controller.taskState, 'prepared');
      expect(controller.savedWork, isNull);
      expect(controller.runRetryAvailable, isTrue);

      await controller.retryRun();

      expect(client.runCalls, 2);
      expect(client.readCalls, 2);
      expect(controller.taskState, 'succeeded');
      expect(controller.savedWork?.version, 1);
      expect(controller.runRetryAvailable, isFalse);
    },
  );

  test(
    'an unresolved task blocks a different draft from starting another save',
    () async {
      client.commitOnRun = false;
      client.runStateOverride = 'running';

      await controller.save();
      expect(controller.taskState, 'running');
      expect(controller.savedWork, isNull);
      expect(controller.hasUnresolvedSave, isTrue);
      expect(controller.canSave, isFalse);
      expect(
        controller.startNewDraft(_manuscript('Independent local draft')),
        isFalse,
      );
      expect(controller.draft.title, 'First draft');

      controller.updateDraft(_manuscript('A different draft'));
      expect(controller.canSave, isFalse);
      await controller.save();

      expect(client.prepareCalls, hasLength(1));
      expect(client.runCalls, 1);
      expect(controller.taskId, isNotNull);
    },
  );

  test(
    'succeeded without a valid commit remains unresolved until readback',
    () async {
      client.omitFirstCommittedReadback = true;

      await controller.save();

      expect(controller.taskState, 'succeeded');
      expect(controller.savedWork, isNull);
      expect(controller.hasUnresolvedSave, isTrue);
      expect(controller.errorCode, 'INTERNAL_PITCH_RESPONSE_INVALID');
      expect(controller.canSave, isFalse);
      expect(
        controller.startNewDraft(_manuscript('Independent local draft')),
        isFalse,
      );
      expect(client.runCalls, 1);

      await controller.read();

      expect(controller.taskState, 'succeeded');
      expect(controller.savedWork?.version, 1);
      expect(controller.hasUnresolvedSave, isFalse);
      expect(controller.errorCode, isNull);
      expect(client.runCalls, 1);
      expect(client.readCalls, 2);
    },
  );

  test(
    'reopen refuses a non-v4 saved manuscript and preserves local text',
    () async {
      client.reopenResult = _savedRow(
        manuscript: _manuscript('Other saved work'),
        taskId: _taskId(90),
        artifactId: _artifactId(90),
        workId: _workId(90),
        version: 1,
        draftDigest: '9' * 64,
        artifactSha256: '8' * 64,
        outputArtifactId: _artifactId(190),
        outputSha256: '7' * 64,
        outputSizeBytes: 64,
        scope: _scope,
      );
      final invalid = Map<String, dynamic>.from(client.reopenResult!);
      final document = Map<String, dynamic>.from(
        invalid['document'] as Map<String, dynamic>,
      );
      document['contract'] = {
        'id': 'lumenis.internal-pitch',
        'version': '3',
        'required_payload_paths': [
          'manuscript',
          'upstream_binding',
          'truth_state',
        ],
      };
      invalid['document'] = document;
      client.reopenResult = invalid;

      await controller.reopen(_artifactId(90));

      expect(controller.savedWork, isNull);
      expect(controller.draft.title, 'First draft');
      expect(controller.errorCode, 'INTERNAL_PITCH_RESPONSE_INVALID');
    },
  );

  test('scope changes invalidate an in-flight prepare reply', () async {
    final started = Completer<void>();
    final release = Completer<void>();
    client.prepareStarted = started;
    client.prepareGate = release;

    final saving = controller.save();
    await started.future;
    final originalDraft = controller.draft;
    expect(controller.startNewDraft(_manuscript('Must not replace')), isFalse);
    expect(controller.draft, same(originalDraft));

    controller.updateScope(_otherScope);
    release.complete();
    await saving;

    expect((controller.scope as InternalPitchScope?)?.subjectId, 'subject-b');
    expect(controller.taskId, isNull);
    expect(controller.taskState, isNull);
    expect(controller.savedWork, isNull);
    expect(client.runCalls, 0);
    expect(controller.busy, isFalse);
  });

  test('cancel reconciles a result already committed by the server', () async {
    client.commitOnRun = false;
    client.commitOnCancel = true;

    await controller.save();
    expect(controller.taskState, 'prepared');
    expect(controller.savedWork, isNull);

    await controller.cancel();

    expect(client.cancelCalls, 1);
    expect(client.runCalls, 1);
    expect(client.readCalls, 2);
    expect(controller.taskState, 'succeeded');
    expect(controller.savedWork?.version, 1);
    expect(controller.errorCode, isNull);
  });

  test('starting a local draft clears the previous saved parent', () async {
    await controller.save();
    final previous = controller.savedWork!;

    expect(
      controller.startNewDraft(_manuscript('Independent local draft')),
      isTrue,
    );
    expect(controller.savedWork, isNull);
    expect(controller.taskId, isNull);
    expect(controller.canSave, isTrue);
    await controller.save();

    expect(client.prepareCalls, hasLength(2));
    expect(client.prepareCalls.last.revision, isNull);
    expect(controller.savedWork!.version, 1);
    expect(controller.savedWork!.workId, isNot(previous.workId));
  });

  test('filtered empty page keeps its opaque continuation cursor', () async {
    const opaqueCursor = 'opaque:/cursor?token=a%2Fb';
    final otherVersion = _savedRow(
      manuscript: _manuscript('Old profile'),
      taskId: _taskId(60),
      artifactId: _artifactId(60),
      workId: _workId(60),
      version: 1,
      draftDigest: '6' * 64,
      artifactSha256: '5' * 64,
      outputArtifactId: _artifactId(160),
      outputSha256: '4' * 64,
      outputSizeBytes: 64,
      scope: _scope,
    );
    (otherVersion['document'] as Map<String, dynamic>)['contract'] = {
      'id': 'lumenis.internal-pitch',
      'version': '3',
      'required_payload_paths': [
        'manuscript',
        'upstream_binding',
        'truth_state',
      ],
    };
    client.listReplies.add({
      'items': [otherVersion],
      'has_more': true,
      'next_cursor': opaqueCursor,
      'verification_complete': false,
      'unverified_candidates': 2,
    });
    client.listReplies.add({
      'items': [
        _savedRow(
          manuscript: _manuscript('Later page'),
          taskId: _taskId(61),
          artifactId: _artifactId(61),
          workId: _workId(61),
          version: 1,
          draftDigest: '1' * 64,
          artifactSha256: '2' * 64,
          outputArtifactId: _artifactId(161),
          outputSha256: '3' * 64,
          outputSizeBytes: 64,
          scope: _scope,
        ),
      ],
      'has_more': false,
      'next_cursor': null,
      'verification_complete': true,
      'unverified_candidates': 0,
    });

    await controller.list(limit: 20);
    expect(controller.items, isEmpty);
    expect(controller.hasMore, isTrue);
    expect(controller.cursor, opaqueCursor);
    expect(controller.pageMetadata['verification_complete'], isFalse);

    await controller.loadMore();
    expect(client.listCursors, [null, opaqueCursor]);
    expect(controller.items.single.manuscript.title, 'Later page');
    expect(controller.hasMore, isFalse);
    expect(controller.cursor, isNull);
  });
}

InternalPitchManuscript _manuscript(String title) => InternalPitchManuscript(
  title: title,
  summary: 'A user supplied summary.',
  sections: const [
    InternalPitchSection(heading: 'Goal', body: 'A concrete outcome.'),
  ],
  language: 'en',
  authorship: 'user_supplied',
);

String _taskId(int sequence) =>
    'task-pitch-${sequence.toRadixString(16).padLeft(24, '0')}';
String _artifactId(int sequence) =>
    'ART-${sequence.toRadixString(16).padLeft(16, '0')}';
String _workId(int sequence) =>
    'WORK-${sequence.toRadixString(16).padLeft(24, '0')}';

Map<String, dynamic> _savedRow({
  required InternalPitchManuscript manuscript,
  required String taskId,
  required String artifactId,
  required String workId,
  required int version,
  required String draftDigest,
  required String artifactSha256,
  required String outputArtifactId,
  required String outputSha256,
  required int outputSizeBytes,
  required LumenisWorkspaceScope scope,
  String? previousArtifactId,
  String? parentSha256,
  String? requestId,
}) {
  final contract = {
    'id': 'lumenis.internal-pitch',
    'version': '4',
    'required_payload_paths': ['manuscript', 'truth_state'],
  };
  final output = {
    'name': 'document.docx',
    'artifact_id': outputArtifactId,
    'sha256': outputSha256,
    'size_bytes': outputSizeBytes,
    'media_type': _docxMediaType,
  };
  final document = <String, dynamic>{
    'schema': 'lumenis.saved-work/v1',
    'context': {...scope.toJson(), 'actor_id': 'actor-test'},
    'work_id': workId,
    'version': version,
    'parent_artifact_id': previousArtifactId,
    'parent_sha256': parentSha256,
    'request_id':
        requestId ?? 'pitch-request-${taskId.substring(taskId.length - 8)}',
    'input_hash': 'd' * 64,
    'draft_digest': draftDigest,
    'contract': contract,
    'task_id': taskId,
    'assertion_id': null,
    'kind': 'report',
    'title': manuscript.title,
    'markdown':
        '${manuscript.title}\n\n${manuscript.summary}\n\n## Goal\n\nA concrete outcome.',
    'payload': {
      'manuscript': manuscript.toJson(),
      'truth_state': {
        'source_admission': 'USER_AUTHORED_CONTENT',
        'citation_admission': 'NO_SIGNED_QUOTE',
        'external_fact_verification': 'NOT_INFERRED_FROM_AUTHORSHIP',
        'owned_model_execution': 'NOT_RUN',
        'external_effect': 'NOT_PERFORMED',
        'business_outcome': 'NOT_OBSERVED',
      },
    },
    'citations': <Object?>[],
    'attachments': [output],
  };
  final artifact = {
    'artifact_id': artifactId,
    'kind': 'saved_document',
    'sha256': artifactSha256,
    'size_bytes': 1024,
    'source_execution_id': workId,
  };
  final receipt = {
    'schema': 'lumenis.committed-saved-work/v1',
    'task_id': taskId,
    'assertion_id': null,
    'contract': contract,
    'scope': scope.toJson(),
    'ref': artifactId,
    'work_id': workId,
    'version': version,
    'parent': {'ref': previousArtifactId, 'sha256': parentSha256},
    'sha256': artifactSha256,
    'size_bytes': 1024,
    'draft_digest': draftDigest,
    'sources': <Object?>[],
    'constraint_observations': {
      'committed_bytes_match': true,
      'parent_chain_verified': true,
      'required_payload_paths_present': ['manuscript', 'truth_state'],
    },
  };
  return {
    'artifact': artifact,
    'document': document,
    'return_ref': {
      'artifact_id': artifactId,
      'work_id': workId,
      'version': version,
      'scope': scope.toJson(),
    },
    'receipt': receipt,
  };
}

final class _PrepareCall {
  const _PrepareCall({
    required this.scope,
    required this.manuscript,
    required this.requestId,
    required this.revision,
  });

  final LumenisWorkspaceScope scope;
  final InternalPitchManuscript manuscript;
  final String requestId;
  final InternalPitchRevision? revision;
}

final class _PitchTask {
  _PitchTask({required this.taskId, required this.call});

  final String taskId;
  final _PrepareCall call;
  bool committed = false;
  Map<String, dynamic>? work;
  Map<String, dynamic>? actionReceipt;
  String state = 'prepared';
}

final class _PitchClient extends LumenisCoreClient {
  _PitchClient() : super(baseUrl: 'http://127.0.0.1:1');

  final List<_PrepareCall> prepareCalls = [];
  final List<String?> listCursors = [];
  final List<Map<String, dynamic>> listReplies = [];
  final List<SharedWorkspaceScope> sharedListScopes = [];
  final List<SharedWorkspaceScope> sharedReopenScopes = [];
  final Map<String, _PitchTask> _tasksByRequest = {};
  final Map<String, _PitchTask> _tasksById = {};
  final Map<String, Map<String, dynamic>> _savedByArtifact = {};
  int runCalls = 0;
  int readCalls = 0;
  int cancelCalls = 0;
  int _sequence = 1;
  bool loseFirstPrepareAcknowledgement = false;
  bool loseFirstRunAcknowledgement = false;
  bool commitFirstLostRun = true;
  bool commitOnRun = true;
  bool commitOnCancel = false;
  bool normalizeBmpReadback = false;
  bool omitFirstCommittedReadback = false;
  String? runStateOverride;
  Completer<void>? prepareStarted;
  Completer<void>? prepareGate;
  Map<String, dynamic>? reopenResult;
  LumenisWorkspaceScope? lastExportScope;

  Map<String, dynamic> savedRow(String artifactId) =>
      _savedByArtifact[artifactId]!;

  @override
  Future<Map<String, dynamic>> prepareInternalPitch({
    required LumenisWorkspaceScope scope,
    required InternalPitchManuscript manuscript,
    required String requestId,
    InternalPitchRevision? revision,
  }) async {
    final call = _PrepareCall(
      scope: scope,
      manuscript: manuscript,
      requestId: requestId,
      revision: revision,
    );
    prepareCalls.add(call);
    final task = _tasksByRequest.putIfAbsent(requestId, () {
      final taskId = _taskId(_sequence++);
      final created = _PitchTask(taskId: taskId, call: call);
      _tasksById[taskId] = created;
      return created;
    });
    final started = prepareStarted;
    if (started != null && !started.isCompleted) started.complete();
    await prepareGate?.future;
    if (loseFirstPrepareAcknowledgement) {
      loseFirstPrepareAcknowledgement = false;
      throw const SocketException('prepare response was lost');
    }
    return _taskReply(task, state: 'prepared');
  }

  @override
  Future<Map<String, dynamic>> runInternalPitch({
    required String taskId,
    required LumenisWorkspaceScope scope,
  }) async {
    runCalls++;
    final task = _tasksById[taskId]!;
    if (loseFirstRunAcknowledgement) {
      loseFirstRunAcknowledgement = false;
      if (commitFirstLostRun) {
        _commit(task);
      } else {
        task.state = 'prepared';
      }
      throw const SocketException('run response was lost');
    }
    if (commitOnRun) {
      _commit(task);
    } else {
      task.state = runStateOverride ?? 'prepared';
    }
    return _taskReply(task, state: task.state);
  }

  @override
  Future<Map<String, dynamic>> readInternalPitch({
    required String taskId,
    required LumenisWorkspaceScope scope,
  }) async {
    readCalls++;
    final task = _tasksById[taskId]!;
    final response = _taskReply(task, state: task.state);
    if (task.committed && omitFirstCommittedReadback) {
      omitFirstCommittedReadback = false;
      return {...response, 'action_receipt': null, 'work': null};
    }
    return response;
  }

  @override
  Future<Map<String, dynamic>> cancelInternalPitch({
    required String taskId,
    required LumenisWorkspaceScope scope,
  }) async {
    cancelCalls++;
    final task = _tasksById[taskId]!;
    if (commitOnCancel) _commit(task);
    return {
      ..._taskReply(task, state: task.state),
      'cancellation': task.committed ? 'ALREADY_COMMITTED' : 'CANCELLED',
    };
  }

  @override
  Future<Map<String, dynamic>> listAuthoredManuscripts({
    required String domainId,
    int limit = 100,
    String? cursor,
  }) async {
    listCursors.add(cursor);
    if (listReplies.isEmpty) {
      return {'items': <Object?>[], 'has_more': false, 'next_cursor': null};
    }
    return listReplies.removeAt(0);
  }

  @override
  Future<Map<String, dynamic>> listSharedAuthoredManuscripts({
    required SharedWorkspaceScope scope,
    int limit = 100,
    String? cursor,
  }) async {
    sharedListScopes.add(scope);
    listCursors.add(cursor);
    if (listReplies.isEmpty) {
      return {'items': <Object?>[], 'has_more': false, 'next_cursor': null};
    }
    return listReplies.removeAt(0);
  }

  @override
  Future<Map<String, dynamic>> reopenSavedManuscript({
    required String domainId,
    required String artifactId,
  }) async => reopenResult ?? _savedByArtifact[artifactId]!;

  @override
  Future<Map<String, dynamic>> reopenSharedSavedManuscript({
    required SharedWorkspaceScope scope,
    required String artifactId,
  }) async {
    sharedReopenScopes.add(scope);
    return reopenResult ?? _savedByArtifact[artifactId]!;
  }

  @override
  Future<InternalPitchFile> exportInternalPitch({
    required String taskId,
    required LumenisWorkspaceScope scope,
  }) async {
    lastExportScope = scope;
    return InternalPitchFile(
      bytes: Uint8List.fromList(const [0x50, 0x4b, 0x03, 0x04]),
      filename: 'document.docx',
      mediaType: _docxMediaType,
    );
  }

  void _commit(_PitchTask task) {
    if (task.committed) return;
    final sequence = _sequence++;
    final previousId = task.call.revision?.previousArtifactId;
    final parent = previousId == null ? null : _savedByArtifact[previousId];
    if (task.call.revision != null && parent == null) {
      throw StateError('The fake revision parent was not saved.');
    }
    final parentArtifact = parent?['artifact'] as Map<String, dynamic>?;
    final parentDocument = parent?['document'] as Map<String, dynamic>?;
    final workId = task.call.revision?.workId ?? _workId(sequence);
    final version = parent == null
        ? 1
        : (parentDocument!['version'] as int) + 1;
    final artifactId = _artifactId(sequence);
    final artifactSha256 = String.fromCharCode(97 + sequence % 6) * 64;
    final draftDigest = String.fromCharCode(102 - sequence % 6) * 64;
    final outputArtifactId = _artifactId(sequence + 1000);
    final outputSha256 = String.fromCharCode(97 + (sequence + 2) % 6) * 64;
    final outputSizeBytes = 64 + sequence;
    final row = _savedRow(
      manuscript: task.call.manuscript,
      taskId: task.taskId,
      artifactId: artifactId,
      workId: workId,
      version: version,
      draftDigest: draftDigest,
      artifactSha256: artifactSha256,
      outputArtifactId: outputArtifactId,
      outputSha256: outputSha256,
      outputSizeBytes: outputSizeBytes,
      scope: _readbackScope(task.call.scope),
      previousArtifactId: parent?['artifact'] == null
          ? null
          : (parent!['artifact'] as Map<String, dynamic>)['artifact_id']
                as String,
      parentSha256: parentArtifact?['sha256'] as String?,
      requestId: task.call.requestId,
    );
    task
      ..committed = true
      ..state = 'succeeded'
      ..work = row;
    task.actionReceipt = {
      'owner': 'Shared ContentCreation/TaskEngine/SavedWork',
      'task_id': task.taskId,
      'artifact_id': artifactId,
      'sha256': artifactSha256,
      'size_bytes': 1024,
      'work_id': workId,
      'version': version,
      'parent_artifact_id': row['document']['parent_artifact_id'],
      'parent_sha256': row['document']['parent_sha256'],
      'action_kind': version == 1
          ? 'INTERNAL_TEXT_CREATION'
          : 'INTERNAL_TEXT_REVISION',
      'execution_state': 'ARTIFACT_COMMITTED',
      'business_outcome': 'NOT_OBSERVED',
      'external_effect': 'NOT_PERFORMED',
      'scope': _readbackScope(task.call.scope).toJson(),
      'output': (row['document']['attachments'] as List).single,
    };
    _savedByArtifact[artifactId] = row;
  }

  Map<String, dynamic> _taskReply(_PitchTask task, {required String state}) => {
    'task_id': task.taskId,
    'state': state,
    'error': null,
    'scope': _readbackScope(task.call.scope).toJson(),
    'action_receipt': task.committed ? task.actionReceipt : null,
    'work': task.committed ? task.work : null,
  };

  LumenisWorkspaceScope _readbackScope(LumenisWorkspaceScope scope) {
    if (scope is InternalPitchScope &&
        normalizeBmpReadback &&
        scope.domainId == 'bmp') {
      return InternalPitchScope(
        domainId: 'zbmp',
        subjectId: scope.subjectId,
        brandFocusId: scope.brandFocusId,
        globalScope: scope.globalScope,
      );
    }
    return scope;
  }
}
