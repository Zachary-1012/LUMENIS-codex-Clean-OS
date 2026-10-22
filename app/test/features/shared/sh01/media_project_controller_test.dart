import 'dart:async';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';
import 'package:lumenis_app/features/shared/sh01/media_project_controller.dart';
import 'package:lumenis_app/features/shared/sh01/media_project_snapshot.dart';

// Contract fixture only; real backend behavior is covered by TC02 Python tests.
MediaProjectSnapshot _batchFixture(
  MediaProjectSnapshot snapshot, List<Map<String, dynamic>> commands,
) {
  var current = snapshot;
  for (final command in commands) {
    final id = command['clip_id'] as String;
    current = switch (command['op']) {
      'trim' => current.trimClip(id,
        sourceIn: (command['source_in'] as num).toDouble(),
        sourceOut: (command['source_out'] as num).toDouble()),
      'move_audio_clip' => current.moveAudioClip(id,
        timelineStart: (command['timeline_start'] as num).toDouble()),
      'audio_mix' => current.setAudioMix(id, MediaProjectAudioMix.fromJson(
        command['mix'], clipDuration: current.tracks.expand((t) => t.clips)
            .firstWhere((c) => c.clipId == id).durationSec)),
      'split' => current.splitClip(id, atSec: (command['at_sec'] as num).toDouble()),
      _ => throw const FormatException('Unsupported fixture command'),
    };
  }
  return current;
}

Map<String, dynamic> _batchResponse(
  MediaProjectSnapshot base, MediaProjectSnapshot candidate, List<String>? refs,
) => {
  'ok': true,
  'assets': base.assets.map((asset) => asset.toJson()).toList(),
  'source_artifact_refs': refs ?? <String>[],
  'rights_state': 'unknown', 'external_fetch': false,
  'edit_batch': {
    'state': 'preview', 'base_version': base.version,
    'base_digest': 'a' * 64, 'timeline_digest': 'b' * 64,
    'timeline': candidate.toJson(), 'persisted': false,
    'export_performed': false, 'approval_required': true,
    'undo_scope': 'session_per_operation_not_persisted',
  },
};

final class _Repository implements MediaProjectRepository {
  @override
  String contextKey = 'BMP:GLOBAL';
  final observedDomains = <String?>[];
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
  bool legacyRightsFormat = false;
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
  int batchCalls = 0;
  Completer<void>? pendingBatch;
  Object? batchFailure;
  Map<String, dynamic>? batchOverride;
  List<Map<String, dynamic>>? batchCommands;

  @override
  Future<Map<String, dynamic>> inspectEditBatch({
    required String? domain,
    required List<String> paths,
    List<String>? refs,
    required MediaProjectSnapshot timeline,
    required List<Map<String, dynamic>> commands,
  }) async {
    observedDomains.add(domain);
    batchCalls++;
    batchCommands = commands;
    await pendingBatch?.future;
    if (batchFailure != null) throw batchFailure!;
    return batchOverride ?? _batchResponse(timeline, _batchFixture(timeline, commands), refs);
  }

  int calls = 0;
  int referenceInspections = 0;
  Object? referenceFailure;
  Completer<void>? pendingReferenceInspection;
  Completer<void>? referenceInspectionStarted;
  List<MediaProjectAsset>? inspectedAssets;
  Completer<void>? pendingInspection;

  @override
  Future<List<MediaProjectAsset>> inspect(
    String? domain,
    List<String> paths,
  ) async {
    observedDomains.add(domain);
    await pendingInspection?.future;
    if (failure != null) throw failure!;
    return inspectedAssets ?? [asset];
  }

