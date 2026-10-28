import 'dart:math';

import 'package:flutter/foundation.dart';

import '../../../core/lumenis_core_client.dart';
import 'sh02_snapshot.dart';

Map<String, dynamic> _map(Object? value) {
  if (value is! Map || value.keys.any((key) => key is! String)) {
    throw const FormatException('Invalid Office response.');
  }
  return Map<String, dynamic>.from(value);
}

bool _hash(Object? value) =>
    value is String && RegExp(r'^[a-f0-9]{64}$').hasMatch(value);
bool _artifact(Object? value) =>
    value is String && RegExp(r'^ART-[a-f0-9]{16}$').hasMatch(value);

class Sh02OfficeObject {
  Sh02OfficeObject.fromJson(Object? raw) {
    final item = _map(raw);
    id = item['object_id'] as String;
    kind = item['kind'] as String;
    value = item['value'] as Object;
    locator = Map.unmodifiable(_map(item['locator']));
    if (!RegExp(r'^office-[a-f0-9]{32}$').hasMatch(id) ||
        !operations.containsKey(kind) ||
        item['editable'] != true ||
        !_hash(item['part_sha256']) ||
        locator['part'] is! String ||
        locator['node_path'] is! String ||
        (value is String && (value as String).runes.length > 32000) ||
        (structured && value is! Map) ||
        (!structured && value is! String) ||
        (item['supported_operations'] != null &&
            !(item['supported_operations'] is List &&
                (item['supported_operations'] as List).contains(
                  operations[kind],
                ))) ||
        (kind == 'cell_boolean' && !{'0', '1'}.contains(value))) {
      throw const FormatException('Invalid Office object.');
    }
  }
  static const operations = {
    'text_run': 'replace_text',
    'cell_text_run': 'replace_text',
    'cell_number': 'set_number',
    'cell_boolean': 'set_boolean',
    'cell_formula': 'replace_formula',
    'word_run_format': 'set_run_format',
    'drawing_run_format': 'set_run_format',
    'word_paragraph_format': 'set_paragraph_format',
    'shape_geometry': 'set_geometry',
    'cell_style': 'set_cell_style',
  };
  late final String id, kind;
  late final Object value;
  bool get structured => const {
    'word_run_format',
    'drawing_run_format',
    'word_paragraph_format',
    'shape_geometry',
    'cell_style',
  }.contains(kind);
  late final Map<String, dynamic> locator;
  Object get initialValue => kind == 'cell_boolean' ? value == '1' : value;
  Map<String, dynamic> command(Object next) => {
    'object_id': id,
    'operation': operations[kind],
    'expected_value': value,
    'value': next,
  };
  bool accepts(Object next) {
    if (structured) {
      if (next is! Map ||
          value is! Map ||
          !setEquals(next.keys.toSet(), (value as Map).keys.toSet())) {
        return false;
      }
      for (final key in next.keys) {
        final field = next[key];
        if (const {
              'bold',
              'italic',
              'keep_with_next',
              'page_break_before',
            }.contains(key) &&
            field != null &&
            field is! bool) {
          return false;
        }
        if (const {'flip_horizontal', 'flip_vertical'}.contains(key) &&
            field is! bool) {
          return false;
        }
        if (key.toString().endsWith('_emu') ||
            key == 'rotation_60000deg' ||
            key == 'style_index') {
          if (field is! int) return false;
          if (const {'width_emu', 'height_emu'}.contains(key) && field <= 0) {
            return false;
          }
        }
        if (const {
              'size_half_points',
              'size_hundredth_points',
              'space_before_twips',
              'space_after_twips',
            }.contains(key) &&
            field != null &&
            (field is! int || field < 0)) {
          return false;
        }
        if (key == 'color' &&
            field != null &&
            (field is! String ||
                !RegExp(r'^[0-9a-fA-F]{6}$|^auto$').hasMatch(field))) {
          return false;
        }
      }
      return true;
    }
    if (kind == 'cell_boolean') return next is bool;
    if (next is! String ||
        next.runes.length > 32000 ||
        RegExp(r'[\x00-\x08\x0b\x0c\x0e-\x1f]').hasMatch(next)) {
      return false;
    }
    if (kind == 'cell_number') {
      return RegExp(
        r'^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$',
      ).hasMatch(next);
    }
    return kind != 'cell_formula' || next.trim().isNotEmpty;
  }
}

