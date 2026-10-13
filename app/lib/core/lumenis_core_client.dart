import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/foundation.dart' show kIsWeb;

import 'transport/lumenis_http_transport.dart';

const _configuredCoreBaseUrl = String.fromEnvironment(
  'LUMENIS_CORE_BASE_URL',
  defaultValue: '',
);
const _legacyConfiguredCoreUrl = String.fromEnvironment(
  'LUMENIS_CORE_URL',
  defaultValue: '',
);
const _defaultCoreBaseUrl = 'http://127.0.0.1:8201';

class LumenisCoreException implements Exception {
  const LumenisCoreException(
    this.message, {
    this.statusCode,
    this.messageKey,
    this.errorCode,
    this.sourceConfirmation,
  });

  final String message;
  final int? statusCode;
  final String? messageKey;
  final String? errorCode;
  final ContentSourceConfirmation? sourceConfirmation;

  @override
  String toString() => 'LumenisCoreException: $message';
}

class ContentSourceConfirmation {
  const ContentSourceConfirmation({
    required this.confirmationId,
    required this.resource,
    required this.expiresAt,
    required this.filename,
    required this.sizeBytes,
    required this.bodySha256,
  });

  final String confirmationId;
  final String resource;
  final DateTime expiresAt;
  final String filename;
  final int sizeBytes;
  final String bodySha256;

  static ContentSourceConfirmation? tryParse(Object? value) {
    if (value is! Map) return null;
    final id = value['confirmation_id'];
    final resource = value['resource'];
    final expires = value['expires_at'];
    final filename = value['filename'];
    final size = value['size_bytes'];
    final sha256 = value['body_sha256'];
    final parsedExpiry = expires is String ? DateTime.tryParse(expires) : null;
    if (id is! String ||
        id.isEmpty ||
        id.length > 180 ||
        RegExp(r'[\x00-\x1f]').hasMatch(id) ||
        resource is! String ||
        RegExp(
              r'^content-source-import:v1:[a-f0-9]{64}$',
            ).stringMatch(resource) !=
            resource ||
        parsedExpiry == null ||
        filename is! String ||
        filename.isEmpty ||
        filename.length > 240 ||
        RegExp(r'[\\/:\x00-\x1f]').hasMatch(filename) ||
        size is! int ||
        size <= 0 ||
        size > MediaSourceLimits.maxBytes ||
        sha256 is! String ||
        !RegExp(r'^[a-f0-9]{64}$').hasMatch(sha256)) {
      return null;
    }
    return ContentSourceConfirmation(
      confirmationId: id,
      resource: resource,
      expiresAt: parsedExpiry,
      filename: filename,
      sizeBytes: size,
      bodySha256: sha256,
    );
  }
}

abstract final class MediaSourceLimits {
  static const maxBytes = 128 * 1024 * 1024;
}

class ContentProjectFile {
  const ContentProjectFile({
    required this.bytes,
    required this.filename,
    required this.mediaType,
  });
  final Uint8List bytes;
  final String filename;
  final String mediaType;
}

class LumenisBrowserFrame {
  const LumenisBrowserFrame({
    required this.bytes,
    required this.frameId,
    required this.targetId,
    required this.pageRevision,
    required this.capturedAt,
    required this.width,
    required this.height,
    // Older read-only frame callers may omit server binding metadata. Zero is
    // deliberately invalid so these frames cannot authorize human actions.
    this.viewportWidth = 0,
    this.viewportHeight = 0,
    this.devicePixelRatio = 0,
  });

  final Uint8List bytes;
  final String frameId;
  final String targetId;
  final int pageRevision;
  final DateTime capturedAt;

  /// PNG dimensions in image pixels.
  final int width;
  final int height;

  /// Browser viewport dimensions in CSS pixels, bound by the server to this frame.
  final int viewportWidth;
  final int viewportHeight;
  final double devicePixelRatio;

  LumenisBrowserFrameBinding get binding => LumenisBrowserFrameBinding(
    frameId: frameId,
    targetId: targetId,
    pageRevision: pageRevision,
    viewportWidth: viewportWidth,
    viewportHeight: viewportHeight,
    devicePixelRatio: devicePixelRatio,
  );
}

class LumenisBrowserFrameBinding {
  const LumenisBrowserFrameBinding({
    required this.frameId,
    required this.targetId,
    required this.pageRevision,
    required this.viewportWidth,
    required this.viewportHeight,
    required this.devicePixelRatio,
  });

  final String frameId;
  final String targetId;
  final int pageRevision;
  final int viewportWidth;
  final int viewportHeight;
  final double devicePixelRatio;

  Map<String, Object?> toJson() => {
    'frame_id': frameId,
    'target_id': targetId,
    'page_revision': pageRevision,
    'viewport': {
      'width': viewportWidth,
      'height': viewportHeight,
      'dpr': devicePixelRatio,
    },
  };
}

class LumenisBrowserVisibleLink {
  const LumenisBrowserVisibleLink({
    required this.linkId,
    required this.label,
    required this.destination,
  });

  final String linkId;
  final String label;
  final String destination;
}

class LumenisBrowserVisibleLinkPage {
  const LumenisBrowserVisibleLinkPage({
    required this.frameBinding,
    required this.links,
  });

  final LumenisBrowserFrameBinding frameBinding;
  final List<LumenisBrowserVisibleLink> links;

  factory LumenisBrowserVisibleLinkPage.fromResponse(
    Map<String, dynamic> value, {
    required LumenisBrowserFrameBinding expectedFrameBinding,
  }) {
    final rawBinding = value['frame_binding'];
    final rawLinks = value['links'];
    if (value['ok'] != true ||
        value['ai_used'] != false ||
        !_browserFrameBindingMatches(rawBinding, expectedFrameBinding) ||
        rawLinks is! List ||
        rawLinks.length > 40) {
      throw const FormatException(
        'The visible-link response is not bound to the current page frame.',
      );
    }
    final ids = <String>{};
    final links = <LumenisBrowserVisibleLink>[];
    for (final rawLink in rawLinks) {
      if (rawLink is! Map) {
        throw const FormatException('A visible browser link is malformed.');
      }
      final linkId = rawLink['link_id'];
      final rawLabel = rawLink['label'];
      final destination = rawLink['destination'];
      final label = rawLabel is String ? rawLabel.trim() : '';
      final uri = destination is String
          ? Uri.tryParse(destination.trim())
          : null;
      if (linkId is! String ||
          !RegExp(r'^bl_[A-Za-z0-9_-]{16,64}$').hasMatch(linkId) ||
          !ids.add(linkId) ||
          label.isEmpty ||
          label.runes.length > 160 ||
          RegExp(r'[\x00-\x1f\x7f]').hasMatch(label) ||
          destination is! String ||
          destination.length > 2048 ||
          destination != destination.trim() ||
          RegExp(r'[\x00-\x1f\x7f]').hasMatch(destination) ||
          uri == null ||
          (uri.scheme != 'http' && uri.scheme != 'https') ||
          uri.host.isEmpty ||
          uri.userInfo.isNotEmpty ||
          uri.hasQuery ||
          uri.hasFragment) {
        throw const FormatException('A visible browser link is malformed.');
      }
      links.add(
        LumenisBrowserVisibleLink(
          linkId: linkId,
          label: label,
          destination: uri.toString(),
        ),
      );
    }
    return LumenisBrowserVisibleLinkPage(
      frameBinding: expectedFrameBinding,
      links: List.unmodifiable(links),
    );
  }
}

