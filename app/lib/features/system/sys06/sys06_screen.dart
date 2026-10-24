import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../../core/lumenis_core_client.dart';
import '../../../core/lumenis_theme.dart';
import '../../../platform/lumenis_external_view.dart';
import 'sys06_browser_repository.dart';
import 'sys06_page_context.dart';

/// SYSTEM's single-page controlled reader.
///
/// It displays a server-owned, permission-checked page frame.  It is not a
/// WebView; the user's installed browser opens only for an explicit view-original jump.
/// Human operation is limited to server-advertised lease actions. The captured
/// image itself is never treated as a coordinate input surface.
class Sys06Screen extends StatefulWidget {
  const Sys06Screen({required this.client, this.browserRepository, super.key});

  final LumenisCoreClient client;
  final Sys06BrowserRepository? browserRepository;

  @override
  State<Sys06Screen> createState() => _Sys06ScreenState();
}

class _Sys06ScreenState extends State<Sys06Screen> with WidgetsBindingObserver {
  late Sys06BrowserRepository _repository;
  late final TextEditingController _addressController;

  Sys06BrowserSession? _session;
  Sys06BrowserFrame? _frame;
  Sys06BrowserLease? _humanLease;
  _Sys06Notice _notice = _Sys06Notice.ready;
  int _generation = 0;
  int? _activeOperation;
  bool _busy = false;
  bool _stopping = false;
  bool _returning = false;
  StreamSubscription<Sys06BrowserFrame>? _frameStream;
  String? _frameStreamSessionId;
  bool _viewVisible = true;
  final List<Sys06BrowserSession> _tabs = <Sys06BrowserSession>[];
  bool _collapsed = false;
  bool _contextVisible = false;
  Key _contextOwnerKey = UniqueKey();

  @override
  void initState() {
    super.initState();
    _repository = _repositoryFor(widget);
    _addressController = TextEditingController();
    WidgetsBinding.instance.addObserver(this);
  }

  // Viewer presence follows real visibility: a covered route (tickers off)
  // or a backgrounded/hidden app ends the stream so the server records
  // USER_LEFT_VIEW; returning re-establishes it from a fresh frame.
  void _setViewVisible(bool visible) {
    visible = visible && !_collapsed;
    if (_viewVisible == visible) return;
    _viewVisible = visible;
    if (!visible) {
      _cancelFrameStream();
      return;
    }
    final session = _session;
    if (session != null && _frame != null) {
      _ensureFrameStream(session, _repository);
    }
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _setViewVisible(
      TickerMode.valuesOf(context).enabled &&
          WidgetsBinding.instance.lifecycleState != AppLifecycleState.paused &&
          WidgetsBinding.instance.lifecycleState != AppLifecycleState.hidden,
    );
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    _setViewVisible(
      state == AppLifecycleState.resumed &&
          TickerMode.valuesOf(context).enabled,
    );
  }

  @override
  void didUpdateWidget(covariant Sys06Screen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (identical(oldWidget.client, widget.client) &&
        identical(oldWidget.browserRepository, widget.browserRepository)) {
      return;
    }
    final priorSession = _session;
    final priorLease = _humanLease;
    final priorRepository = _repository;
    if (priorSession != null && priorLease != null) {
      unawaited(_releaseWithoutUi(priorRepository, priorSession, priorLease));
    }
    _generation++;
    _activeOperation = null;
    _repository = _repositoryFor(widget);
    _session = null;
    _frame = null;
    _humanLease = null;
    _notice = _Sys06Notice.ready;
    _busy = false;
    _stopping = false;
    _returning = false;
    _cancelFrameStream();
    _addressController.clear();
    _tabs.clear();
    _contextVisible = false;
    _collapsed = false;
    _contextOwnerKey = UniqueKey();
  }

  @override
  void dispose() {
    final session = _session;
    final lease = _humanLease;
    if (session != null && lease != null) {
      unawaited(_releaseWithoutUi(_repository, session, lease));
    }
    WidgetsBinding.instance.removeObserver(this);
    _cancelFrameStream();
    _addressController.dispose();
    super.dispose();
  }

  Future<void> _releaseWithoutUi(
    Sys06BrowserRepository repository,
    Sys06BrowserSession session,
    Sys06BrowserLease lease,
  ) async {
    if (repository is! Sys06BrowserHumanControlRepository) return;
    final controlRepository = repository as Sys06BrowserHumanControlRepository;
    try {
      await controlRepository.releaseHumanControl(
        sessionId: session.sessionId,
        leaseToken: lease.token,
      );
    } catch (_) {
      // The server lease is short-lived and still independently enforced.
    }
  }

  Future<void> _open() => _run((generation, repository) async {
    final session = await repository.open();
    if (!_isCurrent(generation, repository)) return;
    _adoptSession(session, clearFrame: true);
    await _readFrame(session, generation, repository);
  });

  Future<void> _navigate() => _run((generation, repository) async {
    final address = _addressController.text.trim();
    final parsed = Uri.tryParse(address);
    if (parsed == null ||
        parsed.host.isEmpty ||
        (parsed.scheme != 'https' && parsed.scheme != 'http') ||
        parsed.userInfo.isNotEmpty) {
      if (mounted) setState(() => _notice = _Sys06Notice.invalidAddress);
      return;
    }
    if (_session?.isRunning != true) {
      final opened = await repository.open();
      if (!_isCurrent(generation, repository)) return;
      _adoptSession(opened, clearFrame: true, updateAddress: false);
      await _readFrame(opened, generation, repository);
    }
    await _acquireControlFor(generation, repository);
    if (!_isCurrent(generation, repository)) return;
    final session = _session;
    final frame = _frame;
    final lease = _humanLease;
    if (repository is! Sys06BrowserHumanControlRepository ||
        session == null ||
        frame == null ||
        lease == null ||
        !_canHumanAction(session, lease, 'navigate')) {
      return;
    }
    final controlRepository = repository as Sys06BrowserHumanControlRepository;
    if (mounted) {
      setState(() {
        _frame = null;
        _notice = _Sys06Notice.navigating;
      });
    }
    Object? actionError;
    try {
      await controlRepository.humanNavigate(
        sessionId: session.sessionId,
        url: address,
        leaseToken: lease.token,
        frameBinding: frame.frame.binding,
      );
    } catch (error) {
      actionError = error;
    }
    if (!mounted ||
        !_isCurrentSession(generation, repository, session.sessionId)) {
      return;
    }
    final updated = await repository.readSession(session.sessionId);
    if (!_isCurrentSession(generation, repository, session.sessionId)) return;
    if (updated.humanControlActive != true || _isLeaseFailure(actionError)) {
      _humanLease = null;
      setState(() {
        _session = updated;
        _frame = null;
        _notice = actionError == null
            ? _Sys06Notice.controlUnavailable
            : _noticeForError(actionError);
      });
      return;
    }
    _adoptSession(
      updated,
      clearFrame: true,
      updateAddress: actionError == null,
    );
    if (_humanLease != null) {
      await _readFrame(updated, generation, repository);
    }
    if (actionError != null &&
        _isCurrentSession(generation, repository, session.sessionId)) {
      setState(() => _notice = _noticeForError(actionError!));
    }
  });

  Future<void> _humanAction(String action, {String value = ''}) => _run((
    generation,
    repository,
  ) async {
    if (repository is! Sys06BrowserHumanControlRepository) return;
    await _acquireControlFor(generation, repository);
    if (!_isCurrent(generation, repository)) return;
    final session = _session;
    final frame = _frame;
    final lease = _humanLease;
    final controlRepository = repository as Sys06BrowserHumanControlRepository;
    if (session != null &&
        lease != null &&
        !lease.expiresAt.isAfter(DateTime.now())) {
      await _refreshSessionAfterExpiredLease(generation, repository, session);
      return;
    }
    if (session == null ||
        frame == null ||
        lease == null ||
        !_canHumanAction(session, lease, action)) {
      return;
    }
    if (mounted) {
      setState(() {
        _frame = null;
        _notice = _Sys06Notice.navigating;
      });
    }
    Object? actionError;
    try {
      await controlRepository.humanAction(
        sessionId: session.sessionId,
        action: action,
        leaseToken: lease.token,
        frameBinding: frame.frame.binding,
        value: value,
      );
    } catch (error) {
      actionError = error;
    }
    if (!_isCurrentSession(generation, repository, session.sessionId)) return;
    final updated = await repository.readSession(session.sessionId);
    if (!_isCurrentSession(generation, repository, session.sessionId)) return;
    if (updated.humanControlActive != true || _isLeaseFailure(actionError)) {
      _humanLease = null;
      setState(() {
        _session = updated;
        _frame = null;
        _notice = actionError == null
            ? _Sys06Notice.controlUnavailable
            : _noticeForError(actionError);
      });
      return;
    }
    _adoptSession(updated, clearFrame: true);
    await _readFrame(updated, generation, repository);
    if (actionError != null &&
        _isCurrentSession(generation, repository, session.sessionId)) {
      setState(() => _notice = _noticeForError(actionError!));
    }
  });

  Future<void> _openVisibleLinks() => _run((generation, repository) async {
    if (repository is! Sys06BrowserVisibleLinksRepository) {
      if (mounted) setState(() => _notice = _Sys06Notice.unavailable);
      return;
    }
    final linksRepository = repository as Sys06BrowserVisibleLinksRepository;
    final session = _session;
    final frame = _frame;
    final lease = _humanLease;
    if (session == null || frame == null || lease == null) {
      if (mounted) setState(() => _notice = _Sys06Notice.controlUnavailable);
      return;
    }
    if (!lease.expiresAt.isAfter(DateTime.now())) {
      await _refreshSessionAfterExpiredLease(generation, repository, session);
      return;
    }
    if (!_canHumanAction(session, lease, 'open_link') ||
        !_hasFreshBoundFrame(session, frame)) {
      if (mounted) setState(() => _notice = _Sys06Notice.controlUnavailable);
      return;
    }
    final frameBinding = frame.frame.binding;
    final List<LumenisBrowserVisibleLink> links;
    try {
      links = await linksRepository.readVisibleLinks(
        sessionId: session.sessionId,
        leaseToken: lease.token,
        frameBinding: frameBinding,
      );
    } catch (error) {
      if (_isLeaseFailure(error) &&
          _isCurrentSession(generation, repository, session.sessionId)) {
        await _refreshSessionAfterExpiredLease(generation, repository, session);
        return;
      }
      rethrow;
    }
    if (!mounted ||
        !_isCurrentSession(generation, repository, session.sessionId)) {
      return;
    }
    if (!identical(_session, session) ||
        !identical(_frame, frame) ||
        !identical(_humanLease, lease) ||
        !_hasFreshBoundFrame(session, frame) ||
        !_canHumanAction(session, lease, 'open_link')) {
      return;
    }
    final selected = await showDialog<LumenisBrowserVisibleLink>(
      context: context,
      builder: (dialogContext) => _BrowserVisibleLinksDialog(
        copy: _Sys06Copy.of(dialogContext),
        links: links,
      ),
    );
    if (selected == null ||
        !_isCurrentSession(generation, repository, session.sessionId)) {
      return;
    }
    if (!lease.expiresAt.isAfter(DateTime.now())) {
      await _refreshSessionAfterExpiredLease(generation, repository, session);
      return;
    }
    if (!links.any((link) => link.linkId == selected.linkId) ||
        !identical(_session, session) ||
        !identical(_frame, frame) ||
        !identical(_humanLease, lease) ||
        !_hasFreshBoundFrame(session, frame) ||
        !_canHumanAction(session, lease, 'open_link')) {
      return;
    }
    setState(() {
      _frame = null;
      _notice = _Sys06Notice.navigating;
    });
    late final Sys06BrowserSession updated;
    try {
      updated = await linksRepository.openVisibleLink(
        sessionId: session.sessionId,
        leaseToken: lease.token,
        linkId: selected.linkId,
        frameBinding: frameBinding,
      );
    } catch (error) {
      if (_isLeaseFailure(error) &&
          _isCurrentSession(generation, repository, session.sessionId)) {
        _humanLease = null;
        await _refreshSessionAfterExpiredLease(generation, repository, session);
        return;
      }
      rethrow;
    }
    if (!_isCurrentSession(generation, repository, session.sessionId)) return;
    if (updated.humanControlActive != true) _humanLease = null;
    _adoptSession(updated, clearFrame: true);
    await _readFrame(updated, generation, repository);
  });

  bool _hasFreshBoundFrame(
    Sys06BrowserSession session,
    Sys06BrowserFrame frame,
  ) {
    final value = frame.frame;
    return session.isRunning &&
        session.targetId != null &&
        value.targetId == session.targetId &&
        value.pageRevision == session.pageRevision &&
        value.frameId.isNotEmpty &&
        value.viewportWidth > 0 &&
        value.viewportHeight > 0 &&
        value.devicePixelRatio.isFinite &&
        value.devicePixelRatio > 0;
  }

