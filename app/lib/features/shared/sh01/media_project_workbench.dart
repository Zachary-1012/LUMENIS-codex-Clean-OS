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

  void _edit(MediaProjectSnapshot Function(MediaProjectSnapshot) operation) {
    if (!_canUseCurrentContext) return;
    try {
      _controller.edit(operation);
      setState(() => _notice = null);
    } on FormatException {
      setState(() => _notice = 'invalid');
    } on StateError {
      setState(() => _notice = 'invalid');
    }
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
    final selected = _selectedClip(timeline);
    final working = _isBusy;
    final notice = _failure ?? _notice;
    return Material(
      color: palette.canvas,
      child: SafeArea(
        child: LayoutBuilder(
          builder: (context, constraints) {
            final wide =
                constraints.maxWidth >= 1180 &&
                MediaQuery.textScalerOf(context).scale(14) <= 22;
            final sources = _sources(timeline);
            final center = Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                _pane(
                  context,
                  'preview',
                  SizedBox(
                    key: _previewKey,
                    height: wide ? 300 : 230,
                    child: !_canUseCurrentContext || _preview == null
                        ? Center(
                            child: Padding(
                              padding: const EdgeInsets.all(24),
                              child: Text(_copy(context, 'preview_empty')),
                            ),
                          )
                        : MediaPreview(file: _preview!),
                  ),
                ),
                const SizedBox(height: 16),
                _timeline(timeline),
              ],
            );
            final inspector = _inspector(timeline, selected);
            return SingleChildScrollView(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Wrap(
                    spacing: 16,
                    runSpacing: 12,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    children: [
                      IconButton(
                        tooltip: _copy(context, 'back'),
                        onPressed: working ? null : _leaveEditor,
                        icon: const Icon(Icons.arrow_back_rounded),
                      ),
                      Text(
                        _copy(context, 'title'),
                        style: Theme.of(context).textTheme.headlineSmall,
                      ),
                      if (timeline == null && _controller.version == null)
                        Text(
                          context.lumenisL10n.text(
                            _controller.domain == 'CTH'
                                ? 'navgroup.cth'
                                : 'navgroup.bmp',
                          ),
                        ),
                      if (timeline != null)
                        Text(
                          _copy(
                            context,
                            _hasUnsavedChanges ? 'draft' : 'saved',
                          ),
                        ),
                      _openSavedButton('media-open-saved'),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(_copy(context, 'subtitle')),
                  if (working) ...[
                    const SizedBox(height: 12),
                    const LinearProgressIndicator(),
                    Text(
                      _copy(
                        context,
                        _retrieving
                            ? 'saved_loading'
                            : switch (_controller.operation) {
                                MediaProjectOperation.exporting => 'exporting',
                                MediaProjectOperation.reopening =>
                                  'saved_loading',
                                _ => 'importing',
                              },
                      ),
                    ),
                  ],
                  if (notice != null)
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 12),
                      child: Semantics(
                        liveRegion: true,
                        child: Text(_copy(context, notice)),
                      ),
                    ),
                  if (!_canUseCurrentContext) Text(_copy(context, 'context')),
                  if (widget.contextAvailable &&
                      _controllerInitialized &&
                      _controller.sourcesNeedRevalidation)
                    Align(
                      alignment: Alignment.centerLeft,
                      child: OutlinedButton.icon(
                        key: const Key('media-recover-draft-sources'),
                        style: OutlinedButton.styleFrom(
                          minimumSize: const Size(48, 48),
                        ),
                        onPressed: _isBusy ? null : _recoverDraftSources,
                        icon: const Icon(Icons.refresh_rounded),
                        label: Text(_copy(context, 'recover_sources')),
                      ),
                    ),
                  const SizedBox(height: 20),
                  if (wide)
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        SizedBox(width: 240, child: sources),
                        const SizedBox(width: 16),
                        Expanded(child: center),
                        const SizedBox(width: 16),
                        SizedBox(width: 270, child: inspector),
                      ],
                    )
                  else ...[
                    center,
                    const SizedBox(height: 16),
                    Wrap(
                      spacing: 10,
                      runSpacing: 10,
                      children: [
                        OutlinedButton.icon(
                          key: const Key('media-open-sources'),
                          style: OutlinedButton.styleFrom(
                            minimumSize: const Size(48, 48),
                          ),
                          onPressed: () => _openLayerSheet(
                            title: _copy(context, 'sources'),
                            content: (_, _) => _sources(
                              _canUseCurrentContext
                                  ? _controller.timeline
                                  : null,
                              onChoose: () {
                                Navigator.of(context).pop();
                                _choose();
                              },
                            ),
                          ),
                          icon: const Icon(Icons.video_library_outlined),
                          label: Text(_copy(context, 'sources')),
                        ),
                        OutlinedButton.icon(
                          key: const Key('media-open-properties'),
                          style: OutlinedButton.styleFrom(
                            minimumSize: const Size(48, 48),
                          ),
                          onPressed: () => _openLayerSheet(
                            title: _copy(context, 'properties'),
                            content: (_, _) {
                              final latest = _canUseCurrentContext
                                  ? _controller.timeline
                                  : null;
                              return _inspector(latest, _selectedClip(latest));
                            },
                          ),
                          icon: const Icon(Icons.tune_rounded),
                          label: Text(_copy(context, 'properties')),
                        ),
                        OutlinedButton.icon(
                          key: const Key('media-open-actions'),
                          style: OutlinedButton.styleFrom(
                            minimumSize: const Size(48, 48),
                          ),
                          onPressed: _openActionsSheet,
                          icon: const Icon(Icons.more_horiz_rounded),
                          label: Text(_copy(context, 'actions')),
                        ),
                      ],
                    ),
                  ],
                  if (wide) ...[const SizedBox(height: 20), _actions(timeline)],
                ],
              ),
            );
          },
        ),
      ),
    );
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
    title: _copy(context, 'actions'),
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
  }) => showModalBottomSheet<void>(
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
                                style: Theme.of(context).textTheme.titleLarge,
                              ),
                            ),
                          ),
                          IconButton(
                            key: const Key('media-close-layer'),
                            tooltip: _copy(context, 'close'),
                            style: IconButton.styleFrom(
                              minimumSize: const Size(48, 48),
                            ),
                            onPressed: () => Navigator.of(sheetContext).pop(),
                            icon: const Icon(Icons.close_rounded),
                          ),
                        ],
                      ),
                      const Divider(),
                      Expanded(
                        child: SingleChildScrollView(
                          padding: EdgeInsets.only(
                            bottom:
                                MediaQuery.viewInsetsOf(context).bottom + 24,
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
        Align(
          alignment: Alignment.centerLeft,
          child: _openSavedButton('media-actions-open-saved'),
        ),
        const SizedBox(height: 16),
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
          if (_retrieving) ...[
            const LinearProgressIndicator(),
            if (setSheetState != null) Text(_copy(context, 'saved_loading')),
          ],
        ],
      ],
    );
  }

  Widget _sources(MediaProjectSnapshot? timeline, {VoidCallback? onChoose}) =>
      _pane(
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
              Padding(
                padding: const EdgeInsets.only(top: 14),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      asset.filename,
                      maxLines: 3,
                      overflow: TextOverflow.ellipsis,
                    ),
                    Text('${_seconds(asset.durationSec)} s'),
                    TextButton.icon(
                      onPressed: () => _add(asset),
                      icon: Icon(
                        asset.hasVideo
                            ? Icons.video_collection_outlined
                            : Icons.audio_file_outlined,
                      ),
                      label: Text(_copy(context, 'add')),
                    ),
                  ],
                ),
              ),
          ],
        ),
      );

  Widget _timeline(MediaProjectSnapshot? timeline) => _pane(
    context,
    'timeline',
    LayoutBuilder(
      builder: (context, constraints) {
        if (timeline == null || timeline.durationSec <= 0) {
          return Padding(
            padding: const EdgeInsets.all(20),
            child: Text(_copy(context, 'empty')),
          );
        }
        final width = math.max(
          constraints.maxWidth,
          math.min(20000.0, math.max(800.0, timeline.durationSec * 36)),
        );
        final scale = width / timeline.durationSec;
        return Scrollbar(
          controller: _timelineScroll,
          thumbVisibility: true,
          child: SingleChildScrollView(
            key: const Key('media-timeline-scroll'),
            controller: _timelineScroll,
            scrollDirection: Axis.horizontal,
            child: SizedBox(
              width: width + 16,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  SizedBox(
                    height: 28,
                    child: Stack(
                      children: [
                        for (var tick = 0; tick < 8; tick++)
                          Positioned(
                            left: tick * width / 8,
                            child: Text(
                              '${_seconds(timeline.durationSec * tick / 8)} s',
                              style: Theme.of(context).textTheme.labelSmall,
                            ),
                          ),
                      ],
                    ),
                  ),
                  for (final track in timeline.tracks) ...[
                    Text(_copy(context, track.kind)),
                    SizedBox(
                      height: 68,
                      child: Stack(
                        children: [
                          for (final clip in track.clips)
                            Positioned(
                              left: clip.timelineStart * scale,
                              width: math.max(48, clip.durationSec * scale - 3),
                              top: 4,
                              child: Semantics(
                                selected:
                                    clip.clipId == _controller.selectedClipId,
                                child: OutlinedButton(
                                  style: OutlinedButton.styleFrom(
                                    backgroundColor:
                                        clip.clipId ==
                                            _controller.selectedClipId
                                        ? LumenisTheme.of(context).surfaceRaised
                                        : null,
                                    minimumSize: const Size(48, 48),
                                    padding: const EdgeInsets.symmetric(
                                      horizontal: 8,
                                    ),
                                  ),
                                  onPressed: () =>
                                      _controller.selectClip(clip.clipId),
                                  child: Text(
                                    '${timeline.assets.firstWhere((a) => a.assetId == clip.mediaAssetId).filename}\n${_seconds(clip.sourceIn)}–${_seconds(clip.sourceOut)} s',
                                    maxLines: 2,
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                ),
                              ),
                            ),
                        ],
                      ),
                    ),
                  ],
                  for (final overlay in timeline.overlays)
                    Text(
                      '${_seconds(overlay.startSec)}–${_seconds(overlay.endSec)} s · ${overlay.text}',
                    ),
                  const SizedBox(height: 12),
                ],
              ),
            ),
          ),
        );
      },
    ),
  );
}

