# 通用 Agent 协议

## 调用方式

本 Skill 不绑定 Agent 品牌、模型商或 CLI。可使用文件宿主模式，也可注入 Python 回调。两种方式共用同一个两阶段状态机、校验器和重试逻辑。

## 文件宿主模式

从 Skill 根目录执行：

```bash
<PYTHON> scripts/analyze.py prepare \
  --symbol 600519 \
  --timeframe 1d \
  --bars 100 \
  --mode auto \
  --output-dir "<OUTPUT_DIR>"
```

`prepare` 输出机器可读 JSON，重要字段：

- `run_dir`：本轮目录，后续命令必须复用。
- `mode`：实际为 `full` 或 `incremental`。
- `incremental_new_bar_count`：真实新增已收盘 K 线数。
- `source`：行情来源和交叉核验结果。
- `prompt`：当前阶段完整消息文件。
- `raw_output_target`：Agent 应写入的裸 JSON 文件。

每个阶段的流程：

1. 完整读取 `stage1_prompt.md` 或 `stage2_prompt.md`。
2. 只依据消息中的 K 线、程序特征和策略规则分析，不补充其他数据。
3. 将完整裸 JSON 写入对应的 `stage1_raw.json` 或 `stage2_raw.json`。
4. 执行：

```bash
<PYTHON> scripts/analyze.py validate-stage1 --run-dir "<RUN_DIR>"
<PYTHON> scripts/analyze.py validate-stage2 --run-dir "<RUN_DIR>"
```

状态处理：

- `awaiting_stage1`：等待阶段一响应。
- `awaiting_stage1_retry`：读取更新后的消息和结构化反馈，重写阶段一响应。
- `awaiting_stage2`：等待阶段二响应。
- `awaiting_stage2_retry`：读取反馈，重写阶段二响应。
- `completed`：记录和摘要已生成。
- `failed`：停止并报告错误，不修改校验后的 JSON 冒充通过。

`stage*_messages.json` 使用通用消息数组：

```json
[
  {"role": "system", "content": "..."},
  {"role": "user", "content": "..."},
  {"role": "assistant", "content": "..."}
]
```

`stage*_prompt.md` 是同一消息链的可读表示。响应文件只含一个 JSON 对象，不得带 Markdown 围栏或解释文字。

## Python 回调模式

将 Skill 的 `scripts/` 加入模块搜索路径，或使用等价的 `PYTHONPATH` 设置：

```python
from ashare_price_action.agent import (
    AgentReply,
    CallbackAgentExecutor,
    run_analysis,
)

executor = CallbackAgentExecutor(
    callback=my_agent_callback,
    name="my-agent",
)
run_dir = run_analysis(
    symbol="600519",
    executor=executor,
    timeframe="1d",
    bars=100,
    mode="auto",
    output_dir="<OUTPUT_DIR>",
)
```

回调收到：

```python
AgentRequest(
    stage="stage1" | "stage2",
    run_dir=Path(...),
    messages=[...],
)
```

回调必须返回 `AgentReply` 或裸 JSON 字符串。`AgentReply` 可包含 `reasoning_content`、`request_id` 和 `usage`，但这些不是分析成功的必要条件。`run_analysis` 会自动执行两阶段、校验反馈重试、防篡改检查和落盘；状态为 `failed` 时抛出错误。

自定义执行器应实现：

```python
class AgentExecutor(Protocol):
    name: str
    interface: str

    def complete(self, request: AgentRequest) -> AgentReply:
        ...
```

## 输出目录

优先级：

1. `--output-dir` 或 `output_dir`。
2. 环境变量 `ASHARE_PRICE_ACTION_OUTPUT_DIR`。
3. 当前工作目录下的 `ashare-price-action-data/`。

增量分析应沿用同一输出目录。没有有效历史锚点时按规则回退全量，不伪造历史或新增 K 线。

## 错误约定

- 命令执行异常输出 `status=failed` 和结构化 `error`，退出码非零。
- 校验耗尽显式返回 `failed`，不得跳过重试、降低阈值或手工修改校验结果。
- Agent 执行器异常向外传播，不伪造模型响应。
