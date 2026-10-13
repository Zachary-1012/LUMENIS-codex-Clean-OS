import 'package:flutter/foundation.dart';

import '../../core/transport/lumenis_http_transport.dart';
import 'ai01_intent.dart';
import 'ai01_repository.dart';
import 'ai01_snapshot.dart';

enum Ai01LoadPhase { loading, ready, failed }

enum Ai01FailureKind { authentication, permissionDenied, offline, server }

/// Outcome of the last submit attempt. Only [completed] means the server
/// returned an execution whose status is `completed`.
enum Ai01SubmitPhase {
  idle,
  submitting,
  completed,
  notCompleted,
  pendingApproval,
  denied,
  invalid,
  authentication,
  failed,
  outcomeUnknown,
}

/// One submitted intent and the response or failure actually observed for it.
/// The task is the trimmed text sent by this client; this record is kept only
/// for the lifetime of its ViewModel and is not persisted.
class Ai01Submission {
  const Ai01Submission({required this.task, required this.phase, this.result});

  final String task;
  final Ai01SubmitPhase phase;
  final Ai01IntentResult? result;

  Ai01Submission copyWith({
    required Ai01SubmitPhase phase,
    required Ai01IntentResult? result,
  }) => Ai01Submission(task: task, phase: phase, result: result);
}

/// Why the submit control is unavailable. [none] means submission is allowed.
enum Ai01SubmitBlock {
  none,
  notReady,
  emptyDraft,
  tooLong,
  submitting,
  alreadySubmitted,
}

const int ai01MaxTaskLength = 4000;

class Ai01ViewModel extends ChangeNotifier {
  Ai01ViewModel({required this._repository});

  final Ai01Repository _repository;

  Ai01LoadPhase _phase = Ai01LoadPhase.loading;
  Ai01FailureKind? _failureKind;
  Ai01Snapshot? _snapshot;
  String? _failureMessage;
  String _draft = '';
  String? _submittedDraft;
  final List<Ai01Submission> _submissions = [];
  int _requestGeneration = 0;
  int _submissionGeneration = 0;
  bool _disposed = false;

  Ai01LoadPhase get phase => _phase;
  Ai01FailureKind? get failureKind => _failureKind;
  Ai01Snapshot? get snapshot => _snapshot;
  String? get failureMessage => _failureMessage;
  String get draft => _draft;

  /// Read-only snapshot of the tasks submitted by this ViewModel instance.
  /// It is session-local and intentionally has no persistence or server-history
  /// claim.
  List<Ai01Submission> get submissions => List.unmodifiable(_submissions);

  Ai01Submission? get latestSubmission =>
      _submissions.isEmpty ? null : _submissions.last;

  /// Compatibility accessors for callers presenting the latest submission.
  Ai01SubmitPhase get submitPhase =>
      latestSubmission?.phase ?? Ai01SubmitPhase.idle;
  Ai01IntentResult? get intentResult => latestSubmission?.result;

  /// Submission needs a successfully read service state, a non-empty draft
  /// within the server limit, no request in flight and a draft that differs
  /// from the one already sent (no accidental duplicate execution).
  Ai01SubmitBlock get submitBlock {
    if (submitPhase == Ai01SubmitPhase.submitting) {
      return Ai01SubmitBlock.submitting;
    }
    if (_phase != Ai01LoadPhase.ready || _snapshot == null) {
      return Ai01SubmitBlock.notReady;
    }
    final task = _draft.trim();
    if (task.isEmpty) return Ai01SubmitBlock.emptyDraft;
    if (task.runes.length > ai01MaxTaskLength) return Ai01SubmitBlock.tooLong;
    if (_submittedDraft != null && _submittedDraft == _draft) {
      return Ai01SubmitBlock.alreadySubmitted;
    }
    return Ai01SubmitBlock.none;
  }

  bool get canSubmit => !_disposed && submitBlock == Ai01SubmitBlock.none;

