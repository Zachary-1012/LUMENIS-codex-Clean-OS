import 'dart:async';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/features/shared/sh01/media_project_controller.dart';
import 'package:lumenis_app/features/shared/sh01/media_project_snapshot.dart';

final class _Repository implements MediaProjectRepository {
  @override
  String contextKey = 'BMP:GLOBAL';
  final asset = MediaProjectAsset(
    assetId: 'MEDIA-aaaaaaaaaaaaaaaa',
    filename: 'interview.mp4',
    sha256: 'a' * 64,
    durationSec: 20,
    mediaKind: 'video_audio',
    hasVideo: true,
    audioStreamCount: 1,
  );
  MediaProjectSnapshot? exported;
  String? parent;
  Object? failure;
  Completer<void>? pending;
  Map<String, dynamic>? savedProject;
  bool approvalRequired = false;
  bool approvalIssued = false;
  int importCalls = 0;
  int confirmationCalls = 0;
  bool? confirmedImport;
  Map<String, dynamic> confirmationResult = const {
    'ok': true,
    'status': 'ready_for_retry',
    'purpose': 'local_content_draft',
  };
  int calls = 0;
  int referenceInspections = 0;
  Object? referenceFailure;
  Completer<void>? pendingReferenceInspection;
  Completer<void>? referenceInspectionStarted;
  List<MediaProjectAsset>? inspectedAssets;
  Completer<void>? pendingInspection;

  @override
  Future<List<MediaProjectAsset>> inspect(
    String domain,
    List<String> paths,
  ) async {
    await pendingInspection?.future;
    if (failure != null) throw failure!;
    return inspectedAssets ?? [asset];
  }

  @override
  Future<Map<String, dynamic>> export({
    required String domain,
    required List<String> paths,
    required MediaProjectSnapshot timeline,
    required String outputKind,
    required bool demoAcknowledged,
    List<String>? refs,
    String? previousArtifactId,
  }) async {
    calls++;
    exported = timeline;
    parent = previousArtifactId;
    await pending?.future;
    if (failure != null) throw failure!;
    savedProject = {
      'source_artifact_refs': ?refs,
      'schema_version': 1,
      'output_kind': outputKind,
      'timeline': timeline.toJson(),
      'rights': {'state': 'unknown', 'demo_acknowledged': true},
    };
    return {
      'ok': true,
      'publish_status': 'not_performed',
      'evidence_recorded': false,
      'result': {
        'status': 'rendered_staged',
        'artifact': {'artifact_id': 'ART-$calls'},
        'project': savedProject,
        'render': render,
      },
    };
  }

  Map<String, dynamic> get render => {
    'state': 'rendered_verified',
    'output_kind': 'video',
    'size_bytes': 8,
    'media_sha256': 'b' * 64,
    'measurement': {'actual_duration_sec': 4.0},
  };

  @override
  Future<Map<String, dynamic>> reopen(String domain, String artifactId) async {
    if (failure != null) throw failure!;
    return {
      'ok': true,
      'project': {'project': savedProject, 'render': render},
    };
  }

  @override
  Future<List<MediaProjectAsset>> inspectReferences(
    String domain,
    List<String> refs,
  ) async {
    referenceInspections++;
    final started = referenceInspectionStarted;
    if (started != null && !started.isCompleted) started.complete();
    await pendingReferenceInspection?.future;
    if (referenceFailure != null) throw referenceFailure!;
    return inspect(domain, refs);
  }

  @override
  Future<Map<String, dynamic>> importFile(
    String domain,
    String filename,
    Uint8List bytes,
  ) async {
    importCalls++;
    if (approvalRequired && !approvalIssued) {
      approvalIssued = true;
      throw LumenisCoreException(
        'approval required',
        statusCode: 403,
        errorCode: 'CONTENT_SOURCE_APPROVAL_REQUIRED',
        sourceConfirmation: ContentSourceConfirmation(
          confirmationId: 'CONF-source',
          resource: 'content-source-import:v1:${'b' * 64}',
          expiresAt: DateTime.utc(2026, 9, 29),
          filename: filename,
          sizeBytes: bytes.length,
          bodySha256: 'c' * 64,
        ),
      );
    }
    if (failure != null) throw failure!;
    return {
      'ok': true,
      'publish_status': 'not_performed',
      'result': {
        'artifact': {'artifact_id': 'ART-source'},
        'asset': asset.toJson(),
      },
    };
  }

  @override
  Future<Map<String, dynamic>> confirmImport(
    String domain,
    String confirmationId, {
    required bool confirmed,
  }) async {
    confirmationCalls++;
    confirmedImport = confirmed;
    return confirmationResult;
  }
}

