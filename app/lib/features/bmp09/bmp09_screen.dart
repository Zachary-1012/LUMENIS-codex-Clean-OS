import 'package:flutter/material.dart';

import '../../core/lumenis_core_client.dart';
import '../../core/lumenis_theme.dart';
import '../../l10n/lumenis_localizations.dart';
import 'bmp09_repository.dart';
import 'bmp09_snapshot.dart';
import 'bmp09_view_model.dart';

class Bmp09Screen extends StatefulWidget {
  const Bmp09Screen({required this.client, this.repository, super.key});

  final LumenisCoreClient client;
  final Bmp09Repository? repository;

  @override
  State<Bmp09Screen> createState() => _Bmp09ScreenState();
}

class _Bmp09ScreenState extends State<Bmp09Screen> {
  late final Bmp09ViewModel _viewModel = Bmp09ViewModel(
    repository: widget.repository ?? CoreBmp09Repository(client: widget.client),
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
            Bmp09LoadPhase.loading => const _Loading(),
            Bmp09LoadPhase.failed => _Failure(
              kind: _viewModel.failureKind!,
              onRetry: _viewModel.refresh,
            ),
            Bmp09LoadPhase.ready => _EvaluationDesk(
              snapshot: _viewModel.snapshot!,
              actionState: _viewModel.actionState,
              onRefresh: _viewModel.refresh,
              onGenerateReport: _viewModel.stageReportRequest,
            ),
          },
        ),
      ),
    );
  }
}

class _EvaluationDesk extends StatelessWidget {
  const _EvaluationDesk({
    required this.snapshot,
    required this.actionState,
    required this.onRefresh,
    required this.onGenerateReport,
  });

  final Bmp09Snapshot snapshot;
  final Bmp09ActionState actionState;
  final VoidCallback onRefresh;
  final VoidCallback onGenerateReport;

  @override
  Widget build(BuildContext context) {
    final copy = _Bmp09Copy.of(context);
    return LayoutBuilder(
      builder: (context, constraints) {
        final wide = constraints.maxWidth >= 1020;
        final padding = constraints.maxWidth >= 800 ? 32.0 : 18.0;
        final body = !snapshot.scopeApproved
            ? _Gate(snapshot: snapshot, copy: copy)
            : snapshot.dimensions.isEmpty
            ? _NoResults(copy: copy)
            : wide
            ? _DesktopEvaluation(snapshot: snapshot, copy: copy)
            : _MobileEvaluation(snapshot: snapshot, copy: copy);
        return Align(
          alignment: Alignment.topCenter,
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1280),
            child: SingleChildScrollView(
              padding: EdgeInsets.fromLTRB(padding, 28, padding, 40),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _Header(copy: copy, onRefresh: onRefresh),
                  const SizedBox(height: 26),
                  body,
                  const SizedBox(height: 22),
                  _ReportAction(
                    copy: copy,
                    state: actionState,
                    onGenerateReport: onGenerateReport,
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

  final _Bmp09Copy copy;
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
              context.lumenisL10n.text('screen.BMP-09'),
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

class _DesktopEvaluation extends StatelessWidget {
  const _DesktopEvaluation({required this.snapshot, required this.copy});

  final Bmp09Snapshot snapshot;
  final _Bmp09Copy copy;

  @override
  Widget build(BuildContext context) {
    final scopeLabel = snapshot.scope.isGlobal ? copy.globalRange : copy.focus;
    final brand =
        snapshot.scope.localizedName(copy.languageCode) ??
        (snapshot.scope.isGlobal ? copy.allBrands : copy.brandUnknown);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _FocusLine(brand: brand, copy: copy, scopeLabel: scopeLabel),
        const SizedBox(height: 16),
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              flex: 7,
              child: _ScoreMatrix(dimensions: snapshot.dimensions, copy: copy),
            ),
            const SizedBox(width: 18),
            Expanded(
              flex: 4,
              child: _ReportShelf(reports: snapshot.reports, copy: copy),
            ),
          ],
        ),
      ],
    );
  }
}

class _MobileEvaluation extends StatelessWidget {
  const _MobileEvaluation({required this.snapshot, required this.copy});

  final Bmp09Snapshot snapshot;
  final _Bmp09Copy copy;