  @override
  Future<Map<String, dynamic>> export({
    required String? domain,
    required List<String> paths,
    required MediaProjectSnapshot timeline,
    required String outputKind,
    List<String>? refs,
    String? previousArtifactId,
    String? title,
    bool renderMedia = true,
  }) async {
    observedDomains.add(domain);
    calls++;
    exported = timeline;
    savedRendered = renderMedia;
    parent = previousArtifactId;
    await pending?.future;
    if (failure != null) throw failure!;
    savedProject = {
      'source_artifact_refs': ?refs,
      'schema_version': title == null ? 1 : 2,
      'title': ?title,
      if (title != null) 'project_revision': 1,
      'output_kind': outputKind,
      'timeline': timeline.toJson(),
      'rights': legacyRightsFormat
          ? {
              'state': 'unknown',
              'demo_acknowledged': true,
              'label': 'demo-only / rights unknown',
            }
          : {'state': 'unknown', 'label': 'rights unknown'},
    };
    return {
      'ok': true,
      'publish_status': 'not_performed',
      'evidence_recorded': false,
      'result': {
        'status': renderMedia ? 'rendered_staged' : 'project_saved',
        'artifact': {'artifact_id': 'ART-$calls'},
        'project': savedProject,
        'render': render,
      },
    };
  }

  bool savedRendered = true;
  Map<String, dynamic> get render => !savedRendered ? {
    'state': 'not_rendered', 'output_kind': 'video',
    'timeline_version': savedProject!['timeline']['version'],
  } : {
    'state': 'rendered_verified',
    'output_kind': 'video',
    'size_bytes': 8,
    'media_sha256': 'b' * 64,
    'measurement': {'actual_duration_sec': 4.0},
  };

  @override
  Future<Map<String, dynamic>> reopen(String? domain, String artifactId) async {
    observedDomains.add(domain);
    if (failure != null) throw failure!;
    return {
      'ok': true,
      'project': {'project': savedProject, 'render': render},
    };
  }

  @override
  Future<List<MediaProjectAsset>> inspectReferences(
    String? domain,
    List<String> refs,
  ) async {
    observedDomains.add(domain);
    referenceInspections++;
    final started = referenceInspectionStarted;
    if (started != null && !started.isCompleted) started.complete();
    await pendingReferenceInspection?.future;
    if (referenceFailure != null) throw referenceFailure!;
    return inspect(domain, refs);
  }

