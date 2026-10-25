import 'package:file_selector/file_selector.dart';
import 'package:flutter/material.dart';

import '../../../core/lumenis_icon.dart';
import '../../../core/lumenis_botanical.dart';
import '../../../core/lumenis_theme.dart';
import 'package:flutter/services.dart' show rootBundle;

import '../../../l10n/lumenis_localizations.dart';
import '../../../platform/lumenis_window_material.dart';
import 'sys05_appearance_controller.dart';
import '../sys02/sys_system_foundation.dart' show SysSystemCopy;

class Sys05AppearanceButton extends StatelessWidget {
  const Sys05AppearanceButton({super.key});
  @override
  Widget build(BuildContext context) {
    final controller = Sys05AppearanceScope.maybeOf(context);
    if (controller == null) return const SizedBox.shrink();
    return IconButton(
      key: const ValueKey('appearance/open'),
      tooltip: context.lumenisL10n.text('appearance.title'),
      icon: const LumenisIcon(Icons.palette_outlined, size: 20),
      onPressed: () {
        FocusManager.instance.primaryFocus?.unfocus();
        if (MediaQuery.sizeOf(context).width >= 768) {
          showDialog<void>(
            context: context,
            barrierColor: Colors.black.withValues(alpha: .12),
            animationStyle: MediaQuery.disableAnimationsOf(context)
                ? AnimationStyle.noAnimation
                : const AnimationStyle(
                    duration: LumenisMotion.panel,
                    reverseDuration: LumenisMotion.exit,
                    curve: Curves.easeOutCubic,
                    reverseCurve: Curves.easeInCubic,
                  ),
            builder: (context) => Dialog(
              key: const ValueKey('appearance/desktop-panel'),
              alignment: Alignment.centerRight,
              insetPadding: const EdgeInsets.all(16),
              backgroundColor: Theme.of(
                context,
              ).bottomSheetTheme.modalBackgroundColor,
              surfaceTintColor: Colors.transparent,
              clipBehavior: Clip.antiAlias,
              child: SizedBox(
                key: const ValueKey('appearance/desktop-content'),
                width: 460,
                height: MediaQuery.sizeOf(context).height - 32,
                child: Sys05AppearanceEditor(
                  controller: controller,
                  onClose: () => Navigator.of(context).pop(),
                ),
              ),
            ),
          );
          return;
        }
        showModalBottomSheet<void>(
          context: context,
          sheetAnimationStyle: MediaQuery.disableAnimationsOf(context)
              ? AnimationStyle.noAnimation
              : const AnimationStyle(
                  duration: LumenisMotion.page,
                  reverseDuration: LumenisMotion.exit,
                ),
          isScrollControlled: true,
          useSafeArea: true,
          showDragHandle: false,
          constraints: const BoxConstraints(maxWidth: 620),
          builder: (context) => SafeArea(
            child: Padding(
              padding: EdgeInsets.only(
                bottom: MediaQuery.viewInsetsOf(context).bottom,
              ),
              child: SizedBox(
                key: const ValueKey('appearance/phone-panel'),
                height: MediaQuery.sizeOf(context).height * .92,
                child: Sys05AppearanceEditor(
                  controller: controller,
                  onClose: () => Navigator.of(context).pop(),
                ),
              ),
            ),
          ),
        );
      },
    );
  }
}

class Sys05AppearanceEditor extends StatefulWidget {
  const Sys05AppearanceEditor({
    required this.controller,
    this.onClose,
    this.embedded = false,
    super.key,
  });
  final Sys05AppearanceController controller;
  final VoidCallback? onClose;
  final bool embedded;
  @override
  State<Sys05AppearanceEditor> createState() => _Sys05AppearanceEditorState();
}

class _Sys05AppearanceEditorState extends State<Sys05AppearanceEditor> {
  final _hex = TextEditingController();
  String? _localError;
  bool _choosing = false;
  @override
  void initState() {
    super.initState();
    _hex.text = widget.controller.solidColor
        .toARGB32()
        .toRadixString(16)
        .substring(2)
        .toUpperCase();
  }

  @override
  void dispose() {
    _hex.dispose();
    super.dispose();
  }