  @override
  Widget build(BuildContext context) {
    final scopeLabel = snapshot.scope.isGlobal ? copy.globalRange : copy.focus;
    final brand =
        snapshot.scope.localizedName(copy.languageCode) ??
        (snapshot.scope.isGlobal ? copy.allBrands : copy.brandUnknown);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _FocusLine(brand: brand, copy: copy, scopeLabel: scopeLabel),
        const SizedBox(height: 14),
        _DimensionList(dimensions: snapshot.dimensions, copy: copy),
        const SizedBox(height: 14),
        _ReportShelf(reports: snapshot.reports, copy: copy),
      ],
    );
  }
}

class _FocusLine extends StatelessWidget {
  const _FocusLine({
    required this.brand,
    required this.copy,
    required this.scopeLabel,
  });

  final String brand;
  final _Bmp09Copy copy;
  final String scopeLabel;

  @override
  Widget build(BuildContext context) => DecoratedBox(
    decoration: BoxDecoration(
      border: Border(bottom: BorderSide(color: LumenisTheme.of(context).line)),
    ),
    child: Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        children: [
          Icon(Icons.insights_outlined, color: LumenisTheme.of(context).bmp),
          const SizedBox(width: 10),
          Text(
            scopeLabel,
            style: TextStyle(color: LumenisTheme.of(context).quiet),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              brand,
              style: TextStyle(
                color: LumenisTheme.of(context).foreground,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          Text(
            copy.actualOnly,
            style: TextStyle(
              color: LumenisTheme.of(context).quiet,
              fontSize: 11,
            ),
          ),
        ],
      ),
    ),
  );
}

class _ScoreMatrix extends StatelessWidget {
  const _ScoreMatrix({required this.dimensions, required this.copy});

  final List<Bmp09Dimension> dimensions;
  final _Bmp09Copy copy;

  @override
  Widget build(BuildContext context) => DecoratedBox(
    decoration: BoxDecoration(
      color: LumenisTheme.of(context).surface,
      borderRadius: BorderRadius.circular(16),
      border: Border.all(color: LumenisTheme.of(context).line),
    ),
    child: Padding(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(copy.scorecard, style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 15),
          for (final dimension in dimensions)
            _DimensionRow(dimension: dimension, copy: copy),
        ],
      ),
    ),
  );
}

class _DimensionList extends StatelessWidget {
  const _DimensionList({required this.dimensions, required this.copy});

  final List<Bmp09Dimension> dimensions;
  final _Bmp09Copy copy;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(copy.scorecard, style: Theme.of(context).textTheme.titleMedium),
      const SizedBox(height: 12),
      for (final dimension in dimensions)
        Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: _DimensionRow(dimension: dimension, copy: copy),
        ),
    ],
  );
}

class _DimensionRow extends StatelessWidget {
  const _DimensionRow({required this.dimension, required this.copy});

  final Bmp09Dimension dimension;
  final _Bmp09Copy copy;

  @override
  Widget build(BuildContext context) {
    final score = dimension.score.toString();
    final details =
        '${copy.movement(dimension.movement)} · '
        '${copy.confidence(dimension.confidence)} · '
        '${copy.coverage(dimension.evidenceCoverage)}';
    return DecoratedBox(
      decoration: BoxDecoration(
        color: LumenisTheme.of(context).surfaceRaised,
        borderRadius: BorderRadius.circular(13),
        border: Border.all(color: LumenisTheme.of(context).line),
      ),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(15, 14, 15, 13),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    dimension.name,
                    style: TextStyle(
                      color: LumenisTheme.of(context).foreground,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 7),
                  Text(
                    details,
                    style: TextStyle(
                      color: LumenisTheme.of(context).muted,
                      fontSize: 11,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 14),
            Text(
              score,
              style: TextStyle(
                color: LumenisTheme.of(context).foreground,
                fontSize: 21,
                fontWeight: FontWeight.w600,
                fontFeatures: [FontFeature.tabularFigures()],
              ),
            ),
            const SizedBox(width: 8),
            Icon(
              _movementIcon(dimension.movement),
              size: 19,
              color: _movementColor(context, dimension.movement),
            ),
          ],
        ),
      ),
    );
  }

  IconData _movementIcon(String movement) => switch (movement) {
    'UP' => Icons.trending_up_rounded,
    'DOWN' => Icons.trending_down_rounded,
    _ => Icons.trending_flat_rounded,
  };

  Color _movementColor(BuildContext context, String movement) =>
      switch (movement) {
        'UP' => LumenisTheme.of(context).positive,
        'DOWN' => LumenisTheme.of(context).caution,
        _ => LumenisTheme.of(context).muted,
      };
}

