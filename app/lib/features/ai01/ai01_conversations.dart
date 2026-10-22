import 'package:flutter/foundation.dart';

import '../../core/lumenis_core_client.dart';

class Ai01ConversationSummary {
  const Ai01ConversationSummary({
    required this.id,
    required this.title,
    required this.revision,
    required this.state,
    required this.updatedAt,
  });

  final String id;
  final String title;
  final int revision;
  final String state;
  final String updatedAt;

  factory Ai01ConversationSummary.fromJson(Map<String, Object?> json) {
    final id = json['conversation_id'];
    final title = json['title'];
    final revision = json['revision'];
    final state = json['state'];
    final updatedAt = json['updated_at'];
    if (id is! String ||
        !RegExp(r'^conv_[a-f0-9]{32}$').hasMatch(id) ||
        title is! String ||
        revision is! int ||
        revision < 1 ||
        state is! String ||
        !const {'active', 'archived'}.contains(state) ||
        updatedAt is! String) {
      throw const FormatException('AI conversation summary is invalid.');
    }
    return Ai01ConversationSummary(
      id: id,
      title: title,
      revision: revision,
      state: state,
      updatedAt: updatedAt,
    );
  }
}

class Ai01ConversationTurn {
  const Ai01ConversationTurn({
    required this.id,
    required this.conversationId,
    required this.sequence,
    required this.role,
    required this.originKind,
    required this.state,
    required this.revision,
    required this.content,
    this.recovery,
  });

  final String id;
  final String conversationId;
  final int sequence;
  final String role;
  final String originKind;
  final String state;
  final int revision;
  final Map<String, Object?> content;
  final String? recovery;

  String? get text => _string(content['text']);
  String? get code => _string(content['code']);
  String? get replyTo => _string(content['in_reply_to']);
  String? get taskId => _string(content['task_id']);
  String? get taskOwner => _string(content['owner']);

  factory Ai01ConversationTurn.fromJson(Map<String, Object?> json) {
    final id = json['turn_id'];
    final conversationId = json['conversation_id'];
    final sequence = json['sequence'];
    final role = json['role'];
    final originKind = json['origin_kind'];
    final state = json['state'];
    final revision = json['revision'];
    final content = _objectMap(json['content']);
    final recovery = json['recovery'];
    if (id is! String ||
        !RegExp(r'^turn_[a-f0-9]{32}$').hasMatch(id) ||
        conversationId is! String ||
        !RegExp(r'^conv_[a-f0-9]{32}$').hasMatch(conversationId) ||
        sequence is! int ||
        sequence < 1 ||
        !const {'user', 'assistant', 'system'}.contains(role) ||
        !const {
          'user_input',
          'model_output',
          'task_projection',
          'system_status',
        }.contains(originKind) ||
        !const {
          'recorded',
          'reserved',
          'completed',
          'unavailable',
          'failed',
          'interrupted',
        }.contains(state) ||
        revision is! int ||
        revision < 1 ||
        content == null ||
        (recovery != null && recovery is! String)) {
      throw const FormatException('AI conversation turn is invalid.');
    }
    return Ai01ConversationTurn(
      id: id,
      conversationId: conversationId,
      sequence: sequence,
      role: role as String,
      originKind: originKind as String,
      state: state as String,
      revision: revision,
      content: content,
      recovery: recovery as String?,
    );
  }
}

class Ai01ConversationDetail extends Ai01ConversationSummary {
  const Ai01ConversationDetail({
    required super.id,
    required super.title,
    required super.revision,
    required super.state,
    required super.updatedAt,
    required this.turns,
    required this.hasMore,
    required this.nextSequence,
  });

  final List<Ai01ConversationTurn> turns;
  final bool hasMore;
  final int? nextSequence;

  int get lastSequence => turns.isEmpty ? 0 : turns.last.sequence;

