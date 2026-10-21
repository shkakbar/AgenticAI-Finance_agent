# Finance Agent

Finance Agent is a modular market intelligence system that combines live market data, regional news ingestion, macroeconomic event tracking, and multiple AI analysis agents to generate investor-facing research reports. The system is built to validate narrative news flow against observable market behavior and package the results into HTML and JSON outputs for both human review and downstream tooling.

## System summary

The application follows a multi-agent orchestration pattern:

- data acquisition agents fetch market, news, and calendar inputs
- a shared model router manages local Ollama LLM calls
- a ChromaDB vector store provides persistence and retrieval helpers; the current orchestrator does not invoke its retrieval path
- specialized agents analyze sentiment, macro, micro, sector, correlation, and risk drivers
- the orchestrator consolidates outputs and exports a final HTML/JSON report

This makes the system extensible without coupling each analysis component to the underlying data sources.

## High-level system flow

```text
main.py
  -> Orchestrator.run()
     -> Phase 1: fetch news, market, calendar data
     -> NewsTagger reclassifies unmatched headlines
     -> Phase 2: run AI analysis agents
        - SentimentAgent
        - MacroAgent
        - MicroAgent
        - CorrelationAgent
        - SectorAgent
        - RiskAgent
        - EnhancedWatchlistAgent
     -> Phase 3: BacktestAgent records pending predictions (no active ground-truth evaluation)
     -> Phase 4: save JSON + HTML report
     -> output in data/reports/
```

## Core architecture

### 1. Entry and orchestration layer
- `main.py` starts the workflow using `Orchestrator`.
- `orchestrator.py` is the coordination layer that controls execution phases and aggregates agent outputs.
- `BaseAgent` provides common logging and safe execution patterns for all specialized agents.

### 2. Infrastructure layer
- `config.py` centralizes environment variables, regional focus definitions, asset classes, and market ticker metadata.
- `model_router.py` selects the correct Ollama model (fast/deep), wraps chat calls, and extracts structured JSON responses.
- `vector_db.py` defines ChromaDB collections and retrieval helpers for news, sentiment, market, analysis, and backtest history. Historical retrieval is used by the legacy entry point, not the current `Orchestrator.run()` path.

### 3. Data source layer
- `news_fetcher.py` and `agents/news_agent.py` gather articles and classify them by region and asset theme.
- `market_data.py` and `agents/market_agent.py` fetch live price and performance data from Yahoo Finance and market watchers.
- `economic_calendar.py` and `agents/calendar_agent.py` collect upcoming macroeconomic events.

### 4. Intelligence layer
- `agents/sentiment_agent.py` scores the overall tone of the market narrative.
- `agents/macro_agent.py` and `agents/micro_agent.py` evaluate broad macro themes and asset-level effects.
- `agents/correlation_agent.py` identifies cross-asset relationships.
- `agents/sector_agent.py` computes sector data and headline sentiment for the US and Sweden only; it does not currently cover all configured news regions.
- `agents/risk_agent.py` and `agents/enhanced_watchlist_agent.py` focus on risk and watchlist prioritization.
- `agents/backtest_agent.py` records pending overall-market direction signals. The active agent does not fetch ground truth or evaluate a time horizon; the separate `backtester.py` implements a legacy 24-hour check.
- `agents/fundamentals_agent.py` exists in the repo but is effectively retired in the current orchestration path; the active watchlist layer is `EnhancedWatchlistAgent`.

### 5. Output layer
- `html_report_generator.py` creates readable HTML reports.
- `app.py` hosts a Streamlit dashboard for interactive analysis review.
- `data/reports/` is the canonical runtime output folder for timestamped and latest JSON/HTML artifacts.
- the top-level `reports/` directory is a convenience folder for generated reports or manual review artifacts and is not the primary run output path.

## Implementation notes and current behavior

### Retrieval timing and ownership
The repository contains RAG-capable helpers in `vector_db.py`, but they are not wired into the current `Orchestrator.run()` execution path. In the legacy entry point, `get_historical_context(..., days_back=30)` combines up to three similar news records (`find_similar_news(..., limit=3)`) with sentiment history from the previous 14 days. The general helper defaults to `limit=5`. The active orchestrator does not currently store fresh records in these collections or inject retrieved context into agent prompts.

### Facts gate enforcement
The facts gate is currently prompt-only. The orchestrator builds a `MARKET FACTS` block from selected market-data fields and passes it to some model prompts with the instruction: “Use ONLY these figures for any quantitative statements.” There is no downstream validation pass that rejects model output that cites numbers outside that block.

### JSON output handling
`ModelRouter` attempts structured parsing with a hierarchy of fallbacks: direct JSON parse, markdown-stripped parse, brace extraction, and final array/object slicing. That is a best-effort parser around the underlying Ollama output, not a strict schema-only gate. Structured validation is enforced only when the schema-based path is invoked; otherwise, the system falls back to tolerant extraction and retries.