class _ReportShelf extends StatelessWidget {
  const _ReportShelf({required this.reports, required this.copy});

  final List<Bmp09Report> reports;
  final _Bmp09Copy copy;

  @override
  Widget build(BuildContext context) => DecoratedBox(
    decoration: BoxDecoration(
      color: LumenisTheme.of(context).surfaceRaised,
      borderRadius: BorderRadius.circular(16),
      border: Border.all(color: LumenisTheme.of(context).line),
    ),
    child: Padding(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(copy.reports, style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 14),
          if (reports.isEmpty)
            Text(
              copy.noReports,
              style: TextStyle(
                color: LumenisTheme.of(context).muted,
                height: 1.5,
              ),
            )
          else
            for (final report in reports)
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: Icon(
                  Icons.description_outlined,
                  color: LumenisTheme.of(context).bmp,
                ),
                title: Text(
                  report.title,
                  style: TextStyle(color: LumenisTheme.of(context).foreground),
                ),
                subtitle: Text(
                  report.period,
                  style: TextStyle(color: LumenisTheme.of(context).muted),
                ),
              ),
        ],
      ),
    ),
  );
}

class _NoResults extends StatelessWidget {
  const _NoResults({required this.copy});

  final _Bmp09Copy copy;

  @override
  Widget build(BuildContext context) => _NoticePanel(
    icon: Icons.query_stats_outlined,
    title: copy.noResultsTitle,
    detail: copy.noResultsDetail,
  );
}

class _Gate extends StatelessWidget {
  const _Gate({required this.snapshot, required this.copy});

  final Bmp09Snapshot snapshot;
  final _Bmp09Copy copy;

  @override
  Widget build(BuildContext context) => _NoticePanel(
    icon: snapshot.dataState == 'NOT_COLLECTED'
        ? Icons.hourglass_empty_rounded
        : Icons.lock_outline_rounded,
    title: snapshot.dataState == 'NOT_COLLECTED'
        ? copy.notCollectedTitle
        : copy.unavailableTitle,
    detail: snapshot.dataState == 'NOT_COLLECTED'
        ? copy.notCollectedDetail
        : copy.unavailableDetail,
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

class _ReportAction extends StatelessWidget {
  const _ReportAction({
    required this.copy,
    required this.state,
    required this.onGenerateReport,
  });

  final _Bmp09Copy copy;
  final Bmp09ActionState state;
  final VoidCallback onGenerateReport;

  @override
  Widget build(BuildContext context) {
    final notice = switch (state) {
      Bmp09ActionState.idle => null,
      Bmp09ActionState.blocked => copy.actionBlocked,
      Bmp09ActionState.staged => copy.actionStaged,
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
                color: state == Bmp09ActionState.staged
                    ? LumenisTheme.of(context).positive
                    : LumenisTheme.of(context).caution,
              ),
            ),
          ),
          const SizedBox(height: 12),
        ],
        FilledButton.icon(
          onPressed: onGenerateReport,
          icon: const Icon(Icons.assignment_outlined),
          label: Text(copy.generateReport),
        ),
        const SizedBox(height: 9),
        Text(
          copy.reportGuard,
          style: TextStyle(color: LumenisTheme.of(context).quiet, fontSize: 12),
        ),
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
      label: _Bmp09Copy.of(context).loading,
      child: Padding(
        padding: EdgeInsets.all(48),
        child: CircularProgressIndicator(color: LumenisTheme.of(context).bmp),
      ),
    ),
  );
}

class _Failure extends StatelessWidget {
  const _Failure({required this.kind, required this.onRetry});

