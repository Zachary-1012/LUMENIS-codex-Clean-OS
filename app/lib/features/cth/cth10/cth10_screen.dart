import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../../core/lumenis_core_client.dart';
import '../../../l10n/lumenis_localizations.dart';
import '../../../core/lumenis_theme.dart';
import 'cth10_repository.dart';
import 'cth10_view_model.dart';

class Cth10Screen extends StatefulWidget {
  const Cth10Screen({required this.client, this.repository, super.key});

  final LumenisCoreClient client;
  final Cth10Repository? repository;

  @override
  State<Cth10Screen> createState() => _Cth10ScreenState();
}

class _Cth10ScreenState extends State<Cth10Screen> {
  late Cth10ViewModel _viewModel = _createViewModel()..load();

  Cth10ViewModel _createViewModel() => Cth10ViewModel(
    repository: widget.repository ?? CoreCth10Repository(client: widget.client),
  );

  @override
  void didUpdateWidget(covariant Cth10Screen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.client != widget.client ||
        oldWidget.repository != widget.repository) {
      _viewModel.dispose();
      _viewModel = _createViewModel()..load();
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
        builder: (context, _) {
          final copy = context.lumenisL10n;
          return switch (_viewModel.phase) {
            Cth10LoadPhase.loading => _LoadingState(copy: copy),
            Cth10LoadPhase.blocked => _BlockedState(
              copy: copy,
              onRetry: _viewModel.load,
            ),
            Cth10LoadPhase.failed => _FailureState(
              copy: copy,
              kind: _viewModel.failureKind,
              onRetry: _viewModel.load,
            ),
            Cth10LoadPhase.empty ||
            Cth10LoadPhase.notCollected ||
            Cth10LoadPhase.partial ||
            Cth10LoadPhase.ready => _Cth10Workspace(
              copy: copy,
              phase: _viewModel.phase,
              data: _viewModel.data!,
              selectedReport: _viewModel.selectedReport,
              onSelectReport: _viewModel.selectReport,
              onReturn: _viewModel.clearSelection,
              onRetry: _viewModel.load,
            ),
          };
        },
      ),
    ),
  );
}

String _cth10ReportStateLabel(LumenisLocalizations l10n, String state) {
  final key = switch (state.toLowerCase()) {
    'confirmed' => 'cth10.report.state.confirmed',
    'draft' => 'cth10.report.state.draft',
    'archived' => 'cth10.report.state.archived',
    _ => 'cth10.report.state.pending',
  };
  return l10n.text(key);
}

String _cth10BlockKindLabel(LumenisLocalizations l10n, String kind) {
  final key = switch (kind.toLowerCase()) {
    'conclusion' => 'cth10.block.kind.conclusion',
    'context' => 'cth10.block.kind.context',
    'driver' => 'cth10.block.kind.driver',
    'action' => 'cth10.block.kind.action',
    'outcome' => 'cth10.block.kind.outcome',
    _ => 'cth10.block.kind.unknown',
  };
  return l10n.text(key);
}

class _LoadingState extends StatelessWidget {
  const _LoadingState({required this.copy});

  final LumenisLocalizations copy;

  @override
  Widget build(BuildContext context) => Center(
    child: Semantics(
      liveRegion: true,
      label: copy.text('cth10.loading'),
      child: const CircularProgressIndicator(),
    ),
  );
}

class _BlockedState extends StatelessWidget {
  const _BlockedState({required this.copy, required this.onRetry});

  final LumenisLocalizations copy;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => _MessageState(
    copy: copy,
    title: copy.text('cth10.blocked.title'),
    detail: copy.text('cth10.blocked.detail'),
    onRetry: onRetry,
  );
}

class _FailureState extends StatelessWidget {
  const _FailureState({
    required this.copy,
    required this.kind,
    required this.onRetry,
  });

  final LumenisLocalizations copy;
  final Cth10FailureKind? kind;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => _MessageState(
    copy: copy,
    title: copy.text('cth10.error.generic'),
    detail: switch (kind) {
      Cth10FailureKind.authentication ||
      Cth10FailureKind.permissionDenied => copy.text('cth10.error.auth'),
      _ => copy.text('cth10.error.generic'),
    },
    onRetry: onRetry,
  );
}

