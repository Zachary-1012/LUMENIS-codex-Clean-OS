import 'dart:convert';

import 'package:flutter/foundation.dart';

import '../../../core/lumenis_core_client.dart';
import 'source_brief_view_model.dart';

Map<String, dynamic> _businessMap(Object? value) =>
    value is Map ? Map<String, dynamic>.from(value) : <String, dynamic>{};

List<Map<String, dynamic>> _businessRows(Object? value) => value is List
    ? value
          .whereType<Map>()
          .map((row) => Map<String, dynamic>.from(row))
          .toList()
    : <Map<String, dynamic>>[];

String? _businessText(Object? value) =>
    value is String && value.trim().isNotEmpty ? value.trim() : null;

/// Frozen inputs for the existing prepare/confirm SavedWork write.
final class BusinessWorkSavePreview {
  BusinessWorkSavePreview({
    required this.workId,
    required this.revision,
    required this.requestId,
    required this.resource,
    required List<Map<String, dynamic>> citations,
    required this.question,
    this.previousArtifactId,
    this.expectedDraftDigest,
  }) : citations = List.unmodifiable(
         citations.map((item) => Map<String, dynamic>.unmodifiable(item)),
       );

  final String workId;
  final String revision;
  final String requestId;
  final String resource;
  final List<Map<String, dynamic>> citations;
  final String question;
  final String? previousArtifactId;
  final String? expectedDraftDigest;
}

/// Durable business-work operations formerly embedded in the CTH10 panel.
/// Presentation collects explicit answers; this owner validates lineage,
/// preserves request identity, and talks to the existing Core/API owner.
class BusinessWorkController extends ChangeNotifier {
  BusinessWorkController({
    required this.client,
    required this.domainId,
    SourceBriefResult? source,
  }) : _contextSignature = _signature(client.currentContextEnvelope),
       _source = source,
       _question = source?.businessQuestion ?? '' {
    if (domainId != 'CTH' && domainId != 'BMP') {
      throw const FormatException('Explicit business domain required.');
    }
    if (source != null &&
        (source.scope.domainId != domainId || source.scope.globalScope)) {
      throw const FormatException(
        'Business work requires a scoped source brief.',
      );
    }
  }

  final LumenisCoreClient client;
  final String domainId;
  final String _contextSignature;
  final Map<String, String> _operationIds = {};
  SourceBriefResult? _source;
  String _question;
  Map<String, dynamic>? _work;
  List<Map<String, dynamic>> _recent = [];
  Map<String, dynamic>? _saved;
  BusinessWorkSavePreview? _pendingSave;
  bool _busy = false;
  bool _disposed = false;
  String? _errorCode;

  bool get busy => _busy;
  String? get errorCode => _errorCode;
  String get question => _question;
  Map<String, dynamic>? get work =>
      _work == null ? null : Map<String, dynamic>.unmodifiable(_work!);
  List<Map<String, dynamic>> get recent => List.unmodifiable(_recent);
  Map<String, dynamic>? get saved =>
      _saved == null ? null : Map<String, dynamic>.unmodifiable(_saved!);
  BusinessWorkSavePreview? get pendingSave => _pendingSave;
  bool get contextCurrent => _sameScope;
  bool get canEdit =>
      !_busy && _sameScope && _work?['is_current_revision'] == true;
  String get state => _work?['state'] as String? ?? '';
  List<Map<String, dynamic>> get citations => List.unmodifiable(
    _businessRows(_businessMap(_work?['citation_candidates'])['items']),
  );

  bool get _sameScope =>
      _contextSignature == _signature(client.currentContextEnvelope);

  void setQuestion(String value) {
    if (_disposed || _busy) return;
    _question = value;
    notifyListeners();
  }

  void updateSource(SourceBriefResult? source) {
    if (_disposed || _busy) return;
    if (source != null &&
        (source.scope.domainId != domainId || source.scope.globalScope)) {
      throw const FormatException(
        'Business work requires a scoped source brief.',
      );
    }
    _source = source;
    if (_work == null && source != null) {
      _question = source.businessQuestion ?? '';
    }
    notifyListeners();
  }

  Future<void> loadRecent() async {
    await _run(() async {
      final value = _payload(await client.listBusinessWork(domainId));
      _requireScope();
      _recent = _businessRows(value['items']);
    });
  }

