import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';

enum SourceBriefPhase { idle, loading, ready, failed }

enum SourceBriefSavedWorkState { idle, saving, saved, reopened, failed }

enum SourceBriefHistoryState { idle, loading, loaded, failed }

enum SourceBriefSharedAdoptionState {
  idle,
  preparing,
  prepared,
  applying,
  reopened,
  failed,
}

enum SourceBriefTaskState {
  unknown,
  pending,
  running,
  succeeded,
  failed,
  interrupted,
}

enum SourceBriefErrorKind {
  contextUnavailable,
  accessDenied,
  notFound,
  unavailable,
  invalidResponse,
  contextChanged,
  analysisUnavailable,
}

enum SourceBriefBusinessAnalysisState {
  unknown,
  notRequested,
  draft,
  unavailable,
  error,
}

final class SourceBriefScope {
  const SourceBriefScope({
    required this.productId,
    required this.domainId,
    required this.globalScope,
    required this.subjectId,
    required this.brandFocusId,
    required this.entityLabel,
    required this.scopeKey,
  });

  final String productId;
  final String domainId;
  final bool globalScope;
  final String? subjectId;
  final String? brandFocusId;
  final String entityLabel;
  final String scopeKey;
}

final class SourceBriefSource {
  const SourceBriefSource({
    required this.sourceId,
    required this.title,
    required this.sourceUrl,
    required this.publishedAt,
    required this.capturedAt,
    required this.evidenceRef,
  });

  final String sourceId;
  final String? title;
  final String? sourceUrl;
  final String? publishedAt;
  final String? capturedAt;
  final String evidenceRef;
}

final class SourceBriefObservation {
  const SourceBriefObservation({required this.sourceId, required this.excerpt});

  final String sourceId;
  final String excerpt;
}

final class SourceBriefInterpretation {
  SourceBriefInterpretation({
    required this.text,
    required List<String> sourceIds,
  }) : sourceIds = List.unmodifiable(sourceIds);

  final String text;
  final List<String> sourceIds;
}

final class SourceBriefPilotProposal {
  const SourceBriefPilotProposal({
    required this.audience,
    required this.procedure,
    required this.measure,
    required this.continueIf,
    required this.stopIf,
  });

  final String audience;
  final String procedure;
  final String measure;
  final String continueIf;
  final String stopIf;
}

final class SourceBriefProposedAction {
  SourceBriefProposedAction({
    required this.action,
    required this.reason,
    required this.check,
    required List<String> sourceIds,
    required this.pilot,
  }) : sourceIds = List.unmodifiable(sourceIds);

  final String action;
  final String reason;
  final String check;
  final List<String> sourceIds;
  final SourceBriefPilotProposal? pilot;
}

final class SourceBriefBusinessAnalysis {
  SourceBriefBusinessAnalysis({
    required List<SourceBriefObservation> sourceObservations,
    required List<SourceBriefInterpretation> interpretations,
    required List<SourceBriefProposedAction> proposedActions,
    required List<String> unknowns,
  }) : sourceObservations = List.unmodifiable(sourceObservations),
       interpretations = List.unmodifiable(interpretations),
       proposedActions = List.unmodifiable(proposedActions),
       unknowns = List.unmodifiable(unknowns);

  final List<SourceBriefObservation> sourceObservations;
  final List<SourceBriefInterpretation> interpretations;
  final List<SourceBriefProposedAction> proposedActions;
  final List<String> unknowns;
}

final class SourceBriefQuerySample {
  SourceBriefQuerySample({
    this.candidateCount,
    this.scannedCount,
    this.rejectedCount,
    this.returnedCount,
    this.returnedVerifiedCount,
    this.withheldCount,
    this.truncated,
    Map<String, int>? platformCountsSample,
    this.countsBasis,
  }) : platformCountsSample = platformCountsSample == null
           ? null
           : Map.unmodifiable(platformCountsSample);

  final int? candidateCount;
  final int? scannedCount;
  final int? rejectedCount;
  final int? returnedCount;
  final int? returnedVerifiedCount;
  final int? withheldCount;
  final bool? truncated;
  final Map<String, int>? platformCountsSample;
  final String? countsBasis;
}

final class SourceBriefAnalysisSample {
  const SourceBriefAnalysisSample({
    this.availableBriefCount,
    this.analyzedSourceCount,
    this.omittedSourceCount,
    this.hasTruncatedBodies,
    this.selection,
    this.coverage,
  });

  final int? availableBriefCount;
  final int? analyzedSourceCount;
  final int? omittedSourceCount;
  final bool? hasTruncatedBodies;
  final String? selection;
  final String? coverage;
}

final class SourceBriefResearchFinding {
  const SourceBriefResearchFinding({
    required this.id,
    required this.sourceId,
    required this.evidenceRef,
    required this.content,
    required this.title,
    required this.truncated,
  });
  final String id, sourceId, evidenceRef, content;
  final String? title;
  final bool? truncated;
}

final class SourceBriefResearchQuestion {
  SourceBriefResearchQuestion({
    required this.statement,
    required this.status,
    required List<String> findingIds,
    required List<String> validationNeeded,
  }) : findingIds = List.unmodifiable(findingIds),
       validationNeeded = List.unmodifiable(validationNeeded);
  final String statement, status;
  final List<String> findingIds, validationNeeded;
}

final class SourceBriefNumberCheck {
  SourceBriefNumberCheck({
    required this.sourceId,
    required List<String> literals,
  }) : literals = List.unmodifiable(literals);
  final String sourceId;
  final List<String> literals;
}

/// A projection of the original source-bound analysis, never factual promotion.
final class SourceBriefResearchAnalysis {
  SourceBriefResearchAnalysis({
    required this.status,
    required this.summary,
    required List<SourceBriefResearchFinding> findings,
    required List<SourceBriefResearchQuestion> questions,
    required List<SourceBriefNumberCheck> numberChecks,
    required List<String> limitations,
  }) : findings = List.unmodifiable(findings),
       questions = List.unmodifiable(questions),
       numberChecks = List.unmodifiable(numberChecks),
       limitations = List.unmodifiable(limitations);
  final String status;
  final String? summary;
  final List<SourceBriefResearchFinding> findings;
  final List<SourceBriefResearchQuestion> questions;
  final List<SourceBriefNumberCheck> numberChecks;
  final List<String> limitations;
}

final class SourceBriefResult {
  SourceBriefResult({
    required this.jobId,
    required this.reportId,
    required this.artifactHash,
    required this.sourceCount,
    required this.scope,
    required List<SourceBriefSource> records,
    required this.businessQuestion,
    required this.businessAnalysisState,
    required this.analysis,
    required this.reviewStatus,
    this.sourceSample,
    this.analysisSample,
    this.researchAnalysis,
    this.markdown,
  }) : records = List.unmodifiable(records);

  final String jobId;
  final String reportId;
  final String artifactHash;
  final int? sourceCount;
  final SourceBriefScope scope;
  final List<SourceBriefSource> records;
  final String? businessQuestion;
  final SourceBriefBusinessAnalysisState businessAnalysisState;
  final SourceBriefBusinessAnalysis? analysis;
  final String reviewStatus;
  final SourceBriefQuerySample? sourceSample;
  final SourceBriefAnalysisSample? analysisSample;
  final SourceBriefResearchAnalysis? researchAnalysis;
  final String? markdown;
}

final class SourceBriefSavedWork {
  const SourceBriefSavedWork({
    required this.artifactId,
    required this.sha256,
    required this.workId,
    required this.version,
    required this.title,
    required this.markdown,
    required this.requestId,
    required this.sourceBriefJobId,
    required this.sourceBriefHash,
    this.parentArtifactId,
    this.parentSha256,
  });

  final String artifactId;
  final String sha256;
  final String workId;
  final int version;
  final String title;
  final String markdown;
  final String requestId;
  final String sourceBriefJobId;
  final String sourceBriefHash;
  final String? parentArtifactId;
  final String? parentSha256;
}

final class SourceBriefRevisionDraft {
  const SourceBriefRevisionDraft({
    required this.title,
    required this.reason,
    required this.markdown,
  });

  final String title;
  final String reason;
  final String markdown;
}

final class SourceBriefSharedAdoptionPreview {
  const SourceBriefSharedAdoptionPreview({
    required this.requestId,
    required this.jobId,
    required this.sourceBriefHash,
    required this.sourceScopeKey,
    required this.title,
    required this.resource,
    required this.displayedCitations,
    required this.guardedSourceCount,
  });

  final String requestId;
  final String jobId;
  final String sourceBriefHash;
  final String sourceScopeKey;
  final String title;
  final String resource;
  final int displayedCitations;
  final int guardedSourceCount;
}

final class SourceBriefSharedSavedWork {
  const SourceBriefSharedSavedWork({
    required this.artifactId,
    required this.sha256,
    required this.title,
    required this.markdown,
    required this.requestId,
    required this.replayed,
  });

  final String artifactId;
  final String sha256;
  final String title;
  final String markdown;
  final String requestId;
  final bool replayed;
}

final class _PendingSourceBriefSharedAdoption {
  const _PendingSourceBriefSharedAdoption({
    required this.requestId,
    required this.jobId,
    required this.sourceBriefHash,
    required this.sourceScopeKey,
    required this.binding,
    this.title,
    this.preview,
  });

  final String requestId;
  final String jobId;
  final String sourceBriefHash;
  final String sourceScopeKey;
  final Map<String, Object?> binding;
  final String? title;
  final SourceBriefSharedAdoptionPreview? preview;
}

final class _PendingSourceBriefRevision {
  const _PendingSourceBriefRevision({
    required this.parentArtifactId,
    required this.parentSha256,
    required this.requestId,
    required this.draft,
  });

  final String parentArtifactId;
  final String parentSha256;
  final String requestId;
  final SourceBriefRevisionDraft draft;

  bool matches(SourceBriefSavedWork parent, SourceBriefRevisionDraft value) =>
      parentArtifactId == parent.artifactId &&
      parentSha256 == parent.sha256 &&
      draft.title == value.title &&
      draft.reason == value.reason &&
      draft.markdown == value.markdown;
}

class SourceBriefViewModel extends ChangeNotifier {
  SourceBriefViewModel({required this.client, this.domainId = 'CTH'}) {
    if (domainId != 'CTH' && domainId != 'BMP') {
      throw const FormatException('Explicit source domain required.');
    }
  }

  final String domainId;
  String get _domainId => domainId;

  final LumenisCoreClient client;
  bool _disposed = false;
  int _generation = 0;
  SourceBriefPhase _phase = SourceBriefPhase.idle;
  bool _busy = false;
  String? _taskId;
  String? _jobId;
  SourceBriefTaskState _taskState = SourceBriefTaskState.unknown;
  bool _canResume = false;
  SourceBriefResult? _result;
  String? _newResultTaskId;
  String? _resultArrivalToken;
  int _resultArrivalSequence = 0;
  String? statisticsTaskId;
  String? _statisticsJobId;
  Map<String, Object?>? sourceStatistics;
  SourceBriefSavedWorkState _savedWorkState = SourceBriefSavedWorkState.idle;
  SourceBriefErrorKind? _savedWorkErrorKind;
  String? _savedWorkArtifactId;
  String? _savedWorkSha256;
  String? _savedWorkTitle;
  String? _savedWorkMarkdown;
  String? _pendingSaveRequestId;
  String? _pendingSaveTitle;
  String? _pendingSaveJobId;
  String? _pendingSaveArtifactHash;
  static int _saveRequestSequence = 0;
  final List<SourceBriefSavedWork> _savedHistory = [];
  SourceBriefHistoryState _savedHistoryState = SourceBriefHistoryState.idle;
  SourceBriefErrorKind? _savedHistoryErrorKind;
  SourceBriefSavedWork? _openedHistoryWork;
  String? _savedHistoryCursor;
  bool _savedHistoryHasMore = false;
  bool _savedHistoryVerificationComplete = true;
  int? _savedHistoryUnverifiedCount;
  _PendingSourceBriefRevision? _pendingRevision;
  _PendingSourceBriefSharedAdoption? _pendingSharedAdoption;
  SourceBriefSharedAdoptionState _sharedAdoptionState =
      SourceBriefSharedAdoptionState.idle;
  SourceBriefErrorKind? _sharedAdoptionErrorKind;
  SourceBriefSharedSavedWork? _sharedAdoptedWork;

