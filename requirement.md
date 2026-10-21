# Requirements specification

## 1. Purpose

Finance Agent is a financial intelligence system that gathers live market signals, news context, and macroeconomic developments, then applies AI-based reasoning to produce structured reports for monitoring and research. The system is intended to support analysts, researchers, and operators who need a rapid view of how financial narratives align with observable market movement.

## 2. Scope

The system includes:

- regional and global financial news collection
- live market pricing and relative performance tracking
- macroeconomic event ingestion from an economic calendar
- AI-driven sentiment and impact analysis
- sector, correlation, and macro/micro analysis
- backtesting of signal performance against market outcomes
- HTML and JSON report generation
- optional dashboard visualization through Streamlit

The system does not aim to execute autonomous trade orders or serve as a regulated financial advisor. It is an analysis and reporting workflow.

## 3. Functional requirements

### 3.1 News ingestion
The system shall:
- collect financial news items from configured sources and feeds
- normalize article metadata such as title, summary, source, region, and timestamp
- map headlines to regions and asset classes using keyword and classification logic
- reclassify low-confidence categories when needed through a NewsTagger step

### 3.2 Market data ingestion
The system shall:
- fetch live and recent market data for stocks, bonds, FX, volatility, crypto, and related assets
- calculate daily and weekly directional changes
- organize market data by region and asset class
- store snapshot data for trend comparison and historical retrieval

### 3.3 Calendar and macro context
The system shall:
- retrieve upcoming macro events such as central bank meetings and economic releases
- group events by region and importance
- pass event context into macro analysis and narrative generation

### 3.4 AI reasoning workflow
The system shall:
- route analysis tasks through an Ollama-backed model router
- support fast and deep models for different analysis tasks
- extract structured JSON from model responses for downstream use
- maintain deterministic facts blocks to anchor model reasoning in observed data

### 3.5 Multi-agent analysis
The system shall support agents for:
- sentiment analysis
- macroeconomic interpretation
- micro-level impact interpretation
- correlation studies
- sector and market rotation analysis
- risk assessment
- watchlist prioritization
- predictive signal evaluation through backtesting

### 3.6 Persistence and retrieval
The system shall:
- store article, sentiment, market, and analysis content in ChromaDB
- retain embeddings for semantic history and retrieval use cases
- keep reports and caches in the `data/` directory for repeatable workflows
- support retrieval-augmented prompting using relevant historical context before deep reasoning

Implementation status: ChromaDB collections and helper methods exist, but the active `Orchestrator.run()` path does not call the vector store or retrieval methods. The legacy `legacy main.py` path stores content and calls `get_historical_context`; this requirement is therefore not met by the current active pipeline.

### 3.7 Model routing and orchestration
The system shall:
- support at least two model roles: a lower-cost fast model and a higher-capability deep reasoning model
- use a model router to select the appropriate model by task type (for example, routing and classification vs. higher-order analysis)
- coordinate specialist agents through a central orchestration layer
- maintain a deterministic facts block so prompts are constrained to validated market signals

Implementation status: the current facts block is prompt-only, contains a selected subset of market data, and is passed to four analysis agents. It does not validate generated values and does not cover derived correlation data or all agents; see §5.7.

### 3.8 Reporting
The system shall:
- compile an end-to-end analysis payload into a structured JSON output
- generate a human-readable HTML report summarizing the technical narrative
- expose a lightweight dashboard for inspection of sentiment, market conditions, and report details

### 3.9 MCP readiness
The system should support extension toward an MCP-style tool architecture in the future, but the current baseline implementation is local-first and in-process; it does not require a formal MCP server/client protocol to function.

## 4. Non-functional requirements

### 4.1 Reliability
- The orchestration layer must continue execution when an individual agent fails.
- Data fetching and analysis tasks should fail gracefully and log clearly rather than terminating the entire pipeline.

### 4.2 Modularity
- Agents should be independently replaceable with consistent interfaces.
- Shared infrastructure should avoid hard-coded dependencies between model logic and data source logic.

### 4.3 Performance
- The system should support periodic runs for daily or intraday monitoring.
- Cached inputs and vector persistence should reduce repeated external calls.

