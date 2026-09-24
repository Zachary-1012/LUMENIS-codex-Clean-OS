import 'package:flutter/material.dart';

import '../../core/lumenis_core_client.dart';
import '../../core/lumenis_theme.dart';
import '../../l10n/lumenis_localizations.dart';
import 'bmp08_repository.dart';
import 'bmp08_snapshot.dart';
import 'bmp08_view_model.dart';

class Bmp08Screen extends StatefulWidget {
  const Bmp08Screen({required this.client, this.repository, super.key});

  final LumenisCoreClient client;
  final Bmp08Repository? repository;

  @override
  State<Bmp08Screen> createState() => _Bmp08ScreenState();
}

class _Bmp08ScreenState extends State<Bmp08Screen> {
  late final Bmp08ViewModel _viewModel = Bmp08ViewModel(
    repository: widget.repository ?? CoreBmp08Repository(client: widget.client),
  );

  @override
  void initState() {
    super.initState();
    _viewModel.refresh();
  }

  @override
  void dispose() {
    _viewModel.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return ColoredBox(
      color: LumenisTheme.of(context).canvas,
      child: SafeArea(
        child: AnimatedBuilder(
          animation: _viewModel,
          builder: (context, _) => switch (_viewModel.phase) {
            Bmp08LoadPhase.loading => const _Loading(),
            Bmp08LoadPhase.failed => _Failure(
              kind: _viewModel.failureKind!,
              onRetry: _viewModel.refresh,
            ),
            Bmp08LoadPhase.ready => _PodcastStudio(
              snapshot: _viewModel.snapshot!,
              actionState: _viewModel.actionState,
              actionId: _viewModel.actionId,
              onRefresh: _viewModel.refresh,
              onAction: _viewModel.stageAction,
            ),
          },
        ),
      ),
    );
  }
}

class _PodcastStudio extends StatefulWidget {
  const _PodcastStudio({
    required this.snapshot,
    required this.actionState,
    required this.actionId,
    required this.onRefresh,
    required this.onAction,
  });

  final Bmp08Snapshot snapshot;
  final Bmp08ActionState actionState;
  final String? actionId;
  final VoidCallback onRefresh;
  final void Function(String actionId, String permission) onAction;

  @override
  State<_PodcastStudio> createState() => _PodcastStudioState();
}

enum _MobileStudioTask { script, materials, audio, properties }

class _PodcastStudioState extends State<_PodcastStudio> {
  int _selectedSection = 0;
  int _selectedMaterial = 0;
  _MobileStudioTask _mobileTask = _MobileStudioTask.script;
  final Map<int, String> _localDrafts = <int, String>{};

  Bmp08Snapshot _safeSnapshot(Bmp08Snapshot source) {
    if (source.scopeApproved) return source;
    return const Bmp08Snapshot(
      contractBound: false,
      dataState: 'UNKNOWN',
      scope: Bmp08Scope(
        mode: 'UNKNOWN',
        brandId: null,
        displayNames: <String, String>{},
      ),
      scopeApproved: false,
      audioAvailable: false,
      versioned: false,
      rightsReady: false,
      materials: <Bmp08Material>[],
      outline: <Bmp08OutlineSection>[],
      grantedPermissions: <String>{},
    );
  }

  @override
  Widget build(BuildContext context) {
    final copy = _Bmp08Copy.of(context);
    final snapshot = _safeSnapshot(widget.snapshot);
    return LayoutBuilder(
      builder: (context, constraints) {
        final wide = constraints.maxWidth >= 980;
        final padding = constraints.maxWidth >= 800 ? 32.0 : 18.0;
        final selectedSection = snapshot.outline.isEmpty
            ? null
            : _selectedSection.clamp(0, snapshot.outline.length - 1).toInt();
        final selectedMaterial = snapshot.materials.isEmpty
            ? null
            : _selectedMaterial.clamp(0, snapshot.materials.length - 1).toInt();
        return Align(
          alignment: Alignment.topCenter,
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1340),
            child: SingleChildScrollView(
              padding: EdgeInsets.fromLTRB(padding, 20, padding, 32),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  _Header(copy: copy, onRefresh: widget.onRefresh),
                  const SizedBox(height: 14),
                  _StudioContext(snapshot: snapshot, copy: copy),
                  if (!snapshot.scopeApproved) ...[
                    const SizedBox(height: 12),
                    _Gate(copy: copy),
                  ],
                  const SizedBox(height: 14),
                  _ActionRail(
                    copy: copy,
                    state: widget.actionState,
                    actionId: widget.actionId,
                    onAction: widget.onAction,
                  ),
                  const SizedBox(height: 14),
                  if (wide) ...[
                    _DesktopStudio(
                      snapshot: snapshot,
                      copy: copy,
                      selectedSection: selectedSection,
                      selectedMaterial: selectedMaterial,
                      localDraft: selectedSection == null
                          ? ''
                          : _localDrafts[selectedSection] ?? '',
                      onSectionSelected: (index) =>
                          setState(() => _selectedSection = index),
                      onMaterialSelected: (index) =>
                          setState(() => _selectedMaterial = index),
                      onDraftChanged: (value) {
                        if (selectedSection != null) {
                          setState(() => _localDrafts[selectedSection] = value);
                        }
                      },
                    ),
                    const SizedBox(height: 14),
                    _AudioStage(snapshot: snapshot, copy: copy),
                  ] else
                    _MobileStudio(
                      snapshot: snapshot,
                      copy: copy,
                      task: _mobileTask,
                      selectedSection: selectedSection,
                      selectedMaterial: selectedMaterial,
                      localDraft: selectedSection == null
                          ? ''
                          : _localDrafts[selectedSection] ?? '',
                      onTaskChanged: (task) =>
                          setState(() => _mobileTask = task),
                      onSectionSelected: (index) =>
                          setState(() => _selectedSection = index),
                      onMaterialSelected: (index) =>
                          setState(() => _selectedMaterial = index),
                      onDraftChanged: (value) {
                        if (selectedSection != null) {
                          setState(() => _localDrafts[selectedSection] = value);
                        }
                      },
                    ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}

class _Header extends StatelessWidget {
  const _Header({required this.copy, required this.onRefresh});

  final _Bmp08Copy copy;
  final VoidCallback onRefresh;

  @override
  Widget build(BuildContext context) => Row(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Expanded(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              context.lumenisL10n.text('screen.BMP-08'),
              style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                color: LumenisTheme.of(context).foreground,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              copy.subtitle,
              style: TextStyle(
                color: LumenisTheme.of(context).muted,
                height: 1.5,
              ),
            ),
          ],
        ),
      ),
      IconButton(
        onPressed: onRefresh,
        tooltip: copy.refresh,
        icon: const Icon(Icons.refresh_rounded),
      ),
    ],
  );
}

class _DesktopStudio extends StatelessWidget {
  const _DesktopStudio({
    required this.snapshot,
    required this.copy,
    required this.selectedSection,
    required this.selectedMaterial,
    required this.localDraft,
    required this.onSectionSelected,
    required this.onMaterialSelected,
    required this.onDraftChanged,
  });

