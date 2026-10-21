"""
Finance Agent Dashboard - Interactive web interface for the AI finance agent.
Built with Streamlit for real-time data exploration and visualization.
Updated to reflect Phase 2 Structured AI Outputs, VIX, and Enhanced Calendar.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import re
from datetime import datetime
from data_loader import get_loader
from config import ASSET_CLASSES, SUB_CLASSES, REGIONS

# Page configuration
st.set_page_config(
    page_title="Finance Agent Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced Custom CSS
st.markdown("""
    <style>
    .main-header { font-size: 2.5rem; font-weight: 700; color: #1e3c72; margin-bottom: 0.5rem; }
    .sub-header { font-size: 1rem; color: #666; margin-bottom: 2rem; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { padding: 10px 20px; border-radius: 8px 8px 0 0; font-weight: 600; }
    
    .headline-item, .calendar-item { 
    padding: 12px 16px; background: white; border-radius: 8px; border-left: 4px solid #2a5298; 
    margin-bottom: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); 
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .headline-item:hover, .calendar-item:hover { transform: translateY(-2px); box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
    .headline-title, .calendar-title { font-weight: 600; color: #1a1a1a; font-size: 14px; margin-bottom: 4px; }
    .headline-meta, .calendar-meta { font-size: 12px; color: #6c757d; }
    
    .vdb-chip { display: inline-block; background: #e8eef7; padding: 6px 12px; border-radius: 6px; margin: 4px; font-size: 13px; }
    .vdb-chip strong { color: #1e3c72; font-size: 16px; }
    
    .takeaway-box { 
    background-color: #f0f7ff; padding: 16px 20px; border-radius: 8px; border-left: 5px solid #1e3c72; 
    margin-bottom: 24px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); 
    }
    .takeaway-title { color: #1e3c72; font-weight: 700; font-size: 1.1em; margin-bottom: 6px; }
    .takeaway-text { color: #333; font-size: 1.05em; line-height: 1.5; }
    
    .exec-summary-box {
    background: linear-gradient(135deg, #fff9e6, #fff3cd); padding: 20px; border-radius: 10px; 
    border-left: 5px solid #f39c12; margin-bottom: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    .exec-summary-box h3 { color: #d68910; margin-bottom: 10px; }
    .exec-summary-box p { font-size: 15px; line-height: 1.7; color: #2c3e50; margin-bottom: 12px; }
    .bottom-line-box {
    background: #e0f7fa; border-left: 4px solid #00838f; padding: 14px 18px; border-radius: 0 8px 8px 0; 
    margin-top: 12px; font-size: 15px; font-weight: 600; color: #004d40;
    }

    .dashboard-footer { margin-top: 40px; padding: 20px 0; border-top: 1px solid #e8eaed; text-align: center; color: #6c757d; font-size: 12px; }
    
    @media (max-width: 768px) {
    .main-header { font-size: 1.8rem; }
    .headline-item, .calendar-item { padding: 10px 12px; }
    }
    </style>
    """, unsafe_allow_html=True)

# --- Helper Functions ---
def get_sentiment_color(score):
    if score >= 60: return '#1b5e20'
    if score >= 30: return '#2e7d32'
    if score >= 10: return '#66bb6a'
    if score >= -10: return '#757575'
    if score >= -30: return '#ef6c00'
    if score >= -60: return '#e64a19'
    return '#c62828'

def get_accuracy_color(accuracy):
    if accuracy >= 60: return '#27ae60'
    if accuracy >= 40: return '#ef6c00'
    return '#e74c3c'

def render_sentiment_gauge(sentiment_data):
    overall = sentiment_data.get('overall_sentiment', 0)
    label = sentiment_data.get('overall_label', 'Neutral')
    shift = sentiment_data.get('sentiment_shift', 'stable')
    shift_icons = {'improving': '⬆️ Improving', 'deteriorating': '⬇️ Deteriorating', 'stable': '➡️ Stable'}
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=overall, domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': f"<b>{label.upper()}</b><br><span style='font-size:0.8em;color:{get_sentiment_color(overall)}'>{shift_icons.get(shift, '➡️ Stable')}</span>", 'font': {'size': 24}},
        gauge={'axis': {'range': [-100, 100]}, 'bar': {'color': get_sentiment_color(overall)}, 'bgcolor': "white", 'borderwidth': 2, 'bordercolor': "gray",
        'steps': [{'range': [-100, -60], 'color': '#ffcdd2'}, {'range': [-60, -30], 'color': '#ffe0b2'}, {'range': [-30, -10], 'color': '#fff9c4'},
        {'range': [-10, 10], 'color': '#f5f5f5'}, {'range': [10, 30], 'color': '#fff9c4'}, {'range': [30, 60], 'color': '#c8e6c9'}, {'range': [60, 100], 'color': '#a5d6a7'}],
        'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': overall}}))
    fig.update_layout(height=350, margin=dict(l=20, r=20, t=60, b=20))
    return fig

def render_accuracy_gauge(backtest_stats):
    accuracy = backtest_stats.get('accuracy_pct', 0)
    total = backtest_stats.get('total_evaluated', 0)
    wins = backtest_stats.get('total_wins', 0)
    if total == 0: return None
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=accuracy, domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': f"Agent Accuracy<br><span style='font-size:0.8em'>{wins}/{total} predictions</span>", 'font': {'size': 24}},
        gauge={'axis': {'range': [0, 100]}, 'bar': {'color': get_accuracy_color(accuracy)}, 'bgcolor': "white", 'borderwidth': 2, 'bordercolor': "gray",
        'steps': [{'range': [0, 40], 'color': '#ffcdd2'}, {'range': [40, 60], 'color': '#fff9c4'}, {'range': [60, 100], 'color': '#c8e6c9'}],
        'threshold': {'line': {'color': "darkblue", 'width': 4}, 'thickness': 0.75, 'value': accuracy}}))
    fig.update_layout(height=300, margin=dict(l=20, r=20, t=60, b=20))
    return fig

def render_sentiment_bar_chart(data_dict, title, icons_dict=None):
    if not data_dict:
        return None

    names, scores, colors, labels = [], [], [], []
    for key, info in data_dict.items():
        if isinstance(info, dict):
            score = info.get('score', 0)
            label = info.get('label', 'Neutral')
            icon = icons_dict.get(key, '') if icons_dict else ''
            names.append(f"{icon} {key.replace('_', ' ').title()}")
            scores.append(score)
            colors.append(get_sentiment_color(score))
            labels.append(f"{score:+d} ({label})")

    if not names:
        return None

    fig = go.Figure()
    fig.add_trace(go.Bar(y=names, x=scores, orientation='h', marker_color=colors, text=labels, textposition='outside', hoverinfo='text'))
    fig.update_layout(
        height=max(300, len(names) * 35),
        xaxis=dict(range=[-120, 120], zeroline=True, zerolinewidth=2, zerolinecolor='black', showgrid=True, gridcolor='#f0f0f0'),
        yaxis=dict(autorange='reversed', showgrid=False),
        showlegend=False,
        margin=dict(l=150, r=100, t=30, b=20),
        plot_bgcolor='white',
        paper_bgcolor='white',
        title=title,
    )
    return fig


def render_ai_analysis(raw_text, report_type):
    if not raw_text or "No " in raw_text[:10] or "failed" in raw_text.lower():
        st.info(raw_text or "No analysis available.")
        return

    bottom_line = ""
    match = re.search(r'BOTTOM LINE:\s*(.*?)(?=\n\s*\n|\Z)', raw_text, re.IGNORECASE | re.DOTALL)
    if match:
        bottom_line = match.group(1).strip()

    if bottom_line:
        st.markdown(
            f"""<div class="takeaway-box"><div class="takeaway-title">💡 {report_type} KEY TAKEAWAY</div><div class="takeaway-text">{bottom_line}</div></div>""",
            unsafe_allow_html=True,
        )

    formatted_text = re.sub(r'^([A-Z][A-Z\s&-]+:)', r'**\1*', raw_text, flags=re.MULTILINE)
    st.markdown(formatted_text.strip())

    # UI-1 Helper: Filter news based on contextual focus
def filter_news_by_focus(news_list, focus):
        if focus == "All Topics" or not news_list:
            return news_list
        focus_lower = focus.lower()
        filtered = []
        for n in news_list:
            title = n.get('title', '').lower()
            region = n.get('region_name', '').lower()
            if focus_lower == "sweden focus" and ("sweden" in region or "se" in region or "sek" in title):
                filtered.append(n)
            elif focus_lower == "us focus" and ("united states" in region or "us" in region or "fed" in title):
                filtered.append(n)
            elif focus_lower in title or focus_lower in region:
                filtered.append(n)
        return filtered

def __main__():
        loader = get_loader()
        metadata = loader.get_report_metadata()

        # ═══════════════════════════════════════════════════════════════
        # SIDEBAR
        # ═══════════════════════════════════════════════════════════════
        with st.sidebar:
            st.title("🚀 Finance Agent")
            st.markdown("---")
            if metadata['exists']:
                st.success("✅ Data loaded")
                st.info(f"**Last Updated:**  \n{metadata['timestamp_str']}\n\n**File Size:** {metadata['file_size_kb']} KB")
            else:
                st.warning("⚠️ No data available")
                st.info("Run the agent to generate data.")
            st.markdown("---")
            st.subheader("⚙️ Agent Configuration")
            hours_back = st.slider("News Lookback (hours)", 6, 48, 24, key="sidebar_hours")
            calendar_days = st.slider("Calendar Days Ahead", 7, 30, 14, key="sidebar_days")
            st.markdown("---")
            run_agent = st.button("🚀 Run Agent Now", type="primary", use_container_width=True, key="sidebar_run")
            if run_agent:
                with st.spinner(f"🤖 Running AI Agent ({hours_back}h news, {calendar_days}d calendar)... This takes 10-15 minutes."):
                    try:
                        from orchestrator import Orchestrator
                        orchestrator = Orchestrator()
                        result = orchestrator.run(hours_back=hours_back, calendar_days_ahead=calendar_days)
                        if result:
                            st.success("✅ Agent run complete! Refreshing dashboard...")
                            st.rerun()
                        else:
                            st.error("❌ Agent run failed. Check terminal.")
                    except Exception as e:
                        st.error(f"❌ Execution Error: {str(e)}")
                        st.exception(e)
            st.markdown("---")
            st.subheader("📚 Available Reports")
            reports = loader.get_all_reports(limit=5)
            if reports:
                for i, report in enumerate(reports):
                    st.caption(f"{i+1}. {report['timestamp_str']} ({report['file_size_kb']} KB)")
            else:
                st.caption("No reports yet")
            st.markdown("---")
            st.caption(f"Built with Streamlit • {datetime.now().strftime('%Y-%m-%d %H:%M')}")

        # ═══════════════════════════════════════════════════════════════
        # MAIN CONTENT
        # ══════════════════════════════════════════════════════════════
        st.markdown('<div class="main-header">📊 Financial Intelligence Dashboard</div>', unsafe_allow_html=True)
        if not metadata['exists']:
            st.warning("⚠️ No analysis data found. Use the sidebar to run the agent first.")
            st.stop()
        data = loader.load_latest_analysis()
        if not data:
            st.error("❌ Failed to load analysis data")
            st.stop()
        st.markdown(f'<div class="sub-header">Last updated: {metadata["timestamp_str"]}</div>', unsafe_allow_html=True)

        # Reordered tabs to match the logical flow of the new HTML report
        tab_overview, tab_sentiment, tab_market, tab_macro, tab_sectors, tab_calendar_news, tab_backtest = st.tabs([
            "📊 Overview", "🎯 Sentiment", "💹 Markets", "🏛️ Macro & Regional", "🏭 Sectors", "📅 Calendar & News", "🎖️ Backtest"
        ])

        # ═══════════════════════════════════════════════════════════════
        # TAB 1: OVERVIEW
        # ═══════════════════════════════════════════════════════════════
        with tab_overview:
            st.header("📊 Executive Overview")
            
            sentiment = data.get('sentiment_data', {})
            cv = sentiment.get('consolidated_view', {})
            th = sentiment.get('time_horizon', {})
            backtest = data.get('backtest_stats', {})

            # NEW: Executive Summary Box
            if cv or th:
                st.markdown('<div class="exec-summary-box">', unsafe_allow_html=True)
                st.markdown("### ⚡ Executive Summary")
                if cv.get('executive_summary') and cv['executive_summary'] != 'No consolidated view available.':
                    st.markdown(f"<p><strong>Market Overview:</strong> {cv['executive_summary']}</p>", unsafe_allow_html=True)
                
                cols = st.columns(3)
                with cols[0]:
                    if th.get('short_term_outlook') and th['short_term_outlook'] != 'No data available.':
                        st.markdown(f"**⏱️ Short-Term (1-4w):**<br>{th['short_term_outlook']}", unsafe_allow_html=True)
                with cols[1]:
                    if th.get('medium_term_outlook') and th['medium_term_outlook'] != 'No data available.':
                        st.markdown(f"**📅 Medium-Term (1-3m):**<br>{th['medium_term_outlook']}", unsafe_allow_html=True)
                with cols[2]:
                    if th.get('long_term_outlook') and th['long_term_outlook'] != 'No data available.':
                        st.markdown(f"**🔮 Long-Term (3-12m):**<br>{th['long_term_outlook']}", unsafe_allow_html=True)

                if cv.get('bottom_line') and cv['bottom_line'] != 'No data available.':
                    st.markdown(f'<div class="bottom-line-box">💡 <strong>Bottom Line:</strong> {cv["bottom_line"]}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            st.markdown("---")
            
            # Gauges
            col1, col2 = st.columns([2, 1])
            with col1:
                if sentiment:
                    st.subheader("🎯 Overall Market Sentiment")
                    fig = render_sentiment_gauge(sentiment)
                    if fig: st.plotly_chart(fig, use_container_width=True, key="overview_sentiment_gauge")
            with col2:
                if backtest and backtest.get('total_evaluated', 0) > 0:
                    st.subheader("🎖️ Agent Accuracy")
                    fig = render_accuracy_gauge(backtest)
                    if fig: st.plotly_chart(fig, use_container_width=True, key="overview_accuracy_gauge")
                else:
                    st.subheader("⏳ Agent Accuracy")
                    st.info("Awaiting first 24h evaluation cycle")
                    
            st.markdown("---")
            
            # Key Metrics
            st.subheader("📈 Key Metrics")
            news_count = len(data.get('all_news', []))
            ticker_count = sum(len(t) for g in data.get('market_data', {}).values() if isinstance(g, dict) for t in g.values() if isinstance(t, list))
            events_count = len(data.get('economic_events', []))
            accuracy = backtest.get('accuracy_pct', 0) if backtest else 0
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("📰 News Articles", news_count)
            c2.metric("💹 Market Tickers", ticker_count)
            c3.metric("📅 Economic Events", events_count)
            c4.metric("🎖️ Agent Accuracy", f"{accuracy}%")
            
            st.markdown("---")
            
            # Asset Sentiment Chart
            if sentiment and sentiment.get('asset_sentiments'):
                st.subheader("💎 Sentiment by Asset Class")
                asset_icons = {'stocks': '📈', 'bonds': '🏦', 'forex': '💱', 'crypto': '₿', 'funds': '💼', 'bullion': '🥇', 'volatility': '📉'}
                fig = render_sentiment_bar_chart(sentiment.get('asset_sentiments', {}), "", asset_icons)
                if fig: st.plotly_chart(fig, use_container_width=True, key="overview_asset_chart")

        # ═══════════════════════════════════════════════════════════════
        # TAB 2: SENTIMENT
        # ═══════════════════════════════════════════════════════════════
        with tab_sentiment:
            st.header("🎯 Sentiment Analysis")
            st.markdown("Deep, time-horizon sentiment and consolidated market views.")
            st.markdown("---")
            
            sentiment = data.get('sentiment_data', {})
            if not sentiment:
                st.info("No sentiment data available.")
            else:
                # Time-Horizon Sentiment (AI-SENT-1)
                th = sentiment.get('time_horizon', {})
                if th:
                    st.subheader("⏳ Time-Horizon Sentiment Splicing")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Current Sentiment", f"{int(th.get('current_sentiment_score', 0)):+d}", th.get('current_label', ''))
                    c2.metric("Overall Trend", f"{int(th.get('overall_trend_score', 0)):+d}", th.get('overall_label', ''))
                    c3.metric("AI Confidence", f"{th.get('confidence_score', 0)*100:.0f}%")
                    
                    st.markdown("---")
                    st.subheader("🔑 Key Drivers")
                    for driver in th.get('key_drivers', []): 
                        st.markdown(f"• {driver}")

                st.markdown("---")

                # Consolidated Market View (AI-SENT-2)
                cv = sentiment.get('consolidated_view', {})
                if cv:
                    st.subheader("🌐 Deep Consolidated Sentiment View")
                    col_a, col_b = st.columns(2)
                    with col_a: 
                        st.markdown("#### 📈 Price Action Synthesis")
                        st.markdown(cv.get('price_action_synthesis', 'No data'))
                    with col_b: 
                        st.markdown("#### 🏛️ Macro Synthesis")
                        st.markdown(cv.get('macro_synthesis', 'No data'))

                st.markdown("---")

                # Breakdowns
                st.subheader("🔍 Sentiment Breakdowns")
                col_reg, col_sub = st.columns(2)
                
                with col_reg:
                    st.markdown("#### 🌍 By Region")
                    region_icons = {'US': '🇺🇸', 'EU': '🇪🇺', 'JP': '🇯🇵', 'CN': '🇨🇳', 'Nordics': '🌍', 'DK': '🇩🇰', 'SE': '🇸🇪'}
                    fig_reg = render_sentiment_bar_chart(sentiment.get('regional_sentiments', {}), "", region_icons)
                    if fig_reg: st.plotly_chart(fig_reg, use_container_width=True)
                    
                with col_sub:
                    st.markdown("#### 🔬 By Sub-Class")
                    sub_icons = {}
                    for asset_key, subs in SUB_CLASSES.items():
                        for sub_name, sub_info in subs.items():
                            sub_icons[sub_name] = sub_info.get('icon', '')
                    fig_sub = render_sentiment_bar_chart(sentiment.get('sub_class_sentiments', {}), "", sub_icons)
                    if fig_sub: st.plotly_chart(fig_sub, use_container_width=True)
                    # ─────────────────────────────────────────────────────────
            # AI-IMPACT: Causal Impact & Transmission Analysis
            # ─────────────────────────────────────────────────────────
            impact = sentiment.get('impact_analysis', {})
            if impact:
                st.markdown("---")
                st.subheader("🎯 Causal Impact & Transmission Analysis")
                st.markdown("Per-news AI reasoning: segment pressure, opposing drivers, delayed transmission, and Sweden exposure.")

                # Req 1 — News-driven causal pressure by asset class
                cat = impact.get('category_impact', {})
                if cat:
                    st.markdown("##### 📊 News-Driven Causal Pressure by Asset Class")
                    cols = st.columns(min(len(cat), 7))
                    for col, (seg, score) in zip(cols, cat.items()):
                        col.metric(str(seg).title(), f"{int(score):+d}")

                # Req 2 — Opposing drivers (market tensions)
                opp = impact.get('opposing_impacts', [])
                if opp:
                    st.markdown("##### ⚖️ Market Tensions (Opposing Drivers)")
                    for o in opp[:4]:
                        with st.expander(f"📰 {str(o.get('headline', ''))[:100]}", expanded=False):
                            for e in o.get('effects', []):
                                sc = int(e.get('score', 0))
                                icon = "🟢" if sc > 0 else "🔴"
                                st.markdown(f"{icon} **{str(e.get('segment', '')).title()} ({sc:+d}):** {e.get('why', '')}")

                # Req 3 — Forward impact watchlist (delayed transmission)
                dl = impact.get('delayed_impacts', [])
                if dl:
                    st.markdown("##### ⏳ Forward Impact Watchlist (Coming Days/Weeks)")
                    df_dl = pd.DataFrame([{
                        'Timing': str(d.get('timing', '')).upper(),
                        'Segment': str(d.get('segment', '')).title(),
                        'Impact': int(d.get('score', 0)),
                        'Headline': str(d.get('headline', ''))[:80],
                        'Rationale': d.get('why', '')
                    } for d in dl[:8]])
                    st.dataframe(df_dl, use_container_width=True, hide_index=True)

                # Req 4 — Sweden market transmission
                se = impact.get('se_impact', {})
                if se:
                    st.markdown("##### 🇸🇪 Sweden Market Transmission")
                    c_se1, c_se2 = st.columns([1, 2])
                    overall = int(se.get('overall', 0))
                    c_se1.metric("Net SE Impact", f"{overall:+d}")
                    subs = se.get('by_sub_class', {})
                    if subs:
                        se_dict = {str(k): {'score': int(v),
                                            'label': 'Bullish' if v > 15 else 'Bearish' if v < -15 else 'Neutral'}
                                   for k, v in subs.items()}
                        fig_se = render_sentiment_bar_chart(se_dict, "", None)
                        if fig_se:
                            c_se2.plotly_chart(fig_se, use_container_width=True, key="se_transmission_chart")
            else:
                st.info("No causal impact analysis in this report. Run the pipeline to generate it.")

                # ─────────────────────────────────────────────────────────
                # AI-IMPACT: Causal Impact & Transmission Analysis
                # ─────────────────────────────────────────────────────────
                impact = sentiment.get('impact_analysis', {})
                if impact:
                    st.markdown("---")
                    st.subheader("🎯 Causal Impact & Transmission Analysis")
                    st.markdown("Per-news AI reasoning: segment pressure, opposing drivers, delayed transmission, and Sweden exposure.")

                    # Req 1 — News-driven causal pressure by asset class
                    cat = impact.get('category_impact', {})
                    if cat:
                        st.markdown("##### 📊 News-Driven Causal Pressure by Asset Class")
                        cols = st.columns(min(len(cat), 7))
                        for col, (seg, score) in zip(cols, cat.items()):
                            col.metric(str(seg).title(), f"{int(score):+d}")

                    # Req 2 — Opposing drivers (market tensions)
                    opp = impact.get('opposing_impacts', [])
                    if opp:
                        st.markdown("##### ⚖️ Market Tensions (Opposing Drivers)")
                        for o in opp[:4]:
                            with st.expander(f"📰 {str(o.get('headline', ''))[:100]}", expanded=False):
                                for e in o.get('effects', []):
                                    sc = int(e.get('score', 0))
                                    icon = "🟢" if sc > 0 else "🔴"
                                    st.markdown(f"{icon} **{str(e.get('segment', '')).title()} ({sc:+d}):** {e.get('why', '')}")

                    # Req 3 — Forward impact watchlist (delayed transmission)
                    dl = impact.get('delayed_impacts', [])
                    if dl:
                        st.markdown("##### ⏳ Forward Impact Watchlist (Coming Days/Weeks)")
                        df_dl = pd.DataFrame([{
                            'Timing': str(d.get('timing', '')).upper(),
                            'Segment': str(d.get('segment', '')).title(),
                            'Impact': int(d.get('score', 0)),
                            'Headline': str(d.get('headline', ''))[:80],
                            'Rationale': d.get('why', '')
                        } for d in dl[:8]])
                        st.dataframe(df_dl, use_container_width=True, hide_index=True)

                    # Req 4 — Sweden market transmission
                    se = impact.get('se_impact', {})
                    if se:
                        st.markdown("##### 🇸🇪 Sweden Market Transmission")
                        c_se1, c_se2 = st.columns([1, 2])
                        overall = int(se.get('overall', 0))
                        c_se1.metric("Net SE Impact", f"{overall:+d}")
                        subs = se.get('by_sub_class', {})
                        if subs:
                            se_dict = {str(k): {'score': int(v),
                                                'label': 'Bullish' if v > 15 else 'Bearish' if v < -15 else 'Neutral'}
                                    for k, v in subs.items()}
                            fig_se = render_sentiment_bar_chart(se_dict, "", None)
                            if fig_se:
                                c_se2.plotly_chart(fig_se, use_container_width=True, key="se_transmission_chart")
                else:
                    st.info("No causal impact analysis in this report. Run the pipeline to generate it.")
        
        # ═══════════════════════════════════════════════════════════════
        # TAB 3: MARKETS
        # ═══════════════════════════════════════════════════════════════
        with tab_market:
            st.header("💹 Market Data")
            st.markdown("Live prices, volatility indices, and multi-timeframe performance.")
            st.markdown("---")
            market_data = data.get('market_data', {})
            performance_data = data.get('performance_data', {})
            
            if not market_data: 
                st.info("No market data available.")
            else:
                # Added Volatility to asset tabs
                asset_tabs = st.tabs(["📈 Stocks", "💱 Forex", "🏦 Bonds", "₿ Crypto", "🥇 Bullion", "📉 Volatility"])
                asset_keys = ['stocks', 'forex', 'bonds', 'crypto', 'bullion', 'volatility']
                
                for tab, asset_key in zip(asset_tabs, asset_keys):
                    with tab:
                        asset_groups = market_data.get(asset_key, {})
                        if not asset_groups: 
                            st.info(f"No {asset_key} data available.")
                            continue
                        
                        for group_name, tickers in asset_groups.items():
                            if isinstance(tickers, list) and tickers:
                                st.subheader(f"{group_name.replace('_', ' ').title()}")
                                cols = st.columns(3)
                                for idx, ticker in enumerate(tickers):
                                    with cols[idx % 3]:
                                        price = ticker.get('price', 0)
                                        daily = ticker.get('daily_change', 0)
                                        weekly = ticker.get('weekly_change', 0)
                                        
                                        # Special formatting for VIX
                                        if asset_key == 'volatility':
                                            vix_color = '#27ae60' if price < 15 else '#f39c12' if price < 20 else '#ef6c00' if price < 30 else '#e74c3c'
                                            st.markdown(f"<h3 style='color:{vix_color}; margin-bottom:0;'>{price:.2f}</h3>", unsafe_allow_html=True)
                                            st.caption(f"{ticker.get('flag', '')} {ticker.get('name', '')}")
                                            st.markdown(f"<span style='color:{'#e74c3c' if daily > 0 else '#27ae60'};'>{daily:+.2f}% today</span>", unsafe_allow_html=True)
                                        else:
                                            st.metric(
                                                label=f"{ticker.get('flag', '')} {ticker.get('name', 'Unknown')}", 
                                                value=f"{price:,.2f}", 
                                                delta=f"{daily:+.2f}% (Daily) | {weekly:+.2f}% (Week)"
                                            )
                        st.markdown("---")
                        
                # Multi-Timeframe Performance
                st.subheader("📊 Multi-Timeframe Performance")
                if performance_data:
                    perf_rows = []
                    # Map keys to display order
                    display_keys = ['sp500', 'nasdaq', 'omx_stockholm', 'us10y_yield', 'gold', 'silver', 'bitcoin', 'ethereum', 'usd_sek', 'eur_sek']
                    for key in display_keys:
                        if key in performance_data:
                            asset_info = performance_data[key]
                            row = {'Asset': f"{asset_info.get('icon', '')} {asset_info.get('name', key)}", 'Current': asset_info.get('current_price', 0)}
                            timeframes = asset_info.get('timeframes', {})
                            for tf in ['1M', '3M', '6M', '1Y', '3Y', '5Y']: 
                                row[tf] = timeframes.get(tf, None)
                            perf_rows.append(row)
                            
                    if perf_rows:
                        df_perf = pd.DataFrame(perf_rows)
                        def color_performance(val):
                            if isinstance(val, (int, float)):
                                if val > 0: return 'color: #27ae60; font-weight: bold'
                                elif val < 0: return 'color: #e74c3c; font-weight: bold'
                            return ''
                        timeframe_cols = ['1M', '3M', '6M', '1Y', '3Y', '5Y']
                        styled_df = df_perf.style.map(color_performance, subset=timeframe_cols)
                        st.dataframe(styled_df, use_container_width=True, hide_index=True)
                else: 
                    st.info("No performance data available.")

        # ══════════════════════════════════════════════════════════════
        # TAB 4: MACRO & REGIONAL
        # ══════════════════════════════════════════════════════════════
        with tab_macro:
            st.header("🏛️ Macro & Regional Analysis")
            st.markdown("Deep insights into US/Sweden divergence, macroeconomic trends, and correlations.")
            st.markdown("---")
            
            macro = data.get('macro_analysis', {})
            
            # AI-REG-1 Regional Deep Dive
            rdd = macro.get('regional_deep_dive', {})
            if rdd:
                st.subheader("🇺🇸🇸🇪 US & Sweden Regional Deep-Dive")
                col_us, col_se = st.columns(2)
                with col_us: 
                    st.markdown("#### 🇺🇸 United States Outlook")
                    st.markdown(rdd.get('us_outlook', 'No data'))
                with col_se: 
                    st.markdown("#### 🇸🇪 Sweden Outlook")
                    st.markdown(rdd.get('sweden_outlook', 'No data'))
                    
                st.markdown("---")
                col_x, col_y = st.columns(2)
                with col_x: 
                    st.markdown("#### 🌉 Cross-Border Impact")
                    st.markdown(rdd.get('cross_border_impact', 'No data'))
                with col_y: 
                    st.markdown("#### ⚖️ Key Differential")
                    st.markdown(rdd.get('key_differential', 'No data'))
                st.markdown("---")

            # Raw Analysis Tabs
            tab_corr, tab_macro_raw, tab_micro = st.tabs(["🔗 Cross-Asset Correlations", "🏛️ Macroeconomic Impact", "🏢 Microeconomic Impact"])
            
            with tab_corr:
                render_ai_analysis(data.get('correlation_analysis', {}).get('raw_analysis', ""), "Correlation")
            with tab_macro_raw:
                render_ai_analysis(macro.get('raw_analysis', ""), "Macro")
            with tab_micro:
                render_ai_analysis(data.get('micro_analysis', {}).get('raw_analysis', ""), "Micro")

        # ══════════════════════════════════════════════════════════════
        # TAB 5: SECTORS
        # ══════════════════════════════════════════════════════════════
        with tab_sectors:
            st.header("🏭 Sector Analysis")
            st.markdown("Deep dive into US and Sweden sector performance and AI sentiment.")
            st.markdown("---")
            region = st.radio("Select Region", ["🇺🇸 United States", "🇸🇪 Sweden"], horizontal=True)
            data_key = 'us_sector_data' if "United States" in region else 'sweden_sector_data'
            sentiment_key = 'us_sector_sentiment' if "United States" in region else 'sweden_sector_sentiment'
            sectors = data.get(data_key, {}); sentiments = data.get(sentiment_key, {})
            
            if not sectors: 
                st.info("No sector data available for this region.")
            else:
                chart_data = [{'Sector': f"{info.get('icon', '')} {name}", 'Daily %': info.get('daily_change', 0), 'Weekly %': info.get('weekly_change', 0), 'Sentiment': sentiments.get(name, {}).get('score', 0), 'Label': sentiments.get(name, {}).get('label', 'Neutral')} for name, info in sectors.items()]
                df_sectors = pd.DataFrame(chart_data)
                st.subheader("📊 Sector Performance (Daily Change)")
                fig_sector = go.Figure()
                colors = ['#27ae60' if x > 0 else '#e74c3c' for x in df_sectors['Daily %']]
                fig_sector.add_trace(go.Bar(x=df_sectors['Daily %'], y=df_sectors['Sector'], orientation='h', marker_color=colors, text=[f"{x:+.2f}%" for x in df_sectors['Daily %']], textposition='outside', hoverinfo='text', hovertext=[f"{s['Sector']}<br>Daily: {s['Daily %']:+.2f}%<br>Weekly: {s['Weekly %']:+.2f}%<br>Sentiment: {s['Sentiment']:+d} ({s['Label']})" for s in chart_data]))
                fig_sector.update_layout(xaxis_title="Daily Change (%)", yaxis=dict(autorange='reversed', showgrid=False), xaxis=dict(showgrid=True, gridcolor='#f0f0f0'), height=max(300, len(sectors) * 40), margin=dict(l=100, r=50, t=20, b=40), plot_bgcolor='white', paper_bgcolor='white')
                st.plotly_chart(fig_sector, use_container_width=True, key=f"sector_chart_{region}")
                
                st.markdown("---")
                st.subheader("🔍 Sector Details & AI Drivers")
                cols = st.columns(2)
                for idx, (name, info) in enumerate(sectors.items()):
                    with cols[idx % 2]:
                        sent = sentiments.get(name, {}); score = sent.get('score', 0); drivers = sent.get('drivers', []); companies = info.get('key_companies', [])
                        with st.container():
                            st.markdown(f"### {info.get('icon', '')} {name}")
                            c1, c2 = st.columns(2)
                            c1.metric("Daily Change", f"{info.get('daily_change', 0):+.2f}%")
                            c2.metric("Weekly Change", f"{info.get('weekly_change', 0):+.2f}%")
                            st.markdown(f"**AI Sentiment:** <span style='color: {get_sentiment_color(score)}; font-weight: 700;'>{score:+d} ({sent.get('label', 'Neutral')})</span>", unsafe_allow_html=True)
                            if companies: st.markdown(f"**Key Companies:** {', '.join(companies[:3])}")
                            if drivers:
                                with st.expander(f"🔍 View AI Drivers for {name}"):
                                    for d in drivers: st.markdown(f"• {d}")

                            # ── Fundamental Watchlist ──
            fund = data.get('watchlist_fundamentals', [])
            if fund:
                st.markdown("---")
                st.subheader("🔍 Fundamental Watchlist (Valuation Screen)")
                df_f = pd.DataFrame([{
                    'Symbol': r.get('symbol'), 'Name': r.get('name'), 'Region': r.get('region'),
                    'Price': r.get('price'), 'P/E (T)': r.get('trailing_pe'), 'P/E (F)': r.get('forward_pe'),
                    'EPS': r.get('eps'), 'Div %': r.get('div_yield_pct'),
                    '52w Pos %': r.get('week52_position_pct'), 'Beta': r.get('beta'),
                } for r in fund])
                st.dataframe(df_f, use_container_width=True, hide_index=True)
        
        # ═══════════════════════════════════════════════════════════════
        # TAB 6: CALENDAR & NEWS
        # ═══════════════════════════════════════════════════════════════
        with tab_calendar_news:
            st.header("📅 Economic Calendar & News")
            
            # Economic Calendar
            st.subheader("📅 Upcoming Economic Events")
            economic_events = data.get('economic_events', [])
            if economic_events:
                for event in economic_events[:10]:
                    date = event.get('date', '')
                    time = event.get('time', '')
                    country = event.get('country', '')
                    impact = event.get('impact', 'MEDIUM')
                    event_name = event.get('event', 'Unknown Event')
                    description = event.get('description', '')
                    forecast = event.get('forecast', 'N/A')
                    previous = event.get('previous', 'N/A')
                    actual = event.get('actual', 'Pending')
                    
                    impact_color = '#e74c3c' if impact == 'HIGH' else '#f39c12' if impact == 'MEDIUM' else '#95a5a6'
                    
                    st.markdown(f"""
                    <div class="calendar-item" style="border-left-color: {impact_color};">
                        <div class="calendar-title">
                            {event.get('flag', '')} {event_name} 
                            <span style="background: {impact_color}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: bold; margin-left: 8px;">{impact}</span>
                        </div>
                        <div class="calendar-meta">🗓️ {date} at {time} • 🌍 {country}</div>
                        <div style="font-size: 12px; color: #555; margin: 6px 0;">{description}</div>
                        <div style="display: flex; gap: 24px; font-size: 13px; margin-top: 8px; padding-top: 8px; border-top: 1px solid #eee;">
                            <span><strong>Forecast:</strong> {forecast}</span>
                            <span><strong>Previous:</strong> {previous}</span>
                            <span><strong>Actual:</strong> <span style="color: #1976d2; font-weight: bold;">{actual}</span></span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No upcoming economic events found.")

            st.markdown("---")

            # News Explorer (UI-1 Integrated)
            st.subheader("📰 News Explorer (Last 24 Hours)")
            
            focus_options = ["All Topics", "Stocks", "Forex", "Bonds", "Crypto", "Macro", "Sweden Focus", "US Focus"]
            contextual_focus = st.selectbox("🎯 Contextual Focus", focus_options, index=0, key="focus_news")
            
            all_news = data.get('all_news', [])
            if contextual_focus != "All Topics":
                all_news = filter_news_by_focus(all_news, contextual_focus)
                
            if not all_news: 
                st.warning("No news data available for this focus.")
            else:
                col1, col2, col3 = st.columns(3)
                with col1: search_query = st.text_input("🔍 Search Headlines", placeholder="e.g., Fed, inflation...", key="news_search")
                with col2:
                    regions = sorted(list(set(n.get('region_name', 'Unknown') for n in all_news)))
                    selected_region = st.selectbox("🌍 Region", ["All"] + regions, key="news_region")
                with col3:
                    languages = sorted(list(set(n.get('original_language', 'en').upper() for n in all_news)))
                    selected_lang = st.selectbox("🗣️ Language", ["All"] + languages, key="news_lang")
                    
                def get_asset_class(title):
                    title_lower = title.lower()
                    for ac, conf in ASSET_CLASSES.items():
                        if any(kw.lower() in title_lower for kw in conf.get('keywords', [])): 
                            return f"{conf.get('icon', '')} {conf.get('name', ac)}"
                    return "🌐 Other"
                    
                df_news = pd.DataFrame([{
                    'Published': n.get('published', '')[:16], 
                    'Region': f"{n.get('region_flag', '')} {n.get('region_name', '')}", 
                    'Asset': get_asset_class(n.get('title', '')), 
                    'Title': n.get('title', ''), 
                    'Source': n.get('source', ''), 
                    'Lang': n.get('original_language', 'en').upper(), 
                    'Link': n.get('link', '#')
                } for n in all_news])
                
                if search_query: df_news = df_news[df_news['Title'].str.contains(search_query, case=False, na=False)]
                if selected_region != "All": df_news = df_news[df_news['Region'].str.contains(selected_region, case=False, na=False)]
                if selected_lang != "All": df_news = df_news[df_news['Lang'] == selected_lang]
                
                st.markdown(f"**Showing {len(df_news)} of {len(data.get('all_news', []))} Articles**")
                display_df = df_news[['Published', 'Region', 'Asset', 'Title', 'Source', 'Lang']]
                st.dataframe(display_df, use_container_width=True, hide_index=True, key="news_dataframe")
                
                csv = df_news.to_csv(index=False).encode('utf-8')
                st.download_button(label="📥 Export Filtered News to CSV", data=csv, file_name=f'finance_news_{datetime.now().strftime("%Y%m%d")}.csv', mime='text/csv', key="news_download")

        # ═══════════════════════════════════════════════════════════════
        # TAB 7: BACKTEST
        # ═══════════════════════════════════════════════════════════════
        with tab_backtest:
            st.header("🎖️ Backtesting & Accuracy")
            st.markdown("AI prediction accuracy tracking and historical performance.")
            st.markdown("---")
            backtest = data.get('backtest_stats', {})
            if backtest:
                total = backtest.get('total_evaluated', 0)
                wins = backtest.get('total_wins', 0)
                losses = total - wins
                accuracy = backtest.get('accuracy_pct', 0)
                
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Accuracy", f"{accuracy}%")
                c2.metric("Total Predictions", total)
                c3.metric("Wins", wins)
                c4.metric("Losses", losses)
                
                st.markdown("---")
                col_chart1, col_chart2 = st.columns(2)
                with col_chart1:
                    st.subheader("📊 Win/Loss Distribution")
                    if total > 0:
                        fig_pie = go.Figure(data=[go.Pie(labels=['Wins', 'Losses'], values=[wins, losses], marker_colors=['#27ae60', '#e74c3c'], hole=.4)])
                        fig_pie.update_layout(height=300, margin=dict(l=20, r=20, t=30, b=20))
                        st.plotly_chart(fig_pie, use_container_width=True, key="backtest_pie_chart")
                    else: st.info("No predictions evaluated yet.")
                with col_chart2:
                    st.subheader("🕒 Recent Predictions Timeline")
                    recent = backtest.get('recent_results', [])
                    if recent:
                        df_recent = pd.DataFrame(recent)
                        df_display = df_recent[['date', 'asset', 'ai_label', 'market_move', 'is_correct']].copy()
                        df_display['Result'] = df_display['is_correct'].apply(lambda x: '✅ Win' if x else '❌ Loss')
                        st.dataframe(df_display, use_container_width=True, hide_index=True, key="backtest_recent_table")
                    else: st.info("No recent predictions available.")
            else: 
                st.info("No backtest data available yet. Run the agent for a few days to build history.")

        # ═══════════════════════════════════════════════════════════════
        # FOOTER
        # ═══════════════════════════════════════════════════════════════
        st.markdown("---")
        st.markdown(f"""
        <div class="dashboard-footer">
            <p><strong>Finance Agent v6.0</strong> • Powered by Qwen3 (Ollama) • ChromaDB RAG • Streamlit</p>
            <p>Disclaimer: This dashboard is for informational and educational purposes only. It does not constitute financial advice.</p>
            <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    __main__()