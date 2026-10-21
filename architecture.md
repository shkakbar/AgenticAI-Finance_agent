# Architecture document

## 1. Overview

Finance Agent is a modular, multi-agent financial monitoring system. Its design separates responsibilities into data acquisition, AI analysis, persistence, orchestration, and reporting. This separation allows the platform to ingest multiple sources of market context, reason over them with local LLMs, and publish final intelligence in a consistent format.

## 2. Design goals

The architecture is designed to satisfy the following goals:

- collect diverse market intelligence from local and external data sources
- support consistent, repeatable analysis runs
- keep the model layer independent from the business logic
- allow multiple specialist agents to operate on the same shared context
- generate usable artifacts for both humans and downstream systems
- operate in a local deployment model using Ollama when possible

## 3. High-level architecture

```text
+---------------------+
| User / Operator     |
| - run main.py       |
| - schedule jobs     |
| - view dashboard    |
+----------+----------+
           |
           v
+---------------------+
| Entry Layer         |
| main.py             |
| scheduler.py        |
+----------+----------+
           |
           v
+---------------------+
| Orchestration Layer |
| Orchestrator        |
| - Phase 1 fetch     |
| - Phase 2 analysis  |
| - Phase 3 backtest  |
| - Phase 4 export    |
+----------+----------+
           |
           v
+---------------------+
| Agent Layer         |
| News, Market,       |
| Calendar, Sentiment, |
| Macro, Micro,       |
| Correlation, Sector, |
| Risk, Watchlist     |
+----------+----------+
           |                                       
           v                                       
+---------------------+      +-------------------------+
| Shared Infrastructure|      | Output & Visualization |
| ModelRouter         |      | HTMLReportGenerator     |
| FinanceVectorDB     |      | Streamlit Dashboard     |
| Config              |      | JSON + HTML artifacts   |
+---------------------+      +-------------------------+
```

## 4. Major components

### 4.1 Entry and control layer

`main.py` is the primary runtime entry point. It instantiates the `Orchestrator` and runs the full pipeline. `scheduler.py` enables repeatable execution for daily or periodic monitoring jobs.

The orchestrator is responsible for:
- initializing shared resources
- coordinating execution order
- collecting agent results into one payload
- saving final JSON and HTML outputs

### 4.2 Shared infrastructure layer

#### Config
`config.py` centralizes reusable metadata, including:
- region definitions and labels
- asset classes and ticker groups
- macro and market keywords
- environment-based model configuration
- optional API keys

This ensures consistent classification and contextual prompts across agents.

`config.py` calls `load_dotenv()` to load local `.env` settings. It defines `OLLAMA_HOST` with a default of `http://localhost:11434`; API keys including `NEWSAPI_KEY` and `FINNHUB_KEY` are read from the environment. `OLLAMA_MODEL`, `OLLAMA_FAST_MODEL`, and `OLLAMA_DEEP_MODEL` are also read, but hard-coded fast/deep model pins override the latter two. `OLLAMA_MODEL` is retained as a legacy setting and does not replace those pins. The active `ModelRouter` calls the module-level Ollama API rather than explicitly passing `config.OLLAMA_HOST`, and the embedding URL in `FinanceVectorDB` is hard-coded to localhost.

#### ModelRouter
`model_router.py` wraps local LLM access through Ollama. The main functions are:
- model selection for fast or deep tasks
- standard text generation
- structured JSON generation using the schema where available
- extraction of JSON from LLM output, including markdown and partial-response cases

The implementation is intentionally tolerant rather than brittle: it tries direct JSON parsing, strips markdown fences, extracts the first valid object/array, and only then validates against a schema if the caller uses the schema-based generation path. In other words, the architecture aims for robust parsing and retry behavior rather than a pure "fail on any non-schema output" rule.

