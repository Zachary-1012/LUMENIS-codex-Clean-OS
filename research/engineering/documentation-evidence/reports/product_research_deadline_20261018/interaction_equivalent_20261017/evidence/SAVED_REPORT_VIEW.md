# 第73例：独立作者报告工作视图

日期：2026-10-17 UTC。新增独立审核示例；不是产品修改、产品接入或真实 E2E 验收。

## 交付

- `src/saved-report-study.mjs` 导出 `savedReportStudy` 与 `createSavedReportStudy({stage,status,onDispose,session,settingsRoot,storage})`。
- `tests/saved-report-adapter.test.mjs` 用最小 DOM 实际挂载视图，操作其 input/change/click/keydown 处理器。未使用浏览器。
- 本实现仅新增本说明、上述视图与测试。不改 controller、app、offline、session 或产品；入口接线和离线清单由父任务负责。

## 一个连续工作流

空白作者标题/Markdown → 纯文本预览 → 当前基线与完整字段前后对比 → 本地版本保存/修改原因 → 保持当前稿独立的历史查看 → 显式确认采用旧内容为当前 head 草稿 → 人工审阅/未核项绑定所选本地版本及 hash → 显式 journal checkpoint → 确认重开并选择保留或替换草稿 → 准备 md/txt UTF-8 字节 → 第二次用户点击才发出浏览器下载。

不运行模型、HTML 或脚本。md/txt 均保留原 Markdown 正文。版本查看不替换编辑稿；采用旧稿不改历史。不提供虚假的 docx/pdf/xlsx 下载。人工审阅不是 Evaluation，不创建事实认证或产品批准。

## 生命周期与隔离

- 保存中标题与正文仍可编辑；只在实际值变化时设置 input/textarea.value，避免无变化重绘破坏选区。
- 按 session 对象用 WeakMap 保持同一 controller；controller 的 subscribe/unsubscribe 负责当前视图订阅。session 仅另存 reason/focus 界面信息。
- 离开 capture 当前输入、UTF-16 editor selection 与 scroll 到内存 controller；取消迟到 UI 并退订，不 checkpoint、不偷做持久保存。取消不撤销已经写入的存储；不确定结果提示显式重开核查。
- journal 重开先显示确认，可选保留当前草稿或替换。Escape/取消不会替换草稿，并返回操作按钮焦点。
- read/write/export 开关、工作区和故障/延迟全部放在 settingsRoot。正常流程无需设置。
- scope/权限切换清 reason/reviewNotes/unknowns、确认面板、准备字节与状态消息；read 撤回另清正文、预览、历史、审阅与 hash 显示。版本选择变化清人工审阅输入，避免跨版本复用未提交意见。
- format 变化使进行中的准备 UI token 失效；版本和权限变化还由 controller 检查。下载处理器重新读取权限、所选版本、格式、hash，不仅依赖 disabled。
- 默认浏览器存储使用显式 Web Locks 包装；无可用锁时失败关闭。注入 storage 的锁/并发边界以 host adapter 为准，不声称跨标签原子性。

## 本次验证

在工作目录 `/workspace/scratch/8d04d68e28f4/review_working` 执行：

`node --test tests/saved-report-adapter.test.mjs tests/saved-report.test.mjs`

结果：37/37 通过，其中本文件对应视图适配器9组，controller28组。测试时间约0.17秒。适配器覆盖：

1. 作者稿/不可执行预览、保存修订父链、历史隔离、采用确认、版本/hash 人评、journal 与准备导出。
2. 重开保留/替换；Escape取消和焦点返回。
3. 保存延迟中继续编辑及选区保留；失败不丢稿，同次重试。
4. 无持久写入的会话离开/返回恢复；dispose 后迟到回执不更新已卸载视图，已经发生写入仍可存在。
5. scope/read 撤回清敏感正文、审阅输入与导出内容。
6. 点击取消等待后迟到回执无效；坏 journal 不覆盖编辑稿。
7. 真实 Blob 类及模拟 URL/anchor 的精确下载字节；只在第二次点击发出下载，明确磁盘落盘未证。
8. write/export/read 夹具分离，设置控件不混入工作区。
9. 导出准备期间切格式拒绝晚结果；撤权后直接调用下载 handler 也无效。

中英韩日法德西葡俄阿印尼及印地语混合原文、emoji/组合字符、HTML字样均包含于原文往返用例。这只证明字节/文本保留；字体、语言理解和完整三语UI不在通过声明中。

## 完成边界

- LOCAL_STATE_VERIFIED / 本地测试 storage readback verified。
- BROWSER_PENDING：真实宽窄布局、键盘 Tab、触屏、读屏、200%字号、实际浏览器选区与 Web Locks、下载交付均未验。
- Backend / Permission / Evaluation：UNBOUND。
- UI 主要中文；中英韩完整界面仍待接入。内容12语言保留不等于翻译或字体覆盖认证。
- 浏览器发出下载不等于磁盘落盘；测试模拟下载也不等于真实文件交付。

## 文件 SHA-256

- `src/saved-report-study.mjs`: `02b68bbe57d49f675037f20acfc8943fd10c8b49affa7ac4a7e7e863a168b3b3`
- `tests/saved-report-adapter.test.mjs`: `c831798e81b8192754c65871ec40075b41f9a332e761fdfad83dabe42730a857`
