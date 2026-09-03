# Passive Video Intelligence Contract V1

## 目标

为 CTH-POMS 增加视频理解能力：对小红书页面中已经由授权浏览器正常呈现/播放的内容进行多模态理解，不建立视频批量下载链路。

## 硬边界

1. **不下载**：Core 不主动下载、缓存或批量保存小红书视频媒体文件。
2. **不直连媒体接口**：视频理解层不得自行请求平台媒体 URL、私有 API、Cookie 或 Token。
3. **被动证据**：只接受授权 Browser Runtime 明确提交的 `browser_rendered` evidence。
4. **主体先行**：`SUBJECT_WORDS` / `SUBJECT_EXCLUDE_WORDS` / `subject_hit()` 等现有主体硬过滤继续是第一裁决；视频 AI 不得决定“是不是广州太古汇”。
5. **AI 非生命线**：视频分析失败不得阻断采集、入库、事件、风险、报告主链路。
6. **可追溯**：结果必须关联 `evidence_id`、`note_id`、provider/model version，并允许人工修正。
7. **安全信号优先**：平台出现安全限制、验证、异常行为信号时，按现有 `STOP → COOLDOWN → HUMAN REVIEW`，不得通过视频分析绕过。

## 分层

```text
XHS Resident Browser Runtime
        │
        │ already-rendered evidence only
        ↓
Passive Video Evidence Adapter
        │
        ├─ visible/key frames
        ├─ OCR text
        └─ ASR transcript
        ↓
VideoIntelligenceEngine
        │
        ├─ visual understanding
        ├─ scene/topic/entity extraction
        ├─ sentiment/risk signals
        └─ marketing signals
        ↓
Core evidence / intelligence layer
```

## 输出字段

- `evidence_id`
- `note_id`
- `transcript`
- `on_screen_text`
- `scenes`
- `entities`
- `topics`
- `sentiment`
- `risk_level`
- `marketing_signals`
- `confidence`
- `provider`
- `model_version`

## 性能与风控原则

视频理解默认采用**按需触发、低频、短证据窗口**，而不是后台持续录制或循环拉取媒体。采集调度、账号身份、Session、Circuit Breaker 和健康监控仍由现有 Resident Runtime 负责。

视频分析属于“候选内容增强”，不是新的采集次数入口。不得因为视频分析而增加小红书访问频率。

## 失败降级

```text
Video unavailable
      ↓
保留标题/正文/评论分析
      ↓
记录 VIDEO_ANALYSIS_UNAVAILABLE
      ↓
不影响主链路
```

## 验收标准

- [ ] 不出现视频下载器、媒体批量缓存或独立平台媒体请求。
- [ ] VideoIntelligenceEngine 无平台网络访问能力。
- [ ] 主体硬过滤仍在视频分析之前。
- [ ] 视频分析失败不会导致采集任务失败。
- [ ] AI 输出有 evidence/provider/model 可追溯性。
- [ ] 安全信号不会被视频模块吞掉或绕过。
- [ ] 现有 CTH-POMS 主链路回归测试保持通过。
