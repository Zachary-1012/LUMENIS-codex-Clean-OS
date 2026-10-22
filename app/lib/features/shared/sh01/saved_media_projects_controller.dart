import 'package:flutter/foundation.dart';
import 'package:lumenis_app/core/lumenis_core_client.dart';

enum SavedMediaProjectsStatus {
  idle,
  loading,
  ok,
  empty,
  scanIncomplete,
  integrityIncomplete,
  error,
}

final class SavedMediaProject {
  const SavedMediaProject({
    required this.artifactId,
    required this.outputKind,
    required this.createdAt,
    this.title,
    this.projectRevision,
    this.renderState,
  });

  final String artifactId;
  final String outputKind;
  final String createdAt;
  final String? title;
  final int? projectRevision;
  final String? renderState;
}

final class SavedMediaProjectsController extends ChangeNotifier {
  SavedMediaProjectsController({
    required this.loadPage,
    required this.contextKey,
  });

  final Future<Map<String, dynamic>> Function(String? cursor) loadPage;
  final String Function() contextKey;

  List<SavedMediaProject> _projects = const [];
  SavedMediaProjectsStatus _status = SavedMediaProjectsStatus.idle;
  bool _busy = false;
  bool _loaded = false;
  String? _errorCode;
  String? _nextCursor;
  String? _stateContext;
  final Set<String> _usedCursors = <String>{};
  int _generation = 0;
  bool _disposed = false;

  List<SavedMediaProject> get projects {
    _synchronizeContextForRead();
    return List<SavedMediaProject>.unmodifiable(_projects);
  }

  bool get busy {
    _synchronizeContextForRead();
    return _busy;
  }

  bool get loaded {
    _synchronizeContextForRead();
    return _loaded;
  }

  SavedMediaProjectsStatus get status {
    _synchronizeContextForRead();
    return _status;
  }

  String? get errorCode {
    _synchronizeContextForRead();
    return _errorCode;
  }

  String? get nextCursor {
    _synchronizeContextForRead();
    return _nextCursor;
  }

  /// Starts a fresh first-page read and immediately hides the previous list.
  /// Calling refresh again supersedes any older in-flight request.
  Future<void> refresh() async {
    if (_disposed) return;
    final context = _readContext();
    final generation = ++_generation;
    _projects = const [];
    _nextCursor = null;
    _usedCursors.clear();
    _errorCode = null;
    _loaded = false;
    _busy = true;
    _stateContext = context;
    _status = SavedMediaProjectsStatus.loading;

    if (context == null) {
      _finishContextFailure('CONTENT_CONTEXT_UNAVAILABLE');
      return;
    }
    notifyListeners();
    await _requestPage(cursor: null, context: context, generation: generation);
  }

  /// Loads one explicit next page. It never retries or follows cursors itself.
  Future<void> loadMore() async {
    if (_disposed) return;
    _synchronizeContextForRead();
    if (_busy) return;
    if (!_loaded) {
      await refresh();
      return;
    }
    final cursor = _nextCursor;
    final context = _stateContext;
    if (cursor == null || context == null) return;

    final generation = ++_generation;
    _usedCursors.add(cursor);
    _busy = true;
    _errorCode = null;
    notifyListeners();
    await _requestPage(
      cursor: cursor,
      context: context,
      generation: generation,
      append: true,
    );
  }

  /// Drops all in-memory rows and invalidates responses from older requests.
  void invalidate() {
    if (_disposed) return;
    ++_generation;
    _projects = const [];
    _busy = false;
    _loaded = false;
    _status = SavedMediaProjectsStatus.idle;
    _errorCode = null;
    _nextCursor = null;
    _stateContext = null;
    _usedCursors.clear();
    notifyListeners();
  }

  Future<void> _requestPage({
    required String? cursor,
    required String context,
    required int generation,
    bool append = false,
  }) async {
    try {
      final response = await loadPage(cursor);
      if (!_isCurrent(generation, context)) return;
      final page = _parsePage(response);
      if (!_isCurrent(generation, context)) return;

      final merged = append
          ? _mergeProjects(_projects, page.projects)
          : page.projects;
      if (page.nextCursor == cursor && page.nextCursor != null ||
          page.nextCursor != null && _usedCursors.contains(page.nextCursor)) {
        throw const FormatException('Repeated saved-project cursor.');
      }

      _projects = List<SavedMediaProject>.unmodifiable(merged);
      _nextCursor = page.nextCursor;
      _status = _combinedStatus(_status, page.status, append: append);
      _errorCode = null;
      _loaded = true;
    } catch (error) {
      if (!_isCurrent(generation, context)) return;
      _projects = const [];
      _status = SavedMediaProjectsStatus.error;
      _errorCode = _errorCodeFor(error);
      _nextCursor = null;
      _usedCursors.clear();
      _loaded = true;
    }

    if (!_isCurrent(generation, context)) return;
    _busy = false;
    notifyListeners();
  }

