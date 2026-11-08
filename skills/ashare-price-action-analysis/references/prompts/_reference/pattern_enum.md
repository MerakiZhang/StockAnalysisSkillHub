# 形态与字段枚举参考

本文件是维护参考，不自动加入每轮提示。实际合法值和校验以 Python Schema、程序特征与动态输出契约为准。

## detected_patterns

| 标签 | 含义 |
|---|---|
| `wedge` | 楔形或三推，含微楔形和嵌套楔形 |
| `reversal_attempt` | 反转尝试，未必满足完整 MTR |
| `mtr` | 主要趋势反转，需要完整组件 |
| `final_flag` | 趋势末端的最终旗形 |
| `h1` / `h2` / `l1` / `l2` | High1/High2/Low1/Low2 计数结构 |
| `breakout_failure` | 突破后快速回到原结构；优先于同义 `failed_breakout` |
| `breakout_test` | 突破后的回测 |
| `breakout_pullback` | 突破回踩或失败的失败 |
| `barbwire` | 铁丝网；优先于同义 `wire` |
| `overlap` | K 线高度重叠 |
| `middle_range` | 区间中部，交易价值低 |
| `always_in` / `ail` / `ais` | Always In 状态及多空方向 |
| `20gb` | 约 20 根连续未触及 EMA |
| `gap_bar` | EMA 几何缺口标签，不是开盘跳空 |
| `opening_gap` | 开盘跳空 |
| `spike_candidate` | 单根或尚未达到最低标准的尖峰候选 |
| `spike_active` / `spike_ending` / `spike_transitioning` | 尖峰阶段标签 |
| `climax_warning` / `climax_triggered` | 对应 `climax_risk=warning/triggered` |
| `shrinking_stairs` | 收缩台阶或推进递减 |
| `failed_signal` | 失败信号及其可能的回测位 |
| `magnet` | 可能回测的结构位，不保证到达 |
| `trapped_traders` | 有证据的被套交易者结构 |
| `ascending_triangle` / `descending_triangle` | 上升/下降三角形 |
| `symmetrical_triangle` / `expanding_triangle` | 对称/扩张三角形 |
| `double_top_bottom` | 双顶、双底及微型结构 |

## bar_type

`trend_bull`、`trend_bear`、`doji`、`inside`、`outside_bull`、`outside_bear`、`flat`、`other`。

每根 K 线只有一个程序标签，优先级和几何条件以 `core/bar-signals.md` 与程序计算为准。

## entry_setup_type

`H1`、`H2`、`L1`、`L2`、`MTR`、`wedge`、`tr_boundary`、`breakout_pullback`、`EMA_pullback`、`triangle_breakout`、`none`。

## 资源与规则

- 风险与目标：`stage2/risk-and-targets.md`。
- 测量移动：`stage2/measured-move.md`。
- 形态只作结构候选，是否可交易由阶段二 §9、§10、§11、§14 决定。
- 多标签可以共存，但不得把形态写入 `cycle_position`。
- 二次结构、缺口和磁力位都不提供未经检验的胜率加分。
