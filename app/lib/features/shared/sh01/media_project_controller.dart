import 'dart:convert';

import 'package:flutter/foundation.dart';

import '../../../core/lumenis_core_client.dart';
import 'media_project_snapshot.dart';

abstract interface class MediaProjectRepository {
  String get contextKey;
  Future<List<MediaProjectAsset>> inspect(String domain, List<String> paths);
  Future<List<MediaProjectAsset>> inspectReferences(
    String domain,
    List<String> refs,
  );
  Future<Map<String, dynamic>> importFile(
    String domain,
    String filename,
    Uint8List bytes,
  );
  Future<Map<String, dynamic>> confirmImport(
    String domain,
    String confirmationId, {
    required bool confirmed,
  });
  Future<Map<String, dynamic>> export({
    required String domain,
    required List<String> paths,
    required MediaProjectSnapshot timeline,
    required String outputKind,
    List<String>? refs,
    String? previousArtifactId,
  });
  Future<Map<String, dynamic>> reopen(String domain, String artifactId);
}

final class CoreMediaProjectRepository implements MediaProjectRepository {
  const CoreMediaProjectRepository(this.client);
  final LumenisCoreClient client;

  @override
  String get contextKey => jsonEncode(client.currentContextEnvelope);

  @override
  Future<List<MediaProjectAsset>> inspect(
    String domain,
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
    required String domain,
    required List<String> paths,
    required MediaProjectSnapshot timeline,
    required String outputKind,
    List<String>? refs,
    String? previousArtifactId,
  }) => client.exportContentProject(
    domainId: domain,
    assetPaths: refs == null ? paths : null,
    assetRefs: refs,
    timeline: timeline.toJson(),
    outputKind: outputKind,
    previousArtifactId: previousArtifactId,
  );

  @override
  Future<Map<String, dynamic>> reopen(String domain, String artifactId) =>
      client.reopenContentProject(domainId: domain, artifactId: artifactId);

  @override
  Future<List<MediaProjectAsset>> inspectReferences(
    String domain,
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
  Future<Map<String, dynamic>> importFile(
    String domain,
    String filename,
    Uint8List bytes,
  ) => client.importContentSource(
    domainId: domain,
    filename: filename,
    bytes: bytes,
  );

  @override
  Future<Map<String, dynamic>> confirmImport(
    String domain,
    String confirmationId, {
    required bool confirmed,
  }) => client.confirmContentSource(
    domainId: domain,
    confirmationId: confirmationId,
    confirmed: confirmed,
  );
}

enum MediaProjectOperation { idle, importing, inspecting, exporting, reopening }

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
  });

  final String artifactId;
  final Map<String, dynamic> timelineJson;
  final String outputKind;
  final double durationSec;
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
    if (project['schema_version'] != 1 ||
        !const ['video', 'audio'].contains(kind) ||
        timeline is! Map ||
        timeline['version'] is! int ||
        (timeline['version'] as int) < 1 ||
        rights is! Map ||
        rights['state'] != 'unknown' ||
        (rights.containsKey('demo_acknowledged') &&
            rights['demo_acknowledged'] != true) ||
        render['state'] != 'rendered_verified' ||
        render['output_kind'] != kind ||
        duration is! num ||
        !duration.isFinite ||
        duration <= 0 ||
        size is! int ||
        size <= 0 ||
        !RegExp(r'^[0-9a-f]{64}$').hasMatch('${render['media_sha256']}') ||
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
    return MediaProjectVersion._(
      artifactId: artifactId,
      timelineJson: Map<String, dynamic>.unmodifiable(detached),
      outputKind: kind as String,
      durationSec: duration.toDouble(),
      timelineVersion: timeline['version'] as int,
      evidenceRecorded: evidenceRecorded,
      sourceRefs: List<String>.unmodifiable(refs.cast<String>()),
    );
  }
}

/// Presentation state only. Core reauthorizes, fingerprints and renders every
/// export; neither a local edit nor a server response is public publication.
final class MediaProjectController extends ChangeNotifier {
  MediaProjectController({required this.repository, required this.domain}) {
    if (!const ['CTH', 'BMP'].contains(domain)) {
      throw ArgumentError.value(domain, 'domain');
    }
  }

  final MediaProjectRepository repository;
  final String domain;
  MediaProjectSnapshot? _timeline;
  MediaProjectVersion? _version;
  List<String> _paths = const [];
  List<String>? _sourceRefs;
  List<String>? _suspendedSourceRefs;
  bool _sourcesNeedRevalidation = false;
  String? _draftContext;
  String? _failureCode;
  String? _selectedClipId;
  bool _disposed = false;
  bool _completionUnknown = false;
  MediaProjectOperation _operation = MediaProjectOperation.idle;

  MediaProjectSnapshot? get timeline => contextMatches ? _timeline : null;
  MediaProjectVersion? get version => contextMatches ? _version : null;
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
      _timeline != null && _timeline!.version != _version?.timelineVersion;
  bool get contextMatches =>
      _draftContext == null ||
      (_matchesContext(_draftContext!) && !_sourcesNeedRevalidation);

  String get _contextKey => '$domain:${repository.contextKey}';

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

  Future<void> export({required String outputKind}) async {
    if (_disposed || busy || _timeline == null) return;
    if (!contextMatches) {
      _fail('CONTENT_CONTEXT_CHANGED');
      return;
    }
    if (_completionUnknown) {
      _fail('CONTENT_EXPORT_COMPLETION_UNKNOWN');
      return;
    }
    if (_version != null && !hasUnsavedChanges) {
      _fail('CONTENT_PROJECT_NO_CHANGES');
      return;
    }
    _begin(MediaProjectOperation.exporting);
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
      );
      final result = response['result'];
      if (response['ok'] != true ||
          response['publish_status'] != 'not_performed' ||
          result is! Map ||
          result['status'] != 'rendered_staged' ||
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
    _failureCode = null;
    notifyListeners();
    return !_disposed;
  }

  bool _acceptContext(String expected) {
    if (_disposed) return false;
    if (!_matchesContext(expected)) {
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
