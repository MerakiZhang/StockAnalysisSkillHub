# Stock Analysis Skill Hub

用于集中维护可独立使用的股票分析 Agent Skills。每个 Skill 都有自己的完整源码、文档、依赖和许可证，不依赖 Hub 中的另一个 Skill。

## 项目结构

```text
StockAnalysisSkillHub/
├── skills/                  # 可阅读、修改和验证的 Skill 源码
│   ├── ashare-price-action-analysis/
│   └── buffett-value-investing/
├── dist/                    # 与源码同步的分发 ZIP
├── tools/
│   └── package_skills.py    # 标准库打包与同步检查
├── README.md
├── LICENSE                  # 项目级 MIT 许可证
└── .gitignore
```

## Skill 索引

| Skill | 用途 | 主要数据与运行要求 | 许可证 |
|---|---|---|---|
| [ashare-price-action-analysis](skills/ashare-price-action-analysis/SKILL.md) | A 股两阶段 Price Action 分析、交易方案校验和增量续析 | Python 3.11+、AkShare 新浪/腾讯接口 | MIT |
| [buffett-value-investing](skills/buffett-value-investing/SKILL.md) | A 股/港股护城河、财务质量、内在价值和安全边际分析 | 通达信 MCP；估值脚本使用 Python 标准库 | MIT |

项目统一采用根目录 `LICENSE` 中的 MIT 许可证，不保留各 Skill 的独立许可证文件。`ashare-price-action-analysis` 的原项目来源和版权署名保留在其 `NOTICE` 中。

## 使用方式

1. 打开对应 `skills/<skill-name>/SKILL.md`，按其中的适用场景、依赖和执行约定使用。
2. 需要导入 Agent 时，复制整个 Skill 目录，不要只复制 `SKILL.md`。
3. 只需要分发或备份时，使用 `dist/<skill-name>.zip`；ZIP 内含同名顶层目录。
4. 不在 Hub 根目录合并两个 Skill 的 `scripts/`、`references/` 或依赖环境。

## 更新与打包

修改源码后，在项目根目录运行：

```bash
<PYTHON> tools/package_skills.py
```

`<PYTHON>` 是能运行 Python 标准库脚本的解释器。工具会打包 `skills/` 下的每个 Skill，排除版本库、缓存、本地环境文件和常见密钥文件，并生成内容确定、路径统一的 ZIP。

只检查现有 ZIP 是否与源码同步，不重写文件：

```bash
<PYTHON> tools/package_skills.py --check
```

打包前的名称检查不能替代 Skill 规范验证或功能测试。新增 Skill 时应提供完整 `SKILL.md`、所需资源、依赖和许可证，并更新本 README 的索引。
