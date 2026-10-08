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
    this.taskBindingStatus = 'UNAVAILABLE',
    this.humanControlActive,
    this.humanActionsRequireLease = false,
    this.humanActions = const <String>{},
  });

  final String sessionId;
  final String status;
  final String engineLabel;
  final String? targetId;
  final int pageRevision;
  final String currentTitle;
  final String currentUrl;
  final Set<String> allowedActions;
  final String taskBindingStatus;
  final bool? humanControlActive;
  final bool humanActionsRequireLease;
  final Set<String> humanActions;

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
    final humanActionsRequireLease =
        value['human_actions_require_lease'] == true;
    final rawHumanActions = value['human_actions'];
    final humanActions = <String>{};
    if (rawHumanActions is List) {
      for (final action in rawHumanActions) {
        if (action is! String) {
          throw const FormatException(
            'Human browser action capability is malformed.',
          );
        }
        if (const {
          'navigate',
          'back',
          'forward',
          'reload',
          'scroll',
        }.contains(action)) {
          humanActions.add(action);
        }
      }
    } else if (rawHumanActions != null) {
      throw const FormatException(
        'Human browser action capability is malformed.',
      );
    }
    final taskBindingStatus = value['task_binding_status'];
    final taskBindingVerified = value['task_binding_verified'] == true;
    final humanControlActive = value['human_control_active'];
    return Sys06BrowserSession(
      sessionId: sessionId,
      status: status,
      engineLabel: _safeText(value['engine_label'], maximum: 80),
      targetId: targetId as String?,
      pageRevision: revision,
      currentTitle: _safeText(value['current_title'], maximum: 300),
      currentUrl: _safeText(value['current_url'], maximum: 2048),
      allowedActions: Set.unmodifiable(actions),
      // A client-supplied task/run pair is only a claim until the canonical
      // task owner verifies it. Never display that claim as a task binding.
      taskBindingStatus: taskBindingStatus == 'BOUND' && taskBindingVerified
          ? 'BOUND'
          : 'UNAVAILABLE',
      humanControlActive: humanControlActive is bool
          ? humanControlActive
          : null,
      humanActionsRequireLease: humanActionsRequireLease,
      humanActions: humanActionsRequireLease
          ? Set.unmodifiable(humanActions)
          : const <String>{},
    );
  }
}

class Sys06BrowserLease {
  const Sys06BrowserLease({
    required this.token,
    required this.expiresAt,
    required this.ttlSeconds,
    required this.humanActions,
  });

  /// A server-issued bearer token. Keep this in memory only and never display it.
  final String token;
  final DateTime expiresAt;
  final int ttlSeconds;
  final Set<String> humanActions;

