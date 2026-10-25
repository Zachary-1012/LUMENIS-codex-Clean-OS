import 'dart:convert';

import 'package:flutter/material.dart';

import '../../../core/lumenis_botanical.dart';
import '../../../core/lumenis_core_client.dart';
import '../../../core/lumenis_theme.dart';
import '../../../navigation/lumenis_leave_guard.dart';

String collectionStatusText(BuildContext context, String? state) {
  final labels = switch (state?.toUpperCase()) {
    'SUCCESS' || 'VERIFIED' => ('已取得并保存', 'Collected and saved', '수집 후 저장됨'),
    'NO_NEW_DATA' => ('没有新增内容', 'No new content', '새 콘텐츠 없음'),
    'READY' => ('可以连接', 'Ready to connect', '연결 가능'),
    'CONFIGURED' => ('等待连接核实', 'Connection not verified', '연결 확인 대기'),
    'AUTH_REQUIRED' ||
    'SESSION_EXPIRED' ||
    'QR_REQUIRED' => ('需要重新登录', 'Sign in again', '다시 로그인 필요'),
    'NEED_VERIFY' || 'RISK_WARNING' => (
      '平台需要人工验证',
      'Platform verification required',
      '플랫폼 확인 필요',
    ),
    'BUSY' => ('正在处理另一项请求', 'Another request is running', '다른 요청 처리 중'),
    'RATE_LIMITED' ||
    'COOLING_DOWN' => ('请稍后再试', 'Please try later', '잠시 후 다시 시도'),
    'COMMENTS_PARTIAL' || 'PARTIAL' || 'PARTIAL_SOURCE_INTAKE_PENDING' => (
      '已取得部分内容',
      'Partial content collected',
      '일부 콘텐츠 수집됨',
    ),
    'APPROVAL_REQUIRED' => (
      '当前资料尚未获准采集',
      'Collection approval required',
      '수집 승인 필요',
    ),
    'SCOPE_UNAUTHORIZED' ||
    'DENIED' => ('当前范围无权访问', 'Access restricted in this scope', '현재 범위 접근 제한'),
    'NOT_SUPPORTED' ||
    'PLANNED' => ('此项尚不可用', 'This action is unavailable', '이 작업을 사용할 수 없음'),
    'NOT_CONFIGURED' => ('尚未连接', 'Not connected', '연결되지 않음'),
    'UNCONFIRMED' => (
      '结果尚未确认，请先查看已有资料',
      'Result unconfirmed. Check saved sources first.',
      '결과 미확인. 먼저 저장된 자료를 확인하세요.',
    ),
    'COLLECTION_WRITE_FAILED' || 'COLLECTION_COMMIT_UNVERIFIED' => (
      '保存未完成，请保留本次请求',
      'Saving is incomplete. Keep this request.',
      '저장 미완료. 요청을 유지하세요.',
    ),
    _ => ('暂时无法读取', 'Currently unavailable', '현재 읽을 수 없음'),
  };
  return switch (Localizations.localeOf(context).languageCode) {
    'en' => labels.$2,
    'ko' => labels.$3,
    _ => labels.$1,
  };
}

class CollectorRequestPanel extends StatefulWidget {
  const CollectorRequestPanel({
    super.key,
    required this.client,
    required this.onComplete,
  });
  final LumenisCoreClient client;
  final VoidCallback onComplete;
  @override
  State<CollectorRequestPanel> createState() => _CollectorRequestPanelState();
}

class _CollectorRequestPanelState extends State<CollectorRequestPanel> {
  final _query = TextEditingController();
  List<Map<String, dynamic>> _platforms = [];
  String? _platform, _domain, _status;
  String? _contextPin;
  bool _loading = true, _busy = false, _detail = false;
  int _limit = 20;
  Map<String, dynamic>? _result;
  LumenisLeaveGuard? _guard;
  String _t(String zh, String en, String ko) =>
      switch (Localizations.localeOf(context).languageCode) {
        'en' => en,
        'ko' => ko,
        _ => zh,
      };
  @override
  void initState() {
    super.initState();
    final selection = widget.client.currentContextEnvelope?['context'];
    if (selection is Map && selection['mode'] == 'FOCUS') {
      _domain = selection['domain_id']?.toString().toUpperCase();
    }
    _load();
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final guard = LumenisLeaveScope.maybeOf(context);
    if (!identical(guard, _guard)) {
      _guard?.unregister(this);
      _guard = guard;
      _guard?.register(
        this,
        needsProtection: () => _busy,
        requestLeave: () async => !_busy,
      );
    }
  }

