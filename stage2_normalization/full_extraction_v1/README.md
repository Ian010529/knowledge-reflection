# 全量摘要关系抽取 v1

已完成：165/165 批、1,971 篇、21,122 条关系，另 6 篇缺摘要登记。见 [完成报告](REPORT.md) 和 [核验记录](verification.json)。`python3 stage2_normalization/full_extraction_v1/verify.py` 可只读复核交付物；程序核验不代表独立语义验收。当前无待续跑批次。

用户于 2026-09-24 明确授权对所有文献抽取并连续推进至完成，每批简短汇报。默认语料 1,977 篇均保留：iTE 1,644、TG 333，其中 1,971 篇有摘要、6 篇无摘要。过去开发/审计样本本次也重新抽取，但不重新算作未接触验收样本。

执行：`python3 stage2_normalization/full_extraction_v1/run.py --workers 6`。用户已要求从 3 路提高到 6 路；旧调度完成在途批次后退出，再由单个 6 路调度器接续，切换记录见 concurrency_transition.json。已有调度器运行时不要重复启动。读取 manifest 固定的 165 个批次，每批最多 12 篇，域内按 ID 排序、两域交错调度。已成功批次直接跳过并核对哈希。无内容筛样；不复用旧语义输出充当新抽取。

后端是实际 ChatGPT 登录的 Codex CLI、gpt-6-astra、medium reasoning，纯结构化推理且工具关闭。程序移除 API key 环境变量并强制 ChatGPT 登录；不使用付费 API 客户端、旧 dsh 或监听。仅模型作语义抽取，Python 做机械分段、证据定位、字段校验与计数。分段可逐字拼回完整摘要；模型每次收到完整批次摘要，选择片段 ID，程序展开原文引文和位置，避免模型重复抄写引文。

PROMPT.md 固定既有范围、模态规则、联合作用和限定要求，并纳入审计中已明确的边界：有对象的物理参数不作为孤立数字丢弃；无方向但明确的关联保留；泛泛未来研究建议不当发现。每批一轮输出，返回前集中自检，不为每篇生成独立参考或另开裁判。输出只有 model_extracted_program_validated 状态，不能当作全量独立语义验收通过。

最多一次技术失败重试，原日志/回复均保留；认证、权限、模型可用性或额度失败停止新派发，不自动切换模型、身份或付费途径。中断后从检查点恢复；已用两次失败的批次须检查原因，不盲目循环。

关键文件：manifest.json（范围/批次/源文件/提示/schema 哈希）、inputs/（原文与片段）、batches/*/attempt_*/（原始模型回复与用量事件）、batches/*/extraction.json、SUCCESS.json（验证成功检查点）、progress.json（已成功计数）、missing_abstracts.json（6 篇原记录）。完成后才写 extraction_all.json、extraction_iTE.json、extraction_TG.json 和 batch_statistics.json。

usage 来自 CLI 实际 turn.completed 事件；未提供时不猜 token。源文件与所有旧冻结试验不改写。本轮到抽取交付为止，不自动建图、归一化合并或执行 match。
