import 'package:flutter/services.dart';
import 'package:flutter/widgets.dart';

import '../../../core/lumenis_core_client.dart';
import '../../../core/lumenis_theme.dart';
import 'cth01_repository.dart';
import 'cth01_view_model.dart';

class Cth01Screen extends StatefulWidget {
  const Cth01Screen({required this.client, super.key});

  final LumenisCoreClient client;

  @override
  State<Cth01Screen> createState() => _Cth01ScreenState();
}

class _Cth01ScreenState extends State<Cth01Screen> {
  late Cth01ViewModel _viewModel;

  @override
  void initState() {
    super.initState();
    _viewModel = Cth01ViewModel(Cth01Repository(widget.client))..load();
  }

  @override
  void didUpdateWidget(covariant Cth01Screen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.client != widget.client) {
      _viewModel.dispose();
      _viewModel = Cth01ViewModel(Cth01Repository(widget.client))..load();
    }
  }

  @override
  void dispose() {
    _viewModel.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return ColoredBox(
      color: LumenisTheme.canvas,
      child: SafeArea(
        child: AnimatedBuilder(
          animation: _viewModel,
          builder: (context, _) => switch (_viewModel.status) {
            Cth01LoadStatus.loading => const _LoadingState(),
            Cth01LoadStatus.blocked => _UnavailableState(
              title: 'CTH Subject 上下文不可用',
              detail: _viewModel.message ?? 'LUMENIS Core 未返回当前 CTH Subject。',
              actionLabel: '重试',
              onAction: _viewModel.load,
            ),
            Cth01LoadStatus.failed => _UnavailableState(
              title: 'CTH 数据暂不可用',
              detail: _viewModel.message ?? '暂时无法读取 LUMENIS Core 的 CTH-01 数据。',
              actionLabel: '重试',
              onAction: _viewModel.load,
            ),
            Cth01LoadStatus.loaded => _Cth01Workspace(
              data: _viewModel.data!,
              selectedSignalIndex: _viewModel.selectedSignalIndex,
              onSelectSignal: _viewModel.selectSignal,
              onReturnToSignals: _viewModel.returnToSignals,
              onRetry: _viewModel.load,
            ),
          },
        ),
      ),
    );
  }
}

class _LoadingState extends StatelessWidget {
  const _LoadingState();

