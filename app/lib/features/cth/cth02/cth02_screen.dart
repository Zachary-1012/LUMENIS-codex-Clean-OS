import 'package:flutter/material.dart';

import '../../../core/lumenis_core_client.dart';
import '../../../core/lumenis_theme.dart';
import 'cth02_repository.dart';
import 'cth02_view_model.dart';

class Cth02Screen extends StatefulWidget {
  const Cth02Screen({required this.client, this.repository, super.key});

  final LumenisCoreClient client;
  final Cth02Repository? repository;

  @override
  State<Cth02Screen> createState() => _Cth02ScreenState();
}

class _Cth02ScreenState extends State<Cth02Screen> {
  late Cth02ViewModel _viewModel = _createViewModel()..refresh();

  Cth02ViewModel _createViewModel() => Cth02ViewModel(
    repository: widget.repository ?? CoreCth02Repository(client: widget.client),
  );

  @override
  void didUpdateWidget(covariant Cth02Screen oldWidget) {
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
  Widget build(BuildContext context) {
    return ColoredBox(
      color: LumenisTheme.of(context).canvas,
      child: SafeArea(
        child: AnimatedBuilder(
          animation: _viewModel,
          builder: (context, _) => switch (_viewModel.phase) {
            Cth02LoadPhase.loading => const _LoadingState(),
            Cth02LoadPhase.failed => _FailureState(
              kind: _viewModel.failureKind!,
              onRetry: _viewModel.refresh,
            ),
            Cth02LoadPhase.ready => _SubjectProfileWorkspace(
              directory: _viewModel.directory!,
              onRefresh: _viewModel.refresh,
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
  Widget build(BuildContext context) => Center(
    child: Semantics(
      liveRegion: true,
      label: '正在查看 CTH 经营主体名单',
      child: const CircularProgressIndicator(),
    ),
  );
}

class _FailureState extends StatelessWidget {
  const _FailureState({required this.kind, required this.onRetry});

  final Cth02FailureKind kind;
  final VoidCallback onRetry;

  String get _message => switch (kind) {
    Cth02FailureKind.authentication => '主体名单授权尚未接入，名单内容暂不显示；其他工作区不受影响。',
    Cth02FailureKind.permissionDenied => '当前没有查看 CTH 经营主体名单的权限。名单内容未显示。',
    Cth02FailureKind.permissionUnavailable => '暂时无法确认 CTH 经营主体名单的访问权限，请稍后重试。',
    Cth02FailureKind.offline => '暂时无法连接服务，未能读取 CTH 经营主体名单。',
    Cth02FailureKind.invalidResponse => 'CTH 经营主体名单暂时无法显示，请稍后重试。',
    Cth02FailureKind.server => 'CTH 经营主体名单暂时无法加载，请稍后重试。',
  };

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) => Align(
        alignment: Alignment.topCenter,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 740),
          child: Padding(
            padding: EdgeInsets.all(constraints.maxWidth < 480 ? 22 : 34),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const _Eyebrow('CTH  ·  经营主体'),
                const SizedBox(height: 15),
                Text(
                  '经营主体与关联信息',
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    color: LumenisTheme.of(context).foreground,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  _message,
                  style: TextStyle(
                    color: LumenisTheme.of(context).muted,
                    height: 1.6,
                  ),
                ),
                const SizedBox(height: 22),
                _ActionButton(label: '重新查看主体名单', onPressed: onRetry),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _SubjectProfileWorkspace extends StatelessWidget {
  const _SubjectProfileWorkspace({
    required this.directory,
    required this.onRefresh,
  });

  final Cth02Directory directory;
  final VoidCallback onRefresh;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final desktop = constraints.maxWidth >= 1020;
        final inset = desktop ? 34.0 : 18.0;
        final directoryPanel = _DirectoryPanel(
          directory: directory,
          desktop: desktop,
        );
        const relationshipPanel = _OwnershipAvailabilityPanel();

        return Align(
          alignment: Alignment.topCenter,
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1500),
            child: SingleChildScrollView(
              padding: EdgeInsets.fromLTRB(inset, 26, inset, 42),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _PageHeading(
                    count: directory.subjects.length,
                    onRefresh: onRefresh,
                  ),
                  const SizedBox(height: 22),
                  if (desktop)
                    Row(
                      key: const ValueKey('cth02/desktop-layout'),
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        SizedBox(width: 370, child: directoryPanel),
                        const SizedBox(width: 20),
                        const Expanded(child: relationshipPanel),
                      ],
                    )
                  else
                    Column(
                      key: const ValueKey('cth02/mobile-layout'),
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        directoryPanel,
                        const SizedBox(height: 16),
                        relationshipPanel,
                      ],
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
  const _PageHeading({required this.count, required this.onRefresh});

  final int count;
  final VoidCallback onRefresh;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const _Eyebrow('CTH  ·  经营主体'),
        const SizedBox(height: 11),
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: Text(
                '经营主体与关联信息',
                style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                  color: LumenisTheme.of(context).foreground,
                  fontWeight: FontWeight.w600,
                  letterSpacing: -0.4,
                ),
              ),
            ),
            IconButton(
              tooltip: '刷新 CTH 主体名单',
              onPressed: onRefresh,
              icon: const Icon(Icons.refresh_rounded),
            ),
          ],
        ),
        const SizedBox(height: 5),
        Text(
          '仅展示 CTH 经营主体名单中的基本资料。名单可见不代表可以查看名单内任一主体的经营数据；本页不会切换当前主体。',
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
            color: LumenisTheme.of(context).muted,
          ),
        ),
        const SizedBox(height: 12),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            _StatusChip(label: 'CTH 主体名单', color: LumenisTheme.of(context).cth),
            _StatusChip(
              label: '名单中 $count 个主体',
              color: LumenisTheme.of(context).quiet,
            ),
          ],
        ),
      ],
    );
  }
}