class _MessageState extends StatelessWidget {
  const _MessageState({
    required this.copy,
    required this.title,
    required this.detail,
    required this.onRetry,
  });

  final LumenisLocalizations copy;
  final String title;
  final String detail;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, constraints) => Align(
      alignment: Alignment.topCenter,
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 720),
        child: Padding(
          padding: EdgeInsets.all(constraints.maxWidth < 480 ? 22 : 34),
          child: Semantics(
            liveRegion: true,
            label: '$title $detail',
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(copy.text('cth10.eyebrow'), style: _eyebrowStyle(context)),
                const SizedBox(height: 12),
                Text(
                  title,
                  style: TextStyle(
                    color: LumenisTheme.of(context).foreground,
                    fontSize: 26,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  detail,
                  style: TextStyle(
                    color: LumenisTheme.of(context).muted,
                    height: 1.55,
                  ),
                ),
                const SizedBox(height: 22),
                _TextButton(
                  label: copy.text('cth10.action.retry'),
                  onPressed: onRetry,
                ),
              ],
            ),
          ),
        ),
      ),
    ),
  );
}

class _Cth10Workspace extends StatelessWidget {
  const _Cth10Workspace({
    required this.copy,
    required this.phase,
    required this.data,
    required this.selectedReport,
    required this.onSelectReport,
    required this.onReturn,
    required this.onRetry,
  });

  final LumenisLocalizations copy;
  final Cth10LoadPhase phase;
  final Cth10WorkspaceData data;
  final Cth10Report? selectedReport;
  final ValueChanged<String> onSelectReport;
  final VoidCallback onReturn;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, constraints) {
      final desktop = constraints.maxWidth >= 1160;
      final inset = constraints.maxWidth < 480
          ? 18.0
          : constraints.maxWidth < 1000
          ? 26.0
          : 38.0;
      final report =
          selectedReport ?? (data.reports.isEmpty ? null : data.reports.first);
      return Focus(
        onKeyEvent: (node, event) {
          if (event is KeyDownEvent &&
              event.logicalKey == LogicalKeyboardKey.escape &&
              report != null) {
            onReturn();
            return KeyEventResult.handled;
          }
          return KeyEventResult.ignored;
        },
        child: Align(
          alignment: Alignment.topCenter,
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1640),
            child: SingleChildScrollView(
              padding: EdgeInsets.fromLTRB(inset, 26, inset, 46),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _PageHeader(copy: copy, onRetry: onRetry),
                  const SizedBox(height: 18),
                  _ScopeBanner(copy: copy, data: data),
                  const SizedBox(height: 22),
                  if (phase == Cth10LoadPhase.empty ||
                      phase == Cth10LoadPhase.notCollected)
                    _InlineNotice(
                      key: const ValueKey('cth10/content-state'),
                      text: phase == Cth10LoadPhase.empty
                          ? copy.text('cth10.state.empty')
                          : copy.text('cth10.state.not_collected'),
                      caution: phase == Cth10LoadPhase.notCollected,
                    ),
                  if (phase == Cth10LoadPhase.partial)
                    _InlineNotice(
                      key: const ValueKey('cth10/partial-state'),
                      text: copy.text('cth10.state.partial'),
                      caution: true,
                    ),
                  if (desktop)
                    Row(
                      key: const ValueKey('cth10/desktop-layout'),
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        SizedBox(
                          width: 240,
                          child: _ReportOutline(
                            copy: copy,
                            reports: data.reports,
                            selected: report,
                            onSelect: onSelectReport,
                          ),
                        ),
                        const SizedBox(width: 22),
                        Expanded(
                          child: _ReportPreview(
                            copy: copy,
                            report: report,
                            onReturn: onReturn,
                          ),
                        ),
                        const SizedBox(width: 22),
                        SizedBox(
                          width: 260,
                          child: _SourceRail(copy: copy, report: report),
                        ),
                      ],
                    )
                  else
                    Column(
                      key: ValueKey(
                        constraints.maxWidth >= 760
                            ? 'cth10/tablet-layout'
                            : 'cth10/mobile-layout',
                      ),
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        _ReportOutline(
                          copy: copy,
                          reports: data.reports,
                          selected: report,
                          onSelect: onSelectReport,
                        ),
                        const SizedBox(height: 18),
                        _ReportPreview(
                          copy: copy,
                          report: report,
                          onReturn: onReturn,
                        ),
                        const SizedBox(height: 18),
                        _SourceRail(copy: copy, report: report),
                      ],
                    ),
                ],
              ),
            ),
          ),
        ),
      );
    },
  );
}

