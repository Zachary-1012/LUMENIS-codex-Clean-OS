import 'dart:convert';

import 'package:flutter/foundation.dart';

import '../../../core/lumenis_core_client.dart';
import 'media_project_snapshot.dart';

abstract interface class MediaProjectRepository {
  String get contextKey;
  Future<List<MediaProjectAsset>> inspect(String? domain, List<String> paths);
  Future<List<MediaProjectAsset>> inspectReferences(
    String? domain,
    List<String> refs,
  );
  Future<Map<String, dynamic>> inspectEditBatch({
    required String? domain,
    required List<String> paths,
    List<String>? refs,
    required MediaProjectSnapshot timeline,
    required List<Map<String, dynamic>> commands,
  });
  Future<Map<String, dynamic>> importFile(
    String? domain,
    String filename,
    Uint8List bytes,
  );
  Future<Map<String, dynamic>> confirmImport(
    String? domain,
    String confirmationId, {
    required bool confirmed,
  });
  Future<Map<String, dynamic>> export({
    required String? domain,
    required List<String> paths,
    required MediaProjectSnapshot timeline,
    required String outputKind,
    List<String>? refs,
    String? previousArtifactId,
    String? title,
    bool renderMedia = true,
    Map<String, double> renderOptions = const {},
  });
  Future<Map<String, dynamic>> reopen(String? domain, String artifactId);
}

final class CoreMediaProjectRepository implements MediaProjectRepository {
  const CoreMediaProjectRepository(this.client);
  final LumenisCoreClient client;

  @override
  String get contextKey => jsonEncode(client.currentContextEnvelope);

  @override
  Future<List<MediaProjectAsset>> inspect(
    String? domain,
    List<String> paths,
  ) async {
    final response = await client.inspectContentMedia(
      domainId: domain,
      assetPaths: paths,
    );
    if (response['ok'] != true || response['assets'] is! List) {
      throw const FormatException('Media inspection response is invalid.');
    }
    return List<MediaProjectAsset>.unmodifiable(
      (response['assets'] as List).map(MediaProjectAsset.fromJson),
    );
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
    Map<String, double> renderOptions = const {},
  }) => client.exportContentProject(
    domainId: domain,
    assetPaths: refs == null ? paths : null,
    assetRefs: refs,
    timeline: timeline.toJson(),
    outputKind: outputKind,
    previousArtifactId: previousArtifactId,
    title: title,
    renderMedia: renderMedia,
    renderOptions: renderOptions,
  );

  @override
  Future<Map<String, dynamic>> reopen(String? domain, String artifactId) =>
      client.reopenContentProject(domainId: domain, artifactId: artifactId);

  @override
  Future<List<MediaProjectAsset>> inspectReferences(
    String? domain,
    List<String> refs,
  ) async {
    final response = await client.inspectContentMedia(
      domainId: domain,
      assetRefs: refs,
    );
    if (response['ok'] != true || response['assets'] is! List) {
      throw const FormatException('Media inspection response is invalid.');
    }
    return List<MediaProjectAsset>.unmodifiable(
      (response['assets'] as List).map(MediaProjectAsset.fromJson),
    );
  }

  @override
  Future<Map<String, dynamic>> inspectEditBatch({
    required String? domain,
    required List<String> paths,
    List<String>? refs,
    required MediaProjectSnapshot timeline,
    required List<Map<String, dynamic>> commands,
  }) => client.inspectContentEditBatch(
    domainId: domain,
    assetPaths: refs == null ? paths : null,
    assetRefs: refs,
    timeline: timeline.toJson(),
    commands: commands,
    expectedVersion: timeline.version,
  );

  @override
  Future<Map<String, dynamic>> importFile(
    String? domain,
    String filename,
    Uint8List bytes,
  ) => client.importContentSource(
    domainId: domain,
    filename: filename,
    bytes: bytes,
  );

  @override
  Future<Map<String, dynamic>> confirmImport(
    String? domain,
    String confirmationId, {
    required bool confirmed,
  }) => client.confirmContentSource(
    domainId: domain,
    confirmationId: confirmationId,
    confirmed: confirmed,
  );
}