  final Bmp09FailureKind kind;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final copy = _Bmp09Copy.of(context);
    final title = switch (kind) {
      Bmp09FailureKind.authentication => copy.signIn,
      Bmp09FailureKind.permissionDenied => copy.accessDenied,
      Bmp09FailureKind.offline => copy.offline,
      Bmp09FailureKind.server => copy.unavailableTitle,
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

class _Bmp09Copy {
  _Bmp09Copy(this.languageCode);

  final String languageCode;

  static _Bmp09Copy of(BuildContext context) {
    final languageCode = Localizations.localeOf(context).languageCode;
    return _Bmp09Copy(
      languageCode == 'en' || languageCode == 'ko' ? languageCode : 'zh-CN',
    );
  }

  String get subtitle => _get('subtitle');
  String get refresh => _get('refresh');
  String get focus => _get('focus');
  String get globalRange => _get('globalRange');
  String get allBrands => _get('allBrands');
  String get brandUnknown => _get('brandUnknown');
  String get actualOnly => _get('actualOnly');
  String get scorecard => _get('scorecard');
  String get reports => _get('reports');
  String get noReports => _get('noReports');
  String get noResultsTitle => _get('noResultsTitle');
  String get noResultsDetail => _get('noResultsDetail');
  String get unavailableTitle => _get('unavailableTitle');
  String get unavailableDetail => _get('unavailableDetail');
  String get notCollectedTitle => _get('notCollectedTitle');
  String get notCollectedDetail => _get('notCollectedDetail');
  String get actionBlocked => _get('actionBlocked');
  String get actionStaged => _get('actionStaged');
  String get reportGuard => _get('reportGuard');
  String get loading => _get('loading');
  String get signIn => _get('signIn');
  String get accessDenied => _get('accessDenied');
  String get offline => _get('offline');
  String get retryDetail => _get('retryDetail');
  String get generateReport => _get('generateReport');

  String movement(String value) => _get('movement.$value');
  String confidence(String value) => _get('confidence.$value');
  String coverage(String value) => _get('coverage.$value');

  String _get(String key) =>
      _values[languageCode]?[key] ?? _values['zh-CN']![key]!;

  static const _values = <String, Map<String, String>>{
    'zh-CN': {
      'subtitle': '只从已记录的真实结果建立品牌评估，让分数、变化、可信度和来源彼此对得上。',
      'refresh': '刷新评估',
      'focus': '当前品牌',
      'globalRange': '全球品牌范围',
      'allBrands': '已授权的全球品牌集合',
      'brandUnknown': '品牌名称暂不可用',
      'actualOnly': '仅展示实际结果',
      'scorecard': '品牌评估矩阵',
      'reports': '评估报告',
      'noReports': '当前品牌还没有可查看的评估报告。',
      'noResultsTitle': '还没有可评估的真实结果',
      'noResultsDetail': '评估不会用主观生成内容补齐分数。实际结果与来源准备好后，这里会显示维度变化。',
      'unavailableTitle': '品牌评估暂不可用',
      'unavailableDetail': '当前品牌范围或评估来源尚未确认，不展示其他品牌的分数，也不把缺失指标当作零分。',
      'notCollectedTitle': '还没有评估结果',
      'notCollectedDetail': '真实结果、对齐的周期与来源准备好后，才能形成品牌评估。',
      'actionBlocked': '当前范围还不能生成评估报告；请先确认品牌范围与报告授权。',
      'actionStaged': '本地评估报告请求草稿已保存；尚未生成或写入任何报告。',
      'reportGuard': '这里仅保存本地评估报告草稿；在真实、确认的结果返回前，不会生成或写入报告。',
      'loading': '正在加载品牌评估',
      'signIn': '当前内容暂时无法打开',
      'accessDenied': '当前内容不可访问',
      'offline': '暂时无法连接评估服务',
      'retryDetail': '可重试读取，或返回后稍后再试。',
      'generateReport': '保存评估报告草稿',
      'movement.UP': '较上期上升',
      'movement.DOWN': '较上期下降',
      'movement.FLAT': '较上期持平',
      'confidence.HIGH': '高可信',
      'confidence.MEDIUM': '中可信',
      'confidence.LOW': '低可信',
      'coverage.FULL': '来源完整',
      'coverage.PARTIAL': '来源部分完整',
    },
    'en': {
      'subtitle':
          'Build the brand evaluation from recorded actual results so score, movement, confidence and source agree.',
      'refresh': 'Refresh evaluation',
      'focus': 'Brand focus',
      'globalRange': 'Global brand range',
      'allBrands': 'Authorized global brand set',
      'brandUnknown': 'Brand name unavailable',
      'actualOnly': 'Actual results only',
      'scorecard': 'Brand evaluation matrix',
      'reports': 'Evaluation reports',
      'noReports': 'No evaluation reports are available for this brand.',
      'noResultsTitle': 'No actual result is ready for evaluation',
      'noResultsDetail':
          'A subjective generated answer never fills a score. Dimensions appear when actual results and sources are ready.',
      'unavailableTitle': 'Brand evaluation is unavailable',
      'unavailableDetail':
          'The current brand range or evaluation source is not confirmed. Scores from another brand stay hidden and missing values are not zero.',
      'notCollectedTitle': 'No evaluation result has been collected',
      'notCollectedDetail':
          'Actual results, aligned periods and sources are required before a brand evaluation can be formed.',
      'actionBlocked':
          'A report cannot be requested in the current brand range or authorization state.',
      'actionStaged':
          'Local evaluation-report draft saved. No report was generated or written.',
      'reportGuard':
          'Only a local evaluation-report draft is saved here; no report is generated or written until real, confirmed results are returned.',
      'loading': 'Loading brand evaluation',
      'signIn': 'This content cannot be opened right now.',
      'accessDenied': 'This content is not accessible.',
      'offline': 'Evaluation service is unavailable',
      'retryDetail': 'You can retry reading it or return and try again later.',
      'generateReport': 'Save evaluation-report draft',
      'movement.UP': 'Up from prior period',
      'movement.DOWN': 'Down from prior period',
      'movement.FLAT': 'Flat from prior period',
      'confidence.HIGH': 'High confidence',
      'confidence.MEDIUM': 'Medium confidence',
      'confidence.LOW': 'Low confidence',
      'coverage.FULL': 'Full source coverage',
      'coverage.PARTIAL': 'Partial source coverage',
    },
    'ko': {
      'subtitle': '기록된 실제 결과만으로 브랜드를 평가하여 점수, 변화, 신뢰도와 출처를 맞춥니다.',
      'refresh': '평가 새로고침',
      'focus': '현재 브랜드',
      'globalRange': '글로벌 브랜드 범위',
      'allBrands': '승인된 글로벌 브랜드 집합',
      'brandUnknown': '브랜드 이름을 사용할 수 없습니다',
      'actualOnly': '실제 결과만',
      'scorecard': '브랜드 평가 매트릭스',
      'reports': '평가 보고서',
      'noReports': '이 브랜드에서 확인할 평가 보고서가 없습니다.',
      'noResultsTitle': '평가할 실제 결과가 없습니다',
      'noResultsDetail':
          '주관적인 생성 답변으로 점수를 채우지 않습니다. 실제 결과와 출처가 준비되면 차원이 표시됩니다.',
      'unavailableTitle': '브랜드 평가를 사용할 수 없습니다',
      'unavailableDetail':
          '현재 브랜드 범위 또는 평가 출처가 확인되지 않았습니다. 다른 브랜드 점수와 누락 값을 0으로 표시하지 않습니다.',
      'notCollectedTitle': '아직 평가 결과가 수집되지 않았습니다',
      'notCollectedDetail': '브랜드 평가에는 실제 결과, 정렬된 기간과 출처가 필요합니다.',
      'actionBlocked': '현재 브랜드 범위 또는 권한 상태에서는 보고서를 요청할 수 없습니다.',
      'actionStaged': '로컬 평가 보고서 요청 초안을 저장했습니다. 보고서를 생성하거나 기록하지 않았습니다.',
      'reportGuard':
          '여기서는 로컬 평가 보고서 초안만 저장합니다. 실제로 확인된 결과가 반환되기 전에는 보고서를 생성하거나 기록하지 않습니다.',
      'loading': '브랜드 평가를 불러오는 중',
      'signIn': '현재 콘텐츠를 지금 열 수 없습니다.',
      'accessDenied': '현재 콘텐츠에 접근할 수 없습니다.',
      'offline': '평가 서비스에 연결할 수 없습니다',
      'retryDetail': '다시 읽기를 시도하거나 돌아간 뒤 나중에 다시 시도할 수 있습니다.',
      'generateReport': '평가 보고서 초안 저장',
      'movement.UP': '이전 기간보다 상승',
      'movement.DOWN': '이전 기간보다 하락',
      'movement.FLAT': '이전 기간과 동일',
      'confidence.HIGH': '높은 신뢰도',
      'confidence.MEDIUM': '중간 신뢰도',
      'confidence.LOW': '낮은 신뢰도',
      'coverage.FULL': '출처 전체 확인',
      'coverage.PARTIAL': '출처 일부 확인',
    },
  };
}