  @override
  Widget build(BuildContext context) {
    return Semantics(
      liveRegion: true,
      label: '正在读取 LUMENIS Core 当前 CTH Subject 与运营信号',
      child: Align(
        alignment: Alignment.topCenter,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 720),
          child: Padding(
            padding: const EdgeInsets.all(28),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  '商业运营总览',
                  style: TextStyle(
                    color: LumenisTheme.foreground,
                    fontSize: 26,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 20),
                _SkeletonLine(width: 250),
                const SizedBox(height: 12),
                _SkeletonLine(width: double.infinity),
                const SizedBox(height: 8),
                _SkeletonLine(width: 430),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _SkeletonLine extends StatelessWidget {
  const _SkeletonLine({required this.width});

  final double width;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: width,
      height: 13,
      decoration: BoxDecoration(
        color: LumenisTheme.surface,
        borderRadius: BorderRadius.circular(4),
      ),
    );
  }
}

class _UnavailableState extends StatelessWidget {
  const _UnavailableState({
    required this.title,
    required this.detail,
    required this.actionLabel,
    required this.onAction,
  });

  final String title;
  final String detail;
  final String actionLabel;
  final VoidCallback onAction;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) => Align(
        alignment: Alignment.topCenter,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 720),
          child: Padding(
            padding: EdgeInsets.all(constraints.maxWidth < 480 ? 22 : 32),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    color: LumenisTheme.foreground,
                    fontSize: 25,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  detail,
                  style: const TextStyle(
                    color: LumenisTheme.muted,
                    height: 1.5,
                  ),
                ),
                const SizedBox(height: 22),
                _CthTextButton(label: actionLabel, onPressed: onAction),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _Cth01Workspace extends StatelessWidget {
  const _Cth01Workspace({
    required this.data,
    required this.selectedSignalIndex,
    required this.onSelectSignal,
    required this.onReturnToSignals,
    required this.onRetry,
  });

  final Cth01ScreenData data;
  final int? selectedSignalIndex;
  final ValueChanged<int> onSelectSignal;
  final VoidCallback onReturnToSignals;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final width = constraints.maxWidth;
        final wide = width >= 1100;
        final compact = width >= 768 && !wide;
        final sidePadding = width < 480
            ? 18.0
            : width < 900
            ? 28.0
            : 40.0;

        final signals = _SignalFlow(
          data: data,
          selectedSignalIndex: selectedSignalIndex,
          onSelectSignal: onSelectSignal,
        );
        final inspection = _SignalInspection(
          data: data,
          selectedSignalIndex: selectedSignalIndex,
          onReturn: onReturnToSignals,
        );
        final insights = _InsightColumn(data: data);

        return Focus(
          onKeyEvent: (node, event) {
            if (selectedSignalIndex != null &&
                event is KeyDownEvent &&
                event.logicalKey == LogicalKeyboardKey.escape) {
              onReturnToSignals();
              return KeyEventResult.handled;
            }
            return KeyEventResult.ignored;
          },
          child: Align(
            alignment: Alignment.topCenter,
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 1680),
              child: SingleChildScrollView(
                padding: EdgeInsets.fromLTRB(sidePadding, 30, sidePadding, 52),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _PageHeader(data: data, onRetry: onRetry),
                    const SizedBox(height: 24),
                    _ScopeNotice(),
                    const SizedBox(height: 22),
                    _MetricSpine(data: data, compact: !wide),
                    const SizedBox(height: 28),
                    if (wide)
                      Row(
                        key: const ValueKey('cth01/layout-desktop'),
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Expanded(flex: 7, child: signals),
                          const SizedBox(width: 32),
                          Expanded(
                            flex: 4,
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                inspection,
                                if (selectedSignalIndex != null)
                                  const SizedBox(height: 24),
                                insights,
                              ],
                            ),
                          ),
                        ],
                      )
                    else
                      Column(
                        key: const ValueKey('cth01/layout-single-task'),
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          signals,
                          if (compact || selectedSignalIndex != null) ...[
                            const SizedBox(height: 22),
                            inspection,
                          ],
                          const SizedBox(height: 28),
                          insights,
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
}

class _PageHeader extends StatelessWidget {
  const _PageHeader({required this.data, required this.onRetry});

  final Cth01ScreenData data;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      alignment: WrapAlignment.spaceBetween,
      crossAxisAlignment: WrapCrossAlignment.center,
      runSpacing: 18,
      spacing: 20,
      children: [
        ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 820),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                '商业运营总览',
                style: TextStyle(
                  color: LumenisTheme.foreground,
                  fontSize: 28,
                  height: 1.2,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 13),
              Semantics(
                key: const ValueKey('cth01/current-subject'),
                label: 'LUMENIS Core 当前 CTH Subject ${data.subjectId}',
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      width: 7,
                      height: 7,
                      decoration: const BoxDecoration(
                        color: LumenisTheme.cth,
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(width: 10),
                    Flexible(
                      child: Text(
                        '当前 Subject · ${data.subjectId}',
                        style: const TextStyle(
                          color: LumenisTheme.foreground,
                          fontSize: 15,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 7),
              const Text(
                '来自 Core 当前上下文；本页接口没有返回操作者与 Subject 的授权绑定。',
                style: TextStyle(color: LumenisTheme.muted, height: 1.45),
              ),
              if (data.generatedAt.isNotEmpty) ...[
                const SizedBox(height: 6),
                Text(
                  'Core 聚合响应生成于 ${data.generatedAt}',
                  style: const TextStyle(
                    color: LumenisTheme.quiet,
                    fontSize: 12,
                  ),
                ),
              ],
            ],
          ),
        ),
        _CthTextButton(label: '重新读取', onPressed: onRetry),
      ],
    );
  }
}

class _ScopeNotice extends StatelessWidget {
  const _ScopeNotice();

  @override
  Widget build(BuildContext context) {
    return Semantics(
      liveRegion: true,
      label: '只读页面。趋势与 Subject 证据关联尚不可验证；业务写入操作不可用。',
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(horizontal: 15, vertical: 12),
        decoration: BoxDecoration(
          color: LumenisTheme.surface,
          border: Border.all(color: LumenisTheme.line),
          borderRadius: BorderRadius.circular(10),
        ),
        child: const Text(
          '只读数据 · Subject 授权、证据关联和部分趋势状态仍待 Core 验证',
          style: TextStyle(color: LumenisTheme.caution, height: 1.45),
        ),
      ),
    );
  }
}