  Future<void> open(String workId, {String? revision}) async {
    final id = _businessText(workId);
    if (id == null) {
      _errorCode = 'invalidResponse';
      notifyListeners();
      return;
    }
    await _run(() async {
      final value = _payload(
        await client.readBusinessWork(
          domainId: domainId,
          workId: id,
          revision: revision,
        ),
      );
      _requireScope();
      _work = value;
      _question = value['question'] as String? ?? '';
      _saved = null;
      _pendingSave = null;
    });
  }

  Future<void> prepare() async {
    final source = _source;
    final question = _question.trim();
    if (source == null || source.scope.globalScope || question.isEmpty) {
      _errorCode = 'sourceUnavailable';
      notifyListeners();
      return;
    }
    await _run(() async {
      final key = jsonEncode(['prepare', source.jobId, question]);
      final value = _payload(
        await client.prepareBusinessWork(
          domainId: domainId,
          jobId: source.jobId,
          question: question,
          submissionId: _id(key),
        ),
      );
      _requireScope();
      _work = value;
      _saved = null;
      _pendingSave = null;
    });
  }

  Future<void> advance(String operation, Map<String, dynamic> payload) async {
    if (!canEdit || _work == null) {
      _errorCode = _sameScope ? 'conflict' : 'contextChanged';
      notifyListeners();
      return;
    }
    await _run(() => _advance(operation, payload));
  }

  Future<void> chooseOption({
    required String optionId,
    required String reason,
    required String owner,
    required String reviewAt,
  }) async {
    if (!_validZonedDate(reviewAt)) {
      _errorCode = 'dateInvalid';
      notifyListeners();
      return;
    }
    await advance('choose', {
      'option_id': optionId,
      'reason': reason,
      'owner': owner,
      'review_at': reviewAt,
    });
  }

  Future<void> reviseOption({
    required String optionId,
    required String proposal,
    required String rationale,
    required String check,
    required String reason,
  }) async {
    final work = _work;
    if (!canEdit || work == null) return;
    final options = _businessRows(work['options'])
        .map(
          (item) => <String, dynamic>{
            for (final key in const [
              'option_id',
              'proposal',
              'rationale',
              'source_ids',
              'assumptions',
              'unknowns',
              'check',
            ])
              key: item[key],
            if (item['option_id'] == optionId) ...{
              'proposal': proposal,
              'rationale': rationale,
              'check': check,
            },
          },
        )
        .toList();
    if (!options.any((item) => item['option_id'] == optionId)) {
      _errorCode = 'conflict';
      notifyListeners();
      return;
    }
    await advance('adopt', {
      'reason': reason,
      'question': work['question'],
      'source_job_id': _businessMap(work['source_report'])['job_id'],
      'options': options,
      'decision': _decisionInput(_businessMap(work['decision'])),
    });
  }

  Future<void> editDecision({
    required String reason,
    required String owner,
    required String reviewAt,
    required String revisionReason,
  }) async {
    if (!_validZonedDate(reviewAt)) {
      _errorCode = 'dateInvalid';
      notifyListeners();
      return;
    }
    final work = _work;
    if (!canEdit ||
        work == null ||
        const {'CANCELLED', 'INTERRUPTED'}.contains(state)) {
      return;
    }
    final decision = _decisionInput(_businessMap(work['decision']));
    if (decision['option_id'] == null) return;
    await advance('adopt', {
      'source_job_id': _businessMap(work['source_report'])['job_id'],
      'question': work['question'],
      'options': _optionInputs(work),
      'decision': {
        ...decision,
        'reason': reason,
        'owner': owner,
        'review_at': reviewAt,
      },
      'reason': revisionReason,
    });
  }

  Future<bool> updateDomainPlan(Map<String, dynamic> plan) async {
    final work = _work;
    if (!canEdit || work == null) return false;
    final initialRevision = work['revision'];
    final analysis = _businessMap(work['domain_analysis']);
    final planning = _businessMap(
      _businessMap(analysis['question_result'])['planning_constraints'],
    );
    await advance('adopt', {
      'reason': 'Update domain plan',
      'question': work['question'],
      'source_job_id': _businessMap(work['source_report'])['job_id'],
      'options': _optionInputs(work),
      if (_businessMap(work['decision']).isNotEmpty)
        'decision': _decisionInput(_businessMap(work['decision'])),
      'planning_constraints': {...planning, 'domain_plan': plan},
    });
    return _errorCode == null && _work?['revision'] != initialRevision;
  }

