# 独立导出字节验证合同（人工 fixture）

## 范围与事实依据

本合同只存在于 review_working 的独立示例模块；未修改产品、数据库、运行环境、浏览器或部署，也不产生网络请求。测试全部是人工 fixture，不是线上或真实产品导出的证据。

只读核对：
- `experience_runtime.py:2790–2814`：出口从 export_work 返回 bytes，设置 X-Source-Artifact-ID 与 X-Content-SHA256；这段路由没有版本或源 Artifact SHA 的响应头。
- `lumenis/shared/reporting/saved_work.py:1136–1165`：导出前后读取 committed work 并核 DATA_EXPORT 权限及原始来源 scope；X-Content-SHA256 对应转换后的 raw bytes。md/txt 在 Markdown 后追加 sources/原始 scope 和 rights；纯 Markdown SHA 不能用于校验真实产品导出。
- `app/lib/core/lumenis_core_client.dart:1110–1200`：现有客户端检查 HTTP 200、格式对应 MIME、非空与 32 MiB 上限。本独立合同不是对该客户端的改动，也没有声称其已执行本文额外检查。

三个摘要不可混用：sourceArtifactSha 是源记录摘要；payload draft_digest 是草稿摘要；actualExportDigest / X-Content-SHA256 是转换后导出字节摘要。本文不推导 draft_digest，也不会把三个值视作同一个校验目标。

## 稳定异步接口

`createExportVerifier({ readOwner, getGeneration, maxBytes })` 返回 `{ verify }`。

`verify({ selection, acquireResponse, signal })` 返回结果对象，不抛出业务异常；拒绝时 `accepted:false, level:REJECTED, code`。不依赖应用模块或第三方包，SHA-256 使用 Web Crypto；无法使用时 fail closed。默认 maxBytes 为 32 MiB。

selection 必须明确包括 artifactId、version、sourceArtifactSha、format、generation。人工合同以正整数表示 version、非负整数表示 generation；这是示例字段约束，不代表已发现真实产品版本协议。格式支持服务器的 json/md/txt/docx/pdf/xlsx；json 并不因此成为当前 Flutter 客户端支持项。

readOwner({ selection, phase }) 是必须由宿主绑定的可信边界。phase 为 before/after：
1. 从独立可信来源读取选中的不可变源版本/服务端记录摘要，并核当前 Owner、导出权限与所有来源访问权；不得使用候选响应头构造这个记录。
2. 返回完整 selection 字段及 authorized:true；不相等、缺失或异常均拒绝。
3. 可选返回 independentExportDigest：只能来自宿主已独立核验、与该 artifact/version/source SHA/format 对应的期望导出摘要。不得把当前响应头、当前 body 的 hash 或请求适配器自报值重新包装为独立摘要。合同无法从字符串本身检测宿主是否违背这一信任边界。

getGeneration() 必须同步返回宿主当前、单调变更且不复用的选择/请求代次；新的选择、新请求或失效操作要递增。signal 可取消。所有等待返回后及结果提交前均核代次与取消，after Owner 读取覆盖转换期间撤权或源版本变化。

acquireResponse(frozenSelection, signal) 由宿主显式注入。返回 status、headers、bytes:Uint8Array 和 requestBinding。requestBinding 必须来自宿主实际发出的请求上下文，不能信任服务端回传的“绑定”。合同核其 artifactId/version/sourceArtifactSha/format/generation 均与预选值一致。宿主还应保证真实传输不重定向/串请求，在下载过程中施加流量上限；本文只能检查已经收到的 bytes，不能防止上游在调用前分配过多内存。模块自身不调用网络、不生成新 endpoint、不处理凭据。

## 结果含义与边界

- SOURCE_BOUND_BYTE_INTEGRITY：Owner 前后独立记录及请求上下文已与预选源版本绑定，实际 bytes SHA-256 等于响应 X-Content-SHA256；authenticity 为 UNESTABLISHED。这里的“绑定”只是源记录与请求绑定，不能据此证明该 body 确实由该版本转换而来。恶意服务器提供任意错误内容及自洽 hash 仍可能到达此等级。
- INDEPENDENT_EXPORT_DIGEST_MATCH：在上述检查外，实际 bytes 与宿主独立已核期望导出摘要相等；authenticity 为 MATCHES_HOST_VERIFIED_DIGEST。这仅证明匹配宿主信任的精确字节摘要，不宣称语义正确、签名真实性或合法来源已经由本模块独立查明。
- accepted:true 表示通过该结果等级的合同，不可单独作为“真实性 VERIFIED”、下载成功、持久化成功或对外分享许可；消费者必须检查 level/authenticity，且不得把较低等级提升为更强宣称。
- 两个成功等级的 diskPersistence 都是 NOT_ESTABLISHED。模块不写文件，无法证明浏览器下载成功、路径正确、磁盘已经落盘或用户能打开文档。需要独立的实际保存及回读证据。
- 源 Artifact SHA / 独立期望摘要改变、前后独立摘要一端缺失、撤权、晚回执、取消均 fail closed。Owner 未绑定时不会调用 acquireResponse。
- 对 md/txt/docx/pdf/xlsx 等转换格式，期望摘要必须覆盖完整实际导出内容（md/txt 包括 sources）。没有可靠的精确字节期望摘要时保留较低等级；不能发明一个生产摘要。可能不确定性转换也必须提供实际期望字节摘要，不能静默跳过比较。

## 验证

运行：`node --test tests/export-verification.test.mjs`

人工反例覆盖：错 artifact ID/格式/MIME/版本/source SHA/代次，空或超限字节，头摘要与 bytes 不符，错误内容与头自洽但独立期望不同，撤权、源版本变化、晚回执、取消、Owner 缺失/异常、独立期望缺失/变化，以及错误使用纯 Markdown hash。没有产品端到端、真实权限、真实导出格式渲染或实际落盘验证。

## 目标工作副本复核与交接快照
初次3文件误写在云工作根，父任务已核原字节复制至review_working并重跑30/30；路径回执见EXPORT_FILE_PATH_RECONCILIATION.json。随后目标副本补强：验通过的结果提供getVerifiedBytes()，每次返回隔离副本，后续文件交接必须使用它，不能重新使用原响应可变buffer。新增原buffer及返回副本被修改的反例。前端格式限制为md/txt/docx/pdf/xlsx，排除Owner内部JSON。新增后32项实际通过；仍不代表落盘/真实Owner或当前导出真实性已实测。
