import '../../../core/lumenis_core_client.dart';

enum Cth06DataState {
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

extension Cth06DataStateParser on Cth06DataState {
  static Cth06DataState parse(Object? value) => switch (value) {
    'ready' => Cth06DataState.ready,
    'empty' => Cth06DataState.empty,
    'notcollected' => Cth06DataState.notCollected,
    'offline' => Cth06DataState.offline,
    'stale' => Cth06DataState.stale,
    'partial' => Cth06DataState.partial,
    'blocked' => Cth06DataState.blocked,
    'error' => Cth06DataState.error,
    _ => Cth06DataState.unknown,
  };
}

enum Cth06Category { publicOpinion, customerFeedback, incident, unclassified }

extension Cth06CategoryCopy on Cth06Category {
  String get label => switch (this) {
    Cth06Category.publicOpinion => '公众意见',
    Cth06Category.customerFeedback => '顾客反馈',
    Cth06Category.incident => '已确认事件',
    Cth06Category.unclassified => '待分类反馈',
  };

  static Cth06Category parse(Object? value) {
    final text = value is String ? value.trim().toLowerCase() : '';
    if (text.contains('public') ||
        text.contains('opinion') ||
        text.contains('舆情')) {
      return Cth06Category.publicOpinion;
    }
    if (text.contains('customer') ||
        text.contains('feedback') ||
        text.contains('用户') ||
        text.contains('顾客')) {
      return Cth06Category.customerFeedback;
    }
    if (text.contains('incident') ||
        text.contains('event') ||
        text.contains('事件')) {
      return Cth06Category.incident;
    }
    return Cth06Category.unclassified;
  }
}

class Cth06Context {
  const Cth06Context({required this.mode, this.subjectId, this.displayName});

  final String mode;
  final String? subjectId;
  final Map<String, String>? displayName;

  bool get isGlobal => mode == 'GLOBAL_ALL';
}

class Cth06Feedback {
  const Cth06Feedback({
    required this.date,
    required this.channel,
    required this.summary,
    required this.sentiment,
    required this.category,
    required this.risk,
  });

  final String date;
  final String channel;
  final String summary;
  final String sentiment;
  final Cth06Category category;
  final String risk;
}

class Cth06ScreenData {
  const Cth06ScreenData({
    required this.context,
    required this.generatedAt,
    required this.items,
    required this.itemsState,
  });

  final Cth06Context context;
  final String generatedAt;
  final List<Cth06Feedback> items;
  final Cth06DataState itemsState;
}

enum Cth06BlockReason { contextUnavailable, pageNotBound, focusNotBound }

class Cth06ContextUnavailable implements Exception {
  const Cth06ContextUnavailable(this.reason);

  final Cth06BlockReason reason;
}

abstract interface class Cth06Repository {
  Future<Cth06ScreenData> load();
}

class CoreCth06Repository implements Cth06Repository {
  const CoreCth06Repository({required this._client});

  final LumenisCoreClient _client;

  @override
  Future<Cth06ScreenData> load() async {
    final contextResponse = await _client.settingsContext();
    final context = _parseContext(contextResponse);
    if (context == null) {
      throw const Cth06ContextUnavailable(Cth06BlockReason.contextUnavailable);
    }

    final response = await _client.screen('CTH-06');
    if (response['ok'] != true || response['screen'] != 'CTH-06') {
      throw const FormatException(
        'CTH-06 response does not match its contract.',
      );
    }
    if (response['bound'] != true) {
      throw const Cth06ContextUnavailable(Cth06BlockReason.pageNotBound);
    }
    if (!_hasAuthorizedBinding(response, context)) {
      throw Cth06ContextUnavailable(
        context.isGlobal
            ? Cth06BlockReason.pageNotBound
            : Cth06BlockReason.focusNotBound,
      );
    }
    return _decode(response, context);
  }

  Cth06ScreenData _decode(Map<String, dynamic> response, Cth06Context context) {
    final sections = _maps(response['sections']);
    final table = _firstSection(sections, 'table');
    final rawItems = _maps(table?['rows']);
    final items = rawItems
        .where((item) => _rowIsAuthorized(item, context))
        .map(_feedback)
        .whereType<Cth06Feedback>()
        .toList(growable: false);
    final rawItemsState = Cth06DataStateParser.parse(table?['state']);
    return Cth06ScreenData(
      context: context,
      generatedAt: _text(response['generated_at']),
      items: items,
      itemsState: rawItems.isNotEmpty && items.length != rawItems.length
          ? Cth06DataState.blocked
          : rawItemsState,
    );
  }

  Cth06Feedback? _feedback(Map<String, dynamic> record) {
    final summary = _text(record['summary'] ?? record['title']);
    if (summary.isEmpty) return null;
    return Cth06Feedback(
      date: _text(record['time'] ?? record['date']),
      channel: _text(record['channel'] ?? record['platform']),
      summary: summary,
      sentiment: _text(record['sentiment']),
      category: Cth06CategoryCopy.parse(
        record['category'] ?? record['cluster'] ?? record['kind'],
      ),
      risk: _text(record['risk'] ?? record['level']),
    );
  }

  static bool _hasAuthorizedBinding(
    Map<String, dynamic> response,
    Cth06Context context,
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

  static bool _rowIsAuthorized(Map<String, dynamic> row, Cth06Context context) {
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

  static bool _projectionMatches(Object? value, Cth06Context context) {
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

  static Cth06Context? _parseContext(Map<String, dynamic> response) {
    if (response['ok'] != true ||
        response['contract'] != 'lumenis.context.v1') {
      return null;
    }
    final context = _map(response['context']);
    if (context == null) return null;
    final mode = _text(context['mode']);
    final domain = _text(context['domain_id']);
    if (mode == 'GLOBAL_ALL') {
      return Cth06Context(
        mode: mode,
        displayName: _displayName(context['display_name']),
      );
    }
    if (mode != 'FOCUS' || domain != 'CTH') return null;
    final subjectId = _text(context['subject_id']);
    if (subjectId.isEmpty) return null;
    return Cth06Context(
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

  static List<Map<String, dynamic>> _maps(Object? value) => value is List
      ? value.map(_map).whereType<Map<String, dynamic>>().toList()
      : const [];

  static Map<String, dynamic>? _map(Object? value) {
    if (value is Map<String, dynamic>) return value;
    if (value is! Map) return null;
    return value.map((key, value) => MapEntry('$key', value));
  }

  static String _text(Object? value) => value is String ? value.trim() : '';
}
