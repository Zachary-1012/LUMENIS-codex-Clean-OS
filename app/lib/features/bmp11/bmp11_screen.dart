import 'package:flutter/material.dart';

import '../../core/lumenis_core_client.dart';
import '../../core/lumenis_theme.dart';
import '../../l10n/lumenis_localizations.dart';
import 'bmp11_repository.dart';
import 'bmp11_snapshot.dart';
import 'bmp11_view_model.dart';

class Bmp11Screen extends StatefulWidget {
  const Bmp11Screen({required this.client, this.repository, super.key});

  final LumenisCoreClient client;
  final Bmp11Repository? repository;

  @override
  State<Bmp11Screen> createState() => _Bmp11ScreenState();
}

class _Bmp11ScreenState extends State<Bmp11Screen> {
  late final Bmp11ViewModel _viewModel = Bmp11ViewModel(
    repository: widget.repository ?? CoreBmp11Repository(client: widget.client),
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
            Bmp11LoadPhase.loading => const _Loading(),
            Bmp11LoadPhase.failed => _Failure(
              kind: _viewModel.failureKind!,
              onRetry: _viewModel.refresh,
            ),
            Bmp11LoadPhase.ready => _BenchmarkDesk(
              snapshot: _viewModel.snapshot!,
              onRefresh: _viewModel.refresh,
            ),
          },
        ),
      ),
    );
  }
}

class _BenchmarkDesk extends StatelessWidget {
  const _BenchmarkDesk({required this.snapshot, required this.onRefresh});

  final Bmp11Snapshot snapshot;
  final VoidCallback onRefresh;