enum MediaProjectOperation {
  idle,
  importing,
  inspecting,
  saving,
  exporting,
  reopening,
}

/// A registered server result, not a claim that the user has downloaded it.
final class MediaProjectVersion {
  MediaProjectVersion._({
    required this.artifactId,
    required this.timelineJson,
    required this.outputKind,
    required this.durationSec,
    required this.timelineVersion,
    required this.evidenceRecorded,
    required this.sourceRefs,
    required this.title,
    required this.projectRevision,
    required this.rendered,
    required this.renderOptions,
    required this.inputLufs,
    required this.inputTruePeak,
    required this.outputLufs,
    required this.outputTruePeak,
  });

  final String artifactId;
  final Map<String, dynamic> timelineJson;
  final String outputKind;
  final double? durationSec;
  final String? title;
  final int? projectRevision;
  final bool rendered;
  final Map<String, double> renderOptions;
  final double? inputLufs;
  final double? inputTruePeak;
  final double? outputLufs;
  final double? outputTruePeak;
  final int timelineVersion;
  final bool? evidenceRecorded;
  final List<String> sourceRefs;

  factory MediaProjectVersion.read(
    String artifactId,
    Object? projectValue,
    Object? renderValue, {
    bool? evidenceRecorded,
  }) {
    if (!RegExp(r'^ART-[A-Za-z0-9_-]{1,70}$').hasMatch(artifactId) ||
        projectValue is! Map ||
        renderValue is! Map) {
      throw const FormatException('Invalid content project response.');
    }
    final project = Map<String, dynamic>.from(projectValue);
    final render = Map<String, dynamic>.from(renderValue);
    final kind = project['output_kind'];
    final timeline = project['timeline'];
    final rights = project['rights'];
    final measurement = render['measurement'];
    final duration = measurement is Map
        ? measurement['actual_duration_sec']
        : null;
    final size = render['size_bytes'];
    final refs = project['source_artifact_refs'] ?? const <String>[];
    final rendered = render['state'] == 'rendered_verified';
    final title = project['title'];
    final revision = project['project_revision'];
    if (!const [1, 2].contains(project['schema_version']) ||
        (project['schema_version'] == 2 &&
            (title is! String ||
                title.trim().isEmpty ||
                title.length > 200 ||
                revision is! int ||
                revision < 1)) ||
        !const ['video', 'audio'].contains(kind) ||
        timeline is! Map ||
        timeline['version'] is! int ||
        (timeline['version'] as int) < 1 ||
        rights is! Map ||
        rights['state'] != 'unknown' ||
        (rights.containsKey('demo_acknowledged') &&
            rights['demo_acknowledged'] != true) ||
        render['output_kind'] != kind ||
        (rendered
            ? (duration is! num ||
                  !duration.isFinite ||
                  duration <= 0 ||
                  size is! int ||
                  size <= 0 ||
                  !RegExp(
                    r'^[0-9a-f]{64}$',
                  ).hasMatch('${render['media_sha256']}'))
            : (project['schema_version'] != 2 ||
                  render['state'] != 'not_rendered' ||
                  render.length != 3 ||
                  render['timeline_version'] != timeline['version'])) ||
        refs is! List ||
        refs.length > 64 ||
        refs.any(
          (r) =>
              r is! String || !RegExp(r'^ART-[A-Za-z0-9_-]{1,70}$').hasMatch(r),
        )) {
      throw const FormatException('Unverified content project response.');
    }
    // Detach server JSON from the mutable response used by the transport caller.
    final detached = jsonDecode(jsonEncode(timeline)) as Map<String, dynamic>;
    final processing = render['audio_processing'];
    final mastering = processing is Map ? processing['mastering'] : null;
    final input = mastering is Map ? mastering['input_measurement'] : null;
    final loudness = measurement is Map ? measurement['loudness'] : null;
    double? measured(Object? value) {
      if (value == null) return null;
      final number = value is num
          ? value.toDouble()
          : double.tryParse('$value');
      return number != null && number.isFinite ? number : null;
    }

    return MediaProjectVersion._(
      artifactId: artifactId,
      timelineJson: Map<String, dynamic>.unmodifiable(detached),
      outputKind: kind as String,
      durationSec: rendered ? (duration as num).toDouble() : null,
      title: title as String?,
      projectRevision: revision as int?,
      rendered: rendered,
      renderOptions: _readRenderOptions(project['render_options']),
      inputLufs: measured(input is Map ? input['input_i'] : null),
      inputTruePeak: measured(input is Map ? input['input_tp'] : null),
      outputLufs: measured(
        loudness is Map ? loudness['integrated_lufs'] : null,
      ),
      outputTruePeak: measured(
        loudness is Map ? loudness['true_peak_dbtp'] : null,
      ),
      timelineVersion: timeline['version'] as int,
      evidenceRecorded: evidenceRecorded,
      sourceRefs: List<String>.unmodifiable(refs.cast<String>()),
    );
  }
}

