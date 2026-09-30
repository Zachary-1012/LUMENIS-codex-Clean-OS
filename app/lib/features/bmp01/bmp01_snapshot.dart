class Bmp01Snapshot {
  const Bmp01Snapshot({
    required this.contractBound,
    required this.source,
    required this.productId,
    required this.domainId,
    required this.dataState,
    required this.blockedFields,
    required this.generatedAt,
    required this.focusContext,
    required this.focusBindingApplied,
    required this.metrics,
  });

  final bool contractBound;
  final String? source;
  final String? productId;
  final String? domainId;
  final String dataState;
  final List<Bmp01BlockedField> blockedFields;
  final String? generatedAt;
  final Bmp01FocusContext focusContext;
  final bool focusBindingApplied;
  final List<Bmp01Metric> metrics;

  bool get isBmpOwner => productId == 'ZBMP' && domainId == 'zbmp';
  bool get isNotCollected => dataState == 'NOT_COLLECTED';
  bool get isCollectedAndAvailable => dataState == 'READY';

  bool get canDisplayMetrics =>
      _bmp01MetricDisplayApproved &&
      contractBound &&
      isBmpOwner &&
      focusContext.isFocus &&
      focusContext.hasUsableName &&
      isCollectedAndAvailable &&
      focusBindingApplied &&
      metrics.any((metric) => metric.isReady);

  factory Bmp01Snapshot.fromResponse(Map<String, dynamic> response) {
    if (response['ok'] != true || response['screen'] != 'BMP-01') {
      throw const FormatException('BMP-01 runtime response is not valid.');
    }

    final truth = _asMap(response['truth']);
    final binding = _asMap(response['binding']);
    final focus = Bmp01FocusContext.fromJson(response['focus_context']);
    final blocked = _asMapList(
      binding?['blocked'],
    ).map(Bmp01BlockedField.fromJson).toList(growable: false);

    return Bmp01Snapshot(
      contractBound:
          response['bound'] == true && response['source'] == 'runtime',
      source: _asString(response['source']),
      productId: _asString(truth?['product_id']),
      domainId: _asString(truth?['domain_id']),
      dataState: (_asString(truth?['data_state']) ?? 'UNKNOWN').toUpperCase(),
      blockedFields: blocked,
      generatedAt: _asString(response['generated_at']),
      focusContext: focus,
      focusBindingApplied: _verifiedBmpFocusBinding(response['focus_binding']),
      metrics: _metrics(response['sections']),
    );
  }
}

class Bmp01FocusContext {
  const Bmp01FocusContext({required this.mode, required this.displayName});

  final String mode;
  final Map<String, String> displayName;

  bool get isGlobal => mode == 'GLOBAL_ALL';
  bool get isFocus => mode == 'FOCUS';
  bool get hasUsableName => const [
    'zh-CN',
    'zh',
    'en',
    'ko',
  ].any((language) => displayName[language]?.trim().isNotEmpty == true);

  factory Bmp01FocusContext.fromJson(Object? value) {
    final map = _asMap(value);
    final rawDisplay = _asMap(map?['display_name']);
    final displayName = <String, String>{};
    if (rawDisplay != null) {
      for (final entry in rawDisplay.entries) {
        if (entry.value is String && (entry.value as String).isNotEmpty) {
          displayName[entry.key] = entry.value as String;
        }
      }
    }
    return Bmp01FocusContext(
      mode: _asString(map?['mode'])?.toUpperCase() ?? 'GLOBAL_ALL',
      displayName: displayName,
    );
  }

  String? localizedName(String languageCode) =>
      displayName[languageCode] ?? displayName['en'] ?? displayName['zh-CN'];
}

class Bmp01Metric {
  const Bmp01Metric({
    required this.id,
    required this.label,
    required this.value,
    required this.state,
  });

  final String id;
  final String label;
  final Object? value;
  final String state;

  String? get safeValueText {
    final specification = _bmp01MetricSchema[id];
    if (specification == null) return null;
    final raw = value;
    if (raw is! num || !raw.isFinite) return null;
    if (specification.integerOnly && raw != raw.roundToDouble()) {
      return null;
    }
    final text = specification.integerOnly
        ? raw.toInt().toString()
        : raw.toString();
    return text.length <= 32 ? text : null;
  }