  _SavedMediaProjectsPage _parsePage(Map<String, dynamic> response) {
    if (response['ok'] != true ||
        response['publish_status'] != 'not_performed') {
      final returnedCode = _safeErrorCode(
        response['error_code'] ?? response['code'],
      );
      if (returnedCode != null) {
        throw _SavedMediaProjectsFailure(returnedCode);
      }
      if (response['status_code'] == 401) {
        throw const _SavedMediaProjectsFailure('CONTENT_AUTH_REQUIRED');
      }
      if (response['status_code'] == 403) {
        throw const _SavedMediaProjectsFailure('CONTENT_SCOPE_DENIED');
      }
      throw const FormatException('Saved projects were not returned.');
    }

    final status = switch (response['status']) {
      'ok' => SavedMediaProjectsStatus.ok,
      'empty' => SavedMediaProjectsStatus.empty,
      'scan_incomplete' => SavedMediaProjectsStatus.scanIncomplete,
      'integrity_incomplete' => SavedMediaProjectsStatus.integrityIncomplete,
      _ => throw const FormatException('Invalid saved-project status.'),
    };
    final rawProjects = response['projects'];
    if (rawProjects is! List || rawProjects.length > 20) {
      throw const FormatException('Invalid saved-project page.');
    }
    final projects = <SavedMediaProject>[];
    for (final rawProject in rawProjects) {
      if (rawProject is! Map) {
        throw const FormatException('Invalid saved-project row.');
      }
      final project = _parseProject(rawProject);
      final duplicateIndex = projects.indexWhere(
        (existing) => existing.artifactId == project.artifactId,
      );
      if (duplicateIndex == -1) {
        projects.add(project);
      } else if (!_sameProject(projects[duplicateIndex], project)) {
        throw const FormatException('Conflicting saved-project row.');
      }
    }

    final rawCursor = response['next_cursor'];
    if (rawCursor != null &&
        (rawCursor is! String ||
            !RegExp(r'^[A-Za-z0-9_-]{40,48}$').hasMatch(rawCursor))) {
      throw const FormatException('Invalid saved-project cursor.');
    }
    if (status == SavedMediaProjectsStatus.empty &&
        (projects.isNotEmpty || rawCursor != null)) {
      throw const FormatException('Contradictory empty saved-project page.');
    }
    return _SavedMediaProjectsPage(
      projects: List<SavedMediaProject>.unmodifiable(projects),
      status: status,
      nextCursor: rawCursor as String?,
    );
  }

  SavedMediaProject _parseProject(Map<dynamic, dynamic> row) {
    final artifactId = row['artifact_id'];
    if (artifactId is! String ||
        !RegExp(r'^ART-[A-Za-z0-9_-]{1,70}$').hasMatch(artifactId)) {
      throw const FormatException('Invalid saved-project artifact.');
    }
    final outputKind = row['output_kind'];
    if (outputKind != 'video' && outputKind != 'audio') {
      throw const FormatException('Invalid saved-project output kind.');
    }
    final createdAt = _parseTimestamp(row['created_at']);
    _parseTimestamp(row['updated_at']);
    final recordStatus = row['status'];
    if (recordStatus is! String || recordStatus.trim().isEmpty) {
      throw const FormatException('Invalid saved-project record status.');
    }
    final title = row['title'];
    final revision = row['project_revision'];
    final state = row['render_state'];
    if (title != null && (title is! String || title.trim().isEmpty || title.length > 200) ||
        revision != null && (revision is! int || revision < 1) ||
        state != null && !const ['rendered_verified', 'not_rendered'].contains(state)) {
      throw const FormatException('Invalid saved-project metadata.');
    }
    return SavedMediaProject(
      artifactId: artifactId,
      outputKind: outputKind,
      createdAt: createdAt,
      title: title as String?,
      projectRevision: revision as int?,
      renderState: state as String?,
    );
  }