`config.py` currently pins the fast and deep roles to `qwen2.5:7b-instruct` and `qwen2.5:32b-instruct`, overriding the values read from `OLLAMA_FAST_MODEL` and `OLLAMA_DEEP_MODEL`. If a pinned model is absent, `ModelRouter` calls `ollama.list()`, matches the substring `14b` for deep and `7b` for fast, then selects the first listed model if no match exists. This is substring matching rather than parameter-size parsing (`17b` also contains `7b`); embedding models are not excluded, and no distinct-model check prevents both roles resolving to the same model. A deep fallback is logged; the fast fallback is not separately logged. Both resolved names are printed at initialization but are not added to report metadata. If `ollama.list()` fails, the configured pinned names remain in use and generation errors are handled by the router.

#### FinanceVectorDB
`vector_db.py` implements persistent semantic storage using ChromaDB and Ollama embeddings. It stores:
- news articles
- sentiment snapshots
- market snapshots
- AI-generated analysis
- backtest results

The vector store has historical retrieval helpers and collection storage capabilities; these are not called by the active orchestrator.

### 4.3 Data acquisition layer

This layer is responsible for all raw inputs.

- `NewsAgent` collects article feeds and organizes them by region and asset class.
- `MarketAgent` obtains live market pricing and performance statistics.
- `CalendarAgent` gathers macro events and upcoming economic signals.

Each agent produces normalized dictionaries so the orchestrator can assemble a unified analysis payload.

### 4.4 Agent analysis layer

Each specialized agent maps to a narrow responsibility:

- `SentimentAgent`: overall tone and driver-based sentiment scoring
- `MacroAgent`: broad macro themes, rates, inflation, growth, policy context
- `MicroAgent`: company- or sector-specific impact signals
- `CorrelationAgent`: relationship and dependency analysis between assets
- `SectorAgent`: sector performance and headline sentiment for the US and Sweden
- `RiskAgent`: downside and uncertainty assessment
- `EnhancedWatchlistAgent`: prioritized watchlist and focus list logic
- `BacktestAgent`: records pending overall-market direction predictions; the active path does not obtain ground truth or evaluate them on a time horizon

The active `BacktestAgent` writes `data/reports/backtest_history.json`. It adds a pending “Overall Market” prediction when sentiment is non-neutral, but its evaluator only grades records that already have `actual_move` populated; the active path does not populate that field or fetch actual market data. No horizon or ground-truth source is connected to this agent, and its accuracy is normally zero at cold start and remains zero until actual moves are supplied. No baseline is calculated.

The separate legacy `backtester.py` writes `data/backtest/predictions.json` and implements a different check: when the legacy entry point invokes evaluation on a later run, it checks records at least 24 hours old and fetches current prices through Yahoo Finance for the S&P 500, gold, and bitcoin. There is no separate timer/callback. It excludes sentiment scores from -19 through 19; scores >=20 require a positive price move, and scores <=-20 require a negative move. This path is not invoked by `Orchestrator.run()` and should not be described as the active benchmark.

`FundamentalsAgent` is instantiated but its execution call is commented out. The orchestrator sets `watchlist_fundamentals` to an empty list. `EnhancedWatchlistAgent` independently produces `enhanced_watchlist`; it does not populate `watchlist_fundamentals`.

Although the configured project scope includes seven news regions, `SectorAgent.execute()` explicitly fetches sector definitions for only `US` and `Sweden`, producing `us_sector_*` and `sweden_sector_*` keys. Other configured regions do not currently have sector outputs.

The shared class `BaseAgent` defines common behavior for logging and safe execution so agents can fail independently without taking down the pipeline.

### 4.5 Output layer

The reporting pipeline writes:
- JSON to `data/reports/analysis_*.json`
- latest JSON pointer to `data/reports/latest_analysis.json`
- HTML report to `data/reports/report_*.html`
- latest HTML pointer to `data/reports/latest_report.html`

`html_report_generator.py` assembles a readable narrative, while `app.py` exposes the report in an interactive Streamlit dashboard. The repo also contains a top-level `reports/` directory, but the canonical runtime output is `data/reports/`; the top-level folder is better treated as a convenience or manual export area rather than the primary runtime artifact path.

### 4.6 Scheduling and runtime execution

The scheduler uses Python's `schedule` library in `scheduler.py`. It configures recurring run times by market and then enters a loop that checks pending jobs every 60 seconds. This is a polling-based scheduler rather than a cron daemon or APScheduler-based system.

