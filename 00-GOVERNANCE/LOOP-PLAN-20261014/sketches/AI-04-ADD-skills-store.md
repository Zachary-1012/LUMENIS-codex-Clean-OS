# AI-04 — 草图增补：Skills 商店

> 已入库参考草图；实施与验收归现有ScreenSpec，按§5/§5A/§6原位维护，不自称已实现或已验收。规划依据：G21,G185,G130。

## 5. Purpose-built desktop composition
```
[搜索 Skill…] 分类 ▾
卡片：名称 | 输入 | 验证状态 | 权限 | [安装] [启用] [更新/回滚] [卸载]
详情：未知项列表、版本历史
```

## 5A. Web Workspace composition
Web：目录筛选与详情分栏在窄屏转为连续详情；权限确认可键盘操作，安装/停用结果按服务端读回，返回保留筛选和选中项。 受限后台插件不在商店上架。

## 6. Purpose-built mobile composition
列表 + 详情页。

## 4. State additions
Ready / Loading / 数据缺失（显示缺失，不补 0/50）/ 不可用（显示原因，不自动回退）/ 权限不足。

## 9. Executable acceptance
- 三语 zh-CN/en/ko 完整；适用全部已登记主体；无账号墙。
- 升级：从只读目录补齐完整生命周期。