### 4.4 Local-first deployment
- The default architecture expects local LLM execution through Ollama.
- External API keys are optional and should not block base functionality when unavailable.

### 4.5 Observability
- Logs should clearly identify each phase and agent in the analysis pipeline.
- Output artifacts should be timestamped to support historical review.
- Failures should be surfaced without stopping the entire workflow.

### 4.6 Security and configuration hygiene
- Secrets such as API keys must be stored in environment variables or equivalent secure configuration and must not be committed to source control.
- .env values should be read from local machine configuration and kept outside the repository.
- The system should avoid leaking sensitive prompt, model, or market data into logs beyond what is necessary for debugging.

## 5. Implementation constraints and execution expectations

### 5.1 Model routing
The system shall support a fast model path and a deep model path. The fast path is intended for classification, tagging, and lightweight routing; the deep path is intended for higher-order reasoning such as macro interpretation and correlation summary.

Current behavior: `config.py` pins `FAST_MODEL` to `qwen2.5:7b-instruct` and `DEEP_MODEL` to `qwen2.5:32b-instruct`, overriding `OLLAMA_FAST_MODEL` and `OLLAMA_DEEP_MODEL` values read from the environment. If a pinned model is not listed by Ollama, the router searches for `14b` in the deep role and `7b` in the fast role, then uses the first listed model. These are substring searches, so `17b` can match `7b`; the fallback does not exclude embedding models or require distinct models for the two roles. Both resolved names are printed during router initialization but are not persisted in report metadata. Logging of the fast-model fallback is absent. The router does not select a model dynamically based on an independent task classifier; agents pass task types to `ModelRouter`.

### 5.2 Retrieval configuration
The vector retrieval layer shall support metadata-aware recall using timestamps, region, source, and topic filters. Retrieval results should be ranked by semantic similarity plus recency and relevance weighting when available.

Implementation status: this is a requirement, not confirmed active behavior. The helper `find_similar_news` accepts a date window and optional region filter, searches the news collection by semantic similarity, and defaults to top-5. `get_historical_context` calls it with top-3 and a 30-day news window, then may include 14-day sentiment history. There is no source/topic filtering or explicit recency re-ranking in that helper. The legacy `legacy main.py` is its caller; the current orchestrator and agents make no vector retrieval calls, and no sentiment, market, analysis, or backtest collection is queried for active prompt context.

### 5.3 Execution model
The current implementation uses a synchronous orchestration flow rather than an asynchronous distributed event queue. Each phase should remain deterministic enough for repeatable output generation and debugging.

### 5.4 Scheduler behavior
Scheduler execution shall be based on `schedule` and a loop that polls for upcoming runs. The system should maintain a stable runtime cadence around active market hours and avoid redundant overlapping executions.

### 5.5 Backtesting methodology
Status: not implemented in the active orchestration path as an end-to-end benchmark.

`Orchestrator.run()` calls `BacktestAgent`, which writes pending overall-market predictions to `data/reports/backtest_history.json` when the overall sentiment label is not `Neutral`. Its evaluator only grades records with an already-populated `actual_move`; the active code neither supplies ground truth nor triggers evaluation after a horizon. As a result, cold-start accuracy is zero and remains so unless actual moves are added. There is no baseline.

A separate legacy `backtester.py` path writes `data/backtest/predictions.json`. When the legacy entry point invokes evaluation (on a later execution), it checks records at least 24 hours old using current Yahoo Finance prices for S&P 500, gold, and bitcoin; there is no separate timer/callback. It excludes sentiment scores in the range -19 to 19; scores >=20 are correct only if price increased, while scores <=-20 are correct only if price decreased. No zero-move tolerance or baseline is defined. This legacy path is not called by the active orchestrator and is not a requirement-grade or broad-asset benchmark.

### 5.6 Active and retired components
The repository may contain retired or legacy modules. The currently active orchestration path is the multi-agent workflow centered on `Orchestrator`. Legacy modules such as a direct fundamentals-only path may exist for historical reference but should not be treated as the active production path unless explicitly re-enabled.

In the current path, `watchlist_fundamentals` is initialized as an empty list. `FundamentalsAgent` is instantiated but not executed; `EnhancedWatchlistAgent` produces `enhanced_watchlist` instead.

