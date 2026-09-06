# XHS Topic Monitor Temporary Strategy V1

## 事实基线

国内主账号当前为 `WARNING / NOT_BANNED`；香港手机号 RedNote 账号为 `RESTRICTED`。两者必须分开建模。

## 临时业务方案

国内主账号的话题监测暂采用：

- 每日最多 10 个 batch
- 每 batch 最多 10 个新 note
- note_id 去重
- 重复内容不进入后续分析
- 触发时间不作为长期固定时钟写死

## 研究优先级

继续寻找并验证：

1. 官方 API / SDK
2. 合规第三方 Provider
3. 用户主动 Evidence + OCR/VLM
4. 其他公开、可验证数据源

更优数据源一旦满足准确性、稳定性和授权条件，就替换 `temporary_browser`，上层 Subject/Risk/Event/Knowledge 链保持不变。

## 禁止方向

不研究或部署用于绕过平台控制的 stealth、指纹伪装、代理/IP 轮换、验证码绕过、私有 API 逆向或自动互动。

## 目标

保持 CTH-POMS 当前业务连续性，同时让 Core 的数据源真正可插拔，避免未来被任何单一平台接口绑死。
