import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../../core/lumenis_core_client.dart';
import '../../../l10n/lumenis_localizations.dart';
import '../../../core/lumenis_theme.dart';
import 'cth10_repository.dart';
import 'cth10_view_model.dart';
import 'source_brief_copy.dart';
import 'source_brief_panel.dart';

class Cth10Screen extends StatefulWidget {
  const Cth10Screen({required this.client, this.repository, super.key});

  final LumenisCoreClient client;
  final Cth10Repository? repository;

  @override
  State<Cth10Screen> createState() => _Cth10ScreenState();
}

class _Cth10ScreenState extends State<Cth10Screen> {
  late Cth10ViewModel _viewModel = _createViewModel()..load();
  bool _showSourceBrief = false;

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
      _showSourceBrief = false;
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
      child: _showSourceBrief
          ? SourceBriefPanel(
              key: ObjectKey(widget.client),
              client: widget.client,
              onReturn: () => setState(() => _showSourceBrief = false),
            )
          : Column(
              children: [
                Align(
                  alignment: Alignment.centerRight,
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
                    child: TextButton.icon(
                      key: const ValueKey('cth10/source-brief-entry'),
                      onPressed: () => setState(() => _showSourceBrief = true),
                      icon: const Icon(Icons.description_outlined, size: 18),
                      label: Text(SourceBriefCopy.of(context).text('entry')),
                    ),
                  ),
                ),
                Expanded(
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
              ],
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

String _readingCopy(BuildContext context, String zh, String en, String ko) =>
    switch (Localizations.localeOf(context).languageCode) {
      'en' => en,
      'ko' => ko,
      _ => zh,
    };

String _scopeName(BuildContext context, Cth10Context scope) =>
    scope.mode == Cth10ContextMode.globalAll
    ? _readingCopy(context, '全部获准主体', 'All permitted subjects', '허용된 전체 대상')
    : scope.displayName ??
          _readingCopy(context, '当前主体', 'Current subject', '현재 대상');

String _reportTitle(BuildContext context, Cth10Report report) =>
    report.sourceBrief == null
    ? report.title
    : _readingCopy(context, '资料来源简报', 'Source brief', '자료 출처 브리프');

String _reportPeriod(BuildContext context, Cth10Report report) =>
    report.sourceBrief == null
    ? report.period
    : _readingCopy(context, '当前已收录资料', 'Current materials', '현재 등록 자료');

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
      final desktop =
          constraints.maxWidth >= 960 &&
          MediaQuery.textScalerOf(context).scale(16) <= 21.6;
      final inset = constraints.maxWidth < 480
          ? 18.0
          : constraints.maxWidth < 1000
          ? 26.0
          : 24.0;
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
                          width: 172,
                          child: _ReportOutline(
                            copy: copy,
                            reports: data.reports,
                            selected: report,
                            scope: data.context,
                            onSelect: onSelectReport,
                          ),
                        ),
                        const SizedBox(width: 22),
                        Expanded(
                          child: _ReportPreview(
                            copy: copy,
                            report: report,
                            scope: data.context,
                            onReturn: onReturn,
                          ),
                        ),
                        const SizedBox(width: 22),
                        SizedBox(
                          width: 228,
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
                          scope: data.context,
                          onSelect: onSelectReport,
                        ),
                        const SizedBox(height: 18),
                        _ReportPreview(
                          copy: copy,
                          report: report,
                          scope: data.context,
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
            Text(
              copy.text('cth10.title'),
              style: TextStyle(
                color: LumenisTheme.of(context).foreground,
                fontSize: 28,
                height: 1.2,
                fontWeight: FontWeight.w600,
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
    final label = _scopeName(context, data.context);
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
    required this.scope,
  });

  final LumenisLocalizations copy;
  final List<Cth10Report> reports;
  final Cth10Report? selected;
  final ValueChanged<String> onSelect;
  final Cth10Context scope;

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
              scope: scope,
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
    required this.scope,
  });

  final LumenisLocalizations copy;
  final Cth10Report report;
  final bool selected;
  final VoidCallback onTap;
  final Cth10Context scope;

  @override
  Widget build(BuildContext context) => Semantics(
    button: true,
    selected: selected,
    label: [
      _reportTitle(context, report),
      _reportPeriod(context, report),
      report.sourceBrief == null
          ? _cth10ReportStateLabel(copy, report.state)
          : _readingCopy(context, '资料预览', 'Source preview', '자료 미리보기'),
      _scopeName(context, scope),
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
                _reportTitle(context, report),
                style: TextStyle(
                  color: LumenisTheme.of(context).foreground,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 5),
              Text(
                _reportPeriod(context, report),
                style: TextStyle(
                  color: LumenisTheme.of(context).muted,
                  fontSize: 12,
                ),
              ),
              const SizedBox(height: 5),
              Text(
                [
                  report.sourceBrief == null
                      ? _cth10ReportStateLabel(copy, report.state)
                      : _readingCopy(
                          context,
                          '资料预览',
                          'Source preview',
                          '자료 미리보기',
                        ),
                  _scopeName(context, scope),
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
    required this.scope,
  });

  final LumenisLocalizations copy;
  final Cth10Report? report;
  final VoidCallback onReturn;
  final Cth10Context scope;

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
      paper: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            _reportTitle(context, item),
            style: TextStyle(
              color: LumenisTheme.of(context).foreground,
              fontSize: 22,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            [
              _reportPeriod(context, item),
              _scopeName(context, scope),
              if (item.sourceBrief == null)
                _cth10ReportStateLabel(copy, item.state),
            ].join(' · '),
            style: TextStyle(
              color: LumenisTheme.of(context).muted,
              fontSize: 13,
            ),
          ),
          const SizedBox(height: 18),
          if (item.sourceBrief case final brief?)
            _SourceBriefReading(brief: brief)
          else ...[
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
    container: true,
    explicitChildNodes: true,
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
        for (final line in block.body.split('\n'))
          if (line.trim().isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: _ReportParagraph(line: line),
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

class _ReportParagraph extends StatelessWidget {
  const _ReportParagraph({required this.line});
  final String line;

  @override
  Widget build(BuildContext context) {
    final heading = RegExp(r'^\s*#{1,6}\s+(.+)$').firstMatch(line);
    final text = (heading?[1] ?? line)
        .replaceFirst(RegExp(r'^\s*[-*]\s+'), '• ')
        .replaceAllMapped(RegExp(r'\*\*(.+?)\*\*'), (match) => match[1]!)
        .replaceAllMapped(
          RegExp(r'\\([\\`*_{}\[\]()#+.!>\-])'),
          (match) => match[1]!,
        )
        .replaceAll('&lt;', '<')
        .replaceAll('&gt;', '>')
        .replaceAll('&amp;', '&');
    return heading != null
        ? Semantics(
            header: true,
            child: Text(text, style: Theme.of(context).textTheme.titleMedium),
          )
        : SelectableText(
            text,
            style: TextStyle(
              color: LumenisTheme.of(context).foreground,
              height: 1.6,
            ),
          );
  }
}

String _sourceText(Object? value) =>
    value is String &&
        value.trim().isNotEmpty &&
        !RegExp(
          r'api[_ -]?key|token|cookie|password|secret|authorization',
          caseSensitive: false,
        ).hasMatch(value)
    ? value.trim()
    : '';

class _SourceBriefReading extends StatelessWidget {
  const _SourceBriefReading({required this.brief});
  final Cth10SourceBrief brief;

  @override
  Widget build(BuildContext context) {
    final palette = LumenisTheme.of(context);
    final unknown = _readingCopy(
      context,
      '尚未确认',
      'Not yet established',
      '아직 확인되지 않음',
    );
    String status(String value) => switch (value) {
      'PARTIAL' => _readingCopy(
        context,
        '部分资料可用',
        'Some materials available',
        '일부 자료 이용 가능',
      ),
      'AVAILABLE' => _readingCopy(
        context,
        '资料可用',
        'Materials available',
        '자료 이용 가능',
      ),
      'EMPTY' => _readingCopy(context, '暂无资料', 'No materials', '자료 없음'),
      _ => unknown,
    };
    Widget fact(String title, String value) => Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Wrap(
        spacing: 12,
        runSpacing: 4,
        children: [
          Text(title, style: TextStyle(color: palette.muted)),
          Text(value, style: TextStyle(color: palette.foreground)),
        ],
      ),
    );
    return Column(
      key: const ValueKey('cth10/source-brief-reading'),
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          _readingCopy(
            context,
            '已收录 ${brief.records.length} 份资料',
            '${brief.records.length} materials in this brief',
            '이 브리프에 자료 ${brief.records.length}개',
          ),
          style: Theme.of(context).textTheme.headlineSmall,
        ),
        const SizedBox(height: 8),
        Text(status(brief.status), style: TextStyle(color: palette.muted)),
        const SizedBox(height: 22),
        for (var index = 0; index < brief.records.length; index++) ...[
          Semantics(
            header: true,
            child: Text(
              '${index + 1}. ${_sourceText(brief.records[index]['title']).isEmpty ? _readingCopy(context, '未命名资料', 'Untitled material', '제목 없는 자료') : _sourceText(brief.records[index]['title'])}',
              style: Theme.of(context).textTheme.titleMedium,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            _sourceDate(context, brief.records[index]),
            style: TextStyle(color: palette.muted, height: 1.55),
          ),
          const SizedBox(height: 20),
        ],
        const Divider(),
        fact(
          _readingCopy(context, '资料覆盖', 'Coverage', '자료 범위'),
          status(brief.coverage),
        ),
        fact(
          _readingCopy(context, '资料时效', 'Freshness', '자료 최신성'),
          status(brief.freshness),
        ),
        fact(
          _readingCopy(context, '采集情况', 'Collection', '수집 현황'),
          status(brief.collectionState),
        ),
        const SizedBox(height: 12),
        Text(
          _readingCopy(
            context,
            '来源材料中的声明仍需核对，现有资料不代表全部市场，也不构成经营结论。',
            'Claims in the materials still need review. These materials do not establish market coverage or business conclusions.',
            '자료의 주장은 검토가 필요합니다. 현재 자료만으로 전체 시장 범위나 경영 결론을 확정할 수 없습니다.',
          ),
          style: TextStyle(color: palette.muted, height: 1.55),
        ),
        const SizedBox(height: 12),
        ExpansionTile(
          key: const ValueKey('cth10/source-method'),
          tilePadding: EdgeInsets.zero,
          childrenPadding: const EdgeInsets.only(bottom: 12),
          title: Text(
            _readingCopy(context, '方法与范围', 'Method and scope', '방법 및 범위'),
          ),
          children: [
            Align(
              alignment: Alignment.centerLeft,
              child: Text(
                _readingCopy(
                  context,
                  '仅整理本次获准返回的来源，不推算客流、销售、情绪或因果。',
                  'Only the permitted returned sources are summarized. Footfall, sales, sentiment and causality are not inferred.',
                  '허용되어 반환된 출처만 정리합니다. 방문객 수, 매출, 감정 또는 인과관계는 추정하지 않습니다.',
                ),
                style: TextStyle(color: palette.muted, height: 1.55),
              ),
            ),
            for (final entry in [
              (
                'candidate_count',
                _readingCopy(context, '候选来源', 'Candidate sources', '후보 출처'),
              ),
              (
                'scanned_count',
                _readingCopy(context, '已检查来源', 'Sources checked', '확인한 출처'),
              ),
              (
                'rejected_count',
                _readingCopy(context, '未获准返回', 'Not admitted', '반환 미허용'),
              ),
              (
                'withheld_count',
                _readingCopy(context, '未展示项目', 'Withheld items', '표시 보류 항목'),
              ),
            ])
              fact(entry.$2, '${brief.sample[entry.$1]}'),
            fact(
              _readingCopy(context, '查询是否截断', 'Query truncated', '조회 잘림'),
              brief.sample['truncated'] == true
                  ? _readingCopy(
                      context,
                      '是，仍有资料未返回',
                      'Yes; more materials were not returned',
                      '예, 반환되지 않은 자료가 더 있음',
                    )
                  : _readingCopy(
                      context,
                      '本次查询未截断',
                      'This query was not truncated',
                      '이번 조회는 잘리지 않음',
                    ),
            ),
            for (final entry in [
              (
                'source_type_counts_sample',
                _readingCopy(context, '来源类型', 'Source types', '출처 유형'),
              ),
              (
                'platform_counts_sample',
                _readingCopy(context, '来源平台', 'Source platforms', '출처 플랫폼'),
              ),
            ])
              if (brief.sample[entry.$1] case final Map counts)
                for (final item in counts.entries)
                  fact(
                    '${entry.$2} · ${_sourceCategory(context, '${item.key}')}',
                    '${item.value}',
                  ),
          ],
        ),
      ],
    );
  }
}

String _sourceCategory(BuildContext context, String value) => switch (value) {
  'UNKNOWN' || '' => _readingCopy(context, '未知', 'Unknown', '알 수 없음'),
  'document' => _readingCopy(context, '文档', 'Document', '문서'),
  'document_row' => _readingCopy(context, '文档条目', 'Document entry', '문서 항목'),
  _ => value,
};

String _sourceDate(BuildContext context, Map<String, dynamic> record) {
  final published = _sourceText(record['publish_datetime']);
  final captured = _sourceText(record['captured_at']);
  return [
    published.isEmpty
        ? _readingCopy(
            context,
            '发布时间未知',
            'Publication date unknown',
            '게시일 알 수 없음',
          )
        : _readingCopy(
            context,
            '发布于 $published',
            'Published $published',
            '게시 $published',
          ),
    captured.isEmpty
        ? _readingCopy(context, '收录时间未知', 'Capture date unknown', '등록일 알 수 없음')
        : _readingCopy(
            context,
            '收录于 $captured',
            'Captured $captured',
            '등록 $captured',
          ),
  ].join(' · ');
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
                      child: ExpansionTile(
                        key: ValueKey('cth10/source/${reference.id}'),
                        tilePadding: EdgeInsets.zero,
                        title: Text(
                          reference.quote.isEmpty
                              ? _readingCopy(
                                  context,
                                  '未命名来源',
                                  'Untitled source',
                                  '제목 없는 출처',
                                )
                              : reference.quote,
                        ),
                        subtitle: reference.capturedAt.isEmpty
                            ? null
                            : Text(reference.capturedAt),
                        children: [
                          for (final record
                              in item.sourceBrief?.records ??
                                  <Map<String, dynamic>>[])
                            if (reference.id ==
                                'evidence:canonical:${record['evidence_id']}')
                              _SourceDetails(record: record),
                          Align(
                            alignment: Alignment.centerLeft,
                            child: SelectableText(
                              '${_readingCopy(context, '引用编号', 'Reference', '참조 번호')}\n${reference.id}',
                              style: TextStyle(
                                color: LumenisTheme.of(context).muted,
                                fontSize: 12,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  )
                  .toList(growable: false),
            ),
    );
  }
}

class _SourceDetails extends StatelessWidget {
  const _SourceDetails({required this.record});
  final Map<String, dynamic> record;

  @override
  Widget build(BuildContext context) {
    final url = _sourceText(record['source_url']);
    final research = record['profile_research'];
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(_sourceDate(context, record)),
          const SizedBox(height: 8),
          Text(_sourceCategory(context, _sourceText(record['source_type']))),
          Text(
            _sourceCategory(context, _sourceText(record['source_platform'])),
          ),
          const SizedBox(height: 8),
          SelectableText(
            url.isNotEmpty
                ? url
                : record['source_link_status'] == 'WITHHELD'
                ? _readingCopy(
                    context,
                    '原文链接未获准显示',
                    'Original link withheld',
                    '원문 링크 표시 보류',
                  )
                : _readingCopy(
                    context,
                    '未提供原文链接',
                    'Original link not supplied',
                    '원문 링크 미제공',
                  ),
          ),
          if (research is Map) ...[
            const SizedBox(height: 8),
            Text(
              _readingCopy(
                context,
                '资料中的研究声明尚未独立核实',
                'Research statements have not been independently verified',
                '자료의 연구 주장은 독립적으로 검증되지 않음',
              ),
            ),
            if (research['references'] case final List references)
              for (final reference in references.whereType<Map>())
                Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: SelectableText(
                    [
                      _sourceText(reference['url']),
                      _sourceText(reference['source_as_of']),
                      _sourceText(reference['temporal_scope_note']),
                    ].where((value) => value.isNotEmpty).join('\n'),
                  ),
                ),
          ],
        ],
      ),
    );
  }
}

class _InspectorFrame extends StatelessWidget {
  const _InspectorFrame({
    required this.title,
    required this.child,
    this.trailing,
    this.paper = false,
  });

  final String title;
  final Widget child;
  final Widget? trailing;
  final bool paper;

  @override
  Widget build(BuildContext context) => DecoratedBox(
    decoration: paper
        ? LumenisTheme.paper(LumenisTheme.of(context), radius: 6)
        : BoxDecoration(
            border: Border(
              top: BorderSide(color: LumenisTheme.of(context).line),
            ),
          ),
    child: Material(
      type: MaterialType.transparency,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Wrap(
              spacing: 12,
              runSpacing: 4,
              alignment: WrapAlignment.spaceBetween,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                Text(
                  title,
                  style: TextStyle(
                    color: LumenisTheme.of(context).foreground,
                    fontWeight: FontWeight.w600,
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
