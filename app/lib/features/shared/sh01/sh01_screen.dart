import 'package:flutter/material.dart';

import '../../../core/lumenis_icon.dart';

import '../../../core/lumenis_core_client.dart';
import '../../../core/lumenis_theme.dart';
import '../../../l10n/lumenis_localizations.dart';
import 'sh01_repository.dart';
import 'sh01_snapshot.dart';
import 'sh01_view_model.dart';
import 'media_project_workbench.dart';
import 'manuscript_editor.dart';

String _catalogFailureCopy(String? error) => switch (error) {
  '登录已失效，请重新登录后读取。' => 'sh01.failure.auth',
  '当前账号无权读取共享能力目录。' => 'sh01.failure.permission',
  'Product Core 暂时不可用。' => 'sh01.failure.offline',
  _ => 'sh01.failure.other',
};

String _consumerLabel(BuildContext context, String consumer) =>
    switch (consumer.trim().toUpperCase()) {
      'CTH' ||
      'COMMERCE' ||
      'COMMERCE OPERATIONS' => context.lumenisL10n.text('navgroup.cth'),
      'BMP' ||
      'ZBMP' ||
      'BRAND' ||
      'BRAND MARKET' => context.lumenisL10n.text('navgroup.bmp'),
      _ => context.lumenisL10n.text('navgroup.shared'),
    };

String _categoryLabel(BuildContext context, String category) =>
    switch (category.trim().toUpperCase()) {
      'RESEARCH' ||
      '研究与证据' ||
      '研究资料' => context.lumenisL10n.text('sh01.category.research'),
      'CONTENT' ||
      '内容制作' ||
      '内容创作' => context.lumenisL10n.text('sh01.category.content'),
      '' => context.lumenisL10n.text('sh01.category.other'),
      _ => context.lumenisL10n.text('sh01.category.other'),
    };

String _permissionLabel(BuildContext context, String permission) {
  final labels = {
    'READ': context.lumenisL10n.text('sh01.permission.read'),
    'RESEARCH': context.lumenisL10n.text('sh01.permission.research'),
    'ANALYZE': context.lumenisL10n.text('sh01.permission.analyze'),
    'SUGGEST': context.lumenisL10n.text('sh01.permission.suggest'),
    'AUDIT': context.lumenisL10n.text('sh01.permission.audit'),
    'WRITE': context.lumenisL10n.text('sh01.permission.write'),
    'EXPORT': context.lumenisL10n.text('sh01.permission.export'),
    'PUBLISH': context.lumenisL10n.text('sh01.permission.publish'),
  };
  final parts = permission
      .split(RegExp(r'\s*/\s*'))
      .map((part) => part.trim().toUpperCase())
      .toList(growable: false);
  if (parts.isEmpty || parts.any((part) => !labels.containsKey(part))) {
    return context.lumenisL10n.text('sh01.permission.other');
  }
  return parts.map((part) => labels[part]!).join('、');
}

String _riskLabel(BuildContext context, String risk) =>
    switch (risk.trim().toUpperCase()) {
      'LOW' => context.lumenisL10n.text('sh01.risk.low'),
      'MEDIUM' => context.lumenisL10n.text('sh01.risk.medium'),
      'HIGH' => context.lumenisL10n.text('sh01.risk.high'),
      _ => context.lumenisL10n.text('sh01.risk.unknown'),
    };

String _useLimitLabel(BuildContext context, String policy) =>
    switch (policy.trim().toUpperCase()) {
      'READ_ONLY' => context.lumenisL10n.text('sh01.limit.read_only'),
      'NO_EXTERNAL_WRITE' => context.lumenisL10n.text(
        'sh01.limit.no_external_write',
      ),
      'APPROVAL_REQUIRED' => context.lumenisL10n.text('sh01.limit.approval'),
      'AUDIT_ONLY' => context.lumenisL10n.text('sh01.limit.audit'),
      _ => context.lumenisL10n.text('sh01.limit.unknown'),
    };

