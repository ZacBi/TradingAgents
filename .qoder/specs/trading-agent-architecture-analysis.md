# TradingAgents 架构分析与升级方案

## 项目概览

**项目**: TradingAgents - 多智能体LLM金融交易框架  
**核心架构**: LangGraph编排 + 10个专业Agent + ChromaDB记忆  
**数据源**: YFinance, Finnhub, Reddit, Google News, SimFin  

---

## 一、当前架构（As-Is）

```mermaid
flowchart TD
    subgraph DataLayer["数据层 (硬编码，无统一接口)"]
        YF[YFinance] & FH[Finnhub] & RD[Reddit] & GN[Google News]
    end

    subgraph AnalystLayer["分析师层 (串行，固定4个，相同LLM)"]
        direction LR
        MA[Market Analyst] --> SA[Social Analyst] --> NA[News Analyst] --> FA[Fundamentals Analyst]
    end

    subgraph ResearchLayer["研究层 (固定轮次辩论 max_rounds=1)"]
        Bull[Bull Researcher] <-->|固定2轮| Bear[Bear Researcher]
        Bull & Bear --> RM[Research Manager]
    end

    subgraph ExecLayer["执行层 (固定轮次)"]
        Trader --> Risky & Safe & Neutral
        Risky & Safe & Neutral --> RiskMgr[Risk Manager]
        RiskMgr --> Output[/"BUY / SELL / HOLD"/]
    end

    subgraph Infra["基础设施层"]
        ChromaDB["ChromaDB (简单向量存储)"]
        LLM["LLM: 仅2层 quick_think / deep_think\n所有同层Agent共享同一模型"]
    end

    DataLayer --> AnalystLayer --> ResearchLayer --> ExecLayer

    Missing["❌ 无持仓管理  ❌ 无可观测性  ❌ 无状态持久化\n❌ 无价值投资  ❌ 无专家系统  ❌ 无财报跟踪"]

    style Missing fill:#fee,stroke:#f66,color:#c00
    style DataLayer fill:#fff3e0
    style AnalystLayer fill:#fff8e1
    style ResearchLayer fill:#e8f5e9
    style ExecLayer fill:#e3f2fd
    style Infra fill:#f3e5f5
```

**核心局限**:
- 分析师固定4个，串行执行，无法扩展
- 辩论机制简单，固定轮次，无收敛检测
- 仅2层模型（quick/deep），所有同层Agent共用
- 无价值投资分析、无专家视角
- 无持仓管理、无交易记录
- 无可观测性、无Prompt版本管理

---

## 二、目标架构（To-Be）

