"""
HTML Report Generator - Creates a standalone HTML report from analysis data.
Generates a professional, self-contained HTML file with inline CSS.
"""
import html
import os
from datetime import datetime


class HTMLReportGenerator:
    def __init__(self, output_dir='data/reports'):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate(self, analysis_data):
        """Generate a complete HTML report from analysis data."""
        timestamp = datetime.now()
        filename = f"{self.output_dir}/report_{timestamp.strftime('%Y%m%d_%H%M%S')}.html"
        
        html = self._build_html(analysis_data, timestamp)
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html)
            print(f"✅ HTML report saved to {filename}")
            
            # Also save as latest_report.html for easy access
            latest_file = f"{self.output_dir}/latest_report.html"
            with open(latest_file, 'w', encoding='utf-8') as f:
                f.write(html)
            print(f"✅ Latest HTML report pointer updated.")
            
            return filename
        except Exception as e:
            print(f"❌ Failed to save HTML report: {e}")
            return None

    def _build_html(self, data, timestamp):
        """Build the complete HTML document."""
        
        # Extract data sections
        metadata = data.get('metadata', {})
        sentiment = data.get('sentiment_data', {})
        macro = data.get('macro_analysis', {})
        micro = data.get('micro_analysis', {})
        correlation = data.get('correlation_analysis', {})
        market_data = data.get('market_data', {})
        performance_data = data.get('performance_data', {})
        all_news = data.get('all_news', [])
        economic_events = data.get('economic_events', [])
        backtest = data.get('backtest_stats', {})
        vdb_stats = data.get('vector_db_stats', {})
        
        # Build sections
        sentiment_html = self._render_sentiment(sentiment)
        market_html = self._render_market(market_data, performance_data)
        news_html = self._render_news(all_news)
        macro_html = self._render_macro(macro)
        calendar_html = self._render_calendar(economic_events)
        backtest_html = self._render_backtest(backtest)
        
        html = f"""<!DOCTYPE html>
            <html lang="en">
            <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Finance Agent Report - {timestamp.strftime('%Y-%m-%d %H:%M')}</title>
            <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f7fa; color: #333; line-height: 1.6; }}
            .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #1e3c72, #2a5298); color: white; padding: 40px; border-radius: 12px; margin-bottom: 30px; }}
            .header h1 {{ font-size: 2.2rem; margin-bottom: 8px; }}
            .header p {{ opacity: 0.85; font-size: 0.95rem; }}
            .section {{ background: white; border-radius: 12px; padding: 24px; margin-bottom: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
            .section h2 {{ color: #1e3c72; font-size: 1.4rem; margin-bottom: 16px; padding-bottom: 8px; border-bottom: 2px solid #e8eef7; }}
            .section h3 {{ color: #2a5298; font-size: 1.1rem; margin: 16px 0 8px; }}
            .metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 20px; }}
            .metric-card {{ background: #f8fafc; border-radius: 8px; padding: 16px; text-align: center; border: 1px solid #e2e8f0; }}
            .metric-card .value {{ font-size: 1.8rem; font-weight: 700; color: #1e3c72; }}
            .metric-card .label {{ font-size: 0.85rem; color: #666; margin-top: 4px; }}
            .positive {{ color: #27ae60 !important; }}
            .negative {{ color: #e74c3c !important; }}
            .neutral {{ color: #757575 !important; }}
            table {{ width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 0.9rem; }}
            th, td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid #eee; }}
            th {{ background: #f8fafc; font-weight: 600; color: #555; }}
            tr:hover {{ background: #f8fafc; }}
            .news-item {{ padding: 12px 0; border-bottom: 1px solid #f0f0f0; }}
            .news-item:last-child {{ border-bottom: none; }}
            .news-item a {{ color: #1e3c72; text-decoration: none; font-weight: 500; }}
            .news-item a:hover {{ text-decoration: underline; }}
            .news-meta {{ font-size: 0.8rem; color: #888; margin-top: 4px; }}
            .outlook-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }}
            .outlook-card {{ background: #f8fafc; border-radius: 8px; padding: 16px; border-left: 4px solid #2a5298; }}
            .outlook-card h4 {{ color: #1e3c72; margin-bottom: 8px; font-size: 0.9rem; }}
            .outlook-card p {{ font-size: 0.85rem; color: #555; }}
            .takeaway {{ background: #f0f7ff; border-left: 5px solid #1e3c72; padding: 16px 20px; border-radius: 0 8px 8px 0; margin: 16px 0; }}
            .takeaway strong {{ color: #1e3c72; }}
            .calendar-item {{ padding: 12px 16px; border-left: 4px solid #f39c12; background: #fffdf5; border-radius: 0 8px 8px 0; margin-bottom: 8px; }}
            .calendar-item.high {{ border-left-color: #e74c3c; background: #fff5f5; }}
            .badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; }}
            .badge-high {{ background: #fde8e8; color: #c0392b; }}
            .badge-medium {{ background: #fef3cd; color: #856404; }}
            .badge-low {{ background: #d4edda; color: #155724; }}
            .footer {{ text-align: center; padding: 30px; color: #888; font-size: 0.85rem; }}
            @media (max-width: 768px) {{
            .outlook-grid {{ grid-template-columns: 1fr; }}
            .metrics-grid {{ grid-template-columns: repeat(2, 1fr); }}
            }}
            </style>
            </head>
            <body>
            <div class="container">
            <!-- HEADER -->
            <div class="header">
            <h1>📊 Financial Intelligence Report</h1>
            <p>Generated: {timestamp.strftime('%Y-%m-%d %H:%M:%S')} | Lookback: {metadata.get('hours_back', 24)}h | Regions: US, Sweden, EU, Asia</p>
            </div>

            <!-- SENTIMENT OVERVIEW -->
            <div class="section">
                <h2>🎯 Sentiment Analysis</h2>
                {sentiment_html}
            </div>

            <!-- MACRO ANALYSIS -->
            <div class="section">
                <h2>🏛️ Macroeconomic Impact</h2>
                {macro_html}
            </div>

            <!-- MARKET DATA -->
            <div class="section">
                <h2>💹 Market Data</h2>
                {market_html}
            </div>

            <!-- ECONOMIC CALENDAR -->
            <div class="section">
                <h2>📅 Economic Calendar</h2>
                {calendar_html}
            </div>

            <!-- NEWS -->
            <div class="section">
                <h2>📰 News Headlines ({len(all_news)} articles)</h2>
                {news_html}
            </div>

            <!-- BACKTEST -->
            <div class="section">
                <h2>🎖️ Backtesting & Accuracy</h2>
                {backtest_html}
            </div>

            <!-- FOOTER -->
            <div class="footer">
                <p><strong>Finance Agent v5.0</strong> | Powered by Qwen/Gemma (Ollama) | ChromaDB RAG</p>
                <p>Disclaimer: This report is for informational purposes only. It does not constitute financial advice.</p>
                <p>RAG Memory: {vdb_stats.get('news_count', 0)} news | {vdb_stats.get('sentiment_count', 0)} sentiment | {vdb_stats.get('market_count', 0)} market | {vdb_stats.get('analysis_count', 0)} analysis</p>
            </div>
            </div>
        </body>
        </html>"""
        return html

    def _render_sentiment(self, sentiment):
        """Render sentiment section with time-horizon splicing."""
        if not sentiment:
            return "<p>No sentiment data available.</p>"
        
        th = sentiment.get('time_horizon', {})
        cv = sentiment.get('consolidated_view', {})
        
        html = ""
        
        # Metrics row
        current_score = th.get('current_sentiment_score', 0)
        overall_score = th.get('overall_trend_score', 0)
        confidence = th.get('confidence_score', 0)
        
        current_class = 'positive' if current_score > 10 else 'negative' if current_score < -10 else 'neutral'
        overall_class = 'positive' if overall_score > 10 else 'negative' if overall_score < -10 else 'neutral'
        
        html += f"""
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="value {current_class}">{current_score:+d}</div>
                <div class="label">Current Sentiment ({th.get('current_label', 'N/A')})</div>
            </div>
            <div class="metric-card">
                <div class="value {overall_class}">{overall_score:+d}</div>
                <div class="label">Overall Trend ({th.get('overall_label', 'N/A')})</div>
            </div>
            <div class="metric-card">
                <div class="value">{confidence*100:.0f}%</div>
                <div class="label">AI Confidence</div>
            </div>
        </div>"""
        
        # Time-horizon outlooks
        if th.get('short_term_outlook'):
            html += f"""
        <h3>⏳ Future Outlook</h3>
        <div class="outlook-grid">
            <div class="outlook-card">
                <h4>Short-Term (1-4 weeks)</h4>
                <p>{th.get('short_term_outlook', 'N/A')}</p>
            </div>
            <div class="outlook-card">
                <h4>Medium-Term (1-3 months)</h4>
                <p>{th.get('medium_term_outlook', 'N/A')}</p>
            </div>
            <div class="outlook-card">
                <h4>Long-Term (3-12 months)</h4>
                <p>{th.get('long_term_outlook', 'N/A')}</p>
            </div>
        </div>"""
        
        # Key drivers
        drivers = th.get('key_drivers', [])
        if drivers:
            html += "<h3>🔑 Key Drivers</h3><ul>"
            for d in drivers:
                html += f"<li>{d}</li>"
            html += "</ul>"
        
        # Consolidated view
        if cv:
            html += f"""
        <h3>🌐 Consolidated Market View</h3>
        <div class="takeaway"><strong>Executive Summary:</strong> {cv.get('executive_summary', '')}</div>
        <p><strong>📈 Price Action:</strong> {cv.get('price_action_synthesis', '')}</p>
        <p><strong>🏛️ Macro Synthesis:</strong> {cv.get('macro_synthesis', '')}</p>
        <div class="takeaway"><strong>💡 Bottom Line:</strong> {cv.get('bottom_line', '')}</div>"""
        
        return html

    def _render_macro(self, macro):
        """Render macro analysis with US/Sweden deep-dive."""
        if not macro:
            return "<p>No macro analysis available.</p>"
        
        rdd = macro.get('regional_deep_dive', {})
        if rdd:
            return f"""
        <h3>🇺🇸 United States Outlook</h3>
        <p>{rdd.get('us_outlook', 'N/A')}</p>
        <h3>🇸🇪 Sweden Outlook</h3>
        <p>{rdd.get('sweden_outlook', 'N/A')}</p>
        <h3>🌉 Cross-Border Impact</h3>
        <p>{rdd.get('cross_border_impact', 'N/A')}</p>
        <div class="takeaway"><strong>⚖️ Key Differential:</strong> {rdd.get('key_differential', 'N/A')}</div>"""
        else:
            raw = macro.get('raw_analysis', 'No analysis available.')
            return f"<p>{raw}</p>"

    def _render_market(self, market_data, performance_data):
        """Render market data tables."""
        html = ""
        
        if not market_data:
            return "<p>No market data available.</p>"
        
        for asset_class, groups in market_data.items():
            if not isinstance(groups, dict):
                continue
            html += f"<h3>{asset_class.replace('_', ' ').title()}</h3>"
            html += "<table><tr><th>Name</th><th>Price</th><th>Daily %</th><th>Weekly %</th></tr>"
            
            for group_name, tickers in groups.items():
                if not isinstance(tickers, list):
                    continue
                for t in tickers:
                    price = t.get('price', 0)
                    daily = t.get('daily_change', 0)
                    weekly = t.get('weekly_change', 0)
                    daily_class = 'positive' if daily > 0 else 'negative' if daily < 0 else ''
                    weekly_class = 'positive' if weekly > 0 else 'negative' if weekly < 0 else ''
                    html += f"<tr><td>{t.get('flag', '')} {t.get('name', '')}</td><td>{price:,.2f}</td><td class='{daily_class}'>{daily:+.2f}%</td><td class='{weekly_class}'>{weekly:+.2f}%</td></tr>"
            
            html += "</table>"
        
        # Performance table
        if performance_data:
            html += "<h3>📊 Multi-Timeframe Performance</h3>"
            html += "<table><tr><th>Asset</th><th>Current</th><th>1M</th><th>3M</th><th>6M</th><th>1Y</th></tr>"
            for symbol, info in performance_data.items():
                tf = info.get('timeframes', {})
                html += f"<tr><td>{info.get('name', symbol)}</td><td>{info.get('current_price', 0):,.2f}</td>"
                for period in ['1M', '3M', '6M', '1Y']:
                    val = tf.get(period, 0)
                    cls = 'positive' if val > 0 else 'negative' if val < 0 else ''
                    html += f"<td class='{cls}'>{val:+.2f}%</td>"
                html += "</tr>"
            html += "</table>"
        
        return html

    def _render_news(self, all_news):
        """Render news headlines."""
        if not all_news:
            return "<p>No news articles fetched.</p>"
        
        html = ""
        for news in all_news[:30]:  # Limit to 30 for readability
            html += f"""
        <div class="news-item">
            <a href="{news.get('link', '#')}" target="_blank">{news.get('title', '')}</a>
            <div class="news-meta">{news.get('region_flag', '')} {news.get('region_name', '')} • {news.get('source', '')} • {news.get('published', '')[:16]}</div>
        </div>"""
        return html

    def _render_calendar(self, events):
        """Render economic calendar."""
        if not events:
            return "<p>No upcoming economic events.</p>"
        
        html = ""
        for event in events:
            impact = event.get('impact', 'LOW')
            impact_class = 'high' if impact == 'HIGH' else ''
            badge_class = 'badge-high' if impact == 'HIGH' else 'badge-medium' if impact == 'MEDIUM' else 'badge-low'
            html += f"""
        <div class="calendar-item {impact_class}">
            <strong>{event.get('event', '')}</strong> <span class="badge {badge_class}">{impact}</span><br>
            🗓️ {event.get('date', '')} {event.get('time', '')} • 🌍 {event.get('country', '')}<br>
            <small>{event.get('description', '')}</small>
        </div>"""
        return html

    def _render_backtest(self, backtest):
        """Render backtest stats."""
        if not backtest or backtest.get('total_evaluated', 0) == 0:
            return "<p>Awaiting first evaluation cycle. Run the agent for 24+ hours to build prediction history.</p>"
        
        total = backtest.get('total_evaluated', 0)
        wins = backtest.get('total_wins', 0)
        accuracy = backtest.get('accuracy_pct', 0)
        acc_class = 'positive' if accuracy >= 60 else 'negative' if accuracy < 40 else 'neutral'
        
        html = f"""
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="value {acc_class}">{accuracy:.1f}%</div>
                <div class="label">Accuracy</div>
            </div>
            <div class="metric-card">
                <div class="value">{total}</div>
                <div class="label">Total Predictions</div>
            </div>
            <div class="metric-card">
                <div class="value positive">{wins}</div>
                <div class="label">Wins</div>
            </div>
            <div class="metric-card">
                <div class="value negative">{total - wins}</div>
                <div class="label">Losses</div>
            </div>
        </div>"""
        
        recent = backtest.get('recent_results', [])
        if recent:
            html += "<h3>Recent Predictions</h3><table><tr><th>Date</th><th>Asset</th><th>AI Call</th><th>Market Move</th><th>Result</th></tr>"
            for r in recent:
                result_icon = '✅' if r.get('is_correct') else '❌'
                html += f"<tr><td>{r.get('date', '')}</td><td>{r.get('asset', '')}</td><td>{r.get('ai_label', '')}</td><td>{r.get('market_move', 0):+.2f}%</td><td>{result_icon}</td></tr>"
            html += "</table>"
        
        return html

    
