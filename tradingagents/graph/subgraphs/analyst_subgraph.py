# TradingAgents/graph/subgraphs/analyst_subgraph.py
"""Analyst 子图工厂 — 将分析师的 tool-call 循环封装为独立可并行子图.

每个分析师子图的内部结构:
    START → analyst ⇄ tools → clear → END

通过 create_analyst_runner() 创建的 runner 节点可在父图中
被 Send API 并行调度, 互不干扰.
"""

from collections.abc import Callable

from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from tradingagents.agents.utils.agent_states import AgentState
from tradingagents.agents.utils.agent_states import create_msg_delete

# 分析师类型 → AgentState 中输出报告字段的映射
ANALYST_REPORT_FIELD: dict[str, str] = {
    "market": "market_report",
    "social": "sentiment_report",
    "news": "news_report",
    "fundamentals": "fundamentals_report",
}


def _should_continue_tools(state: AgentState):
    """通用 tool-call 条件判断: 有 tool_calls → tools, 否则 → clear."""
    messages = state["messages"]
    last_message = messages[-1]
    if last_message.tool_calls:
        return "tools"
    return "clear"


def create_analyst_subgraph(
    analyst_node_fn: Callable,
    tool_node: ToolNode,
):
    """创建并编译封装了 tool-call 循环的分析师子图.

    Args:
        analyst_node_fn: 分析师节点函数 (由 create_*_analyst(llm) 返回)
        tool_node: 该分析师对应的 ToolNode

    Returns:
        已编译的 StateGraph
    """
    workflow = StateGraph(AgentState)
    workflow.add_node("analyst", analyst_node_fn)
    workflow.add_node("tools", tool_node)
    workflow.add_node("clear", create_msg_delete())

    workflow.add_edge(START, "analyst")
    workflow.add_conditional_edges(
        "analyst", _should_continue_tools, ["tools", "clear"]
    )
    workflow.add_edge("tools", "analyst")
    workflow.add_edge("clear", END)

    return workflow.compile()


def create_analyst_runner(
    analyst_type: str,
    compiled_subgraph,
) -> Callable:
    """创建并行安全的 runner 节点函数.

    runner 内部调用已编译的子图, 仅将对应报告字段返回父图,
    避免子图内部 messages 泄漏到父图 state.

    Args:
        analyst_type: 分析师类型 (market / social / news / fundamentals)
        compiled_subgraph: 已编译的分析师子图

    Returns:
        可作为 StateGraph.add_node() 参数的节点函数
    """
    report_field = ANALYST_REPORT_FIELD[analyst_type]

    def runner(state):
        # 仅传入分析师需要的最小字段, 每个子图独立运行
        input_state = {
            "messages": [HumanMessage(content="Begin analysis")],
            "company_of_interest": state["company_of_interest"],
            "trade_date": state["trade_date"],
        }
        result = compiled_subgraph.invoke(input_state)
        return {report_field: result.get(report_field, "")}

    return runner