  SourceBriefSavedWorkState get savedWorkState => _savedWorkState;
  SourceBriefErrorKind? get savedWorkErrorKind => _savedWorkErrorKind;
  String? get savedWorkMarkdown => _savedWorkMarkdown;
  String? get savedWorkTitle => _savedWorkTitle;
  List<SourceBriefSavedWork> get savedHistory =>
      List.unmodifiable(_savedHistory);
  SourceBriefHistoryState get savedHistoryState => _savedHistoryState;
  SourceBriefErrorKind? get savedHistoryErrorKind => _savedHistoryErrorKind;
  SourceBriefSavedWork? get openedHistoryWork => _openedHistoryWork;
  bool get savedHistoryHasMore => _savedHistoryHasMore;
  bool get savedHistoryVerificationComplete =>
      _savedHistoryVerificationComplete;
  int? get savedHistoryUnverifiedCount => _savedHistoryUnverifiedCount;
  SourceBriefSharedAdoptionState get sharedAdoptionState =>
      _sharedAdoptionState;
  SourceBriefErrorKind? get sharedAdoptionErrorKind => _sharedAdoptionErrorKind;
  SourceBriefSharedAdoptionPreview? get sharedAdoptionPreview =>
      _pendingSharedAdoption?.preview;
  SourceBriefSharedSavedWork? get sharedAdoptedWork => _sharedAdoptedWork;
  SourceBriefRevisionDraft? pendingRevisionDraftFor(
    SourceBriefSavedWork parent,
  ) => _pendingRevision?.matches(parent, _pendingRevision!.draft) == true
      ? _pendingRevision!.draft
      : null;
  Future<void> analyseSources({String? taskId}) async {
    if (_disposed || _busy) return;
    final jobId = _result?.jobId ?? _jobId;
    final priorTaskId = _statisticsJobId == jobId ? statisticsTaskId : null;
    final operation = _beginOperation();
    final fresh = await _loadFreshContext(operation);
    if (fresh == null || !_isCurrent(operation)) return;
    if (fresh.scopeChanged) {
      _finish(
        operation,
        phase: SourceBriefPhase.ready,
        errorKind: SourceBriefErrorKind.contextChanged,
      );
      return;
    }
    try {
      String? selectedJobId = jobId;
      String? selectedTaskId = taskId ?? priorTaskId;
      Map<String, Object?>? task;
      if (selectedTaskId != null) {
        final response = await client.sourceStatisticsTask(
          domainId: _domainId,
          taskId: selectedTaskId,
        );
        if (!_contextStillCurrent(fresh, operation)) return;
        task = _asMap(response['task']);
        final taskContext = _asMap(task?['context']);
        if (response['ok'] != true ||
            taskContext?['analysis_operation'] != 'source_statistics') {
          throw const _InvalidSourceBriefResponse();
        }
        selectedJobId = _safeIdentifier(taskContext?['source_brief_job_id']);
      }
      if (selectedJobId == null) throw const _InvalidSourceBriefResponse();
      final sourceResponse = await client.sourceBriefJob(
        domainId: _domainId,
        jobId: selectedJobId,
      );
      if (!_contextStillCurrent(fresh, operation)) return;
      final source = _asMap(sourceResponse['result']);
      if (sourceResponse['ok'] != true || source == null) {
        throw const _InvalidSourceBriefResponse();
      }
      final parsed = _parseResult(
        source,
        expectedJobId: selectedJobId,
        expectedContext: fresh.selection,
      );
      if (selectedTaskId == null) {
        final created = await client.createSourceStatistics(
          domainId: _domainId,
          jobId: selectedJobId,
        );
        if (!_contextStillCurrent(fresh, operation)) return;
        selectedTaskId = _safeIdentifier(_asMap(created['task'])?['task_id']);
        if (created['ok'] != true || selectedTaskId == null) {
          throw const _InvalidSourceBriefResponse();
        }
      }
      statisticsTaskId = selectedTaskId;
      _statisticsJobId = selectedJobId;
      if (task?['status'] != 'succeeded') {
        final response = await client.sourceStatisticsTask(
          domainId: _domainId,
          taskId: selectedTaskId,
          run: true,
        );
        if (!_contextStillCurrent(fresh, operation)) return;
        task = _asMap(response['task']);
        if (response['ok'] != true) throw const _InvalidSourceBriefResponse();
      }
      final result = _asMap(task?['result']);
      final output = _asMap(result?['output']);
      final verification = _asMap(result?['verification']);
      final artifact = _asMap(output?['artifact_outcome']);
      final statistics = _asMap(output?['base_analysis']);
      if (task?['task_id'] != selectedTaskId ||
          task?['status'] != 'succeeded' ||
          result?['task_outcome'] != 'VERIFIED' ||
          verification?['verified'] != true ||
          verification?['verification_scope'] !=
              'SOURCE_BRIEF_SAMPLE_ANALYSIS' ||
          output?['source_brief_job_id'] != parsed.jobId ||
          artifact?['artifact_hash'] != parsed.artifactHash ||
          output?['base_analysis_status'] != 'completed' ||
          statistics == null) {
        throw const _InvalidSourceBriefResponse();
      }
      // Re-read the committed task; an execution return alone is insufficient.
      final reopened = await client.sourceStatisticsTask(
        domainId: _domainId,
        taskId: selectedTaskId,
      );
      if (!_contextStillCurrent(fresh, operation)) return;
      final savedTask = _asMap(reopened['task']);
      if (reopened['ok'] != true ||
          _contextSignature(savedTask?['result']) !=
              _contextSignature(result) ||
          savedTask?['finished_at'] != task?['finished_at']) {
        throw const _InvalidSourceBriefResponse();
      }
      _result = parsed;
      _jobId = parsed.jobId;
      sourceStatistics = Map.unmodifiable(statistics);
      _finish(operation, phase: SourceBriefPhase.ready);
    } catch (error) {
      _fail(operation, _errorFor(error), fresh: fresh);
    }
  }

  Future<void> saveAsEditableResearch({required String title}) async {
    final sourceResult = _result;
    final selection = _selection;
    if (_disposed || _busy || sourceResult == null || selection == null) {
      return;
    }
    if (_savedWorkState == SourceBriefSavedWorkState.saved &&
        _pendingSaveJobId == sourceResult.jobId &&
        _pendingSaveArtifactHash == sourceResult.artifactHash) {
      return;
    }
    if (_pendingSaveJobId != sourceResult.jobId ||
        _pendingSaveArtifactHash != sourceResult.artifactHash) {
      _resetSavedWorkState();
    }
    final normalizedTitle = title.trim();
    if (normalizedTitle.isEmpty || normalizedTitle.length > 300) {
      _savedWorkState = SourceBriefSavedWorkState.failed;
      _savedWorkErrorKind = SourceBriefErrorKind.invalidResponse;
      notifyListeners();
      return;
    }
    _pendingSaveJobId = sourceResult.jobId;
    _pendingSaveArtifactHash = sourceResult.artifactHash;
    _pendingSaveTitle ??= normalizedTitle;
    _pendingSaveRequestId ??= _newSourceBriefSaveRequestId();
    final operation = _beginOperation(preserveResult: true);
    _savedWorkState = SourceBriefSavedWorkState.saving;
    _savedWorkErrorKind = null;
    final fresh = await _loadFreshContext(operation);
    if (fresh == null || !_isCurrent(operation)) {
      _finishSavedWorkContextFailure(operation);
      return;
    }
    if (fresh.scopeChanged || !fresh.selection.matches(sourceResult.scope)) {
      _savedWorkErrorKind = SourceBriefErrorKind.contextChanged;
      _savedWorkState = SourceBriefSavedWorkState.failed;
      _finish(
        operation,
        phase: SourceBriefPhase.ready,
        errorKind: SourceBriefErrorKind.contextChanged,
      );
      return;
    }
    if (!_contextStillCurrent(fresh, operation)) return;
    final latest = _result;
    if (latest == null ||
        latest.jobId != sourceResult.jobId ||
        latest.artifactHash != sourceResult.artifactHash) {
      _savedWorkErrorKind = SourceBriefErrorKind.contextChanged;
      _savedWorkState = SourceBriefSavedWorkState.failed;
      _finish(
        operation,
        phase: SourceBriefPhase.ready,
        errorKind: SourceBriefErrorKind.contextChanged,
      );
      return;
    }
    try {
      final saveResponse = await client.saveSourceBriefResult(
        domainId: _domainId,
        jobId: sourceResult.jobId,
        requestId: _pendingSaveRequestId!,
        title: _pendingSaveTitle!,
      );
      if (!_isCurrent(operation) || !_contextStillCurrent(fresh, operation)) {
        return;
      }
      if (saveResponse['ok'] != true) {
        throw _SourceBriefSaveFailure(_errorForResponse(saveResponse));
      }
      final saved = _validatedSavedWork(
        saveResponse['result'],
        expectedResult: sourceResult,
        expectedTitle: _pendingSaveTitle!,
        expectedRequestId: _pendingSaveRequestId!,
      );
      final reopenResponse = await client.reopenSourceBriefSavedWork(
        domainId: _domainId,
        artifactId: saved.artifactId,
      );
      if (!_isCurrent(operation) || !_contextStillCurrent(fresh, operation)) {
        return;
      }
      if (reopenResponse['ok'] != true) {
        throw _SourceBriefSaveFailure(_errorForResponse(reopenResponse));
      }
      final reopened = _validatedSavedWork(
        reopenResponse['result'],
        expectedResult: sourceResult,
        expectedTitle: _pendingSaveTitle!,
        expectedRequestId: _pendingSaveRequestId!,
        expectedArtifactId: saved.artifactId,
        expectedSha256: saved.sha256,
        expectedMarkdown: saved.markdown,
      );
      _savedWorkArtifactId = reopened.artifactId;
      _savedWorkSha256 = reopened.sha256;
      _savedWorkTitle = reopened.title;
      _savedWorkMarkdown = reopened.markdown;
      _savedWorkState = SourceBriefSavedWorkState.saved;
      _savedWorkErrorKind = null;
      _finish(operation, phase: SourceBriefPhase.ready);
    } catch (error) {
      if (!_isCurrent(operation)) return;
      _savedWorkErrorKind = error is _SourceBriefSaveFailure
          ? error.kind
          : _errorFor(error);
      _savedWorkState = SourceBriefSavedWorkState.failed;
      _finish(operation, phase: SourceBriefPhase.ready);
    }
  }

  Future<void> reopenSavedResearch() async {
    final sourceResult = _result;
    final artifactId = _savedWorkArtifactId;
    final sha256 = _savedWorkSha256;
    final title = _savedWorkTitle;
    final markdown = _savedWorkMarkdown;
    final requestId = _pendingSaveRequestId;
    if (_disposed ||
        _busy ||
        sourceResult == null ||
        artifactId == null ||
        sha256 == null ||
        title == null ||
        markdown == null ||
        requestId == null) {
      return;
    }
    final operation = _beginOperation(preserveResult: true);
    final fresh = await _loadFreshContext(operation);
    if (fresh == null || !_isCurrent(operation)) {
      _finishSavedWorkContextFailure(operation);
      return;
    }
    if (fresh.scopeChanged || !fresh.selection.matches(sourceResult.scope)) {
      _savedWorkErrorKind = SourceBriefErrorKind.contextChanged;
      _savedWorkState = SourceBriefSavedWorkState.failed;
      _finish(
        operation,
        phase: SourceBriefPhase.ready,
        errorKind: SourceBriefErrorKind.contextChanged,
      );
      return;
    }
    try {
      final response = await client.reopenSourceBriefSavedWork(
        domainId: _domainId,
        artifactId: artifactId,
      );
      if (!_isCurrent(operation) || !_contextStillCurrent(fresh, operation)) {
        return;
      }
      if (response['ok'] != true) {
        throw _SourceBriefSaveFailure(_errorForResponse(response));
      }
      final reopened = _validatedSavedWork(
        response['result'],
        expectedResult: sourceResult,
        expectedTitle: title,
        expectedRequestId: requestId,
        expectedArtifactId: artifactId,
        expectedSha256: sha256,
        expectedMarkdown: markdown,
      );
      _savedWorkMarkdown = reopened.markdown;
      _savedWorkState = SourceBriefSavedWorkState.reopened;
      _savedWorkErrorKind = null;
      _finish(operation, phase: SourceBriefPhase.ready);
    } catch (error) {
      if (!_isCurrent(operation)) return;
      _savedWorkErrorKind = error is _SourceBriefSaveFailure
          ? error.kind
          : _errorFor(error);
      _savedWorkState = SourceBriefSavedWorkState.failed;
      _finish(operation, phase: SourceBriefPhase.ready);
    }
  }