  Future<void> _chooseWallpaper() async {
    if (_choosing || widget.controller.resetting) return;
    setState(() {
      _choosing = true;
      _localError = null;
    });
    try {
      final file = await openFile(
        acceptedTypeGroups: const [
          XTypeGroup(
            label: 'Images',
            extensions: ['png', 'jpg', 'jpeg', 'webp'],
            mimeTypes: ['image/png', 'image/jpeg', 'image/webp'],
            uniformTypeIdentifiers: ['public.image'],
          ),
        ],
      );
      if (file == null || !mounted) return;
      if (await file.length() > Sys05AppearanceController.maxWallpaperBytes) {
        if (mounted) setState(() => _localError = 'appearance.invalidImage');
        return;
      }
      await widget.controller.setWallpaper(await file.readAsBytes());
    } catch (_) {
      if (mounted) setState(() => _localError = 'appearance.chooseFailed');
    } finally {
      if (mounted) setState(() => _choosing = false);
    }
  }

  Future<void> _choosePresetWallpaper(String assetPath) async {
    if (_choosing || widget.controller.resetting) return;
    setState(() {
      _choosing = true;
      _localError = null;
    });
    try {
      final image = await rootBundle.load(assetPath);
      final bytes = image.buffer.asUint8List(
        image.offsetInBytes,
        image.lengthInBytes,
      );
      await widget.controller.setWallpaper(bytes);
    } catch (_) {
      if (mounted) setState(() => _localError = 'appearance.chooseFailed');
    } finally {
      if (mounted) setState(() => _choosing = false);
    }
  }

