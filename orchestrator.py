"""
Orchestrator - Coordinates the multi-agent pipeline for data fetching, AI analysis, and backtesting.
Integrates with existing html_report_generator.py (generate_html_report method).
"""
import os
import json
import time
from datetime import datetime

from model_router import ModelRouter
from vector_db import FinanceVectorDB
from html_report_generator import HTMLReportGenerator
from agents.news_agent import NewsAgent
from agents.market_agent import MarketAgent
from agents.calendar_agent import CalendarAgent
from agents.sentiment_agent import SentimentAgent
from agents.macro_agent import MacroAgent
from agents.micro_agent import MicroAgent
from agents.correlation_agent import CorrelationAgent
from agents.sector_agent import SectorAgent
from agents.backtest_agent import BacktestAgent
from agents.fundamentals_agent import FundamentalsAgent
from agents.news_tagger import NewsTagger
from agents.risk_agent import RiskAgent
from agents.enhanced_watchlist_agent import EnhancedWatchlistAgent


class Orchestrator:
    def __init__(self, max_workers_phase1=2, max_workers_phase2=5, **kwargs):
        self.max_workers_phase1 = max_workers_phase1
        self.max_workers_phase2 = max_workers_phase2

        print("\n" + "=" * 80)
        print("🚀 FINANCE AGENT ORCHESTRATOR INITIALIZING")
        print("=" * 80)

        # 1. Initialize Shared Resources
        print("\n🔧 Initializing shared resources...")
        self.model_router = ModelRouter()
        self.vector_db = FinanceVectorDB()
        self.html_generator = HTMLReportGenerator()

        # 2. Initialize Agents
        print("\n🤖 Initializing agents...")
        self.news_agent = NewsAgent(self.model_router, self.vector_db)
        self.market_agent = MarketAgent(self.model_router, self.vector_db)
        self.calendar_agent = CalendarAgent(self.model_router, self.vector_db)

        self.sentiment_agent = SentimentAgent(self.model_router, self.vector_db)
        self.macro_agent = MacroAgent(self.model_router, self.vector_db)
        self.micro_agent = MicroAgent(self.model_router, self.vector_db)
        self.correlation_agent = CorrelationAgent(self.model_router, self.vector_db)
        self.sector_agent = SectorAgent(self.model_router, self.vector_db)
        self.backtest_agent = BacktestAgent(self.model_router, self.vector_db)
        self.fundamentals_agent = FundamentalsAgent(self.model_router, self.vector_db)
        self.news_tagger = NewsTagger(self.model_router)
        self.risk_agent = RiskAgent(self.model_router, self.vector_db)
        self.enhanced_watchlist_agent = EnhancedWatchlistAgent(self.model_router, self.vector_db)
        

        print("\n✅ Orchestrator ready.\n")

    def run(self, hours_back=24, calendar_days_ahead=14):
        """Main execution pipeline."""
        start_time = time.time()
        analysis_data = {}

        # ═══════════════════════════════════════════════════════════════
        # PHASE 1: Data Fetching
        # ═══════════════════════════════════════════════════════════════
        print("\n" + "=" * 80)
        print("PHASE 1: Fetching data...")
        print("=" * 80)

        print("  -> Fetching News...")
        try:
            news_result = self.news_agent.execute(hours_back) or {}
        except Exception as e:
            print(f"  ❌ NewsAgent failed: {e}")
            news_result = {}

        print("  -> Fetching Market Data...")
        try:
            market_result = self.market_agent.execute() or {}
        except Exception as e:
            print(f"  ❌ MarketAgent failed: {e}")
            market_result = {}

        print("  -> Fetching Economic Calendar...")
        try:
            calendar_result = self.calendar_agent.execute(calendar_days_ahead) or {}
        except Exception as e:
            print(f"  ❌ CalendarAgent failed: {e}")
            calendar_result = {}

        # Map Phase 1 results
        analysis_data['all_news'] = news_result.get('all_news', [])
        analysis_data['news_by_region'] = news_result.get('news_by_region', {})
        analysis_data['news_by_asset'] = news_result.get('news_by_asset', {})
        analysis_data['market_data'] = market_result.get('market_data', {})
        analysis_data['performance_data'] = market_result.get('performance_data', {})
        analysis_data['economic_events'] = calendar_result.get('economic_events', [])

        # NEWS-TAG: LLM re-classification of the 'Other' bucket
        print("  -> Re-tagging 'Other' headlines [FAST model]...")
        try:
            new_by_asset, moved = self.news_tagger.retag(analysis_data['news_by_asset'])
            analysis_data['news_by_asset'] = new_by_asset
            print(f"  ✅ [NewsTagger] Re-classified {moved} headlines out of 'Other'.")
        except Exception as e:
            print(f"  ❌ NewsTagger failed: {e}")

        if not analysis_data['all_news']:
            print("  ⚠️  No news fetched. AI analysis may be limited.")

        print(f"  ✅ Phase 1 complete. {len(analysis_data['all_news'])} news, "
            f"{len(analysis_data['economic_events'])} events.\n")

        """print("  -> Fetching Fundamentals (Watchlist)...")
        try:
            fund = self.fundamentals_agent.execute() or {}
            analysis_data['watchlist_fundamentals'] = fund.get('watchlist_fundamentals', [])
        except Exception as e:
            print(f"  ❌ FundamentalsAgent failed: {e}")
            analysis_data['watchlist_fundamentals'] = []"""
        # RETIRED (cleanup sweep): Legacy Fundamental Watchlist replaced by the Enhanced Watchlist.
        # The legacy screen had a dividend-yield percent/decimal bug (Apple 32%, Microsoft 72%)
        # and duplicated Enhanced Watchlist data. Empty list keeps downstream code safe;
        # the HTML section self-hides when rows are empty.
        analysis_data['watchlist_fundamentals'] = []

        print(f"  ✅ Phase 1 complete. {len(analysis_data['all_news'])} news, "
            f"{len(analysis_data['economic_events'])} events, "
            f"{len(analysis_data.get('watchlist_fundamentals', []))} fundamentals.\n")

        # ═══════════════════════════════════════════════════════════════
        # PHASE 2: AI Analysis
        # ═══════════════════════════════════════════════════════════════
        print("\n" + "=" * 80)
        print("PHASE 2: Running analysis agents...")
        print("=" * 80)

        # Build market summary for AI prompts
        # P0-1: Build a deterministic Facts Block to prevent LLM hallucination
        md = analysis_data.get('market_data', {})
        facts = ["MARKET FACTS (Use ONLY these figures for any quantitative statements):"]
        
        # Extract key indices
        for asset_class, groups in md.items():
            if asset_class == 'stocks':
                for group, tickers in groups.items():
                    for t in tickers:
                        if t.get('symbol') in ['^GSPC', '^IXIC', '^DJI', '^OMX']:
                            facts.append(f"- {t.get('name')}: {t.get('price')} (Daily: {t.get('daily_change')}%)")
        
        # Extract yields
        if 'bonds' in md:
            for group, tickers in md['bonds'].items():
                for t in tickers:
                    if t.get('symbol') in ['^TNX', '^IRX']:
                        facts.append(f"- {t.get('name')}: {t.get('price')}%")
                        
        # Extract FX
        if 'forex' in md:
            for group, tickers in md['forex'].items():
                for t in tickers:
                    if t.get('symbol') in ['DX-Y.NYB', 'EURUSD=X', 'USDSEK=X']:
                        facts.append(f"- {t.get('name')}: {t.get('price')} (Daily: {t.get('daily_change')}%)")

        market_summary = "\n".join(facts)

        # Sentiment Agent
        print("  -> Sentiment Agent...")
        try:
            sentiment_result = self.sentiment_agent.execute(
                analysis_data['all_news'], market_summary
            ) or {}
            analysis_data['sentiment_data'] = sentiment_result
        except Exception as e:
            print(f"  ❌ SentimentAgent failed: {e}")
            analysis_data['sentiment_data'] = {}

        # Macro Agent
        print("  -> Macro Agent...")
        try:
            analysis_data['macro_analysis'] = self.macro_agent.execute(
                analysis_data['all_news'], market_summary
            ) or {}
        except Exception as e:
            print(f"  ❌ MacroAgent failed: {e}")
            analysis_data['macro_analysis'] = {}

        # Micro Agent
        print("  -> Micro Agent...")
        try:
            analysis_data['micro_analysis'] = self.micro_agent.execute(
                analysis_data['all_news'], market_summary
            ) or {}
        except Exception as e:
            print(f"  ❌ MicroAgent failed: {e}")
            analysis_data['micro_analysis'] = {}

        # Risk Agent (runs FIRST so the real 12x12 matrix is available downstream)
        print("  -> Risk Agent...")
        try:
            risk_result = self.risk_agent.execute() or {}
            analysis_data['risk_metrics'] = risk_result.get('risk_metrics', {})
            analysis_data['correlation_matrix'] = risk_result.get('correlation_matrix', {})
        except Exception as e:
            print(f"  ❌ RiskAgent failed: {e}")
            analysis_data['risk_metrics'] = {}
            analysis_data['correlation_matrix'] = {}

        # Correlation Agent (now grounded in the real matrix)
        print("  -> Correlation Agent...")
        try:
            analysis_data['correlation_analysis'] = self.correlation_agent.execute(
                analysis_data.get('news_by_asset', {}), market_summary,
                analysis_data.get('correlation_matrix', {})
            ) or {}
        except Exception as e:
            print(f"  ❌ CorrelationAgent failed: {e}")
            analysis_data['correlation_analysis'] = {}


        # Enhanced Watchlist Agent (WATCHLIST 2.0)
        print("  -> Enhanced Watchlist Agent...")
        try:
            ew = self.enhanced_watchlist_agent.execute() or {}
            analysis_data['enhanced_watchlist'] = ew
        except Exception as e:
            print(f"  ❌ EnhancedWatchlistAgent failed: {e}")
            analysis_data['enhanced_watchlist'] = {}

        # Sector Agent
        print("  -> Sector Agent...")
        try:
            sector_result = self.sector_agent.execute(analysis_data['all_news']) or {}
            analysis_data.update(sector_result)
        except Exception as e:
            print(f"  ❌ SectorAgent failed: {e}")

        print("  ✅ Phase 2 complete.\n")

        # ═══════════════════════════════════════════════════════════════
        # PHASE 3: Backtesting
        # ═══════════════════════════════════════════════════════════════
        print("\n" + "=" * 80)
        print("PHASE 3: Backtesting...")
        print("=" * 80)

        try:
            backtest_result = self.backtest_agent.execute(
                sentiment_data=analysis_data.get('sentiment_data'),
                market_data=analysis_data.get('market_data')
            )
            analysis_data['backtest_stats'] = backtest_result or {}
        except Exception as e:
            print(f"  ❌ BacktestAgent failed: {e}")
            analysis_data['backtest_stats'] = {}

        print("  ✅ Phase 3 complete.\n")

        # ═══════════════════════════════════════════════════════════════
        # PHASE 4: Save & Export (JSON + HTML)
        # ═══════════════════════════════════════════════════════════════
        print("\n" + "=" * 80)
        print("PHASE 4: Saving reports...")
        print("=" * 80)

        timestamp = datetime.now()
        analysis_data['metadata'] = {
            'timestamp': timestamp.isoformat(),
            'timestamp_str': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'hours_back': hours_back,
            'calendar_days_ahead': calendar_days_ahead
        }

        analysis_data['vector_db_stats'] = {
            'news_count': len(analysis_data.get('all_news', [])),
            'sentiment_count': 1,
            'market_count': len(analysis_data.get('market_data', {})),
            'analysis_count': 3,
            'backtest_count': analysis_data.get('backtest_stats', {}).get('total_evaluated', 0)
        }

        os.makedirs('data/reports', exist_ok=True)

        # Save JSON
        json_filename = f"data/reports/analysis_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
        try:
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(analysis_data, f, indent=2, ensure_ascii=False, default=str)
            print(f"  ✅ JSON saved: {json_filename}")
        except Exception as e:
            print(f"  ❌ JSON save failed: {e}")

        # Update latest JSON pointer
        try:
            with open("data/reports/latest_analysis.json", 'w', encoding='utf-8') as f:
                json.dump(analysis_data, f, indent=2, ensure_ascii=False, default=str)
            print(f"  ✅ Latest JSON pointer updated.")
        except Exception as e:
            print(f"  ⚠️  Latest JSON update failed: {e}")

        # Generate HTML Report using existing generator
        try:
            html_content = self.html_generator.generate_html_report(analysis_data)
            
            # Save timestamped HTML
            html_filename = f"data/reports/report_{timestamp.strftime('%Y%m%d_%H%M%S')}.html"
            with open(html_filename, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"  ✅ HTML saved: {html_filename}")
            
            # Update latest HTML pointer
            with open("data/reports/latest_report.html", 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"  ✅ Latest HTML pointer updated.")
            
        except Exception as e:
            print(f"  ⚠️  HTML generation failed: {e}")

        elapsed = round(time.time() - start_time, 2)
        print(f"\n🏁 PIPELINE COMPLETE in {elapsed} seconds.")
        print("=" * 80 + "\n")

        return analysis_data

    def _build_market_facts(self, market_data):
        """P0-1: Deterministic facts block — the ONLY numbers narrative agents may cite."""
        if not market_data or not isinstance(market_data, dict):
            return "MARKET FACTS: unavailable for this run. Do not cite any market figures."
        lines = ["MARKET FACTS (latest available session; use ONLY these figures when making quantitative statements):"]
        for asset_class, groups in market_data.items():
            if not isinstance(groups, dict):
                continue
            rows = []
            for _group, entries in groups.items():
                if not isinstance(entries, list):
                    continue
                for e in entries:
                    try:
                        name = e.get('name') or e.get('symbol') or ''
                        price = e.get('price')
                        if price is None or price != price:          # skip NaN
                            continue
                        dc = e.get('daily_change') or 0.0
                        wc = e.get('weekly_change')
                        wc_txt = f", weekly {wc:+.2f}%" if wc is not None and wc == wc else ""
                        rows.append(f"- {name}: {price} (daily {dc:+.2f}%{wc_txt})")
                    except Exception:
                        continue
            if rows:
                lines.append(f"[{str(asset_class).upper()}]")
                lines.extend(rows)
        if len(lines) == 1:
            return "MARKET FACTS: unavailable for this run. Do not cite any market figures."
        return "\n".join(lines)
    
if __name__ == "__main__":
    orchestrator = Orchestrator()
    orchestrator.run(hours_back=24, calendar_days_ahead=14)