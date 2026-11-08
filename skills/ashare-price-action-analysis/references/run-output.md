# 运行产物与状态

## 目录布局

所有运行产物位于 Skill 外部：

```text
<OUTPUT_DIR>/
├── runs/
│   └── <RUN_ID>/
└── records/
    └── pending/
```

Skill 目录只包含代码、提示词和静态文档，不保存分析记录、日志或运行缓存。

## 每轮产物

- `run.json`：状态、配置、输出目录、行情来源、模式和重试状态。
- `frame.json`：实际分析的已收盘 K 线及指标。
- `source.json`：数据来源和交叉核验证明。
- `previous_record.json`：增量模式使用的上一轮记录副本。
- `stage1_messages.json`、`stage2_messages.json`：完整消息数组。
- `stage1_prompt.md`、`stage2_prompt.md`：可读消息链。
- `stage1_raw.json`、`stage2_raw.json`：当前 Agent 裸 JSON 响应。
- `stage1_response.json`、`stage2_response.json`：响应及通用执行器元数据。
- `stage1_raw_attempt_N.json`、`stage2_raw_attempt_N.json`：每次响应历史。
- `stage1_diagnosis.json`：校验后的阶段一诊断。
- `stage2_decision.json`：校验后的阶段二决策。
- `summary.md`：可读摘要。

完整 `AnalysisRecord` 写入 `records/pending/`。只有完整成功记录可作为后续增量锚点，失败或部分记录不得冒充成功历史。增量锚点还会比较重叠 K 线的 OHLC；若前复权历史被修订，则回退全量，不把旧诊断当作不变事实。

## 摘要内容

最终摘要包括：

- 全量或增量模式、真实新增 K 线数、数据来源和核验异常。
- 市场周期、方向、形态和诊断置信度。
- 下单类型、方向、入场、止损、TP1、TP2（如有）。
- 交易置信度、主观胜率、盈亏比和交易者方程。
- 失效条件、风险、观察点和决策路径。

计划型订单只表示分析计划，不表示已经成交。本 Skill 不自动下单。

## 命令状态

- `awaiting_stage1`：等待阶段一响应。
- `awaiting_stage1_retry`：等待按反馈修正阶段一响应。
- `awaiting_stage2`：等待阶段二响应。
- `awaiting_stage2_retry`：等待按反馈修正阶段二响应。
- `completed`：两阶段或闸门短路流程已完成。
- `failed`：数据、执行或校验失败，应停止并检查 `run.json`。

查看结果：

```bash
<PYTHON> scripts/analyze.py show --run-dir "<RUN_DIR>"
```

## 经验库

经验库默认关闭。启用时可指定 `--experience-dir`；未指定时读取 `<OUTPUT_DIR>/experience/`。经验条目只作对照，不得替代当前 K 线的独立判断。
