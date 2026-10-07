import 'dart:async';
import 'dart:convert';
import 'dart:math' as math;

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../../core/lumenis_core_client.dart';
import '../../../core/lumenis_theme.dart';
import '../../../l10n/lumenis_localizations.dart';
import '../../../navigation/lumenis_leave_guard.dart';
import 'media_preview.dart';
import '../read_aloud_action.dart';
import 'media_project_controller.dart';
import 'media_project_files.dart';
import 'media_project_snapshot.dart';
import 'saved_media_projects_controller.dart';

String _copy(BuildContext context, String key) =>
    context.lumenisL10n.text('sh01.media.$key');
String _seconds(double value) => value.toStringAsFixed(2);

String? _safeDisplayName(Object? value, String languageCode) {
  final names = value is Map ? value : null;
  final preferredLocales = switch (languageCode) {
    'zh' => const ['zh', 'en', 'ko'],
    'ko' => const ['ko', 'en', 'zh'],
    _ => const ['en', 'zh', 'ko'],
  };
  final candidates = names == null
      ? [value]
      : preferredLocales.map((locale) => names[locale]).toList();
  for (final candidate in candidates) {
    if (candidate is! String) continue;
    final name = candidate.trim();
    if (name.isNotEmpty &&
        name.length <= 120 &&
        !RegExp(r'[\x00-\x1f\x7f]').hasMatch(name)) {
      return name;
    }
  }
  return null;
}

class MediaProjectWorkbench extends StatefulWidget {
  const MediaProjectWorkbench({
    required this.client,
    required this.onBack,
    this.invokingDomain,
    this.contextAvailable = true,
    this.controller,
    this.files,
    super.key,
  });
  final LumenisCoreClient client;
  final VoidCallback onBack;
  final String? invokingDomain;
  final bool contextAvailable;
  final MediaProjectController? controller;
  final MediaProjectFiles? files;

  @override
  State<MediaProjectWorkbench> createState() => _MediaProjectWorkbenchState();
}

