#!/usr/bin/env python3
"""valuation.py — 巴菲特价值投资 Skill 的估值计算器。

三个子命令：
  dcf     两段式自由现金流折现 + 敏感性矩阵
  dupont  ROE 三因子分解（净利率 × 周转率 × 权益乘数）
  margin  安全边际判定

设计约束：
  - 仅使用 Python 3.8+ 标准库，无第三方依赖，无网络请求
  - 只做数学，不取数据；数据由外部（MCP / 用户）提供
  - 参数非法时向 stderr 报错并返回退出码 2，不静默修正

用法示例：
  python valuation.py dcf --fcf 120,135,150 --discount 0.09 --shares 12.5 --net-cash 30
  python valuation.py dupont --revenue 1688 --net-profit 823 --assets 3183 --equity 2712
  python valuation.py margin --price 1453 --intrinsic 2400
"""

import argparse
import json
import sys
import unicodedata


class InputError(Exception):
    """输入不合法，需要中断并提示用户。"""


# ---------- 输出工具 ----------

def dwidth(text):
    """按终端显示宽度计算字符串长度（中文占 2 列）。"""
    return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
               for ch in str(text))


def pad(text, width, align="left"):
    text = str(text)
    gap = max(0, width - dwidth(text))
    if align == "right":
        return " " * gap + text
    return text + " " * gap


def render_table(headers, rows, aligns=None):
    """渲染等宽文本表格。"""
    if not rows:
        return ""
    aligns = aligns or ["left"] * len(headers)
    widths = []
    for i, head in enumerate(headers):
        w = max([dwidth(head)] + [dwidth(r[i]) for r in rows])
        widths.append(w)
    lines = ["  ".join(pad(h, widths[i], aligns[i]) for i, h in enumerate(headers))]
    lines.append("  ".join("-" * w for w in widths))
    for row in rows:
        lines.append("  ".join(pad(c, widths[i], aligns[i]) for i, c in enumerate(row)))
    return "\n".join(lines)


def money(value):
    """统一的金额格式：亿元，保留两位小数。"""
    return "{:,.2f}亿".format(value)


# ---------- 参数解析辅助 ----------

def parse_floats(text, name):
    try:
        values = [float(x) for x in str(text).replace("，", ",").split(",") if x.strip() != ""]
    except ValueError:
        raise InputError("{} 需要逗号分隔的数字，收到：{}".format(name, text))
    if not values:
        raise InputError("{} 不能为空".format(name))
    for v in values:
        if v != v or v in (float("inf"), float("-inf")):
            raise InputError("{} 含非法数值".format(name))
    return values


def check_rate(value, name, low, high):
    if not (low <= value <= high):
        raise InputError("{} 应在 {:.0%} 到 {:.0%} 之间，收到 {:.2%}".format(name, low, high, value))
    return value


def safety_label(ratio, threshold=0.7):
    """安全边际的统一措辞，正文与 JSON 必须一致。"""
    if ratio <= threshold:
        return "充足"
    if ratio <= 1:
        return "不足"
    return "明显溢价"


# ---------- DCF ----------

def cagr(values):
    """按首尾值计算复合年均增速；样本不足或多期非正时返回 None。"""
    if len(values) < 2:
        return None
    first, last = values[0], values[-1]
    if first <= 0 or last <= 0:
        return None
    years = len(values) - 1
    return (last / first) ** (1.0 / years) - 1.0


def dcf_equity_value(fcf_base, growth, discount, terminal_growth, years, net_cash):
    """两段式 DCF：显性期逐年折现 + 期末永续价值。"""
    pv_explicit = 0.0
    for t in range(1, years + 1):
        pv_explicit += fcf_base * (1 + growth) ** t / (1 + discount) ** t
    fcf_terminal = fcf_base * (1 + growth) ** years
    terminal_value = fcf_terminal * (1 + terminal_growth) / (discount - terminal_growth)
    pv_terminal = terminal_value / (1 + discount) ** years
    enterprise_value = pv_explicit + pv_terminal
    return {
        "pv_explicit": pv_explicit,
        "pv_terminal": pv_terminal,
        "enterprise_value": enterprise_value,
        "equity_value": enterprise_value + net_cash,
    }


def build_sensitivity(fcf_base, growth, discount, terminal_growth, years, net_cash, shares):
    """在增速 ±2pp、折现率 ±1pp 的邻域内做 3×3 敏感性测试。"""
    growth_axis = [round(growth + d, 4) for d in (-0.02, 0.0, 0.02)]
    discount_axis = [round(discount + d, 4) for d in (-0.01, 0.0, 0.01)]
    grid = []
    for g in growth_axis:
        row = []
        for r in discount_axis:
            if r <= terminal_growth or g <= -1:
                row.append(None)
                continue
            result = dcf_equity_value(fcf_base, g, r, terminal_growth, years, net_cash)
            row.append(result["equity_value"] / shares if shares else result["equity_value"])
        grid.append(row)
    valid = [v for row in grid for v in row if v is not None]
    return growth_axis, discount_axis, grid, valid


