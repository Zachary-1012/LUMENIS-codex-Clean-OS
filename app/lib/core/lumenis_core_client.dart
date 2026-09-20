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
  String? _username;
  String? _password;
  String? _accountToken;

  /// Called when a request using the active session is rejected.
  void Function(LumenisCoreException error)? onAccessFailure;

  bool get hasSession => _username != null && _password != null;
  bool get hasAccountSession => _accountToken != null;

  Future<Map<String, dynamic>> authenticate({
    required String username,
    required String password,
  }) async {
    final normalizedUsername = username.trim();
    if (normalizedUsername.isEmpty || normalizedUsername.contains(':')) {
      throw const LumenisCoreException('Invalid Basic Auth username.');
    }
    if (password.isEmpty) {
      throw const LumenisCoreException('Password is required.');
    }

    // Never keep an old session while validating a new set of credentials.
    clearCredentials();
    final uri = _uri('/api/experience/runtime/identity');
    if (!_allowsAuthorization(uri)) {
      throw const LumenisCoreException(
        'Credentials require HTTPS or loopback HTTP.',
      );
    }

    final identity = await _get(
      '/api/experience/runtime/identity',
      authorization: _basicAuthorization(normalizedUsername, password),
    );
    if (identity['ok'] != true) {
      throw const LumenisCoreException(
        'LUMENIS Core returned an invalid runtime identity.',
      );
    }

    // Credentials stay in memory only, after Core has accepted them.
    _username = normalizedUsername;
    _password = password;
    return identity;
  }

  void clearCredentials() {
    _username = null;
    _password = null;
    _accountToken = null;
  }

  Future<void> authenticateAccount({
    required String username,
    required String password,
  }) async {
    final normalizedUsername = username.trim();
    if (normalizedUsername.isEmpty || password.isEmpty) {
      clearCredentials();
      throw const LumenisCoreException(
        'Account username and password are required.',
        statusCode: HttpStatus.unauthorized,
      );
    }

    try {
      final response = await _postJson('/v4/auth/login', {
        'username': normalizedUsername,
        'password': password,
      });
      final token = response['token'];
      if (response['success'] != true || token is! String || token.isEmpty) {
        clearCredentials();
        throw LumenisCoreException(
          response['success'] == true
              ? 'Account login did not return a session token.'
              : 'Account login was rejected.',
          statusCode: response['success'] == true
              ? HttpStatus.internalServerError
              : HttpStatus.unauthorized,
        );
      }
      _accountToken = token;
    } on LumenisCoreException {
      clearCredentials();
      rethrow;
    } catch (_) {
      clearCredentials();
      rethrow;
    }
  }

  /// Revokes the account session where possible, then immediately drops both
  /// in-memory authentication channels.
  Future<void> logout() async {
    final token = _accountToken;
    clearCredentials();
    if (token == null) return;

    try {
      await _postJson(
        '/v4/auth/logout',
        const <String, Object?>{},
        authorization: _bearerAuthorization(token),
      );
    } catch (_) {
      // Local logout is complete even when Core is unavailable.
    }
  }

  Future<Map<String, dynamic>> runtimeIdentity() =>
      _get('/api/experience/runtime/identity');

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

  /// Reads the account-scoped Subject Registry for CTH selection metadata.
  /// This does not authorize business data for any returned Subject.
  Future<Map<String, dynamic>> settingsSubjects() {
    final token = _accountToken;
    if (token == null) {
      throw const LumenisCoreException(
        'An account session is required for the CTH Subject Registry.',
        statusCode: HttpStatus.unauthorized,
      );
    }
    return _get(
      '/api/settings/subjects?domain_id=CTH',
      authorization: _bearerAuthorization(token),
      accountScoped: true,
    );
  }

  Future<Map<String, dynamic>> sharedSkillsCatalog() =>
      _get('/api/experience/shared-skills');

  Future<Map<String, dynamic>> contentEvidence(String evidenceId) => _get(
    '/api/experience/content/evidence/${Uri.encodeComponent(evidenceId)}',
  );

  Future<Map<String, dynamic>> screen(String screenId) =>
      _get('/api/experience/screen/${Uri.encodeComponent(screenId)}');

  Future<Map<String, dynamic>> _get(
    String path, {
    String? authorization,
    bool notifyAccessFailure = true,
    bool accountScoped = false,
  }) async {
    final uri = _uri(path);
    final usesSessionCredentials = authorization == null && hasSession;
    final requestAuthorization =
        authorization ??
        (usesSessionCredentials
            ? _basicAuthorization(_username!, _password!)
            : null);
    if (requestAuthorization != null && !_allowsAuthorization(uri)) {
      throw const LumenisCoreException(
        'Credentials require HTTPS or loopback HTTP.',
      );
    }

    final http = HttpClient();
    try {
      http.connectionTimeout = const Duration(seconds: 8);
      final request = await http.getUrl(uri);
      if (requestAuthorization != null) {
        request.followRedirects = false;
        request.headers.set(
          HttpHeaders.authorizationHeader,
          requestAuthorization,
        );
      }
      request.headers.set(HttpHeaders.acceptHeader, 'application/json');
      final reply = await request.close();
      final body = await utf8.decoder.bind(reply).join();
      if (reply.statusCode < 200 || reply.statusCode >= 300) {
        final error = LumenisCoreException(
          'GET $path failed with HTTP ${reply.statusCode}',
          statusCode: reply.statusCode,
        );
        if (usesSessionCredentials &&
            (reply.statusCode == HttpStatus.unauthorized ||
                reply.statusCode == HttpStatus.forbidden)) {
          if (reply.statusCode == HttpStatus.unauthorized) {
            clearCredentials();
          }
          if (notifyAccessFailure) onAccessFailure?.call(error);
        }
        if (accountScoped && reply.statusCode == HttpStatus.unauthorized) {
          clearCredentials();
          if (notifyAccessFailure) onAccessFailure?.call(error);
        }
        throw error;
      }
      final decoded = jsonDecode(body);
      if (decoded is! Map<String, dynamic>) {
        throw LumenisCoreException('GET $path returned non-object JSON');
      }
      return decoded;
    } on SocketException catch (error) {
      throw LumenisCoreException(
        'LUMENIS Core unavailable at $baseUrl: ${error.message}',
      );
    } finally {
      http.close(force: true);
    }
  }

  Future<Map<String, dynamic>> _postJson(
    String path,
    Map<String, Object?> payload, {
    String? authorization,
  }) async {
    final uri = _uri(path);
    if (!_allowsAuthorization(uri)) {
      throw const LumenisCoreException(
        'Account credentials require HTTPS or loopback HTTP.',
      );
    }
    if (authorization != null && !_allowsAuthorization(uri)) {
      throw const LumenisCoreException(
        'Credentials require HTTPS or loopback HTTP.',
      );
    }

    final http = HttpClient();
    try {
      http.connectionTimeout = const Duration(seconds: 8);
      final request = await http.postUrl(uri);
      request.followRedirects = false;
      request.headers.set(HttpHeaders.acceptHeader, 'application/json');
      request.headers.contentType = ContentType.json;
      if (authorization != null) {
        request.headers.set(HttpHeaders.authorizationHeader, authorization);
      }
      request.write(jsonEncode(payload));
      final reply = await request.close();
      final body = await utf8.decoder.bind(reply).join();
      if (reply.statusCode < 200 || reply.statusCode >= 300) {
        throw LumenisCoreException(
          'POST $path failed with HTTP ${reply.statusCode}',
          statusCode: reply.statusCode,
        );
      }
      final decoded = jsonDecode(body);
      if (decoded is! Map<String, dynamic>) {
        throw LumenisCoreException('POST $path returned non-object JSON');
      }
      return decoded;
    } on SocketException catch (error) {
      throw LumenisCoreException(
        'LUMENIS Core unavailable at $baseUrl: ${error.message}',
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

  static String _basicAuthorization(String username, String password) =>
      'Basic ${base64Encode(utf8.encode('$username:$password'))}';

  static String _bearerAuthorization(String token) => 'Bearer $token';

  static bool _allowsAuthorization(Uri uri) {
    if (uri.scheme == 'https') return true;
    if (uri.scheme != 'http') return false;
    final host = uri.host.toLowerCase();
    if (host == 'localhost' || host.endsWith('.localhost')) return true;
    return InternetAddress.tryParse(host)?.isLoopback ?? false;
  }
}