  Future<String?> readVerifiedSourceExcerpt(Map<String, dynamic> source) async {
    return _run<String>(() async {
      final verified = await _verifiedSource(source);
      final quote = _businessMap(verified['citation'])['quote'];
      if (quote is! String || quote.isEmpty) {
        throw const FormatException('Source excerpt unavailable.');
      }
      return quote;
    });
  }

  Future<void> reanalyze(String reason) async {
    final work = _work;
    if (!canEdit || work == null) return;
    await advance('adopt', {
      'source_job_id': _businessMap(work['source_report'])['job_id'],
      'question': work['question'],
      'options': null,
      'decision': null,
      'reason': reason,
    });
  }

  Future<List<Map<String, dynamic>>> loadCitationSources({
    String? cursor,
  }) async {
    final local = citations;
    final page = await _run<List<Map<String, dynamic>>>(() async {
      final value = _payload(
        await client.businessWorkSources(domainId, cursor: cursor),
      );
      _requireScope();
      final candidates = <Map<String, dynamic>>[];
      for (final report in _businessRows(value['items'])) {
        candidates.addAll(
          _businessRows(_businessMap(report['citation_candidates'])['items']),
        );
      }
      final merged = [...local];
      for (final item in candidates) {
        if (!_containsSource(merged, item)) merged.add(item);
      }
      return merged;
    });
    return page ?? local;
  }

  Future<void> recordManualAction({
    required Map<String, dynamic> source,
    required String performer,
    required String exactTarget,
    required String performedAt,
    required String limits,
    String? plannedActionId,
  }) async {
    if (!_validZonedDate(performedAt)) {
      _errorCode = 'dateInvalid';
      notifyListeners();
      return;
    }
    final work = _work;
    if (!canEdit || work == null) return;
    await _run(() async {
      final verified = await _verifiedSource(source);
      await _advance('manual_action', {
        'source_job_id': verified['source_job_id'],
        'source_id': verified['source_id'],
        'quote': _businessMap(verified['citation'])['quote'],
        'limits': limits,
        'plan_action_id': ?plannedActionId,
        'option_id': _businessMap(work['decision'])['option_id'],
        'performer': performer,
        'exact_target': exactTarget,
        'performed_at': performedAt,
      });
    });
  }

  Future<void> recordObservation({
    required Map<String, dynamic> source,
    required String start,
    required String end,
    required String observedAt,
    required String name,
    required String definition,
    required String? value,
    required String? unit,
    required String? numerator,
    required String? denominator,
    required String limits,
  }) async {
    if (!_validZonedDate(start) ||
        !_validZonedDate(end) ||
        !_validZonedDate(observedAt) ||
        DateTime.parse(end).isBefore(DateTime.parse(start))) {
      _errorCode = 'dateInvalid';
      notifyListeners();
      return;
    }
    await _run(() async {
      final verified = await _verifiedSource(source);
      await _advance('observation', {
        'source_job_id': verified['source_job_id'],
        'source_id': verified['source_id'],
        'quote': _businessMap(verified['citation'])['quote'],
        'limits': limits,
        'observed_at': observedAt,
        'window': {'start': start, 'end': end},
        'metrics': [
          {
            'name': _blankToNull(name),
            'definition': _blankToNull(definition),
            'value': _blankToNull(value),
            'unit': _blankToNull(unit),
            'numerator': _blankToNull(numerator),
            'denominator': _blankToNull(denominator),
          },
        ],
        'costs': <Object>[],
      });
    });
  }