  Future<void> _refreshFrame() => _run((generation, repository) async {
    final session = _session;
    if (session == null) return;
    final lease = _humanLease;
    if (lease != null && !lease.expiresAt.isAfter(DateTime.now())) {
      _humanLease = null;
    }
    final updated = await repository.readSession(session.sessionId);
    if (!_isCurrentSession(generation, repository, session.sessionId)) return;
    if (updated.humanControlActive != true) _humanLease = null;
    _adoptSession(updated, clearFrame: true);
    await _readFrame(updated, generation, repository);
  });

  Future<void> _refreshSessionAfterExpiredLease(
    int generation,
    Sys06BrowserRepository repository,
    Sys06BrowserSession session,
  ) async {
    if (!_isCurrentSession(generation, repository, session.sessionId)) return;
    _humanLease = null;
    setState(() {
      _frame = null;
      _notice = _Sys06Notice.controlUnavailable;
    });
    final updated = await repository.readSession(session.sessionId);
    if (!_isCurrentSession(generation, repository, session.sessionId)) return;
    _adoptSession(updated, clearFrame: true);
    await _readFrame(updated, generation, repository);
    if (updated.humanControlActive == true &&
        _isCurrentSession(generation, repository, session.sessionId)) {
      setState(() => _notice = _Sys06Notice.controlUnavailable);
    }
  }

  Future<void> _stop() async {
    final session = _session;
    if (session == null || _stopping) return;
    final repository = _repository;
    final generation = ++_generation;
    _activeOperation = null;
    _cancelFrameStream();
    setState(() {
      _busy = false;
      _stopping = true;
      _frame = null;
      _notice = _Sys06Notice.stopping;
    });
    try {
      await repository.stop(session.sessionId);
      if (!_isCurrentSession(generation, repository, session.sessionId)) return;
      setState(() {
        _tabs.removeWhere((tab) => tab.sessionId == session.sessionId);
        _session = null;
        _humanLease = null;
        _frame = null;
        _addressController.clear();
        _notice = _Sys06Notice.closed;
        _stopping = false;
      });
    } catch (error) {
      if (!_isCurrentSession(generation, repository, session.sessionId)) return;
      setState(() {
        _frame = null;
        _notice = _noticeForError(error);
        _stopping = false;
      });
    }
  }

  Future<void> _acquireHumanControl() => _run(_acquireControlFor);

  Future<void> _acquireControlFor(
    int generation,
    Sys06BrowserRepository repository,
  ) async {
    final currentLease = _humanLease;
    if (currentLease != null &&
        currentLease.expiresAt.isAfter(DateTime.now()) &&
        _session?.humanControlActive == true) {
      return;
    }
    if (currentLease != null && _session != null) {
      await _refreshSessionAfterExpiredLease(generation, repository, _session!);
      if (!_isCurrent(generation, repository)) return;
    }
    if (repository is! Sys06BrowserHumanControlRepository) {
      if (mounted) setState(() => _notice = _Sys06Notice.controlUnavailable);
      return;
    }
    final controlRepository = repository as Sys06BrowserHumanControlRepository;
    final session = _session;
    if (session == null ||
        !session.isRunning ||
        !session.humanActionsRequireLease ||
        session.humanActions.isEmpty ||
        session.humanControlActive != false) {
      if (mounted) setState(() => _notice = _Sys06Notice.controlUnavailable);
      return;
    }
    final lease = await controlRepository.acquireHumanControl(
      session.sessionId,
    );
    if (!_isCurrentSession(generation, repository, session.sessionId)) {
      await _releaseWithoutUi(repository, session, lease);
      return;
    }
    _humanLease = lease;
    late final Sys06BrowserSession updated;
    try {
      updated = await repository.readSession(session.sessionId);
    } catch (_) {
      try {
        await controlRepository.releaseHumanControl(
          sessionId: session.sessionId,
          leaseToken: lease.token,
        );
        _humanLease = null;
      } catch (_) {
        // Keep the short-lived token in memory so the user can retry release.
      }
      rethrow;
    }
    if (!_isCurrentSession(generation, repository, session.sessionId)) {
      await _releaseWithoutUi(repository, session, lease);
      return;
    }
    final commonActions = lease.humanActions.intersection(updated.humanActions);
    if (updated.humanControlActive != true || commonActions.isEmpty) {
      _humanLease = null;
      await _releaseWithoutUi(repository, session, lease);
      if (mounted) {
        setState(() {
          _session = updated;
          _frame = null;
          _notice = _Sys06Notice.controlUnavailable;
        });
      }
      return;
    }
    _adoptSession(updated, clearFrame: true, updateAddress: false);
    await _readFrame(updated, generation, repository);
  }

  Future<void> _releaseHumanControl() => _run((generation, repository) async {
    final session = _session;
    final lease = _humanLease;
    if (session == null || lease == null) return;
    if (repository is! Sys06BrowserHumanControlRepository) {
      if (mounted) setState(() => _notice = _Sys06Notice.controlUnavailable);
      return;
    }
    final controlRepository = repository as Sys06BrowserHumanControlRepository;
    setState(() {
      _frame = null;
      _notice = _Sys06Notice.releasingControl;
    });
    try {
      await controlRepository.releaseHumanControl(
        sessionId: session.sessionId,
        leaseToken: lease.token,
      );
    } catch (error) {
      if (!_isLeaseFailure(error)) rethrow;
    }
    if (!_isCurrentSession(generation, repository, session.sessionId)) return;
    _humanLease = null;
    final updated = await repository.readSession(session.sessionId);
    if (!_isCurrentSession(generation, repository, session.sessionId)) return;
    setState(() {
      _session = updated;
      _frame = null;
      _notice = _Sys06Notice.controlReleased;
    });
    await _readFrame(updated, generation, repository);
  });

  Future<void> _returnToTask() async {
    if (_busy || _stopping || _returning) return;
    final session = _session;
    final lease = _humanLease;
    setState(() => _returning = true);
    try {
      if (session != null && lease != null) {
        if (_repository is! Sys06BrowserHumanControlRepository) {
          throw StateError(
            'The active Browser control lease cannot be released.',
          );
        }
        final controlRepository =
            _repository as Sys06BrowserHumanControlRepository;
        await controlRepository.releaseHumanControl(
          sessionId: session.sessionId,
          leaseToken: lease.token,
        );
        _humanLease = null;
        _frame = null;
      }
      if (!mounted) return;
      final navigator = Navigator.of(context);
      if (navigator.canPop()) {
        await navigator.maybePop();
      } else {
        setState(() => _notice = _Sys06Notice.returnUnavailable);
      }
    } catch (error) {
      if (mounted) setState(() => _notice = _noticeForError(error));
    } finally {
      if (mounted) setState(() => _returning = false);
    }
  }

