import '../../../core/lumenis_core_client.dart';

enum Cth04DataState {
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

extension Cth04DataStateParser on Cth04DataState {
  static Cth04DataState parse(Object? value) => switch (value) {
    'ready' => Cth04DataState.ready,
    'empty' => Cth04DataState.empty,
    'notcollected' => Cth04DataState.notCollected,
    'offline' => Cth04DataState.offline,
    'stale' => Cth04DataState.stale,
    'partial' => Cth04DataState.partial,
    'blocked' => Cth04DataState.blocked,
    'error' => Cth04DataState.error,
    _ => Cth04DataState.unknown,
  };
}

class Cth04Context {
  const Cth04Context({required this.mode, this.subjectId, this.displayName});

  final String mode;
  final String? subjectId;
  final Map<String, String>? displayName;

  bool get isGlobal => mode == 'GLOBAL_ALL';
}

class Cth04Event {
  const Cth04Event({
    required this.title,
    required this.date,
    required this.time,
    required this.description,
    required this.level,
    required this.tags,
  });

  final String title;
  final String date;
  final String time;
  final String description;
  final String level;
  final List<String> tags;
}

class Cth04Graph {
  const Cth04Graph({
    required this.state,
    required this.nodes,
    required this.edgeCount,
  });

  final Cth04DataState state;
  final List<String> nodes;
  final int edgeCount;

  bool get available =>
      state == Cth04DataState.ready && nodes.isNotEmpty && edgeCount > 0;
}

class Cth04ScreenData {
  const Cth04ScreenData({
    required this.context,
    required this.generatedAt,
    required this.events,
    required this.eventsState,
    required this.graph,
  });

  final Cth04Context context;
  final String generatedAt;
  final List<Cth04Event> events;
  final Cth04DataState eventsState;
  final Cth04Graph graph;
}

enum Cth04BlockReason { contextUnavailable, pageNotBound, focusNotBound }

class Cth04ContextUnavailable implements Exception {
  const Cth04ContextUnavailable(this.reason);

  final Cth04BlockReason reason;
}

abstract interface class Cth04Repository {
  Future<Cth04ScreenData> load();
}

class CoreCth04Repository implements Cth04Repository {
  const CoreCth04Repository({required this._client});

  final LumenisCoreClient _client;

  @override
  Future<Cth04ScreenData> load() async {
    final contextResponse = await _client.settingsContext();
    final context = _parseContext(contextResponse);
    if (context == null) {
      throw const Cth04ContextUnavailable(Cth04BlockReason.contextUnavailable);
    }

    final response = await _client.screen('CTH-04');
    if (response['ok'] != true || response['screen'] != 'CTH-04') {
      throw const FormatException(
        'CTH-04 response does not match its contract.',
      );
    }
    if (response['bound'] != true) {
      throw const Cth04ContextUnavailable(Cth04BlockReason.pageNotBound);
    }
    if (!_hasAuthorizedBinding(response, context)) {
      throw Cth04ContextUnavailable(
        context.isGlobal
            ? Cth04BlockReason.pageNotBound
            : Cth04BlockReason.focusNotBound,
      );
    }
    return _decode(response, context);
  }