class Sh02OfficePage {
  Sh02OfficePage.fromJson(
    Object? raw,
    Sh02ImportedMaterial source,
    int offset,
    int limit,
  ) {
    final value = _map(raw);
    artifactId = value['source_artifact_id'] as String;
    artifactSha256 = value['source_artifact_sha256'] as String;
    packageSha256 = value['package_sha256'] as String;
    workId = value['work_id'] as String;
    version = value['version'] as int;
    format = value['format'] as String;
    attachment = value['attachment_name'] as String;
    final rows = value['objects'];
    if (value['schema'] != 'lumenis.office-objects/v1' ||
        artifactId != source.artifactId ||
        artifactSha256 != source.artifactSha256 ||
        packageSha256 != source.sourceSha256 ||
        !_hash(packageSha256) ||
        !RegExp(r'^WORK-[a-f0-9]{24}$').hasMatch(workId) ||
        version < 1 ||
        !{'docx', 'pptx', 'xlsx'}.contains(format) ||
        !source.filename.toLowerCase().endsWith('.$format') ||
        attachment.isEmpty ||
        attachment.length > 185 ||
        attachment.contains(RegExp(r'[/\\\x00-\x1f]')) ||
        value['current_version'] is! bool ||
        value['has_more'] is! bool ||
        value['object_count'] is! int ||
        (value['object_count'] as int) < 0 ||
        rows is! List ||
        rows.length > limit) {
      throw const FormatException('Office version was not verified.');
    }
    current = value['current_version'] as bool;
    total = value['object_count'] as int;
    hasMore = value['has_more'] as bool;
    nextOffset = value['next_offset'] as int?;
    if (offset + rows.length > total ||
        (hasMore &&
            (rows.length != limit ||
                nextOffset != offset + limit ||
                nextOffset! >= total)) ||
        (!hasMore && (nextOffset != null || offset + rows.length != total))) {
      throw const FormatException('Office page was incomplete.');
    }
    objects = List.unmodifiable(rows.map(Sh02OfficeObject.fromJson));
    final styles = value['style_options'];
    styleOptions = styles is List
        ? List.unmodifiable(
            styles
                .map(_map)
                .where(
                  (style) =>
                      style['style_index'] is int &&
                      style['name'] is String &&
                      style['editable'] == true &&
                      style['source'] == 'existing_workbook_style',
                ),
          )
        : const [];
    if (objects.map((object) => object.id).toSet().length != objects.length) {
      throw const FormatException('Duplicate Office identity.');
    }
    for (final key in [
      'signature_parts',
      'active_content_parts',
      'unsupported_objects',
    ]) {
      if (value[key] is! List) {
        throw const FormatException('Office preservation state missing.');
      }
    }
    signed = (value['signature_parts'] as List).isNotEmpty;
    activeContent = (value['active_content_parts'] as List).isNotEmpty;
    unsupported = (value['unsupported_objects'] as List).length;
    formulaRecalculationNeeded =
        format == 'xlsx' && value['formula_evaluation'] != 'COMPLETED';
  }
  late final String artifactId,
      artifactSha256,
      packageSha256,
      workId,
      format,
      attachment;
  late final int version, total, unsupported;
  late final bool current,
      hasMore,
      signed,
      activeContent,
      formulaRecalculationNeeded;
  late final int? nextOffset;
  late final List<Sh02OfficeObject> objects;
  late final List<Map<String, dynamic>> styleOptions;
}

class Sh02OfficeSaved {
  Sh02OfficeSaved.fromJson(
    Object? raw,
    Sh02OfficePage parent,
    String requestId,
  ) {
    final value = _map(raw);
    final parsed = Sh02ImportedMaterial.tryParse(value);
    if (parsed == null) {
      throw const FormatException('Office saved material was not verified.');
    }
    material = parsed;
    final document = _map(value['document']);
    final attachment = _map(value['office_attachment']);
    if (material.requestId != requestId ||
        material.workId != parent.workId ||
        material.version != parent.version + 1 ||
        material.parentArtifactId != parent.artifactId ||
        document['parent_sha256'] != parent.artifactSha256 ||
        attachment['artifact_id'] != material.artifactId ||
        attachment['sha256'] != material.sourceSha256 ||
        attachment['name'] is! String ||
        attachment['size_bytes'] != material.sizeBytes) {
      throw const FormatException('Office save receipt mismatch.');
    }
    attachmentName = attachment['name'] as String;
  }
  late final Sh02ImportedMaterial material;
  late final String attachmentName;
}

