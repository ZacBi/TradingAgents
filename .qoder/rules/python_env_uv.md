---
description: Python 工程化规范，强制使用 uv 进行包管理与环境隔离
globs: pyproject.toml, uv.lock, .python-version
---

# Python Engineering & Environment

## 1. 依赖管理工具 (uv)
本项目强制使用 `uv` 作为唯一包管理工具，严禁直接使用 `pip` 或 `poetry`。

## 2. 标准操作流程
- **同步环境**：更新依赖后，必须执行 `uv sync`。
- **依赖锁定**：新增包时，使用 `uv add <package>`，并确保生成/更新 `uv.lock`。
- **隔离执行**：在生成运行指令或脚本时，必须前缀 `uv run` 以确保环境一致性。
- **脚本依赖**：对于单文件脚本，推荐使用 `uv` 的内联依赖定义（PEP 723）。

## 3. 目录与环境隔离
- 严禁在代码中硬编码虚拟环境路径。
- 引导用户通过 `uv venv` 初始化项目。