  final Bmp08Snapshot snapshot;
  final _Bmp08Copy copy;
  final int? selectedSection;
  final int? selectedMaterial;
  final String localDraft;
  final ValueChanged<int> onSectionSelected;
  final ValueChanged<int> onMaterialSelected;
  final ValueChanged<String> onDraftChanged;

  @override
  Widget build(BuildContext context) => Row(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      SizedBox(
        width: 188,
        child: _MaterialsSectionsRail(
          snapshot: snapshot,
          copy: copy,
          selectedSection: selectedSection,
          selectedMaterial: selectedMaterial,
          onSectionSelected: onSectionSelected,
          onMaterialSelected: onMaterialSelected,
        ),
      ),
      const SizedBox(width: 12),
      Expanded(
        child: _ScriptPanel(
          snapshot: snapshot,
          copy: copy,
          selectedSection: selectedSection,
          localDraft: localDraft,
          onSectionSelected: onSectionSelected,
          onDraftChanged: onDraftChanged,
        ),
      ),
      const SizedBox(width: 12),
      SizedBox(
        width: 248,
        child: _PropertiesPanel(
          snapshot: snapshot,
          copy: copy,
          selectedSection: selectedSection,
          selectedMaterial: selectedMaterial,
        ),
      ),
    ],
  );
}

class _MobileStudio extends StatelessWidget {
  const _MobileStudio({
    required this.snapshot,
    required this.copy,
    required this.task,
    required this.selectedSection,
    required this.selectedMaterial,
    required this.localDraft,
    required this.onTaskChanged,
    required this.onSectionSelected,
    required this.onMaterialSelected,
    required this.onDraftChanged,
  });

  final Bmp08Snapshot snapshot;
  final _Bmp08Copy copy;
  final _MobileStudioTask task;
  final int? selectedSection;
  final int? selectedMaterial;
  final String localDraft;
  final ValueChanged<_MobileStudioTask> onTaskChanged;
  final ValueChanged<int> onSectionSelected;
  final ValueChanged<int> onMaterialSelected;
  final ValueChanged<String> onDraftChanged;

  @override
  Widget build(BuildContext context) {
    final pane = switch (task) {
      _MobileStudioTask.script => _ScriptPanel(
        snapshot: snapshot,
        copy: copy,
        selectedSection: selectedSection,
        localDraft: localDraft,
        onSectionSelected: onSectionSelected,
        onDraftChanged: onDraftChanged,
      ),
      _MobileStudioTask.materials => _MaterialsSectionsRail(
        snapshot: snapshot,
        copy: copy,
        selectedSection: selectedSection,
        selectedMaterial: selectedMaterial,
        onSectionSelected: onSectionSelected,
        onMaterialSelected: onMaterialSelected,
      ),
      _MobileStudioTask.audio => _AudioStage(snapshot: snapshot, copy: copy),
      _MobileStudioTask.properties => _PropertiesPanel(
        snapshot: snapshot,
        copy: copy,
        selectedSection: selectedSection,
        selectedMaterial: selectedMaterial,
      ),
    };
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          copy.mobileWorkspace,
          style: Theme.of(context).textTheme.titleSmall?.copyWith(
            color: LumenisTheme.of(context).quiet,
          ),
        ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 6,
          runSpacing: 6,
          children: [
            for (final option in _MobileStudioTask.values)
              ChoiceChip(
                label: Text(copy.mobilePane(option)),
                selected: task == option,
                onSelected: (_) => onTaskChanged(option),
                visualDensity: VisualDensity.compact,
                side: BorderSide(
                  color: task == option
                      ? LumenisTheme.of(context).bmp.withValues(alpha: 0.25)
                      : LumenisTheme.of(context).line,
                ),
                selectedColor: LumenisTheme.of(
                  context,
                ).bmp.withValues(alpha: 0.09),
                backgroundColor: LumenisTheme.of(context).surface,
              ),
          ],
        ),
        const SizedBox(height: 10),
        AnimatedSwitcher(
          duration: MediaQuery.maybeOf(context)?.disableAnimations == true
              ? Duration.zero
              : const Duration(milliseconds: 160),
          child: KeyedSubtree(key: ValueKey(task), child: pane),
        ),
      ],
    );
  }
}

class _StudioContext extends StatelessWidget {
  const _StudioContext({required this.snapshot, required this.copy});

  final Bmp08Snapshot snapshot;
  final _Bmp08Copy copy;