class _DirectoryPanel extends StatelessWidget {
  const _DirectoryPanel({required this.directory, required this.desktop});

  final Cth02Directory directory;
  final bool desktop;

  @override
  Widget build(BuildContext context) {
    final panel = _Panel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _PanelHeading(eyebrow: 'CTH 主体名单', title: '经营主体名单'),
          const SizedBox(height: 8),
          Text(
            '名单只展示主体基本资料，不会切换当前经营主体或显示主体经营数据。',
            style: TextStyle(
              color: LumenisTheme.of(context).muted,
              height: 1.5,
            ),
          ),
          const SizedBox(height: 16),
          if (directory.subjects.isEmpty)
            const _EmptyDirectory()
          else
            SizedBox(
              height: desktop ? 470 : 310,
              child: ListView.separated(
                key: const ValueKey('cth02/subject-directory'),
                itemCount: directory.subjects.length,
                itemBuilder: (context, index) =>
                    _SubjectMetadataRow(subject: directory.subjects[index]),
                separatorBuilder: (_, _) => const Divider(height: 1),
              ),
            ),
        ],
      ),
    );
    return panel;
  }
}

class _SubjectMetadataRow extends StatelessWidget {
  const _SubjectMetadataRow({required this.subject});

  final Cth02SubjectMetadata subject;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 13),
      child: Semantics(
        container: true,
        label: [
          subject.name,
          subject.id,
          if (subject.type.isNotEmpty) subject.type,
          if (subject.industry.isNotEmpty) subject.industry,
        ].join(' · '),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              subject.name,
              style: TextStyle(
                color: LumenisTheme.of(context).foreground,
                fontSize: 15,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 4),
            Wrap(
              spacing: 8,
              runSpacing: 3,
              children: [
                if (subject.type.isNotEmpty) _MetadataText(subject.type),
                if (subject.industry.isNotEmpty)
                  _MetadataText(subject.industry),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _EmptyDirectory extends StatelessWidget {
  const _EmptyDirectory();

  @override
  Widget build(BuildContext context) => Padding(
    padding: EdgeInsets.symmetric(vertical: 26),
    child: Text(
      '当前 CTH 经营主体名单中暂无主体。',
      style: TextStyle(color: LumenisTheme.of(context).muted, height: 1.5),
    ),
  );
}

class _OwnershipAvailabilityPanel extends StatelessWidget {
  const _OwnershipAvailabilityPanel();

  @override
  Widget build(BuildContext context) {
    return _Panel(
      child: Column(
        key: const ValueKey('cth02/ownership-not-collected'),
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _PanelHeading(eyebrow: '主体关联信息', title: '主体关联信息'),
          const SizedBox(height: 9),
          Text(
            '经营主体 → 业务单元 → 品牌 / 业态',
            style: TextStyle(
              color: LumenisTheme.of(context).foreground,
              fontSize: 16,
            ),
          ),
          const SizedBox(height: 7),
          Text(
            '当前名单未提供已核实的主体与业务单元、品牌及业态关联资料。',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              color: LumenisTheme.of(context).muted,
            ),
          ),
          const SizedBox(height: 22),
          const _RelationshipRecord(
            index: '01',
            title: '经营主体 → 业务单元',
            detail: '主体对应的业务单元关联信息暂缺',
          ),
          const _RelationshipRecord(
            index: '02',
            title: '业务单元 → 品牌 / 业态',
            detail: '品牌、业态及有效期关联信息暂缺',
          ),
          const SizedBox(height: 15),
          const _LineageNotice(),
        ],
      ),
    );
  }
}

class _RelationshipRecord extends StatelessWidget {
  const _RelationshipRecord({
    required this.index,
    required this.title,
    required this.detail,
  });

  final String index;
  final String title;
  final String detail;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Container(
        decoration: BoxDecoration(
          color: LumenisTheme.of(context).surfaceRaised,
          border: Border.all(color: LumenisTheme.of(context).line),
          borderRadius: BorderRadius.circular(14),
        ),
        padding: const EdgeInsets.all(16),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              index,
              style: TextStyle(
                color: LumenisTheme.of(context).cth,
                fontFeatures: [FontFeature.tabularFigures()],
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(width: 14),
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
                  const SizedBox(height: 5),
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
            const SizedBox(width: 10),
            _StatusChip(label: '资料暂缺', color: LumenisTheme.of(context).caution),
          ],
        ),
      ),
    );
  }
}