### 4.7 Data source contract

The runtime depends on a small set of concrete data providers:
- news: feed/article ingestion layer, plus downstream regional classification
- markets: Yahoo Finance market snapshots and performance summaries
- macro events: calendar/event parser for upcoming economic releases and central bank actions
- API configuration: `FRED_API_KEY` is consumed by the active `CalendarAgent`; `FINNHUB_KEY` is used by the legacy `economic_calendar.py` fetcher, not the active CalendarAgent. `NEWSAPI_KEY` and `ALPHA_VANTAGE_KEY` are read into config but have no current Python call sites.

### 4.8 Test and validation surface

The repository contains a focused validation suite in `tests/`:
- `test_analysis_schema.py` checks analysis contracts and score ranges
- `test_config_guard.py` enforces safe model configuration
- `test_news_tagger.py` validates category reclassification logic
- `test_report_sections.py` verifies the presence of key HTML report sections

These are the primary regression checks for the current design.

### 4.9 Security and observability

Operationally, the app relies on environment variables for secrets and machine-local configuration. Logs already contain per-phase and per-agent markers, but the system does not implement a formal audit subsystem or centralized telemetry stack. In other words, the observability model is best described as structured console logging combined with persisted output artifacts.

## 5. Runtime execution flow

### Phase 1: data acquisition
The orchestrator begins by calling the data agents:

1. NewsAgent executes and returns article dictionaries.
2. MarketAgent executes and returns prices, indices, and performance data.
3. CalendarAgent executes and returns future macro events.
4. NewsTagger reclassifies unmatched news buckets into better asset categories.
5. The orchestrator consolidates these into an `analysis_data` payload.

### Phase 2: AI analysis
The system forms a prompt-only market facts block from selected market-data fields and passes it to SentimentAgent, MacroAgent, MicroAgent, and CorrelationAgent. It does not validate generated numbers, include computed correlation values, or pass the block to all agents.

The following agents are then invoked:

- SentimentAgent
- MacroAgent
- MicroAgent
- CorrelationAgent
- SectorAgent
- RiskAgent
- EnhancedWatchlistAgent

Each agent adds structured outputs into the same analysis payload.

### Phase 3: backtesting
The `BacktestAgent` creates pending overall-market predictions and reports counts/statistics. The current path does not fetch ground truth or grade them after a horizon; see §4.4 for the separate legacy 24-hour implementation.

### Phase 4: export
The orchestrator writes:
- a timestamped JSON report
- a latest JSON pointer
- a generated HTML report
- a latest HTML pointer

## 6. Data flow design

```text
Raw feeds / APIs
  -> NewsAgent / MarketAgent / CalendarAgent
  -> normalized dictionaries
  -> Orchestrator aggregation
  -> NewsTagger normalization
  -> AI analysis agents
  -> structured insights payload
  -> BacktestAgent pending-prediction processing
  -> HTML and JSON export
```

## 7. Vector storage and retrieval status

### 7.1 Available vector DB capabilities

`FinanceVectorDB` defines ChromaDB collections for news, sentiment, market, analysis, and backtest data. It includes store methods and retrieval helpers, but the current orchestrator initializes this component without invoking those store or retrieval methods.

### 7.2 Metadata and retrieval helpers
`FinanceVectorDB` creates separate collections for:
- news articles
- sentiment snapshots
- market snapshots
- AI analysis artifacts
- backtest results

News records include timestamp/date, region, source, language, and link metadata. `find_similar_news(query, limit=5, region=None, days_back=30)` applies a date cutoff and optional region filter and orders results by vector similarity. It does not apply source/topic filters or explicit recency re-ranking. `get_historical_context(..., days_back=30)` requests three similar news results and includes sentiment history for 14 days when at least three snapshots exist.

### 7.3 Active vs. legacy retrieval callers
The historical-context helper is called from `legacy main.py`; it retrieves similar news and sentiment history before legacy analysis. The active `Orchestrator.run()` and its agents do not call vector DB store or retrieval methods. In particular, the active pipeline does not query sentiment, market, analysis, or backtest collections for prompt context.

