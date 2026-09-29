import '../../../core/lumenis_core_client.dart';

enum Cth03DataState {
  ready,
  empty,
  notCollected,
  offline,
  stale,
  partial,
  blocked,
  error,
  unknown,
}

extension Cth03DataStateCopy on Cth03DataState {
  static Cth03DataState parse(Object? value) => switch (value) {
    'ready' => Cth03DataState.ready,
    'empty' => Cth03DataState.empty,
    'notcollected' => Cth03DataState.notCollected,
    'offline' => Cth03DataState.offline,
    'stale' => Cth03DataState.stale,
    'partial' => Cth03DataState.partial,
    'blocked' => Cth03DataState.blocked,
    'error' => Cth03DataState.error,
    _ => Cth03DataState.unknown,
  };
}

class Cth03Context {
  const Cth03Context({required this.mode, this.subjectId, this.displayName});

  final String mode;
  final String? subjectId;
  final Map<String, String>? displayName;

  bool get isGlobal => mode == 'GLOBAL_ALL';
}

class Cth03Metric {
  const Cth03Metric({required this.id, required this.state, this.value});

  final String id;
  final Cth03DataState state;
  final num? value;

  bool get hasValue => state == Cth03DataState.ready && value != null;
}

class Cth03Channel {
  const Cth03Channel({
    required this.name,
    required this.status,
    this.detail = '',
  });

  final String name;
  final String status;
  final String detail;
}

class Cth03Record {
  const Cth03Record({
    required this.date,
    required this.title,
    required this.channel,
    required this.sentiment,
    required this.risk,
  });

  final String date;
  final String title;
  final String channel;
  final String sentiment;
  final String risk;
}

class Cth03ScreenData {
  const Cth03ScreenData({
    required this.context,
    required this.generatedAt,
    required this.recentCount,
    required this.negativeCount,
    required this.channels,
    required this.records,
    required this.recordState,
  });

  final Cth03Context context;
  final String generatedAt;
  final Cth03Metric recentCount;
  final Cth03Metric negativeCount;
  final List<Cth03Channel> channels;
  final List<Cth03Record> records;
  final Cth03DataState recordState;
}

enum Cth03BlockReason { contextUnavailable, pageNotBound, focusNotBound }

class Cth03ContextUnavailable implements Exception {
  const Cth03ContextUnavailable(this.reason);

  final Cth03BlockReason reason;
}

abstract interface class Cth03Repository {
  Future<Cth03ScreenData> load();
}

class CoreCth03Repository implements Cth03Repository {
  const CoreCth03Repository({required this._client});

  final LumenisCoreClient _client;

  @override
  Future<Cth03ScreenData> load() async {
    final contextResponse = await _client.settingsContext();
    final context = _parseContext(contextResponse);
    if (context == null) {
      throw const Cth03ContextUnavailable(Cth03BlockReason.contextUnavailable);
    }

    final response = await _client.screen('CTH-03');
    if (response['ok'] != true || response['screen'] != 'CTH-03') {
      throw const FormatException(
        'CTH-03 response does not match its contract.',
      );
    }
    if (response['bound'] != true) {
      throw const Cth03ContextUnavailable(Cth03BlockReason.pageNotBound);
    }

    // `bound` only describes route wiring. It is not proof that the response
    // was authorized for the active scope or that its Evidence is traceable.
    if (!_hasAuthorizedBinding(response, context)) {
      throw Cth03ContextUnavailable(
        context.isGlobal
            ? Cth03BlockReason.pageNotBound
            : Cth03BlockReason.focusNotBound,
      );
    }

    return _decode(response, context);
  }