String? _safeBusinessCopy(String value) {
  final normalized = value.trim();
  if (normalized.isEmpty || normalized.length > 280) return null;
  if (RegExp(
    r'(api|database|sqlite|\bdb\b|provider|model|permission|evidence|owner|runtime|contract|canonical|viewmodel|subject|brandfocus|cth|bmp|zbmp|token|cookie|secret|internal|private|path|https?)',
    caseSensitive: false,
  ).hasMatch(normalized)) {
    return null;
  }
  if (normalized.runes.any((rune) => !_isAllowedBusinessRune(rune))) {
    return null;
  }
  return normalized;
}

bool _isAllowedBusinessRune(int rune) {
  final asciiLetterOrDigit =
      rune >= 0x30 && rune <= 0x39 ||
      rune >= 0x41 && rune <= 0x5a ||
      rune >= 0x61 && rune <= 0x7a;
  final naturalLanguageRange =
      rune >= 0x3400 && rune <= 0x9fff ||
      rune >= 0xac00 && rune <= 0xd7af ||
      rune >= 0x00c0 && rune <= 0x024f;
  const punctuation = ' \t\n\r&·、，。！？：；（）()“”‘’+-—–';
  return asciiLetterOrDigit ||
      naturalLanguageRange ||
      punctuation.runes.contains(rune);
}

String _businessDescription(String description) {
  final normalized = description
      .replaceAll('已入库 Evidence', '已入库资料')
      .replaceAll(RegExp('Evidence', caseSensitive: false), '资料依据')
      .replaceAll(RegExp(r'\bBrief\b', caseSensitive: false), '需求说明')
      .replaceAll(RegExp(r'Canonical Data', caseSensitive: false), '正式业务数据')
      .replaceAll(RegExp(r'\bCanonical\b', caseSensitive: false), '正式记录')
      .replaceAll(RegExp(r'\bSVG\b', caseSensitive: false), '矢量图')
      .replaceAll(RegExp(r'\bArtifact\b', caseSensitive: false), '成果')
      .replaceAll(RegExp(r'(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])'), '');
  return _safeBusinessCopy(normalized) ?? '';
}

String _capabilityName(BuildContext context, String name) =>
    _safeBusinessCopy(name) ?? context.lumenisL10n.text('sh01.detail.empty');

String _catalogTitle(BuildContext context, String _) =>
    context.lumenisL10n.text('sh01.charter.title');

class Sh01Screen extends StatefulWidget {
  const Sh01Screen({
    required this.client,
    this.repository,
    this.invokingDomain,
    this.contextAvailable = true,
    super.key,
  });

  final LumenisCoreClient client;
  final Sh01Repository? repository;
  final String? invokingDomain;
  final bool contextAvailable;

  @override
  State<Sh01Screen> createState() => _Sh01ScreenState();
}

