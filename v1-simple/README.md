# Agentic BI POC v1

企业级 Agentic BI 助手 POC — 多智能体协作 + 技能库 + DuckDB

## 架构

```
用户提问 → Router Agent (选技能) → Executor Agent (生成SQL+执行) → Reviewer Agent (审核+摘要)
```

## 快速启动

### 后端

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env  # 编辑填入你的 API Key
python -m uvicorn backend.main:app --reload --port 8000
```

> 也可以从上级目录运行: `cd .. && python -m uvicorn backend.main:app --reload --port 8000`

### 前端

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:5173

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| OPENAI_API_KEY | API 密钥 | - |
| OPENAI_BASE_URL | API 地址 | https://api.openai.com/v1 |
| MODEL_NAME | 模型名称 | gpt-4o |

## 技能列表

| 技能 | 说明 |
|------|------|
| general_query | 通用 SQL 查询 |
| year_over_year | 同比分析 |
| top_n | TopN 排名分析 |
| trend | 趋势分析 |

## 示例问题

- 各地区销售额排名
- 2024年月度销售趋势
- 电子产品的同比增长情况
- 销售额最高的5个产品类别