### Model routing behavior
The intended two-model stack uses a fast model for lightweight tasks and a deep model for reasoning. Currently, `config.py` hard-codes `qwen2.5:7b-instruct` and `qwen2.5:32b-instruct`, overriding model names read from environment variables. If a configured model is absent, `ModelRouter` searches available names for the substring `14b` (deep) or `7b` (fast), then uses the first listed model if no match is found. This fallback does not filter embedding models, enforce distinct fast/deep choices, or record the resolved models in report metadata. The substring matching is not an exact parameter-count check (for example, `17b` contains `7b`). Resolved model names are printed at initialization; fallback logging is not consistent between roles.

### Execution model
The current orchestration is synchronous and phase-oriented. It does not use a task queue or async worker pool; the orchestrator runs through the phases in sequence while agents remain specialized and independent.

### Data sources and scheduler
- news: configured financial feeds and article ingestion code
- markets: Yahoo Finance plus market-data helpers for indices, FX, yields, crypto, and volatility
- calendar: economic event parser and macro event storage
- scheduler: `schedule` library, configured per market time block in `scheduler.py`, with a continuous loop on a 60-second polling interval

### Persistence and reporting split
The repository keeps both:
- `data/sentiment_history/` as a flat historical artifact for human-readable trend continuity
- the vector database collections as searchable, embedding-backed memory

These are complementary, not redundant: one is a file-based history layer and the other is a retrieval-oriented semantic memory layer.

These describe available storage components, not current orchestrator write behavior: the active pipeline persists its JSON/HTML reports, but it does not call the vector DB store/retrieval helpers.

### Top-level analysis payload keys
The live `analysis_data` object currently contains these top-level keys:
- `all_news`
- `news_by_region`
- `news_by_asset`
- `market_data`
- `performance_data`
- `economic_events`
- `watchlist_fundamentals`
- `sentiment_data`
- `macro_analysis`
- `micro_analysis`
- `risk_metrics`
- `correlation_matrix`
- `correlation_analysis`
- `enhanced_watchlist`
- `us_sector_data`
- `us_sector_sentiment`
- `sweden_sector_data`
- `sweden_sector_sentiment`
- `backtest_stats`
- `metadata`
- `vector_db_stats`

`watchlist_fundamentals` is currently initialized to an empty list in `Orchestrator.run()`. Neither `FundamentalsAgent` nor `EnhancedWatchlistAgent` populates this key; the latter returns its separate result under `enhanced_watchlist`.

Sector outputs are limited to `us_sector_*` and `sweden_sector_*` because `SectorAgent` explicitly invokes configured sector definitions for `US` and `Sweden`. The project’s wider region list applies to news and market monitoring; it does not imply sector coverage for every region.

### Backtest status
The active `BacktestAgent` writes `data/reports/backtest_history.json`. It adds a pending “Overall Market” UP/DOWN prediction when the overall sentiment label is not `Neutral`; its evaluator grades only records that already have an `actual_move`, and nothing in the active path supplies that value, fetches ground truth, or triggers evaluation after 24 hours. Consequently, current accuracy is normally zero until ground-truth values are supplied. No baseline is calculated.

A separate legacy `backtester.py` writes `data/backtest/predictions.json` and contains a Yahoo Finance price-based 24-hour grading path for S&P 500, gold, and bitcoin. Evaluation is checked when the legacy entry point invokes it on a later run; there is no separate timer/callback. It ignores scores in the neutral range (-19 through 19) and counts bullish scores of at least 20 as correct only for a positive move, and bearish scores of at most -20 as correct only for a negative move. This legacy path is not called by `Orchestrator.run()`. Its universe is three assets and it has no comparison baseline.

### Retrieval requirement status
The metadata filters and recency/relevance weighting described as desired behavior in `requirement.md` are not implemented in the active pipeline. The vector DB helper can apply a date cutoff and optional region filter for news similarity, and can read recent sentiment history; source/topic filters and explicit recency re-ranking are not present in that helper. Retrieval from sentiment, market, analysis, and backtest collections is not part of the current analysis path. The legacy caller is `legacy main.py`; it obtains historical context before analysis. The active orchestrator and agents do not make vector retrieval calls.

### Facts block scope and auditability
The active orchestrator builds a prompt string from selected market-data rows: major indices (`^GSPC`, `^IXIC`, `^DJI`, `^OMX`), Treasury yields (`^TNX`, `^IRX`), and selected FX tickers (`DX-Y.NYB`, `EURUSD=X`, `USDSEK=X`). It does not include derived `correlation_matrix` values or other computed analysis results. This string is passed to SentimentAgent, MacroAgent, MicroAgent, and CorrelationAgent. RiskAgent, SectorAgent, and EnhancedWatchlistAgent do not receive it through their orchestrator calls. The facts block is not stored as a separate `analysis_data` key; only the underlying market data and agent outputs are exported, so an exact prompt-level audit record is unavailable.

