import 'dart:convert';
import '../../../core/lumenis_core_client.dart';

enum Cth01BackendState {
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

extension Cth01BackendStateLabel on Cth01BackendState {
  String get label => switch (this) {
    Cth01BackendState.ready => '已返回',
    Cth01BackendState.empty => '暂无记录',
    Cth01BackendState.notCollected => '未采集',
    Cth01BackendState.offline => '依赖不可用',
    Cth01BackendState.stale => '数据已过期',
    Cth01BackendState.partial => '部分返回',
    Cth01BackendState.blocked => '访问受限',
    Cth01BackendState.error => '读取失败',
    Cth01BackendState.unknown => '状态未返回',
  };

  static Cth01BackendState parse(Object? value) => switch (value) {
    'ready' => Cth01BackendState.ready,
    'empty' => Cth01BackendState.empty,
    'notcollected' => Cth01BackendState.notCollected,
    'offline' => Cth01BackendState.offline,
    'stale' => Cth01BackendState.stale,
    'partial' => Cth01BackendState.partial,
    'blocked' => Cth01BackendState.blocked,
    'error' => Cth01BackendState.error,
    _ => Cth01BackendState.unknown,
  };
}

class Cth01Metric {
  const Cth01Metric({
    required this.state,
    this.value,
    this.unit = '',
    this.source = '',
    this.note = '',
  });

  final Cth01BackendState state;
  final num? value;
  final String unit;
  final String source;
  final String note;

  bool get hasValue => state == Cth01BackendState.ready && value != null;
}

class Cth01Signal {
  const Cth01Signal({
    required this.title,
    required this.level,
    required this.date,
    required this.time,
    required this.summary,
    required this.tags,
    required this.eventReference,
  });

  final String title;
  final String level;
  final String date;
  final String time;
  final String summary;
  final List<String> tags;
  final String eventReference;
}

class Cth01RiskNote {
  const Cth01RiskNote({
    required this.title,
    required this.level,
    required this.description,
    required this.noteReference,
    this.score,
  });

  final String title;
  final String level;
  final String description;
  final String noteReference;
  final num? score;
}

class Cth01DailySummary {
  const Cth01DailySummary({
    this.riskIndex,
    this.subjectHealthScore,
    this.mediumHighRiskNoteCount,
  });

  final num? riskIndex;
  final num? subjectHealthScore;
  final num? mediumHighRiskNoteCount;

  bool get hasValues =>
      riskIndex != null ||
      subjectHealthScore != null ||
      mediumHighRiskNoteCount != null;
}

class Cth01ScreenData {
  const Cth01ScreenData({
    required this.contextMode,
    required this.contextDisplayName,
    required this.generatedAt,
    required this.negativeVoice,
    required this.footfall,
    required this.memberSales,
    required this.eventState,
    required this.signals,
    required this.risks,
    required this.dailySummary,
  });

  final String contextMode;
  final Map<String, String>? contextDisplayName;
  final String generatedAt;
  final Cth01Metric negativeVoice;
  final Cth01Metric footfall;
  final Cth01Metric memberSales;
  final Cth01BackendState eventState;
  final List<Cth01Signal> signals;
  final List<Cth01RiskNote> risks;
  final Cth01DailySummary dailySummary;
}

enum Cth01BlockReason { contextUnavailable, pageNotBound }

class Cth01ContextUnavailable implements Exception {
  const Cth01ContextUnavailable(this.reason);

  final Cth01BlockReason reason;
}

class Cth01Repository {
  const Cth01Repository(this._client);

  final LumenisCoreClient _client;

