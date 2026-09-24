import 'package:flutter/material.dart';

import '../../../core/lumenis_core_client.dart';
import '../../../core/lumenis_theme.dart';
import '../../../l10n/lumenis_localizations.dart';
import 'cth06_repository.dart';
import 'cth06_view_model.dart';

class Cth06Screen extends StatefulWidget {
  const Cth06Screen({required this.client, this.repository, super.key});

  final LumenisCoreClient client;
  final Cth06Repository? repository;

  @override
  State<Cth06Screen> createState() => _Cth06ScreenState();
}

class _Cth06ScreenState extends State<Cth06Screen> {
  late Cth06ViewModel _viewModel = _createViewModel()..refresh();

  Cth06ViewModel _createViewModel() => Cth06ViewModel(
    repository: widget.repository ?? CoreCth06Repository(client: widget.client),
  );

  @override
  void didUpdateWidget(covariant Cth06Screen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.client != widget.client ||
        oldWidget.repository != widget.repository) {
      _viewModel.dispose();
      _viewModel = _createViewModel()..refresh();
    }
  }

  @override
  void dispose() {
    _viewModel.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => ColoredBox(
    color: LumenisTheme.of(context).canvas,
    child: SafeArea(
      child: AnimatedBuilder(
        animation: _viewModel,
        builder: (context, _) => switch (_viewModel.phase) {
          Cth06LoadPhase.loading => const _Cth06Loading(),
          Cth06LoadPhase.unavailable => _Cth06Unavailable(
            kind: _viewModel.failureKind ?? Cth06FailureKind.server,
            onRetry: _viewModel.refresh,
          ),
          Cth06LoadPhase.ready => _Cth06Workspace(
            data: _viewModel.data!,
            selectedCategory: _viewModel.selectedCategory,
            visibleItems: _viewModel.visibleItems(),
            selectedItem: _viewModel.selectedItem,
            onCategoryChanged: _viewModel.chooseCategory,
            onSelectItem: _viewModel.selectItem,
            onRetry: _viewModel.refresh,
          ),
        },
      ),
    ),
  );
}

class _Cth06Loading extends StatelessWidget {
  const _Cth06Loading();

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    return Semantics(
      liveRegion: true,
      label: copy.text('state.loading_d'),
      child: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const CircularProgressIndicator(),
            const SizedBox(height: 16),
            Text(copy.text('screen.CTH-06')),
          ],
        ),
      ),
    );
  }
}

class _Cth06Unavailable extends StatelessWidget {
  const _Cth06Unavailable({required this.kind, required this.onRetry});

  final Cth06FailureKind kind;
  final VoidCallback onRetry;

  String _detail(LumenisLocalizations copy) => switch (kind) {
    Cth06FailureKind.contextUnavailable => copy.text(
      'cth01.context_unavailable',
    ),
    Cth06FailureKind.pageNotBound || Cth06FailureKind.focusNotBound =>
      copy.text('context.screen_binding_unavailable'),
    Cth06FailureKind.authentication => copy.text('cth01.login_required'),
    Cth06FailureKind.permissionDenied => copy.text('cth01.access_unavailable'),
    Cth06FailureKind.offline => copy.text('cth01.connection_unavailable'),
    Cth06FailureKind.server => copy.text('cth01.generic_unavailable'),
  };

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    final binding =
        kind == Cth06FailureKind.pageNotBound ||
        kind == Cth06FailureKind.focusNotBound;
    return LayoutBuilder(
      builder: (context, constraints) => Align(
        alignment: Alignment.topCenter,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 720),
          child: Padding(
            padding: EdgeInsets.all(constraints.maxWidth < 480 ? 22 : 32),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  binding
                      ? copy.text('cth01.subject_unavailable')
                      : copy.text('cth01.operation_unavailable'),
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
                const SizedBox(height: 12),
                Text(
                  _detail(copy),
                  style: TextStyle(
                    color: LumenisTheme.of(context).muted,
                    height: 1.55,
                  ),
                ),
                const SizedBox(height: 22),
                FilledButton.tonalIcon(
                  onPressed: onRetry,
                  icon: const Icon(Icons.refresh_rounded),
                  label: Text(copy.text('common.refresh')),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _Cth06Workspace extends StatelessWidget {
  const _Cth06Workspace({
    required this.data,
    required this.selectedCategory,
    required this.visibleItems,
    required this.selectedItem,
    required this.onCategoryChanged,
    required this.onSelectItem,
    required this.onRetry,
  });

  final Cth06ScreenData data;
  final Cth06Category? selectedCategory;
  final List<Cth06Feedback> visibleItems;
  final Cth06Feedback? selectedItem;
  final ValueChanged<Cth06Category?> onCategoryChanged;
  final ValueChanged<int> onSelectItem;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, constraints) {
      final wide = constraints.maxWidth >= 1120;
      final padding = constraints.maxWidth < 480
          ? 18.0
          : constraints.maxWidth < 900
          ? 28.0
          : 40.0;
      final queue = _TriageQueue(
        state: data.itemsState,
        items: visibleItems,
        selectedCategory: selectedCategory,
        onCategoryChanged: onCategoryChanged,
        onSelectItem: onSelectItem,
      );
      final reader = _ReadingPane(item: selectedItem);
      return Align(
        alignment: Alignment.topCenter,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1680),
          child: SingleChildScrollView(
            padding: EdgeInsets.fromLTRB(padding, 28, padding, 48),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _Header(data: data, onRetry: onRetry),
                const SizedBox(height: 24),
                if (wide)
                  Row(
                    key: const ValueKey('cth06/desktop-layout'),
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(flex: 7, child: queue),
                      const SizedBox(width: 24),
                      Expanded(flex: 4, child: reader),
                    ],
                  )
                else
                  Column(
                    key: const ValueKey('cth06/mobile-layout'),
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [queue, const SizedBox(height: 18), reader],
                  ),
              ],
            ),
          ),
        ),
      );
    },
  );
}