The 30-day window and top-3 similar-news count therefore describe the helper/legacy path, not retrieval performed by the current orchestrated runtime. Metadata-aware filters and recency weighting are desired requirements, not active implementation behavior.

### 7.4 Intended future RAG flow
A future active RAG path would need to store current-run material, define filters/ranking and collection ownership, make retrieval calls from selected agents or the orchestrator, and record retrieved context for audit. Those behaviors are not connected in the active path.

### 7.5 Facts gate enforcement
The active orchestrator constructs a prompt-only `MARKET FACTS` string from selected market-data rows: indices `^GSPC`, `^IXIC`, `^DJI`, `^OMX`; yields `^TNX`, `^IRX`; and FX `DX-Y.NYB`, `EURUSD=X`, `USDSEK=X`. It does not include the computed `correlation_matrix` or other derived analysis values. The string is passed to SentimentAgent, MacroAgent, MicroAgent, and CorrelationAgent. It is not passed through the orchestrator calls to RiskAgent, SectorAgent, or EnhancedWatchlistAgent. There is no downstream numeric validation. The prompt facts string is not a top-level payload field or separately saved artifact, so exact prompt-level audit is unavailable.

## 8. Dual-model routing and orchestration design

### 8.1 Fast model path
The fast model is designed for:
- classification and tagging of news headlines
- routing and triage between tasks
- lightweight summaries and structured extraction
- lower-latency analysis that does not require deep synthesis

In the current implementation this is represented by `FAST_MODEL` and the `ModelRouter.get_model(task_type='fast')` path.

### 8.2 Deep model path
The deep model is designed for:
- macroeconomic interpretation
- cross-asset correlation reasoning
- micro-impact analysis
- nuanced risk synthesis and narrative interpretation
- higher-order decision support where stronger reasoning matters more than raw speed

This is represented by `DEEP_MODEL` and `ModelRouter.get_model(task_type='deep')`.

### 8.3 Orchestration pattern
The system separates orchestration from model choice:

```text
User trigger
  -> Orchestrator.run()
  -> run Phase 1 data collection
  -> send task to fast or deep model via ModelRouter
  -> (current orchestrator does not inject vector DB retrieval context)
  -> aggregate outputs from all agents
  -> save final JSON + HTML report
```

This produces a classic hybrid architecture:
- low-cost routing layer for efficiency
- higher-power reasoning layer for synthesis
- vector DB helper capability (retrieval is not wired into the active orchestrator)
- orchestrator to coordinate decisions and output assembly

## 9. MCP implementation status and architecture fit

The current application is not implemented as a formal MCP server/client system. It uses direct in-process orchestration and local model calls instead of external tool-protocol integration.

### 9.1 Current implementation reality
The app currently has:
- local Ollama model integration via `ModelRouter`
- local ChromaDB memory via `FinanceVectorDB`
- internal agent execution through `Orchestrator`
- no dedicated MCP tool registry, MCP client, or external resource protocol

### 9.2 How it relates to MCP
The architecture is conceptually close to MCP in spirit because it encapsulates capabilities behind a structured tool/agent layer, but it is not MCP-compliant as implemented.

A future MCP-ready extension would likely look like:

```text
MCP client / orchestrator
  -> tool calls: get_news(), get_market_data(), get_calendar(), get_risk_context()
  -> model router chooses fast/deep model
  -> RAG memory provides historical context
  -> final synthesis and report generation
```

### 9.3 Best interpretation
The repository today is best described as:
- a local multi-agent financial intelligence system
- includes vector storage/retrieval helpers, with retrieval currently limited to the legacy entry point
- using two model tiers for routing and reasoning
- not currently using RAG retrieval in the active orchestrator
- not yet a native MCP deployment

## 10. Design decisions and rationale

### 10.1 Agent-based decomposition
Breaking the system into specialist agents reduces cognitive load and allows targeted maintenance. For example, the sentiment and macro logic can evolve without reworking the market ingestion layer.

### 10.2 Shared infrastructure
Reusing `ModelRouter` and `FinanceVectorDB` across all agents reduces duplication and improves consistency. This is especially important when multiple agents rely on the same LLM routing and storage semantics.

