import 'dart:convert';
import 'dart:math' as math;

import 'package:flutter/foundation.dart';
import 'package:file_selector/file_selector.dart';

import '../../../core/lumenis_core_client.dart';
import '../../../core/transport/lumenis_http_transport.dart';
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
  Future<Map<String, dynamic>> inspectAudioProcessing({
    required String? domain,
    required List<String> paths,
    List<String>? refs,
    required MediaProjectSnapshot timeline,
    required Map<String, double> renderOptions,
    required double startSec,
    required double endSec,
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
    List<String>? sourceProjectArtifactRefs,
    String? title,
    bool renderMedia = true,
    Map<String, double> renderOptions = const {},
    Map<String, dynamic> deliveryOptions = const {},
  });
  Future<Map<String, dynamic>> reopen(String? domain, String artifactId);
}

abstract interface class MediaProjectTaskRepository {
  Future<Map<String, dynamic>> startExportTask(
    String? domain,
    String requestId,
    Map<String, dynamic> input,
  );
  Future<Map<String, dynamic>> readExportTask(
    String? domain,
    int taskId, {
    String? action,
  });
}

abstract interface class MediaProjectStreamRepository {
  Future<Map<String, dynamic>> importPicked(
    String? domain,
    XFile file,
    int length,
  );
}

abstract interface class MediaProjectTranscriptRepository {
  Future<Map<String, dynamic>> readTranscripts(
    String? domain,
    List<String> refs,
    String projectId,
    int offset,
  );
  Future<Map<String, dynamic>> previewWordCut(
    String? domain,
    List<String> refs,
    String projectId,
    List<Map<String, dynamic>> selections,
  );
}