  Cth04ScreenData _decode(Map<String, dynamic> response, Cth04Context context) {
    final sections = _maps(response['sections']);
    final eventSection = _firstSection(sections, 'events');
    final graphSection = _firstSection(sections, 'graph');
    final graphMetric = _firstMetric(
      _firstSection(sections, 'kpis'),
      'cth04.graph',
    );
    final graphAuthorized = graphSection != null
        ? _projectionMatches(graphSection['projection'], context)
        : _projectionMatches(graphMetric?['projection'], context);
    final graphNodes = graphAuthorized
        ? (_maps(graphSection?['nodes'])
              .map(
                (node) => _text(node['label'] ?? node['title'] ?? node['name']),
              )
              .where((label) => label.isNotEmpty)
              .toList(growable: false))
        : const <String>[];
    final graphEdges = graphAuthorized
        ? (graphSection == null ? null : graphSection['edges'])
        : null;

    final rawEvents = _maps(eventSection?['items']);
    final events = rawEvents
        .where((event) => _rowIsAuthorized(event, context))
        .map(_event)
        .whereType<Cth04Event>()
        .toList(growable: false);
    final rawEventState = Cth04DataStateParser.parse(eventSection?['state']);

    final graphState =
        !graphAuthorized && (graphSection != null || graphMetric != null)
        ? Cth04DataState.blocked
        : graphSection == null
        ? Cth04DataStateParser.parse(graphMetric?['state'])
        : Cth04DataStateParser.parse(graphSection['state']);
    final edgeCount = graphEdges is List
        ? graphEdges.length
        : graphAuthorized
        ? _number(graphMetric?['value'])?.toInt() ?? 0
        : 0;

    return Cth04ScreenData(
      context: context,
      generatedAt: _text(response['generated_at']),
      events: events,
      eventsState: rawEvents.isNotEmpty && events.length != rawEvents.length
          ? Cth04DataState.blocked
          : rawEventState,
      graph: Cth04Graph(
        state: graphState,
        nodes: graphNodes,
        edgeCount: edgeCount,
      ),
    );
  }

  Cth04Event? _event(Map<String, dynamic> record) {
    final title = _text(record['title']);
    if (title.isEmpty) return null;
    return Cth04Event(
      title: title,
      date: _text(record['date']),
      time: _text(record['time']),
      description: _text(record['desc'] ?? record['summary']),
      level: _text(record['level'] ?? record['risk']),
      tags: (record['tags'] is List ? record['tags'] as List : const [])
          .whereType<String>()
          .map((tag) => tag.trim())
          .where((tag) => tag.isNotEmpty)
          .toList(growable: false),
    );
  }

  static bool _hasAuthorizedBinding(
    Map<String, dynamic> response,
    Cth04Context context,
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
      return binding['global_all_granted'] == true &&
          _projectionMatches(binding['projection'], context);
    }
    return binding['subject_id'] == context.subjectId &&
        binding['global_all_granted'] != true &&
        _projectionMatches(binding['projection'], context);
  }

  static bool _rowIsAuthorized(Map<String, dynamic> row, Cth04Context context) {
    final scopeMatches = context.isGlobal
        ? row['scope_mode'] == 'GLOBAL_ALL' &&
              row['canonical_scope'] == 'GLOBAL_ALL'
        : row['scope_mode'] == 'FOCUS' &&
              row['canonical_scope'] == 'FOCUS' &&
              row['subject_id'] == context.subjectId;
    return scopeMatches &&
        row['read_allowed'] == true &&
        _projectionMatches(row['projection'], context);
  }

  static bool _projectionMatches(Object? value, Cth04Context context) {
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
      if (scope['global_all_granted'] != true ||
          _text(scope['subject_id']).isNotEmpty) {
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

  static Map<String, dynamic>? _firstMetric(
    Map<String, dynamic>? section,
    String id,
  ) {
    for (final item in _maps(section?['items'])) {
      if (item['id'] == id) return item;
    }
    return null;
  }

  static Cth04Context? _parseContext(Map<String, dynamic> response) {
    if (response['ok'] != true ||
        response['contract'] != 'lumenis.context.v1') {
      return null;
    }
    final context = _map(response['context']);
    if (context == null) return null;
    final mode = _text(context['mode']);
    final domain = _text(context['domain_id']);
    if (mode == 'GLOBAL_ALL') {
      return Cth04Context(
        mode: mode,
        displayName: _displayName(context['display_name']),
      );
    }
    if (mode != 'FOCUS' || domain != 'CTH') return null;
    final subjectId = _text(context['subject_id']);
    if (subjectId.isEmpty) return null;
    return Cth04Context(
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