  Future<void> loadSavedResearchHistory({bool loadMore = false}) async {
    if (_disposed ||
        _busy ||
        _savedHistoryState == SourceBriefHistoryState.loading) {
      return;
    }
    if (loadMore && (!_savedHistoryHasMore || _savedHistoryCursor == null)) {
      return;
    }
    final priorCursor = loadMore ? _savedHistoryCursor : null;
    final operation = _beginOperation(preserveResult: true);
    _savedHistoryState = SourceBriefHistoryState.loading;
    _savedHistoryErrorKind = null;
    notifyListeners();
    final fresh = await _loadFreshContext(operation);
    if (fresh == null || !_isCurrent(operation)) {
      _savedHistoryState = SourceBriefHistoryState.failed;
      _savedHistoryErrorKind = _errorKind ?? SourceBriefErrorKind.unavailable;
      _finishSavedWorkContextFailure(operation);
      return;
    }
    if (fresh.scopeChanged) {
      _clearSavedResearchHistory();
      _savedHistoryState = SourceBriefHistoryState.failed;
      _savedHistoryErrorKind = SourceBriefErrorKind.contextChanged;
      _finish(
        operation,
        phase: SourceBriefPhase.ready,
        errorKind: SourceBriefErrorKind.contextChanged,
      );
      return;
    }
    try {
      final response = await client.listBrowserResearchNotes(
        domainId: _domainId,
        limit: 100,
        cursor: priorCursor,
      );
      if (!_isCurrent(operation) || !_contextStillCurrent(fresh, operation)) {
        return;
      }
      if (response['ok'] != true) {
        throw _SourceBriefSaveFailure(_errorForResponse(response));
      }
      final page = _asMap(response['result']);
      final items = page?['items'];
      final hasMore = page?['has_more'];
      final verificationComplete = page?['verification_complete'];
      final unverified = page?['unverified_candidates'];
      final nextCursor = page?['next_cursor'];
      if (page == null ||
          items is! List ||
          hasMore is! bool ||
          verificationComplete is! bool ||
          unverified is! int ||
          unverified < 0 ||
          (nextCursor != null && nextCursor is! String) ||
          (hasMore && (nextCursor is! String || nextCursor.isEmpty))) {
        throw const _InvalidSourceBriefResponse();
      }
      final parsed = <SourceBriefSavedWork>[];
      for (final item in items) {
        final document = _asMap(_asMap(item)?['document']);
        final payload = _asMap(document?['payload']);
        if (payload?.containsKey('source_brief_reference') != true) continue;
        parsed.add(
          _validatedHistoricalSavedWork(
            item,
            expectedSelection: fresh.selection,
          ),
        );
      }
      if (!_isCurrent(operation) || !_contextStillCurrent(fresh, operation)) {
        return;
      }
      if (!loadMore) _savedHistory.clear();
      final known = _savedHistory.map((work) => work.artifactId).toSet();
      _savedHistory.addAll(parsed.where((work) => known.add(work.artifactId)));
      _savedHistory.sort((left, right) {
        final workOrder = right.workId.compareTo(left.workId);
        if (workOrder != 0) return workOrder;
        return right.version.compareTo(left.version);
      });
      _savedHistoryCursor = nextCursor as String?;
      _savedHistoryHasMore = hasMore;
      _savedHistoryVerificationComplete = verificationComplete;
      _savedHistoryUnverifiedCount = unverified;
      _savedHistoryState = SourceBriefHistoryState.loaded;
      _savedHistoryErrorKind = null;
      _finish(operation, phase: SourceBriefPhase.ready);
    } catch (error) {
      if (!_isCurrent(operation)) return;
      _savedHistoryState = SourceBriefHistoryState.failed;
      _savedHistoryErrorKind = error is _SourceBriefSaveFailure
          ? error.kind
          : _errorFor(error);
      _finish(operation, phase: SourceBriefPhase.ready);
    }
  }

  Future<void> reopenSavedResearchVersion(SourceBriefSavedWork work) async {
    if (_disposed || _busy) return;
    final selection = _selection;
    if (selection == null || !_savedHistory.contains(work)) {
      _savedHistoryErrorKind = SourceBriefErrorKind.contextChanged;
      _savedHistoryState = SourceBriefHistoryState.failed;
      notifyListeners();
      return;
    }
    final operation = _beginOperation(preserveResult: true);
    final fresh = await _loadFreshContext(operation);
    if (fresh == null || !_isCurrent(operation)) {
      _savedHistoryState = SourceBriefHistoryState.failed;
      _savedHistoryErrorKind = _errorKind ?? SourceBriefErrorKind.unavailable;
      _finish(operation, phase: SourceBriefPhase.ready);
      return;
    }
    if (fresh.scopeChanged || !fresh.selection.sameScope(selection)) {
      _clearSavedResearchHistory();
      _savedHistoryState = SourceBriefHistoryState.failed;
      _savedHistoryErrorKind = SourceBriefErrorKind.contextChanged;
      _finish(
        operation,
        phase: SourceBriefPhase.ready,
        errorKind: SourceBriefErrorKind.contextChanged,
      );
      return;
    }
    try {
      final response = await client.reopenBrowserResearchNote(
        domainId: _domainId,
        artifactId: work.artifactId,
      );
      if (!_isCurrent(operation) || !_contextStillCurrent(fresh, operation)) {
        return;
      }
      if (response['ok'] != true) {
        throw _SourceBriefSaveFailure(_errorForResponse(response));
      }
      final reopened = _validatedHistoricalSavedWork(
        response['result'],
        expectedSelection: fresh.selection,
        expectedArtifactId: work.artifactId,
        expectedSha256: work.sha256,
        expectedWorkId: work.workId,
        expectedVersion: work.version,
        expectedJobId: work.sourceBriefJobId,
        expectedSourceBriefHash: work.sourceBriefHash,
      );
      _openedHistoryWork = reopened;
      _savedHistoryState = SourceBriefHistoryState.loaded;
      _savedHistoryErrorKind = null;
      _finish(operation, phase: SourceBriefPhase.ready);
    } catch (error) {
      if (!_isCurrent(operation)) return;
      _savedHistoryState = SourceBriefHistoryState.failed;
      _savedHistoryErrorKind = error is _SourceBriefSaveFailure
          ? error.kind
          : _errorFor(error);
      _finish(operation, phase: SourceBriefPhase.ready);
    }
  }

  Future<void> reviseSavedResearchVersion({
    required SourceBriefSavedWork parent,
    required String reason,
    required String title,
    required String markdown,
  }) async {
    if (_disposed || _busy) return;
    final normalizedReason = reason.trim();
    final normalizedTitle = title.trim();
    if (normalizedReason.isEmpty ||
        normalizedReason.length > 4000 ||
        normalizedTitle.isEmpty ||
        normalizedTitle.length > 300 ||
        markdown.trim().isEmpty ||
        markdown.length > 100000) {
      _savedHistoryState = SourceBriefHistoryState.failed;
      _savedHistoryErrorKind = SourceBriefErrorKind.invalidResponse;
      notifyListeners();
      return;
    }
    final selection = _selection;
    final latestVersion = _savedHistory
        .where((work) => work.workId == parent.workId)
        .fold<int>(
          0,
          (latest, work) => work.version > latest ? work.version : latest,
        );
    if (selection == null ||
        !_savedHistory.contains(parent) ||
        latestVersion != parent.version) {
      _savedHistoryState = SourceBriefHistoryState.failed;
      _savedHistoryErrorKind = SourceBriefErrorKind.contextChanged;
      notifyListeners();
      return;
    }
    final operation = _beginOperation(preserveResult: true);
    _savedHistoryState = SourceBriefHistoryState.loading;
    _savedHistoryErrorKind = null;
    notifyListeners();
    final fresh = await _loadFreshContext(operation);
    if (fresh == null || !_isCurrent(operation)) {
      _savedHistoryState = SourceBriefHistoryState.failed;
      _savedHistoryErrorKind = _errorKind ?? SourceBriefErrorKind.unavailable;
      _finish(operation, phase: SourceBriefPhase.ready);
      return;
    }
    if (fresh.scopeChanged || !fresh.selection.sameScope(selection)) {
      _clearSavedResearchHistory();
      _savedHistoryState = SourceBriefHistoryState.failed;
      _savedHistoryErrorKind = SourceBriefErrorKind.contextChanged;
      _finish(
        operation,
        phase: SourceBriefPhase.ready,
        errorKind: SourceBriefErrorKind.contextChanged,
      );
      return;
    }
    final draft = SourceBriefRevisionDraft(
      title: normalizedTitle,
      reason: normalizedReason,
      markdown: markdown,
    );
    final pending = _pendingRevision;
    if (pending != null && !pending.matches(parent, draft)) {
      _savedHistoryState = SourceBriefHistoryState.failed;
      _savedHistoryErrorKind = SourceBriefErrorKind.unavailable;
      _finish(operation, phase: SourceBriefPhase.ready);
      return;
    }
    final requestId = pending?.requestId ?? _newSourceBriefRevisionRequestId();
    _pendingRevision ??= _PendingSourceBriefRevision(
      parentArtifactId: parent.artifactId,
      parentSha256: parent.sha256,
      requestId: requestId,
      draft: draft,
    );
    try {
      final revised = await client.reviseBrowserResearchNote(
        domainId: _domainId,
        artifactId: parent.artifactId,
        requestId: requestId,
        expectedSha256: parent.sha256,
        reason: normalizedReason,
        expectedTitle: parent.title,
        title: normalizedTitle,
        expectedMarkdown: parent.markdown,
        markdown: markdown,
      );
      if (!_isCurrent(operation) || !_contextStillCurrent(fresh, operation)) {
        return;
      }
      if (revised['ok'] != true) {
        throw _SourceBriefSaveFailure(_errorForResponse(revised));
      }
      final created = _validatedHistoricalSavedWork(
        revised['result'],
        expectedSelection: fresh.selection,
        expectedWorkId: parent.workId,
        expectedVersion: parent.version + 1,
        expectedJobId: parent.sourceBriefJobId,
        expectedSourceBriefHash: parent.sourceBriefHash,
        expectedParentArtifactId: parent.artifactId,
        expectedParentSha256: parent.sha256,
        expectedTitle: normalizedTitle,
        expectedMarkdown: markdown,
        expectedRequestId: requestId,
      );
      final reopenedResponse = await client.reopenBrowserResearchNote(
        domainId: _domainId,
        artifactId: created.artifactId,
      );
      if (!_isCurrent(operation) || !_contextStillCurrent(fresh, operation)) {
        return;
      }
      if (reopenedResponse['ok'] != true) {
        throw _SourceBriefSaveFailure(_errorForResponse(reopenedResponse));
      }
      final reopened = _validatedHistoricalSavedWork(
        reopenedResponse['result'],
        expectedSelection: fresh.selection,
        expectedArtifactId: created.artifactId,
        expectedSha256: created.sha256,
        expectedWorkId: created.workId,
        expectedVersion: created.version,
        expectedJobId: parent.sourceBriefJobId,
        expectedSourceBriefHash: parent.sourceBriefHash,
        expectedParentArtifactId: parent.artifactId,
        expectedParentSha256: parent.sha256,
        expectedTitle: normalizedTitle,
        expectedMarkdown: markdown,
        expectedRequestId: requestId,
      );
      _savedHistory.removeWhere(
        (work) => work.artifactId == reopened.artifactId,
      );
      _savedHistory.add(reopened);
      _savedHistory.sort((left, right) {
        final workOrder = right.workId.compareTo(left.workId);
        if (workOrder != 0) return workOrder;
        return right.version.compareTo(left.version);
      });
      _openedHistoryWork = reopened;
      _pendingRevision = null;
      _savedHistoryState = SourceBriefHistoryState.loaded;
      _savedHistoryErrorKind = null;
      _finish(operation, phase: SourceBriefPhase.ready);
    } catch (error) {
      if (!_isCurrent(operation)) return;
      _savedHistoryState = SourceBriefHistoryState.failed;
      _savedHistoryErrorKind = error is _SourceBriefSaveFailure
          ? error.kind
          : _errorFor(error);
      _finish(operation, phase: SourceBriefPhase.ready);
    }
  }

  Future<void> prepareSharedAdoption() async {
    if (_disposed || _busy) return;
    final sourceResult = _result;
    final selection = _selection;
    if (sourceResult == null ||
        selection == null ||
        _taskState != SourceBriefTaskState.succeeded) {
      _failSharedAdoption(null, SourceBriefErrorKind.invalidResponse);
      return;
    }
    var pending = _pendingSharedAdoption;
    if (pending != null && !_sharedAdoptionMatches(pending, sourceResult)) {
      _resetSharedAdoption();
      pending = null;
    }
    if (pending?.preview != null) {
      _sharedAdoptionState = SourceBriefSharedAdoptionState.prepared;
      _sharedAdoptionErrorKind = null;
      notifyListeners();
      return;
    }
    pending ??= _PendingSourceBriefSharedAdoption(
      requestId: _newSourceBriefSharedAdoptionRequestId(),
      jobId: sourceResult.jobId,
      sourceBriefHash: sourceResult.artifactHash,
      sourceScopeKey: sourceResult.scope.scopeKey,
      binding: const {},
    );
    _pendingSharedAdoption = pending;
    final operation = _beginOperation(preserveResult: true);
    _sharedAdoptionState = SourceBriefSharedAdoptionState.preparing;
    _sharedAdoptionErrorKind = null;
    _sharedAdoptedWork = null;
    final fresh = await _loadFreshContext(operation);
    if (fresh == null || !_isCurrent(operation)) {
      _failSharedAdoption(
        operation,
        _errorKind ?? SourceBriefErrorKind.unavailable,
      );
      return;
    }
    if (fresh.scopeChanged ||
        !fresh.selection.sameScope(selection) ||
        !fresh.selection.matches(sourceResult.scope)) {
      _finish(
        operation,
        phase: SourceBriefPhase.ready,
        errorKind: SourceBriefErrorKind.contextChanged,
      );
      return;
    }
    if (!_contextStillCurrent(fresh, operation)) return;
    if (!_sameCurrentResult(sourceResult)) {
      _failSharedAdoption(operation, SourceBriefErrorKind.contextChanged);
      return;
    }
    try {
      final response = await client.adoptSourceBriefToShared(
        jobId: pending.jobId,
        requestId: pending.requestId,
        mode: 'prepare',
      );
      if (!_isCurrent(operation) || !_contextStillCurrent(fresh, operation)) {
        return;
      }
      if (response['ok'] != true) {
        throw _SourceBriefSaveFailure(_errorForResponse(response));
      }
      final prepared = _asMap(response['result']);
      final binding = _asMap(prepared?['binding']);
      final resource = _safeText(prepared?['resource'], maxLength: 4096);
      final title = _safeText(prepared?['title'], maxLength: 300);
      final citations = prepared?['displayed_citations'];
      final guardedSources = prepared?['guarded_source_count'];
      if (prepared == null ||
          binding == null ||
          prepared['state'] != 'requires_explicit_export_approval' ||
          prepared['operation'] != 'data_export' ||
          resource == null ||
          title == null ||
          citations is! int ||
          citations < 0 ||
          citations > 8 ||
          guardedSources is! int ||
          guardedSources < 1 ||
          citations > guardedSources ||
          !_validSharedAdoptionBinding(binding, sourceResult)) {
        throw const _InvalidSourceBriefResponse();
      }
      final preview = SourceBriefSharedAdoptionPreview(
        requestId: pending.requestId,
        jobId: pending.jobId,
        sourceBriefHash: pending.sourceBriefHash,
        sourceScopeKey: pending.sourceScopeKey,
        title: title,
        resource: resource,
        displayedCitations: citations,
        guardedSourceCount: guardedSources,
      );
      _pendingSharedAdoption = _PendingSourceBriefSharedAdoption(
        requestId: pending.requestId,
        jobId: pending.jobId,
        sourceBriefHash: pending.sourceBriefHash,
        sourceScopeKey: pending.sourceScopeKey,
        binding: Map.unmodifiable(binding),
        title: title,
        preview: preview,
      );
      _sharedAdoptionState = SourceBriefSharedAdoptionState.prepared;
      _sharedAdoptionErrorKind = null;
      _finish(operation, phase: SourceBriefPhase.ready);
    } catch (error) {
      if (!_isCurrent(operation)) return;
      _failSharedAdoption(
        operation,
        error is _SourceBriefSaveFailure ? error.kind : _errorFor(error),
      );
    }
  }