class _Sh01ScreenState extends State<Sh01Screen> {
  String? _editing;
  late final Sh01ViewModel _viewModel = Sh01ViewModel(
    repository: widget.repository ?? CoreSh01Repository(client: widget.client),
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
  Widget build(BuildContext context) => _editing == 'writing'
      ? ManuscriptEditor(
          client: widget.client,
          invokingDomain: widget.invokingDomain,
          contextAvailable: widget.contextAvailable,
          onBack: () => setState(() => _editing = null),
        )
      : _editing != null
      ? MediaProjectWorkbench(
          client: widget.client,
          invokingDomain: widget.invokingDomain,
          contextAvailable: widget.contextAvailable,
          initialOutputKind: _editing == 'audio' ? 'audio' : 'video',
          onBack: () => setState(() => _editing = null),
        )
      : ColoredBox(
          color: LumenisTheme.of(context).canvas,
          child: SafeArea(
            child: Column(
              children: [
                Align(
                  alignment: Alignment.centerLeft,
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
                    child: Wrap(
                      spacing: 12,
                      runSpacing: 8,
                      children: [
                        OutlinedButton.icon(
                          key: const Key('sh01-open-manuscript-editor'),
                          onPressed: () => setState(() => _editing = 'writing'),
                          icon: const LumenisIcon(Icons.edit_note_rounded),
                          label: Text(switch (Localizations.localeOf(
                            context,
                          ).languageCode) {
                            'zh' => '写文稿',
                            'ko' => '문서 작성',
                            _ => 'Write a document',
                          }),
                        ),
                        OutlinedButton.icon(
                          key: const Key('sh01-open-video-editor'),
                          onPressed: () => setState(() => _editing = 'video'),
                          icon: const LumenisIcon(
                            Icons.video_collection_outlined,
                          ),
                          label: Text(
                            context.lumenisL10n.text('sh01.media.open'),
                          ),
                        ),
                        OutlinedButton.icon(
                          key: const Key('sh01-open-audio-editor'),
                          onPressed: () => setState(() => _editing = 'audio'),
                          icon: const LumenisIcon(
                            Icons.multitrack_audio_rounded,
                          ),
                          label: Text(switch (Localizations.localeOf(
                            context,
                          ).languageCode) {
                            'zh' => '编辑音频',
                            'ko' => '오디오 편집',
                            _ => 'Edit audio',
                          }),
                        ),
                      ],
                    ),
                  ),
                ),
                Expanded(
                  child: AnimatedBuilder(
                    animation: _viewModel,
                    builder: (context, _) => switch (_viewModel.phase) {
                      Sh01LoadPhase.loading => const _LoadingState(),
                      Sh01LoadPhase.failed => _FailureState(
                        messageKey: _catalogFailureCopy(_viewModel.error),
                        onRetry: _viewModel.refresh,
                      ),
                      Sh01LoadPhase.ready => _Workspace(
                        viewModel: _viewModel,
                        catalog: _viewModel.catalog!,
                      ),
                    },
                  ),
                ),
              ],
            ),
          ),
        );
}

class _Workspace extends StatelessWidget {
  const _Workspace({required this.viewModel, required this.catalog});