class _MediaProjectWorkbenchState extends State<MediaProjectWorkbench> {
  late MediaProjectController _controller;
  late SavedMediaProjectsController _savedProjects;
  String? _savedListContextKey;
  bool _controllerInitialized = false;
  bool _ownsController = false;
  bool _scopeAvailable = false;
  late final MediaProjectFiles _files = widget.files ?? MediaProjectFiles();
  final _previewKey = GlobalKey();
  final _timelineScroll = ScrollController();
  final _sheetUpdates = _SheetUpdateSignal();
  final _savedReference = TextEditingController();
  final _versions = <MediaProjectVersion>[];
  ContentProjectFile? _preview;
  String? _previewArtifact;
  String? _notice;
  bool _choosing = false;
  bool _retrieving = false;
  bool _demo = false;
  bool _sourcesVisible = true;
  bool _propertiesVisible = true;
  double _timelineFraction = .38;
  double _timelineZoom = 1;
  double? _timelinePlayheadSec;
  Duration? _previewSeekPosition;
  int _previewSeekRequest = 0;
  bool _layerOpen = false;
  final _inspectorDrafts = <String, _ClipInspectorDraft>{};
  LumenisLeaveGuard? _leaveGuard;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final nextGuard = LumenisLeaveScope.maybeOf(context);
    if (identical(nextGuard, _leaveGuard)) return;
    _leaveGuard?.unregister(this);
    _leaveGuard = nextGuard;
    _leaveGuard?.register(
      this,
      needsProtection: _needsProtection,
      requestLeave: _requestLeaveDecision,
    );
  }

  @override
  void initState() {
    super.initState();
    final context = widget.client.currentContextEnvelope?['context'];
    final mode = context is Map ? context['mode'] : null;
    final rawDomain = mode == 'FOCUS'
        ? context['domain_id']
        : mode == 'GLOBAL_ALL'
        ? widget.invokingDomain
        : null;
    final domain = rawDomain == 'CTH' || rawDomain == 'BMP'
        ? rawDomain as String
        : null;
    // A test/embedded controller can supply scope outside an active GLOBAL_ALL
    // route. GLOBAL_ALL itself always requires an explicit caller or user choice.
    final scopedControllerDomain =
        domain == null && mode != 'GLOBAL_ALL' && widget.controller != null
        ? widget.controller!.domain
        : null;
    final resolvedDomain = domain ?? scopedControllerDomain;
    _scopeAvailable = resolvedDomain != null;
    if (resolvedDomain != null) {
      _attachController(resolvedDomain);
      if (!widget.contextAvailable) _controller.quarantineDraftSources();
    }
  }

  @override
  void didUpdateWidget(covariant MediaProjectWorkbench oldWidget) {
    super.didUpdateWidget(oldWidget);
    final savedContextChanged =
        _controllerInitialized && _savedListContextKey != _savedContextKey;
    if (savedContextChanged) _savedListContextKey = _savedContextKey;
    if (oldWidget.contextAvailable && !widget.contextAvailable) {
      if (_controllerInitialized) {
        _controller.quarantineDraftSources();
      }
      _leaveGuard?.refresh();
    } else if (oldWidget.contextAvailable != widget.contextAvailable) {
      _leaveGuard?.refresh();
    }
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      if (_controllerInitialized &&
          (!widget.contextAvailable || savedContextChanged)) {
        _savedProjects.invalidate();
      }
      _sheetUpdates.refresh();
    });
  }

  void _attachController(String domain) {
    final supplied = widget.controller;
    if (supplied != null && supplied.domain == domain) {
      _controller = supplied;
      _ownsController = false;
    } else {
      _controller = MediaProjectController(
        repository: CoreMediaProjectRepository(widget.client),
        domain: domain,
      );
      _ownsController = true;
    }
    _controllerInitialized = true;
    _controller.addListener(_changed);
    _savedListContextKey = _savedContextKey;
    _savedProjects = SavedMediaProjectsController(
      loadPage: (cursor) =>
          widget.client.listContentProjects(domainId: domain, cursor: cursor),
      contextKey: () => _savedContextKey,
    );
  }

  String get _savedContextKey =>
      '${widget.contextAvailable}:${_controller.domain}:${jsonEncode(widget.client.currentContextEnvelope)}';

  void _chooseInvokingDomain(String domain) {
    if (_controllerInitialized) {
      _controller.removeListener(_changed);
      _savedProjects.dispose();
      if (_ownsController) _controller.dispose();
    }
    _attachController(domain);
    setState(() => _scopeAvailable = true);
    _leaveGuard?.refresh();
  }

  void _changed() {
    if (!mounted) return;
    _sheetUpdates.refresh();
    _leaveGuard?.refresh();
    final version = _controller.version;
    if (version != null &&
        !_versions.any((v) => v.artifactId == version.artifactId)) {
      _versions.add(version);
    }
    if (_previewArtifact != version?.artifactId) {
      _preview = null;
      _previewArtifact = null;
    }
    setState(() {});
  }

  @override
  void dispose() {
    _leaveGuard?.unregister(this);
    if (_controllerInitialized) {
      _controller.removeListener(_changed);
      _savedProjects.dispose();
      if (_ownsController) _controller.dispose();
    }
    _timelineScroll.dispose();
    _savedReference.dispose();
    _sheetUpdates.dispose();
    super.dispose();
  }

  bool get _isBusy =>
      _choosing || _retrieving || _controllerInitialized && _controller.busy;

  String get _operationCopyKey => _retrieving
      ? 'saved_loading'
      : switch (_controller.operation) {
          MediaProjectOperation.exporting => 'exporting',
          MediaProjectOperation.reopening => 'saved_loading',
          _ => 'importing',
        };

  bool get _hasUnappliedInspectorDrafts {
    if (_inspectorDrafts.isEmpty) return false;
    final timeline = _controllerInitialized ? _controller.timeline : null;
    for (final entry in _inspectorDrafts.entries) {
      final clip = timeline?.tracks
          .expand((track) => track.clips)
          .where((candidate) => candidate.clipId == entry.key)
          .firstOrNull;
      if (clip == null) return true;
      final expected = <String, String>{
        'source_in': _seconds(clip.sourceIn),
        'source_out': _seconds(clip.sourceOut),
        'position': _seconds(clip.timelineStart),
        'gain': _seconds(clip.audioMix.volume),
        'fade_in': _seconds(clip.audioMix.fadeInSec),
        'fade_out': _seconds(clip.audioMix.fadeOutSec),
        'split_position': _seconds((clip.sourceIn + clip.sourceOut) / 2),
      };
      if (entry.value.values.entries.any(
        (value) => expected[value.key] != value.value,
      )) {
        return true;
      }
      final stream = clip.audioRole == 'muted' ? -1 : clip.audioStreamIndex;
      if (entry.value.stream != stream) return true;
    }
    return false;
  }

  bool get _hasUnsavedChanges =>
      _controllerInitialized && _controller.hasUnsavedChanges ||
      _hasUnappliedInspectorDrafts;

  bool get _canUseCurrentContext {
    if (!_controllerInitialized) return false;
    final contextMatches = _controller.contextMatches;
    return contextMatches && widget.contextAvailable;
  }

  bool _needsProtection() => _isBusy || _hasUnsavedChanges;

  Future<bool> _requestLeaveDecision() async {
    if (_isBusy) return false;
    if (!_hasUnsavedChanges) return true;
    return await showDialog<bool>(
          context: context,
          builder: (context) => AlertDialog(
            title: Text(_copy(context, 'discard')),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context, false),
                child: Text(_copy(context, 'cancel')),
              ),
              FilledButton(
                onPressed: () => Navigator.pop(context, true),
                child: Text(_copy(context, 'discard_confirm')),
              ),
            ],
          ),
        ) ==
        true;
  }

  Future<bool> _requestLeave() async {
    final guard = _leaveGuard ?? LumenisLeaveScope.maybeOf(context);
    return guard == null ? _requestLeaveDecision() : guard.requestLeave();
  }

  Future<void> _leaveEditor() async {
    if (await _requestLeave() && mounted) widget.onBack();
  }

  Future<void> _reopen(String artifactId) async {
    if (_isBusy || !_canUseCurrentContext) return;
    if (!await _requestLeave() || !mounted || !_canUseCurrentContext) return;
    setState(() => _notice = null);
    await _controller.reopen(artifactId, discardExisting: true);
    if (!mounted) return;
    if (_controller.failureCode == null &&
        _controller.version?.artifactId == artifactId) {
      _inspectorDrafts.clear();
      _savedReference.text = artifactId;
      _leaveGuard?.refresh();
    }
    _sheetUpdates.refresh();
    setState(() {});
  }

  Future<void> _openSavedWork() async {
    if (_isBusy || !_canUseCurrentContext) return;
    var invalid = false;
    unawaited(_savedProjects.refresh());
    final reference = await showDialog<String>(
      context: context,
      builder: (dialogContext) => AnimatedBuilder(
        animation: _savedProjects,
        builder: (_, _) => StatefulBuilder(
          builder: (context, updateDialog) {
            void submit() {
              final value = _savedReference.text.trim();
              if (!RegExp(r'^ART-[A-Za-z0-9_-]{1,70}$').hasMatch(value)) {
                updateDialog(() => invalid = true);
                return;
              }
              Navigator.of(dialogContext).pop(value);
            }

            return AlertDialog(
              scrollable: true,
              title: Text(_copy(context, 'open_saved')),
              content: SizedBox(
                width: 420,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    _savedProjectList(dialogContext),
                    const Divider(height: 32),
                    TextField(
                      key: const Key('media-saved-reference'),
                      controller: _savedReference,
                      autocorrect: false,
                      enableSuggestions: false,
                      textInputAction: TextInputAction.go,
                      decoration: InputDecoration(
                        labelText: _copy(context, 'saved_reference'),
                        helperText: _copy(context, 'saved_reference_hint'),
                        helperMaxLines: 4,
                        errorText: invalid
                            ? _copy(context, 'saved_reference_invalid')
                            : null,
                        errorMaxLines: 3,
                      ),
                      onSubmitted: (_) => submit(),
                    ),
                  ],
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.of(dialogContext).pop(),
                  child: Text(_copy(context, 'cancel')),
                ),
                FilledButton(
                  key: const Key('media-confirm-open-saved'),
                  style: FilledButton.styleFrom(
                    minimumSize: const Size(48, 48),
                  ),
                  onPressed: submit,
                  child: Text(_copy(context, 'reopen')),
                ),
              ],
            );
          },
        ),
      ),
    );
    if (reference != null && mounted) await _reopen(reference);
  }

  Widget _savedProjectList(BuildContext dialogContext) {
    if (!_canUseCurrentContext) return Text(_copy(context, 'context'));
    final library = _savedProjects;
    final error = library.errorCode;
    final denied =
        error != null &&
        (error.contains('DENIED') ||
            error.contains('AUTH') ||
            error.contains('CONTEXT'));
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (library.busy) ...[
          const LinearProgressIndicator(),
          const SizedBox(height: 8),
          Text(_copy(context, 'saved_loading')),
        ],
        if (error != null)
          Semantics(
            liveRegion: true,
            child: Text(_copy(context, denied ? 'denied' : 'saved_failed')),
          ),
        if (library.loaded && library.status == SavedMediaProjectsStatus.empty)
          Text(_copy(context, 'saved_empty')),
        if (library.status == SavedMediaProjectsStatus.scanIncomplete ||
            library.status == SavedMediaProjectsStatus.integrityIncomplete)
          Text(_copy(context, 'saved_partial')),
        for (final project in library.projects)
          Padding(
            padding: const EdgeInsets.only(top: 12),
            child: OutlinedButton(
              key: Key('media-saved-project-${project.artifactId}'),
              style: OutlinedButton.styleFrom(minimumSize: const Size(48, 48)),
              onPressed: () =>
                  Navigator.of(dialogContext).pop(project.artifactId),
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: 12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      _copy(
                        context,
                        project.outputKind == 'video'
                            ? 'saved_video'
                            : 'saved_audio',
                      ),
                    ),
                    Text(project.artifactId),
                    Text(project.createdAt),
                  ],
                ),
              ),
            ),
          ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 12,
          children: [
            TextButton.icon(
              key: const Key('media-saved-refresh'),
              style: TextButton.styleFrom(minimumSize: const Size(48, 48)),
              onPressed: library.busy ? null : library.refresh,
              icon: const Icon(Icons.refresh_rounded),
              label: Text(_copy(context, 'saved_refresh')),
            ),
            if (library.nextCursor != null)
              TextButton(
                key: const Key('media-saved-more'),
                style: TextButton.styleFrom(minimumSize: const Size(48, 48)),
                onPressed: library.busy ? null : library.loadMore,
                child: Text(_copy(context, 'saved_more')),
              ),
          ],
        ),
      ],
    );
  }

  Future<void> _copyReference(String reference) async {
    try {
      await Clipboard.setData(ClipboardData(text: reference));
      if (!mounted || !_canUseCurrentContext) return;
      setState(() => _notice = 'copied_reference');
    } catch (_) {
      if (mounted) setState(() => _notice = 'failure');
    }
    if (mounted) _sheetUpdates.refresh();
  }

  Widget _openSavedButton(String key) => OutlinedButton.icon(
    key: Key(key),
    style: OutlinedButton.styleFrom(minimumSize: const Size(48, 48)),
    onPressed: _isBusy || !_canUseCurrentContext ? null : _openSavedWork,
    icon: const Icon(Icons.folder_open_outlined),
    label: Text(_copy(context, 'open_saved')),
  );

  Future<void> _recoverDraftSources() async {
    if (!_controllerInitialized || !widget.contextAvailable || _isBusy) return;
    await _controller.recoverDraftSources();
    if (!mounted) return;
    _leaveGuard?.refresh();
    setState(() {});
  }

  Future<void> _choose() async {
    if (_choosing || _controller.busy || !_canUseCurrentContext) return;
    setState(() {
      _choosing = true;
      _notice = null;
    });
    _leaveGuard?.refresh();
    try {
      final files = await _files.choose();
      for (final file in files) {
        if (!mounted) return;
        if (await file.length() > MediaProjectFiles.maxImportBytes) {
          throw const FormatException();
        }
        final bytes = await file.readAsBytes();
        if (bytes.length > MediaProjectFiles.maxImportBytes) {
          throw const FormatException();
        }
        await _controller.importFile(
          file.name,
          bytes,
          requestApproval: _confirmSourceImport,
        );
        if (_controller.failureCode != null) break;
      }
    } catch (_) {
      if (mounted) setState(() => _notice = 'failure');
    } finally {
      if (mounted) {
        setState(() => _choosing = false);
        _leaveGuard?.refresh();
      }
    }
  }

  Future<bool?> _confirmSourceImport(
    ContentSourceConfirmation confirmation,
  ) async {
    final contextEnvelope = widget.client.currentContextEnvelope?['context'];
    if (contextEnvelope is! Map) {
      return null;
    }
    final mode = contextEnvelope['mode'];
    final domain = contextEnvelope['domain_id'];
    final subjectId = contextEnvelope['subject_id'];
    final focused = mode == 'FOCUS';
    final global = mode == 'GLOBAL_ALL';
    final invokedDomain = global ? _controller.domain : domain;
    if ((!focused && !global) ||
        (invokedDomain != 'CTH' && invokedDomain != 'BMP') ||
        (global &&
            widget.invokingDomain != null &&
            widget.invokingDomain != invokedDomain) ||
        invokedDomain != _controller.domain ||
        (focused && (subjectId is! String || subjectId.isEmpty))) {
      return null;
    }
    final businessName = context.lumenisL10n.text(
      invokedDomain == 'CTH' ? 'navgroup.cth' : 'navgroup.bmp',
    );
    final focusName = focused
        ? _safeDisplayName(
            contextEnvelope['display_name'],
            Localizations.localeOf(context).languageCode,
          )
        : null;
    final scope = focused
        ? [businessName, ?focusName, _copy(context, 'focus_scope')].join(' · ')
        : '${_copy(context, 'global_all')} · $businessName';
    final purpose = _copy(
      context,
      invokedDomain == 'CTH' ? 'purpose_cth' : 'purpose_bmp',
    );
    var expiredOnAttempt = !confirmation.expiresAt.isAfter(DateTime.now());
    var contextChanged = false;
    bool stillInScope() {
      final current = widget.client.currentContextEnvelope?['context'];
      if (current is! Map || current['mode'] != mode) return false;
      if (global) {
        return widget.client.currentContextEnvelope?['context'] is Map &&
            (widget.invokingDomain == null ||
                widget.invokingDomain == invokedDomain) &&
            _controller.domain == invokedDomain;
      }
      return current['domain_id'] == domain &&
          current['subject_id'] == subjectId;
    }

    return await showDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (dialogContext) => StatefulBuilder(
        builder: (dialogContext, setDialogState) => AlertDialog(
          title: Text(_copy(dialogContext, 'approval_title')),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(_copy(dialogContext, 'approval_purpose')),
                const SizedBox(height: 8),
                Text(purpose),
                const SizedBox(height: 12),
                Text(
                  _copy(dialogContext, 'approval_file')
                      .replaceAll('{name}', confirmation.filename)
                      .replaceAll('{size}', confirmation.sizeBytes.toString()),
                ),
                const SizedBox(height: 8),
                Text(
                  _copy(
                    dialogContext,
                    'approval_scope',
                  ).replaceAll('{scope}', scope),
                ),
                if (expiredOnAttempt)
                  Padding(
                    padding: const EdgeInsets.only(top: 12),
                    child: Semantics(
                      liveRegion: true,
                      child: Text(_copy(dialogContext, 'approval_expired')),
                    ),
                  ),
                if (contextChanged)
                  Padding(
                    padding: const EdgeInsets.only(top: 12),
                    child: Semantics(
                      liveRegion: true,
                      child: Text(_copy(dialogContext, 'context')),
                    ),
                  ),
                const SizedBox(height: 8),
                ExpansionTile(
                  key: const Key('media-import-technical-details'),
                  tilePadding: EdgeInsets.zero,
                  title: Text(
                    _copy(dialogContext, 'approval_technical_details'),
                  ),
                  children: [
                    if (focused)
                      SelectableText(
                        '${_copy(dialogContext, 'approval_subject_id')}: $subjectId',
                      ),
                    Text(_copy(dialogContext, 'approval_hash')),
                    SelectableText(confirmation.bodySha256),
                    Text(
                      _copy(dialogContext, 'approval_expiry').replaceAll(
                        '{expiry}',
                        confirmation.expiresAt.toLocal().toString(),
                      ),
                    ),
                    SelectableText(
                      '${_copy(dialogContext, 'approval_confirmation_id')}: ${confirmation.confirmationId}',
                    ),
                    SelectableText(
                      '${_copy(dialogContext, 'approval_resource')}: ${confirmation.resource}',
                    ),
                  ],
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext, false),
              child: Text(_copy(dialogContext, 'cancel')),
            ),
            FilledButton(
              onPressed: () {
                if (!confirmation.expiresAt.isAfter(DateTime.now())) {
                  setDialogState(() => expiredOnAttempt = true);
                  return;
                }
                if (!stillInScope()) {
                  setDialogState(() => contextChanged = true);
                  return;
                }
                Navigator.pop(dialogContext, true);
              },
              child: Text(_copy(dialogContext, 'approval_confirm')),
            ),
          ],
        ),
      ),
    );
  }

  bool _edit(MediaProjectSnapshot Function(MediaProjectSnapshot) operation) {
    if (!_canUseCurrentContext) return false;
    try {
      _controller.edit(operation);
      final remainingClips =
          _controller.timeline?.tracks
              .expand((track) => track.clips)
              .map((clip) => clip.clipId)
              .toSet() ??
          <String>{};
      _inspectorDrafts.removeWhere((id, _) => !remainingClips.contains(id));
      setState(() => _notice = null);
      _leaveGuard?.refresh();
      _sheetUpdates.refresh();
      return true;
    } on FormatException {
      setState(() => _notice = 'invalid');
    } on StateError {
      setState(() => _notice = 'invalid');
    }
    return false;
  }

  Future<void> _add(MediaProjectAsset asset) async {
    final result = await showDialog<_NewClip>(
      context: context,
      builder: (context) => _AddClipDialog(asset: asset),
    );
    if (result == null || !mounted) return;
    _edit((timeline) {
      final role = result.role;
      var next = timeline;
      if (role != 'video' && !next.tracks.any((t) => t.trackId == role)) {
        next = next.addAudioTrack(role, audioRole: role);
      }
      return next.addClip(
        asset.assetId,
        trackId: role,
        sourceIn: result.start,
        sourceOut: result.end,
        audioStreamIndex: result.stream,
        audioRole: role == 'video' ? 'original' : role,
      );
    });
    final clips = _controller.timeline?.tracks
        .where((t) => t.trackId == result.role)
        .firstOrNull
        ?.clips;
    if (_notice == null && clips != null && clips.isNotEmpty) {
      _controller.selectClip(clips.last.clipId);
    }
  }

  Future<void> _retrieve({
    required bool download,
    BuildContext? actionsSheetContext,
  }) async {
    final version = _controller.version;
    if (version == null || _retrieving || !_canUseCurrentContext) return;
    final scope = _controller.repository.contextKey;
    if (!download && actionsSheetContext != null) {
      Navigator.of(actionsSheetContext).pop();
    }
    setState(() {
      _retrieving = true;
      _notice = null;
    });
    _leaveGuard?.refresh();
    _sheetUpdates.refresh();
    try {
      final file = await widget.client.contentProjectFile(
        domainId: _controller.domain,
        artifactId: version.artifactId,
        package: download,
      );
      if (!mounted ||
          _controller.repository.contextKey != scope ||
          _controller.version?.artifactId != version.artifactId) {
        return;
      }
      if (download) {
        final saved = await _files.save(file);
        if (mounted && saved) {
          setState(
            () => _notice = kIsWeb ? 'download_handoff' : 'download_saved',
          );
        }
      } else {
        setState(() {
          _preview = file;
          _previewArtifact = version.artifactId;
        });
        _revealPreview(scope, version.artifactId);
      }
    } catch (_) {
      if (mounted) setState(() => _notice = 'failure');
    } finally {
      if (mounted) {
        setState(() => _retrieving = false);
        _leaveGuard?.refresh();
        _sheetUpdates.refresh();
      }
    }
  }

  void _revealPreview(String scope, String artifactId) {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final previewContext = _previewKey.currentContext;
      if (!mounted ||
          previewContext == null ||
          !_canUseCurrentContext ||
          _controller.repository.contextKey != scope ||
          _controller.version?.artifactId != artifactId ||
          _previewArtifact != artifactId) {
        return;
      }
      unawaited(
        Scrollable.ensureVisible(
          previewContext,
          alignment: 0.08,
          duration: MediaQuery.disableAnimationsOf(context)
              ? Duration.zero
              : const Duration(milliseconds: 240),
          curve: Curves.easeInOutCubic,
        ),
      );
    });
  }

  String? get _failure {
    final code = _controller.failureCode;
    if (code == null) return null;
    if (code.contains('TIMEOUT') || code.contains('COMPLETION_UNKNOWN')) {
      return 'timeout';
    }
    if (code == 'CONTENT_APPROVAL_PENDING') return 'approval_pending';
    if (code == 'CONTENT_IMPORT_CANCELLED') return 'approval_cancelled';
    if (code == 'CONTENT_FOCUS_REQUIRED') return 'focus_required';
    if (code == 'CONTENT_PROJECT_NO_CHANGES' ||
        code == 'CONTENT_PROJECT_PARENT_REVISION_REQUIRED') {
      return 'no_changes';
    }
    if (code.contains('CONTEXT')) return 'context';
    if (code.contains('AUTH') || code.contains('DENIED')) return 'denied';
    if (code == 'CONTENT_SOURCE_ALREADY_ADDED') return 'duplicate';
    if (code == 'CONTENT_DEMO_ACKNOWLEDGEMENT_REQUIRED') return 'demo';
    return 'failure';
  }

  @override
  Widget build(BuildContext context) {
    if (!_scopeAvailable) {
      final contextValue = widget.client.currentContextEnvelope?['context'];
      final needsInvokingDomain =
          contextValue is Map &&
          contextValue['mode'] == 'GLOBAL_ALL' &&
          widget.invokingDomain != 'CTH' &&
          widget.invokingDomain != 'BMP';
      return Material(
        color: LumenisTheme.of(context).canvas,
        child: SafeArea(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 560),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      _copy(context, 'title'),
                      style: Theme.of(context).textTheme.headlineSmall,
                    ),
                    const SizedBox(height: 12),
                    if (needsInvokingDomain) ...[
                      Semantics(
                        liveRegion: true,
                        child: Text(
                          _copy(context, 'choose_business_purpose_body'),
                        ),
                      ),
                      const SizedBox(height: 18),
                      Wrap(
                        spacing: 12,
                        runSpacing: 12,
                        children: [
                          FilledButton.icon(
                            key: const Key('media-domain-cth'),
                            style: FilledButton.styleFrom(
                              minimumSize: const Size(48, 48),
                            ),
                            onPressed: () => _chooseInvokingDomain('CTH'),
                            icon: const Icon(Icons.storefront_outlined),
                            label: Text(
                              context.lumenisL10n.text('navgroup.cth'),
                            ),
                          ),
                          OutlinedButton.icon(
                            key: const Key('media-domain-bmp'),
                            style: OutlinedButton.styleFrom(
                              minimumSize: const Size(48, 48),
                            ),
                            onPressed: () => _chooseInvokingDomain('BMP'),
                            icon: const Icon(Icons.branding_watermark_outlined),
                            label: Text(
                              context.lumenisL10n.text('navgroup.bmp'),
                            ),
                          ),
                        ],
                      ),
                    ] else ...[
                      Semantics(
                        liveRegion: true,
                        child: Text(_copy(context, 'focus_required')),
                      ),
                    ],
                    const SizedBox(height: 18),
                    OutlinedButton.icon(
                      style: OutlinedButton.styleFrom(
                        minimumSize: const Size(48, 48),
                      ),
                      onPressed: _leaveEditor,
                      icon: const Icon(Icons.arrow_back_rounded),
                      label: Text(_copy(context, 'back')),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      );
    }
    final palette = LumenisTheme.of(context);
    final timeline = _canUseCurrentContext ? _controller.timeline : null;
    return Material(
      color: palette.canvas,
      child: SafeArea(
        child: LayoutBuilder(
          builder: (context, constraints) {
            final textSize = MediaQuery.textScalerOf(context).scale(14);
            final wide = constraints.maxWidth >= 1180 && textSize <= 22;
            final compact = constraints.maxWidth < 700 || textSize > 22;
            final height = constraints.hasBoundedHeight
                ? constraints.maxHeight
                : MediaQuery.sizeOf(context).height;
            return SizedBox(
              height: height,
              child: Padding(
                padding: EdgeInsets.all(compact ? 8 : 12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    ConstrainedBox(
                      constraints: BoxConstraints(maxHeight: height * .36),
                      child: SingleChildScrollView(
                        child: _editorHeader(
                          timeline,
                          wide: wide,
                          compact: compact,
                        ),
                      ),
                    ),
                    const SizedBox(height: 4),
                    Expanded(
                      key: const ValueKey('media-editing-stage'),
                      child: LayoutBuilder(
                        builder: (context, area) {
                          final minimumHeight = textSize > 22 ? 560.0 : 460.0;
                          final editingHeight = math.max(
                            minimumHeight,
                            area.maxHeight,
                          );
                          final timelineHeight =
                              (editingHeight * _timelineFraction).clamp(
                                180.0,
                                editingHeight - 260.0,
                              );
                          return SingleChildScrollView(
                            key: const Key('media-editing-region-scroll'),
                            physics: area.maxHeight >= editingHeight
                                ? const NeverScrollableScrollPhysics()
                                : null,
                            child: SizedBox(
                              height: editingHeight,
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.stretch,
                                children: [
                                  Expanded(
                                    child: Row(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.stretch,
                                      children: [
                                        if (wide && _sourcesVisible) ...[
                                          SizedBox(
                                            width: 232,
                                            child: SingleChildScrollView(
                                              key: const Key(
                                                'media-source-rail',
                                              ),
                                              child: _sources(timeline),
                                            ),
                                          ),
                                          const SizedBox(width: 1),
                                        ],
                                        Expanded(
                                          key: const ValueKey(
                                            'media-preview-stage',
                                          ),
                                          child: _previewArea(),
                                        ),
                                        if (wide && _propertiesVisible) ...[
                                          const SizedBox(width: 1),
                                          SizedBox(
                                            width: 280,
                                            child: SingleChildScrollView(
                                              key: const Key(
                                                'media-property-rail',
                                              ),
                                              child: _inspector(
                                                timeline,
                                                _selectedClip(timeline),
                                              ),
                                            ),
                                          ),
                                        ],
                                      ],
                                    ),
                                  ),
                                  SizedBox(
                                    key: const Key('media-timeline-region'),
                                    height: timelineHeight,
                                    child: _timeline(timeline),
                                  ),
                                ],
                              ),
                            ),
                          );
                        },
                      ),
                    ),
                  ],
                ),
              ),
            );
          },
        ),
      ),
    );
  }

  Widget _editorHeader(
    MediaProjectSnapshot? timeline, {
    required bool wide,
    required bool compact,
  }) {
    final notice = _failure ?? _notice;
    final version = _controller.version;
    final status = timeline == null && version == null
        ? context.lumenisL10n.text(
            _controller.domain == 'CTH' ? 'navgroup.cth' : 'navgroup.bmp',
          )
        : _copy(context, _hasUnsavedChanges ? 'draft' : 'saved');
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            IconButton(
              key: const Key('media-editor-back'),
              tooltip: _copy(context, 'back'),
              constraints: const BoxConstraints(minWidth: 48, minHeight: 48),
              onPressed: _isBusy ? null : _leaveEditor,
              icon: const Icon(Icons.arrow_back_rounded),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    _copy(context, 'title'),
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  Text(status, style: Theme.of(context).textTheme.bodySmall),
                ],
              ),
            ),
            if (wide) _editorTools(timeline, wide: wide),
            const SizedBox(width: 8),
            if (compact)
              IconButton(
                key: const Key('media-open-saved'),
                tooltip: _copy(context, 'open_saved'),
                constraints: const BoxConstraints(minWidth: 48, minHeight: 48),
                onPressed: _isBusy || !_canUseCurrentContext
                    ? null
                    : _openSavedWork,
                icon: const Icon(Icons.folder_open_outlined),
              )
            else
              _openSavedButton('media-open-saved'),
            const SizedBox(width: 8),
            if (compact)
              IconButton.filled(
                key: const Key('media-open-actions'),
                tooltip: _copy(context, 'versions_export'),
                constraints: const BoxConstraints(minWidth: 48, minHeight: 48),
                onPressed: _openActionsSheet,
                icon: const Icon(Icons.ios_share_rounded),
              )
            else
              FilledButton.icon(
                key: const Key('media-open-actions'),
                style: FilledButton.styleFrom(minimumSize: const Size(48, 48)),
                onPressed: _openActionsSheet,
                icon: const Icon(Icons.ios_share_rounded),
                label: Text(_copy(context, 'versions_export')),
              ),
          ],
        ),
        if (!wide) _editorTools(timeline, wide: wide),
        if (_isBusy && !_layerOpen) ...[
          const LinearProgressIndicator(),
          Semantics(
            liveRegion: true,
            child: Text(_copy(context, _operationCopyKey)),
          ),
        ],
        if (notice != null && !_layerOpen)
          Semantics(liveRegion: true, child: Text(_copy(context, notice))),
        if (!_canUseCurrentContext) Text(_copy(context, 'context')),
        if (widget.contextAvailable && _controller.sourcesNeedRevalidation)
          Align(
            alignment: Alignment.centerLeft,
            child: OutlinedButton.icon(
              key: const Key('media-recover-draft-sources'),
              style: OutlinedButton.styleFrom(minimumSize: const Size(48, 48)),
              onPressed: _isBusy ? null : _recoverDraftSources,
              icon: const Icon(Icons.refresh_rounded),
              label: Text(_copy(context, 'recover_sources')),
            ),
          ),
      ],
    );
  }

  Widget _editorTools(MediaProjectSnapshot? timeline, {required bool wide}) =>
      Wrap(
        spacing: 8,
        runSpacing: 4,
        children: [
          _areaButton(
            key: 'media-open-sources',
            title: 'sources',
            icon: Icons.video_library_outlined,
            selected: wide && _sourcesVisible,
            onPressed: () {
              if (wide) {
                setState(() => _sourcesVisible = !_sourcesVisible);
              } else {
                _openLayerSheet(
                  title: _copy(context, 'sources'),
                  content: (_, sheetContext) => _sources(
                    _canUseCurrentContext ? _controller.timeline : null,
                    onChoose: () {
                      Navigator.of(sheetContext).pop();
                      _choose();
                    },
                  ),
                );
              }
            },
          ),
          _areaButton(
            key: 'media-open-properties',
            title: 'properties',
            icon: Icons.tune_rounded,
            selected: wide && _propertiesVisible,
            onPressed: () {
              if (wide) {
                setState(() => _propertiesVisible = !_propertiesVisible);
              } else {
                _openLayerSheet(
                  title: _copy(context, 'properties'),
                  content: (_, _) {
                    final latest = _canUseCurrentContext
                        ? _controller.timeline
                        : null;
                    return _inspector(latest, _selectedClip(latest));
                  },
                );
              }
            },
          ),
          IconButton(
            key: const Key('media-toolbar-undo'),
            tooltip: _copy(context, 'undo'),
            constraints: const BoxConstraints(minWidth: 48, minHeight: 48),
            onPressed: timeline?.canUndo == true && !_isBusy
                ? () => _edit((s) => s.undo())
                : null,
            icon: const Icon(Icons.undo_rounded),
          ),
        ],
      );

  Widget _areaButton({
    required String key,
    required String title,
    required IconData icon,
    required bool selected,
    required VoidCallback onPressed,
  }) => Semantics(
    selected: selected,
    child: OutlinedButton.icon(
      key: Key(key),
      style: OutlinedButton.styleFrom(
        minimumSize: const Size(48, 48),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(4)),
        backgroundColor: selected
            ? LumenisTheme.of(context).surfaceRaised
            : null,
      ),
      onPressed: onPressed,
      icon: Icon(icon),
      label: Text(_copy(context, title)),
    ),
  );

  Widget _previewArea() {
    final version = _controller.version;
    final available = _canUseCurrentContext && _preview != null;
    final canPreview = _canUseCurrentContext && version != null;
    final theme = Theme.of(context);
    final mediaTheme = theme.copyWith(
      brightness: Brightness.dark,
      colorScheme: theme.colorScheme.copyWith(
        brightness: Brightness.dark,
        surface: const Color(0xff181a1d),
        onSurface: Colors.white,
        onSurfaceVariant: Colors.white70,
        primary: Colors.white,
      ),
      textTheme: theme.textTheme.apply(
        bodyColor: Colors.white,
        displayColor: Colors.white,
      ),
      iconTheme: const IconThemeData(color: Colors.white),
    );
    return Container(
      key: _previewKey,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: LumenisTheme.of(context).surface,
        border: Border.all(color: LumenisTheme.of(context).line),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            '${_copy(context, 'rendered_preview')}'
            '${canPreview ? ' · v${version.timelineVersion} · ${_seconds(version.durationSec)} s' : ''}',
            style: theme.textTheme.labelLarge,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),
          if (available && _hasUnsavedChanges)
            Flexible(
              child: SingleChildScrollView(
                child: Semantics(
                  liveRegion: true,
                  child: Text(
                    _copy(context, 'previous_render'),
                    key: const Key('media-previous-render'),
                    style: theme.textTheme.bodySmall,
                  ),
                ),
              ),
            ),
          const SizedBox(height: 8),
          Expanded(
            flex: 4,
            child: ClipRRect(
              borderRadius: BorderRadius.circular(6),
              child: ColoredBox(
                key: const Key('media-preview-matte'),
                color: const Color(0xff181a1d),
                child: Theme(
                  data: mediaTheme,
                  child: DefaultTextStyle.merge(
                    style: const TextStyle(color: Colors.white),
                    child: available
                        ? MediaPreview(
                            file: _preview!,
                            seekPosition: _previewSeekPosition,
                            seekRequest: _previewSeekRequest,
                            onPositionChanged: _onPreviewPosition,
                          )
                        : Center(
                            child: SingleChildScrollView(
                              padding: const EdgeInsets.all(16),
                              child: canPreview
                                  ? OutlinedButton.icon(
                                      key: const Key('media-load-preview'),
                                      style: OutlinedButton.styleFrom(
                                        foregroundColor: Colors.white,
                                        side: const BorderSide(
                                          color: Colors.white54,
                                        ),
                                        minimumSize: const Size(48, 48),
                                      ),
                                      onPressed: _isBusy
                                          ? null
                                          : () => _retrieve(download: false),
                                      icon: const Icon(
                                        Icons.play_circle_outline_rounded,
                                      ),
                                      label: Text(_copy(context, 'preview')),
                                    )
                                  : Text(_copy(context, 'preview_empty')),
                            ),
                          ),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  void _onPreviewPosition(Duration position) {
    final timeline = _canUseCurrentContext ? _controller.timeline : null;
    if (!mounted ||
        timeline == null ||
        timeline.durationSec <= 0 ||
        !_previewMatchesDraft) {
      return;
    }
    final seconds = (position.inMicroseconds / Duration.microsecondsPerSecond)
        .clamp(0.0, timeline.durationSec);
    if (_timelinePlayheadSec != null &&
        (_timelinePlayheadSec! - seconds).abs() < .03) {
      return;
    }
    setState(() => _timelinePlayheadSec = seconds);
  }

  void _seekFromTimeline(double seconds) {
    final timeline = _canUseCurrentContext ? _controller.timeline : null;
    if (timeline == null || timeline.durationSec <= 0) return;
    final clamped = seconds.clamp(0.0, timeline.durationSec);
    setState(() {
      _timelinePlayheadSec = clamped;
      if (_previewMatchesDraft) {
        _previewSeekPosition = Duration(
          microseconds: (clamped * Duration.microsecondsPerSecond).round(),
        );
        _previewSeekRequest++;
      }
    });
  }

  bool get _previewMatchesDraft =>
      _preview != null &&
      !_controller.hasUnsavedChanges &&
      _previewArtifact == _controller.version?.artifactId;

  void _seekBy(double delta) {
    _seekFromTimeline((_timelinePlayheadSec ?? 0) + delta);
  }

  Future<void> _openLayerSheet({
    required String title,
    required Widget Function(
      StateSetter setSheetState,
      BuildContext sheetContext,
    )
    content,
  }) => _showLayerSheet(title: title, content: content);

  MediaProjectClip? _selectedClip(MediaProjectSnapshot? timeline) => timeline
      ?.tracks
      .expand((track) => track.clips)
      .where((clip) => clip.clipId == _controller.selectedClipId)
      .firstOrNull;

  Widget _inspector(MediaProjectSnapshot? timeline, MediaProjectClip? clip) =>
      _pane(
        context,
        'properties',
        _ClipInspector(
          timeline: timeline,
          clip: clip,
          onEdit: _edit,
          draft: clip == null ? null : _inspectorDrafts[clip.clipId],
          onDraftChanged: _updateInspectorDraft,
        ),
      );

  Future<void> _openActionsSheet() => _showLayerSheet(
    title: _copy(context, 'versions_export'),
    content: (setSheetState, sheetContext) => _actions(
      _canUseCurrentContext ? _controller.timeline : null,
      setSheetState: setSheetState,
      actionsSheetContext: sheetContext,
    ),
  );

  void _updateInspectorDraft(String clipId, _ClipInspectorDraft? draft) {
    if (draft == null) {
      _inspectorDrafts.remove(clipId);
    } else {
      _inspectorDrafts[clipId] = draft;
    }
    _leaveGuard?.refresh();
    _sheetUpdates.refresh();
    if (mounted) setState(() {});
  }

  Future<void> _showLayerSheet({
    required String title,
    required Widget Function(
      StateSetter setSheetState,
      BuildContext sheetContext,
    )
    content,
  }) async {
    setState(() => _layerOpen = true);
    try {
      await showModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        useSafeArea: true,
        sheetAnimationStyle: MediaQuery.disableAnimationsOf(context)
            ? AnimationStyle.noAnimation
            : null,
        builder: (sheetContext) => AnimatedBuilder(
          animation: _sheetUpdates,
          builder: (context, _) => Padding(
            padding: EdgeInsets.only(
              bottom: MediaQuery.viewInsetsOf(context).bottom,
            ),
            child: FractionallySizedBox(
              heightFactor: .9,
              child: Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 760),
                  child: StatefulBuilder(
                    builder: (context, setSheetState) => Padding(
                      padding: const EdgeInsets.fromLTRB(20, 12, 20, 20),
                      child: Column(
                        children: [
                          Row(
                            children: [
                              Expanded(
                                child: Semantics(
                                  header: true,
                                  child: Text(
                                    title,
                                    style: Theme.of(
                                      context,
                                    ).textTheme.titleLarge,
                                  ),
                                ),
                              ),
                              IconButton(
                                key: const Key('media-close-layer'),
                                tooltip: _copy(context, 'close'),
                                style: IconButton.styleFrom(
                                  minimumSize: const Size(48, 48),
                                ),
                                onPressed: () =>
                                    Navigator.of(sheetContext).pop(),
                                icon: const Icon(Icons.close_rounded),
                              ),
                            ],
                          ),
                          if (_isBusy) ...[
                            const LinearProgressIndicator(),
                            Semantics(
                              liveRegion: true,
                              child: Text(
                                _copy(context, _operationCopyKey),
                                key: const Key('media-layer-progress'),
                              ),
                            ),
                          ],
                          if ((_failure ?? _notice) case final notice?)
                            Semantics(
                              liveRegion: true,
                              child: Text(
                                _copy(context, notice),
                                key: const Key('media-layer-notice'),
                              ),
                            ),
                          const Divider(),
                          Expanded(
                            child: SingleChildScrollView(
                              padding: EdgeInsets.only(
                                bottom:
                                    MediaQuery.viewInsetsOf(context).bottom +
                                    24,
                              ),
                              child: content(setSheetState, sheetContext),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
      );
    } finally {
      if (mounted) setState(() => _layerOpen = false);
    }
  }

  Widget _actions(
    MediaProjectSnapshot? timeline, {
    StateSetter? setSheetState,
    BuildContext? actionsSheetContext,
  }) {
    final palette = LumenisTheme.of(context);
    final working = _isBusy;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          _copy(context, 'rights'),
          style: TextStyle(color: palette.caution),
        ),
        CheckboxListTile(
          contentPadding: EdgeInsets.zero,
          controlAffinity: ListTileControlAffinity.leading,
          value: _demo,
          onChanged: (value) {
            setState(() => _demo = value ?? false);
            setSheetState?.call(() {});
          },
          title: Text(_copy(context, 'demo')),
        ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 12,
          runSpacing: 12,
          children: [
            FilledButton.icon(
              key: const Key('media-export'),
              style: FilledButton.styleFrom(minimumSize: const Size(48, 48)),
              onPressed:
                  timeline == null ||
                      working ||
                      !_canUseCurrentContext ||
                      _controller.completionUnknown
                  ? null
                  : () => _controller.export(
                      outputKind: 'video',
                      demoAcknowledged: _demo,
                    ),
              icon: const Icon(Icons.file_download_outlined),
              label: Text(_copy(context, 'export')),
            ),
            OutlinedButton.icon(
              style: OutlinedButton.styleFrom(minimumSize: const Size(48, 48)),
              onPressed: timeline?.canUndo == true
                  ? () => _edit((s) => s.undo())
                  : null,
              icon: const Icon(Icons.undo),
              label: Text(_copy(context, 'undo')),
            ),
          ],
        ),
        if (_controller.needsOriginalFiles)
          Padding(
            padding: const EdgeInsets.only(top: 12),
            child: Text(_copy(context, 'relink_hint')),
          ),
        if (_canUseCurrentContext && _versions.isNotEmpty) ...[
          const SizedBox(height: 24),
          Text(
            _copy(context, 'versions'),
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 12),
          if (_controller.version case final version?) ...[
            Text(_copy(context, 'saved_reference')),
            SelectableText(
              version.artifactId,
              key: const Key('media-output-reference'),
            ),
            const SizedBox(height: 8),
            Text(_copy(context, 'saved_reference_keep')),
            Align(
              alignment: Alignment.centerLeft,
              child: TextButton.icon(
                style: TextButton.styleFrom(minimumSize: const Size(48, 48)),
                onPressed: () => _copyReference(version.artifactId),
                icon: const Icon(Icons.copy_outlined),
                label: Text(_copy(context, 'copy_reference')),
              ),
            ),
            const SizedBox(height: 12),
          ],
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: _versions
                .map(
                  (version) => OutlinedButton(
                    key: Key('media-reopen-${version.artifactId}'),
                    style: OutlinedButton.styleFrom(
                      minimumSize: const Size(48, 48),
                    ),
                    onPressed: working || !_canUseCurrentContext
                        ? null
                        : () => _reopen(version.artifactId),
                    child: Text(
                      '${_copy(context, 'reopen')} · v${version.timelineVersion} · ${_seconds(version.durationSec)} s',
                    ),
                  ),
                )
                .toList(),
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: [
              OutlinedButton(
                key: const Key('media-version-preview'),
                style: OutlinedButton.styleFrom(
                  minimumSize: const Size(48, 48),
                ),
                onPressed: _retrieving
                    ? null
                    : () => _retrieve(
                        download: false,
                        actionsSheetContext: setSheetState == null
                            ? null
                            : actionsSheetContext,
                      ),
                child: Text(_copy(context, 'preview')),
              ),
              OutlinedButton(
                key: const Key('media-version-download'),
                style: OutlinedButton.styleFrom(
                  minimumSize: const Size(48, 48),
                ),
                onPressed: _retrieving || !_files.canSave
                    ? null
                    : () => _retrieve(download: true),
                child: Text(_copy(context, 'download')),
              ),
            ],
          ),
        ],
      ],
    );
  }

  Widget _sources(
    MediaProjectSnapshot? timeline, {
    VoidCallback? onChoose,
  }) => _pane(
    context,
    'sources',
    Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        OutlinedButton.icon(
          key: const Key('media-import'),
          onPressed:
              _controller.busy ||
                  _choosing ||
                  !_canUseCurrentContext ||
                  _controller.needsOriginalFiles
              ? null
              : (onChoose ?? _choose),
          icon: const Icon(Icons.add),
          label: Text(_copy(context, 'choose')),
        ),
        if (timeline == null)
          Padding(
            padding: const EdgeInsets.only(top: 16),
            child: Text(_copy(context, 'empty')),
          ),
        for (final asset in timeline?.assets ?? <MediaProjectAsset>[])
          Container(
            padding: const EdgeInsets.symmetric(vertical: 8),
            decoration: BoxDecoration(
              border: Border(
                bottom: BorderSide(color: LumenisTheme.of(context).line),
              ),
            ),
            child: Row(
              children: [
                Icon(
                  asset.hasVideo
                      ? Icons.movie_outlined
                      : Icons.audio_file_outlined,
                  size: 20,
                  color: LumenisTheme.of(context).muted,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        asset.filename,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.labelLarge,
                      ),
                      Text(
                        '${_seconds(asset.durationSec)} s',
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          fontFeatures: const [FontFeature.tabularFigures()],
                        ),
                      ),
                    ],
                  ),
                ),
                IconButton(
                  constraints: const BoxConstraints(
                    minWidth: 48,
                    minHeight: 48,
                  ),
                  tooltip: '${_copy(context, 'add')} · ${asset.filename}',
                  onPressed: _isBusy ? null : () => _add(asset),
                  icon: const Icon(Icons.add_rounded),
                ),
              ],
            ),
          ),
      ],
    ),
  );

  Widget _timeline(MediaProjectSnapshot? timeline) {
    final palette = LumenisTheme.of(context);
    final textSize = MediaQuery.textScalerOf(context).scale(14);
    final rowHeight = math.max(72.0, textSize * 3 + 20);
    final rulerHeight = math.max(28.0, textSize + 10);
    final tracks = timeline?.tracks ?? <MediaProjectTrack>[];
    final overlays = timeline?.overlays ?? <MediaProjectOverlay>[];
    return Material(
      color: palette.surface,
      shape: Border(top: BorderSide(color: palette.line)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          SizedBox(
            height: 48,
            child: Row(
              children: [
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    '${_copy(context, 'timeline')}'
                    '${timeline == null ? '' : ' · ${_seconds(timeline.durationSec)} s'}',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.labelLarge,
                  ),
                ),
                IconButton(
                  key: const Key('media-timeline-smaller'),
                  tooltip: _copy(context, 'preview_size'),
                  onPressed: _timelineFraction <= .28
                      ? null
                      : () => setState(() {
                          _timelineFraction = (_timelineFraction - .1).clamp(
                            .28,
                            .58,
                          );
                        }),
                  icon: const Icon(Icons.keyboard_arrow_down_rounded),
                ),
                IconButton(
                  key: const Key('media-timeline-larger'),
                  tooltip: _copy(context, 'timeline_size'),
                  onPressed: _timelineFraction >= .58
                      ? null
                      : () => setState(() {
                          _timelineFraction = (_timelineFraction + .1).clamp(
                            .28,
                            .58,
                          );
                        }),
                  icon: const Icon(Icons.keyboard_arrow_up_rounded),
                ),
                if (timeline != null &&
                    tracks.any((track) => track.clips.isNotEmpty))
                  PopupMenuButton<String>(
                    key: const Key('media-clip-list'),
                    tooltip: _copy(context, 'select'),
                    icon: const Icon(Icons.view_list_outlined),
                    onSelected: _controller.selectClip,
                    itemBuilder: (_) => [
                      for (final track in tracks)
                        for (final clip in track.clips)
                          PopupMenuItem(
                            value: clip.clipId,
                            child: Text(
                              '${timeline.assets.firstWhere((a) => a.assetId == clip.mediaAssetId).filename} · ${_seconds(clip.timelineStart)} s',
                            ),
                          ),
                    ],
                  ),
                PopupMenuButton<double>(
                  key: const Key('media-timeline-zoom'),
                  tooltip: _copy(context, 'timeline_zoom'),
                  onSelected: (value) => setState(() => _timelineZoom = value),
                  initialValue: _timelineZoom,
                  icon: const Icon(Icons.zoom_in_rounded),
                  itemBuilder: (_) => [
                    PopupMenuItem(
                      value: 0,
                      child: Text(_copy(context, 'timeline_fit')),
                    ),
                    for (final zoom in [1.0, 2.0, 4.0, 8.0])
                      PopupMenuItem(
                        value: zoom,
                        child: Text('${(zoom * 100).round()}%'),
                      ),
                  ],
                ),
              ],
            ),
          ),
          Divider(height: 1, color: palette.line),
          Expanded(
            child: timeline == null || timeline.durationSec <= 0
                ? Center(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Text(_copy(context, 'empty')),
                    ),
                  )
                : SingleChildScrollView(
                    key: const Key('media-track-scroll'),
                    child: LayoutBuilder(
                      builder: (context, area) {
                        final labelWidth = area.maxWidth < 500 ? 76.0 : 128.0;
                        final viewport = math.max(
                          1.0,
                          area.maxWidth - labelWidth,
                        );
                        final baseWidth = math.max(
                          800.0,
                          math.min(20000.0, timeline.durationSec * 36),
                        );
                        final width = _timelineZoom == 0
                            ? viewport
                            : math.max(viewport, baseWidth * _timelineZoom);
                        final scale = width / timeline.durationSec;
                        // Use readable time steps while keeping clip geometry exact.
                        final minimumStep = 110 * (textSize / 14) / scale;
                        final magnitude = math
                            .pow(
                              10,
                              (math.log(minimumStep) / math.ln10).floor(),
                            )
                            .toDouble();
                        final interval = [1, 2, 5, 10]
                            .map((step) => step * magnitude)
                            .firstWhere((step) => step >= minimumStep);
                        final divisions = (timeline.durationSec / interval)
                            .ceil();
                        return Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            SizedBox(
                              key: const Key('media-track-labels'),
                              width: labelWidth,
                              child: Column(
                                children: [
                                  SizedBox(height: rulerHeight),
                                  for (final track in tracks)
                                    Container(
                                      height: rowHeight,
                                      alignment: Alignment.centerLeft,
                                      padding: const EdgeInsets.symmetric(
                                        horizontal: 12,
                                      ),
                                      decoration: BoxDecoration(
                                        color: palette.surfaceRaised,
                                        border: Border(
                                          top: BorderSide(color: palette.line),
                                          right: BorderSide(
                                            color: palette.line,
                                          ),
                                        ),
                                      ),
                                      child: Text(
                                        _copy(context, track.kind),
                                        maxLines: 2,
                                        overflow: TextOverflow.ellipsis,
                                        style: Theme.of(
                                          context,
                                        ).textTheme.labelMedium,
                                      ),
                                    ),
                                ],
                              ),
                            ),
                            Expanded(
                              child: Scrollbar(
                                controller: _timelineScroll,
                                thumbVisibility: true,
                                child: SingleChildScrollView(
                                  key: const Key('media-timeline-scroll'),
                                  controller: _timelineScroll,
                                  scrollDirection: Axis.horizontal,
                                  child: SizedBox(
                                    width: width,
                                    child: Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.stretch,
                                      children: [
                                        Builder(
                                          builder: (context) {
                                            final playhead =
                                                (_timelinePlayheadSec ?? 0.0)
                                                    .clamp(
                                                      0.0,
                                                      timeline.durationSec,
                                                    );
                                            final earlier = (playhead - 1)
                                                .clamp(
                                                  0.0,
                                                  timeline.durationSec,
                                                );
                                            final later = (playhead + 1).clamp(
                                              0.0,
                                              timeline.durationSec,
                                            );
                                            return SizedBox(
                                              height: rulerHeight,
                                              child: Semantics(
                                                label: _copy(
                                                  context,
                                                  'player.seek',
                                                ),
                                                value: _seconds(playhead),
                                                increasedValue: _seconds(later),
                                                decreasedValue: _seconds(
                                                  earlier,
                                                ),
                                                onIncrease: () => _seekBy(1),
                                                onDecrease: () => _seekBy(-1),
                                                child: GestureDetector(
                                                  key: const Key(
                                                    'media-timeline-ruler',
                                                  ),
                                                  behavior:
                                                      HitTestBehavior.opaque,
                                                  onTapDown: (details) =>
                                                      _seekFromTimeline(
                                                        (details
                                                                    .localPosition
                                                                    .dx -
                                                                4) /
                                                            scale,
                                                      ),
                                                  child: Stack(
                                                    children: [
                                                      for (
                                                        var tick = 0;
                                                        tick < divisions;
                                                        tick++
                                                      )
                                                        Positioned(
                                                          left:
                                                              tick *
                                                                  interval *
                                                                  scale +
                                                              4,
                                                          top: 4,
                                                          child: Text(
                                                            '${_seconds(tick * interval)} s',
                                                            style: Theme.of(context)
                                                                .textTheme
                                                                .labelSmall
                                                                ?.copyWith(
                                                                  fontFeatures:
                                                                      const [
                                                                        FontFeature.tabularFigures(),
                                                                      ],
                                                                ),
                                                          ),
                                                        ),
                                                      if (_timelinePlayheadSec !=
                                                          null)
                                                        Positioned(
                                                          left:
                                                              _timelinePlayheadSec! *
                                                              scale,
                                                          top: 0,
                                                          bottom: 0,
                                                          child: Container(
                                                            width: 2,
                                                            color:
                                                                palette.accent,
                                                          ),
                                                        ),
                                                    ],
                                                  ),
                                                ),
                                              ),
                                            );
                                          },
                                        ),
                                        for (final track in tracks)
                                          Container(
                                            height: rowHeight,
                                            decoration: BoxDecoration(
                                              color: palette.canvas,
                                              border: Border(
                                                top: BorderSide(
                                                  color: palette.line,
                                                ),
                                              ),
                                            ),
                                            child: Stack(
                                              children: [
                                                for (
                                                  var tick = 0;
                                                  tick < divisions;
                                                  tick++
                                                )
                                                  Positioned(
                                                    left:
                                                        tick * interval * scale,
                                                    top: 0,
                                                    bottom: 0,
                                                    child: Container(
                                                      width: 1,
                                                      color: palette.line,
                                                    ),
                                                  ),
                                                if (_timelinePlayheadSec !=
                                                    null)
                                                  Positioned(
                                                    left:
                                                        _timelinePlayheadSec! *
                                                        scale,
                                                    top: 0,
                                                    bottom: 0,
                                                    child: Container(
                                                      width: 2,
                                                      color: palette.accent,
                                                    ),
                                                  ),
                                                for (final clip in track.clips)
                                                  Positioned(
                                                    left:
                                                        clip.timelineStart *
                                                        scale,
                                                    width:
                                                        clip.durationSec *
                                                        scale,
                                                    top: 6,
                                                    bottom: 6,
                                                    child: _timelineClip(
                                                      timeline,
                                                      clip,
                                                    ),
                                                  ),
                                              ],
                                            ),
                                          ),
                                        for (final overlay in overlays)
                                          Padding(
                                            padding: const EdgeInsets.all(8),
                                            child: Column(
                                              crossAxisAlignment:
                                                  CrossAxisAlignment.start,
                                              children: [
                                                Text(
                                                  '${_seconds(overlay.startSec)}–${_seconds(overlay.endSec)} s · ${overlay.text}',
                                                ),
                                                if (overlay.kind == 'caption')
                                                  ReadAloudAction(
                                                    sessionId:
                                                        'sh01:${overlay.overlayId}',
                                                    scopeVersion:
                                                        '${_controller.domain}:${_controller.repository.contextKey}:${timeline.version}',
                                                    text: overlay.text,
                                                    purpose: ReadAloudPurpose
                                                        .videoCaption,
                                                  ),
                                              ],
                                            ),
                                          ),
                                        const SizedBox(height: 12),
                                      ],
                                    ),
                                  ),
                                ),
                              ),
                            ),
                          ],
                        );
                      },
                    ),
                  ),
          ),
        ],
      ),
    );
  }

  Widget _timelineClip(MediaProjectSnapshot timeline, MediaProjectClip clip) {
    final palette = LumenisTheme.of(context);
    final selected = clip.clipId == _controller.selectedClipId;
    final asset = timeline.assets.firstWhere(
      (a) => a.assetId == clip.mediaAssetId,
    );
    final label =
        '${asset.filename}\n${_seconds(clip.sourceIn)}–${_seconds(clip.sourceOut)} s';
    return Padding(
      padding: const EdgeInsets.only(right: 2),
      child: Semantics(
        selected: selected,
        child: Tooltip(
          message: label,
          child: OutlinedButton(
            key: ValueKey('media-clip-${clip.clipId}'),
            style: OutlinedButton.styleFrom(
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(3),
              ),
              backgroundColor: selected
                  ? palette.surfaceRaised
                  : palette.surface,
              foregroundColor: palette.foreground,
              side: BorderSide(
                color: selected ? palette.foreground : palette.line,
                width: selected ? 2 : 1,
              ),
              minimumSize: const Size(0, 48),
              padding: const EdgeInsets.symmetric(horizontal: 8),
              alignment: Alignment.centerLeft,
            ),
            onPressed: () => _controller.selectClip(clip.clipId),
            child: Text(
              label,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.labelMedium,
            ),
          ),
        ),
      ),
    );
  }
}