  Future<void> recordCost({
    required String kind,
    required Map<String, dynamic> source,
    required String? amount,
    required String currency,
    required String start,
    required String end,
    required String observedAt,
    required String occurredAt,
    required String limits,
    String? relatedEntryId,
    String? planActionId,
    Map<String, dynamic>? correction,
  }) async {
    if (!const {'ESTIMATE', 'COMMITTED', 'ACTUAL', 'REFUND'}.contains(kind) ||
        !_validZonedDate(start) ||
        !_validZonedDate(end) ||
        !_validZonedDate(observedAt) ||
        !_validZonedDate(occurredAt) ||
        DateTime.parse(end).isBefore(DateTime.parse(start))) {
      _errorCode = 'invalidInput';
      notifyListeners();
      return;
    }
    final work = _work;
    if (!canEdit || work == null) return;
    final ledger = _businessRows(
      _businessMap(work['observation'])['cost_ledger'],
    );
    if (kind == 'REFUND') {
      Map<String, dynamic>? parent;
      for (final row in ledger) {
        if (row['entry_id'] == relatedEntryId) {
          parent = row;
          break;
        }
      }
      if (parent == null || parent['kind'] != 'ACTUAL') {
        _errorCode = 'invalidInput';
        notifyListeners();
        return;
      }
    }
    await _run(() async {
      final verified = await _verifiedSource(source);
      final correctionId = _businessText(correction?['entry_id']);
      final key = jsonEncode([
        'cost',
        work['revision'],
        kind,
        amount,
        currency,
        start,
        end,
        observedAt,
        occurredAt,
        relatedEntryId,
        planActionId,
        correctionId,
        verified['source_id'],
      ]);
      final costs = <Map<String, dynamic>>[
        {
          'entry_id': _id(key),
          'kind': kind,
          'amount': _blankToNull(amount),
          'currency': currency.trim().toUpperCase(),
          'related_entry_id': relatedEntryId,
          'occurred_at': occurredAt,
          if (planActionId != null && kind != 'REFUND' && correctionId == null)
            'plan_action_id': planActionId,
          if (correctionId != null) ...{
            'supersedes_entry_id': correctionId,
            'correction_reason': correction?['correction_reason'],
          },
        },
      ];
      await _advance('observation', {
        'source_job_id': verified['source_job_id'],
        'source_id': verified['source_id'],
        'quote': _businessMap(verified['citation'])['quote'],
        'limits': limits,
        'observed_at': observedAt,
        'window': {'start': start, 'end': end},
        'metrics': <Object>[],
        'costs': costs,
      });
    });
  }

  Future<BusinessWorkSavePreview?> prepareSave() async {
    final work = _work;
    if (!canEdit || work == null) return null;
    final latest = _businessMap(_businessMap(work['saved_results'])['latest']);
    if (latest['business_revision'] == work['revision']) {
      await verifyLatestSavedResult();
      return null;
    }
    final candidates = citations;
    if (candidates.isEmpty ||
        _businessMap(work['citation_candidates'])['save_limit_state'] ==
            'SHARED_CITATION_LIMIT_EXCEEDED') {
      _errorCode = 'sourceUnavailable';
      notifyListeners();
      return null;
    }
    final citationValues = candidates
        .map((item) => _businessMap(item['citation']))
        .toList(growable: false);
    final requestId = _id(
      jsonEncode(['save', work['work_id'], work['revision'], citationValues]),
    );
    final savedResults = _businessMap(work['saved_results']);
    if (savedResults['next_parent_state'] == 'UNAVAILABLE') {
      _errorCode = 'parentUnavailable';
      notifyListeners();
      return null;
    }
    final previous = savedResults['latest'] is Map ? latest : null;
    final preview = await _run<BusinessWorkSavePreview>(() async {
      final prepared = _payload(
        await client.saveBusinessWork(
          domainId: domainId,
          workId: work['work_id'] as String,
          revision: work['revision'] as String,
          requestId: requestId,
          citations: citationValues,
          previousArtifactId: previous?['artifact_id'] as String?,
          expectedDraftDigest: previous?['draft_digest'] as String?,
        ),
      );
      _requireScope();
      final resource = _businessText(prepared['resource']);
      if (resource == null ||
          _work?['work_id'] != work['work_id'] ||
          _work?['revision'] != work['revision']) {
        throw const FormatException('Business save preparation unavailable.');
      }
      final result = BusinessWorkSavePreview(
        workId: work['work_id'] as String,
        revision: work['revision'] as String,
        requestId: requestId,
        resource: resource,
        citations: citationValues,
        question: work['question'] as String? ?? '',
        previousArtifactId: previous?['artifact_id'] as String?,
        expectedDraftDigest: previous?['draft_digest'] as String?,
      );
      _pendingSave = result;
      return result;
    });
    return preview;
  }