Map<String, double> _readRenderOptions(Object? value) {
  if (value == null) return const {};
  if (value is! Map ||
      value.keys.any(
        (key) => !const {
          'loudness_target_lufs',
          'noise_reduction_db',
          'noise_floor_db',
        }.contains(key),
      )) {
    throw const FormatException('Invalid audio processing options.');
  }
  final result = <String, double>{};
  for (final entry in value.entries) {
    final number = entry.value;
    if (number is! num || !number.isFinite) {
      throw const FormatException('Invalid audio processing value.');
    }
    result[entry.key as String] = number.toDouble();
  }
  final target = result['loudness_target_lufs'];
  final reduction = result['noise_reduction_db'];
  final floor = result['noise_floor_db'];
  if (target != null && !const {-16, -14, -23}.contains(target) ||
      reduction != null && (reduction < 3 || reduction > 18) ||
      floor != null && (reduction == null || floor < -80 || floor > -20)) {
    throw const FormatException('Unsupported audio processing values.');
  }
  if (reduction != null) result['noise_floor_db'] = floor ?? -50;
  return Map.unmodifiable(result);
}

/// A validated, in-memory preview tied to one controller and one exact draft.
/// Keeping this object never saves, exports, or grants source rights.
final class MediaProjectBatchPreview {
  const MediaProjectBatchPreview._(
    this._owner,
    this._base,
    this._context,
    this.timeline,
    this.commandCount,
  );
  final MediaProjectController _owner;
  final MediaProjectSnapshot _base;
  final String _context;
  final MediaProjectSnapshot timeline;
  final int commandCount;
}

/// Presentation state only. Core reauthorizes, fingerprints and renders every
/// export; neither a local edit nor a server response is public publication.
final class MediaProjectController extends ChangeNotifier {
  MediaProjectController({required this.repository, required this.domain}) {
    if (domain != null && !const ['CTH', 'BMP'].contains(domain)) {
      throw ArgumentError.value(domain, 'domain');
    }
  }

  final MediaProjectRepository repository;

  /// Null explicitly selects independent Shared creation, not a business domain.
  final String? domain;
  MediaProjectSnapshot? _timeline;
  MediaProjectVersion? _version;
  String? _title;
  Map<String, double> _renderOptions = const {};
  List<String> _paths = const [];
  List<String>? _sourceRefs;
  List<String>? _suspendedSourceRefs;
  bool _sourcesNeedRevalidation = false;
  String? _draftContext;
  String? _failureCode;
  String? _selectedClipId;
  bool _disposed = false;
  bool _completionUnknown = false;
  int _scopeGeneration = 0;
  int _operationScopeGeneration = 0;
  MediaProjectOperation _operation = MediaProjectOperation.idle;

