enum Sh06ScopeMode { globalAll, focus }

enum Sh06ScopeErrorKind { unavailable, denied, malformed }

class Sh06ScopeError implements Exception {
  const Sh06ScopeError(this.kind);

  final Sh06ScopeErrorKind kind;
}

class Sh06Scope {
  const Sh06Scope({
    required this.mode,
    required this.domain,
    required this.focusId,
    required this.displayName,
  });

  final Sh06ScopeMode mode;
  final String? domain;
  final String? focusId;
  final String displayName;

  bool get isGlobal => mode == Sh06ScopeMode.globalAll;

  String get businessDomain => switch (domain) {
    'CTH' => '商业运营',
    'BMP' => '品牌市场',
    _ => '全部范围',
  };

  static Sh06Scope fromResponse(Map<String, dynamic> response) {
    final rawScope = _asMap(response['scope'] ?? response['context']);
    final permission = _asMap(
      response['permission'] ?? response['authorization'],
    );
    if (rawScope == null || permission == null) {
      throw const Sh06ScopeError(Sh06ScopeErrorKind.unavailable);
    }
    if (response['selection_only'] == true ||
        rawScope['selection_only'] == true) {
      throw const Sh06ScopeError(Sh06ScopeErrorKind.unavailable);
    }
    final decision = _string(
      permission['decision'] ?? permission['result'] ?? permission['state'],
    )?.toUpperCase();
    final canRead =
        permission['read'] == true ||
        permission['can_read'] == true ||
        permission['view'] == true;
    if (!canRead ||
        !const {'ALLOW', 'ALLOWED', 'GRANTED', 'PERMITTED'}.contains(decision)) {
      throw const Sh06ScopeError(Sh06ScopeErrorKind.denied);
    }
    final mode = _string(
      rawScope['mode'] ?? rawScope['scope_mode'],
    )?.toUpperCase();
    if (mode == 'GLOBAL_ALL') {
      if (_present(rawScope['subject_id']) ||
          _present(rawScope['brand_focus_id']) ||
          rawScope['global'] == false) {
        throw const Sh06ScopeError(Sh06ScopeErrorKind.malformed);
      }
      return const Sh06Scope(
        mode: Sh06ScopeMode.globalAll,
        domain: null,
        focusId: null,
        displayName: '全部范围',
      );
    }
    if (mode != 'FOCUS') {
      throw const Sh06ScopeError(Sh06ScopeErrorKind.malformed);
    }
    final domain = _string(
      rawScope['domain_id'] ?? rawScope['domain'],
    )?.toUpperCase();
    final focusId = _string(
      rawScope['subject_id'] ??
          rawScope['brand_focus_id'] ??
          rawScope['focus_id'],
    );
    final displayName = _safeText(rawScope['display_name']);
    if ((domain != 'CTH' && domain != 'BMP' && domain != 'ZBMP') ||
        focusId == null ||
        displayName == null) {
      throw const Sh06ScopeError(Sh06ScopeErrorKind.malformed);
    }
    return Sh06Scope(
      mode: Sh06ScopeMode.focus,
      domain: domain == 'ZBMP' ? 'BMP' : domain,
      focusId: focusId,
      displayName: displayName,
    );
  }
}

enum Sh06ItemKind { task, notification, alert }

enum Sh06Priority { high, medium, low, unknown }

enum Sh06ItemState { open, inProgress, blocked, complete, unavailable }

class Sh06Item {
  const Sh06Item({
    required this.internalId,
    required this.title,
    required this.detail,
    required this.sourceLabel,
    required this.kind,
    required this.priority,
    required this.due,
    required this.state,
    required this.originVerified,
    required this.evidenceLinked,
  });

  final String internalId;
  final String title;
  final String detail;
  final String sourceLabel;
  final Sh06ItemKind kind;
  final Sh06Priority priority;
  final String due;
  final Sh06ItemState state;
  final bool originVerified;
  final bool evidenceLinked;

  String get kindLabel => switch (kind) {
    Sh06ItemKind.task => '待办',
    Sh06ItemKind.notification => '通知',
    Sh06ItemKind.alert => '告警',
  };

  String get priorityLabel => switch (priority) {
    Sh06Priority.high => '高',
    Sh06Priority.medium => '中',
    Sh06Priority.low => '低',
    Sh06Priority.unknown => '未确认',
  };

  String get stateLabel => switch (state) {
    Sh06ItemState.open => '待处理',
    Sh06ItemState.inProgress => '处理中',
    Sh06ItemState.blocked => '已阻断',
    Sh06ItemState.complete => '已完成',
    Sh06ItemState.unavailable => '状态未确认',
  };