bool _browserFrameBindingMatches(
  Object? value,
  LumenisBrowserFrameBinding expected,
) {
  if (value is! Map) return false;
  final rawViewport = value['viewport'];
  if (rawViewport is! Map) return false;
  final viewport = expected.toJson()['viewport'] as Map<String, Object?>;
  final expectedJson = expected.toJson();
  return value['frame_id'] == expectedJson['frame_id'] &&
      value['target_id'] == expectedJson['target_id'] &&
      value['page_revision'] == expectedJson['page_revision'] &&
      rawViewport['width'] == viewport['width'] &&
      rawViewport['height'] == viewport['height'] &&
      rawViewport['dpr'] is num &&
      rawViewport['dpr'] == viewport['dpr'];
}

class LumenisCoreClient {
  LumenisCoreClient({String? baseUrl})
    : baseUrl =
          baseUrl ??
          (_configuredCoreBaseUrl.isNotEmpty
              ? _configuredCoreBaseUrl
              : _legacyConfiguredCoreUrl.isNotEmpty
              ? _legacyConfiguredCoreUrl
              : kIsWeb
              ? Uri.base.origin
              : _defaultCoreBaseUrl);

  final String baseUrl;
  Map<String, String> _contextHeaders = const {
    'X-Lumenis-Context-Mode': 'GLOBAL_ALL',
  };
  Map<String, dynamic>? _contextEnvelope;

  /// Last server-returned selection envelope. This is display state only; Core
  /// still reauthorizes each request carrying the focus headers.
  Map<String, dynamic>? get currentContextEnvelope => _contextEnvelope;

  /// Retained for the existing launch lifecycle. The client no longer obtains
  /// or stores Core credentials. Server-owned workspace/session authorization
  /// is checked on every request; this hook cannot create or revoke a session.
  void clearCredentials() {}

  Future<Map<String, dynamic>> runtimeIdentity() =>
      _get('/api/experience/runtime/identity', withContext: false);

  Future<List<Map<String, dynamic>>> subjects() async {
    final payload = await settingsSubjects();
    if (payload['source'] != 'lumenis_subject_registry' ||
        payload['selection_only'] != true) {
      throw const FormatException(
        'Subject Registry selection contract required.',
      );
    }
    final domains = payload['domains'];
    if (domains is! List ||
        !domains.any(
          (domain) =>
              domain is Map &&
              domain['id'] == 'CTH' &&
              domain['product'] == 'CTH',
        )) {
      throw const FormatException(
        'CTH Subject Registry scope was not returned.',
      );
    }
    final raw = payload['subjects'];
    if (raw is! List) {
      throw const FormatException('Subject Registry response is not a list.');
    }
    return raw
        .map((item) {
          if (item is! Map || item['domain_id'] != 'CTH') {
            throw const FormatException(
              'Subject Registry returned a non-CTH row.',
            );
          }
          final subjectId = item['subject_id'];
          final nameZh = item['name_zh'];
          final nameEn = item['name_en'];
          if (subjectId is! String || subjectId.isEmpty) {
            throw const FormatException(
              'Subject Registry row is missing identity.',
            );
          }
          return <String, dynamic>{
            'id': subjectId,
            'subject_id': subjectId,
            'name': nameZh is String && nameZh.isNotEmpty
                ? nameZh
                : nameEn is String
                ? nameEn
                : subjectId,
            'subject_type_name': item['subject_type_name'] is String
                ? item['subject_type_name']
                : '',
            'industry': item['industry'] is String ? item['industry'] : '',
          };
        })
        .toList(growable: false);
  }

  /// Reads the existing account-scoped CTH Subject Registry. A denial is
  /// surfaced to that screen only and does not eject the user from the App.
  Future<Map<String, dynamic>> settingsSubjects({String domainId = 'CTH'}) {
    if (domainId != 'CTH' && domainId != 'BMP') {
      throw ArgumentError.value(domainId, 'domainId');
    }
    return _get(
      '/api/settings/subjects?domain_id=$domainId',
      withContext: false,
    );
  }

  /// Reads the actor-authorized context selection. The returned selection is
  /// not a permission grant; the Core must reauthorize every consumer request.
  Future<Map<String, dynamic>> settingsContext() async {
    final response = await _get('/api/settings/context');
    _acceptContextEnvelope(response);
    return response;
  }

  /// Selects a directory entry for focus. The server rechecks access and the
  /// returned selection is attached to every subsequent business request.
  Future<Map<String, dynamic>> selectContext({
    required String domainId,
    required String subjectId,
  }) async {
    if ((domainId != 'CTH' && domainId != 'BMP') || subjectId.trim().isEmpty) {
      throw ArgumentError('A supported domain and subject are required.');
    }
    final response = await _request(
      'PUT',
      '/api/settings/context',
      payload: {
        'mode': 'FOCUS',
        'domain_id': domainId,
        'subject_id': subjectId,
      },
      withContext: false,
    );
    final context = response['context'];
    if (context is! Map ||
        context['mode'] != 'FOCUS' ||
        context['domain_id'] != domainId ||
        context['subject_id'] != subjectId) {
      throw const FormatException(
        'Core did not confirm the requested context selection.',
      );
    }
    _acceptContextEnvelope(response);
    return response;
  }

