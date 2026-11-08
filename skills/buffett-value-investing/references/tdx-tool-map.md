# 通达信 MCP 工具映射

本文件回答一个问题：**要拿到某个分析结论，该调哪个工具、传什么参数、结果怎么看。**

## 通用调用约定

1. **先查码，再取数**。任何带中文名的请求，先用 `tdx_lookup_stock` 换成 `code` + `setcode`。
2. **工具名带前缀**。不同宿主的 MCP 工具前缀不同（常见 `mcp__tdx-connector__tdx_quotes`），按后缀匹配即可。
3. **空结果不猜**。返回空就如实说无数据，禁止用记忆补字段。
4. **单次少取**。`limit`、`pageSize` 不超过 50，避免上下文被塞满。
5. **不信卡片**。工具会返回 `presentationContextId` 和 `dataCard` 候选，那是给支持的宿主用的。默认忽略；除非宿主明确支持且用户要求可视化，才调用 `tdx_present_research_ui`，且只调一次。

## 验证状态图例

| 标记 | 含义 |
|---|---|
| ✅ | 本技能开发时真实调用验证过，参数与返回结构均确认 |
| ⚠️ | 可调用，但有已知陷阱，必须按备注处理 |
| 🟡 | 与已验证接口同族、参数模式一致，但未逐一实测；首次使用需核对返回 |

> 表中"已验证"部分基于 2026-11-07 对 600519 的实际调用。

## 主映射表

| 分析动作 | 工具 | 参数模板 | 关键返回 | 状态 |
|---|---|---|---|---|
| 名称→代码 | `tdx_lookup_stock` | `query="贵州茅台"`；港股加 `range="HK-GP"` | 代码、名称、setcode、别名 | ✅ |
| 实时行情 + 估值 | `tdx_quotes` | `code="600519", setcode="1", hasCwInfo="1"`；港股 `code="00700", setcode="31"` | 现价、涨跌幅、PE、总市值、股息率、EPS、每股净资产（**PB 需用现价 ÷ 每股净资产自算**） | ✅ |
| 盘口深度 | `tdx_quotes` | 加 `bspNum="10"` | 买卖十档 | 🟡 |
| 长期走势 | `tdx_kline` | `code="00700", setcode="31", period="5", wantNum="260"`（港股周线实测）；A 股换 `setcode="1"`、日线用 `period="4"` | 周线序列，用于回撤与趋势 | ✅ |
| 利润表（25 期） | `tdx_api_data` | `entry="TdxShareCW.ph_agf10_cw_lyb", fixedTag="00101", code="600519"` | 营收、成本、净利、归母净利、扣非、EPS，单位**元** | ✅ |
| 资产负债表 | `tdx_api_data` | `entry="TdxShareCW.ph_agf10_cw_zcfzb", code="600519"` | 总资产、负债、归母权益 | 🟡 |
| 现金流量表 | `tdx_api_data` | `entry="TdxShareCW.ph_agf10_cw_xjllb", fixedTag="00101", code="600519"` | 经营现金流净额、购建固定资产支付的现金 → FCF | ✅ |
| 主营构成 | `tdx_api_data` | `entry="TdxShareCW.ph_agf10_jyfx", fixedTag="00202", code="600519"` | 分业务/分地区收入占比 | 🟡 |
| 估值历史分位 | `tdx_api_data` | `entry="TdxShareCW.ph_agf10_gzfx", extraOne="1Y", extraTwo="PE", code="600519"` | 日频估值序列 | ⚠️ |
| 分红概览 | `tdx_api_data` | `entry="TdxSharePCCW.tdxf10_gg_fhrz", fixedTag="pxmz", code="600519"` | 分红率、股息率、连续性 | 🟡 |
| 十大流通股东 | `tdx_api_data` | `entry="TdxSharePCCW.tdxf10_gg_gdyj", fixedTag="ltgd", code="600519"` | 股东名单与集中度 | 🟡 |
| 主营业务资料 | `tdx_api_data` | `entry="TdxSharePCCW.tdxf10_gg_gsgk", fixedTag="0", code="600519"` | 行业分类、上市日期、员工数 | 🟡 |
| 主力资金流 | `tdx_api_data` | `entry="TdxSharePCCW.tdxf10_gg_jyds", fixedTag="zjlx", code="600519"` | 净流入（仅辅助，不作结论） | 🟡 |
| 券商一致预期 | `tdx_api_data` | `entry="CWServ.tdxf10_gg_ybpj", fixedTag="yzyq", code="600519"` | 一致 EPS、评级分布 | 🟡 |
| 港股三表 | `tdx_api_data` | `entry="TdxSharePCCW.skef10_hk_cwfx", fixedTag="1/2/3", code="00700"` | 损益 / 资产负债 / 现金流 | 🟡 |
| 候选池筛选 | `tdx_screener` | `message="ROE大于15%且市盈率低于25", pageSize="15"` | 代码、名称、现价、当期 ROE、PE、负债率、营收、成本；**按当期 ROE 降序** | ✅ |
| 个股研报 | `wenda_report_query` | `name="贵州茅台", bdate="20260101", edate="20261107"` | 评级、目标价、观点摘要 | 🟡 |
| 公司公告 | `wenda_notice_query` | `name="贵州茅台", bdate="...", edate="..."` | 定期报告、临时公告 | 🟡 |
| 相关资讯 | `wenda_news_query` | `name="贵州茅台", bdate="...", edate="..."` | 近期事件 | 🟡 |
| 宏观数据 | `wenda_macro_query` | `query="中国\|20260101\|20261107\|CPI"` | 指标序列 | 🟡 |
| 五年 ROE / 毛利 / 净利序列 | `tdx_indicator_select` | `message="山西汾酒、公牛集团 近五年ROE、毛利率、净利率"` | 按报告期返回序列，**支持多只一次查**，字段名自带报告期 | ✅ |

