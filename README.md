# 寰意 / OEVIRA

**可靠信息、持续监测、专业判断与可交付成果。**

寰意是自研的信息研究与创作工作平台，服务商业运营团队、品牌与代理机构，以及
个人研究与创作者。用户围绕目标工作，获得可以核对、修改、保存、重开和交付的成果。

> 当前版本是新产品的规划与仓库结构基线，不是可运行产品。旧实现已退出当前文件树，
> 保留在 Git 历史中。这里没有安装或启动成功的承诺，也没有占位界面冒充功能。

仓库：[Zachary-1012/OEVIRA](https://github.com/Zachary-1012/OEVIRA)
本地主路径：`D:\寰意`。

## 唯一现行产品资料

| 文件 | 职责 |
| --- | --- |
| [PRODUCT.md](PRODUCT.md) | 定位、用户、范围和取舍 |
| [完整功能与流程](docs/PRODUCT-SPEC.md) | 功能、真实工作、页面映射及取舍理由 |
| [DESIGN.md](DESIGN.md) | 导航、页面交互、视觉、三语和无障碍 |
| [架构](docs/ARCHITECTURE.md) | 自研模块、数据、接口、任务和运行边界 |
| [验收](docs/ACCEPTANCE.md) | 真实成果、异常恢复、质量与发布要求 |

[AGENTS.md](AGENTS.md) 只负责工程执行，[CONTRIBUTING.md](CONTRIBUTING.md) 说明协作流程。
历史资料不是现行规划，检索入口见 [来源历史](docs/reference/README.md)。

## 新目录

```text
app/          Flutter Web / Windows 客户端
server/       Python 产品核心、API 与后台工作进程
website/      Astro 官网，展示与真实入口
assets/       原创身份资产与获准公共素材
docs/         产品规格、架构、验收及接口合同
scripts/      构建、验证、运行与维护工具
tests/        跨模块验证；模块测试随所属源码维护
.github/      PR 流程与质量检查
```

工作、监测、资料、成果是四个一级入口。自研采集与受控浏览器共用一套来源、任务、
授权和恢复机制。用户自行授权自己的平台账号，不继承开发者身份或地区限制。
基础工作可无 AI 运行；AI 增强和专业媒体制作分别验收。

## 检查本次结构

```powershell
Set-Location D:\寰意
python scripts/verify_repository.py
python -m unittest discover -s tests -v
```

以上只验证结构与规格完整性。产品发布检查独立且保持阻塞，直到实际源码、构建、
权限、恢复和真实操作证据通过。后续实现不能把本次结构检查当成发布验收。

## License

原有 [Apache-2.0 LICENSE](LICENSE) 保持原文，不因品牌或架构重构变更。
第三方代码、字体、素材和模型保留独立许可，见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

---

OEVIRA is a self-developed information research and creation product. This branch
establishes the approved specification and repository layout; it is not a runnable
release. Product capabilities require independent implementation and acceptance.