Widget _pane(BuildContext context, String title, Widget child) => Container(
  padding: const EdgeInsets.all(16),
  decoration: BoxDecoration(
    color: LumenisTheme.of(context).surface,
    border: Border.all(color: LumenisTheme.of(context).line),
    borderRadius: BorderRadius.circular(12),
  ),
  child: Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      Text(
        _copy(context, title),
        style: Theme.of(context).textTheme.titleMedium,
      ),
      const SizedBox(height: 12),
      child,
    ],
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
  final void Function(MediaProjectSnapshot Function(MediaProjectSnapshot))
  onEdit;
  final _ClipInspectorDraft? draft;
  final void Function(String clipId, _ClipInspectorDraft? draft) onDraftChanged;
  @override
  State<_ClipInspector> createState() => _ClipInspectorState();
}

class _ClipInspectorState extends State<_ClipInspector> {
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
    if (!identical(oldWidget.clip, widget.clip)) _sync();
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
        for (final name in [
          'source_in',
          'source_out',
          if (!video) 'position',
          'gain',
          'fade_in',
          'fade_out',
        ])
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
            decoration: InputDecoration(labelText: _copy(context, 'stream')),
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
        const SizedBox(height: 12),
        FilledButton(
          onPressed: () {
            widget.onEdit(
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
            widget.onDraftChanged(clip.clipId, null);
          },
          child: Text(_copy(context, 'apply')),
        ),
        _numberField(
          context,
          'split_position',
          _fields['split_position']!,
          onChanged: (_) => _saveDraft(),
        ),
        OutlinedButton(
          onPressed: () => widget.onEdit(
            (s) => s.splitClip(clip.clipId, atSec: _value('split_position')),
          ),
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
    );
  }
}