## 已实测的参数陷阱

这几条是真金白银踩出来的，写死在流程里，别自己改。

### 1. `tdx_quotes` 需要 code + setcode，不是数组

```text
正确：code="600519" setcode="1" hasCwInfo="1"
错误：codes=["600519"] fields=["price"]
```

`setcode`：沪市 6/68 开头 = `1`，深市 00/30 开头 = `0`，北交所 43/83/87 = `2`，港股 = `31`。
**code 与 setcode 不匹配时不报错，直接返回空**——这是最容易误判成"没这只股票"的地方。

### 2. 两个工具的单位差一万倍

| 来源 | 字段 | 数值 | 单位 |
|---|---|---|---|
| `tdx_api_data` 利润表 | 营业收入 | 130,970,743,649.04 | 元 |
| `tdx_quotes` CwInfo | YYSR | 13,097,074 | **万元** |

同为 600519 的 2026 三季报，前者是元，后者是万元。CwInfo 里的 `ZGB`（总股本）、`LTGB`（流通股本）也是万股。
**换算规则**：CwInfo 数值 × 10,000 = 元。

### 3. 利润表一次返回 25 期，`pageSize` 管不住

`pageSize="6"` 依然返回 2020 年报至今全部 25 期。做法是**取回后在本地按 `截止日期` 筛最近 5 个年报**，不要指望服务端分页。
另外注意"年报/中报/三季报"混排，做五年 ROE 趋势时只筛 `截止日期` 以"年报"结尾的行，否则会把单季和累计混在一起。

### 4. 估值历史接口是上下文炸弹

`ph_agf10_gzfx` 传 `extraOne="5Y"` 会返回 **1,212 条日频数据**，单次输出约 13 万字符，直接撑爆上下文。

- 必须降级为 `extraOne="1Y"`，或干脆不用
- 替代方案：用 `tdx_quotes` 拿当前 PE/PB，配合五年 EPS 自己推历史区间
- 该接口返回列名是 `交易日` / `行业估值`，字段含义需与个股口径核对后再引用

### 5. `tdx_lookup_stock` 是模糊匹配

搜"贵州茅台"会返回 10 条（贵州轮胎、贵州燃气、贵州银行……）。
规则：**名称完全一致者优先**；没有完全匹配就列前 3 条让用户选，不许默认取第一条。

### 6. K 线周期是数字，不是单词

```text
正确：period="4"（日线）/ period="5"（周线）/ period="6"（月线）
错误：period="week" / period="day"
```