class _MetricSpine extends StatelessWidget {
  const _MetricSpine({required this.data, required this.compact});

  final Cth01ScreenData data;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(18, 16, 18, 17),
      decoration: BoxDecoration(
        color: LumenisTheme.surface,
        border: Border.all(color: LumenisTheme.line),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _SectionHeading(
            title: '主体信号',
            detail: '仅显示 CTH-01 当前返回的生产数据状态',
          ),
          const SizedBox(height: 15),
          if (compact)
            Column(
              children: [
                _MetricLine(
                  key: const ValueKey('cth01/metric-negative-voice'),
                  label: '在线负面记录',
                  metric: data.negativeVoice,
                  readyUnit: '条',
                ),
                const _ThinRule(),
                _MetricLine(
                  key: const ValueKey('cth01/metric-footfall'),
                  label: '到店客流',
                  metric: data.footfall,
                ),
                const _ThinRule(),
                _MetricLine(
                  key: const ValueKey('cth01/metric-member-sales'),
                  label: '会员销售占比',
                  metric: data.memberSales,
                ),
              ],
            )
          else
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: _MetricLine(
                    key: const ValueKey('cth01/metric-negative-voice'),
                    label: '在线负面记录',
                    metric: data.negativeVoice,
                    readyUnit: '条',
                  ),
                ),
                const _VerticalRule(),
                Expanded(
                  child: _MetricLine(
                    key: const ValueKey('cth01/metric-footfall'),
                    label: '到店客流',
                    metric: data.footfall,
                  ),
                ),
                const _VerticalRule(),
                Expanded(
                  child: _MetricLine(
                    key: const ValueKey('cth01/metric-member-sales'),
                    label: '会员销售占比',
                    metric: data.memberSales,
                  ),
                ),
              ],
            ),
        ],
      ),
    );
  }
}

class _MetricLine extends StatelessWidget {
  const _MetricLine({
    required this.label,
    required this.metric,
    this.readyUnit = '',
    super.key,
  });

  final String label;
  final Cth01Metric metric;
  final String readyUnit;