  Cth03ScreenData _decode(Map<String, dynamic> response, Cth03Context context) {
    final sections = _maps(response['sections']);
    final binding = _map(
      context.isGlobal ? response['global_binding'] : response['focus_binding'],
    );
    final allowAnonymousGlobal =
        context.isGlobal && _isAnonymousGlobalRead(binding);
    final kpis = _firstSection(sections, 'kpis');
    final channels = _firstSection(sections, 'platforms');
    final stream = _firstSection(sections, 'table');

    final rawRecords = _maps(stream?['rows']);
    final records = rawRecords
        .where(
          (record) => _rowIsAuthorized(
            record,
            context,
            allowAnonymousGlobal: allowAnonymousGlobal,
          ),
        )
        .map(_record)
        .whereType<Cth03Record>()
        .toList(growable: false);
    final rawRecordState = Cth03DataStateCopy.parse(stream?['state']);

    return Cth03ScreenData(
      context: context,
      generatedAt: _text(response['generated_at']),
      recentCount: _metric(
        kpis,
        'cth03.recent',
        context,
        allowAnonymousGlobal: allowAnonymousGlobal,
      ),
      negativeCount: _metric(
        kpis,
        'cth03.negative',
        context,
        allowAnonymousGlobal: allowAnonymousGlobal,
      ),
      channels: _maps(channels?['items'])
          .where(
            (channel) => _projectionMatches(
              channel['projection'],
              context,
              allowAnonymousGlobal: allowAnonymousGlobal,
            ),
          )
          .map(_channel)
          .where((channel) => channel.name.isNotEmpty)
          .toList(growable: false),
      records: records,
      recordState: rawRecords.isNotEmpty && records.length != rawRecords.length
          ? Cth03DataState.blocked
          : rawRecordState,
    );
  }

  Cth03Metric _metric(
    Map<String, dynamic>? section,
    String id,
    Cth03Context context,
    {bool allowAnonymousGlobal = false}
  ) {
    final item = _maps(section?['items']).where((entry) => entry['id'] == id);
    if (item.isEmpty ||
        !_projectionMatches(
          item.first['projection'],
          context,
          allowAnonymousGlobal: allowAnonymousGlobal,
        )) {
      return Cth03Metric(id: id, state: Cth03DataState.unknown);
    }
    final record = item.first;
    final state = Cth03DataStateCopy.parse(record['state']);
    final value = _number(record['value']);
    return Cth03Metric(
      id: id,
      state: state == Cth03DataState.ready && value == null
          ? Cth03DataState.unknown
          : state,
      value: value,
    );
  }

  Cth03Channel _channel(Map<String, dynamic> record) => Cth03Channel(
    name: _text(record['platform'] ?? record['name']),
    status: _text(record['status'] ?? record['state']),
    detail: _text(record['schedule'] ?? record['detail']),
  );

  Cth03Record? _record(Map<String, dynamic> record) {
    final title = _text(record['title']);
    if (title.isEmpty) return null;
    return Cth03Record(
      date: _text(record['date'] ?? record['time']),
      title: title,
      channel: _text(record['platform'] ?? record['channel']),
      sentiment: _text(record['sentiment']),
      risk: _text(record['risk'] ?? record['level']),
    );
  }

  static bool _hasAuthorizedBinding(
    Map<String, dynamic> response,
    Cth03Context context,
  ) {
    final binding = _map(
      context.isGlobal ? response['global_binding'] : response['focus_binding'],
    );
    if (binding == null ||
        binding['applied'] != true ||
        binding['domain_id'] != 'CTH' ||
        binding['product_id'] != 'CTH' ||
        binding['read_allowed'] != true ||
        binding['canonical_scope'] !=
            (context.isGlobal ? 'GLOBAL_ALL' : 'FOCUS')) {
      return false;
    }
    if (context.isGlobal) {
      final allowAnonymousGlobal = _isAnonymousGlobalRead(binding);
      return (binding['global_all_granted'] == true ||
              allowAnonymousGlobal) &&
          _projectionMatches(
            binding['projection'],
            context,
            allowAnonymousGlobal: allowAnonymousGlobal,
          );
    }
    return binding['subject_id'] == context.subjectId &&
        binding['global_all_granted'] != true &&
        _projectionMatches(binding['projection'], context);
  }

  static bool _rowIsAuthorized(
    Map<String, dynamic> row,
    Cth03Context context, {
    bool allowAnonymousGlobal = false,
  }) {
    final scopeMatches = context.isGlobal
        ? row['scope_mode'] == 'GLOBAL_ALL' &&
              row['canonical_scope'] == 'GLOBAL_ALL'
        : row['scope_mode'] == 'FOCUS' &&
              row['canonical_scope'] == 'FOCUS' &&
              row['subject_id'] == context.subjectId;
    return scopeMatches &&
        row['read_allowed'] == true &&
        _projectionMatches(
          row['projection'],
          context,
          allowAnonymousGlobal: allowAnonymousGlobal,
        );
  }

