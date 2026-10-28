import 'dart:convert';

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

class Ai01ConversationContext {
  const Ai01ConversationContext({
    required this.conversationId,
    required this.revision,
    required this.value,
    this.turn,
    this.sourceReferences = const [],
  });

  final String conversationId;
  final int revision;
  final Map<String, dynamic> value;
  final Ai01ConversationTurn? turn;
  final List<Map<String, dynamic>> sourceReferences;

  factory Ai01ConversationContext.fromResponse(
    Map<String, dynamic> response,
    String expectedId,
  ) {
    final revision = response['revision'];
    final raw = response['context'];
    if (response['ok'] != true ||
        response['conversation_id'] != expectedId ||
        revision is! int ||
        revision < 1 ||
        response['training_admission'] != 'NOT_GRANTED' ||
        response['effect_permission'] != 'NOT_GRANTED') {
      throw const FormatException('Conversation work details are invalid.');
    }
    final rawTurn = _objectMap(raw);
    final turn = raw == null
        ? null
        : rawTurn == null
        ? throw const FormatException('Conversation work details are invalid.')
        : Ai01ConversationTurn.fromJson(rawTurn);
    final value = turn == null
        ? <String, dynamic>{
            'goal': '',
            'constraints': <String>[],
            'draft': '',
            'decisions': <String>[],
            'excluded_turn_ids': <String>[],
          }
        : _objectMap(turn.content['value']);
    if ((turn != null &&
            (turn.conversationId != expectedId ||
                turn.originKind != 'system_status' ||
                turn.content['schema'] != 'conversation-human-context/v1')) ||
        value == null ||
        value.length != 5 ||
        value['goal'] is! String ||
        value['draft'] is! String ||
        ['constraints', 'decisions', 'excluded_turn_ids'].any(
          (key) =>
              value[key] is! List ||
              (value[key] as List).any((item) => item is! String),
        )) {
      throw const FormatException('Conversation work details are invalid.');
    }
    return Ai01ConversationContext(
      conversationId: expectedId,
      revision: revision,
      value: Map<String, dynamic>.from(value),
      turn: turn,
      sourceReferences: _sourceProjections(response['source_references']),
    );
  }
}

List<Map<String, dynamic>> _sourceProjections(dynamic raw) {
  if (raw == null) return const [];
  if (raw is! List) throw const FormatException('Invalid references.');
  return raw
      .map((item) {
        final projection = _objectMap(item);
        if (projection == null ||
            _objectMap(projection['reference']) == null ||
            projection['state'] is! String) {
          throw const FormatException('Invalid reference identity.');
        }
        return projection;
      })
      .toList(growable: false);
}

abstract interface class Ai01ConversationSources {
  Future<Map<String, dynamic>> sourceQuery(
    String conversationId,
    Map<String, String> query,
  );
}

/// Source lookup state owned by the conversation controller.
final class Ai01ConversationSourceSearch {
  String? conversationId;
  String? submittedQuery;
  String? sourceSnapshot;
  final List<Map<String, dynamic>> records = [];
  Map<String, dynamic>? preview;
  int? nextOffset;
  bool busy = false;
  bool incomplete = false;
  String? issue;
  bool get hasMore => nextOffset != null;
}

/// Editable context for one persistent conversation identity.
final class Ai01ConversationContextDraft {
  Ai01ConversationContextDraft(this.conversationId);

  final String conversationId;
  Ai01ConversationContext? saved;
  Ai01ConversationContext? remote;
  Map<String, dynamic> value = _emptyConversationContext();
  List<Map<String, dynamic>> sourceReferences = [];
  bool loading = false;
  bool saving = false;
  String? issue;

  bool get dirty =>
      saved != null &&
      (_contextSignature(value) != _contextSignature(saved!.value) ||
          _sourceSignature(sourceReferences) !=
              _sourceSignature(saved!.sourceReferences));
}

