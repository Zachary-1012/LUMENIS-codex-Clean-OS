# XHS Topic Monitor Global Adaptation Gate V2

## 目标

允许 Core 在当前 UI/视觉升级并行期间，最小改动接入临时 Topic Monitor 10×10，并为未来 API/Provider/Evidence 切换保留统一契约。

## 影响评估

### 不允许大动

- 不重构 CTH-POMS 页面导航
- 不重写现有采集主链
- 不重建数据库
- 不改变 Risk/Event/Knowledge 上层契约
- 不因本任务暂停当前 UI/UX 升级

### 必须变更

- 统一 Scheduler 接管 Topic Monitor 调度
- 历史固定小时/固定次数逻辑降级为 legacy
- 增加 temporary strategy / 10 batch/day / 10 new items/batch 配置
- Source Contract 抽象 Official API / Licensed Provider / Evidence / Temporary Browser
- Session Validator + crash recovery + manual re-auth state
- 前端只增加状态/来源/进度信息，不改变现有交互骨架

## 门禁

1. 10×10 仅为临时业务预算，不得被描述为风控保证。
2. 不实现 stealth、指纹伪装、代理/IP 规避、验证码绕过、私有 API 逆向。
3. 香港 RedNote 受限账号不得作为自动化测试账号。
4. 生产 UI 升级必须与后端契约解耦。
5. 新 Source 必须可以替换而不修改上层业务逻辑。