  static bool _projectionMatches(
    Object? value,
    Cth03Context context, {
    bool allowAnonymousGlobal = false,
  }) {
    final projection = _map(value);
    if (projection == null ||
        projection['contract'] != 'lumenis.shared.experience-row-projection' ||
        projection['version'] != 2 ||
        projection['read_allowed'] != true) {
      return false;
    }
    final scope = _map(projection['scope']);
    final expectedMode = context.isGlobal ? 'GLOBAL_ALL' : 'FOCUS';
    if (scope == null ||
        scope['mode'] != expectedMode ||
        scope['domain_id'] != 'CTH' ||
        scope['product_id'] != 'CTH') {
      return false;
    }
    if (context.isGlobal) {
      final granted = scope['global_all_granted'] == true;
      final anonymousProjection =
          allowAnonymousGlobal && _hasStoredSubjectProjection(projection);
      if ((!granted && !anonymousProjection) ||
          (granted && _text(scope['subject_id']).isNotEmpty)) {
        return false;
      }
    } else if (scope['subject_id'] != context.subjectId ||
        scope['global_all_granted'] == true) {
      return false;
    }

    final evidence = _map(projection['evidence']);
    final reference = _text(evidence?['canonical_reference']);
    final integrity = _map(projection['integrity']);
    final assurance = _text(integrity?['assurance']);
    final algorithm = _text(integrity?['algorithm']);
    final digest = _text(integrity?['digest']);
    final honestAssurance =
        assurance == 'writer-authenticated' ||
        assurance == 'content-integrity-only';
    final consistentAssurance =
        (assurance == 'writer-authenticated' && algorithm == 'hmac-sha256') ||
        (assurance == 'content-integrity-only' && algorithm == 'sha256');
    return reference.length <= 200 &&
        RegExp(r'^evidence:canonical:[A-Za-z0-9._:-]+$').hasMatch(reference) &&
        integrity?['integrity_version'] == 2 &&
        integrity?['verified'] == true &&
        integrity?['lineage_verified'] == true &&
        honestAssurance &&
        consistentAssurance &&
        RegExp(r'^[0-9a-fA-F]{64}$').hasMatch(digest);
  }

  static bool _isAnonymousGlobalRead(Map<String, dynamic>? binding) =>
      _text(binding?['actor_scope']) == 'anonymous_read' &&
      binding?['read_allowed'] == true &&
      binding?['scope_verified'] == true &&
      binding?['evidence_lineage'] == 'verified';

  static bool _hasStoredSubjectProjection(Map<String, dynamic> projection) {
    final storedScope = _map(projection['stored_scope']);
    return storedScope != null &&
        storedScope['global'] == false &&
        _text(storedScope['product_id']) == 'CTH' &&
        _text(storedScope['subject_id']).isNotEmpty;
  }

  static Cth03Context? _parseContext(Map<String, dynamic> response) {
    if (response['ok'] != true ||
        response['contract'] != 'lumenis.context.v1') {
      return null;
    }
    final context = _map(response['context']);
    if (context == null) return null;
    final mode = _text(context['mode']);
    final domain = _text(context['domain_id']);
    if (mode == 'GLOBAL_ALL') {
      return Cth03Context(
        mode: mode,
        displayName: _displayName(context['display_name']),
      );
    }
    if (mode != 'FOCUS' || domain != 'CTH') return null;
    final subjectId = _text(context['subject_id']);
    if (subjectId.isEmpty) return null;
    return Cth03Context(
      mode: mode,
      subjectId: subjectId,
      displayName: _displayName(context['display_name']),
    );
  }

  static Map<String, String>? _displayName(Object? value) {
    final map = _map(value);
    if (map == null) return null;
    final result = <String, String>{};
    for (final entry in map.entries) {
      final text = _text(entry.value);
      if (text.isNotEmpty) result[entry.key] = text;
    }
    return result.isEmpty ? null : result;
  }

  static Map<String, dynamic>? _firstSection(
    List<Map<String, dynamic>> sections,
    String type,
  ) {
    for (final section in sections) {
      if (section['type'] == type) return section;
    }
    return null;
  }

  static List<Map<String, dynamic>> _maps(Object? value) {
    if (value is! List) return const [];
    return value.map(_map).whereType<Map<String, dynamic>>().toList();
  }

  static Map<String, dynamic>? _map(Object? value) {
    if (value is Map<String, dynamic>) return value;
    if (value is! Map) return null;
    return value.map((key, value) => MapEntry('$key', value));
  }

  static num? _number(Object? value) =>
      value is num && value.isFinite ? value : null;

  static String _text(Object? value) => value is String ? value.trim() : '';
}