def cmd_dcf(args):
    fcf = parse_floats(args.fcf, "--fcf")
    if any(v <= 0 for v in fcf):
        raise InputError("自由现金流含非正值，DCF 不适用；请改用 PE/PB 历史分位法，并在报告中说明局限")

    base = sum(fcf) / len(fcf)

    # FCF 波动系数：预收款型业务（白酒、软件订阅）会因合同负债变动导致单年失真，
    # 由 FCF 序列推算的增速不可靠，必须提示。
    if len(fcf) >= 2 and base:
        variance = sum((x - base) ** 2 for x in fcf) / len(fcf)
        cv = (variance ** 0.5) / abs(base)
    else:
        cv = 0.0

    if args.growth is None:
        implied = cagr(fcf)
        if implied is None:
            raise InputError("样本不足，无法推算增速；请显式传入 --growth")
        growth = max(min(implied * 0.6, 0.10), -0.10)
        growth_note = "近三年 FCF 复合增速 {:.2%} × 0.6，封顶 10%，下限 -10%".format(implied)
        if implied < 0:
            growth_note += "（FCF 三年复合增速为负，自动推算不可信，务必用 --growth 重算）".format(implied)
    else:
        growth = check_rate(args.growth, "--growth", -0.10, 0.15)
        growth_note = "用户指定"

    discount = check_rate(args.discount, "--discount", 0.03, 0.30)
    terminal_growth = check_rate(args.terminal_growth, "--terminal-growth", 0.0, 0.05)

    if discount <= terminal_growth:
        raise InputError("折现率 {:.2%} 必须大于永续增速 {:.2%}，否则永续价值为负".format(discount, terminal_growth))
    if args.shares is not None and args.shares <= 0:
        raise InputError("股本必须大于 0")
    if args.price is not None and not args.shares:
        raise InputError("传了 --price 就必须同时传 --shares，否则无法折算每股价值")
    if args.years < 1 or args.years > 30:
        raise InputError("显性期应介于 1 到 30 年")

    result = dcf_equity_value(base, growth, discount, terminal_growth, args.years, args.net_cash)
    per_share = result["equity_value"] / args.shares if args.shares else None
    ratio = args.price / per_share if (args.price is not None and per_share) else None

    g_axis, r_axis, grid, valid = build_sensitivity(
        base, growth, discount, terminal_growth, args.years, args.net_cash, args.shares
    )
    low, high = (min(valid), max(valid)) if valid else (None, None)

    payload = {
        "subcommand": "dcf",
        "inputs": {
            "fcf_history": fcf,
            "fcf_base": round(base, 2),
            "fcf_cv": round(cv, 3),
            "growth": round(growth, 4),
            "growth_note": growth_note,
            "discount": discount,
            "terminal_growth": terminal_growth,
            "years": args.years,
            "shares": args.shares,
            "net_cash": args.net_cash,
        },
        "result": {
            "pv_explicit": round(result["pv_explicit"], 2),
            "pv_terminal": round(result["pv_terminal"], 2),
            "enterprise_value": round(result["enterprise_value"], 2),
            "equity_value": round(result["equity_value"], 2),
            "per_share": round(per_share, 2) if per_share else None,
            "conservative": round(low, 2) if low else None,
            "optimistic": round(high, 2) if high else None,
        },
    }

    if ratio is not None:
        payload["result"]["price"] = args.price
        payload["result"]["price_to_value"] = round(ratio, 3)
        payload["result"]["verdict"] = safety_label(ratio)

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    unit = "亿股" if args.shares else ""
    print("自由现金流折现（两段式）")
    print("=" * 46)
    print("三年 FCF 均值      : {}".format(money(base)))
    print("显性期增速         : {:.2%}（{}）".format(growth, growth_note))
    print("折现率 / 永续增速  : {:.2%} / {:.2%}".format(discount, terminal_growth))
    print("显性期             : {} 年".format(args.years))
    if args.net_cash:
        print("净现金调整         : {}".format(money(args.net_cash)))
    print("-" * 46)
    print("显性期现值         : {}".format(money(result["pv_explicit"])))
    print("永续价值现值       : {}".format(money(result["pv_terminal"])))
    print("企业价值           : {}".format(money(result["enterprise_value"])))
    print("股权价值           : {}".format(money(result["equity_value"])))
    if args.shares:
        print("每股内在价值       : {:.2f}元（股本 {}{}）".format(per_share, args.shares, unit))
        print("每股价值区间       : {:.2f} — {:.2f} 元".format(low, high))
    if cv > 0.20:
        print()
        print("警告：FCF 波动系数 {:.0%}（阈值 20%），现金流年际起伏明显。".format(cv))
        print("      常见于预收款型业务（白酒、软件订阅）：合同负债变动会让单年现金流失真。")
        print("      由该序列推算的增速不可靠，建议改用 --growth 显式指定并做两档情景。")
    print()

    rows = []
    for i, g in enumerate(g_axis):
        cells = []
        for j in range(len(r_axis)):
            v = grid[i][j]
            cells.append("{:.2f}".format(v) if v is not None else "n/a")
        rows.append(["增速 {:.2%}".format(g)] + cells)
    headers = ["情景 \\ 折现率"] + ["{:.2%}".format(r) for r in r_axis]
    print("敏感性矩阵（每股价值，元）" if args.shares else "敏感性矩阵（股权价值，亿元）")
    print(render_table(headers, rows, aligns=["left"] + ["right"] * len(r_axis)))
    print()

    if ratio is not None:
        print("当前价 {:.2f} 元 ÷ 每股价值 {:.2f} 元 = {:.2f} 倍 → 安全边际【{}】".format(
            args.price, per_share, ratio, safety_label(ratio)))
        if ratio > 0.7:
            print("提示：巴菲特口径要求市值 ≤ 内在价值 × 70%，当前未达阈值。")
    return 0


