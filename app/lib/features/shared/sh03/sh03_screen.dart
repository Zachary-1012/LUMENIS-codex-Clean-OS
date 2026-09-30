import 'package:flutter/material.dart';

import '../../../core/lumenis_core_client.dart';
import '../../../core/lumenis_theme.dart';
import '../../../l10n/lumenis_localizations.dart';
import 'sh03_repository.dart';
import 'sh03_snapshot.dart';
import 'sh03_view_model.dart';

class Sh03Screen extends StatefulWidget {
  const Sh03Screen({required this.client, this.repository, super.key});

  final LumenisCoreClient client;
  final Sh03Repository? repository;

  @override
  State<Sh03Screen> createState() => _Sh03ScreenState();
}

class _Sh03ScreenState extends State<Sh03Screen> {
  late final Sh03ViewModel _viewModel = Sh03ViewModel(
    repository: widget.repository ?? CoreSh03Repository(client: widget.client),
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
  Widget build(BuildContext context) => ColoredBox(
    color: LumenisTheme.of(context).canvas,
    child: SafeArea(
      child: AnimatedBuilder(
        animation: _viewModel,
        builder: (context, _) => switch (_viewModel.phase) {
          Sh03LoadPhase.loading => _LoadingState(),
          Sh03LoadPhase.blocked => _BlockedState(
            error: _viewModel.scopeError,
            onRetry: _viewModel.refresh,
          ),
          Sh03LoadPhase.failed => _FailureState(
            kind: _viewModel.failureKind!,
            onRetry: _viewModel.refresh,
          ),
          Sh03LoadPhase.ready => _Workspace(viewModel: _viewModel),
        },
      ),
    ),
  );
}

class _Workspace extends StatelessWidget {
  const _Workspace({required this.viewModel});

  final Sh03ViewModel viewModel;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, constraints) {
      final wide = constraints.maxWidth >= 1120;
      final medium = constraints.maxWidth >= 760;
      final snapshot = viewModel.snapshot!;
      final navigator = _MetricNavigator(viewModel: viewModel);
      final definition = _DefinitionPane(metric: viewModel.selected);
      final samples = _SamplePane(metric: viewModel.selected);
      return Align(
        alignment: Alignment.topCenter,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1540),
          child: SingleChildScrollView(
            padding: EdgeInsets.fromLTRB(
              wide ? 32 : 18,
              24,
              wide ? 32 : 18,
              44,
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _Header(),
                const SizedBox(height: 18),
                _ScopeBanner(scope: snapshot.scope),
                const SizedBox(height: 16),
                if (wide)
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      SizedBox(width: 300, child: navigator),
                      const SizedBox(width: 16),
                      Expanded(child: definition),
                      const SizedBox(width: 16),
                      SizedBox(width: 330, child: samples),
                    ],
                  )
                else if (medium)
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      navigator,
                      const SizedBox(height: 14),
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Expanded(child: definition),
                          const SizedBox(width: 14),
                          Expanded(child: samples),
                        ],
                      ),
                    ],
                  )
                else ...[
                  navigator,
                  const SizedBox(height: 14),
                  definition,
                  const SizedBox(height: 14),
                  samples,
                ],
                const SizedBox(height: 14),
                Align(
                  alignment: Alignment.centerLeft,
                  child: OutlinedButton.icon(
                    onPressed: viewModel.refresh,
                    icon: const Icon(Icons.refresh_rounded),
                    label: Text(_copy(context, '重新读取', 'Read again', '다시 읽기')),
                    style: OutlinedButton.styleFrom(
                      minimumSize: const Size(48, 48),
                    ),
                  ),
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
  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      _Eyebrow(_copy(context, '正式数据', 'FORMAL DATA', '정식 데이터')),
      const SizedBox(height: 9),
      Text(
        context.lumenisL10n.text('screen.SH-03'),
        style: Theme.of(context).textTheme.headlineMedium?.copyWith(
          color: LumenisTheme.of(context).foreground,
          fontWeight: FontWeight.w600,
        ),
      ),
      const SizedBox(height: 6),
      Text(
        _copy(
          context,
          '查看指标定义、来源链路和经过筛选的样本；这里只读，不编辑业务事实。',
          'Inspect metric definitions, source lineage and scoped samples. This browser is read-only.',
          '지표 정의·출처 계보·범위가 확인된 샘플을 확인합니다. 이 화면은 읽기 전용입니다.',
        ),
        style: TextStyle(color: LumenisTheme.of(context).muted, height: 1.45),
      ),
    ],
  );
}

