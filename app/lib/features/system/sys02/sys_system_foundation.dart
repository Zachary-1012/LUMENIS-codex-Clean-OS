import 'dart:math' as math;
import 'package:flutter/material.dart';
import '../sys05/sys05_appearance_controller.dart';

import '../../../core/lumenis_icon.dart';

import '../../../core/lumenis_core_client.dart';
import '../../../core/lumenis_theme.dart';
import '../../../core/transport/lumenis_http_transport.dart';

enum WaitingScene { search, sources, compare, analysis, export, waiting }

enum SysLoadPhase { loading, ready, failed }

enum SysFailureKind { authentication, permissionDenied, offline, response }

SysFailureKind classifySysFailure(Object error) {
  final message = error.toString().toLowerCase();
  if (message.contains('http 401')) return SysFailureKind.authentication;
  if (message.contains('http 403')) return SysFailureKind.permissionDenied;
  if (isLumenisConnectionError(error) ||
      (error is LumenisCoreException &&
          (message.contains('core unavailable') ||
              message.contains('connection timed out')))) {
    return SysFailureKind.offline;
  }
  return SysFailureKind.response;
}

/// Feature-local copy keys keep this bounded batch independent from the shared
/// locale registry. The keys are intentionally stable so the later shell
/// integration can promote them without changing screen semantics.
abstract final class SysSystemCopy {
  static String text(BuildContext context, String key) {
    final language = Localizations.localeOf(context).languageCode;
    final localeKey = switch (language) {
      'en' => 'en',
      'ko' => 'ko',
      _ => 'zh-CN',
    };
    return _translations[localeKey]?[key] ??
        _translations['zh-CN']![key] ??
        key;
  }