  final Sh01ViewModel viewModel;
  final Sh01Catalog catalog;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, constraints) {
      final wide = constraints.maxWidth >= 1120;
      final medium = constraints.maxWidth >= 760;
      final inset = wide ? 30.0 : 18.0;
      final index = _CapabilityIndex(
        catalog: catalog,
        selected: viewModel.selected,
        onSelect: viewModel.select,
      );
      final detail = _CapabilityDetail(
        capability: viewModel.selected,
        hasTools: catalog.skills.isNotEmpty,
      );
      return Align(
        alignment: Alignment.topCenter,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1480),
          child: SingleChildScrollView(
            padding: EdgeInsets.fromLTRB(inset, 24, inset, 36),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const _Heading(),
                const SizedBox(height: 22),
                if (wide)
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      SizedBox(
                        width: 270,
                        child: _SharedCharter(catalog: catalog),
                      ),
                      const SizedBox(width: 16),
                      SizedBox(width: 365, child: index),
                      const SizedBox(width: 16),
                      Expanded(child: detail),
                    ],
                  )
                else if (medium)
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      SizedBox(
                        width: 260,
                        child: _SharedCharter(catalog: catalog),
                      ),
                      const SizedBox(width: 14),
                      Expanded(child: index),
                    ],
                  )
                else ...[
                  _SharedCharter(catalog: catalog),
                  const SizedBox(height: 14),
                  index,
                ],
                if (!wide && viewModel.selected != null) ...[
                  const SizedBox(height: 14),
                  detail,
                ],
                const SizedBox(height: 14),
                const _EvidenceBoundary(),
                const SizedBox(height: 14),
                Align(
                  alignment: Alignment.centerLeft,
                  child: OutlinedButton.icon(
                    onPressed: viewModel.refresh,
                    icon: const Icon(Icons.refresh_rounded),
                    label: Text(context.lumenisL10n.text('sh01.refresh')),
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

class _Heading extends StatelessWidget {
  const _Heading();

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Row(
        children: [
          Container(
            width: 8,
            height: 28,
            decoration: BoxDecoration(
              color: LumenisTheme.of(context).shared,
              borderRadius: BorderRadius.circular(8),
            ),
          ),
          const SizedBox(width: 11),
          Text(
            context.lumenisL10n.text('sh01.eyebrow'),
            style: Theme.of(context).textTheme.labelSmall?.copyWith(
              color: LumenisTheme.of(context).shared,
              letterSpacing: 1,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
      const SizedBox(height: 13),
      Text(
        context.lumenisL10n.text('sh01.title'),
        style: Theme.of(context).textTheme.headlineMedium?.copyWith(
          color: LumenisTheme.of(context).foreground,
          fontWeight: FontWeight.w600,
          letterSpacing: -0.5,
        ),
      ),
      const SizedBox(height: 7),
      Text(
        context.lumenisL10n.text('sh01.subtitle'),
        style: Theme.of(
          context,
        ).textTheme.bodyMedium?.copyWith(color: LumenisTheme.of(context).muted),
      ),
    ],
  );
}

class _SharedCharter extends StatelessWidget {
  const _SharedCharter({required this.catalog});

  final Sh01Catalog catalog;

  @override
  Widget build(BuildContext context) => _Panel(
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _Eyebrow(context.lumenisL10n.text('sh01.charter.eyebrow')),
        const SizedBox(height: 16),
        Container(
          width: 52,
          height: 52,
          decoration: BoxDecoration(
            color: LumenisTheme.of(context).shared.withValues(alpha: 0.1),
            border: Border.all(
              color: LumenisTheme.of(context).shared.withValues(alpha: 0.35),
            ),
            borderRadius: BorderRadius.circular(15),
          ),
          child: Icon(
            Icons.hub_outlined,
            color: LumenisTheme.of(context).shared,
            size: 25,
          ),
        ),
        const SizedBox(height: 14),
        Text(
          _catalogTitle(context, catalog.capability),
          style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: 8),
        Text(
          context.lumenisL10n.text('sh01.charter.detail'),
          style: TextStyle(color: LumenisTheme.of(context).muted, height: 1.5),
        ),
        const SizedBox(height: 17),
        const Divider(height: 1),
        const SizedBox(height: 14),
        _Eyebrow(context.lumenisL10n.text('sh01.charter.products')),
        const SizedBox(height: 9),
        Wrap(
          spacing: 7,
          runSpacing: 7,
          children: [
            for (final consumer in catalog.consumers)
              _MetaChip(_consumerLabel(context, consumer)),
          ],
        ),
        const SizedBox(height: 16),
        Text(
          context.lumenisL10n.text('sh01.charter.note'),
          style: TextStyle(
            color: LumenisTheme.of(context).quiet,
            fontSize: 12,
            height: 1.5,
          ),
        ),
      ],
    ),
  );
}

class _CapabilityIndex extends StatelessWidget {
  const _CapabilityIndex({
    required this.catalog,
    required this.selected,
    required this.onSelect,
  });

  final Sh01Catalog catalog;
  final Sh01Capability? selected;
  final ValueChanged<Sh01Capability> onSelect;

  @override
  Widget build(BuildContext context) => _Panel(
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(
              child: _Eyebrow(context.lumenisL10n.text('sh01.index.title')),
            ),
            Text(
              catalog.skills.length.toString(),
              style: TextStyle(
                color: LumenisTheme.of(context).shared,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        if (catalog.skills.isEmpty)
          _InfoMessage(context.lumenisL10n.text('sh01.index.empty'))
        else
          for (final item in catalog.skills)
            _CapabilityRow(
              item: item,
              selected: selected?.id == item.id,
              onTap: () => onSelect(item),
            ),
      ],
    ),
  );
}

class _CapabilityRow extends StatelessWidget {
  const _CapabilityRow({
    required this.item,
    required this.selected,
    required this.onTap,
  });

  final Sh01Capability item;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 7),
    child: Material(
      color: selected
          ? LumenisTheme.of(context).shared.withValues(alpha: 0.09)
          : LumenisTheme.of(context).surfaceRaised,
      borderRadius: BorderRadius.circular(11),
      child: InkWell(
        key: Key('sh01-capability-${item.id}'),
        onTap: onTap,
        borderRadius: BorderRadius.circular(11),
        child: Container(
          constraints: const BoxConstraints(minHeight: 62),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          decoration: BoxDecoration(
            border: Border.all(
              color: selected
                  ? LumenisTheme.of(context).shared.withValues(alpha: 0.55)
                  : LumenisTheme.of(context).line,
            ),
            borderRadius: BorderRadius.circular(11),
          ),
          child: Row(
            children: [
              Container(
                width: 30,
                height: 30,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: LumenisTheme.of(context).canvas,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Icon(
                  Icons.extension_outlined,
                  size: 17,
                  color: selected
                      ? LumenisTheme.of(context).shared
                      : LumenisTheme.of(context).quiet,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      _capabilityName(context, item.name),
                      style: const TextStyle(fontWeight: FontWeight.w600),
                    ),
                    if (item.category.isNotEmpty) ...[
                      const SizedBox(height: 3),
                      Text(
                        _categoryLabel(context, item.category),
                        style: TextStyle(
                          color: LumenisTheme.of(context).muted,
                          fontSize: 11,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
              Icon(
                Icons.chevron_right_rounded,
                color: LumenisTheme.of(context).quiet,
              ),
            ],
          ),
        ),
      ),
    ),
  );
}

class _CapabilityDetail extends StatelessWidget {
  const _CapabilityDetail({required this.capability, required this.hasTools});

  final Sh01Capability? capability;
  final bool hasTools;

  @override
  Widget build(BuildContext context) => _Panel(
    child: capability == null
        ? _InfoMessage(
            context.lumenisL10n.text(
              hasTools ? 'sh01.detail.select' : 'sh01.detail.empty',
            ),
          )
        : _CapabilityFacts(capability: capability!),
  );
}

class _CapabilityFacts extends StatelessWidget {
  const _CapabilityFacts({required this.capability});

  final Sh01Capability capability;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Row(
        children: [
          Expanded(
            child: _Eyebrow(context.lumenisL10n.text('sh01.detail.title')),
          ),
        ],
      ),
      const SizedBox(height: 17),
      Text(
        _capabilityName(context, capability.name),
        style: Theme.of(context).textTheme.headlineSmall,
      ),
      if (_businessDescription(capability.description).isNotEmpty) ...[
        const SizedBox(height: 10),
        Text(
          _businessDescription(capability.description),
          style: TextStyle(color: LumenisTheme.of(context).muted, height: 1.6),
        ),
      ],
      const SizedBox(height: 22),
      _Eyebrow(context.lumenisL10n.text('sh01.detail.info')),
      const SizedBox(height: 11),
      _FactRow(
        context.lumenisL10n.text('sh01.detail.category'),
        _categoryLabel(context, capability.category),
      ),
      _FactRow(
        context.lumenisL10n.text('sh01.detail.products'),
        capability.consumers
            .map((consumer) => _consumerLabel(context, consumer))
            .join(' · '),
      ),
      _FactRow(
        context.lumenisL10n.text('sh01.detail.permission'),
        _permissionLabel(context, capability.permission),
      ),
      _FactRow(
        context.lumenisL10n.text('sh01.detail.risk'),
        _riskLabel(context, capability.risk),
      ),
      _FactRow(
        context.lumenisL10n.text('sh01.detail.limit'),
        _useLimitLabel(context, capability.executionPolicy),
      ),
      const SizedBox(height: 15),
      _InfoMessage(context.lumenisL10n.text('sh01.detail.note')),
    ],
  );
}

class _FactRow extends StatelessWidget {
  const _FactRow(this.label, this.value);

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    if (value.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 7),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 150,
            child: Text(
              label,
              style: TextStyle(color: LumenisTheme.of(context).quiet),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: SelectableText(
              value,
              style: TextStyle(color: LumenisTheme.of(context).foreground),
            ),
          ),
        ],
      ),
    );
  }
}