class _ScopeBanner extends StatelessWidget {
  const _ScopeBanner({required this.scope});

  final Sh03Scope scope;

  @override
  Widget build(BuildContext context) {
    final range = scope.isGlobal
        ? _copy(context, '全部范围', 'All scopes', '전체 범위')
        : '${scope.businessDomain} · ${scope.displayName}';
    return Semantics(
      liveRegion: true,
      label: _copy(
        context,
        '当前查看范围：$range',
        'Current range: $range',
        '현재 범위: $range',
      ),
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(horizontal: 15, vertical: 12),
        decoration: BoxDecoration(
          color: LumenisTheme.of(context).system.withValues(alpha: 0.08),
          border: Border.all(
            color: LumenisTheme.of(context).system.withValues(alpha: 0.35),
          ),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Row(
          children: [
            Icon(
              Icons.tune_rounded,
              color: LumenisTheme.of(context).system,
              size: 19,
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                range,
                style: const TextStyle(fontWeight: FontWeight.w600),
              ),
            ),
            Text(
              _copy(context, '已确认查看范围', 'Verified viewing range', '확인된 조회 범위'),
              style: TextStyle(
                color: LumenisTheme.of(context).muted,
                fontSize: 12,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _MetricNavigator extends StatelessWidget {
  const _MetricNavigator({required this.viewModel});

  final Sh03ViewModel viewModel;

  @override
  Widget build(BuildContext context) => _Panel(
    title: _copy(context, '指标目录', 'Metric index', '지표 목록'),
    detail: _copy(
      context,
      '选择一个指标查看定义和样本。',
      'Select a metric to inspect its definition and samples.',
      '지표를 선택해 정의와 샘플을 확인하세요.',
    ),
    child: Column(
      children: [
        TextField(
          key: const Key('sh03-search'),
          onChanged: viewModel.setQuery,
          decoration: InputDecoration(
            labelText: _copy(context, '搜索指标', 'Search metrics', '지표 검색'),
            prefixIcon: const Icon(Icons.search_rounded),
            border: const OutlineInputBorder(),
          ),
        ),
        const SizedBox(height: 12),
        if (viewModel.visibleMetrics.isEmpty)
          _InfoMessage(
            _copy(
              context,
              '当前没有可查看的指标。',
              'No metrics are available to inspect.',
              '확인할 지표가 없습니다.',
            ),
          )
        else
          for (final metric in viewModel.visibleMetrics)
            _MetricRow(
              metric: metric,
              selected: viewModel.selected?.internalName == metric.internalName,
              onTap: () => viewModel.select(metric),
            ),
      ],
    ),
  );
}

class _MetricRow extends StatelessWidget {
  const _MetricRow({
    required this.metric,
    required this.selected,
    required this.onTap,
  });

  final Sh03Metric metric;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 7),
    child: Material(
      color: selected
          ? LumenisTheme.of(context).system.withValues(alpha: 0.1)
          : LumenisTheme.of(context).surfaceRaised,
      borderRadius: BorderRadius.circular(10),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(10),
        child: Container(
          constraints: const BoxConstraints(minHeight: 64),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          decoration: BoxDecoration(
            border: Border.all(
              color: selected
                  ? LumenisTheme.of(context).system.withValues(alpha: 0.52)
                  : LumenisTheme.of(context).line,
            ),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Row(
            children: [
              Icon(
                metric.derived
                    ? Icons.auto_graph_rounded
                    : Icons.straighten_rounded,
                color: selected
                    ? LumenisTheme.of(context).system
                    : LumenisTheme.of(context).quiet,
                size: 18,
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  metric.name,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontWeight: FontWeight.w600),
                ),
              ),
              const SizedBox(width: 8),
              Icon(
                Icons.chevron_right_rounded,
                color: LumenisTheme.of(context).quiet,
                size: 18,
              ),
            ],
          ),
        ),
      ),
    ),
  );
}

class _DefinitionPane extends StatelessWidget {
  const _DefinitionPane({required this.metric});

  final Sh03Metric? metric;

  @override
  Widget build(BuildContext context) => _Panel(
    title: _copy(context, '口径与来源', 'Definition & lineage', '정의와 계보'),
    detail: _copy(
      context,
      '定义、更新节奏和派生关系分开呈现。',
      'Definition, cadence and derivation are shown separately.',
      '정의·갱신 주기·파생 관계를 구분해 표시합니다.',
    ),
    child: metric == null
        ? _InfoMessage(
            _copy(
              context,
              '选择一个指标查看详情。',
              'Select a metric to inspect its details.',
              '지표를 선택해 세부 정보를 확인하세요.',
            ),
          )
        : Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                metric!.name,
                style: const TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 12),
              _DefinitionLine(
                label: _copy(context, '类型', 'Type', '유형'),
                value: metric!.derived
                    ? _copy(context, '派生指标', 'Derived metric', '파생 지표')
                    : _copy(context, '正式记录', 'Formal record', '정식 기록'),
              ),
              _DefinitionLine(
                label: _copy(context, '当前状态', 'Current state', '현재 상태'),
                value: metric!.stateLabel,
              ),
              _DefinitionLine(
                label: _copy(context, '更新节奏', 'Update cadence', '갱신 주기'),
                value: metric!.cadence,
              ),
              const SizedBox(height: 5),
              Text(
                _copy(context, '定义', 'Definition', '정의'),
                style: TextStyle(
                  color: LumenisTheme.of(context).quiet,
                  fontSize: 11,
                ),
              ),
              const SizedBox(height: 4),
              Text(metric!.definition, style: const TextStyle(height: 1.5)),
              const SizedBox(height: 15),
              Text(
                _copy(context, '来源链路', 'Source lineage', '출처 계보'),
                style: TextStyle(
                  color: LumenisTheme.of(context).quiet,
                  fontSize: 11,
                ),
              ),
              const SizedBox(height: 7),
              Wrap(
                spacing: 6,
                runSpacing: 6,
                children: metric!.lineage.isEmpty
                    ? [
                        _MetaChip(
                          _copy(
                            context,
                            '链路未完整',
                            'Lineage incomplete',
                            '계보 불완전',
                          ),
                        ),
                      ]
                    : [for (final step in metric!.lineage) _MetaChip(step)],
              ),
              const SizedBox(height: 15),
              Text(
                _copy(
                  context,
                  '这里只能查看定义，不提供编辑入口。',
                  'Definitions can be inspected here; editing is not available.',
                  '정의만 확인할 수 있으며 편집은 제공하지 않습니다.',
                ),
                style: TextStyle(
                  color: LumenisTheme.of(context).quiet,
                  fontSize: 11,
                  height: 1.45,
                ),
              ),
            ],
          ),
  );
}