  static const _translations = <String, Map<String, String>>{
    'zh-CN': {
      'sys.waiting.preference': '等待文案',
      'sys.waiting.playful': '轻松',
      'sys.waiting.simple': '简洁',
      'sys.waiting.off': '关闭附加文案',
      'sys.waiting.hint': '工作在继续，你可以先伸个懒腰。',
      'sys.waiting.neutral': '你可以继续查看其他工作。',
      'sys.common.loading': '正在读取系统状态',
      'sys.common.retry': '重新读取',
      'sys.common.refresh': '刷新',
      'sys.common.unavailable': '暂不可用',
      'sys.common.notCollected': '尚未提供',
      'sys.common.partial': '部分可用',
      'sys.common.offline': '离线',
      'sys.common.error': '读取失败',
      'sys.common.ready': '已确认',
      'sys.common.unknown': '状态未确认',
      'sys.common.readOnly': '只读查看，不改变系统事实',
      'sys.common.bindingUnavailable': '当前绑定尚未提供可核实结果',
      'sys.common.noData': '当前没有可展示的记录',
      'sys.common.source': '来源',
      'sys.common.trace': '观测编号',
      'sys.common.status': '状态',
      'sys.common.notReturned': '当前接口未返回',
      'sys.common.noAction': '当前没有已验证的操作契约',
      'sys.failure.auth.title': '需要验证访问',
      'sys.failure.auth.detail': '当前访问需要先完成身份验证。',
      'sys.failure.permission.title': '当前访问范围无法查看',
      'sys.failure.permission.detail': '当前账号没有查看这项系统状态的权限。',
      'sys.failure.offline.title': '系统服务暂不可用',
      'sys.failure.offline.detail': '暂时无法读取当前状态，请检查连接后重试。',
      'sys.failure.response.title': '系统状态暂不可用',
      'sys.failure.response.detail': '系统没有提供有效结果，请稍后重试。',
      'sys02.eyebrow': '系统 · 采集',
      'sys02.title': '获取资料',
      'sys02.summary.title': '采集记录',
      'sys02.manual.action': '手动采集',
      'sys02.manual.hint': '刷新时采集；定时采集需单独开启。',
      'sys02.manual.queued': '已提交手动采集，在系统后台运行。',
      'sys02.manual.failed': '手动采集未能提交，请稍后重试。',
      'sys02.subtitle': '查看调度、限流、重试与入链状态；未验证的采集不会被标为已运行。',
      'sys02.summary.active': '已确认连通',
      'sys02.summary.partial': '受限连通',
      'sys02.summary.missing': '缺少访问条件',
      'sys02.summary.blocked': '被安全策略阻断',
      'sys02.lanes.title': '来源连接',
      'sys02.lanes.detail': '每条线只呈现最近一次返回的状态，不把注册记录当作健康证明。',
      'sys02.lanes.empty': '当前接口没有返回平台运行线。',
      'sys02.field.platform': '平台',
      'sys02.field.status': '当前状态',
      'sys02.field.records': '已解析记录',
      'sys02.field.detail': '状态说明',
      'sys02.boundary.title': '入链边界',
      'sys02.boundary.detail':
          '采集失败停留在采集层；只有经过验证的记录才可进入 Evidence 与 Canonical Data。',
      'sys02.boundary.noActions': '重试、停止与补偿操作没有在当前契约中提供。',
      'sys02.source.title': '采集状态来源',
      'sys02.source.detail': '当前视图读取系统返回的采集状态汇总。',
      'sys03.eyebrow': '系统 · 数据事实',
      'sys03.title': '数据库与事实链',
      'sys03.subtitle':
          '把 schema、可读性、完整性与 Source → Evidence → Canonical 链路分开查看。',
      'sys03.validation.title': '验证脊柱',
      'sys03.validation.schema': 'Schema 版本记录',
      'sys03.validation.integrity': '完整性检查',
      'sys03.validation.readability': '应用可读性',
      'sys03.validation.detail': '迁移版本存在不等于应用能够安全读取。',
      'sys03.checks.title': '当前检查结果',
      'sys03.checks.empty': '当前接口没有返回完整性检查结果。',
      'sys03.chain.title': '事实链',
      'sys03.chain.source': 'Source',
      'sys03.chain.evidence': 'Evidence',
      'sys03.chain.canonical': 'Canonical Data',
      'sys03.chain.metric': 'Metric / ViewModel',
      'sys03.chain.unavailable': '事实链分层尚未由当前接口逐段返回。',
      'sys03.identity.title': '数据库身份',
      'sys03.identity.detail': '路径、连接细节和内部实现不在用户界面中回显。',
      'sys03.identity.state': '身份与隔离状态',
      'sys03.boundary': '数据库检查为只读；恢复与迁移需要独立的授权操作契约。',
      'sys04.eyebrow': '系统 · 安全边界',
      'sys04.title': '安全与权限',
      'sys04.subtitle': '查看访问姿态与安全边界；页面不替代服务端授权，也不回显秘密或策略内部细节。',
      'sys04.matrix.title': '访问姿态',
      'sys04.matrix.detail': '当前只显示可公开解释的权限层级，不显示原始策略表达式。',
      'sys04.field.level': '访问层级',
      'sys04.field.scope': '用户可见范围',
      'sys04.level.read': '读取',
      'sys04.level.task': '任务',
      'sys04.level.audit': '审计',
      'sys04.level.write': '写入',
      'sys04.level.deploy': '发布',
      'sys04.level.unknown': '未确认',
      'sys04.operations': '受控操作类型',
      'sys04.audit.title': '审计与决定',
      'sys04.audit.detail': '每次受保护操作仍由服务端重新验证 actor、domain、scope 与风险。',
      'sys04.audit.unavailable': '当前没有可显示的审计决定。',
      'sys04.boundary': '切换 Subject 只改变工作上下文，不授予访问权限。',
      'sys05.eyebrow': '系统 · 偏好',
      'sys05.title': '设置 / 外观 / 语言',
      'sys05.subtitle': '调整本地工作体验；偏好不改变业务数据、Subject、Evidence 或权限。',
      'sys05.appearance.title': '外观与动效',
      'sys05.preview.title': '即时预览',
      'sys05.preview.detail': '预览使用 SYSTEM 语义状态，不代表任何业务数据结果。',
      'sys05.field.theme': '主题',
      'sys05.field.optical': '光学密度',
      'sys05.field.density': '界面密度',
      'sys05.field.motion': '减弱动效',
      'sys05.field.locale': '界面语言',
      'sys05.system': '跟随系统',
      'sys05.light': '浅色',
      'sys05.dark': '深色',
      'sys05.low': '低',
      'sys05.balanced': '标准',
      'sys05.high': '高',
      'sys05.comfortable': '舒适',
      'sys05.compact': '紧凑',
      'sys05.on': '开启',
      'sys05.off': '关闭',
      'sys05.zh': '简体中文',
      'sys05.en': 'English',
      'sys05.ko': '한국어',
      'sys05.save': '保存本地偏好',
      'sys05.saved': '已保存到当前工作区状态',
      'sys05.reset': '恢复默认',
      'sys05.localOnly': '当前偏好绑定仍是本地工作区范围；跨重启持久化尚未由宿主契约确认。',
      'sys06.eyebrow': '系统 · 受控浏览',
      'sys06.title': '内部浏览器',
      'sys06.subtitle': '查看受控取证能力与边界；它不是个人浏览器，也不会回显身份材料。',
      'sys06.boundary.title': '能力边界',
      'sys06.boundary.detail': '当前只展示能力状态、实例数量与可验证的只读范围。',
      'sys06.boundary.allowed': '允许：在批准的采集规则内读取来源与元数据。',
      'sys06.boundary.blocked': '未提供：打开新标签、固定快照、结构化抽取等操作契约。',
      'sys06.instances': '受控实例',
      'sys06.online': '当前在线',
      'sys06.capabilities': '只读能力',
      'sys06.instances.title': '实例状态',
      'sys06.instance': '受控实例 {n}',
      'sys06.noInstances': '当前没有返回受控实例。',
      'sys06.status': '状态',
      'sys06.safe': '身份材料已隐藏',
      'sys06.source': '来源：系统浏览器能力报告；仅呈现经过筛选的状态字段。',
      'sys07.eyebrow': '系统 · 评估',
      'sys07.title': '验收评估',
      'sys07.subtitle': '只展示有真实结果和证据引用的检查；缺失、部分和未知都不会被判定为通过。',
      'sys07.posture.title': '当前评估姿态',
      'sys07.posture.unknown': '生产验收状态未由当前接口返回',
      'sys07.posture.ready': '检查结果已返回，但不等同于整套生产验收通过',
      'sys07.gates.title': '生产验收 Gate',
      'sys07.gates.empty': '当前接口没有返回带证据的生产验收 Gate。',
      'sys07.gates.detail': '没有完整 Gate 证据时，页面保持 UNKNOWN。',
      'sys07.checks.title': '已返回的真实检查',
      'sys07.checks.empty': '当前没有可核实的检查结果。',
      'sys07.field.check': '检查',
      'sys07.field.evidence': '证据引用',
      'sys07.skills': '已注册技能',
      'sys07.notPass': '未形成 PASS 结论',
      'sys07.source': '检查来源：当前 ViewModel 返回的真实安全/技能状态。',
      'sys08.eyebrow': '系统 · 观测',
      'sys08.title': '可观测 / 日志',
      'sys08.subtitle': '把日志清单、结构化记录与 Trace 关联分开；没有时序数据就不画吞吐或错误率图。',
      'sys08.trace.title': 'Trace 关联',
      'sys08.trace.unavailable': '当前接口没有返回 Trace waterfall 或关联记录。',
      'sys08.trace.detail': 'Trace ID 只有在真实日志记录返回时才显示。',
      'sys08.inventory.title': '日志清单',
      'sys08.files': '日志文件',
      'sys08.size': '日志体积',
      'sys08.entries': '结构化记录',
      'sys08.logs.title': '可查看记录',
      'sys08.logs.empty': '当前没有可展示的结构化日志。',
      'sys08.field.time': '时间',
      'sys08.field.level': '级别',
      'sys08.field.module': '模块',
      'sys08.field.message': '消息',
      'sys08.field.trace': 'Trace',
      'sys08.filter.all': '全部',
      'sys08.exportUnavailable': '日志导出尚未绑定可验证的权限与效果契约。',
      'sys08.safe': '敏感凭证、绝对路径与会话材料不会显示。',
    },
    'en': {
      'sys.waiting.preference': 'Waiting text',
      'sys.waiting.playful': 'Light',
      'sys.waiting.simple': 'Simple',
      'sys.waiting.off': 'No extra text',
      'sys.waiting.hint': 'Loading. You can continue with other work.',
      'sys.waiting.neutral': 'You can continue with other work.',
      'sys.common.loading': 'Reading system state',
      'sys.common.retry': 'Read again',
      'sys.common.refresh': 'Refresh',
      'sys.common.unavailable': 'Unavailable',
      'sys.common.notCollected': 'Not provided',
      'sys.common.partial': 'Partially available',
      'sys.common.offline': 'Offline',
      'sys.common.error': 'Read failed',
      'sys.common.ready': 'Confirmed',
      'sys.common.unknown': 'Unconfirmed',
      'sys.common.readOnly': 'Read only; system facts are not changed',
      'sys.common.bindingUnavailable': 'No verifiable result is bound yet',
      'sys.common.noData': 'No record is available to display',
      'sys.common.source': 'Source',
      'sys.common.trace': 'Observation reference',
      'sys.common.status': 'Status',
      'sys.common.notReturned': 'Not returned by the current endpoint',
      'sys.common.noAction': 'No verified operation contract is available',
      'sys.failure.auth.title': 'Access verification required',
      'sys.failure.auth.detail':
          'Verify access before reading this system state.',
      'sys.failure.permission.title': 'This access scope cannot view it',
      'sys.failure.permission.detail':
          'The current account is not allowed to view this system state.',
      'sys.failure.offline.title': 'System service unavailable',
      'sys.failure.offline.detail':
          'The current state cannot be read. Check the connection and retry.',
      'sys.failure.response.title': 'System state unavailable',
      'sys.failure.response.detail':
          'The system did not return a valid result. Try again later.',
      'sys02.eyebrow': 'SYSTEM · COLLECTION',
      'sys02.title': 'Collect sources',
      'sys02.summary.title': 'Collection history',
      'sys02.manual.action': 'Collect now',
      'sys02.manual.hint':
          'Collect on refresh. Scheduled collection is optional.',
      'sys02.manual.queued':
          'Manual collection queued in the system background.',
      'sys02.manual.failed':
          'Manual collection could not be queued. Try again later.',
      'sys02.subtitle':
          'Inspect scheduling, rate limits, retries and ingestion without treating registration as health.',
      'sys02.summary.active': 'Confirmed connected',
      'sys02.summary.partial': 'Partially connected',
      'sys02.summary.missing': 'Access condition missing',
      'sys02.summary.blocked': 'Policy blocked',
      'sys02.lanes.title': 'Connections',
      'sys02.lanes.detail':
          'Each lane shows only the latest returned state; registration is not health proof.',
      'sys02.lanes.empty': 'The current endpoint returned no platform lanes.',
      'sys02.field.platform': 'Platform',
      'sys02.field.status': 'Current state',
      'sys02.field.records': 'Parsed records',
      'sys02.field.detail': 'State detail',
      'sys02.boundary.title': 'Ingestion boundary',
      'sys02.boundary.detail':
          'A failed collection stays at the collection layer; only validated records may enter Evidence and Canonical Data.',
      'sys02.boundary.noActions':
          'Retry, stop and compensation actions are not present in the current contract.',
      'sys02.source.title': 'Collection status source',
      'sys02.source.detail':
          'This view reads the system-returned collection status summary.',
      'sys03.eyebrow': 'SYSTEM · DATA TRUTH',
      'sys03.title': 'Database and truth chain',
      'sys03.subtitle':
          'Separate schema, readability, integrity and the Source → Evidence → Canonical chain.',
      'sys03.validation.title': 'Validation spine',
      'sys03.validation.schema': 'Schema version records',
      'sys03.validation.integrity': 'Integrity checks',
      'sys03.validation.readability': 'Application readability',
      'sys03.validation.detail':
          'A migration version does not prove that the application can read safely.',
      'sys03.checks.title': 'Current checks',
      'sys03.checks.empty':
          'The current endpoint returned no integrity checks.',
      'sys03.chain.title': 'Truth chain',
      'sys03.chain.source': 'Source',
      'sys03.chain.evidence': 'Evidence',
      'sys03.chain.canonical': 'Canonical Data',
      'sys03.chain.metric': 'Metric / ViewModel',
      'sys03.chain.unavailable':
          'The current endpoint did not return each truth-chain stage.',
      'sys03.identity.title': 'Database identity',
      'sys03.identity.detail':
          'Paths, connection details and internal implementation are not echoed in the UI.',
      'sys03.identity.state': 'Identity and isolation state',
      'sys03.boundary':
          'Database inspection is read only; recovery and migration need a separately authorized contract.',
      'sys04.eyebrow': 'SYSTEM · SECURITY',
      'sys04.title': 'Security and permission',
      'sys04.subtitle':
          'Inspect access posture and boundaries; the screen never replaces server authorization or reveals secrets.',
      'sys04.matrix.title': 'Access posture',
      'sys04.matrix.detail':
          'Only user-explainable permission levels are shown, not raw policy expressions.',
      'sys04.field.level': 'Access level',
      'sys04.field.scope': 'User-visible scope',
      'sys04.level.read': 'Read',
      'sys04.level.task': 'Task',
      'sys04.level.audit': 'Audit',
      'sys04.level.write': 'Write',
      'sys04.level.deploy': 'Deploy',
      'sys04.level.unknown': 'Unconfirmed',
      'sys04.operations': 'Controlled operation types',
      'sys04.audit.title': 'Audit and decision',
      'sys04.audit.detail':
          'Protected operations re-check actor, domain, scope and risk on the server.',
      'sys04.audit.unavailable': 'No audit decision is available to display.',
      'sys04.boundary':
          'Changing a Subject changes working context; it does not grant access.',
      'sys05.eyebrow': 'SYSTEM · PREFERENCES',
      'sys05.title': 'Settings / appearance / language',
      'sys05.subtitle':
          'Tune the local work experience; preferences do not change business data, Subject, Evidence or permission.',
      'sys05.appearance.title': 'Appearance and motion',
      'sys05.preview.title': 'Live preview',
      'sys05.preview.detail':
          'The preview uses SYSTEM semantic states and is not a business-data result.',
      'sys05.field.theme': 'Theme',
      'sys05.field.optical': 'Optical density',
      'sys05.field.density': 'Interface density',
      'sys05.field.motion': 'Reduced motion',
      'sys05.field.locale': 'Interface language',
      'sys05.system': 'Follow system',
      'sys05.light': 'Light',
      'sys05.dark': 'Dark',
      'sys05.low': 'Low',
      'sys05.balanced': 'Balanced',
      'sys05.high': 'High',
      'sys05.comfortable': 'Comfortable',
      'sys05.compact': 'Compact',
      'sys05.on': 'On',
      'sys05.off': 'Off',
      'sys05.zh': 'Simplified Chinese',
      'sys05.en': 'English',
      'sys05.ko': '한국어',
      'sys05.save': 'Save local preference',
      'sys05.saved': 'Saved to the current workspace state',
      'sys05.reset': 'Restore defaults',
      'sys05.localOnly':
          'This preference binding is limited to the local workspace; cross-restart persistence is not confirmed by the host contract.',
      'sys06.eyebrow': 'SYSTEM · CONTROLLED BROWSER',
      'sys06.title': 'Internal browser',
      'sys06.subtitle':
          'Inspect controlled capture capability and boundaries; this is not personal browsing and identity material is not echoed.',
      'sys06.boundary.title': 'Capability boundary',
      'sys06.boundary.detail':
          'Only capability state, instance counts and verified read-only scope are shown.',
      'sys06.boundary.allowed':
          'Allowed: read source content and metadata inside approved capture rules.',
      'sys06.boundary.blocked':
          'Not bound: new tabs, evidence snapshots and structured extraction operations.',
      'sys06.instances': 'Controlled instances',
      'sys06.online': 'Online now',
      'sys06.capabilities': 'Read-only capabilities',
      'sys06.instances.title': 'Instance state',
      'sys06.instance': 'Controlled instance {n}',
      'sys06.noInstances': 'No controlled instance was returned.',
      'sys06.status': 'Status',
      'sys06.safe': 'Identity material hidden',
      'sys06.source':
          'Source: system browser capability report; only screened state fields are shown.',
      'sys07.eyebrow': 'SYSTEM · EVALUATION',
      'sys07.title': 'Evaluation and acceptance',
      'sys07.subtitle':
          'Show only checks with real outcomes and evidence references; missing, partial and unknown never pass.',
      'sys07.posture.title': 'Current evaluation posture',
      'sys07.posture.unknown':
          'Production acceptance state was not returned by the current endpoint',
      'sys07.posture.ready':
          'Checks were returned, but this is not a complete production-acceptance pass',
      'sys07.gates.title': 'Production acceptance gates',
      'sys07.gates.empty':
          'No evidence-backed production acceptance gate was returned.',
      'sys07.gates.detail':
          'Without complete gate evidence, the page remains UNKNOWN.',
      'sys07.checks.title': 'Returned real checks',
      'sys07.checks.empty': 'No verifiable check result is available.',
      'sys07.field.check': 'Check',
      'sys07.field.evidence': 'Evidence reference',
      'sys07.skills': 'Registered skills',
      'sys07.notPass': 'No PASS conclusion formed',
      'sys07.source':
          'Check source: real security/skill status returned by the current ViewModel.',
      'sys08.eyebrow': 'SYSTEM · OBSERVABILITY',
      'sys08.title': 'Observability and logs',
      'sys08.subtitle':
          'Separate log inventory, structured records and Trace correlation; no time-series means no throughput or error-rate chart.',
      'sys08.trace.title': 'Trace correlation',
      'sys08.trace.unavailable':
          'No Trace waterfall or correlated record was returned.',
      'sys08.trace.detail':
          'A Trace ID is shown only when a real log record returns one.',
      'sys08.inventory.title': 'Log inventory',
      'sys08.files': 'Log files',
      'sys08.size': 'Log volume',
      'sys08.entries': 'Structured records',
      'sys08.logs.title': 'Viewable records',
      'sys08.logs.empty': 'No structured log is available to display.',
      'sys08.field.time': 'Time',
      'sys08.field.level': 'Level',
      'sys08.field.module': 'Module',
      'sys08.field.message': 'Message',
      'sys08.field.trace': 'Trace',
      'sys08.filter.all': 'All',
      'sys08.exportUnavailable':
          'Log export has no verified permission and effect contract yet.',
      'sys08.safe':
          'Credentials, absolute paths and session material are never displayed.',
    },
    'ko': {
      'sys.waiting.preference': '대기 문구',
      'sys.waiting.playful': '가볍게',
      'sys.waiting.simple': '간결하게',
      'sys.waiting.off': '추가 문구 끄기',
      'sys.waiting.hint': '불러오는 중입니다. 다른 작업을 계속할 수 있습니다.',
      'sys.waiting.neutral': '다른 작업을 계속할 수 있습니다.',
      'sys.common.loading': '시스템 상태를 읽는 중',
      'sys.common.retry': '다시 읽기',
      'sys.common.refresh': '새로 고침',
      'sys.common.unavailable': '사용할 수 없음',
      'sys.common.notCollected': '제공되지 않음',
      'sys.common.partial': '일부 사용 가능',
      'sys.common.offline': '오프라인',
      'sys.common.error': '읽기 실패',
      'sys.common.ready': '확인됨',
      'sys.common.unknown': '확인되지 않음',
      'sys.common.readOnly': '읽기 전용이며 시스템 사실을 변경하지 않습니다',
      'sys.common.bindingUnavailable': '확인 가능한 결과가 아직 연결되지 않았습니다',
      'sys.common.noData': '표시할 기록이 없습니다',
      'sys.common.source': '출처',
      'sys.common.trace': '관측 참조',
      'sys.common.status': '상태',
      'sys.common.notReturned': '현재 엔드포인트가 반환하지 않음',
      'sys.common.noAction': '확인된 작업 계약이 없습니다',
      'sys.failure.auth.title': '접근 확인 필요',
      'sys.failure.auth.detail': '시스템 상태를 읽기 전에 접근을 확인하세요.',
      'sys.failure.permission.title': '현재 접근 범위에서 볼 수 없음',
      'sys.failure.permission.detail': '현재 계정에는 이 시스템 상태를 볼 권한이 없습니다.',
      'sys.failure.offline.title': '시스템 서비스를 사용할 수 없음',
      'sys.failure.offline.detail': '현재 상태를 읽을 수 없습니다. 연결을 확인하고 다시 시도하세요.',
      'sys.failure.response.title': '시스템 상태를 사용할 수 없음',
      'sys.failure.response.detail': '시스템이 유효한 결과를 반환하지 않았습니다. 나중에 다시 시도하세요.',
      'sys02.eyebrow': 'SYSTEM · 수집',
      'sys02.title': '자료 수집',
      'sys02.summary.title': '수집 기록',
      'sys02.manual.action': '수동 수집',
      'sys02.manual.hint': '새로고침할 때 수집합니다. 예약 수집은 별도로 설정합니다.',
      'sys02.manual.queued': '수동 수집이 시스템 백그라운드에 등록되었습니다.',
      'sys02.manual.failed': '수동 수집을 등록하지 못했습니다. 잠시 후 다시 시도하세요.',
      'sys02.subtitle': '스케줄, 제한, 재시도와 체인 유입을 확인하며 등록 상태를 정상으로 표시하지 않습니다.',
      'sys02.summary.active': '연결 확인',
      'sys02.summary.partial': '부분 연결',
      'sys02.summary.missing': '접근 조건 없음',
      'sys02.summary.blocked': '정책 차단',
      'sys02.lanes.title': '출처 연결',
      'sys02.lanes.detail': '각 라인은 마지막 반환 상태만 표시하며 등록은 정상 증명이 아닙니다.',
      'sys02.lanes.empty': '현재 엔드포인트가 플랫폼 실행 라인을 반환하지 않았습니다.',
      'sys02.field.platform': '플랫폼',
      'sys02.field.status': '현재 상태',
      'sys02.field.records': '해석된 기록',
      'sys02.field.detail': '상태 설명',
      'sys02.boundary.title': '체인 유입 경계',
      'sys02.boundary.detail':
          '수집 실패는 수집 계층에 남으며 검증된 기록만 Evidence와 Canonical Data로 들어갑니다.',
      'sys02.boundary.noActions': '현재 계약에는 재시도, 중지와 보상 작업이 없습니다.',
      'sys02.source.title': '수집 상태 출처',
      'sys02.source.detail': '이 화면은 시스템이 반환한 수집 상태 요약을 읽습니다.',
      'sys03.eyebrow': 'SYSTEM · 데이터 사실',
      'sys03.title': '데이터베이스와 사실 체인',
      'sys03.subtitle':
          '스키마, 가독성, 무결성과 Source → Evidence → Canonical 체인을 분리합니다.',
      'sys03.validation.title': '검증 흐름',
      'sys03.validation.schema': '스키마 버전 기록',
      'sys03.validation.integrity': '무결성 검사',
      'sys03.validation.readability': '애플리케이션 가독성',
      'sys03.validation.detail': '마이그레이션 버전은 애플리케이션이 안전하게 읽는다는 뜻이 아닙니다.',
      'sys03.checks.title': '현재 검사 결과',
      'sys03.checks.empty': '현재 엔드포인트가 무결성 검사 결과를 반환하지 않았습니다.',
      'sys03.chain.title': '사실 체인',
      'sys03.chain.source': 'Source',
      'sys03.chain.evidence': 'Evidence',
      'sys03.chain.canonical': 'Canonical Data',
      'sys03.chain.metric': 'Metric / ViewModel',
      'sys03.chain.unavailable': '현재 엔드포인트가 사실 체인의 각 단계를 반환하지 않았습니다.',
      'sys03.identity.title': '데이터베이스 식별',
      'sys03.identity.detail': '경로, 연결 세부 정보와 내부 구현은 화면에 표시하지 않습니다.',
      'sys03.identity.state': '식별과 격리 상태',
      'sys03.boundary': '데이터베이스 검사는 읽기 전용이며 복구와 마이그레이션은 별도 승인 계약이 필요합니다.',
      'sys04.eyebrow': 'SYSTEM · 보안 경계',
      'sys04.title': '보안과 권한',
      'sys04.subtitle': '접근 상태와 경계를 확인하며 서버 권한을 대체하거나 비밀을 노출하지 않습니다.',
      'sys04.matrix.title': '접근 상태',
      'sys04.matrix.detail': '사용자가 이해할 수 있는 권한 수준만 표시하고 원시 정책 표현식은 숨깁니다.',
      'sys04.field.level': '접근 수준',
      'sys04.field.scope': '사용자에게 보이는 범위',
      'sys04.level.read': '읽기',
      'sys04.level.task': '작업',
      'sys04.level.audit': '감사',
      'sys04.level.write': '쓰기',
      'sys04.level.deploy': '배포',
      'sys04.level.unknown': '미확인',
      'sys04.operations': '제어되는 작업 유형',
      'sys04.audit.title': '감사와 결정',
      'sys04.audit.detail': '보호된 작업은 서버에서 actor, domain, scope와 위험을 다시 확인합니다.',
      'sys04.audit.unavailable': '표시할 감사 결정이 없습니다.',
      'sys04.boundary': 'Subject 변경은 작업 맥락만 바꾸며 접근 권한을 주지 않습니다.',
      'sys05.eyebrow': 'SYSTEM · 환경 설정',
      'sys05.title': '설정 / 외관 / 언어',
      'sys05.subtitle':
          '로컬 작업 경험을 조정하며 비즈니스 데이터, Subject, Evidence와 권한은 바꾸지 않습니다.',
      'sys05.appearance.title': '외관과 모션',
      'sys05.preview.title': '즉시 미리보기',
      'sys05.preview.detail': '미리보기는 SYSTEM 의미 상태를 사용하며 비즈니스 결과가 아닙니다.',
      'sys05.field.theme': '테마',
      'sys05.field.optical': '광학 밀도',
      'sys05.field.density': '화면 밀도',
      'sys05.field.motion': '동작 줄이기',
      'sys05.field.locale': '화면 언어',
      'sys05.system': '시스템 따르기',
      'sys05.light': '라이트',
      'sys05.dark': '다크',
      'sys05.low': '낮음',
      'sys05.balanced': '표준',
      'sys05.high': '높음',
      'sys05.comfortable': '편안함',
      'sys05.compact': '간결함',
      'sys05.on': '켜기',
      'sys05.off': '끄기',
      'sys05.zh': '简体中文',
      'sys05.en': 'English',
      'sys05.ko': '한국어',
      'sys05.save': '로컬 환경 설정 저장',
      'sys05.saved': '현재 작업 공간 상태에 저장됨',
      'sys05.reset': '기본값 복원',
      'sys05.localOnly':
          '이 환경 설정은 로컬 작업 공간에 한정되며 재시작 후 지속성은 호스트 계약으로 확인되지 않았습니다.',
      'sys06.eyebrow': 'SYSTEM · 제어 브라우저',
      'sys06.title': '내부 브라우저',
      'sys06.subtitle': '제어된 캡처 능력과 경계를 확인하며 개인 브라우징이나 신원 자료를 표시하지 않습니다.',
      'sys06.boundary.title': '능력 경계',
      'sys06.boundary.detail': '능력 상태, 인스턴스 수와 확인된 읽기 전용 범위만 표시합니다.',
      'sys06.boundary.allowed': '허용: 승인된 캡처 규칙 안에서 출처와 메타데이터 읽기.',
      'sys06.boundary.blocked': '연결되지 않음: 새 탭, 증거 스냅샷과 구조화 추출 작업.',
      'sys06.instances': '제어 인스턴스',
      'sys06.online': '현재 온라인',
      'sys06.capabilities': '읽기 전용 능력',
      'sys06.instances.title': '인스턴스 상태',
      'sys06.instance': '제어 인스턴스 {n}',
      'sys06.noInstances': '제어 인스턴스가 반환되지 않았습니다.',
      'sys06.status': '상태',
      'sys06.safe': '신원 자료 숨김',
      'sys06.source': '출처: 시스템 브라우저 능력 보고서; 선별한 상태 필드만 표시합니다.',
      'sys07.eyebrow': 'SYSTEM · 평가',
      'sys07.title': '평가와 어셉턴스',
      'sys07.subtitle': '실제 결과와 증거 참조가 있는 검사만 표시하며 누락, 부분과 미확인은 통과하지 않습니다.',
      'sys07.posture.title': '현재 평가 상태',
      'sys07.posture.unknown': '현재 엔드포인트가 생산 어셉턴스 상태를 반환하지 않았습니다',
      'sys07.posture.ready': '검사 결과는 반환되었지만 전체 생산 어셉턴스 통과는 아닙니다',
      'sys07.gates.title': '생산 어셉턴스 Gate',
      'sys07.gates.empty': '증거가 있는 생산 어셉턴스 Gate가 반환되지 않았습니다.',
      'sys07.gates.detail': '완전한 Gate 증거가 없으면 화면은 UNKNOWN으로 남습니다.',
      'sys07.checks.title': '반환된 실제 검사',
      'sys07.checks.empty': '확인 가능한 검사 결과가 없습니다.',
      'sys07.field.check': '검사',
      'sys07.field.evidence': '증거 참조',
      'sys07.skills': '등록된 스킬',
      'sys07.notPass': 'PASS 결론 없음',
      'sys07.source': '검사 출처: 현재 ViewModel이 반환한 실제 보안/스킬 상태.',
      'sys08.eyebrow': 'SYSTEM · 관측',
      'sys08.title': '옵저버빌리티와 로그',
      'sys08.subtitle':
          '로그 목록, 구조화 기록과 Trace 연계를 분리하며 시계열이 없으면 처리량이나 오류율 차트를 그리지 않습니다.',
      'sys08.trace.title': 'Trace 연계',
      'sys08.trace.unavailable': 'Trace waterfall이나 연결된 기록이 반환되지 않았습니다.',
      'sys08.trace.detail': '실제 로그 기록에 Trace ID가 있을 때만 표시합니다.',
      'sys08.inventory.title': '로그 목록',
      'sys08.files': '로그 파일',
      'sys08.size': '로그 용량',
      'sys08.entries': '구조화 기록',
      'sys08.logs.title': '열람 가능한 기록',
      'sys08.logs.empty': '표시할 구조화 로그가 없습니다.',
      'sys08.field.time': '시간',
      'sys08.field.level': '등급',
      'sys08.field.module': '모듈',
      'sys08.field.message': '메시지',
      'sys08.field.trace': 'Trace',
      'sys08.filter.all': '전체',
      'sys08.exportUnavailable': '로그 내보내기에 확인된 권한과 효과 계약이 없습니다.',
      'sys08.safe': '자격 증명, 절대 경로와 세션 자료는 표시하지 않습니다.',
    },
  };
}