  /// Clears focus. GLOBAL_ALL is a view selection only and does not imply
  /// that any data source is complete or that all records are authorized.
  Future<Map<String, dynamic>> clearContext() async {
    final response = await _request(
      'DELETE',
      '/api/settings/context',
      withContext: false,
    );
    final context = response['context'];
    if (context is! Map || context['mode'] != 'GLOBAL_ALL') {
      throw const FormatException('Core did not confirm clearing the focus.');
    }
    _acceptContextEnvelope(response);
    return response;
  }

  void _acceptContextEnvelope(Map<String, dynamic> response) {
    if (response['ok'] != true ||
        response['contract'] != 'lumenis.context.v1' ||
        response['selection_only'] != true) {
      throw const FormatException(
        'Invalid LUMENIS context selection contract.',
      );
    }
    final rawContext = response['context'];
    if (rawContext is! Map) {
      throw const FormatException('Context selection was not returned.');
    }
    final mode = rawContext['mode'];
    if (mode == 'GLOBAL_ALL') {
      if (rawContext['subject_id'] != null) {
        throw const FormatException('Global context cannot name a subject.');
      }
      _contextHeaders = const {'X-Lumenis-Context-Mode': 'GLOBAL_ALL'};
    } else if (mode == 'FOCUS') {
      final domainId = rawContext['domain_id'];
      final subjectId = rawContext['subject_id'];
      if ((domainId != 'CTH' && domainId != 'BMP') ||
          subjectId is! String ||
          subjectId.trim().isEmpty) {
        throw const FormatException('Focused context is incomplete.');
      }
      _contextHeaders = {
        'X-Lumenis-Context-Mode': 'FOCUS',
        'X-Domain-Id': domainId as String,
        'X-Subject-ID': subjectId,
      };
    } else {
      throw const FormatException('Unknown context selection mode.');
    }
    _contextEnvelope = response;
  }

  Future<Map<String, dynamic>> sharedSkillsCatalog() =>
      _get('/api/experience/shared-skills');

  Future<Map<String, dynamic>> contentEvidence(String evidenceId) => _get(
    '/api/experience/content/evidence/${Uri.encodeComponent(evidenceId)}',
  );

  Future<Map<String, dynamic>> screen(String screenId) =>
      _get('/api/experience/screen/${Uri.encodeComponent(screenId)}');

  /// AI-01 intent submission. Only the task text and the low-risk `ANALYZE`
  /// action are sent: the actor, domain, product and skill are never supplied
  /// by the client (the server's PermissionGate owns them). The timeout covers
  /// the whole synchronous execution; an elapsed timeout means the outcome is
  /// unknown and the caller must not resubmit automatically.
  Future<Map<String, dynamic>> submitAiIntent({required String task}) {
    return _request(
      'POST',
      '/api/experience/ai/intent',
      payload: {'task': task, 'action_type': 'ANALYZE'},
      connectionTimeout: const Duration(minutes: 2),
    );
  }

  Future<Map<String, dynamic>> startSourceBriefTask({
    required String domainId,
    int limit = 30,
    String? businessQuestion,
  }) {
    final questionPayload = businessQuestion == null
        ? null
        : <String, Object?>{'business_question': businessQuestion};
    return _request(
      'POST',
      '/api/experience/reports/source-brief/start',
      operationContext: _contentContext(domainId),
      payload: {'limit': limit, ...?questionPayload},
    );
  }

  Future<Map<String, dynamic>> sourceBriefTask({
    required String domainId,
    required String taskId,
  }) {
    _validateSourceBriefTaskId(taskId);
    return _request(
      'GET',
      '/api/experience/reports/source-brief/tasks/${Uri.encodeComponent(taskId)}',
      operationContext: _contentContext(domainId),
    );
  }

  Future<Map<String, dynamic>> resumeSourceBriefTask({
    required String domainId,
    required String taskId,
  }) {
    _validateSourceBriefTaskId(taskId);
    return _request(
      'POST',
      '/api/experience/reports/source-brief/tasks/${Uri.encodeComponent(taskId)}/resume',
      operationContext: _contentContext(domainId),
      payload: const <String, Object?>{},
    );
  }

  Future<Map<String, dynamic>> sourceBriefJob({
    required String domainId,
    required String jobId,
  }) {
    _validateSourceBriefJobId(jobId);
    return _request(
      'GET',
      '/api/experience/reports/source-brief/jobs/${Uri.encodeComponent(jobId)}',
      operationContext: _contentContext(domainId),
      connectionTimeout: const Duration(seconds: 30),
    );
  }

  static void _validateSourceBriefTaskId(String value) {
    if (!RegExp(
      r'^rbrief_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
    ).hasMatch(value)) {
      throw const FormatException('Invalid source brief task identifier.');
    }
  }

  Future<Map<String, dynamic>> createSourceStatistics({
    required String domainId,
    required String jobId,
  }) {
    _validateSourceBriefJobId(jobId);
    return _request(
      'POST',
      '/api/ai/tasks',
      operationContext: _contentContext(domainId),
      payload: {
        'input': '统计已保存来源的发布时间与平台分布',
        'context': {
          'analysis_operation': 'source_statistics',
          'source_brief_job_id': jobId,
        },
      },
    );
  }

  Future<Map<String, dynamic>> sourceStatisticsTask({
    required String domainId,
    required String taskId,
    bool run = false,
  }) {
    if (!RegExp(r'^task_[0-9a-f]{16}$').hasMatch(taskId)) {
      throw const FormatException('Invalid source statistics task identifier.');
    }
    return _request(
      run ? 'POST' : 'GET',
      '/api/ai/tasks/${Uri.encodeComponent(taskId)}${run ? '/run' : ''}',
      operationContext: _contentContext(domainId),
      payload: run ? const <String, Object?>{} : null,
      // Execution includes source/Permission revalidation and Artifact commit.
      // A lost acknowledgement is recovered through the same task identifier.
      connectionTimeout: run
          ? const Duration(seconds: 60)
          : const Duration(seconds: 30),
    );
  }

  static void _validateSourceBriefJobId(String value) {
    if (!RegExp(r'^[A-Za-z0-9][A-Za-z0-9_-]{7,127}$').hasMatch(value)) {
      throw const FormatException('Invalid source brief job identifier.');
    }
  }