  /// Sends the trimmed draft once. There is no automatic retry: a transport
  /// failure or timeout after sending leaves the outcome unknown.
  Future<void> submit() async {
    if (!canSubmit) return;

    final task = _draft.trim();
    _submittedDraft = _draft;
    final submissionIndex = _submissions.length;
    final submissionGeneration = ++_submissionGeneration;
    _submissions.add(
      Ai01Submission(task: task, phase: Ai01SubmitPhase.submitting),
    );
    _notifyIfAlive();

    Ai01SubmitPhase next;
    Ai01IntentResult? result;
    try {
      result = await _repository.submitIntent(task);
      next = switch (result.kind) {
        Ai01IntentKind.completed => Ai01SubmitPhase.completed,
        Ai01IntentKind.notCompleted => Ai01SubmitPhase.notCompleted,
        Ai01IntentKind.pendingApproval => Ai01SubmitPhase.pendingApproval,
      };
    } catch (error) {
      result = null;
      next = _classifySubmitFailure(error);
    }
    if (_disposed || submissionGeneration != _submissionGeneration) return;

    _submissions[submissionIndex] = _submissions[submissionIndex].copyWith(
      phase: next,
      result: result,
    );
    _notifyIfAlive();
  }

  Future<void> refresh() async {
    if (_disposed) return;

    final requestGeneration = ++_requestGeneration;
    _phase = Ai01LoadPhase.loading;
    _failureKind = null;
    _failureMessage = null;
    _snapshot = null;
    _notifyIfAlive();

    try {
      final snapshot = await _repository.load();
      if (_isStale(requestGeneration)) return;

      _snapshot = snapshot;
      _phase = Ai01LoadPhase.ready;
    } catch (error) {
      if (_isStale(requestGeneration)) return;

      _snapshot = null;
      _failureKind = _classifyFailure(error);
      _failureMessage = _failureText(_failureKind!);
      _phase = Ai01LoadPhase.failed;
    }

    _notifyIfAlive();
  }

  void updateDraft(String value) {
    if (_disposed || value == _draft) return;
    _draft = value;
    _notifyIfAlive();
  }

  void useSuggestion(Ai01Suggestion suggestion) {
    final intent = suggestion.safeIntent;
    if (intent == null || intent.isEmpty) return;
    updateDraft(intent);
  }

  bool _isStale(int requestGeneration) =>
      _disposed || requestGeneration != _requestGeneration;

  void _notifyIfAlive() {
    if (!_disposed) notifyListeners();
  }

  @override
  void dispose() {
    if (latestSubmission?.phase == Ai01SubmitPhase.submitting) {
      _submissions[_submissions.length - 1] = latestSubmission!.copyWith(
        phase: Ai01SubmitPhase.outcomeUnknown,
        result: null,
      );
    }
    _disposed = true;
    _requestGeneration++;
    _submissionGeneration++;
    super.dispose();
  }

  static Ai01FailureKind _classifyFailure(Object error) {
    final message = error.toString().toLowerCase();
    if (message.contains('http 401') || message.contains('auth_required')) {
      return Ai01FailureKind.authentication;
    }
    if (message.contains('http 403')) {
      return Ai01FailureKind.permissionDenied;
    }
    if (isLumenisConnectionError(error) ||
        message.contains('core unavailable') ||
        message.contains('connection timed out')) {
      return Ai01FailureKind.offline;
    }
    return Ai01FailureKind.server;
  }

  static Ai01SubmitPhase _classifySubmitFailure(Object error) {
    if (error is FormatException) return Ai01SubmitPhase.outcomeUnknown;
    final message = error.toString().toLowerCase();
    if (message.contains('http 401') || message.contains('auth_required')) {
      return Ai01SubmitPhase.authentication;
    }
    if (message.contains('http 403')) return Ai01SubmitPhase.denied;
    if (message.contains('http 400')) return Ai01SubmitPhase.invalid;
    if (RegExp(r'http 5\d\d').hasMatch(message)) return Ai01SubmitPhase.failed;
    // Connection errors and timeouts may have happened after the server
    // accepted the request, so the outcome is unknown rather than "failed".
    return Ai01SubmitPhase.outcomeUnknown;
  }

  static String _failureText(Ai01FailureKind kind) => switch (kind) {
    Ai01FailureKind.authentication => '服务连接授权已失效，无法读取 AI-01 实时状态。',
    Ai01FailureKind.permissionDenied => '此操作不可访问 AI-01 实时状态。',
    Ai01FailureKind.offline => '暂时无法连接 AI 服务。',
    Ai01FailureKind.server => 'AI-01 实时数据读取失败。',
  };
}
