# Regression Memory

用于保存历史故障、根因、验证和防回归知识，而不是简单复制旧测试代码。

统一结构：
- Regression ID
- Failure
- Affected Capability
- Root Cause
- Detection
- Fix
- Test
- Evidence
- Preventive Rule
- Current Coverage

首批应收录：
- JS Fatal Syntax Regression
- Frontend Field Contract Regression
- Permission Gate Contamination
- Browser Render Regression
- Truth Chain Regression
- Runtime Heartbeat / Last-success Failure
- Security Scan real-positive / false-positive lessons

原则：代码可以重写，已验证过的故障模式和防回归规则不能丢失。