  Future<void> confirmSave(BusinessWorkSavePreview preview) async {
    final work = _work;
    if (!identical(preview, _pendingSave) ||
        !canEdit ||
        work == null ||
        work['work_id'] != preview.workId ||
        work['revision'] != preview.revision) {
      _errorCode = _sameScope ? 'conflict' : 'contextChanged';
      notifyListeners();
      return;
    }
    await _run(() async {
      final savedResponse = _payload(
        await client.saveBusinessWork(
          domainId: domainId,
          workId: preview.workId,
          revision: preview.revision,
          requestId: preview.requestId,
          citations: preview.citations,
          confirmedResource: preview.resource,
          previousArtifactId: preview.previousArtifactId,
          expectedDraftDigest: preview.expectedDraftDigest,
        ),
      );
      _requireScope();
      final receipt = _businessMap(savedResponse['saved_work']);
      final refreshed = _payload(
        await client.readBusinessWork(
          domainId: domainId,
          workId: preview.workId,
        ),
      );
      _requireScope();
      final latest = _businessMap(
        _businessMap(refreshed['saved_results'])['latest'],
      );
      if (refreshed['work_id'] != preview.workId ||
          refreshed['revision'] != preview.revision ||
          latest['business_revision'] != preview.revision ||
          (receipt['artifact_id'] != null &&
              receipt['artifact_id'] != latest['artifact_id']) ||
          (receipt['sha256'] != null &&
              receipt['sha256'] != latest['sha256'])) {
        _work = refreshed;
        throw const LumenisCoreException(
          'Business result changed before save confirmation.',
          statusCode: 409,
        );
      }
      final verified = _payload(
        await client.reopenSourceBriefSavedWork(
          domainId: domainId,
          artifactId: latest['artifact_id'] as String,
        ),
      );
      _requireScope();
      _verifySavedBusinessVersion(
        verified,
        workId: preview.workId,
        revision: preview.revision,
        artifactId: latest['artifact_id'] as String,
        sha256: latest['sha256'] as String,
        digest: latest['draft_digest'] as String,
        version: latest['version'] as int?,
      );
      _saved = verified;
      _work = refreshed;
      _pendingSave = null;
    });
  }

  Future<Map<String, dynamic>?> verifyLatestSavedResult() async {
    final work = _work;
    if (!_sameScope || work == null) return null;
    final latest = _businessMap(_businessMap(work['saved_results'])['latest']);
    if (latest.isEmpty || latest['business_revision'] != work['revision']) {
      _errorCode = 'notFound';
      notifyListeners();
      return null;
    }
    return _run<Map<String, dynamic>>(() async {
      final refreshed = _payload(
        await client.readBusinessWork(
          domainId: domainId,
          workId: work['work_id'] as String,
        ),
      );
      _requireScope();
      final actual = _businessMap(
        _businessMap(refreshed['saved_results'])['latest'],
      );
      if (refreshed['work_id'] != work['work_id'] ||
          refreshed['revision'] != work['revision'] ||
          actual['business_revision'] != work['revision'] ||
          const [
            'artifact_id',
            'sha256',
            'draft_digest',
          ].any((key) => actual[key] != latest[key])) {
        _work = refreshed;
        throw const LumenisCoreException(
          'Saved result changed.',
          statusCode: 409,
        );
      }
      final verified = _payload(
        await client.reopenSourceBriefSavedWork(
          domainId: domainId,
          artifactId: latest['artifact_id'] as String,
        ),
      );
      _requireScope();
      _verifySavedBusinessVersion(
        verified,
        workId: work['work_id'] as String,
        revision: work['revision'] as String,
        artifactId: latest['artifact_id'] as String,
        sha256: latest['sha256'] as String,
        digest: latest['draft_digest'] as String,
        version: latest['version'] as int?,
      );
      _work = refreshed;
      _saved = verified;
      return verified;
    });
  }

