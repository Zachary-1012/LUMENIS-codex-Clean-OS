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
  String? _coreAuthorization;
  bool _authorizationBootstrapped = false;
  Map<String, String> _contextHeaders = const {
    'X-Lumenis-Context-Mode': 'GLOBAL_ALL',
  };
  Map<String, dynamic>? _contextEnvelope;

  /// Last server-returned selection envelope. This is display state only; Core
  /// still reauthorizes each request carrying the focus headers.
  Map<String, dynamic>? get currentContextEnvelope => _contextEnvelope;

  /// Core transport credentials are read only from a loopback Core runtime
  /// and kept in memory. They are not a product account and do not create an
  /// account session.
  void clearCredentials() {
    _coreAuthorization = null;
    _authorizationBootstrapped = false;
  }

  Future<void> _bootstrapCoreAuthorization() async {
    if (_authorizationBootstrapped) return;

    if (!supportsLocalCoreCredentialBootstrap) {
      // A browser must never receive the reusable credential returned by the
      // loopback-only bootstrap endpoint. Any protected Web Workspace route
      // therefore remains an honest server-owned unavailable/denied state.
      _authorizationBootstrapped = true;
      return;
    }

    final uri = _uri('/api/auth/config');
    if (!_isLoopback(uri)) {
      // /api/auth/config returns a reusable Basic header. It is intentionally
      // consumed only by a local Core process, never by a remote client.
      _authorizationBootstrapped = true;
      return;
    }

    try {
      final config = await _get(
        '/api/auth/config',
        useCoreAuthorization: false,
        withContext: false,
      );
      if (config['ok'] != true || config['auth_enabled'] is! bool) {
        throw const FormatException('Core auth configuration is invalid.');
      }

      if (config['auth_enabled'] == true) {
        final authorization = config['auth_header'];
        if (authorization is! String ||
            !authorization.startsWith('Basic ') ||
            authorization.contains('\r') ||
            authorization.contains('\n')) {
          throw const FormatException(
            'Core did not provide a valid configured authorization header.',
          );
        }
        _coreAuthorization = authorization;
      } else {
        _coreAuthorization = null;
      }
      _authorizationBootstrapped = true;
    } on LumenisCoreException catch (error) {
      // Older/local Core builds may not expose this optional bootstrap route.
      // Try the normal no-credential read; an actual 401 remains visible.
      if (error.statusCode == 404) {
        _authorizationBootstrapped = true;
        return;
      }
      rethrow;
    }
  }

  Future<Map<String, dynamic>> runtimeIdentity() async {
    await _bootstrapCoreAuthorization();
    return _get('/api/experience/runtime/identity', withContext: false);
  }

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
    required bool demoAcknowledged,
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
          'demo_acknowledged': demoAcknowledged,
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
    final authorization = _coreAuthorization;
    if (authorization != null && !_allowsAuthorization(uri)) {
      throw const LumenisCoreException(
        'Core credentials require a loopback Core endpoint.',
      );
    }
    try {
      final response = await sendLumenisBinaryRequest(
        LumenisTransportRequest(
          method: 'GET',
          uri: uri,
          headers: {
            ...context,
            'Accept': package ? 'application/zip' : 'video/mp4, audio/wav',
            'Authorization': ?authorization,
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

  Future<Map<String, dynamic>> _get(
    String path, {
    bool useCoreAuthorization = true,
    bool withContext = true,
  }) => _request(
    'GET',
    path,
    useCoreAuthorization: useCoreAuthorization,
    withContext: withContext,
  );

  Future<Map<String, dynamic>> _request(
    String method,
    String path, {
    Map<String, Object?>? payload,
    bool useCoreAuthorization = true,
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
    final authorization = useCoreAuthorization ? _coreAuthorization : null;
    if (authorization != null && !_allowsAuthorization(uri)) {
      throw const LumenisCoreException(
        'Core credentials require a loopback Core endpoint.',
      );
    }

    try {
      final headers = <String, String>{
        'Accept': 'application/json',
        ...requestHeaders,
      };
      if (authorization != null) {
        headers['Authorization'] = authorization;
      }
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
          if (errorBody is Map && errorBody['code'] is String) {
            final code = errorBody['code'] as String;
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

  static bool _allowsAuthorization(Uri uri) {
    return _isLoopback(uri);
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