### 10.3 Deterministic facts gating
The orchestrator generates a prompt-only fact block from selected market data and supplies it to four analysis agents. It does not cover derived correlation values, is not supplied to every agent, and has no post-generation enforcement.

### 10.4 Local-first AI deployment
The architecture defaults to local Ollama prompts instead of a cloud-only AI approach. This keeps the system operational in constrained hosting environments while remaining easy to extend.

### 10.5 Artifact-driven reporting
Final outputs are saved as both machine-readable JSON and a presentation-ready HTML summary. This supports both automation and analyst review.

## 11. Component interaction model

The system operates through a central orchestrator rather than a fully distributed event bus. Each run is assembled in a predictable sequence:

```text
main.py
  -> Orchestrator.__init__()
      -> ModelRouter()
      -> FinanceVectorDB()
      -> initialize agent instances
  -> Orchestrator.run()
      -> Phase 1: fetch market/news/calendar data
      -> Phase 2: run specialist analysis agents
      -> Phase 3: process pending backtest predictions
      -> Phase 4: export JSON + HTML report
```

The runtime interaction is as follows:

- `main.py` triggers the workflow.
- `Orchestrator` owns execution order and result aggregation.
- `ModelRouter` decides whether a task should use the fast or deep LLM.
- `FinanceVectorDB` provides storage/retrieval methods, but the active orchestrator does not call them.
- each agent reads shared inputs and writes structured findings back into the `analysis_data` payload.
- `HTMLReportGenerator` and the Streamlit dashboard read the final payload for visualization.

This creates a clean pipeline in which the orchestration layer handles coordination, while specialized agents remain focused on one concern at a time.

## 12. Summary

Finance Agent is best understood as a local-first, multi-agent financial intelligence system built around:

- structured ingestion of market, news, and macro data
- ChromaDB storage and retrieval helpers (legacy retrieval path; not active in the current orchestrator)
- fast/deep model separation for efficient and high-quality reasoning
- orchestrated agent execution with a single shared analysis payload
- artifact generation for both reporting and downstream tooling

This design is well suited to research, monitoring, and financial narrative validation, while remaining modular enough to evolve toward more formal MCP-style external tool integrations in the future.

## 13. Future-state architecture: MCP evolution path

The current implementation is a local-first architecture that already resembles a tool-oriented agent system, but it does not yet expose external MCP tool interfaces. A natural future evolution is to layer MCP around the current orchestration model rather than replacing it.

```text
External clients / UI / automation
          |
          v
+-------------------------------+
| MCP Adapter / Tool Layer      |
| - get_news()                  |
| - get_market_data()           |
| - get_calendar_events()       |
| - get_risk_context()          |
+-------------------------------+
          |
          v
+--------------------------------------------------+
| Orchestrator / Task Router                       |
| - classify task                                |
| - choose fast vs deep model                    |
| - compose prompt with RAG context              |
| - coordinate specialist agent execution       |
+--------------------------------------------------+
          |
          v
+-------------------------------+
| Local AI runtime              |
| - Ollama fast model           |
| - Ollama deep model           |
| - ChromaDB vector memory      |
+-------------------------------+
          |
          v
+-------------------------------+
| Report / dashboard output     |
| - JSON payload                |
| - HTML report                 |
| - Streamlit dashboard         |
+-------------------------------+
```

### 13.1 Why this evolution is sensible

- the current system already separates data gathering, model selection, and report generation
- the orchestration logic is already centralized in `Orchestrator`
- vector memory and schema-tolerant model calls are already in place
- the remaining gap is formal MCP exposure and standardized tool contracts

### 13.2 Practical migration path

A realistic migration path would be:

1. keep the current local orchestrator as the execution backbone
2. expose each data source or agent function as a tool interface
3. add an MCP client/server boundary only where external tooling or automation needs it
4. continue using the same fast/deep model routing and RAG memory under the hood
5. keep the report-generation layer unchanged so downstream dashboards remain stable

This would preserve the existing system behavior while enabling a more interoperable tool ecosystem.