  Future<Map<String, dynamic>?> readInternalResult(
    Map<String, dynamic> expectedReceipt,
  ) async {
    final work = _work;
    if (work == null || !_sameScope) return null;
    return _run<Map<String, dynamic>>(() async {
      final refreshed = _payload(
        await client.readBusinessWork(
          domainId: domainId,
          workId: work['work_id'] as String,
          revision: work['revision'] as String,
        ),
      );
      _requireScope();
      final receipt = _businessMap(
        _businessMap(refreshed['action'])['receipt'],
      );
      const identity = [
        'artifact_id',
        'sha256',
        'work_id',
        'task_id',
        'version',
        'parent_artifact_id',
        'parent_sha256',
      ];
      if (refreshed['work_id'] != work['work_id'] ||
          refreshed['revision'] != work['revision'] ||
          !_internalReceiptReady(receipt) ||
          identity.any((key) => receipt[key] != expectedReceipt[key])) {
        _work = refreshed;
        throw const LumenisCoreException(
          'Created result changed.',
          statusCode: 409,
        );
      }
      final reopened = _payload(
        await client.reopenSourceBriefSavedWork(
          domainId: domainId,
          artifactId: receipt['artifact_id'] as String,
        ),
      );
      _requireScope();
      final artifact = _businessMap(reopened['artifact']);
      final document = _businessMap(reopened['document']);
      final attachments = _businessRows(document['attachments']);
      final output = _businessMap(receipt['output']);
      if (artifact['artifact_id'] != receipt['artifact_id'] ||
          artifact['sha256'] != receipt['sha256'] ||
          document['work_id'] != receipt['work_id'] ||
          document['task_id'] != receipt['task_id'] ||
          document['version'] != receipt['version'] ||
          document['parent_artifact_id'] != receipt['parent_artifact_id'] ||
          document['parent_sha256'] != receipt['parent_sha256'] ||
          attachments.length != 1 ||
          const [
            'artifact_id',
            'sha256',
            'name',
            'media_type',
            'size_bytes',
          ].any(
            (key) =>
                output[key] == null || attachments.single[key] != output[key],
          ) ||
          document['markdown'] is! String ||
          (document['markdown'] as String).trim().isEmpty) {
        throw const FormatException('Created material identity changed.');
      }
      _work = refreshed;
      return document;
    });
  }

  Future<Map<String, dynamic>?> reopenSavedVersion(
    Map<String, dynamic> row,
  ) async {
    final work = _work;
    if (work == null || !_sameScope) return null;
    return _run<Map<String, dynamic>>(() => _readSavedVersion(work, row));
  }

  Future<SavedWorkExportFile?> exportSavedVersion({
    required Map<String, dynamic> row,
    required String format,
    required String purpose,
  }) async {
    final work = _work;
    if (work == null || !_sameScope) return null;
    if (!const {'docx', 'pdf', 'md', 'txt', 'xlsx', 'pptx'}.contains(format) ||
        !const {'delivery', 'audit_snapshot'}.contains(purpose)) {
      _errorCode = 'invalidInput';
      notifyListeners();
      return null;
    }
    return _run<SavedWorkExportFile>(() async {
      await _readSavedVersion(work, row);
      final file = await client.exportSourceBriefSavedWork(
        domainId: domainId,
        artifactId: row['artifact_id'] as String,
        format: format,
        purpose: purpose,
      );
      _requireScope();
      if (file.bytes.isEmpty) throw const FormatException('Empty export.');
      return file;
    });
  }

  Future<void> clear() async {
    _work = null;
    _recent = [];
    _saved = null;
    _pendingSave = null;
    _errorCode = null;
    notifyListeners();
  }

  Future<void> _advance(String operation, Map<String, dynamic> payload) async {
    final work = _work;
    if (work == null || !_sameScope || work['is_current_revision'] != true) {
      throw const LumenisCoreException(
        'Business revision changed.',
        statusCode: 409,
      );
    }
    final key = jsonEncode([
      work['work_id'],
      work['revision'],
      operation,
      payload,
    ]);
    final value = _payload(
      await client.advanceBusinessWork(
        domainId: domainId,
        workId: work['work_id'] as String,
        operation: operation,
        revision: work['revision'] as String,
        submissionId: _id(key),
        payload: payload,
      ),
    );
    _requireScope();
    if (value['work_id'] != work['work_id']) {
      throw const FormatException('Business work identity changed.');
    }
    _work = value;
    if (value['revision'] != work['revision']) {
      _saved = null;
      _pendingSave = null;
    }
  }