```mermaid
flowchart TD
    subgraph Observe["可观测层 - Langfuse (自托管)"]
        Tracing["Tracing: 全链路追踪"]
        PromptMgmt["Prompt Management: 版本控制 + A/B测试"]
        CostTrack["Cost Tracking: 每节点Token消耗"]
        Eval["Evaluation: 决策质量评分"]
    end

    subgraph LLMGateway["LLM网关层 - LiteLLM"]
        direction LR
        Google["Google Gemini"]
        Bailian["百炼 Qwen/DS"]
        OpenRouter["OpenRouter GPT/Claude"]
        Ollama["Ollama 本地模型"]
        Google & Bailian & OpenRouter & Ollama --> UnifiedAPI["统一API接口\n自动fallback / 成本路由 / 负载均衡"]
    end

    subgraph DataLayer2["数据层"]
        direction LR
        subgraph Free["免费数据源"]
            YF2["Yahoo Finance (主力)"]
            FRED["FRED (宏观经济)"]
            FH2["Finnhub (新闻)"]
            RD2["Reddit (情绪)"]
        end
        subgraph Paid["付费数据源"]
            Longport["长桥 Longport API\n港/美/A股实时行情+交易"]
        end
    end

    subgraph AgentOrch["Agent编排层 - LangGraph 1.0\n(Checkpointing | Subgraph | Human-in-the-Loop | Streaming)"]

        subgraph Phase1["阶段1: 数据收集 (并行)"]
            MA2[Market Analyst] & NA2[News Analyst] & SA2[Social Analyst] & FA2[Fundamentals] --> Reports["4份分析报告"]
            DeepRes["Deep Research Agent (可选)"] --> DeepReport["深度研究报告"]
            Earnings["Earnings Tracker (可选)"] --> EarningsAlert["财报预警"]
        end

        subgraph Phase2["阶段2: 多视角分析"]
            subgraph TrendTeam["趋势/投机团队"]
                Bull2["Bull Researcher"] <-->|动态收敛辩论| Bear2["Bear Researcher"]
            end
            subgraph ValueTeam["价值投资团队 (动态选择N个专家)"]
                Buffett["Buffett Agent"]
                Munger["Munger Agent"]
                Lynch["Lynch Agent"]
                Livermore["Livermore Agent"]
                MoreExperts["... (可扩展注册)"]
            end
            TrendTeam & ValueTeam --> RM2["Research Manager (综合裁决)"]
        end

        subgraph Phase3["阶段3: 风险评估 + 执行"]
            Trader2["Trader"] --> RiskTeam["Risk Team (动态收敛辩论)"]
            RiskTeam --> RiskMgr2["Risk Manager"]
            RiskMgr2 --> FinalDecision[/"BUY/SELL/HOLD + 仓位 + 止损"/]
        end

        Phase1 --> Phase2 --> Phase3
    end

    subgraph Persist["持久化层"]
        subgraph SQLiteDB["SQLite 数据库"]
            Positions["positions (持仓)"]
            Trades["trades (交易记录)"]
            Decisions["agent_decisions (决策日志)"]
            NAV["daily_nav (净值曲线)"]
        end
        subgraph ChromaDBE["ChromaDB (增强)"]
            Working["工作记忆 (当日)"]
            Episodic["情节记忆 (历史案例)"]
            Semantic["语义记忆 (市场规律)"]
        end
        Checkpoints["LangGraph Checkpoints\n状态快照，支持回滚/重放"]
    end

    subgraph Display["展示层 (渐进式)"]
        direction LR
        CLI["CLI (已有)"] --> Streamlit["Streamlit Dashboard"] --> WebApp["FastAPI + React"]
    end

    Observe -.->|监控所有Agent节点| AgentOrch
    UnifiedAPI --> AgentOrch
    DataLayer2 --> AgentOrch
    AgentOrch --> Persist
    Persist --> Display

    style Observe fill:#e8eaf6,stroke:#3f51b5
    style LLMGateway fill:#fce4ec,stroke:#e91e63
    style DataLayer2 fill:#fff3e0,stroke:#ff9800
    style AgentOrch fill:#e8f5e9,stroke:#4caf50
    style Persist fill:#f3e5f5,stroke:#9c27b0
    style Display fill:#e0f7fa,stroke:#00bcd4
```

---

## 三、分层模型策略（LLM网关）

### 3.1 设计原则

- 每个Agent节点可**独立配置**最佳模型，不限于特定厂商
- 通过LiteLLM网关统一管理Google Pro、百炼、OpenRouter等多平台
- 支持**fallback链**：首选模型失败时自动降级
- 支持**成本路由**：优先使用免费额度，超额后切换低价模型
- 后续收益稳定后可**一键切换**全部使用最佳模型

### 3.2 节点-模型映射（可配置，非固定）

每个节点定义一个**角色类型**（role_type），通过配置文件映射到具体模型。

**当前可用模型池** (截至2026年2月):

| 平台 | 轻量/快速模型 | 标准模型 | 旗舰/推理模型 |
|------|-------------|---------|-------------|
| **Google** | Gemini 3 Flash | Gemini 3 Pro | Gemini 3.1 Pro, Gemini 3 Deep Think |
| **百炼/Qwen** | Qwen3-Turbo | Qwen3-Max | Qwen3.5-Plus (397B) |
| **OpenAI** | GPT-4.5-mini | GPT-4.5 | GPT-5.2 Codex, o4-mini, o3 |
| **Anthropic** | Claude Haiku 4 | Claude Sonnet 4 | Claude Opus 4.5 |
| **DeepSeek** | DeepSeek-V3.2 | DeepSeek-V3.2 | DeepSeek-R2 Pro |
| **Meta (本地)** | Llama 4 (8B) | Llama 4 (70B) | Llama 4 (405B) |

