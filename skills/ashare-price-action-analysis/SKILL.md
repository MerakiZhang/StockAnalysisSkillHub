---
name: ashare-price-action-analysis
description: >-
  对 A 股执行完整的两阶段 Price Action（价格行为）分析：已收盘 K 线诊断、市场闸门、
  策略路由、交易决策、校验重试和增量续析。用户要求分析一只 A 股、做 PA/K 线结构诊断、
  评估限价/突破/市价或不下单方案，或继续上一轮分析时使用。行情仅使用 AkShare 新浪和腾讯接口。
license: MIT
compatibility: >-
  需要 Python 3.11+、requirements.txt 中的依赖，以及访问新浪和腾讯行情接口的网络。
  可由任何能执行命令、读写文件的 Agent 使用，也提供 Python Agent 回调。
---

# A 股价格行为分析

## 目标

执行两阶段分析：已收盘 K 线快照 → 阶段一市场诊断与闸门 → 策略路由 → 阶段二交易决策 → 校验与重试 → 记录和摘要。

不得改成普通技术指标点评、新闻或基本面报告，不自动下单，不编造行情、模型响应或新增 K 线。

## 准备环境

使用能导入 `requirements.txt` 所需依赖的 Python 解释器。不要自动安装依赖；缺少依赖时如实报告。

从本 Skill 根目录运行命令，`<PYTHON>` 是解释器占位符，`<OUTPUT_DIR>` 是 Skill 外部的数据目录：

```bash
<PYTHON> scripts/analyze.py prepare \
  --symbol 600519 \
  --timeframe 1d \
  --bars 100 \
  --mode auto \
  --output-dir "<OUTPUT_DIR>"
```

默认使用 100 根已收盘 K 线、`balanced` 交易倾向、新浪主源及腾讯只读核验。常用选项：

- `--mode full|incremental|auto`：全量、尝试增量或自动选择。
- `--primary sina|tencent`：日线主源；分钟线始终使用新浪。
- `--no-crosscheck`：关闭日线交叉核验。
- `--decision-stance conservative|balanced|aggressive|extreme_aggressive`。
- `--enable-next-bar`：启用下一根 K 线预测；下一市场周期预测始终保留。
- `--experience-dir <目录> --experience-max-entries <0-10>`：启用经验库。
- `--run-dir <目录>`：指定本轮目录，便于续跑。

数据源、周期和核验纪律见 [data-sources.md](references/data-sources.md)。Brooks 原始概念、系统启发式阈值和 A 股交易边界见 [analysis-theory.md](references/analysis-theory.md)。

## 两阶段执行

### 1. 检查准备结果

`prepare` 输出机器可读 JSON。确认：

- `run_dir`、`mode` 和 `incremental_new_bar_count`。
- `source` 中的主源、备用切换和核验差异。
- `prompt` 与 `raw_output_target`。

数据或前置闸门失败时停止，不换用其他数据源。

### 2. 完成阶段一

1. 完整读取 `stage1_prompt.md`，不得只读开头。
2. 只依据消息中的 K 线、程序特征和策略规则分析，不补充其他数据。
3. 将阶段一完整裸 JSON 写入 `stage1_raw.json`，不得带围栏或解释。
4. 执行：

```bash
<PYTHON> scripts/analyze.py validate-stage1 --run-dir "<RUN_DIR>"
```

- `awaiting_stage1_retry`：完整读取更新后的消息和结构化反馈，重写响应并再次校验。
- `awaiting_stage2`：继续阶段二。
- `completed`：闸门短路，无需调用阶段二。
- `failed`：停止并报告，不修改校验后的 JSON 冒充通过。

### 3. 完成阶段二

1. 完整读取 `stage2_prompt.md`，保留阶段一对话链、诊断和路由策略。
2. 将阶段二完整裸 JSON 写入 `stage2_raw.json`。
3. 执行：

```bash
<PYTHON> scripts/analyze.py validate-stage2 --run-dir "<RUN_DIR>"
```

`awaiting_stage2_retry` 时按更新后的反馈重写响应；`failed` 时停止；`completed` 时进入展示。

### 4. 展示结果

```bash
<PYTHON> scripts/analyze.py show --run-dir "<RUN_DIR>"
```

最终说明模式、真实新增 K 线数、数据来源、周期、方向、下单类型、三价（如有）、置信度、交易者方程、风险和记录路径。计划型订单不得表述为已成交。

## 通用 Agent 接入

文件模式只要求宿主能执行命令并读写文件。Python 回调提供 `AgentRequest`、`AgentReply`、`AgentExecutor` 和 `run_analysis`，与文件模式共用状态机。

请求响应格式、回调示例、重试状态和错误约定见 [agent-protocol.md](references/agent-protocol.md)。

## 产物与硬性纪律

运行产物只写入 `<OUTPUT_DIR>`，不得写回 Skill。产物说明见 [run-output.md](references/run-output.md)。

- 不得只做阶段一就给出交易三价。
- 不得漏掉增量序号平移、`incremental_delta`、方案连续性或反手冷却。
- 不得在 `wait/unknown` 闸门后调用阶段二。
- 不得为通过校验而修改阈值、跳过失败或编辑校验后结果。
- 修正只能发生在下一次 Agent 原始响应中，再由同一校验器处理。