  factory Ai01ConversationDetail.fromJson(Map<String, Object?> json) {
    final summary = Ai01ConversationSummary.fromJson(json);
    final rawTurns = json['turns'];
    final hasMore = json['has_more'];
    final nextSequence = json['next_sequence'];
    if (rawTurns is! List ||
        hasMore is! bool ||
        (nextSequence != null && nextSequence is! int)) {
      throw const FormatException('AI conversation page is invalid.');
    }
    final turns = rawTurns
        .map((raw) {
          final map = _objectMap(raw);
          if (map == null) {
            throw const FormatException('AI conversation turn is invalid.');
          }
          return Ai01ConversationTurn.fromJson(map);
        })
        .toList(growable: false);
    if (turns.any((turn) => turn.conversationId != summary.id) ||
        !_strictlyOrdered(turns) ||
        hasMore != (nextSequence is int) ||
        (hasMore && (turns.isEmpty || nextSequence != turns.last.sequence))) {
      throw const FormatException('AI conversation page is inconsistent.');
    }
    return Ai01ConversationDetail(
      id: summary.id,
      title: summary.title,
      revision: summary.revision,
      state: summary.state,
      updatedAt: summary.updatedAt,
      turns: turns,
      hasMore: hasMore,
      nextSequence: nextSequence as int?,
    );
  }

  Ai01ConversationDetail merge(
    Ai01ConversationDetail other, {
    bool advanceCursor = false,
  }) {
    if (id != other.id) {
      throw const FormatException('AI conversation identity changed.');
    }
    final byId = {for (final turn in turns) turn.id: turn};
    for (final turn in other.turns) {
      final existing = byId[turn.id];
      if (existing != null && existing.sequence != turn.sequence) {
        throw const FormatException('AI conversation turn identity changed.');
      }
      byId[turn.id] = turn;
    }
    final merged = byId.values.toList()
      ..sort((left, right) => left.sequence.compareTo(right.sequence));
    if (!_strictlyOrdered(merged)) {
      throw const FormatException('AI conversation turn order changed.');
    }
    return Ai01ConversationDetail(
      id: id,
      title: other.revision >= revision ? other.title : title,
      revision: other.revision > revision ? other.revision : revision,
      state: other.revision >= revision ? other.state : state,
      updatedAt: other.revision >= revision ? other.updatedAt : updatedAt,
      turns: List.unmodifiable(merged),
      hasMore: advanceCursor ? other.hasMore : hasMore,
      nextSequence: advanceCursor ? other.nextSequence : nextSequence,
    );
  }
}

class Ai01ConversationMutation {
  const Ai01ConversationMutation({
    required this.turn,
    required this.revision,
    required this.idempotentHit,
    this.externalCallStopped,
    this.priorResultUnknown,
  });

  final Ai01ConversationTurn turn;
  final int revision;
  final bool idempotentHit;
  final bool? externalCallStopped;
  final bool? priorResultUnknown;

  factory Ai01ConversationMutation.fromResponse(Map<String, dynamic> response) {
    final rawTurn = _objectMap(response['turn']);
    final revision = response['revision'];
    final idempotentHit = response['idempotent_hit'];
    if (response['ok'] != true ||
        rawTurn == null ||
        revision is! int ||
        revision < 1 ||
        idempotentHit is! bool) {
      throw const FormatException('AI conversation update is invalid.');
    }
    final externalCallStopped = response['external_call_stopped'];
    final priorResultUnknown = response['prior_result_unknown'];
    if ((externalCallStopped != null && externalCallStopped is! bool) ||
        (priorResultUnknown != null && priorResultUnknown is! bool)) {
      throw const FormatException('AI conversation recovery is invalid.');
    }
    return Ai01ConversationMutation(
      turn: Ai01ConversationTurn.fromJson(rawTurn),
      revision: revision,
      idempotentHit: idempotentHit,
      externalCallStopped: externalCallStopped as bool?,
      priorResultUnknown: priorResultUnknown as bool?,
    );
  }
}

class _PendingConversationAppend {
  const _PendingConversationAppend({
    required this.text,
    required this.idempotencyKey,
    required this.expectedRevision,
    required this.afterSequence,
  });

  final String text;
  final String idempotencyKey;
  final int expectedRevision;
  final int afterSequence;
}

