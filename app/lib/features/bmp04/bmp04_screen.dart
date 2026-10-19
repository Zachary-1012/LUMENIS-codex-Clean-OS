import 'package:flutter/material.dart';

import '../../core/lumenis_icon.dart';

import '../../core/lumenis_core_client.dart';
import '../../core/lumenis_theme.dart';
import '../../l10n/lumenis_localizations.dart';
import '../cth/cth10/source_brief_panel.dart';
import '../cth/cth10/source_brief_copy.dart';
import 'bmp04_repository.dart';
import 'bmp04_snapshot.dart';
import 'bmp04_view_model.dart';

class Bmp04Screen extends StatefulWidget {
  const Bmp04Screen({required this.client, this.repository, super.key});

  final LumenisCoreClient client;
  final Bmp04Repository? repository;

  @override
  State<Bmp04Screen> createState() => _Bmp04ScreenState();
}

class _Bmp04ScreenState extends State<Bmp04Screen> {
  bool _showSourceBrief = false;
  late final Bmp04ViewModel _viewModel = Bmp04ViewModel(
    repository: widget.repository ?? CoreBmp04Repository(client: widget.client),
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
        child: _showSourceBrief
            ? SourceBriefPanel(
                client: widget.client,
                domainId: 'BMP',
                onReturn: () => setState(() => _showSourceBrief = false),
              )
            : Column(
                children: [
                  Align(
                    alignment: AlignmentDirectional.centerEnd,
                    child: TextButton.icon(
                      onPressed: () => setState(() => _showSourceBrief = true),
                      icon: const Icon(Icons.find_in_page_outlined),
                      label: Text(
                        SourceBriefCopy.of(context).text('entry'),
                      ),
                    ),
                  ),
                  Expanded(
                    child: AnimatedBuilder(
                      animation: _viewModel,
                      builder: (context, _) => switch (_viewModel.phase) {
                        Bmp04LoadPhase.loading => const _LoadingState(),
                        Bmp04LoadPhase.failed => _FailureState(
                          kind: _viewModel.failureKind!,
                          onRetry: _viewModel.refresh,
                        ),
                        Bmp04LoadPhase.ready => _ReadyState(
                          snapshot: _viewModel.snapshot!,
                          viewModel: _viewModel,
                        ),
                      },
                    ),
                  ),
                ],
              ),
      ),
    );
  }
}

class _ReadyState extends StatelessWidget {
  const _ReadyState({required this.snapshot, required this.viewModel});

  final Bmp04Snapshot snapshot;
  final Bmp04ViewModel viewModel;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final compact = constraints.maxWidth < 720;
        final inset = compact ? 18.0 : 34.0;
        return Align(
          alignment: Alignment.topCenter,
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1420),
            child: SingleChildScrollView(
              padding: EdgeInsets.fromLTRB(inset, 26, inset, 40),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const _PageHeading(),
                  const SizedBox(height: 20),
                  _FocusBand(snapshot: snapshot),
                  const SizedBox(height: 20),
                  if (snapshot.scopeReady && snapshot.dashboards.isNotEmpty) ...[
                    _ClassificationWorkspace(snapshot: snapshot, viewModel: viewModel),
                    const SizedBox(height: 20),
                  ],
                  if (snapshot.presentationState ==
                          Bmp04PresentationState.ready ||
                      snapshot.presentationState ==
                          Bmp04PresentationState.partial ||
                      snapshot.presentationState ==
                          Bmp04PresentationState.stale)
                    _PropagationWorkspace(
                      snapshot: snapshot,
                      viewModel: viewModel,
                      compact: compact,
                    )
                  else
                    _AvailabilityPanel(
                      snapshot: snapshot,
                      onRetry: viewModel.refresh,
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

class _PageHeading extends StatelessWidget {
  const _PageHeading();

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          copy.text('screen.BMP-04'),
          style: Theme.of(context).textTheme.headlineMedium?.copyWith(
            color: LumenisTheme.of(context).foreground,
            fontWeight: FontWeight.w600,
            letterSpacing: -0.5,
          ),
        ),
        const SizedBox(height: 7),
        Text(
          copy.text('common.status'),
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
            color: LumenisTheme.of(context).muted,
          ),
        ),
      ],
    );
  }
}