  @override
  Widget build(BuildContext context) {
    final scopeLabel = !snapshot.scopeApproved
        ? copy.focus
        : snapshot.scope.isGlobal
        ? copy.globalRange
        : copy.focus;
    final brand = !snapshot.scopeApproved
        ? copy.brandUnknown
        : snapshot.scope.localizedName(copy.languageCode) ??
              (snapshot.scope.isGlobal ? copy.allBrands : copy.brandUnknown);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        border: Border(
          top: BorderSide(color: LumenisTheme.of(context).line),
          bottom: BorderSide(color: LumenisTheme.of(context).line),
        ),
      ),
      child: Wrap(
        crossAxisAlignment: WrapCrossAlignment.center,
        spacing: 10,
        runSpacing: 6,
        children: [
          Icon(
            Icons.mic_none_rounded,
            size: 18,
            color: LumenisTheme.of(context).bmp,
          ),
          Text(
            scopeLabel,
            style: TextStyle(
              color: LumenisTheme.of(context).quiet,
              fontSize: 12,
            ),
          ),
          Text(
            brand,
            style: TextStyle(
              color: LumenisTheme.of(context).foreground,
              fontWeight: FontWeight.w600,
              fontSize: 13,
            ),
          ),
          if (snapshot.scopeApproved)
            _StatusLabel(text: copy.scopeVerified, emphasized: true),
        ],
      ),
    );
  }
}

class _MaterialsSectionsRail extends StatelessWidget {
  const _MaterialsSectionsRail({
    required this.snapshot,
    required this.copy,
    required this.selectedSection,
    required this.selectedMaterial,
    required this.onSectionSelected,
    required this.onMaterialSelected,
  });

  final Bmp08Snapshot snapshot;
  final _Bmp08Copy copy;
  final int? selectedSection;
  final int? selectedMaterial;
  final ValueChanged<int> onSectionSelected;
  final ValueChanged<int> onMaterialSelected;

