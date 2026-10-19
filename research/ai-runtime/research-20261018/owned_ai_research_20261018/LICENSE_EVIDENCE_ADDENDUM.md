# 训练许可证据增补

2026-10-17 20:02 UTC；保持REPORT.md原冻结副本。

第三方依赖核查已从官方raw固定tag补得TRL v0.22.2 LICENSE，原报告§8网页Internal Error不再意味着该许可证源文本缺失。相同证据集补得Transformers v4.56.2、Tokenizers v0.22.2、PyTorch v2.11.0、bitsandbytes 0.50.2与Triton v3.6.0固定源许可。本人核对index与保存文件hash一致。

证据索引：`[LOCAL_WORKSPACE]/third_party_inventory_recovered_20261018/training-license-index.json`；文本位于同目录`training-license-source/`。官方URL与完整hash见索引。

此增补仅关闭固定源码LICENSE读取缺口；不证明部署wheel、CUDA及全部传递依赖许可齐备，不证明这些版本已安装/兼容/运行。Unsloth 2026.9.12与unsloth_zoo 2026.9.8同名tag LICENSE读取404仍未核；PEFT/datasets/safetensors实际安装版本未在局部训练pins锁定，保持待核。

补篇`APPENDIX_PRODUCT_UNDERSTANDING.md`§7含13个验收场景（另主CSV为14组G项），均为计划而非已执行结果。