  void _selectMode(WorkspaceBackdrop mode) {
    if (mode == WorkspaceBackdrop.wallpaper) {
      _chooseWallpaper();
      return;
    }
    widget.controller.update(mode: mode);
  }

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
    animation: widget.controller,
    builder: (context, _) {
      final c = widget.controller;
      if (!c.loaded) {
        return const Padding(
          padding: EdgeInsets.all(40),
          child: Center(child: CircularProgressIndicator()),
        );
      }
      final scheme = Theme.of(context).colorScheme;
      final palette = LumenisTheme.of(context);
      String copy(String key, {Map<String, Object?> values = const {}}) =>
          context.lumenisL10n.text(key, values: values);
      final error = _localError ?? c.errorKey;
      final compact = MediaQuery.sizeOf(context).width < 480;
      final horizontalPadding = compact
          ? LumenisSpace.control
          : LumenisSpace.section;
      final heading = Row(
        children: [
          Expanded(
            child: Text(
              copy('appearance.title'),
              style: Theme.of(context).textTheme.headlineSmall,
            ),
          ),
          if (widget.onClose != null)
            IconButton(
              key: const ValueKey('appearance/close'),
              tooltip: MaterialLocalizations.of(context).closeButtonTooltip,
              onPressed: widget.onClose,
              icon: const LumenisIcon(Icons.close),
            ),
        ],
      );
      final content = SingleChildScrollView(
        primary: widget.embedded ? false : null,
        physics: widget.embedded ? const NeverScrollableScrollPhysics() : null,
        padding: EdgeInsets.fromLTRB(
          widget.embedded ? 0 : horizontalPadding,
          6,
          widget.embedded ? 0 : horizontalPadding,
          28,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (widget.onClose == null) heading,
            const SizedBox(height: 8),
            Text(
              copy('appearance.deviceOnly'),
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const SizedBox(height: 24),
            LayoutBuilder(
              builder: (context, constraints) {
                final columns = constraints.maxWidth >= 580 ? 3 : 2;
                final width =
                    (constraints.maxWidth - (columns - 1) * 12) / columns;
                return Wrap(
                  key: const ValueKey('appearance/modes-scroll'),
                  spacing: 12,
                  runSpacing: 12,
                  children: [
                    for (final mode in WorkspaceBackdrop.values)
                      SizedBox(
                        width: width,
                        child: _AppearanceChoice(
                          key: ValueKey('appearance/${mode.name}'),
                          mode: mode,
                          label: copy('appearance.mode.${mode.name}'),
                          selected: c.mode == mode,
                          palette: palette,
                          customColor: c.solidColor,
                          onPressed:
                              _choosing ||
                                  c.resetting ||
                                  (mode == WorkspaceBackdrop.desktop &&
                                      !LumenisWindowMaterial.supported)
                              ? null
                              : () => _selectMode(mode),
                        ),
                      ),
                  ],
                );
              },
            ),
            if (!LumenisWindowMaterial.supported) ...[
              const SizedBox(height: 12),
              Text(
                copy('appearance.desktopUnavailable'),
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
            const SizedBox(height: 20),
            Text(
              copy('appearance.presets'),
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            LayoutBuilder(
              builder: (context, constraints) {
                const spacing = 12.0;
                final tileWidth = (constraints.maxWidth - spacing) / 2;
                return Wrap(
                  spacing: spacing,
                  runSpacing: spacing,
                  children: [
                    for (final (id, assetPath, labelKey) in const [
                      (
                        'crimson-sunset',
                        'assets/wallpapers/crimson-sunset.jpg',
                        'appearance.preset.crimson',
                      ),
                      (
                        'cobalt-dusk',
                        'assets/wallpapers/cobalt-dusk.jpg',
                        'appearance.preset.cobalt',
                      ),
                    ])
                      SizedBox(
                        width: tileWidth,
                        child: OutlinedButton(
                          key: ValueKey('appearance/preset/$id'),
                          onPressed: _choosing || c.resetting
                              ? null
                              : () => _choosePresetWallpaper(assetPath),
                          style: OutlinedButton.styleFrom(
                            padding: const EdgeInsets.all(8),
                            minimumSize: const Size(0, 48),
                            tapTargetSize: MaterialTapTargetSize.padded,
                            shape: const LumenisPixelBorder(step: 3),
                          ),
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              ClipPath(
                                clipper: const ShapeBorderClipper(
                                  shape: LumenisPixelBorder(step: 2),
                                ),
                                child: Image.asset(
                                  assetPath,
                                  width: tileWidth - 16,
                                  height: (tileWidth - 16) * .56,
                                  fit: BoxFit.cover,
                                  errorBuilder: (context, error, stackTrace) =>
                                      SizedBox(
                                        width: tileWidth - 16,
                                        height: (tileWidth - 16) * .56,
                                        child: LumenisIcon(
                                          Icons.image_not_supported_outlined,
                                          color: Theme.of(
                                            context,
                                          ).colorScheme.onSurfaceVariant,
                                        ),
                                      ),
                                ),
                              ),
                              const SizedBox(height: 8),
                              Text(
                                copy(labelKey),
                                textAlign: TextAlign.center,
                                style: Theme.of(context).textTheme.labelLarge,
                              ),
                            ],
                          ),
                        ),
                      ),
                  ],
                );
              },
            ),
            if (c.mode == WorkspaceBackdrop.wallpaper) ...[
              const SizedBox(height: 18),
              if (c.wallpaper != null)
                ClipPath(
                  clipper: const ShapeBorderClipper(
                    shape: LumenisPixelBorder(step: 3),
                  ),
                  child: Image.memory(
                    key: const ValueKey('appearance/wallpaper-preview'),
                    c.wallpaper!,
                    height: compact ? 156 : 190,
                    fit: BoxFit.cover,
                    cacheWidth: 900,
                  ),
                ),
              const SizedBox(height: 10),
              Wrap(
                spacing: 10,
                runSpacing: 8,
                children: [
                  FilledButton.icon(
                    key: const ValueKey('appearance/choose-wallpaper'),
                    onPressed: _choosing || c.resetting
                        ? null
                        : _chooseWallpaper,
                    icon: const LumenisIcon(Icons.add_photo_alternate_outlined),
                    label: Text(copy('appearance.chooseWallpaper')),
                  ),
                  if (c.wallpaper != null)
                    TextButton(
                      key: const ValueKey('appearance/remove-wallpaper'),
                      onPressed: c.resetting ? null : c.removeWallpaper,
                      child: Text(copy('appearance.removeWallpaper')),
                    ),
                ],
              ),
              Text(
                copy('appearance.wallpaperLimit'),
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
            if (c.mode == WorkspaceBackdrop.solid) ...[
              Wrap(
                spacing: 14,
                runSpacing: 12,
                children: [
                  for (final color in const [
                    Color(0xFFF2E8E5),
                    Color(0xFFE7E6F0),
                    Color(0xFFE5ECE7),
                    Color(0xFFE6EDF3),
                    Color(0xFF252731),
                    Color(0xFF183B39),
                  ])
                    Semantics(
                      label:
                          '#${color.toARGB32().toRadixString(16).substring(2)}',
                      button: true,
                      child: InkWell(
                        onTap: c.resetting
                            ? null
                            : () {
                                _hex.text = color
                                    .toARGB32()
                                    .toRadixString(16)
                                    .substring(2)
                                    .toUpperCase();
                                c.update(solidColor: color);
                              },
                        customBorder: const LumenisPixelBorder(step: 3),
                        child: Container(
                          width: LumenisSpace.touchTarget,
                          height: LumenisSpace.touchTarget,
                          decoration: ShapeDecoration(
                            color: color,
                            shape: LumenisPixelBorder(
                              step: 3,
                              side: BorderSide(color: scheme.outline),
                            ),
                          ),
                        ),
                      ),
                    ),
                ],
              ),
              const SizedBox(height: 16),
              TextField(
                key: const ValueKey('appearance/hex'),
                controller: _hex,
                enabled: !c.resetting,
                maxLength: 6,
                decoration: InputDecoration(
                  labelText: copy('appearance.hex'),
                  prefixText: '#',
                  suffixIcon: IconButton(
                    tooltip: copy('appearance.applyColor'),
                    icon: const LumenisIcon(Icons.check),
                    onPressed: c.resetting
                        ? null
                        : () {
                            final value = _hex.text.trim();
                            if (!RegExp(r'^[a-fA-F0-9]{6}$').hasMatch(value)) {
                              setState(
                                () => _localError = 'appearance.invalidColor',
                              );
                              return;
                            }
                            setState(() => _localError = null);
                            c.update(
                              solidColor: Color(
                                int.parse('FF$value', radix: 16),
                              ),
                            );
                          },
                  ),
                ),
              ),
            ],
            if (c.isGlass) ...[
              SwitchListTile.adaptive(
                contentPadding: EdgeInsets.zero,
                title: Text(copy('appearance.darkGlass')),
                value: c.darkGlass,
                onChanged: c.resetting
                    ? null
                    : (value) => c.update(darkGlass: value),
              ),
              if (c.mode != WorkspaceBackdrop.desktop) ...[
                Text(copy('appearance.blur')),
                Semantics(
                  label: copy('appearance.blur'),
                  child: Slider(
                    key: const ValueKey('appearance/blur'),
                    value: c.blur,
                    max: 48,
                    divisions: 24,
                    label: '${c.blur.round()} px',
                    semanticFormatterCallback: (value) => '${value.round()} px',
                    onChanged: c.resetting
                        ? null
                        : (value) => c.update(blur: value),
                  ),
                ),
              ],
              Text(copy('appearance.panelOpacity')),
              Semantics(
                label: copy('appearance.panelOpacity'),
                child: Slider(
                  key: const ValueKey('appearance/panelOpacity'),
                  value: c.panelOpacity,
                  min: .65,
                  max: 1,
                  divisions: 7,
                  label: '${(c.panelOpacity * 100).round()}%',
                  semanticFormatterCallback: (value) =>
                      '${(value * 100).round()}%',
                  onChanged: c.resetting
                      ? null
                      : (value) => c.update(panelOpacity: value),
                ),
              ),
            ],
            const Divider(height: 32),
            Row(
              children: [
                Expanded(
                  child: Text(
                    copy('appearance.uiFontSize'),
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                ),
                Text(
                  copy(
                    'appearance.uiFontSizeValue',
                    values: {'size': c.uiFontSize.round()},
                  ),
                  style: Theme.of(context).textTheme.titleSmall,
                ),
              ],
            ),
            Semantics(
              label: copy('appearance.uiFontSize'),
              child: Slider(
                key: const ValueKey('appearance/uiFontSize'),
                value: c.uiFontSize,
                min: Sys05AppearanceController.minUiFontSize,
                max: Sys05AppearanceController.maxUiFontSize,
                divisions: 5,
                label: '${c.uiFontSize.round()} px',
                semanticFormatterCallback: (value) => copy(
                  'appearance.uiFontSizeValue',
                  values: {'size': value.round()},
                ),
                onChanged: c.resetting
                    ? null
                    : (value) => c.update(uiFontSize: value),
              ),
            ),
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 8),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    copy('appearance.uiFontSizePreview'),
                    style: Theme.of(context).textTheme.labelMedium?.copyWith(
                      color: scheme.onSurfaceVariant,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    copy('appearance.uiFontSizeSample'),
                    style: Theme.of(
                      context,
                    ).textTheme.bodyLarge?.copyWith(fontSize: c.uiFontSize),
                  ),
                ],
              ),
            ),
            const Divider(height: 28),
            SwitchListTile.adaptive(
              key: const ValueKey('appearance/compact'),
              contentPadding: EdgeInsets.zero,
              title: Text(copy('appearance.compact')),
              value: c.compact,
              onChanged: c.resetting
                  ? null
                  : (value) => c.update(compact: value),
            ),
            const Divider(height: 1),
            SwitchListTile.adaptive(
              key: const ValueKey('appearance/botanicalRoles'),
              contentPadding: EdgeInsets.zero,
              title: Text(copy('appearance.botanicalRoles')),
              value: c.botanicalRoles,
              onChanged: c.resetting
                  ? null
                  : (value) => c.update(botanicalRoles: value),
            ),
            if (c.botanicalRoles)
              Padding(
                padding: const EdgeInsets.fromLTRB(0, 4, 0, 16),
                child: Wrap(
                  spacing: 12,
                  runSpacing: 12,
                  children: [
                    for (final (name, plant) in const [
                      ('Pim', LumenisPlant.orchid),
                      ('Bram', LumenisPlant.spiderLily),
                      ('Ness', LumenisPlant.palm),
                      ('Jas', LumenisPlant.grape),
                      ('Aris', LumenisPlant.jasmine),
                    ])
                      Semantics(
                        label: name,
                        image: true,
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            LumenisBotanical(plant: plant, size: 56),
                            const SizedBox(height: 4),
                            Text(
                              name,
                              style: Theme.of(context).textTheme.labelMedium,
                            ),
                          ],
                        ),
                      ),
                  ],
                ),
              ),
            const Divider(height: 1),
            SwitchListTile.adaptive(
              key: const ValueKey('appearance/reduceMotion'),
              contentPadding: EdgeInsets.zero,
              title: Text(copy('appearance.reduceMotion')),
              value: c.reducedMotion,
              onChanged: c.resetting
                  ? null
                  : (value) => c.update(reducedMotion: value),
            ),
            const Divider(height: 1),
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(SysSystemCopy.text(context, 'sys.waiting.preference')),
                  Wrap(
                    spacing: 8,
                    children: WaitingTone.values
                        .map(
                          (tone) => ChoiceChip(
                            key: ValueKey(
                              'appearance/waitingTone/${tone.name}',
                            ),
                            label: Text(
                              SysSystemCopy.text(
                                context,
                                'sys.waiting.${tone.name}',
                              ),
                            ),
                            selected: c.waitingTone == tone,
                            onSelected: c.resetting
                                ? null
                                : (_) => c.update(waitingTone: tone),
                          ),
                        )
                        .toList(),
                  ),
                ],
              ),
            ),
            if (error != null) ...[
              const SizedBox(height: 12),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Semantics(
                    liveRegion: true,
                    child: Text(
                      copy(error),
                      style: TextStyle(color: scheme.error),
                    ),
                  ),
                  if (c.errorKey == 'appearance.restoreFailed' ||
                      c.errorKey == 'appearance.resetLocalFailed')
                    TextButton.icon(
                      key: const ValueKey('appearance/reset-local'),
                      onPressed: c.resetting || _choosing
                          ? null
                          : () async {
                              await c.resetLocalAppearance();
                            },
                      icon: c.resetting
                          ? const SizedBox.square(
                              dimension: 18,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const LumenisIcon(Icons.restart_alt_rounded),
                      label: Text(copy('appearance.resetLocal')),
                    ),
                ],
              ),
            ],
            if (c.statusKey != null) ...[
              const SizedBox(height: 8),
              Semantics(
                liveRegion: true,
                child: Text(
                  copy(c.statusKey!),
                  style: TextStyle(color: scheme.primary),
                ),
              ),
            ],
            const SizedBox(height: 12),
            Text(
              copy(
                c.saving
                    ? 'appearance.saving'
                    : error == null
                    ? 'appearance.remembered'
                    : 'appearance.previewOnly',
              ),
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        ),
      );
      if (widget.onClose == null) return content;
      return Column(
        children: [
          Padding(
            padding: EdgeInsets.fromLTRB(horizontalPadding, 12, 12, 8),
            child: heading,
          ),
          const Divider(height: 1),
          Expanded(child: content),
        ],
      );
    },
  );
}

