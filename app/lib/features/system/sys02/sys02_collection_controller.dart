import 'dart:convert';
import 'dart:math';

import 'package:flutter/foundation.dart';

import '../../../core/lumenis_core_client.dart';

/// Owns the existing SYS-02 collection request lifecycle independently of a
/// particular renderer. Server authorization and the prepare/confirm contract
/// remain authoritative for every operation.
class Sys02CollectionController extends ChangeNotifier {
  Sys02CollectionController({required this.client, String? initialDomainId})
    : _scopePin = jsonEncode(client.currentContextEnvelope) {
    final selection = client.currentContextEnvelope?['context'];
    if (selection is Map && selection['mode'] == 'FOCUS') {
      _domain = _businessDomain(selection['domain_id']);
    } else {
      _domain = _businessDomain(initialDomainId);
    }
  }

  final LumenisCoreClient client;
  final String _scopePin;
  bool _disposed = false;
  bool _loading = true;
  bool _busy = false;
  int _executionEpoch = 0;
  List<Map<String, dynamic>> _platforms = [];
  String? _platform;
  String? _domain;
  String? _status;
  String _capability = 'search';
  String _query = '';
  int _limit = 20;
  int _maxPageItems = 20;
  String _period = 'month';
  DateTime? _customSince;
  DateTime? _customUntil;
  Map<String, dynamic>? _task;
  final List<Map<String, dynamic>> _history = [];
  int? _historyBefore;
  String? _requestId;
  String? _historyError;
  Map<String, dynamic>? _result;
  Map<String, dynamic>? _openedItem;

  bool get loading => _loading;
  bool get busy => _busy;
  bool get sameScope => _scopePin == jsonEncode(client.currentContextEnvelope);
  bool get needsLeaveProtection => _busy && _task == null;
  bool get canLeave => !_busy || _task != null;
  String? get domainId => _domain;
  String? get platform => _platform;
  String get capability => _capability;
  String get query => _query;
  int get limit => _limit;
  int get maxPageItems => _maxPageItems;
  String get period => _period;
  DateTime? get customSince => _customSince;
  DateTime? get customUntil => _customUntil;
  String? get status => _status;
  String? get historyError => _historyError;
  String? get requestId => _requestId;
  Map<String, dynamic>? get task => _task == null ? null : Map.of(_task!);
  Map<String, dynamic>? get result => _result == null ? null : Map.of(_result!);
  Map<String, dynamic>? get openedItem =>
      _openedItem == null ? null : Map.of(_openedItem!);
  List<Map<String, dynamic>> get platforms =>
      List.unmodifiable(_platforms.map(Map<String, dynamic>.unmodifiable));
  List<Map<String, dynamic>> get history =>
      List.unmodifiable(_history.map(Map<String, dynamic>.unmodifiable));
  int? get historyBefore => _historyBefore;
  bool get hasMoreHistory => _historyBefore != null;

  String? get visibleResultStatus {
    final saved = _result?['saved_sources'] as Map?;
    final discovery =
        _result?['discovery_observations'] ?? saved?['discovery_observations'];
    if (const {
          'PARTIAL_COMMITTED',
          'PARTIAL_ACQUISITION_PENDING',
          'PARTIAL_SOURCE_INTAKE_PENDING',
          'PARTIAL',
        }.contains(_status) &&
        _result?['returned_count'] == 0 &&
        discovery is List &&
        discovery.isNotEmpty) {
      return 'DISCOVERY_ONLY';
    }
    return _status;
  }

  static String? _businessDomain(Object? value) {
    final domain = value?.toString().toUpperCase();
    return const {'CTH', 'BMP'}.contains(domain) ? domain : null;
  }

  void _notify() {
    if (!_disposed) notifyListeners();
  }

  void _setBusy(bool value) {
    _busy = value;
    _notify();
  }

  void _scopeDenied() {
    _result = null;
    _task = null;
    _openedItem = null;
    _history.clear();
    _historyBefore = null;
    _status = 'SCOPE_UNAUTHORIZED';
    _notify();
  }

  bool _requireSameScope() {
    if (sameScope) return true;
    _scopeDenied();
    return false;
  }

