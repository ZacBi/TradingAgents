# 项目文件组织结构深度审查（魔改版）

> 不考虑历史包袱，按「开源魔改项目」做破坏性调整。

## 1. 现状与问题（简述）

- **配置三处**：`default_config.py`（包根）、`config/`（Pydantic）、`dataflows/config.py`（运行时 dict），两套 `get_config` 易混淆。
- **入口冗余**：根目录 `main.py`、`test.py` 与 CLI 重叠或为临时脚本。
- **文档规范**：规则要求图表在 `assets/`，实际在 `docs/arch/`。
- **CLI 包位**：`cli` 与 `tradingagents` 平级，entry_point 为 `tradingagents = "cli.main:app"`。

---

## 2. 推荐调整（激进、可一次性做）

### 2.1 配置收敛

| 调整 | 说明 |
|------|------|
| 删除 `tradingagents/default_config.py` | 默认值迁入 `tradingagents/config/defaults.py`（或由 `settings.py` 提供），单一来源 |
| 运行时 config 迁出 dataflows | 将 `dataflows/config.py` 的 `get_config`/`set_config`/`initialize_config` 迁入 `tradingagents/config/runtime.py`，dataflows 与 graph 改为从 `tradingagents.config` 导入 |
| 统一对外入口 | `tradingagents.config` 仅暴露：`get_settings()`、`get_config()`（运行时 dict）、`set_config()`；Pydantic 与 dict 职责在 docstring 写清，避免同名歧义（可保留 `get_config` 仅指运行时，env 用 `get_settings().to_dict()`） |

### 2.2 根目录与入口清理

| 调整 | 说明 |
|------|------|
| 删除根目录 `main.py` | 功能由 `tradingagents analyze` 覆盖；若需单次传播脚本，放到 `scripts/run_single_propagate.py` |
| 删除或迁移根目录 `test.py` | 迁入 `scripts/smoke_yfinance.py` 或删除，根目录不再保留临时脚本 |
| 根目录仅保留 | README、pyproject.toml、uv.lock、.env.example、.gitignore、docker-compose、model_routing.yaml 等配置；`tradingagents/`、`cli/`、`dashboard/`、`tests/`、`scripts/`、`docs/`、`assets/` |

### 2.3 文档与图表规范

| 调整 | 说明 |
|------|------|
| 建立 `assets/` | 在项目根目录创建 `assets/` |
| 图表迁入 assets | 将 `docs/arch/*.d2` 移至 `assets/`（如 `assets/arch/01-current-architecture.d2`），文档中引用新路径；或保留 `docs/arch/` 但在规则中明确例外并注明「图表源文件推荐 assets，现有 docs/arch 保留」 |
| 二选一 | 要么迁移到 assets 满足现有规则，要么改规则允许 docs/arch 并存 |

### 2.4 CLI 与包结构（可选但推荐）

| 调整 | 说明 |
|------|------|
| CLI 收进主包 | 将 `cli/` 整体移为 `tradingagents/cli/`，entry_point 改为 `tradingagents = "tradingagents.cli.main:app"` |
| pyproject | `include = ["tradingagents*"]`，删除 `cli*`；package-data 若有 `cli` 的 static 改为 `tradingagents/cli/static` |

这样根目录只有「一个主包 + tests + scripts + docs + assets」，入口唯一，无顶层 `cli` 包。

### 2.5 不动的部分

- **tradingagents 内部子包**：agents、experts、graph、dataflows、prompts、valuation、research、backtest、database、llm_clients、embeddings、observability、utils 等保持现有划分，不大规模合并或拆包。
- **dashboard**：可继续独立目录 `dashboard/`，或随偏好迁为 `tradingagents/dashboard/` 用子命令启动；非必须。

---

## 3. 实施顺序建议

1. **配置收敛**：default_config → config；dataflows/config → config/runtime；改所有 import。
2. **根目录清理**：删 main.py、test.py（或迁到 scripts）。
3. **文档/图表**：建 assets/，迁 D2 或改规则。
4. **CLI 入主包**（可选）：cli → tradingagents/cli，改 pyproject 与 entry_point。

每步后跑：`uv run pytest tests/`、`tradingagents analyze`（或等价的单次传播）、`tradingagents backtest`。

---

## 4. 小结

| 类别 | 建议 |
|------|------|
| 配置 | 收敛到 `tradingagents/config`，单一默认来源 + 明确运行时 get/set，去掉 dataflows 里的 config |
| 根目录 | 删冗余入口与临时脚本，只保留配置与目录结构 |
| 文档 | 满足规则：assets/ 存图，或规则允许 docs/arch |
| CLI | 推荐收进 tradingagents 成子包，单包单入口 |
| 内部子包 | 不做大动，保持当前领域划分 |