Widget _pane(BuildContext context, String title, Widget child) => Material(
  color: LumenisTheme.of(context).surface,
  shape: RoundedRectangleBorder(
    side: BorderSide(color: LumenisTheme.of(context).line),
    borderRadius: BorderRadius.circular(4),
  ),
  clipBehavior: Clip.antiAlias,
  child: Padding(
    padding: const EdgeInsets.all(12),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          _copy(context, title),
          style: Theme.of(context).textTheme.labelLarge,
        ),
        const SizedBox(height: 12),
        child,
      ],
    ),
  ),
);

class _NewClip {
  const _NewClip(this.role, this.start, this.end, this.stream);
  final String role;
  final double start;
  final double end;
  final int? stream;
}

class _AddClipDialog extends StatefulWidget {
  const _AddClipDialog({required this.asset});
  final MediaProjectAsset asset;
  @override
  State<_AddClipDialog> createState() => _AddClipDialogState();
}

class _AddClipDialogState extends State<_AddClipDialog> {
  late String _role = widget.asset.hasVideo ? 'video' : 'voiceover';
  late int? _stream = widget.asset.audioStreamCount == 1 ? 0 : null;
  final _start = TextEditingController(text: '0');
  late final _end = TextEditingController(
    text: _seconds(widget.asset.durationSec),
  );
  bool _invalid = false;
  @override
  void dispose() {
    _start.dispose();
    _end.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
    title: Text(_copy(context, 'add')),
    content: SizedBox(
      width: 340,
      child: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(widget.asset.filename),
            DropdownButtonFormField<String>(
              initialValue: _role,
              items:
                  [
                        if (widget.asset.hasVideo) 'video',
                        if (widget.asset.audioStreamCount > 0) ...[
                          'voiceover',
                          'bgm',
                          'sfx',
                        ],
                      ]
                      .map(
                        (r) => DropdownMenuItem(
                          value: r,
                          child: Text(_copy(context, r)),
                        ),
                      )
                      .toList(),
              onChanged: (value) => setState(() => _role = value!),
            ),
            _numberField(context, 'source_in', _start),
            _numberField(context, 'source_out', _end),
            if (widget.asset.audioStreamCount > 0)
              DropdownButtonFormField<int>(
                initialValue: _stream,
                decoration: InputDecoration(
                  labelText: _copy(context, 'stream'),
                ),
                items: List.generate(
                  widget.asset.audioStreamCount,
                  (i) => DropdownMenuItem(
                    value: i,
                    child: Text('${_copy(context, 'stream')} ${i + 1}'),
                  ),
                ),
                onChanged: (value) => setState(() => _stream = value),
              ),
            if (_invalid) Text(_copy(context, 'invalid')),
          ],
        ),
      ),
    ),
    actions: [
      TextButton(
        onPressed: () => Navigator.pop(context),
        child: Text(_copy(context, 'cancel')),
      ),
      FilledButton(
        onPressed: () {
          final start = double.tryParse(_start.text);
          final end = double.tryParse(_end.text);
          if (start == null ||
              end == null ||
              !start.isFinite ||
              !end.isFinite ||
              start < 0 ||
              end <= start ||
              end > widget.asset.durationSec ||
              widget.asset.audioStreamCount > 1 && _stream == null) {
            setState(() => _invalid = true);
            return;
          }
          Navigator.pop(context, _NewClip(_role, start, end, _stream));
        },
        child: Text(_copy(context, 'add')),
      ),
    ],
  );
}