  void updateRequest({
    String? platform,
    String? capability,
    String? query,
    int? limit,
  }) {
    if (_busy) return;
    final nextCapability = capability ?? _capability;
    if (!const {
      'search',
      'detail',
      'author',
      'author_posts',
    }.contains(nextCapability)) {
      throw const FormatException('Unsupported collection capability.');
    }
    _platform = platform ?? _platform;
    _capability = nextCapability;
    _query = query ?? _query;
    if (limit != null) {
      _limit = limit.clamp(1, _maxPageItems).toInt();
    }
    _requestId = null;
    _notify();
  }

  void updatePeriod({
    required String period,
    DateTime? since,
    DateTime? until,
  }) {
    if (_busy) return;
    if (!const {
      'all',
      'week',
      'month',
      'half-year',
      'year',
      'custom',
    }.contains(period)) {
      throw const FormatException('Unsupported publication period.');
    }
    if (period == 'custom' &&
        (since == null || until == null || since.isAfter(until))) {
      throw const FormatException('A valid publication range is required.');
    }
    _period = period;
    _customSince = period == 'custom' ? since : _customSince;
    _customUntil = period == 'custom' ? until : _customUntil;
    _requestId = null;
    _notify();
  }

  Map<String, dynamic> buildSourceRequest() {
    final platform = _platform;
    final query = _query.trim();
    if (platform == null || platform.isEmpty || query.isEmpty) {
      throw const FormatException('A platform and query are required.');
    }
    final detail = _capability == 'detail';
    return {
      'platform': platform,
      'capability': _capability,
      if (detail)
        'content_id': query
      else if (_capability == 'author' || _capability == 'author_posts')
        'author_id': query
      else
        'keyword': query,
      if (!detail) 'max_results': _limit,
      if (_capability == 'search') ..._publicationRange(),
    };
  }

  Map<String, String> _publicationRange() {
    if (_period == 'all') return {};
    final today = _dateOnly(DateTime.now());
    final months = switch (_period) {
      'month' => 1,
      'half-year' => 6,
      'year' => 12,
      _ => 0,
    };
    final startMonth = DateTime(today.year, today.month - months);
    final lastDay = DateTime(startMonth.year, startMonth.month + 1, 0).day;
    final since = _period == 'custom'
        ? _dateOnly(_customSince!)
        : months == 0
        ? today.subtract(const Duration(days: 6))
        : DateTime(startMonth.year, startMonth.month, min(today.day, lastDay));
    final until = _period == 'custom' ? _dateOnly(_customUntil!) : today;
    String date(DateTime value) =>
        '${value.year.toString().padLeft(4, '0')}-${value.month.toString().padLeft(2, '0')}-${value.day.toString().padLeft(2, '0')}';
    return {'publication_since': date(since), 'publication_until': date(until)};
  }

  static DateTime _dateOnly(DateTime value) =>
      DateTime(value.year, value.month, value.day);

  Future<void> initialize({int? initialTaskId}) async {
    await loadSources();
    if (_domain == null || !_requireSameScope()) return;
    try {
      await loadHistory();
      if (initialTaskId case final int taskId when taskId > 0) {
        await taskAction('status', taskId: taskId);
      }
    } catch (_) {
      _historyError = 'UNCONFIRMED';
      _notify();
    }
  }

  Future<void> loadSources() async {
    if (!_requireSameScope()) return;
    _loading = true;
    _notify();
    try {
      final data = await client.collectionSources();
      if (!_requireSameScope()) return;
      if (data['ok'] != true || data['platforms'] is! List) {
        throw const FormatException('Collection sources are unavailable.');
      }
      final rows = <Map<String, dynamic>>[];
      for (final raw in [
        data['primary_collection'],
        ...data['platforms'] as List,
      ]) {
        if (raw is! Map ||
            raw['platform'] is! String ||
            raw['name'] is! String) {
          continue;
        }
        final row = Map<String, dynamic>.from(raw);
        if (!rows.any((item) => item['platform'] == row['platform'])) {
          rows.add(row);
        }
      }
      _platforms = rows;
      final serverLimit = (data['request_limits'] as Map?)?['max_page_items'];
      if (serverLimit is int && serverLimit > 0) {
        _maxPageItems = serverLimit;
        _limit = min(_limit, serverLimit);
      }
      if (!_platforms.any((item) => item['platform'] == _platform)) {
        _platform = null;
      }
      _status = null;
    } catch (error) {
      _handleFailure(error);
    } finally {
      _loading = false;
      _notify();
    }
  }