class Sh02OfficeHistoryPage {
  const Sh02OfficeHistoryPage(this.items, this.cursor, this.complete);
  final List<Sh02ImportedMaterial> items;
  final String? cursor;
  final bool complete;
}

abstract interface class Sh02OfficeRepository {
  Future<Sh02OfficePage> read(Sh02ImportedMaterial source, {int offset = 0});
  Future<Sh02OfficeSaved> save(
    Sh02OfficePage parent, {
    required String requestId,
    required String reason,
    required List<Map<String, dynamic>> commands,
    required bool invalidateSignature,
  });
  Future<Sh02ImportedMaterial> reopen(String artifactId);
  Future<Sh02OfficeHistoryPage> history(String workId, {String? cursor});
  Future<SavedWorkExportFile> download(Sh02OfficePage page);
}

class CoreSh02OfficeRepository implements Sh02OfficeRepository {
  const CoreSh02OfficeRepository(this.client);
  final LumenisCoreClient client;
  Map<String, dynamic> _result(Map<String, dynamic> value) {
    if (value['ok'] != true) {
      throw const FormatException('Office action unavailable.');
    }
    return _map(value['result']);
  }

  @override
  Future<Sh02OfficePage> read(
    Sh02ImportedMaterial source, {
    int offset = 0,
  }) async => Sh02OfficePage.fromJson(
    _result(
      await client.readSharedOfficeDocument(
        source.artifactId,
        offset: offset,
        limit: 100,
      ),
    ),
    source,
    offset,
    100,
  );
  @override
  Future<Sh02OfficeSaved> save(
    Sh02OfficePage parent, {
    required String requestId,
    required String reason,
    required List<Map<String, dynamic>> commands,
    required bool invalidateSignature,
  }) async => Sh02OfficeSaved.fromJson(
    _result(
      await client.editSharedOfficeDocument(
        artifactId: parent.artifactId,
        requestId: requestId,
        expectedSha256: parent.artifactSha256,
        expectedPackageSha256: parent.packageSha256,
        reason: reason,
        commands: commands,
        acknowledgeSignatureInvalidation: invalidateSignature,
      ),
    ),
    parent,
    requestId,
  );
  @override
  Future<Sh02ImportedMaterial> reopen(String artifactId) async {
    final item = Sh02ImportedMaterial.tryParse(
      _result(await client.reopenSharedSavedWork(artifactId)),
    );
    if (item == null || item.artifactId != artifactId) {
      throw const FormatException('Office readback unavailable.');
    }
    return item;
  }

  @override
  Future<Sh02OfficeHistoryPage> history(String workId, {String? cursor}) async {
    final result = _result(
      await client.listSharedSavedWork(
        kind: 'research',
        limit: 100,
        cursor: cursor,
      ),
    );
    if (result['items'] is! List ||
        result['has_more'] is! bool ||
        result['verification_complete'] is! bool) {
      throw const FormatException('Office history incomplete.');
    }
    final items = <Sh02ImportedMaterial>[];
    var complete = result['verification_complete'] == true;
    for (final raw in result['items'] as List) {
      final row = _map(raw);
      final doc = _map(row['document']);
      if (doc['work_id'] != workId) continue;
      final item = Sh02ImportedMaterial.tryParse(row);
      if (item == null) {
        complete = false;
      } else {
        items.add(item);
      }
    }
    final next = result['has_more'] == true ? result['next_cursor'] : null;
    if (result['has_more'] == true &&
        (next is! String || next.isEmpty || next == cursor)) {
      throw const FormatException('Office history cursor invalid.');
    }
    return Sh02OfficeHistoryPage(
      List.unmodifiable(items),
      next as String?,
      complete,
    );
  }

  @override
  Future<SavedWorkExportFile> download(Sh02OfficePage page) =>
      client.downloadSharedSavedWorkAttachment(
        artifactId: page.artifactId,
        name: page.attachment,
      );
}

class Sh02OfficeComparison {
  const Sh02OfficeComparison(this.previous, this.latest, this.proposed);
  final Sh02OfficeObject previous;
  final Sh02OfficeObject? latest;
  final Object proposed;
}

class _OfficePendingEdit {
  _OfficePendingEdit(
    String reason,
    List<Map<String, dynamic>> commands,
    this.invalidateSignature,
  ) : reason = reason.trim(),
      commands = List.unmodifiable(
        commands.map(Map<String, dynamic>.unmodifiable),
      );
  final String reason;
  final List<Map<String, dynamic>> commands;
  final bool invalidateSignature;
}