class Ai01ConversationListPage {
  const Ai01ConversationListPage({
    required this.items,
    required this.hasMore,
    required this.nextOffset,
  });

  final List<Ai01ConversationSummary> items;
  final bool hasMore;
  final int? nextOffset;
}

abstract interface class Ai01ConversationRepository {
  Future<Ai01ConversationListPage> list({
    required int limit,
    required int offset,
  });

  Future<Ai01ConversationSummary> create({required String title});

  Future<Ai01ConversationDetail> read({
    required String conversationId,
    required int afterSequence,
    required int limit,
  });

  Future<Ai01ConversationMutation> append({
    required String conversationId,
    required String text,
    required String idempotencyKey,
    required int expectedRevision,
  });

  Future<Ai01ConversationMutation> attachTask({
    required String conversationId,
    required String taskId,
    required String idempotencyKey,
    required int expectedRevision,
  });

  Future<Ai01ConversationMutation> respond({
    required String conversationId,
    required String turnId,
    required String idempotencyKey,
    required int expectedRevision,
    required bool retryConfirmed,
  });

  Future<Ai01ConversationMutation> interrupt({
    required String conversationId,
    required String turnId,
    required int expectedRevision,
  });
}

class CoreAi01ConversationRepository implements Ai01ConversationRepository {
  CoreAi01ConversationRepository({required this._client});

  final LumenisCoreClient _client;

  @override
  Future<Ai01ConversationListPage> list({
    required int limit,
    required int offset,
  }) async {
    final response = await _client.listAiConversations(
      limit: limit,
      offset: offset,
    );
    final raw = response['conversations'];
    final hasMore = response['has_more'];
    final nextOffset = response['next_offset'];
    if (response['ok'] != true ||
        raw is! List ||
        hasMore is! bool ||
        (nextOffset != null && nextOffset is! int) ||
        hasMore != (nextOffset is int) ||
        (hasMore && nextOffset != offset + limit)) {
      throw const FormatException('AI conversation list is invalid.');
    }
    final items = raw
        .map((item) {
          final map = _objectMap(item);
          if (map == null) {
            throw const FormatException('AI conversation list is invalid.');
          }
          return Ai01ConversationSummary.fromJson(map);
        })
        .toList(growable: false);
    if (items.map((item) => item.id).toSet().length != items.length) {
      throw const FormatException('AI conversation list is inconsistent.');
    }
    return Ai01ConversationListPage(
      items: List.unmodifiable(items),
      hasMore: hasMore,
      nextOffset: nextOffset as int?,
    );
  }

  @override
  Future<Ai01ConversationSummary> create({required String title}) async {
    final response = await _client.createAiConversation(title: title);
    final raw = _objectMap(response['conversation']);
    if (response['ok'] != true || raw == null) {
      throw const FormatException('AI conversation creation is invalid.');
    }
    return Ai01ConversationSummary.fromJson(raw);
  }

  @override
  Future<Ai01ConversationDetail> read({
    required String conversationId,
    required int afterSequence,
    required int limit,
  }) async {
    final response = await _client.readAiConversation(
      conversationId,
      afterSequence: afterSequence,
      limit: limit,
    );
    final raw = _objectMap(response['conversation']);
    if (response['ok'] != true || raw == null) {
      throw const FormatException('AI conversation read is invalid.');
    }
    final detail = Ai01ConversationDetail.fromJson(raw);
    if (detail.id != conversationId ||
        detail.turns.any((turn) => turn.sequence <= afterSequence)) {
      throw const FormatException('AI conversation identity changed.');
    }
    return detail;
  }

  @override
  Future<Ai01ConversationMutation> append({
    required String conversationId,
    required String text,
    required String idempotencyKey,
    required int expectedRevision,
  }) async {
    final result = Ai01ConversationMutation.fromResponse(
      await _client.appendAiConversationTurn(
        conversationId: conversationId,
        text: text,
        idempotencyKey: idempotencyKey,
        expectedRevision: expectedRevision,
      ),
    );
    return _validateMutation(result, conversationId, expectedRevision);
  }

