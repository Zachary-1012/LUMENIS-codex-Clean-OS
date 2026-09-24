import '../../../core/lumenis_core_client.dart';

enum Cth07DataState {
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

extension Cth07DataStateParser on Cth07DataState {
  static Cth07DataState parse(Object? value) => switch (value) {
    'ready' => Cth07DataState.ready,
    'empty' => Cth07DataState.empty,
    'notcollected' => Cth07DataState.notCollected,
    'offline' => Cth07DataState.offline,
    'stale' => Cth07DataState.stale,
    'partial' => Cth07DataState.partial,
    'blocked' => Cth07DataState.blocked,
    'error' => Cth07DataState.error,
    _ => Cth07DataState.unknown,
  };
}

class Cth07Context {
  const Cth07Context({required this.mode, this.subjectId, this.displayName});

  final String mode;
  final String? subjectId;
  final Map<String, String>? displayName;

  bool get isGlobal => mode == 'GLOBAL_ALL';
}

class Cth07TrendDefinition {
  const Cth07TrendDefinition({
    required this.numerator,
    required this.denominator,
    required this.timeWindow,
    required this.subject,
    required this.source,
    required this.freshness,
  });

  final String numerator;
  final String denominator;
  final String timeWindow;
  final String subject;
  final String source;
  final String freshness;

  bool get isComplete =>
      numerator.isNotEmpty &&
      denominator.isNotEmpty &&
      timeWindow.isNotEmpty &&
      subject.isNotEmpty &&
      source.isNotEmpty &&
      freshness.isNotEmpty;
}

class Cth07Series {
  const Cth07Series({required this.label, required this.values});

  final String label;
  final List<num> values;
}

class Cth07ScreenData {
  const Cth07ScreenData({
    required this.context,
    required this.generatedAt,
    required this.labels,
    required this.series,
    required this.state,
    required this.definition,
  });

  final Cth07Context context;
  final String generatedAt;
  final List<String> labels;
  final List<Cth07Series> series;
  final Cth07DataState state;
  final Cth07TrendDefinition? definition;

  bool get trendAvailable =>
      state == Cth07DataState.ready && labels.isNotEmpty && series.isNotEmpty;
}

enum Cth07BlockReason { contextUnavailable, pageNotBound, focusNotBound }

class Cth07ContextUnavailable implements Exception {
  const Cth07ContextUnavailable(this.reason);

  final Cth07BlockReason reason;
}

abstract interface class Cth07Repository {
  Future<Cth07ScreenData> load();
}

class CoreCth07Repository implements Cth07Repository {
  const CoreCth07Repository({required this._client});

  final LumenisCoreClient _client;

  @override
  Future<Cth07ScreenData> load() async {
    final contextResponse = await _client.settingsContext();
    final context = _parseContext(contextResponse);
    if (context == null) {
      throw const Cth07ContextUnavailable(Cth07BlockReason.contextUnavailable);
    }

    final response = await _client.screen('CTH-07');
    if (response['ok'] != true || response['screen'] != 'CTH-07') {
      throw const FormatException(
        'CTH-07 response does not match its contract.',
      );
    }
    if (response['bound'] != true) {
      throw const Cth07ContextUnavailable(Cth07BlockReason.pageNotBound);
    }
    if (!_hasAuthorizedBinding(response, context)) {
      throw Cth07ContextUnavailable(
        context.isGlobal
            ? Cth07BlockReason.pageNotBound
            : Cth07BlockReason.focusNotBound,
      );
    }
    return _decode(response, context);
  }

  Cth07ScreenData _decode(Map<String, dynamic> response, Cth07Context context) {
    final sections = _maps(response['sections']);
    final chart = _firstSection(sections, 'chart');
    final definition = _trendDefinition(response, context);
    final labels = _strings(chart?['labels']);
    final series = _maps(
      chart?['series'],
    ).map(_series).whereType<Cth07Series>().toList(growable: false);
    final valid =
        definition != null &&
        definition.isComplete &&
        _scopeMatches(context, definition.subject) &&
        _projectionMatches(chart?['projection'], context) &&
        labels.isNotEmpty &&
        series.isNotEmpty &&
        series.every((item) => item.values.length == labels.length);

    return Cth07ScreenData(
      context: context,
      generatedAt: _text(response['generated_at']),
      labels: valid ? labels : const [],
      series: valid ? series : const [],
      state: valid
          ? Cth07DataState.ready
          : Cth07DataStateParser.parse(chart?['state']) == Cth07DataState.empty
          ? Cth07DataState.empty
          : Cth07DataState.notCollected,
      definition: definition,
    );
  }

  Cth07TrendDefinition? _trendDefinition(
    Map<String, dynamic> response,
    Cth07Context context,
  ) {
    final truth = _map(response['truth']);
    final trend = _map(response['trend_metadata']) ?? _map(truth?['trend']);
    if (trend == null || !_projectionMatches(trend['projection'], context)) {
      return null;
    }
    return Cth07TrendDefinition(
      numerator: _text(trend['numerator']),
      denominator: _text(trend['denominator']),
      timeWindow: _text(trend['time_window'] ?? trend['window']),
      subject: _text(trend['subject'] ?? trend['subject_id']),
      source: _safeSource(_text(trend['source'])),
      freshness: _text(trend['freshness']),
    );
  }

  Cth07Series? _series(Map<String, dynamic> record) {
    final label = _text(record['label'] ?? record['name']);
    final values = record['data'] ?? record['values'];
    if (label.isEmpty || values is! List) return null;
    final parsed = values
        .whereType<num>()
        .where((value) => value.isFinite)
        .toList(growable: false);
    if (parsed.length != values.length) return null;
    return Cth07Series(label: label, values: parsed);
  }

  static bool _scopeMatches(Cth07Context context, String subject) {
    final value = subject.trim().toLowerCase();
    if (value.isEmpty) return false;
    if (context.isGlobal) {
      return value == 'global/all' ||
          value == 'global_all' ||
          value == 'global';
    }
    return value == context.subjectId!.toLowerCase();
  }

  static bool _hasAuthorizedBinding(
    Map<String, dynamic> response,
    Cth07Context context,
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

  static bool _projectionMatches(Object? value, Cth07Context context) {
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

  static Cth07Context? _parseContext(Map<String, dynamic> response) {
    if (response['ok'] != true ||
        response['contract'] != 'lumenis.context.v1') {
      return null;
    }
    final context = _map(response['context']);
    if (context == null) return null;
    final mode = _text(context['mode']);
    final domain = _text(context['domain_id']);
    if (mode == 'GLOBAL_ALL') {
      return Cth07Context(
        mode: mode,
        displayName: _displayName(context['display_name']),
      );
    }
    if (mode != 'FOCUS' || domain != 'CTH') return null;
    final subjectId = _text(context['subject_id']);
    if (subjectId.isEmpty) return null;
    return Cth07Context(
      mode: mode,
      subjectId: subjectId,
      displayName: _displayName(context['display_name']),
    );
  }

  static String _safeSource(String value) {
    final lowered = value.toLowerCase();
    const forbidden = [
      'api',
      'database',
      'core',
      'evidence',
      'permission',
      'owner',
      '/',
      '\\',
    ];
    return forbidden.any(lowered.contains) ? '' : value;
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

  static List<String> _strings(Object? value) => value is List
      ? value
            .whereType<String>()
            .map((item) => item.trim())
            .where((item) => item.isNotEmpty)
            .toList(growable: false)
      : const [];

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