class _FocusBand extends StatelessWidget {
  const _FocusBand({required this.snapshot});

  final Bmp04Snapshot snapshot;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    final languageCode = Localizations.localeOf(context).languageCode == 'zh'
        ? 'zh-CN'
        : Localizations.localeOf(context).languageCode;
    final name = snapshot.focus.localizedName(languageCode);
    final title = name == null
        ? copy.text('bmp01.focus.global')
        : copy.text('shell.bmp.brand_named', values: {'name': name});
    final detail = copy.text('context.selector.scope_note');
    return Semantics(
      container: true,
      liveRegion: true,
      label: '$title. $detail',
      child: _Panel(
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            LumenisIcon(
              Icons.center_focus_strong,
              color: LumenisTheme.of(context).bmp,
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: TextStyle(
                      color: LumenisTheme.of(context).foreground,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    detail,
                    style: TextStyle(
                      color: LumenisTheme.of(context).muted,
                      height: 1.45,
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
}

class _PropagationWorkspace extends StatelessWidget {
  const _PropagationWorkspace({
    required this.snapshot,
    required this.viewModel,
    required this.compact,
  });

  final Bmp04Snapshot snapshot;
  final Bmp04ViewModel viewModel;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final selected = viewModel.selectedChannel;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (compact)
          _ChannelPicker(
            channels: snapshot.channels,
            selectedId: viewModel.selectedChannelId,
            onChanged: viewModel.selectChannel,
          ),
        if (compact) const SizedBox(height: 14),
        if (compact)
          Column(
            children: [
              _FlowPanel(channel: selected),
              const SizedBox(height: 14),
              _ChannelDetails(channel: selected),
            ],
          )
        else
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(flex: 7, child: _FlowPanel(channel: selected)),
              const SizedBox(width: 18),
              Expanded(
                flex: 5,
                child: _ChannelMatrix(
                  channels: snapshot.channels,
                  selectedId: viewModel.selectedChannelId,
                  onSelect: viewModel.selectChannel,
                ),
              ),
            ],
          ),
      ],
    );
  }
}

class _ChannelPicker extends StatelessWidget {
  const _ChannelPicker({
    required this.channels,
    required this.selectedId,
    required this.onChanged,
  });

  final List<Bmp04Channel> channels;
  final String? selectedId;
  final ValueChanged<String> onChanged;

  @override
  Widget build(BuildContext context) {
    return _Panel(
      child: Wrap(
        spacing: 9,
        runSpacing: 9,
        children: [
          for (final channel in channels)
            ChoiceChip(
              selected: channel.id == selectedId,
              label: Text(channel.name),
              onSelected: (_) => onChanged(channel.id),
            ),
        ],
      ),
    );
  }
}

class _FlowPanel extends StatelessWidget {
  const _FlowPanel({required this.channel});

  final Bmp04Channel? channel;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    if (channel == null) {
      return _Panel(
        padding: const EdgeInsets.all(24),
        child: Text(
          copy.text('state.empty_true_d'),
          style: TextStyle(color: LumenisTheme.of(context).muted),
        ),
      );
    }
    return _Panel(
      padding: const EdgeInsets.fromLTRB(18, 18, 18, 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(channel!.name, style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 5),
          Text(
            copy.text('common.status'),
            style: TextStyle(color: LumenisTheme.of(context).muted),
          ),
          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            height: 104,
            child: CustomPaint(
              painter: _RiverPainter(palette: LumenisTheme.of(context)),
            ),
          ),
          const SizedBox(height: 6),
          _StageMetric(
            metric: channel!.content,
            fallback: copy.text('common.type'),
            icon: Icons.article_outlined,
          ),
          _StageMetric(
            metric: channel!.exposure,
            fallback: copy.text('common.status'),
            icon: Icons.visibility_outlined,
          ),
          _StageMetric(
            metric: channel!.response,
            fallback: copy.text('comp.insight'),
            icon: Icons.forum_outlined,
          ),
          _StageMetric(
            metric: channel!.conversion,
            fallback: copy.text('comp.actions'),
            icon: Icons.arrow_forward_outlined,
          ),
        ],
      ),
    );
  }
}