  @override
  Future<Ai01ConversationMutation> attachTask({
    required String conversationId,
    required String taskId,
    required String idempotencyKey,
    required int expectedRevision,
  }) async {
    final result = Ai01ConversationMutation.fromResponse(
      await _client.attachAiConversationTask(
        conversationId: conversationId,
        taskId: taskId,
        idempotencyKey: idempotencyKey,
        expectedRevision: expectedRevision,
      ),
    );
    return _validateMutation(result, conversationId, expectedRevision);
  }

  @override
  Future<Ai01ConversationMutation> respond({
    required String conversationId,
    required String turnId,
    required String idempotencyKey,
    required int expectedRevision,
    required bool retryConfirmed,
  }) async {
    final result = Ai01ConversationMutation.fromResponse(
      await _client.respondToAiConversationTurn(
        conversationId: conversationId,
        turnId: turnId,
        idempotencyKey: idempotencyKey,
        expectedRevision: expectedRevision,
        retryConfirmed: retryConfirmed,
      ),
    );
    return _validateMutation(result, conversationId, expectedRevision);
  }

  @override
  Future<Ai01ConversationMutation> interrupt({
    required String conversationId,
    required String turnId,
    required int expectedRevision,
  }) async {
    final result = Ai01ConversationMutation.fromResponse(
      await _client.interruptAiConversationResponse(
        conversationId: conversationId,
        turnId: turnId,
        expectedRevision: expectedRevision,
      ),
    );
    return _validateMutation(result, conversationId, expectedRevision);
  }

  Ai01ConversationMutation _validateMutation(
    Ai01ConversationMutation mutation,
    String conversationId,
    int expectedRevision,
  ) {
    if (mutation.turn.conversationId != conversationId ||
        mutation.revision < expectedRevision) {
      throw const FormatException('AI conversation identity changed.');
    }
    return mutation;
  }
}

class Ai01ConversationViewModel extends ChangeNotifier {
  Ai01ConversationViewModel({required this.repository});

  final Ai01ConversationRepository repository;
  static const int pageSize = 30;

  List<Ai01ConversationSummary> conversations = const [];
  Ai01ConversationDetail? detail;
  String? selectedId;
  bool listLoading = false;
  bool detailLoading = false;
  bool busy = false;
  bool listHasMore = false;
  bool creatingUnknown = false;
  bool outcomeUnknown = false;
  String? issue;
  int _listOffset = 0;
  int _generation = 0;
  int _keyCounter = 0;
  final Map<String, _PendingConversationAppend> _pendingAppends = {};
  bool _disposed = false;

  bool get canLoadMoreTurns => detail?.hasMore == true && !detailLoading;
  bool get canLoadMoreConversations => listHasMore && !listLoading;
  bool get canSend =>
      !_disposed &&
      !busy &&
      !outcomeUnknown &&
      !_pendingAppends.containsKey(selectedId) &&
      detail?.state == 'active' &&
      selectedId == detail?.id;

  String? get pendingAppendText =>
      selectedId == null ? null : _pendingAppends[selectedId]?.text;

  Future<void> refreshList({bool selectFirstIfEmpty = true}) async {
    if (_disposed || listLoading) return;
    final preserveCreateUnknown = creatingUnknown;
    listLoading = true;
    if (!preserveCreateUnknown) issue = null;
    _notify();
    try {
      _listOffset = 0;
      final page = await repository.list(limit: pageSize, offset: 0);
      if (_disposed) return;
      conversations = page.items;
      listHasMore = page.hasMore;
      _listOffset = page.nextOffset ?? page.items.length;
      if (!creatingUnknown) issue = null;
      if (selectedId == null && selectFirstIfEmpty && page.items.isNotEmpty) {
        await open(page.items.first.id);
      }
    } catch (error) {
      if (!_disposed) {
        issue = creatingUnknown ? 'create_unknown' : _classify(error);
      }
    } finally {
      listLoading = false;
      _notify();
    }
  }