  MediaProjectSnapshot? get timeline => contextMatches ? _timeline : null;
  MediaProjectVersion? get version => contextMatches ? _version : null;
  String? get title => contextMatches ? _title : null;
  Map<String, double> get renderOptions =>
      contextMatches ? _renderOptions : const {};
  String? get selectedClipId => _selectedClipId;
  String? get failureCode => _failureCode;
  MediaProjectOperation get operation => _operation;
  bool get busy => _operation != MediaProjectOperation.idle;
  bool get completionUnknown => _completionUnknown;
  bool get needsOriginalFiles => _version != null && _timeline == null;
  bool get sourcesNeedRevalidation => _sourcesNeedRevalidation;
  List<String> get sourceRefs => contextMatches
      ? List<String>.unmodifiable(_sourceRefs ?? const [])
      : const [];
  bool get hasUnsavedChanges =>
      _timeline != null &&
      (_timeline!.version != _version?.timelineVersion ||
          _title != _version?.title ||
          !mapEquals(_renderOptions, _version?.renderOptions));
  bool get contextMatches =>
      _draftContext == null ||
      (_matchesContext(_draftContext!) && !_sourcesNeedRevalidation);

  String get _contextKey =>
      '${domain ?? 'shared_workspace:v1'}:${repository.contextKey}';

  void setLoudnessTarget(double? target) {
    if (_disposed || busy || !contextMatches || _timeline == null) return;
    final options = Map<String, double>.from(_renderOptions);
    if (target == null) {
      options.remove('loudness_target_lufs');
    } else {
      options['loudness_target_lufs'] = target;
    }
    _renderOptions = _readRenderOptions(options);
    _failureCode = null;
    notifyListeners();
  }

  void setTitle(String value) {
    if (_disposed || busy || !contextMatches) return;
    final title = value.trim();
    if (title.isEmpty ||
        title.length > 200 ||
        RegExp(r'[\x00-\x1f]').hasMatch(title)) {
      _fail('CONTENT_PROJECT_TITLE_INVALID');
      return;
    }
    _title = title;
    _failureCode = null;
    notifyListeners();
  }

  void selectClip(String? id) {
    if (_disposed) return;
    if (id != null &&
        (_timeline == null ||
            !_timeline!.tracks.any(
              (t) => t.clips.any((c) => c.clipId == id),
            ))) {
      throw ArgumentError.value(id, 'clipId');
    }
    _selectedClipId = id;
    notifyListeners();
  }

  void edit(MediaProjectSnapshot Function(MediaProjectSnapshot) transform) {
    if (_disposed || _timeline == null) return;
    if (!contextMatches) {
      _fail('CONTENT_CONTEXT_CHANGED');
      return;
    }
    // Export captures its input before awaiting; further edits remain unsaved.
    final next = transform(_timeline!);
    _timeline = next;
    if (!next.tracks.any(
      (t) => t.clips.any((c) => c.clipId == _selectedClipId),
    )) {
      _selectedClipId = null;
    }
    _failureCode = null;
    notifyListeners();
  }

