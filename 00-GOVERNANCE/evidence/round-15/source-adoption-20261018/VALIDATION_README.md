# 来源能力吸收验证收口

本目录既有 FILE / ENDPOINT / CAPABILITY 映射分别覆盖 72 文件、51 路由意图、33 能力；SEED 映射保留 9 维和 36 条历史资料来源与未知权利。所有能力归入现有 CTH、BMP、Shared、SYSTEM；来源名称只作追溯和四仓兼容身份。

## 当前验证状态

统一冻结源 4003 文件，manifest 549d6cfa8added1d11c4178df3b4d5f7fcc0a0d3dde6903ed9c2fc03c39e0f22。11 静态验证器通过；另一次固定范围治理回归 289 passed / 318 subtests passed。主回归 4087 passed / 6 deselected / 318 subtests passed，0 failed、0 skipped，556.07 秒；这 6 个排除的真实 TCP 节点另在同版源独立执行，6 passed。两种执行环境分别保留证据，不与旧版或重复选择器相加作覆盖率。最终状态见 VALIDATION_RECEIPT.json。

validation/ 保留日志、官方主线完整树和逐 blob 的完整候选差异。首次无 HEAD / CLI 缺参数失败与正确完整输入后通过均保留；没有制造提交或远端历史。SANITIZATION_MANIFEST.json 保留原日志哈希与公开副本哈希，仅移除本机路径与本地测试地址。未经验证的外部接收、四端前端、生产和商业效果不计入通过。

人工反证与恢复并非事实认证；B 旧批准和 C 旧候选在 review 版本变更后失效，重新采用/真实新评价后方可继续。本仓 ACK 不等于外部发送。原规划、原创、至少 200 交互、四表面及界面 AIGC 要求完整保留，前端接续使用现有唯一完整规划与 screen specifications。

前轮 5 项失败（xlwt 依赖缺失、git 路径解析及三个 spawn harness 重入相关项）保留于 validation/prior_attempt/full.log；最终固定版日志保留完整节点结果，不擦除历史失败。包装后 11 个原静态门禁仍通过，未修改产品代码或门禁谓词。远端 required checks、合并读回、生产激活与四表面仍独立待验。

最终独立核验回执见 validation/FINAL_VALIDATION_RECEIPT.json：4087 主集与 6 TCP 恰为不重叠同版集合，合计 4093 primary，318 subtests 另列；原始回执 SHA256 为 677015b42d8c2fb5c4b0f582edda8f31aac2bfaf5bce60c0e17b22c0f2b1967e。公开副本已去本机路径/地址/主机标识，原哈希可回溯。