  Future<void> loadMoreConversations() async {
    if (_disposed || !canLoadMoreConversations) return;
    listLoading = true;
    _notify();
    try {
      final page = await repository.list(limit: pageSize, offset: _listOffset);
      if (_disposed) return;
      final ids = conversations.map((item) => item.id).toSet();
      conversations = List.unmodifiable([
        ...conversations,
        ...page.items.where((item) => !ids.contains(item.id)),
      ]);
      _listOffset = page.nextOffset ?? (_listOffset + page.items.length);
      listHasMore = page.hasMore;
    } catch (error) {
      if (!_disposed) issue = _classify(error);
    } finally {
      listLoading = false;
      _notify();
    }
  }

  Future<void> createConversation({
    bool acknowledgeUnresolvedPrevious = false,
  }) async {
    if (_disposed || busy) return;
    if (creatingUnknown && !acknowledgeUnresolvedPrevious) return;
    busy = true;
    issue = null;
    creatingUnknown = false;
    _notify();
    try {
      final made = await repository.create(title: '');
      if (_disposed) return;
      conversations = List.unmodifiable([
        made,
        ...conversations.where((item) => item.id != made.id),
      ]);
      selectedId = made.id;
      await open(made.id);
    } catch (error) {
      if (!_disposed) {
        issue = _classify(error);
        creatingUnknown = _isOutcomeUnknown(error);
        if (creatingUnknown) issue = 'create_unknown';
      }
      await refreshList(selectFirstIfEmpty: false);
    } finally {
      busy = false;
      _notify();
    }
  }

  Future<void> open(String conversationId) async {
    if (_disposed) return;
    final generation = ++_generation;
    selectedId = conversationId;
    detail = null;
    detailLoading = true;
    final pendingAppend = _pendingAppends[conversationId];
    issue = pendingAppend == null ? null : 'append_unknown';
    outcomeUnknown = pendingAppend != null;
    _notify();
    try {
      final result = await repository.read(
        conversationId: conversationId,
        afterSequence: 0,
        limit: pageSize,
      );
      if (_isStale(generation) || result.id != conversationId) return;
      detail = result;
      outcomeUnknown =
          pendingAppend != null ||
          result.turns.any((turn) => turn.state == 'reserved');
      if (outcomeUnknown && pendingAppend == null) issue = 'unknown';
      _updateSummary(result);
    } catch (error) {
      if (!_isStale(generation)) {
        issue = pendingAppend == null ? _classify(error) : 'append_unknown';
        if (pendingAppend != null) outcomeUnknown = true;
      }
    } finally {
      if (!_isStale(generation)) {
        detailLoading = false;
        _notify();
      }
    }
  }

  Future<void> loadMoreTurns() async {
    final current = detail;
    if (_disposed || current == null || !canLoadMoreTurns) return;
    final cursor = current.nextSequence;
    if (cursor == null) return;
    final generation = _generation;
    detailLoading = true;
    issue = null;
    _notify();
    try {
      final page = await repository.read(
        conversationId: current.id,
        afterSequence: cursor,
        limit: pageSize,
      );
      if (_isStale(generation) || page.id != current.id) return;
      detail = current.merge(page, advanceCursor: true);
      outcomeUnknown = detail!.turns.any((turn) => turn.state == 'reserved');
      if (outcomeUnknown) issue = 'unknown';
      _updateSummary(detail!);
    } catch (error) {
      if (!_isStale(generation)) issue = _classify(error);
    } finally {
      if (!_isStale(generation)) {
        detailLoading = false;
        _notify();
      }
    }
  }