  Future<MediaProjectBatchPreview?> previewEditBatch(
    List<Map<String, dynamic>> commands,
  ) async {
    if (_disposed || busy || _timeline == null) return null;
    if (!contextMatches) {
      _fail('CONTENT_CONTEXT_CHANGED');
      return null;
    }
    final base = _timeline!;
    final context = _contextKey;
    final refs = _sourceRefs;
    if (!_begin(MediaProjectOperation.inspecting)) return null;
    try {
      if (commands.isEmpty || commands.length > 128) {
        throw const FormatException('Invalid batch command count.');
      }
      // Detach the request from fields that may change while inspection awaits.
      final frozen = (jsonDecode(jsonEncode(commands)) as List)
          .map((value) => Map<String, dynamic>.from(value as Map))
          .toList(growable: false);
      final response = await repository.inspectEditBatch(
        domain: domain,
        paths: _paths,
        refs: refs,
        timeline: base,
        commands: frozen,
      );
      if (!_acceptContext(context) || _sourcesNeedRevalidation) return null;
      if (!identical(_timeline, base)) {
        _fail('CONTENT_BATCH_PREVIEW_STALE');
        return null;
      }
      final batch = response['edit_batch'];
      if (response['ok'] != true ||
          response['assets'] is! List ||
          response['rights_state'] != 'unknown' ||
          response['external_fetch'] != false ||
          jsonEncode(response['source_artifact_refs']) !=
              jsonEncode(refs ?? const <String>[]) ||
          batch is! Map ||
          batch['state'] != 'preview' ||
          batch['base_version'] != base.version ||
          batch['persisted'] != false ||
          batch['export_performed'] != false ||
          batch['approval_required'] != true ||
          !RegExp(r'^[0-9a-f]{64}$').hasMatch('${batch['base_digest']}') ||
          !RegExp(r'^[0-9a-f]{64}$').hasMatch('${batch['timeline_digest']}')) {
        throw const FormatException('Invalid batch preview response.');
      }
      final assets = (response['assets'] as List)
          .map(MediaProjectAsset.fromJson)
          .toList(growable: false);
      MediaProjectSnapshot.fromJson(base.toJson(), inspectedAssets: assets);
      final candidate = MediaProjectSnapshot.fromJson(
        batch['timeline'],
        inspectedAssets: assets,
      );
      if (candidate.version <= base.version) {
        throw const FormatException('Batch preview did not advance the draft.');
      }
      return MediaProjectBatchPreview._(
        this,
        base,
        context,
        candidate,
        frozen.length,
      );
    } catch (error) {
      if (_acceptContext(context)) _capture(error);
      return null;
    } finally {
      _end();
    }
  }

  bool canAdoptEditBatch(MediaProjectBatchPreview preview) =>
      !_disposed &&
      !busy &&
      identical(preview._owner, this) &&
      identical(_timeline, preview._base) &&
      contextMatches &&
      _contextKey == preview._context;

  bool adoptEditBatch(MediaProjectBatchPreview preview) {
    if (!canAdoptEditBatch(preview)) {
      if (!_disposed) _fail('CONTENT_BATCH_PREVIEW_STALE');
      return false;
    }
    // Use the concrete returned IDs. Export later submits this snapshot without
    // rerunning the commands; Artifact parent/version checks remain unchanged.
    _timeline = preview._base.adoptInspectedPreview(preview.timeline);
    if (!_timeline!.tracks.any(
      (track) => track.clips.any((clip) => clip.clipId == _selectedClipId),
    )) {
      _selectedClipId = null;
    }
    _failureCode = null;
    notifyListeners();
    return true;
  }

  Future<void> createFromLocalFiles(
    List<String> paths, {
    bool discardExisting = false,
    String formatRatio = '9:16',
  }) async {
    if (!_canReplace(discardExisting) ||
        !_begin(MediaProjectOperation.inspecting)) {
      return;
    }
    final context = _contextKey;
    final selected = List<String>.unmodifiable(paths);
    try {
      final assets = await repository.inspect(domain, selected);
      final timeline = MediaProjectSnapshot.empty(
        inspectedAssets: assets,
        formatRatio: formatRatio,
      );
      if (!_acceptContext(context)) return;
      _timeline = timeline;
      _paths = selected;
      _sourceRefs = null;
      _suspendedSourceRefs = null;
      _sourcesNeedRevalidation = false;
      _version = null;
      _renderOptions = const {};
      _draftContext = context;
      _selectedClipId = null;
      _completionUnknown = false;
    } catch (error) {
      _capture(error);
    } finally {
      _end();
    }
  }

