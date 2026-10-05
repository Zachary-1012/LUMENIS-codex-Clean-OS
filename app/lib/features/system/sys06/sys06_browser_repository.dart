import '../../../core/lumenis_core_client.dart';

class Sys06BrowserSession {
  const Sys06BrowserSession({
    required this.sessionId,
    required this.status,
    required this.engineLabel,
    required this.targetId,
    required this.pageRevision,
    required this.currentTitle,
    required this.currentUrl,
    required this.allowedActions,
  });

  final String sessionId;
  final String status;
  final String engineLabel;
  final String? targetId;
  final int pageRevision;
  final String currentTitle;
  final String currentUrl;
  final Set<String> allowedActions;

  bool get isRunning => status == 'running';
  bool allows(String action) => allowedActions.contains(action);

  factory Sys06BrowserSession.fromResponse(Map<String, dynamic> value) {
    if (value['ok'] != true) {
      throw const FormatException(
        'Browser session response is not successful.',
      );
    }
    final sessionId = value['session_id'];
    final status = value['status'];
    final revision = value['page_revision'];
    final rawActions = value['allowed_actions'];
    if (sessionId is! String ||
        !RegExp(r'^bs_[a-f0-9]{12}$').hasMatch(sessionId) ||
        status is! String ||
        !const {
          'created',
          'running',
          'idle',
          'need_verify',
          'cooling_down',
          'blocked',
          'error',
        }.contains(status) ||
        revision is! int ||
        revision < 0 ||
        rawActions is! List) {
      throw const FormatException('Browser session response is malformed.');
    }
    final targetId = value['target_id'];
    if (targetId != null &&
        (targetId is! String ||
            !RegExp(r'^[A-Za-z0-9_-]{1,180}$').hasMatch(targetId))) {
      throw const FormatException('Browser target identity is malformed.');
    }
    final actions = <String>{};
    for (final action in rawActions) {
      if (action is! String ||
          !const {'navigate', 'reload', 'frame'}.contains(action)) {
        throw const FormatException('Browser action capability is malformed.');
      }
      actions.add(action);
    }
    return Sys06BrowserSession(
      sessionId: sessionId,
      status: status,
      engineLabel: _safeText(value['engine_label'], maximum: 80),
      targetId: targetId as String?,
      pageRevision: revision,
      currentTitle: _safeText(value['current_title'], maximum: 300),
      currentUrl: _safeText(value['current_url'], maximum: 2048),
      allowedActions: Set.unmodifiable(actions),
    );
  }
}

class Sys06BrowserFrame {
  const Sys06BrowserFrame({required this.frame});

  final LumenisBrowserFrame frame;
}

abstract interface class Sys06BrowserRepository {
  Future<Sys06BrowserSession> open();
  Future<Sys06BrowserSession> readSession(String sessionId);
  Future<Sys06BrowserSession> navigate({
    required String sessionId,
    required String url,
  });
  Future<Sys06BrowserSession> reload(String sessionId);
  Future<Sys06BrowserFrame> readFrame(String sessionId);
  Future<void> stop(String sessionId);
}

class CoreSys06BrowserRepository implements Sys06BrowserRepository {
  CoreSys06BrowserRepository({required this.client});

  final LumenisCoreClient client;

  @override
  Future<Sys06BrowserSession> open() async =>
      Sys06BrowserSession.fromResponse(await client.openBrowserSession());

  @override
  Future<Sys06BrowserSession> readSession(String sessionId) async =>
      Sys06BrowserSession.fromResponse(await client.browserSession(sessionId));

  @override
  Future<Sys06BrowserSession> navigate({
    required String sessionId,
    required String url,
  }) async {
    final response = await client.navigateBrowserSession(
      sessionId: sessionId,
      url: url,
    );
    _requireActionSuccess(response, action: 'navigate');
    return readSession(sessionId);
  }

  @override
  Future<Sys06BrowserSession> reload(String sessionId) async {
    final response = await client.reloadBrowserSession(sessionId);
    _requireActionSuccess(response, action: 'reload');
    return readSession(sessionId);
  }

  @override
  Future<Sys06BrowserFrame> readFrame(String sessionId) async =>
      Sys06BrowserFrame(frame: await client.browserFrame(sessionId));

  @override
  Future<void> stop(String sessionId) async {
    final response = await client.stopBrowserSession(sessionId);
    if (response['ok'] != true || response['closed'] != true) {
      throw const LumenisCoreException(
        'The controlled browser session was not closed.',
        errorCode: 'BROWSER_STOP_UNCONFIRMED',
      );
    }
  }

  static void _requireActionSuccess(
    Map<String, dynamic> response, {
    required String action,
  }) {
    if (response['ok'] == true) return;
    final code = response['error_code'];
    throw LumenisCoreException(
      'Browser $action was not accepted.',
      errorCode:
          code is String && RegExp(r'^[A-Z][A-Z_0-9]{0,99}$').hasMatch(code)
          ? code
          : 'BROWSER_ACTION_REJECTED',
    );
  }
}

String _safeText(Object? value, {required int maximum}) {
  if (value is! String) return '';
  final sanitized = value.replaceAll(RegExp(r'[\x00-\x1f\x7f]'), ' ').trim();
  return sanitized.length <= maximum
      ? sanitized
      : sanitized.substring(0, maximum);
}