  String _parseTimestamp(Object? value) {
    if (value is! String || value.length < 19 || value.length > 40) {
      throw const FormatException('Invalid saved-project timestamp.');
    }
    if (!RegExp(
          r'^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})?$',
        ).hasMatch(value) ||
        DateTime.tryParse(value) == null) {
      throw const FormatException('Invalid saved-project timestamp.');
    }
    // Keep the source timestamp unchanged. It is display metadata, not an
    // ordering or business-time authority.
    return value;
  }

  List<SavedMediaProject> _mergeProjects(
    List<SavedMediaProject> current,
    List<SavedMediaProject> incoming,
  ) {
    final merged = List<SavedMediaProject>.of(current);
    for (final project in incoming) {
      final existing = merged.cast<SavedMediaProject?>().firstWhere(
        (candidate) => candidate?.artifactId == project.artifactId,
        orElse: () => null,
      );
      if (existing == null) {
        merged.add(project);
      } else if (!_sameProject(existing, project)) {
        throw const FormatException('Conflicting saved-project row.');
      }
    }
    return merged;
  }

  bool _sameProject(SavedMediaProject left, SavedMediaProject right) =>
      left.outputKind == right.outputKind && left.createdAt == right.createdAt &&
      left.title == right.title && left.projectRevision == right.projectRevision &&
      left.renderState == right.renderState;

  SavedMediaProjectsStatus _combinedStatus(
    SavedMediaProjectsStatus previous,
    SavedMediaProjectsStatus page, {
    required bool append,
  }) {
    if (!append) return page;
    if (previous == SavedMediaProjectsStatus.integrityIncomplete ||
        page == SavedMediaProjectsStatus.integrityIncomplete) {
      return SavedMediaProjectsStatus.integrityIncomplete;
    }
    if (previous == SavedMediaProjectsStatus.scanIncomplete ||
        page == SavedMediaProjectsStatus.scanIncomplete) {
      return SavedMediaProjectsStatus.scanIncomplete;
    }
    if (page == SavedMediaProjectsStatus.empty && _projects.isNotEmpty) {
      return SavedMediaProjectsStatus.ok;
    }
    return page;
  }

  bool _isCurrent(int generation, String expectedContext) {
    if (_disposed || generation != _generation) return false;
    final currentContext = _readContext();
    if (currentContext == expectedContext) return true;
    _finishContextFailure(
      currentContext == null
          ? 'CONTENT_CONTEXT_UNAVAILABLE'
          : 'CONTENT_CONTEXT_CHANGED',
    );
    return false;
  }

  void _synchronizeContextForRead() {
    if (_disposed || _stateContext == null) return;
    final currentContext = _readContext();
    if (currentContext == _stateContext) return;
    _finishContextFailure(
      currentContext == null
          ? 'CONTENT_CONTEXT_UNAVAILABLE'
          : 'CONTENT_CONTEXT_CHANGED',
      notify: false,
    );
  }

  String? _readContext() {
    try {
      final context = contextKey();
      return context.trim().isEmpty ? null : context;
    } catch (_) {
      return null;
    }
  }

  void _finishContextFailure(String code, {bool notify = true}) {
    if (_disposed) return;
    ++_generation;
    _projects = const [];
    _busy = false;
    _loaded = true;
    _status = SavedMediaProjectsStatus.error;
    _errorCode = code;
    _nextCursor = null;
    _stateContext = null;
    _usedCursors.clear();
    if (notify) notifyListeners();
  }

  String _errorCodeFor(Object error) {
    if (error is _SavedMediaProjectsFailure) return error.code;
    if (error is FormatException) return 'CONTENT_RESPONSE_INVALID';
    if (error is LumenisCoreException) {
      final code = _safeErrorCode(error.errorCode);
      if (code != null) return code;
      if (error.statusCode == 401) return 'CONTENT_AUTH_REQUIRED';
      if (error.statusCode == 403) return 'CONTENT_SCOPE_DENIED';
    }
    return 'CONTENT_PROJECT_LIST_UNAVAILABLE';
  }

  String? _safeErrorCode(Object? value) {
    if (value is String && RegExp(r'^[A-Z][A-Z0-9_]{0,79}$').hasMatch(value)) {
      return value;
    }
    return null;
  }

  @override
  void dispose() {
    _disposed = true;
    ++_generation;
    super.dispose();
  }
}

final class _SavedMediaProjectsPage {
  const _SavedMediaProjectsPage({
    required this.projects,
    required this.status,
    required this.nextCursor,
  });

  final List<SavedMediaProject> projects;
  final SavedMediaProjectsStatus status;
  final String? nextCursor;
}

final class _SavedMediaProjectsFailure implements Exception {
  const _SavedMediaProjectsFailure(this.code);

  final String code;
}