  Future<void> importFile(
    String filename,
    Uint8List bytes, {
    Future<bool?> Function(ContentSourceConfirmation confirmation)?
    requestApproval,
  }) async {
    if (_disposed || busy) return;
    if (!contextMatches) {
      _fail('CONTENT_CONTEXT_CHANGED');
      return;
    }
    if (needsOriginalFiles || (_timeline != null && _sourceRefs == null)) {
      _fail('CONTENT_ORIGINAL_FILES_REQUIRED');
      return;
    }
    _begin(MediaProjectOperation.importing);
    final context = _contextKey;
    try {
      Map<String, dynamic> response;
      try {
        response = await repository.importFile(domain, filename, bytes);
      } on LumenisCoreException catch (error) {
        final confirmation = error.sourceConfirmation;
        if (error.statusCode != 403 ||
            error.errorCode != 'CONTENT_SOURCE_APPROVAL_REQUIRED' ||
            confirmation == null ||
            confirmation.filename != filename ||
            confirmation.sizeBytes != bytes.length) {
          rethrow;
        }
        if (requestApproval == null) {
          _fail('CONTENT_APPROVAL_PENDING');
          return;
        }
        if (!_acceptContext(context)) return;
        final confirmed = await requestApproval(confirmation);
        if (!_acceptContext(context)) return;
        if (confirmed == null) {
          _fail('CONTENT_APPROVAL_PENDING');
          return;
        }
        final confirmationResult = await repository.confirmImport(
          domain,
          confirmation.confirmationId,
          confirmed: confirmed,
        );
        if (!confirmed) {
          _fail('CONTENT_IMPORT_CANCELLED');
          return;
        }
        if (confirmationResult['ok'] != true ||
            confirmationResult['status'] != 'ready_for_retry' ||
            confirmationResult['purpose'] != 'local_content_draft') {
          throw const FormatException(
            'Source approval did not authorize the documented retry.',
          );
        }
        if (!_acceptContext(context)) return;
        response = await repository.importFile(domain, filename, bytes);
      }
      final responseCode = response['code'] ?? response['error_code'];
      final approvalStatus = response['approval_status'] ?? response['status'];
      if (responseCode == 'CONTENT_SOURCE_APPROVAL_REQUIRED' ||
          responseCode == 'APPROVAL_REQUIRED' ||
          approvalStatus?.toString().toUpperCase() == 'PENDING' ||
          approvalStatus?.toString().toUpperCase() == 'APPROVAL_PENDING') {
        _fail('CONTENT_APPROVAL_PENDING');
        return;
      }
      final result = response['result'];
      if (response['ok'] != true ||
          result is! Map ||
          result['artifact'] is! Map ||
          response['publish_status'] != 'not_performed') {
        throw const FormatException('Media was not registered.');
      }
      final ref = result['artifact']['artifact_id'];
      if (ref is! String ||
          !RegExp(r'^ART-[A-Za-z0-9_-]{1,70}$').hasMatch(ref)) {
        throw const FormatException('Invalid source reference.');
      }
      final asset = MediaProjectAsset.fromJson(result['asset']);
      if (!_acceptContext(context)) return;
      if (_timeline?.assets.any((a) => a.assetId == asset.assetId) ?? false) {
        _failureCode = 'CONTENT_SOURCE_ALREADY_ADDED';
        return;
      }
      _timeline = _timeline == null
          ? MediaProjectSnapshot.empty(inspectedAssets: [asset])
          : _timeline!.addInspectedAsset(asset);
      if (_sourcesNeedRevalidation) {
        _suspendedSourceRefs = List<String>.unmodifiable([
          ...?_suspendedSourceRefs,
          ref,
        ]);
      } else {
        _sourceRefs = List<String>.unmodifiable([...?_sourceRefs, ref]);
      }
      _draftContext = context;
    } catch (error) {
      _capture(error);
    } finally {
      _end();
    }
  }