class _EvidenceBoundary extends StatelessWidget {
  const _EvidenceBoundary();

  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    padding: const EdgeInsets.all(16),
    decoration: BoxDecoration(
      color: LumenisTheme.of(context).caution.withValues(alpha: 0.07),
      border: Border.all(
        color: LumenisTheme.of(context).caution.withValues(alpha: 0.28),
      ),
      borderRadius: BorderRadius.circular(14),
    ),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(
          Icons.lock_outline_rounded,
          color: LumenisTheme.of(context).caution,
          size: 19,
        ),
        const SizedBox(width: 11),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                context.lumenisL10n.text('sh01.evidence.title'),
                style: TextStyle(fontWeight: FontWeight.w600),
              ),
              SizedBox(height: 5),
              Text(
                context.lumenisL10n.text('sh01.evidence.detail'),
                style: TextStyle(
                  color: LumenisTheme.of(context).muted,
                  height: 1.5,
                ),
              ),
            ],
          ),
        ),
      ],
    ),
  );
}

class _InfoMessage extends StatelessWidget {
  const _InfoMessage(this.message);

  final String message;

  @override
  Widget build(BuildContext context) => Text(
    message,
    style: TextStyle(color: LumenisTheme.of(context).muted, height: 1.5),
  );
}

class _MetaChip extends StatelessWidget {
  const _MetaChip(this.label);

