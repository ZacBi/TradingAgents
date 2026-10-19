# 项目根目录结构说明

第一层级文件与目录的用途说明。

## 目录


| 路径                          | 说明                                                                     |
| --------------------------- | ---------------------------------------------------------------------- |
| **tradingagents/**          | 主包：图、Agent、数据流、配置、CLI 等                                                |
| **dashboard/**              | Streamlit 看板入口（`streamlit run dashboard/app.py`）                       |
| **tests/**                  | 单元测试与 e2e 测试                                                           |
| **scripts/**                | 运维与示例脚本（如 `run_single_propagate.py`、`smoke_yfinance.py`、`init-db.sql`） |
| **docs/**                   | 文档：架构（`arch/`）、使用（`usage/`）、PR 描述（`pr/`）等                              |
| **assets/**                 | 静态资源与架构图源文件（如 D2 图在 `assets/arch/`）                                    |
| **eval_results/**           | 运行/评估输出目录（已在 .gitignore）                                               |
| **.venv/**                  | uv 虚拟环境（已在 .gitignore）                                                 |
| **.cursor/**                | Cursor 规则与配置                                                           |
| **.qoder/**                 | Qoder 规范与 spec                                                         |
| **.agents/**                | Agent 技能等                                                              |
| **.git/**                   | 版本控制                                                                   |
| **.pytest_cache/**          | pytest 缓存（已在 .gitignore）                                               |
| **.ruff_cache/**            | ruff 缓存（已在 .gitignore）                                                 |
| **tradingagents.egg-info/** | setuptools 构建产物（已在 .gitignore）                                         |


## 根目录文件


| 文件                     | 说明                                                             |
| ---------------------- | -------------------------------------------------------------- |
| **pyproject.toml**     | 项目元数据、依赖、入口（`tradingagents = tradingagents.cli.main:app`）、工具配置 |
| **uv.lock**            | uv 依赖锁文件（建议提交以保证可复现构建）                                         |
| **README.md**          | 项目说明与使用说明                                                      |
| **LICENSE**            | 许可证（Apache-2.0）                                                |
| **AUTHORS.md**         | 作者与维护者                                                         |
| **.gitignore**         | Git 忽略规则                                                       |
| **.env.example**       | 环境变量示例（复制为 `.env` 后填写密钥；`.env` 已忽略）                            |
| **model_routing.yaml** | 模型路由配置（按角色选择 LLM）                                              |
| **docker-compose.yml** | 本地 Docker 编排（如需要）                                              |
| **requirements.txt**   | pip 依赖列表（可选，与 pyproject 并存）                                    |
| **skills-lock.json**   | Cursor 技能锁文件（若使用）                                              |


## 运行时/本地文件（不提交）

- **.env**：本地环境变量与密钥（已忽略）
- **tradingagents.db**：默认 SQLite 数据库路径（`*.db` 已忽略）
- **.DS_Store**：macOS 目录元数据（建议忽略）

## PR 描述

PR 相关描述文档已移至 **docs/pr/**：

- `docs/pr/PR_DESCRIPTION_OPTIMIZED.md`
- `docs/pr/PR_DESCRIPTION.md`