class _StageMetric extends StatelessWidget {
  const _StageMetric({
    required this.metric,
    required this.fallback,
    required this.icon,
  });

  final Bmp04Metric? metric;
  final String fallback;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    final label =
        metric?.localizedLabel(
          Localizations.localeOf(context).languageCode == 'zh'
              ? 'zh-CN'
              : Localizations.localeOf(context).languageCode,
          fallback,
        ) ??
        fallback;
    final value = metric == null
        ? copy.text('state.empty_true')
        : _format(metric!.value) +
              (metric!.unit == null ? '' : ' ${metric!.unit!}');
    final details = metric == null
        ? copy.text('state.empty_true_d')
        : '${metric!.definition} · ${metric!.window}';
    return Semantics(
      container: true,
      label: '$label: $value. $details',
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 7),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, color: LumenisTheme.of(context).bmp, size: 20),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    label,
                    style: TextStyle(
                      color: LumenisTheme.of(context).foreground,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    details,
                    style: TextStyle(
                      color: LumenisTheme.of(context).muted,
                      height: 1.4,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 10),
            Text(
              value,
              textAlign: TextAlign.end,
              style: TextStyle(
                color: LumenisTheme.of(context).foreground,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ),
    );
  }

  String _format(num value) {
    if (value == value.roundToDouble()) return value.toInt().toString();
    return value.toStringAsFixed(2);
  }
}

class _ChannelMatrix extends StatelessWidget {
  const _ChannelMatrix({
    required this.channels,
    required this.selectedId,
    required this.onSelect,
  });

  final List<Bmp04Channel> channels;
  final String? selectedId;
  final ValueChanged<String> onSelect;