  Future<void> applySharedAdoption() async {
    if (_disposed || _busy) return;
    final sourceResult = _result;
    final selection = _selection;
    final pending = _pendingSharedAdoption;
    final preview = pending?.preview;
    if (sourceResult == null ||
        selection == null ||
        pending == null ||
        preview == null ||
        _taskState != SourceBriefTaskState.succeeded ||
        !_sharedAdoptionMatches(pending, sourceResult)) {
      _failSharedAdoption(null, SourceBriefErrorKind.contextChanged);
      return;
    }
    final operation = _beginOperation(preserveResult: true);
    _sharedAdoptionState = SourceBriefSharedAdoptionState.applying;
    _sharedAdoptionErrorKind = null;
    _sharedAdoptedWork = null;
    final fresh = await _loadFreshContext(operation);
    if (fresh == null || !_isCurrent(operation)) {
      _failSharedAdoption(
        operation,
        _errorKind ?? SourceBriefErrorKind.unavailable,
      );
      return;
    }
    if (fresh.scopeChanged ||
        !fresh.selection.sameScope(selection) ||
        !fresh.selection.matches(sourceResult.scope) ||
        !_sharedAdoptionMatches(pending, sourceResult)) {
      _finish(
        operation,
        phase: SourceBriefPhase.ready,
        errorKind: SourceBriefErrorKind.contextChanged,
      );
      return;
    }
    if (!_contextStillCurrent(fresh, operation)) {
      return;
    }
    if (!_sameCurrentResult(sourceResult)) {
      _failSharedAdoption(operation, SourceBriefErrorKind.contextChanged);
      return;
    }
    try {
      final response = await client.adoptSourceBriefToShared(
        jobId: pending.jobId,
        requestId: pending.requestId,
        mode: 'apply',
        title: pending.title,
        confirm: true,
        confirmedResource: preview.resource,
      );
      if (!_isCurrent(operation) || !_contextStillCurrent(fresh, operation)) {
        return;
      }
      if (response['ok'] != true) {
        throw _SourceBriefSaveFailure(_errorForResponse(response));
      }
      final committed = _validateSharedAdoptedWork(
        response['result'],
        expected: pending,
        requireReplayState: true,
      );
      final reopenedResponse = await client.reopenSharedSavedWork(
        committed.artifactId,
      );
      if (!_isCurrent(operation) || !_contextStillCurrent(fresh, operation)) {
        return;
      }
      if (reopenedResponse['ok'] != true) {
        throw _SourceBriefSaveFailure(_errorForResponse(reopenedResponse));
      }
      final reopened = _validateSharedAdoptedWork(
        reopenedResponse['result'],
        expected: pending,
        expectedArtifactId: committed.artifactId,
        expectedSha256: committed.sha256,
        requireReplayState: false,
      );
      _sharedAdoptedWork = reopened;
      _sharedAdoptionState = SourceBriefSharedAdoptionState.reopened;
      _sharedAdoptionErrorKind = null;
      _finish(operation, phase: SourceBriefPhase.ready);
    } catch (error) {
      if (!_isCurrent(operation)) return;
      _failSharedAdoption(
        operation,
        error is _SourceBriefSaveFailure ? error.kind : _errorFor(error),
      );
    }
  }

  bool _sameCurrentResult(SourceBriefResult expected) {
    final current = _result;
    return current != null &&
        current.jobId == expected.jobId &&
        current.artifactHash == expected.artifactHash &&
        current.scope.scopeKey == expected.scope.scopeKey;
  }

  bool _sharedAdoptionMatches(
    _PendingSourceBriefSharedAdoption pending,
    SourceBriefResult result,
  ) =>
      pending.jobId == result.jobId &&
      pending.sourceBriefHash == result.artifactHash &&
      pending.sourceScopeKey == result.scope.scopeKey;

  bool _validSharedAdoptionBinding(
    Map<String, Object?> binding,
    SourceBriefResult result,
  ) {
    final sourceScope = _asMap(binding['source_scope']);
    final targetScope = _asMap(binding['target_scope']);
    final sourceCount = binding['source_count'];
    final sourcesHash = binding['sources_sha256'];
    return binding['schema'] == 'domain-report-adoption/v1' &&
        binding['job_id'] == result.jobId &&
        binding['report_hash'] == result.artifactHash &&
        binding['authority'] == 'SOURCE_REFERENCE_ONLY' &&
        binding['semantic_verification'] == 'NOT_PERFORMED' &&
        binding['actor_id'] is String &&
        (binding['actor_id'] as String).isNotEmpty &&
        sourceCount is int &&
        sourceCount > 0 &&
        sourcesHash is String &&
        RegExp(r'^[0-9a-f]{64}$').hasMatch(sourcesHash) &&
        _sourceScopeMatches(sourceScope, result.scope) &&
        _isSharedScope(targetScope);
  }

  bool _sourceScopeMatches(
    Map<String, Object?>? scope,
    SourceBriefScope expected,
  ) =>
      scope != null &&
      scope['domain_id'] == expected.domainId &&
      scope['subject_id'] == expected.subjectId &&
      scope['brand_focus_id'] == expected.brandFocusId &&
      scope['global_scope'] == expected.globalScope;

  bool _isSharedScope(Map<String, Object?>? scope) =>
      scope != null &&
      scope.length == 2 &&
      scope['scope_kind'] == 'shared_workspace' &&
      scope['version'] == 1;

  SourceBriefSharedSavedWork _validateSharedAdoptedWork(
    Object? value, {
    required _PendingSourceBriefSharedAdoption expected,
    String? expectedArtifactId,
    String? expectedSha256,
    required bool requireReplayState,
  }) {
    final envelope = _asMap(value);
    final artifact = _asMap(envelope?['artifact']);
    final document = _asMap(envelope?['document']);
    final returnRef = _asMap(envelope?['return_ref']);
    final payload = _asMap(document?['payload']);
    final binding = _asMap(payload?['domain_report_adoption']);
    final artifactId = _safeText(artifact?['artifact_id'], maxLength: 20);
    final sha256 = _safeText(artifact?['sha256'], maxLength: 64);
    final title = _safeText(document?['title'], maxLength: 300);
    final markdown = document?['markdown'];
    final requestId = _safeText(document?['request_id'], maxLength: 128);
    final replayed = envelope?['replayed'];
    final workId = _safeText(returnRef?['work_id'], maxLength: 80);
    if (artifactId == null ||
        !RegExp(r'^ART-[0-9a-f]{16}$').hasMatch(artifactId) ||
        sha256 == null ||
        !RegExp(r'^[0-9a-f]{64}$').hasMatch(sha256) ||
        (expectedArtifactId != null && artifactId != expectedArtifactId) ||
        (expectedSha256 != null && sha256 != expectedSha256) ||
        title != expected.title ||
        document?['kind'] != 'report' ||
        requestId != expected.requestId ||
        markdown is! String ||
        markdown.trim().isEmpty ||
        workId == null ||
        !workId.startsWith('WORK-') ||
        returnRef?['artifact_id'] != artifactId ||
        returnRef?['version'] != 1 ||
        !_isSharedScope(_asMap(returnRef?['scope'])) ||
        binding == null ||
        _contextSignature(binding) != _contextSignature(expected.binding) ||
        (requireReplayState && replayed is! bool)) {
      throw const _InvalidSourceBriefResponse();
    }
    return SourceBriefSharedSavedWork(
      artifactId: artifactId,
      sha256: sha256,
      title: title!,
      markdown: markdown,
      requestId: requestId!,
      replayed: replayed == true,
    );
  }

  void _failSharedAdoption(int? operation, SourceBriefErrorKind kind) {
    _sharedAdoptionState = SourceBriefSharedAdoptionState.failed;
    _sharedAdoptionErrorKind = kind;
    if (operation == null) {
      notifyListeners();
    } else {
      _finish(operation, phase: SourceBriefPhase.ready);
    }
  }

  void _resetSharedAdoption() {
    _pendingSharedAdoption = null;
    _sharedAdoptionState = SourceBriefSharedAdoptionState.idle;
    _sharedAdoptionErrorKind = null;
    _sharedAdoptedWork = null;
  }

  SourceBriefErrorKind? _errorKind;
  String? _scopeLabel;
  _SourceContextSelection? _selection;

  SourceBriefPhase get phase => _phase;
  bool get busy => _busy;
  String? get taskId => _taskId;
  String? get jobId => _jobId;
  SourceBriefTaskState get taskState => _taskState;
  bool get canResume => _canResume;
  SourceBriefResult? get result => _result;
  String? get resultArrivalToken => _resultArrivalToken;
  SourceBriefErrorKind? get errorKind => _errorKind;
  String? get scopeLabel => _scopeLabel;
  bool get globalScope => _selection?.globalScope == true;

  Future<void> initialize() async {
    if (_disposed) return;
    final operation = _beginOperation();
    final fresh = await _loadFreshContext(operation);
    if (fresh == null || !_isCurrent(operation)) return;
    _finish(
      operation,
      phase: SourceBriefPhase.ready,
      errorKind: fresh.scopeChanged
          ? SourceBriefErrorKind.contextChanged
          : null,
    );
  }