  @override
  Widget build(BuildContext context) => _StudioPanel(
    padding: const EdgeInsets.fromLTRB(10, 12, 10, 12),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _PanelHeading(
          title: copy.sources,
          detail: snapshot.scopeApproved
              ? copy.materialCount(snapshot.materials.length)
              : copy.unknownValue,
        ),
        const SizedBox(height: 8),
        if (snapshot.materials.isEmpty && snapshot.scopeApproved)
          _EmptyLine(text: copy.noSources)
        else if (snapshot.scopeApproved)
          for (var index = 0; index < snapshot.materials.length; index++)
            Semantics(
              button: true,
              selected: selectedMaterial == index,
              label:
                  '${snapshot.materials[index].name}, ${copy.kind(snapshot.materials[index].kind)}',
              child: InkWell(
                onTap: () => onMaterialSelected(index),
                borderRadius: BorderRadius.circular(6),
                child: AnimatedContainer(
                  duration: _bmp08Motion(context),
                  margin: const EdgeInsets.only(bottom: 4),
                  padding: const EdgeInsets.symmetric(
                    horizontal: 8,
                    vertical: 8,
                  ),
                  decoration: BoxDecoration(
                    color: selectedMaterial == index
                        ? LumenisTheme.of(context).bmp.withValues(alpha: 0.08)
                        : Colors.transparent,
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Row(
                    children: [
                      Icon(
                        Icons.insert_drive_file_outlined,
                        size: 15,
                        color: LumenisTheme.of(context).quiet,
                      ),
                      const SizedBox(width: 6),
                      Expanded(
                        child: Text(
                          snapshot.materials[index].name,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            color: LumenisTheme.of(context).foreground,
                            fontSize: 11,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
        const Padding(
          padding: EdgeInsets.symmetric(vertical: 9),
          child: Divider(height: 1),
        ),
        _PanelHeading(
          title: copy.sections,
          detail: snapshot.scopeApproved
              ? copy.sectionCount(snapshot.outline.length)
              : copy.unknownValue,
        ),
        const SizedBox(height: 8),
        if (snapshot.outline.isEmpty && snapshot.scopeApproved)
          _EmptyLine(text: copy.noOutline)
        else if (snapshot.scopeApproved)
          for (var index = 0; index < snapshot.outline.length; index++)
            _Bmp08SectionRow(
              section: snapshot.outline[index],
              copy: copy,
              selected: selectedSection == index,
              compact: true,
              onTap: () => onSectionSelected(index),
            ),
      ],
    ),
  );
}

class _PropertiesPanel extends StatelessWidget {
  const _PropertiesPanel({
    required this.snapshot,
    required this.copy,
    required this.selectedSection,
    required this.selectedMaterial,
  });

  final Bmp08Snapshot snapshot;
  final _Bmp08Copy copy;
  final int? selectedSection;
  final int? selectedMaterial;

  @override
  Widget build(BuildContext context) {
    final unavailable = !snapshot.scopeApproved;
    final section = selectedSection == null
        ? null
        : snapshot.outline[selectedSection!];
    final material = selectedMaterial == null
        ? null
        : snapshot.materials[selectedMaterial!];
    return _StudioPanel(
      padding: const EdgeInsets.fromLTRB(13, 12, 13, 14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _PanelHeading(title: copy.properties, detail: copy.rightsLabel),
          const SizedBox(height: 12),
          _PropertyLine(
            label: copy.selectedSection,
            value: unavailable
                ? copy.unknownValue
                : section?.title ?? copy.noSectionSelected,
          ),
          if (section != null)
            _PropertyLine(label: copy.timecode, value: section.timecode),
          const Divider(height: 20),
          _PropertyLine(
            label: copy.sources,
            value: unavailable
                ? copy.unknownValue
                : material == null
                ? copy.noSources
                : copy.kind(material.kind),
          ),
          if (!unavailable && section != null)
            _PropertyLine(
              label: copy.sourceStatus,
              value: section.hasSource
                  ? copy.sourceAttached
                  : copy.sourcePending,
            ),
          const Divider(height: 20),
          _PropertyLine(
            label: copy.version,
            value: unavailable
                ? copy.unknownValue
                : snapshot.versioned
                ? copy.ready
                : copy.pending,
          ),
          _PropertyLine(
            label: copy.rights,
            value: unavailable
                ? copy.unknownValue
                : snapshot.rightsReady
                ? copy.ready
                : copy.pending,
          ),
        ],
      ),
    );
  }
}

class _Bmp08SectionRow extends StatelessWidget {
  const _Bmp08SectionRow({
    required this.section,
    required this.copy,
    required this.selected,
    required this.onTap,
    this.compact = false,
  });

  final Bmp08OutlineSection section;
  final _Bmp08Copy copy;
  final bool selected;
  final VoidCallback onTap;
  final bool compact;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 4),
    child: Semantics(
      button: true,
      selected: selected,
      label: '${section.timecode}, ${section.title}',
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(7),
        child: AnimatedContainer(
          duration: _bmp08Motion(context),
          curve: Curves.easeOut,
          padding: EdgeInsets.symmetric(
            horizontal: compact ? 7 : 10,
            vertical: compact ? 8 : 10,
          ),
          decoration: BoxDecoration(
            color: selected
                ? LumenisTheme.of(context).bmp.withValues(alpha: 0.08)
                : Colors.transparent,
            borderRadius: BorderRadius.circular(7),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              SizedBox(
                width: compact ? 30 : 42,
                child: Text(
                  section.timecode,
                  style: TextStyle(
                    color: selected
                        ? LumenisTheme.of(context).bmp
                        : LumenisTheme.of(context).quiet,
                    fontSize: compact ? 10 : 11,
                  ),
                ),
              ),
              const SizedBox(width: 6),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      section.title,
                      maxLines: compact ? 2 : 3,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        color: LumenisTheme.of(context).foreground,
                        fontSize: compact ? 11 : 13,
                        fontWeight: selected
                            ? FontWeight.w600
                            : FontWeight.w400,
                      ),
                    ),
                    if (!compact) ...[
                      const SizedBox(height: 4),
                      Text(
                        section.hasSource
                            ? copy.sourceAttached
                            : copy.sourcePending,
                        style: TextStyle(
                          color: LumenisTheme.of(context).muted,
                          fontSize: 11,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    ),
  );
}

class _StudioPanel extends StatelessWidget {
  const _StudioPanel({
    required this.child,
    this.padding = const EdgeInsets.all(14),
  });

  final Widget child;
  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) => DecoratedBox(
    decoration: BoxDecoration(
      color: LumenisTheme.of(context).surface,
      border: Border.all(color: LumenisTheme.of(context).line),
      borderRadius: BorderRadius.circular(8),
    ),
    child: Padding(padding: padding, child: child),
  );
}

class _PanelHeading extends StatelessWidget {
  const _PanelHeading({required this.title, this.detail});

  final String title;
  final String? detail;

  @override
  Widget build(BuildContext context) => Row(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Expanded(
        child: Text(
          title,
          style: TextStyle(
            color: LumenisTheme.of(context).foreground,
            fontSize: 13,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
      if (detail != null)
        Text(
          detail!,
          style: TextStyle(color: LumenisTheme.of(context).quiet, fontSize: 10),
        ),
    ],
  );
}

class _StatusLabel extends StatelessWidget {
  const _StatusLabel({required this.text, required this.emphasized});

  final String text;
  final bool emphasized;

  @override
  Widget build(BuildContext context) => DecoratedBox(
    decoration: BoxDecoration(
      color: emphasized
          ? LumenisTheme.of(context).bmp.withValues(alpha: 0.07)
          : LumenisTheme.of(context).surfaceRaised,
      borderRadius: BorderRadius.circular(5),
    ),
    child: Padding(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
      child: Text(
        text,
        style: TextStyle(
          color: emphasized
              ? LumenisTheme.of(context).bmp
              : LumenisTheme.of(context).quiet,
          fontSize: 10,
        ),
      ),
    ),
  );
}

class _PropertyLine extends StatelessWidget {
  const _PropertyLine({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 5),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 68,
          child: Text(
            label,
            style: TextStyle(
              color: LumenisTheme.of(context).quiet,
              fontSize: 11,
            ),
          ),
        ),
        const SizedBox(width: 6),
        Expanded(
          child: Text(
            value,
            style: TextStyle(
              color: LumenisTheme.of(context).foreground,
              fontSize: 11,
              height: 1.35,
            ),
          ),
        ),
      ],
    ),
  );
}

class _EmptyLine extends StatelessWidget {
  const _EmptyLine({required this.text, this.roomy = false});

  final String text;
  final bool roomy;

  @override
  Widget build(BuildContext context) => Padding(
    padding: EdgeInsets.symmetric(vertical: roomy ? 22 : 10, horizontal: 4),
    child: Text(
      text,
      style: TextStyle(
        color: LumenisTheme.of(context).quiet,
        fontSize: 11,
        height: 1.45,
      ),
    ),
  );
}

Duration _bmp08Motion(BuildContext context) =>
    MediaQuery.maybeOf(context)?.disableAnimations == true
    ? Duration.zero
    : const Duration(milliseconds: 160);

class _AudioStage extends StatelessWidget {
  const _AudioStage({required this.snapshot, required this.copy});

  final Bmp08Snapshot snapshot;
  final _Bmp08Copy copy;

  @override
  Widget build(BuildContext context) {
    final audioReferenceAvailable =
        snapshot.scopeApproved && snapshot.audioAvailable;
    return _StudioPanel(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(2, 0, 2, 2),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _PanelHeading(
              title: copy.audioStage,
              detail: audioReferenceAvailable
                  ? copy.audioReady
                  : snapshot.scopeApproved
                  ? copy.audioPending
                  : copy.unknownValue,
            ),
            const SizedBox(height: 10),
            Semantics(
              label: audioReferenceAvailable
                  ? copy.audioPreviewUnavailable
                  : copy.audioPendingDetail,
              child: Container(
                height: 82,
                width: double.infinity,
                decoration: BoxDecoration(
                  color: LumenisTheme.of(context).canvas,
                  border: Border.all(color: LumenisTheme.of(context).line),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Center(
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 12),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          Icons.music_note_outlined,
                          size: 19,
                          color: LumenisTheme.of(context).quiet,
                        ),
                        const SizedBox(height: 5),
                        Text(
                          audioReferenceAvailable
                              ? copy.audioPreviewUnavailable
                              : snapshot.scopeApproved
                              ? copy.audioPendingDetail
                              : copy.audioPendingDetail,
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            color: LumenisTheme.of(context).muted,
                            fontSize: 11,
                            height: 1.35,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
            const SizedBox(height: 10),
            _StudioFlags(snapshot: snapshot, copy: copy),
          ],
        ),
      ),
    );
  }
}

class _StudioFlags extends StatelessWidget {
  const _StudioFlags({required this.snapshot, required this.copy});

  final Bmp08Snapshot snapshot;
  final _Bmp08Copy copy;

  @override
  Widget build(BuildContext context) => Wrap(
    spacing: 8,
    runSpacing: 8,
    children: [
      _Flag(
        label: copy.version,
        value: !snapshot.scopeApproved
            ? copy.unknownValue
            : snapshot.versioned
            ? copy.ready
            : copy.pending,
        ready: snapshot.versioned,
      ),
      _Flag(
        label: copy.rights,
        value: !snapshot.scopeApproved
            ? copy.unknownValue
            : snapshot.rightsReady
            ? copy.ready
            : copy.pending,
        ready: snapshot.rightsReady,
      ),
    ],
  );
}

class _Flag extends StatelessWidget {
  const _Flag({required this.label, required this.value, required this.ready});

  final String label;
  final String value;
  final bool ready;

  @override
  Widget build(BuildContext context) => DecoratedBox(
    decoration: BoxDecoration(
      color: ready
          ? LumenisTheme.of(context).positive.withValues(alpha: 0.08)
          : LumenisTheme.of(context).surfaceRaised,
      border: Border.all(
        color: ready
            ? LumenisTheme.of(context).positive.withValues(alpha: 0.35)
            : LumenisTheme.of(context).line,
      ),
      borderRadius: BorderRadius.circular(20),
    ),
    child: Padding(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
      child: Text(
        '$label · $value',
        style: TextStyle(
          color: ready
              ? LumenisTheme.of(context).positive
              : LumenisTheme.of(context).muted,
          fontSize: 11,
        ),
      ),
    ),
  );
}

class _ScriptPanel extends StatelessWidget {
  const _ScriptPanel({
    required this.snapshot,
    required this.copy,
    required this.selectedSection,
    required this.localDraft,
    required this.onSectionSelected,
    required this.onDraftChanged,
  });

  final Bmp08Snapshot snapshot;
  final _Bmp08Copy copy;
  final int? selectedSection;
  final String localDraft;
  final ValueChanged<int> onSectionSelected;
  final ValueChanged<String> onDraftChanged;

  @override
  Widget build(BuildContext context) => DecoratedBox(
    decoration: BoxDecoration(
      color: LumenisTheme.of(context).surface,
      borderRadius: BorderRadius.circular(8),
      border: Border.all(color: LumenisTheme.of(context).line),
    ),
    child: Padding(
      padding: const EdgeInsets.fromLTRB(16, 14, 16, 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _PanelHeading(
            title: copy.script,
            detail: snapshot.scopeApproved
                ? copy.sectionCount(snapshot.outline.length)
                : copy.unknownValue,
          ),
          const SizedBox(height: 10),
          if (snapshot.outline.isEmpty && snapshot.scopeApproved)
            _EmptyLine(text: copy.noOutline, roomy: true)
          else if (!snapshot.scopeApproved)
            _EmptyLine(text: copy.scriptPreviewHint, roomy: true)
          else
            for (var index = 0; index < snapshot.outline.length; index++)
              _Bmp08SectionRow(
                section: snapshot.outline[index],
                copy: copy,
                selected: selectedSection == index,
                onTap: () => onSectionSelected(index),
              ),
          if (snapshot.scopeApproved && selectedSection != null) ...[
            const SizedBox(height: 10),
            const Divider(height: 1),
            const SizedBox(height: 10),
            Text(
              copy.localDraftTitle,
              style: TextStyle(
                color: LumenisTheme.of(context).foreground,
                fontSize: 13,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              copy.localDraftHint,
              style: TextStyle(
                color: LumenisTheme.of(context).quiet,
                fontSize: 11,
                height: 1.4,
              ),
            ),
            const SizedBox(height: 8),
            TextFormField(
              key: ValueKey<int>(selectedSection!),
              initialValue: localDraft,
              minLines: 3,
              maxLines: 6,
              onChanged: onDraftChanged,
              decoration: InputDecoration(
                hintText: copy.localDraftPlaceholder,
                contentPadding: const EdgeInsets.all(12),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                  borderSide: BorderSide(color: LumenisTheme.of(context).line),
                ),
              ),
            ),
          ],
        ],
      ),
    ),
  );
}

class _Gate extends StatelessWidget {
  const _Gate({required this.copy});

  final _Bmp08Copy copy;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(12),
    decoration: BoxDecoration(
      color: LumenisTheme.of(context).caution.withValues(alpha: 0.07),
      border: Border.all(
        color: LumenisTheme.of(context).caution.withValues(alpha: 0.22),
      ),
      borderRadius: BorderRadius.circular(7),
    ),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(
          Icons.lock_outline_rounded,
          size: 18,
          color: LumenisTheme.of(context).caution,
        ),
        const SizedBox(width: 8),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                copy.rangePending,
                style: TextStyle(
                  color: LumenisTheme.of(context).foreground,
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 3),
              Text(
                copy.withheldDetails,
                style: TextStyle(
                  color: LumenisTheme.of(context).muted,
                  fontSize: 11,
                  height: 1.4,
                ),
              ),
            ],
          ),
        ),
      ],
    ),
  );
}