| 角色类型 | 任务特征 | 推荐模型层级 |
|----------|----------|-------------|
| `data_analyst` | 数据处理、摘要 | 轻量模型 (低成本高速) |
| `researcher` | 论证、分析 | 标准模型 |
| `expert` | 投资哲学推理 | 标准~旗舰模型 |
| `judge` | 综合裁决 | 旗舰模型 |
| `critical_decision` | 最终风险决策 | 推理模型 (o3/Deep Think/R2) |

### 3.3 配置方式

通过YAML配置文件管理，不硬编码在代码中：

```yaml
# model_routing.yaml

# ===== 模型别名定义 =====
# 所有profile通过别名引用模型，新模型上线只需修改此处
model_aliases:
  # --- 轻量级 ---
  gemini_flash: "gemini/gemini-3-flash"
  qwen_turbo: "dashscope/qwen3-turbo"
  gpt_mini: "openrouter/openai/gpt-4.5-mini"
  haiku: "openrouter/anthropic/claude-haiku-4"
  deepseek_v3: "openrouter/deepseek/deepseek-v3.2"
  # --- 标准级 ---
  gemini_pro: "gemini/gemini-3-pro"
  qwen_max: "dashscope/qwen3-max"
  gpt_std: "openrouter/openai/gpt-4.5"
  sonnet: "openrouter/anthropic/claude-sonnet-4"
  # --- 旗舰/推理 ---
  gemini_top: "gemini/gemini-3.1-pro"
  gemini_think: "gemini/gemini-3-deep-think"
  qwen_plus: "dashscope/qwen3.5-plus"
  gpt_reasoning: "openrouter/openai/o4-mini"
  gpt_top: "openrouter/openai/o3"
  opus: "openrouter/anthropic/claude-opus-4.5"
  deepseek_r2: "openrouter/deepseek/deepseek-r2-pro"

# ===== 角色-模型映射 Profiles =====
profiles:
  cost_saving:  # 省钱模式 (优先免费额度)
    data_analyst: "${gemini_flash}"
    researcher: "${qwen_turbo}"
    expert: "${gemini_pro}"
    judge: "${qwen_max}"
    critical_decision: "${gpt_reasoning}"
    fallback_chain: ["${deepseek_v3}", "${qwen_turbo}"]

  balanced:  # 平衡模式
    data_analyst: "${gemini_flash}"
    researcher: "${sonnet}"
    expert: "${gemini_pro}"
    judge: "${gpt_std}"
    critical_decision: "${gpt_reasoning}"
    fallback_chain: ["${qwen_max}", "${gemini_pro}"]

  best_quality:  # 最佳质量模式
    data_analyst: "${gpt_std}"
    researcher: "${opus}"
    expert: "${gemini_top}"
    judge: "${gpt_top}"
    critical_decision: "${gpt_top}"
    fallback_chain: ["${opus}", "${gemini_think}"]

active_profile: "balanced"
```

### 3.4 模型生命周期管理

模型迭代速度极快（每1-2个月有新模型发布），需要一套机制确保系统持续使用最优模型：

```mermaid
flowchart TD
    subgraph AutoSync["自动感知 (LiteLLM内置)"]
        LiteLLM["LiteLLM Auto-Sync\n自动从Provider同步新模型定义"]
    end

    subgraph AliasLayer["别名隔离层 (model_routing.yaml)"]
        Alias["model_aliases 集中定义\n所有profile通过别名引用"]
        Profiles["profiles 不直接写模型名\n只引用 ${alias}"]
        Alias --> Profiles
    end

    subgraph UpdateFlow["模型更新流程"]
        direction TB
        NewModel["新模型发布\n(如 Gemini 4, GPT-6, Qwen4)"] 
        Step1["1. LiteLLM自动识别新模型"]
        Step2["2. 在YAML中新增/修改alias"]
        Step3["3. 热加载配置 (无需重启)"]
        Step4["4. Langfuse对比新旧模型效果"]
        NewModel --> Step1 --> Step2 --> Step3 --> Step4
    end

    subgraph Safeguard["安全保障"]
        Fallback["fallback_chain: 主模型不可用时\n自动降级到备用模型"]
        Deprecation["模型废弃预警:\n监控Provider deprecation通知"]
    end

    AutoSync --> AliasLayer
    AliasLayer --> UpdateFlow
    UpdateFlow --> Safeguard

    style AutoSync fill:#e3f2fd,stroke:#1565c0
    style AliasLayer fill:#e8f5e9,stroke:#388e3c
    style UpdateFlow fill:#fff3e0,stroke:#e65100
    style Safeguard fill:#fce4ec,stroke:#c62828
```