Widget _numberField(
  BuildContext context,
  String key,
  TextEditingController controller, {
  ValueChanged<String>? onChanged,
}) => Padding(
  padding: const EdgeInsets.symmetric(vertical: 6),
  child: TextField(
    controller: controller,
    onChanged: onChanged,
    keyboardType: const TextInputType.numberWithOptions(decimal: true),
    decoration: InputDecoration(labelText: _copy(context, key)),
  ),
);

class _ClipInspectorDraft {
  const _ClipInspectorDraft({required this.values, required this.stream});

  final Map<String, String> values;
  final int? stream;
}

class _SheetUpdateSignal extends ChangeNotifier {
  void refresh() => notifyListeners();
}

class _ClipInspector extends StatefulWidget {
  const _ClipInspector({
    required this.timeline,
    required this.clip,
    required this.onEdit,
    required this.draft,
    required this.onDraftChanged,
  });
  final MediaProjectSnapshot? timeline;
  final MediaProjectClip? clip;
  final bool Function(MediaProjectSnapshot Function(MediaProjectSnapshot))
  onEdit;
  final _ClipInspectorDraft? draft;
  final void Function(String clipId, _ClipInspectorDraft? draft) onDraftChanged;
  @override
  State<_ClipInspector> createState() => _ClipInspectorState();
}