class _SamplePane extends StatelessWidget {
  const _SamplePane({required this.metric});

  final Sh03Metric? metric;

  @override
  Widget build(BuildContext context) => _Panel(
    title: _copy(context, '范围内样本', 'Scoped samples', '범위 내 샘플'),
    detail: _copy(
      context,
      '仅显示服务明确允许展示的样本字段。',
      'Only fields explicitly allowed by the service are shown.',
      '서비스가 표시를 허용한 필드만 보여줍니다.',
    ),
    child: metric == null
        ? _InfoMessage(
            _copy(
              context,
              '选择一个指标查看样本。',
              'Select a metric to inspect samples.',
              '지표를 선택해 샘플을 확인하세요.',
            ),
          )
        : metric!.samples.isEmpty
        ? _InfoMessage(
            _copy(
              context,
              '当前指标没有可展示的样本。',
              'This metric has no samples available to show.',
              '이 지표에는 표시할 샘플이 없습니다.',
            ),
          )
        : Column(
            children: [
              for (final sample in metric!.samples) _SampleLine(sample: sample),
            ],
          ),
  );
}

class _SampleLine extends StatelessWidget {
  const _SampleLine({required this.sample});

  final Sh03Sample sample;

  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    margin: const EdgeInsets.only(bottom: 8),
    padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 10),
    decoration: BoxDecoration(
      color: LumenisTheme.of(context).surfaceRaised,
      border: Border.all(color: LumenisTheme.of(context).line),
      borderRadius: BorderRadius.circular(9),
    ),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: Text(
            sample.label,
            style: TextStyle(color: LumenisTheme.of(context).muted),
          ),
        ),
        const SizedBox(width: 10),
        Flexible(
          child: Text(
            sample.value,
            textAlign: TextAlign.end,
            style: const TextStyle(fontWeight: FontWeight.w600),
          ),
        ),
      ],
    ),
  );
}