class _LineageNotice extends StatelessWidget {
  const _LineageNotice();

  @override
  Widget build(BuildContext context) => Container(
    decoration: BoxDecoration(
      color: LumenisTheme.of(context).cth.withValues(alpha: 0.07),
      borderRadius: BorderRadius.circular(12),
      border: Border.all(
        color: LumenisTheme.of(context).cth.withValues(alpha: 0.22),
      ),
    ),
    padding: const EdgeInsets.all(15),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(
          Icons.info_outline_rounded,
          color: LumenisTheme.of(context).cth,
          size: 19,
        ),
        SizedBox(width: 10),
        Expanded(
          child: Text(
            '本页不会根据其他资料推断主体之间的关联，也不会自动切换当前经营主体。',
            style: TextStyle(
              color: LumenisTheme.of(context).muted,
              height: 1.55,
            ),
          ),
        ),
      ],
    ),
  );
}

class _Panel extends StatelessWidget {
  const _Panel({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    decoration: BoxDecoration(
      color: LumenisTheme.of(context).surface,
      borderRadius: BorderRadius.circular(18),
      border: Border.all(color: LumenisTheme.of(context).line),
    ),
    padding: const EdgeInsets.all(20),
    child: child,
  );
}

class _PanelHeading extends StatelessWidget {
  const _PanelHeading({required this.eyebrow, required this.title});

  final String eyebrow;
  final String title;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      _Eyebrow(eyebrow),
      const SizedBox(height: 8),
      Text(
        title,
        style: Theme.of(context).textTheme.titleLarge?.copyWith(
          color: LumenisTheme.of(context).foreground,
          fontSize: 20,
        ),
      ),
    ],
  );
}

class _Eyebrow extends StatelessWidget {
  const _Eyebrow(this.label);

  final String label;

  @override
  Widget build(BuildContext context) => Text(
    label,
    style: TextStyle(
      color: LumenisTheme.of(context).cth,
      fontSize: 10,
      letterSpacing: 1.1,
      fontWeight: FontWeight.w700,
    ),
  );
}

class _StatusChip extends StatelessWidget {
  const _StatusChip({required this.label, required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
    decoration: BoxDecoration(
      color: color.withValues(alpha: 0.1),
      borderRadius: BorderRadius.circular(99),
      border: Border.all(color: color.withValues(alpha: 0.35)),
    ),
    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
    child: Text(
      label,
      style: TextStyle(color: color, fontSize: 10, fontWeight: FontWeight.w700),
    ),
  );
}

class _MetadataText extends StatelessWidget {
  const _MetadataText(this.value);

  final String value;

  @override
  Widget build(BuildContext context) => Text(
    value,
    style: TextStyle(color: LumenisTheme.of(context).quiet, fontSize: 11),
  );
}

class _ActionButton extends StatelessWidget {
  const _ActionButton({required this.label, required this.onPressed});

  final String label;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) => FilledButton.tonalIcon(
    onPressed: onPressed,
    icon: const Icon(Icons.refresh_rounded),
    label: Text(label),
  );
}
