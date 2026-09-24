import 'package:flutter/material.dart';

import '../../../core/lumenis_core_client.dart';
import '../../../core/lumenis_theme.dart';
import '../../../l10n/lumenis_localizations.dart';
import 'sh04_repository.dart';
import 'sh04_snapshot.dart';
import 'sh04_view_model.dart';

class Sh04Screen extends StatefulWidget {
  const Sh04Screen({required this.client, this.repository, super.key});

  final LumenisCoreClient client;
  final Sh04Repository? repository;

  @override
  State<Sh04Screen> createState() => _Sh04ScreenState();
}

class _Sh04ScreenState extends State<Sh04Screen> {
  late final Sh04ViewModel _viewModel = Sh04ViewModel(
    repository: widget.repository ?? CoreSh04Repository(client: widget.client),
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
          Sh04LoadPhase.loading => _LoadingState(),
          Sh04LoadPhase.blocked => _BlockedState(
            error: _viewModel.scopeError,
            onRetry: _viewModel.refresh,
          ),
          Sh04LoadPhase.failed => _FailureState(
            kind: _viewModel.failureKind!,
            onRetry: _viewModel.refresh,
          ),
          Sh04LoadPhase.ready => _Workspace(viewModel: _viewModel),
        },
      ),
    ),
  );
}

class _Workspace extends StatelessWidget {
  const _Workspace({required this.viewModel});

  final Sh04ViewModel viewModel;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, constraints) {
      final wide = constraints.maxWidth >= 1120;
      final snapshot = viewModel.snapshot!;
      final queue = _ExportQueue(viewModel: viewModel);
      final inspector = _ArtifactInspector(exportItem: viewModel.selected);
      return Align(
        alignment: Alignment.topCenter,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1480),
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
                      SizedBox(width: 390, child: queue),
                      const SizedBox(width: 16),
                      Expanded(child: inspector),
                    ],
                  )
                else
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [queue, const SizedBox(height: 14), inspector],
                  ),
                const SizedBox(height: 14),
                _ReadOnlyExportNote(),
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
      _Eyebrow(_copy(context, '可回溯成果', 'REOPENABLE OUTPUT', '다시 열 수 있는 결과물')),
      const SizedBox(height: 9),
      Text(
        context.lumenisL10n.text('screen.SH-04'),
        style: Theme.of(context).textTheme.headlineMedium?.copyWith(
          color: LumenisTheme.of(context).foreground,
          fontWeight: FontWeight.w600,
        ),
      ),
      const SizedBox(height: 6),
      Text(
        _copy(
          context,
          '先确认精确范围，再查看已生成并可重新打开的成果；没有真实成果时不提供假下载。',
          'Confirm the exact range first, then inspect generated and reopenable outputs. No fake download is offered.',
          '먼저 정확한 범위를 확인한 뒤 생성되어 다시 열 수 있는 결과물을 확인합니다. 실제 결과물이 없으면 다운로드를 가장하지 않습니다.',
        ),
        style: TextStyle(color: LumenisTheme.of(context).muted, height: 1.45),
      ),
    ],
  );
}

class _ScopeBanner extends StatelessWidget {
  const _ScopeBanner({required this.scope});

  final Sh04Scope scope;