# ---------- 杜邦分解 ----------

def cmd_dupont(args):
    if args.revenue <= 0 or args.assets <= 0 or args.equity <= 0:
        raise InputError("营业收入、总资产、净资产均须大于 0")
    if args.equity > args.assets:
        raise InputError("净资产不能大于总资产，请检查口径（是否用了归母权益与合并总资产混搭）")

    net_margin = args.net_profit / args.revenue
    turnover = args.revenue / args.assets
    multiplier = args.assets / args.equity
    roe = net_margin * turnover * multiplier
    direct = args.net_profit / args.equity

    if abs(roe - direct) > max(0.005, abs(direct) * 0.01):
        print("警告：杜邦乘积 {:.2%} 与直接计算 {:.2%} 差异较大，请核对数据口径".format(roe, direct),
              file=sys.stderr)

    # 相对中性基准（净利率 8%、周转 0.8 次、权益乘数 1.2 倍）的倍数，
    # 倍数最高者即 ROE 的主导来源。
    baseline = [("净利率", net_margin, 0.08), ("资产周转率", turnover, 0.80), ("权益乘数", multiplier, 1.20)]
    scored = [(name, value, value / base) for name, value, base in baseline]
    leader, _, leader_score = max(scored, key=lambda item: item[2])

    if leader == "权益乘数":
        judgement = "高杠杆驱动——ROE 被负债放大，先看偿债能力"
        health = "警惕"
    elif multiplier >= 4:
        judgement = "杠杆偏高（{:.1f} 倍），即便主导因子是{}也需警惕".format(multiplier, leader)
        health = "警惕"
    elif leader == "净利率":
        judgement = "高利润率驱动——靠产品本身赚钱，最健康的一类"
        health = "健康"
    elif leader == "资产周转率":
        judgement = "高周转驱动——薄利多销，靠效率赚钱"
        health = "良好"
    else:
        judgement = "权益乘数偏高，杠杆贡献明显"
        health = "警惕"

    payload = {
        "subcommand": "dupont",
        "inputs": {
            "revenue": args.revenue,
            "net_profit": args.net_profit,
            "assets": args.assets,
            "equity": args.equity,
        },
        "result": {
            "roe": round(roe, 4),
            "net_margin": round(net_margin, 4),
            "asset_turnover": round(turnover, 4),
            "equity_multiplier": round(multiplier, 4),
            "relative_to_baseline": {name: round(score, 2) for name, _, score in scored},
            "driver": leader,
            "judgement": judgement,
            "health": health,
        },
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    print("ROE 杜邦分解")
    print("=" * 46)
    print("ROE                : {:.2%}".format(roe))
    print("净利率             : {:.2%}".format(net_margin))
    print("资产周转率         : {:.3f} 次".format(turnover))
    print("权益乘数           : {:.3f} 倍".format(multiplier))
    print("-" * 46)
    rows = [
        ["净利率", "{:.2%}".format(net_margin), "8%", "{:.2f}×".format(net_margin / 0.08)],
        ["资产周转率", "{:.2f} 次".format(turnover), "0.8 次", "{:.2f}×".format(turnover / 0.80)],
        ["权益乘数", "{:.2f} 倍".format(multiplier), "1.2 倍", "{:.2f}×".format(multiplier / 1.20)],
    ]
    print(render_table(["因子", "数值", "中性基准", "相对倍数"], rows,
                       aligns=["left", "right", "right", "right"]))
    print()
    print("主导因子：{}（相对基准 {:.2f} 倍）".format(leader, leader_score))
    print("判定：{}（{}）".format(judgement, health))
    if multiplier >= 3:
        print("提示：权益乘数 {:.1f} 倍，ROE 的含金量要打折看（零售、公用事业等薄利行业属正常）。".format(multiplier))
    return 0


# ---------- 安全边际 ----------

def cmd_margin(args):
    if args.intrinsic <= 0:
        raise InputError("内在价值必须大于 0")
    if args.price < 0:
        raise InputError("价格不能为负")
    if not (0.1 <= args.threshold <= 1.0):
        raise InputError("阈值应在 10% 到 100% 之间")

    ratio = args.price / args.intrinsic
    safety = 1 - ratio
    verdict = safety_label(ratio, args.threshold)

    payload = {
        "subcommand": "margin",
        "inputs": {"price": args.price, "intrinsic": args.intrinsic, "threshold": args.threshold},
        "result": {
            "price_to_value": round(ratio, 4),
            "margin_of_safety": round(safety, 4),
            "verdict": verdict,
            "pass": ratio <= args.threshold,
        },
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    print("安全边际判定")
    print("=" * 46)
    print("当前价格           : {:.2f} 元".format(args.price))
    print("内在价值           : {:.2f} 元".format(args.intrinsic))
    print("市值 / 内在价值    : {:.2f} 倍".format(ratio))
    print("安全边际           : {:.1%}".format(safety))
    print("-" * 46)
    print("判定：{}（阈值：价格 ≤ 内在价值 × {:.0%}）".format(verdict, args.threshold))
    if not payload["result"]["pass"]:
        target = args.intrinsic * args.threshold
        print("如需满足阈值，价格需回落至 {:.2f} 元以下。".format(target))
    return 0


# ---------- 入口 ----------

def build_parser():
    parser = argparse.ArgumentParser(
        prog="valuation.py",
        description="巴菲特价值投资 Skill 的估值计算器（只做数学，不取数据）",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_dcf = sub.add_parser("dcf", help="自由现金流折现 + 敏感性矩阵")
    p_dcf.add_argument("--fcf", required=True,
                       help='近三年自由现金流，亿元，逗号分隔；含负值请写成 --fcf="-10,20,30"')
    p_dcf.add_argument("--growth", type=float, default=None,
                       help="显性期增速（不传则按 FCF 复合增速×0.6 推算）")
    p_dcf.add_argument("--discount", type=float, default=0.09, help="折现率，默认 0.09")
    p_dcf.add_argument("--terminal-growth", type=float, default=0.03, dest="terminal_growth",
                       help="永续增速，默认 0.03")
    p_dcf.add_argument("--years", type=int, default=10, help="显性期年数，默认 10")
    p_dcf.add_argument("--shares", type=float, default=None, help="股本（亿股）")
    p_dcf.add_argument("--net-cash", type=float, default=0.0, dest="net_cash",
                       help="净现金（亿元），有息负债为负")
    p_dcf.add_argument("--price", type=float, default=None, help="当前股价，用于计算安全边际")
    p_dcf.add_argument("--json", action="store_true", help="输出 JSON")
    p_dcf.set_defaults(func=cmd_dcf)

    p_dupont = sub.add_parser("dupont", help="ROE 三因子分解")
    p_dupont.add_argument("--revenue", type=float, required=True, help="营业收入（亿元）")
    p_dupont.add_argument("--net-profit", type=float, required=True, dest="net_profit",
                          help="净利润（亿元）")
    p_dupont.add_argument("--assets", type=float, required=True, help="总资产（亿元）")
    p_dupont.add_argument("--equity", type=float, required=True, help="净资产（亿元）")
    p_dupont.add_argument("--json", action="store_true", help="输出 JSON")
    p_dupont.set_defaults(func=cmd_dupont)

    p_margin = sub.add_parser("margin", help="安全边际判定")
    p_margin.add_argument("--price", type=float, required=True, help="当前价格")
    p_margin.add_argument("--intrinsic", type=float, required=True, help="内在价值（同单位）")
    p_margin.add_argument("--threshold", type=float, default=0.7, help="价格/价值阈值，默认 0.7")
    p_margin.add_argument("--json", action="store_true", help="输出 JSON")
    p_margin.set_defaults(func=cmd_margin)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except InputError as exc:
        print("参数错误：{}".format(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