  Future<void> loadHistory({bool more = false}) async {
    final domain = _domain;
    if (domain == null || !_requireSameScope()) return;
    final pin = jsonEncode(client.currentContextEnvelope);
    final data = await client.collectionRequests(
      domainId: domain,
      before: more ? _historyBefore : null,
    );
    if (pin != jsonEncode(client.currentContextEnvelope) ||
        !_requireSameScope()) {
      return;
    }
    if (data['ok'] != true || data['tasks'] is! List) {
      throw const FormatException('Collection history is unavailable.');
    }
    final rows = <Map<String, dynamic>>[];
    for (final raw in data['tasks'] as List) {
      if (raw is Map) rows.add(Map<String, dynamic>.from(raw));
    }
    if (!more) _history.clear();
    _history.addAll(rows);
    _historyBefore = data['next_cursor'] as int?;
    _historyError = null;
    _notify();
  }

  void _applyTask(Map<String, dynamic> value) {
    if (!_requireSameScope()) return;
    if (value['task_id'] is! int) {
      _status = value['status'] as String? ?? 'UNAVAILABLE';
      _notify();
      return;
    }
    _task = Map<String, dynamic>.from(value);
    _result = value['result'] is Map
        ? Map<String, dynamic>.from(value['result'] as Map)
        : null;
    _status =
        const {'CANCELLED', 'FAILED', 'WAITING_USER'}.contains(value['status'])
        ? value['status'] as String?
        : _result?['status'] as String? ?? value['status'] as String?;
    _notify();
  }

  void _handleFailure(Object error) {
    final denied =
        error is LumenisCoreException &&
        const {401, 403, 404, 410}.contains(error.statusCode);
    if (!sameScope || denied) {
      _result = null;
      _task = null;
      _openedItem = null;
      _history.clear();
      _historyBefore = null;
    }
    _status = !sameScope || denied ? 'SCOPE_UNAUTHORIZED' : 'UNCONFIRMED';
    _notify();
  }

  Future<void> startRequest({Map<String, dynamic>? sourceOverride}) async {
    if (_busy || _domain == null || !_requireSameScope()) return;
    Map<String, dynamic> source;
    try {
      source = Map<String, dynamic>.from(
        sourceOverride ?? buildSourceRequest(),
      );
    } on FormatException {
      _status = 'INVALID_REQUEST';
      _notify();
      return;
    }
    final domain = _domain!;
    final epoch = ++_executionEpoch;
    _busy = true;
    _result = null;
    _task = null;
    _openedItem = null;
    _status = null;
    _requestId ??=
        'source_${DateTime.now().microsecondsSinceEpoch}_${Random.secure().nextInt(1 << 30)}';
    _notify();
    try {
      final prepared = await client.collectionRequestAction(
        domainId: domain,
        action: 'prepare',
        sourceRequest: source,
      );
      if (!_requireSameScope() || epoch != _executionEpoch) return;
      if (prepared['ok'] != true || prepared['approval_resource'] is! String) {
        _status = prepared['status'] as String? ?? 'UNAVAILABLE';
        _notify();
        return;
      }
      if (source['capability'] == 'media') {
        source = Map<String, dynamic>.from(prepared['request'] as Map)
          ..remove('platform');
      }
      final confirmed = await client.collectionRequestAction(
        domainId: domain,
        action: 'confirm',
        sourceRequest: source,
        confirmedResource: prepared['approval_resource'] as String,
      );
      if (!_requireSameScope() || epoch != _executionEpoch) return;
      if (confirmed['approved'] != true) {
        _status = confirmed['status'] as String? ?? 'UNAVAILABLE';
        _notify();
        return;
      }
      final started = await client.collectionRequestAction(
        domainId: domain,
        action: 'start',
        sourceRequest: source,
        requestId: _requestId,
      );
      if (!_requireSameScope() || epoch != _executionEpoch) return;
      _applyTask(started);
      final taskId = _task?['task_id'];
      if (taskId is! int || !_requireSameScope()) return;
      final completed = await client.collectionRequestAction(
        domainId: domain,
        action: 'step',
        taskId: taskId,
      );
      if (!_requireSameScope() || epoch != _executionEpoch) return;
      _applyTask(completed);
      await _continueMediaRequest(domain, completed, epoch);
      _requestId = null;
    } catch (error) {
      if (epoch == _executionEpoch) _handleFailure(error);
    } finally {
      // The older request can be invalidated by a concurrent cancel. Keep its
      // completion responsible for releasing the shared busy state, matching
      // the previous operation lifecycle.
      _busy = false;
      _notify();
      if (sameScope) {
        try {
          await loadHistory();
        } catch (_) {
          _historyError = 'UNCONFIRMED';
          _notify();
        }
      }
    }
  }