  /// Media actions use canonical focus when selected. GLOBAL_ALL still needs
  /// an explicit invoking domain; it never supplies a subject or focus grant.
  Map<String, String> _contentContext(String domainId) {
    final domain = domainId.trim().toUpperCase();
    if (domain != 'CTH' && domain != 'BMP') {
      throw const FormatException('A CTH or BMP creation context is required.');
    }
    final mode = _contextHeaders['X-Lumenis-Context-Mode'];
    if (mode == 'FOCUS' && _contextHeaders['X-Domain-Id'] != domain) {
      throw const LumenisCoreException(
        'The selected domain conflicts with the focused workspace context.',
        errorCode: 'CONTENT_CONTEXT_MISMATCH',
      );
    }
    if (mode != 'FOCUS' && mode != 'GLOBAL_ALL') {
      throw const LumenisCoreException(
        'A recognized workspace context is required before using media actions.',
        errorCode: 'CONTENT_CONTEXT_REQUIRED',
      );
    }
    return {
      ..._contextHeaders,
      if (mode == 'GLOBAL_ALL') 'X-Domain-Id': domain,
      'X-Product-Id': domain == 'BMP' ? 'ZBMP' : 'CTH',
    };
  }

  Future<Map<String, dynamic>> inspectContentMedia({
    required String domainId,
    List<String>? assetPaths,
    List<String>? assetRefs,
  }) => _request(
    'POST',
    '/api/experience/shared-skills/shared.content_project/inspect',
    operationContext: _contentContext(domainId),
    payload: {
      'action_type': 'READ',
      'input': _contentAssets(assetPaths, assetRefs),
    },
  );

  Future<Map<String, dynamic>> exportContentProject({
    required String domainId,
    List<String>? assetPaths,
    List<String>? assetRefs,
    required Map<String, dynamic> timeline,
    required String outputKind,
    bool? demoAcknowledged,
    String? previousArtifactId,
  }) {
    if (outputKind != 'video' && outputKind != 'audio') {
      throw const FormatException('Unsupported content output kind.');
    }
    if (previousArtifactId != null) {
      _validateContentArtifactId(previousArtifactId);
    }
    return _request(
      'POST',
      '/api/experience/content-projects/export',
      operationContext: _contentContext(domainId),
      connectionTimeout: const Duration(minutes: 5),
      payload: {
        'action_type': 'EXPORT',
        'input': {
          ..._contentAssets(assetPaths, assetRefs),
          'timeline': timeline,
          'output_kind': outputKind,
          'demo_acknowledged': ?demoAcknowledged,
          'previous_artifact_id': previousArtifactId,
        },
      },
    ).timeout(
      const Duration(minutes: 5),
      onTimeout: () => throw const LumenisCoreException(
        'Export response timed out; server completion is unknown.',
        errorCode: 'CONTENT_EXPORT_TIMEOUT',
      ),
    );
  }

  Future<Map<String, dynamic>> listContentProjects({
    required String domainId,
    int limit = 20,
    String? cursor,
  }) {
    if (limit < 1 || limit > 20) {
      throw ArgumentError.value(limit, 'limit');
    }
    if (cursor != null && !RegExp(r'^[A-Za-z0-9_-]{40,48}$').hasMatch(cursor)) {
      throw const FormatException('Invalid saved-project cursor.');
    }
    final query = Uri(
      queryParameters: {'limit': '$limit', 'cursor': ?cursor},
    ).query;
    return _request(
      'GET',
      '/api/experience/content-projects?$query',
      operationContext: _contentContext(domainId),
    );
  }

  Future<Map<String, dynamic>> reopenContentProject({
    required String domainId,
    required String artifactId,
  }) {
    _validateContentArtifactId(artifactId);
    return _request(
      'GET',
      '/api/experience/content-projects/$artifactId',
      operationContext: _contentContext(domainId),
    );
  }

  static void _validateContentArtifactId(String value) {
    if (!RegExp(r'^ART-[A-Za-z0-9_-]{1,70}$').hasMatch(value)) {
      throw const FormatException('Invalid content project identifier.');
    }
  }

  static Map<String, Object?> _contentAssets(
    List<String>? paths,
    List<String>? refs,
  ) {
    if ((paths == null) == (refs == null)) {
      throw const FormatException(
        'Exactly one media source input is required.',
      );
    }
    if (refs != null) {
      for (final ref in refs) {
        _validateContentArtifactId(ref);
      }
      return {'asset_refs': refs};
    }
    return {'asset_paths': paths};
  }

  Future<Map<String, dynamic>> importContentSource({
    required String domainId,
    required String filename,
    required Uint8List bytes,
  }) {
    if (filename.isEmpty ||
        filename.length > 240 ||
        RegExp(r'[\\/:\x00-\x1f]').hasMatch(filename) ||
        bytes.isEmpty ||
        bytes.length > MediaSourceLimits.maxBytes) {
      throw const FormatException('Invalid media file input.');
    }
    return _request(
      'POST',
      '/api/experience/content-sources?filename=${Uri.encodeQueryComponent(filename)}',
      operationContext: _contentContext(domainId),
      connectionTimeout: const Duration(minutes: 4),
      binaryBody: bytes,
      requestHeaders: const {'X-Lumenis-Action': 'WRITE'},
    ).timeout(
      const Duration(minutes: 4),
      onTimeout: () => throw const LumenisCoreException(
        'Import response timed out; server completion is unknown.',
        errorCode: 'CONTENT_IMPORT_TIMEOUT',
      ),
    );
  }

  Future<Map<String, dynamic>> confirmContentSource({
    required String domainId,
    required String confirmationId,
    required bool confirmed,
  }) {
    if (confirmationId.isEmpty ||
        confirmationId.length > 180 ||
        RegExp(r'[\\/\x00-\x1f]').hasMatch(confirmationId)) {
      throw const FormatException('Invalid source confirmation identifier.');
    }
    return _request(
      'POST',
      '/api/experience/content-source-confirmations/${Uri.encodeComponent(confirmationId)}',
      operationContext: _contentContext(domainId),
      payload: {'confirmed': confirmed},
    );
  }