/// Extends the existing imported-material reader. It never edits a reconstructed
/// report and never treats an uncertain write as a reason to submit it again.
class Sh02OfficeController extends ChangeNotifier {
  Sh02OfficeController({required this.repository, required this.source});
  final Sh02OfficeRepository repository;
  Sh02ImportedMaterial source;
  Sh02OfficePage? page;
  final List<Sh02OfficeObject> objects = [];
  final Map<String, Object> edits = {};
  bool busy = false, saveUnknown = false, conflict = false;
  String? problem, notice;
  int? nextOffset;
  String? _pendingId;
  Sh02OfficePage? _pendingParent;
  _OfficePendingEdit? _pendingEdit;
  Sh02ImportedMaterial? _pendingSaved, _newer;
  Sh02ImportedMaterial? comparisonSource;
  Sh02OfficePage? comparisonPage;
  List<Sh02OfficeComparison> comparisons = [];
  List<Sh02OfficeObject> _comparisonObjects = [];
  bool _disposed = false;
  final _checkCursors = <String>{};
  String? _checkCursor;
  bool _checkHistoryComplete = true;
  bool _retryAfterNotFound = false;
  bool get dirty => edits.isNotEmpty;
  bool get protected => busy || dirty || saveUnknown;
  bool get canEdit =>
      !busy &&
      !saveUnknown &&
      !conflict &&
      page?.current == true &&
      page?.activeContent == false;
  bool get valid =>
      edits.length <= 200 &&
      objects
          .where((o) => edits.containsKey(o.id))
          .every((o) => o.accepts(edits[o.id]!));
  bool get canSave => canEdit && dirty && valid;
  bool get canOpenNewer =>
      _newer != null && _newer!.artifactId != source.artifactId;
  Object value(Sh02OfficeObject object) =>
      edits[object.id] ?? object.initialValue;

  void change(Sh02OfficeObject object, Object value) {
    if (!canEdit || !objects.any((candidate) => identical(candidate, object))) {
      return;
    }
    if (value == object.initialValue ||
        (value is Map &&
            object.initialValue is Map &&
            mapEquals(value, object.initialValue as Map))) {
      edits.remove(object.id);
    } else {
      edits[object.id] = value;
    }
    notice = null;
    _notify();
  }

  void undo(String? id) {
    if (busy || saveUnknown) return;
    id == null ? edits.clear() : edits.remove(id);
    _notify();
  }

  Future<void> load({bool more = false}) async {
    if (busy || (more && nextOffset == null)) return;
    await _readOnly(() async {
      final offset = more ? nextOffset! : 0;
      final next = await repository.read(source, offset: offset);
      if (_disposed) return;
      if (more &&
          (page?.packageSha256 != next.packageSha256 ||
              page?.total != next.total ||
              page?.current != next.current)) {
        conflict = true;
        throw const FormatException('Office pagination changed.');
      }
      final prior = more ? objects.map((o) => o.id).toSet() : <String>{};
      if (next.objects.any((o) => prior.contains(o.id))) {
        throw const FormatException('Office objects repeated.');
      }
      if (!more) objects.clear();
      page = next;
      objects.addAll(next.objects);
      nextOffset = next.nextOffset;
    });
  }

  Future<void> _readOnly(Future<void> Function() action) async {
    if (busy || _disposed) return;
    busy = true;
    problem = null;
    _notify();
    try {
      await action();
    } catch (error) {
      _failure(error);
    } finally {
      busy = false;
      _notify();
    }
  }

  bool _accessUnavailable(Object error) =>
      error is LumenisCoreException &&
      {401, 403, 404, 410}.contains(error.statusCode);

  void _clearPending() {
    _pendingId = null;
    _pendingParent = null;
    _pendingSaved = null;
    _pendingEdit = null;
    _checkCursor = null;
    _checkCursors.clear();
    _checkHistoryComplete = true;
    _retryAfterNotFound = false;
  }

  void _failure(Object error) {
    if (_accessUnavailable(error)) {
      objects.clear();
      page = null;
      comparisons = [];
      comparisonPage = null;
      comparisonSource = null;
      _comparisonObjects = [];
      edits.clear();
      _clearPending();
      _newer = null;
      nextOffset = null;
      saveUnknown = false;
      conflict = false;
      notice = null;
      problem = 'editUnavailable';
    } else {
      problem = saveUnknown
          ? 'unknownSave'
          : conflict
          ? 'conflict'
          : 'loadFailed';
    }
  }