  Future<void> _continueMediaRequest(
    String domain,
    Map<String, dynamic> value,
    int epoch,
  ) async {
    var current = value;
    final id = current['task_id'];
    if (id is! int) return;
    while (!_disposed && sameScope && epoch == _executionEpoch) {
      final result = current['result'];
      final wait = current['retry_after_seconds'];
      if (current['request'] is! Map ||
          current['request']['capability'] != 'media' ||
          current['status'] != 'PENDING' ||
          current['cancel_requested'] == true ||
          result is! Map ||
          result['auto_continue'] != true ||
          result['intervention_required'] == true ||
          (wait is num && wait > 0)) {
        return;
      }
      final pending = jsonEncode(result['pending_positions']);
      final next = await client.collectionRequestAction(
        domainId: domain,
        action: 'step',
        taskId: id,
      );
      if (!sameScope || epoch != _executionEpoch) return;
      _applyTask(next);
      if (next['result'] is! Map ||
          jsonEncode(next['result']['pending_positions']) == pending) {
        return;
      }
      current = next;
    }
  }

  Future<void> taskAction(String action, {int? taskId, int? beforePage}) async {
    if (!const {
      'status',
      'step',
      'cancel',
      'resume',
      'recover',
    }.contains(action)) {
      throw const FormatException('Unsupported collection task action.');
    }
    final id = taskId ?? _task?['task_id'] as int?;
    final domain = _domain;
    if (id == null ||
        domain == null ||
        !_requireSameScope() ||
        (_busy && action != 'cancel')) {
      return;
    }
    final alreadyRunning = _busy;
    final epoch = ++_executionEpoch;
    _busy = true;
    _notify();
    try {
      if (const {'step', 'resume', 'recover'}.contains(action)) {
        final rawRequest = _task?['request'];
        if (rawRequest is! Map) {
          _status = 'UNCONFIRMED';
          _notify();
          return;
        }
        final saved = Map<String, dynamic>.from(rawRequest)
          ..remove('source_url');
        if (saved['capability'] == 'comments' ||
            saved['capability'] == 'media') {
          saved.remove('platform');
        }
        if (saved['capability'] == 'detail') saved.remove('max_results');
        final prepared = await client.collectionRequestAction(
          domainId: domain,
          action: 'prepare',
          sourceRequest: saved,
        );
        if (!_requireSameScope() || epoch != _executionEpoch) return;
        if (prepared['approval_resource'] is! String) {
          _status = prepared['status'] as String? ?? 'UNAVAILABLE';
          _notify();
          return;
        }
        final approved = await client.collectionRequestAction(
          domainId: domain,
          action: 'confirm',
          sourceRequest: saved,
          confirmedResource: prepared['approval_resource'] as String,
        );
        if (!_requireSameScope() || epoch != _executionEpoch) return;
        if (approved['approved'] != true) {
          _status = approved['status'] as String? ?? 'UNAVAILABLE';
          _notify();
          return;
        }
      }
      final value = action == 'status'
          ? await client.collectionRequest(
              domainId: domain,
              taskId: id,
              beforePage: beforePage,
            )
          : await client.collectionRequestAction(
              domainId: domain,
              action: action,
              taskId: id,
            );
      if (!_requireSameScope() || epoch != _executionEpoch) return;
      _applyTask(value);
      if (action == 'step') {
        await _continueMediaRequest(domain, value, epoch);
      }
      await loadHistory();
    } catch (error) {
      if (epoch == _executionEpoch) _handleFailure(error);
    } finally {
      if (!(action == 'cancel' && alreadyRunning)) {
        _busy = false;
      }
      _notify();
    }
  }

