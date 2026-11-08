# 价格行为缩写术语表

本文件为维护参考，不自动加入每轮提示。面向用户的解释应先写中文，必要时在括号内附英文缩写。

## 结构与形态

| 缩写 | 英文 | 中文要点 |
|---|---|---|
| FF | Final Flag | 趋势末端的最终旗形 |
| Spike Flag | Spike Flag | 尖峰后的整理，需与 FF 区分 |
| MW | Micro Wedge | 约 3–4 根的微楔形 |
| NW | Nested Wedge | 第三推内嵌更小楔形 |
| MM | Measured Move | 等距测量目标候选 |
| MTR | Major Trend Reversal | 主要趋势反转诊断 |
| MRV | Minor Trend Reversal | 小反转，可能只是回撤或区间 |
| OB / IB | Outside Bar / Inside Bar | 外包棒 / 内包棒 |
| OD / OU | Outside Down / Outside Up | 收阴外包 / 收阳外包 |
| 2BR | Two-Bar Reversal | 双棒反转候选 |

## 趋势与状态

| 缩写 | 含义 |
|---|---|
| AIL / AIS | Always In Long / Short，持续多头/空头倾向 |
| 20GB | 约 20 根连续未触及 EMA |
| GB / gap_bar | EMA 几何缺口标签，需结合趋势解释 |
| GU / GD | 开盘向上/向下跳空 |
| FT | Follow-through，后续跟随 |
| SPS | Spike Pullback，尖峰回撤后的顺势结构 |
| SCS | Spike Continuous Spike，尖峰追单；本系统禁止 |
| TR / TTR | 交易区间 / 紧凑交易区间 |

## 入场与目标

| 缩写 | 含义 |
|---|---|
| H1/H2 | 上涨背景中第一次/第二次回撤后的做多计数 |
| L1/L2 | 下跌背景中第一次/第二次反弹后的做空计数 |
| MGN | Magnet，可能回测的磁力位 |
| 5t/9t/17t/41t | Brooks 特定点数目标前差一跳的术语，不直接套用到 A 股 |
| TP1/TP2 | 近端主目标 / 更远结构目标 |
| RR | 回报 ÷ 风险，本系统只用 TP1 计算 |

形态路由以 `pattern_enum.md` 和程序 `detected_patterns` 规则为准。