Map<String, dynamic> _emptyConversationContext() => {
  'goal': '',
  'constraints': <String>[],
  'draft': '',
  'decisions': <String>[],
  'excluded_turn_ids': <String>[],
};

String _contextSignature(Map<String, dynamic> value) => jsonEncode({
  for (final key in ['goal', 'constraints', 'draft', 'decisions'])
    key: value[key],
  'excluded_turn_ids': List<String>.from(value['excluded_turn_ids'] as List)
    ..sort(),
});

String _sourceSignature(List<Map<String, dynamic>> sources) =>
    jsonEncode(sources.map((source) => source['reference']).toList());

final class _PendingConversationContextSave {
  const _PendingConversationContextSave({
    required this.conversationId,
    required this.value,
    required this.sourceReferences,
    required this.idempotencyKey,
    required this.expectedRevision,
  });

  final String conversationId;
  final Map<String, dynamic> value;
  final List<Map<String, dynamic>> sourceReferences;
  final String idempotencyKey;
  final int expectedRevision;
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
  Future<Ai01ConversationContext> readContext(String conversationId);

  Future<Ai01ConversationMutation> updateContext({
    required String conversationId,
    required Map<String, dynamic> value,
    required String idempotencyKey,
    required int expectedRevision,
    List<Map<String, dynamic>>? sourceReferences,
  });

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

class CoreAi01ConversationRepository
    implements Ai01ConversationRepository, Ai01ConversationSources {
  CoreAi01ConversationRepository({required this._client});

  final LumenisCoreClient _client;

  @override
  Future<Map<String, dynamic>> sourceQuery(
    String conversationId,
    Map<String, String> query,
  ) => _client.readAiConversationContext(conversationId, query: query);

  @override
  Future<Ai01ConversationContext> readContext(String conversationId) async =>
      Ai01ConversationContext.fromResponse(
        await _client.readAiConversationContext(conversationId),
        conversationId,
      );

  @override
  Future<Ai01ConversationMutation> updateContext({
    required String conversationId,
    required Map<String, dynamic> value,
    required String idempotencyKey,
    required int expectedRevision,
    List<Map<String, dynamic>>? sourceReferences,
  }) async => _validateMutation(
    Ai01ConversationMutation.fromResponse(
      await _client.updateAiConversationContext(
        conversationId: conversationId,
        value: value,
        idempotencyKey: idempotencyKey,
        expectedRevision: expectedRevision,
        sourceReferences: sourceReferences,
      ),
    ),
    conversationId,
    expectedRevision,
  );

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

  void applyContextMutation(Ai01ConversationMutation mutation) {
    if (!_disposed && mutation.turn.originKind == 'system_status') {
      _applyMutation(mutation.turn.conversationId, mutation);
    }
  }

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
  Ai01ConversationContextDraft? contextDraft;
  final Ai01ConversationSourceSearch sourceSearch =
      Ai01ConversationSourceSearch();
  int _listOffset = 0;
  int _generation = 0;
  int _contextGeneration = 0;
  int _sourceGeneration = 0;
  int _keyCounter = 0;
  final Map<String, _PendingConversationAppend> _pendingAppends = {};
  final Map<String, _PendingConversationContextSave> _pendingContextSaves = {};
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

  Future<void> loadContext(
    String conversationId, {
    bool replaceLocal = false,
  }) async {
    if (_disposed || conversationId.isEmpty) return;
    final generation = ++_contextGeneration;
    var session = contextDraft;
    if (session == null || session.conversationId != conversationId) {
      session = Ai01ConversationContextDraft(conversationId);
      contextDraft = session;
    }
    session.loading = true;
    session.issue = null;
    _notify();
    try {
      final saved = await repository.readContext(conversationId);
      if (_disposed || generation != _contextGeneration) return;
      final localMatches =
          session.saved == null ||
          (_contextSignature(saved.value) == _contextSignature(session.value) &&
              _sourceSignature(saved.sourceReferences) ==
                  _sourceSignature(session.sourceReferences));
      if (replaceLocal || localMatches) {
        _applyContextDraft(session, saved);
        session.issue = replaceLocal ? null : 'saved';
      } else {
        session.remote = saved;
        session.issue = 'conflict';
      }
    } on LumenisCoreException catch (error) {
      if (_disposed || generation != _contextGeneration) return;
      if (_readDenied(error.statusCode)) {
        _clearContextDraft(session);
        session.issue = error.statusCode == 401
            ? 'authentication'
            : 'permission';
        // Transcript and work details share the same read boundary. Re-read
        // through the conversation owner so cached turns are dropped too.
        await open(conversationId);
      } else {
        session.issue = 'load_error';
      }
    } catch (_) {
      if (!_disposed && generation == _contextGeneration) {
        session.issue = 'load_error';
      }
    } finally {
      if (!_disposed && generation == _contextGeneration) {
        session.loading = false;
        _notify();
      }
    }
  }

  void editContext({
    required Map<String, dynamic> value,
    required List<Map<String, dynamic>> sourceReferences,
  }) {
    final session = contextDraft;
    if (_disposed || session == null || session.saving) return;
    session.value = _copyContextValue(value);
    session.sourceReferences = sourceReferences
        .map((source) => Map<String, dynamic>.from(source))
        .toList(growable: false);
    session.issue = null;
    _notify();
  }

  void addContextSource(Map<String, dynamic> source) {
    final session = contextDraft;
    if (_disposed || session == null || session.saved == null) return;
    final identity = jsonEncode(source['reference']);
    if (source['reference'] is! Map ||
        session.sourceReferences.any(
          (item) => jsonEncode(item['reference']) == identity,
        )) {
      return;
    }
    session.sourceReferences = [
      ...session.sourceReferences,
      Map<String, dynamic>.from(source),
    ];
    session.issue = null;
    _notify();
  }

  void removeContextSource(Map<String, dynamic> reference) {
    final session = contextDraft;
    if (_disposed || session == null || session.saved == null) return;
    final identity = jsonEncode(reference);
    session.sourceReferences = session.sourceReferences
        .where((source) => jsonEncode(source['reference']) != identity)
        .toList(growable: false);
    session.issue = null;
    _notify();
  }

  void discardContextEdits() {
    final session = contextDraft;
    if (_disposed || session == null) return;
    final latest = session.remote ?? session.saved;
    if (latest == null) return;
    _applyContextDraft(session, latest);
    session.issue = 'saved';
    _notify();
  }

  Future<void> saveContext({bool keepLocal = false}) async {
    final session = contextDraft;
    if (_disposed || session == null || session.saving || session.loading) {
      return;
    }
    final pending = _pendingContextSaves[session.conversationId];
    if (pending != null) {
      await checkContextSaveOutcome(session.conversationId);
      return;
    }
    final base = keepLocal ? session.remote : session.saved;
    if (base == null) return;
    final snapshot = _PendingConversationContextSave(
      conversationId: session.conversationId,
      value: _copyContextValue(session.value),
      sourceReferences: session.sourceReferences
          .map((source) => Map<String, dynamic>.from(source))
          .toList(growable: false),
      idempotencyKey: _newKey('context'),
      expectedRevision: base.revision,
    );
    _pendingContextSaves[session.conversationId] = snapshot;
    await _sendContextSave(snapshot);
  }

  Future<void> retryContextSave(String conversationId) async {
    final pending = _pendingContextSaves[conversationId];
    if (_disposed || pending == null) return;
    await checkContextSaveOutcome(conversationId);
    if (_pendingContextSaves[conversationId] == pending) {
      await _sendContextSave(pending);
    }
  }

  Future<void> checkContextSaveOutcome(String conversationId) async {
    final pending = _pendingContextSaves[conversationId];
    final session = contextDraft;
    if (_disposed || pending == null || session?.saving == true) return;
    session?.saving = true;
    _notify();
    try {
      final readback = await repository.readContext(conversationId);
      if (_disposed) return;
      if (_contextMatches(readback, pending) &&
          readback.revision > pending.expectedRevision) {
        _completeContextSave(pending, readback);
      } else if (readback.revision == pending.expectedRevision) {
        if (session != null && session.conversationId == conversationId) {
          session.saved ??= readback;
          session.issue = 'save_unknown';
        }
      } else {
        _pendingContextSaves.remove(conversationId);
        if (session != null && session.conversationId == conversationId) {
          session.remote = readback;
          session.issue = 'conflict';
        }
      }
    } on LumenisCoreException catch (error) {
      if (_disposed) return;
      if (_readDenied(error.statusCode)) {
        _pendingContextSaves.remove(conversationId);
        if (session != null && session.conversationId == conversationId) {
          _clearContextDraft(session);
          session.issue = error.statusCode == 401
              ? 'authentication'
              : 'permission';
        }
        await open(conversationId);
      } else if (session != null && session.conversationId == conversationId) {
        session.issue = 'save_unknown';
      }
    } catch (_) {
      if (!_disposed && session?.conversationId == conversationId) {
        session!.issue = 'save_unknown';
      }
    } finally {
      if (!_disposed && session?.conversationId == conversationId) {
        session!.saving = false;
        _notify();
      }
    }
  }

  Future<void> _sendContextSave(_PendingConversationContextSave pending) async {
    final session = contextDraft;
    if (_disposed || session?.saving == true) return;
    if (session?.conversationId == pending.conversationId) {
      session!.saving = true;
      session.issue = null;
    }
    _notify();
    try {
      final result = await repository.updateContext(
        conversationId: pending.conversationId,
        value: pending.value,
        idempotencyKey: pending.idempotencyKey,
        expectedRevision: pending.expectedRevision,
        sourceReferences: pending.sourceReferences
            .map(
              (source) => Map<String, dynamic>.from(source['reference'] as Map),
            )
            .toList(growable: false),
      );
      applyContextMutation(result);
      final readback = await repository.readContext(pending.conversationId);
      if (_disposed) return;
      if (_contextMatches(readback, pending) &&
          readback.revision >= result.revision) {
        _completeContextSave(pending, readback);
      } else {
        _pendingContextSaves.remove(pending.conversationId);
        if (session?.conversationId == pending.conversationId) {
          session!.remote = readback;
          session.issue = 'conflict';
        }
      }
    } on LumenisCoreException catch (error) {
      if (_disposed) return;
      if (error.statusCode == 409) {
        await loadContext(pending.conversationId);
        if (contextDraft?.conversationId == pending.conversationId &&
            contextDraft?.remote != null) {
          contextDraft!.issue = 'conflict';
        }
        _pendingContextSaves.remove(pending.conversationId);
      } else if (_readDenied(error.statusCode)) {
        await loadContext(pending.conversationId, replaceLocal: false);
        if (contextDraft?.conversationId == pending.conversationId &&
            contextDraft?.saved != null) {
          contextDraft!.issue = error.statusCode == 401
              ? 'authentication'
              : 'permission';
        }
        _pendingContextSaves.remove(pending.conversationId);
      } else if (!_isOutcomeUnknown(error)) {
        _pendingContextSaves.remove(pending.conversationId);
        if (contextDraft?.conversationId == pending.conversationId) {
          contextDraft!.issue = error.statusCode == 400
              ? 'invalid'
              : 'save_error';
        }
      } else if (contextDraft?.conversationId == pending.conversationId) {
        contextDraft!.issue = 'save_unknown';
      }
    } catch (_) {
      if (!_disposed &&
          contextDraft?.conversationId == pending.conversationId) {
        contextDraft!.issue = 'save_unknown';
      }
    } finally {
      if (!_disposed && session?.conversationId == pending.conversationId) {
        session!.saving = false;
        _notify();
      }
    }
  }

  Future<void> searchSources(
    String conversationId,
    String query, {
    bool more = false,
  }) async {
    final search = sourceSearch;
    final normalized = more ? search.submittedQuery : query.trim();
    final repository = this.repository;
    if (_disposed || search.busy || repository is! Ai01ConversationSources) {
      return;
    }
    final sourceRepository = repository as Ai01ConversationSources;
    if (normalized == null ||
        normalized.isEmpty ||
        (more &&
            (search.nextOffset == null ||
                search.conversationId != conversationId))) {
      return;
    }
    final generation = ++_sourceGeneration;
    search.busy = true;
    search.issue = null;
    search.preview = null;
    search.conversationId = conversationId;
    _notify();
    try {
      final result = await sourceRepository.sourceQuery(conversationId, {
        'query': normalized,
        'limit': '12',
        if (more) 'offset': '${search.nextOffset}',
        if (more && search.sourceSnapshot != null)
          'snapshot': search.sourceSnapshot!,
      });
      if (_disposed || generation != _sourceGeneration) return;
      final page = result['search'];
      if (result['ok'] != true ||
          page is! Map ||
          page['records'] is! List ||
          page['has_more'] is! bool ||
          page['verification_complete'] is! bool) {
        throw const FormatException('Invalid source search.');
      }
      final records = (page['records'] as List)
          .map(_validateSource)
          .toList(growable: false);
      final next = page['next_offset'];
      if (page['has_more'] == true && next is! int) {
        throw const FormatException('Invalid source cursor.');
      }
      final retrieval = page['retrieval'];
      search.sourceSnapshot = retrieval is Map
          ? retrieval['source_snapshot_sha256'] as String?
          : null;
      if (more) {
        search.records.addAll(records);
      } else {
        search.records
          ..clear()
          ..addAll(records);
      }
      search.nextOffset = page['has_more'] == true ? next as int : null;
      search.submittedQuery = normalized;
      search.incomplete = page['verification_complete'] != true;
      if (search.incomplete) search.issue = 'incomplete';
    } catch (error) {
      if (_disposed || generation != _sourceGeneration) return;
      if (error is LumenisCoreException && _readDenied(error.statusCode)) {
        search.records.clear();
        search.preview = null;
        search.nextOffset = null;
        search.issue = 'restricted';
      } else if (error is LumenisCoreException && error.statusCode == 409) {
        search.records.clear();
        search.nextOffset = null;
        search.sourceSnapshot = null;
        search.issue = 'sources_changed';
      } else {
        search.issue = 'read_failed';
      }
    } finally {
      if (!_disposed && generation == _sourceGeneration) {
        search.busy = false;
        _notify();
      }
    }
  }

  Future<void> previewSource(
    String conversationId,
    Map<String, dynamic> record, {
    int start = 0,
  }) async {
    final search = sourceSearch;
    final repository = this.repository;
    if (_disposed || search.busy || repository is! Ai01ConversationSources) {
      return;
    }
    final sourceRepository = repository as Ai01ConversationSources;
    if (record['state'] != 'available' ||
        search.conversationId != conversationId) {
      return;
    }
    final count = record['character_count'];
    if (count is! int || start < 0 || start > count) return;
    final generation = ++_sourceGeneration;
    search.busy = true;
    search.issue = null;
    search.preview = null;
    _notify();
    try {
      final reference = Map<String, dynamic>.from(record['reference'] as Map)
        ..['start'] = start
        ..['end'] = (start + 64000).clamp(start, count);
      final response = await sourceRepository.sourceQuery(conversationId, {
        'source_reference': jsonEncode(reference),
      });
      if (_disposed || generation != _sourceGeneration) return;
      if (response['ok'] != true) {
        throw const FormatException('Invalid source preview.');
      }
      search.preview = _validateSource(response['source_preview']);
    } catch (error) {
      if (_disposed || generation != _sourceGeneration) return;
      if (error is LumenisCoreException && _readDenied(error.statusCode)) {
        search.records.clear();
        search.preview = null;
        search.nextOffset = null;
        search.issue = 'restricted';
      } else if (error is LumenisCoreException && error.statusCode == 409) {
        search.records.clear();
        search.preview = null;
        search.nextOffset = null;
        search.sourceSnapshot = null;
        search.issue = 'sources_changed';
      } else {
        search.issue = 'read_failed';
      }
    } finally {
      if (!_disposed && generation == _sourceGeneration) {
        search.busy = false;
        _notify();
      }
    }
  }

  Map<String, dynamic>? adoptSourcePreview({
    int? selectionStart,
    int? selectionEnd,
  }) {
    final preview = sourceSearch.preview;
    if (_disposed ||
        sourceSearch.busy ||
        preview == null ||
        preview['state'] != 'available') {
      return null;
    }
    final reference = Map<String, dynamic>.from(preview['reference'] as Map);
    final text = preview['text'] as String;
    final start = reference['start'] as int;
    if (selectionStart != null &&
        selectionEnd != null &&
        selectionStart >= 0 &&
        selectionEnd > selectionStart &&
        selectionEnd <= text.length) {
      reference['start'] =
          start + text.substring(0, selectionStart).runes.length;
      reference['end'] = start + text.substring(0, selectionEnd).runes.length;
    }
    return {...preview, 'reference': reference};
  }

  void clearSourceSearch() {
    _sourceGeneration++;
    sourceSearch
      ..conversationId = null
      ..submittedQuery = null
      ..sourceSnapshot = null
      ..records.clear()
      ..preview = null
      ..nextOffset = null
      ..busy = false
      ..incomplete = false
      ..issue = null;
    _notify();
  }

  static Map<String, dynamic> _validateSource(Object? raw) {
    if (raw is! Map || raw['reference'] is! Map || raw['state'] is! String) {
      throw const FormatException('Invalid source.');
    }
    final item = Map<String, dynamic>.from(raw);
    if (item['state'] == 'available' &&
        (item['text'] is! String ||
            item['title'] is! String ||
            item['offset_unit'] != 'unicode_codepoint' ||
            item['character_count'] is! int)) {
      throw const FormatException('Invalid source text.');
    }
    return item;
  }

  static Map<String, dynamic> _copyContextValue(Map<String, dynamic> value) {
    final copy = Map<String, dynamic>.from(value);
    if (copy.length != 5 ||
        copy['goal'] is! String ||
        copy['draft'] is! String ||
        ['constraints', 'decisions', 'excluded_turn_ids'].any(
          (key) =>
              copy[key] is! List ||
              (copy[key] as List).any((item) => item is! String),
        )) {
      throw const FormatException('Invalid conversation context.');
    }
    return {
      'goal': copy['goal'],
      'constraints': List<String>.from(copy['constraints'] as List),
      'draft': copy['draft'],
      'decisions': List<String>.from(copy['decisions'] as List),
      'excluded_turn_ids': List<String>.from(copy['excluded_turn_ids'] as List),
    };
  }

  void _applyContextDraft(
    Ai01ConversationContextDraft session,
    Ai01ConversationContext saved,
  ) {
    session
      ..saved = saved
      ..remote = null
      ..value = _copyContextValue(saved.value)
      ..sourceReferences = saved.sourceReferences
          .map((source) => Map<String, dynamic>.from(source))
          .toList(growable: false)
      ..issue = null;
    if (saved.turn case final Ai01ConversationTurn turn) {
      applyContextMutation(
        Ai01ConversationMutation(
          turn: turn,
          revision: saved.revision,
          idempotentHit: true,
        ),
      );
    }
  }

  void _clearContextDraft(Ai01ConversationContextDraft session) {
    session
      ..saved = null
      ..remote = null
      ..value = _emptyConversationContext()
      ..sourceReferences = [];
  }

  bool _contextMatches(
    Ai01ConversationContext context,
    _PendingConversationContextSave pending,
  ) {
    final expected = _copyContextValue(pending.value);
    final actual = _copyContextValue(context.value);
    final excluded = Set<String>.from(actual['excluded_turn_ids'] as List);
    if (!excluded.containsAll(expected['excluded_turn_ids'] as List<String>)) {
      return false;
    }
    expected['excluded_turn_ids'] = actual['excluded_turn_ids'];
    return context.conversationId == pending.conversationId &&
        _contextSignature(actual) == _contextSignature(expected) &&
        _sourceSignature(context.sourceReferences) ==
            _sourceSignature(pending.sourceReferences);
  }

  void _completeContextSave(
    _PendingConversationContextSave pending,
    Ai01ConversationContext readback,
  ) {
    _pendingContextSaves.remove(pending.conversationId);
    final session = contextDraft;
    if (session == null || session.conversationId != pending.conversationId) {
      return;
    }
    final localStillMatches =
        _contextSignature(session.value) == _contextSignature(pending.value) &&
        _sourceSignature(session.sourceReferences) ==
            _sourceSignature(pending.sourceReferences);
    session
      ..saved = readback
      ..remote = null
      ..issue = localStillMatches ? 'saved' : null;
    if (localStillMatches) {
      session
        ..value = _copyContextValue(readback.value)
        ..sourceReferences = readback.sourceReferences
            .map((source) => Map<String, dynamic>.from(source))
            .toList(growable: false);
    } else {
      session.value['excluded_turn_ids'] = <String>{
        ...List<String>.from(session.value['excluded_turn_ids'] as List),
        ...List<String>.from(readback.value['excluded_turn_ids'] as List),
      }.toList();
    }
    if (readback.turn case final Ai01ConversationTurn turn) {
      applyContextMutation(
        Ai01ConversationMutation(
          turn: turn,
          revision: readback.revision,
          idempotentHit: true,
        ),
      );
    }
    _notify();
  }

  static bool _readDenied(int? status) =>
      const {401, 403, 404, 410}.contains(status);

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
    if (selectedId != conversationId) {
      _contextGeneration++;
      contextDraft = null;
      clearSourceSearch();
    }
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

  /// Creates a persistent conversation when the current task has no identity,
  /// then appends the user's text through the same conversation owner.
  ///
  /// If an earlier creation had an uncertain outcome, a caller must explicitly
  /// acknowledge that unresolved creation before another identity is made.
  Future<bool> sendToCurrentOrCreate(
    String text, {
    required VoidCallback onPersisted,
    bool acknowledgeUnresolvedCreation = false,
  }) async {
    if (_disposed || busy || text.trim().isEmpty) return false;
    if (selectedId == null || detail?.id != selectedId) {
      if (creatingUnknown && !acknowledgeUnresolvedCreation) return false;
      await createConversation(
        acknowledgeUnresolvedPrevious: acknowledgeUnresolvedCreation,
      );
    }
    if (_disposed || !canSend) return false;
    return send(text, onPersisted: onPersisted);
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
    _contextGeneration++;
    contextDraft = null;
    clearSourceSearch();
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
      if (status == null) return 'offline';
      return switch (status) {
        401 => 'authentication',
        403 => 'permission',
        409 => 'conflict',
        400 => 'invalid',
        >= 500 => 'server',
        _ => 'unknown',
      };
    }
    return error is FormatException ? 'invalid_response' : 'offline';
  }

  void _notify() {
    if (!_disposed) notifyListeners();
  }

  @override
  void dispose() {
    _disposed = true;
    _generation++;
    _contextGeneration++;
    _sourceGeneration++;
    _pendingContextSaves.clear();
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