  Future<ContentProjectFile> contentProjectFile({
    required String domainId,
    required String artifactId,
    required bool package,
  }) async {
    _validateContentArtifactId(artifactId);
    final context = _contentContext(domainId);
    final uri = _uri(
      '/api/experience/content-projects/$artifactId/${package ? 'package' : 'media'}',
    );
    try {
      final response = await sendLumenisBinaryRequest(
        LumenisTransportRequest(
          method: 'GET',
          uri: uri,
          headers: {
            ...context,
            'Accept': package ? 'application/zip' : 'video/mp4, audio/wav',
          },
          connectionTimeout: const Duration(minutes: 2),
          followRedirects: false,
        ),
        maxBytes: 512 * 1024 * 1024,
      );
      if (response.statusCode != 200) {
        throw LumenisCoreException(
          'Content file was not returned.',
          statusCode: response.statusCode,
        );
      }
      final type = response.contentType?.split(';').first.trim().toLowerCase();
      final extension = switch (type) {
        'application/zip' when package => 'zip',
        'video/mp4' when !package => 'mp4',
        'audio/wav' when !package => 'wav',
        _ => null,
      };
      if (extension == null || response.bytes.isEmpty) {
        throw const FormatException(
          'Content file type does not match the requested artifact.',
        );
      }
      return ContentProjectFile(
        bytes: response.bytes,
        filename: '$artifactId.$extension',
        mediaType: type!,
      );
    } on LumenisTransportException {
      throw const LumenisCoreException(
        'Content file retrieval is unavailable.',
        errorCode: 'CONTENT_FILE_UNAVAILABLE',
      );
    }
  }

  /// Browser sessions use the server-issued open-workspace principal.
  ///
  /// This deliberately omits the development Basic credential and all business
  /// context headers.  The Browser API accepts it only on the explicitly open,
  /// loopback workspace transport and refuses forged identity headers, cookies
  /// and remote origins.  A client credential must never become a substitute
  /// for a Browser actor/session boundary.
  /// Optional manual collection for the selected scope. Automatic
  /// collection of every registered subject stays the default; this only
  /// queues one human-confirmed read-only run in the system background.
  Future<Map<String, dynamic>> startManualCollection() => _request(
    'POST',
    '/api/collect',
    payload: const <String, Object?>{
      'operator': 'human_ui',
      'confirm_read_only': true,
    },
  );

  Future<Map<String, dynamic>> openBrowserSession() {
    _requireLocalBrowserEndpoint();
    return _request(
      'POST',
      '/api/browser/sessions',
      payload: const <String, Object?>{},
      withContext: false,
    );
  }

  Future<Map<String, dynamic>> browserSession(String sessionId) {
    _validateBrowserSessionId(sessionId);
    _requireLocalBrowserEndpoint();
    return _request(
      'GET',
      '/api/browser/sessions/${Uri.encodeComponent(sessionId)}',
      withContext: false,
    );
  }

  /// Reads the existing Shared SavedWork registry for Browser-authored notes.
  /// The server still resolves and authorizes the actor and exact CTH/BMP scope.
  Future<Map<String, dynamic>> listBrowserResearchNotes({
    required String domainId,
    int limit = 100,
    String? cursor,
  }) {
    if (limit < 1 || limit > 100) {
      throw ArgumentError.value(limit, 'limit');
    }
    if (cursor != null &&
        (cursor.isEmpty ||
            cursor.length > 4096 ||
            RegExp(r'[\x00-\x1f\x7f]').hasMatch(cursor))) {
      throw const FormatException('Invalid SavedWork cursor.');
    }
    final queryParameters = <String, String>{
      'kind': 'research',
      'limit': '$limit',
    };
    if (cursor != null) queryParameters['cursor'] = cursor;
    final query = Uri(queryParameters: queryParameters).query;
    return _request(
      'GET',
      '/api/experience/saved-work?$query',
      operationContext: _contentContext(domainId),
      requestHeaders: const {'Cache-Control': 'no-store'},
    );
  }

  Future<Map<String, dynamic>> saveBrowserResearchNote({
    required String domainId,
    required String title,
    required String markdown,
    required Map<String, Object?> payload,
    required String requestId,
  }) {
    _validateSavedWorkRequestId(requestId);
    return _request(
      'POST',
      '/api/experience/saved-work',
      operationContext: _contentContext(domainId),
      requestHeaders: const {'Cache-Control': 'no-store'},
      payload: {
        'title': title,
        'markdown': markdown,
        'kind': 'research',
        'payload': payload,
        'citations': const <Object?>[],
        'request_id': requestId,
      },
    );
  }

  Future<Map<String, dynamic>> reopenBrowserResearchNote({
    required String domainId,
    required String artifactId,
  }) {
    _validateSavedWorkArtifactId(artifactId);
    return _request(
      'GET',
      '/api/experience/saved-work/$artifactId',
      operationContext: _contentContext(domainId),
      requestHeaders: const {'Cache-Control': 'no-store'},
    );
  }

  Future<Map<String, dynamic>> reviseBrowserResearchNote({
    required String domainId,
    required String artifactId,
    required String requestId,
    required String expectedSha256,
    required String reason,
    required String expectedTitle,
    required String title,
    required String expectedMarkdown,
    required String markdown,
  }) {
    _validateSavedWorkArtifactId(artifactId);
    _validateSavedWorkRequestId(requestId);
    if (!RegExp(r'^[0-9a-f]{64}$').hasMatch(expectedSha256)) {
      throw const FormatException('Invalid SavedWork version digest.');
    }
    return _request(
      'POST',
      '/api/experience/saved-work/$artifactId/revise',
      operationContext: _contentContext(domainId),
      requestHeaders: const {'Cache-Control': 'no-store'},
      payload: {
        'request_id': requestId,
        'expected_sha256': expectedSha256,
        'reason': reason,
        'edits': [
          {'pointer': '/title', 'expected': expectedTitle, 'value': title},
          {
            'pointer': '/markdown',
            'expected': expectedMarkdown,
            'value': markdown,
          },
        ],
      },
    );
  }

  static void _validateSavedWorkArtifactId(String value) {
    if (!RegExp(r'^ART-[0-9a-f]{16}$').hasMatch(value)) {
      throw const FormatException('Invalid SavedWork artifact identifier.');
    }
  }

  static void _validateSavedWorkRequestId(String value) {
    if (!RegExp(r'^[A-Za-z0-9_-]{8,128}$').hasMatch(value)) {
      throw const FormatException('Invalid SavedWork request identifier.');
    }
  }

  Future<Map<String, dynamic>> navigateBrowserSession({
    required String sessionId,
    required String url,
  }) {
    _validateBrowserSessionId(sessionId);
    _validateBrowserUrl(url);
    _requireLocalBrowserEndpoint();
    return _request(
      'POST',
      '/api/browser/sessions/${Uri.encodeComponent(sessionId)}/navigate',
      payload: <String, Object?>{'url': url},
      withContext: false,
      connectionTimeout: const Duration(seconds: 20),
    );
  }