  @override
  Widget build(BuildContext context) {
    return _Panel(
      padding: const EdgeInsets.fromLTRB(18, 18, 18, 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.lumenisL10n.text('common.type'),
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 5),
          Text(
            context.lumenisL10n.text('common.source'),
            style: TextStyle(color: LumenisTheme.of(context).muted),
          ),
          const SizedBox(height: 12),
          ListView.separated(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: channels.length,
            separatorBuilder: (_, _) => const Divider(height: 1),
            itemBuilder: (context, index) {
              final channel = channels[index];
              final selected = channel.id == selectedId;
              return Semantics(
                button: true,
                selected: selected,
                label: channel.name,
                child: InkWell(
                  key: Key('bmp04-channel-${channel.id}'),
                  onTap: () => onSelect(channel.id),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(
                      vertical: 12,
                      horizontal: 4,
                    ),
                    child: Row(
                      children: [
                        Icon(
                          selected
                              ? Icons.radio_button_checked
                              : Icons.radio_button_unchecked,
                          color: selected
                              ? LumenisTheme.of(context).bmp
                              : LumenisTheme.of(context).quiet,
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            channel.name,
                            style: TextStyle(
                              color: LumenisTheme.of(context).foreground,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ),
                        Text(
                          _metricValue(channel.exposure, context),
                          style: TextStyle(
                            color: LumenisTheme.of(context).muted,
                            fontSize: 12,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              );
            },
          ),
        ],
      ),
    );
  }

  String _metricValue(Bmp04Metric? metric, BuildContext context) {
    if (metric == null) return context.lumenisL10n.text('state.empty_true');
    return metric.value == metric.value.roundToDouble()
        ? metric.value.toInt().toString()
        : metric.value.toStringAsFixed(1);
  }
}

class _ChannelDetails extends StatelessWidget {
  const _ChannelDetails({required this.channel});

  final Bmp04Channel? channel;

  @override
  Widget build(BuildContext context) {
    if (channel == null) return const SizedBox.shrink();
    final metrics = <Bmp04Metric?>[
      channel!.content,
      channel!.exposure,
      channel!.response,
      channel!.conversion,
    ].whereType<Bmp04Metric>();
    return _Panel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          for (final metric in metrics) ...[
            Text(
              metric.localizedLabel(
                Localizations.localeOf(context).languageCode == 'zh'
                    ? 'zh-CN'
                    : Localizations.localeOf(context).languageCode,
                context.lumenisL10n.text('common.detail'),
              ),
              style: TextStyle(
                color: LumenisTheme.of(context).foreground,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 3),
            Text(
              '${context.lumenisL10n.text('common.source')}: ${metric.source} · ${metric.evidenceReference}',
              style: TextStyle(
                color: LumenisTheme.of(context).muted,
                fontSize: 12,
              ),
            ),
            const SizedBox(height: 12),
          ],
        ],
      ),
    );
  }
}

class _AvailabilityPanel extends StatelessWidget {
  const _AvailabilityPanel({required this.snapshot, required this.onRetry});

  final Bmp04Snapshot snapshot;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    final title = switch (snapshot.presentationState) {
      Bmp04PresentationState.global => copy.text('bmp01.market.global.title'),
      Bmp04PresentationState.notCollected => copy.text(
        'state.empty_notcollected',
      ),
      Bmp04PresentationState.empty => copy.text('state.empty_true'),
      Bmp04PresentationState.blocked => copy.text('state.permission_denied'),
      Bmp04PresentationState.unavailable => copy.text('state.error'),
      Bmp04PresentationState.stale => copy.text('state.stale'),
      Bmp04PresentationState.partial => copy.text('state.partial'),
      _ => copy.text('state.error'),
    };
    final detail = switch (snapshot.presentationState) {
      Bmp04PresentationState.global => copy.text('bmp01.market.global.detail'),
      Bmp04PresentationState.notCollected => copy.text(
        'state.empty_notcollected_d',
      ),
      Bmp04PresentationState.empty => copy.text('state.empty_true_d'),
      Bmp04PresentationState.blocked => copy.text('state.permission_denied_d'),
      Bmp04PresentationState.unavailable => copy.text(
        'context.screen_binding_unavailable',
      ),
      Bmp04PresentationState.stale => copy.text('state.stale_d'),
      Bmp04PresentationState.partial => copy.text('state.partial_d'),
      _ => copy.text('state.error_d'),
    };
    return _Panel(
      padding: const EdgeInsets.all(24),
      child: Semantics(
        liveRegion: true,
        label: '$title. $detail',
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(
              snapshot.presentationState == Bmp04PresentationState.blocked
                  ? Icons.lock_outline
                  : Icons.info_outline,
              color: LumenisTheme.of(context).caution,
            ),
            const SizedBox(height: 14),
            Text(title, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 7),
            Text(
              detail,
              style: TextStyle(
                color: LumenisTheme.of(context).muted,
                height: 1.55,
              ),
            ),
            const SizedBox(height: 18),
            FilledButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh),
              label: Text(copy.text('common.refresh')),
            ),
          ],
        ),
      ),
    );
  }
}

class _LoadingState extends StatelessWidget {
  const _LoadingState();

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Semantics(
        liveRegion: true,
        label: context.lumenisL10n.text('state.loading_d'),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const CircularProgressIndicator(),
            const SizedBox(height: 14),
            Text(context.lumenisL10n.text('state.loading')),
          ],
        ),
      ),
    );
  }
}

class _FailureState extends StatelessWidget {
  const _FailureState({required this.kind, required this.onRetry});

  final Bmp04FailureKind kind;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final copy = context.lumenisL10n;
    final title = kind == Bmp04FailureKind.offline
        ? copy.text('state.offline')
        : kind == Bmp04FailureKind.server
        ? copy.text('state.error')
        : copy.text('state.permission_denied');
    final detail = kind == Bmp04FailureKind.offline
        ? copy.text('state.offline_d')
        : kind == Bmp04FailureKind.server
        ? copy.text('state.error_d')
        : copy.text('state.permission_denied_d');
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: _Panel(
          padding: const EdgeInsets.all(24),
          child: Semantics(
            liveRegion: true,
            label: '$title. $detail',
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: Theme.of(context).textTheme.titleLarge),
                const SizedBox(height: 8),
                Text(
                  detail,
                  style: TextStyle(
                    color: LumenisTheme.of(context).muted,
                    height: 1.5,
                  ),
                ),
                const SizedBox(height: 18),
                FilledButton.icon(
                  onPressed: onRetry,
                  icon: const Icon(Icons.refresh),
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

class _Panel extends StatelessWidget {
  const _Panel({required this.child, this.padding = const EdgeInsets.all(16)});

  final Widget child;
  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: padding,
      decoration: BoxDecoration(
        color: LumenisTheme.of(context).surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: LumenisTheme.of(context).line),
      ),
      child: child,
    );
  }
}