  Future<void> retryTask() async {
    final request = _task?['request'];
    if (request is Map && request['capability'] == 'media' && !_busy) {
      final source = Map<String, dynamic>.from(request)
        ..remove('platform')
        ..remove('source_url');
      _requestId = null;
      await startRequest(sourceOverride: source);
      return;
    }
    await taskAction('resume');
  }

  Future<Map<String, dynamic>?> readPage(Map<String, dynamic> page) async {
    final domain = _domain;
    if (_busy || domain == null || !_requireSameScope()) return null;
    _setBusy(true);
    try {
      final evidence = page['author_evidence_ref'] ?? page['evidence_ref'];
      Map<String, dynamic>? value;
      if (page['page_ref'] != null && page['source_id'] is String) {
        value = await client.sourceComments(
          domainId: domain,
          sourceId: page['source_id'] as String,
          pageRef: page['page_ref'] as String,
        );
        if (!_requireSameScope()) return null;
        _result = {...page, 'saved_page': value};
      } else if (evidence != null) {
        final ref = evidence.toString().startsWith('app_evidence_records:')
            ? evidence.toString()
            : 'app_evidence_records:$evidence';
        value = await client.collectedSourceResults(
          domainId: domain,
          evidenceRef: ref,
        );
        if (!_requireSameScope()) return null;
        _result = {...page, 'saved_sources': value};
      }
      _notify();
      return _result == null ? null : Map.of(_result!);
    } catch (error) {
      _handleFailure(error);
      return null;
    } finally {
      _setBusy(false);
    }
  }

  Future<Map<String, dynamic>?> readSource(Map<String, dynamic> item) async {
    final domain = _domain;
    if (_busy ||
        domain == null ||
        !_requireSameScope() ||
        item['evidence_ref'] is! String ||
        item['source_id'] is! String) {
      return null;
    }
    _setBusy(true);
    try {
      final value = await client.collectedSourceResults(
        domainId: domain,
        evidenceRef: item['evidence_ref'] as String,
        sourceId: item['source_id'] as String,
      );
      if (!_requireSameScope()) return null;
      final items = value['items'];
      if (items is! List || items.length != 1 || items.single is! Map) {
        throw const FormatException('Saved source identity is unavailable.');
      }
      _openedItem = Map<String, dynamic>.from(items.single as Map);
      _notify();
      return Map.of(_openedItem!);
    } catch (error) {
      _handleFailure(error);
      return null;
    } finally {
      _setBusy(false);
    }
  }

  Future<Map<String, dynamic>?> readReview(Map<String, dynamic> item) async {
    final domain = _domain;
    final candidateId = item['candidate_id'];
    if (_busy ||
        domain == null ||
        !_requireSameScope() ||
        item['evidence_ref'] is! String ||
        candidateId is! String) {
      return null;
    }
    _setBusy(true);
    try {
      final value = await client.collectedSourceResults(
        domainId: domain,
        evidenceRef: item['evidence_ref'] as String,
        sourceId: candidateId,
      );
      if (!_requireSameScope()) return null;
      final rows = value['review_candidates'];
      if (rows is! List ||
          rows.length != 1 ||
          rows.single is! Map ||
          rows.single['candidate_id'] != candidateId ||
          rows.single['body'] is! String) {
        throw const FormatException('Review source identity is unavailable.');
      }
      _openedItem = Map<String, dynamic>.from(rows.single as Map);
      _notify();
      return Map.of(_openedItem!);
    } catch (error) {
      _handleFailure(error);
      return null;
    } finally {
      _setBusy(false);
    }
  }