  Future<Map<String, dynamic>> _verifiedSource(
    Map<String, dynamic> source,
  ) async {
    final work = _work;
    if (work == null || !_sameScope) {
      throw const LumenisCoreException(
        'Business context changed.',
        statusCode: 409,
      );
    }
    final refreshed = _payload(
      await client.readBusinessWork(
        domainId: domainId,
        workId: work['work_id'] as String,
        revision: work['revision'] as String,
      ),
    );
    _requireScope();
    final matches = <Map<String, dynamic>>[
      ..._businessRows(
        _businessMap(refreshed['citation_candidates'])['items'],
      ).where((item) => _sameSource(item, source)),
    ];
    String? cursor;
    for (var pageCount = 0; matches.isEmpty && pageCount < 200; pageCount++) {
      final page = _payload(
        await client.businessWorkSources(domainId, cursor: cursor),
      );
      _requireScope();
      for (final report in _businessRows(page['items'])) {
        matches.addAll(
          _businessRows(
            _businessMap(report['citation_candidates'])['items'],
          ).where((item) => _sameSource(item, source)),
        );
      }
      final hasMore = page['has_more'] == true;
      final nextCursor = _businessText(page['next_cursor']);
      if (!hasMore || nextCursor == null || nextCursor == cursor) break;
      cursor = nextCursor;
    }
    if (refreshed['work_id'] != work['work_id'] ||
        refreshed['revision'] != work['revision'] ||
        matches.length != 1) {
      _work = refreshed;
      throw const FormatException('Source citation unavailable.');
    }
    final current = matches.single;
    final expected = _businessMap(source['citation']);
    final citation = _businessMap(current['citation']);
    if (citation['quote'] is! String ||
        const [
          'evidence_id',
          'start',
          'end',
          'quote',
        ].any((key) => citation[key] != expected[key])) {
      _work = refreshed;
      throw const FormatException('Source citation changed.');
    }
    _work = refreshed;
    return current;
  }

  Future<Map<String, dynamic>> _readSavedVersion(
    Map<String, dynamic> work,
    Map<String, dynamic> row,
  ) async {
    if (!_savedVersionContextCurrent(work)) {
      throw const LumenisCoreException(
        'Business context changed.',
        statusCode: 409,
      );
    }
    final value = _payload(
      await client.reopenSourceBriefSavedWork(
        domainId: domainId,
        artifactId: row['artifact_id'] as String,
      ),
    );
    _requireScope();
    if (!_savedVersionContextCurrent(work)) {
      throw const LumenisCoreException(
        'Business context changed.',
        statusCode: 409,
      );
    }
    final artifact = _businessMap(value['artifact']);
    final document = _businessMap(value['document']);
    final business = _businessMap(
      _businessMap(document['payload'])['business_work'],
    );
    if (artifact['artifact_id'] != row['artifact_id'] ||
        artifact['sha256'] != row['sha256'] ||
        document['version'] != row['version'] ||
        document['draft_digest'] != row['draft_digest'] ||
        business['work_id'] != work['work_id'] ||
        business['revision'] != row['business_revision']) {
      throw const FormatException('Saved business version changed.');
    }
    return value;
  }

  void _verifySavedBusinessVersion(
    Map<String, dynamic> value, {
    required String workId,
    required String revision,
    required String artifactId,
    required String sha256,
    required String digest,
    required int? version,
  }) {
    final artifact = _businessMap(value['artifact']);
    final document = _businessMap(value['document']);
    final business = _businessMap(
      _businessMap(document['payload'])['business_work'],
    );
    if (artifact['artifact_id'] != artifactId ||
        artifact['sha256'] != sha256 ||
        document['draft_digest'] != digest ||
        (version != null && document['version'] != version) ||
        business['work_id'] != workId ||
        business['revision'] != revision) {
      throw const FormatException('Saved business version changed.');
    }
  }

  bool _savedVersionContextCurrent(Map<String, dynamic> work) =>
      _sameScope &&
      _work?['work_id'] == work['work_id'] &&
      _work?['revision'] == work['revision'];