**核心设计**: 三层解耦

| 层 | 职责 | 新模型时需要做什么 |
|----|------|-------------------|
| **LiteLLM层** | 与Provider API通信 | 无需操作，自动同步 |
| **别名层** (model_aliases) | 将模型名映射为语义化别名 | 修改1行YAML |
| **Profile层** (profiles) | 角色到别名的映射 | 通常无需修改 |

**更新模型只需改一处**: 例如 Gemini 4 发布后，只需将 `gemini_pro: "gemini/gemini-3-pro"` 改为 `gemini_pro: "gemini/gemini-4-pro"`，所有引用该别名的profile自动生效。

**LiteLLM 热加载**: 支持通过 API 调用 `/model/update` 动态更新模型配置，无需重启服务。

### 3.4 LLM网关架构

```mermaid
flowchart TD
    Agent["Agent节点"] -->|role_type| Config["model_routing.yaml\n别名解析"]
    Config -->|实际model_name| Gateway["LiteLLM Gateway\n统一 OpenAI 兼容 API\nlocalhost:4000"]

    Gateway -->|路由策略| Strategy{"按Profile映射\n自动fallback\n速率限制\n成本追踪\n热加载配置"}

    Strategy --> G["Google Pro\nGemini 3 Flash/Pro/3.1 Pro\nGemini 3 Deep Think"]
    Strategy --> B["百炼\nQwen3-Turbo/Max\nQwen3.5-Plus"]
    Strategy --> O["OpenRouter\nGPT-4.5/o3/o4-mini\nClaude Sonnet 4/Opus 4.5\nDeepSeek-V3.2/R2"]
    Strategy --> L["Ollama\nLlama 4 (本地)\n离线可用"]

    style Gateway fill:#e3f2fd,stroke:#1565c0
    style Strategy fill:#fff8e1,stroke:#f9a825
```

---

## 四、可扩展专家智能体框架

### 4.1 设计原则

- **注册机制**: 专家以插件形式注册到系统，新增专家无需修改核心代码
- **动态选择**: 根据股票特征（行业、市值、波动率等）自动选择最适合的专家组合
- **可配置数量**: 每次分析可选择2-5个专家，而非固定组合
- **统一接口**: 所有专家遵循相同的输入输出协议

### 4.2 专家注册与发现架构

```mermaid
flowchart TD
    subgraph Registry["Expert Agent Registry"]
        direction TB
        Profile["ExpertProfile (注册信息)\nname | philosophy | style\nbest_for: sectors, market_cap, volatility\nprompt_template | role_type"]

        subgraph Experts["已注册专家池"]
            Graham["Ben Graham\n深度价值, 烟蒂股"]
            Buffett["Warren Buffett\n护城河, 长期持有"]
            Munger["Charlie Munger\n多元思维, 逆向检验"]
            Lynch["Peter Lynch\n成长价值, PEG"]
            Livermore["Jesse Livermore\n趋势投机, 关键点"]
            Greenblatt["Joel Greenblatt\n魔法公式, 量化"]
            Marks["Howard Marks\n周期投资, 风险意识"]
            Dalio["Ray Dalio\n全天候, 宏观对冲"]
            Custom["... 自定义专家\n用户可注册新专家"]
        end
    end

    subgraph Selector["Expert Selector (动态选择器)"]
        Input["输入:\n股票特征 (行业/市值/波动率/PE)\n市场环境 (牛/熊/震荡)\n用户偏好 (可选)"]
        Strategy2["选择策略:\n特征匹配 best_for\n多样性保障\n数量控制 2~5个\n用户覆盖"]
        Output2["输出: 选定的专家Agent列表"]
        Input --> Strategy2 --> Output2
    end

    Registry --> Selector

    style Registry fill:#e8f5e9,stroke:#388e3c
    style Selector fill:#e3f2fd,stroke:#1565c0
    style Profile fill:#fff8e1,stroke:#f9a825
```

