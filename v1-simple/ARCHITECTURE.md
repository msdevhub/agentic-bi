# Agentic BI POC - 架构设计

## 设计原则
- **简洁优先**: 不引入 LangGraph/AutoGen 等重框架，纯 Python 实现 Agent 协作
- **最小可用**: 能展示 agent teamwork + skill 调用即可
- **技术栈**: Python (FastAPI) + React + DuckDB

## 系统架构

```
┌─────────────────────────────────────────────┐
│                 React Frontend               │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐ │
│  │ Chat UI  │  │ Result   │  │ Reasoning │ │
│  │          │  │ Table +  │  │ Chain     │ │
│  │          │  │ Chart    │  │ Viewer    │ │
│  └──────────┘  └──────────┘  └───────────┘ │
└──────────────────┬──────────────────────────┘
                   │ HTTP/SSE
┌──────────────────▼──────────────────────────┐
│              FastAPI Backend                  │
│                                              │
│  ┌─────────────────────────────────────────┐│
│  │           Agent Orchestrator             ││
│  │                                         ││
│  │  ┌──────────┐  ┌──────────┐  ┌───────┐ ││
│  │  │ Router   │→ │ Executor │→ │Reviewer│ ││
│  │  │ Agent    │  │ Agent    │  │ Agent  │ ││
│  │  └──────────┘  └──────────┘  └───────┘ ││
│  └─────────────────────────────────────────┘│
│                                              │
│  ┌──────────────┐  ┌────────────────┐       │
│  │ Skill Library│  │ DuckDB Engine  │       │
│  │ (YoY, TopN..)│  │ (SQL 执行)     │       │
│  └──────────────┘  └────────────────┘       │
│                                              │
│  ┌──────────────────────────────────┐       │
│  │ Knowledge Base (schema + terms)  │       │
│  └──────────────────────────────────┘       │
└─────────────────────────────────────────────┘
```

## Agent 设计（纯 Python class）

### Router Agent
- 输入: 用户自然语言问题
- 职责: 理解意图 → 选择技能 → 提取参数
- 输出: { skill_name, parameters, reasoning }

### Executor Agent
- 输入: Router 的输出
- 职责: 调用技能生成 SQL → DuckDB 执行 → 格式化结果
- 输出: { sql, data, columns, chart_suggestion }

### Reviewer Agent
- 输入: 用户问题 + Executor 的结果
- 职责: 检查结果合理性 → 生成自然语言摘要 → 推荐下一步
- 输出: { summary, is_valid, suggestions, corrections }

## 技能库（MVP 版本）

| 技能 | 描述 | 参数 |
|------|------|------|
| general_query | 通用 SQL 查询 | sql |
| year_over_year | 同比分析 | metric, date_col, dimensions |
| top_n | TopN 排名 | metric, dimension, n, order |
| trend | 趋势分析 | metric, date_col, granularity |

## 示例数据集
使用一个销售数据集（~5000行），包含:
- date, region, product_category, sales_amount, quantity, cost

## 文件结构

```
poc/v1-simple/
├── backend/
│   ├── main.py              # FastAPI 入口
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py          # BaseAgent 类
│   │   ├── router.py        # RouterAgent
│   │   ├── executor.py      # ExecutorAgent
│   │   └── reviewer.py      # ReviewerAgent
│   ├── skills/
│   │   ├── __init__.py
│   │   ├── registry.py      # 技能注册表
│   │   ├── general_query.py
│   │   ├── year_over_year.py
│   │   ├── top_n.py
│   │   └── trend.py
│   ├── db/
│   │   ├── __init__.py
│   │   ├── engine.py        # DuckDB 管理
│   │   └── sample_data.py   # 生成示例数据
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── ChatPanel.tsx
│   │   │   ├── ResultPanel.tsx
│   │   │   └── ReasoningChain.tsx
│   │   └── api.ts
│   ├── package.json
│   └── index.html
└── README.md
```

## LLM 调用
- 使用 OpenAI 兼容 API（可配置 endpoint）
- Router/Reviewer 各用一次 LLM 调用
- Executor 不用 LLM，直接用技能模板生成 SQL