  factory Sys06BrowserLease.fromResponse(Map<String, dynamic> value) {
    final token = value['lease_token'];
    final expiresAt = DateTime.tryParse(
      value['lease_expires_at'] is String
          ? value['lease_expires_at'] as String
          : '',
    );
    final ttlSeconds = value['lease_ttl_seconds'];
    final rawActions = value['human_actions'];
    if (value['ok'] != true ||
        value['control_mode'] != 'HUMAN_EXCLUSIVE' ||
        token is! String ||
        !RegExp(r'^[A-Za-z0-9_-]{16,256}$').hasMatch(token) ||
        expiresAt == null ||
        ttlSeconds is! int ||
        ttlSeconds < 1 ||
        rawActions is! List) {
      throw const FormatException('Human browser lease response is malformed.');
    }
    final actions = <String>{};
    for (final action in rawActions) {
      if (action is! String) {
        throw const FormatException(
          'Human browser lease capabilities are malformed.',
        );
      }
      if (const {
        'navigate',
        'back',
        'forward',
        'reload',
        'scroll',
      }.contains(action)) {
        actions.add(action);
      }
    }
    return Sys06BrowserLease(
      token: token,
      expiresAt: expiresAt.toUtc(),
      ttlSeconds: ttlSeconds,
      humanActions: Set.unmodifiable(actions),
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

/// Optional, explicitly lease-gated human control. Read-only Browser
/// repositories do not gain these capabilities through the base interface.
abstract interface class Sys06BrowserHumanControlRepository {
  Future<Sys06BrowserLease> acquireHumanControl(String sessionId);
  Future<void> releaseHumanControl({
    required String sessionId,
    required String leaseToken,
  });
  Future<void> humanNavigate({
    required String sessionId,
    required String url,
    required String leaseToken,
    required LumenisBrowserFrameBinding frameBinding,
  });
  Future<void> humanAction({
    required String sessionId,
    required String action,
    required String leaseToken,
    required LumenisBrowserFrameBinding frameBinding,
    String value = '',
  });
}

/// A business context resolved from the existing actor-authorized workspace
/// selection. It is routing metadata; every SavedWork operation is still
/// re-authorized by Core.
class Sys06BrowserResearchContext {
  const Sys06BrowserResearchContext({
    required this.mode,
    required this.domainId,
    required this.subjectId,
  });

  final String mode;
  final String domainId;
  final String? subjectId;

  bool get isGlobal => mode == 'GLOBAL_ALL';
  String get fingerprint => '$mode|$domainId|${subjectId ?? ''}';
}

class Sys06BrowserWorkspaceSelection {
  const Sys06BrowserWorkspaceSelection({
    required this.mode,
    required this.domainId,
    required this.subjectId,
  });

  final String mode;
  final String? domainId;
  final String? subjectId;
}

class Sys06BrowserResearchNote {
  const Sys06BrowserResearchNote({
    required this.artifactId,
    required this.workId,
    required this.version,
    required this.sha256,
    required this.draftDigest,
    required this.parentArtifactId,
    required this.parentSha256,
    required this.title,
    required this.markdown,
    required this.payload,
  });

  final String artifactId;
  final String workId;
  final int version;
  final String sha256;
  final String draftDigest;
  final String? parentArtifactId;
  final String? parentSha256;
  final String title;
  final String markdown;
  final Map<String, dynamic> payload;

  factory Sys06BrowserResearchNote.fromSavedWorkResult(
    Map<String, dynamic> result, {
    bool requireReturnRef = true,
  }) {
    final artifact = result['artifact'];
    final document = result['document'];
    if (artifact is! Map || document is! Map) {
      throw const FormatException('SavedWork note response is malformed.');
    }
    final artifactId = artifact['artifact_id'];
    final sha256 = artifact['sha256'];
    final workId = document['work_id'];
    final version = document['version'];
    final draftDigest = document['draft_digest'];
    final parentArtifactId = document['parent_artifact_id'];
    final parentSha256 = document['parent_sha256'];
    final title = document['title'];
    final markdown = document['markdown'];
    final payload = document['payload'];
    final citations = document['citations'];
    final marker = payload is Map ? payload['browser_note'] : null;
    final locator = marker is Map ? marker['locator'] : null;
    final returnRef = result['return_ref'];
    final receiptScope = returnRef is Map ? returnRef['scope'] : null;
    final documentScope = document['context'];
    final rawLocatorUrl = locator is Map ? locator['url'] : null;
    final safeLocatorOrigin = sys06SafeBrowserSiteOrigin(rawLocatorUrl);
    if (artifactId is! String ||
        !RegExp(r'^ART-[0-9a-f]{16}$').hasMatch(artifactId) ||
        sha256 is! String ||
        !RegExp(r'^[0-9a-f]{64}$').hasMatch(sha256) ||
        workId is! String ||
        !RegExp(r'^WORK-[A-Za-z0-9_-]{8,80}$').hasMatch(workId) ||
        version is! int ||
        version < 1 ||
        draftDigest is! String ||
        !RegExp(r'^[0-9a-f]{64}$').hasMatch(draftDigest) ||
        (parentArtifactId != null &&
            (parentArtifactId is! String ||
                !RegExp(r'^ART-[0-9a-f]{16}$').hasMatch(parentArtifactId))) ||
        (parentSha256 != null &&
            (parentSha256 is! String ||
                !RegExp(r'^[0-9a-f]{64}$').hasMatch(parentSha256))) ||
        title is! String ||
        title.trim().isEmpty ||
        markdown is! String ||
        markdown.trim().isEmpty ||
        document['schema'] != 'lumenis.saved-work/v1' ||
        document['kind'] != 'research' ||
        document['task_id'] != null ||
        document['assertion_id'] != null ||
        citations is! List ||
        citations.isNotEmpty ||
        marker is! Map ||
        marker['schema'] != 'lumenis.browser-session-note/v1' ||
        marker['surface'] != 'SYS-06' ||
        marker['source_capture'] != 'NOT_IMPORTED' ||
        marker['source_verification'] != 'NOT_VERIFIED' ||
        marker['task_binding'] != 'UNBOUND' ||
        locator is! Map ||
        rawLocatorUrl is! String ||
        safeLocatorOrigin == null ||
        locator['title'] is! String ||
        (locator['title'] as String).length > 300 ||
        locator['page_revision'] is! int ||
        locator['captured_at'] is! String ||
        DateTime.tryParse(locator['captured_at'] as String) == null ||
        documentScope is! Map ||
        (requireReturnRef &&
            (returnRef is! Map ||
                returnRef['artifact_id'] != artifactId ||
                returnRef['work_id'] != workId ||
                returnRef['version'] != version ||
                receiptScope is! Map ||
                receiptScope['domain_id'] != documentScope['domain_id'] ||
                receiptScope['subject_id'] != documentScope['subject_id'] ||
                receiptScope['brand_focus_id'] !=
                    documentScope['brand_focus_id'] ||
                receiptScope['global_scope'] !=
                    documentScope['global_scope']))) {
      throw const FormatException(
        'SavedWork item is not a verified SYS-06 browser note.',
      );
    }
    if (version == 1 && (parentArtifactId != null || parentSha256 != null) ||
        version > 1 && (parentArtifactId == null || parentSha256 == null)) {
      throw const FormatException('SavedWork note version chain is malformed.');
    }
    final sanitizedPayload = Map<String, dynamic>.from(payload as Map);
    final sanitizedMarker = Map<String, dynamic>.from(marker);
    final sanitizedLocator = Map<String, dynamic>.from(locator)
      ..['url'] = safeLocatorOrigin;
    sanitizedMarker['locator'] = sanitizedLocator;
    sanitizedPayload['browser_note'] = sanitizedMarker;
    return Sys06BrowserResearchNote(
      artifactId: artifactId,
      workId: workId,
      version: version,
      sha256: sha256,
      draftDigest: draftDigest,
      parentArtifactId: parentArtifactId as String?,
      parentSha256: parentSha256 as String?,
      title: title,
      markdown: markdown,
      payload: sanitizedPayload,
    );
  }
}

class Sys06BrowserResearchPage {
  const Sys06BrowserResearchPage({
    required this.notes,
    required this.hasMore,
    required this.nextCursor,
    required this.unverifiedCandidates,
  });

  final List<Sys06BrowserResearchNote> notes;
  final bool hasMore;
  final String? nextCursor;
  final int unverifiedCandidates;
}

/// Separate optional interface keeps existing Browser repository consumers
/// source-compatible while Core supplies the real Shared SavedWork binding.
abstract interface class Sys06BrowserResearchRepository {
  Future<Sys06BrowserWorkspaceSelection> readWorkspaceSelection();
  Future<Sys06BrowserResearchContext> resolveResearchContext({
    String? globalDomainId,
  });
  Future<Sys06BrowserResearchPage> listResearchNotes({
    required Sys06BrowserResearchContext context,
    String? cursor,
  });
  Future<Sys06BrowserResearchNote> reopenResearchNote({
    required Sys06BrowserResearchContext context,
    required String artifactId,
  });
  Future<Sys06BrowserResearchNote> saveResearchNote({
    required Sys06BrowserResearchContext context,
    required String title,
    required String markdown,
    required String requestId,
    required String pageUrl,
    required String pageTitle,
    required int pageRevision,
    required DateTime capturedAt,
  });
  Future<Sys06BrowserResearchNote> reviseResearchNote({
    required Sys06BrowserResearchContext context,
    required Sys06BrowserResearchNote parent,
    required String title,
    required String markdown,
    required String requestId,
    required String reason,
  });
}

class CoreSys06BrowserRepository
    implements
        Sys06BrowserRepository,
        Sys06BrowserHumanControlRepository,
        Sys06BrowserResearchRepository {
  CoreSys06BrowserRepository({required this.client});

  final LumenisCoreClient client;

  @override
  Future<Sys06BrowserWorkspaceSelection> readWorkspaceSelection() async {
    final response = await client.settingsContext();
    final selection = response['context'];
    if (response['ok'] != true || selection is! Map) {
      throw const FormatException('Workspace context is unavailable.');
    }
    final mode = selection['mode'];
    if (mode == 'GLOBAL_ALL' && selection['subject_id'] == null) {
      return const Sys06BrowserWorkspaceSelection(
        mode: 'GLOBAL_ALL',
        domainId: null,
        subjectId: null,
      );
    }
    final domain = selection['domain_id'];
    final subject = selection['subject_id'];
    if (mode != 'FOCUS' ||
        (domain != 'CTH' && domain != 'BMP') ||
        subject is! String ||
        subject.trim().isEmpty) {
      throw const LumenisCoreException(
        'A valid CTH/BMP Subject or BrandFocus must be selected in the workspace.',
        errorCode: 'CONTENT_CONTEXT_REQUIRED',
      );
    }
    return Sys06BrowserWorkspaceSelection(
      mode: 'FOCUS',
      domainId: domain as String,
      subjectId: subject,
    );
  }

  @override
  Future<Sys06BrowserResearchContext> resolveResearchContext({
    String? globalDomainId,
  }) async {
    final selection = await readWorkspaceSelection();
    if (selection.mode == 'GLOBAL_ALL') {
      final domain = globalDomainId?.trim().toUpperCase();
      if (domain != 'CTH' && domain != 'BMP') {
        throw const LumenisCoreException(
          'Select CTH or BMP before using Shared SavedWork.',
          errorCode: 'CONTENT_CONTEXT_REQUIRED',
        );
      }
      return Sys06BrowserResearchContext(
        mode: 'GLOBAL_ALL',
        domainId: domain!,
        subjectId: null,
      );
    }
    final domain = selection.domainId;
    final subject = selection.subjectId;
    if ((domain != 'CTH' && domain != 'BMP') ||
        subject == null ||
        subject.trim().isEmpty ||
        (globalDomainId != null &&
            globalDomainId.trim().toUpperCase() != domain)) {
      throw const LumenisCoreException(
        'A valid CTH/BMP Subject or BrandFocus must be selected in the workspace.',
        errorCode: 'CONTENT_CONTEXT_REQUIRED',
      );
    }
    return Sys06BrowserResearchContext(
      mode: 'FOCUS',
      domainId: domain!,
      subjectId: subject,
    );
  }

  Future<void> _requireResearchContext(
    Sys06BrowserResearchContext expected,
  ) async {
    final current = await resolveResearchContext(
      globalDomainId: expected.isGlobal ? expected.domainId : null,
    );
    if (current.fingerprint != expected.fingerprint) {
      throw const LumenisCoreException(
        'The selected business context changed. Recheck the note before continuing.',
        errorCode: 'CONTENT_CONTEXT_CHANGED',
      );
    }
  }

  @override
  Future<Sys06BrowserResearchPage> listResearchNotes({
    required Sys06BrowserResearchContext context,
    String? cursor,
  }) async {
    await _requireResearchContext(context);
    final response = await client.listBrowserResearchNotes(
      domainId: context.domainId,
      cursor: cursor,
    );
    final result = response['result'];
    if (response['ok'] != true || result is! Map) {
      throw const LumenisCoreException(
        'Saved browser notes could not be read.',
        errorCode: 'WORK_SEARCH_UNAVAILABLE',
      );
    }
    final rawItems = result['items'];
    if (rawItems is! List || result['has_more'] is! bool) {
      throw const FormatException('SavedWork list response is malformed.');
    }
    final notes = <Sys06BrowserResearchNote>[];
    for (final item in rawItems) {
      if (item is! Map) continue;
      final document = item['document'];
      final artifact = item['artifact'];
      final payload = document is Map ? document['payload'] : null;
      final marker = payload is Map ? payload['browser_note'] : null;
      if (marker is! Map ||
          marker['schema'] != 'lumenis.browser-session-note/v1') {
        continue;
      }
      notes.add(
        Sys06BrowserResearchNote.fromSavedWorkResult(<String, dynamic>{
          'artifact': artifact,
          'document': document,
        }, requireReturnRef: false),
      );
    }
    final nextCursor = result['next_cursor'];
    final unverifiedCandidates = result['unverified_candidates'];
    if ((nextCursor != null && nextCursor is! String) ||
        (unverifiedCandidates != null && unverifiedCandidates is! int)) {
      throw const FormatException('SavedWork continuation is malformed.');
    }
    await _requireResearchContext(context);
    return Sys06BrowserResearchPage(
      notes: List.unmodifiable(notes),
      hasMore: result['has_more'] as bool,
      nextCursor: nextCursor as String?,
      unverifiedCandidates: unverifiedCandidates is int
          ? unverifiedCandidates
          : 0,
    );
  }

  @override
  Future<Sys06BrowserResearchNote> reopenResearchNote({
    required Sys06BrowserResearchContext context,
    required String artifactId,
  }) async {
    await _requireResearchContext(context);
    final response = await client.reopenBrowserResearchNote(
      domainId: context.domainId,
      artifactId: artifactId,
    );
    final result = response['result'];
    if (response['ok'] != true || result is! Map) {
      throw const LumenisCoreException(
        'The selected browser note could not be reopened.',
        errorCode: 'WORK_NOT_FOUND',
      );
    }
    final note = Sys06BrowserResearchNote.fromSavedWorkResult(
      Map<String, dynamic>.from(result),
    );
    await _requireResearchContext(context);
    return note;
  }

  @override
  Future<Sys06BrowserResearchNote> saveResearchNote({
    required Sys06BrowserResearchContext context,
    required String title,
    required String markdown,
    required String requestId,
    required String pageUrl,
    required String pageTitle,
    required int pageRevision,
    required DateTime capturedAt,
  }) async {
    await _requireResearchContext(context);
    final safeUrl = sys06SafeBrowserSiteOrigin(pageUrl);
    if (safeUrl == null || pageRevision < 0) {
      throw const FormatException('The browser page locator is unavailable.');
    }
    final response = await client.saveBrowserResearchNote(
      domainId: context.domainId,
      title: title,
      markdown: markdown,
      requestId: requestId,
      payload: {
        'browser_note': {
          'schema': 'lumenis.browser-session-note/v1',
          'surface': 'SYS-06',
          'source_capture': 'NOT_IMPORTED',
          'source_verification': 'NOT_VERIFIED',
          'task_binding': 'UNBOUND',
          'locator': {
            'url': safeUrl,
            'title': _safeText(pageTitle, maximum: 300),
            'page_revision': pageRevision,
            'captured_at': capturedAt.toUtc().toIso8601String(),
          },
        },
      },
    );
    final result = response['result'];
    if (response['ok'] != true || result is! Map) {
      throw const LumenisCoreException(
        'The browser note was not confirmed by SavedWork.',
        errorCode: 'WORK_SAVE_UNCONFIRMED',
      );
    }
    final note = Sys06BrowserResearchNote.fromSavedWorkResult(
      Map<String, dynamic>.from(result),
    );
    if (note.version != 1 ||
        note.parentArtifactId != null ||
        note.parentSha256 != null) {
      throw const FormatException('A new browser note has an invalid version.');
    }
    await _requireResearchContext(context);
    return note;
  }

  @override
  Future<Sys06BrowserResearchNote> reviseResearchNote({
    required Sys06BrowserResearchContext context,
    required Sys06BrowserResearchNote parent,
    required String title,
    required String markdown,
    required String requestId,
    required String reason,
  }) async {
    await _requireResearchContext(context);
    final response = await client.reviseBrowserResearchNote(
      domainId: context.domainId,
      artifactId: parent.artifactId,
      requestId: requestId,
      expectedSha256: parent.sha256,
      reason: reason,
      expectedTitle: parent.title,
      title: title,
      expectedMarkdown: parent.markdown,
      markdown: markdown,
    );
    final result = response['result'];
    if (response['ok'] != true || result is! Map) {
      throw const LumenisCoreException(
        'The revised browser note was not confirmed by SavedWork.',
        errorCode: 'WORK_REVISION_UNCONFIRMED',
      );
    }
    final note = Sys06BrowserResearchNote.fromSavedWorkResult(
      Map<String, dynamic>.from(result),
    );
    if (note.workId != parent.workId ||
        note.version != parent.version + 1 ||
        note.parentArtifactId != parent.artifactId ||
        note.parentSha256 != parent.sha256 ||
        note.title != title ||
        note.markdown != markdown) {
      throw const FormatException('SavedWork did not confirm the new version.');
    }
    await _requireResearchContext(context);
    return note;
  }

  @override
  Future<Sys06BrowserSession> open() async =>
      Sys06BrowserSession.fromResponse(await client.openBrowserSession());

  @override
  Future<Sys06BrowserSession> readSession(String sessionId) async =>
      Sys06BrowserSession.fromResponse(await client.browserSession(sessionId));

  @override
  Future<Sys06BrowserLease> acquireHumanControl(String sessionId) async {
    final response = await client.acquireBrowserHumanControl(sessionId);
    final lease = Sys06BrowserLease.fromResponse(response);
    if (lease.humanActions.isEmpty) {
      await client.releaseBrowserHumanControl(
        sessionId: sessionId,
        leaseToken: lease.token,
      );
      throw const LumenisCoreException(
        'The server did not advertise a supported human browser action.',
        errorCode: 'BROWSER_HUMAN_ACTIONS_UNAVAILABLE',
      );
    }
    return lease;
  }

  @override
  Future<void> releaseHumanControl({
    required String sessionId,
    required String leaseToken,
  }) async {
    final response = await client.releaseBrowserHumanControl(
      sessionId: sessionId,
      leaseToken: leaseToken,
    );
    if (response['ok'] != true || response['released'] != true) {
      throw const LumenisCoreException(
        'The human browser lease was not released.',
        errorCode: 'BROWSER_HUMAN_LEASE_RELEASE_UNCONFIRMED',
      );
    }
  }

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
  Future<void> humanNavigate({
    required String sessionId,
    required String url,
    required String leaseToken,
    required LumenisBrowserFrameBinding frameBinding,
  }) async {
    final response = await client.navigateBrowserSessionWithHumanControl(
      sessionId: sessionId,
      url: url,
      leaseToken: leaseToken,
      frameBinding: frameBinding,
    );
    if (response['ok'] != true) {
      _requireActionSuccess(response, action: 'navigate');
    }
  }

  @override
  Future<void> humanAction({
    required String sessionId,
    required String action,
    required String leaseToken,
    required LumenisBrowserFrameBinding frameBinding,
    String value = '',
  }) async {
    final response = await client.executeBrowserHumanAction(
      sessionId: sessionId,
      action: action,
      leaseToken: leaseToken,
      frameBinding: frameBinding,
      value: value,
    );
    if (response['control_actor'] != 'HUMAN_DIRECT') {
      throw const LumenisCoreException(
        'The server did not confirm a direct human browser action.',
        errorCode: 'BROWSER_HUMAN_ACTOR_UNCONFIRMED',
      );
    }
    if (response['ok'] != true) {
      _requireActionSuccess(response, action: action);
    }
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

/// Returns only an HTTP(S) site origin for research-note metadata.
/// Credentials, explicit default ports, paths, queries and fragments are
/// deliberately omitted. Browser navigation continues to use the full URL.
String? sys06SafeBrowserSiteOrigin(Object? value) {
  if (value is! String || value.length > 2048) return null;
  final uri = Uri.tryParse(value.trim());
  if (uri == null ||
      (uri.scheme != 'http' && uri.scheme != 'https') ||
      uri.host.isEmpty) {
    return null;
  }
  final defaultPort = uri.scheme == 'https' ? 443 : 80;
  return Uri(
    scheme: uri.scheme,
    host: uri.host,
    port: uri.hasPort && uri.port != defaultPort ? uri.port : null,
  ).toString();
}
