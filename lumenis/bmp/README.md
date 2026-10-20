# BMP — Brand & Market

BMP 是寰意 / OEVIRA 现有产品中的品牌与市场业务领域，与 CTH 商业运营域并列；CTH 稳定不是 BMP 开始工作的前置条件。

## 领域范围

BMP 围绕用户明确选择的 `BrandFocus` 和市场开展品牌资料、市场与竞品比较、创作者/渠道、传播内容、Campaign 及其评价工作。选择品牌只确定任务范围，不自行授予权限；产品默认工作范围仍为 `GLOBAL / ALL`。

## 现有架构与源码边界

- CTH、BMP、Shared 与 SYSTEM 属于同一产品和 Product Core；业务事实、Evidence 与权限继续由各自现有 Owner 管理。
- CTH/BMP/Shared 共用当前唯一业务真值数据库 `data/monitor.db`（保留 `ZBC_DB_PATH` 兼容覆盖），此目录不定义独立数据库或第二套事实。
- `PRODUCT_ZBMP`、`product_id=ZBMP`、`domain_id=zbmp` 是现有兼容标识，不代表第二个产品。
- BMP 领域源码与业务含义归 C3；调用方（来源、AI、研究、传输、前端等）保留[源码 Owner 索引](../../00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md)中登记的各自 Owner（C1/C2/C5/C6/F），改动按对应 Owner 合同进行。本 README 是范围与导航说明，不证明某项实现或产品闭环已经验收。

旧文本中的“预留占位、独立 `zbrand.db`、`/zbrand/` 产品入口、等待 CTH-POMS V4.0”不符合当前产品架构，不作为实现合同。

## 权威入口

- [当前产品架构](../../00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md)
- [源码 Owner 索引](../../00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md)
- [体验宪章](../../00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md)