Map<String, Object?> sysMap(Object? value) {
  if (value is Map) {
    return value.map((key, value) => MapEntry('$key', value));
  }
  return <String, Object?>{};
}

List<Map<String, Object?>> sysMapList(Object? value) {
  if (value is! List) return const [];
  return value.map(sysMap).where((item) => item.isNotEmpty).toList();
}

String? sysString(Object? value) {
  if (value is! String) return null;
  final trimmed = value.trim();
  return trimmed.isEmpty ? null : trimmed;
}

int? sysInt(Object? value) => value is int && value >= 0 ? value : null;

Map<String, Object?>? sysSection(
  List<Map<String, Object?>> sections,
  String type,
) {
  for (final section in sections) {
    if (section['type'] == type) return section;
  }
  return null;
}

String sysSafeDisplay(Object? value, {String fallback = '—'}) {
  final text = sysString(value);
  if (text == null) return fallback;
  final sensitive = RegExp(
    r'(cookie|token|session|authorization|password|secret|profile|cdp|[A-Za-z]:\\|/Users/|/home/|/var/)',
    caseSensitive: false,
  );
  return sensitive.hasMatch(text) ? fallback : text;
}

Color sysStatusColor(String state, {required LumenisPalette palette}) {
  return switch (state.toLowerCase()) {
    'ready' || 'ok' || 'active' || 'success' || 'online' => palette.positive,
    'warning' ||
    'warn' ||
    'partial' ||
    'degraded' ||
    'pending' => palette.caution,
    'error' || 'offline' || 'blocked' || 'danger' || 'bad' => palette.danger,
    _ => palette.quiet,
  };
}