class _NoticePanel extends StatelessWidget {
  const _NoticePanel({
    required this.icon,
    required this.title,
    required this.detail,
  });

  final IconData icon;
  final String title;
  final String detail;

  @override
  Widget build(BuildContext context) => DecoratedBox(
    decoration: BoxDecoration(
      color: LumenisTheme.of(context).surface,
      borderRadius: BorderRadius.circular(16),
      border: Border.all(color: LumenisTheme.of(context).line),
    ),
    child: Padding(
      padding: const EdgeInsets.all(24),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: LumenisTheme.of(context).caution, size: 28),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 8),
                Text(
                  detail,
                  style: TextStyle(
                    color: LumenisTheme.of(context).muted,
                    height: 1.55,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    ),
  );
}

class _ActionRail extends StatelessWidget {
  const _ActionRail({
    required this.copy,
    required this.state,
    required this.actionId,
    required this.onAction,
  });

  final _Bmp08Copy copy;
  final Bmp08ActionState state;
  final String? actionId;
  final void Function(String actionId, String permission) onAction;

  @override
  Widget build(BuildContext context) {
    final notice = switch (state) {
      Bmp08ActionState.idle => null,
      Bmp08ActionState.blocked => copy.actionBlocked,
      Bmp08ActionState.staged => copy.actionStaged,
    };
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (notice != null) ...[
          Semantics(
            liveRegion: true,
            child: Text(
              notice,
              style: TextStyle(
                color: state == Bmp08ActionState.staged
                    ? LumenisTheme.of(context).positive
                    : LumenisTheme.of(context).caution,
              ),
            ),
          ),
          const SizedBox(height: 12),
        ],
        Wrap(
          spacing: 10,
          runSpacing: 10,
          children: [
            FilledButton.icon(
              onPressed: () => onAction('BMP-08.gen-script', 'podcast:draft'),
              icon: const Icon(Icons.edit_note_rounded),
              label: Text(copy.generateScript),
            ),
            OutlinedButton.icon(
              onPressed: () => onAction('BMP-08.render', 'podcast:render'),
              icon: const Icon(Icons.movie_creation_outlined),
              label: Text(copy.render),
            ),
          ],
        ),
        const SizedBox(height: 5),
        Text(
          copy.actionLocalOnly,
          style: TextStyle(color: LumenisTheme.of(context).quiet, fontSize: 10),
        ),
        if (actionId == 'BMP-08.render') ...[
          const SizedBox(height: 9),
          Text(
            copy.renderGuard,
            style: TextStyle(
              color: LumenisTheme.of(context).quiet,
              fontSize: 12,
            ),
          ),
        ],
      ],
    );
  }
}