  Future<void> _openResearchNotes() async {
    final session = _session;
    final frame = _frame?.frame;
    final locator =
        session != null &&
            session.isRunning &&
            frame != null &&
            session.currentUrl.isNotEmpty &&
            frame.pageRevision == session.pageRevision &&
            frame.targetId == session.targetId
        ? _Sys06BrowserNoteLocator(
            url: session.currentUrl,
            title: session.currentTitle,
            pageRevision: frame.pageRevision,
            capturedAt: frame.capturedAt,
          )
        : null;
    final notesRepository = _repository is Sys06BrowserResearchRepository
        ? _repository as Sys06BrowserResearchRepository
        : CoreSys06BrowserRepository(client: widget.client);
    await showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (dialogContext) => _BrowserResearchNotesDialog(
        repository: notesRepository,
        currentPage: locator,
      ),
    );
  }

  void _openPageContext() => setState(() => _contextVisible = !_contextVisible);

  Future<Map<String, dynamic>> _readPageContext(String question) async {
    final session = _session;
    final client = widget.client;
    final repository = _repository;
    if (session == null ||
        !session.isRunning ||
        session.targetId == null ||
        _busy) {
      throw const LumenisCoreException(
        'Open a page first.',
        errorCode: 'BROWSER_CONTEXT_PAGE_REQUIRED',
      );
    }
    bool isCurrent() =>
        mounted &&
        identical(client, widget.client) &&
        identical(repository, _repository) &&
        _session?.isRunning == true &&
        _session?.sessionId == session.sessionId &&
        _session?.targetId == session.targetId &&
        _session?.pageRevision == session.pageRevision;
    if (_humanLease != null) await _releaseHumanControl();
    if (!isCurrent() || _humanLease != null) {
      throw const LumenisCoreException(
        'The page changed.',
        errorCode: 'BROWSER_EXTRACTION_PAGE_CHANGED',
      );
    }
    final result = await client.readBrowserPageContext(
      sessionId: session.sessionId,
      targetId: session.targetId!,
      pageRevision: session.pageRevision,
      question: question,
    );
    if (!isCurrent() ||
        result['metadata']?['page_revision'] != session.pageRevision) {
      throw const LumenisCoreException(
        'The page changed.',
        errorCode: 'BROWSER_EXTRACTION_PAGE_CHANGED',
      );
    }
    return result;
  }

  bool _canHumanAction(
    Sys06BrowserSession session,
    Sys06BrowserLease lease,
    String action,
  ) =>
      session.isRunning &&
      session.humanActionsRequireLease &&
      session.humanControlActive == true &&
      session.humanActions.contains(action) &&
      lease.humanActions.contains(action) &&
      lease.expiresAt.isAfter(DateTime.now());

  bool _isLeaseFailure(Object? error) {
    if (error is! LumenisCoreException) return false;
    return const {
      'BROWSER_HUMAN_LEASE_REQUIRED',
      'BROWSER_HUMAN_LEASE_INVALID',
      'BROWSER_HUMAN_LEASE_EXPIRED',
      'BROWSER_HUMAN_CONTROL_ACTIVE',
    }.contains(error.errorCode);
  }

  Future<void> _readFrame(
    Sys06BrowserSession expected,
    int generation,
    Sys06BrowserRepository repository,
  ) async {
    if (!expected.allowedActions.contains('frame') ||
        expected.targetId == null) {
      if (_isCurrentSession(generation, repository, expected.sessionId)) {
        setState(() => _notice = _Sys06Notice.enterAddress);
      }
      return;
    }
    try {
      final frame = await repository.readFrame(expected.sessionId);
      if (!_isCurrentSession(generation, repository, expected.sessionId)) {
        return;
      }
      final current = _session;
      if (current == null ||
          frame.frame.targetId != current.targetId ||
          frame.frame.pageRevision != current.pageRevision) {
        return;
      }
      setState(() {
        _frame = frame;
        _notice = _Sys06Notice.previewReady;
      });
      _ensureFrameStream(current, repository);
    } catch (error) {
      if (!_isCurrentSession(generation, repository, expected.sessionId)) {
        return;
      }
      setState(() {
        _frame = null;
        _notice = error is FormatException
            ? _Sys06Notice.frameEmpty
            : _noticeForError(error);
      });
    }
  }

  /// Live frames: the server pushes fresh frames of this isolated session over
  /// SSE; the screen swaps them in place (gapless).  The stream only runs for
  /// read-only viewing; during human control each lease action reads its own
  /// bound frame, so frames are never mixed with a lease binding.
  void _cancelFrameStream() {
    final subscription = _frameStream;
    _frameStream = null;
    _frameStreamSessionId = null;
    if (subscription != null) unawaited(subscription.cancel());
  }

  /// The server ended the stream (stopped, expired, unauthorized, navigated,
  /// human control) or the connection failed: never keep showing the last
  /// frame as the current page.
  void _frameStreamEnded(String sessionId) {
    if (_frameStreamSessionId != sessionId) return;
    _frameStream = null;
    _frameStreamSessionId = null;
    if (!mounted || _humanLease != null || _stopping) return;
    setState(() {
      _frame = null;
      _notice = _Sys06Notice.unavailable;
    });
  }

  void _ensureFrameStream(
    Sys06BrowserSession session,
    Sys06BrowserRepository repository,
  ) {
    if (repository is! Sys06BrowserFrameStreamRepository) return;
    if (_humanLease != null ||
        !session.isRunning ||
        _stopping ||
        !_viewVisible) {
      _cancelFrameStream();
      return;
    }
    if (_frameStream != null && _frameStreamSessionId == session.sessionId) {
      return;
    }
    _cancelFrameStream();
    final streamRepository = repository as Sys06BrowserFrameStreamRepository;
    final sessionId = session.sessionId;
    _frameStreamSessionId = sessionId;
    _frameStream = streamRepository
        .watchFrames(sessionId)
        .listen(
          (frame) {
            final current = _session;
            if (!mounted ||
                !identical(_repository, repository) ||
                current == null ||
                current.sessionId != sessionId ||
                !current.isRunning ||
                _humanLease != null ||
                _stopping) {
              _cancelFrameStream();
              return;
            }
            if (_busy ||
                frame.frame.targetId != current.targetId ||
                frame.frame.pageRevision != current.pageRevision) {
              return;
            }
            setState(() {
              _frame = frame;
              _notice = _Sys06Notice.previewReady;
            });
          },
          onError: (Object _) => _frameStreamEnded(sessionId),
          onDone: () => _frameStreamEnded(sessionId),
          cancelOnError: true,
        );
  }

  Future<void> _run(
    Future<void> Function(int generation, Sys06BrowserRepository repository)
    operation,
  ) async {
    if (_busy || _stopping || _returning) return;
    final generation = ++_generation;
    final repository = _repository;
    _activeOperation = generation;
    setState(() => _busy = true);
    try {
      await operation(generation, repository);
    } catch (error) {
      if (_isCurrent(generation, repository)) {
        setState(() {
          if (_isLeaseFailure(error)) _humanLease = null;
          _frame = null;
          _notice = _noticeForError(error);
        });
      }
    } finally {
      if (mounted && _activeOperation == generation) {
        _activeOperation = null;
        setState(() => _busy = false);
      }
    }
  }

  bool _isCurrent(int generation, Sys06BrowserRepository repository) =>
      mounted &&
      generation == _generation &&
      identical(repository, _repository);

  bool _isCurrentSession(
    int generation,
    Sys06BrowserRepository repository,
    String sessionId,
  ) => _isCurrent(generation, repository) && _session?.sessionId == sessionId;

  Sys06BrowserRepository _repositoryFor(Sys06Screen source) =>
      source.browserRepository ??
      CoreSys06BrowserRepository(client: source.client);

  void _adoptSession(
    Sys06BrowserSession session, {
    required bool clearFrame,
    bool updateAddress = true,
  }) {
    setState(() {
      _session = session;
      final tabIndex = _tabs.indexWhere(
        (tab) => tab.sessionId == session.sessionId,
      );
      if (tabIndex < 0) {
        _tabs.add(session);
      } else {
        _tabs[tabIndex] = session;
      }
      if (clearFrame) _frame = null;
      _notice = session.targetId == null
          ? _Sys06Notice.enterAddress
          : _Sys06Notice.reading;
      // The server strips query/fragment material before it reaches this field.
      // A raw typed address is never stored after navigation succeeds.
      if (updateAddress && session.currentUrl.isNotEmpty) {
        _addressController.text = session.currentUrl;
      }
    });
  }

  Future<void> _switchTab(Sys06BrowserSession tab) {
    if (_humanLease != null || tab.sessionId == _session?.sessionId) {
      return Future<void>.value();
    }
    _cancelFrameStream();
    return _run((generation, repository) async {
      final current = await repository.readSession(tab.sessionId);
      if (!_isCurrent(generation, repository)) return;
      _adoptSession(current, clearFrame: true);
      await _readFrame(current, generation, repository);
    });
  }

  Future<void> _closeTab(Sys06BrowserSession tab) async {
    if (tab.sessionId == _session?.sessionId) {
      await _stop();
      if (mounted && _session == null && _tabs.isNotEmpty) {
        await _switchTab(_tabs.last);
      }
      return;
    }
    await _run((generation, repository) async {
      await repository.stop(tab.sessionId);
      if (!_isCurrent(generation, repository)) return;
      setState(
        () => _tabs.removeWhere((item) => item.sessionId == tab.sessionId),
      );
    });
  }

  // Optional user-chosen jump; collection and login stay in the built-in browser.
  Future<void> _viewOriginalExternally() async {
    final url = Uri.tryParse(_session?.currentUrl ?? '');
    if (url == null) return;
    final opened = await openLumenisExternalView(url);
    if (!opened) {
      await Clipboard.setData(ClipboardData(text: url.toString()));
    }
  }

  _Sys06Notice _noticeForError(Object error) {
    if (error is LumenisCoreException) {
      if (error.statusCode == 401 || error.statusCode == 403) {
        return _Sys06Notice.accessUnavailable;
      }
      return switch (error.errorCode) {
        'BROWSER_LOCAL_CORE_REQUIRED' => _Sys06Notice.localCoreRequired,
        'BROWSER_NAVIGATION_POLICY_DENIED' => _Sys06Notice.navigationRestricted,
        'BROWSER_FRAME_PENDING' => _Sys06Notice.framePending,
        'BROWSER_FRAME_EMPTY' => _Sys06Notice.frameEmpty,
        'BROWSER_CAPACITY_OCCUPIED' => _Sys06Notice.capacityOccupied,
        'BROWSER_HUMAN_ACTIONS_UNAVAILABLE' => _Sys06Notice.controlUnavailable,
        'BROWSER_HUMAN_CONTROL_UNAVAILABLE' => _Sys06Notice.controlUnavailable,
        'BROWSER_HUMAN_ACTION_NOT_ALLOWED' => _Sys06Notice.controlUnavailable,
        'BROWSER_FRAME_BINDING_REQUIRED' ||
        'BROWSER_FRAME_STALE' => _Sys06Notice.framePending,
        'BROWSER_LINK_STALE' => _Sys06Notice.linkStale,
        'BROWSER_HUMAN_LEASE_REQUIRED' ||
        'BROWSER_HUMAN_LEASE_INVALID' ||
        'BROWSER_HUMAN_LEASE_EXPIRED' => _Sys06Notice.controlUnavailable,
        'BROWSER_PERMISSION_DENIED' => _Sys06Notice.accessUnavailable,
        'BROWSER_ACTOR_REQUIRED' => _Sys06Notice.accessUnavailable,
        _ => _Sys06Notice.unavailable,
      };
    }
    return _Sys06Notice.unavailable;
  }

  @override
  Widget build(BuildContext context) {
    final copy = _Sys06Copy.of(context);
    final theme = LumenisTheme.of(context);
    return ColoredBox(
      color: theme.canvas,
      child: SafeArea(
        child: LayoutBuilder(
          builder: (context, constraints) {
            final wide = constraints.maxWidth >= 840;
            final panelWidth = wide
                ? (constraints.maxWidth * .3).clamp(320.0, 390.0)
                : constraints.maxWidth;
            final preview = _ReaderPreview(
              copy: copy,
              frame: _frame,
              notice: _notice,
              busy: _busy || _stopping,
              onRefresh: _refreshFrame,
            );
            final panel = SizedBox(
              width: panelWidth,
              child: ColoredBox(
                color: theme.surface.withValues(alpha: 1),
                child: Sys06PageContext(
                  key: _contextOwnerKey,
                  embedded: true,
                  read: _readPageContext,
                  pageIdentity:
                      '${_session?.sessionId}:${_session?.targetId}:${_session?.pageRevision}',
                  onClose: _openPageContext,
                ),
              ),
            );
            return Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Padding(
                  padding: const EdgeInsets.fromLTRB(8, 4, 8, 0),
                  child: _ReaderTabs(
                    copy: copy,
                    tabs: _tabs,
                    activeSessionId: _session?.sessionId,
                    collapsed: _collapsed,
                    busy: _busy || _stopping,
                    canViewExternally:
                        _session?.currentUrl.startsWith('http') == true,
                    onSelect: _switchTab,
                    onClose: _closeTab,
                    onNewTab: _open,
                    onToggleCollapsed: () {
                      setState(() => _collapsed = !_collapsed);
                      _setViewVisible(!_collapsed);
                    },
                    onViewExternally: _viewOriginalExternally,
                  ),
                ),
                if (!_collapsed) ...[
                  _ReaderControls(
                    copy: copy,
                    addressController: _addressController,
                    session: _session,
                    frame: _frame,
                    busy: _busy || _stopping,
                    stopping: _stopping,
                    returning: _returning,
                    lease: _humanLease,
                    onOpen: _open,
                    onNavigate: _navigate,
                    onAcquireControl: _acquireHumanControl,
                    onReleaseControl: _releaseHumanControl,
                    onHumanAction: _humanAction,
                    onOpenPageLinks: _openVisibleLinks,
                    onRefreshFrame: _refreshFrame,
                    onStop: _stop,
                    onReturn: _returnToTask,
                    onResearchNotes: _openResearchNotes,
                    onReadPage: _openPageContext,
                  ),
                  SizedBox(
                    height: 2,
                    child: _busy || _stopping
                        ? LinearProgressIndicator(color: theme.accent)
                        : const SizedBox.shrink(),
                  ),
                  if (_notice.isFailure)
                    Padding(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 16,
                        vertical: 6,
                      ),
                      child: Semantics(
                        liveRegion: true,
                        child: Text(
                          copy.notice(_notice, session: _session),
                          key: const ValueKey('sys06-status'),
                          style: TextStyle(color: theme.caution),
                        ),
                      ),
                    ),
                  Divider(height: 1, thickness: 1, color: theme.line),
                ],
                Expanded(
                  key: const ValueKey('sys06-reader-content'),
                  child: Stack(
                    fit: StackFit.expand,
                    children: [
                      Positioned.fill(
                        right: wide && _contextVisible ? panelWidth : 0,
                        child: Offstage(
                          offstage: _collapsed || (!wide && _contextVisible),
                          child: ExcludeFocus(
                            excluding: _collapsed || (!wide && _contextVisible),
                            child: preview,
                          ),
                        ),
                      ),
                      Positioned(
                        top: 0,
                        bottom: 0,
                        right: 0,
                        width: panelWidth,
                        child: Offstage(
                          offstage: _collapsed || !_contextVisible,
                          child: ExcludeFocus(
                            excluding: _collapsed || !_contextVisible,
                            child: DecoratedBox(
                              decoration: BoxDecoration(
                                border: Border(
                                  left: BorderSide(color: theme.line),
                                ),
                              ),
                              child: panel,
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            );
          },
        ),
      ),
    );
  }
}

class _ReaderTabs extends StatelessWidget {
  const _ReaderTabs({
    required this.copy,
    required this.tabs,
    required this.activeSessionId,
    required this.collapsed,
    required this.busy,
    required this.canViewExternally,
    required this.onSelect,
    required this.onClose,
    required this.onNewTab,
    required this.onToggleCollapsed,
    required this.onViewExternally,
  });

  final _Sys06Copy copy;
  final List<Sys06BrowserSession> tabs;
  final String? activeSessionId;
  final bool collapsed;
  final bool busy;
  final bool canViewExternally;
  final ValueChanged<Sys06BrowserSession> onSelect;
  final ValueChanged<Sys06BrowserSession> onClose;
  final VoidCallback onNewTab;
  final VoidCallback onToggleCollapsed;
  final VoidCallback onViewExternally;

  String _label(Sys06BrowserSession tab) {
    if (tab.currentTitle.isNotEmpty) return tab.currentTitle;
    final host = Uri.tryParse(tab.currentUrl)?.host ?? '';
    return host.isNotEmpty ? host : copy.text('tab.new');
  }

  @override
  Widget build(BuildContext context) {
    final theme = LumenisTheme.of(context);
    return Row(
      children: [
        Expanded(
          child: SingleChildScrollView(
            key: const ValueKey('sys06-tabs'),
            scrollDirection: Axis.horizontal,
            child: Row(
              children: [
                for (final tab in tabs)
                  Padding(
                    padding: const EdgeInsets.only(right: 3),
                    child: _BrowserTab(
                      key: ValueKey('sys06-tab-${tab.sessionId}'),
                      selected: tab.sessionId == activeSessionId,
                      label: _label(tab),
                      onPressed: busy ? null : () => onSelect(tab),
                      onClose: busy ? null : () => onClose(tab),
                      closeLabel: copy.text('tab.close'),
                    ),
                  ),
                IconButton(
                  tooltip: copy.text('tab.add'),
                  key: const ValueKey('sys06-tab-new'),
                  onPressed: busy ? null : onNewTab,
                  icon: const Icon(Icons.add_rounded),
                ),
              ],
            ),
          ),
        ),
        IconButton(
          tooltip: copy.text('viewExternal'),
          key: const ValueKey('sys06-view-external'),
          onPressed: canViewExternally ? onViewExternally : null,
          icon: Icon(Icons.open_in_new_rounded, color: theme.muted),
        ),
        IconButton(
          tooltip: copy.text(collapsed ? 'expand' : 'collapse'),
          key: const ValueKey('sys06-collapse'),
          onPressed: onToggleCollapsed,
          icon: Icon(
            collapsed ? Icons.unfold_more_rounded : Icons.unfold_less_rounded,
          ),
        ),
      ],
    );
  }
}

class _BrowserTab extends StatelessWidget {
  const _BrowserTab({
    super.key,
    required this.label,
    required this.selected,
    required this.onPressed,
    required this.onClose,
    required this.closeLabel,
  });

  final String label;
  final bool selected;
  final VoidCallback? onPressed;
  final VoidCallback? onClose;
  final String closeLabel;

  @override
  Widget build(BuildContext context) {
    final palette = LumenisTheme.of(context);
    return Material(
      color: selected
          ? palette.surface.withValues(alpha: 1)
          : Colors.transparent,
      borderRadius: const BorderRadius.vertical(top: Radius.circular(10)),
      child: SizedBox(
        width: 228,
        height: 42,
        child: Row(
          children: [
            Expanded(
              child: Semantics(
                selected: selected,
                child: InkWell(
                  onTap: onPressed,
                  borderRadius: const BorderRadius.only(
                    topLeft: Radius.circular(10),
                  ),
                  child: Padding(
                    padding: const EdgeInsets.only(
                      left: 14,
                      top: 11,
                      bottom: 11,
                    ),
                    child: Row(
                      children: [
                        Icon(Icons.language, size: 16, color: palette.muted),
                        const SizedBox(width: 9),
                        Expanded(
                          child: Text(
                            label,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              fontSize: 12,
                              color: selected
                                  ? palette.foreground
                                  : palette.muted,
                              fontWeight: selected
                                  ? FontWeight.w600
                                  : FontWeight.w400,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
            IconButton(
              tooltip: closeLabel,
              onPressed: onClose,
              icon: const Icon(Icons.close, size: 16),
            ),
          ],
        ),
      ),
    );
  }
}

class _ReaderControls extends StatelessWidget {
  const _ReaderControls({
    required this.copy,
    required this.addressController,
    required this.session,
    required this.frame,
    required this.busy,
    required this.stopping,
    required this.returning,
    required this.lease,
    required this.onOpen,
    required this.onNavigate,
    required this.onAcquireControl,
    required this.onReleaseControl,
    required this.onHumanAction,
    required this.onOpenPageLinks,
    required this.onRefreshFrame,
    required this.onStop,
    required this.onReturn,
    required this.onResearchNotes,
    required this.onReadPage,
  });

  final _Sys06Copy copy;
  final TextEditingController addressController;
  final Sys06BrowserSession? session;
  final Sys06BrowserFrame? frame;
  final bool busy;
  final bool stopping;
  final bool returning;
  final Sys06BrowserLease? lease;
  final VoidCallback onOpen;
  final VoidCallback onNavigate;
  final VoidCallback onAcquireControl;
  final VoidCallback onReleaseControl;
  final Future<void> Function(String action, {String value}) onHumanAction;
  final VoidCallback onOpenPageLinks;
  final VoidCallback onRefreshFrame;
  final VoidCallback onStop;
  final VoidCallback onReturn;
  final VoidCallback onResearchNotes;
  final VoidCallback onReadPage;

  @override
  Widget build(BuildContext context) {
    final theme = LumenisTheme.of(context);
    final active = session;
    final hasLease =
        lease != null &&
        lease!.expiresAt.isAfter(DateTime.now()) &&
        active?.humanControlActive == true;
    bool canControl(String action) =>
        !busy &&
        active?.isRunning == true &&
        frame != null &&
        (hasLease || active?.humanControlActive == false) &&
        active!.humanActions.contains(action) &&
        (!hasLease || lease!.humanActions.contains(action));
    final canAcquire =
        !busy &&
        active?.isRunning == true &&
        active?.humanControlActive == false &&
        lease == null;
    Widget control(
      String key,
      String label,
      IconData icon,
      VoidCallback? action,
    ) => IconButton(
      key: ValueKey(key),
      tooltip: copy.text(label),
      onPressed: action,
      visualDensity: VisualDensity.compact,
      icon: Icon(icon, size: 19),
    );
    final navigation = [
      control(
        'sys06-back',
        'back',
        Icons.arrow_back_rounded,
        canControl('back') ? () => onHumanAction('back') : null,
      ),
      control(
        'sys06-forward',
        'forward',
        Icons.arrow_forward_rounded,
        canControl('forward') ? () => onHumanAction('forward') : null,
      ),
      control(
        'sys06-reload',
        'reload',
        Icons.refresh_rounded,
        canControl('reload') ? () => onHumanAction('reload') : null,
      ),
    ];
    return ColoredBox(
      color: theme.surface.withValues(alpha: 1),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(8, 6, 8, 6),
        child: Column(
          children: [
            Row(
              children: [
                if (MediaQuery.sizeOf(context).width >= 650) ...navigation,
                Expanded(
                  child: TextField(
                    key: const ValueKey('sys06-address'),
                    controller: addressController,
                    keyboardType: TextInputType.url,
                    textInputAction: TextInputAction.go,
                    autocorrect: false,
                    enableSuggestions: false,
                    onSubmitted: (_) => onNavigate(),
                    decoration: InputDecoration(
                      isDense: true,
                      filled: true,
                      fillColor: theme.surfaceRaised.withValues(alpha: 1),
                      labelText: copy.text('address'),
                      floatingLabelBehavior: FloatingLabelBehavior.never,
                      hintText: copy.text('addressHint'),
                      contentPadding: const EdgeInsets.symmetric(
                        horizontal: 12,
                        vertical: 10,
                      ),
                      prefixIcon: const Icon(Icons.public_rounded, size: 18),
                      suffixIcon: control(
                        'sys06-go',
                        'go',
                        Icons.arrow_forward_rounded,
                        busy ? null : onNavigate,
                      ),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(9),
                        borderSide: BorderSide.none,
                      ),
                    ),
                  ),
                ),
                control(
                  'sys06-read-page',
                  'readPage',
                  Icons.chat_bubble_outline_rounded,
                  onReadPage,
                ),
                PopupMenuButton<String>(
                  key: const ValueKey('sys06-more'),
                  tooltip: copy.text('more'),
                  icon: const Icon(Icons.more_horiz),
                  onSelected: (value) {
                    switch (value) {
                      case 'notes':
                        onResearchNotes();
                      case 'stop':
                        onStop();
                      case 'return':
                        onReturn();
                      case 'links':
                        onOpenPageLinks();
                      case 'refresh':
                        onRefreshFrame();
                    }
                  },
                  itemBuilder: (_) => [
                    PopupMenuItem(
                      key: const ValueKey('sys06-research-notes'),
                      value: 'notes',
                      child: Text(copy.text('researchNotes')),
                    ),
                    PopupMenuItem(
                      value: 'links',
                      enabled: canControl('open_link'),
                      child: Text(copy.text('pageLinks')),
                    ),
                    PopupMenuItem(
                      key: const ValueKey('sys06-refresh-frame'),
                      value: 'refresh',
                      enabled: !busy && active != null,
                      child: Text(copy.text('refreshPreview')),
                    ),
                    PopupMenuItem(
                      key: const ValueKey('sys06-return'),
                      value: 'return',
                      enabled: !returning && !busy,
                      child: Text(copy.text('return')),
                    ),
                    PopupMenuItem(
                      value: 'stop',
                      enabled: active != null && !stopping,
                      child: Text(copy.text('end')),
                    ),
                  ],
                ),
              ],
            ),
            if (active != null || MediaQuery.sizeOf(context).width < 650)
              Row(
                children: [
                  if (MediaQuery.sizeOf(context).width < 650) ...navigation,
                  if (active != null) ...[
                    if (hasLease)
                      control(
                        'sys06-release-control',
                        'releaseControl',
                        Icons.pause_rounded,
                        busy ? null : onReleaseControl,
                      )
                    else
                      control(
                        'sys06-acquire-control',
                        'takeControl',
                        Icons.touch_app_outlined,
                        canAcquire ? onAcquireControl : null,
                      ),
                    control(
                      'sys06-page-links',
                      'pageLinks',
                      Icons.link_rounded,
                      canControl('open_link') ? onOpenPageLinks : null,
                    ),
                  ],
                  const Spacer(),
                  if (active != null) ...[
                    control(
                      'sys06-scroll-up',
                      'scrollUp',
                      Icons.keyboard_arrow_up,
                      canControl('scroll')
                          ? () => onHumanAction('scroll', value: '-600')
                          : null,
                    ),
                    control(
                      'sys06-scroll-down',
                      'scrollDown',
                      Icons.keyboard_arrow_down,
                      canControl('scroll')
                          ? () => onHumanAction('scroll', value: '600')
                          : null,
                    ),
                    control(
                      'sys06-stop',
                      'end',
                      Icons.stop_circle_outlined,
                      stopping ? null : onStop,
                    ),
                  ],
                ],
              ),
            if (active == null)
              Align(
                alignment: Alignment.centerLeft,
                child: TextButton(
                  key: const ValueKey('sys06-open'),
                  onPressed: busy ? null : onOpen,
                  child: Text(copy.text('open')),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _BrowserVisibleLinksDialog extends StatelessWidget {
  const _BrowserVisibleLinksDialog({required this.copy, required this.links});

  final _Sys06Copy copy;
  final List<LumenisBrowserVisibleLink> links;

  @override
  Widget build(BuildContext context) => AlertDialog(
    title: Text(copy.text('pageLinks')),
    content: ConstrainedBox(
      constraints: const BoxConstraints(maxWidth: 640, maxHeight: 480),
      child: SizedBox(
        width: double.maxFinite,
        child: links.isEmpty
            ? Align(
                alignment: Alignment.topLeft,
                child: Text(copy.text('pageLinksEmpty')),
              )
            : ListView.separated(
                shrinkWrap: true,
                itemCount: links.length,
                separatorBuilder: (_, _) => const Divider(height: 1),
                itemBuilder: (context, index) {
                  final link = links[index];
                  return ListTile(
                    leading: const Icon(Icons.link_rounded),
                    title: Text(
                      link.label,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                    subtitle: Text(
                      link.destination,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                    onTap: () => Navigator.of(context).pop(link),
                  );
                },
              ),
      ),
    ),
    actions: [
      TextButton(
        onPressed: () => Navigator.of(context).pop(),
        child: Text(copy.text('cancel')),
      ),
    ],
  );
}

class _Sys06BrowserNoteLocator {
  const _Sys06BrowserNoteLocator({
    required this.url,
    required this.title,
    required this.pageRevision,
    required this.capturedAt,
  });

  final String url;
  final String title;
  final int pageRevision;
  final DateTime capturedAt;
}

class _BrowserResearchNotesDialog extends StatefulWidget {
  const _BrowserResearchNotesDialog({
    required this.repository,
    required this.currentPage,
  });

  final Sys06BrowserResearchRepository repository;
  final _Sys06BrowserNoteLocator? currentPage;

  @override
  State<_BrowserResearchNotesDialog> createState() =>
      _BrowserResearchNotesDialogState();
}

class _BrowserResearchNotesDialogState
    extends State<_BrowserResearchNotesDialog> {
  late final TextEditingController _titleController;
  late final TextEditingController _markdownController;
  Sys06BrowserWorkspaceSelection? _selection;
  Sys06BrowserResearchContext? _scope;
  Sys06BrowserResearchNote? _selectedNote;
  List<Sys06BrowserResearchNote> _notes = const [];
  String _globalDomainId = 'SHARED';
  String? _cursor;
  String? _errorKey;
  String? _pendingSaveRequestId;
  String? _pendingRevisionRequestId;
  int _generation = 0;
  int _operation = 0;
  int _unverifiedCandidates = 0;
  bool _hasMore = false;
  bool _loadingContext = true;
  bool _loadingNotes = false;
  bool _saving = false;
  bool _isNewNote = false;

  @override
  void initState() {
    super.initState();
    _titleController = TextEditingController();
    _markdownController = TextEditingController();
    unawaited(_loadWorkspaceSelection());
  }

  @override
  void dispose() {
    _generation++;
    _titleController.dispose();
    _markdownController.dispose();
    super.dispose();
  }

  bool _isCurrent(int generation) => mounted && generation == _generation;

  void _draftChanged() {
    if (!mounted) return;
    _pendingSaveRequestId = null;
    _pendingRevisionRequestId = null;
    setState(() {});
  }

  Future<void> _loadWorkspaceSelection() async {
    final generation = ++_generation;
    setState(() {
      _loadingContext = true;
      _loadingNotes = false;
      _operation++;
      _errorKey = null;
    });
    try {
      final selection = await widget.repository.readWorkspaceSelection();
      if (!_isCurrent(generation)) return;
      setState(() {
        final previous = _selection;
        if (previous != null &&
            (previous.mode != selection.mode ||
                previous.domainId != selection.domainId ||
                previous.subjectId != selection.subjectId)) {
          _scope = null;
          _selectedNote = null;
          _isNewNote = false;
          _pendingSaveRequestId = null;
          _pendingRevisionRequestId = null;
        }
        _selection = selection;
        if (selection.mode == 'FOCUS' &&
            _globalDomainId != 'SHARED' &&
            _globalDomainId != selection.domainId) {
          _globalDomainId = 'SHARED';
        }
        _loadingContext = false;
      });
      await _resolveAndLoadNotes(generation);
    } catch (_) {
      if (!_isCurrent(generation)) return;
      setState(() {
        _loadingContext = false;
        _errorKey = 'noteError';
      });
    }
  }

  Future<void> _selectGlobalDomain(String? domainId) async {
    if (domainId == null ||
        !const {'SHARED', 'CTH', 'BMP'}.contains(domainId)) {
      return;
    }
    final discard = await _confirmDiscard();
    if (!mounted) return;
    if (!discard) {
      setState(() {
        _generation++;
      });
      return;
    }
    final generation = ++_generation;
    setState(() {
      _globalDomainId = domainId;
      _scope = null;
      _notes = const [];
      _cursor = null;
      _hasMore = false;
      _selectedNote = null;
      _isNewNote = false;
      _titleController.clear();
      _markdownController.clear();
      _errorKey = null;
    });
    await _resolveAndLoadNotes(generation);
  }

  Future<void> _resolveAndLoadNotes(int generation) async {
    final selection = _selection;
    if (selection == null) return;
    setState(() {
      _loadingContext = true;
      _errorKey = null;
    });
    try {
      final scope = await widget.repository.resolveResearchContext(
        globalDomainId: _globalDomainId,
      );
      if (!_isCurrent(generation)) return;
      setState(() {
        if (_scope != null && _scope!.fingerprint != scope.fingerprint) {
          _selectedNote = null;
          _isNewNote = false;
          _pendingSaveRequestId = null;
          _pendingRevisionRequestId = null;
        }
        _scope = scope;
        _loadingContext = false;
      });
      await _loadNotes(generation, scope: scope, reset: true);
    } catch (error) {
      if (!_isCurrent(generation)) return;
      setState(() {
        _loadingContext = false;
        _errorKey = _contextErrorKey(error);
      });
    }
  }

  Future<void> _loadNotes(
    int generation, {
    required Sys06BrowserResearchContext scope,
    required bool reset,
  }) async {
    if (!_isCurrent(generation)) return;
    setState(() {
      _loadingNotes = true;
      _errorKey = null;
      if (reset) {
        _notes = const [];
        _cursor = null;
        _hasMore = false;
        _unverifiedCandidates = 0;
      }
    });
    final operation = ++_operation;
    try {
      final page = await widget.repository.listResearchNotes(
        context: scope,
        cursor: reset ? null : _cursor,
      );
      if (!_isCurrent(generation) ||
          operation != _operation ||
          _scope?.fingerprint != scope.fingerprint) {
        return;
      }
      setState(() {
        _notes = reset
            ? page.notes
            : List.unmodifiable([..._notes, ...page.notes]);
        _cursor = page.nextCursor;
        _hasMore = page.hasMore && page.nextCursor != null;
        _unverifiedCandidates = page.unverifiedCandidates;
        _loadingNotes = false;
      });
    } catch (error) {
      if (!_isCurrent(generation) || operation != _operation) return;
      setState(() {
        _loadingNotes = false;
        _errorKey = _contextErrorKey(error);
      });
    }
  }

  Future<void> _loadMore() async {
    final scope = _scope;
    if (scope == null || _loadingNotes || !_hasMore) return;
    await _loadNotes(_generation, scope: scope, reset: false);
  }

  Future<void> _refreshContext() async {
    if (!await _confirmDiscard() || !mounted) return;
    final priorFingerprint = _scope?.fingerprint;
    await _loadWorkspaceSelection();
    if (!mounted || priorFingerprint == _scope?.fingerprint) return;
    setState(() {
      _selectedNote = null;
      _isNewNote = false;
      _pendingSaveRequestId = null;
      _pendingRevisionRequestId = null;
      _errorKey = 'noteContextChanged';
    });
  }

  Future<void> _startNewNote() async {
    if (_scope == null || widget.currentPage == null || _saving) return;
    if (!await _confirmDiscard() || !mounted) return;
    _generation++;
    setState(() {
      _selectedNote = null;
      _isNewNote = true;
      _titleController.clear();
      _markdownController.clear();
      _pendingSaveRequestId = null;
      _pendingRevisionRequestId = null;
      _errorKey = null;
    });
  }

  Future<void> _reopen(Sys06BrowserResearchNote note) async {
    final scope = _scope;
    if (scope == null || _saving) return;
    if (!await _confirmDiscard() || !mounted) return;
    final generation = ++_generation;
    setState(() {
      _saving = true;
      _errorKey = null;
    });
    try {
      final reopened = await widget.repository.reopenResearchNote(
        context: scope,
        artifactId: note.artifactId,
      );
      if (!_isCurrent(generation) || _scope?.fingerprint != scope.fingerprint) {
        return;
      }
      setState(() {
        _selectedNote = reopened;
        _isNewNote = false;
        _titleController.text = reopened.title;
        _markdownController.text = reopened.markdown;
        _pendingSaveRequestId = null;
        _pendingRevisionRequestId = null;
        _saving = false;
      });
    } catch (error) {
      if (!_isCurrent(generation)) return;
      setState(() {
        _saving = false;
        _errorKey = _contextErrorKey(error);
      });
    }
  }

  String _newRequestId() =>
      'sys06-${DateTime.now().microsecondsSinceEpoch}-${_operation++}';

  Future<void> _save() async {
    final scope = _scope;
    final source = widget.currentPage;
    final title = _titleController.text.trim();
    final markdown = _markdownController.text;
    if (scope == null ||
        source == null ||
        title.isEmpty ||
        markdown.trim().isEmpty ||
        _saving) {
      return;
    }
    final generation = ++_generation;
    final requestId = _pendingSaveRequestId ??= _newRequestId();
    setState(() {
      _saving = true;
      _errorKey = null;
    });
    try {
      final saved = await widget.repository.saveResearchNote(
        context: scope,
        title: title,
        markdown: markdown,
        requestId: requestId,
        pageUrl: source.url,
        pageTitle: source.title,
        pageRevision: source.pageRevision,
        capturedAt: source.capturedAt,
      );
      if (!_isCurrent(generation) || _scope?.fingerprint != scope.fingerprint) {
        return;
      }
      setState(() {
        _selectedNote = saved;
        _isNewNote = false;
        _pendingSaveRequestId = null;
        _pendingRevisionRequestId = null;
        _saving = false;
        _notes = List.unmodifiable([
          saved,
          ..._notes.where((item) => item.artifactId != saved.artifactId),
        ]);
      });
    } catch (error) {
      if (!_isCurrent(generation)) return;
      setState(() {
        _saving = false;
        // Keep the request ID so retrying an uncertain response is idempotent.
        _errorKey = _contextErrorKey(error);
      });
    }
  }

  Future<void> _revise() async {
    final scope = _scope;
    final parent = _selectedNote;
    final title = _titleController.text.trim();
    final markdown = _markdownController.text;
    if (scope == null ||
        parent == null ||
        title.isEmpty ||
        markdown.trim().isEmpty ||
        _saving ||
        (title == parent.title && markdown == parent.markdown)) {
      return;
    }
    final generation = ++_generation;
    final requestId = _pendingRevisionRequestId ??= _newRequestId();
    setState(() {
      _saving = true;
      _errorKey = null;
    });
    try {
      final revised = await widget.repository.reviseResearchNote(
        context: scope,
        parent: parent,
        title: title,
        markdown: markdown,
        requestId: requestId,
        reason: _Sys06Copy.of(context).text('noteRevisionReason'),
      );
      if (!_isCurrent(generation) || _scope?.fingerprint != scope.fingerprint) {
        return;
      }
      setState(() {
        _selectedNote = revised;
        _pendingRevisionRequestId = null;
        _saving = false;
        _notes = List.unmodifiable([
          revised,
          ..._notes.where((item) => item.artifactId != revised.artifactId),
        ]);
      });
    } catch (error) {
      if (!_isCurrent(generation)) return;
      setState(() {
        _saving = false;
        // Keep the request ID so a lost acknowledgment can be retried safely.
        _errorKey = _contextErrorKey(error);
      });
    }
  }

  String _contextErrorKey(Object error) {
    if (error is LumenisCoreException) {
      if (error.statusCode == 401 || error.statusCode == 403) {
        return 'noteAccessError';
      }
      if (error.errorCode == 'CONTENT_CONTEXT_CHANGED') {
        return 'noteContextChanged';
      }
    }
    return 'noteError';
  }

  bool get _canSave {
    if (_saving ||
        _scope == null ||
        _titleController.text.trim().isEmpty ||
        _markdownController.text.trim().isEmpty) {
      return false;
    }
    if (_isNewNote) return widget.currentPage != null;
    final parent = _selectedNote;
    final hasNewerVersion =
        parent != null &&
        _notes.any(
          (item) =>
              item.workId == parent.workId && item.version > parent.version,
        );
    return parent != null &&
        !hasNewerVersion &&
        (_titleController.text.trim() != parent.title ||
            _markdownController.text != parent.markdown);
  }

  bool get _draftHasUncommittedText {
    final note = _selectedNote;
    if (note != null) {
      return _titleController.text.trim() != note.title ||
          _markdownController.text != note.markdown;
    }
    return _titleController.text.isNotEmpty ||
        _markdownController.text.isNotEmpty;
  }

  bool get _hasEdits =>
      _titleController.text != (_selectedNote?.title ?? '') ||
      _markdownController.text != (_selectedNote?.markdown ?? '');

  Future<bool> _confirmDiscard() async {
    if (!_hasEdits) return true;
    final copy = _Sys06Copy.of(context);
    return await showDialog<bool>(
          context: context,
          builder: (dialogContext) => AlertDialog(
            title: Text(copy.text('noteUnsaved')),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(dialogContext, false),
                child: Text(copy.text('noteKeepEditing')),
              ),
              TextButton(
                onPressed: () => Navigator.pop(dialogContext, true),
                child: Text(copy.text('noteDiscard')),
              ),
            ],
          ),
        ) ??
        false;
  }

  Future<void> _close() async {
    if (_saving || !await _confirmDiscard() || !mounted) return;
    setState(() {
      _titleController.text = _selectedNote?.title ?? '';
      _markdownController.text = _selectedNote?.markdown ?? '';
    });
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) Navigator.of(context).pop();
    });
  }

  bool get _selectedVersionIsOld =>
      _selectedNote != null &&
      _notes.any(
        (item) =>
            item.workId == _selectedNote!.workId &&
            item.version > _selectedNote!.version,
      );

  @override
  Widget build(BuildContext context) {
    final copy = _Sys06Copy.of(context);
    final screen = MediaQuery.sizeOf(context);
    final wide = screen.width >= 760;
    final page = widget.currentPage;
    return PopScope(
      canPop: !_saving && !_hasEdits,
      onPopInvokedWithResult: (didPop, result) {
        if (!didPop) unawaited(_close());
      },
      child: Dialog(
        child: SizedBox(
          width: screen.width < 920 ? screen.width - 40 : 880,
          height: screen.height < 760 ? screen.height - 48 : 700,
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        copy.text('researchNotes'),
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                    ),
                    IconButton(
                      key: const ValueKey('sys06-notes-close'),
                      onPressed: _saving ? null : _close,
                      tooltip: MaterialLocalizations.of(
                        context,
                      ).closeButtonTooltip,
                      icon: const Icon(Icons.close_rounded),
                    ),
                  ],
                ),
                const SizedBox(height: 6),
                Text(
                  copy.text('noteBoundary'),
                  style: Theme.of(context).textTheme.bodySmall,
                ),
                const SizedBox(height: 12),
                _buildScopeControl(copy),
                if (_errorKey != null) ...[
                  const SizedBox(height: 8),
                  Text(
                    copy.text(_errorKey!),
                    key: const ValueKey('sys06-note-error'),
                    style: TextStyle(
                      color: Theme.of(context).colorScheme.error,
                    ),
                  ),
                ],
                const SizedBox(height: 12),
                if (_loadingContext)
                  const Expanded(
                    child: Center(child: CircularProgressIndicator()),
                  )
                else if (_scope == null)
                  Expanded(
                    child: Center(child: Text(copy.text('noteChooseDomain'))),
                  )
                else
                  Expanded(
                    child: wide
                        ? Row(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              SizedBox(width: 270, child: _buildNoteList(copy)),
                              const VerticalDivider(width: 24),
                              Expanded(child: _buildEditor(copy, page)),
                            ],
                          )
                        : Column(
                            children: [
                              SizedBox(
                                height: 150,
                                child: _buildNoteList(copy),
                              ),
                              const Divider(height: 20),
                              Expanded(child: _buildEditor(copy, page)),
                            ],
                          ),
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildScopeControl(_Sys06Copy copy) {
    final selection = _selection;
    if (_loadingContext || selection == null) {
      return Text(copy.text('noteScopeLoading'));
    }
    return Row(
      children: [
        Expanded(
          child: DropdownButtonFormField<String>(
            key: ValueKey('sys06-note-domain-$_globalDomainId-$_generation'),
            initialValue: _globalDomainId,
            decoration: InputDecoration(
              isDense: true,
              labelText: copy.text('noteBusinessDomain'),
            ),
            items: [
              DropdownMenuItem(
                value: 'SHARED',
                child: Text(copy.text('noteShared')),
              ),
              if (selection.mode == 'GLOBAL_ALL' || selection.domainId == 'CTH')
                DropdownMenuItem(
                  value: 'CTH',
                  child: Text(copy.text('noteCth')),
                ),
              if (selection.mode == 'GLOBAL_ALL' || selection.domainId == 'BMP')
                DropdownMenuItem(
                  value: 'BMP',
                  child: Text(copy.text('noteBmp')),
                ),
            ],
            onChanged: _saving ? null : _selectGlobalDomain,
          ),
        ),
        IconButton(
          key: const ValueKey('sys06-note-refresh-context'),
          onPressed: _loadingContext || _saving ? null : _refreshContext,
          tooltip: copy.text('noteRefreshContext'),
          icon: const Icon(Icons.refresh_rounded),
        ),
      ],
    );
  }

  Widget _buildNoteList(_Sys06Copy copy) {
    if (_loadingNotes && _notes.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Expanded(
          child: _notes.isEmpty
              ? Center(child: Text(copy.text('noteEmpty')))
              : ListView.builder(
                  itemCount: _notes.length,
                  itemBuilder: (context, index) {
                    final note = _notes[index];
                    return ListTile(
                      key: ValueKey('sys06-note-${note.artifactId}'),
                      selected: _selectedNote?.artifactId == note.artifactId,
                      title: Text(
                        note.title,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                      subtitle: Text(
                        '${copy.text('noteVersion')} ${note.version}',
                      ),
                      onTap: _saving ? null : () => _reopen(note),
                    );
                  },
                ),
        ),
        if (_hasMore)
          TextButton(
            onPressed: _loadingNotes ? null : _loadMore,
            child: Text(copy.text('noteLoadMore')),
          ),
        if (_unverifiedCandidates > 0)
          Text(
            copy.text('noteSomeUnavailable'),
            style: Theme.of(context).textTheme.bodySmall,
          ),
      ],
    );
  }

  Widget _buildEditor(_Sys06Copy copy, _Sys06BrowserNoteLocator? page) {
    final note = _selectedNote;
    final canStart =
        page != null && !_saving && !_isNewNote && !_draftHasUncommittedText;
    final rawNote = note?.payload['browser_note'];
    final storedLocator = rawNote is Map ? rawNote['locator'] : null;
    final siteOrigin = storedLocator is Map
        ? sys06SafeBrowserSiteOrigin(storedLocator['url'])
        : page == null
        ? null
        : sys06SafeBrowserSiteOrigin(page.url);
    final pageRevision = storedLocator is Map
        ? storedLocator['page_revision']
        : page?.pageRevision;
    final capturedAt = storedLocator is Map
        ? storedLocator['captured_at']
        : page?.capturedAt.toUtc().toIso8601String();
    final locator =
        siteOrigin != null && pageRevision is int && capturedAt is String
        ? '${copy.text('noteLocator')}: $siteOrigin\n${copy.text('notePageRevision')} $pageRevision · $capturedAt'
        : null;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Wrap(
          alignment: WrapAlignment.spaceBetween,
          crossAxisAlignment: WrapCrossAlignment.center,
          spacing: 8,
          children: [
            Text(
              note == null
                  ? copy.text('noteDraft')
                  : '${copy.text('noteVersion')} ${note.version}',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            OutlinedButton.icon(
              key: const ValueKey('sys06-note-new'),
              onPressed: canStart ? _startNewNote : null,
              icon: const Icon(Icons.add_rounded),
              label: Text(copy.text('noteNew')),
            ),
          ],
        ),
        if (locator != null) ...[
          const SizedBox(height: 6),
          Text(
            locator,
            maxLines: 3,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ] else if (_isNewNote && page == null) ...[
          const SizedBox(height: 6),
          Text(
            copy.text('noteNoCurrentPage'),
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ],
        const SizedBox(height: 8),
        if (_selectedVersionIsOld) ...[
          Text(
            copy.text('noteOlderVersion'),
            key: const ValueKey('sys06-note-older-version'),
            style: TextStyle(color: Theme.of(context).colorScheme.error),
          ),
          const SizedBox(height: 6),
        ],
        TextField(
          key: const ValueKey('sys06-note-title'),
          controller: _titleController,
          enabled: !_saving && (_isNewNote || note != null),
          onChanged: (_) => _draftChanged(),
          maxLength: 300,
          decoration: InputDecoration(
            isDense: true,
            labelText: copy.text('noteTitle'),
          ),
        ),
        const SizedBox(height: 8),
        Expanded(
          child: TextField(
            key: const ValueKey('sys06-note-markdown'),
            controller: _markdownController,
            enabled: !_saving && (_isNewNote || note != null),
            onChanged: (_) => _draftChanged(),
            maxLines: null,
            expands: true,
            textAlignVertical: TextAlignVertical.top,
            decoration: InputDecoration(
              alignLabelWithHint: true,
              labelText: copy.text('noteMarkdown'),
              border: const OutlineInputBorder(),
            ),
          ),
        ),
        const SizedBox(height: 8),
        Text(
          copy.text('noteContextDisclosure'),
          style: Theme.of(context).textTheme.bodySmall,
        ),
        const SizedBox(height: 8),
        Row(
          mainAxisAlignment: MainAxisAlignment.end,
          children: [
            if (_saving)
              const Padding(
                padding: EdgeInsets.only(right: 12),
                child: SizedBox(
                  height: 18,
                  width: 18,
                  child: CircularProgressIndicator(strokeWidth: 2),
                ),
              ),
            FilledButton.icon(
              key: const ValueKey('sys06-note-save'),
              onPressed: !_canSave
                  ? null
                  : _isNewNote
                  ? _save
                  : _revise,
              icon: Icon(
                _isNewNote ? Icons.save_rounded : Icons.edit_note_rounded,
              ),
              label: Text(copy.text(_isNewNote ? 'noteSave' : 'noteRevise')),
            ),
          ],
        ),
      ],
    );
  }
}

class _ReaderPreview extends StatelessWidget {
  const _ReaderPreview({
    required this.copy,
    required this.frame,
    required this.notice,
    required this.busy,
    required this.onRefresh,
  });

  final _Sys06Copy copy;
  final Sys06BrowserFrame? frame;
  final _Sys06Notice notice;
  final bool busy;
  final VoidCallback onRefresh;

  @override
  Widget build(BuildContext context) {
    final theme = LumenisTheme.of(context);
    final value = frame;
    return ColoredBox(
      color: theme.surface.withValues(alpha: 1),
      child: ClipRect(
        child: value == null
            ? _PreviewEmpty(
                copy: copy,
                notice: notice,
                busy: busy,
                onRefresh: onRefresh,
              )
            : Semantics(
                key: const ValueKey('sys06-preview-readonly'),
                label: copy.text('previewSemantics'),
                image: true,
                child: Stack(
                  fit: StackFit.expand,
                  children: [
                    ColoredBox(
                      color: Colors.white,
                      child: InteractiveViewer(
                        minScale: 1,
                        maxScale: 4,
                        child: Align(
                          alignment: Alignment.topCenter,
                          child: Image.memory(
                            value.frame.bytes,
                            key: const ValueKey('sys06-frame'),
                            fit: BoxFit.contain,
                            gaplessPlayback: true,
                            filterQuality: FilterQuality.medium,
                          ),
                        ),
                      ),
                    ),
                    Positioned(
                      right: 8,
                      bottom: 8,
                      child: IgnorePointer(
                        child: DecoratedBox(
                          decoration: BoxDecoration(
                            color: Colors.black.withValues(alpha: 0.56),
                            borderRadius: BorderRadius.circular(9),
                          ),
                          child: Padding(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 7,
                              vertical: 4,
                            ),
                            child: Text(
                              copy.previewTimestamp(value.frame.capturedAt),
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 12,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
      ),
    );
  }
}

class _PreviewEmpty extends StatelessWidget {
  const _PreviewEmpty({
    required this.copy,
    required this.notice,
    required this.busy,
    required this.onRefresh,
  });

  final _Sys06Copy copy;
  final _Sys06Notice notice;
  final bool busy;
  final VoidCallback onRefresh;

  @override
  Widget build(BuildContext context) {
    final theme = LumenisTheme.of(context);
    final progress =
        busy ||
        notice == _Sys06Notice.navigating ||
        notice == _Sys06Notice.reading;
    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 420),
        child: Padding(
          padding: const EdgeInsets.all(28),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (progress)
                const SizedBox(
                  height: 30,
                  width: 30,
                  child: CircularProgressIndicator(strokeWidth: 2.5),
                )
              else
                Icon(
                  notice.isFailure
                      ? Icons.portable_wifi_off_rounded
                      : Icons.pageview_outlined,
                  color: notice.isFailure ? theme.caution : theme.system,
                  size: 34,
                ),
              const SizedBox(height: 14),
              Text(
                copy.emptyTitle(notice),
                key: const ValueKey('sys06-preview-state'),
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: theme.foreground,
                  fontWeight: FontWeight.w700,
                  fontSize: 18,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                copy.emptyDetail(notice),
                textAlign: TextAlign.center,
                style: TextStyle(color: theme.muted, height: 1.45),
              ),
              if (notice.canRetry) ...[
                const SizedBox(height: 16),
                OutlinedButton.icon(
                  key: const ValueKey('sys06-retry'),
                  onPressed: busy ? null : onRefresh,
                  icon: const Icon(Icons.refresh_rounded),
                  label: Text(copy.text('retry')),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

enum _Sys06Notice {
  ready,
  enterAddress,
  stopping,
  navigating,
  reading,
  previewReady,
  framePending,
  linkStale,
  frameEmpty,
  capacityOccupied,
  accessUnavailable,
  localCoreRequired,
  invalidAddress,
  navigationRestricted,
  unavailable,
  releasingControl,
  controlReleased,
  controlUnavailable,
  returnUnavailable,
  closed,
}

extension on _Sys06Notice {
  bool get isFailure => switch (this) {
    _Sys06Notice.frameEmpty ||
    _Sys06Notice.linkStale ||
    _Sys06Notice.capacityOccupied ||
    _Sys06Notice.accessUnavailable ||
    _Sys06Notice.localCoreRequired ||
    _Sys06Notice.invalidAddress ||
    _Sys06Notice.navigationRestricted ||
    _Sys06Notice.unavailable ||
    _Sys06Notice.controlUnavailable ||
    _Sys06Notice.returnUnavailable => true,
    _ => false,
  };

  bool get canRetry => switch (this) {
    _Sys06Notice.framePending ||
    _Sys06Notice.linkStale ||
    _Sys06Notice.frameEmpty ||
    _Sys06Notice.unavailable => true,
    _ => false,
  };
}

class _Sys06Copy {
  const _Sys06Copy(this._language);

  final String _language;

  static _Sys06Copy of(BuildContext context) {
    final language = Localizations.localeOf(context).languageCode;
    return _Sys06Copy(
      language == 'ko'
          ? 'ko'
          : language == 'en'
          ? 'en'
          : 'zh',
    );
  }

  String text(String key) => (_values[_language]?[key] ?? _values['en']![key])!;

  String notice(_Sys06Notice notice, {Sys06BrowserSession? session}) {
    if (notice == _Sys06Notice.previewReady &&
        session?.currentTitle.isNotEmpty == true) {
      return '${text('previewReady')} · ${session!.currentTitle}';
    }
    return text('notice.${notice.name}');
  }

  String emptyTitle(_Sys06Notice notice) => text('empty.${notice.name}.title');

  String emptyDetail(_Sys06Notice notice) =>
      text('empty.${notice.name}.detail');

  String previewTimestamp(DateTime timestamp) =>
      '${text('preview')} · ${timestamp.toLocal().toIso8601String().replaceFirst('T', ' ').split('.').first}';

  String taskBinding(String status) => switch (status) {
    'BOUND' => text('taskBinding.bound'),
    _ => text('taskBinding.unavailable'),
  };

  static const _values = <String, Map<String, String>>{
    'zh': {
      'eyebrow': 'SYSTEM · 受控来源阅读',
      'title': '内置来源阅读器',
      'subtitle': '页面在寰意受控会话中读取，不会跳转或使用你的个人浏览器。',
      'more': '更多',
      'open': '打开浏览器',
      'address': '网址',
      'addressHint': 'https://example.com',
      'go': '前往',
      'reload': '重新加载页面',
      'refreshPreview': '更新只读预览',
      'end': '结束会话',
      'return': '返回任务',
      'takeControl': '接管浏览',
      'releaseControl': '释放控制',
      'tab.new': '新标签页',
      'tab.add': '新建标签页',
      'tab.close': '关闭标签页',
      'viewExternal': '在外部浏览器查看原文（仅查看，不采集）',
      'collapse': '收起浏览器',
      'expand': '展开浏览器',
      'back': '返回上一页',
      'forward': '前进',
      'scrollUp': '向上滚动',
      'scrollDown': '向下滚动',
      'manualActionBoundary':
          '操作由服务端逐项提供并校验；页面链接只能从服务端为当前画面列出的链接中选择打开，不支持任意点击、文字输入或坐标控制。',
      'pageLinks': '页面链接',
      'pageLinksEmpty': '当前画面没有可打开的链接。',
      'cancel': '取消',
      'taskBinding.bound': '任务关联：服务端已绑定',
      'taskBinding.unavailable': '任务关联：未验证，不会关联到任务证据',
      'humanActionsUnavailable': '服务端尚未公告可用的手动操作。',
      'retry': '重试预览',
      'preview': '只读页面预览',
      'previewSemantics': '只读页面预览。此区域不可点击、输入或远程滚动。',
      'boundaryTitle': '安全边界',
      'researchNotes': '研究笔记',
      'readPage': '问这个网页',
      'noteBoundary': '保存自己的阅读记录。网页原文和截图不会随笔记保存。',
      'noteScopeLoading': '正在读取当前工作区范围…',
      'noteBusinessDomain': '保存位置',
      'noteShared': '我的笔记',
      'noteUnsaved': '笔记还未保存',
      'noteKeepEditing': '继续编辑',
      'noteDiscard': '放弃修改',
      'noteCth': 'CTH 商业运营',
      'noteBmp': 'BMP 品牌市场',
      'noteFocusedScope': '当前已选范围',
      'noteSelectedSubject': '已选主体 / 品牌焦点',
      'noteChooseDomain': '请选择笔记的保存位置。',
      'noteError': '研究笔记暂时不可用。请保留文字并重试。',
      'noteAccessError': '当前没有访问这些笔记的权限。',
      'noteContextChanged': '工作区范围已变化。请重新核对范围后再保存或修订。',
      'noteRefreshContext': '重新读取工作区范围',
      'noteEmpty': '此范围内暂无浏览器研究笔记。',
      'noteVersion': '版本',
      'noteOlderVersion': '这是较早版本。它仍可查看，但必须先重开最新版本才能继续修订。',
      'noteLoadMore': '加载更多',
      'noteSomeUnavailable': '部分记录未能核验，因此未显示。',
      'noteDraft': '手动笔记',
      'noteNew': '新建笔记',
      'noteLocator': '站点来源（origin）',
      'notePageRevision': '页面版本 / 画面时间',
      'noteNoCurrentPage': '先在受控会话中读取页面，再新建带站点来源的笔记。',
      'noteTitle': '标题',
      'noteMarkdown': '笔记内容',
      'noteContextDisclosure': '笔记是你的记录，引用网页内容前请核对原文。',
      'noteSave': '保存笔记',
      'noteRevise': '保存为新版本',
      'noteRevisionReason': '用户在 SYS-06 中修订浏览器研究笔记。',
      'boundary':
          '预览只显示当前已授权页面的短暂快照。它不会读取个人浏览器、Cookie、账号、端口或本地路径。后退、前进、重新加载和滚动仅在服务端公告且人工租约有效时开放；打开链接只能选择服务端为当前画面列出的项目，不提供任意点击、输入或坐标控制。',
      'previewReady': '已更新只读预览',
      'notice.ready': '尚未开启受控会话。',
      'notice.enterAddress': '会话已开启。输入一个允许的公开来源地址。',
      'notice.stopping': '正在请求结束受控会话。',
      'notice.navigating': '正在请求受控导航。',
      'notice.reading': '正在读取已授权页面。',
      'notice.previewReady': '已更新只读预览。',
      'notice.framePending': '页面仍在准备预览，可稍后更新。',
      'notice.linkStale': '页面已变化；请刷新预览后重新选择链接。',
      'notice.frameEmpty': '页面没有可用的可视预览。',
      'notice.capacityOccupied': '受控浏览容量暂被其他会话占用。',
      'notice.accessUnavailable': '当前工作区没有此浏览权限。',
      'notice.localCoreRequired': '目前仅支持连接本机寰意 Core；远程 Web 浏览尚未验证或开放。',
      'notice.invalidAddress': '请输入一个有效的 http 或 https 地址。',
      'notice.unavailable': '网页暂时无法打开，请重试。',
      'notice.navigationRestricted': '当前浏览访问规则未允许此地址。网址已保留，请核对地址或联系管理员。',
      'notice.releasingControl': '正在释放人工控制权。',
      'notice.controlReleased': '已释放人工控制权；需要时可重新读取画面。',
      'notice.controlUnavailable': '人工控制当前不可用或租约已失效。',
      'notice.returnUnavailable': '当前没有可返回的任务页面。',
      'notice.closed': '受控会话已结束。',
      'empty.ready.title': '打开一个网页',
      'empty.ready.detail': '输入网址，开始浏览。',
      'empty.enterAddress.title': '输入来源地址',
      'empty.enterAddress.detail': '导航成功后，系统会显示已授权页面的只读快照。',
      'empty.stopping.title': '正在结束会话',
      'empty.stopping.detail': '正在向当前受控会话请求停止。',
      'empty.navigating.title': '正在导航',
      'empty.navigating.detail': '不会打开外部浏览器。',
      'empty.reading.title': '正在生成预览',
      'empty.reading.detail': '页面加载完成后可更新快照。',
      'empty.previewReady.title': '预览已更新',
      'empty.previewReady.detail': '当前预览已失效，请重新读取。',
      'empty.framePending.title': '页面仍在准备',
      'empty.framePending.detail': '等待页面绘制后再更新预览。',
      'empty.linkStale.title': '页面已变化',
      'empty.linkStale.detail': '请刷新预览后重新选择链接。',
      'empty.frameEmpty.title': '没有可用预览',
      'empty.frameEmpty.detail': '这不代表来源为空或采集完成。',
      'empty.capacityOccupied.title': '受控浏览容量被占用',
      'empty.capacityOccupied.detail': '其他会话不会被识别、关闭或接管。',
      'empty.accessUnavailable.title': '浏览权限不可用',
      'empty.accessUnavailable.detail': '请返回工作区继续其他任务，权限恢复后再试。',
      'empty.localCoreRequired.title': '远程浏览尚不可用',
      'empty.localCoreRequired.detail':
          '当前入口只接受本机寰意 Core。远程 Web 的认证、传输与部署能力仍未验证。',
      'empty.invalidAddress.title': '地址不可用',
      'empty.invalidAddress.detail': '只接受无凭证的 http 或 https 公开地址。',
      'empty.unavailable.title': '预览暂时不可用',
      'empty.unavailable.detail': '画面暂时中断，请重新载入。',
      'empty.releasingControl.title': '正在释放控制权',
      'empty.releasingControl.detail': '受控画面会先清除，服务端确认释放后才能继续。',
      'empty.controlReleased.title': '控制权已释放',
      'empty.controlReleased.detail': '重新读取画面不会恢复控制权；需要操作时请重新接管。',
      'empty.controlUnavailable.title': '人工控制不可用',
      'empty.controlUnavailable.detail': '没有有效租约或服务端没有公告可用操作。',
      'empty.returnUnavailable.title': '无法返回任务',
      'empty.returnUnavailable.detail': '此入口没有保留可返回的上一页。',
      'empty.closed.title': '会话已结束',
      'empty.closed.detail': '需要时可重新开启一个受控会话。',
    },
    'en': {
      'eyebrow': 'SYSTEM · CONTROLLED SOURCE READING',
      'title': 'Internal source reader',
      'subtitle':
          'The page is read in an OEVIRA-controlled session. Your personal browser is never opened or used.',
      'more': 'More',
      'open': 'Open browser',
      'address': 'Web address',
      'addressHint': 'https://example.com',
      'go': 'Go',
      'reload': 'Reload page',
      'refreshPreview': 'Refresh read-only preview',
      'end': 'End session',
      'return': 'Return to task',
      'takeControl': 'Take control',
      'releaseControl': 'Release control',
      'tab.new': 'New tab',
      'tab.add': 'New tab',
      'tab.close': 'Close tab',
      'viewExternal':
          'View original in external browser (view only, no collection)',
      'collapse': 'Collapse browser',
      'expand': 'Expand browser',
      'back': 'Back',
      'forward': 'Forward',
      'scrollUp': 'Scroll up',
      'scrollDown': 'Scroll down',
      'manualActionBoundary':
          'Actions are advertised and checked by the server. Links can only be opened from the server list for this frame; arbitrary clicks, text entry and coordinate control are unavailable.',
      'pageLinks': 'Page links',
      'pageLinksEmpty': 'There are no openable links in this frame.',
      'cancel': 'Cancel',
      'taskBinding.bound': 'Task binding: verified by server',
      'taskBinding.unavailable':
          'Task association: unverified; no task Evidence link',
      'humanActionsUnavailable':
          'The server has not advertised a human action.',
      'retry': 'Retry preview',
      'preview': 'Read-only page preview',
      'previewSemantics':
          'Read-only page preview. This area cannot click, type, or scroll the remote page.',
      'boundaryTitle': 'Safety boundary',
      'researchNotes': 'Research notes',
      'readPage': 'Ask about this page',
      'noteBoundary':
          'Save your reading notes. Page text and screenshots are not saved with them.',
      'noteScopeLoading': 'Reading the current workspace scope…',
      'noteBusinessDomain': 'Save to',
      'noteShared': 'My notes',
      'noteUnsaved': 'This note has unsaved changes',
      'noteKeepEditing': 'Keep editing',
      'noteDiscard': 'Discard changes',
      'noteCth': 'CTH commerce operations',
      'noteBmp': 'BMP brand and market',
      'noteFocusedScope': 'Current focused scope',
      'noteSelectedSubject': 'selected Subject / BrandFocus',
      'noteChooseDomain': 'Choose where to keep your notes.',
      'noteError':
          'Research notes are temporarily unavailable. Keep your text and retry.',
      'noteAccessError':
          'The current account or scope does not have SavedWork access.',
      'noteContextChanged':
          'The workspace scope changed. Recheck it before saving or revising.',
      'noteRefreshContext': 'Refresh workspace scope',
      'noteEmpty': 'No browser research notes in this scope yet.',
      'noteVersion': 'Version',
      'noteOlderVersion':
          'This is an older version. It remains readable; reopen the latest version before revising.',
      'noteLoadMore': 'Load more',
      'noteSomeUnavailable':
          'Some records could not be verified and were not shown.',
      'noteDraft': 'Manual note',
      'noteNew': 'New note',
      'noteLocator': 'Site origin',
      'notePageRevision': 'Page revision / frame time',
      'noteNoCurrentPage':
          'Read a page in the controlled session before creating a note with its site origin.',
      'noteTitle': 'Title',
      'noteMarkdown': 'Note',
      'noteContextDisclosure':
          'These are your notes. Check the original page before citing it.',
      'noteSave': 'Save note',
      'noteRevise': 'Save new version',
      'noteRevisionReason': 'User revised the browser research note in SYS-06.',
      'boundary':
          'The preview contains only a temporary snapshot of the currently authorized page. It never reads a personal browser, cookies, accounts, ports, or local paths. Back, forward, reload and scroll are available only when advertised by the server and protected by an active human lease. Links can only be opened from the server list for this frame; arbitrary clicks, typing and coordinate control are unavailable.',
      'previewReady': 'Read-only preview updated',
      'notice.ready': 'No controlled session is open.',
      'notice.enterAddress':
          'Session opened. Enter an allowed public source address.',
      'notice.stopping': 'Requesting the controlled session to stop.',
      'notice.navigating': 'Requesting controlled navigation.',
      'notice.reading': 'Reading the authorized page.',
      'notice.previewReady': 'Read-only preview updated.',
      'notice.framePending': 'The page is still preparing a preview.',
      'notice.linkStale':
          'The page changed. Refresh the preview and choose the link again.',
      'notice.frameEmpty': 'The page has no usable visual preview.',
      'notice.capacityOccupied': 'Controlled browsing capacity is occupied.',
      'notice.accessUnavailable': 'This workspace has no browser access.',
      'notice.localCoreRequired':
          'Only local OEVIRA Core is supported here; remote Web browsing is not yet verified or enabled.',
      'notice.invalidAddress': 'Enter a valid http or https address.',
      'notice.unavailable': 'Controlled reading is temporarily unavailable.',
      'notice.navigationRestricted':
          'This address is restricted by the current browsing rules. It is retained; check it or contact your administrator.',
      'notice.releasingControl': 'Releasing human control.',
      'notice.controlReleased':
          'Human control released. Refresh the frame when needed.',
      'notice.controlUnavailable':
          'Human control is unavailable or its lease expired.',
      'notice.returnUnavailable': 'There is no task page to return to.',
      'notice.closed': 'Controlled session ended.',
      'empty.ready.title': 'Read inside OEVIRA',
      'empty.ready.detail':
          'Open a controlled session, then enter an allowed public source address.',
      'empty.enterAddress.title': 'Enter a source address',
      'empty.enterAddress.detail':
          'After navigation, the system shows a read-only snapshot of the authorized page.',
      'empty.stopping.title': 'Ending session',
      'empty.stopping.detail':
          'Requesting stop for the current controlled session.',
      'empty.navigating.title': 'Navigating',
      'empty.navigating.detail': 'No external browser will open.',
      'empty.reading.title': 'Preparing preview',
      'empty.reading.detail': 'Refresh once the page has painted.',
      'empty.previewReady.title': 'Preview updated',
      'empty.previewReady.detail':
          'The current preview expired. Read it again.',
      'empty.framePending.title': 'Page is still preparing',
      'empty.framePending.detail': 'Refresh after the page finishes painting.',
      'empty.linkStale.title': 'The page changed',
      'empty.linkStale.detail':
          'Refresh the preview and choose the link again.',
      'empty.frameEmpty.title': 'No usable preview',
      'empty.frameEmpty.detail':
          'This does not mean the source is empty or collection completed.',
      'empty.capacityOccupied.title': 'Controlled capacity occupied',
      'empty.capacityOccupied.detail':
          'Another session is not identified, closed, or taken over.',
      'empty.accessUnavailable.title': 'Browser access unavailable',
      'empty.accessUnavailable.detail':
          'Return to other work and try again after access is restored.',
      'empty.localCoreRequired.title': 'Remote browsing is unavailable',
      'empty.localCoreRequired.detail':
          'This entry accepts local OEVIRA Core only. Remote Web authentication, transport and deployment are not verified.',
      'empty.invalidAddress.title': 'Address unavailable',
      'empty.invalidAddress.detail':
          'Only credential-free http or https public addresses are accepted.',
      'empty.unavailable.title': 'Preview temporarily unavailable',
      'empty.unavailable.detail':
          'No old page is kept and no success state is fabricated.',
      'empty.releasingControl.title': 'Releasing control',
      'empty.releasingControl.detail':
          'The protected frame is cleared until the server confirms release.',
      'empty.controlReleased.title': 'Control released',
      'empty.controlReleased.detail':
          'Refreshing the frame does not restore control; take control again before acting.',
      'empty.controlUnavailable.title': 'Human control unavailable',
      'empty.controlUnavailable.detail':
          'There is no valid lease or server-advertised action.',
      'empty.returnUnavailable.title': 'Cannot return to task',
      'empty.returnUnavailable.detail':
          'This entry has no preserved previous page.',
      'empty.closed.title': 'Session ended',
      'empty.closed.detail': 'Open a new controlled session when needed.',
    },
    'ko': {
      'eyebrow': 'SYSTEM · 제어된 소스 읽기',
      'title': '내장 소스 리더',
      'subtitle': '페이지는 OEVIRA 제어 세션에서 읽습니다. 개인 브라우저를 열거나 사용하지 않습니다.',
      'more': '더 보기',
      'open': '브라우저 열기',
      'address': '웹 주소',
      'addressHint': 'https://example.com',
      'go': '이동',
      'reload': '페이지 새로고침',
      'refreshPreview': '읽기 전용 미리보기 갱신',
      'end': '세션 종료',
      'return': '작업으로 돌아가기',
      'takeControl': '브라우저 제어',
      'releaseControl': '제어 해제',
      'tab.new': '새 탭',
      'tab.add': '새 탭',
      'tab.close': '탭 닫기',
      'viewExternal': '외부 브라우저에서 원문 보기(보기 전용, 수집 안 함)',
      'collapse': '브라우저 접기',
      'expand': '브라우저 펼치기',
      'back': '뒤로',
      'forward': '앞으로',
      'scrollUp': '위로 스크롤',
      'scrollDown': '아래로 스크롤',
      'manualActionBoundary':
          '동작은 서버가 제공하고 검증합니다. 링크는 현재 화면에서 서버가 제공한 목록에서만 열 수 있으며 임의 클릭, 문자 입력 또는 좌표 제어는 지원하지 않습니다.',
      'pageLinks': '페이지 링크',
      'pageLinksEmpty': '현재 화면에서 열 수 있는 링크가 없습니다.',
      'cancel': '취소',
      'taskBinding.bound': '작업 연결: 서버 확인됨',
      'taskBinding.unavailable': '작업 연결: 미검증, 작업 Evidence에 연결되지 않음',
      'humanActionsUnavailable': '서버가 사용 가능한 수동 동작을 제공하지 않았습니다.',
      'retry': '미리보기 재시도',
      'preview': '읽기 전용 페이지 미리보기',
      'previewSemantics':
          '읽기 전용 페이지 미리보기입니다. 이 영역은 원격 페이지를 클릭, 입력 또는 스크롤할 수 없습니다.',
      'boundaryTitle': '안전 경계',
      'researchNotes': '연구 노트',
      'readPage': '이 페이지에 질문하기',
      'noteBoundary': '읽으면서 작성한 노트를 저장하세요. 페이지 원문과 스크린샷은 함께 저장되지 않습니다.',
      'noteScopeLoading': '현재 작업 공간 범위를 읽는 중…',
      'noteBusinessDomain': '저장 위치',
      'noteShared': '내 노트',
      'noteUnsaved': '저장하지 않은 변경 사항이 있습니다',
      'noteKeepEditing': '계속 편집',
      'noteDiscard': '변경 취소',
      'noteCth': 'CTH 상업 운영',
      'noteBmp': 'BMP 브랜드·시장',
      'noteFocusedScope': '현재 선택 범위',
      'noteSelectedSubject': '선택된 Subject / BrandFocus',
      'noteChooseDomain': '노트를 저장할 위치를 선택하세요.',
      'noteError': '연구 노트를 일시적으로 사용할 수 없습니다. 텍스트를 보존하고 다시 시도하세요.',
      'noteAccessError': '이 노트에 접근할 권한이 없습니다.',
      'noteContextChanged': '작업 공간 범위가 바뀌었습니다. 저장 또는 수정 전에 범위를 다시 확인하세요.',
      'noteRefreshContext': '작업 공간 범위 새로고침',
      'noteEmpty': '이 범위에 브라우저 연구 노트가 없습니다.',
      'noteVersion': '버전',
      'noteOlderVersion': '이전 버전입니다. 읽을 수 있지만 수정하려면 최신 버전을 다시 여세요.',
      'noteLoadMore': '더 불러오기',
      'noteSomeUnavailable': '일부 기록은 검증할 수 없어 표시하지 않았습니다.',
      'noteDraft': '수동 노트',
      'noteNew': '새 노트',
      'noteLocator': '사이트 출처(origin)',
      'notePageRevision': '페이지 버전 / 화면 시각',
      'noteNoCurrentPage': '제어 세션에서 페이지를 읽은 후 사이트 출처가 기록된 노트를 만드세요.',
      'noteTitle': '제목',
      'noteMarkdown': '노트 내용',
      'noteContextDisclosure': '개인 기록입니다. 인용하기 전에 원문을 확인하세요.',
      'noteSave': '노트 저장',
      'noteRevise': '새 버전으로 저장',
      'noteRevisionReason': '사용자가 SYS-06에서 브라우저 연구 노트를 수정했습니다.',
      'boundary':
          '미리보기에는 현재 승인된 페이지의 임시 스냅샷만 표시됩니다. 개인 브라우저, 쿠키, 계정, 포트 또는 로컬 경로를 읽지 않습니다. 뒤로, 앞으로, 새로고침 및 스크롤은 서버가 제공하고 유효한 사람 제어 임대가 있을 때만 사용할 수 있습니다. 링크는 현재 화면에서 서버가 제공한 목록에서만 열 수 있으며 임의 클릭, 입력 및 좌표 제어는 사용할 수 없습니다.',
      'previewReady': '읽기 전용 미리보기가 갱신되었습니다',
      'notice.ready': '제어된 세션이 열려 있지 않습니다.',
      'notice.enterAddress': '세션이 열렸습니다. 허용된 공개 소스 주소를 입력하세요.',
      'notice.stopping': '제어 세션 종료를 요청하고 있습니다.',
      'notice.navigating': '제어된 탐색을 요청하고 있습니다.',
      'notice.reading': '승인된 페이지를 읽고 있습니다.',
      'notice.previewReady': '읽기 전용 미리보기가 갱신되었습니다.',
      'notice.framePending': '페이지가 아직 미리보기를 준비하고 있습니다.',
      'notice.linkStale': '페이지가 변경되었습니다. 미리보기를 갱신하고 링크를 다시 선택하세요.',
      'notice.frameEmpty': '페이지에 사용할 수 있는 시각 미리보기가 없습니다.',
      'notice.capacityOccupied': '제어된 브라우징 용량이 사용 중입니다.',
      'notice.accessUnavailable': '이 작업 공간에는 브라우저 권한이 없습니다.',
      'notice.localCoreRequired':
          '현재는 로컬 OEVIRA Core만 지원합니다. 원격 Web 브라우징은 아직 검증되거나 활성화되지 않았습니다.',
      'notice.invalidAddress': '유효한 http 또는 https 주소를 입력하세요.',
      'notice.unavailable': '제어된 읽기를 일시적으로 사용할 수 없습니다.',
      'notice.navigationRestricted':
          '현재 탐색 규칙에서 허용하지 않는 주소입니다. 주소는 유지됩니다. 주소를 확인하거나 관리자에게 문의하세요.',
      'notice.releasingControl': '사람 제어권을 해제하고 있습니다.',
      'notice.controlReleased': '사람 제어권이 해제되었습니다. 필요하면 화면을 다시 읽으세요.',
      'notice.controlUnavailable': '사람 제어를 사용할 수 없거나 임대가 만료되었습니다.',
      'notice.returnUnavailable': '돌아갈 작업 페이지가 없습니다.',
      'notice.closed': '제어된 세션이 종료되었습니다.',
      'empty.ready.title': 'OEVIRA 안에서 읽기 시작',
      'empty.ready.detail': '제어된 세션을 연 다음 허용된 공개 소스 주소를 입력하세요.',
      'empty.enterAddress.title': '소스 주소 입력',
      'empty.enterAddress.detail': '탐색 뒤에 시스템이 승인된 페이지의 읽기 전용 스냅샷을 표시합니다.',
      'empty.stopping.title': '세션 종료 중',
      'empty.stopping.detail': '현재 제어 세션에 종료를 요청하고 있습니다.',
      'empty.navigating.title': '탐색 중',
      'empty.navigating.detail': '외부 브라우저를 열지 않습니다.',
      'empty.reading.title': '미리보기 준비 중',
      'empty.reading.detail': '페이지가 그려진 뒤 미리보기를 갱신하세요.',
      'empty.previewReady.title': '미리보기 갱신됨',
      'empty.previewReady.detail': '현재 미리보기가 만료되었습니다. 다시 읽으세요.',
      'empty.framePending.title': '페이지 준비 중',
      'empty.framePending.detail': '페이지가 그려진 후 미리보기를 갱신하세요.',
      'empty.linkStale.title': '페이지가 변경됨',
      'empty.linkStale.detail': '미리보기를 갱신하고 링크를 다시 선택하세요.',
      'empty.frameEmpty.title': '사용 가능한 미리보기 없음',
      'empty.frameEmpty.detail': '소스가 비었거나 수집이 완료되었다는 뜻은 아닙니다.',
      'empty.capacityOccupied.title': '제어된 용량 사용 중',
      'empty.capacityOccupied.detail': '다른 세션을 식별, 종료 또는 인계하지 않습니다.',
      'empty.accessUnavailable.title': '브라우저 접근 불가',
      'empty.accessUnavailable.detail': '다른 작업으로 돌아가고 접근이 복구된 뒤 다시 시도하세요.',
      'empty.localCoreRequired.title': '원격 브라우징 사용 불가',
      'empty.localCoreRequired.detail':
          '이 진입은 로컬 OEVIRA Core만 허용합니다. 원격 Web 인증, 전송 및 배포는 검증되지 않았습니다.',
      'empty.invalidAddress.title': '주소를 사용할 수 없음',
      'empty.invalidAddress.detail': '자격 증명이 없는 http 또는 https 공개 주소만 허용됩니다.',
      'empty.unavailable.title': '미리보기를 일시적으로 사용할 수 없음',
      'empty.unavailable.detail': '이전 페이지를 유지하거나 성공 상태를 만들지 않습니다.',
      'empty.releasingControl.title': '제어권 해제 중',
      'empty.releasingControl.detail': '서버가 해제를 확인할 때까지 보호된 화면을 지웁니다.',
      'empty.controlReleased.title': '제어권 해제됨',
      'empty.controlReleased.detail':
          '화면을 다시 읽어도 제어권은 복원되지 않습니다. 조작하려면 다시 제어를 요청하세요.',
      'empty.controlUnavailable.title': '사람 제어 사용 불가',
      'empty.controlUnavailable.detail': '유효한 임대가 없거나 서버가 조작을 제공하지 않습니다.',
      'empty.returnUnavailable.title': '작업으로 돌아갈 수 없음',
      'empty.returnUnavailable.detail': '이 진입에는 보존된 이전 페이지가 없습니다.',
      'empty.closed.title': '세션 종료됨',
      'empty.closed.detail': '필요할 때 새 제어 세션을 여세요.',
    },
  };
}