  final String label;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 6),
    decoration: BoxDecoration(
      color: LumenisTheme.of(context).canvas,
      border: Border.all(color: LumenisTheme.of(context).line),
      borderRadius: BorderRadius.circular(20),
    ),
    child: Text(
      label,
      style: TextStyle(color: LumenisTheme.of(context).muted, fontSize: 11),
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
      color: LumenisTheme.of(context).quiet,
      fontSize: 10,
      letterSpacing: 0.9,
      fontWeight: FontWeight.w700,
    ),
  );
}

class _Panel extends StatelessWidget {
  const _Panel({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    padding: const EdgeInsets.all(18),
    decoration: BoxDecoration(
      color: LumenisTheme.of(context).surface,
      borderRadius: BorderRadius.circular(16),
      border: Border.all(color: LumenisTheme.of(context).line),
    ),
    child: child,
  );
}

class _LoadingState extends StatelessWidget {
  const _LoadingState();

  @override
  Widget build(BuildContext context) => Center(
    child: Semantics(
      liveRegion: true,
      label: context.lumenisL10n.text('sh01.loading'),
      child: CircularProgressIndicator(color: LumenisTheme.of(context).shared),
    ),
  );
}

class _FailureState extends StatelessWidget {
  const _FailureState({required this.messageKey, required this.onRetry});

  final String messageKey;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => Center(
    child: Padding(
      padding: const EdgeInsets.all(24),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 520),
        child: _Panel(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                context.lumenisL10n.text('sh01.failure.title'),
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 8),
              Text(
                context.lumenisL10n.text(messageKey),
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              const SizedBox(height: 16),
              OutlinedButton.icon(
                onPressed: onRetry,
                icon: const Icon(Icons.refresh_rounded),
                label: Text(context.lumenisL10n.text('sh01.failure.retry')),
                style: OutlinedButton.styleFrom(
                  minimumSize: const Size(48, 48),
                ),
              ),
            ],
          ),
        ),
      ),
    ),
  );
}