  Future<void> save(String reason, {bool invalidateSignature = false}) async {
    if (!canSave ||
        reason.trim().isEmpty ||
        reason.runes.length > 2000 ||
        (page!.signed && !invalidateSignature)) {
      return;
    }
    final parent = page!;
    final commands = [
      for (final object in objects)
        if (edits.containsKey(object.id)) object.command(edits[object.id]!),
    ];
    _pendingId =
        'office_${DateTime.now().microsecondsSinceEpoch}_${Random.secure().nextInt(1 << 30)}';
    _pendingParent = parent;
    _pendingEdit = _OfficePendingEdit(reason, commands, invalidateSignature);
    _checkCursor = null;
    _checkCursors.clear();
    _checkHistoryComplete = true;
    _retryAfterNotFound = false;
    busy = true;
    problem = null;
    notice = null;
    _notify();
    try {
      await _submitPending();
    } finally {
      busy = false;
      _notify();
    }
  }

  Future<void> _submitPending() async {
    final edit = _pendingEdit;
    if (edit == null || _pendingParent == null || _pendingId == null) return;
    try {
      // The original request and CAS parent remain frozen across every retry.
      // The repository's normal save rechecks current write/source permission.
      final result = await repository.save(
        _pendingParent!,
        requestId: _pendingId!,
        reason: edit.reason,
        commands: edit.commands,
        invalidateSignature: edit.invalidateSignature,
      );
      if (_disposed) return;
      _pendingSaved = result.material;
      await _confirmSaved(result.material);
    } catch (error) {
      if (_disposed) return;
      if (_accessUnavailable(error)) {
        _failure(error);
      } else if (_pendingSaved == null &&
          error is LumenisCoreException &&
          (error.statusCode == 400 || error.statusCode == 409)) {
        conflict = error.statusCode == 409;
        problem = conflict ? 'conflict' : 'invalid';
        saveUnknown = false;
        notice = null;
        _clearPending();
      } else {
        saveUnknown = true;
        problem = 'unknownSave';
        notice = null;
        _retryAfterNotFound = false;
      }
    }
  }

  Future<void> _confirmSaved(Sh02ImportedMaterial candidate) async {
    final reopened = await repository.reopen(candidate.artifactId);
    if (_disposed) return;
    if (reopened.artifactSha256 != candidate.artifactSha256 ||
        reopened.sourceSha256 != candidate.sourceSha256 ||
        reopened.workId != _pendingParent?.workId ||
        reopened.requestId != _pendingId) {
      throw const FormatException('Office save not confirmed.');
    }
    final next = await repository.read(reopened);
    if (_disposed) return;
    if (next.workId != _pendingParent?.workId ||
        next.version != _pendingParent!.version + 1 ||
        reopened.parentArtifactId != _pendingParent!.artifactId) {
      throw const FormatException('Office save chain mismatch.');
    }
    source = reopened;
    page = next;
    _newer = null;
    objects
      ..clear()
      ..addAll(next.objects);
    nextOffset = next.nextOffset;
    edits.clear();
    conflict = false;
    saveUnknown = false;
    problem = null;
    notice = 'saved';
    _clearPending();
    comparisons = [];
    comparisonPage = null;
    comparisonSource = null;
  }

  Future<void> checkSave() async {
    if (busy || !saveUnknown || _pendingParent == null || _pendingId == null) {
      return;
    }
    await _readOnly(() async {
      if (_pendingSaved case final known?) {
        await _confirmSaved(known);
        return;
      }
      final history = await repository.history(
        _pendingParent!.workId,
        cursor: _checkCursor,
      );
      if (_disposed) return;
      _checkHistoryComplete = _checkHistoryComplete && history.complete;
      final matches = history.items
          .where((item) => item.requestId == _pendingId)
          .toList();
      if (matches.length > 1) {
        throw const FormatException('Office request identity ambiguous.');
      }
      if (matches.isNotEmpty) {
        await _confirmSaved(matches.single);
        return;
      }
      if (history.cursor case final cursor?) {
        if (!_checkCursors.add(cursor)) {
          throw const FormatException('Office history repeated.');
        }
        _checkCursor = cursor;
        notice = 'checkMore';
      } else {
        _checkCursor = null;
        _checkCursors.clear();
        final complete = _checkHistoryComplete;
        _checkHistoryComplete = true;
        if (complete && _retryAfterNotFound && _pendingEdit != null) {
          // A second explicit check revalidates all history immediately before
          // replay. A late commit above is reopened instead of posted again.
          _retryAfterNotFound = false;
          await _submitPending();
          return;
        }
        _retryAfterNotFound = complete;
        notice = 'notFound';
      }
      problem = 'unknownSave';
    });
  }