  @override
  Widget build(BuildContext context) {
    final stateText = metric.hasValue
        ? _formatNumber(metric.value!) +
              (readyUnit.isEmpty ? metric.unit : readyUnit)
        : metric.state.label;
    final stateColor = metric.hasValue
        ? LumenisTheme.foreground
        : metric.state == Cth01BackendState.notCollected
        ? LumenisTheme.caution
        : LumenisTheme.muted;
    final detail = metric.note.isNotEmpty
        ? metric.note
        : metric.hasValue
        ? '当前请求返回的记录数；未提供来源时间戳。'
        : metric.source;

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: const TextStyle(color: LumenisTheme.muted, fontSize: 13),
          ),
          const SizedBox(height: 6),
          Semantics(
            label: '$label：$stateText',
            child: Text(
              stateText,
              style: TextStyle(
                color: stateColor,
                fontSize: metric.hasValue ? 22 : 15,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          if (detail.isNotEmpty) ...[
            const SizedBox(height: 5),
            Text(
              detail,
              style: const TextStyle(
                color: LumenisTheme.quiet,
                fontSize: 12,
                height: 1.4,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _SignalFlow extends StatelessWidget {
  const _SignalFlow({
    required this.data,
    required this.selectedSignalIndex,
    required this.onSelectSignal,
  });

  final Cth01ScreenData data;
  final int? selectedSignalIndex;
  final ValueChanged<int> onSelectSignal;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const _SectionHeading(
          title: '时间信号流',
          detail: '按 Core 返回顺序查看主体事件；这里只展示当前响应的样本',
        ),
        const SizedBox(height: 10),
        _TrendAvailability(),
        const SizedBox(height: 16),
        if (data.signals.isEmpty)
          _UnavailableInline(
            key: const ValueKey('cth01/events-empty-or-unknown'),
            title: data.eventState == Cth01BackendState.empty
                ? 'Core 未返回事件记录'
                : '事件流当前不可用',
            detail: data.eventState == Cth01BackendState.empty
                ? '后端把空结果与查询异常映射成相同状态；不能据此断言“没有事件”。'
                : 'Core 未提供可展示的事件记录或可判定的空状态。',
          )
        else ...[
          for (var index = 0; index < data.signals.length; index++)
            _SignalRow(
              key: ValueKey('cth01/signal-$index'),
              signal: data.signals[index],
              selected: selectedSignalIndex == index,
              onTap: () => onSelectSignal(index),
            ),
          const SizedBox(height: 11),
          const Text(
            '最多显示 Core 返回的三条事件；该列表不代表全量在办数量。',
            style: TextStyle(color: LumenisTheme.quiet, fontSize: 12),
          ),
        ],
      ],
    );
  }
}

class _SignalRow extends StatefulWidget {
  const _SignalRow({
    required this.signal,
    required this.selected,
    required this.onTap,
    super.key,
  });

  final Cth01Signal signal;
  final bool selected;
  final VoidCallback onTap;

  @override
  State<_SignalRow> createState() => _SignalRowState();
}

class _SignalRowState extends State<_SignalRow> {
  bool _showFocus = false;

  @override
  Widget build(BuildContext context) {
    final signal = widget.signal;
    final time = [
      signal.date,
      signal.time,
    ].where((value) => value.isNotEmpty && value != '—').join(' · ');
    final severity = _severityLabel(signal.level);
    final dateLabel = time.isEmpty ? '时间未提供' : time;
    final semanticLabel = '$dateLabel，$severity，${signal.title}';

    return FocusableActionDetector(
      mouseCursor: SystemMouseCursors.click,
      onShowFocusHighlight: (value) => setState(() => _showFocus = value),
      shortcuts: const <ShortcutActivator, Intent>{
        SingleActivator(LogicalKeyboardKey.enter): ActivateIntent(),
        SingleActivator(LogicalKeyboardKey.space): ActivateIntent(),
      },
      actions: <Type, Action<Intent>>{
        ActivateIntent: CallbackAction<ActivateIntent>(
          onInvoke: (intent) {
            widget.onTap();
            return null;
          },
        ),
      },
      child: Semantics(
        button: true,
        selected: widget.selected,
        label: semanticLabel,
        onTap: widget.onTap,
        child: GestureDetector(
          behavior: HitTestBehavior.opaque,
          onTap: widget.onTap,
          child: Container(
            constraints: const BoxConstraints(minHeight: 58),
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
            decoration: BoxDecoration(
              color: widget.selected ? LumenisTheme.surfaceRaised : null,
              border: Border(
                top: _showFocus || widget.selected
                    ? const BorderSide(color: LumenisTheme.cth)
                    : BorderSide.none,
                bottom: const BorderSide(color: LumenisTheme.line),
                left: BorderSide(
                  color: _showFocus
                      ? LumenisTheme.cth
                      : const Color(0x00000000),
                  width: 1,
                ),
                right: BorderSide(
                  color: _showFocus
                      ? LumenisTheme.cth
                      : const Color(0x00000000),
                  width: 1,
                ),
              ),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Padding(
                  padding: const EdgeInsets.only(top: 7, right: 13),
                  child: Container(
                    width: 8,
                    height: 8,
                    decoration: BoxDecoration(
                      color: _severityColor(signal.level),
                      shape: BoxShape.circle,
                    ),
                  ),
                ),
                SizedBox(
                  width: 100,
                  child: Text(
                    dateLabel,
                    style: const TextStyle(
                      color: LumenisTheme.quiet,
                      fontSize: 12,
                      height: 1.45,
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Wrap(
                        spacing: 9,
                        runSpacing: 4,
                        crossAxisAlignment: WrapCrossAlignment.center,
                        children: [
                          Text(
                            signal.title,
                            style: const TextStyle(
                              color: LumenisTheme.foreground,
                              fontWeight: FontWeight.w600,
                              height: 1.4,
                            ),
                          ),
                          Text(
                            severity,
                            style: TextStyle(
                              color: _severityColor(signal.level),
                              fontSize: 12,
                            ),
                          ),
                        ],
                      ),
                      if (signal.summary.isNotEmpty) ...[
                        const SizedBox(height: 5),
                        Text(
                          signal.summary,
                          maxLines: 3,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            color: LumenisTheme.muted,
                            fontSize: 13,
                            height: 1.45,
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
}

class _SignalInspection extends StatelessWidget {
  const _SignalInspection({
    required this.data,
    required this.selectedSignalIndex,
    required this.onReturn,
  });

  final Cth01ScreenData data;
  final int? selectedSignalIndex;
  final VoidCallback onReturn;

  @override
  Widget build(BuildContext context) {
    if (selectedSignalIndex == null ||
        selectedSignalIndex! >= data.signals.length) {
      return const SizedBox.shrink();
    }
    final signal = data.signals[selectedSignalIndex!];
    final timestamp = [
      signal.date,
      signal.time,
    ].where((value) => value.isNotEmpty && value != '—').join(' · ');

    return Container(
      key: const ValueKey('cth01/signal-inspection'),
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(17, 16, 17, 15),
      decoration: BoxDecoration(
        color: LumenisTheme.surface,
        border: Border.all(color: LumenisTheme.cth.withValues(alpha: 0.55)),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _SectionHeading(
            title: '信号检查',
            detail: '仅检查 Core 返回的事件记录；未创建或更新业务数据',
          ),
          const SizedBox(height: 12),
          Text(
            signal.title,
            style: const TextStyle(
              color: LumenisTheme.foreground,
              fontSize: 17,
              fontWeight: FontWeight.w600,
              height: 1.4,
            ),
          ),
          const SizedBox(height: 9),
          _DetailLine(
            label: '时间',
            value: timestamp.isEmpty ? '未提供' : timestamp,
          ),
          _DetailLine(label: '风险级别', value: _severityLabel(signal.level)),
          if (signal.summary.isNotEmpty)
            _DetailLine(label: '摘要', value: signal.summary),
          if (signal.tags.isNotEmpty)
            _DetailLine(label: '标签', value: signal.tags.join(' · ')),
          if (signal.eventReference.isNotEmpty)
            _DetailLine(label: '事件记录引用', value: signal.eventReference),
          const SizedBox(height: 8),
          const Text(
            '事件引用不是证据 ID；当前响应没有可核验的来源链接。',
            style: TextStyle(color: LumenisTheme.quiet, fontSize: 12),
          ),
          const SizedBox(height: 11),
          _CthTextButton(label: '返回信号流', onPressed: onReturn),
        ],
      ),
    );
  }
}

class _InsightColumn extends StatelessWidget {
  const _InsightColumn({required this.data});

  final Cth01ScreenData data;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _DailySummaryView(summary: data.dailySummary),
        const SizedBox(height: 22),
        _RiskNotesView(risks: data.risks),
        const SizedBox(height: 22),
        const _EvidenceLineageState(),
        const SizedBox(height: 22),
        const _ActionAvailability(),
      ],
    );
  }
}

class _DailySummaryView extends StatelessWidget {
  const _DailySummaryView({required this.summary});

  final Cth01DailySummary summary;

  @override
  Widget build(BuildContext context) {
    return _ReadSection(
      key: const ValueKey('cth01/daily-summary'),
      title: '今日确定性指标',
      detail: '来自 Shared Reporting 对 CTH 记录的计算；不是 AI 结论',
      child: summary.hasValues
          ? Column(
              children: [
                if (summary.riskIndex != null)
                  _FactLine(
                    label: '风险指数',
                    value: '${_formatNumber(summary.riskIndex!)} / 100',
                  ),
                if (summary.subjectHealthScore != null)
                  _FactLine(
                    label: '当前 Subject 健康分',
                    value:
                        '${_formatNumber(summary.subjectHealthScore!)} / 100',
                  ),
                if (summary.mediumHighRiskNoteCount != null)
                  _FactLine(
                    label: '中 / 高风险笔记',
                    value: _formatNumber(summary.mediumHighRiskNoteCount!),
                  ),
                const SizedBox(height: 9),
                const Text(
                  '风险笔记口径来自今日已筛选记录；不包含 critical 桶，且不代表事件总数。',
                  style: TextStyle(
                    color: LumenisTheme.quiet,
                    fontSize: 12,
                    height: 1.45,
                  ),
                ),
              ],
            )
          : const Text(
              '今日摘要未返回可用指标；当前接口未区分空值与汇总读取失败。',
              style: TextStyle(color: LumenisTheme.muted, height: 1.5),
            ),
    );
  }
}

class _RiskNotesView extends StatelessWidget {
  const _RiskNotesView({required this.risks});

  final List<Cth01RiskNote> risks;

  @override
  Widget build(BuildContext context) {
    return _ReadSection(
      key: const ValueKey('cth01/risk-notes'),
      title: '风险笔记',
      detail: '主体筛选后的高风险记录样本',
      child: risks.isEmpty
          ? const Text(
              'Core 未返回可展示的风险笔记；当前接口没有区分空结果与查询失败。',
              style: TextStyle(color: LumenisTheme.muted, height: 1.5),
            )
          : Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                for (var index = 0; index < risks.length; index++) ...[
                  if (index > 0) const _ThinRule(),
                  _RiskNoteLine(risk: risks[index]),
                ],
              ],
            ),
    );
  }
}

class _RiskNoteLine extends StatelessWidget {
  const _RiskNoteLine({required this.risk});

  final Cth01RiskNote risk;

  @override
  Widget build(BuildContext context) {
    final details = <String>[_severityLabel(risk.level)];
    if (risk.score != null) details.add('风险分 ${_formatNumber(risk.score!)}');
    if (risk.noteReference.isNotEmpty) {
      details.add('记录引用 ${risk.noteReference}');
    }

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            risk.title,
            style: const TextStyle(
              color: LumenisTheme.foreground,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 5),
          Text(
            details.join(' · '),
            style: TextStyle(color: _severityColor(risk.level), fontSize: 12),
          ),
          if (risk.description.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(
              risk.description,
              style: const TextStyle(
                color: LumenisTheme.muted,
                fontSize: 13,
                height: 1.45,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _TrendAvailability extends StatelessWidget {
  const _TrendAvailability();

  @override
  Widget build(BuildContext context) {
    return const _UnavailableInline(
      key: ValueKey('cth01/trend-blocked'),
      title: '14 日趋势暂不显示',
      detail: '当前 Core 会将按日查询错误转换成 0；在返回可区分“零值 / 缺数 / 错误”的状态前，本页不绘制趋势。',
    );
  }
}

class _EvidenceLineageState extends StatelessWidget {
  const _EvidenceLineageState();

  @override
  Widget build(BuildContext context) {
    return const _UnavailableInline(
      key: ValueKey('cth01/evidence-scope-blocked'),
      title: 'Subject 证据关联未验证',
      detail: 'Core 当前只返回未按 product、Subject 或来源域筛选的共享记录，本页不展示或关联这些记录。',
    );
  }
}

class _ActionAvailability extends StatelessWidget {
  const _ActionAvailability();

  @override
  Widget build(BuildContext context) {
    return const _UnavailableInline(
      key: ValueKey('cth01/actions-blocked'),
      title: '业务操作暂不可用',
      detail: '简报、导出、建案、计划与通知尚无本页可验证的权限结果和执行接口。',
    );
  }
}

class _UnavailableInline extends StatelessWidget {
  const _UnavailableInline({
    required this.title,
    required this.detail,
    super.key,
  });

  final String title;
  final String detail;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 15, vertical: 13),
      decoration: BoxDecoration(
        color: LumenisTheme.surface,
        border: Border.all(color: LumenisTheme.line),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: const TextStyle(
              color: LumenisTheme.foreground,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 5),
          Text(
            detail,
            style: const TextStyle(
              color: LumenisTheme.muted,
              fontSize: 12,
              height: 1.45,
            ),
          ),
        ],
      ),
    );
  }
}

class _ReadSection extends StatelessWidget {
  const _ReadSection({
    required this.title,
    required this.detail,
    required this.child,
    super.key,
  });

  final String title;
  final String detail;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(16, 15, 16, 15),
      decoration: BoxDecoration(
        color: LumenisTheme.surface,
        border: Border.all(color: LumenisTheme.line),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _SectionHeading(title: title, detail: detail),
          const SizedBox(height: 12),
          child,
        ],
      ),
    );
  }
}

class _SectionHeading extends StatelessWidget {
  const _SectionHeading({required this.title, required this.detail});

  final String title;
  final String detail;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: const TextStyle(
            color: LumenisTheme.foreground,
            fontSize: 17,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          detail,
          style: const TextStyle(
            color: LumenisTheme.quiet,
            fontSize: 12,
            height: 1.45,
          ),
        ),
      ],
    );
  }
}

class _FactLine extends StatelessWidget {
  const _FactLine({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 7),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Text(
              label,
              style: const TextStyle(color: LumenisTheme.muted),
            ),
          ),
          const SizedBox(width: 12),
          Flexible(
            child: Text(
              value,
              textAlign: TextAlign.end,
              softWrap: true,
              style: const TextStyle(
                color: LumenisTheme.foreground,
                fontWeight: FontWeight.w600,
                fontFeatures: [FontFeature.tabularFigures()],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _DetailLine extends StatelessWidget {
  const _DetailLine({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 7),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 82,
            child: Text(
              label,
              style: const TextStyle(color: LumenisTheme.quiet, fontSize: 12),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(
                color: LumenisTheme.muted,
                fontSize: 13,
                height: 1.45,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _ThinRule extends StatelessWidget {
  const _ThinRule();

  @override
  Widget build(BuildContext context) => const Padding(
    padding: EdgeInsets.symmetric(vertical: 12),
    child: SizedBox(height: 1, child: ColoredBox(color: LumenisTheme.line)),
  );
}

class _VerticalRule extends StatelessWidget {
  const _VerticalRule();

  @override
  Widget build(BuildContext context) => const Padding(
    padding: EdgeInsets.symmetric(horizontal: 15),
    child: SizedBox(
      height: 76,
      width: 1,
      child: ColoredBox(color: LumenisTheme.line),
    ),
  );
}

class _CthTextButton extends StatefulWidget {
  const _CthTextButton({required this.label, required this.onPressed});

  final String label;
  final VoidCallback onPressed;

  @override
  State<_CthTextButton> createState() => _CthTextButtonState();
}

class _CthTextButtonState extends State<_CthTextButton> {
  bool _showFocus = false;

  @override
  Widget build(BuildContext context) {
    return FocusableActionDetector(
      mouseCursor: SystemMouseCursors.click,
      onShowFocusHighlight: (value) => setState(() => _showFocus = value),
      shortcuts: const <ShortcutActivator, Intent>{
        SingleActivator(LogicalKeyboardKey.enter): ActivateIntent(),
        SingleActivator(LogicalKeyboardKey.space): ActivateIntent(),
      },
      actions: <Type, Action<Intent>>{
        ActivateIntent: CallbackAction<ActivateIntent>(
          onInvoke: (intent) {
            widget.onPressed();
            return null;
          },
        ),
      },
      child: Semantics(
        button: true,
        label: widget.label,
        onTap: widget.onPressed,
        child: GestureDetector(
          behavior: HitTestBehavior.opaque,
          onTap: widget.onPressed,
          child: Container(
            constraints: const BoxConstraints(minHeight: 48, minWidth: 48),
            alignment: Alignment.center,
            padding: const EdgeInsets.symmetric(horizontal: 15, vertical: 11),
            decoration: BoxDecoration(
              color: LumenisTheme.surfaceRaised,
              border: Border.all(
                color: _showFocus ? LumenisTheme.cth : LumenisTheme.line,
              ),
              borderRadius: BorderRadius.circular(9),
            ),
            child: Text(
              widget.label,
              style: const TextStyle(
                color: LumenisTheme.foreground,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ),
      ),
    );
  }
}

String _severityLabel(String level) => switch (level.toLowerCase()) {
  'critical' => '严重风险',
  'high' => '高风险',
  'medium' || 'med' => '中风险',
  'low' => '低风险',
  _ => '风险级别未返回',
};

Color _severityColor(String level) => switch (level.toLowerCase()) {
  'critical' || 'high' => LumenisTheme.danger,
  'medium' || 'med' => LumenisTheme.caution,
  'low' => LumenisTheme.positive,
  _ => LumenisTheme.muted,
};

String _formatNumber(num value) {
  if (value % 1 == 0) return value.toInt().toString();
  return value.toStringAsFixed(1);
}
