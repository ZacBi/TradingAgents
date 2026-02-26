# 插件系统使用指南

## 概述

插件系统允许动态加载和注册自定义Agent、数据源、策略等组件，无需修改核心代码。

## 快速开始

### 1. 创建插件

创建一个自定义Analyst插件：

```python
# my_plugins/custom_analyst.py

from tradingagents.agents.base import BaseAnalyst
from tradingagents.prompts import PromptNames

class CustomAnalyst(BaseAnalyst):
    """Custom analyst plugin."""
    
    def __init__(self, llm):
        from tradingagents.agents.utils.news_data_tools import get_news
        tools = [get_news]
        super().__init__(
            llm=llm,
            tools=tools,
            prompt_name=PromptNames.ANALYST_NEWS,  # 或自定义prompt
            report_field="custom_report",
            name="Custom Analyst",
        )

# 插件注册
PLUGIN_METADATA = {
    "plugin_id": "custom_analyst",
    "name": "Custom Analyst",
    "version": "1.0.0",
    "description": "A custom analyst plugin",
    "plugin_type": "analyst",
    "entry_point": CustomAnalyst,
    "config_schema": {},
}

def register_plugin(registry):
    """Register this plugin."""
    from tradingagents.plugins.registry import PluginRegistry
    registry.register(
        plugin_id=PLUGIN_METADATA["plugin_id"],
        name=PLUGIN_METADATA["name"],
        version=PLUGIN_METADATA["version"],
        description=PLUGIN_METADATA["description"],
        plugin_type=PLUGIN_METADATA["plugin_type"],
        entry_point=PLUGIN_METADATA["entry_point"],
        config_schema=PLUGIN_METADATA.get("config_schema"),
    )
```

### 2. 配置插件目录

```python
config = {
    "plugins_enabled": True,
    "plugin_dirs": [
        "./my_plugins",
        "./custom_agents",
    ],
}

graph = TradingAgentsGraph(config=config)
# 插件会自动发现和加载
```

### 3. 使用插件

```python
# 插件会自动注册到NodeFactory
# 可以在selected_analysts中使用
selected_analysts = ["market", "custom_analyst", "news"]
graph = TradingAgentsGraph(config=config)
# custom_analyst插件会被自动加载和使用
```

## 插件类型

### Analyst插件

```python
class MyAnalyst(BaseAnalyst):
    def __init__(self, llm):
        tools = [...]  # 定义工具
        super().__init__(
            llm=llm,
            tools=tools,
            prompt_name=PromptNames.ANALYST_MARKET,
            report_field="my_report",
            name="My Analyst",
        )
```

### Researcher插件

```python
class MyResearcher(BaseResearcher):
    def __init__(self, llm, memory):
        super().__init__(
            llm=llm,
            memory=memory,
            prompt_name=PromptNames.RESEARCHER_BULL,
            prefix="My Researcher",
            name="My Researcher",
        )
```

### 数据源插件

```python
def get_custom_data(ticker: str, date: str) -> str:
    """Custom data source function."""
    # 实现数据获取逻辑
    return data

# 注册为数据源插件
PLUGIN_METADATA = {
    "plugin_id": "custom_data_source",
    "plugin_type": "data_source",
    "entry_point": get_custom_data,
}
```

## 插件管理

### 手动管理插件

```python
from tradingagents.plugins import PluginManager

# 创建插件管理器
plugin_manager = PluginManager(plugin_dirs=["./my_plugins"])

# 发现和加载插件
loaded_count = plugin_manager.discover_and_load_plugins()
print(f"Loaded {loaded_count} plugins")

# 列出可用插件
plugins = plugin_manager.list_available_plugins()
for plugin in plugins:
    print(f"{plugin['plugin_id']}: {plugin['name']}")

# 创建插件实例
instance = plugin_manager.create_plugin_instance(
    plugin_id="custom_analyst",
    config={"custom_param": "value"},
)
```

### 从模块加载

```python
# 从Python模块加载插件
plugin_manager.load_plugin_from_module("my_plugins.custom_analyst")
```

## 插件配置

### 配置文件方式

```yaml
# workflow_config.yaml
plugins:
  enabled: true
  directories:
    - ./my_plugins
    - ./custom_agents
  custom_analyst:
    enabled: true
    config:
      custom_param: value
```

## 最佳实践

1. **遵循接口规范**：插件应继承相应的基类
2. **提供元数据**：包含完整的插件元数据
3. **错误处理**：插件应处理自己的错误
4. **配置验证**：验证插件配置
5. **文档**：为插件提供使用文档

## 故障排查

### 插件未加载

```python
# 检查插件是否加载
plugins = plugin_manager.list_available_plugins()
if "custom_analyst" not in [p["plugin_id"] for p in plugins]:
    print("Plugin not loaded, check:")
    print("1. Plugin directory is correct")
    print("2. Plugin defines register_plugin or PLUGIN_METADATA")
    print("3. No import errors")
```

### 插件注册失败

```python
# 检查注册状态
metadata = plugin_manager.registry.get("custom_analyst")
if metadata:
    print(f"Plugin registered: {metadata.name}")
else:
    print("Plugin not registered")
```
