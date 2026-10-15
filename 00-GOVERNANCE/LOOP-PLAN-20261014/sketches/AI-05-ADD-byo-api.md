# AI-05 — 草图增补：模型设置：自有模型默认 + 一个通用 OpenAI 兼容自带 API

> 已入库参考草图；实施与验收归现有ScreenSpec，按§5/§5A/§6原位维护，不自称已实现或已验收。规划依据：G50。

## 5. Purpose-built desktop composition
```
模型来源 (●) 序境自有模型（默认）  ( ) 我的 API（OpenAI 兼容）
  Base URL [        ] Model [      ] Key [••••] [测试连接]
说明：不可用时显示「不可用」，不会自动切换
```

## 5A. Web Workspace composition
Web：模型状态、配置与连接结果分区显示；密钥不回显，失败保留非敏感表单值；刷新重新读真实绑定，不把配置成功当推理可用。

## 6. Purpose-built mobile composition
同内容纵排。

## 4. State additions
Ready / Loading / 数据缺失（显示缺失，不补 0/50）/ 不可用（显示原因，不自动回退）/ 权限不足。

## 9. Executable acceptance
- 三语 zh-CN/en/ko 完整；适用全部已登记主体；无账号墙。
- 无豆包/智谱/Ollama 选项；无自动回退；Key 不落盘明文。
