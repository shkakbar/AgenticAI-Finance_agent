"""
Risk Agent - Calculates quantitative risk metrics and correlation matrices.
Fetches 1-year daily historical data for the WATCHLIST + benchmarks.
"""
import numpy as np
import pandas as pd
import yfinance as yf
import config

class RiskAgent:
    # Benchmarks to include in the correlation matrix for context
    BENCHMARKS = {'^GSPC': 'S&P 500', '^OMX': 'OMX Stockholm'}
    RISK_FREE_RATE = 0.04  # Approximate current risk-free rate (e.g., US 10Y or T-Bill)

    def __init__(self, model_router=None, vector_db=None):
        self.name = 'RiskAgent'

    def log(self, msg, level='INFO'):
        prefix = {'INFO': 'ℹ️', 'SUCCESS': '✅', 'WARN': '⚠️', 'ERROR': '❌'}.get(level, 'ℹ️')
        print(f"  {prefix} [{self.name}] {msg}")

    def _fetch_prices(self, tickers):
        """Fetch 1 year of daily adjusted close prices."""
        try:
            # yfinance can fetch multiple tickers at once
            data = yf.download(tickers, period='1y', interval='1d', progress=False, threads=True)
            if 'Close' in data.columns.levels[0]:
                return data['Close'].dropna(how='all')
            elif 'Close' in data.columns:
                return data[['Close']].dropna().rename(columns={'Close': tickers[0]})
            return pd.DataFrame()
        except Exception as e:
            self.log(f"yfinance download failed: {str(e)[:80]}", 'WARN')
            return pd.DataFrame()

    def _calculate_metrics(self, prices):
        """Calculate Sharpe, Max Drawdown, and VaR for each ticker."""
        daily_returns = prices.pct_change().dropna()
        metrics = {}
        
        for ticker in prices.columns:
            ret_series = daily_returns[ticker].dropna()
            if len(ret_series) < 20:
                continue
                
            # Annualized Return and Volatility
            # GAP-06: Trailing 1Y price return — same basis as Multi-Timeframe & Watchlist tables.
            # (Old method annualized the mean daily return, overstating vs actual trailing returns.)
            # GAP-06: Trailing 1Y return via 365-calendar-day lookback —
            # identical method to the Watchlist '1y' column.
            price_series = prices[ticker].dropna()
            if len(price_series) >= 2:
                target = price_series.index[-1] - pd.Timedelta(days=365)
                past = price_series[price_series.index <= target]
                ref_price = float(past.iloc[-1]) if not past.empty else float(price_series.iloc[0])
                ann_return = float(price_series.iloc[-1]) / ref_price - 1 if ref_price > 0 else 0.0
            else:
                ann_return = 0.0
            ann_vol = ret_series.std() * np.sqrt(252)
            
            # Sharpe Ratio
            sharpe = (ann_return - self.RISK_FREE_RATE) / ann_vol if ann_vol > 0 else 0
            
            # Max Drawdown
            cum_returns = (1 + ret_series).cumprod()
            running_max = cum_returns.cummax()
            drawdown = (cum_returns - running_max) / running_max
            max_dd = drawdown.min()
            
            # Value at Risk (Historical 95%)
            var_95 = np.percentile(ret_series, 5)

            metrics[ticker] = {
                'ann_return_pct': round(ann_return * 100, 2),
                'ann_vol_pct': round(ann_vol * 100, 2),
                'sharpe_ratio': round(sharpe, 2),
                'max_drawdown_pct': round(max_dd * 100, 2),
                'var_95_pct': round(var_95 * 100, 2)
            }
        return metrics, daily_returns

    def execute(self):
        self.log("Calculating Risk Analytics (1Y daily data)...", 'INFO')
        
        # Build ticker list from WATCHLIST + Benchmarks
        watchlist = getattr(config, 'WATCHLIST', [])
        wl_tickers = [w['symbol'] for w in watchlist]
        all_tickers = list(set(wl_tickers + list(self.BENCHMARKS.keys())))
        
        prices = self._fetch_prices(all_tickers)
        if prices.empty:
            self.log("No historical price data retrieved.", 'WARN')
            return {'risk_metrics': {}, 'correlation_matrix': {}}

        metrics, daily_returns = self._calculate_metrics(prices)
        
        # Correlation Matrix (only for tickers that have data)
        valid_tickers = [t for t in all_tickers if t in daily_returns.columns]
        corr_matrix = daily_returns[valid_tickers].corr().round(2)
        
        # Convert correlation matrix to a simple dict for JSON serialization
        corr_dict = {
            row: {col: float(val) for col, val in corr_matrix.loc[row].items()} 
            for row in corr_matrix.index
        }

        # Map tickers to friendly names
        name_map = {w['symbol']: w['name'] for w in watchlist}
        name_map.update(self.BENCHMARKS)
        
        final_metrics = {}
        for ticker, m in metrics.items():
            final_metrics[ticker] = {
                'name': name_map.get(ticker, ticker),
                **m
            }

        self.log(f"Risk Analytics complete: {len(final_metrics)} tickers analyzed.", 'SUCCESS')
        return {
            'risk_metrics': final_metrics,
            'correlation_matrix': corr_dict
        }