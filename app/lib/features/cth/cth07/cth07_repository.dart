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
  final List<num?> values;
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
      (state == Cth07DataState.ready || state == Cth07DataState.partial) &&
      labels.isNotEmpty &&
      series.isNotEmpty;
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
    final definition = _trendDefinition(response);
    final labels = _strings(chart?['labels']);
    final rawSeries = _maps(chart?['series']);
    final series = rawSeries
        .map(_series)
        .whereType<Cth07Series>()
        .toList(growable: false);
    final truth = _map(response['truth']);
    final metadata = _map(response['trend_metadata']) ?? _map(truth?['trend']);
    final metrics = _map(response['temporal_metrics']);
    final binding = _map(
      context.isGlobal ? response['global_binding'] : response['focus_binding'],
    );
    final metricsBinding = _map(metrics?['binding']);
    final temporalDays = _maps(metrics?['days']);
    final snapshotMatches = _snapshotMatches(
      chart: chart,
      metadata: metadata,
      metrics: metrics,
      binding: binding,
      metricsBinding: metricsBinding,
      labels: labels,
      series: series,
      rawSeries: rawSeries,
      temporalDays: temporalDays,
      rawSeriesCount: chart?['series'] is List
          ? (chart!['series'] as List).length
          : -1,
    );
    final responseState = Cth07DataStateParser.parse(chart?['state']);
    if (responseState == Cth07DataState.error) {
      throw const FormatException('CTH-07 metric read returned an error.');
    }
    final valid =
        definition != null &&
        definition.isComplete &&
        _scopeMatches(context, definition.subject) &&
        snapshotMatches &&
        labels.isNotEmpty &&
        series.isNotEmpty &&
        series.every((item) => item.values.length == labels.length);

    return Cth07ScreenData(
      context: context,
      generatedAt: _text(response['generated_at']),
      labels: valid ? labels : const [],
      series: valid ? series : const [],
      state: valid
          ? responseState
          : responseState == Cth07DataState.empty
          ? Cth07DataState.empty
          : Cth07DataState.notCollected,
      definition: definition,
    );
  }

  Cth07TrendDefinition? _trendDefinition(Map<String, dynamic> response) {
    final truth = _map(response['truth']);
    final trend = _map(response['trend_metadata']) ?? _map(truth?['trend']);
    if (trend == null) return null;
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
    final parsed = <num?>[];
    for (final value in values) {
      if (value == null) {
        parsed.add(null);
      } else if (value is num && value.isFinite) {
        parsed.add(value);
      } else {
        return null;
      }
    }
    return Cth07Series(label: label, values: parsed);
  }

  bool _snapshotMatches({
    required Map<String, dynamic>? chart,
    required Map<String, dynamic>? metadata,
    required Map<String, dynamic>? metrics,
    required Map<String, dynamic>? binding,
    required Map<String, dynamic>? metricsBinding,
    required List<String> labels,
    required List<Cth07Series> series,
    required List<Map<String, dynamic>> rawSeries,
    required List<Map<String, dynamic>> temporalDays,
    required int rawSeriesCount,
  }) {
    if (chart == null ||
        metadata == null ||
        metrics == null ||
        binding == null ||
        metricsBinding == null) {
      return false;
    }
    if (!_sameBinding(binding, metricsBinding) ||
        metrics['state'] != chart['state']) {
      return false;
    }
    final recipe = _text(metadata['recipe']);
    final snapshotHash = _text(metadata['snapshot_sha256']);
    if (recipe.isEmpty ||
        recipe != metrics['recipe'] ||
        !RegExp(r'^[0-9a-fA-F]{64}$').hasMatch(snapshotHash) ||
        snapshotHash != metrics['snapshot_sha256']) {
      return false;
    }
    if (rawSeriesCount != series.length ||
        labels.length != temporalDays.length ||
        series.isEmpty ||
        series.any((item) => item.values.length != labels.length)) {
      return false;
    }
    for (var index = 0; index < labels.length; index++) {
      if (temporalDays[index]['date'] != labels[index]) return false;
    }
    final seenMetrics = <String>{};
    for (var seriesIndex = 0; seriesIndex < series.length; seriesIndex++) {
      final item = series[seriesIndex];
      final source = rawSeries[seriesIndex];
      if (_text(source['name'] ?? source['label']) != item.label) return false;
      final metric = _text(source['metric']);
      if (metric.isEmpty || !seenMetrics.add(metric)) return false;
      for (var index = 0; index < labels.length; index++) {
        final point = _map(temporalDays[index][metric]);
        if (point == null || point['value'] != item.values[index]) return false;
      }
    }
    return true;
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
    return _bindingMatches(binding, context);
  }

  static bool _bindingMatches(
    Map<String, dynamic>? binding,
    Cth07Context context,
  ) {
    if (binding == null ||
        binding['contract'] != 'lumenis.scope-read-binding.v1' ||
        binding['applied'] != true ||
        binding['domain_id'] != 'CTH' ||
        binding['product_id'] != 'CTH' ||
        binding['read_allowed'] != true ||
        binding['scope_verified'] != true ||
        binding['canonical_scope'] !=
            (context.isGlobal ? 'GLOBAL_ALL' : 'FOCUS')) {
      return false;
    }
    final policy = binding['policy'];
    final actorScope = binding['actor_scope'];
    if (!((policy == 'actor-exact-scope-v1' && actorScope == 'authenticated') ||
        (policy == 'local-workspace-read-v1' &&
            actorScope == 'anonymous_read'))) {
      return false;
    }
    if (context.isGlobal) {
      final expectedGrant = policy == 'actor-exact-scope-v1';
      return binding['subject_id'] == null &&
          binding['global_all_granted'] == expectedGrant;
    }
    return binding['subject_id'] == context.subjectId &&
        binding['global_all_granted'] != true &&
        binding['global_all_granted'] == false;
  }

  static bool _sameBinding(
    Map<String, dynamic> left,
    Map<String, dynamic> right,
  ) {
    if (left.length != right.length) return false;
    for (final entry in left.entries) {
      if (!right.containsKey(entry.key) ||
          !_deepEquals(entry.value, right[entry.key])) {
        return false;
      }
    }
    return true;
  }

  static bool _deepEquals(Object? left, Object? right) {
    if (left is Map && right is Map) {
      if (left.length != right.length) return false;
      for (final entry in left.entries) {
        if (!right.containsKey(entry.key) ||
            !_deepEquals(entry.value, right[entry.key])) {
          return false;
        }
      }
      return true;
    }
    if (left is List && right is List) {
      if (left.length != right.length) return false;
      for (var index = 0; index < left.length; index++) {
        if (!_deepEquals(left[index], right[index])) return false;
      }
      return true;
    }
    return left == right;
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

  static List<String> _strings(Object? value) {
    if (value is! List ||
        value.any((item) => item is! String || item.trim().isEmpty)) {
      return const [];
    }
    return value.map((item) => (item as String).trim()).toList(growable: false);
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
