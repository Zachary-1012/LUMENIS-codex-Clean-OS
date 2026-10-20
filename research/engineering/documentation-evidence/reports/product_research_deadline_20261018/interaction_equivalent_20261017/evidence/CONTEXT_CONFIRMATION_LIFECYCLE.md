# 29视角确认与返回修复

现行依据：当前工作树contracts/experience/screen-specifications/ACC-02.md §§0–3、§4窄屏list/detail与Return，明确选择只改view lens，服务端仍负责Subject授权；真实GET /api/settings/context、GET /api/settings/subjects与PUT /api/settings/context都未在本例绑定。此处GLOBAL_ALL及allowed均明确人工夹具，恢复缓存不能替代实际服务器确认。

原视图缺另一modal互斥检查、确认预览快照、焦点安全返回与路由草稿。已补：现有弹窗在前时不打开第二个；确认保存对象ID/上下文revision/所选lens并在动作时复核，不把变动后的对象默默当已确认；unknown/denied仍拒绝；Cancel/Escape不变焦点对象；断开opener回到工作区。dialog不支持或打开失败明确保持原视角，没有假成功。

本地草稿/选区/滚动和选择状态可在同会话路由返回；不会重开旧确认窗或发请求。未知/损坏路由引用不被当成身份。纯状态confirm新增可选expectedSelected/expectedRevision，旧函数名及未传caller保持兼容；真实产品caller必须使用其Owner的请求/回执，而不能把这里的local focus当服务端envelope。

6项实际最小DOM测试覆盖精确预览确认、模态互斥、Cancel/Escape保稿、过期对象/lens、未知/拒绝、空搜索、路由重开无modal、卸载迟到回调及unsupported-dialog/断开焦点。原生dialog焦点陷阱、移动两阶段视觉和读屏仍BROWSER_PENDING。未新增入口，也未关闭ACC-02真实注册/读取/确认/恢复全流程缺口。
