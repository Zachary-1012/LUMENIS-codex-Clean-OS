# 统一合规 Gate（P1-H）
> 基线《UNIFIED-ENGINEERING-BASELINE》§18 合规 Gate 落地文档。

## 定位
把散落的合规能力（`platform_adapters/safe_collection`、`ai_governance`、`intelligence.redact_for_cloud`）
统一编排为 **动作 → 多法域裁决** 的确定性 Gate。

## 裁决
| 结果 | 语义 |
|---|---|
| `BLOCK` | 禁止执行（违反红线：凭证入库/绕过访问控制/绕过验证码/绕过付费等） |
| `REVIEW` | 需人工/法务复核后放行（个人信息/跨境/版权/公开数据采集等） |
| `PASS` | 允许执行 |
| 不确定 | BLOCK / HUMAN REVIEW |

任一 BLOCK → 整体 BLOCK（`ok=False`）；仅 REVIEW → 整体 REVIEW。

## 规则矩阵
`config/compliance-rules.json`：7 维度（data_protection/personal_info/ai/web_scraping/
cross_border/data_minimization/copyright）× 5 法域（CN/HK/EU/UK/US，`*` 全域）。

## 用法
```python
from compliance_gate import ComplianceGate
gate = ComplianceGate()
r = gate.gate(action='scrape_public_notes', data_type='note', jurisdiction='CN')
# r['overall'] in ('PASS','REVIEW','BLOCK'); r['ok']=False 时禁止执行
```
采集动作（`scrape_*`/`collect_*`）会自动尝试并入 `safe_collection` 本地守卫结论（可选，不阻塞）。

## 红线（不可 REVIEW，直接 BLOCK）
- Cookie/Token/密钥永不入库
- 绕过访问控制 / 验证码 / 平台安全机制
- 伪造授权 / 规避付费权限 / 爬取受限制数据
- 大段复现受版权保护内容用于商业用途

## 法域研究（持续，仅合法适配）
中国大陆 PIPL / 香港 PDPO / EU GDPR / UK UK-GDPR / US 各州（CCPA 等）——数据保护、个人信息、AI、
Web Scraping、跨境、数据最小化、目的限制、数据保留、去标识化、平台规则、License/Copyright。