  static Sh06Item? tryParse(Object? value, {required Sh06Scope scope}) {
    final record = _asMap(value);
    if (record == null) return null;
    final id = _string(
      record['id'] ?? record['task_id'] ?? record['notification_id'],
    );
    final title = _safeText(record['title'] ?? record['name']);
    if (id == null || title == null) return null;
    final projection = _SharedProjection.tryParse(
      record['projection'],
      scope: scope,
      requireOrigin: true,
    );
    if (projection == null) return null;
    return Sh06Item(
      internalId: id,
      title: title,
      detail:
          _safeText(
            record['detail'] ?? record['description'] ?? record['summary'],
          ) ??
          '',
      sourceLabel: _safeText(record['source_label'] ?? record['source']) ?? '',
      kind: _kind(record['kind'] ?? record['type']),
      priority: _priority(record['priority'] ?? record['level']),
      due: _safeText(record['due'] ?? record['due_at'] ?? record['time']) ?? '',
      state: _state(record['state'] ?? record['status']),
      originVerified: projection.originVerified,
      evidenceLinked: projection.canonicalEvidenceReference.isNotEmpty,
    );
  }
}

class Sh06Snapshot {
  const Sh06Snapshot({
    required this.scope,
    required this.items,
    required this.operationalState,
  });

  final Sh06Scope scope;
  final List<Sh06Item> items;
  final String operationalState;

  factory Sh06Snapshot.fromResponse(Map<String, dynamic> response) {
    if (response['ok'] != true || response['screen'] != 'SH-06') {
      throw const FormatException('SH-06 response identity is invalid.');
    }
    if (response['bound'] != true || response['source'] != 'runtime') {
      throw const FormatException('SH-06 runtime binding is unavailable.');
    }
    final scope = Sh06Scope.fromResponse(response);
    final data = _asMap(response['data']);
    if (data == null) {
      throw const FormatException('SH-06 data envelope is incomplete.');
    }
    final rawItems = <Object?>[];
    for (final key in const ['tasks', 'notifications', 'alerts', 'items']) {
      final list = data[key];
      if (list is! List) continue;
      final inferredKind = switch (key) {
        'tasks' => 'TASK',
        'alerts' => 'ALERT',
        _ => 'NOTIFICATION',
      };
      for (final item in list) {
        if (item is Map &&
            !item.containsKey('kind') &&
            !item.containsKey('type')) {
          final copy = <String, dynamic>{};
          item.forEach((itemKey, value) => copy['$itemKey'] = value);
          copy['kind'] = inferredKind;
          rawItems.add(copy);
        } else {
          rawItems.add(item);
        }
      }
    }
    if (data['tasks'] is! List &&
        data['notifications'] is! List &&
        data['alerts'] is! List &&
        data['items'] is! List) {
      throw const FormatException('SH-06 inbox list is unavailable.');
    }
    final parsed = rawItems
        .map((item) => Sh06Item.tryParse(item, scope: scope))
        .whereType<Sh06Item>()
        .toList(growable: false);
    return Sh06Snapshot(
      scope: scope,
      items: parsed,
      operationalState: _stateLabel(
        data['operational_state'] ?? data['runtime_state'],
      ),
    );
  }
}

class _SharedProjection {
  const _SharedProjection({
    required this.canonicalEvidenceReference,
    required this.integrityDigest,
    required this.assurance,
    required this.originVerified,
  });

  final String canonicalEvidenceReference;
  final String integrityDigest;
  final String assurance;
  final bool originVerified;

  static _SharedProjection? tryParse(
    Object? value, {
    required Sh06Scope scope,
    bool requireOrigin = false,
  }) {
    final projection = _asMap(value);
    if (projection == null ||
        projection['contract'] !=
            'lumenis.shared.experience-row-projection' ||
        projection['version'] != 2 ||
        projection['read_allowed'] != true) {
      return null;
    }
    final projectionScope = _asMap(projection['scope']);
    if (projectionScope == null ||
        !_projectionScopeMatches(projectionScope, scope)) {
      return null;
    }
    final evidence = _asMap(projection['evidence']);
    final canonicalReference = _safeProjectionReference(
      evidence?['canonical_reference'],
    );
    if (canonicalReference == null) return null;
    final integrity = _asMap(projection['integrity']);
    if (integrity == null ||
        integrity['integrity_version'] != 2 ||
        integrity['verified'] != true ||
        integrity['lineage_verified'] != true) {
      return null;
    }
    final assurance = _string(integrity['assurance']);
    if (assurance == null ||
        !const {'writer-authenticated', 'content-integrity-only'}
            .contains(assurance)) {
      return null;
    }
    final algorithm = _string(integrity['algorithm'])?.toLowerCase();
    final digest = _safeProjectionDigest(integrity['digest']);
    final consistentAssurance =
        (assurance == 'writer-authenticated' && algorithm == 'hmac-sha256') ||
        (assurance == 'content-integrity-only' && algorithm == 'sha256');
    if (digest == null || !consistentAssurance) {
      return null;
    }
    final originVerified = projection['origin_verified'] == true;
    if (requireOrigin && !originVerified) return null;
    return _SharedProjection(
      canonicalEvidenceReference: canonicalReference,
      integrityDigest: digest,
      assurance: assurance,
      originVerified: originVerified,
    );
  }
}