### 4.3 动态选择示例

| 场景 | 股票 | 自动选择的专家 | 理由 |
|------|------|----------------|------|
| 大盘蓝筹 | AAPL | Buffett, Munger, Lynch | 护城河+多元思维+成长 |
| 周期股 | CAT | Marks, Greenblatt, Graham | 周期意识+量化+安全边际 |
| 高波动成长 | TSLA | Livermore, Lynch, Dalio | 趋势+成长+宏观 |
| 低估值小盘 | XYZ | Graham, Greenblatt, Lynch | 深度价值+魔法公式+挖掘 |
| 用户指定 | 任意 | 用户选择 | 完全自定义 |

### 4.4 专家统一接口协议

每个专家Agent遵循统一的输入/输出协议:

**输入**:
- 4份分析师报告（技术/情绪/新闻/基本面）
- 股票基础数据（价格、估值指标、财务数据）
- 历史记忆（该专家过去对类似情况的分析）

**输出** (结构化JSON):
- `recommendation`: BUY / SELL / HOLD
- `confidence`: 0.0 ~ 1.0
- `time_horizon`: short_term / medium_term / long_term
- `key_reasoning`: 核心论据（3-5条）
- `risks`: 主要风险点
- `position_suggestion`: 仓位建议百分比

---

## 五、增强辩论机制

### 5.1 当前 vs 升级

```mermaid
flowchart LR
    subgraph Current["当前辩论流程"]
        direction TB
        CB[Bull] -->|Round 1| CBear[Bear]
        CBear -->|"固定 max_rounds=1\n2轮后直接判决"| CRM[Research Manager\n直接裁决]
    end

    subgraph Upgraded["升级后辩论流程"]
        direction TB
        UB[Bull] <-->|"Round N..."| UBear[Bear]
        UBear --> Check{"收敛检测"}
        Check -->|"语义收敛度 > 阈值\nOR 信息增益 < 阈值\nOR 达到最大轮次"| Stop["提前停止"]
        Check -->|"未收敛"| UB
        Stop --> URM["Research Manager\n裁决 + 收敛质量评估"]
    end

    style Current fill:#fff3e0,stroke:#e65100
    style Upgraded fill:#e8f5e9,stroke:#2e7d32
    style Check fill:#fff8e1,stroke:#f9a825
```

### 5.2 辩论质量指标

| 指标 | 描述 | 用途 |
|------|------|------|
| **语义收敛度** | 连续轮次观点embedding的余弦相似度 | 判断是否继续辩论 |
| **信息增益** | 新轮次引入的新论据/数据占比 | 判断辩论是否有效 |
| **极化程度** | Bull和Bear信号分数的差距 | 检测是否陷入极端 |
| **引用密度** | 引用原始数据的频率 | 评估论证质量 |

---

## 六、数据源升级

### 6.1 数据源架构

```mermaid
flowchart TD
    subgraph Interface["DataInterface (统一接口层)"]
        direction LR
        API1["get_price_data(ticker, period)"]
        API2["get_financials(ticker)"]
        API3["get_valuation_metrics(ticker) ← 新增"]
        API4["get_earnings_calendar(ticker) ← 新增"]
        API5["get_macro_indicators() ← 新增"]
        API6["get_institutional_holdings(ticker) ← 新增"]
        API7["get_news(ticker, source)"]
    end

    Interface --> FreeLayer & PaidLayer

    subgraph FreeLayer["免费层 (默认)"]
        YF["Yahoo Finance\n价格/财务/估值/财报日期/机构持仓"]
        FRED["FRED\nCPI/GDP/利率/失业率/M2"]
        Finnhub["Finnhub\n新闻/基本面"]
        Reddit["Reddit\n社交情绪"]
    end

    subgraph PaidLayer["付费层 (可选)"]
        Longport["长桥 Longport API\n实时行情/K线/港美A股/程序化交易"]
    end

    style Interface fill:#e3f2fd,stroke:#1565c0
    style FreeLayer fill:#e8f5e9,stroke:#388e3c
    style PaidLayer fill:#fff3e0,stroke:#e65100
```