  bool get isSchemaValid {
    final specification = _bmp01MetricSchema[id];
    if (specification == null || !specification.labels.contains(label.trim())) {
      return false;
    }
    final normalizedState = state.toUpperCase();
    return normalizedState == 'READY' ? safeValueText != null : value == null;
  }

  bool get isReady => state.toUpperCase() == 'READY' && safeValueText != null;
}

class _Bmp01MetricSpecification {
  const _Bmp01MetricSpecification({
    required this.labels,
    required this.integerOnly,
  });

  final Set<String> labels;
  final bool integerOnly;
}

// This is deliberately narrower than arbitrary API labels. Only metrics
// emitted by the current BMP-01 contract can ever reach the renderer.
const _bmp01MetricSchema = <String, _Bmp01MetricSpecification>{
  'bmp01.total': _Bmp01MetricSpecification(labels: {'总声量'}, integerOnly: true),
  'bmp01.neg': _Bmp01MetricSpecification(labels: {'负面声量'}, integerOnly: true),
  'bmp01.high': _Bmp01MetricSpecification(labels: {'高风险'}, integerOnly: true),
  'bmp01.eng': _Bmp01MetricSpecification(labels: {'总互动'}, integerOnly: true),
  'bmp01.ri': _Bmp01MetricSpecification(labels: {'风险指数'}, integerOnly: false),
  'bmp01.health': _Bmp01MetricSpecification(
    labels: {'品牌健康分'},
    integerOnly: false,
  ),
};

// Focused metrics are displayed only after the backend supplies the exact
// verified BrandFocus read binding. Incomplete/legacy payloads remain hidden.
const _bmp01MetricDisplayApproved = true;

bool _verifiedBmpFocusBinding(Object? value) {
  final binding = _asMap(value);
  if (binding == null) return false;
  final policy = _asString(binding['policy']);
  final actorScope = _asString(binding['actor_scope']);
  return binding['contract'] == 'lumenis.scope-read-binding.v1' &&
      binding['module'] == 'brand_market_overview' &&
      binding['domain_id'] == 'BMP' &&
      binding['product_id'] == 'ZBMP' &&
      binding['canonical_scope'] == 'FOCUS' &&
      binding['applied'] == true &&
      binding['read_allowed'] == true &&
      binding['scope_verified'] == true &&
      binding['global_all_granted'] == false &&
      _asString(binding['subject_id']) != null &&
      _asString(binding['brand_focus_id']) != null &&
      ((policy == 'local-workspace-read-v1' && actorScope == 'anonymous_read') ||
          (policy == 'actor-exact-scope-v1' && actorScope == 'authenticated'));
}

List<Bmp01Metric> _metrics(Object? value) {
  final sections = _asMapList(value);
  for (final section in sections) {
    if (section['type'] != 'kpis') continue;
    return _asMapList(section['items'])
        .map(
          (item) => Bmp01Metric(
            id: _asString(item['id'])?.trim() ?? '',
            label: _asString(item['label'])?.trim() ?? '',
            value: item['value'],
            state: _asString(item['state'])?.trim() ?? 'UNKNOWN',
          ),
        )
        .where((metric) => metric.isSchemaValid)
        .toList(growable: false);
  }
  return const [];
}

class Bmp01BlockedField {
  const Bmp01BlockedField({
    required this.field,
    required this.reason,
    required this.required,
  });

  final String field;
  final String reason;
  final String required;

  factory Bmp01BlockedField.fromJson(Map<String, Object?> json) {
    return Bmp01BlockedField(
      field: _asString(json['field']) ?? '未知字段',
      reason: _asString(json['reason']) ?? '当前没有可验证的来源说明。',
      required: _asString(json['required']) ?? '',
    );
  }
}

Map<String, Object?>? _asMap(Object? value) {
  if (value is! Map) return null;
  return value.map((key, value) => MapEntry('$key', value));
}

List<Map<String, Object?>> _asMapList(Object? value) {
  if (value is! List) return const [];
  return value.map(_asMap).whereType<Map<String, Object?>>().toList();
}

String? _asString(Object? value) {
  if (value is! String || value.isEmpty) return null;
  return value;
}