bool _projectionScopeMatches(Map<String, dynamic> raw, Sh06Scope scope) {
  final mode = _string(raw['mode'] ?? raw['scope_mode'])?.toUpperCase();
  if (scope.isGlobal) {
    return mode == 'GLOBAL_ALL' &&
        raw['global_all_granted'] == true &&
        !_present(raw['subject_id']) &&
        !_present(raw['brand_focus_id']) &&
        !_present(raw['focus_id']);
  }
  if (mode != 'FOCUS' || raw['global_all_granted'] == true) return false;
  final domain = _string(raw['domain_id'] ?? raw['domain'])?.toUpperCase();
  final ids = <String?>[
    _string(raw['subject_id']),
    _string(raw['brand_focus_id']),
    _string(raw['focus_id']),
  ].whereType<String>().toList(growable: false);
  if (ids.length != 1) return false;
  return (domain == scope.domain || (domain == 'ZBMP' && scope.domain == 'BMP')) &&
      ids.single == scope.focusId;
}

String? _safeProjectionReference(Object? value) {
  final reference = _string(value);
  if (reference == null || reference.length > 200) return null;
  return RegExp(r'^evidence:canonical:[A-Za-z0-9._:-]+$').hasMatch(reference)
      ? reference
      : null;
}

String? _safeProjectionDigest(Object? value) {
  final digest = _string(value);
  if (digest == null || digest.length > 200) return null;
  return RegExp(r'^[a-f0-9]{64}$').hasMatch(digest)
      ? digest
      : null;
}

Sh06ItemKind _kind(Object? value) => switch (_string(value)?.toUpperCase()) {
  'TASK' || 'APPROVAL' => Sh06ItemKind.task,
  'ALERT' || 'WARNING' => Sh06ItemKind.alert,
  _ => Sh06ItemKind.notification,
};

Sh06Priority _priority(Object? value) =>
    switch (_string(value)?.toUpperCase()) {
      'HIGH' || 'DANGER' || 'URGENT' => Sh06Priority.high,
      'MEDIUM' || 'WARN' => Sh06Priority.medium,
      'LOW' || 'INFO' => Sh06Priority.low,
      _ => Sh06Priority.unknown,
    };

Sh06ItemState _state(Object? value) => switch (_string(value)?.toUpperCase()) {
  'OPEN' || 'PENDING' || 'TODO' => Sh06ItemState.open,
  'IN_PROGRESS' || 'RUNNING' => Sh06ItemState.inProgress,
  'BLOCKED' || 'FAILED' => Sh06ItemState.blocked,
  'COMPLETE' || 'COMPLETED' || 'RESOLVED' => Sh06ItemState.complete,
  _ => Sh06ItemState.unavailable,
};

String _stateLabel(Object? value) => switch (_string(value)?.toUpperCase()) {
  'READY' || 'HEALTHY' || 'OK' => '运行正常',
  'DEGRADED' || 'WARN' => '部分可用',
  'OFFLINE' => '暂时离线',
  _ => '运行状态未确认',
};

Map<String, dynamic>? _asMap(Object? value) {
  if (value is! Map) return null;
  return value.map((key, value) => MapEntry('$key', value));
}

String? _string(Object? value) =>
    value is String && value.trim().isNotEmpty ? value.trim() : null;

bool _present(Object? value) => _string(value) != null;

String? _safeText(Object? value) {
  final text = _string(value);
  if (text == null || text.length > 220 || RegExp(r'[<>]').hasMatch(text)) {
    return null;
  }
  if (RegExp(
    r'(api|database|sqlite|\bdb\b|provider|permission|owner|runtime|contract|viewmodel|canonical|subject|brandfocus|\bcth\b|\bbmp\b|\bzbmp\b|token|cookie|secret|internal|private|path|https?)',
    caseSensitive: false,
  ).hasMatch(text)) {
    return null;
  }
  return text;
}