void main() {
  late _Repository repository;
  late MediaProjectController controller;
  setUp(() {
    repository = _Repository();
    controller = MediaProjectController(repository: repository, domain: 'BMP');
  });
  tearDown(() => controller.dispose());
  Future<void> create() async {
    await controller.createFromLocalFiles(['chosen.mp4']);
    controller.edit(
      (s) =>
          s.addClip(repository.asset.assetId, trackId: 'video', sourceOut: 4),
    );
  }

  test(
    'inspection starts a blank timeline, not an invented automatic cut',
    () async {
      await controller.createFromLocalFiles(['chosen.mp4']);
      expect(controller.timeline!.tracks.single.clips, isEmpty);
      expect(controller.hasUnsavedChanges, isTrue);
      expect(controller.version, isNull);
    },
  );

  test('demo choice is explicit and denial preserves edit intent', () async {
    await create();
    final before = controller.timeline;
    await controller.export(outputKind: 'video', demoAcknowledged: false);
    expect(repository.calls, 0);
    expect(controller.timeline, same(before));
    expect(controller.failureCode, 'CONTENT_DEMO_ACKNOWLEDGEMENT_REQUIRED');
    repository.failure = const LumenisCoreException(
      'private-path',
      statusCode: 403,
    );
    await controller.export(outputKind: 'video', demoAcknowledged: true);
    expect(controller.timeline, same(before));
    expect(controller.failureCode, 'CONTENT_SCOPE_DENIED');
    expect(controller.busy, isFalse);
  });

  test(
    'export captures a version and preserves concurrent newer edits',
    () async {
      await create();
      final snapshot = controller.timeline!;
      repository.pending = Completer<void>();
      final export = controller.export(
        outputKind: 'video',
        demoAcknowledged: true,
      );
      controller.edit(
        (s) => s.trimClip(
          s.tracks.single.clips.single.clipId,
          sourceIn: 1,
          sourceOut: 4,
        ),
      );
      repository.pending!.complete();
      await export;
      expect(repository.exported, same(snapshot));
      expect(controller.version!.timelineVersion, snapshot.version);
      expect(controller.version!.evidenceRecorded, isFalse);
      expect(controller.hasUnsavedChanges, isTrue);
      await controller.export(outputKind: 'video', demoAcknowledged: true);
      expect(repository.parent, 'ART-1');
      expect(controller.hasUnsavedChanges, isFalse);
    },
  );

  test('export failure retains prior registered version', () async {
    await create();
    await controller.export(outputKind: 'video', demoAcknowledged: true);
    final parent = controller.version;
    controller.edit(
      (s) => s.setAudioMix(
        s.tracks.single.clips.single.clipId,
        const MediaProjectAudioMix(volume: .4),
      ),
    );
    repository.failure = const LumenisCoreException(
      'render error',
      statusCode: 503,
      errorCode: 'CONTENT_RENDER_FAILED',
    );
    await controller.export(outputKind: 'video', demoAcknowledged: true);
    expect(controller.version, same(parent));
    expect(controller.timeline!.tracks.single.clips.single.audioMix.volume, .4);
    expect(controller.completionUnknown, isFalse);
  });

  test('timeout is completion unknown and never silently retries', () async {
    await create();
    repository.failure = const LumenisCoreException(
      'timeout',
      errorCode: 'CONTENT_EXPORT_TIMEOUT',
    );
    await controller.export(outputKind: 'video', demoAcknowledged: true);
    expect(controller.completionUnknown, isTrue);
    await controller.export(outputKind: 'video', demoAcknowledged: true);
    expect(repository.calls, 1);
    expect(controller.failureCode, 'CONTENT_EXPORT_COMPLETION_UNKNOWN');
    expect(controller.hasUnsavedChanges, isTrue);
  });

  test('reopen is read-only until original media is re-inspected', () async {
    await create();
    await controller.export(outputKind: 'video', demoAcknowledged: true);
    await controller.reopen('ART-1');
    expect(controller.timeline, isNull);
    expect(controller.needsOriginalFiles, isTrue);
    expect(controller.version!.durationSec, 4);
    await controller.relinkOriginalFiles(['relocated.mp4']);
    expect(controller.needsOriginalFiles, isFalse);
    expect(controller.hasUnsavedChanges, isFalse);
    expect(controller.timeline!.tracks.single.clips.single.sourceOut, 4);
  });

  test(
    'failed reference inspection preserves the current unsaved draft',
    () async {
      await controller.importFile('interview.mp4', Uint8List.fromList([1, 2]));
      controller.edit(
        (s) =>
            s.addClip(repository.asset.assetId, trackId: 'video', sourceOut: 4),
      );
      await controller.export(outputKind: 'video', demoAcknowledged: true);
      final previousVersion = controller.version!;
      final clipId = controller.timeline!.tracks.single.clips.single.clipId;
      controller.edit((s) => s.trimClip(clipId, sourceIn: 1, sourceOut: 4));
      final previousDraft = controller.timeline!;
      controller.selectClip(clipId);

      repository.referenceFailure = const LumenisCoreException(
        'source unavailable',
        statusCode: 503,
        errorCode: 'CONTENT_SOURCE_UNAVAILABLE',
      );
      await controller.reopen('ART-1', discardExisting: true);

      expect(controller.timeline, same(previousDraft));
      expect(controller.timeline!.canUndo, isTrue);
      expect(controller.version, same(previousVersion));
      expect(controller.sourceRefs, ['ART-source']);
      expect(controller.selectedClipId, clipId);
      expect(controller.hasUnsavedChanges, isTrue);
      expect(controller.failureCode, 'CONTENT_SOURCE_UNAVAILABLE');
      expect(controller.busy, isFalse);
    },
  );

  test(
    'successful reopen replaces the old draft after reference inspection',
    () async {
      await controller.importFile('interview.mp4', Uint8List.fromList([1, 2]));
      controller.edit(
        (s) =>
            s.addClip(repository.asset.assetId, trackId: 'video', sourceOut: 4),
      );
      await controller.export(outputKind: 'video', demoAcknowledged: true);
      final previousVersion = controller.version!;
      final clipId = controller.timeline!.tracks.single.clips.single.clipId;
      controller.edit((s) => s.trimClip(clipId, sourceIn: 1, sourceOut: 4));
      final previousDraft = controller.timeline!;

      await controller.reopen('ART-1', discardExisting: true);

      expect(controller.timeline, isNot(same(previousDraft)));
      expect(controller.timeline!.tracks.single.clips.single.sourceIn, 0);
      expect(controller.version, isNot(same(previousVersion)));
      expect(controller.version!.artifactId, 'ART-1');
      expect(controller.sourceRefs, ['ART-source']);
      expect(controller.needsOriginalFiles, isFalse);
      expect(controller.hasUnsavedChanges, isFalse);
      expect(repository.referenceInspections, 1);
    },
  );

  test(
    'scope change during reopen quarantines and preserves the old draft',
    () async {
      await controller.importFile('interview.mp4', Uint8List.fromList([1, 2]));
      controller.edit(
        (s) =>
            s.addClip(repository.asset.assetId, trackId: 'video', sourceOut: 4),
      );
      await controller.export(outputKind: 'video', demoAcknowledged: true);
      final previousVersion = controller.version!;
      final clipId = controller.timeline!.tracks.single.clips.single.clipId;
      controller.edit((s) => s.trimClip(clipId, sourceIn: 1, sourceOut: 4));
      final previousDraft = controller.timeline!;
      repository.pendingReferenceInspection = Completer<void>();
      repository.referenceInspectionStarted = Completer<void>();

      final reopening = controller.reopen('ART-1', discardExisting: true);
      await repository.referenceInspectionStarted!.future;
      repository.contextKey = 'BMP:brand-two';
      repository.pendingReferenceInspection!.complete();
      await reopening;

      expect(controller.failureCode, 'CONTENT_CONTEXT_CHANGED');
      expect(controller.contextMatches, isFalse);
      expect(controller.timeline, isNull);
      expect(controller.version, isNull);
      expect(controller.sourceRefs, isEmpty);
      expect(controller.hasUnsavedChanges, isTrue);

      repository.contextKey = 'BMP:GLOBAL';
      await controller.recoverDraftSources();
      expect(controller.timeline, same(previousDraft));
      expect(controller.timeline!.canUndo, isTrue);
      expect(controller.version, same(previousVersion));
      expect(controller.sourceRefs, ['ART-source']);
    },
  );

  test('unsaved work is not replaced without explicit discard', () async {
    await create();
    final snapshot = controller.timeline;
    await controller.reopen('ART-other');
    expect(controller.timeline, same(snapshot));
    expect(controller.failureCode, 'CONTENT_UNSAVED_CHANGES');
    await controller.createFromLocalFiles(['other.mp4']);
    expect(controller.timeline, same(snapshot));
  });

  test(
    'context switch during export does not attach another scope result',
    () async {
      await create();
      repository.pending = Completer<void>();
      final export = controller.export(
        outputKind: 'video',
        demoAcknowledged: true,
      );
      repository.contextKey = 'BMP:brand-two';
      repository.pending!.complete();
      await export;
      expect(controller.version, isNull);
      expect(controller.failureCode, 'CONTENT_CONTEXT_CHANGED');
      expect(controller.contextMatches, isFalse);
      final before = controller.timeline;
      controller.edit((s) => s.undo());
      expect(controller.timeline, same(before));
    },
  );

  test('malformed response cannot become a saved version', () async {
    await create();
    await controller.export(outputKind: 'audio', demoAcknowledged: true);
    expect(controller.version, isNull);
    expect(controller.failureCode, 'CONTENT_RESPONSE_INVALID');
    expect(controller.completionUnknown, isTrue);
  });

  test('imported references reopen through fresh source inspection', () async {
    await controller.importFile('interview.mp4', Uint8List.fromList([1, 2]));
    controller.edit(
      (s) =>
          s.addClip(repository.asset.assetId, trackId: 'video', sourceOut: 4),
    );
    await controller.export(outputKind: 'video', demoAcknowledged: true);
    expect(controller.version!.sourceRefs, ['ART-source']);
    await controller.reopen('ART-1');
    expect(controller.needsOriginalFiles, isFalse);
    expect(controller.timeline!.tracks.single.clips.single.sourceOut, 4);
    expect(controller.hasUnsavedChanges, isFalse);
  });

  test(
    'scope change quarantines refs and draft until sources are reauthorized',
    () async {
      await controller.importFile('interview.mp4', Uint8List.fromList([1, 2]));
      expect(controller.sourceRefs, ['ART-source']);
      expect(
        () => controller.sourceRefs.add('ART-other'),
        throwsUnsupportedError,
      );
      controller.edit(
        (s) =>
            s.addClip(repository.asset.assetId, trackId: 'video', sourceOut: 4),
      );
      final draft = controller.timeline;

      repository.contextKey = 'BMP:actor-two:GLOBAL';
      expect(controller.contextMatches, isFalse);
      expect(controller.sourceRefs, isEmpty);
      expect(controller.timeline, isNull);
      expect(controller.hasUnsavedChanges, isTrue);
      await controller.recoverDraftSources();
      expect(repository.referenceInspections, 0);

      repository.contextKey = 'BMP:GLOBAL';
      expect(controller.contextMatches, isFalse);
      expect(controller.sourceRefs, isEmpty);
      await controller.export(outputKind: 'video', demoAcknowledged: true);
      expect(repository.calls, 0);
      repository.failure = const LumenisCoreException(
        'denied',
        statusCode: 403,
      );
      await controller.recoverDraftSources();
      expect(controller.timeline, isNull);
      expect(controller.sourcesNeedRevalidation, isTrue);
      repository.failure = null;
      await controller.recoverDraftSources();
      expect(repository.referenceInspections, 2);
      expect(controller.contextMatches, isTrue);
      expect(controller.timeline, same(draft));
      expect(controller.timeline!.canUndo, isTrue);
      expect(controller.sourceRefs, ['ART-source']);
    },
  );

  test(
    'local draft recovery reinspects original files without losing edits',
    () async {
      await create();
      final draft = controller.timeline;
      repository.contextKey = 'BMP:brand-two';
      expect(controller.contextMatches, isFalse);
      expect(controller.timeline, isNull);
      repository.contextKey = 'BMP:GLOBAL';
      await controller.recoverDraftSources();
      expect(controller.failureCode, 'CONTENT_ORIGINAL_FILES_REQUIRED');
      await controller.relinkOriginalFiles(['chosen.mp4']);
      expect(controller.contextMatches, isTrue);
      expect(controller.timeline, same(draft));
      expect(controller.timeline!.canUndo, isTrue);
    },
  );

  test(
    'failed scope read quarantines unchanged scope until fresh source checks',
    () async {
      await controller.importFile('interview.mp4', Uint8List.fromList([1, 2]));
      controller.edit(
        (s) =>
            s.addClip(repository.asset.assetId, trackId: 'video', sourceOut: 4),
      );
      await controller.export(outputKind: 'video', demoAcknowledged: true);
      final draft = controller.timeline;
      final version = controller.version;
      final contextBefore = repository.contextKey;
      controller.quarantineDraftSources();
      expect(repository.contextKey, contextBefore);
      expect(controller.timeline, isNull);
      expect(controller.version, isNull);
      expect(controller.sourceRefs, isEmpty);
      repository.failure = const LumenisCoreException(
        'Unavailable',
        statusCode: 503,
      );
      await controller.recoverDraftSources();
      expect(controller.sourcesNeedRevalidation, isTrue);
      expect(controller.timeline, isNull);
      repository.failure = null;
      await controller.recoverDraftSources();
      expect(repository.referenceInspections, 2);
      expect(controller.timeline, same(draft));
      expect(controller.version, same(version));
      expect(controller.sourceRefs, ['ART-source']);
    },
  );

  test(
    'recovery rejects missing sources and late cross-scope responses',
    () async {
      await controller.importFile('interview.mp4', Uint8List.fromList([1, 2]));
      controller.edit(
        (s) =>
            s.addClip(repository.asset.assetId, trackId: 'video', sourceOut: 4),
      );
      final draft = controller.timeline;
      repository.contextKey = 'BMP:other';
      expect(controller.contextMatches, isFalse);
      repository.contextKey = 'BMP:GLOBAL';
      repository.inspectedAssets = [];
      await controller.recoverDraftSources();
      expect(controller.failureCode, 'CONTENT_RESPONSE_INVALID');
      expect(controller.timeline, isNull);
      expect(controller.sourceRefs, isEmpty);
      repository.inspectedAssets = null;
      repository.pendingInspection = Completer<void>();
      final recovery = controller.recoverDraftSources();
      repository.contextKey = 'BMP:other';
      repository.pendingInspection!.complete();
      await recovery;
      expect(controller.failureCode, 'CONTENT_CONTEXT_CHANGED');
      expect(controller.timeline, isNull);
      repository.contextKey = 'BMP:GLOBAL';
      repository.pendingInspection = null;
      await controller.recoverDraftSources();
      expect(controller.timeline, same(draft));
    },
  );

  test(
    'approval requires an explicit choice before one exact-byte retry',
    () async {
      repository.approvalRequired = true;
      final bytes = Uint8List.fromList([1, 2, 3]);
      ContentSourceConfirmation? shown;
      await controller.importFile(
        'interview.wav',
        bytes,
        requestApproval: (confirmation) async {
          shown = confirmation;
          return true;
        },
      );
      expect(shown?.filename, 'interview.wav');
      expect(shown?.sizeBytes, bytes.length);
      expect(shown?.bodySha256, 'c' * 64);
      expect(repository.confirmationCalls, 1);
      expect(repository.confirmedImport, isTrue);
      expect(repository.importCalls, 2);
      expect(controller.sourceRefs, ['ART-source']);
      expect(controller.failureCode, isNull);
    },
  );

  test('cancel records false and leaves an existing draft untouched', () async {
    await controller.importFile('interview.mp4', Uint8List.fromList([1, 2]));
    controller.edit(
      (s) =>
          s.addClip(repository.asset.assetId, trackId: 'video', sourceOut: 4),
    );
    final before = controller.timeline;
    final importsBeforeCancel = repository.importCalls;
    repository.approvalRequired = true;
    await controller.importFile(
      'another.wav',
      Uint8List.fromList([9, 8]),
      requestApproval: (_) async => false,
    );
    expect(repository.confirmationCalls, 1);
    expect(repository.confirmedImport, isFalse);
    expect(repository.importCalls, importsBeforeCancel + 1);
    expect(controller.timeline, same(before));
    expect(controller.failureCode, 'CONTENT_IMPORT_CANCELLED');
  });

  test(
    'approval denial without a prompt never confirms or imports again',
    () async {
      repository.approvalRequired = true;
      await controller.importFile('pending.wav', Uint8List.fromList([1]));
      expect(repository.confirmationCalls, 0);
      expect(repository.importCalls, 1);
      expect(controller.timeline, isNull);
      expect(controller.failureCode, 'CONTENT_APPROVAL_PENDING');
    },
  );

  test(
    'failed import and duplicate media leave the current edit untouched',
    () async {
      await controller.importFile('interview.mp4', Uint8List.fromList([1, 2]));
      final before = controller.timeline;
      await controller.importFile('interview.mp4', Uint8List.fromList([1, 2]));
      expect(controller.timeline, same(before));
      expect(controller.failureCode, 'CONTENT_SOURCE_ALREADY_ADDED');
      repository.failure = const LumenisCoreException(
        'import failed',
        statusCode: 400,
      );
      await controller.importFile('invalid.mp4', Uint8List.fromList([3]));
      expect(controller.timeline, same(before));
    },
  );
}
