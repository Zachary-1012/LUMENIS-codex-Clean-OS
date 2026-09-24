import '../../../core/lumenis_core_client.dart';

enum Cth05DataState {
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

extension Cth05DataStateParser on Cth05DataState {
  static Cth05DataState parse(Object? value) => switch (value) {
    'ready' => Cth05DataState.ready,
    'empty' => Cth05DataState.empty,
    'notcollected' => Cth05DataState.notCollected,
    'offline' => Cth05DataState.offline,
    'stale' => Cth05DataState.stale,
    'partial' => Cth05DataState.partial,
    'blocked' => Cth05DataState.blocked,
    'error' => Cth05DataState.error,
    _ => Cth05DataState.unknown,
  };
}

class Cth05Context {
  const Cth05Context({required this.mode, this.subjectId, this.displayName});

  final String mode;
  final String? subjectId;
  final Map<String, String>? displayName;

  bool get isGlobal => mode == 'GLOBAL_ALL';
}

class Cth05TrendDefinition {
  const Cth05TrendDefinition({
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

class Cth05CalendarDay {
  const Cth05CalendarDay({
    required this.label,
    required this.negative,
    required this.highRisk,
  });

  final String label;
  final num negative;
  final num highRisk;
}

class Cth05ScreenData {
  const Cth05ScreenData({
    required this.context,
    required this.generatedAt,
    required this.state,
    required this.days,
    required this.definition,
  });

  final Cth05Context context;
  final String generatedAt;
  final Cth05DataState state;
  final List<Cth05CalendarDay> days;
  final Cth05TrendDefinition? definition;

  bool get calendarAvailable =>
      state == Cth05DataState.ready && days.isNotEmpty;
}

enum Cth05BlockReason { contextUnavailable, pageNotBound, focusNotBound }

class Cth05ContextUnavailable implements Exception {
  const Cth05ContextUnavailable(this.reason);

  final Cth05BlockReason reason;
}

abstract interface class Cth05Repository {
  Future<Cth05ScreenData> load();
}

class CoreCth05Repository implements Cth05Repository {
  const CoreCth05Repository({required this._client});

  final LumenisCoreClient _client;

  @override
  Future<Cth05ScreenData> load() async {
    final contextResponse = await _client.settingsContext();
    final context = _parseContext(contextResponse);
    if (context == null) {
      throw const Cth05ContextUnavailable(Cth05BlockReason.contextUnavailable);
    }

    final response = await _client.screen('CTH-05');
    if (response['ok'] != true || response['screen'] != 'CTH-05') {
      throw const FormatException(
        'CTH-05 response does not match its contract.',
      );
    }
    if (response['bound'] != true) {
      throw const Cth05ContextUnavailable(Cth05BlockReason.pageNotBound);
    }
    if (!_hasAuthorizedBinding(response, context)) {
      throw Cth05ContextUnavailable(
        context.isGlobal
            ? Cth05BlockReason.pageNotBound
            : Cth05BlockReason.focusNotBound,
      );
    }
    return _decode(response, context);
  }

  Cth05ScreenData _decode(Map<String, dynamic> response, Cth05Context context) {
    final sections = _maps(response['sections']);
    final chart = _firstSection(sections, 'chart');
    final definition = _trendDefinition(response, context);
    final labels = _strings(chart?['labels']);
    final series = _maps(chart?['series']);
    final negative = _series(series, const ['negative', '负面']);
    final highRisk = _series(series, const ['high', '高风险']);
    final values = _days(labels, negative, highRisk);
    final chartState = Cth05DataStateParser.parse(chart?['state']);

    // The existing CTH-05 builder returns arrays but no per-day error state or
    // trend definition. Keep the page readable without treating those arrays
    // as a trustworthy calendar until the canonical contract is complete.
    if (definition == null ||
        !definition.isComplete ||
        !_scopeMatches(context, definition.subject) ||
        !_projectionMatches(chart?['projection'], context) ||
        values == null) {
      return Cth05ScreenData(
        context: context,
        generatedAt: _text(response['generated_at']),
        state: chartState == Cth05DataState.empty
            ? Cth05DataState.empty
            : Cth05DataState.notCollected,
        days: const [],
        definition: definition,
      );
    }

    return Cth05ScreenData(
      context: context,
      generatedAt: _text(response['generated_at']),
      state: values.isEmpty ? Cth05DataState.empty : Cth05DataState.ready,
      days: values,
      definition: definition,
    );
  }

  static bool _scopeMatches(Cth05Context context, String subject) {
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
    Cth05Context context,
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

  static bool _projectionMatches(Object? value, Cth05Context context) {
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

  Cth05TrendDefinition? _trendDefinition(
    Map<String, dynamic> response,
    Cth05Context context,
  ) {
    final truth = _map(response['truth']);
    final trend = _map(response['trend_metadata']) ?? _map(truth?['trend']);
    if (trend == null || !_projectionMatches(trend['projection'], context)) {
      return null;
    }
    return Cth05TrendDefinition(
      numerator: _text(trend['numerator']),
      denominator: _text(trend['denominator']),
      timeWindow: _text(trend['time_window'] ?? trend['window']),
      subject: _text(trend['subject'] ?? trend['subject_id']),
      source: _safeSource(_text(trend['source'])),
      freshness: _text(trend['freshness']),
    );
  }

  List<Cth05CalendarDay>? _days(
    List<String> labels,
    List<num>? negative,
    List<num>? highRisk,
  ) {
    if (labels.isEmpty || negative == null || highRisk == null) return null;
    if (negative.length != labels.length || highRisk.length != labels.length) {
      return null;
    }
    return [
      for (var index = 0; index < labels.length; index++)
        Cth05CalendarDay(
          label: labels[index],
          negative: negative[index],
          highRisk: highRisk[index],
        ),
    ];
  }

  static List<num>? _series(
    List<Map<String, dynamic>> series,
    List<String> names,
  ) {
    for (final item in series) {
      final label = _text(item['name']).toLowerCase();
      if (names.any((name) => label.contains(name.toLowerCase()))) {
        final values = item['data'];
        if (values is! List) return null;
        final parsed = values
            .whereType<num>()
            .where((value) => value.isFinite)
            .toList(growable: false);
        return parsed.length == values.length ? parsed : null;
      }
    }
    return null;
  }

  static Cth05Context? _parseContext(Map<String, dynamic> response) {
    if (response['ok'] != true ||
        response['contract'] != 'lumenis.context.v1') {
      return null;
    }
    final context = _map(response['context']);
    if (context == null) return null;
    final mode = _text(context['mode']);
    final domain = _text(context['domain_id']);
    if (mode == 'GLOBAL_ALL') {
      return Cth05Context(
        mode: mode,
        displayName: _displayName(context['display_name']),
      );
    }
    if (mode != 'FOCUS' || domain != 'CTH') return null;
    final subjectId = _text(context['subject_id']);
    if (subjectId.isEmpty) return null;
    return Cth05Context(
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