  Future<void> export({
    required String outputKind,
    bool renderMedia = true,
  }) async {
    if (_disposed || busy || _timeline == null) return;
    if (!contextMatches) {
      _fail('CONTENT_CONTEXT_CHANGED');
      return;
    }
    if (_completionUnknown) {
      _fail('CONTENT_EXPORT_COMPLETION_UNKNOWN');
      return;
    }
    if (_version != null &&
        !hasUnsavedChanges &&
        (!renderMedia || _version!.rendered)) {
      _fail('CONTENT_PROJECT_NO_CHANGES');
      return;
    }
    _begin(
      renderMedia
          ? MediaProjectOperation.exporting
          : MediaProjectOperation.saving,
    );
    final title = _title;
    final renderOptions = _renderOptions;
    final snapshot = _timeline!;
    final context = _contextKey;
    try {
      final response = await repository.export(
        domain: domain,
        paths: _paths,
        refs: _sourceRefs,
        timeline: snapshot,
        outputKind: outputKind,
        previousArtifactId: _version?.artifactId,
        title: title,
        renderMedia: renderMedia,
        renderOptions: renderOptions,
      );
      final result = response['result'];
      if (response['ok'] != true ||
          response['publish_status'] != 'not_performed' ||
          result is! Map ||
          result['status'] !=
              (renderMedia ? 'rendered_staged' : 'project_saved') ||
          result['artifact'] is! Map) {
        throw const FormatException(
          'Export returned no registered content project.',
        );
      }
      final version = MediaProjectVersion.read(
        '${result['artifact']['artifact_id']}',
        result['project'],
        result['render'],
        evidenceRecorded: response['evidence_recorded'] == true,
      );
      final returned = MediaProjectSnapshot.fromJson(
        version.timelineJson,
        inspectedAssets: snapshot.assets,
      );
      if (version.outputKind != outputKind ||
          version.title != title ||
          version.rendered != renderMedia ||
          !mapEquals(version.renderOptions, renderOptions) ||
          jsonEncode(returned.toJson()) != jsonEncode(snapshot.toJson())) {
        throw const FormatException(
          'Export does not match the submitted edit.',
        );
      }
      if (!_acceptContext(context)) {
        _completionUnknown = true;
        return;
      }
      _version = version;
    } catch (error) {
      _capture(error);
      // A lost or malformed response cannot prove that no file was created.
      _completionUnknown =
          error is FormatException ||
          error is LumenisCoreException &&
              (error.errorCode == 'CONTENT_EXPORT_TIMEOUT' ||
                  error.statusCode == null);
    } finally {
      _end();
    }
  }

  Future<void> reopen(String artifactId, {bool discardExisting = false}) async {
    if (!_canReplace(discardExisting) ||
        !_begin(MediaProjectOperation.reopening)) {
      return;
    }
    final context = _contextKey;
    try {
      if (!_acceptContext(context)) return;
      final response = await repository.reopen(domain, artifactId);
      if (!_acceptContext(context)) return;
      final bundle = response['project'];
      if (response['ok'] != true || bundle is! Map) {
        throw const FormatException('Project was not returned.');
      }
      final version = MediaProjectVersion.read(
        artifactId,
        bundle['project'],
        bundle['render'],
      );
      MediaProjectSnapshot? timeline;
      if (version.sourceRefs.isNotEmpty) {
        final assets = await repository.inspectReferences(
          domain,
          version.sourceRefs,
        );
        if (!_acceptContext(context)) return;
        timeline = MediaProjectSnapshot.fromJson(
          version.timelineJson,
          inspectedAssets: assets,
        );
      }

      // Keep the current in-memory draft intact until the candidate version
      // and every required source reference have passed validation.
      if (!_acceptContext(context)) return;
      _version = version;
      _title = version.title;
      _renderOptions = version.renderOptions;
      _timeline = timeline;
      _paths = const [];
      _sourceRefs = version.sourceRefs.isEmpty ? null : version.sourceRefs;
      _suspendedSourceRefs = null;
      _sourcesNeedRevalidation = false;
      _selectedClipId = null;
      _draftContext = context;
      _completionUnknown = false;
    } catch (error) {
      if (_acceptContext(context)) _capture(error);
    } finally {
      _end();
    }
  }

  Future<void> relinkOriginalFiles(List<String> paths) async {
    if (_disposed ||
        busy ||
        (!needsOriginalFiles &&
            !(_sourcesNeedRevalidation && _timeline != null))) {
      return;
    }
    if (_draftContext != _contextKey) {
      _fail('CONTENT_CONTEXT_CHANGED');
      return;
    }
    _begin(MediaProjectOperation.inspecting);
    final context = _contextKey;
    final selected = List<String>.unmodifiable(paths);
    try {
      final assets = await repository.inspect(domain, selected);
      final timeline = MediaProjectSnapshot.fromJson(
        _timeline?.toJson() ?? _version!.timelineJson,
        inspectedAssets: assets,
      );
      if (!_acceptContext(context)) return;
      _paths = selected;
      // Preserve the unsaved draft's undo history after fresh asset validation.
      _timeline ??= timeline;
      _sourceRefs = null;
      _suspendedSourceRefs = null;
      _sourcesNeedRevalidation = false;
    } catch (error) {
      _capture(error);
    } finally {
      _end();
    }
  }