class _LoadingState extends StatelessWidget {
  @override
  Widget build(BuildContext context) => Semantics(
    liveRegion: true,
    label: _copy(context, '正在读取指标', 'Reading metrics', '지표를 읽는 중'),
    child: const Center(child: CircularProgressIndicator()),
  );
}

class _BlockedState extends StatelessWidget {
  const _BlockedState({required this.error, required this.onRetry});

  final Sh03ScopeErrorKind? error;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => _StateMessage(
    title: _copy(
      context,
      '正式数据暂不显示',
      'Formal data is hidden for now',
      '정식 데이터를 현재 표시하지 않습니다',
    ),
    detail: switch (error) {
      Sh03ScopeErrorKind.denied => _copy(
        context,
        '当前账号没有这个范围的查看权限。',
        'This account cannot view the selected range.',
        '이 계정은 선택한 범위를 볼 수 없습니다.',
      ),
      Sh03ScopeErrorKind.malformed => _copy(
        context,
        '服务返回的查看范围不完整，因此不会显示指标。',
        'The returned viewing range is incomplete, so metrics are not shown.',
        '반환된 조회 범위가 불완전하여 지표를 표시하지 않습니다.',
      ),
      _ => _copy(
        context,
        '尚未确认账号与业务范围的对应关系，因此不会显示指标。',
        'The account and business range have not been verified, so metrics are not shown.',
        '계정과 업무 범위가 확인되지 않아 지표를 표시하지 않습니다.',
      ),
    },
    onRetry: onRetry,
  );
}

class _FailureState extends StatelessWidget {
  const _FailureState({required this.kind, required this.onRetry});

  final Sh03FailureKind kind;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => _StateMessage(
    title: _copy(
      context,
      '指标浏览器暂不可用',
      'Metric browser unavailable',
      '지표 브라우저를 사용할 수 없습니다',
    ),
    detail: switch (kind) {
      Sh03FailureKind.authentication => _copy(
        context,
        '当前内容暂时无法打开。可重试读取，或返回后稍后再试。',
        'This content cannot be opened right now. You can retry reading it or return and try again later.',
        '현재 콘텐츠를 지금 열 수 없습니다. 다시 읽기를 시도하거나 돌아간 뒤 나중에 다시 시도할 수 있습니다.',
      ),
      Sh03FailureKind.permissionDenied => _copy(
        context,
        '当前内容不可访问。',
        'This content is not accessible.',
        '현재 콘텐츠에 접근할 수 없습니다.',
      ),
      Sh03FailureKind.offline => _copy(
        context,
        '指标服务暂时无法连接，请检查连接后重试。',
        'The metric service cannot connect right now. Check the connection and try again.',
        '지표 서비스에 연결할 수 없습니다. 연결을 확인하고 다시 시도하세요.',
      ),
      Sh03FailureKind.response => _copy(
        context,
        '指标服务没有返回可验证的数据，请稍后重试。',
        'The metric service did not return verifiable data. Try again later.',
        '지표 서비스가 확인 가능한 데이터를 반환하지 않았습니다. 나중에 다시 시도하세요.',
      ),
    },
    onRetry: onRetry,
  );
}

