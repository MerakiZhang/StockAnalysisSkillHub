from __future__ import annotations

ANALYST_ROLE = "core/analyst-role.md"
DECISION_TREE = "core/decision-tree.md"
BAR_SIGNALS = "core/bar-signals.md"
MARKET_DIAGNOSIS = "stage1/market-diagnosis.md"
BAR_BY_BAR = "stage2/bar-by-bar.md"
RISK_AND_TARGETS = "stage2/risk-and-targets.md"
MEASURED_MOVE = "stage2/measured-move.md"

BULL_CHANNEL = "strategies/bull-channel.md"
BEAR_CHANNEL = "strategies/bear-channel.md"
BULL_SPIKE = "strategies/bull-spike.md"
BEAR_SPIKE = "strategies/bear-spike.md"
TRADING_RANGE = "strategies/trading-range.md"
CHANNEL_WIDTH = "strategies/channel-width.md"

WEDGE = "patterns/wedge.md"
SECOND_ENTRY = "patterns/second-entry.md"
BREAKOUT = "patterns/breakout.md"
HIGH_LOW_COUNTS = "patterns/high-low-counts.md"
ALWAYS_IN = "patterns/always-in.md"
BARBWIRE = "patterns/barbwire.md"
MAGNETS = "patterns/magnets.md"
FINAL_FLAG = "patterns/final-flag.md"
MAJOR_TREND_REVERSAL = "patterns/major-trend-reversal.md"
TRIANGLES = "patterns/triangles.md"
DOUBLE_TOP_BOTTOM = "patterns/double-top-bottom.md"

COMMON_SYSTEM_FILES = (ANALYST_ROLE, DECISION_TREE)
STAGE1_TASK_FILES = (MARKET_DIAGNOSIS, BAR_SIGNALS)
STAGE2_BASE_FILES = (BAR_BY_BAR, BAR_SIGNALS, RISK_AND_TARGETS, MEASURED_MOVE)

BULL_CHANNEL_FILES = (BULL_CHANNEL,)
BEAR_CHANNEL_FILES = (BEAR_CHANNEL,)
BULL_SPIKE_FILES = (BULL_SPIKE,)
BEAR_SPIKE_FILES = (BEAR_SPIKE,)
RANGE_FILES = (TRADING_RANGE,)

FULL_STRATEGY_FILES = (
    BULL_CHANNEL,
    BEAR_CHANNEL,
    BULL_SPIKE,
    BEAR_SPIKE,
    TRADING_RANGE,
    CHANNEL_WIDTH,
    WEDGE,
    SECOND_ENTRY,
    BREAKOUT,
    HIGH_LOW_COUNTS,
    ALWAYS_IN,
    BARBWIRE,
    MAGNETS,
    FINAL_FLAG,
    MAJOR_TREND_REVERSAL,
    TRIANGLES,
    DOUBLE_TOP_BOTTOM,
)

ALL_PROMPT_FILES = frozenset(
    (
        *COMMON_SYSTEM_FILES,
        *STAGE1_TASK_FILES,
        *STAGE2_BASE_FILES,
        *FULL_STRATEGY_FILES,
    )
)

LEGACY_PROMPT_ALIASES = {
    "提示词大纲_人设与思维方式.txt": ANALYST_ROLE,
    "二元决策.txt": DECISION_TREE,
    "市场诊断框架.txt": MARKET_DIAGNOSIS,
    "文件16-K线信号识别.txt": BAR_SIGNALS,
    "逐棒分析检查单.txt": BAR_BY_BAR,
    "文件17-止损和止盈与仓位管理.txt": RISK_AND_TARGETS,
    "文件23-MeasuredMove与结构目标.txt": MEASURED_MOVE,
    "上涨通道分析识别.txt": BULL_CHANNEL,
    "上涨通道交易策略.txt": BULL_CHANNEL,
    "下跌通道分析识别.txt": BEAR_CHANNEL,
    "下跌通道交易策略.txt": BEAR_CHANNEL,
    "极速上涨分析识别.txt": BULL_SPIKE,
    "极速上涨交易策略.txt": BULL_SPIKE,
    "极速下跌分析识别.txt": BEAR_SPIKE,
    "极速下跌交易策略.txt": BEAR_SPIKE,
    "震荡区间分析识别.txt": TRADING_RANGE,
    "震荡区间交易策略.txt": TRADING_RANGE,
    "交易区间分析识别.txt": TRADING_RANGE,
    "交易区间交易策略.txt": TRADING_RANGE,
    "文件13-窄通道与宽通道策略.txt": CHANNEL_WIDTH,
    "宽通道分析识别.txt": CHANNEL_WIDTH,
    "宽通道交易策略.txt": CHANNEL_WIDTH,
    "文件14-楔形形态分析交易.txt": WEDGE,
    "文件15-二次入场机会.txt": SECOND_ENTRY,
    "文件18-突破失败与突破测试.txt": BREAKOUT,
    "文件19-H1H2-L1L2计数.txt": HIGH_LOW_COUNTS,
    "文件20-AlwaysIn与20GB.txt": ALWAYS_IN,
    "文件21-铁丝网与无交易环境.txt": BARBWIRE,
    "文件22-信号失败后的磁力位.txt": MAGNETS,
    "文件24-最终旗形与趋势末端.txt": FINAL_FLAG,
    "文件25-主要趋势反转MTR.txt": MAJOR_TREND_REVERSAL,
    "文件27-三角形与收敛形态.txt": TRIANGLES,
    "文件28-双重顶底与微型结构.txt": DOUBLE_TOP_BOTTOM,
    "下跌通道策略.txt": BEAR_CHANNEL,
    "下跌通道策略": BEAR_CHANNEL,
}
