# buffett-value-investing

巴菲特价值投资分析技能。判定护城河、拆解 ROE 质量、估算内在价值与安全边际，通过通达信 MCP 获取行情与财务数据。

## 依赖

| 依赖 | 说明 |
|---|---|
| 通达信 MCP 连接器 | 必需。工具名以 `tdx_` 开头（`tdx_quotes`、`tdx_api_data`、`tdx_lookup_stock` 等） |
| Python 3.8+ | 可选，仅 `scripts/valuation.py` 需要；无第三方库 |

缺少 MCP 连接器时，技能会明确提示并停止取数，不会用模型记忆编造财务数据。

## 安装

把整个 `buffett-value-investing/` 目录放进宿主的 skills 目录。目录名必须与 `SKILL.md` 里的 `name` 一致。

| 宿主 | 典型路径 |
|---|---|
| WorkBuddy | `~/.workbuddy/skills/buffett-value-investing/` |
| Claude Code | `~/.claude/skills/buffett-value-investing/` |
| Codex CLI / 兼容 `.agents` 的客户端 | `.agents/skills/buffett-value-investing/` |
| GitHub Copilot | `.github/skills/buffett-value-investing/` |
| KimiCode / CodeBuddy 等 | 以其文档中的 skills 目录为准；多数支持项目级 `.xxx/skills/` 或用户级目录 |

项目级安装（只对当前仓库生效）把目录放到工作区的 skills 路径即可，其余不变。

### 关于 `agent_created`

本包 frontmatter 严格遵循 Agent Skills 规范的白名单字段，**不含** `agent_created`。
如果在 WorkBuddy 内需要用 `skill_manage` 编辑或删除该技能，可手动在 `SKILL.md` 的 frontmatter 末尾补一行：

```yaml
agent_created: true
```

其他宿主会忽略该字段，补上不影响兼容性。

## 快速验证

```bash
# 内在价值与安全边际
python scripts/valuation.py dcf --fcf 120,135,150 --shares 12.5 --net-cash 30 --price 1453

# ROE 三因子分解
python scripts/valuation.py dupont --revenue 1309.71 --net-profit 644.67 --assets 3183.05 --equity 2712.05

# 安全边际判定
python scripts/valuation.py margin --price 1453 --intrinsic 2400
```

三组命令应能直接跑通，无需任何第三方库。

## 结构

```text
buffett-value-investing/
├── SKILL.md                       主入口：流程、路由、红线
├── README.md                      本文件
├── references/
│   ├── tdx-tool-map.md            工具映射与实测参数陷阱
│   ├── analysis-framework.md      三问、护城河、ROE、安全边际、六层漏斗
│   ├── report-templates.md        五套报告模板
│   ├── data-guardrails.md         单位、时效、空数据、口径
│   └── coaching.md                亏损梳理六步
├── scripts/
│   └── valuation.py               DCF / 杜邦 / 安全边际
```

## 工具可用性

`references/tdx-tool-map.md` 中标注了每条映射的验证状态：

- ✅ 开发时真实调用验证过
- ⚠️ 可调用但有陷阱（如估值历史接口返回 1200+ 条日频数据）
- 🟡 与已验证接口同族、参数模式一致，但未逐一实测

首次在某个宿主使用时，建议先跑一条 `tdx_quotes` 确认连接正常，再走完整流程。

## 合规

本技能输出为基于公开数据的研究分析，不构成投资建议，不承诺收益，不提供买卖点位。投资决策与风险由使用者本人承担。

## 版本

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.1.2 | 2026-11-07 | 复跑验证：`dcf` 在 FCF 三年复合增速为负时给出显式警告并要求用 `--growth` 重算（否则会算出 -10% 的荒谬估值） |
| 1.1.1 | 2026-11-07 | 清理审计：删除未使用的 HTML 报告模板目录；脚本移除死代码、统一安全边际措辞、补 `--price` 缺 `--shares` 校验；修正 `hasCwInfo` 不含 ROE/PB 的错误描述；诊断报告字数校准 |
| 1.1.0 | 2026-11-07 | 审计修正：补毛利率/净利率/FCF 门槛；接入 `tdx_indicator_select` 五年序列；改为股息率主导筛选；DCF 增加 FCF 波动检测；补 CwInfo 报告期陷阱 |
| 1.0.0 | 2026-11-07 | 首版。基于 `慢慢变富-巴菲特.md` 重构，接入通达信 MCP |