### 6.2 新增数据能力

| 能力 | 数据源 | 用途 |
|------|--------|------|
| **财报日历** | Yahoo Finance earnings_dates | 财报跟踪Agent |
| **估值指标** | Yahoo Finance info (P/E, P/B, EV/EBITDA) | 价值投资分析 |
| **机构持仓** | Yahoo Finance institutional_holders | 资金流向判断 |
| **宏观经济** | FRED API (CPI, GDP, 利率曲线) | 宏观环境判断 |
| **实时行情** | 长桥 QuoteContext | 盘中交易信号 |

---

## 七、价值投资框架

### 7.1 价值投资分析流程图

```mermaid
flowchart TD
    S1["① 定量筛选"] --> S2["② 定性分析"]
    S2 --> S3["③ 内在价值估算"]
    S3 --> S4["④ 专家投票"]
    S4 --> S5["⑤ 综合决策"]

    S1 -.- S1D["P/E, P/B, EV/EBITDA → 相对估值\nROE, ROIC, 毛利率 → 质量评估\n收入/EPS/FCF增长率 → 成长评估\n债务/权益, 流动比率 → 安全评估"]
    S2 -.- S2D["护城河: 品牌/网络效应/转换成本/成本优势\n管理层: 诚信/能力/股权激励一致性\n行业: 竞争格局/进入壁垒/周期性"]
    S3 -.- S3D["DCF模型 (保守/基准/乐观)\n行业对标估值\n安全边际 = (内在价值 - 当前价格) / 内在价值"]
    S4 -.- S4D["动态选择的专家Agent\n各专家基于自身哲学给出独立评估"]
    S5 -.- S5D["Research Manager\n综合定量+定性+专家意见 → 最终建议"]

    style S1 fill:#e3f2fd,stroke:#1565c0
    style S2 fill:#e8f5e9,stroke:#388e3c
    style S3 fill:#fff3e0,stroke:#e65100
    style S4 fill:#f3e5f5,stroke:#7b1fa2
    style S5 fill:#fce4ec,stroke:#c62828
    style S1D fill:#f5f5f5,stroke:#bbb
    style S2D fill:#f5f5f5,stroke:#bbb
    style S3D fill:#f5f5f5,stroke:#bbb
    style S4D fill:#f5f5f5,stroke:#bbb
    style S5D fill:#f5f5f5,stroke:#bbb
```

### 7.2 财报跟踪功能

**目标**: 自动监控持仓和关注列表的财报发布时间，在财报前自动触发深度分析

```mermaid
flowchart TD
    DailyCheck["每日定时检查"] --> HasEarnings{"未来14天内有财报?"}
    HasEarnings -->|NO| Skip["跳过"]
    HasEarnings -->|YES| PreAnalysis["触发财报前分析"]

    PreAnalysis --> Surprise["历史财报惊喜率"]
    PreAnalysis --> Guidance["近期指引变化"]
    PreAnalysis --> Industry["行业趋势对比"]
    PreAnalysis --> Alert["生成预警报告"]

    Alert --> EarningsRelease["财报发布后"]
    EarningsRelease --> Compare["实际 vs 预期对比"]
    EarningsRelease --> Update["更新持仓建议"]
    EarningsRelease --> Reflect["反思记忆更新"]

    style HasEarnings fill:#fff8e1,stroke:#f9a825
    style PreAnalysis fill:#e3f2fd,stroke:#1565c0
    style EarningsRelease fill:#e8f5e9,stroke:#388e3c
```