class _AppearanceChoice extends StatelessWidget {
  const _AppearanceChoice({
    super.key,
    required this.mode,
    required this.label,
    required this.selected,
    required this.palette,
    required this.customColor,
    required this.onPressed,
  });

  final WorkspaceBackdrop mode;
  final String label;
  final bool selected;
  final LumenisPalette palette;
  final Color customColor;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    final background = switch (mode) {
      WorkspaceBackdrop.white => Colors.white,
      WorkspaceBackdrop.black => Colors.black,
      WorkspaceBackdrop.solid => customColor,
      _ =>
        palette.brightness == Brightness.dark
            ? LumenisTheme.darkPalette.canvas
            : LumenisTheme.canvas,
    };
    final dark = background.computeLuminance() < .179;
    final line = (dark ? Colors.white : Colors.black).withValues(alpha: .24);
    final sheet = dark
        ? LumenisTheme.darkPalette.surface
        : LumenisTheme.surface;
    return Semantics(
      selected: selected,
      child: OutlinedButton(
        onPressed: onPressed,
        style: OutlinedButton.styleFrom(
          padding: const EdgeInsets.all(10),
          side: BorderSide(
            color: selected ? palette.accentStrong : palette.line,
            width: selected ? 2 : 1,
          ),
          backgroundColor: selected ? palette.surfaceRaised : palette.surface,
          shape: const LumenisPixelBorder(step: 3),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            ExcludeSemantics(
              child: SizedBox(
                height: 72,
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    color: background,
                    border: Border.all(color: line),
                  ),
                  child: Stack(
                    children: [
                      if (mode == WorkspaceBackdrop.wallpaper)
                        Positioned.fill(
                          child: Image.asset(
                            'assets/wallpapers/cobalt-dusk.jpg',
                            fit: BoxFit.cover,
                          ),
                        ),
                      Positioned(
                        left: 8,
                        top: 8,
                        bottom: 8,
                        width: 18,
                        child: ColoredBox(color: sheet.withValues(alpha: .8)),
                      ),
                      Positioned(
                        left: 34,
                        right: 8,
                        top: 8,
                        height: 8,
                        child: ColoredBox(color: line),
                      ),
                      Positioned(
                        left: 34,
                        right: 8,
                        top: 24,
                        bottom: 8,
                        child: ColoredBox(
                          color: sheet.withValues(alpha: .8),
                          child: Theme(
                            data: LumenisTheme.forPalette(
                              dark
                                  ? LumenisTheme.darkPalette
                                  : LumenisTheme.lightPalette,
                            ),
                            child: const Center(
                              child: LumenisBotanical(
                                size: 28,
                                monochrome: true,
                              ),
                            ),
                          ),
                        ),
                      ),
                      if (mode == WorkspaceBackdrop.desktop)
                        Center(
                          child: LumenisIcon(
                            Icons.desktop_windows_outlined,
                            size: 22,
                            color: dark ? Colors.white : Colors.black,
                          ),
                        ),
                    ],
                  ),
                ),
              ),
            ),
            const SizedBox(height: 10),
            Row(
              children: [
                Expanded(
                  child: Text(
                    label,
                    style: Theme.of(context).textTheme.labelMedium,
                  ),
                ),
                if (selected)
                  LumenisIcon(
                    Icons.check,
                    size: 16,
                    color: palette.accentStrong,
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