`SectorAgent` currently fetches sector performance only for US and Sweden, using configured sector definitions for those two regions. Seven-region news scope does not mean equivalent sector coverage.

### 5.7 Facts block scope and auditability
The current orchestrator builds a prompt string from selected market rows: indices `^GSPC`, `^IXIC`, `^DJI`, `^OMX`; yields `^TNX`, `^IRX`; and FX `DX-Y.NYB`, `EURUSD=X`, `USDSEK=X`. It does not include computed values such as `correlation_matrix`. The string is passed to SentimentAgent, MacroAgent, MicroAgent, and CorrelationAgent, but not through the orchestrator calls to RiskAgent, SectorAgent, or EnhancedWatchlistAgent. The gate is prompt-only: there is no generated-output numeric validation. The facts string is not a top-level `analysis_data` field or separately persisted, so the exact prompt context cannot be audited from a report.

## 6. Testing and verification requirements

The project should maintain a regression suite covering:
- analysis schema constraints
- report section rendering
- model configuration guardrails
- news tagging and classification edge cases

Current repository checks include:
- `tests/test_analysis_schema.py`
- `tests/test_config_guard.py`
- `tests/test_news_tagger.py`
- `tests/test_report_sections.py`

## 7. Technical stack

- Python 3.10+
- Ollama for local LLM serving
- ChromaDB for vector persistence
- Yahoo Finance for market data
- Requests, FeedParser, BeautifulSoup for data collection
- Pandas and NumPy for processing and transformations
- Streamlit and Plotly for dashboard visualization
- Jinja2 for HTML rendering
- python-dotenv for environment variables

## 8. Acceptance criteria

These are target acceptance criteria, not a statement that all are currently satisfied:

- a complete run produces a valid analysis JSON payload
- an HTML report is generated without runtime exceptions
- market, news, and macro inputs are grouped by asset and region
- the output includes a coherent narrative supported by market data
- the workflow is repeatable across scheduled or manual executions
- model selection uses the appropriate route for the task complexity
- active retrieval memory contributes context without exceeding the system’s runtime budget (not currently satisfied by the active orchestrator; see §5.2)
- logs and outputs are sufficient for debugging and review

## 9. Configuration requirements

- Read local settings from environment variables, optionally loaded from a machine-local `.env` file using `python-dotenv`; do not commit secrets.
- `config.py` exposes `OLLAMA_HOST` with an in-code default of `http://localhost:11434`. The active `ModelRouter` does not explicitly pass this config value to the module-level Ollama API; `FinanceVectorDB` hard-codes its embedding URL to localhost. Endpoint configuration should be wired consistently before relying on a non-default host.
- `OLLAMA_MODEL` is a legacy model setting. `OLLAMA_FAST_MODEL` and `OLLAMA_DEEP_MODEL` are read, but current hard-coded model pins override them; environment-based model selection is therefore not effective until those pins are removed.
- Optional integration settings include `NEWSAPI_KEY`, `FINNHUB_KEY`, `ALPHA_VANTAGE_KEY`, and `FRED_API_KEY`. The active CalendarAgent consumes FRED; the legacy `economic_calendar.py` path consumes Finnhub. `NEWSAPI_KEY` and `ALPHA_VANTAGE_KEY` currently have no Python call sites. Their absence should not prevent the local base workflow.
- `OLLAMA_TRANSLATION_MODEL` can configure translation, and `OLLAMA_EMBEDDING_MODEL` configures embeddings (default `nomic-embed-text`).
- Keep `.env` outside version control and avoid logging secret values.

## 10. Operational workflow

- Run `python main.py` for a single orchestrated analysis.
- Run `python scheduler.py` for recurring scheduled runs; the scheduler uses the `schedule` library and polls at a 60-second interval.
- Run `streamlit run app.py` to inspect the dashboard.
- The active orchestrator runs data acquisition, analysis, backtest-agent processing, and JSON/HTML export sequentially.
- Runtime reports and active backtest-agent history are written under `data/reports/`; the separate legacy `backtester.py` uses `data/backtest/predictions.json`.