class _Loading extends StatelessWidget {
  const _Loading();

  @override
  Widget build(BuildContext context) => Center(
    child: Semantics(
      liveRegion: true,
      label: _Bmp08Copy.of(context).loading,
      child: Padding(
        padding: EdgeInsets.all(48),
        child: CircularProgressIndicator(color: LumenisTheme.of(context).bmp),
      ),
    ),
  );
}

class _Failure extends StatelessWidget {
  const _Failure({required this.kind, required this.onRetry});

  final Bmp08FailureKind kind;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final copy = _Bmp08Copy.of(context);
    final title = switch (kind) {
      Bmp08FailureKind.authentication => copy.signIn,
      Bmp08FailureKind.permissionDenied => copy.accessDenied,
      Bmp08FailureKind.offline => copy.offline,
      Bmp08FailureKind.server => copy.unavailableTitle,
    };
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _NoticePanel(
              icon: Icons.cloud_off_outlined,
              title: title,
              detail: copy.retryDetail,
            ),
            const SizedBox(height: 14),
            OutlinedButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh_rounded),
              label: Text(copy.refresh),
            ),
          ],
        ),
      ),
    );
  }
}

class _Bmp08Copy {
  _Bmp08Copy(this.languageCode);

  final String languageCode;

  static _Bmp08Copy of(BuildContext context) {
    final languageCode = Localizations.localeOf(context).languageCode;
    return _Bmp08Copy(
      languageCode == 'en' || languageCode == 'ko' ? languageCode : 'zh-CN',
    );
  }

  String get subtitle => _get('subtitle');
  String get refresh => _get('refresh');
  String get focus => _get('focus');
  String get globalRange => _get('globalRange');
  String get allBrands => _get('allBrands');
  String get brandUnknown => _get('brandUnknown');
  String get rightsLabel => _get('rightsLabel');
  String get audioStage => _get('audioStage');
  String get audioReady => _get('audioReady');
  String get audioPending => _get('audioPending');
  String get audioReadyDetail => _get('audioReadyDetail');
  String get audioPendingDetail => _get('audioPendingDetail');
  String get audioPreviewUnavailable => _get('audioPreviewUnavailable');
  String get version => _get('version');
  String get rights => _get('rights');
  String get ready => _get('ready');
  String get pending => _get('pending');
  String get script => _get('script');
  String get sections => _get('sections');
  String get noOutline => _get('noOutline');
  String get sourceAttached => _get('sourceAttached');
  String get sourcePending => _get('sourcePending');
  String get sources => _get('sources');
  String get noSources => _get('noSources');
  String get unavailableTitle => _get('unavailableTitle');
  String get unavailableDetail => _get('unavailableDetail');
  String get notCollectedTitle => _get('notCollectedTitle');
  String get notCollectedDetail => _get('notCollectedDetail');
  String get actionBlocked => _get('actionBlocked');
  String get actionStaged => _get('actionStaged');
  String get renderGuard => _get('renderGuard');
  String get loading => _get('loading');
  String get signIn => _get('signIn');
  String get accessDenied => _get('accessDenied');
  String get offline => _get('offline');
  String get retryDetail => _get('retryDetail');
  String get generateScript => _get('generateScript');
  String get render => _get('render');
  String get actionLocalOnly => _get('actionLocalOnly');
  String get rangePending => _get('rangePending');
  String get scopeVerified => _get('scopeVerified');
  String get withheldDetails => _get('withheldDetails');
  String get properties => _get('properties');
  String get selectedSection => _get('selectedSection');
  String get noSectionSelected => _get('noSectionSelected');
  String get timecode => _get('timecode');
  String get sourceStatus => _get('sourceStatus');
  String get localDraftTitle => _get('localDraftTitle');
  String get localDraftHint => _get('localDraftHint');
  String get localDraftPlaceholder => _get('localDraftPlaceholder');
  String get scriptPreviewHint => _get('scriptPreviewHint');
  String get unknownValue => '—';
  String get mobileWorkspace => _get('mobileWorkspace');
  String sectionCount(int count) =>
      _get('sectionCount').replaceAll('{count}', '$count');
  String materialCount(int count) =>
      _get('materialCount').replaceAll('{count}', '$count');
  String mobilePane(_MobileStudioTask task) => _get(switch (task) {
    _MobileStudioTask.script => 'mobile.script',
    _MobileStudioTask.materials => 'mobile.materials',
    _MobileStudioTask.audio => 'mobile.audio',
    _MobileStudioTask.properties => 'mobile.properties',
  });