class _PageHeader extends StatelessWidget {
  const _PageHeader({required this.copy, required this.onRetry});

  final LumenisLocalizations copy;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => Wrap(
    alignment: WrapAlignment.spaceBetween,
    crossAxisAlignment: WrapCrossAlignment.center,
    runSpacing: 16,
    spacing: 18,
    children: [
      ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 780),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(copy.text('cth10.eyebrow'), style: _eyebrowStyle(context)),
            const SizedBox(height: 9),
            Text(
              copy.text('cth10.title'),
              style: TextStyle(
                color: LumenisTheme.of(context).foreground,
                fontSize: 28,
                height: 1.2,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 9),
            Text(
              copy.text('cth10.summary'),
              style: TextStyle(
                color: LumenisTheme.of(context).muted,
                height: 1.5,
              ),
            ),
          ],
        ),
      ),
      Wrap(
        alignment: WrapAlignment.start,
        crossAxisAlignment: WrapCrossAlignment.center,
        spacing: 8,
        runSpacing: 8,
        children: [
          Tooltip(
            message: copy.text('cth10.action.unavailable'),
            child: Semantics(
              button: true,
              enabled: false,
              label: copy.text('cth10.action.unavailable'),
              child: FilledButton.icon(
                onPressed: null,
                icon: const Icon(Icons.auto_awesome_outlined),
                label: Text(copy.text('cth10.action.generate')),
              ),
            ),
          ),
          Tooltip(
            message: copy.text('cth10.action.unavailable'),
            child: Semantics(
              button: true,
              enabled: false,
              label: copy.text('cth10.action.unavailable'),
              child: OutlinedButton.icon(
                onPressed: null,
                icon: const Icon(Icons.download_outlined),
                label: Text(copy.text('cth10.action.export')),
              ),
            ),
          ),
          IconButton(
            tooltip: copy.text('cth10.action.retry'),
            onPressed: onRetry,
            icon: const Icon(Icons.refresh_rounded),
          ),
        ],
      ),
    ],
  );
}

class _ScopeBanner extends StatelessWidget {
  const _ScopeBanner({required this.copy, required this.data});

  final LumenisLocalizations copy;
  final Cth10WorkspaceData data;