  @override
  Widget build(BuildContext context) {
    final copy = _Bmp11Copy.of(context);
    return LayoutBuilder(
      builder: (context, constraints) {
        final wide = constraints.maxWidth >= 1040;
        final padding = constraints.maxWidth >= 800 ? 32.0 : 18.0;
        final body = !snapshot.scopeApproved
            ? _Gate(snapshot: snapshot, copy: copy)
            : snapshot.rows.isEmpty
            ? _NoResults(copy: copy)
            : wide
            ? _DesktopBenchmark(snapshot: snapshot, copy: copy)
            : _MobileBenchmark(snapshot: snapshot, copy: copy);
        return Align(
          alignment: Alignment.topCenter,
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1320),
            child: SingleChildScrollView(
              padding: EdgeInsets.fromLTRB(padding, 28, padding, 44),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _Header(copy: copy, onRefresh: onRefresh),
                  const SizedBox(height: 26),
                  body,
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

  final _Bmp11Copy copy;
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
              context.lumenisL10n.text('screen.BMP-11'),
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

class _DesktopBenchmark extends StatelessWidget {
  const _DesktopBenchmark({required this.snapshot, required this.copy});

  final Bmp11Snapshot snapshot;
  final _Bmp11Copy copy;

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
        const SizedBox(height: 18),
        _BenchmarkGrid(
          rows: snapshot.rows,
          copy: copy,
          selfLabel: snapshot.scope.isGlobal ? copy.allBrands : copy.self,
        ),
        const SizedBox(height: 18),
        _DefinitionRail(rows: snapshot.rows, copy: copy),
        const SizedBox(height: 14),
        _SourceStrip(rows: snapshot.rows, copy: copy),
      ],
    );
  }
}

class _MobileBenchmark extends StatelessWidget {
  const _MobileBenchmark({required this.snapshot, required this.copy});

  final Bmp11Snapshot snapshot;
  final _Bmp11Copy copy;

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
        _MobileMetricList(
          rows: snapshot.rows,
          copy: copy,
          selfLabel: snapshot.scope.isGlobal ? copy.allBrands : copy.self,
        ),
        const SizedBox(height: 18),
        _SourceStrip(rows: snapshot.rows, copy: copy),
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
  final _Bmp11Copy copy;
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
          Icon(
            Icons.compare_arrows_rounded,
            color: LumenisTheme.of(context).bmp,
          ),
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
            copy.normalized,
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

class _BenchmarkGrid extends StatelessWidget {
  const _BenchmarkGrid({
    required this.rows,
    required this.copy,
    required this.selfLabel,
  });

  final List<Bmp11BenchmarkRow> rows;
  final _Bmp11Copy copy;
  final String selfLabel;

  @override
  Widget build(BuildContext context) {
    final competitors = <String>[];
    for (final row in rows) {
      for (final competitor in row.competitors) {
        if (!competitors.contains(competitor.name)) {
          competitors.add(competitor.name);
        }
      }
    }
    final tableWidth = 220.0 + 140.0 + competitors.length * 150.0;
    return DecoratedBox(
      decoration: BoxDecoration(
        color: LumenisTheme.of(context).surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: LumenisTheme.of(context).line),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(16),
        child: SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.all(18),
          child: SizedBox(
            width: tableWidth,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _GridHeader(
                  competitors: competitors,
                  copy: copy,
                  selfLabel: selfLabel,
                ),
                Divider(color: LumenisTheme.of(context).line, height: 22),
                for (final row in rows) ...[
                  _GridRow(row: row, competitors: competitors, copy: copy),
                  const SizedBox(height: 8),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _GridHeader extends StatelessWidget {
  const _GridHeader({
    required this.competitors,
    required this.copy,
    required this.selfLabel,
  });

  final List<String> competitors;
  final _Bmp11Copy copy;
  final String selfLabel;

  @override
  Widget build(BuildContext context) => Row(
    children: [
      SizedBox(
        width: 220,
        child: Text(copy.dimension, style: _headerStyle(context)),
      ),
      SizedBox(
        width: 140,
        child: Text(selfLabel, style: _headerStyle(context)),
      ),
      for (final competitor in competitors)
        SizedBox(
          width: 150,
          child: Text(competitor, style: _headerStyle(context)),
        ),
    ],
  );

  TextStyle _headerStyle(BuildContext context) => TextStyle(
    color: LumenisTheme.of(context).quiet,
    fontSize: 12,
    fontWeight: FontWeight.w600,
  );
}

class _GridRow extends StatelessWidget {
  const _GridRow({
    required this.row,
    required this.competitors,
    required this.copy,
  });

  final Bmp11BenchmarkRow row;
  final List<String> competitors;
  final _Bmp11Copy copy;

  @override
  Widget build(BuildContext context) {
    final comparable = row.comparable;
    return Semantics(
      container: true,
      label: row.dimension,
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: LumenisTheme.of(context).surfaceRaised,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: LumenisTheme.of(context).line),
        ),
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 13),
          child: Row(
            children: [
              SizedBox(
                width: 220,
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 13),
                  child: Text(
                    row.dimension,
                    style: TextStyle(
                      color: LumenisTheme.of(context).foreground,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ),
              SizedBox(
                width: 140,
                child: _ValueCell(
                  value: comparable ? row.selfValue : null,
                  withheldLabel: copy.withheld,
                  highlighted: true,
                ),
              ),
              for (final name in competitors)
                SizedBox(
                  width: 150,
                  child: _ValueCell(
                    value: comparable ? _valueFor(name) : null,
                    withheldLabel: copy.withheld,
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }

  num? _valueFor(String name) {
    for (final competitor in row.competitors) {
      if (competitor.name == name && competitor.comparable) {
        return competitor.value;
      }
    }
    return null;
  }
}

class _ValueCell extends StatelessWidget {
  const _ValueCell({
    required this.value,
    required this.withheldLabel,
    this.highlighted = false,
  });

  final num? value;
  final String withheldLabel;
  final bool highlighted;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(horizontal: 13),
    child: value == null
        ? Text(
            withheldLabel,
            style: TextStyle(
              color: LumenisTheme.of(context).quiet,
              fontSize: 12,
            ),
          )
        : Text(
            _formatNumber(value!),
            style: TextStyle(
              color: highlighted
                  ? LumenisTheme.of(context).foreground
                  : LumenisTheme.of(context).muted,
              fontWeight: highlighted ? FontWeight.w600 : FontWeight.w500,
              fontFeatures: const [FontFeature.tabularFigures()],
            ),
          ),
  );

  String _formatNumber(num value) {
    if (value == value.roundToDouble()) return value.toInt().toString();
    return value.toStringAsFixed(1);
  }
}

class _DefinitionRail extends StatelessWidget {
  const _DefinitionRail({required this.rows, required this.copy});

  final List<Bmp11BenchmarkRow> rows;
  final _Bmp11Copy copy;

  @override
  Widget build(BuildContext context) => DecoratedBox(
    decoration: BoxDecoration(
      color: LumenisTheme.of(context).surfaceRaised,
      borderRadius: BorderRadius.circular(16),
      border: Border.all(color: LumenisTheme.of(context).line),
    ),
    child: Padding(
      padding: const EdgeInsets.fromLTRB(20, 18, 20, 18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            copy.definitions,
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 13),
          for (final row in rows)
            Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  SizedBox(
                    width: 180,
                    child: Text(
                      row.dimension,
                      style: TextStyle(
                        color: LumenisTheme.of(context).foreground,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                  Expanded(
                    child: Text(
                      row.definition,
                      style: TextStyle(
                        color: LumenisTheme.of(context).muted,
                        height: 1.45,
                      ),
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

class _MobileMetricList extends StatelessWidget {
  const _MobileMetricList({
    required this.rows,
    required this.copy,
    required this.selfLabel,
  });

  final List<Bmp11BenchmarkRow> rows;
  final _Bmp11Copy copy;
  final String selfLabel;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(copy.comparison, style: Theme.of(context).textTheme.titleMedium),
      const SizedBox(height: 12),
      for (final row in rows)
        Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: _MobileMetric(row: row, copy: copy, selfLabel: selfLabel),
        ),
    ],
  );
}

class _MobileMetric extends StatelessWidget {
  const _MobileMetric({
    required this.row,
    required this.copy,
    required this.selfLabel,
  });

  final Bmp11BenchmarkRow row;
  final _Bmp11Copy copy;
  final String selfLabel;

  @override
  Widget build(BuildContext context) => DecoratedBox(
    decoration: BoxDecoration(
      color: LumenisTheme.of(context).surface,
      borderRadius: BorderRadius.circular(15),
      border: Border.all(color: LumenisTheme.of(context).line),
    ),
    child: Padding(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            row.dimension,
            style: TextStyle(
              color: LumenisTheme.of(context).foreground,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 7),
          Text(
            row.definition,
            style: TextStyle(
              color: LumenisTheme.of(context).muted,
              height: 1.4,
            ),
          ),
          const SizedBox(height: 15),
          if (!row.comparable)
            _Withheld(copy: copy)
          else ...[
            _MobileValueRow(
              label: selfLabel,
              value: row.selfValue,
              highlighted: true,
            ),
            for (final competitor in row.competitors)
              _MobileValueRow(
                label: competitor.name,
                value: competitor.comparable ? competitor.value : null,
                withheld: copy.withheld,
              ),
          ],
        ],
      ),
    ),
  );
}

class _MobileValueRow extends StatelessWidget {
  const _MobileValueRow({
    required this.label,
    required this.value,
    this.highlighted = false,
    this.withheld,
  });

  final String label;
  final num? value;
  final bool highlighted;
  final String? withheld;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 9),
    child: Row(
      children: [
        Expanded(
          child: Text(
            label,
            style: TextStyle(color: LumenisTheme.of(context).muted),
          ),
        ),
        Text(
          value == null ? withheld ?? '—' : _formatNumber(value!),
          style: TextStyle(
            color: highlighted
                ? LumenisTheme.of(context).foreground
                : LumenisTheme.of(context).muted,
            fontWeight: highlighted ? FontWeight.w600 : FontWeight.w500,
            fontFeatures: const [FontFeature.tabularFigures()],
          ),
        ),
      ],
    ),
  );

  String _formatNumber(num value) {
    if (value == value.roundToDouble()) return value.toInt().toString();
    return value.toStringAsFixed(1);
  }
}

class _Withheld extends StatelessWidget {
  const _Withheld({required this.copy});

  final _Bmp11Copy copy;

  @override
  Widget build(BuildContext context) => Semantics(
    liveRegion: true,
    child: Row(
      children: [
        Icon(
          Icons.remove_circle_outline,
          color: LumenisTheme.of(context).caution,
        ),
        const SizedBox(width: 9),
        Expanded(
          child: Text(
            copy.withheldDetail,
            style: TextStyle(
              color: LumenisTheme.of(context).caution,
              height: 1.4,
            ),
          ),
        ),
      ],
    ),
  );
}

class _SourceStrip extends StatelessWidget {
  const _SourceStrip({required this.rows, required this.copy});

  final List<Bmp11BenchmarkRow> rows;
  final _Bmp11Copy copy;

  @override
  Widget build(BuildContext context) {
    final hasComparable = rows.any((row) => row.hasComparableCompetitors);
    return DecoratedBox(
      decoration: BoxDecoration(
        color: LumenisTheme.of(context).surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: LumenisTheme.of(context).line),
      ),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(15, 13, 15, 13),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(
              hasComparable ? Icons.fact_check_outlined : Icons.info_outline,
              color: hasComparable
                  ? LumenisTheme.of(context).positive
                  : LumenisTheme.of(context).caution,
              size: 20,
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                hasComparable ? copy.sourceRequirement : copy.noComparable,
                style: TextStyle(
                  color: LumenisTheme.of(context).muted,
                  height: 1.45,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _NoResults extends StatelessWidget {
  const _NoResults({required this.copy});

  final _Bmp11Copy copy;

  @override
  Widget build(BuildContext context) => _NoticePanel(
    icon: Icons.compare_arrows_outlined,
    title: copy.noResultsTitle,
    detail: copy.noResultsDetail,
  );
}

class _Gate extends StatelessWidget {
  const _Gate({required this.snapshot, required this.copy});

  final Bmp11Snapshot snapshot;
  final _Bmp11Copy copy;

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

class _Loading extends StatelessWidget {
  const _Loading();

  @override
  Widget build(BuildContext context) => Center(
    child: Semantics(
      liveRegion: true,
      label: _Bmp11Copy.of(context).loading,
      child: Padding(
        padding: EdgeInsets.all(48),
        child: CircularProgressIndicator(color: LumenisTheme.of(context).bmp),
      ),
    ),
  );
}

class _Failure extends StatelessWidget {
  const _Failure({required this.kind, required this.onRetry});

  final Bmp11FailureKind kind;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final copy = _Bmp11Copy.of(context);
    final title = switch (kind) {
      Bmp11FailureKind.authentication => copy.signIn,
      Bmp11FailureKind.permissionDenied => copy.accessDenied,
      Bmp11FailureKind.offline => copy.offline,
      Bmp11FailureKind.server => copy.unavailableTitle,
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
              label: Text(copy.retry),
            ),
          ],
        ),
      ),
    );
  }
}

class _Bmp11Copy {
  _Bmp11Copy(this.languageCode);

  final String languageCode;

  static _Bmp11Copy of(BuildContext context) {
    final languageCode = Localizations.localeOf(context).languageCode;
    return _Bmp11Copy(
      languageCode == 'en' || languageCode == 'ko' ? languageCode : 'zh-CN',
    );
  }

  String get subtitle => _get('subtitle');
  String get refresh => _get('refresh');
  String get focus => _get('focus');
  String get globalRange => _get('globalRange');
  String get allBrands => _get('allBrands');
  String get brandUnknown => _get('brandUnknown');
  String get normalized => _get('normalized');
  String get dimension => _get('dimension');
  String get self => _get('self');
  String get definitions => _get('definitions');
  String get comparison => _get('comparison');
  String get withheld => _get('withheld');
  String get withheldDetail => _get('withheldDetail');
  String get sourceRequirement => _get('sourceRequirement');
  String get noComparable => _get('noComparable');
  String get noResultsTitle => _get('noResultsTitle');
  String get noResultsDetail => _get('noResultsDetail');
  String get unavailableTitle => _get('unavailableTitle');
  String get unavailableDetail => _get('unavailableDetail');
  String get notCollectedTitle => _get('notCollectedTitle');
  String get notCollectedDetail => _get('notCollectedDetail');
  String get loading => _get('loading');
  String get signIn => _get('signIn');
  String get accessDenied => _get('accessDenied');
  String get offline => _get('offline');
  String get retryDetail => _get('retryDetail');
  String get retry => _get('retry');

  String _get(String key) =>
      _values[languageCode]?[key] ?? _values['zh-CN']![key]!;

  static const _values = <String, Map<String, String>>{
    'zh-CN': {
      'subtitle': '用同一套指标定义比较品牌表现；不能对齐的项目保留待核状态，不强行排名。',
      'refresh': '刷新基准',
      'focus': '比较范围',
      'globalRange': '全球品牌范围',
      'allBrands': '已授权的全球品牌集合',
      'brandUnknown': '品牌名称暂不可用',
      'normalized': '定义已对齐',
      'dimension': '比较维度',
      'self': '当前品牌',
      'definitions': '指标定义',
      'comparison': '品牌对比',
      'withheld': '暂不展示',
      'withheldDetail': '该项目的定义或记录来源尚未对齐，暂不比较。',
      'sourceRequirement': '可见数值均来自同一指标定义，并且保留了对应的记录来源。',
      'noComparable': '当前项目还没有可对齐的比较结果；不把缺失值当作零，也不生成排名。',
      'noResultsTitle': '还没有可用的品牌基准',
      'noResultsDetail': '品牌基准需要同一指标定义、已记录的结果和可追溯的来源；准备好后这里才会显示比较。',
      'unavailableTitle': '品牌基准暂不可用',
      'unavailableDetail': '当前品牌范围或比较结果尚未确认，不展示其他范围的数据，也不把缺失指标当作零。',
      'notCollectedTitle': '还没有收集到品牌基准',
      'notCollectedDetail': '对齐的结果与来源准备好后，才能形成品牌之间的可比基准。',
      'loading': '正在加载品牌基准',
      'signIn': '需要登录后查看品牌基准',
      'accessDenied': '当前账号暂时无法查看品牌基准',
      'offline': '暂时无法连接品牌基准服务',
      'retryDetail': '请检查连接后重试；未经确认的比较不会显示。',
      'retry': '重试',
    },
    'en': {
      'subtitle':
          'Compare brand performance with one metric definition; leave unaligned items pending instead of forcing a rank.',
      'refresh': 'Refresh benchmark',
      'focus': 'Comparison range',
      'globalRange': 'Global brand range',
      'allBrands': 'Authorized global brand set',
      'brandUnknown': 'Brand name unavailable',
      'normalized': 'Definitions aligned',
      'dimension': 'Comparison dimension',
      'self': 'Current brand',
      'definitions': 'Metric definitions',
      'comparison': 'Brand comparison',
      'withheld': 'Not shown yet',
      'withheldDetail':
          'The definition or recorded source is not aligned for this item, so it is not compared.',
      'sourceRequirement':
          'Visible values use one metric definition and retain their recorded source.',
      'noComparable':
          'No aligned comparison is ready. Missing values are not treated as zero and no rank is invented.',
      'noResultsTitle': 'No brand benchmark is ready',
      'noResultsDetail':
          'A benchmark needs one metric definition, recorded results and traceable sources before comparison appears.',
      'unavailableTitle': 'Brand benchmark is unavailable',
      'unavailableDetail':
          'The current brand range or comparison result is not confirmed. Other ranges stay hidden and missing metrics are not zero.',
      'notCollectedTitle': 'No brand benchmark has been collected',
      'notCollectedDetail':
          'Aligned results and sources are required before a comparable brand benchmark can be formed.',
      'loading': 'Loading brand benchmark',
      'signIn': 'Sign in to view the brand benchmark',
      'accessDenied': 'This account cannot view the brand benchmark right now',
      'offline': 'Brand benchmark service is unavailable',
      'retryDetail':
          'Check the connection and try again. Unconfirmed comparisons stay hidden.',
      'retry': 'Try again',
    },
    'ko': {
      'subtitle': '하나의 지표 정의로 브랜드 성과를 비교하고, 맞지 않는 항목은 순위를 강요하지 않고 대기 상태로 둡니다.',
      'refresh': '벤치마크 새로고침',
      'focus': '비교 범위',
      'globalRange': '글로벌 브랜드 범위',
      'allBrands': '승인된 글로벌 브랜드 집합',
      'brandUnknown': '브랜드 이름을 사용할 수 없습니다',
      'normalized': '정의가 정렬됨',
      'dimension': '비교 차원',
      'self': '현재 브랜드',
      'definitions': '지표 정의',
      'comparison': '브랜드 비교',
      'withheld': '아직 표시하지 않음',
      'withheldDetail': '이 항목의 정의 또는 기록된 출처가 정렬되지 않아 비교하지 않습니다.',
      'sourceRequirement': '표시되는 값은 하나의 지표 정의를 사용하며 기록된 출처를 보존합니다.',
      'noComparable': '정렬된 비교 결과가 없습니다. 누락 값을 0으로 처리하거나 순위를 만들지 않습니다.',
      'noResultsTitle': '사용할 수 있는 브랜드 벤치마크가 없습니다',
      'noResultsDetail': '비교를 표시하려면 하나의 지표 정의, 기록된 결과와 추적 가능한 출처가 필요합니다.',
      'unavailableTitle': '브랜드 벤치마크를 사용할 수 없습니다',
      'unavailableDetail':
          '현재 브랜드 범위 또는 비교 결과가 확인되지 않았습니다. 다른 범위의 데이터와 누락 지표를 0으로 표시하지 않습니다.',
      'notCollectedTitle': '브랜드 벤치마크가 수집되지 않았습니다',
      'notCollectedDetail': '비교 가능한 브랜드 벤치마크에는 정렬된 결과와 출처가 필요합니다.',
      'loading': '브랜드 벤치마크를 불러오는 중',
      'signIn': '브랜드 벤치마크를 보려면 로그인하세요',
      'accessDenied': '이 계정은 지금 브랜드 벤치마크를 볼 수 없습니다',
      'offline': '브랜드 벤치마크 서비스에 연결할 수 없습니다',
      'retryDetail': '연결을 확인하고 다시 시도하세요. 확인되지 않은 비교는 숨겨집니다.',
      'retry': '다시 시도',
    },
  };
}