  Future<bool> send(String text, {required VoidCallback onPersisted}) async {
    final current = detail;
    if (!canSend || current == null || text.trim().isEmpty) return false;
    final message = text;
    final conversationId = current.id;
    final userKey = _newKey('turn');
    busy = true;
    issue = null;
    outcomeUnknown = false;
    _notify();
    Ai01ConversationMutation? appended;
    try {
      appended = await repository.append(
        conversationId: conversationId,
        text: message,
        idempotencyKey: userKey,
        expectedRevision: current.revision,
      );
      _applyMutation(conversationId, appended);
      onPersisted();
    } catch (error) {
      if (!_disposed) {
        issue = _classify(error);
        outcomeUnknown = _isOutcomeUnknown(error);
        if (outcomeUnknown) {
          _pendingAppends[conversationId] = _PendingConversationAppend(
            text: message,
            idempotencyKey: userKey,
            expectedRevision: current.revision,
            afterSequence: current.lastSequence,
          );
          issue = 'append_unknown';
        }
      }
      if (outcomeUnknown) {
        await _reconcile(conversationId, afterSequence: current.lastSequence);
      }
      busy = false;
      _notify();
      return false;
    }

    try {
      final response = await repository.respond(
        conversationId: conversationId,
        turnId: appended.turn.id,
        idempotencyKey: _newKey('reply'),
        expectedRevision: appended.revision,
        retryConfirmed: false,
      );
      _applyMutation(conversationId, response);
      outcomeUnknown = response.turn.state == 'reserved';
      if (outcomeUnknown) issue = 'unknown';
    } catch (error) {
      issue = _classify(error);
      outcomeUnknown = _isOutcomeUnknown(error);
      if (outcomeUnknown) {
        await _reconcile(conversationId, afterSequence: appended.turn.sequence);
      } else {
        await _reconcile(conversationId, afterSequence: appended.turn.sequence);
      }
    } finally {
      busy = false;
      _notify();
    }
    return true;
  }

  Future<void> checkOutcome({VoidCallback? onAppendPersisted}) async {
    final current = detail;
    if (_disposed || current == null || detailLoading) return;
    final pendingAppend = _pendingAppends[current.id];
    if (pendingAppend != null) {
      final checked = await _reconcile(
        current.id,
        afterSequence: pendingAppend.afterSequence,
      );
      if (checked == null || _disposed) return;
      final persisted = checked.turns.any(
        (turn) =>
            turn.sequence > pendingAppend.afterSequence &&
            turn.originKind == 'user_input' &&
            turn.text == pendingAppend.text,
      );
      if (persisted) {
        _pendingAppends.remove(current.id);
        outcomeUnknown = detail!.turns.any((turn) => turn.state == 'reserved');
        issue = outcomeUnknown ? 'unknown' : null;
        onAppendPersisted?.call();
      } else {
        outcomeUnknown = true;
        issue = 'append_unknown';
      }
      _notify();
      return;
    }
    final userTurns = current.turns
        .where((turn) => turn.originKind == 'user_input')
        .toList(growable: false);
    await _reconcile(
      current.id,
      afterSequence: userTurns.isEmpty
          ? current.lastSequence
          : userTurns.last.sequence,
    );
  }

  Future<void> retryPendingAppend({required VoidCallback onPersisted}) async {
    final current = detail;
    final pending = current == null ? null : _pendingAppends[current.id];
    if (_disposed || current == null || pending == null || busy) return;
    busy = true;
    issue = null;
    _notify();
    try {
      final result = await repository.append(
        conversationId: current.id,
        text: pending.text,
        idempotencyKey: pending.idempotencyKey,
        expectedRevision: pending.expectedRevision,
      );
      _applyMutation(current.id, result);
      _pendingAppends.remove(current.id);
      outcomeUnknown = detail!.turns.any((turn) => turn.state == 'reserved');
      issue = outcomeUnknown ? 'unknown' : null;
      onPersisted();
    } catch (error) {
      issue = _classify(error);
      outcomeUnknown = _isOutcomeUnknown(error);
      if (outcomeUnknown) issue = 'append_unknown';
      await _reconcile(current.id, afterSequence: pending.afterSequence);
    } finally {
      busy = false;
      _notify();
    }
  }