`period` 默认值是 `"0"`（5 分钟线），**不传就是分钟线**。查历史走势必须显式写 `"4"` 或 `"5"`，否则会拿到一堆分钟内数据还以为取错了股票。
数量用 `wantNum`（上限 1000），不是 `count`。

### 7. 港股的三处差异

- 行情有 **15 分钟延迟**（返回里 `BaseInfo.DelayHQMin = 15`），不能当实时价用
- 价格是长小数（`419.800018`），报告统一四舍五入到两位
- K 线成交量的单位是**股**，A 股是**手**，别直接比大小

### 8. `tdx_screener` 只产出候选池，不是答案

```text
正确：message="ROE大于15%且市盈率低于25" pageSize="15"
错误：query="..." limit=30
```

- 参数是自然语言 `message`，分页是 `pageSize`
- 返回**按当期 ROE 降序**，头部必然被"小分母"公司占据（次新、亏损转盈、重组后）
- 复合条件能解析，但"连续 5 年""上市满 5 年"这类**时间维度不支持**，必须自己回查
- 返回列已含 `资产负债率`、`营业成本`、`营业收入`，可以直接算毛利率，不必再取数

**有效的筛法**（实测）：用"股息率 >4% + ROE >15% + PE <20 + 负债率 <50%"组合，得到 22 只，再逐只核五年序列。同样的市场，换成按 ROE 降序取头部 15 只，全部在 L0/L2 被淘汰。差别就在前者的条件本身排除了次新与一次性收益。

### 9. `tdx_indicator_select` 是五年序列的唯一便捷入口

```text
正确：message="山西汾酒、公牛集团 近五年ROE、毛利率、净利率"
```

- `message` 里必须同时有**实体**和**指标**，否则解析失败
- 一次可写多只股票（顿号/逗号分隔），比分头调 `tdx_quotes` 省很多次调用
- 返回 JSON 数组，key 形如 `净资产收益率ROE(平均)<br>2025-12-31(报告期:20251231)`，需按报告期解析
- 口径是**平均净资产**；`tdx_quotes` 算的是期末净资产，两者能差 3–5 个百分点，报告里注明用的哪个

## 数据字典（`tdx_quotes` 实测字段）

| 路径 | 含义 | 单位 |
|---|---|---|
| `HQInfo.Now` | 最新价 | 元 |
| `HQInfo.Close` | 昨收 | 元 |
| `HQInfo.HQDate` / `HQTime` | 行情日期 / 时间 | — |
| `HQInfo.Volume` | 成交量 | 手 |
| `HQInfo.Amount` | 成交额 | 元 |
| `ExtInfo.SYL` | 市盈率（动态） | 倍 |
| `ExtInfo.ZSZ` | 总市值 | 元 |
| `ExtInfo.MGSY` | 每股收益 | 元 |
| `ExtInfo.MGJZC` | 每股净资产 | 元 |
| `ExtInfo.股息率` | 股息率 | % |
| `ExtInfo.ZGB` / `LTGB` | 总股本 / 流通股本 | 万股 |
| `CwInfo.YYSR` / `JLY` / `JZC` | 营收 / 净利润 / 净资产 | 万元 |
| `CwInfo.GDRS` | 股东人数 | 户 |

## 降级路径

| 场景 | 处理 |
|---|---|
| 港股行情 | 支持，但有 15 分钟延迟；价格四舍五入到两位，报告注明延迟 |
| 港股 K 线 | 支持，`period` 用数字（周线 `"5"`），成交量单位是股不是手 |
| 财报接口空返回 | 换 `fixedTag="00102"`（单季）再试一次；仍空则标注"财务数据缺失"，体检结论降级 |
| 估值历史过大 | 缩短到 `1Y`，或用 PE 绝对值 + 行业分位替代 |
| 研报/公告空 | 如实说"未找到"，不影响主结论 |
| 非交易日 | 用最近收盘价，并标注 `HQDate` |
| 停牌 | 行情为最后成交价，必须标注"停牌" |

## 禁止事项

- 禁止不查码直接传中文名给 `tdx_quotes` / `tdx_api_data`
- 禁止用 `mode="raw"` 手工拼 Params 数组（顺序无文档，必错）
- 禁止把 `tdx_screener` 的自然语言结果直接当"推荐名单"，它只产出候选池
- 禁止在报告里出现工具没返回过的数字