  /// Reauthorize imported sources before revealing a quarantined draft again.
  /// This restores an in-memory draft only; the shell still owns navigation.
  Future<void> recoverDraftSources() async {
    if (_disposed || busy || !_sourcesNeedRevalidation || _timeline == null) {
      return;
    }
    if (_draftContext != _contextKey) {
      _fail('CONTENT_CONTEXT_CHANGED');
      return;
    }
    final refs = _suspendedSourceRefs;
    if (refs == null || refs.isEmpty) {
      _fail('CONTENT_ORIGINAL_FILES_REQUIRED');
      return;
    }
    if (!_begin(MediaProjectOperation.inspecting)) return;
    final context = _contextKey;
    try {
      final assets = await repository.inspectReferences(domain, refs);
      MediaProjectSnapshot.fromJson(
        _timeline!.toJson(),
        inspectedAssets: assets,
      );
      if (!_acceptContext(context)) return;
      _sourceRefs = refs;
      _suspendedSourceRefs = null;
      _sourcesNeedRevalidation = false;
    } catch (error) {
      _capture(error);
    } finally {
      _end();
    }
  }

  bool _canReplace(bool discardExisting) {
    if (_disposed || busy) return false;
    if (hasUnsavedChanges && !discardExisting) {
      _fail('CONTENT_UNSAVED_CHANGES');
      return false;
    }
    return true;
  }

  bool _begin(MediaProjectOperation operation) {
    if (_disposed || busy) return false;
    _operation = operation;
    _operationScopeGeneration = _scopeGeneration;
    _failureCode = null;
    notifyListeners();
    return !_disposed;
  }

  bool _acceptContext(String expected) {
    if (_disposed) return false;
    if (_operationScopeGeneration != _scopeGeneration ||
        !_matchesContext(expected)) {
      _failureCode = 'CONTENT_CONTEXT_CHANGED';
      return false;
    }
    return true;
  }

  bool _matchesContext(String expected) {
    if (_contextKey == expected) return true;
    quarantineDraftSources();
    return false;
  }

  /// An unavailable scope read invalidates cached access even when the client
  /// retained its last envelope. Keep the draft for explicit source revalidation.
  void quarantineDraftSources() {
    if (_disposed) return;
    // Invalidate pending work even if a failed scope read retains its envelope.
    // Keep the draft identity unchanged so explicit revalidation can recover it.
    _scopeGeneration++;
    _suspendedSourceRefs ??= _sourceRefs;
    _sourceRefs = null;
    if (_timeline != null || _version != null) {
      _sourcesNeedRevalidation = true;
    }
  }

  void _capture(Object error) {
    if (_disposed) return;
    _failureCode = switch (error) {
      LumenisCoreException(:final errorCode, :final statusCode) =>
        errorCode == 'APPROVAL_REQUIRED' ||
                errorCode == 'CONTENT_SOURCE_APPROVAL_REQUIRED'
            ? 'CONTENT_APPROVAL_PENDING'
            : errorCode ??
                  (statusCode == 401
                      ? 'CONTENT_AUTH_REQUIRED'
                      : statusCode == 403
                      ? 'CONTENT_SCOPE_DENIED'
                      : 'CONTENT_CORE_UNAVAILABLE'),
      FormatException() => 'CONTENT_RESPONSE_INVALID',
      _ => 'CONTENT_CORE_UNAVAILABLE',
    };
  }

  void _fail(String code) {
    _failureCode = code;
    notifyListeners();
  }

  void _end() {
    if (_disposed) return;
    _operation = MediaProjectOperation.idle;
    notifyListeners();
  }

  @override
  void dispose() {
    _disposed = true;
    super.dispose();
  }
}