  Future<Cth01ScreenData> load() async {
    final selection = await _client.settingsContext();
    final context = _map(selection['context']);
    if (selection['ok'] != true ||
        selection['contract'] != 'lumenis.context.v1' ||
        context == null) {
      throw const Cth01ContextUnavailable(Cth01BlockReason.contextUnavailable);
    }
    final mode = _text(context['mode']);
    final domain = _text(context['domain_id']);
    if (mode != 'GLOBAL_ALL' && (mode != 'FOCUS' || domain != 'CTH')) {
      throw const Cth01ContextUnavailable(Cth01BlockReason.contextUnavailable);
    }

    final signature = jsonEncode(_client.currentContextEnvelope);
    final response = await _client.screen('CTH-01');
    if (signature != jsonEncode(_client.currentContextEnvelope)) {
      throw const Cth01ContextUnavailable(Cth01BlockReason.contextUnavailable);
    }
    if (response['ok'] != true || response['screen'] != 'CTH-01') {
      throw const FormatException(
        'CTH-01 response does not match its contract',
      );
    }
    final global = mode == 'GLOBAL_ALL';
    final binding = _map(response[global ? 'global_binding' : 'focus_binding']);
    final policyAllowed = switch (binding?['policy']) {
      'local-workspace-read-v1' =>
        binding?['actor_scope'] == 'anonymous_read' &&
            binding?['global_all_granted'] == false,
      'actor-exact-scope-v1' =>
        binding?['actor_scope'] == 'authenticated' &&
            binding?['global_all_granted'] == global,
      _ => false,
    };
    if (response['bound'] != true ||
        response['source'] != 'runtime' ||
        binding?['contract'] != 'lumenis.scope-read-binding.v1' ||
        binding?['module'] != 'commercial_realtime_stream' ||
        binding?['domain_id'] != 'CTH' ||
        binding?['product_id'] != 'CTH' ||
        binding?['canonical_scope'] != mode ||
        binding?['applied'] != true ||
        binding?['read_allowed'] != true ||
        binding?['scope_verified'] != true ||
        binding?.containsKey('subject_id') != true ||
        binding?['subject_id'] != (global ? null : context['subject_id']) ||
        !policyAllowed) {
      throw const Cth01ContextUnavailable(Cth01BlockReason.pageNotBound);
    }

    final displayName = _map(context['display_name']);
    return _decodeScreen(
      response,
      contextMode: mode,
      contextDisplayName: displayName?.map(
        (key, value) => MapEntry(key, '$value'),
      ),
    );
  }

  Cth01ScreenData _decodeScreen(
    Map<String, dynamic> response, {
    required String contextMode,
    required Map<String, String>? contextDisplayName,
  }) {
    final sections = _maps(response['sections']);
    final kpis = _firstSection(sections, 'kpis');
    final split = _firstSection(sections, 'split');
    final mainSections = _maps(split?['main']);
    final sideSections = _maps(split?['side']);
    final events = _firstSection(mainSections, 'events');
    final risks = _firstSection(sideSections, 'risks');
    final truth = _map(response['truth']);
    final canonical = _map(truth?['canonical']);

    return Cth01ScreenData(
      contextMode: contextMode,
      contextDisplayName: contextDisplayName,
      generatedAt: _text(response['generated_at']),
      negativeVoice: _metric(kpis, 'cth.negative_voice'),
      footfall: _metric(kpis, 'cth.footfall'),
      memberSales: _metric(kpis, 'cth.member_sales'),
      eventState: Cth01BackendStateLabel.parse(events?['state']),
      signals: _maps(events?['items']).map(_signal).toList(growable: false),
      risks: _maps(risks?['items']).map(_risk).toList(growable: false),
      dailySummary: Cth01DailySummary(
        riskIndex: _number(canonical?['risk_index']),
        subjectHealthScore: _number(canonical?['brand_health_score']),
        mediumHighRiskNoteCount: _number(canonical?['risk_count']),
      ),
    );
  }

  Cth01Metric _metric(Map<String, dynamic>? section, String id) {
    final item = _maps(section?['items']).where((entry) => entry['id'] == id);
    if (item.isEmpty) {
      return const Cth01Metric(
        state: Cth01BackendState.unknown,
        note: 'OEVIRA Core did not return this metric.',
      );
    }
    final record = item.first;
    final state = Cth01BackendStateLabel.parse(record['state']);
    final value = _number(record['value']);
    return Cth01Metric(
      state: state == Cth01BackendState.ready && value == null
          ? Cth01BackendState.unknown
          : state,
      value: value,
      unit: _text(record['unit']),
      source: _text(record['source']),
      note: _text(record['stateNote']),
    );
  }

  Cth01Signal _signal(Map<String, dynamic> record) => Cth01Signal(
    title: _text(record['title']),
    level: _text(record['level']),
    date: _text(record['date']),
    time: _text(record['time']),
    summary: _text(record['desc']),
    tags: (record['tags'] is List ? record['tags'] as List : const [])
        .whereType<String>()
        .toList(growable: false),
    eventReference: _text(record['evidence']),
  );

  Cth01RiskNote _risk(Map<String, dynamic> record) => Cth01RiskNote(
    title: _text(record['title']),
    level: _text(record['level']),
    description: _text(record['desc']),
    noteReference: _text(record['evidence']),
    score: _number(record['score']),
  );

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
