# Finance Agent Skills and Project Scope

## Overview

This project is a modular financial intelligence and monitoring system designed to transform raw news, market signals, and macroeconomic events into a structured, analyst-friendly report. Its purpose is to help a user understand how global developments are affecting markets, sectors, currencies, and economic conditions.

The current system combines:
- regional news collection
- live market data validation
- macroeconomic event tracking
- sentiment and narrative scoring
- correlation and sector analysis
- risk and watchlist evaluation
- ChromaDB storage/retrieval helpers (the retrieval path is legacy-only and not wired into the current orchestrator)
- dual-model LLM routing across fast and deep analysis tasks
- orchestration across specialized agents
- HTML/JSON report generation
- scheduled automated execution

## Primary objective

The agent focuses on the question: "What is happening in the markets, and how does it line up with the news and with actual market behavior?"

Instead of relying on headlines alone, the workflow validates narrative stories against measured market moves, yield changes, FX rates, major indices, and macro events.

## Supported scope

### Regions of focus
- United States
- European Union
- Japan
- China
- Nordic region
- Denmark
- Sweden

### Asset classes tracked
- equities/stocks
- bonds and fixed income
- FX and currencies
- crypto
- funds/ETF-style flow narratives
- bullion and precious metals
- volatility and market stress indicators

### Analysis types
- sentiment analysis for news coverage
- region and asset classification
- macroeconomic impact analysis
- microeconomic and sector impact analysis
- cross-asset correlation assessment
- watchlist and risk prioritization
- pending signal recording through the active backtest agent
- historical memory retrieval in the legacy entry point

## Project workflow

The application follows a clear pipeline:

1. fetch recent financial news across configured regions
2. classify articles by geography and asset theme
3. retrieve live market data from Yahoo Finance and related sources
4. collect relevant economic calendar events
5. normalize and enrich data for downstream agents
6. route tasks through a fast or deep model based on complexity
7. analyze cross-asset relationships, macro risk, and sector effects
8. process pending predictions through the active backtest agent
9. produce a structured JSON payload and polished HTML output summarizing all findings

Historical context retrieval is available in `vector_db.py` and used by `legacy main.py`, but it is not called by the current `Orchestrator.run()` flow.

## Core architecture and modules

### `main.py`
The runtime entry point. It creates the orchestrator and triggers the full analysis run.

### `orchestrator.py`
The coordination hub for the whole application. It:
- initializes shared infrastructure
- runs phase-based data acquisition
- dispatches specialized agents
- aggregates results into a common analysis payload
- exports JSON and HTML reports

### `model_router.py`
A local AI routing layer that:
- selects the fast model for low-latency tasks
- selects the deep model for higher-complexity analysis
- wraps Ollama calls
- extracts structured JSON responses from LLM output

### `vector_db.py`
The ChromaDB layer. Its helpers can store embeddings and metadata for:
- news articles
- sentiment snapshots
- market snapshots
- analysis outputs
- backtest results

### `config.py`
Defines project-wide configuration:
- region metadata
- asset class keywords
- sector mappings
- environment variables
- model and API settings

### `news_fetcher.py` and `agents/news_agent.py`
Collect and normalize financial news by region and category.

### `market_data.py` and `agents/market_agent.py`
Fetch and summarize live market indicators such as indices, rates, FX, metals, and crypto.

### `economic_calendar.py` and `agents/calendar_agent.py`
Load relevant upcoming events and macroeconomic announcements.

### `agents/sentiment_agent.py`
Converts article coverage into sentiment scores and trend summaries.

### `agents/correlation_agent.py`
Measures how different asset classes and market narratives relate to each other.

### `agents/macro_agent.py` and `agents/micro_agent.py`
Assess impact at macroeconomic and company/sector levels.

### `agents/sector_agent.py`
Calculates sector performance and headline sentiment for configured US and Sweden sectors. It does not currently provide sector coverage for all seven news regions.

### `agents/risk_agent.py` and `agents/enhanced_watchlist_agent.py`
Evaluate risk posture, uncertainty, and prioritization logic.

### `agents/backtest_agent.py`
Stores pending overall-market UP/DOWN predictions in `data/reports/backtest_history.json`. The active path does not supply `actual_move`, fetch ground truth, or evaluate on a time horizon. The separate legacy `backtester.py` has a Yahoo Finance 24-hour check for S&P 500, gold, and bitcoin, but is not called by the orchestrator.

### `html_report_generator.py`
Builds the final HTML dashboard and narrative report.

### `app.py`
Provides the Streamlit-based dashboard for exploring the generated output.

## RAG and dual-model design

### Vector storage and retrieval
`vector_db.py` provides ChromaDB collections, embedding, storage, and retrieval helpers. The legacy `legacy main.py` stores data and calls `get_historical_context`, which retrieves up to three similar news records over a 30-day window and may include 14-day sentiment history. The current orchestrator initializes the vector DB but does not call its store/retrieval methods or inject historical context into prompts. Do not describe the active orchestration path as RAG-backed until it is wired in.

### Dual-model strategy
The system is intentionally designed with two model layers:
- a fast model for routing, classification, and lightweight analysis
- a deeper model for macro reasoning, correlation analysis, and narrative synthesis

This reduces latency for repetitive tasks while preserving stronger reasoning for complex market interpretation.

### Orchestration layer
The orchestration layer controls the sequence of operations, making sure:
- data is fetched before analysis
- required agent inputs are passed through the current in-process flow
- tasks are routed to the right model
- all outputs are aggregated into a final report

## Data and output conventions

The project stores persistent outputs under `data/`:
- `news_cache/` for fetched news snapshots
- `market_cache/` for market data snapshots
- `calendar_cache/` for macro event snapshots
- `sentiment_history/` for historical sentiment tracking
- `reports/` for HTML and JSON outputs
- `vector_db/` for persistent vector memory

These caches support reproducibility, debugging, historical retrieval, and scheduled analysis.

## Operational notes

- The app is designed to work with a local Ollama host by default. `config.py` loads `.env` values with `python-dotenv` and defines `OLLAMA_HOST` as `http://localhost:11434` by default, but the active router does not explicitly pass that config value to its module-level Ollama API calls; the vector DB embedding endpoint is also hard-coded to localhost.
- `OLLAMA_MODEL`, `OLLAMA_FAST_MODEL`, and `OLLAMA_DEEP_MODEL` are read, but hard-coded fast/deep model pins currently override the model environment settings.
- Optional API keys can be added for expanded data sources.
- The project is built for repeated monitoring and report generation rather than direct automated trading.
- The architecture is local-first and modular; it does not require a formal MCP protocol to function.

## Recommended usage

- Run `python main.py` for a single full analysis cycle.
- Run `python scheduler.py` for automated repeated monitoring.
- Run `streamlit run app.py` to open the interactive dashboard.
- Open generated HTML reports in a browser for review.

## Extension considerations

This is a strong foundation for future enhancement in areas such as:
- investor sentiment scoring calibration
- deeper narrative summarization
- risk-factor detection
- event-driven alerts
- stronger sector-level drilldown
- export to PDF, CSV, or dashboard integrations
- MCP-style tool exposure for external systems

## Summary

This project functions as a research and market monitoring system that turns financial news, macro events, and market data into a structured intelligence report. It is best understood as a local-first, multi-agent market context and analysis pipeline rather than a pure data scraper or trading bot. The design combines retrieval memory, model specialization, and orchestration to support both efficient routing and deeper reasoning in a single financial intelligence workflow.