class _RiverPainter extends CustomPainter {
  const _RiverPainter({required this.palette});

  final LumenisPalette palette;

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = palette.bmp.withValues(alpha: 0.7)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3;
    final thin = Paint()
      ..color = palette.bmp.withValues(alpha: 0.22)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1;
    final path = Path()
      ..moveTo(10, size.height * 0.70)
      ..cubicTo(
        size.width * 0.25,
        size.height * 0.20,
        size.width * 0.38,
        size.height * 0.82,
        size.width * 0.55,
        size.height * 0.42,
      )
      ..cubicTo(
        size.width * 0.70,
        size.height * 0.10,
        size.width * 0.83,
        size.height * 0.65,
        size.width - 10,
        size.height * 0.28,
      );
    canvas.drawPath(path, paint);
    canvas.drawLine(
      Offset(10, size.height * 0.83),
      Offset(size.width - 10, size.height * 0.83),
      thin,
    );
    canvas.drawCircle(
      Offset(10, size.height * 0.70),
      5,
      Paint()..color = palette.bmp,
    );
    canvas.drawCircle(
      Offset(size.width - 10, size.height * 0.28),
      5,
      Paint()..color = palette.bmp,
    );
  }

  @override
  bool shouldRepaint(covariant _RiverPainter oldDelegate) =>
      oldDelegate.palette != palette;
}

String _classificationCopy(BuildContext context, String en, String zh, String ko) {
  return switch (Localizations.localeOf(context).languageCode) {
    'zh' => zh, 'ko' => ko, _ => en,
  };
}

String _categoryLabel(BuildContext context, String category) => switch (category) {
  'brand_event' => _classificationCopy(context, 'Brand events', '品牌事件', '브랜드 이벤트'),
  'product_event' => _classificationCopy(context, 'Product events', '产品事件', '제품 이벤트'),
  _ => _classificationCopy(context, 'Industry events', '行业事件', '업계 이벤트'),
};

class _ClassificationWorkspace extends StatelessWidget {
  const _ClassificationWorkspace({required this.snapshot, required this.viewModel});
  final Bmp04Snapshot snapshot;
  final Bmp04ViewModel viewModel;