---

## 八、Deep Research集成

### 8.1 Deep Research在交易流程中的位置

```mermaid
flowchart LR
    subgraph Normal["普通分析模式"]
        direction TB
        DS1["数据源"] --> A1["4个Analyst"] --> Debate1["直接进入辩论"]
    end

    subgraph Deep["Deep Research模式"]
        direction TB
        DS2["数据源"] --> A2["4个Analyst"] --> DR["Deep Research Agent"]
        DR --> WebSearch["多轮Web搜索"]
        DR --> DocAnalysis["文档/报告分析"]
        DR --> Competitor["竞争对手对比"]
        DR --> Supply["产业链分析"]
        DR --> Report["生成深度研究报告"]
        Report --> Debate2["补充到辩论上下文"]
    end

    style Normal fill:#fff3e0,stroke:#e65100
    style Deep fill:#e8f5e9,stroke:#2e7d32
    style DR fill:#e3f2fd,stroke:#1565c0
```

**参考实现**: `langchain-ai/open_deep_research` (LangGraph原生)

**触发条件**:
- 用户手动请求深度研究
- 首次分析某只新股票
- 财报前深度调研
- 持仓出现重大波动

---

## 九、持仓管理与数据库

### 9.1 数据库架构

```mermaid
erDiagram
    positions {
        string ticker PK
        float quantity
        float avg_cost
        float current_price
        float unrealized_pnl
        datetime updated_at
    }

    trades {
        int id PK
        string ticker
        string action
        float quantity
        float price
        float commission
        float realized_pnl
        int decision_id FK
        datetime created_at
    }

    agent_decisions {
        int id PK
        string ticker
        date trade_date
        string final_decision
        float confidence
        text market_report
        text sentiment_report
        text news_report
        text debate_history
        text risk_assessment
    }

    daily_nav {
        date date PK
        float total_value
        float cash
        float positions_value
        float daily_return
        float cumulative_return
    }

    positions ||--o{ trades : "持仓产生交易"
    agent_decisions ||--o{ trades : "决策触发交易"
```

### 9.2 渐进式升级路径

```mermaid
flowchart LR
    P1["阶段1: CLI + SQLite\n(零依赖)"] --> P2["阶段2: Streamlit Dashboard\n(Python原生Web)"] --> P3["阶段3: FastAPI + React\n(专业级Web)"]

    style P1 fill:#e8f5e9,stroke:#388e3c
    style P2 fill:#e3f2fd,stroke:#1565c0
    style P3 fill:#f3e5f5,stroke:#7b1fa2
```

---

## 十、可观测性方案

### 10.1 Langfuse集成架构

```mermaid
flowchart LR
    subgraph App["TradingAgents"]
        direction TB
        LG["LangGraph"]
        Analyst["Analyst节点"]
        Research["Research节点"]
        Expert["Expert节点"]
        Risk["Risk节点"]
        CB["CallbackHandler()\n自动注入到所有节点"]
    end

    subgraph LF["Langfuse (自托管)"]
        direction TB
        subgraph Traces["Traces"]
            T1["输入/输出/延迟/Token数"]
            T2["模型名称/成本"]
            T3["错误日志"]
        end
        subgraph PM["Prompt Management"]
            P1["版本控制"]
            P2["A/B测试"]
            P3["性能对比"]
        end
        subgraph Dashboard["Dashboard"]
            D1["成本趋势"]
            D2["Token消耗分布"]
            D3["决策质量评分"]
        end
    end

    Analyst -->|trace| Traces
    Research -->|trace| Traces
    Expert -->|trace| Traces
    Risk -->|trace| Traces

    style App fill:#e3f2fd,stroke:#1565c0
    style LF fill:#e8f5e9,stroke:#388e3c
    style Traces fill:#fff8e1,stroke:#f9a825
    style PM fill:#f3e5f5,stroke:#7b1fa2
    style Dashboard fill:#fce4ec,stroke:#c62828
```

---

## 十一、开源项目复用清单