## Design principles

- Modular agent-based architecture: each agent owns a specific analysis responsibility.
- Shared data contracts: all agents work on a common structured analysis dictionary.
- Local-first deployment: the project defaults to Ollama-hosted models and local cache output.
- Prompt-only facts instruction: a selected market facts block is supplied to four analysis agents; no output validation enforces it.
- RAG-capable vector DB helpers: historical retrieval exists in the repository, but is not wired into the active orchestrator.
- Dual-model inference: low-cost routing/classification uses a fast model, while deeper reasoning uses a more capable model.
- Resilience by design: agents fail independently and logs continue the pipeline without crashing the whole workflow.
- Artifact-first reporting: final outputs are saved as JSON and HTML for repeatable review and historical comparison.

## RAG and dual-model summary

The repository includes a RAG-capable vector DB implementation using ChromaDB and Ollama embeddings:

- `vector_db.py` creates persistent collections for market, news, sentiment, and analysis content
- embeddings are generated from Ollama (`nomic-embed-text` by default)
- legacy entry-point code can retrieve past news and sentiment history and inject it into analysis prompts; this is not active in the current orchestrator
- this creates a local memory layer for financial context, without requiring a cloud vector service

The system has two intended model roles:

- `FAST_MODEL` handles quick classification, routing, and lightweight analysis
- `DEEP_MODEL` handles higher-complexity reasoning such as macro, correlation, and narrative synthesis
- `ModelRouter` selects a role based on the task type and applies fallback selection if the pinned model is unavailable; the fallback limitations above apply

This is not a full MCP implementation. The repo currently uses direct local model orchestration and in-process agent coordination, rather than an external MCP tool server protocol.

## Requirements and architecture references

- [requirement.md](requirement.md) — functional and non-functional requirements
- [architecture.md](architecture.md) — deep architecture and design document

## Current state vs future state

| Area | Current implementation | Future extension |
|------|------------------------|------------------|
| Model access | Local Ollama via `ModelRouter` | MCP-adapted tool access and external integration |
| Memory | ChromaDB helpers; retrieval is only called by the legacy entry point | Wire retrieval into active orchestration and add auditable context selection |
| Orchestration | Central `Orchestrator` with phase-based execution | MCP tool routing and multi-tool workflows |
| Agent design | Specialized internal agents | External tool-backed agent capabilities |
| Reporting | JSON + HTML + Streamlit dashboard | Same reporting layer with extended automation |

## Future architecture evolution

The current system is a local-first multi-agent platform with ChromaDB helper capabilities and dual-model orchestration. A natural future extension is to wire retrieval into the active orchestration path and add a formal MCP layer, exposing tools such as market data access, news retrieval, risk context, and calendar events behind a standard interface.

## Quick start

### Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Run once

```bash
python main.py
```

### Run the scheduler

```bash
python scheduler.py
```

### Launch dashboard

```bash
streamlit run app.py
```

## Output artifacts

The project writes:

- HTML reports in `data/reports/`
- JSON snapshots in `data/reports/`
- cached market, news, and calendar data under `data/`
- vector database state in `data/vector_db/`

## Notes

- The system is designed for research and monitoring rather than direct automated trading.
- Live data is sourced from Yahoo Finance and other external feeds, while the AI layer interprets the context.
- Chat LLM usage is local-first via Ollama, which keeps the workflow self-hosted and flexible.
- `config.py` loads `.env` values with `python-dotenv`; it defines `OLLAMA_HOST` with default `http://localhost:11434`. The active `ModelRouter` uses the module-level Ollama API rather than explicitly passing `config.OLLAMA_HOST`, and the vector DB embedding URL is hard-coded to localhost.
- Although `OLLAMA_MODEL`, `OLLAMA_FAST_MODEL`, and `OLLAMA_DEEP_MODEL` are read, hard-coded fast/deep model pins currently override the model environment settings.

## Project structure

```text
finance-agent/
├── main.py
├── orchestrator.py
├── app.py
├── config.py
├── model_router.py
├── vector_db.py
├── market_data.py
├── news_fetcher.py
├── economic_calendar.py
├── html_report_generator.py
├── scheduler.py
├── requirements.txt
├── README.md
├── requirement.md
├── architecture.md
├── agents/
│   ├── base_agent.py
│   ├── news_agent.py
│   ├── market_agent.py
│   ├── calendar_agent.py
│   ├── sentiment_agent.py
│   ├── macro_agent.py
│   ├── micro_agent.py
│   ├── correlation_agent.py
│   ├── sector_agent.py
│   ├── risk_agent.py
│   ├── enhanced_watchlist_agent.py
│   ├── backtest_agent.py
│   └── fundamentals_agent.py
├── data/
│   ├── cache/
│   ├── calendar_cache/
│   ├── market_cache/
│   ├── news_cache/
│   ├── reports/
│   ├── sentiment_history/
│   └── vector_db/
├── reports/
└── tests/
```