class _Header extends StatelessWidget {
  const _Header({required this.data, required this.onRetry});

  final Cth06ScreenData data;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    final contextLabel = _contextLabel(context, data.context);
    return Wrap(
      alignment: WrapAlignment.spaceBetween,
      crossAxisAlignment: WrapCrossAlignment.center,
      runSpacing: 15,
      spacing: 20,
      children: [
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              copy.text('screen.CTH-06'),
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 9),
            Semantics(
              label: contextLabel,
              child: Text(
                contextLabel,
                style: TextStyle(
                  color: LumenisTheme.of(context).foreground,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
            const SizedBox(height: 7),
            Text(
              data.generatedAt.isEmpty
                  ? copy.text('cth01.activity.detail')
                  : '${copy.text('cth01.activity.detail')} · ${data.generatedAt}',
              style: TextStyle(color: LumenisTheme.of(context).muted),
            ),
          ],
        ),
        FilledButton.tonalIcon(
          onPressed: onRetry,
          icon: const Icon(Icons.refresh_rounded),
          label: Text(copy.text('common.refresh')),
        ),
      ],
    );
  }
}

class _TriageQueue extends StatelessWidget {
  const _TriageQueue({
    required this.state,
    required this.items,
    required this.selectedCategory,
    required this.onCategoryChanged,
    required this.onSelectItem,
  });

  final Cth06DataState state;
  final List<Cth06Feedback> items;
  final Cth06Category? selectedCategory;
  final ValueChanged<Cth06Category?> onCategoryChanged;
  final ValueChanged<int> onSelectItem;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    return _Panel(
      key: const ValueKey('cth06/triage-queue'),
      title: copy.text('common.filter'),
      detail: copy.text('cth01.metrics.detail'),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              FilterChip(
                label: Text(copy.text('common.all')),
                selected: selectedCategory == null,
                onSelected: (_) => onCategoryChanged(null),
              ),
              for (final category in Cth06Category.values)
                FilterChip(
                  label: Text(category.label),
                  selected: selectedCategory == category,
                  onSelected: (_) => onCategoryChanged(
                    selectedCategory == category ? null : category,
                  ),
                ),
            ],
          ),
          const SizedBox(height: 16),
          if (items.isEmpty)
            _InlineState(text: _emptyCopy(copy, state))
          else
            Column(
              children: [
                for (var index = 0; index < items.length; index++)
                  _FeedbackRow(
                    item: items[index],
                    onTap: () => onSelectItem(index),
                  ),
              ],
            ),
        ],
      ),
    );
  }

  String _emptyCopy(LumenisLocalizations copy, Cth06DataState state) {
    return switch (state) {
      Cth06DataState.empty => copy.text('state.empty_true'),
      Cth06DataState.notCollected => copy.text('state.empty_notcollected'),
      Cth06DataState.offline => copy.text('state.offline'),
      Cth06DataState.stale => copy.text('state.stale'),
      Cth06DataState.blocked => copy.text('state.blocked'),
      Cth06DataState.partial => copy.text('state.partial'),
      Cth06DataState.error => copy.text('state.error'),
      _ => copy.text('common.empty'),
    };
  }
}

class _FeedbackRow extends StatelessWidget {
  const _FeedbackRow({required this.item, required this.onTap});