  Future<void> respondToTurn(
    Ai01ConversationTurn userTurn, {
    required bool confirmed,
  }) async {
    final current = detail;
    if (_disposed || current == null || busy || !confirmed) return;
    final priorResponses = current.turns.where(
      (turn) =>
          turn.originKind == 'model_output' && turn.replyTo == userTurn.id,
    );
    if (userTurn.conversationId != current.id ||
        userTurn.originKind != 'user_input' ||
        userTurn.state != 'recorded' ||
        priorResponses.isNotEmpty) {
      issue = 'conflict';
      _notify();
      return;
    }
    busy = true;
    issue = null;
    outcomeUnknown = false;
    _notify();
    try {
      final result = await repository.respond(
        conversationId: current.id,
        turnId: userTurn.id,
        idempotencyKey: _newKey('reply'),
        expectedRevision: current.revision,
        retryConfirmed: false,
      );
      _applyMutation(current.id, result);
      outcomeUnknown = result.turn.state == 'reserved';
      if (outcomeUnknown) issue = 'unknown';
    } catch (error) {
      issue = _classify(error);
      outcomeUnknown = _isOutcomeUnknown(error);
      await _reconcile(current.id, afterSequence: userTurn.sequence);
    } finally {
      busy = false;
      _notify();
    }
  }

  void showConversationList() {
    if (_disposed || busy) return;
    _generation++;
    selectedId = null;
    detail = null;
    detailLoading = false;
    issue = null;
    outcomeUnknown = false;
    _notify();
  }

  Future<void> retryResponse(
    Ai01ConversationTurn userTurn, {
    required bool confirmed,
  }) async {
    final current = detail;
    if (_disposed || current == null || busy || !confirmed) return;
    final previous = current.turns.where(
      (turn) =>
          turn.originKind == 'model_output' && turn.replyTo == userTurn.id,
    );
    if (userTurn.conversationId != current.id ||
        userTurn.originKind != 'user_input' ||
        previous.isEmpty ||
        previous.any((turn) => turn.state == 'reserved') ||
        !const {
          'failed',
          'unavailable',
          'interrupted',
        }.contains(previous.last.state)) {
      issue = 'conflict';
      _notify();
      return;
    }
    busy = true;
    issue = null;
    outcomeUnknown = false;
    _notify();
    try {
      final result = await repository.respond(
        conversationId: current.id,
        turnId: userTurn.id,
        idempotencyKey: _newKey('retry'),
        expectedRevision: current.revision,
        retryConfirmed: true,
      );
      _applyMutation(current.id, result);
      outcomeUnknown = result.turn.state == 'reserved';
      if (outcomeUnknown) issue = 'unknown';
    } catch (error) {
      issue = _classify(error);
      outcomeUnknown = _isOutcomeUnknown(error);
      await _reconcile(current.id, afterSequence: userTurn.sequence);
    } finally {
      busy = false;
      _notify();
    }
  }

  Future<void> interruptResponse(
    Ai01ConversationTurn turn, {
    required bool confirmed,
  }) async {
    final current = detail;
    if (_disposed || current == null || busy || !confirmed) return;
    if (current.id != turn.conversationId ||
        turn.originKind != 'model_output' ||
        turn.state != 'reserved') {
      issue = 'conflict';
      _notify();
      return;
    }
    busy = true;
    issue = null;
    _notify();
    try {
      final result = await repository.interrupt(
        conversationId: current.id,
        turnId: turn.id,
        expectedRevision: current.revision,
      );
      _applyMutation(current.id, result);
      issue = 'interrupted_unknown';
      outcomeUnknown = true;
    } catch (error) {
      issue = _classify(error);
      await _reconcile(current.id, afterSequence: turn.sequence - 1);
    } finally {
      busy = false;
      _notify();
    }
  }

  Future<void> attachTask(String taskId) async {
    final current = detail;
    if (_disposed || current == null || busy || taskId.isEmpty) return;
    if (current.turns.any((turn) => turn.taskId == taskId)) return;
    busy = true;
    issue = null;
    _notify();
    try {
      final result = await repository.attachTask(
        conversationId: current.id,
        taskId: taskId,
        idempotencyKey: _newKey('task'),
        expectedRevision: current.revision,
      );
      _applyMutation(current.id, result);
    } catch (error) {
      issue = _classify(error);
      if (_isOutcomeUnknown(error)) {
        outcomeUnknown = true;
        await _reconcile(current.id, afterSequence: current.lastSequence);
      }
    } finally {
      busy = false;
      _notify();
    }
  }