  Future<Map<String, dynamic>> reloadBrowserSession(String sessionId) {
    _validateBrowserSessionId(sessionId);
    _requireLocalBrowserEndpoint();
    return _request(
      'POST',
      '/api/browser/sessions/${Uri.encodeComponent(sessionId)}/action',
      payload: const <String, Object?>{'action': 'reload'},
      withContext: false,
      connectionTimeout: const Duration(seconds: 20),
    );
  }

  Future<Map<String, dynamic>> stopBrowserSession(String sessionId) {
    _validateBrowserSessionId(sessionId);
    _requireLocalBrowserEndpoint();
    return _request(
      'POST',
      '/api/browser/sessions/${Uri.encodeComponent(sessionId)}/stop',
      payload: const <String, Object?>{},
      withContext: false,
    );
  }

  /// Acquire the server-owned, exclusive human lease for this session.
  /// The bearer token is returned once and must remain in memory only.
  Future<Map<String, dynamic>> acquireBrowserHumanControl(String sessionId) {
    _validateBrowserSessionId(sessionId);
    _requireLocalBrowserEndpoint();
    return _request(
      'POST',
      '/api/browser/sessions/${Uri.encodeComponent(sessionId)}/human-control/acquire',
      payload: const <String, Object?>{},
      withContext: false,
      requestHeaders: const {'Cache-Control': 'no-store'},
      connectionTimeout: const Duration(seconds: 20),
    );
  }

  Future<Map<String, dynamic>> releaseBrowserHumanControl({
    required String sessionId,
    required String leaseToken,
  }) {
    _validateBrowserSessionId(sessionId);
    _validateBrowserLeaseToken(leaseToken);
    _requireLocalBrowserEndpoint();
    return _request(
      'POST',
      '/api/browser/sessions/${Uri.encodeComponent(sessionId)}/human-control/release',
      payload: const <String, Object?>{},
      withContext: false,
      requestHeaders: {
        'Cache-Control': 'no-store',
        'X-LUMENIS-Human-Control-Lease': leaseToken,
      },
      connectionTimeout: const Duration(seconds: 20),
    );
  }

  Future<Map<String, dynamic>> navigateBrowserSessionWithHumanControl({
    required String sessionId,
    required String url,
    required String leaseToken,
    required LumenisBrowserFrameBinding frameBinding,
  }) {
    _validateBrowserSessionId(sessionId);
    _validateBrowserLeaseToken(leaseToken);
    _validateBrowserUrl(url);
    _requireLocalBrowserEndpoint();
    return _request(
      'POST',
      '/api/browser/sessions/${Uri.encodeComponent(sessionId)}/human-control/navigate',
      payload: <String, Object?>{
        'url': url,
        'frame_binding': frameBinding.toJson(),
      },
      withContext: false,
      requestHeaders: {
        'Cache-Control': 'no-store',
        'X-LUMENIS-Human-Control-Lease': leaseToken,
      },
      connectionTimeout: const Duration(seconds: 20),
    );
  }

  /// Calls only existing human-safe actions exposed by the server capability.
  /// This client intentionally has no coordinate, upload, download or stop action.
  Future<Map<String, dynamic>> executeBrowserHumanAction({
    required String sessionId,
    required String action,
    required String leaseToken,
    required LumenisBrowserFrameBinding frameBinding,
    String value = '',
  }) {
    _validateBrowserSessionId(sessionId);
    _validateBrowserLeaseToken(leaseToken);
    if (!const {'back', 'forward', 'reload', 'scroll'}.contains(action)) {
      throw const FormatException('Unsupported human browser action.');
    }
    if (action == 'scroll') {
      final delta = int.tryParse(value);
      if (delta == null || delta == 0 || delta.abs() > 2000) {
        throw const FormatException('Human scroll distance is invalid.');
      }
    }
    _requireLocalBrowserEndpoint();
    return _request(
      'POST',
      '/api/browser/sessions/${Uri.encodeComponent(sessionId)}/human-control/action',
      payload: <String, Object?>{
        'action': action,
        if (action == 'scroll') 'value': value,
        'frame_binding': frameBinding.toJson(),
      },
      withContext: false,
      requestHeaders: {
        'Cache-Control': 'no-store',
        'X-LUMENIS-Human-Control-Lease': leaseToken,
      },
      connectionTimeout: const Duration(seconds: 20),
    );
  }

  Future<LumenisBrowserVisibleLinkPage> browserHumanVisibleLinks({
    required String sessionId,
    required String leaseToken,
    required LumenisBrowserFrameBinding frameBinding,
  }) async {
    _validateBrowserSessionId(sessionId);
    _validateBrowserLeaseToken(leaseToken);
    _requireLocalBrowserEndpoint();
    final response = await _request(
      'POST',
      '/api/browser/sessions/${Uri.encodeComponent(sessionId)}/human-control/links',
      payload: <String, Object?>{'frame_binding': frameBinding.toJson()},
      withContext: false,
      requestHeaders: {
        'Cache-Control': 'no-store',
        'X-LUMENIS-Human-Control-Lease': leaseToken,
      },
      connectionTimeout: const Duration(seconds: 20),
    );
    return LumenisBrowserVisibleLinkPage.fromResponse(
      response,
      expectedFrameBinding: frameBinding,
    );
  }

  Future<Map<String, dynamic>> openBrowserHumanVisibleLink({
    required String sessionId,
    required String leaseToken,
    required String linkId,
    required LumenisBrowserFrameBinding frameBinding,
  }) {
    _validateBrowserSessionId(sessionId);
    _validateBrowserLeaseToken(leaseToken);
    if (!RegExp(r'^bl_[A-Za-z0-9_-]{16,64}$').hasMatch(linkId)) {
      throw const FormatException('Invalid server-issued browser link ID.');
    }
    _requireLocalBrowserEndpoint();
    return _request(
      'POST',
      '/api/browser/sessions/${Uri.encodeComponent(sessionId)}/human-control/open-link',
      payload: <String, Object?>{
        'frame_binding': frameBinding.toJson(),
        'link_id': linkId,
      },
      withContext: false,
      requestHeaders: {
        'Cache-Control': 'no-store',
        'X-LUMENIS-Human-Control-Lease': leaseToken,
      },
      connectionTimeout: const Duration(seconds: 20),
    );
  }

