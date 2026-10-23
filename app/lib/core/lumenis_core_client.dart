import 'dart:convert';
import 'dart:math' as math;
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
              r'^content-source-import:(?:shared-workspace:)?v1:[a-f0-9]{64}$',
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

class SavedWorkExportFile {
  const SavedWorkExportFile({
    required this.bytes,
    required this.filename,
    required this.mediaType,
  });

  final Uint8List bytes;
  final String filename;
  final String mediaType;
}

const _sharedWorkspaceScopeHeaders = <String, String>{
  'X-Lumenis-Workspace-Scope': '{"scope_kind":"shared_workspace","version":1}',
};

sealed class LumenisWorkspaceScope {
  const LumenisWorkspaceScope();

  Map<String, Object?> toJson();
  Map<String, String> toQueryParameters();
  Map<String, String> get requestHeaders;
}

/// Exact CTH/BMP context for an explicitly domain-linked manuscript.
class InternalPitchScope extends LumenisWorkspaceScope {
  const InternalPitchScope({
    required this.domainId,
    required this.subjectId,
    required this.brandFocusId,
    required this.globalScope,
  });

  final String domainId;
  final String? subjectId;
  final String? brandFocusId;
  final bool globalScope;

  Map<String, Object?> _validated() {
    final suppliedDomain = domainId.trim().toUpperCase();
    final domain = suppliedDomain == 'ZBMP' ? 'BMP' : suppliedDomain;
    final subject = subjectId?.trim();
    final brand = brandFocusId?.trim();
    final validFocus =
        !globalScope &&
        ((domain == 'CTH' &&
                subject != null &&
                subject.isNotEmpty &&
                brand == null) ||
            (domain == 'BMP' &&
                subject == null &&
                brand != null &&
                brand.isNotEmpty));
    final validGlobal = globalScope && subject == null && brand == null;
    if ((domain != 'CTH' && domain != 'BMP') || (!validFocus && !validGlobal)) {
      throw const FormatException('Internal pitch scope is invalid.');
    }
    for (final value in [subject, brand].whereType<String>()) {
      if (value.length > 240 || RegExp(r'[\x00-\x1f\x7f]').hasMatch(value)) {
        throw const FormatException('Internal pitch scope is invalid.');
      }
    }
    return {
      'domain_id': domain == 'BMP' ? 'bmp' : 'cth',
      'subject_id': subject,
      'brand_focus_id': brand,
      'global_scope': globalScope,
    };
  }

  @override
  Map<String, Object?> toJson() => _validated();

  @override
  Map<String, String> toQueryParameters() =>
      _validated().map((key, value) => MapEntry(key, value?.toString() ?? ''));

  @override
  Map<String, String> get requestHeaders => const {};
}

/// The independent Shared workspace discriminator; identity and Permission
/// are resolved by Core and are never supplied by this client.
final class SharedWorkspaceScope extends LumenisWorkspaceScope {
  const SharedWorkspaceScope();

  @override
  Map<String, Object?> toJson() => const {
    'scope_kind': 'shared_workspace',
    'version': 1,
  };

  @override
  Map<String, String> toQueryParameters() => const {
    'scope_kind': 'shared_workspace',
    'version': '1',
  };

  @override
  Map<String, String> get requestHeaders => _sharedWorkspaceScopeHeaders;
}

class InternalPitchSection {
  const InternalPitchSection({required this.heading, required this.body});

  final String heading;
  final String body;

  Map<String, String> toJson() => {'heading': heading, 'body': body};
}

class InternalPitchManuscript {
  InternalPitchManuscript({
    required this.title,
    required this.summary,
    required List<InternalPitchSection> sections,
    required this.language,
    required this.authorship,
  }) : sections = List.unmodifiable(sections);

  final String title;
  final String summary;
  final List<InternalPitchSection> sections;
  final String language;
  final String authorship;

  Map<String, Object?> toJson() {
    if (title.trim().isEmpty ||
        title.runes.length > 300 ||
        summary.trim().isEmpty ||
        sections.isEmpty ||
        sections.length > 64 ||
        !const {'zh', 'en', 'ko'}.contains(language) ||
        !const {'user_supplied', 'assisted'}.contains(authorship)) {
      throw const FormatException('Internal pitch manuscript is invalid.');
    }
    for (final section in sections) {
      if (section.heading.trim().isEmpty || section.body.trim().isEmpty) {
        throw const FormatException('Internal pitch section is invalid.');
      }
    }
    return {
      'title': title,
      'summary': summary,
      'sections': sections.map((section) => section.toJson()).toList(),
      'language': language,
      'authorship': authorship,
    };
  }
}

class InternalPitchRevision {
  const InternalPitchRevision({
    this.workId,
    this.previousArtifactId,
    this.expectedDraftDigest,
  });

  final String? workId;
  final String? previousArtifactId;
  final String? expectedDraftDigest;

  Map<String, Object?> toJson() {
    if (workId != null && !RegExp(r'^WORK-[0-9a-f]{24}$').hasMatch(workId!)) {
      throw const FormatException('Internal pitch work ID is invalid.');
    }
    if (previousArtifactId != null &&
        !RegExp(r'^ART-[0-9a-f]{16}$').hasMatch(previousArtifactId!)) {
      throw const FormatException(
        'Internal pitch parent artifact ID is invalid.',
      );
    }
    if (expectedDraftDigest != null &&
        !RegExp(r'^[0-9a-f]{64}$').hasMatch(expectedDraftDigest!)) {
      throw const FormatException('Internal pitch draft digest is invalid.');
    }
    if (previousArtifactId != null &&
        (workId == null || expectedDraftDigest == null)) {
      throw const FormatException(
        'An internal pitch revision requires its saved parent.',
      );
    }
    if (expectedDraftDigest != null && previousArtifactId == null) {
      throw const FormatException('A draft digest requires a parent artifact.');
    }
    return {
      if (workId != null) 'work_id': workId,
      if (previousArtifactId != null)
        'previous_artifact_id': previousArtifactId,
      if (expectedDraftDigest != null)
        'expected_draft_digest': expectedDraftDigest,
    };
  }
}

