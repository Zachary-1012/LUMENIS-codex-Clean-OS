import 'package:file_selector/file_selector.dart';
import 'package:flutter/material.dart';

import '../../../l10n/lumenis_localizations.dart';
import '../../../platform/lumenis_window_material.dart';
import 'sys05_appearance_controller.dart';

class Sys05AppearanceButton extends StatelessWidget {
  const Sys05AppearanceButton({super.key});
  @override
  Widget build(BuildContext context) {
    final controller = Sys05AppearanceScope.maybeOf(context);
    if (controller == null) return const SizedBox.shrink();
    return IconButton(
      key: const ValueKey('appearance/open'),
      tooltip: context.lumenisL10n.text('appearance.title'),
      icon: const Icon(Icons.palette_outlined, size: 20),
      onPressed: () {
        FocusManager.instance.primaryFocus?.unfocus();
        showModalBottomSheet<void>(
          context: context,
          isScrollControlled: true,
          showDragHandle: true,
          constraints: const BoxConstraints(maxWidth: 620),
          builder: (context) => SafeArea(
            child: Padding(
              padding: EdgeInsets.only(
                bottom: MediaQuery.viewInsetsOf(context).bottom,
              ),
              child: Sys05AppearanceEditor(
                controller: controller,
                onClose: () => Navigator.of(context).pop(),
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
    super.key,
  });
  final Sys05AppearanceController controller;
  final VoidCallback? onClose;
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
      String copy(String key, {Map<String, Object?> values = const {}}) =>
          context.lumenisL10n.text(key, values: values);
      final error = _localError ?? c.errorKey;
      return SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(24, 6, 24, 28),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
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
                    tooltip: MaterialLocalizations.of(
                      context,
                    ).closeButtonTooltip,
                    onPressed: widget.onClose,
                    icon: const Icon(Icons.close),
                  ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              copy('appearance.deviceOnly'),
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const SizedBox(height: 24),
            Wrap(
              spacing: 10,
              runSpacing: 12,
              children: [
                for (final mode in WorkspaceBackdrop.values)
                  Semantics(
                    selected: c.mode == mode,
                    child: ChoiceChip(
                      key: ValueKey('appearance/${mode.name}'),
                      label: Text(copy('appearance.mode.${mode.name}')),
                      selected: c.mode == mode,
                      avatar: Icon(switch (mode) {
                        WorkspaceBackdrop.frosted => Icons.blur_on,
                        WorkspaceBackdrop.wallpaper => Icons.image_outlined,
                        WorkspaceBackdrop.desktop =>
                          Icons.desktop_windows_outlined,
                        WorkspaceBackdrop.white => Icons.light_mode_outlined,
                        WorkspaceBackdrop.black => Icons.dark_mode_outlined,
                        WorkspaceBackdrop.solid => Icons.color_lens_outlined,
                      }, size: 18),
                      onSelected:
                          mode == WorkspaceBackdrop.desktop &&
                              !LumenisWindowMaterial.supported
                          ? null
                          : (_) => c.update(mode: mode),
                    ),
                  ),
              ],
            ),
            if (!LumenisWindowMaterial.supported) ...[
              const SizedBox(height: 12),
              Text(
                copy('appearance.desktopUnavailable'),
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
            const SizedBox(height: 20),
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
                onChanged: (value) => c.update(uiFontSize: value),
              ),
            ),
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: scheme.surfaceContainerHighest.withValues(alpha: .45),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: scheme.outlineVariant),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    copy('appearance.uiFontSizePreview'),
                    style: Theme.of(context).textTheme.labelMedium?.copyWith(
                      color: scheme.onSurfaceVariant,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    copy('appearance.uiFontSizeSample'),
                    style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                      fontSize: Sys05AppearanceController.defaultUiFontSize,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),
            if (c.mode == WorkspaceBackdrop.wallpaper) ...[
              if (c.wallpaper != null)
                ClipRRect(
                  borderRadius: BorderRadius.circular(16),
                  child: Image.memory(
                    c.wallpaper!,
                    height: 140,
                    fit: BoxFit.cover,
                    cacheWidth: 900,
                  ),
                ),
              const SizedBox(height: 10),
              Wrap(
                spacing: 8,
                children: [
                  FilledButton.icon(
                    onPressed: _choosing ? null : _chooseWallpaper,
                    icon: const Icon(Icons.add_photo_alternate_outlined),
                    label: Text(copy('appearance.chooseWallpaper')),
                  ),
                  if (c.wallpaper != null)
                    TextButton(
                      onPressed: c.removeWallpaper,
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
                        onTap: () {
                          _hex.text = color
                              .toARGB32()
                              .toRadixString(16)
                              .substring(2)
                              .toUpperCase();
                          c.update(solidColor: color);
                        },
                        borderRadius: BorderRadius.circular(24),
                        child: Container(
                          width: 46,
                          height: 46,
                          decoration: BoxDecoration(
                            color: color,
                            shape: BoxShape.circle,
                            border: Border.all(color: scheme.outline),
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
                maxLength: 6,
                decoration: InputDecoration(
                  labelText: copy('appearance.hex'),
                  prefixText: '#',
                  suffixIcon: IconButton(
                    tooltip: copy('appearance.applyColor'),
                    icon: const Icon(Icons.check),
                    onPressed: () {
                      final value = _hex.text.trim();
                      if (!RegExp(r'^[a-fA-F0-9]{6}$').hasMatch(value)) {
                        setState(() => _localError = 'appearance.invalidColor');
                        return;
                      }
                      setState(() => _localError = null);
                      c.update(
                        solidColor: Color(int.parse('FF$value', radix: 16)),
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
                onChanged: (value) => c.update(darkGlass: value),
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
                    onChanged: (value) => c.update(blur: value),
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
                  onChanged: (value) => c.update(panelOpacity: value),
                ),
              ),
            ],
            SwitchListTile.adaptive(
              contentPadding: EdgeInsets.zero,
              title: Text(copy('appearance.compact')),
              value: c.compact,
              onChanged: (value) => c.update(compact: value),
            ),
            SwitchListTile.adaptive(
              contentPadding: EdgeInsets.zero,
              title: Text(copy('appearance.reduceMotion')),
              value: c.reducedMotion,
              onChanged: (value) => c.update(reducedMotion: value),
            ),
            if (error != null) ...[
              const SizedBox(height: 12),
              Semantics(
                liveRegion: true,
                child: Text(copy(error), style: TextStyle(color: scheme.error)),
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
    },
  );
}
