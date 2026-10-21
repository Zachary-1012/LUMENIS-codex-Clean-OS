# V02 原始测试证据与补跑范围

## 已实证，不倒填

- 对原12771条账本逐节点取最后记录：3046条对应回执没有执行SHA；其余8749条标6d080205576739870624ad261fdcf8961d822cf8，976条标5e975f9aa4c43f6cb84de82b3e24b0c68b5e6d98。
- 3046的精确分解为final-shard-0-optout.xml 2981、ort-optout-real-formats.xml 23、public-macro-optout.xml 20、otio-final.xml 22。精确node列表和模块列表另存。
- 原账本所引用53份XML均在原临时证据目录找回，SHA256逐份53/53相同，总计15109269字节。未重建XML、未覆盖原件。原件发布另经全量秘密/隐私复核。
- 特别限制：finalize_test_appendix.py按文件名填写recorded_base_head，原XML不含完整Git工作树身份。即使非null，亦不能单凭该字段证明当时dirty修改不存在。新回执不得倒填到旧记录。

## 候选重跑选择

冻结本地提交1e549e016666a9b3de078f7020038d8a7df353be，tree f9ceb7b9973187255711cb0459504aa1522e3eae。

1. 首片225模块：全部3046未知SHA节点，加源变更测试、worker父路由/SSH/Permission/批准/保存恢复消费者、Douyin注册表间接消费者、治理归档测试。旧node并集4121；模块运行会包含新node，不以此预报实际通过数。
2. Python AST导入与字面动态import闭包保守识别616个模块；其中427不在首片，拆为两片各3794旧node，独立detached验证工作树、seed/home/output。
3. AST是模块粒度，会因Permission公共Owner高估影响，且不能证明非字面动态导入或配置依赖不存在。另77模块1062旧node的历史执行工作树身份仍不能独立证实，列remaining_provenance_modules.txt建议补跑，避免靠猜测继承。

依赖锁、requirements、pytest.ini和tests/conftest.py在6d080205到本轮主线间无变化，但这只证明提交对象差异，不把它写成历史运行环境已验。

## 27脚本与10跳过

27个脚本全文已读，逐项分类及当前工程语义的限定映射在manual_script_applicability.json。原脚本没有被执行，更不计入PASS。涉及真实平台/账号/默认数据库、Windows伴随项目、退休Provider的脚本不为数字清零而执行。test_growth_business_fixture.py是prepare_owner_source辅助函数，不是独立测试；覆盖由实际调用者提供。

映射不等于每个旧手工脚本完整功能验收，也不把线上源码测试冒称实际Runtime。当前纯工程语义依现行Owner隔离测试，原live层继续明确不在本次清障范围。

10个SKIP均从原XML逐条取得实际skip消息，不只照抄汇总，见skip_provenance.json。退休Provider、用户未供原资料、外部组件职责和实际Runtime/Browser opt-in层继续SKIP_NOT_PASS。

## 新回执约束

runner要求精确HEAD、tracked worktree干净、逐文件Git blob与SHA256前后相同、依赖freeze前后相同；记录UTC/北京时间、解释器入口/sys.prefix/base_prefix、实际argv、环境白名单、合成seed、guard、XML/log hash及终态。旧原53XML保持不变。

准备阶段首试发现隔离venv未安装pip模块，未进入pytest；使用现有uv pip freeze --python取得同一解释器环境清单，不安装依赖、不掩盖产品测试失败。首试保留NOT_EXECUTED证据；正式测试从frozen-rerun-2开始。

## 本轮冻结实跑终态（不是最终修后签收）

正式收集与四片XML逐节点匹配：12785唯一node，无重复、无缺项，12774 PASS、10 SKIP、1 FAIL。比旧12771增加11个worker测试和3个归档治理测试，旧node无移除。CURRENT_BOUND_NODE_LEDGER.json保留此版本事实，不将后续修复覆盖原失败。

唯一FAIL是scoped topic label读回测试比较整个SQLite SHM原字节。HTTP读成功，主DB/WAL字节相同，SHM offset8（iChange）变化。此刻只是已定位失败，不直接判生产写DB，也不直接删除断言；独立合成机制复现和当前Owner合同校准另记录。

## 手工脚本追加验证与发现

上述27项的初次记录均未执行；随后经明确授权追加4个源码确认无外部effects的脚本：ProxyPool 11项assertion通过，Risk 10项检查通过；Guard旧collector_guard导入失效，T2旧“未到期成功可清冷却”两断言失败。这是旧工程验证与现行Owner不一致，不是新生产熔断漏洞。

最小test-only修复：Guard迁现行Owner，临时数据/Checkpoint路径及registry缓存上下文恢复并断言隔离；T2保留有效冷却不得被on_success取消负例，双clock推进后才验证half-open恢复。v2隔离脚本Guard 6项检查、T2 73项检查均通过，另5个相关canonical模块70 PASS。均是staging patch验证，最终clean提交仍由最终回执确认。原失败日志、v1/v2 patch及回执不覆盖。未执行其他23脚本，不把原live/退休路径宣称通过；脚本检查数不加入12785测试node统计。
