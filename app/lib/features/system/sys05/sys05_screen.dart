import 'package:flutter/material.dart';

import '../../../core/lumenis_core_client.dart';
import '../../../core/lumenis_theme.dart';
import '../sys02/sys_system_foundation.dart';
import 'sys05_repository.dart';
import 'sys05_view_model.dart';
import 'sys05_appearance_controller.dart';
import 'sys05_appearance_editor.dart';

class Sys05Screen extends StatefulWidget {
  const Sys05Screen({required this.client, this.repository, super.key});

  final LumenisCoreClient client;
  final Sys05Repository? repository;

  @override
  State<Sys05Screen> createState() => _Sys05ScreenState();
}

class _Sys05ScreenState extends State<Sys05Screen> {
  late final Sys05ViewModel _viewModel;

  @override
  void initState() {
    super.initState();
    _viewModel = Sys05ViewModel(
      repository:
          widget.repository ?? CoreSys05Repository(client: widget.client),
    )..refresh();
  }

  @override
  void dispose() {
    _viewModel.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final appearance = Sys05AppearanceScope.maybeOf(context);
    if (appearance != null) {
      return Align(
        alignment: Alignment.topCenter,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 760),
          child: SafeArea(child: Sys05AppearanceEditor(controller: appearance)),
        ),
      );
    }
    return ColoredBox(
      color: LumenisTheme.of(context).canvas,
      child: SafeArea(
        child: AnimatedBuilder(
          animation: _viewModel,
          builder: (context, _) => switch (_viewModel.phase) {
            SysLoadPhase.loading => const SysLoadingView(
              titleKey: 'sys.common.loading',
            ),
            SysLoadPhase.failed => SysFailureView(
              kind: _viewModel.failureKind!,
              onRetry: _viewModel.refresh,
            ),
            SysLoadPhase.ready => _SettingsContent(
              viewModel: _viewModel,
              onRefresh: _viewModel.refresh,
            ),
          },
        ),
      ),
    );
  }
}

class _SettingsContent extends StatelessWidget {
  const _SettingsContent({required this.viewModel, required this.onRefresh});

  final Sys05ViewModel viewModel;
  final VoidCallback onRefresh;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final width = constraints.maxWidth;
        final mobile = width < 768;
        final horizontalPadding = width < 480
            ? 18.0
            : width < 900
            ? 26.0
            : 38.0;
        String copy(String key) => SysSystemCopy.text(context, key);
        final header = SysPageHeader(
          eyebrow: copy('sys05.eyebrow'),
          title: copy('sys05.title'),
          subtitle: copy('sys05.subtitle'),
          onRefresh: onRefresh,
        );
        final form = SysPanel(
          title: copy('sys05.appearance.title'),
          child: _PreferenceForm(viewModel: viewModel),
        );
        final preview = SysPanel(
          title: copy('sys05.preview.title'),
          detail: copy('sys05.preview.detail'),
          child: _PreferencePreview(viewModel: viewModel),
        );
        final content = mobile
            ? Column(
                key: const ValueKey('sys05/layout-mobile'),
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [form, const SizedBox(height: 14), preview],
              )
            : Row(
                key: const ValueKey('sys05/layout-desktop'),
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(flex: 7, child: form),
                  const SizedBox(width: 18),
                  Expanded(flex: 5, child: preview),
                ],
              );
        return Align(
          alignment: Alignment.topCenter,
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1360),
            child: SingleChildScrollView(
              padding: EdgeInsets.fromLTRB(
                horizontalPadding,
                26,
                horizontalPadding,
                48,
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [header, const SizedBox(height: 24), content],
              ),
            ),
          ),
        );
      },
    );
  }
}

class _PreferenceForm extends StatelessWidget {
  const _PreferenceForm({required this.viewModel});

  final Sys05ViewModel viewModel;