  @override
  Widget build(BuildContext context) {
    final label = data.context.mode == Cth10ContextMode.globalAll
        ? copy.text('cth10.scope.global_all')
        : data.context.displayName ?? copy.text('cth10.scope.focused');
    return Semantics(
      label: label,
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        decoration: BoxDecoration(
          border: Border(
            top: BorderSide(color: LumenisTheme.of(context).line),
            bottom: BorderSide(color: LumenisTheme.of(context).line),
          ),
        ),
        child: Row(
          children: [
            Icon(
              Icons.adjust_rounded,
              size: 17,
              color: LumenisTheme.of(context).cth,
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                label,
                style: TextStyle(
                  color: LumenisTheme.of(context).foreground,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
            Text(
              copy.text('cth10.title'),
              style: TextStyle(
                color: LumenisTheme.of(context).quiet,
                fontSize: 12,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ReportOutline extends StatelessWidget {
  const _ReportOutline({
    required this.copy,
    required this.reports,
    required this.selected,
    required this.onSelect,
  });

  final LumenisLocalizations copy;
  final List<Cth10Report> reports;
  final Cth10Report? selected;
  final ValueChanged<String> onSelect;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      _SectionHeading(title: copy.text('cth10.outline')),
      const SizedBox(height: 12),
      if (reports.isEmpty)
        _EmptyPanel(text: copy.text('cth10.report.none'))
      else
        ...reports.map(
          (item) => Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: _ReportListItem(
              copy: copy,
              report: item,
              selected: selected?.id == item.id,
              onTap: () => onSelect(item.id),
            ),
          ),
        ),
    ],
  );
}

class _ReportListItem extends StatelessWidget {
  const _ReportListItem({
    required this.copy,
    required this.report,
    required this.selected,
    required this.onTap,
  });

  final LumenisLocalizations copy;
  final Cth10Report report;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Semantics(
    button: true,
    selected: selected,
    label: [
      report.title,
      report.period,
      _cth10ReportStateLabel(copy, report.state),
      report.scopeLabel,
    ].join(' · '),
    child: Material(
      color: selected
          ? LumenisTheme.of(context).surfaceRaised
          : LumenisTheme.of(context).surface,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                report.title,
                style: TextStyle(
                  color: LumenisTheme.of(context).foreground,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 5),
              Text(
                report.period,
                style: TextStyle(
                  color: LumenisTheme.of(context).muted,
                  fontSize: 12,
                ),
              ),
              const SizedBox(height: 5),
              Text(
                [
                  _cth10ReportStateLabel(copy, report.state),
                  report.scopeLabel,
                ].join(' · '),
                style: TextStyle(
                  color: LumenisTheme.of(context).quiet,
                  fontSize: 12,
                ),
              ),
            ],
          ),
        ),
      ),
    ),
  );
}

class _ReportPreview extends StatelessWidget {
  const _ReportPreview({
    required this.copy,
    required this.report,
    required this.onReturn,
  });

  final LumenisLocalizations copy;
  final Cth10Report? report;
  final VoidCallback onReturn;

  @override
  Widget build(BuildContext context) {
    final item = report;
    if (item == null) {
      return _InspectorFrame(
        title: copy.text('cth10.preview'),
        child: _EmptyPanel(text: copy.text('cth10.report.none')),
      );
    }

    return _InspectorFrame(
      title: copy.text('cth10.preview'),
      trailing: _TextButton(
        label: copy.text('cth10.action.clear_selection'),
        onPressed: onReturn,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            item.title,
            style: TextStyle(
              color: LumenisTheme.of(context).foreground,
              fontSize: 22,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            [
              item.period,
              item.scopeLabel,
              _cth10ReportStateLabel(copy, item.state),
            ].join(' · '),
            style: TextStyle(
              color: LumenisTheme.of(context).muted,
              fontSize: 13,
            ),
          ),
          const SizedBox(height: 18),
          Wrap(
            spacing: 7,
            runSpacing: 7,
            children: ['Conclusion', 'Context', 'Driver', 'Action', 'Outcome']
                .map(
                  (label) => DecoratedBox(
                    decoration: BoxDecoration(
                      border: Border(
                        bottom: BorderSide(
                          color: LumenisTheme.of(context).line,
                        ),
                      ),
                    ),
                    child: Padding(
                      padding: const EdgeInsets.only(
                        left: 2,
                        right: 2,
                        bottom: 5,
                      ),
                      child: Text(
                        _cth10BlockKindLabel(copy, label),
                        style: TextStyle(
                          color: LumenisTheme.of(context).cth,
                          fontSize: 12,
                        ),
                      ),
                    ),
                  ),
                )
                .toList(growable: false),
          ),
          const SizedBox(height: 20),
          if (item.blocks.isEmpty)
            Text(
              copy.text('cth10.block.none'),
              style: TextStyle(color: LumenisTheme.of(context).quiet),
            )
          else
            ...item.blocks.map(
              (block) => Padding(
                padding: const EdgeInsets.only(bottom: 18),
                child: _ReportBlock(copy: copy, block: block),
              ),
            ),
        ],
      ),
    );
  }
}

class _ReportBlock extends StatelessWidget {
  const _ReportBlock({required this.copy, required this.block});

  final LumenisLocalizations copy;
  final Cth10ReportBlock block;

  @override
  Widget build(BuildContext context) => Semantics(
    label: [
      _cth10BlockKindLabel(copy, block.kind),
      block.title,
      block.body,
      if (block.status.isNotEmpty) _cth10ReportStateLabel(copy, block.status),
    ].join(' · '),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          block.title,
          style: TextStyle(
            color: LumenisTheme.of(context).foreground,
            fontSize: 16,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 7),
        Text(
          block.body,
          style: TextStyle(color: LumenisTheme.of(context).muted, height: 1.55),
        ),
        if (block.status.isNotEmpty) ...[
          const SizedBox(height: 7),
          Text(
            _cth10ReportStateLabel(copy, block.status),
            style: TextStyle(
              color: LumenisTheme.of(context).caution,
              fontSize: 12,
            ),
          ),
        ],
      ],
    ),
  );
}