  Future<void> start({String? businessQuestion}) async {
    if (_disposed) return;
    final operation = _beginOperation();
    final fresh = await _loadFreshContext(operation);
    if (fresh == null || !_isCurrent(operation)) return;

    _clearReportState();
    if (!_contextStillCurrent(fresh, operation)) return;

    final question = businessQuestion?.trim();
    if (question != null &&
        question.isNotEmpty &&
        (question.runes.length < 4 ||
            question.runes.length > 1500 ||
            RegExp(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]').hasMatch(question))) {
      _finish(
        operation,
        phase: SourceBriefPhase.failed,
        errorKind: SourceBriefErrorKind.invalidResponse,
      );
      return;
    }

    try {
      final response = await client.startSourceBriefTask(
        domainId: _domainId,
        limit: 30,
        businessQuestion: question == null || question.isEmpty
            ? null
            : question,
      );
      if (!_isCurrent(operation)) return;
      if (!_contextStillCurrent(fresh, operation)) return;
      await _applyTaskResponse(
        response,
        fresh: fresh,
        operation: operation,
        newlySubmitted: true,
      );
    } catch (error) {
      _fail(operation, _errorFor(error), fresh: fresh);
    }
  }

  Future<void> refreshTask() async {
    if (_disposed) return;
    final operation = _beginOperation();
    final expectedTaskId = _taskId;
    final expectedJobId = _jobId;
    final fresh = await _loadFreshContext(operation);
    if (fresh == null || !_isCurrent(operation)) return;
    if (fresh.scopeChanged) {
      _finish(
        operation,
        phase: SourceBriefPhase.ready,
        errorKind: SourceBriefErrorKind.contextChanged,
      );
      return;
    }
    if (expectedTaskId == null) {
      _finish(
        operation,
        phase: SourceBriefPhase.failed,
        errorKind: SourceBriefErrorKind.notFound,
      );
      return;
    }
    if (!_contextStillCurrent(fresh, operation)) return;

    try {
      final response = await client.sourceBriefTask(
        domainId: _domainId,
        taskId: expectedTaskId,
      );
      if (!_isCurrent(operation)) return;
      if (!_contextStillCurrent(fresh, operation)) return;
      await _applyTaskResponse(
        response,
        fresh: fresh,
        operation: operation,
        expectedTaskId: expectedTaskId,
        expectedJobId: expectedJobId,
      );
    } catch (error) {
      _fail(operation, _errorFor(error), fresh: fresh);
    }
  }

  Future<void> resume() async {
    if (_disposed) return;
    final operation = _beginOperation();
    final expectedTaskId = _taskId;
    final expectedJobId = _jobId;
    final wasResumable = _canResume;
    final fresh = await _loadFreshContext(operation);
    if (fresh == null || !_isCurrent(operation)) return;
    if (fresh.scopeChanged) {
      _finish(
        operation,
        phase: SourceBriefPhase.ready,
        errorKind: SourceBriefErrorKind.contextChanged,
      );
      return;
    }
    if (expectedTaskId == null || !wasResumable) {
      _finish(
        operation,
        phase: SourceBriefPhase.failed,
        errorKind: SourceBriefErrorKind.invalidResponse,
      );
      return;
    }
    if (!_contextStillCurrent(fresh, operation)) return;

    try {
      final response = await client.resumeSourceBriefTask(
        domainId: _domainId,
        taskId: expectedTaskId,
      );
      if (!_isCurrent(operation)) return;
      if (!_contextStillCurrent(fresh, operation)) return;
      await _applyTaskResponse(
        response,
        fresh: fresh,
        operation: operation,
        expectedTaskId: expectedTaskId,
        expectedJobId: expectedJobId,
      );
    } catch (error) {
      _fail(operation, _errorFor(error), fresh: fresh);
    }
  }

  Future<void> openTask(String taskId) async {
    if (_disposed) return;
    final operation = _beginOperation();
    final requestedTaskId = _safeIdentifier(taskId);
    final fresh = await _loadFreshContext(operation);
    if (fresh == null || !_isCurrent(operation)) return;
    if (fresh.scopeChanged) {
      _finish(
        operation,
        phase: SourceBriefPhase.ready,
        errorKind: SourceBriefErrorKind.contextChanged,
      );
      return;
    }
    if (requestedTaskId == null) {
      _finish(
        operation,
        phase: SourceBriefPhase.failed,
        errorKind: SourceBriefErrorKind.invalidResponse,
      );
      return;
    }
    _clearReportState();
    if (!_contextStillCurrent(fresh, operation)) return;

    try {
      final response = await client.sourceBriefTask(
        domainId: _domainId,
        taskId: requestedTaskId,
      );
      if (!_isCurrent(operation)) return;
      if (!_contextStillCurrent(fresh, operation)) return;
      await _applyTaskResponse(
        response,
        fresh: fresh,
        operation: operation,
        expectedTaskId: requestedTaskId,
      );
    } catch (error) {
      _fail(operation, _errorFor(error), fresh: fresh);
    }
  }

  Future<void> reopenJob(String jobId) async {
    if (_disposed) return;
    final operation = _beginOperation();
    final requestedJobId = _safeIdentifier(jobId);
    final fresh = await _loadFreshContext(operation);
    if (fresh == null || !_isCurrent(operation)) return;
    if (fresh.scopeChanged) {
      _finish(
        operation,
        phase: SourceBriefPhase.ready,
        errorKind: SourceBriefErrorKind.contextChanged,
      );
      return;
    }
    if (requestedJobId == null) {
      _finish(
        operation,
        phase: SourceBriefPhase.failed,
        errorKind: SourceBriefErrorKind.invalidResponse,
      );
      return;
    }
    _clearReportState();
    if (!_contextStillCurrent(fresh, operation)) return;
    await _readBackJob(requestedJobId, fresh: fresh, operation: operation);
  }

  void clear() {
    if (_disposed) return;
    _generation += 1;
    _clearReportState();
    _clearSavedResearchHistory();
    _busy = false;
    _errorKind = null;
    _phase = _selection == null
        ? SourceBriefPhase.idle
        : SourceBriefPhase.ready;
    notifyListeners();
  }

  /// Invalidates transient results immediately after the shell changes scope.
  /// The server still reauthorizes every report request independently.
  void syncContext() {
    if (_disposed || _selection == null) return;
    final selection = _selectionFromEnvelope(
      client.currentContextEnvelope,
      domainId: _domainId,
    );
    if (selection != null && _selection!.sameScope(selection)) return;

    _generation += 1;
    _clearReportState();
    if (selection == null) {
      _forgetContext();
      _phase = SourceBriefPhase.failed;
    } else {
      _selection = selection;
      _scopeLabel = selection.scopeLabel;
      _phase = SourceBriefPhase.ready;
    }
    _busy = false;
    _errorKind = SourceBriefErrorKind.contextChanged;
    notifyListeners();
  }

  Future<_FreshSourceContext?> _loadFreshContext(int operation) async {
    try {
      final response = await client.settingsContext();
      if (!_isCurrent(operation)) return null;
      final selection = _SourceContextSelection.parse(
        response,
        domainId: _domainId,
      );
      if (selection == null) {
        _forgetContext();
        _finish(
          operation,
          phase: SourceBriefPhase.failed,
          errorKind: SourceBriefErrorKind.contextUnavailable,
        );
        return null;
      }
      final responseSignature = _contextSignature(response);
      final currentSignature = _contextSignature(client.currentContextEnvelope);
      if (responseSignature == null || responseSignature != currentSignature) {
        _updateSelectionFromCurrentEnvelope();
        _finish(
          operation,
          phase: _selection == null
              ? SourceBriefPhase.failed
              : SourceBriefPhase.ready,
          errorKind: SourceBriefErrorKind.contextChanged,
        );
        return null;
      }

      final changed = _selection != null && !_selection!.sameScope(selection);
      if (changed) {
        _clearReportState();
        _clearSavedResearchHistory();
      }
      _selection = selection;
      _scopeLabel = selection.scopeLabel;
      return _FreshSourceContext(
        selection: selection,
        signature: responseSignature,
        scopeChanged: changed,
      );
    } catch (error) {
      if (!_isCurrent(operation)) return null;
      final errorKind = _errorFor(error);
      if (errorKind == SourceBriefErrorKind.unavailable ||
          errorKind == SourceBriefErrorKind.accessDenied) {
        // Keep opaque recovery references, but never show a prior result
        // without a fresh, verified scope selection.
        _result = null;
        _scopeLabel = null;
        if (errorKind == SourceBriefErrorKind.accessDenied) {
          _canResume = false;
        }
      } else {
        _forgetContext();
      }
      _finish(operation, phase: SourceBriefPhase.failed, errorKind: errorKind);
      return null;
    }
  }

  bool _contextStillCurrent(_FreshSourceContext fresh, int operation) {
    if (!_isCurrent(operation)) return false;
    if (_contextSignature(client.currentContextEnvelope) == fresh.signature) {
      return true;
    }
    _updateSelectionFromCurrentEnvelope();
    _finish(
      operation,
      phase: _selection == null
          ? SourceBriefPhase.failed
          : SourceBriefPhase.ready,
      errorKind: SourceBriefErrorKind.contextChanged,
    );
    return false;
  }

  void _updateSelectionFromCurrentEnvelope() {
    _clearReportState();
    final selection = _selectionFromEnvelope(
      client.currentContextEnvelope,
      domainId: _domainId,
    );
    if (selection == null) {
      _forgetContext();
      return;
    }
    if (_selection != null && !_selection!.sameScope(selection)) {
      _clearSavedResearchHistory();
    }
    _selection = selection;
    _scopeLabel = selection.scopeLabel;
  }

  Future<void> _applyTaskResponse(
    Map<String, dynamic> response, {
    required _FreshSourceContext fresh,
    required int operation,
    bool newlySubmitted = false,
    String? expectedTaskId,
    String? expectedJobId,
  }) async {
    if (response['ok'] != true) {
      _fail(operation, _errorForResponse(response), fresh: fresh);
      return;
    }
    final task = _asMap(response['task']);
    if (task == null) {
      _finish(
        operation,
        phase: SourceBriefPhase.failed,
        errorKind: SourceBriefErrorKind.invalidResponse,
      );
      return;
    }

    final returnedTaskId = _safeIdentifier(task['task_id']);
    final returnedJobId = _safeIdentifier(task['job_id']);
    if (returnedTaskId == null ||
        returnedJobId == null ||
        (expectedTaskId != null && returnedTaskId != expectedTaskId) ||
        (expectedJobId != null && returnedJobId != expectedJobId)) {
      _clearReportState();
      _finish(
        operation,
        phase: SourceBriefPhase.failed,
        errorKind: SourceBriefErrorKind.invalidResponse,
      );
      return;
    }

    final parsedState = _parseTaskState(task['state']);
    _taskId = returnedTaskId;
    _jobId = returnedJobId;
    if (newlySubmitted) _newResultTaskId = returnedTaskId;
    _taskState = parsedState;
    _canResume =
        task['can_resume'] == true &&
        const {
          SourceBriefTaskState.pending,
          SourceBriefTaskState.failed,
          SourceBriefTaskState.interrupted,
        }.contains(parsedState);
    _result = null;

    if (parsedState == SourceBriefTaskState.unknown) {
      _finish(
        operation,
        phase: SourceBriefPhase.failed,
        errorKind: SourceBriefErrorKind.invalidResponse,
      );
      return;
    }

    if (parsedState == SourceBriefTaskState.succeeded) {
      notifyListeners();
      await _readBackJob(
        returnedJobId,
        fresh: fresh,
        operation: operation,
        newlyGeneratedTaskId: _newResultTaskId == returnedTaskId
            ? returnedTaskId
            : null,
      );
      return;
    }

    _finish(
      operation,
      phase: SourceBriefPhase.ready,
      errorKind: parsedState == SourceBriefTaskState.failed
          ? _errorForTask(task['error'])
          : null,
    );
  }

  Future<void> _readBackJob(
    String jobId, {
    required _FreshSourceContext fresh,
    required int operation,
    String? newlyGeneratedTaskId,
  }) async {
    if (!_contextStillCurrent(fresh, operation)) return;
    try {
      final response = await client.sourceBriefJob(
        domainId: _domainId,
        jobId: jobId,
      );
      if (!_isCurrent(operation)) return;
      if (!_contextStillCurrent(fresh, operation)) return;
      if (response['ok'] != true) {
        _fail(operation, _errorForResponse(response), fresh: fresh);
        return;
      }
      final resultMap = _asMap(response['result']);
      if (resultMap == null) {
        _finish(
          operation,
          phase: SourceBriefPhase.failed,
          errorKind: SourceBriefErrorKind.invalidResponse,
        );
        return;
      }
      final parsed = _parseResult(
        resultMap,
        expectedJobId: jobId,
        expectedContext: fresh.selection,
      );
      final previous = _result;
      if (previous != null &&
          (previous.jobId != parsed.jobId ||
              previous.artifactHash != parsed.artifactHash ||
              previous.scope.scopeKey != parsed.scope.scopeKey)) {
        _resetSharedAdoption();
      }
      _jobId = jobId;
      _taskState = SourceBriefTaskState.succeeded;
      _canResume = false;
      _result = parsed;
      final resultVersion =
          '${parsed.scope.scopeKey}:${parsed.jobId}:${parsed.artifactHash}';
      if (newlyGeneratedTaskId != null &&
          newlyGeneratedTaskId == _newResultTaskId &&
          parsed.records.isNotEmpty) {
        _resultArrivalToken =
            '$newlyGeneratedTaskId:$resultVersion:${++_resultArrivalSequence}';
      }
      if (_newResultTaskId == newlyGeneratedTaskId) {
        _newResultTaskId = null;
      }
      _finish(operation, phase: SourceBriefPhase.ready);
    } catch (error) {
      _fail(operation, _errorFor(error), fresh: fresh);
    }
  }

  int _beginOperation({bool preserveResult = false}) {
    if (_disposed) return _generation;
    _generation += 1;
    _busy = true;
    _phase = SourceBriefPhase.loading;
    _errorKind = null;
    _resultArrivalToken = null;
    // Each operation must verify access and the saved artifact again. Keep
    // recovery references, but do not present the previous read as current.
    if (!preserveResult) _result = null;
    sourceStatistics = null;
    notifyListeners();
    return _generation;
  }

  void _finish(
    int operation, {
    required SourceBriefPhase phase,
    SourceBriefErrorKind? errorKind,
  }) {
    if (!_isCurrent(operation)) return;
    _busy = false;
    _phase = phase;
    _errorKind = errorKind;
    notifyListeners();
  }

  void _finishSavedWorkContextFailure(int operation) {
    if (!_isCurrent(operation)) return;
    if (_savedWorkState == SourceBriefSavedWorkState.idle) return;
    _savedWorkState = SourceBriefSavedWorkState.failed;
    _savedWorkErrorKind = _errorKind ?? SourceBriefErrorKind.unavailable;
    notifyListeners();
  }

  void _fail(
    int operation,
    SourceBriefErrorKind errorKind, {
    _FreshSourceContext? fresh,
  }) {
    if (!_isCurrent(operation)) return;
    if (fresh != null &&
        _contextSignature(client.currentContextEnvelope) != fresh.signature) {
      _updateSelectionFromCurrentEnvelope();
      _finish(
        operation,
        phase: _selection == null
            ? SourceBriefPhase.failed
            : SourceBriefPhase.ready,
        errorKind: SourceBriefErrorKind.contextChanged,
      );
      return;
    }
    if (errorKind == SourceBriefErrorKind.accessDenied ||
        errorKind == SourceBriefErrorKind.notFound) {
      _canResume = false;
    }
    _finish(operation, phase: SourceBriefPhase.failed, errorKind: errorKind);
  }

  void _clearReportState() {
    _resetSharedAdoption();
    _taskId = null;
    _jobId = null;
    _taskState = SourceBriefTaskState.unknown;
    _canResume = false;
    _result = null;
    _newResultTaskId = null;
    _resultArrivalToken = null;
    statisticsTaskId = null;
    _statisticsJobId = null;
    sourceStatistics = null;
    _resetSavedWorkState();
  }

  void _resetSavedWorkState() {
    _savedWorkState = SourceBriefSavedWorkState.idle;
    _savedWorkErrorKind = null;
    _savedWorkArtifactId = null;
    _savedWorkSha256 = null;
    _savedWorkTitle = null;
    _savedWorkMarkdown = null;
    _pendingSaveRequestId = null;
    _pendingSaveTitle = null;
    _pendingSaveJobId = null;
    _pendingSaveArtifactHash = null;
  }

  void _clearSavedResearchHistory() {
    _savedHistory.clear();
    _savedHistoryState = SourceBriefHistoryState.idle;
    _savedHistoryErrorKind = null;
    _openedHistoryWork = null;
    _savedHistoryCursor = null;
    _savedHistoryHasMore = false;
    _savedHistoryVerificationComplete = true;
    _savedHistoryUnverifiedCount = null;
    _pendingRevision = null;
  }

  void _forgetContext() {
    _clearReportState();
    _clearSavedResearchHistory();
    _selection = null;
    _scopeLabel = null;
  }

  bool _isCurrent(int operation) => !_disposed && operation == _generation;

  SourceBriefErrorKind _errorFor(Object error) {
    if (error is _ContextChanged) {
      return SourceBriefErrorKind.contextChanged;
    }
    if (error is FormatException || error is _InvalidSourceBriefResponse) {
      return SourceBriefErrorKind.invalidResponse;
    }
    if (error is LumenisCoreException) {
      return switch (error.statusCode) {
        401 || 403 => SourceBriefErrorKind.accessDenied,
        404 => SourceBriefErrorKind.notFound,
        _ => SourceBriefErrorKind.unavailable,
      };
    }
    return SourceBriefErrorKind.unavailable;
  }

  SourceBriefErrorKind _errorForResponse(Map<String, dynamic> response) {
    final code = _safeText(response['code'], maxLength: 120)?.toUpperCase();
    if (code == null) return SourceBriefErrorKind.unavailable;
    if (code.contains('DENIED') || code.contains('FORBIDDEN')) {
      return SourceBriefErrorKind.accessDenied;
    }
    if (code.contains('NOT_FOUND')) return SourceBriefErrorKind.notFound;
    return SourceBriefErrorKind.unavailable;
  }

  SourceBriefErrorKind _errorForTask(Object? value) {
    final code = _safeText(value, maxLength: 120)?.toUpperCase();
    if (code != null && code.contains('DENIED')) {
      return SourceBriefErrorKind.accessDenied;
    }
    return SourceBriefErrorKind.unavailable;
  }

  @override
  void dispose() {
    _disposed = true;
    _generation += 1;
    super.dispose();
  }
}

SourceBriefResult _parseResult(
  Map<String, Object?> result, {
  required String expectedJobId,
  required _SourceContextSelection expectedContext,
}) {
  if (result['job_id'] != expectedJobId || result['job_state'] != 'completed') {
    throw const _InvalidSourceBriefResponse();
  }
  final artifact = _asMap(result['artifact_outcome']);
  if (artifact == null ||
      artifact['state'] != 'persisted_and_reopened_verified' ||
      artifact['report_id'] != expectedJobId) {
    throw const _InvalidSourceBriefResponse();
  }
  final artifactHash = _safeText(artifact['artifact_hash'], maxLength: 64);
  if (artifactHash == null ||
      !RegExp(r'^[0-9a-f]{64}$').hasMatch(artifactHash)) {
    throw const _InvalidSourceBriefResponse();
  }

  final countValue = artifact['source_count'];
  final sourceCount = countValue == null
      ? null
      : countValue is int && countValue >= 0
      ? countValue
      : throw const _InvalidSourceBriefResponse();

  final sourceBrief = _asMap(result['source_brief']);
  if (sourceBrief == null) throw const _InvalidSourceBriefResponse();
  final rawScope = _asMap(sourceBrief['scope']);
  final scope = _parseScope(rawScope);
  if (scope == null) throw const _InvalidSourceBriefResponse();
  if (!expectedContext.matches(scope)) throw const _ContextChanged();
  final rawRecords = sourceBrief['records'];
  if (rawRecords is! List) throw const _InvalidSourceBriefResponse();
  final records = <SourceBriefSource>[];
  for (final rawRecord in rawRecords) {
    final record = _asMap(rawRecord);
    if (record == null) throw const _InvalidSourceBriefResponse();
    final sourceId = _safeIdentifier(record['source_id']);
    final evidenceRef = _safeIdentifier(record['scope_evidence_ref']);
    if (sourceId == null ||
        evidenceRef == null ||
        record['evidence_id'] != evidenceRef) {
      throw const _InvalidSourceBriefResponse();
    }
    if (!scope.globalScope &&
        (record['subject_id'] != scope.subjectId ||
            record['brand_focus_id'] != scope.brandFocusId)) {
      throw const _ContextChanged();
    }
    records.add(
      SourceBriefSource(
        sourceId: sourceId,
        title: _safeText(record['title'], maxLength: 240),
        sourceUrl: _safeSourceUrl(record['source_url']),
        publishedAt: _safeText(record['publish_datetime'], maxLength: 100),
        capturedAt: _safeText(record['captured_at'], maxLength: 100),
        evidenceRef: evidenceRef,
      ),
    );
  }
  if (sourceCount != null && sourceCount != records.length) {
    throw const _InvalidSourceBriefResponse();
  }

  final rawBusiness = _asMap(result['business_analysis']);
  final businessState = _businessAnalysisState(rawBusiness?['state']);
  final sourceSample = _parseSourceBriefQuerySample(sourceBrief['sample']);
  final analysisSample = _parseSourceBriefAnalysisSample(
    rawBusiness?['sample'],
  );
  final question = _safeText(result['business_question'], maxLength: 3000);
  if (question != null &&
      (question.runes.length < 4 || question.runes.length > 1500)) {
    throw const _InvalidSourceBriefResponse();
  }
  final researchAnalysis = _parseResearchAnalysis(
    result['research_analysis'],
    scope: scope,
    records: records,
    question: question,
  );
  final rawMarkdown = sourceBrief['markdown'];
  final markdown = _safeText(rawMarkdown, maxLength: 200000);
  if (rawMarkdown != null &&
      (markdown == null ||
          _safeText(sourceBrief['content_hash'], maxLength: 64) == null ||
          !RegExp(
            r'^[a-f0-9]{64}$',
          ).hasMatch(sourceBrief['content_hash'] as String))) {
    throw const _InvalidSourceBriefResponse();
  }
  SourceBriefBusinessAnalysis? analysis;
  if (businessState == SourceBriefBusinessAnalysisState.draft) {
    final rawAnalysis = _asMap(rawBusiness?['analysis']);
    if (rawAnalysis == null) throw const _InvalidSourceBriefResponse();
    analysis = _parseBusinessAnalysis(
      rawAnalysis,
      knownSourceIds: records.map((record) => record.sourceId).toSet(),
    );
  }

  final reviewStatus = _safeReviewStatus(
    result['review_status'] ?? rawBusiness?['review_status'],
  );
  return SourceBriefResult(
    jobId: expectedJobId,
    reportId: artifact['report_id'] as String,
    artifactHash: artifactHash,
    sourceCount: sourceCount,
    scope: scope,
    records: records,
    businessQuestion: question,
    businessAnalysisState: businessState,
    analysis: analysis,
    reviewStatus: reviewStatus,
    sourceSample: sourceSample,
    analysisSample: analysisSample,
    researchAnalysis: researchAnalysis,
    markdown: markdown,
  );
}

SourceBriefResearchAnalysis? _parseResearchAnalysis(
  Object? value, {
  required SourceBriefScope scope,
  required List<SourceBriefSource> records,
  required String? question,
}) {
  if (value == null) return null;
  final raw = _asMap(value);
  if (raw == null) throw const _InvalidSourceBriefResponse();
  List<String> texts(Object? values, {int max = 100, int length = 5000}) {
    if (values is! List || values.length > max) {
      throw const _InvalidSourceBriefResponse();
    }
    return values
        .map(
          (v) =>
              _safeText(v, maxLength: length) ??
              (throw const _InvalidSourceBriefResponse()),
        )
        .toList(growable: false);
  }

  final status = raw['status'];
  final limitations = texts(raw['limitations']);
  if (status == 'source_use_unavailable') {
    if (raw['ranked_findings'] is! List ||
        (raw['ranked_findings'] as List).isNotEmpty ||
        raw['fact_verified'] != false) {
      throw const _InvalidSourceBriefResponse();
    }
    return SourceBriefResearchAnalysis(
      status: status as String,
      summary: null,
      findings: const [],
      questions: const [],
      numberChecks: const [],
      limitations: limitations,
    );
  }
  if (raw['schema'] != 'source_bound_research.v1' ||
      !{'research_draft', 'needs_sources', 'needs_question'}.contains(status) ||
      raw['permission_granted'] != false ||
      raw['canonical_promotion'] != false) {
    throw const _InvalidSourceBriefResponse();
  }
  final sourceScope = _parseScope(_asMap(raw['scope']));
  if (sourceScope == null ||
      sourceScope.domainId != scope.domainId ||
      sourceScope.globalScope != scope.globalScope ||
      sourceScope.subjectId != scope.subjectId ||
      sourceScope.brandFocusId != scope.brandFocusId ||
      sourceScope.scopeKey != scope.scopeKey) {
    throw const _ContextChanged();
  }
  if (question != null && raw['goal'] != question) {
    throw const _InvalidSourceBriefResponse();
  }
  final summary = _safeText(raw['summary'], maxLength: 10000);
  final setHash = _safeText(raw['source_set_sha256'], maxLength: 64);
  if (summary == null ||
      setHash == null ||
      !RegExp(r'^[a-f0-9]{64}$').hasMatch(setHash)) {
    throw const _InvalidSourceBriefResponse();
  }
  bool bound(String id, String ref) =>
      records.any((r) => r.sourceId == id && r.evidenceRef == ref);
  final rawFindings = raw['ranked_findings'],
      rawLineage = raw['evidence_lineage'];
  if (rawFindings is! List ||
      rawFindings.length > 100 ||
      rawLineage is! List ||
      rawLineage.length > 100) {
    throw const _InvalidSourceBriefResponse();
  }
  final findings = <SourceBriefResearchFinding>[];
  final findingRefs = <String, String>{};
  for (final value in rawFindings) {
    final item = _asMap(value);
    final id = _safeIdentifier(item?['finding_id']);
    final sid = _safeIdentifier(item?['source_id']);
    final content = _safeText(item?['content'], maxLength: 100000);
    final refs = item?['evidence_refs'];
    final lineageId = _safeIdentifier(item?['lineage_id']);
    if (item == null ||
        id == null ||
        sid == null ||
        content == null ||
        lineageId == null ||
        refs is! List ||
        refs.length != 1 ||
        refs.single is! String ||
        !bound(sid, refs.single as String) ||
        item['claim_type'] != 'source_statement' ||
        item['fact_verified'] != false ||
        item['validated'] != false ||
        item['confidence'] != null ||
        findingRefs.containsKey(id)) {
      throw const _InvalidSourceBriefResponse();
    }
    final matches = rawLineage
        .map(_asMap)
        .where((v) => v?['lineage_id'] == lineageId)
        .toList();
    final lineage = matches.length == 1 ? matches.single : null;
    final provenance = _asMap(lineage?['provenance']);
    if (lineage?['source'] != sid ||
        lineage?['evidence_id'] != refs.single ||
        provenance?['fact_verified'] != false) {
      throw const _InvalidSourceBriefResponse();
    }
    findingRefs[id] = refs.single as String;
    findings.add(
      SourceBriefResearchFinding(
        id: id,
        sourceId: sid,
        evidenceRef: refs.single as String,
        content: content,
        title: _safeText(item['title'], maxLength: 1000),
        truncated: item['excerpt_truncated'] is bool
            ? item['excerpt_truncated'] as bool
            : null,
      ),
    );
  }
  final rawQuestions = raw['hypotheses'], rawComparisons = raw['comparisons'];
  if (rawQuestions is! List ||
      rawQuestions.length > 100 ||
      rawComparisons is! List ||
      rawComparisons.length > 100) {
    throw const _InvalidSourceBriefResponse();
  }
  final questions = <SourceBriefResearchQuestion>[];
  for (final value in rawQuestions) {
    final item = _asMap(value);
    final statement = _safeText(item?['statement'], maxLength: 5000);
    final ids = texts(item?['finding_ids'], max: 100, length: 160);
    final refs = texts(item?['evidence_refs'], max: 100, length: 160);
    if (item == null ||
        statement == null ||
        item['claim_type'] != 'hypothesis' ||
        !{
          'proposed',
          'challenged',
          'rejected',
          'reinstated',
        }.contains(item['status']) ||
        item['source_set_sha256'] != setHash ||
        item['confidence'] != null ||
        ids.isEmpty ||
        ids.any((id) => !findingRefs.containsKey(id)) ||
        refs
            .toSet()
            .difference(ids.map((id) => findingRefs[id]!).toSet())
            .isNotEmpty ||
        ids
            .map((id) => findingRefs[id]!)
            .toSet()
            .difference(refs.toSet())
            .isNotEmpty) {
      throw const _InvalidSourceBriefResponse();
    }
    questions.add(
      SourceBriefResearchQuestion(
        statement: statement,
        status: item['status'] as String,
        findingIds: ids,
        validationNeeded: texts(item['validation_needed']),
      ),
    );
  }
  final checks = <SourceBriefNumberCheck>[];
  for (final value in rawComparisons) {
    final item = _asMap(value);
    final sid = _safeIdentifier(item?['source_id']);
    final refs = item?['evidence_refs'];
    if (item == null ||
        sid == null ||
        refs is! List ||
        refs.length != 1 ||
        refs.single is! String ||
        !bound(sid, refs.single as String) ||
        item['comparison_status'] !=
            'NOT_COMPARABLE_WITHOUT_MEASURE_DEFINITIONS' ||
        [
          'unit',
          'currency',
          'period',
          'denominator',
        ].any((k) => item[k] != null)) {
      throw const _InvalidSourceBriefResponse();
    }
    checks.add(
      SourceBriefNumberCheck(
        sourceId: sid,
        literals: texts(item['numeric_literals'], max: 2000),
      ),
    );
  }
  return SourceBriefResearchAnalysis(
    status: status as String,
    summary: summary,
    findings: findings,
    questions: questions,
    numberChecks: checks,
    limitations: limitations,
  );
}

SourceBriefQuerySample? _parseSourceBriefQuerySample(Object? value) {
  final raw = _asMap(value);
  if (raw == null) return null;
  return SourceBriefQuerySample(
    candidateCount: _optionalSampleCount(raw['candidate_count']),
    scannedCount: _optionalSampleCount(raw['scanned_count']),
    rejectedCount: _optionalSampleCount(raw['rejected_count']),
    returnedCount: _optionalSampleCount(raw['returned_count']),
    returnedVerifiedCount: _optionalSampleCount(raw['returned_verified_count']),
    withheldCount: _optionalSampleCount(raw['withheld_count']),
    truncated: raw['truncated'] is bool ? raw['truncated'] as bool : null,
    platformCountsSample: _optionalSampleCounts(raw['platform_counts_sample']),
    countsBasis: _safeText(raw['counts_basis'], maxLength: 240),
  );
}

SourceBriefAnalysisSample? _parseSourceBriefAnalysisSample(Object? value) {
  final raw = _asMap(value);
  if (raw == null) return null;
  return SourceBriefAnalysisSample(
    availableBriefCount: _optionalSampleCount(raw['available_brief_count']),
    analyzedSourceCount: _optionalSampleCount(raw['analyzed_source_count']),
    omittedSourceCount: _optionalSampleCount(raw['omitted_source_count']),
    hasTruncatedBodies: raw['has_truncated_bodies'] is bool
        ? raw['has_truncated_bodies'] as bool
        : null,
    selection: _safeText(raw['selection'], maxLength: 240),
    coverage: _safeText(raw['coverage'], maxLength: 80),
  );
}

int? _optionalSampleCount(Object? value) =>
    value is int && value >= 0 ? value : null;

Map<String, int>? _optionalSampleCounts(Object? value) {
  final raw = _asMap(value);
  if (raw == null) return null;
  final counts = <String, int>{};
  for (final entry in raw.entries) {
    final key = _safeText(entry.key, maxLength: 80);
    final count = _optionalSampleCount(entry.value);
    if (key == null || key != entry.key || count == null) return null;
    counts[key] = count;
  }
  return Map.unmodifiable(counts);
}

SourceBriefScope? _parseScope(Map<String, Object?>? value) {
  if (value == null || value['global'] is! bool) return null;
  final productId = value['product_id'];
  final domainId = value['domain_id'];
  final isCth = productId == 'CTH' && domainId == 'cth';
  final isBmp = productId == 'ZBMP' && domainId == 'zbmp';
  if (!isCth && !isBmp) return null;
  final globalScope = value['global'] as bool;
  final rawSubjectId = value['subject_id'];
  final rawBrandFocusId = value['brand_focus_id'];
  final subjectId = _optionalIdentifier(rawSubjectId);
  final brandFocusId = _optionalIdentifier(rawBrandFocusId);
  final entityLabel = _safeText(value['entity_label'], maxLength: 240);
  final scopeKey = _safeText(value['scope_key'], maxLength: 64);
  if (entityLabel == null ||
      scopeKey == null ||
      !RegExp(r'^[0-9a-f]{64}$').hasMatch(scopeKey) ||
      (rawSubjectId != null && subjectId == null) ||
      (rawBrandFocusId != null && brandFocusId == null) ||
      (globalScope && (subjectId != null || brandFocusId != null)) ||
      (!globalScope && isCth && (subjectId == null || brandFocusId != null)) ||
      (!globalScope && isBmp && (brandFocusId == null || subjectId != null))) {
    return null;
  }
  return SourceBriefScope(
    productId: productId as String,
    domainId: domainId as String,
    globalScope: globalScope,
    subjectId: subjectId,
    brandFocusId: brandFocusId,
    entityLabel: entityLabel,
    scopeKey: scopeKey,
  );
}

SourceBriefBusinessAnalysis _parseBusinessAnalysis(
  Map<String, Object?> value, {
  required Set<String> knownSourceIds,
}) {
  const keys = {
    'source_observations',
    'interpretations',
    'proposed_actions',
    'unknowns',
  };
  if (value.keys.toSet().difference(keys).isNotEmpty ||
      value.keys.toSet().length != keys.length) {
    throw const _InvalidSourceBriefResponse();
  }

  final observationsValue = value['source_observations'];
  final interpretationsValue = value['interpretations'];
  final actionsValue = value['proposed_actions'];
  final unknownsValue = value['unknowns'];
  if (observationsValue is! List ||
      interpretationsValue is! List ||
      actionsValue is! List ||
      unknownsValue is! List ||
      observationsValue.isEmpty ||
      interpretationsValue.isEmpty ||
      actionsValue.isEmpty ||
      unknownsValue.isEmpty ||
      observationsValue.length > 3 ||
      interpretationsValue.length > 3 ||
      actionsValue.length > 3 ||
      unknownsValue.length > 5) {
    throw const _InvalidSourceBriefResponse();
  }

  final observations = <SourceBriefObservation>[];
  for (final raw in observationsValue) {
    final row = _asMap(raw);
    final sourceId = _safeIdentifier(row?['source_id']);
    final excerpt = _safeText(row?['excerpt'], maxLength: 500);
    if (row == null ||
        row.keys.toSet().difference({'source_id', 'excerpt'}).isNotEmpty ||
        sourceId == null ||
        !knownSourceIds.contains(sourceId) ||
        excerpt == null) {
      throw const _InvalidSourceBriefResponse();
    }
    observations.add(
      SourceBriefObservation(sourceId: sourceId, excerpt: excerpt),
    );
  }

  final interpretations = <SourceBriefInterpretation>[];
  for (final raw in interpretationsValue) {
    final row = _asMap(raw);
    final text = _safeText(row?['text'], maxLength: 180);
    final sourceIds = _sourceReferences(
      row?['source_ids'],
      knownSourceIds: knownSourceIds,
    );
    if (row == null ||
        row.keys.toSet().difference({'text', 'source_ids'}).isNotEmpty ||
        text == null ||
        sourceIds == null) {
      throw const _InvalidSourceBriefResponse();
    }
    interpretations.add(
      SourceBriefInterpretation(text: text, sourceIds: sourceIds),
    );
  }

  final actions = <SourceBriefProposedAction>[];
  for (final raw in actionsValue) {
    final row = _asMap(raw);
    final action = _safeText(row?['action'], maxLength: 180);
    final reason = _safeText(row?['reason'], maxLength: 180);
    final check = _safeText(row?['check'], maxLength: 180);
    final sourceIds = _sourceReferences(
      row?['source_ids'],
      knownSourceIds: knownSourceIds,
    );
    final pilot = row?['pilot'] == null ? null : _parsePilot(row?['pilot']);
    const allowed = {'action', 'reason', 'check', 'source_ids', 'pilot'};
    if (row == null ||
        row.keys.toSet().difference(allowed).isNotEmpty ||
        action == null ||
        reason == null ||
        check == null ||
        sourceIds == null ||
        (row.containsKey('pilot') && row['pilot'] != null && pilot == null)) {
      throw const _InvalidSourceBriefResponse();
    }
    actions.add(
      SourceBriefProposedAction(
        action: action,
        reason: reason,
        check: check,
        sourceIds: sourceIds,
        pilot: pilot,
      ),
    );
  }

  final unknowns = <String>[];
  for (final raw in unknownsValue) {
    final item = _safeText(raw, maxLength: 180);
    if (item == null) throw const _InvalidSourceBriefResponse();
    unknowns.add(item);
  }
  return SourceBriefBusinessAnalysis(
    sourceObservations: observations,
    interpretations: interpretations,
    proposedActions: actions,
    unknowns: unknowns,
  );
}

SourceBriefPilotProposal? _parsePilot(Object? value) {
  final map = _asMap(value);
  if (map == null ||
      map.keys.toSet().difference({
        'audience',
        'procedure',
        'measure',
        'continue_if',
        'stop_if',
      }).isNotEmpty ||
      map.keys.toSet().length != 5) {
    return null;
  }
  final audience = _safeText(map['audience'], maxLength: 180);
  final procedure = _safeText(map['procedure'], maxLength: 180);
  final measure = _safeText(map['measure'], maxLength: 180);
  final continueIf = _safeText(map['continue_if'], maxLength: 180);
  final stopIf = _safeText(map['stop_if'], maxLength: 180);
  if (audience == null ||
      procedure == null ||
      measure == null ||
      continueIf == null ||
      stopIf == null) {
    return null;
  }
  return SourceBriefPilotProposal(
    audience: audience,
    procedure: procedure,
    measure: measure,
    continueIf: continueIf,
    stopIf: stopIf,
  );
}

List<String>? _sourceReferences(
  Object? value, {
  required Set<String> knownSourceIds,
}) {
  if (value is! List || value.isEmpty || value.length > 8) return null;
  final result = <String>[];
  for (final raw in value) {
    final sourceId = _safeIdentifier(raw);
    if (sourceId == null || !knownSourceIds.contains(sourceId)) return null;
    result.add(sourceId);
  }
  return result;
}

SourceBriefBusinessAnalysisState _businessAnalysisState(Object? value) =>
    switch (value) {
      'not_requested' => SourceBriefBusinessAnalysisState.notRequested,
      'draft' => SourceBriefBusinessAnalysisState.draft,
      'unavailable' => SourceBriefBusinessAnalysisState.unavailable,
      'error' => SourceBriefBusinessAnalysisState.error,
      _ => SourceBriefBusinessAnalysisState.unknown,
    };

SourceBriefTaskState _parseTaskState(Object? value) => switch (value) {
  'pending' => SourceBriefTaskState.pending,
  'running' => SourceBriefTaskState.running,
  'succeeded' => SourceBriefTaskState.succeeded,
  'failed' => SourceBriefTaskState.failed,
  'interrupted' => SourceBriefTaskState.interrupted,
  _ => SourceBriefTaskState.unknown,
};

String _safeReviewStatus(Object? value) => switch (value) {
  'HUMAN_PENDING' => 'HUMAN_PENDING',
  'APPROVED' => 'APPROVED',
  'REJECTED' => 'REJECTED',
  _ => 'UNKNOWN',
};

String? _safeSourceUrl(Object? value) {
  final text = _safeText(value, maxLength: 2048);
  if (text == null) return null;
  final uri = Uri.tryParse(text);
  if (uri == null ||
      (uri.scheme != 'http' && uri.scheme != 'https') ||
      uri.host.isEmpty ||
      uri.userInfo.isNotEmpty) {
    return null;
  }
  return text;
}

String? _safeIdentifier(Object? value) {
  final text = _safeText(value, maxLength: 160);
  if (text == null ||
      !RegExp(r'^[A-Za-z0-9][A-Za-z0-9:._/@-]{0,159}$').hasMatch(text)) {
    return null;
  }
  return text;
}

String? _optionalIdentifier(Object? value) {
  if (value == null) return null;
  return _safeIdentifier(value);
}

String? _safeText(Object? value, {required int maxLength}) {
  if (value is! String) return null;
  final text = value.trim();
  if (text.isEmpty ||
      text.length > maxLength ||
      RegExp(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]').hasMatch(text)) {
    return null;
  }
  return text;
}

String? _optionalSafeText(Object? value, {required int maxLength}) =>
    value == null ? null : _safeText(value, maxLength: maxLength);

Map<String, Object?>? _asMap(Object? value) {
  if (value is! Map) return null;
  final result = <String, Object?>{};
  for (final entry in value.entries) {
    if (entry.key is! String) return null;
    result[entry.key as String] = entry.value;
  }
  return result;
}

String? _contextSignature(Object? value) {
  if (value is! Map) return null;
  try {
    return jsonEncode(_canonicalValue(value));
  } on Object {
    return null;
  }
}

Object? _canonicalValue(Object? value) {
  if (value is Map) {
    final entries = value.entries.where((entry) => entry.key is String).toList()
      ..sort(
        (left, right) => (left.key as String).compareTo(right.key as String),
      );
    return {
      for (final entry in entries)
        entry.key as String: _canonicalValue(entry.value),
    };
  }
  if (value is Iterable) {
    return value.map(_canonicalValue).toList(growable: false);
  }
  return value;
}

final class _SourceContextSelection {
  const _SourceContextSelection({
    required this.domainId,
    required this.globalScope,
    required this.subjectId,
    required this.brandFocusId,
    required this.displayNames,
  });
  final String domainId;
  final bool globalScope;
  final String? subjectId;
  final String? brandFocusId;
  final Map<String, String> displayNames;
  String? get scopeLabel =>
      displayNames['zh-CN'] ??
      displayNames['en'] ??
      displayNames['ko'] ??
      (globalScope
          ? (domainId == 'CTH' ? '全球商业' : '全球品牌')
          : subjectId ?? brandFocusId);
  bool sameScope(_SourceContextSelection other) =>
      domainId == other.domainId &&
      globalScope == other.globalScope &&
      subjectId == other.subjectId &&
      brandFocusId == other.brandFocusId;
  bool matches(SourceBriefScope scope) =>
      scope.productId == (domainId == 'CTH' ? 'CTH' : 'ZBMP') &&
      scope.domainId == (domainId == 'CTH' ? 'cth' : 'zbmp') &&
      scope.globalScope == globalScope &&
      scope.subjectId == subjectId &&
      scope.brandFocusId == brandFocusId;
  static _SourceContextSelection? parse(
    Map<String, dynamic> response, {
    required String domainId,
  }) {
    if ((domainId != 'CTH' && domainId != 'BMP') ||
        response['ok'] != true ||
        response['contract'] != 'lumenis.context.v1' ||
        response['selection_only'] != true) {
      return null;
    }
    final context = _asMap(response['context']);
    if (context == null) return null;
    final global = context['mode'] == 'GLOBAL_ALL';
    String? subjectId;
    String? brandFocusId;
    if (global) {
      if (context['domain_id'] != null ||
          context['subject_id'] != null ||
          context['brand_focus_id'] != null) {
        return null;
      }
    } else {
      if (context['mode'] != 'FOCUS' || context['domain_id'] != domainId) {
        return null;
      }
      subjectId = _optionalIdentifier(context['subject_id']);
      brandFocusId = _optionalIdentifier(context['brand_focus_id']);
      if ((domainId == 'CTH' &&
              (subjectId == null || context['brand_focus_id'] != null)) ||
          (domainId == 'BMP' &&
              (brandFocusId == null || context['subject_id'] != null))) {
        return null;
      }
    }
    return _SourceContextSelection(
      domainId: domainId,
      globalScope: global,
      subjectId: subjectId,
      brandFocusId: brandFocusId,
      displayNames: _displayNames(context['display_name']),
    );
  }
}

_SourceContextSelection? _selectionFromEnvelope(
  Object? envelope, {
  required String domainId,
}) {
  final response = _asMap(envelope);
  return response == null
      ? null
      : _SourceContextSelection.parse(response, domainId: domainId);
}

Map<String, String> _displayNames(Object? value) {
  final map = _asMap(value);
  if (map == null) return const {};
  final result = <String, String>{};
  for (final entry in map.entries) {
    final text = _safeText(entry.value, maxLength: 240);
    if (text != null) result[entry.key] = text;
  }
  return Map.unmodifiable(result);
}

final class _FreshSourceContext {
  const _FreshSourceContext({
    required this.selection,
    required this.signature,
    required this.scopeChanged,
  });