class SysPanel extends StatelessWidget {
  const SysPanel({required this.child, this.title, this.detail, super.key});

  final Widget child;
  final String? title;
  final String? detail;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: LumenisTheme.paper(LumenisTheme.of(context)),
      child: Padding(
        padding: const EdgeInsets.all(LumenisSpace.section),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (title != null) ...[
              Text(title!, style: Theme.of(context).textTheme.titleMedium),
              if (detail != null) ...[
                const SizedBox(height: LumenisSpace.tight),
                Text(
                  detail!,
                  style: TextStyle(
                    color: LumenisTheme.of(context).muted,
                    height: 1.45,
                  ),
                ),
              ],
              const SizedBox(height: LumenisSpace.section),
            ],
            child,
          ],
        ),
      ),
    );
  }
}

class SysPageHeader extends StatelessWidget {
  const SysPageHeader({
    required this.eyebrow,
    required this.title,
    required this.subtitle,
    this.onRefresh,
    super.key,
  });

  final String eyebrow;
  final String title;
  final String subtitle;
  final VoidCallback? onRefresh;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: Theme.of(context).textTheme.headlineMedium),
              if (subtitle.trim().isNotEmpty) ...[
                const SizedBox(height: LumenisSpace.inset),
                ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 760),
                  child: Text(
                    subtitle,
                    style: TextStyle(
                      color: LumenisTheme.of(context).muted,
                      height: 1.5,
                    ),
                  ),
                ),
              ],
            ],
          ),
        ),
        if (onRefresh != null)
          IconButton(
            tooltip: SysSystemCopy.text(context, 'sys.common.refresh'),
            onPressed: onRefresh,
            icon: const LumenisIcon(Icons.refresh_rounded),
          ),
      ],
    );
  }
}

