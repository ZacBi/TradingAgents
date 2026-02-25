# TradingAgents/prompts/registry.py
"""Prompt name registry - defines standardized prompt names for Langfuse."""


class PromptNames:
    """Standardized prompt names for the TradingAgents system.
    
    Naming convention: {category}-{role}
    Categories: expert, analyst, researcher, manager, risk, trader
    """
    
    # Expert Prompts (5)
    EXPERT_BUFFETT = "expert-buffett"
    EXPERT_MUNGER = "expert-munger"
    EXPERT_LYNCH = "expert-lynch"
    EXPERT_LIVERMORE = "expert-livermore"
    EXPERT_GRAHAM = "expert-graham"
    
    # Analyst Prompts (4)
    ANALYST_MARKET = "analyst-market"
    ANALYST_SOCIAL = "analyst-social"
    ANALYST_NEWS = "analyst-news"
    ANALYST_FUNDAMENTALS = "analyst-fundamentals"
    
    # Researcher Prompts (2)
    RESEARCHER_BULL = "researcher-bull"
    RESEARCHER_BEAR = "researcher-bear"
    
    # Manager Prompts (2)
    MANAGER_RESEARCH = "manager-research"
    MANAGER_RISK = "manager-risk"
    
    # Risk Debator Prompts (3)
    RISK_AGGRESSIVE = "risk-aggressive"
    RISK_CONSERVATIVE = "risk-conservative"
    RISK_NEUTRAL = "risk-neutral"
    
    # Trader Prompt (1)
    TRADER_MAIN = "trader-main"

    # Valuation Prompt (1)
    VALUATION_MOAT = "valuation-moat"


# Langfuse label mapping (for organization in UI)
PROMPT_LABELS = {
    PromptNames.EXPERT_BUFFETT: "expert/buffett",
    PromptNames.EXPERT_MUNGER: "expert/munger",
    PromptNames.EXPERT_LYNCH: "expert/lynch",
    PromptNames.EXPERT_LIVERMORE: "expert/livermore",
    PromptNames.EXPERT_GRAHAM: "expert/graham",
    PromptNames.ANALYST_MARKET: "analyst/market",
    PromptNames.ANALYST_SOCIAL: "analyst/social",
    PromptNames.ANALYST_NEWS: "analyst/news",
    PromptNames.ANALYST_FUNDAMENTALS: "analyst/fundamentals",
    PromptNames.RESEARCHER_BULL: "researcher/bull",
    PromptNames.RESEARCHER_BEAR: "researcher/bear",
    PromptNames.MANAGER_RESEARCH: "manager/research",
    PromptNames.MANAGER_RISK: "manager/risk",
    PromptNames.RISK_AGGRESSIVE: "risk/aggressive",
    PromptNames.RISK_CONSERVATIVE: "risk/conservative",
    PromptNames.RISK_NEUTRAL: "risk/neutral",
    PromptNames.TRADER_MAIN: "trader/main",
    PromptNames.VALUATION_MOAT: "valuation/moat",
}

# All prompt names as a list (for iteration)
ALL_PROMPT_NAMES = [
    PromptNames.EXPERT_BUFFETT,
    PromptNames.EXPERT_MUNGER,
    PromptNames.EXPERT_LYNCH,
    PromptNames.EXPERT_LIVERMORE,
    PromptNames.EXPERT_GRAHAM,
    PromptNames.ANALYST_MARKET,
    PromptNames.ANALYST_SOCIAL,
    PromptNames.ANALYST_NEWS,
    PromptNames.ANALYST_FUNDAMENTALS,
    PromptNames.RESEARCHER_BULL,
    PromptNames.RESEARCHER_BEAR,
    PromptNames.MANAGER_RESEARCH,
    PromptNames.MANAGER_RISK,
    PromptNames.RISK_AGGRESSIVE,
    PromptNames.RISK_CONSERVATIVE,
    PromptNames.RISK_NEUTRAL,
    PromptNames.TRADER_MAIN,
    PromptNames.VALUATION_MOAT,
]
