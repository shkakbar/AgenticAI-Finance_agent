from news_fetcher import RegionalNewsFetcher
from market_data import MarketDataFetcher
from economic_calendar import EconomicCalendarFetcher
from sentiment_analyzer import SentimentAnalyzer
from aaa_sector_analyzer import SectorAnalyzer
from timeframe_analyzer import TimeframeAnalyzer
from correlation_analyzer import CorrelationAnalyzer
from macro_micro_analyzer import MacroMicroAnalyzer
from model_router import ModelRouter
from backtester import Backtester
from vector_db import FinanceVectorDB
from html_report_generator import HTMLReportGenerator
from config import ASSET_CLASSES, REGIONS
from datetime import datetime
import os



def __main__():
    print("=" * 80)
    print("🚀 Advanced Finance & News Impact Analysis Agent v3.5 (RAG + Multi-Model + Backtest + Multi Language)")
    print("=" * 80)
    print()

    # Initialize model router FIRST
    print("🧠 Initializing Multi-Model Architecture...")
    model_router = ModelRouter()
    print()

    # Initialize model router FIRST
    print("🧠 Initializing Multi-Model Architecture...")
    model_router = ModelRouter()
    print()

    # Initialize vector DB
    print("🗄️ Initializing Vector Database (RAG)...")
    vector_db = FinanceVectorDB()
    print()

    # Initialize components
    news_fetcher = RegionalNewsFetcher()  # No translation
    market_fetcher = MarketDataFetcher()
    calendar_fetcher = EconomicCalendarFetcher()
    sentiment_analyzer = SentimentAnalyzer()
    sector_analyzer = SectorAnalyzer()
    timeframe_analyzer = TimeframeAnalyzer()
    correlation_analyzer = CorrelationAnalyzer(model_router)
    macro_micro_analyzer = MacroMicroAnalyzer(model_router)
    backtester = Backtester()
    html_generator = HTMLReportGenerator()

    # STEP 0: Evaluate past predictions
    print("📊 Step 0: Evaluating past AI predictions...")
    backtester.evaluate_past_predictions()
    backtest_stats = backtester.get_accuracy_stats()
    if backtest_stats['total_evaluated'] > 0:
        print(f"    🎯 Agent Accuracy: {backtest_stats['accuracy_pct']}% ({backtest_stats['total_wins']} wins / {backtest_stats['total_evaluated']} predictions)")
    print()

    # STEP 1: Market data
    print("📊 Fetching real-time market data...")
    market_data = market_fetcher.fetch_all_market_data()
    market_summary = market_fetcher.format_market_summary(market_data)
    print("✅ Market data fetched")

    # Store market snapshot in vector DB
    vector_db.store_market_snapshot(market_data)
    print()

    # STEP 2: Historical performance
    print("📈 Fetching multi-timeframe historical performance...")
    performance_data = timeframe_analyzer.fetch_historical_performance()
    performance_summary = timeframe_analyzer.format_performance_summary(performance_data)
    print()

    # STEP 3: Economic calendar
    print("📅 Fetching economic calendar...")
    economic_events = calendar_fetcher.fetch_upcoming_events(days_ahead=14)
    calendar_summary = calendar_fetcher.format_calendar_summary(economic_events)
    print(f"✅ Found {len(economic_events)} upcoming events")
    print()

    # STEP 4: News (no translation - original languages)
    print("📡 Fetching latest financial news (English + Native languages)...")
    all_news = news_fetcher.fetch_all_regional_news(hours_back=24)
    print(f"✅ Found {len(all_news)} news articles")

    # Count by language
    lang_counts = {}
    for news in all_news:
        lang = news.get('original_language', 'en')
        lang_counts[lang] = lang_counts.get(lang, 0) + 1

    for lang, count in lang_counts.items():
        print(f"   📝 {lang.upper()}: {count} articles")

    # Store news in vector DB
    news_stored = vector_db.store_news_articles(all_news)
    print(f"   🗄️  Stored {news_stored} articles in vector DB")
    print()

    if not all_news:
        print("❌ No news found.")
        return

    # Categorize by region
    print("🌍 Categorizing by region...")
    news_by_region = {}
    for news in all_news:
        region = news.get('region', 'Global')
        if region not in news_by_region:
            news_by_region[region] = []
        news_by_region[region].append(news)

    for region, news_list in news_by_region.items():
        ri = REGIONS.get(region, {})
        print(f"  {ri.get('flag', '🌐')} {ri.get('name', region)}: {len(news_list)} articles")
    print()

    # Categorize by asset class
    print("💎 Categorizing by asset class...")
    news_by_asset = {}
    for asset_class, config in ASSET_CLASSES.items():
        news_by_asset[asset_class] = []
        for news in all_news:
            if any(kw.lower() in news['title'].lower() or kw.lower() in news.get('summary', '').lower() for kw in config['keywords']):
                news_by_asset[asset_class].append({'news': news})

    for ac, nl in news_by_asset.items():
        print(f"  {ASSET_CLASSES[ac].get('icon', '•')} {ASSET_CLASSES[ac]['name']}: {len(nl)} articles")
    print()

    # STEP 5: Sentiment (FAST model)
    print("🎯 Analyzing sentiment [FAST model]...")
    sentiment_data = sentiment_analyzer.analyze_sentiment(all_news)
    sentiment_data['historical_trend'] = sentiment_analyzer.get_historical_trend(periods=10)
    print(f"✅ Overall: {sentiment_data['overall_sentiment']:+d} ({sentiment_data['overall_label']})")

    # Store sentiment in vector DB
    vector_db.store_sentiment_snapshot(sentiment_data)
    print()

    # STEP 5.5: Query historical context from vector DB (RAG)
    print("🧠 Querying historical context from vector DB...")
    news_summary_text = ' '.join([n.get('title', '') for n in all_news[:20]])
    historical_context = vector_db.get_historical_context(news_summary_text, days_back=30)
    if historical_context:
        print(f"    📚 Found historical context ({len(historical_context)} chars)")
        # Append historical context to market summary for AI analyzers
        market_summary_with_context = market_summary + "\n\n" + historical_context
    else:
        print("    ⏳ No historical context yet (will build over time)")
        market_summary_with_context = market_summary
    print()

    # STEP 6: US Sectors (FAST model)
    print("🏭 Analyzing US sectors [FAST model]...")
    us_sector_data = sector_analyzer.fetch_sector_performance('US')
    us_sector_sentiment = sector_analyzer.analyze_sector_sentiment('US', us_sector_data, all_news)
    print(f"✅ {len(us_sector_data)} US sectors")
    print()

    # STEP 7: Sweden Sectors (FAST model)
    print("🏭 Analyzing Sweden sectors [FAST model]...")
    sweden_sector_data = sector_analyzer.fetch_sector_performance('Sweden')
    sweden_sector_sentiment = sector_analyzer.analyze_sector_sentiment('Sweden', sweden_sector_data, all_news)
    print(f"✅ {len(sweden_sector_data)} Sweden sectors")
    print()

    # STEP 8: Correlations (DEEP model + RAG context)
    print("🔗 Analyzing correlations [DEEP model + RAG]...")
    correlation_data = correlation_analyzer.analyze_cross_asset_correlations(news_by_asset, market_summary_with_context)
    print("✅ Done")

    # Store analysis in vector DB
    if correlation_data.get('raw_analysis'):
        vector_db.store_analysis('correlation', correlation_data['raw_analysis'])
    print()

    # STEP 9: Macro (DEEP model + RAG context)
    print("🏛️ Analyzing macro impact [DEEP model + RAG]...")
    macro_analysis = macro_micro_analyzer.analyze_macro_impact(all_news, market_summary_with_context)
    print("✅ Done")

    if macro_analysis.get('raw_analysis'):
        vector_db.store_analysis('macro', macro_analysis['raw_analysis'])
    print()

    # STEP 10: Micro (DEEP model + RAG context)
    print("🏢 Analyzing micro impact [DEEP model + RAG]...")
    micro_analysis = macro_micro_analyzer.analyze_micro_impact(all_news, market_summary_with_context)
    print("✅ Done")

    if micro_analysis.get('raw_analysis'):
        vector_db.store_analysis('micro', micro_analysis['raw_analysis'])
    print()

    # STEP 11: Save predictions for backtesting
    print("💾 Saving today's AI predictions for future backtesting...")
    backtester.save_predictions(sentiment_data, market_data)
    vector_db.store_backtest_results(backtest_stats)
    print()

    # Prepare report data
    analysis_data = {
        'all_news': all_news,
        'news_by_region': {REGIONS.get(r, {}).get('name', r): len(nl) for r, nl in news_by_region.items()},
        'news_by_asset': news_by_asset,
        'market_data': market_data,
        'performance_data': performance_data,
        'economic_events': economic_events,
        'sentiment_data': sentiment_data,
        'us_sector_data': us_sector_data,
        'us_sector_sentiment': us_sector_sentiment,
        'sweden_sector_data': sweden_sector_data,
        'sweden_sector_sentiment': sweden_sector_sentiment,
        'correlation_analysis': correlation_data,
        'macro_analysis': macro_analysis,
        'micro_analysis': micro_analysis,
        'backtest_stats': backtest_stats,
        'vector_db_stats': vector_db.get_stats()
    }

    # Generate report
    print("📊 Generating HTML report...")
    html_report = html_generator.generate_html_report(analysis_data)

    os.makedirs('data/reports', exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_filename = f'data/reports/analysis_{timestamp}.html'

    with open(report_filename, 'w', encoding='utf-8') as f:
        f.write(html_report)

    print(f"✅ Report saved to: {report_filename}")
    print()
    print("=" * 80)
    print("📈 Run Summary:")
    print("=" * 80)
    print(f"  🚀 FAST model ({model_router.fast_model}): Sentiment, Sectors")
    print(f"  🧠 DEEP model ({model_router.deep_model}): Correlations, Macro, Micro")
    db_stats = vector_db.get_stats()
    print(f"  🗄️  Vector DB: {db_stats['news_count']} news, {db_stats['sentiment_count']} sentiment, {db_stats['analysis_count']} analysis")
    if backtest_stats['total_evaluated'] > 0:
        print(f"  🎯 Agent Accuracy: {backtest_stats['accuracy_pct']}% ({backtest_stats['total_wins']}/{backtest_stats['total_evaluated']})")
    else:
        print(f"  🎯 Agent Accuracy: Awaiting first 24h evaluation cycle...")
    print()
    print("🎉 Analysis complete! Open the HTML file in your browser.")

    
if __name__ == "__main__":
    __main__()