  @override
  Widget build(BuildContext context) {
    final range = scope.isGlobal
        ? _copy(context, '全部范围', 'All scopes', '전체 범위')
        : '${scope.businessDomain} · ${scope.displayName}';
    return Semantics(
      liveRegion: true,
      label: _copy(
        context,
        '当前成果范围：$range',
        'Current output range: $range',
        '현재 결과 범위: $range',
      ),
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(horizontal: 15, vertical: 12),
        decoration: BoxDecoration(
          color: LumenisTheme.of(context).accentStrong.withValues(alpha: 0.08),
          border: Border.all(
            color: LumenisTheme.of(
              context,
            ).accentStrong.withValues(alpha: 0.35),
          ),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Row(
          children: [
            Icon(
              Icons.lock_outline_rounded,
              color: LumenisTheme.of(context).accentStrong,
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
              _copy(context, '精确范围已确认', 'Exact range confirmed', '정확한 범위 확인됨'),
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

class _ExportQueue extends StatelessWidget {
  const _ExportQueue({required this.viewModel});

  final Sh04ViewModel viewModel;

  @override
  Widget build(BuildContext context) {
    final items = viewModel.exports;
    return _Panel(
      title: _copy(context, '成果队列', 'Output queue', '결과물 대기열'),
      detail: _copy(
        context,
        '区分草稿、生成中、已完成和失败。',
        'Separate drafts, running, completed and failed outputs.',
        '초안·생성 중·완료·실패 결과를 구분합니다.',
      ),
      child: items.isEmpty
          ? _InfoMessage(
              _copy(
                context,
                '当前范围没有可查看的成果。',
                'There are no outputs to inspect for this range.',
                '현재 범위에 확인할 결과물이 없습니다.',
              ),
            )
          : Column(
              children: [
                for (final item in items)
                  _ExportRow(
                    item: item,
                    selected: viewModel.selected?.internalId == item.internalId,
                    onTap: () => viewModel.select(item),
                  ),
              ],
            ),
    );
  }
}

class _ExportRow extends StatelessWidget {
  const _ExportRow({
    required this.item,
    required this.selected,
    required this.onTap,
  });

  final Sh04Export item;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 8),
    child: Material(
      color: selected
          ? LumenisTheme.of(context).accentStrong.withValues(alpha: 0.1)
          : LumenisTheme.of(context).surfaceRaised,
      borderRadius: BorderRadius.circular(10),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(10),
        child: Container(
          constraints: const BoxConstraints(minHeight: 78),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          decoration: BoxDecoration(
            border: Border.all(
              color: selected
                  ? LumenisTheme.of(
                      context,
                    ).accentStrong.withValues(alpha: 0.55)
                  : LumenisTheme.of(context).line,
            ),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(
                _formatIcon(item.format),
                color: selected
                    ? LumenisTheme.of(context).accentStrong
                    : LumenisTheme.of(context).quiet,
                size: 19,
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      item.title,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontWeight: FontWeight.w600),
                    ),
                    const SizedBox(height: 6),
                    Wrap(
                      spacing: 8,
                      runSpacing: 4,
                      children: [
                        Text(
                          item.formatLabel,
                          style: TextStyle(
                            color: LumenisTheme.of(context).muted,
                            fontSize: 11,
                          ),
                        ),
                        _StateTag(
                          item.stateLabel,
                          color: _stateColor(context, item.state),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 6),
              Icon(
                selected
                    ? Icons.chevron_right_rounded
                    : Icons.visibility_outlined,
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

class _ArtifactInspector extends StatelessWidget {
  const _ArtifactInspector({required this.exportItem});

  final Sh04Export? exportItem;

  @override
  Widget build(BuildContext context) {
    final item = exportItem;
    return _Panel(
      title: _copy(context, '成果预览', 'Output preview', '결과물 미리보기'),
      detail: _copy(
        context,
        '只有范围相符且可重新打开的成果才会显示内容。',
        'Only outputs matching the exact range and marked reopenable show content.',
        '정확한 범위와 다시 열기 상태가 확인된 결과만 내용을 표시합니다.',
      ),
      child: item == null
          ? _InfoMessage(
              _copy(
                context,
                '选择一个成果查看状态。',
                'Select an output to inspect its state.',
                '결과물을 선택해 상태를 확인하세요.',
              ),
            )
          : Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  item.title,
                  style: const TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 12),
                _DetailLine(
                  label: _copy(context, '格式', 'Format', '형식'),
                  value: item.formatLabel,
                ),
                _DetailLine(
                  label: _copy(context, '状态', 'State', '상태'),
                  value: item.stateLabel,
                ),
                if (item.evidenceCount != null)
                  _DetailLine(
                    label: _copy(context, '来源条数', 'Source count', '출처 수'),
                    value: '${item.evidenceCount}',
                  ),
                if (item.generatedAt.isNotEmpty)
                  _DetailLine(
                    label: _copy(context, '生成时间', 'Generated', '생성 시간'),
                    value: item.generatedAt,
                  ),
                if (item.state == Sh04ExportState.ready && item.reopenable)
                  _VerifiedNotice(
                    _copy(
                      context,
                      '范围已核对，成果可重新打开。',
                      'The exact range is verified and this output can be reopened.',
                      '정확한 범위가 확인되어 결과물을 다시 열 수 있습니다.',
                    ),
                  )
                else if (item.state == Sh04ExportState.failed)
                  _InfoMessage(
                    item.failureReason.isEmpty
                        ? _copy(
                            context,
                            '成果生成失败，当前没有可打开的文件。',
                            'Generation failed; there is no file to reopen.',
                            '생성에 실패하여 다시 열 수 있는 파일이 없습니다.',
                          )
                        : item.failureReason,
                  )
                else if (item.state == Sh04ExportState.generating)
                  _InfoMessage(
                    _copy(
                      context,
                      '成果仍在生成中，完成前不会显示下载入口。',
                      'The output is still being generated; no download entry is shown yet.',
                      '결과물을 생성 중이므로 아직 다운로드 입구를 표시하지 않습니다.',
                    ),
                  )
                else
                  _InfoMessage(
                    _copy(
                      context,
                      '当前没有可重新打开的真实成果。',
                      'There is no real output available to reopen.',
                      '다시 열 수 있는 실제 결과물이 없습니다.',
                    ),
                  ),
                if (item.preview.isNotEmpty) ...[
                  const SizedBox(height: 15),
                  Text(
                    _copy(context, '已生成内容', 'Generated content', '생성된 내용'),
                    style: TextStyle(
                      color: LumenisTheme.of(context).quiet,
                      fontSize: 11,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(13),
                    decoration: BoxDecoration(
                      color: LumenisTheme.of(context).canvas,
                      borderRadius: BorderRadius.circular(9),
                    ),
                    child: Text(
                      item.preview,
                      maxLines: 12,
                      overflow: TextOverflow.fade,
                      style: const TextStyle(height: 1.5),
                    ),
                  ),
                ],
                const SizedBox(height: 13),
                Text(
                  _copy(
                    context,
                    '创建、导出和外部分享需要受控入口；此页不会用本地按钮模拟成功。',
                    'Creation, export and external sharing require a governed entry; this page does not simulate success with a local button.',
                    '생성·내보내기·외부 공유는 통제된 입구가 필요하며 이 화면은 로컬 버튼으로 성공을 가장하지 않습니다.',
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
}

class _ReadOnlyExportNote extends StatelessWidget {
  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    padding: const EdgeInsets.fromLTRB(15, 13, 15, 13),
    decoration: BoxDecoration(
      color: LumenisTheme.of(context).caution.withValues(alpha: 0.08),
      border: Border.all(
        color: LumenisTheme.of(context).caution.withValues(alpha: 0.35),
      ),
      borderRadius: BorderRadius.circular(11),
    ),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(
          Icons.info_outline_rounded,
          color: LumenisTheme.of(context).caution,
          size: 19,
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Text(
            _copy(
              context,
              '导出动作尚未绑定可验证的受控入口。这里仅查看真实目录和可重新打开的成果，不会生成假文件。',
              'The export action has no verified governed entry yet. This page only inspects real catalog entries and reopenable outputs; it does not create fake files.',
              '내보내기 작업에는 아직 확인 가능한 통제 입구가 없습니다. 이 화면은 실제 목록과 다시 열 수 있는 결과만 확인하며 가짜 파일을 만들지 않습니다.',
            ),
            style: TextStyle(
              color: LumenisTheme.of(context).muted,
              height: 1.45,
            ),
          ),
        ),
      ],
    ),
  );
}

class _VerifiedNotice extends StatelessWidget {
  const _VerifiedNotice(this.message);

  final String message;

  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 11),
    decoration: BoxDecoration(
      color: LumenisTheme.of(context).positive.withValues(alpha: 0.1),
      border: Border.all(
        color: LumenisTheme.of(context).positive.withValues(alpha: 0.35),
      ),
      borderRadius: BorderRadius.circular(9),
    ),
    child: Row(
      children: [
        Icon(
          Icons.check_circle_outline_rounded,
          color: LumenisTheme.of(context).positive,
          size: 18,
        ),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            message,
            style: TextStyle(
              color: LumenisTheme.of(context).muted,
              height: 1.4,
            ),
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
    label: _copy(
      context,
      '正在读取报告成果',
      'Reading report outputs',
      '보고서 결과물을 읽는 중',
    ),
    child: const Center(child: CircularProgressIndicator()),
  );
}

class _BlockedState extends StatelessWidget {
  const _BlockedState({required this.error, required this.onRetry});

  final Sh04ScopeErrorKind? error;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => _StateMessage(
    title: _copy(
      context,
      '成果中心暂不显示',
      'Output center is hidden for now',
      '결과물 센터를 현재 표시하지 않습니다',
    ),
    detail: switch (error) {
      Sh04ScopeErrorKind.denied => _copy(
        context,
        '当前账号没有这个范围的查看权限。',
        'This account cannot view the selected range.',
        '이 계정은 선택한 범위를 볼 수 없습니다.',
      ),
      Sh04ScopeErrorKind.malformed => _copy(
        context,
        '服务返回的范围不完整，因此不会显示成果。',
        'The returned range is incomplete, so outputs are not shown.',
        '반환된 범위가 불완전하여 결과물을 표시하지 않습니다.',
      ),
      _ => _copy(
        context,
        '尚未确认账号与成果范围的对应关系，因此不会显示成果。',
        'The account and output range have not been verified, so outputs are not shown.',
        '계정과 결과물 범위가 확인되지 않아 결과물을 표시하지 않습니다.',
      ),
    },
    onRetry: onRetry,
  );
}

class _FailureState extends StatelessWidget {
  const _FailureState({required this.kind, required this.onRetry});

  final Sh04FailureKind kind;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => _StateMessage(
    title: _copy(
      context,
      '成果中心暂不可用',
      'Output center unavailable',
      '결과물 센터를 사용할 수 없습니다',
    ),
    detail: switch (kind) {
      Sh04FailureKind.authentication => _copy(
        context,
        '登录状态已过期，请重新登录后查看。',
        'Your sign-in has expired. Sign in again before viewing.',
        '로그인이 만료되었습니다. 다시 로그인한 뒤 확인하세요.',
      ),
      Sh04FailureKind.permissionDenied => _copy(
        context,
        '当前账号暂不能查看成果。',
        'This account cannot view outputs right now.',
        '이 계정은 현재 결과물을 볼 수 없습니다.',
      ),
      Sh04FailureKind.offline => _copy(
        context,
        '成果服务暂时无法连接，请检查连接后重试。',
        'The output service cannot connect right now. Check the connection and try again.',
        '결과물 서비스에 연결할 수 없습니다. 연결을 확인하고 다시 시도하세요.',
      ),
      Sh04FailureKind.response => _copy(
        context,
        '成果服务没有返回可验证的数据，请稍后重试。',
        'The output service did not return verifiable data. Try again later.',
        '결과물 서비스가 확인 가능한 데이터를 반환하지 않았습니다. 나중에 다시 시도하세요.',
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

class _DetailLine extends StatelessWidget {
  const _DetailLine({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 10),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 86,
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

class _StateTag extends StatelessWidget {
  const _StateTag(this.label, {required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 4),
    decoration: BoxDecoration(
      color: color.withValues(alpha: 0.12),
      borderRadius: BorderRadius.circular(12),
    ),
    child: Text(
      label,
      style: TextStyle(color: color, fontSize: 10, fontWeight: FontWeight.w600),
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
      color: LumenisTheme.of(context).accentStrong,
      fontSize: 10,
      letterSpacing: 1.1,
      fontWeight: FontWeight.w700,
    ),
  );
}

IconData _formatIcon(Sh04Format format) => switch (format) {
  Sh04Format.pdf => Icons.picture_as_pdf_outlined,
  Sh04Format.excel || Sh04Format.csv => Icons.table_chart_outlined,
  Sh04Format.powerpoint => Icons.slideshow_outlined,
  Sh04Format.markdown => Icons.article_outlined,
  Sh04Format.unknown => Icons.insert_drive_file_outlined,
};

Color _stateColor(BuildContext context, Sh04ExportState state) =>
    switch (state) {
      Sh04ExportState.ready => LumenisTheme.of(context).positive,
      Sh04ExportState.generating => LumenisTheme.of(context).system,
      Sh04ExportState.failed => LumenisTheme.of(context).danger,
      Sh04ExportState.draft => LumenisTheme.of(context).caution,
      Sh04ExportState.unavailable => LumenisTheme.of(context).muted,
    };

String _copy(BuildContext context, String zh, String en, String ko) =>
    switch (context.lumenisL10n.locale.languageCode) {
      'en' => en,
      'ko' => ko,
      _ => zh,
    };