  String kind(String value) => _get('kind.$value');

  String _get(String key) =>
      _values[languageCode]?[key] ?? _values['zh-CN']![key]!;

  static const _values = <String, Map<String, String>>{
    'zh-CN': {
      'subtitle': '让脚本、音频、逐字稿、来源与版权在同一个制作台对齐。',
      'refresh': '刷新播客工作台',
      'focus': '当前品牌',
      'globalRange': '全球品牌范围',
      'allBrands': '已授权的全球品牌集合',
      'brandUnknown': '品牌名称暂不可用',
      'rightsLabel': '版权与版本',
      'audioStage': '音频舞台',
      'audioReady': '音频来源已登记',
      'audioPending': '音频待提供',
      'audioReadyDetail': '可进入逐段校对。',
      'audioPendingDetail': '当前只显示制作结构，不播放或导出未确认音频。',
      'audioPreviewUnavailable': '音频来源已登记；可播放音频与真实波形尚未提供。',
      'version': '版本',
      'rights': '版权',
      'ready': '已确认',
      'pending': '待确认',
      'script': '逐字稿与分段',
      'sections': '分段',
      'noOutline': '还没有可确认的脚本段落。',
      'sourceAttached': '来源已关联',
      'sourcePending': '来源待确认',
      'sources': '制作资料',
      'noSources': '当前品牌没有可确认的制作资料。',
      'unavailableTitle': '播客制作资料暂不可用',
      'unavailableDetail': '当前品牌范围或来源尚未确认，暂不显示其他品牌的脚本、音频或版权状态。',
      'notCollectedTitle': '还没有播客资料',
      'notCollectedDetail': '脚本、来源、音频、版本、发布与版权状态准备好后，这里会成为可编辑的制作台。',
      'actionBlocked': '当前范围还不能执行这项制作操作；请先确认品牌范围与资料条件。',
      'actionStaged': '本地制作请求草稿已保存；尚未生成脚本或渲染成片。',
      'renderGuard': '这里仅保存本地渲染请求草稿；不会生成成片，直到授权、版权确认与明确结果都准备好。',
      'loading': '正在加载播客工作台',
      'signIn': '需要登录后查看播客',
      'accessDenied': '当前账号暂时无法查看播客',
      'offline': '暂时无法连接播客服务',
      'retryDetail': '请检查连接后重试；未经确认的音频与脚本不会显示。',
      'generateScript': '保存脚本请求草稿',
      'render': '保存渲染请求草稿',
      'actionLocalOnly': '仅暂存本地请求草稿；不会生成脚本或音频。',
      'rangePending': '播客范围尚未确认',
      'scopeVerified': '当前范围已确认',
      'withheldDetails': '范围与来源验证完成前，资料、脚本、音频和版权信息均保持隐藏。',
      'properties': '属性',
      'selectedSection': '当前段落',
      'noSectionSelected': '未选择段落',
      'timecode': '时间码',
      'sourceStatus': '来源状态',
      'localDraftTitle': '本地修订草稿',
      'localDraftHint': '只保留在此页面状态，不会发送或保存到服务端。',
      'localDraftPlaceholder': '输入本次审阅的临时修改意见',
      'mobileWorkspace': '选择要处理的工作区',
      'scriptPreviewHint': '经确认的逐字稿会按时间码显示在这里。',
      'mobile.script': '脚本',
      'mobile.materials': '资料',
      'mobile.audio': '音频',
      'mobile.properties': '属性',
      'sectionCount': '共 {count} 段',
      'materialCount': '共 {count} 项',
      'kind.FILE': '文件',
      'kind.BRIEF': 'Brief',
      'kind.AUDIO': '音频',
      'kind.TRANSCRIPT': '逐字稿',
    },
    'en': {
      'subtitle':
          'Align script, audio, transcript, sources and rights in one production desk.',
      'refresh': 'Refresh podcast studio',
      'focus': 'Brand focus',
      'globalRange': 'Global brand range',
      'allBrands': 'Authorized global brand set',
      'brandUnknown': 'Brand name unavailable',
      'rightsLabel': 'Rights and version',
      'audioStage': 'Audio stage',
      'audioReady': 'Audio reference confirmed',
      'audioPending': 'Audio pending',
      'audioReadyDetail': 'Ready for timecoded review.',
      'audioPendingDetail':
          'Only the studio structure is shown; unconfirmed audio is not played or exported.',
      'audioPreviewUnavailable':
          'Audio reference confirmed; playable audio and waveform data are not available here.',
      'version': 'Version',
      'rights': 'Rights',
      'ready': 'Confirmed',
      'pending': 'Pending',
      'script': 'Transcript and outline',
      'sections': 'Sections',
      'noOutline': 'No confirmed script sections are available.',
      'sourceAttached': 'Source attached',
      'sourcePending': 'Source pending',
      'sources': 'Production material',
      'noSources':
          'No confirmed production material is available for this brand.',
      'unavailableTitle': 'Podcast material is unavailable',
      'unavailableDetail':
          'The current brand range or source is not confirmed. Scripts, audio and rights from another brand stay hidden.',
      'notCollectedTitle': 'No podcast material has been collected',
      'notCollectedDetail':
          'Script, source, audio, version, publishing and rights states will become editable when confirmed.',
      'actionBlocked':
          'This production action is not available in the current brand range or material state.',
      'actionStaged':
          'Local production request draft saved. No script was generated and no cut was rendered.',
      'renderGuard':
          'Only a local render-request draft is saved here; no cut is generated until access, rights confirmation, and an explicit result are ready.',
      'loading': 'Loading podcast studio',
      'signIn': 'Sign in to view podcasts',
      'accessDenied': 'This account cannot view podcasts right now',
      'offline': 'Podcast service is unavailable',
      'retryDetail':
          'Check the connection and try again. Unconfirmed audio and scripts stay hidden.',
      'generateScript': 'Save script-request draft',
      'render': 'Save render-request draft',
      'actionLocalOnly':
          'Only stages a local request draft; no script or audio is generated.',
      'rangePending': 'Podcast scope is not confirmed',
      'scopeVerified': 'Current scope confirmed',
      'withheldDetails':
          'Materials, script, audio and rights stay hidden until scope and sources are verified.',
      'properties': 'Properties',
      'selectedSection': 'Selected section',
      'noSectionSelected': 'No section selected',
      'timecode': 'Timecode',
      'sourceStatus': 'Source status',
      'localDraftTitle': 'Local revision draft',
      'localDraftHint':
          'Held only in this page state; it is not sent or saved to the server.',
      'localDraftPlaceholder': 'Write a temporary review note',
      'mobileWorkspace': 'Choose a workspace task',
      'scriptPreviewHint':
          'Verified transcript sections will appear here by timecode.',
      'mobile.script': 'Script',
      'mobile.materials': 'Sources',
      'mobile.audio': 'Audio',
      'mobile.properties': 'Properties',
      'sectionCount': '{count} sections',
      'materialCount': '{count} items',
      'kind.FILE': 'File',
      'kind.BRIEF': 'Brief',
      'kind.AUDIO': 'Audio',
      'kind.TRANSCRIPT': 'Transcript',
    },
    'ko': {
      'subtitle': '스크립트, 오디오, 대본, 출처와 권리를 하나의 제작 데스크에서 맞춥니다.',
      'refresh': '팟캐스트 스튜디오 새로고침',
      'focus': '현재 브랜드',
      'globalRange': '글로벌 브랜드 범위',
      'allBrands': '승인된 글로벌 브랜드 집합',
      'brandUnknown': '브랜드 이름을 사용할 수 없습니다',
      'rightsLabel': '권리와 버전',
      'audioStage': '오디오 스테이지',
      'audioReady': '오디오 출처 확인됨',
      'audioPending': '오디오 대기',
      'audioReadyDetail': '타임코드 검토를 시작할 수 있습니다.',
      'audioPendingDetail': '제작 구조만 표시하며 확인되지 않은 오디오는 재생하거나 내보내지 않습니다.',
      'audioPreviewUnavailable': '오디오 출처는 확인됐지만 재생 데이터와 실제 파형은 제공되지 않았습니다.',
      'version': '버전',
      'rights': '권리',
      'ready': '확인됨',
      'pending': '대기',
      'script': '대본과 구성',
      'sections': '구간',
      'noOutline': '확인된 스크립트 구간이 없습니다.',
      'sourceAttached': '출처 연결됨',
      'sourcePending': '출처 대기',
      'sources': '제작 자료',
      'noSources': '이 브랜드에서 확인된 제작 자료가 없습니다.',
      'unavailableTitle': '팟캐스트 제작 자료를 사용할 수 없습니다',
      'unavailableDetail':
          '현재 브랜드 범위 또는 출처가 확인되지 않았습니다. 다른 브랜드의 스크립트, 오디오와 권리를 표시하지 않습니다.',
      'notCollectedTitle': '아직 팟캐스트 자료가 수집되지 않았습니다',
      'notCollectedDetail': '스크립트, 출처, 오디오, 버전, 게시와 권리가 확인되면 편집할 수 있습니다.',
      'actionBlocked': '현재 브랜드 범위 또는 자료 상태에서는 이 제작 작업을 사용할 수 없습니다.',
      'actionStaged': '로컬 제작 요청 초안을 저장했습니다. 스크립트를 생성하거나 컷을 렌더링하지 않았습니다.',
      'renderGuard':
          '여기서는 로컬 렌더링 요청 초안만 저장합니다. 접근, 권리 확인과 명시적 결과가 준비되기 전에는 컷을 생성하지 않습니다.',
      'loading': '팟캐스트 스튜디오를 불러오는 중',
      'signIn': '팟캐스트를 보려면 로그인하세요',
      'accessDenied': '이 계정은 지금 팟캐스트를 볼 수 없습니다',
      'offline': '팟캐스트 서비스에 연결할 수 없습니다',
      'retryDetail': '연결을 확인하고 다시 시도하세요. 확인되지 않은 오디오와 스크립트는 숨겨집니다.',
      'generateScript': '스크립트 요청 초안 저장',
      'render': '렌더링 요청 초안 저장',
      'actionLocalOnly': '요청 초안만 이 화면에 임시 보관합니다. 스크립트나 오디오를 생성하지 않습니다.',
      'rangePending': '팟캐스트 범위가 확인되지 않았습니다',
      'scopeVerified': '현재 범위 확인됨',
      'withheldDetails': '범위와 출처가 확인될 때까지 자료, 스크립트, 오디오와 권리 정보를 숨깁니다.',
      'properties': '속성',
      'selectedSection': '선택한 구간',
      'noSectionSelected': '선택된 구간 없음',
      'timecode': '타임코드',
      'sourceStatus': '출처 상태',
      'localDraftTitle': '로컬 수정 초안',
      'localDraftHint': '이 화면에만 임시 보관하며 서버로 보내거나 저장하지 않습니다.',
      'localDraftPlaceholder': '검토용 임시 수정 의견 입력',
      'mobileWorkspace': '작업할 영역 선택',
      'scriptPreviewHint': '확인된 대본 구간이 타임코드 순서로 표시됩니다.',
      'mobile.script': '스크립트',
      'mobile.materials': '자료',
      'mobile.audio': '오디오',
      'mobile.properties': '속성',
      'sectionCount': '{count}개 구간',
      'materialCount': '{count}개 항목',
      'kind.FILE': '파일',
      'kind.BRIEF': '브리프',
      'kind.AUDIO': '오디오',
      'kind.TRANSCRIPT': '대본',
    },
  };
}