class InternalPitchFile {
  const InternalPitchFile({
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
      throw const FormatException('Invalid OEVIRA context selection contract.');
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

  Future<Map<String, dynamic>> listAiConversations({
    int limit = 30,
    int offset = 0,
  }) {
    if (limit < 1 || limit > 100 || offset < 0) {
      throw ArgumentError('Invalid AI conversation page.');
    }
    final query = Uri(
      queryParameters: {'limit': '$limit', 'offset': '$offset'},
    ).query;
    return _request(
      'GET',
      '/v4/ai/conversations?$query',
      operationContext: _sharedWorkspaceScopeHeaders,
      requestHeaders: const {'Cache-Control': 'no-store'},
    );
  }

  Future<Map<String, dynamic>> createAiConversation({String title = ''}) {
    if (title.length > 512 || RegExp(r'[\x00-\x1f\x7f]').hasMatch(title)) {
      throw const FormatException('Invalid AI conversation title.');
    }
    return _request(
      'POST',
      '/v4/ai/conversations',
      operationContext: _sharedWorkspaceScopeHeaders,
      requestHeaders: const {'Cache-Control': 'no-store'},
      payload: {'title': title},
    );
  }

  Future<Map<String, dynamic>> readAiConversation(
    String conversationId, {
    int afterSequence = 0,
    int limit = 30,
  }) {
    _validateAiConversationId(conversationId);
    if (afterSequence < 0 || limit < 1 || limit > 100) {
      throw ArgumentError('Invalid AI conversation page.');
    }
    final query = Uri(
      queryParameters: {'after_sequence': '$afterSequence', 'limit': '$limit'},
    ).query;
    return _request(
      'GET',
      '/v4/ai/conversations/${Uri.encodeComponent(conversationId)}?$query',
      operationContext: _sharedWorkspaceScopeHeaders,
      requestHeaders: const {'Cache-Control': 'no-store'},
    );
  }

  Future<Map<String, dynamic>> appendAiConversationTurn({
    required String conversationId,
    required String text,
    required String idempotencyKey,
    required int expectedRevision,
  }) {
    _validateAiConversationId(conversationId);
    _validateAiConversationIdempotencyKey(idempotencyKey);
    if (text.trim().isEmpty || expectedRevision < 1) {
      throw const FormatException('Invalid AI conversation turn.');
    }
    return _request(
      'POST',
      '/v4/ai/conversations/${Uri.encodeComponent(conversationId)}/turns',
      operationContext: _sharedWorkspaceScopeHeaders,
      requestHeaders: const {'Cache-Control': 'no-store'},
      payload: {
        'text': text,
        'idempotency_key': idempotencyKey,
        'expected_revision': expectedRevision,
      },
    );
  }

  Future<Map<String, dynamic>> attachAiConversationTask({
    required String conversationId,
    required String taskId,
    required String idempotencyKey,
    required int expectedRevision,
  }) {
    _validateAiConversationId(conversationId);
    _validateAiConversationIdempotencyKey(idempotencyKey);
    if (taskId.isEmpty ||
        taskId.length > 256 ||
        RegExp(r'[\x00-\x1f\x7f]').hasMatch(taskId) ||
        expectedRevision < 1) {
      throw const FormatException('Invalid AI conversation task reference.');
    }
    return _request(
      'POST',
      '/v4/ai/conversations/${Uri.encodeComponent(conversationId)}/tasks',
      operationContext: _sharedWorkspaceScopeHeaders,
      requestHeaders: const {'Cache-Control': 'no-store'},
      payload: {
        'task_id': taskId,
        'idempotency_key': idempotencyKey,
        'expected_revision': expectedRevision,
      },
    );
  }

  Future<Map<String, dynamic>> respondToAiConversationTurn({
    required String conversationId,
    required String turnId,
    required String idempotencyKey,
    required int expectedRevision,
    bool retryConfirmed = false,
  }) {
    _validateAiConversationId(conversationId);
    _validateAiConversationTurnId(turnId);
    _validateAiConversationIdempotencyKey(idempotencyKey);
    if (expectedRevision < 1) {
      throw const FormatException('Invalid AI conversation revision.');
    }
    return _request(
      'POST',
      '/v4/ai/conversations/${Uri.encodeComponent(conversationId)}/turns/${Uri.encodeComponent(turnId)}/respond',
      operationContext: _sharedWorkspaceScopeHeaders,
      requestHeaders: const {'Cache-Control': 'no-store'},
      connectionTimeout: const Duration(minutes: 2),
      payload: {
        'idempotency_key': idempotencyKey,
        'expected_revision': expectedRevision,
        if (retryConfirmed) 'retry_confirmed': true,
      },
    );
  }

  Future<Map<String, dynamic>> interruptAiConversationResponse({
    required String conversationId,
    required String turnId,
    required int expectedRevision,
  }) {
    _validateAiConversationId(conversationId);
    _validateAiConversationTurnId(turnId);
    if (expectedRevision < 1) {
      throw const FormatException('Invalid AI conversation revision.');
    }
    return _request(
      'POST',
      '/v4/ai/conversations/${Uri.encodeComponent(conversationId)}/turns/${Uri.encodeComponent(turnId)}/respond',
      operationContext: _sharedWorkspaceScopeHeaders,
      requestHeaders: const {'Cache-Control': 'no-store'},
      payload: {
        'operation': 'interrupt',
        'expected_revision': expectedRevision,
        'confirmed': true,
      },
    );
  }

  static void _validateAiConversationId(String value) {
    if (!RegExp(r'^conv_[a-f0-9]{32}$').hasMatch(value)) {
      throw const FormatException('Invalid AI conversation ID.');
    }
  }

  static void _validateAiConversationTurnId(String value) {
    if (!RegExp(r'^turn_[a-f0-9]{32}$').hasMatch(value)) {
      throw const FormatException('Invalid AI conversation turn ID.');
    }
  }

  static void _validateAiConversationIdempotencyKey(String value) {
    if (!RegExp(r'^[A-Za-z0-9_.:-]{1,128}$').hasMatch(value)) {
      throw const FormatException('Invalid AI conversation idempotency key.');
    }
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

  Future<Map<String, dynamic>> saveSourceBriefResult({
    required String domainId,
    required String jobId,
    required String requestId,
    required String title,
  }) {
    _validateSourceBriefJobId(jobId);
    _validateSavedWorkRequestId(requestId);
    if (title.trim().isEmpty || title.length > 300) {
      throw const FormatException('Invalid source brief SavedWork title.');
    }
    return _request(
      'POST',
      '/api/experience/reports/source-brief/jobs/${Uri.encodeComponent(jobId)}/save',
      operationContext: _contentContext(domainId),
      requestHeaders: const {'Cache-Control': 'no-store'},
      payload: {'request_id': requestId, 'title': title},
      connectionTimeout: const Duration(seconds: 60),
    );
  }

  Future<Map<String, dynamic>> reopenSourceBriefSavedWork({
    required String domainId,
    required String artifactId,
  }) {
    _validateSavedWorkArtifactId(artifactId);
    return _request(
      'GET',
      '/api/experience/saved-work/$artifactId',
      operationContext: _contentContext(domainId),
      requestHeaders: const {'Cache-Control': 'no-store'},
      connectionTimeout: const Duration(seconds: 30),
    );
  }

  /// Prepares or explicitly saves a SourceBrief into the independent Shared
  /// workspace through the existing SavedWork owner. The server resolves the
  /// actor, target Shared scope, source evidence and exact DATA_EXPORT effect.
  Future<Map<String, dynamic>> adoptSourceBriefToShared({
    required String jobId,
    required String requestId,
    required String mode,
    String? title,
    bool confirm = false,
    String? confirmedResource,
  }) {
    _validateSourceBriefJobId(jobId);
    _validateSavedWorkRequestId(requestId);
    if (!const {'prepare', 'save', 'apply', 'revoke'}.contains(mode)) {
      throw ArgumentError.value(mode, 'mode');
    }
    if (title != null && (title.trim().isEmpty || title.length > 300)) {
      throw const FormatException('Invalid shared research title.');
    }
    final needsConfirmation = mode == 'apply' || mode == 'revoke';
    if (needsConfirmation != confirm ||
        needsConfirmation != (confirmedResource != null) ||
        (confirmedResource != null &&
            (confirmedResource.trim().isEmpty ||
                confirmedResource.length > 4096))) {
      throw const FormatException('Invalid shared report confirmation.');
    }
    return _request(
      'POST',
      '/api/experience/saved-work',
      operationContext: _sharedWorkspaceScopeHeaders,
      requestHeaders: const {'Cache-Control': 'no-store'},
      payload: {
        'adopt_source_brief_job_id': jobId,
        'request_id': requestId,
        'mode': mode,
        'title': ?title,
        if (needsConfirmation) ...{
          'confirm': true,
          'confirmed_resource': confirmedResource,
        },
      },
      connectionTimeout: const Duration(seconds: 60),
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

  /// An explicit null selects the existing independent Shared workspace.
  /// Business context is never merged into this actor-free wire scope; Core
  /// still authorizes the current workspace, source uses and every effect.
  Map<String, String> _mediaContentContext(String? domainId) => domainId == null
      ? _sharedWorkspaceScopeHeaders
      : _contentContext(domainId);

  Future<Map<String, dynamic>> inspectContentMedia({
    required String? domainId,
    List<String>? assetPaths,
    List<String>? assetRefs,
  }) => _request(
    'POST',
    '/api/experience/shared-skills/shared.content_project/inspect',
    operationContext: _mediaContentContext(domainId),
    payload: {
      'action_type': 'READ',
      'input': _contentAssets(assetPaths, assetRefs),
    },
  );

  Future<Map<String, dynamic>> inspectContentWaveform({
    required String? domainId,
    required String assetRef,
    required double startSec,
    required double endSec,
    required int audioStreamIndex,
  }) => _request(
    'POST',
    '/api/experience/shared-skills/shared.content_project/inspect',
    operationContext: _mediaContentContext(domainId),
    payload: {
      'action_type': 'READ',
      'input': {
        'asset_refs': [assetRef],
        'waveform': {
          'start_sec': startSec,
          'end_sec': endSec,
          'audio_stream_index': audioStreamIndex,
          'bins': 256,
        },
      },
    },
  );

  /// Read-only batch preview through the existing media inspection owner.
  Future<Map<String, dynamic>> inspectContentEditBatch({
    required String? domainId,
    List<String>? assetPaths,
    List<String>? assetRefs,
    required Map<String, dynamic> timeline,
    required List<Map<String, dynamic>> commands,
    required int expectedVersion,
  }) => _request(
    'POST',
    '/api/experience/shared-skills/shared.content_project/inspect',
    operationContext: _mediaContentContext(domainId),
    payload: {
      'action_type': 'READ',
      'input': {
        ..._contentAssets(assetPaths, assetRefs),
        'timeline': timeline,
        'edit_batch': {
          'commands': commands,
          'expected_version': expectedVersion,
        },
      },
    },
  );

  Future<Map<String, dynamic>> inspectAudioProcessing({
    required String? domainId,
    List<String>? assetPaths,
    List<String>? assetRefs,
    required Map<String, dynamic> timeline,
    required Map<String, double> renderOptions,
    required double startSec,
    required double endSec,
  }) => _request(
    'POST',
    '/api/experience/shared-skills/shared.content_project/inspect',
    operationContext: _mediaContentContext(domainId),
    payload: {
      'action_type': 'READ',
      'input': {
        ..._contentAssets(assetPaths, assetRefs),
        'timeline': timeline,
        'audio_comparison': {
          'start_sec': startSec,
          'end_sec': endSec,
          'render_options': renderOptions,
        },
      },
    },
    connectionTimeout: const Duration(minutes: 5),
  );

  Future<Map<String, dynamic>> exportContentProject({
    required String? domainId,
    List<String>? assetPaths,
    List<String>? assetRefs,
    required Map<String, dynamic> timeline,
    required String outputKind,
    bool? demoAcknowledged,
    String? previousArtifactId,
    String? title,
    bool renderMedia = true,
    Map<String, double> renderOptions = const {},
    Map<String, dynamic> deliveryOptions = const {},
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
      operationContext: _mediaContentContext(domainId),
      connectionTimeout: const Duration(minutes: 5),
      payload: {
        'action_type': 'EXPORT',
        'input': {
          ..._contentAssets(assetPaths, assetRefs),
          'timeline': timeline,
          'output_kind': outputKind,
          'demo_acknowledged': ?demoAcknowledged,
          'previous_artifact_id': previousArtifactId,
          'title': ?title,
          if (!renderMedia) 'render_media': false,
          if (renderOptions.isNotEmpty) 'render_options': renderOptions,
          if (deliveryOptions.isNotEmpty) 'delivery_options': deliveryOptions,
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
    required String? domainId,
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
      operationContext: _mediaContentContext(domainId),
    );
  }

  Future<Map<String, dynamic>> reopenContentProject({
    required String? domainId,
    required String artifactId,
  }) {
    _validateContentArtifactId(artifactId);
    return _request(
      'GET',
      '/api/experience/content-projects/$artifactId',
      operationContext: _mediaContentContext(domainId),
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

  /// Exact human classification preview/commit; the server binds actor, source
  /// version and prior classification revision into the returned resource.
  Future<Map<String, dynamic>> classifyPropagationEvent({
    required String subjectId,
    required int sourceEventId,
    required String category,
    required String requestId,
    String? confirmedResource,
  }) {
    final context = _contentContext('BMP');
    if (context['X-Lumenis-Context-Mode'] != 'FOCUS' ||
        context['X-Subject-ID'] != subjectId ||
        sourceEventId <= 0 ||
        !const {
          'brand_event',
          'product_event',
          'industry_event',
        }.contains(category) ||
        !RegExp(r'^[A-Za-z0-9_-]{8,128}$').hasMatch(requestId) ||
        (confirmedResource != null &&
            !RegExp(
              r'^propagation-classification:v1:[a-f0-9]{64}$',
            ).hasMatch(confirmedResource))) {
      throw const FormatException('Classification context or preview changed.');
    }
    return _request(
      'POST',
      '/api/experience/propagation/classify',
      operationContext: context,
      payload: {
        'source_event_id': sourceEventId,
        'category': category,
        'request_id': requestId,
        'confirm': confirmedResource != null,
        'confirmed_resource': ?confirmedResource,
      },
    );
  }

  Future<Map<String, dynamic>> importContentSource({
    required String? domainId,
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
      operationContext: _mediaContentContext(domainId),
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
    required String? domainId,
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
      operationContext: _mediaContentContext(domainId),
      payload: {'confirmed': confirmed},
    );
  }

  Future<ContentProjectFile> contentProjectFile({
    required String? domainId,
    required String artifactId,
    required bool package,
  }) async {
    _validateContentArtifactId(artifactId);
    final context = _mediaContentContext(domainId);
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

  /// Existing podcast SavedWork owner. A null domain explicitly selects the
  /// independent Shared workspace; BMP retains its current exact context.
  Future<Map<String, dynamic>> listPodcastWork({
    String? domainId,
    String? cursor,
  }) {
    if (cursor != null &&
        (cursor.isEmpty ||
            cursor.length > 4096 ||
            RegExp(r'[\x00-\x1f\x7f]').hasMatch(cursor))) {
      throw const FormatException('Invalid SavedWork cursor.');
    }
    final query = Uri(
      queryParameters: {
        'kind': 'podcast_episode',
        'latest_only': 'true',
        'limit': '30',
        'cursor': ?cursor,
      },
    ).query;
    return _request(
      'GET',
      '/api/experience/saved-work?$query',
      operationContext: domainId == null
          ? _sharedWorkspaceScopeHeaders
          : _contentContext(domainId),
      requestHeaders: const {'Cache-Control': 'no-store'},
    );
  }

  Future<Map<String, dynamic>> reopenPodcastWork(
    String artifactId, {
    String? domainId,
  }) {
    _validateSavedWorkArtifactId(artifactId);
    return _request(
      'GET',
      '/api/experience/saved-work/$artifactId',
      operationContext: domainId == null
          ? _sharedWorkspaceScopeHeaders
          : _contentContext(domainId),
      requestHeaders: const {'Cache-Control': 'no-store'},
    );
  }

  Future<Map<String, dynamic>> savePodcastWork({
    required Map<String, Object?> body,
    String? domainId,
  }) {
    _validateSavedWorkRequestId(body['request_id'] as String);
    _validateSavedWorkArtifactId(body['previous_artifact_id'] as String);
    if (body['kind'] != 'podcast_episode' ||
        !RegExp(
          r'^[0-9a-f]{64}$',
        ).hasMatch(body['expected_draft_digest'] as String)) {
      throw const FormatException('Invalid podcast revision.');
    }
    return _request(
      'POST',
      '/api/experience/saved-work',
      payload: body,
      operationContext: domainId == null
          ? _sharedWorkspaceScopeHeaders
          : _contentContext(domainId),
      requestHeaders: const {'Cache-Control': 'no-store'},
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

  Future<Map<String, dynamic>> prepareInternalPitch({
    required LumenisWorkspaceScope scope,
    required InternalPitchManuscript manuscript,
    required String requestId,
    InternalPitchRevision? revision,
  }) async {
    _validateSavedWorkRequestId(requestId);
    final response = await _request(
      'POST',
      '/api/experience/creation/internal-pitches',
      withContext: false,
      requestHeaders: scope.requestHeaders,
      payload: {
        'scope': scope.toJson(),
        'manuscript': manuscript.toJson(),
        'request_id': requestId,
        'profile': 'authored-manuscript/v4',
        ...(revision?.toJson() ?? const <String, Object?>{}),
      },
    );
    return _internalPitchResult(response);
  }

  Future<Map<String, dynamic>> readInternalPitch({
    required String taskId,
    required LumenisWorkspaceScope scope,
  }) async {
    _validateInternalPitchTaskId(taskId);
    final query = Uri(queryParameters: scope.toQueryParameters()).query;
    final response = await _request(
      'GET',
      '/api/experience/creation/internal-pitches/${Uri.encodeComponent(taskId)}${query.isEmpty ? '' : '?$query'}',
      withContext: false,
      requestHeaders: scope.requestHeaders,
      connectionTimeout: const Duration(seconds: 30),
    );
    return _internalPitchResult(response, expectedTaskId: taskId);
  }

  Future<Map<String, dynamic>> runInternalPitch({
    required String taskId,
    required LumenisWorkspaceScope scope,
  }) => _internalPitchAction(taskId, 'run', scope);

  Future<Map<String, dynamic>> cancelInternalPitch({
    required String taskId,
    required LumenisWorkspaceScope scope,
  }) => _internalPitchAction(taskId, 'cancel', scope);

  Future<Map<String, dynamic>> _internalPitchAction(
    String taskId,
    String action,
    LumenisWorkspaceScope scope,
  ) async {
    _validateInternalPitchTaskId(taskId);
    final response = await _request(
      'POST',
      '/api/experience/creation/internal-pitches/${Uri.encodeComponent(taskId)}/$action',
      withContext: false,
      requestHeaders: scope.requestHeaders,
      payload: {'scope': scope.toJson()},
      connectionTimeout: const Duration(seconds: 30),
    );
    return _internalPitchResult(response, expectedTaskId: taskId);
  }

  Future<InternalPitchFile> exportInternalPitch({
    required String taskId,
    required LumenisWorkspaceScope scope,
  }) async {
    _validateInternalPitchTaskId(taskId);
    final query = Uri(queryParameters: scope.toQueryParameters()).query;
    final path =
        '/api/experience/creation/internal-pitches/${Uri.encodeComponent(taskId)}/export${query.isEmpty ? '' : '?$query'}';
    final response = await sendLumenisBinaryRequest(
      LumenisTransportRequest(
        method: 'GET',
        uri: _uri(path),
        headers: {
          ...scope.requestHeaders,
          'Accept':
              'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
          'Cache-Control': 'no-store',
        },
        connectionTimeout: const Duration(seconds: 45),
        followRedirects: false,
      ),
      maxBytes: 32 * 1024 * 1024,
    );
    if (response.statusCode != 200) {
      throw _internalPitchExportFailure(response);
    }
    const mediaType =
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
    final actualType = response.contentType
        ?.split(';')
        .first
        .trim()
        .toLowerCase();
    if (actualType != mediaType || response.bytes.isEmpty) {
      throw const FormatException('Internal pitch export is not a DOCX file.');
    }
    return InternalPitchFile(
      bytes: response.bytes,
      filename: 'document.docx',
      mediaType: mediaType,
    );
  }

  Future<Map<String, dynamic>> listAuthoredManuscripts({
    required String domainId,
    int limit = 100,
    String? cursor,
  }) async {
    _validateSavedWorkPage(limit, cursor);
    final query = Uri(
      queryParameters: {'kind': 'report', 'limit': '$limit', 'cursor': ?cursor},
    ).query;
    final response = await _request(
      'GET',
      '/api/experience/saved-work?$query',
      operationContext: _contentContext(domainId),
      requestHeaders: const {'Cache-Control': 'no-store'},
      connectionTimeout: const Duration(seconds: 30),
    );
    return _authoredManuscriptPage(_savedWorkResult(response));
  }

  Future<Map<String, dynamic>> listSharedAuthoredManuscripts({
    required SharedWorkspaceScope scope,
    int limit = 100,
    String? cursor,
  }) async {
    _validateSavedWorkPage(limit, cursor);
    final response = await listSharedSavedWork(
      limit: limit,
      cursor: cursor,
      kind: 'report',
    );
    return _authoredManuscriptPage(_savedWorkResult(response));
  }

  Future<Map<String, dynamic>> reopenSavedManuscript({
    required String domainId,
    required String artifactId,
  }) async {
    _validateSavedWorkArtifactId(artifactId);
    final response = await _request(
      'GET',
      '/api/experience/saved-work/$artifactId',
      operationContext: _contentContext(domainId),
      requestHeaders: const {'Cache-Control': 'no-store'},
      connectionTimeout: const Duration(seconds: 30),
    );
    return _requireAuthoredManuscript(_savedWorkResult(response));
  }

  Future<Map<String, dynamic>> reopenSharedSavedManuscript({
    required SharedWorkspaceScope scope,
    required String artifactId,
  }) async {
    _validateSavedWorkArtifactId(artifactId);
    return _requireAuthoredManuscript(
      _savedWorkResult(await reopenSharedSavedWork(artifactId)),
    );
  }

  static void _validateSavedWorkPage(int limit, String? cursor) {
    if (limit < 1 ||
        limit > 100 ||
        (cursor != null &&
            (cursor.isEmpty ||
                cursor.length > 4096 ||
                RegExp(r'[\x00-\x1f\x7f]').hasMatch(cursor)))) {
      throw const FormatException('Invalid SavedWork page.');
    }
  }

  static Map<String, dynamic> _savedWorkResult(Map<String, dynamic> response) {
    final result = response['result'];
    if (response['ok'] != true || result is! Map<String, dynamic>) {
      throw const FormatException('SavedWork response is invalid.');
    }
    return result;
  }

  static Map<String, dynamic> _authoredManuscriptPage(
    Map<String, dynamic> result,
  ) {
    final rows = result['items'];
    if (rows is! List) {
      throw const FormatException('SavedWork list response is invalid.');
    }
    final manuscripts = <Map<String, dynamic>>[];
    for (final value in rows) {
      if (value is! Map<String, dynamic>) {
        throw const FormatException('SavedWork item is invalid.');
      }
      final document = value['document'];
      if (document is! Map<String, dynamic>) {
        throw const FormatException('SavedWork document is invalid.');
      }
      if (_isAuthoredManuscriptV4(document['contract'])) {
        final payload = document['payload'];
        if (payload is! Map<String, dynamic> ||
            payload['manuscript'] is! Map<String, dynamic> ||
            payload['truth_state'] is! Map<String, dynamic>) {
          throw const FormatException(
            'Authored manuscript payload is invalid.',
          );
        }
        manuscripts.add(value);
      }
    }
    return {
      ...result,
      'items': List<Map<String, dynamic>>.unmodifiable(manuscripts),
    };
  }

  static Map<String, dynamic> _requireAuthoredManuscript(
    Map<String, dynamic> result,
  ) {
    final document = result['document'];
    if (document is! Map<String, dynamic> ||
        !_isAuthoredManuscriptV4(document['contract'])) {
      throw const FormatException(
        'SavedWork artifact is not authored-manuscript/v4.',
      );
    }
    final payload = document['payload'];
    if (payload is! Map<String, dynamic> ||
        payload['manuscript'] is! Map<String, dynamic> ||
        payload['truth_state'] is! Map<String, dynamic>) {
      throw const FormatException('Authored manuscript payload is invalid.');
    }
    return result;
  }

  static bool _isAuthoredManuscriptV4(Object? value) {
    if (value is! Map ||
        value['id'] != 'lumenis.internal-pitch' ||
        value['version'] != '4') {
      return false;
    }
    final paths = value['required_payload_paths'];
    return paths is List &&
        paths.length == 2 &&
        paths[0] == 'manuscript' &&
        paths[1] == 'truth_state';
  }

  static Map<String, dynamic> _internalPitchResult(
    Map<String, dynamic> response, {
    String? expectedTaskId,
  }) {
    final result = response['result'];
    if (response['ok'] != true ||
        response['contract'] != 'lumenis.internal-pitch.v1' ||
        result is! Map<String, dynamic>) {
      throw const FormatException(
        'Internal pitch response contract is invalid.',
      );
    }
    final taskId = result['task_id'];
    final state = result['state'];
    if (taskId is! String ||
        !_isInternalPitchTaskId(taskId) ||
        (expectedTaskId != null && taskId != expectedTaskId) ||
        state is! String ||
        state.isEmpty ||
        !result.containsKey('error') ||
        (result['error'] != null && result['error'] is! String)) {
      throw const FormatException('Internal pitch task response is invalid.');
    }
    return result;
  }

  static bool _isInternalPitchTaskId(String value) =>
      RegExp(r'^task-pitch-[0-9a-f]{24}$').hasMatch(value);

  static void _validateInternalPitchTaskId(String value) {
    if (!_isInternalPitchTaskId(value)) {
      throw const FormatException('Invalid internal pitch task ID.');
    }
  }

  static LumenisCoreException _internalPitchExportFailure(
    LumenisBinaryTransportResponse response,
  ) {
    String? code;
    try {
      final decoded = jsonDecode(utf8.decode(response.bytes));
      if (decoded is Map &&
          (decoded['code'] is String || decoded['error_code'] is String)) {
        final candidate = (decoded['code'] ?? decoded['error_code']) as String;
        if (RegExp(r'^[A-Z][A-Z_0-9]{0,99}$').hasMatch(candidate)) {
          code = candidate;
        }
      }
    } on FormatException {
      // Keep the HTTP status when Core returns a non-JSON error response.
    }
    return LumenisCoreException(
      'Internal pitch export was not returned.',
      statusCode: response.statusCode,
      errorCode: code,
    );
  }

  /// Reads user-authored reports from the independent Shared workspace.
  /// This deliberately never inherits the selected CTH/BMP business context;
  /// the server resolves the actor and checks Shared Permission on every call.
  Future<Map<String, dynamic>> listSharedSavedWork({
    int limit = 100,
    String? cursor,
    String kind = 'report',
  }) {
    if (limit < 1 || limit > 100) {
      throw ArgumentError.value(limit, 'limit');
    }
    if (!const {'report', 'research'}.contains(kind)) {
      throw ArgumentError.value(kind, 'kind');
    }
    if (cursor != null &&
        (cursor.isEmpty ||
            cursor.length > 4096 ||
            RegExp(r'[\x00-\x1f\x7f]').hasMatch(cursor))) {
      throw const FormatException('Invalid SavedWork cursor.');
    }
    final query = Uri(
      queryParameters: {'kind': kind, 'limit': '$limit', 'cursor': ?cursor},
    ).query;
    return _request(
      'GET',
      '/api/experience/saved-work?$query',
      operationContext: _sharedWorkspaceScopeHeaders,
      requestHeaders: const {'Cache-Control': 'no-store'},
    );
  }

  Future<Map<String, dynamic>> startSharedResearch({
    required String question,
    required List<String> sourceIds,
    required String requestId,
  }) {
    _validateSavedWorkRequestId(requestId);
    if (question.trim().length < 4 ||
        question.length > 1500 ||
        sourceIds.isEmpty ||
        sourceIds.length > 100 ||
        sourceIds.toSet().length != sourceIds.length) {
      throw const FormatException('Invalid research request.');
    }
    for (final id in sourceIds) {
      _validateSavedWorkArtifactId(id);
    }
    return _request(
      'POST',
      '/api/experience/reports/source-brief/start',
      operationContext: _sharedWorkspaceScopeHeaders,
      requestHeaders: const {'Cache-Control': 'no-store'},
      payload: {
        'business_question': question.trim(),
        'source_ids': sourceIds,
        'limit': sourceIds.length,
        'request_id': requestId,
      },
    );
  }

  Future<Map<String, dynamic>> sharedResearchTasks({String? cursor}) {
    final query = Uri(
      queryParameters: {'limit': '30', 'cursor': ?cursor},
    ).query;
    return _request(
      'GET',
      '/api/experience/reports/source-brief/tasks?$query',
      operationContext: _sharedWorkspaceScopeHeaders,
      requestHeaders: const {'Cache-Control': 'no-store'},
    );
  }

  Future<Map<String, dynamic>> sharedResearchTask(
    String taskId, {
    bool resume = false,
  }) {
    _validateSourceBriefTaskId(taskId);
    return _request(
      resume ? 'POST' : 'GET',
      '/api/experience/reports/source-brief/tasks/$taskId${resume ? '/resume' : ''}',
      operationContext: _sharedWorkspaceScopeHeaders,
      requestHeaders: const {'Cache-Control': 'no-store'},
      payload: resume ? const <String, Object?>{} : null,
    );
  }

  Future<Map<String, dynamic>> saveSharedResearch({
    required String jobId,
    required String requestId,
    required String title,
  }) {
    _validateSourceBriefJobId(jobId);
    _validateSavedWorkRequestId(requestId);
    if (title.trim().isEmpty || title.length > 300) {
      throw const FormatException('Invalid research title.');
    }
    return _request(
      'POST',
      '/api/experience/reports/source-brief/jobs/$jobId/save',
      operationContext: _sharedWorkspaceScopeHeaders,
      requestHeaders: const {'Cache-Control': 'no-store'},
      payload: {'request_id': requestId, 'title': title},
      connectionTimeout: const Duration(seconds: 60),
    );
  }

  /// Lists the existing SavedWork records created by Shared document import.
  /// The server still resolves the actor and applies the Shared read boundary.
  Future<Map<String, dynamic>> listSharedDocumentImports({
    int limit = 30,
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
    final query = Uri(
      queryParameters: {
        'kind': 'research',
        'query': 'Private uploaded source analysis',
        'latest_only': 'true',
        'limit': '$limit',
        'cursor': ?cursor,
      },
    ).query;
    return _request(
      'GET',
      '/api/experience/saved-work?$query',
      operationContext: _sharedWorkspaceScopeHeaders,
      requestHeaders: const {'Cache-Control': 'no-store'},
    );
  }

  /// Imports one user-selected file through the current Shared document owner.
  /// No actor, source assertion or business-domain context is accepted here.
  Future<Map<String, dynamic>> importSharedDocument({
    required String filename,
    required Uint8List bytes,
    required String requestId,
  }) {
    _validateSavedWorkRequestId(requestId);
    _validateSharedImportFile(filename, bytes);
    final boundary = _multipartBoundary();
    final body = _sharedImportMultipartBody(
      filename: filename,
      bytes: bytes,
      requestId: requestId,
      boundary: boundary,
    );
    return _request(
      'POST',
      '/api/experience/materials/documents',
      operationContext: _sharedWorkspaceScopeHeaders,
      requestHeaders: const {'Cache-Control': 'no-store'},
      binaryBody: body,
      binaryContentType: 'multipart/form-data; boundary=$boundary',
      connectionTimeout: const Duration(seconds: 60),
    );
  }

  static const _sharedImportExtensions = {
    'docx',
    'xlsx',
    'pptx',
    'pdf',
    'txt',
    'csv',
    'json',
    'xml',
    'xbrl',
    'html',
    'htm',
    'doc',
    'xls',
  };

  static void _validateSharedImportFile(String filename, Uint8List bytes) {
    final extension = filename.contains('.')
        ? filename.split('.').last.toLowerCase()
        : '';
    final stem = filename.split('.').first.toUpperCase();
    const reservedWindowsNames = {
      'CON',
      'PRN',
      'AUX',
      'NUL',
      'COM1',
      'COM2',
      'COM3',
      'COM4',
      'COM5',
      'COM6',
      'COM7',
      'COM8',
      'COM9',
      'LPT1',
      'LPT2',
      'LPT3',
      'LPT4',
      'LPT5',
      'LPT6',
      'LPT7',
      'LPT8',
      'LPT9',
    };
    if (filename.isEmpty ||
        filename.runes.length > 185 ||
        filename.trim() != filename ||
        filename.startsWith('.') ||
        RegExp(r'[<>:"/\\|?*\x00-\x1f\x7f]').hasMatch(filename) ||
        filename.endsWith('.') ||
        filename.endsWith(' ') ||
        reservedWindowsNames.contains(stem) ||
        !_sharedImportExtensions.contains(extension) ||
        bytes.isEmpty ||
        bytes.length > 8 * 1024 * 1024) {
      throw const FormatException('Shared document file is invalid.');
    }
  }

  static String _multipartBoundary() {
    final random = math.Random.secure();
    final suffix = List.generate(
      24,
      (_) => random.nextInt(256).toRadixString(16).padLeft(2, '0'),
    ).join();
    return 'lumenis-sh02-$suffix';
  }

  static Uint8List _sharedImportMultipartBody({
    required String filename,
    required Uint8List bytes,
    required String requestId,
    required String boundary,
  }) {
    final builder = BytesBuilder(copy: false);
    void text(String value) => builder.add(utf8.encode(value));
    final asciiName = filename.replaceAll(RegExp(r'[^A-Za-z0-9._-]'), '_');
    final encodedName = Uri.encodeComponent(filename);
    text('--$boundary\r\n');
    text(
      'Content-Disposition: form-data; name="file"; filename="$asciiName"; filename*=UTF-8\'\'$encodedName\r\n',
    );
    text('Content-Type: application/octet-stream\r\n\r\n');
    builder.add(bytes);
    text('\r\n--$boundary\r\n');
    text('Content-Disposition: form-data; name="request_id"\r\n\r\n');
    text('$requestId\r\n--$boundary--\r\n');
    return builder.takeBytes();
  }

  /// Saves a user-authored report as a versioned Shared SavedWork artifact.
  /// Source citations are empty for this user-authored draft; revisions of an
  /// existing cited artifact retain the server's original citation scopes.
  Future<Map<String, dynamic>> saveSharedReport({
    required String title,
    required String markdown,
    required String requestId,
  }) {
    _validateSavedWorkRequestId(requestId);
    return _request(
      'POST',
      '/api/experience/saved-work',
      operationContext: _sharedWorkspaceScopeHeaders,
      requestHeaders: const {'Cache-Control': 'no-store'},
      payload: {
        'title': title,
        'markdown': markdown,
        'kind': 'report',
        'payload': const <String, Object?>{},
        'citations': const <Object?>[],
        'request_id': requestId,
      },
    );
  }

  /// Reopens one committed SavedWork version through the Shared Permission
  /// boundary. The artifact identifier is never sent as actor or scope data.
  Future<Map<String, dynamic>> reopenSharedSavedWork(String artifactId) {
    _validateSavedWorkArtifactId(artifactId);
    return _request(
      'GET',
      '/api/experience/saved-work/$artifactId',
      operationContext: _sharedWorkspaceScopeHeaders,
      requestHeaders: const {'Cache-Control': 'no-store'},
    );
  }

  Future<Map<String, dynamic>> sharedDocumentRows({
    required String artifactId,
    required String sourceSha256,
    required int offset,
  }) {
    _validateSavedWorkArtifactId(artifactId);
    if (!RegExp(r'^[0-9a-f]{64}$').hasMatch(sourceSha256) ||
        offset < 0 ||
        offset > 100000) {
      throw const FormatException('Invalid source page.');
    }
    final query = Uri(
      queryParameters: {
        'offset': '$offset',
        'limit': '50',
        'source_version': artifactId,
        'source_sha256': sourceSha256,
      },
    ).query;
    return _request(
      'GET',
      '/api/experience/saved-work/$artifactId?$query',
      operationContext: _sharedWorkspaceScopeHeaders,
      requestHeaders: const {'Cache-Control': 'no-store'},
    );
  }

  /// Creates an immutable report revision. Omitting citations and source
  /// adoptions asks the server to preserve and freshly reauthorize the exact
  /// parent version's original source uses.
  Future<Map<String, dynamic>> reviseSharedReport({
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
      operationContext: _sharedWorkspaceScopeHeaders,
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

  /// Requests an explicitly selected export. The server performs DATA_EXPORT
  /// Permission and rechecks every retained source scope before returning bytes.
  Future<SavedWorkExportFile> exportSharedSavedWork({
    required String artifactId,
    required String format,
  }) async {
    _validateSavedWorkArtifactId(artifactId);
    if (!const {'md', 'txt', 'docx', 'pdf', 'xlsx', 'pptx'}.contains(format)) {
      throw ArgumentError.value(format, 'format');
    }
    final expectedMediaType = switch (format) {
      'md' => 'text/markdown',
      'txt' => 'text/plain',
      'docx' =>
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'pdf' => 'application/pdf',
      'xlsx' =>
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'pptx' =>
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
      _ => throw ArgumentError.value(format, 'format'),
    };
    final uri = _uri(
      '/api/experience/saved-work/$artifactId/export?'
      '${Uri(queryParameters: {'format': format}).query}',
    );
    try {
      final response = await sendLumenisBinaryRequest(
        LumenisTransportRequest(
          method: 'GET',
          uri: uri,
          headers: {
            ..._sharedWorkspaceScopeHeaders,
            'Accept': expectedMediaType,
            'Cache-Control': 'no-store',
          },
          connectionTimeout: const Duration(seconds: 45),
          followRedirects: false,
        ),
        maxBytes: 32 * 1024 * 1024,
      );
      if (response.statusCode != 200) {
        String? errorCode;
        try {
          final body = jsonDecode(utf8.decode(response.bytes));
          if (body is Map && body['code'] is String) {
            final candidate = body['code'] as String;
            if (RegExp(r'^[A-Z][A-Z_0-9]{0,99}$').hasMatch(candidate)) {
              errorCode = candidate;
            }
          }
        } on FormatException {
          // Keep the status when Core returns a non-JSON error body.
        }
        throw LumenisCoreException(
          'SavedWork export was not returned.',
          statusCode: response.statusCode,
          errorCode: errorCode,
        );
      }
      final mediaType = response.contentType
          ?.split(';')
          .first
          .trim()
          .toLowerCase();
      if (mediaType != expectedMediaType || response.bytes.isEmpty) {
        throw const FormatException(
          'SavedWork export type does not match the requested format.',
        );
      }
      return SavedWorkExportFile(
        bytes: response.bytes,
        filename: '$artifactId.$format',
        mediaType: mediaType!,
      );
    } on LumenisTransportException {
      throw const LumenisCoreException(
        'SavedWork export is unavailable.',
        errorCode: 'SAVED_WORK_EXPORT_UNAVAILABLE',
      );
    }
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
        'Controlled browser access is available only through local OEVIRA Core.',
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
    String? binaryContentType,
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
        headers['Content-Type'] =
            binaryContentType ?? 'application/octet-stream';
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
        'OEVIRA Core unavailable at $baseUrl for $method $path: '
        '$error',
      );
    }
  }

  Uri _uri(String path) {
    final uri = Uri.parse('$baseUrl$path');
    if (uri.userInfo.isNotEmpty || uri.host.isEmpty) {
      throw const LumenisCoreException('Invalid OEVIRA Core URL.');
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