final class CoreMediaProjectRepository
    implements
        MediaProjectRepository,
        MediaProjectStreamRepository,
        MediaProjectTaskRepository,
        MediaProjectTranscriptRepository {
  const CoreMediaProjectRepository(this.client);
  final LumenisCoreClient client;

  @override
  Future<Map<String, dynamic>> startExportTask(
    String? domain,
    String requestId,
    Map<String, dynamic> input,
  ) => client.startContentExportTask(
    domainId: domain,
    requestId: requestId,
    input: input,
  );
  @override
  Future<Map<String, dynamic>> readExportTask(
    String? domain,
    int taskId, {
    String? action,
  }) => client.contentExportTask(
    domainId: domain,
    taskId: taskId,
    action: action,
  );

  @override
  Future<Map<String, dynamic>> readTranscripts(
    String? domain,
    List<String> refs,
    String projectId,
    int offset,
  ) => client.readContentProjectTranscripts(
    domainId: domain,
    assetRefs: refs,
    projectId: projectId,
    offset: offset,
  );

  @override
  Future<Map<String, dynamic>> previewWordCut(
    String? domain,
    List<String> refs,
    String projectId,
    List<Map<String, dynamic>> selections,
  ) => client.previewContentWordCut(
    domainId: domain,
    assetRefs: refs,
    projectId: projectId,
    selections: selections,
  );

  @override
  Future<Map<String, dynamic>> importPicked(
    String? domain,
    XFile file,
    int length,
  ) => client.importContentSourceStream(
    domainId: domain,
    filename: file.name,
    upload: LumenisUploadBody(
      length: length,
      openRead: file.openRead,
      browserBlobUri: kIsWeb ? Uri.parse(file.path) : null,
    ),
  );

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
    List<String>? sourceProjectArtifactRefs,
    String? title,
    bool renderMedia = true,
    Map<String, double> renderOptions = const {},
    Map<String, dynamic> deliveryOptions = const {},
  }) => client.exportContentProject(
    domainId: domain,
    assetPaths: refs == null ? paths : null,
    assetRefs: refs,
    timeline: timeline.toJson(),
    outputKind: outputKind,
    previousArtifactId: previousArtifactId,
    sourceProjectArtifactRefs: sourceProjectArtifactRefs,
    title: title,
    renderMedia: renderMedia,
    renderOptions: renderOptions,
    deliveryOptions: deliveryOptions,
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
  Future<Map<String, dynamic>> inspectAudioProcessing({
    required String? domain,
    required List<String> paths,
    List<String>? refs,
    required MediaProjectSnapshot timeline,
    required Map<String, double> renderOptions,
    required double startSec,
    required double endSec,
  }) => client.inspectAudioProcessing(
    domainId: domain,
    assetPaths: refs == null ? paths : null,
    assetRefs: refs,
    timeline: timeline.toJson(),
    renderOptions: renderOptions,
    startSec: startSec,
    endSec: endSec,
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
    required this.sourceProjectArtifactRefs,
    required this.title,
    required this.projectRevision,
    required this.parentArtifactId,
    required this.rendered,
    required this.renderOptions,
    required this.deliveryOptions,
    required this.deliveryReports,
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
  final String? parentArtifactId;
  final bool rendered;
  final Map<String, double> renderOptions;
  final Map<String, dynamic> deliveryOptions;
  final Map<String, dynamic> deliveryReports;
  final double? inputLufs;
  final double? inputTruePeak;
  final double? outputLufs;
  final double? outputTruePeak;
  final int timelineVersion;
  final bool? evidenceRecorded;
  final List<String> sourceRefs;
  final List<String> sourceProjectArtifactRefs;

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
    final projectRefs =
        project['source_project_artifact_refs'] ?? const <String>[];
    final rendered = render['state'] == 'rendered_verified';
    final title = project['title'];
    final revision = project['project_revision'];
    final parent = project['parent_artifact_id'];
    if (!const [1, 2].contains(project['schema_version']) ||
        (project['schema_version'] == 2 &&
            (title is! String ||
                title.trim().isEmpty ||
                title.length > 200 ||
                revision is! int ||
                revision < 1)) ||
        (parent != null &&
            (parent is! String ||
                !RegExp(r'^ART-[A-Za-z0-9_-]{1,70}$').hasMatch(parent) ||
                parent == artifactId)) ||
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
        projectRefs is! List ||
        projectRefs.length > 64 ||
        projectRefs.toSet().length != projectRefs.length ||
        projectRefs.any(
          (r) =>
              r is! String ||
              !RegExp(r'^ART-[A-Za-z0-9_-]{1,70}$').hasMatch(r) ||
              r == artifactId ||
              r == parent,
        ) ||
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
      parentArtifactId: parent as String?,
      rendered: rendered,
      renderOptions: _readRenderOptions(project['render_options']),
      deliveryOptions: _readDeliveryOptions(project['delivery_options']),
      deliveryReports: _freezeJsonMap(render['delivery_reports']),
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
      sourceProjectArtifactRefs: List<String>.unmodifiable(
        projectRefs.cast<String>(),
      ),
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

Map<String, dynamic> _freezeJsonMap(Object? value) {
  if (value == null) return const {};
  if (value is! Map || value.keys.any((key) => key is! String)) {
    throw const FormatException('Invalid project option object.');
  }
  Object? freeze(Object? item) {
    if (item is Map) return _freezeJsonMap(item);
    if (item is List) return List<Object?>.unmodifiable(item.map(freeze));
    if (item == null ||
        item is String ||
        item is bool ||
        item is num && item.isFinite) {
      return item;
    }
    throw const FormatException('Invalid project option value.');
  }

  final keys = value.keys.cast<String>().toList()..sort();
  return Map.unmodifiable({for (final key in keys) key: freeze(value[key])});
}

Map<String, dynamic> _readDeliveryOptions(Object? value) {
  final options = _freezeJsonMap(value);
  final formats = options['audio_formats'];
  if (formats != null &&
      (formats is! List ||
          formats.length > 2 ||
          formats.toSet().length != formats.length ||
          formats.any((format) => !const ['mp3', 'm4a'].contains(format)))) {
    throw const FormatException('Invalid audio delivery formats.');
  }
  return options;
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
final class MediaAudioComparison {
  const MediaAudioComparison._(
    this._owner,
    this._base,
    this._context,
    this._previousOptions,
    this._scopeGeneration,
    this.options,
    this.original,
    this.processed,
    this.measurements,
    this.startSec,
    this.endSec,
  );
  final MediaProjectController _owner;
  final MediaProjectSnapshot _base;
  final String _context;
  final Map<String, double> _previousOptions;
  final int _scopeGeneration;
  final Map<String, double> options;
  final ContentProjectFile original;
  final ContentProjectFile processed;
  final Map<String, dynamic> measurements;
  final double startSec;
  final double endSec;
}

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
  Map<String, dynamic> _deliveryOptions = const {};
  List<String> _paths = const [];
  List<String>? _sourceRefs;
  List<String>? _suspendedSourceRefs;
  bool _sourcesNeedRevalidation = false;
  String? _draftContext;
  String? _failureCode;
  String? _selectedClipId;
  bool _disposed = false;
  bool _completionUnknown = false;
  Map<String, dynamic>? _exportTask;
  Map<String, dynamic>? get exportTask => contextMatches ? _exportTask : null;
  bool _taskActionPending = false;
  bool get taskActionPending => _taskActionPending;

  int _scopeGeneration = 0;
  int _operationScopeGeneration = 0;
  MediaProjectOperation _operation = MediaProjectOperation.idle;

  MediaProjectSnapshot? get timeline => contextMatches ? _timeline : null;
  MediaProjectVersion? get version => contextMatches ? _version : null;
  String? get title => contextMatches ? _title : null;
  Map<String, double> get renderOptions =>
      contextMatches ? _renderOptions : const {};
  Map<String, dynamic> get deliveryOptions =>
      contextMatches ? _deliveryOptions : const {};
  String? get selectedClipId => _selectedClipId;
  String? get failureCode => _failureCode;
  MediaProjectOperation get operation => _operation;
  bool get busy => _operation != MediaProjectOperation.idle;
  int get contextRevision => _scopeGeneration;
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
          !mapEquals(_renderOptions, _version?.renderOptions) ||
          jsonEncode(_deliveryOptions) !=
              jsonEncode(_version?.deliveryOptions));
  bool get contextMatches =>
      _draftContext == null ||
      (_matchesContext(_draftContext!) && !_sourcesNeedRevalidation);

  String get _contextKey =>
      '${domain ?? 'shared_workspace:v1'}:${repository.contextKey}';

  bool get canReadTranscripts =>
      repository is MediaProjectTranscriptRepository &&
      contextMatches &&
      _timeline != null &&
      _version != null &&
      !hasUnsavedChanges &&
      sourceRefs.isNotEmpty;

  Future<Map<String, dynamic>?> readTranscripts({int offset = 0}) async {
    if (!canReadTranscripts || busy || _disposed) return null;
    final base = _timeline!;
    final version = _version!;
    final context = _contextKey;
    if (!_begin(MediaProjectOperation.inspecting)) return null;
    try {
      final response = await (repository as MediaProjectTranscriptRepository)
          .readTranscripts(domain, sourceRefs, version.artifactId, offset);
      if (!_acceptContext(context) ||
          !identical(base, _timeline) ||
          !identical(version, _version)) {
        return null;
      }
      final result = response['transcripts'];
      if (response['ok'] != true ||
          response['external_fetch'] != false ||
          jsonEncode(response['source_artifact_refs']) !=
              jsonEncode(sourceRefs) ||
          result is! Map ||
          result['project_artifact_id'] != version.artifactId ||
          result['timeline_version'] != base.version ||
          result['words'] is! List ||
          !RegExp(r'^[0-9a-f]{64}$').hasMatch('${result['project_sha256']}')) {
        throw const FormatException('Invalid project transcript response.');
      }
      return Map<String, dynamic>.from(result);
    } catch (error) {
      if (_acceptContext(context)) _capture(error);
      return null;
    } finally {
      _end();
    }
  }

  Future<MediaProjectBatchPreview?> previewWordCut({
    required String projectSha256,
    required List<Map<String, dynamic>> selections,
  }) async {
    if (!canReadTranscripts || busy || _disposed || selections.isEmpty) {
      return null;
    }
    final base = _timeline!;
    final version = _version!;
    final context = _contextKey;
    final refs = sourceRefs;
    if (!_begin(MediaProjectOperation.inspecting)) return null;
    try {
      final frozen = (jsonDecode(jsonEncode(selections)) as List)
          .map((value) => Map<String, dynamic>.from(value as Map))
          .toList();
      final response = await (repository as MediaProjectTranscriptRepository)
          .previewWordCut(domain, refs, version.artifactId, frozen);
      if (!_acceptContext(context) ||
          !identical(base, _timeline) ||
          !identical(version, _version)) {
        return null;
      }
      final edit = response['transcript_edit'];
      if (response['ok'] != true ||
          response['assets'] is! List ||
          response['external_fetch'] != false ||
          jsonEncode(response['source_artifact_refs']) != jsonEncode(refs) ||
          edit is! Map ||
          edit['state'] != 'candidate' ||
          edit['edit_kind'] != 'cut_original' ||
          edit['parent_artifact_id'] != version.artifactId ||
          edit['parent_sha256'] != projectSha256 ||
          edit['parent_timeline_version'] != base.version ||
          edit['automatic_application'] != false) {
        throw const FormatException('Invalid word edit response.');
      }
      final assets = (response['assets'] as List)
          .map(MediaProjectAsset.fromJson)
          .toList(growable: false);
      MediaProjectSnapshot.fromJson(base.toJson(), inspectedAssets: assets);
      final candidate = MediaProjectSnapshot.fromJson(
        edit['preview_timeline'],
        inspectedAssets: assets,
      );
      if (candidate.version <= base.version) {
        throw const FormatException('Word edit did not advance the draft.');
      }
      return MediaProjectBatchPreview._(this, base, context, candidate, 1);
    } catch (error) {
      if (_acceptContext(context)) _capture(error);
      return null;
    } finally {
      _end();
    }
  }

  Future<MediaAudioComparison> previewAudioProcessing(
    Map<String, double> options, {
    required double startSec,
    required double endSec,
  }) async {
    if (_disposed || busy || !contextMatches || _timeline == null) {
      throw const FormatException('Audio preview context unavailable.');
    }
    final base = _timeline!;
    final context = _contextKey;
    final previous = _renderOptions;
    final generation = _scopeGeneration;
    final frozen = _readRenderOptions(options);
    final refs = _sourceRefs;
    final response = await repository.inspectAudioProcessing(
      domain: domain,
      paths: _paths,
      refs: refs,
      timeline: base,
      renderOptions: frozen,
      startSec: startSec,
      endSec: endSec,
    );
    final result = response['audio_comparison'];
    if (response['ok'] != true ||
        response['assets'] is! List ||
        response['rights_state'] != 'unknown' ||
        response['external_fetch'] != false ||
        jsonEncode(response['source_artifact_refs']) !=
            jsonEncode(refs ?? <String>[]) ||
        result is! Map ||
        result['state'] != 'preview' ||
        result['base_version'] != base.version ||
        result['persisted'] != false ||
        result['export_performed'] != false ||
        result['approval_required'] != true ||
        result['start_sec'] != startSec ||
        result['end_sec'] != endSec ||
        result['programme_duration_sec'] != base.durationSec ||
        !RegExp(r'^[0-9a-f]{64}$').hasMatch('${result['base_digest']}') ||
        !mapEquals(_readRenderOptions(result['render_options']), frozen)) {
      throw const FormatException('Invalid audio comparison response.');
    }
    MediaProjectSnapshot.fromJson(
      base.toJson(),
      inspectedAssets: (response['assets'] as List)
          .map(MediaProjectAsset.fromJson)
          .toList(),
    );
    final samples = result['samples'];
    ContentProjectFile read(String name) {
      final sample = samples is Map ? samples[name] : null;
      if (sample is! Map ||
          sample['wav_base64'] is! String ||
          (sample['wav_base64'] as String).length > 16 * 1024 * 1024 ||
          !RegExp(r'^[0-9a-f]{64}$').hasMatch('${sample['sha256']}')) {
        throw const FormatException('Invalid audio sample.');
      }
      final bytes = base64Decode(sample['wav_base64'] as String);
      if (bytes.length < 44 ||
          bytes.length > 12 * 1024 * 1024 ||
          bytes.length != sample['size_bytes'] ||
          ascii.decode(bytes.sublist(0, 4), allowInvalid: true) != 'RIFF' ||
          ascii.decode(bytes.sublist(8, 12), allowInvalid: true) != 'WAVE') {
        throw const FormatException('Invalid audio sample bytes.');
      }
      return ContentProjectFile(
        bytes: bytes,
        filename: '$name.wav',
        mediaType: 'audio/wav',
      );
    }

    final preview = MediaAudioComparison._(
      this,
      base,
      context,
      previous,
      generation,
      frozen,
      read('original'),
      read('processed'),
      _freezeJsonMap(result['programme_measurements']),
      startSec,
      endSec,
    );
    if (!canAdoptAudioProcessing(preview)) {
      throw const FormatException('Audio preview is stale.');
    }
    return preview;
  }

  bool canAdoptAudioProcessing(MediaAudioComparison preview) =>
      !_disposed &&
      !busy &&
      contextMatches &&
      identical(preview._owner, this) &&
      identical(preview._base, _timeline) &&
      preview._scopeGeneration == _scopeGeneration &&
      preview._context == _contextKey &&
      mapEquals(preview._previousOptions, _renderOptions);

  bool adoptAudioProcessing(MediaAudioComparison preview) {
    if (!canAdoptAudioProcessing(preview)) return false;
    _renderOptions = preview.options;
    _failureCode = null;
    notifyListeners();
    return true;
  }

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

  void setNoiseReduction({
    required bool enabled,
    double reduction = 12,
    double floor = -50,
  }) {
    if (_disposed || busy || !contextMatches || _timeline == null) return;
    final options = Map<String, double>.from(_renderOptions);
    if (enabled) {
      options['noise_reduction_db'] = reduction;
      options['noise_floor_db'] = floor;
    } else {
      options.remove('noise_reduction_db');
      options.remove('noise_floor_db');
    }
    _renderOptions = _readRenderOptions(options);
    _failureCode = null;
    notifyListeners();
  }

  void setAudioDeliveryFormat(String format, bool selected) {
    if (_disposed || busy || !contextMatches || _timeline == null) return;
    if (!const ['mp3', 'm4a'].contains(format)) {
      throw const FormatException('Unsupported audio delivery format.');
    }
    final formats = Set<String>.from(
      _deliveryOptions['audio_formats'] as List? ?? [],
    );
    selected ? formats.add(format) : formats.remove(format);
    final options = Map<String, dynamic>.from(_deliveryOptions);
    if (formats.isEmpty) {
      options.remove('audio_formats');
    } else {
      options['audio_formats'] = formats.toList()..sort();
    }
    _deliveryOptions = _readDeliveryOptions(options);
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
      _deliveryOptions = const {};
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
  }) => _importFile(
    filename,
    bytes.length,
    () => repository.importFile(domain, filename, bytes),
    requestApproval: requestApproval,
  );

  Future<void> importPickedFile(
    XFile file, {
    Future<bool?> Function(ContentSourceConfirmation confirmation)?
    requestApproval,
  }) async {
    final streamRepository = repository;
    if (streamRepository is! MediaProjectStreamRepository) {
      _fail('CONTENT_STREAM_UPLOAD_UNAVAILABLE');
      return;
    }
    final length = await file.length();
    if (length <= 0) {
      _fail('CONTENT_MEDIA_FILE_EMPTY');
      return;
    }
    return _importFile(
      file.name,
      length,
      () => (streamRepository as MediaProjectStreamRepository).importPicked(
        domain,
        file,
        length,
      ),
      requestApproval: requestApproval,
    );
  }

  Future<void> _importFile(
    String filename,
    int length,
    Future<Map<String, dynamic>> Function() upload, {
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
        response = await upload();
      } on LumenisCoreException catch (error) {
        final confirmation = error.sourceConfirmation;
        if (error.statusCode != 403 ||
            error.errorCode != 'CONTENT_SOURCE_APPROVAL_REQUIRED' ||
            confirmation == null ||
            confirmation.filename != filename ||
            confirmation.sizeBytes != length) {
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
        response = await upload();
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
    final derived = _version != null && _version!.outputKind != outputKind;
    if (!derived &&
        _version != null &&
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
    if (renderMedia) _exportTask = null;
    final title = _title;
    final renderOptions = _renderOptions;
    final deliveryOptions = _deliveryOptions;
    final snapshot = _timeline!;
    final context = _contextKey;
    final parent = derived ? null : _version?.artifactId;
    final projectRefs = derived
        ? <String>[_version!.artifactId]
        : _version?.sourceProjectArtifactRefs ?? const <String>[];
    try {
      final response =
          renderMedia &&
              _sourceRefs != null &&
              repository is MediaProjectTaskRepository
          ? await _runExportTask({
              'asset_refs': _sourceRefs,
              'timeline': snapshot.toJson(),
              'output_kind': outputKind,
              'previous_artifact_id': parent,
              'source_project_artifact_refs': projectRefs,
              'title': ?title,
              'render_options': renderOptions,
              'delivery_options': deliveryOptions,
            }, context)
          : await repository.export(
              domain: domain,
              paths: _paths,
              refs: _sourceRefs,
              timeline: snapshot,
              outputKind: outputKind,
              previousArtifactId: parent,
              sourceProjectArtifactRefs: projectRefs,
              title: title,
              renderMedia: renderMedia,
              renderOptions: renderOptions,
              deliveryOptions: deliveryOptions,
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
          version.parentArtifactId != parent ||
          !listEquals(version.sourceProjectArtifactRefs, projectRefs) ||
          version.title != title ||
          version.rendered != renderMedia ||
          !mapEquals(version.renderOptions, renderOptions) ||
          jsonEncode(version.deliveryOptions) != jsonEncode(deliveryOptions) ||
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

  Future<Map<String, dynamic>> _runExportTask(
    Map<String, dynamic> input,
    String context,
  ) async {
    final tasks = repository as MediaProjectTaskRepository;
    final random = math.Random.secure();
    final requestId = List.generate(
      16,
      (_) => random.nextInt(256).toRadixString(16).padLeft(2, '0'),
    ).join();
    var response = await tasks.startExportTask(domain, requestId, input);
    while (_acceptContext(context)) {
      final task = response['task'];
      if (response['ok'] != true || task is! Map || task['task_id'] is! int) {
        throw const FormatException('Export task was not registered.');
      }
      _exportTask = Map<String, dynamic>.from(task);
      notifyListeners();
      if (task['status'] == 'completed') {
        final result = task['result'];
        if (result is! Map) {
          throw const FormatException('Export task has no result.');
        }
        return {
          'ok': true,
          'publish_status': result['publish_status'],
          'result': result,
          'evidence_recorded': result['evidence_recorded'],
        };
      }
      if (const [
        'cancelled',
        'interrupted',
        'failed',
      ].contains(task['status'])) {
        throw LumenisCoreException(
          'Export task did not complete.',
          errorCode: task['status'] == 'cancelled'
              ? 'CONTENT_EXPORT_CANCELLED'
              : task['status'] == 'interrupted'
              ? 'CONTENT_EXPORT_INTERRUPTED'
              : 'CONTENT_EXPORT_FAILED',
        );
      }
      if (!const ['pending', 'running', 'canceling'].contains(task['status'])) {
        throw const FormatException('Unknown export task state.');
      }
      await Future<void>.delayed(const Duration(seconds: 1));
      if (!_acceptContext(context)) break;
      response = await tasks.readExportTask(domain, task['task_id'] as int);
    }
    throw const LumenisCoreException(
      'Export context changed.',
      errorCode: 'CONTENT_CONTEXT_CHANGED',
    );
  }

  Future<void> cancelExportTask() async {
    final task = exportTask;
    if (_disposed ||
        _taskActionPending ||
        repository is! MediaProjectTaskRepository ||
        task == null ||
        task['can_cancel'] != true ||
        task['task_id'] is! int) {
      return;
    }
    final context = _contextKey;
    _taskActionPending = true;
    notifyListeners();
    try {
      final response = await (repository as MediaProjectTaskRepository)
          .readExportTask(domain, task['task_id'] as int, action: 'cancel');
      if (_acceptContext(context) && response['task'] is Map) {
        _exportTask = Map<String, dynamic>.from(response['task'] as Map);
      }
    } catch (error) {
      if (_acceptContext(context)) _capture(error);
    } finally {
      _taskActionPending = false;
      if (!_disposed) notifyListeners();
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
      _deliveryOptions = version.deliveryOptions;
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