  Future<ContentProjectFile?> readMedia(Map<String, dynamic> media) async {
    final domain = _domain;
    final taskId = _task?['task_id'];
    final original = media['original'];
    if (_busy ||
        domain == null ||
        taskId is! int ||
        original is! Map ||
        media['evidence_ref'] is! String ||
        original['sha256'] is! String ||
        !_requireSameScope()) {
      return null;
    }
    _setBusy(true);
    try {
      final file = await client.collectedMediaFile(
        domainId: domain,
        taskId: taskId,
        evidenceRef: media['evidence_ref'] as String,
        sha256: original['sha256'] as String,
      );
      if (!_requireSameScope()) return null;
      return file;
    } catch (error) {
      _handleFailure(error);
      return null;
    } finally {
      _setBusy(false);
    }
  }

  @override
  void dispose() {
    _disposed = true;
    super.dispose();
  }
}

/// Owns saved-comment pagination and the server-authorized collection task.
class Sys02CommentsController extends ChangeNotifier {
  Sys02CommentsController({
    required this.client,
    required this.domainId,
    required this.sourceId,
  }) : _scopePin = jsonEncode(client.currentContextEnvelope);

  final LumenisCoreClient client;
  final String domainId;
  final String sourceId;
  final String _scopePin;
  bool _disposed = false;
  bool _busy = false;
  bool _stopping = false;
  bool _includeReplies = false;
  bool _attempted = false;
  String? _requestId;
  int? _taskId;
  final List<Map<String, dynamic>> _comments = [];
  String? _nextCursor;
  String? _status;
  String? _pageRef;
  String? _sourceVersion;
  Map<String, dynamic>? _continuation;

  bool get busy => _busy;
  bool get stopping => _stopping;
  bool get attempted => _attempted;
  bool get includeReplies => _includeReplies;
  bool get sameScope => _scopePin == jsonEncode(client.currentContextEnvelope);
  int? get taskId => _taskId;
  String? get status => _status;
  String? get nextCursor => _nextCursor;
  String? get pageRef => _pageRef;
  String? get sourceVersion => _sourceVersion;
  Map<String, dynamic>? get continuation =>
      _continuation == null ? null : Map.of(_continuation!);
  List<Map<String, dynamic>> get comments =>
      List.unmodifiable(_comments.map(Map<String, dynamic>.unmodifiable));
  bool get hasMoreSavedComments => _nextCursor != null;
  bool get canContinueCollection => _continuation != null;

  void _notify() {
    if (!_disposed) notifyListeners();
  }

  bool _requireSameScope() {
    if (sameScope) return true;
    _comments.clear();
    _continuation = null;
    _nextCursor = null;
    _status = 'SCOPE_UNAUTHORIZED';
    _notify();
    return false;
  }

  void setIncludeReplies(bool value) {
    if (_busy || _attempted) return;
    _includeReplies = value;
    _notify();
  }

  void _apply(Map<String, dynamic> value, {bool append = false}) {
    if (!_requireSameScope()) return;
    final rows = value['comments'];
    if (rows is! List ||
        rows.any(
          (row) =>
              row is! Map ||
              (row['content'] is! String &&
                  row['state'] != 'LEGACY_COMMENT_NOT_VERIFIED'),
        )) {
      throw const FormatException('Saved comments are malformed.');
    }
    if (!append) _comments.clear();
    for (final raw in rows) {
      final row = Map<String, dynamic>.from(raw as Map);
      final nativeId = row['platform_comment_id'];
      final existing = nativeId == null
          ? -1
          : _comments.indexWhere(
              (old) => old['platform_comment_id'] == nativeId,
            );
      if (existing >= 0) {
        _comments[existing] = row;
      } else {
        _comments.add(row);
      }
    }
    _nextCursor = value['next_cursor'] as String?;
    _pageRef = value['page_ref'] as String? ?? _pageRef;
    _sourceVersion = value['source_version_state'] as String?;
    _status = value['status'] as String?;
    _continuation = value['continuation'] is Map
        ? Map<String, dynamic>.from(value['continuation'] as Map)
        : null;
    _notify();
  }