  Future<Ai01ConversationDetail?> _reconcile(
    String conversationId, {
    required int afterSequence,
  }) async {
    final generation = _generation;
    try {
      final result = await repository.read(
        conversationId: conversationId,
        afterSequence: afterSequence,
        limit: pageSize,
      );
      if (_isStale(generation) || result.id != conversationId) return null;
      final current = detail;
      detail = current != null && current.id == conversationId
          ? current.merge(result)
          : result;
      final pendingAppend = _pendingAppends[conversationId];
      outcomeUnknown =
          pendingAppend != null ||
          detail!.turns.any((turn) => turn.state == 'reserved');
      if (pendingAppend != null) {
        issue = 'append_unknown';
      } else if (!outcomeUnknown &&
          const {
            'unknown',
            'server',
            'offline',
            'interrupted_unknown',
          }.contains(issue)) {
        issue = null;
      } else if (outcomeUnknown) {
        issue = 'unknown';
      }
      _updateSummary(detail!);
      _notify();
      return detail;
    } catch (_) {
      if (!_disposed) {
        outcomeUnknown = true;
        if (issue != 'create_unknown' && issue != 'append_unknown') {
          issue = 'unknown';
        }
        _notify();
      }
      return null;
    }
  }

  void _applyMutation(String conversationId, Ai01ConversationMutation value) {
    if (value.turn.conversationId != conversationId) {
      throw const FormatException('AI conversation identity changed.');
    }
    final current = detail;
    if (current?.id != conversationId) return;
    final byId = {for (final turn in current!.turns) turn.id: turn};
    byId[value.turn.id] = value.turn;
    final turns = byId.values.toList()
      ..sort((left, right) => left.sequence.compareTo(right.sequence));
    detail = Ai01ConversationDetail(
      id: current.id,
      title: current.title,
      revision: value.revision > current.revision
          ? value.revision
          : current.revision,
      state: current.state,
      updatedAt: current.updatedAt,
      turns: List.unmodifiable(turns),
      hasMore: current.hasMore,
      nextSequence: current.nextSequence,
    );
    _updateSummary(detail!);
    _notify();
  }

  void _updateSummary(Ai01ConversationSummary summary) {
    final index = conversations.indexWhere((item) => item.id == summary.id);
    if (index < 0) return;
    final next = [...conversations];
    next[index] = summary;
    conversations = List.unmodifiable(next);
  }

  String _newKey(String prefix) {
    _keyCounter++;
    return '$prefix-${DateTime.now().microsecondsSinceEpoch}-$_keyCounter';
  }

  bool _isStale(int generation) => _disposed || generation != _generation;

  static bool _isOutcomeUnknown(Object error) {
    if (error is FormatException) return true;
    if (error is LumenisCoreException) {
      final status = error.statusCode;
      return status == null || status >= 500;
    }
    return true;
  }

  static String _classify(Object error) {
    if (error is LumenisCoreException) {
      final status = error.statusCode;
      if (status == null) return 'unknown';
      return switch (status) {
        401 => 'authentication',
        403 => 'permission',
        409 => 'conflict',
        400 => 'invalid',
        >= 500 => 'server',
        _ => 'unknown',
      };
    }
    return error is FormatException ? 'unknown' : 'offline';
  }

  void _notify() {
    if (!_disposed) notifyListeners();
  }

  @override
  void dispose() {
    _disposed = true;
    _generation++;
    super.dispose();
  }
}

bool _strictlyOrdered(List<Ai01ConversationTurn> turns) {
  for (var index = 1; index < turns.length; index++) {
    if (turns[index - 1].sequence >= turns[index].sequence) return false;
  }
  return true;
}

Map<String, Object?>? _objectMap(Object? value) {
  if (value is! Map) return null;
  return value.map((key, value) => MapEntry('$key', value));
}

String? _string(Object? value) =>
    value is String && value.isNotEmpty ? value : null;