  @override
  void dispose() {
    _guard?.unregister(this);
    _query.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final data = await widget.client.collectionSources();
      if (data['ok'] != true || data['platforms'] is! List) {
        throw const FormatException();
      }
      final rows = <Map<String, dynamic>>[];
      for (final raw in [
        data['primary_collection'],
        ...data['platforms'] as List,
      ]) {
        if (raw is! Map ||
            raw['platform'] is! String ||
            raw['name'] is! String) {
          continue;
        }
        final row = Map<String, dynamic>.from(raw);
        if (!rows.any((item) => item['platform'] == row['platform'])) {
          rows.add(row);
        }
      }
      if (!mounted) return;
      setState(() {
        _platforms = rows;
        _status = null;
        if (!_platforms.any((p) => p['platform'] == _platform)) {
          _platform = null;
        }
      });
    } catch (_) {
      if (mounted) setState(() => _status = 'UNAVAILABLE');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _run() async {
    if (_busy ||
        _platform == null ||
        _domain == null ||
        _query.text.trim().isEmpty) {
      return;
    }
    final pin = jsonEncode(widget.client.currentContextEnvelope);
    setState(() {
      _busy = true;
      _result = null;
      _status = null;
      _contextPin = pin;
    });
    _guard?.refresh();
    try {
      final result = await widget.client.collectSource(
        domainId: _domain!,
        platform: _platform!,
        query: _query.text,
        detail: _detail,
        limit: _limit,
      );
      if (!mounted) return;
      if (pin != jsonEncode(widget.client.currentContextEnvelope)) {
        setState(() {
          _result = null;
          _status = 'SCOPE_UNAUTHORIZED';
        });
      } else {
        setState(() {
          _result = result;
          _status = result['status'] as String?;
        });
      }
      widget.onComplete();
    } catch (error) {
      if (mounted) {
        setState(
          () => _status = error is LumenisCoreException
              ? error.errorCode ??
                    (error.statusCode == 403
                        ? 'SCOPE_UNAUTHORIZED'
                        : 'UNCONFIRMED')
              : 'UNCONFIRMED',
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
      _guard?.refresh();
    }
  }

  @override
  Widget build(BuildContext context) {
    final palette = LumenisTheme.of(context);
    final contextChanged =
        _contextPin != null &&
        _contextPin != jsonEncode(widget.client.currentContextEnvelope);
    final selected = _platforms
        .where((p) => p['platform'] == _platform)
        .firstOrNull;
    return DecoratedBox(
      decoration: LumenisTheme.paper(palette),
      child: Padding(
        padding: const EdgeInsets.all(22),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                const LumenisBotanical(plant: LumenisPlant.grape, size: 42),
                const SizedBox(width: 14),
                Expanded(
                  child: Text(
                    _t('获取资料', 'Collect sources', '자료 수집'),
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                ),
                IconButton(
                  onPressed: _loading || _busy ? null : _load,
                  tooltip: _t('更新连接状态', 'Refresh connections', '연결 상태 새로고침'),
                  icon: const Icon(Icons.refresh),
                ),
              ],
            ),
            const SizedBox(height: 20),
            if (_loading)
              const LinearProgressIndicator()
            else
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  for (final platform in _platforms)
                    ChoiceChip(
                      label: Text(platform['name'] as String),
                      selected: _platform == platform['platform'],
                      onSelected:
                          _busy || platform['manual_collection_enabled'] != true
                          ? null
                          : (_) => setState(
                              () => _platform = platform['platform'] as String,
                            ),
                    ),
                ],
              ),
            if (selected != null)
              Padding(
                padding: const EdgeInsets.only(top: 10),
                child: Text(
                  collectionStatusText(context, selected['status'] as String?),
                  style: TextStyle(color: palette.muted),
                ),
              ),
            const SizedBox(height: 20),
            Wrap(
              spacing: 16,
              runSpacing: 12,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                SizedBox(
                  width: 190,
                  child: DropdownButtonFormField<String>(
                    initialValue: _domain,
                    decoration: InputDecoration(
                      labelText: _t('用于', 'Use in', '사용할 영역'),
                    ),
                    items: [
                      DropdownMenuItem(
                        value: 'CTH',
                        child: Text(_t('商业运营', 'Commerce operations', '상업 운영')),
                      ),
                      DropdownMenuItem(
                        value: 'BMP',
                        child: Text(
                          _t('品牌与市场', 'Brand and market', '브랜드 및 시장'),
                        ),
                      ),
                    ],
                    onChanged: _busy
                        ? null
                        : (v) => setState(() => _domain = v),
                  ),
                ),
                SegmentedButton<bool>(
                  segments: [
                    ButtonSegment(
                      value: false,
                      icon: const Icon(Icons.search),
                      label: Text(_t('搜索', 'Search', '검색')),
                    ),
                    ButtonSegment(
                      value: true,
                      icon: const Icon(Icons.article_outlined),
                      label: Text(_t('原帖详情', 'Original post', '원문')),
                    ),
                  ],
                  selected: {_detail},
                  onSelectionChanged: _busy
                      ? null
                      : (v) => setState(() => _detail = v.single),
                ),
                if (!_detail)
                  SizedBox(
                    width: 120,
                    child: DropdownButtonFormField<int>(
                      initialValue: _limit,
                      decoration: InputDecoration(
                        labelText: _t('本次数量', 'This request', '이번 수량'),
                      ),
                      items: [
                        for (final n in [10, 20, 50])
                          DropdownMenuItem(value: n, child: Text('$n')),
                      ],
                      onChanged: _busy
                          ? null
                          : (n) => setState(() => _limit = n!),
                    ),
                  ),
              ],
            ),
            const SizedBox(height: 18),
            TextField(
              controller: _query,
              enabled: !_busy,
              minLines: 1,
              maxLines: 3,
              onChanged: (_) => setState(() {}),
              onSubmitted: (_) => _run(),
              decoration: InputDecoration(
                labelText: _detail
                    ? _t('原帖链接或编号', 'Post URL or ID', '원문 링크 또는 번호')
                    : _t(
                        '关键词或公开网页链接',
                        'Keywords or a public page URL',
                        '검색어 또는 공개 웹페이지 링크',
                      ),
              ),
            ),
            const SizedBox(height: 14),
            Align(
              alignment: Alignment.centerRight,
              child: FilledButton.icon(
                onPressed:
                    _busy ||
                        _loading ||
                        _domain == null ||
                        selected == null ||
                        _query.text.trim().isEmpty
                    ? null
                    : _run,
                icon: const Icon(Icons.south_west),
                label: Text(
                  _busy
                      ? _t('正在获取…', 'Collecting…', '수집 중…')
                      : _t('获取', 'Collect', '수집'),
                ),
              ),
            ),
            if (_status != null || contextChanged) ...[
              const Divider(height: 28),
              Semantics(
                liveRegion: true,
                child: Text(
                  collectionStatusText(
                    context,
                    contextChanged ? 'SCOPE_UNAUTHORIZED' : _status,
                  ),
                ),
              ),
              if (_result != null && !contextChanged)
                Padding(
                  padding: const EdgeInsets.only(top: 12),
                  child: Wrap(
                    spacing: 24,
                    runSpacing: 8,
                    children: [
                      for (final item in [
                        ('returned_count', _t('取得', 'Retrieved', '가져옴')),
                        (
                          'canonical_synced',
                          _t('已存资料', 'Saved sources', '저장된 자료'),
                        ),
                        ('updated', _t('已更新', 'Updated', '갱신됨')),
                      ])
                        Text(
                          '${item.$2}  ${_result![item.$1] is num ? _result![item.$1] : '—'}',
                        ),
                    ],
                  ),
                ),
            ],
          ],
        ),
      ),
    );
  }
}