  @override
  Widget build(BuildContext context) {
    String copy(String key) => SysSystemCopy.text(context, key);
    final preferences = viewModel.preferences;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _PreferenceSelect(
          label: copy('sys05.field.theme'),
          value: preferences.theme,
          options: {
            'system': copy('sys05.system'),
            'light': copy('sys05.light'),
            'dark': copy('sys05.dark'),
          },
          onChanged: (value) => viewModel.update(theme: value),
        ),
        const SizedBox(height: 14),
        _PreferenceSelect(
          label: copy('sys05.field.optical'),
          value: preferences.optical,
          options: {
            'low': copy('sys05.low'),
            'balanced': copy('sys05.balanced'),
            'high': copy('sys05.high'),
          },
          onChanged: (value) => viewModel.update(optical: value),
        ),
        const SizedBox(height: 14),
        _PreferenceSelect(
          label: copy('sys05.field.density'),
          value: preferences.density,
          options: {
            'comfortable': copy('sys05.comfortable'),
            'compact': copy('sys05.compact'),
          },
          onChanged: (value) => viewModel.update(density: value),
        ),
        const SizedBox(height: 14),
        _PreferenceSelect(
          label: copy('sys05.field.motion'),
          value: preferences.reducedMotion,
          options: {
            'system': copy('sys05.system'),
            'on': copy('sys05.on'),
            'off': copy('sys05.off'),
          },
          onChanged: (value) => viewModel.update(reducedMotion: value),
        ),
        const SizedBox(height: 14),
        _PreferenceSelect(
          label: copy('sys05.field.locale'),
          value: preferences.locale,
          options: {
            'zh-CN': copy('sys05.zh'),
            'en': copy('sys05.en'),
            'ko': copy('sys05.ko'),
          },
          onChanged: (value) => viewModel.update(locale: value),
        ),
        const SizedBox(height: 22),
        Wrap(
          spacing: 10,
          runSpacing: 10,
          children: [
            FilledButton.tonal(
              onPressed: viewModel.hasUnsavedChanges
                  ? viewModel.saveLocal
                  : null,
              child: Text(copy('sys05.save')),
            ),
            OutlinedButton(
              onPressed: viewModel.restoreDefaults,
              child: Text(copy('sys05.reset')),
            ),
          ],
        ),
        const SizedBox(height: 14),
        Text(
          copy('sys05.localOnly'),
          style: TextStyle(color: LumenisTheme.of(context).quiet, height: 1.45),
        ),
        if (viewModel.savedInSession) ...[
          const SizedBox(height: 12),
          Text(
            copy('sys05.saved'),
            style: TextStyle(
              color: LumenisTheme.of(context).positive,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ],
    );
  }
}

class _PreferenceSelect extends StatelessWidget {
  const _PreferenceSelect({
    required this.label,
    required this.value,
    required this.options,
    required this.onChanged,
  });

  final String label;
  final String value;
  final Map<String, String> options;
  final ValueChanged<String?> onChanged;

  @override
  Widget build(BuildContext context) {
    return DropdownButtonFormField<String>(
      initialValue: options.containsKey(value) ? value : options.keys.first,
      onChanged: onChanged,
      decoration: InputDecoration(
        labelText: label,
        filled: true,
        fillColor: LumenisTheme.of(context).canvas,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: BorderSide(color: LumenisTheme.of(context).line),
        ),
      ),
      items: [
        for (final entry in options.entries)
          DropdownMenuItem(value: entry.key, child: Text(entry.value)),
      ],
    );
  }
}

class _PreferencePreview extends StatelessWidget {
  const _PreferencePreview({required this.viewModel});

  final Sys05ViewModel viewModel;

  @override
  Widget build(BuildContext context) {
    String copy(String key) => SysSystemCopy.text(context, key);
    final preferences = viewModel.preferences;
    final dark = preferences.theme != 'light';
    final sampleSurface = dark
        ? LumenisTheme.of(context).surfaceRaised
        : const Color(0xFFE9ECEB);
    final sampleText = dark
        ? LumenisTheme.of(context).foreground
        : const Color(0xFF18201E);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Container(
          padding: const EdgeInsets.all(18),
          decoration: BoxDecoration(
            color: sampleSurface,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: dark
                  ? LumenisTheme.of(context).line
                  : const Color(0xFFC8D0CC),
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                copy('sys05.preview.title'),
                style: TextStyle(
                  color: sampleText,
                  fontSize: 18,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                copy('sys05.preview.detail'),
                style: TextStyle(
                  color: dark
                      ? LumenisTheme.of(context).muted
                      : const Color(0xFF4C5B55),
                  height: 1.45,
                ),
              ),
              const SizedBox(height: 18),
              Row(
                children: [
                  Icon(
                    Icons.verified_outlined,
                    color: dark
                        ? LumenisTheme.of(context).positive
                        : const Color(0xFF2D745B),
                    size: 18,
                  ),
                  const SizedBox(width: 8),
                  Text(
                    copy('sys.common.ready'),
                    style: TextStyle(
                      color: dark
                          ? LumenisTheme.of(context).positive
                          : const Color(0xFF2D745B),
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: 14),
        Text(
          '${copy('sys05.field.theme')}: ${preferences.theme}',
          style: TextStyle(color: LumenisTheme.of(context).muted),
        ),
        const SizedBox(height: 6),
        Text(
          '${copy('sys05.field.density')}: ${preferences.density}',
          style: TextStyle(color: LumenisTheme.of(context).muted),
        ),
        const SizedBox(height: 6),
        Text(
          '${copy('sys05.field.motion')}: ${preferences.reducedMotion}',
          style: TextStyle(color: LumenisTheme.of(context).muted),
        ),
      ],
    );
  }
}