class _StateMessage extends StatelessWidget {
  const _StateMessage({
    required this.title,
    required this.detail,
    required this.onRetry,
  });

  final String title;
  final String detail;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => Center(
    child: ConstrainedBox(
      constraints: const BoxConstraints(maxWidth: 620),
      child: Padding(
        padding: const EdgeInsets.all(26),
        child: _Panel(
          title: title,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                detail,
                style: TextStyle(
                  color: LumenisTheme.of(context).muted,
                  height: 1.5,
                ),
              ),
              const SizedBox(height: 18),
              OutlinedButton(
                onPressed: onRetry,
                child: Text(_copy(context, '重新读取', 'Read again', '다시 읽기')),
              ),
            ],
          ),
        ),
      ),
    ),
  );
}

class _Panel extends StatelessWidget {
  const _Panel({required this.title, required this.child, this.detail});

  final String title;
  final String? detail;
  final Widget child;

  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    padding: const EdgeInsets.fromLTRB(16, 15, 16, 15),
    decoration: BoxDecoration(
      color: LumenisTheme.of(context).surface,
      border: Border.all(color: LumenisTheme.of(context).line),
      borderRadius: BorderRadius.circular(13),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
        ),
        if (detail != null) ...[
          const SizedBox(height: 4),
          Text(
            detail!,
            style: TextStyle(
              color: LumenisTheme.of(context).quiet,
              fontSize: 11,
              height: 1.45,
            ),
          ),
        ],
        const SizedBox(height: 12),
        child,
      ],
    ),
  );
}

class _DefinitionLine extends StatelessWidget {
  const _DefinitionLine({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 10),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 88,
          child: Text(
            label,
            style: TextStyle(
              color: LumenisTheme.of(context).quiet,
              fontSize: 11,
            ),
          ),
        ),
        Expanded(
          child: Text(
            value,
            style: const TextStyle(fontWeight: FontWeight.w600),
          ),
        ),
      ],
    ),
  );
}

class _MetaChip extends StatelessWidget {
  const _MetaChip(this.label);

  final String label;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
    decoration: BoxDecoration(
      color: LumenisTheme.of(context).canvas,
      borderRadius: BorderRadius.circular(7),
    ),
    child: Text(
      label,
      style: TextStyle(color: LumenisTheme.of(context).muted, fontSize: 11),
    ),
  );
}

class _InfoMessage extends StatelessWidget {
  const _InfoMessage(this.message);

  final String message;

  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 15),
    decoration: BoxDecoration(
      color: LumenisTheme.of(context).canvas,
      borderRadius: BorderRadius.circular(9),
    ),
    child: Text(
      message,
      style: TextStyle(color: LumenisTheme.of(context).muted, height: 1.45),
    ),
  );
}

class _Eyebrow extends StatelessWidget {
  const _Eyebrow(this.label);

  final String label;

  @override
  Widget build(BuildContext context) => Text(
    label,
    style: TextStyle(
      color: LumenisTheme.of(context).system,
      fontSize: 10,
      letterSpacing: 1.1,
      fontWeight: FontWeight.w700,
    ),
  );
}

String _copy(BuildContext context, String zh, String en, String ko) =>
    switch (context.lumenisL10n.locale.languageCode) {
      'en' => en,
      'ko' => ko,
      _ => zh,
    };
