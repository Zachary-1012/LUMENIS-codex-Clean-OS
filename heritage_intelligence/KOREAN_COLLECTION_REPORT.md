# G. Korean Collection Report

正式 Collection：`03_language_content_intelligence/Korean_Content_Intelligence_Collection/`

| 指标 | 结果 |
|---|---:|
| 匹配远程分支 | 40 |
| 不同尖端提交 | 3 |
| 历史路径×Blob 版本 | 32 |
| 唯一 Blob / 知识对象 | 16 |
| 精确重复附加版本 | 16 |
| 当前精确覆盖 | 11 |
| 同路径不同内容 | 4 |
| 无当前精确等价 | 1 |
| 只存在于历史过程的路径×Blob 版本 | 5 |
| 语义近似候选 | 1 |

## 核心判断

- K-drama Dialogue Research 来源明确，当前存在精确 Blob，保留表达机制与原创迁移方法。
- Fansub 历史分叉与当前版本近似但有独有范围差异，采用 `MERGE KNOWLEDGE`，不覆盖当前文件。
- Emotional Resonance 文档存在跨仓精确镜像，采用一次知识、多个来源指针的去重方式。
- Korean NLP Landscape 仅 `REFERENCE_ONLY`：模型、性能、硬件、发布日期和许可需一手来源复核。
- 历史 `xujing-i18n.js` 不恢复旧品牌命名；只审计其独有 key 和本地化规则。

注：40 个分支是远程引用数，3 个尖端提交是这些引用去重后的 commit 数；“精确重复附加版本”按路径×Blob 版本统计，“唯一 Blob”按内容统计，二者不是同一口径。

## 最终结构

- `README.md`：Collection 语义、谱系、规则、差异和 Pending。
- `KOREAN_SOURCE_POINTERS.csv`：全部韩语域历史来源指针。
- 总账：`../../_inventory/ASSET_PROVENANCE_LEDGER.csv`。
- 待验证：`../../_inventory/PENDING_VERIFICATION_LEDGER.csv`。

该 Collection 属于 Shared Capability / Content & Creation，不构成第三产品线。