  final _SourceContextSelection selection;
  final String signature;
  final bool scopeChanged;
}

final class _ContextChanged implements Exception {
  const _ContextChanged();
}

final class _InvalidSourceBriefResponse implements Exception {
  const _InvalidSourceBriefResponse();
}

final class _SourceBriefSaveFailure implements Exception {
  const _SourceBriefSaveFailure(this.kind);

  final SourceBriefErrorKind kind;
}

final class _ValidatedSavedWork {
  const _ValidatedSavedWork({
    required this.artifactId,
    required this.sha256,
    required this.title,
    required this.markdown,
  });

  final String artifactId;
  final String sha256;
  final String title;
  final String markdown;
}

String _newSourceBriefSaveRequestId() =>
    'sourcebrief_${DateTime.now().toUtc().microsecondsSinceEpoch}_${++SourceBriefViewModel._saveRequestSequence}';

String _newSourceBriefRevisionRequestId() =>
    'sourcebriefrev_${DateTime.now().toUtc().microsecondsSinceEpoch}_${++SourceBriefViewModel._saveRequestSequence}';

String _newSourceBriefSharedAdoptionRequestId() =>
    'sourcebriefshared_${DateTime.now().toUtc().microsecondsSinceEpoch}_${++SourceBriefViewModel._saveRequestSequence}';

SourceBriefSavedWork _validatedHistoricalSavedWork(
  Object? value, {
  required _SourceContextSelection expectedSelection,
  String? expectedArtifactId,
  String? expectedSha256,
  String? expectedWorkId,
  int? expectedVersion,
  String? expectedJobId,
  String? expectedSourceBriefHash,
  String? expectedParentArtifactId,
  String? expectedParentSha256,
  String? expectedTitle,
  String? expectedMarkdown,
  String? expectedRequestId,
}) {
  final envelope = _asMap(value);
  final artifact = _asMap(envelope?['artifact']);
  final document = _asMap(envelope?['document']);
  final returnRef = _asMap(envelope?['return_ref']);
  final payload = _asMap(document?['payload']);
  final reference = _asMap(payload?['source_brief_reference']);
  final artifactId = _safeText(artifact?['artifact_id'], maxLength: 20);
  final sha256 = _safeText(artifact?['sha256'], maxLength: 64);
  final title = _safeText(document?['title'], maxLength: 300);
  final markdown = document?['markdown'];
  final requestId = _safeText(document?['request_id'], maxLength: 128);
  final workId = _safeText(returnRef?['work_id'], maxLength: 80);
  final version = returnRef?['version'];
  final jobId = _safeText(reference?['job_id'], maxLength: 120);
  final sourceBriefHash = _safeText(reference?['artifact_hash'], maxLength: 64);
  final actorId = _safeText(reference?['actor_id'], maxLength: 256);
  final scope = _asMap(returnRef?['scope']);
  final sourceScope = _asMap(reference?['scope']);
  final parentArtifactId = _optionalSafeText(
    document?['parent_artifact_id'],
    maxLength: 20,
  );
  final parentSha256 = _optionalSafeText(
    document?['parent_sha256'],
    maxLength: 64,
  );
  final domain = expectedSelection.domainId == 'CTH' ? 'cth' : 'zbmp';
  bool matchesScope(Map<String, Object?>? candidate) =>
      candidate != null &&
      candidate.keys.toSet().difference({
        'domain_id',
        'subject_id',
        'brand_focus_id',
        'global_scope',
      }).isEmpty &&
      candidate['domain_id'] == domain &&
      candidate['subject_id'] == expectedSelection.subjectId &&
      candidate['brand_focus_id'] == expectedSelection.brandFocusId &&
      candidate['global_scope'] == expectedSelection.globalScope;

  if (artifactId == null ||
      !RegExp(r'^ART-[0-9a-f]{16}$').hasMatch(artifactId) ||
      sha256 == null ||
      !RegExp(r'^[0-9a-f]{64}$').hasMatch(sha256) ||
      workId == null ||
      !workId.startsWith('WORK-') ||
      version is! int ||
      version < 1 ||
      title == null ||
      title.isEmpty ||
      markdown is! String ||
      markdown.trim().isEmpty ||
      requestId == null ||
      !RegExp(r'^[A-Za-z0-9_-]{8,128}$').hasMatch(requestId) ||
      document?['kind'] != 'research' ||
      reference == null ||
      reference.keys.toSet().difference({
        'job_id',
        'actor_id',
        'scope',
        'artifact_hash',
      }).isNotEmpty ||
      actorId == null ||
      jobId == null ||
      sourceBriefHash == null ||
      !RegExp(r'^[0-9a-f]{64}$').hasMatch(sourceBriefHash) ||
      returnRef?['artifact_id'] != artifactId ||
      returnRef?['version'] != document?['version'] ||
      !matchesScope(scope) ||
      !matchesScope(sourceScope) ||
      (version == 1 && (parentArtifactId != null || parentSha256 != null)) ||
      (version > 1 &&
          (parentArtifactId == null ||
              !RegExp(r'^ART-[0-9a-f]{16}$').hasMatch(parentArtifactId) ||
              parentSha256 == null ||
              !RegExp(r'^[0-9a-f]{64}$').hasMatch(parentSha256))) ||
      (expectedArtifactId != null && artifactId != expectedArtifactId) ||
      (expectedSha256 != null && sha256 != expectedSha256) ||
      (expectedWorkId != null && workId != expectedWorkId) ||
      (expectedVersion != null && version != expectedVersion) ||
      (expectedJobId != null && jobId != expectedJobId) ||
      (expectedSourceBriefHash != null &&
          sourceBriefHash != expectedSourceBriefHash) ||
      (expectedParentArtifactId != null &&
          parentArtifactId != expectedParentArtifactId) ||
      (expectedParentSha256 != null && parentSha256 != expectedParentSha256) ||
      (expectedTitle != null && title != expectedTitle) ||
      (expectedMarkdown != null && markdown != expectedMarkdown) ||
      (expectedRequestId != null && requestId != expectedRequestId)) {
    throw const _InvalidSourceBriefResponse();
  }
  return SourceBriefSavedWork(
    artifactId: artifactId,
    sha256: sha256,
    workId: workId,
    version: version,
    title: title,
    markdown: markdown,
    requestId: requestId,
    sourceBriefJobId: jobId,
    sourceBriefHash: sourceBriefHash,
    parentArtifactId: parentArtifactId,
    parentSha256: parentSha256,
  );
}

_ValidatedSavedWork _validatedSavedWork(
  Object? value, {
  required SourceBriefResult expectedResult,
  required String expectedTitle,
  required String expectedRequestId,
  String? expectedArtifactId,
  String? expectedSha256,
  String? expectedMarkdown,
}) {
  final envelope = _asMap(value);
  final artifact = _asMap(envelope?['artifact']);
  final document = _asMap(envelope?['document']);
  final returnRef = _asMap(envelope?['return_ref']);
  final artifactId = _safeText(artifact?['artifact_id'], maxLength: 20);
  final sha256 = _safeText(artifact?['sha256'], maxLength: 64);
  final title = _safeText(document?['title'], maxLength: 300);
  final markdown = document?['markdown'];
  final payload = _asMap(document?['payload']);
  final sourceReference = _asMap(payload?['source_brief_reference']);
  final sourceScope = _asMap(sourceReference?['scope']);
  final returnScope = _asMap(returnRef?['scope']);
  final workId = _safeText(returnRef?['work_id'], maxLength: 80);
  final actorRef = _safeText(sourceReference?['actor_id'], maxLength: 256);
  final returnScopeMatches =
      returnScope != null &&
      returnScope.keys.toSet().difference({
        'domain_id',
        'subject_id',
        'brand_focus_id',
        'global_scope',
      }).isEmpty &&
      returnScope['domain_id'] == expectedResult.scope.domainId &&
      returnScope['subject_id'] == expectedResult.scope.subjectId &&
      returnScope['brand_focus_id'] == expectedResult.scope.brandFocusId &&
      returnScope['global_scope'] == expectedResult.scope.globalScope;
  final sourceScopeMatches =
      sourceScope != null &&
      sourceScope['domain_id'] == expectedResult.scope.domainId &&
      sourceScope['subject_id'] == expectedResult.scope.subjectId &&
      sourceScope['brand_focus_id'] == expectedResult.scope.brandFocusId &&
      sourceScope['global_scope'] == expectedResult.scope.globalScope;
  if (artifactId == null ||
      !RegExp(r'^ART-[0-9a-f]{16}$').hasMatch(artifactId) ||
      sha256 == null ||
      !RegExp(r'^[0-9a-f]{64}$').hasMatch(sha256) ||
      (expectedArtifactId != null && artifactId != expectedArtifactId) ||
      (expectedSha256 != null && sha256 != expectedSha256) ||
      title != expectedTitle ||
      document?['kind'] != 'research' ||
      document?['request_id'] != expectedRequestId ||
      markdown is! String ||
      markdown.trim().isEmpty ||
      (expectedMarkdown != null && markdown != expectedMarkdown) ||
      sourceReference?['job_id'] != expectedResult.jobId ||
      sourceReference?['artifact_hash'] != expectedResult.artifactHash ||
      actorRef == null ||
      !sourceScopeMatches ||
      returnRef?['artifact_id'] != artifactId ||
      workId == null ||
      returnRef?['version'] != 1 ||
      !returnScopeMatches) {
    throw const _InvalidSourceBriefResponse();
  }
  return _ValidatedSavedWork(
    artifactId: artifactId,
    sha256: sha256,
    title: title!,
    markdown: markdown,
  );
}
