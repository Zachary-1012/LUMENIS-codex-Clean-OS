import 'dart:convert';
import 'dart:io';

class LumenisCoreException implements Exception {
  const LumenisCoreException(this.message, {this.statusCode});

  final String message;
  final int? statusCode;

  @override
  String toString() => 'LumenisCoreException: $message';
}

class LumenisCoreClient {
  LumenisCoreClient({String? baseUrl})
    : baseUrl =
          baseUrl ??
          const String.fromEnvironment(
            'LUMENIS_CORE_URL',
            defaultValue: 'http://127.0.0.1:8201',
          );

  final String baseUrl;
  String? _coreAuthorization;
  bool _authorizationBootstrapped = false;

  /// Core transport credentials are read only from a loopback Core runtime
  /// and kept in memory. They are not a product account and do not create an
  /// account session.
  void clearCredentials() {
    _coreAuthorization = null;
    _authorizationBootstrapped = false;
  }

  Future<void> _bootstrapCoreAuthorization() async {
    if (_authorizationBootstrapped) return;

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
      if (error.statusCode == HttpStatus.notFound) {
        _authorizationBootstrapped = true;
        return;
      }
      rethrow;
    }
  }

  Future<Map<String, dynamic>> runtimeIdentity() async {
    await _bootstrapCoreAuthorization();
    return _get('/api/experience/runtime/identity');
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
  Future<Map<String, dynamic>> settingsSubjects() =>
      _get('/api/settings/subjects?domain_id=CTH');

  Future<Map<String, dynamic>> sharedSkillsCatalog() =>
      _get('/api/experience/shared-skills');

  Future<Map<String, dynamic>> contentEvidence(String evidenceId) => _get(
    '/api/experience/content/evidence/${Uri.encodeComponent(evidenceId)}',
  );

  Future<Map<String, dynamic>> screen(String screenId) =>
      _get('/api/experience/screen/${Uri.encodeComponent(screenId)}');

  Future<Map<String, dynamic>> _get(
    String path, {
    bool useCoreAuthorization = true,
  }) async {
    final uri = _uri(path);
    final authorization = useCoreAuthorization ? _coreAuthorization : null;
    if (authorization != null && !_allowsAuthorization(uri)) {
      throw const LumenisCoreException(
        'Core credentials require a loopback Core endpoint.',
      );
    }

    final http = HttpClient();
    try {
      http.connectionTimeout = const Duration(seconds: 8);
      final request = await http.getUrl(uri);
      if (authorization != null) {
        request.followRedirects = false;
        request.headers.set(HttpHeaders.authorizationHeader, authorization);
      }
      request.headers.set(HttpHeaders.acceptHeader, 'application/json');
      final reply = await request.close();
      final body = await utf8.decoder.bind(reply).join();
      if (reply.statusCode < 200 || reply.statusCode >= 300) {
        throw LumenisCoreException(
          'GET $path failed with HTTP ${reply.statusCode}',
          statusCode: reply.statusCode,
        );
      }
      final decoded = jsonDecode(body);
      if (decoded is! Map<String, dynamic>) {
        throw LumenisCoreException('GET $path returned non-object JSON');
      }
      return decoded;
    } on IOException catch (error) {
      throw LumenisCoreException(
        'LUMENIS Core unavailable at $baseUrl for GET $path: '
        '$error',
      );
    } finally {
      http.close(force: true);
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
    return InternetAddress.tryParse(host)?.isLoopback ?? false;
  }
}