  Future<void> _classify(BuildContext context, Bmp04CuratedEvent event, String category) async {
    final prepared = await viewModel.previewClassification(event.id, category);
    if (!context.mounted || !prepared) return;
    final confirmed = await showDialog<bool>(context: context, builder: (context) => AlertDialog(
      title: Text(_classificationCopy(context, 'Confirm classification', '确认分类', '분류 확인')),
      content: Text('${event.title}\n${event.evidenceReference}\n${_categoryLabel(context, category)}\n\n${_classificationCopy(context,
        'This saves your interpretation of this event. It does not change the source facts. If the source or saved classification changes, preview again.',
        '仅保存你对此事件的人工判断，不改变来源事实。来源或已保存分类发生变化时，需要重新预览。',
        '이 이벤트에 대한 판단을 저장합니다. 원본 사실은 변경하지 않습니다. 원본이나 저장된 분류가 바뀌면 다시 미리 보세요.')}'),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context, false), child: Text(_classificationCopy(context, 'Cancel', '取消', '취소'))),
        FilledButton(key: const Key('bmp04-confirm-classification'),
          onPressed: () => Navigator.pop(context, true),
          child: Text(_classificationCopy(context, 'Save classification', '保存分类', '분류 저장'))),
      ],
    ));
    if (confirmed == true && context.mounted) {
      await viewModel.confirmClassification();
    } else {
      viewModel.cancelClassification();
    }
  }

  @override
  Widget build(BuildContext context) {
    final dashboard = snapshot.dashboards.firstWhere(
      (item) => item.category == viewModel.selectedCategory,
      orElse: () => snapshot.dashboards.first);
    return _Panel(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text(_classificationCopy(context, 'Human-classified event sample', '人工分类事件样本', '수동 분류 이벤트 표본'),
        style: Theme.of(context).textTheme.titleLarge),
      const SizedBox(height: 8),
      Text(_classificationCopy(context,
        'Counts describe the current verified curated sample, not market reach or popularity. Unclassified events stay unknown.',
        '计数仅描述当前已核验策展样本，不代表全市场覆盖或热度。未分类事件保持未知。',
        '집계는 현재 검증된 큐레이션 표본이며 시장 도달률이나 인기도가 아닙니다. 미분류 이벤트는 미확인으로 유지됩니다.')),
      const SizedBox(height: 12),
      Wrap(spacing: 8, runSpacing: 8, children: [
        for (final category in bmp04Categories)
          ChoiceChip(key: Key('bmp04-view-$category'),
            label: Text(_categoryLabel(context, category)),
            selected: dashboard.category == category,
            onSelected: (_) => viewModel.selectCategory(category)),
      ]),
      const SizedBox(height: 12),
      Text('${_classificationCopy(context, 'Observed classified events', '已分类观测事件', '분류된 관측 이벤트')}: ${dashboard.observed}'),
      Text('${_classificationCopy(context, 'Complete sample count', '完整样本计数', '전체 표본 수')}: ${dashboard.total ?? '—'}'),
      Text('${_classificationCopy(context, 'Unclassified', '未分类', '미분류')}: ${snapshot.unclassifiedEventCount ?? '—'}'),
      for (final event in dashboard.events)
        ListTile(key: Key('bmp04-dashboard-event-${event.id}'),
          title: Text(event.title), subtitle: Text(event.evidenceReference)),
      if (dashboard.events.length < dashboard.observed)
        Text(_classificationCopy(context, 'Only part of the event list is displayed.', '当前仅展示部分事件。', '이벤트 목록의 일부만 표시됩니다.')),
      const Divider(),
      Text(_classificationCopy(context, 'Review an individual event', '逐条核对事件', '개별 이벤트 검토')),
      Text(_classificationCopy(context, 'The displayed event list may be a limited subset of the sample.', '下方事件列表可能只展示当前样本的一部分。', '아래 이벤트 목록은 현재 표본의 일부일 수 있습니다.')),
      if (snapshot.focus.isGlobal)
        Text(_classificationCopy(context, 'Select a brand to classify events.', '请选择品牌后再分类。', '이벤트를 분류하려면 브랜드를 선택하세요.')),
      for (final event in snapshot.curatedEvents)
        ListTile(title: Text(event.title), subtitle: Text(event.evidenceReference),
          trailing: PopupMenuButton<String>(key: Key('bmp04-classify-${event.id}'),
            enabled: viewModel.canClassify,
            tooltip: _classificationCopy(context, 'Preview classification', '预览分类', '분류 미리 보기'),
            icon: const Icon(Icons.edit_outlined),
            onSelected: (category) => _classify(context, event, category),
            itemBuilder: (context) => [for (final category in bmp04Categories)
              PopupMenuItem(value: category, child: Text(_categoryLabel(context, category)))],
          )),
      if (viewModel.classificationBusy) const LinearProgressIndicator(),
      if (viewModel.classificationFailure != null)
        Text(viewModel.classificationOutcomeUnknown
          ? _classificationCopy(context, 'Save outcome is uncertain. Refresh to check before trying again.', '保存结果尚未确认，请先刷新核对后再尝试。', '저장 결과가 불확실합니다. 다시 시도하기 전에 새로고침하여 확인하세요.')
          : _classificationCopy(context, 'The classification could not be saved. Check access and refresh for a new preview.', '分类未能保存，请核对权限并刷新后重新预览。', '분류를 저장하지 못했습니다. 권한을 확인하고 새로고침 후 다시 미리 보세요.')),
      TextButton(onPressed: viewModel.classificationBusy ? null : viewModel.refresh,
        child: Text(_classificationCopy(context, 'Refresh', '刷新', '새로고침'))),
    ]));
  }
}