  Future<LumenisBrowserFrame> browserFrame(String sessionId) async {
    _validateBrowserSessionId(sessionId);
    _requireLocalBrowserEndpoint();
    final uri = _uri(
      '/api/browser/sessions/${Uri.encodeComponent(sessionId)}/frame',
    );
    try {
      final response = await sendLumenisBinaryRequest(
        LumenisTransportRequest(
          method: 'GET',
          uri: uri,
          headers: <String, String>{'Accept': 'image/png, application/json'},
          connectionTimeout: const Duration(seconds: 20),
          followRedirects: false,
        ),
        maxBytes: 16 * 1024 * 1024,
      );
      if (response.statusCode != 200) {
        throw _browserFrameFailure(response);
      }
      final contentType = response.contentType
          ?.split(';')
          .first
          .trim()
          .toLowerCase();
      if (contentType != 'image/png' ||
          response.bytes.length < 24 ||
          response.bytes[0] != 0x89 ||
          response.bytes[1] != 0x50 ||
          response.bytes[2] != 0x4e ||
          response.bytes[3] != 0x47) {
        throw const FormatException('Browser frame is not a PNG image.');
      }
      final frameId = response.headers['x-lumenis-frame-id'];
      final targetId = response.headers['x-lumenis-target-id'];
      final revision = int.tryParse(
        response.headers['x-lumenis-page-revision'] ?? '',
      );
      final capturedAt = DateTime.tryParse(
        response.headers['x-lumenis-captured-at'] ?? '',
      );
      final width = int.tryParse(
        response.headers['x-lumenis-frame-width'] ?? '',
      );
      final height = int.tryParse(
        response.headers['x-lumenis-frame-height'] ?? '',
      );
      final viewportWidth = int.tryParse(
        response.headers['x-lumenis-viewport-width'] ?? '',
      );
      final viewportHeight = int.tryParse(
        response.headers['x-lumenis-viewport-height'] ?? '',
      );
      final devicePixelRatio = double.tryParse(
        response.headers['x-lumenis-viewport-dpr'] ?? '',
      );
      if (!_isOpaqueBrowserId(frameId) ||
          !_isOpaqueBrowserId(targetId) ||
          revision == null ||
          revision < 0 ||
          capturedAt == null ||
          width == null ||
          height == null ||
          width < 1 ||
          height < 1 ||
          width > 16384 ||
          height > 16384 ||
          viewportWidth == null ||
          viewportHeight == null ||
          viewportWidth < 1 ||
          viewportHeight < 1 ||
          viewportWidth > 16384 ||
          viewportHeight > 16384 ||
          devicePixelRatio == null ||
          !devicePixelRatio.isFinite ||
          devicePixelRatio <= 0 ||
          devicePixelRatio > 16) {
        throw const FormatException('Browser frame metadata is invalid.');
      }
      return LumenisBrowserFrame(
        bytes: response.bytes,
        frameId: frameId!,
        targetId: targetId!,
        pageRevision: revision,
        capturedAt: capturedAt.toUtc(),
        width: width,
        height: height,
        viewportWidth: viewportWidth,
        viewportHeight: viewportHeight,
        devicePixelRatio: devicePixelRatio,
      );
    } on LumenisTransportException {
      throw const LumenisCoreException(
        'Browser frame retrieval is unavailable.',
        errorCode: 'BROWSER_FRAME_UNAVAILABLE',
      );
    }
  }

  /// Live frames of an authorized local browser session (SSE).  Frames are
  /// only displayed; the server never stores them or sends them to AI.
  Stream<LumenisBrowserFrame> browserFrameStream(String sessionId) async* {
    _validateBrowserSessionId(sessionId);
    _requireLocalBrowserEndpoint();
    final uri = _uri(
      '/api/browser/sessions/${Uri.encodeComponent(sessionId)}/frames/stream',
    );
    try {
      await for (final data in openLumenisEventStream(
        LumenisTransportRequest(
          method: 'GET',
          uri: uri,
          headers: <String, String>{'Accept': 'text/event-stream'},
          connectionTimeout: const Duration(seconds: 20),
          followRedirects: false,
        ),
        maxEventBytes: 24 * 1024 * 1024,
      )) {
        final frame = parseBrowserStreamEvent(data);
        if (frame != null) yield frame;
      }
    } on LumenisTransportException {
      throw const LumenisCoreException(
        'Browser frame stream is unavailable.',
        errorCode: 'BROWSER_FRAME_STREAM_UNAVAILABLE',
      );
    }
  }

  /// Parses one SSE `data:` payload; returns null for non-frame events.
  static LumenisBrowserFrame? parseBrowserStreamEvent(String data) {
    final decoded = jsonDecode(data);
    if (decoded is! Map || decoded['t'] != 'frame') return null;
    final frameId = decoded['frame_id'];
    final targetId = decoded['target_id'];
    final revision = decoded['page_revision'];
    final capturedAt = decoded['captured_at'] is String
        ? DateTime.tryParse(decoded['captured_at'] as String)
        : null;
    final width = decoded['width'];
    final height = decoded['height'];
    final viewport = decoded['viewport'];
    final payload = decoded['data'];
    if (decoded['mime'] != 'image/png' ||
        frameId is! String ||
        !_isOpaqueBrowserId(frameId) ||
        targetId is! String ||
        !_isOpaqueBrowserId(targetId) ||
        revision is! int ||
        revision < 0 ||
        capturedAt == null ||
        width is! int ||
        height is! int ||
        width < 1 ||
        height < 1 ||
        width > 16384 ||
        height > 16384 ||
        viewport is! Map ||
        payload is! String) {
      throw const FormatException('Browser stream frame metadata is invalid.');
    }
    final viewportWidth = viewport['width'];
    final viewportHeight = viewport['height'];
    final dpr = viewport['dpr'];
    if (viewportWidth is! int ||
        viewportHeight is! int ||
        viewportWidth < 1 ||
        viewportHeight < 1 ||
        viewportWidth > 16384 ||
        viewportHeight > 16384 ||
        dpr is! num ||
        !dpr.isFinite ||
        dpr <= 0 ||
        dpr > 16) {
      throw const FormatException('Browser stream viewport is invalid.');
    }
    final bytes = base64Decode(payload);
    if (bytes.length < 24 ||
        bytes[0] != 0x89 ||
        bytes[1] != 0x50 ||
        bytes[2] != 0x4e ||
        bytes[3] != 0x47) {
      throw const FormatException('Browser stream frame is not a PNG image.');
    }
    return LumenisBrowserFrame(
      bytes: bytes,
      frameId: frameId,
      targetId: targetId,
      pageRevision: revision,
      capturedAt: capturedAt.toUtc(),
      width: width,
      height: height,
      viewportWidth: viewportWidth,
      viewportHeight: viewportHeight,
      devicePixelRatio: dpr.toDouble(),
    );
  }