  Map<String, dynamic> _decisionInput(Map<String, dynamic> value) => {
    for (final key in const ['option_id', 'reason', 'owner', 'review_at'])
      key: value[key],
    if (value['resource_constraints'] is Map)
      'resource_constraints': {
        for (final key in const [
          'budget_amount',
          'estimated_cost_amount',
          'currency',
          'as_of',
          'limits',
        ])
          key: _businessMap(value['resource_constraints'])[key],
      },
  };

  List<Map<String, dynamic>> _optionInputs(Map<String, dynamic> work) => [
    for (final option in _businessRows(work['options']))
      {
        for (final key in const [
          'option_id',
          'proposal',
          'rationale',
          'source_ids',
          'assumptions',
          'unknowns',
          'check',
        ])
          key: option[key],
      },
  ];

  bool _internalReceiptReady(Map<String, dynamic> receipt) =>
      receipt['owner'] == 'Shared ContentCreation/TaskEngine/SavedWork' &&
      const {
        'INTERNAL_TEXT_CREATION',
        'INTERNAL_TEXT_REVISION',
      }.contains(receipt['action_kind']) &&
      receipt['execution_state'] == 'ARTIFACT_COMMITTED' &&
      receipt['external_effect'] == 'NOT_PERFORMED' &&
      receipt['business_outcome'] == 'NOT_OBSERVED' &&
      _businessText(receipt['artifact_id']) != null &&
      _businessText(receipt['task_id']) != null &&
      _businessText(receipt['work_id']) != null &&
      receipt['version'] is int &&
      (receipt['version'] as int) > 0 &&
      receipt['sha256'] is String &&
      RegExp(r'^[0-9a-f]{64}$').hasMatch(receipt['sha256'] as String);

  Future<T?> _run<T>(Future<T> Function() action) async {
    if (_disposed || _busy) return null;
    if (!_sameScope) {
      _clearRestrictedState();
      _errorCode = 'contextChanged';
      notifyListeners();
      return null;
    }
    _busy = true;
    _errorCode = null;
    notifyListeners();
    try {
      final value = await action();
      if (!_sameScope) {
        _clearRestrictedState();
        _errorCode = 'contextChanged';
        return null;
      }
      return value;
    } catch (error) {
      if (error is LumenisCoreException &&
          (error.statusCode == 401 || error.statusCode == 403)) {
        _clearRestrictedState();
        _errorCode = 'accessChanged';
      } else if (error is LumenisCoreException && error.statusCode == 409) {
        _errorCode = 'conflict';
      } else if (error is FormatException) {
        _errorCode = 'sourceUnavailable';
      } else {
        _errorCode = 'retryMessage';
      }
      return null;
    } finally {
      _busy = false;
      if (!_disposed) notifyListeners();
    }
  }

  void _clearRestrictedState() {
    _work = null;
    _recent = [];
    _saved = null;
    _pendingSave = null;
  }

  void _requireScope() {
    if (!_sameScope) {
      _clearRestrictedState();
      throw const LumenisCoreException(
        'Business context changed.',
        statusCode: 409,
      );
    }
  }

  String _id(String key) => _operationIds.putIfAbsent(
    key,
    () =>
        'business_${DateTime.now().microsecondsSinceEpoch}_${_operationIds.length}',
  );

  Map<String, dynamic> _payload(Map<String, dynamic> response) {
    if (response['ok'] != true || response['result'] is! Map) {
      throw const FormatException('Invalid business response.');
    }
    return Map<String, dynamic>.from(response['result'] as Map);
  }

  static bool _containsSource(
    List<Map<String, dynamic>> rows,
    Map<String, dynamic> candidate,
  ) => rows.any(
    (row) =>
        row['source_job_id'] == candidate['source_job_id'] &&
        row['source_id'] == candidate['source_id'],
  );

  static bool _sameSource(
    Map<String, dynamic> left,
    Map<String, dynamic> right,
  ) =>
      left['source_job_id'] == right['source_job_id'] &&
      left['source_id'] == right['source_id'];

  static String? _blankToNull(String? value) =>
      value == null || value.trim().isEmpty ? null : value;

  static bool _validZonedDate(String value) =>
      DateTime.tryParse(value) != null &&
      RegExp(r'(Z|[+-]\d{2}:\d{2})$').hasMatch(value.trim());

  static String _signature(Object? value) => jsonEncode(value);

  @override
  void dispose() {
    _disposed = true;
    super.dispose();
  }
}