class _ClipInspectorState extends State<_ClipInspector> {
  bool _invalid = false;
  final _fields = {
    for (final name in [
      'source_in',
      'source_out',
      'position',
      'gain',
      'fade_in',
      'fade_out',
      'split_position',
    ])
      name: TextEditingController(),
  };
  int? _stream;
  @override
  void initState() {
    super.initState();
    _sync();
  }

  @override
  void didUpdateWidget(covariant _ClipInspector oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (!identical(oldWidget.clip, widget.clip)) {
      _invalid = false;
      _sync();
    }
  }

  void _sync() {
    final clip = widget.clip;
    if (clip == null) return;
    final draft = widget.draft;
    if (draft != null) {
      for (final entry in draft.values.entries) {
        _fields[entry.key]?.text = entry.value;
      }
      _stream = draft.stream;
      return;
    }
    final values = {
      'source_in': clip.sourceIn,
      'source_out': clip.sourceOut,
      'position': clip.timelineStart,
      'gain': clip.audioMix.volume,
      'fade_in': clip.audioMix.fadeInSec,
      'fade_out': clip.audioMix.fadeOutSec,
      'split_position': (clip.sourceIn + clip.sourceOut) / 2,
    };
    for (final entry in values.entries) {
      _fields[entry.key]!.text = _seconds(entry.value);
    }
    _stream = clip.audioRole == 'muted' ? -1 : clip.audioStreamIndex;
  }

