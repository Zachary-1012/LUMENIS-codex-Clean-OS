import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../../core/lumenis_core_client.dart';
import '../../../core/lumenis_theme.dart';
import '../../shared/read_aloud_action.dart';
import 'source_brief_copy.dart';
import 'source_brief_view_model.dart';

/// A source brief is a saved reading artifact, separate from period reports.
class SourceBriefPanel extends StatefulWidget {
  const SourceBriefPanel({
    required this.client,
    required this.onReturn,
    this.domainId = 'CTH',
    super.key,
  });

  final String domainId;
  final LumenisCoreClient client;
  final VoidCallback onReturn;

  @override
  State<SourceBriefPanel> createState() => _SourceBriefPanelState();
}

class _SourceBriefPanelState extends State<SourceBriefPanel>
    with WidgetsBindingObserver {
  late final _model = SourceBriefViewModel(client: widget.client, domainId: widget.domainId);
  final _reference = TextEditingController();
  final _scroll = ScrollController();
  Timer? _poll;
  bool _taskReference = false;
  bool _referenceRequired = false;
  bool _foreground = true;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _model.addListener(_schedulePoll);
    unawaited(_model.initialize());
  }

  bool get _pending =>
      _model.taskState == SourceBriefTaskState.pending ||
      _model.taskState == SourceBriefTaskState.running;

  void _schedulePoll() {
    _poll?.cancel();
    if (!_foreground || _model.busy || !_pending || _model.errorKind != null) {
      return;
    }
    _poll = Timer(const Duration(seconds: 5), () {
      if (mounted && _foreground && !_model.busy) {
        unawaited(_model.refreshTask());
      }
    });
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    _foreground = state == AppLifecycleState.resumed;
    _schedulePoll();
  }

  @override
  void didUpdateWidget(covariant SourceBriefPanel oldWidget) {
    super.didUpdateWidget(oldWidget);
    _model.syncContext();
  }

  @override
  void dispose() {
    _poll?.cancel();
    WidgetsBinding.instance.removeObserver(this);
    _model.removeListener(_schedulePoll);
    _model.dispose();
    _reference.dispose();
    _scroll.dispose();
    super.dispose();
  }

  Future<void> _copy(String value) async {
    final copy = SourceBriefCopy.of(context);
    var message = copy.text('copied');
    try {
      await Clipboard.setData(ClipboardData(text: value));
    } catch (_) {
      message = copy.text('copyFailed');
    }
    if (mounted) {
      ScaffoldMessenger.maybeOf(
        context,
      )?.showSnackBar(SnackBar(content: Text(message)));
    }
  }

  Future<void> _open() async {
    final value = _reference.text.trim();
    setState(() => _referenceRequired = value.isEmpty);
    if (value.isEmpty) return;
    if (value.startsWith('task_')) {
      await _model.analyseSources(taskId: value);
      return;
    }
    if (_taskReference) {
      await _model.openTask(value);
    } else {
      await _model.reopenJob(value);
    }
  }

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
    animation: _model,
    builder: (context, _) {
      final copy = SourceBriefCopy.of(context);
      final palette = LumenisTheme.of(context);
      return LayoutBuilder(
        builder: (context, constraints) {
          final narrow = constraints.maxWidth < 760;
          final result = _model.result;
          return Scrollbar(
            controller: _scroll,
            child: SingleChildScrollView(
              controller: _scroll,
              padding: EdgeInsets.all(narrow ? 20 : 32),
              child: Align(
                alignment: Alignment.topCenter,
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 1120),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      TextButton.icon(
                        onPressed: widget.onReturn,
                        icon: const Icon(Icons.arrow_back, size: 18),
                        label: Text(copy.text('return')),
                      ),
                      const SizedBox(height: 16),
                      Text(
                        copy.text('title'),
                        style: TextStyle(
                          color: palette.foreground,
                          fontSize: narrow ? 25 : 30,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      const SizedBox(height: 12),
                      Text(
                        copy.text('intro'),
                        style: TextStyle(
                          color: palette.muted,
                          fontSize: 15,
                          height: 1.6,
                        ),
                      ),
                      const SizedBox(height: 18),
                      _line(
                        copy.text('scope'),
                        _model.scopeLabel == null
                            ? copy.text('scopeUnknown')
                            : _model.globalScope
                            ? copy.text('global')
                            : _model.scopeLabel!,
                      ),
                      const SizedBox(height: 18),
                      if (_model.busy) ...[
                        Semantics(
                          liveRegion: true,
                          label: copy.text('loading'),
                          child: const LinearProgressIndicator(minHeight: 2),
                        ),
                        const SizedBox(height: 16),
                      ],
                      if (_model.errorKind case final error?) ...[
                        Semantics(
                          liveRegion: true,
                          child: Text(
                            copy.text(error.name),
                            style: TextStyle(
                              color: palette.danger,
                              height: 1.55,
                            ),
                          ),
                        ),
                        const SizedBox(height: 10),
                        if (_model.taskId == null)
                          TextButton(
                            onPressed: _model.busy ? null : _model.initialize,
                            child: Text(copy.text('retry')),
                          ),
                      ],
                      if (_model.taskId != null) _task(copy),
                      if (result != null) ...[
                        const SizedBox(height: 24),
                        if (narrow)
                          Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              _resultSummary(copy, result),
                              const SizedBox(height: 28),
                              _sources(copy, result),
                            ],
                          )
                        else
                          Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Expanded(
                                flex: 3,
                                child: _resultSummary(copy, result),
                              ),
                              const SizedBox(width: 40),
                              Expanded(flex: 4, child: _sources(copy, result)),
                            ],
                          ),
                      ],
                      if (_model.taskId == null && result == null) ...[
                        const SizedBox(height: 20),
                        _sectionTitle(copy.text('empty')),
                        const SizedBox(height: 8),
                        Text(copy.text('emptyDetail')),
                      ],
                      const SizedBox(height: 28),
                      if (_model.taskId == null && result == null) ...[
                        FilledButton.icon(
                          key: const ValueKey('source-brief/create'),
                          onPressed: _model.busy || _model.scopeLabel == null
                              ? null
                              : () => _model.start(),
                          icon: const Icon(
                            Icons.description_outlined,
                            size: 18,
                          ),
                          label: Text(copy.text('create')),
                        ),
                        const SizedBox(height: 12),
                        Text(
                          copy.text('createHint'),
                          style: TextStyle(color: palette.muted, height: 1.5),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          copy.text('analysisUnavailable'),
                          style: TextStyle(color: palette.muted, height: 1.5),
                        ),
                      ] else
                        OutlinedButton(
                          onPressed: _model.busy ? null : _model.clear,
                          child: Text(copy.text('new')),
                        ),
                      const SizedBox(height: 28),
                      Divider(color: palette.line),
                      const SizedBox(height: 20),
                      _sectionTitle(copy.text('existing')),
                      const SizedBox(height: 12),
                      Wrap(
                        spacing: 8,
                        children: [
                          ChoiceChip(
                            label: Text(copy.text('reportKind')),
                            selected: !_taskReference,
                            onSelected: _model.busy
                                ? null
                                : (_) => setState(() => _taskReference = false),
                          ),
                          ChoiceChip(
                            label: Text(copy.text('taskKind')),
                            selected: _taskReference,
                            onSelected: _model.busy
                                ? null
                                : (_) => setState(() => _taskReference = true),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        key: const ValueKey('source-brief/reference'),
                        controller: _reference,
                        enabled: !_model.busy,
                        maxLength: 128,
                        textInputAction: TextInputAction.go,
                        onSubmitted: (_) => _open(),
                        decoration: InputDecoration(
                          labelText: copy.text('reference'),
                          counterText: '',
                          errorText: _referenceRequired
                              ? copy.text('referenceRequired')
                              : null,
                          border: const OutlineInputBorder(),
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        copy.text('referenceHint'),
                        style: TextStyle(color: palette.muted, height: 1.5),
                      ),
                      const SizedBox(height: 12),
                      OutlinedButton(
                        onPressed: _model.busy ? null : _open,
                        child: Text(copy.text('open')),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          );
        },
      );
    },
  );

  Widget _task(SourceBriefCopy copy) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Semantics(
        liveRegion: true,
        child: _sectionTitle(
          copy.text(
            _model.result != null
                ? 'taskDone'
                : _model.taskState == SourceBriefTaskState.succeeded &&
                      _model.errorKind != null
                ? 'unknown'
                : _model.taskState.name,
          ),
        ),
      ),
      const SizedBox(height: 8),
      Text(copy.text('taskHint'), style: const TextStyle(height: 1.5)),
      const SizedBox(height: 12),
      SelectableText(_model.taskId!),
      Wrap(
        spacing: 8,
        children: [
          TextButton.icon(
            onPressed: () => _copy(_model.taskId!),
            icon: const Icon(Icons.copy_outlined, size: 16),
            label: Text(copy.text('copyTask')),
          ),
          TextButton(
            onPressed: _model.busy ? null : _model.refreshTask,
            child: Text(copy.text('refresh')),
          ),
          if (_model.canResume)
            FilledButton(
              onPressed: _model.busy ? null : _model.resume,
              child: Text(copy.text('resume')),
            ),
        ],
      ),
    ],
  );

  Widget _resultSummary(
    SourceBriefCopy copy,
    SourceBriefResult result,
  ) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Semantics(liveRegion: true, child: _sectionTitle(copy.text('saved'))),
      const SizedBox(height: 16),
      _line(
        copy.text('count'),
        result.sourceCount?.toString() ?? copy.text('unknownValue'),
      ),
      const SizedBox(height: 16),
      SelectableText(result.jobId),
      TextButton.icon(
        onPressed: () => _copy(result.jobId),
        icon: const Icon(Icons.copy_outlined, size: 16),
        label: Text(copy.text('copyJob')),
      ),
      Text(
        copy.text('referenceNote'),
        style: TextStyle(color: LumenisTheme.of(context).muted, height: 1.5),
      ),
      const SizedBox(height: 24),
      _sectionTitle(copy.text('sourceStatistics')),
      const SizedBox(height: 8),
      Text(copy.text('sourceStatisticsHint')),
      const SizedBox(height: 8),
      FilledButton.tonal(
        onPressed: _model.busy ? null : () => _model.analyseSources(),
        child: Text(copy.text('calculateSources')),
      ),
      if (_model.sourceStatistics case final statistics?) ...[
        const SizedBox(height: 12),
        Semantics(liveRegion: true, child: Text(copy.text('statisticsSaved'))),
        _line(
          copy.text('uniqueSourceCount'),
          statistics['unique_source_count']?.toString() ??
              copy.text('unknownValue'),
        ),
        _line(
          copy.text('publicationKnown'),
          statistics['publication_time_known_count']?.toString() ??
              copy.text('unknownValue'),
        ),
        _line(
          copy.text('publicationUnknown'),
          statistics['publication_time_unknown_count']?.toString() ??
              copy.text('unknownValue'),
        ),
        if (statistics['platform_counts'] case final Map counts)
          for (final entry in counts.entries)
            _line(entry.key.toString(), entry.value.toString()),
      ],
      if (_model.statisticsTaskId case final taskId?)
        TextButton.icon(
          onPressed: () => _copy(taskId),
          icon: const Icon(Icons.copy_outlined, size: 16),
          label: Text('${copy.text('statisticsReference')}: $taskId'),
        ),
      const SizedBox(height: 24),
      _sectionTitle(copy.text('review')),
      const SizedBox(height: 8),
      Text(
        copy.text(
          result.reviewStatus == 'HUMAN_PENDING'
              ? 'reviewPending'
              : 'reviewUnknown',
        ),
        style: const TextStyle(height: 1.6),
      ),
      const SizedBox(height: 24),
      _sectionTitle(copy.text('analysis')),
      const SizedBox(height: 8),
      Text(
        copy.text(switch (result.businessAnalysisState) {
          SourceBriefBusinessAnalysisState.notRequested =>
            'analysisNotRequested',
          SourceBriefBusinessAnalysisState.draft => 'analysisDraft',
          SourceBriefBusinessAnalysisState.unavailable ||
          SourceBriefBusinessAnalysisState.error => 'analysisError',
          SourceBriefBusinessAnalysisState.unknown => 'analysisUnknown',
        }),
        style: const TextStyle(height: 1.6),
      ),
      const SizedBox(height: 16),
      _sampleMetadata(copy, result),
      if (result.analysis case final analysis?)
        ReadAloudAction(
          sessionId: 'source-brief:${result.reportId}',
          scopeVersion:
              '${result.scope.scopeKey}:${result.reportId}:${result.artifactHash}',
          text: _speechText(result, analysis),
          purpose: ReadAloudPurpose.sourceBrief,
        ),
      if (result.analysis case final analysis?) ...[
        if (result.businessQuestion case final question?) ...[
          const SizedBox(height: 16),
          SelectableText(
            question,
            style: const TextStyle(fontWeight: FontWeight.w600, height: 1.6),
          ),
        ],
        for (final observation in analysis.sourceObservations) ...[
          const SizedBox(height: 16),
          _line(copy.text('observations'), observation.excerpt),
          SelectableText(
            observation.sourceId,
            style: const TextStyle(fontSize: 12),
          ),
        ],
        for (final interpretation in analysis.interpretations) ...[
          const SizedBox(height: 16),
          _line(copy.text('interpretations'), interpretation.text),
          SelectableText(
            interpretation.sourceIds.join(' · '),
            style: const TextStyle(fontSize: 12),
          ),
        ],
        for (final action in analysis.proposedActions) ...[
          const SizedBox(height: 20),
          _line(copy.text('actions'), action.action),
          const SizedBox(height: 8),
          _line(copy.text('reason'), action.reason),
          const SizedBox(height: 8),
          _line(copy.text('check'), action.check),
          const SizedBox(height: 8),
          SelectableText(
            action.sourceIds.join(' · '),
            style: const TextStyle(fontSize: 12),
          ),
          if (action.pilot case final pilot?) ...[
            const SizedBox(height: 12),
            _line(copy.text('audience'), pilot.audience),
            const SizedBox(height: 8),
            _line(copy.text('procedure'), pilot.procedure),
            const SizedBox(height: 8),
            _line(copy.text('measure'), pilot.measure),
            const SizedBox(height: 8),
            _line(copy.text('continueIf'), pilot.continueIf),
            const SizedBox(height: 8),
            _line(copy.text('stopIf'), pilot.stopIf),
          ],
        ],
        if (analysis.unknowns.isNotEmpty) ...[
          const SizedBox(height: 20),
          _line(copy.text('unknowns'), analysis.unknowns.join('\n\n')),
        ],
      ],
    ],
  );

  Widget _sampleMetadata(SourceBriefCopy copy, SourceBriefResult result) {
    final sourceSample = result.sourceSample;
    final analysisSample = result.analysisSample;
    final showAnalysisSample =
        analysisSample != null ||
        result.businessAnalysisState == SourceBriefBusinessAnalysisState.draft;
    String count(int? value) => value?.toString() ?? copy.text('unknownValue');
    String flag(bool? value, {required String yes, required String no}) =>
        value == null ? copy.text('unknownValue') : copy.text(value ? yes : no);

    final queryCounts = [
      '${copy.text('candidateCount')}: ${count(sourceSample?.candidateCount)}',
      '${copy.text('scannedCount')}: ${count(sourceSample?.scannedCount)}',
      '${copy.text('rejectedCount')}: ${count(sourceSample?.rejectedCount)}',
      '${copy.text('returnedCount')}: ${count(sourceSample?.returnedCount)}',
      '${copy.text('withheldCount')}: ${count(sourceSample?.withheldCount)}',
    ].join(' · ');
    final platformCounts = sourceSample?.platformCountsSample;
    final analysisCounts = [
      '${copy.text('availableBriefCount')}: ${count(analysisSample?.availableBriefCount)}',
      '${copy.text('analyzedSourceCount')}: ${count(analysisSample?.analyzedSourceCount)}',
      '${copy.text('omittedSourceCount')}: ${count(analysisSample?.omittedSourceCount)}',
    ].join(' · ');

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _sectionTitle(copy.text('sourceQuerySample')),
        const SizedBox(height: 8),
        _line(
          copy.text('returnedVerifiedCount'),
          count(sourceSample?.returnedVerifiedCount),
        ),
        const SizedBox(height: 8),
        _line(copy.text('queryCounts'), queryCounts),
        const SizedBox(height: 8),
        _line(
          copy.text('queryTruncation'),
          flag(sourceSample?.truncated, yes: 'truncatedYes', no: 'truncatedNo'),
        ),
        if (platformCounts != null && platformCounts.isNotEmpty) ...[
          const SizedBox(height: 8),
          _line(
            copy.text('platformCountsSample'),
            platformCounts.entries
                .map((entry) => '${entry.key}: ${entry.value}')
                .join(' · '),
          ),
        ],
        const SizedBox(height: 8),
        _line(
          copy.text('countsBasis'),
          _countsBasisLabel(copy, sourceSample?.countsBasis),
        ),
        if (showAnalysisSample) ...[
          const SizedBox(height: 16),
          _sectionTitle(copy.text('analysisInputSample')),
          const SizedBox(height: 8),
          _line(copy.text('analysisCounts'), analysisCounts),
          const SizedBox(height: 8),
          _line(
            copy.text('selection'),
            _selectionLabel(copy, analysisSample?.selection),
          ),
          const SizedBox(height: 8),
          _line(
            copy.text('analysisBodyTruncation'),
            flag(
              analysisSample?.hasTruncatedBodies,
              yes: 'truncatedYes',
              no: 'truncatedNo',
            ),
          ),
          const SizedBox(height: 8),
          _line(
            copy.text('coverage'),
            _coverageLabel(copy, analysisSample?.coverage),
          ),
        ],
        const SizedBox(height: 12),
        Text(
          copy.text('sampleLimit'),
          style: TextStyle(color: LumenisTheme.of(context).muted, height: 1.5),
        ),
      ],
    );
  }

  String _countsBasisLabel(
    SourceBriefCopy copy,
    String? value,
  ) => switch (value) {
    'returned verified Canonical records only; not coverage or business metrics' =>
      copy.text('countsBasisValue'),
    null => copy.text('unknownValue'),
    _ => value,
  };

  String _selectionLabel(
    SourceBriefCopy copy,
    String? value,
  ) => switch (value) {
    'explicit operator-selected verified sources; task-term window up to 1200 characters each' =>
      copy.text('selectionExplicit'),
    'latest verified nonempty bodies; at most 8, task-term window up to 1200 characters each' =>
      copy.text('selectionLatest'),
    null => copy.text('unknownValue'),
    _ => value,
  };

  String _coverageLabel(SourceBriefCopy copy, String? value) => switch (value) {
    'PARTIAL' => copy.text('coveragePartial'),
    'UNKNOWN' => copy.text('unknownValue'),
    null => copy.text('unknownValue'),
    _ => value,
  };

  String _speechText(
    SourceBriefResult result,
    SourceBriefBusinessAnalysis analysis,
  ) {
    final lines = <String>[];
    final question = result.businessQuestion?.trim();
    if (question != null && question.isNotEmpty) lines.add(question);
    for (final observation in analysis.sourceObservations) {
      if (observation.excerpt.trim().isNotEmpty) lines.add(observation.excerpt);
    }
    for (final interpretation in analysis.interpretations) {
      if (interpretation.text.trim().isNotEmpty) lines.add(interpretation.text);
    }
    for (final action in analysis.proposedActions) {
      lines.addAll([action.action, action.reason, action.check]);
      if (action.pilot case final pilot?) {
        lines.addAll([
          pilot.audience,
          pilot.procedure,
          pilot.measure,
          pilot.continueIf,
          pilot.stopIf,
        ]);
      }
    }
    lines.addAll(analysis.unknowns);
    return lines.where((line) => line.trim().isNotEmpty).join('\n\n');
  }

  Widget _sources(SourceBriefCopy copy, SourceBriefResult result) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      _sectionTitle(copy.text('sources')),
      const SizedBox(height: 10),
      if (result.records.isEmpty) Text(copy.text('noSources')),
      for (final source in result.records)
        ExpansionTile(
          key: ValueKey('source-brief/source/${source.sourceId}'),
          tilePadding: EdgeInsets.zero,
          childrenPadding: const EdgeInsets.only(bottom: 20),
          title: Text(
            source.title ?? copy.text('untitled'),
            style: const TextStyle(fontSize: 15, height: 1.5),
          ),
          subtitle: Text(
            source.sourceId,
            style: TextStyle(
              fontSize: 12,
              color: LumenisTheme.of(context).muted,
            ),
          ),
          expandedCrossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _line(
              copy.text('published'),
              source.publishedAt ?? copy.text('unknownValue'),
            ),
            const SizedBox(height: 10),
            _line(
              copy.text('captured'),
              source.capturedAt ?? copy.text('unknownValue'),
            ),
            if (source.sourceUrl != null) ...[
              const SizedBox(height: 10),
              _line(copy.text('sourceLink'), source.sourceUrl!),
            ],
            const SizedBox(height: 10),
            _line(copy.text('sourceProof'), source.evidenceRef),
          ],
        ),
    ],
  );

  Widget _sectionTitle(String text) => Text(
    text,
    style: TextStyle(
      color: LumenisTheme.of(context).foreground,
      fontSize: 18,
      fontWeight: FontWeight.w600,
    ),
  );

  Widget _line(String label, String value) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(
        label,
        style: TextStyle(color: LumenisTheme.of(context).muted, fontSize: 12),
      ),
      const SizedBox(height: 4),
      SelectableText(
        value,
        style: TextStyle(
          color: LumenisTheme.of(context).foreground,
          height: 1.5,
        ),
      ),
    ],
  );
}