  @override
  Future<Map<String, dynamic>> importFile(
    String? domain,
    String filename,
    Uint8List bytes,
  ) async {
    observedDomains.add(domain);
    importCalls++;
    if (approvalRequired && !approvalIssued) {
      approvalIssued = true;
      throw LumenisCoreException(
        'approval required',
        statusCode: 403,
        errorCode: 'CONTENT_SOURCE_APPROVAL_REQUIRED',
        sourceConfirmation: ContentSourceConfirmation(
          confirmationId: 'CONF-source',
          resource: 'content-source-import:${domain == null ? 'shared-workspace:' : ''}v1:${'b' * 64}',
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
    String? domain,
    String confirmationId, {
    required bool confirmed,
  }) async {
    observedDomains.add(domain);
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

  List<Map<String, dynamic>> trims() => [{
    'op': 'trim',
    'clip_id': controller.timeline!.tracks.single.clips.single.clipId,
    'source_in': 0.0, 'source_out': 3.0,
  }];


  test('project-only save reopens unchanged and can later render', () async {
    await controller.importFile('chosen.mp4', Uint8List.fromList([1]));
    controller.edit((s) => s.addClip(repository.asset.assetId, trackId: 'video', sourceOut: 4));
    controller.setTitle('My edit');
    await controller.export(outputKind: 'video', renderMedia: false);
    expect(controller.version!.rendered, isFalse);
    expect(controller.version!.durationSec, isNull);
    expect(controller.hasUnsavedChanges, isFalse);
    await controller.reopen('ART-1');
    expect(controller.title, 'My edit');
    expect(controller.version!.rendered, isFalse);
    controller.setTitle('New title');
    expect(controller.hasUnsavedChanges, isTrue);
    await controller.export(outputKind: 'video', renderMedia: false);
    expect(repository.parent, 'ART-1');
    expect(controller.version!.title, 'New title');
    await controller.export(outputKind: 'video');
    expect(controller.version!.rendered, isTrue);
    expect(repository.parent, 'ART-2');
    expect(controller.hasUnsavedChanges, isFalse);
  });

  test('independent media imports edits exports and reopens with null domain', () async {
    final shared = MediaProjectController(repository: repository, domain: null);
    addTearDown(shared.dispose);
    await shared.importFile('interview.mp4', Uint8List.fromList([1, 2]));
    shared.edit((s) => s.addClip(repository.asset.assetId,
      trackId: 'video', sourceOut: 4));
    await shared.export(outputKind: 'video');
    expect(shared.version!.artifactId, 'ART-1');
    final saved = shared.timeline!.toJson();
    await shared.reopen('ART-1');
    expect(shared.timeline!.toJson(), saved);
    expect(shared.hasUnsavedChanges, isFalse);
    expect(repository.referenceInspections, 1);
    expect(repository.observedDomains, isNotEmpty);
    expect(repository.observedDomains, everyElement(isNull));
    expect(() => MediaProjectController(repository: repository, domain: 'SHARED'),
      throwsArgumentError);
  });

  test('Shared import approval retries only its exact independent context', () async {
    final shared = MediaProjectController(repository: repository, domain: null);
    addTearDown(shared.dispose);
    repository.approvalRequired = true;
    await shared.importFile('voice.wav', Uint8List.fromList([1, 2]),
      requestApproval: (confirmation) async {
        expect(confirmation.resource,
          'content-source-import:shared-workspace:v1:${'b' * 64}');
        return true;
      });
    expect(repository.importCalls, 2);
    expect(repository.confirmationCalls, 1);
    expect(shared.sourceRefs, ['ART-source']);
    expect(repository.observedDomains, everyElement(isNull));
  });

  test('independent draft rejects a late export after workspace context changes', () async {
    final shared = MediaProjectController(repository: repository, domain: null);
    addTearDown(shared.dispose);
    await shared.importFile('interview.mp4', Uint8List.fromList([1, 2]));
    shared.edit((s) => s.addClip(repository.asset.assetId,
      trackId: 'video', sourceOut: 4));
    repository.pending = Completer<void>();
    final saving = shared.export(outputKind: 'video');
    repository.contextKey = 'other-workspace';
    repository.pending!.complete();
    await saving;
    expect(shared.version, isNull);
    expect(shared.timeline, isNull);
    expect(shared.completionUnknown, isTrue);
    expect(shared.failureCode, 'CONTENT_CONTEXT_CHANGED');
    expect(shared.hasUnsavedChanges, isTrue);
    expect(repository.calls, 1);
  });

  test('batch inspect does not edit or export until explicit adoption', () async {
    await create();
    final base = controller.timeline!;
    final preview = await controller.previewEditBatch(trims());
    expect(preview, isNotNull);
    expect(controller.timeline, same(base));
    expect(repository.calls, 0);
    expect(controller.adoptEditBatch(preview!), isTrue);
    expect(controller.timeline!.toJson(), preview.timeline.toJson());
    expect(controller.adoptEditBatch(preview), isFalse);
    expect(repository.batchCalls, 1);
    controller.edit((s) => s.undo());
    expect(controller.timeline!.tracks.single.clips.single.sourceOut, 4);
    controller.edit((s) => s.undo());
    expect(controller.timeline!.tracks.single.clips, isEmpty);
  });

  test('preview discard leaves draft selection and prior history untouched', () async {
    await create();
    final id = controller.timeline!.tracks.single.clips.single.clipId;
    controller.selectClip(id);
    final base = controller.timeline;
    await controller.previewEditBatch(trims());
    expect(controller.timeline, same(base));
    expect(controller.selectedClipId, id);
    expect(controller.timeline!.canUndo, isTrue);
    expect(repository.calls, 0);
  });

  test('batch adoption exports stable returned IDs and preserves saved parent', () async {
    await create();
    await controller.export(outputKind: 'video');
    final preview = await controller.previewEditBatch([{
      'op': 'split',
      'clip_id': controller.timeline!.tracks.single.clips.single.clipId,
      'at_sec': 2.0,
    }]);
    expect(controller.adoptEditBatch(preview!), isTrue);
    final adopted = controller.timeline!;
    await controller.export(outputKind: 'video');
    expect(repository.parent, 'ART-1');
    expect(repository.exported, same(adopted));
    expect(repository.exported!.toJson(), preview.timeline.toJson());
    expect(repository.batchCalls, 1);
    expect(controller.version!.artifactId, 'ART-2');
  });

  test('a later local edit rejects an in-flight or unadopted preview', () async {
    await create();
    repository.pendingBatch = Completer<void>();
    final pending = controller.previewEditBatch(trims());
    controller.edit((s) => s.setAudioMix(s.tracks.single.clips.single.clipId,
      const MediaProjectAudioMix(volume: 0.8)));
    final changed = controller.timeline;
    repository.pendingBatch!.complete();
    expect(await pending, isNull);
    expect(controller.failureCode, 'CONTENT_BATCH_PREVIEW_STALE');
    expect(controller.timeline, same(changed));
    repository.pendingBatch = null;
    final preview = await controller.previewEditBatch(trims());
    controller.edit((s) => s.setAudioMix(s.tracks.single.clips.single.clipId,
      const MediaProjectAudioMix(volume: 0.7)));
    expect(controller.adoptEditBatch(preview!), isFalse);
  });

  test('changed context or quarantined sources reject preview adoption', () async {
    await create();
    final preview = await controller.previewEditBatch(trims());
    controller.quarantineDraftSources();
    expect(controller.adoptEditBatch(preview!), isFalse);
    expect(repository.calls, 0);
  });

  test('context switch during inspection keeps the result quarantined', () async {
    await create();
    repository.pendingBatch = Completer<void>();
    final pending = controller.previewEditBatch(trims());
    repository.contextKey = 'BMP:OTHER';
    repository.pendingBatch!.complete();
    expect(await pending, isNull);
    expect(controller.timeline, isNull);
    expect(controller.sourcesNeedRevalidation, isTrue);
    expect(repository.calls, 0);
  });

  test('batch failure keeps saved parent draft selection and retry available', () async {
    await create();
    await controller.export(outputKind: 'video');
    final base = controller.timeline;
    final id = base!.tracks.single.clips.single.clipId;
    controller.selectClip(id);
    repository.batchFailure = const LumenisCoreException(
      'private diagnostic', statusCode: 403, errorCode: 'CONTENT_SCOPE_DENIED');
    expect(await controller.previewEditBatch(trims()), isNull);
    expect(controller.timeline, same(base));
    expect(controller.version!.artifactId, 'ART-1');
    expect(controller.selectedClipId, id);
    expect(controller.busy, isFalse);
    repository.batchFailure = null;
    expect(await controller.previewEditBatch(trims()), isNotNull);
  });

  test('invalid response flags metadata and stale versions are rejected', () async {
    await create();
    final base = controller.timeline!;
    final candidate = _batchFixture(base, trims());
    for (final mutate in <void Function(Map<String, dynamic>)>[
      (r) => (r['edit_batch'] as Map)['persisted'] = true,
      (r) => (r['edit_batch'] as Map)['export_performed'] = true,
      (r) => (r['edit_batch'] as Map)['base_version'] = base.version + 1,
      (r) => (r['edit_batch'] as Map)['timeline'] = base.toJson(),
      (r) => r['source_artifact_refs'] = ['ART-unrequested'],
      (r) => ((r['assets'] as List).first as Map)['filename'] = 'substituted.mp4',
    ]) {
      final response = _batchResponse(base, candidate, null);
      mutate(response);
      repository.batchOverride = response;
      expect(await controller.previewEditBatch(trims()), isNull);
      expect(controller.timeline, same(base));
      expect(controller.failureCode, 'CONTENT_RESPONSE_INVALID');
    }
  });

  test('busy preview rejects repeat calls and captures immutable commands', () async {
    await create();
    repository.pendingBatch = Completer<void>();
    final commands = trims();
    final pending = controller.previewEditBatch(commands);
    commands.first['source_out'] = 1.0;
    expect(await controller.previewEditBatch(trims()), isNull);
    repository.pendingBatch!.complete();
    final preview = await pending;
    expect(preview!.timeline.tracks.single.clips.single.sourceOut, 3);
    expect(repository.batchCalls, 1);
  });

  test('empty or excessive batches never reach the repository', () async {
    await create();
    expect(await controller.previewEditBatch([]), isNull);
    expect(await controller.previewEditBatch(List.generate(129, (_) => trims().single)), isNull);
    expect(repository.batchCalls, 0);
  });

  test(
    'inspection starts a blank timeline, not an invented automatic cut',
    () async {
      await controller.createFromLocalFiles(['chosen.mp4']);
      expect(controller.timeline!.tracks.single.clips, isEmpty);
      expect(controller.hasUnsavedChanges, isTrue);
      expect(controller.version, isNull);
    },
  );

  test(
    'unknown rights do not gate export and permission denial preserves edits',
    () async {
      await create();
      final before = controller.timeline;
      await controller.export(outputKind: 'video');
      expect(repository.calls, 1);
      expect(controller.timeline, same(before));
      expect(controller.version?.artifactId, 'ART-1');
      expect(repository.savedProject?['rights'], {
        'state': 'unknown',
        'label': 'rights unknown',
      });
      controller.edit(
        (s) => s.setAudioMix(
          s.tracks.single.clips.single.clipId,
          const MediaProjectAudioMix(volume: .7),
        ),
      );
      repository.failure = const LumenisCoreException(
        'private-path',
        statusCode: 403,
      );
      await controller.export(outputKind: 'video');
      expect(repository.calls, 2);
      expect(
        controller.timeline!.tracks.single.clips.single.audioMix.volume,
        .7,
      );
      expect(controller.failureCode, 'CONTENT_SCOPE_DENIED');
      expect(controller.busy, isFalse);
    },
  );

  test(
    'legacy demo receipt stays readable with rights still unknown',
    () async {
      await create();
      repository.legacyRightsFormat = true;
      await controller.export(outputKind: 'video');
      expect(controller.version?.artifactId, 'ART-1');
      expect(controller.failureCode, isNull);
    },
  );

  test(
    'export captures a version and preserves concurrent newer edits',
    () async {
      await create();
      final snapshot = controller.timeline!;
      repository.pending = Completer<void>();
      final export = controller.export(outputKind: 'video');
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
      await controller.export(outputKind: 'video');
      expect(repository.parent, 'ART-1');
      expect(controller.hasUnsavedChanges, isFalse);
    },
  );

  test('export failure retains prior registered version', () async {
    await create();
    await controller.export(outputKind: 'video');
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
    await controller.export(outputKind: 'video');
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
    await controller.export(outputKind: 'video');
    expect(controller.completionUnknown, isTrue);
    await controller.export(outputKind: 'video');
    expect(repository.calls, 1);
    expect(controller.failureCode, 'CONTENT_EXPORT_COMPLETION_UNKNOWN');
    expect(controller.hasUnsavedChanges, isTrue);
  });

  test('reopen is read-only until original media is re-inspected', () async {
    await create();
    await controller.export(outputKind: 'video');
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
      await controller.export(outputKind: 'video');
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
      await controller.export(outputKind: 'video');
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
      await controller.export(outputKind: 'video');
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
      final export = controller.export(outputKind: 'video');
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
    await controller.export(outputKind: 'audio');
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
    await controller.export(outputKind: 'video');
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
      await controller.export(outputKind: 'video');
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
      await controller.export(outputKind: 'video');
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