  void _saveDraft() {
    final clip = widget.clip;
    if (clip == null) return;
    widget.onDraftChanged(
      clip.clipId,
      _ClipInspectorDraft(
        values: {
          for (final entry in _fields.entries) entry.key: entry.value.text,
        },
        stream: _stream,
      ),
    );
  }

  @override
  void dispose() {
    for (final controller in _fields.values) {
      controller.dispose();
    }
    super.dispose();
  }

  double _value(String name) =>
      double.tryParse(_fields[name]!.text) ?? double.nan;

  bool get _hasClipFieldChanges {
    final clip = widget.clip;
    if (clip == null) return false;
    final expected = {
      'source_in': clip.sourceIn,
      'source_out': clip.sourceOut,
      'position': clip.timelineStart,
      'gain': clip.audioMix.volume,
      'fade_in': clip.audioMix.fadeInSec,
      'fade_out': clip.audioMix.fadeOutSec,
    };
    return expected.entries.any((entry) => _value(entry.key) != entry.value) ||
        _stream != (clip.audioRole == 'muted' ? -1 : clip.audioStreamIndex);
  }

  @override
  Widget build(BuildContext context) {
    final clip = widget.clip;
    final timeline = widget.timeline;
    if (clip == null || timeline == null) return Text(_copy(context, 'select'));
    final track = timeline.tracks.firstWhere((t) => t.trackId == clip.trackId);
    final video = track.kind == 'video';
    final asset = timeline.assets.firstWhere(
      (a) => a.assetId == clip.mediaAssetId,
    );
    final index = track.clips.indexOf(clip);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(asset.filename, maxLines: 3, overflow: TextOverflow.ellipsis),
        for (final name in ['source_in', 'source_out', if (!video) 'position'])
          _numberField(
            context,
            name,
            _fields[name]!,
            onChanged: (_) => _saveDraft(),
          ),
        ExpansionTile(
          key: const Key('media-sound-settings'),
          maintainState: true,
          tilePadding: EdgeInsets.zero,
          title: Text(_copy(context, 'sound_settings')),
          children: [
            for (final name in ['gain', 'fade_in', 'fade_out'])
              _numberField(
                context,
                name,
                _fields[name]!,
                onChanged: (_) => _saveDraft(),
              ),
            if (asset.audioStreamCount > 0)
              DropdownButtonFormField<int>(
                key: ValueKey(
                  '${clip.clipId}-${clip.audioRole}-${clip.audioStreamIndex}',
                ),
                initialValue: _stream,
                decoration: InputDecoration(
                  labelText: _copy(context, 'stream'),
                ),
                items: [
                  if (video)
                    DropdownMenuItem(
                      value: -1,
                      child: Text(_copy(context, 'muted')),
                    ),
                  ...List.generate(
                    asset.audioStreamCount,
                    (i) => DropdownMenuItem(
                      value: i,
                      child: Text('${_copy(context, 'stream')} ${i + 1}'),
                    ),
                  ),
                ],
                onChanged: (value) {
                  setState(() => _stream = value);
                  _saveDraft();
                },
              ),
          ],
        ),
        if (_invalid)
          Semantics(
            liveRegion: true,
            child: Text(
              _copy(context, 'invalid'),
              key: const Key('media-inspector-invalid'),
            ),
          ),
        const SizedBox(height: 12),
        FilledButton(
          style: FilledButton.styleFrom(minimumSize: const Size(48, 48)),
          onPressed: () {
            final applied = widget.onEdit(
              (s) => s.adjustClip(
                clip.clipId,
                sourceIn: _value('source_in'),
                sourceOut: _value('source_out'),
                timelineStart: _value('position'),
                audioMix: MediaProjectAudioMix(
                  volume: _value('gain'),
                  fadeInSec: _value('fade_in'),
                  fadeOutSec: _value('fade_out'),
                  ducking: clip.audioMix.ducking,
                ),
                audioRole: video
                    ? (_stream == -1 ? 'muted' : 'original')
                    : track.kind,
                audioStreamIndex: _stream == -1 ? null : _stream,
              ),
            );
            setState(() => _invalid = !applied);
            if (applied) widget.onDraftChanged(clip.clipId, null);
          },
          child: Text(_copy(context, 'apply')),
        ),
        ExpansionTile(
          key: const Key('media-clip-operations'),
          maintainState: true,
          tilePadding: EdgeInsets.zero,
          title: Text(_copy(context, 'clip_operations')),
          children: [
            _numberField(
              context,
              'split_position',
              _fields['split_position']!,
              onChanged: (_) => _saveDraft(),
            ),
            if (_hasClipFieldChanges)
              Text(
                _copy(context, 'apply_before_split'),
                key: const Key('media-apply-before-split'),
              ),
            OutlinedButton(
              key: const Key('media-split-clip'),
              style: OutlinedButton.styleFrom(minimumSize: const Size(48, 48)),
              onPressed: _hasClipFieldChanges
                  ? null
                  : () {
                      final applied = widget.onEdit(
                        (s) => s.splitClip(
                          clip.clipId,
                          atSec: _value('split_position'),
                        ),
                      );
                      if (!applied) setState(() => _invalid = true);
                    },
              child: Text(_copy(context, 'split')),
            ),
            if (video)
              Wrap(
                spacing: 8,
                children: [
                  TextButton(
                    onPressed: index == 0
                        ? null
                        : () => widget.onEdit(
                            (s) => s.reorderVideoClip(
                              clip.clipId,
                              newIndex: index - 1,
                            ),
                          ),
                    child: Text(_copy(context, 'earlier')),
                  ),
                  TextButton(
                    onPressed: index == track.clips.length - 1
                        ? null
                        : () => widget.onEdit(
                            (s) => s.reorderVideoClip(
                              clip.clipId,
                              newIndex: index + 1,
                            ),
                          ),
                    child: Text(_copy(context, 'later')),
                  ),
                ],
              ),
            TextButton(
              onPressed: () => widget.onEdit(
                (s) => video
                    ? s.deleteVideoClip(clip.clipId)
                    : s.deleteAudioClip(clip.clipId),
              ),
              child: Text(_copy(context, 'delete')),
            ),
          ],
        ),
      ],
    );
  }
}