  Future<void> compareLatest() async {
    if (busy || page == null || (!conflict && page!.current)) return;
    await _readOnly(() async {
      Sh02ImportedMaterial? latest;
      String? cursor;
      final seen = <String>{};
      do {
        final history = await repository.history(page!.workId, cursor: cursor);
        if (_disposed) return;
        if (!history.complete) {
          throw const FormatException('Office history unverified.');
        }
        for (final item in history.items) {
          if (latest == null || (item.version ?? 0) > (latest.version ?? 0)) {
            latest = item;
          }
        }
        cursor = history.cursor;
        if (cursor != null && !seen.add(cursor)) {
          throw const FormatException('Office history repeated.');
        }
      } while (cursor != null);
      if (latest == null || latest.artifactId == source.artifactId) {
        problem = 'conflict';
        return;
      }
      final reopened = await repository.reopen(latest.artifactId);
      if (_disposed) return;
      var next = await repository.read(reopened);
      if (_disposed) return;
      if (!next.current || next.workId != page!.workId) {
        throw const FormatException('Office latest version changed.');
      }
      final fresh = [...next.objects];
      while (next.hasMore &&
          !edits.keys.every((id) => fresh.any((o) => o.id == id))) {
        final offset = next.nextOffset!;
        final following = await repository.read(reopened, offset: offset);
        if (_disposed) return;
        if (following.packageSha256 != next.packageSha256 ||
            !following.current ||
            following.total != next.total ||
            following.nextOffset == offset) {
          throw const FormatException('Office comparison changed.');
        }
        next = following;
        fresh.addAll(next.objects);
      }
      comparisonSource = reopened;
      comparisonPage = next;
      _comparisonObjects = fresh;
      final map = {for (final object in fresh) object.id: object};
      comparisons = [
        for (final object in objects)
          if (edits.containsKey(object.id))
            Sh02OfficeComparison(object, map[object.id], edits[object.id]!),
      ];
    });
  }

  void adoptComparison(Set<String> selected) {
    if (busy || comparisonPage == null || comparisonSource == null) {
      return;
    }
    final wanted = {
      for (final comparison in comparisons)
        if (selected.contains(comparison.previous.id) &&
            comparison.latest != null)
          comparison.previous.id: comparison.proposed,
    };
    if (wanted.length != selected.length) return;
    source = comparisonSource!;
    page = comparisonPage;
    objects
      ..clear()
      ..addAll(_comparisonObjects);
    nextOffset = page!.nextOffset;
    edits
      ..clear()
      ..addAll(wanted);
    conflict = false;
    problem = null;
    comparisons = [];
    comparisonPage = null;
    comparisonSource = null;
    notice = null;
    _notify();
  }

  Future<void> openVersion(String artifactId) async {
    if (busy || dirty || saveUnknown || !_artifact(artifactId)) return;
    await _readOnly(() async {
      final opened = await repository.reopen(artifactId);
      if (_disposed) return;
      final next = await repository.read(opened);
      if (_disposed) return;
      if (next.workId != page?.workId) {
        throw const FormatException('Office version belongs to another work.');
      }
      if (next.version < page!.version) _newer = source;
      source = opened;
      page = next;
      objects
        ..clear()
        ..addAll(next.objects);
      nextOffset = next.nextOffset;
      conflict = false;
      problem = null;
      notice = null;
    });
  }

  Future<void> openNewer() async {
    if (_newer case final newer?) await openVersion(newer.artifactId);
  }

  Future<SavedWorkExportFile?> download() async {
    if (busy || page == null) return null;
    busy = true;
    problem = null;
    _notify();
    try {
      return await repository.download(page!);
    } catch (error) {
      if (_accessUnavailable(error)) {
        _failure(error);
      } else {
        problem = 'downloadFailed';
      }
      return null;
    } finally {
      busy = false;
      _notify();
    }
  }

  void _notify() {
    if (!_disposed) notifyListeners();
  }

  @override
  void dispose() {
    _disposed = true;
    super.dispose();
  }
}