| 需求 | 推荐项目 | 复用方式 |
|------|----------|----------|
| 投资大师Agent Prompt | virattt/ai-hedge-fund | 复用Prompt设计，扩展为注册式框架 |
| Deep Research | langchain-ai/open_deep_research | 集成为子模块 |
| 持仓管理Schema | evancole99/investment_tracker | 参考数据库设计 |
| LLM网关 | litellm | 直接使用，配置多平台路由 |
| 可观测性 | langfuse (自托管) | Docker部署，集成Callback |
| 技术指标扩展 | bukosabino/ta | 扩充当前stockstats |

---

## 十二、实施路线图

### 阶段0: 环境准备
- [ ] 升级LangGraph到1.0
- [ ] 部署LiteLLM网关 + 配置多平台密钥
- [ ] 部署Langfuse自托管实例
- [ ] 设置SQLite数据库

### 阶段1: 核心架构升级
- [ ] LangGraph 1.0 Checkpointing集成
- [ ] Langfuse追踪回调接入
- [ ] LiteLLM分层模型配置（YAML配置化）
- [ ] 持仓管理数据库实现
- [ ] 重构 `trading_graph.py` 支持模型路由

### 阶段2: 数据源升级
- [ ] Yahoo Finance增强（财报日期、估值指标、机构持仓）
- [ ] 长桥Longport API集成
- [ ] FRED宏观经济数据接入

### 阶段3: Agent升级
- [ ] 可扩展专家框架（注册机制 + 动态选择器）
- [ ] 首批专家Agent: Buffett, Munger, Lynch, Livermore, Graham
- [ ] 动态收敛辩论机制
- [ ] Deep Research集成（基于open_deep_research）
- [ ] 财报跟踪Agent

### 阶段4: 价值投资框架
- [ ] DCF估值模型
- [ ] 护城河评估模块
- [ ] 安全边际计算
- [ ] 价值投资决策流程集成

### 阶段5: 优化与测试
- [ ] Token成本优化验证
- [ ] 回测框架
- [ ] 端到端测试
- [ ] Streamlit Dashboard（可选）

---

## 关键改造文件

| 文件 | 改造内容 | 优先级 |
|------|----------|--------|
| `tradingagents/graph/trading_graph.py` | LangGraph 1.0升级、Checkpointing、LiteLLM | P0 |
| `tradingagents/graph/setup.py` | 模型路由配置、新Agent节点、并行执行 | P0 |
| `tradingagents/default_config.py` | LiteLLM/Langfuse配置项、模型profile | P0 |
| `tradingagents/graph/conditional_logic.py` | 动态收敛辩论逻辑 | P1 |
| `tradingagents/dataflows/interface.py` | 长桥/FRED/YFinance增强 | P1 |
| `tradingagents/agents/utils/memory.py` | 分层记忆架构 | P1 |
| 新增 `tradingagents/experts/` | 专家注册框架 + 专家Agent定义 | P1 |
| 新增 `tradingagents/database/` | SQLite Schema和ORM | P1 |
| 新增 `tradingagents/research/` | Deep Research模块 | P2 |
| 新增 `tradingagents/valuation/` | 价值投资指标计算 | P2 |
| 新增 `model_routing.yaml` | 分层模型配置 | P0 |

---

## 验证方案

- **LLM网关**: 验证各平台模型通过LiteLLM正常响应
- **数据库**: 验证SQLite Schema创建和CRUD操作
- **数据源**: 验证YFinance增强数据和长桥API连通性
- **专家框架**: 验证专家注册、发现、动态选择流程
- **辩论机制**: 验证收敛检测在不同场景下的表现
- **端到端**: 对AAPL执行完整分析流程，检查各环节输出
- **成本追踪**: 在Langfuse中验证Token消耗统计

---

## 成本预算（月度）

| 项目 | 预估成本 | 备注 |
|------|----------|------|
| LLM API（分层优化） | $20-50 | Gemini免费额度 + 百炼 + OpenRouter |
| 长桥行情 | 免费~$99 | Level 1免费 |
| Langfuse | 免费 | 自托管 |
| **总计** | **$20-150/月** | 省钱模式约$20，平衡模式约$50 |