  void _handleFailure(Object error) {
    final denied =
        error is LumenisCoreException &&
        const {401, 403, 404, 410}.contains(error.statusCode);
    if (denied || !sameScope) {
      _comments.clear();
      _continuation = null;
      _nextCursor = null;
    }
    _status = denied || !sameScope ? 'SCOPE_UNAUTHORIZED' : 'UNCONFIRMED';
    _notify();
  }

  Future<void> initialize() => read();

  Future<void> read({bool more = false, bool exactPage = false}) async {
    if (_busy || !_requireSameScope()) return;
    _busy = true;
    _notify();
    try {
      final value = await client.sourceComments(
        domainId: domainId,
        sourceId: sourceId,
        before: more ? _nextCursor : null,
        pageRef: exactPage ? _pageRef : null,
      );
      if (_requireSameScope()) _apply(value, append: more);
    } catch (error) {
      _handleFailure(error);
    } finally {
      _busy = false;
      _notify();
    }
  }

  Future<void> collect({bool more = false}) async {
    if (_busy || (more && _continuation == null) || !_requireSameScope()) {
      return;
    }
    _busy = true;
    _attempted = true;
    _notify();
    try {
      final source = <String, dynamic>{
        'capability': 'comments',
        'source_id': sourceId,
        'max_results': 20,
        'include_replies': _includeReplies,
      };
      final prepared = await client.collectionRequestAction(
        domainId: domainId,
        action: 'prepare',
        sourceRequest: source,
      );
      if (!_requireSameScope()) return;
      if (prepared['approval_resource'] is! String) {
        _status = prepared['status'] as String? ?? 'UNAVAILABLE';
        _notify();
        return;
      }
      final approved = await client.collectionRequestAction(
        domainId: domainId,
        action: 'confirm',
        sourceRequest: source,
        confirmedResource: prepared['approval_resource'] as String,
      );
      if (!_requireSameScope()) return;
      if (approved['approved'] != true) {
        _status = approved['status'] as String? ?? 'UNAVAILABLE';
        _notify();
        return;
      }
      if (!more || _taskId == null) {
        _requestId ??=
            'comments_${DateTime.now().microsecondsSinceEpoch}_${Random.secure().nextInt(1 << 30)}';
        final started = await client.collectionRequestAction(
          domainId: domainId,
          action: 'start',
          sourceRequest: source,
          requestId: _requestId,
        );
        if (!_requireSameScope()) return;
        if (started['task_id'] is! int) {
          _status = started['status'] as String? ?? 'UNAVAILABLE';
          _notify();
          return;
        }
        _taskId = started['task_id'] as int;
      }
      final task = await client.collectionRequestAction(
        domainId: domainId,
        action: 'step',
        taskId: _taskId,
      );
      if (!_requireSameScope()) return;
      final result = task['result'] is Map
          ? Map<String, dynamic>.from(task['result'] as Map)
          : task;
      final saved = result['saved_page'];
      if (saved is Map) {
        _apply(Map<String, dynamic>.from(saved), append: more);
      }
      _status =
          const {'CANCELLED', 'FAILED', 'WAITING_USER'}.contains(task['status'])
          ? task['status'] as String?
          : result['status'] as String? ?? task['status'] as String?;
      _continuation = task['continuation_required'] == true
          ? {'task_id': _taskId}
          : null;
      _requestId = null;
      _notify();
    } catch (error) {
      _handleFailure(error);
    } finally {
      _busy = false;
      _notify();
    }
  }

  Future<void> stop() async {
    final id = _taskId;
    if (id == null || !_requireSameScope() || _stopping) return;
    _stopping = true;
    _notify();
    try {
      final task = await client.collectionRequestAction(
        domainId: domainId,
        action: 'cancel',
        taskId: id,
      );
      if (!_requireSameScope()) return;
      _status = task['status'] as String?;
      _continuation = null;
      _notify();
    } catch (error) {
      _handleFailure(error);
    } finally {
      _stopping = false;
      _notify();
    }
  }

  @override
  void dispose() {
    _disposed = true;
    super.dispose();
  }
}