class _SourceRail extends StatelessWidget {
  const _SourceRail({required this.copy, required this.report});

  final LumenisLocalizations copy;
  final Cth10Report? report;

  @override
  Widget build(BuildContext context) {
    final item = report;
    return _InspectorFrame(
      title: copy.text('cth10.source.rail'),
      child: item == null || item.evidence.isEmpty
          ? _EmptyPanel(text: copy.text('cth10.source.none'))
          : Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: item.evidence
                  .map(
                    (reference) => Padding(
                      padding: const EdgeInsets.only(bottom: 10),
                      child: Semantics(
                        label: [
                          reference.id,
                          if (reference.quote.isNotEmpty) reference.quote,
                          if (reference.capturedAt.isNotEmpty)
                            reference.capturedAt,
                        ].join(' · '),
                        child: Text(
                          [
                            reference.id,
                            if (reference.quote.isNotEmpty) reference.quote,
                            if (reference.capturedAt.isNotEmpty)
                              reference.capturedAt,
                          ].join(' · '),
                          style: TextStyle(
                            color: LumenisTheme.of(context).muted,
                            fontSize: 12,
                            height: 1.4,
                          ),
                        ),
                      ),
                    ),
                  )
                  .toList(growable: false),
            ),
    );
  }
}

class _InspectorFrame extends StatelessWidget {
  const _InspectorFrame({
    required this.title,
    required this.child,
    this.trailing,
  });

  final String title;
  final Widget child;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) => DecoratedBox(
    decoration: BoxDecoration(
      border: Border(top: BorderSide(color: LumenisTheme.of(context).line)),
    ),
    child: Padding(
      padding: const EdgeInsets.fromLTRB(16, 14, 16, 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  title,
                  style: TextStyle(
                    color: LumenisTheme.of(context).foreground,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
              ?trailing,
            ],
          ),
          const SizedBox(height: 15),
          child,
        ],
      ),
    ),
  );
}

class _SectionHeading extends StatelessWidget {
  const _SectionHeading({required this.title});

  final String title;

  @override
  Widget build(BuildContext context) => Text(
    title,
    style: TextStyle(
      color: LumenisTheme.of(context).foreground,
      fontSize: 16,
      fontWeight: FontWeight.w600,
    ),
  );
}

class _EmptyPanel extends StatelessWidget {
  const _EmptyPanel({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    padding: const EdgeInsets.all(16),
    decoration: BoxDecoration(
      color: LumenisTheme.of(context).surface,
      border: Border(top: BorderSide(color: LumenisTheme.of(context).line)),
    ),
    child: Text(text, style: TextStyle(color: LumenisTheme.of(context).muted)),
  );
}

class _InlineNotice extends StatelessWidget {
  const _InlineNotice({required this.text, required this.caution, super.key});

  final String text;
  final bool caution;

  @override
  Widget build(BuildContext context) => Semantics(
    liveRegion: true,
    label: text,
    child: Padding(
      padding: const EdgeInsets.only(bottom: 18),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            caution ? Icons.info_outline_rounded : Icons.check_circle_outline,
            size: 18,
            color: caution
                ? LumenisTheme.of(context).caution
                : LumenisTheme.of(context).positive,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              text,
              style: TextStyle(
                color: caution
                    ? LumenisTheme.of(context).caution
                    : LumenisTheme.of(context).muted,
                height: 1.45,
              ),
            ),
          ),
        ],
      ),
    ),
  );
}

class _TextButton extends StatelessWidget {
  const _TextButton({required this.label, required this.onPressed});

  final String label;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) =>
      TextButton(onPressed: onPressed, child: Text(label));
}

TextStyle _eyebrowStyle(BuildContext context) => TextStyle(
  color: LumenisTheme.of(context).cth,
  fontSize: 12,
  fontWeight: FontWeight.w600,
  letterSpacing: 0.4,
);