  static bool _isOpaqueBrowserId(String? value) =>
      value != null && RegExp(r'^[A-Za-z0-9_-]{1,180}$').hasMatch(value);

  void _requireLocalBrowserEndpoint() {
    if (!_isLoopback(_uri('/api/browser/sessions'))) {
      throw const LumenisCoreException(
        'Controlled browser access is available only through local LUMENIS Core.',
        errorCode: 'BROWSER_LOCAL_CORE_REQUIRED',
      );
    }
  }

  static void _validateBrowserSessionId(String value) {
    if (!RegExp(r'^bs_[a-f0-9]{12}$').hasMatch(value)) {
      throw const FormatException('Invalid browser session identifier.');
    }
  }

  static void _validateBrowserLeaseToken(String value) {
    if (!RegExp(r'^[A-Za-z0-9_-]{16,256}$').hasMatch(value)) {
      throw const FormatException('Invalid browser control lease.');
    }
  }

  static void _validateBrowserUrl(String value) {
    final uri = Uri.tryParse(value.trim());
    if (uri == null ||
        uri.host.isEmpty ||
        (uri.scheme != 'https' && uri.scheme != 'http') ||
        value.length > 4096 ||
        RegExp(r'[\x00-\x1f]').hasMatch(value)) {
      throw const FormatException('Invalid browser address.');
    }
  }

  static LumenisCoreException _browserFrameFailure(
    LumenisBinaryTransportResponse response,
  ) {
    String? code;
    try {
      final body = jsonDecode(utf8.decode(response.bytes));
      if (body is Map && body['error_code'] is String) {
        final candidate = body['error_code'] as String;
        if (RegExp(r'^[A-Z][A-Z_0-9]{0,99}$').hasMatch(candidate)) {
          code = candidate;
        }
      }
    } on FormatException {
      // A malformed error body never becomes a successful browser frame.
    }
    return LumenisCoreException(
      'Browser frame was not returned.',
      statusCode: response.statusCode,
      errorCode: code,
    );
  }

  Future<Map<String, dynamic>> _get(String path, {bool withContext = true}) =>
      _request('GET', path, withContext: withContext);

  Future<Map<String, dynamic>> _request(
    String method,
    String path, {
    Map<String, Object?>? payload,
    bool withContext = true,
    Map<String, String>? operationContext,
    Duration connectionTimeout = const Duration(seconds: 8),
    Uint8List? binaryBody,
    Map<String, String> requestHeaders = const {},
  }) async {
    if (payload != null && binaryBody != null) {
      throw const FormatException('Only one request body is allowed.');
    }
    final uri = _uri(path);

    try {
      final headers = <String, String>{
        'Accept': 'application/json',
        ...requestHeaders,
      };
      if (withContext) {
        headers.addAll(operationContext ?? _contextHeaders);
      }
      String? requestBody;
      if (payload != null) {
        headers['Content-Type'] = 'application/json; charset=utf-8';
        requestBody = jsonEncode(payload);
      }
      if (binaryBody != null) {
        headers['Content-Type'] = 'application/octet-stream';
      }
      final reply = await sendLumenisHttpRequest(
        LumenisTransportRequest(
          method: method,
          uri: uri,
          headers: headers,
          body: requestBody,
          bodyBytes: binaryBody,
          connectionTimeout: connectionTimeout,
          // Core redirects are a deployment/configuration error. Following
          // them could forward the current Subject/BrandFocus headers to a
          // different origin, so every Product Core request fails closed.
          followRedirects: false,
        ),
      );
      if (reply.statusCode < 200 || reply.statusCode >= 300) {
        String? messageKey;
        String? errorCode;
        ContentSourceConfirmation? sourceConfirmation;
        try {
          final errorBody = jsonDecode(reply.body);
          if (errorBody is Map && errorBody['message_key'] is String) {
            messageKey = errorBody['message_key'] as String;
          }
          if (errorBody is Map &&
              (errorBody['code'] is String ||
                  errorBody['error_code'] is String)) {
            final code =
                (errorBody['code'] ?? errorBody['error_code']) as String;
            if (RegExp(r'^[A-Z][A-Z_0-9]{0,99}$').hasMatch(code)) {
              errorCode = code;
            }
          }
          if (reply.statusCode == 403 &&
              errorBody is Map &&
              errorBody['code'] == 'CONTENT_SOURCE_APPROVAL_REQUIRED' &&
              errorBody['requires_approval'] == true) {
            sourceConfirmation = ContentSourceConfirmation.tryParse(
              errorBody['confirmation'],
            );
          }
        } on FormatException {
          // Preserve the HTTP status even if an older Core returns non-JSON.
        }
        throw LumenisCoreException(
          '$method $path failed with HTTP ${reply.statusCode}',
          statusCode: reply.statusCode,
          messageKey: messageKey,
          errorCode: errorCode,
          sourceConfirmation: sourceConfirmation,
        );
      }
      final decoded = jsonDecode(reply.body);
      if (decoded is! Map<String, dynamic>) {
        throw LumenisCoreException('$method $path returned non-object JSON');
      }
      return decoded;
    } on LumenisTransportException catch (error) {
      throw LumenisCoreException(
        'LUMENIS Core unavailable at $baseUrl for $method $path: '
        '$error',
      );
    }
  }

  Uri _uri(String path) {
    final uri = Uri.parse('$baseUrl$path');
    if (uri.userInfo.isNotEmpty || uri.host.isEmpty) {
      throw const LumenisCoreException('Invalid LUMENIS Core URL.');
    }
    return uri;
  }

  static bool _isLoopback(Uri uri) {
    if (uri.scheme != 'http' && uri.scheme != 'https') return false;
    final host = uri.host.toLowerCase();
    if (host == 'localhost' || host.endsWith('.localhost')) return true;
    if (host == '::1' || host == '0:0:0:0:0:0:0:1') return true;
    final octets = host.split('.');
    if (octets.length != 4 || octets.first != '127') return false;
    return octets.every((octet) {
      final value = int.tryParse(octet);
      return value != null && value >= 0 && value <= 255;
    });
  }
}