  final Cth06Feedback item;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Semantics(
    button: true,
    label: '${item.category.label}, ${item.summary}, ${item.date}',
    child: InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Container(
        width: double.infinity,
        margin: const EdgeInsets.only(bottom: 10),
        padding: const EdgeInsets.all(15),
        decoration: BoxDecoration(
          color: LumenisTheme.of(context).surfaceRaised,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: LumenisTheme.of(context).line),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Padding(
              padding: EdgeInsets.only(top: 3),
              child: Icon(
                Icons.flag_outlined,
                size: 17,
                color: LumenisTheme.of(context).danger,
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    item.summary,
                    style: TextStyle(
                      color: LumenisTheme.of(context).foreground,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 7),
                  Wrap(
                    spacing: 10,
                    runSpacing: 5,
                    children: [
                      Text(
                        item.category.label,
                        style: TextStyle(
                          color: LumenisTheme.of(context).cth,
                          fontSize: 12,
                        ),
                      ),
                      if (item.channel.isNotEmpty)
                        Text(
                          item.channel,
                          style: TextStyle(
                            color: LumenisTheme.of(context).muted,
                            fontSize: 12,
                          ),
                        ),
                      if (item.date.isNotEmpty)
                        Text(
                          item.date,
                          style: TextStyle(
                            color: LumenisTheme.of(context).quiet,
                            fontSize: 12,
                          ),
                        ),
                    ],
                  ),
                ],
              ),
            ),
            Icon(
              Icons.chevron_right_rounded,
              color: LumenisTheme.of(context).quiet,
            ),
          ],
        ),
      ),
    ),
  );
}

class _ReadingPane extends StatelessWidget {
  const _ReadingPane({required this.item});

  final Cth06Feedback? item;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    return _Panel(
      key: const ValueKey('cth06/reading-pane'),
      title: copy.text('common.detail'),
      detail: copy.text('cth01.activity.detail'),
      child: item == null
          ? _InlineState(text: copy.text('state.empty_filter'))
          : Semantics(
              container: true,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    item!.category.label,
                    style: TextStyle(
                      color: LumenisTheme.of(context).cth,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 12),
                  Text(
                    item!.summary,
                    style: TextStyle(
                      color: LumenisTheme.of(context).foreground,
                      fontSize: 18,
                      height: 1.4,
                    ),
                  ),
                  const SizedBox(height: 16),
                  Wrap(
                    spacing: 14,
                    runSpacing: 7,
                    children: [
                      if (item!.channel.isNotEmpty)
                        _Detail(
                          label: copy.text('common.source'),
                          value: item!.channel,
                        ),
                      if (item!.date.isNotEmpty)
                        _Detail(
                          label: copy.text('common.time'),
                          value: item!.date,
                        ),
                      if (item!.sentiment.isNotEmpty)
                        _Detail(
                          label: copy.text('common.status'),
                          value: item!.sentiment,
                        ),
                      if (item!.risk.isNotEmpty)
                        _Detail(
                          label: copy.text('cth01.field.severity'),
                          value: item!.risk,
                        ),
                    ],
                  ),
                  const SizedBox(height: 18),
                  Text(
                    copy.text('cth01.source.unavailable'),
                    style: TextStyle(
                      color: LumenisTheme.of(context).muted,
                      height: 1.5,
                    ),
                  ),
                ],
              ),
            ),
    );
  }
}

class _Detail extends StatelessWidget {
  const _Detail({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(
        label,
        style: TextStyle(color: LumenisTheme.of(context).quiet, fontSize: 11),
      ),
      const SizedBox(height: 3),
      Text(value, style: TextStyle(color: LumenisTheme.of(context).muted)),
    ],
  );
}

class _Panel extends StatelessWidget {
  const _Panel({
    super.key,
    required this.title,
    required this.detail,
    required this.child,
  });

  final String title;
  final String detail;
  final Widget child;

  @override
  Widget build(BuildContext context) => Container(
    decoration: BoxDecoration(
      color: LumenisTheme.of(context).surface,
      borderRadius: BorderRadius.circular(18),
      border: Border.all(color: LumenisTheme.of(context).line),
    ),
    padding: const EdgeInsets.all(20),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: Theme.of(context).textTheme.titleLarge?.copyWith(fontSize: 20),
        ),
        const SizedBox(height: 6),
        Text(
          detail,
          style: TextStyle(color: LumenisTheme.of(context).muted, height: 1.45),
        ),
        const SizedBox(height: 16),
        child,
      ],
    ),
  );
}

class _InlineState extends StatelessWidget {
  const _InlineState({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) => Semantics(
    liveRegion: true,
    label: text,
    child: Padding(
      padding: const EdgeInsets.symmetric(vertical: 18),
      child: Text(
        text,
        style: TextStyle(color: LumenisTheme.of(context).muted, height: 1.5),
      ),
    ),
  );
}

String _contextLabel(BuildContext context, Cth06Context value) {
  final copy = context.lumenisL10n;
  if (value.isGlobal) return copy.text('context.mode.global_all');
  final locale = Localizations.localeOf(context);
  return value.displayName?[locale.toLanguageTag()] ??
      value.displayName?[locale.languageCode] ??
      value.displayName?['zh-CN'] ??
      copy.text('context.mode.focus');
}