class SysStatusBadge extends StatelessWidget {
  const SysStatusBadge({required this.state, required this.label, super.key});

  final String state;
  final String label;

  @override
  Widget build(BuildContext context) {
    final color = sysStatusColor(state, palette: LumenisTheme.of(context));
    return Semantics(
      label: '${SysSystemCopy.text(context, 'sys.common.status')}: $label',
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: ShapeDecoration(
          color: color.withValues(alpha: 0.11),
          shape: LumenisPixelBorder(
            step: 2,
            side: BorderSide(color: color.withValues(alpha: 0.42)),
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            SizedBox.square(dimension: 4, child: ColoredBox(color: color)),
            const SizedBox(width: LumenisSpace.tight),
            Text(
              label,
              style: TextStyle(
                color: color,
                fontSize: 12,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class SysLoadingView extends StatelessWidget {
  const SysLoadingView({required this.titleKey, super.key});

  final String titleKey;

  @override
  Widget build(BuildContext context) {
    final copy = SysSystemCopy.text(context, titleKey);
    return Semantics(
      liveRegion: true,
      label: copy,
      excludeSemantics: true,
      child: Align(
        alignment: Alignment.topCenter,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 760),
          child: Padding(
            padding: const EdgeInsets.all(28),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  copy,
                  style: TextStyle(
                    color: LumenisTheme.of(context).foreground,
                    fontSize: 22,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 18),
                const WaitingFeedback(scene: WaitingScene.waiting),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class SysFailureView extends StatelessWidget {
  const SysFailureView({required this.kind, required this.onRetry, super.key});

  final SysFailureKind kind;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final titleKey = switch (kind) {
      SysFailureKind.authentication => 'sys.failure.auth.title',
      SysFailureKind.permissionDenied => 'sys.failure.permission.title',
      SysFailureKind.offline => 'sys.failure.offline.title',
      SysFailureKind.response => 'sys.failure.response.title',
    };
    final detailKey = switch (kind) {
      SysFailureKind.authentication => 'sys.failure.auth.detail',
      SysFailureKind.permissionDenied => 'sys.failure.permission.detail',
      SysFailureKind.offline => 'sys.failure.offline.detail',
      SysFailureKind.response => 'sys.failure.response.detail',
    };
    final retryable =
        kind == SysFailureKind.offline || kind == SysFailureKind.response;
    return Align(
      alignment: Alignment.topCenter,
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 760),
        child: Padding(
          padding: const EdgeInsets.all(28),
          child: SysPanel(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Semantics(
                  liveRegion: true,
                  child: Text(
                    SysSystemCopy.text(context, titleKey),
                    style: TextStyle(
                      color: LumenisTheme.of(context).foreground,
                      fontSize: 22,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
                const SizedBox(height: 10),
                Text(
                  SysSystemCopy.text(context, detailKey),
                  style: TextStyle(
                    color: LumenisTheme.of(context).muted,
                    height: 1.5,
                  ),
                ),
                if (retryable) ...[
                  const SizedBox(height: 20),
                  FilledButton.tonal(
                    onPressed: onRetry,
                    child: Text(
                      SysSystemCopy.text(context, 'sys.common.retry'),
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class SysMetricLine extends StatelessWidget {
  const SysMetricLine({
    required this.label,
    required this.value,
    required this.state,
    super.key,
  });

  final String label;
  final Object? value;
  final String state;

  @override
  Widget build(BuildContext context) {
    final hasValue = value != null;
    final display = hasValue
        ? '$value'
        : SysSystemCopy.text(context, 'sys.common.unavailable');
    return Expanded(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14),
        child: Semantics(
          label: '$label: $display',
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                label,
                style: TextStyle(
                  color: LumenisTheme.of(context).muted,
                  height: 1.35,
                ),
              ),
              const SizedBox(height: 6),
              Text(
                display,
                style: TextStyle(
                  color: hasValue
                      ? sysStatusColor(state, palette: LumenisTheme.of(context))
                      : LumenisTheme.of(context).quiet,
                  fontSize: 24,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Supplemental decoration only. The caller owns authoritative status and actions.
class WaitingFeedback extends StatelessWidget {
  const WaitingFeedback({required this.scene, super.key});
  final WaitingScene scene;
  static const _jokes = <WaitingScene, String>{
    WaitingScene.search: '在找资料，暂时不找借口。',
    WaitingScene.sources: '让资料排好队，别再开会排队。',
    WaitingScene.compare: '方案可以多，选项别打架。',
    WaitingScene.analysis: '把线索理清，比把锅甩清重要。',
    WaitingScene.export: '正在收尾，希望这版不用叫“最终版7”。',
    WaitingScene.waiting: '工作在继续，你可以先伸个懒腰。',
  };
  @override
  Widget build(BuildContext context) {
    final appearance = Sys05AppearanceScope.maybeOf(context);
    final tone = appearance?.waitingTone ?? WaitingTone.simple;
    final reduced =
        appearance?.reducedMotion == true ||
        MediaQuery.maybeOf(context)?.disableAnimations == true;
    // English/Korean deliberately use neutral copy pending editorial review.
    final playfulChinese =
        tone == WaitingTone.playful &&
        Localizations.localeOf(context).languageCode == 'zh';
    return ExcludeSemantics(
      child: IgnorePointer(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _WaitingPaper(reduced: reduced, scene: scene),
            if (tone != WaitingTone.off) ...[
              const SizedBox(height: 8),
              Text(
                playfulChinese
                    ? _jokes[scene]!
                    : SysSystemCopy.text(context, 'sys.waiting.neutral'),
                key: const ValueKey('sys/waiting-extra-text'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _WaitingPaper extends StatefulWidget {
  const _WaitingPaper({required this.reduced, required this.scene});
  final bool reduced;
  final WaitingScene scene;
  @override
  State<_WaitingPaper> createState() => _WaitingPaperState();
}

class _WaitingPaperState extends State<_WaitingPaper>
    with SingleTickerProviderStateMixin, WidgetsBindingObserver {
  late final AnimationController _motion;
  bool _foreground = true;
  @override
  void initState() {
    super.initState();
    _motion = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1800),
    );
    _foreground =
        WidgetsBinding.instance.lifecycleState == null ||
        WidgetsBinding.instance.lifecycleState == AppLifecycleState.resumed;
    WidgetsBinding.instance.addObserver(this);
  }

  void _sync() {
    if (!widget.reduced &&
        _foreground &&
        TickerMode.valuesOf(context).enabled) {
      if (!_motion.isAnimating) _motion.repeat(reverse: true);
    } else {
      _motion.stop();
      _motion.value = 0;
    }
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _sync();
  }

  @override
  void didUpdateWidget(covariant _WaitingPaper oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.scene != widget.scene) _motion.value = 0;
    _sync();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    _foreground = state == AppLifecycleState.resumed;
    _sync();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _motion.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
    animation: _motion,
    builder: (context, _) => CustomPaint(
      key: const ValueKey('sys/waiting-paper'),
      size: const Size(64, 40),
      painter: _PaperPainter(
        _motion.value,
        Theme.of(context).colorScheme.primary,
        widget.scene,
      ),
    ),
  );
}

class _PaperPainter extends CustomPainter {
  const _PaperPainter(this.phase, this.color, this.scene);
  final double phase;
  final Color color;
  final WaitingScene scene;
  @override
  void paint(Canvas canvas, Size size) {
    final wave = math.sin(phase * math.pi);
    final ink = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.6;
    void line(double x, double y, double xx, double yy) =>
        canvas.drawLine(Offset(x, y), Offset(xx, yy), ink);
    switch (scene) {
      case WaitingScene.search:
        canvas.drawRect(Rect.fromLTWH(8, 8, 23, 26), ink);
        line(12, 14, 24, 14);
        line(12, 20, 22, 20);
        canvas.drawCircle(Offset(34 + wave * 5, 18), 8, ink);
        line(40 + wave * 5, 24, 48 + wave * 5, 32);
        break;
      case WaitingScene.sources:
        for (var i = 0; i < 3; i++) {
          canvas.drawRect(
            Rect.fromLTWH(
              10.0 + i * (5.0 - wave * 2.0),
              5.0 + i * 5.0,
              28.0,
              22.0,
            ),
            ink,
          );
        }
        canvas.drawCircle(const Offset(40, 9), 3, ink);
        line(40, 12, 40, 18);
        break;
      case WaitingScene.compare:
        for (var i = 0; i < 2; i++) {
          final x = 12.0 + i * 26;
          final y = 6 + (i == 0 ? wave : 1 - wave) * 4;
          canvas.drawPath(
            Path()
              ..moveTo(x, y)
              ..lineTo(x + 5, y)
              ..lineTo(x + 5, 28)
              ..lineTo(x + 2.5, 33)
              ..lineTo(x, 28)
              ..close(),
            ink,
          );
        }
        line(25, 19, 33, 19);
        break;
      case WaitingScene.analysis:
        final d = wave * 3;
        canvas.drawPath(
          Path()
            ..moveTo(16 + d, 8)
            ..lineTo(10 + d, 8)
            ..lineTo(10 + d, 32)
            ..lineTo(16 + d, 32),
          ink,
        );
        canvas.drawPath(
          Path()
            ..moveTo(48 - d, 8)
            ..lineTo(54 - d, 8)
            ..lineTo(54 - d, 32)
            ..lineTo(48 - d, 32),
          ink,
        );
        line(24, 17, 39, 17);
        canvas.drawCircle(const Offset(31, 26), 3, ink);
        break;
      case WaitingScene.export:
        // A folded paper remains on-screen; no claimed delivery or success.
        canvas.drawPath(
          Path()
            ..moveTo(8, 10)
            ..lineTo(53, 8 + wave * 3)
            ..lineTo(36, 33)
            ..lineTo(27, 23)
            ..close(),
          ink,
        );
        line(27, 23, 53, 8 + wave * 3);
        line(27, 23, 24, 32);
        break;
      case WaitingScene.waiting:
        canvas.drawPath(
          Path()
            ..moveTo(36, 11)
            ..lineTo(36, 28)
            ..quadraticBezierTo(36, 36, 28, 36)
            ..quadraticBezierTo(20, 36, 20, 28)
            ..lineTo(20, 9 - wave * 3)
            ..quadraticBezierTo(20, 3, 26, 3)
            ..quadraticBezierTo(32, 3, 32, 9)
            ..lineTo(32, 27)
            ..quadraticBezierTo(32, 31, 28, 31)
            ..quadraticBezierTo(25, 31, 25, 27)
            ..lineTo(25, 12),
          ink,
        );
        break;
    }
  }

  @override
  bool shouldRepaint(_PaperPainter old) =>
      old.phase != phase || old.color != color || old.scene != scene;
}
