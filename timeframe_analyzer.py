import yfinance as yf
from datetime import datetime
import os
import json


class TimeframeAnalyzer:

    def __init__(self):
        self.cache_dir = 'data/timeframe_cache'
        os.makedirs(self.cache_dir, exist_ok=True)

        # Core benchmarks for multi-timeframe analysis
        self.benchmarks = {
            'sp500': {
                'symbol': '^GSPC',
                'name': 'S&P 500',
                'icon': '🇺🇸',
                'category': 'US Equities'
            },
            'omx_stockholm': {
                'symbol': '^OMX',
                'name': 'OMX Stockholm',
                'icon': '🇸🇪',
                'category': 'Swedish Equities'
            },
            'us10y_yield': {
                'symbol': '^TNX',
                'name': 'US 10Y Yield',
                'icon': '🏦',
                'category': 'Rates'
            },
            'gold': {
                'symbol': 'GC=F',
                'name': 'Gold',
                'icon': '🥇',
                'category': 'Safe Haven'
            },
            'bitcoin': {
                'symbol': 'BTC-USD',
                'name': 'Bitcoin',
                'icon': '₿',
                'category': 'Crypto'
            },
            'usd_sek': {
                'symbol': 'SEK=X',
                'name': 'USD/SEK',
                'icon': '💱',
                'category': 'Regional FX'
            }
        }
        
        # Timeframes to analyze
        self.timeframes = [
            {'period': '1mo', 'label': '1M', 'days': 30},
            {'period': '3mo', 'label': '3M', 'days': 90},
            {'period': '6mo', 'label': '6M', 'days': 180},
            {'period': '1y', 'label': '1Y', 'days': 365},
            {'period': '3y', 'label': '3Y', 'days': 1095},
            {'period': '5y', 'label': '5Y', 'days': 1825}
        ]

    def fetch_historical_performance(self):
        """Fetch historical performance data for all benchmarks across all timeframes"""
        print("    📈 Fetching historical performance data...")
        
        performance_data = {}
        
        for key, benchmark in self.benchmarks.items():
            symbol = benchmark['symbol']
            print(f"      • {benchmark['icon']} {benchmark['name']}...")
            
            try:
                ticker = yf.Ticker(symbol)
                
                # Fetch 5-year history (covers all timeframes)
                hist = ticker.history(period='5y')
                
                if hist.empty:
                    print(f"        ⚠️  No data for {symbol}")
                    continue
                
                current_price = hist['Close'].iloc[-1]
                timeframe_changes = {}
                
                for tf in self.timeframes:
                    period = tf['period']
                    label = tf['label']
                    
                    # Get the price from the start of this period
                    period_data = ticker.history(period=period)
                    
                    if not period_data.empty and len(period_data) > 1:
                        start_price = period_data['Close'].iloc[0]
                        change_pct = ((current_price - start_price) / start_price) * 100
                        timeframe_changes[label] = round(change_pct, 2)
                    else:
                        timeframe_changes[label] = None
                
                performance_data[key] = {
                    'name': benchmark['name'],
                    'icon': benchmark['icon'],
                    'category': benchmark['category'],
                    'current_price': round(current_price, 2),
                    'timeframes': timeframe_changes
                }
                
            except Exception as e:
                print(f"        ⚠️  Error fetching {symbol}: {e}")
                continue
        
        # Cache the data
        self._cache_performance(performance_data)
        
        print(f"    ✅ Fetched historical data for {len(performance_data)} benchmarks")
        return performance_data

    def _cache_performance(self, performance_data):
        """Cache performance data"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        cache_file = os.path.join(self.cache_dir, f'performance_{timestamp}.json')
        
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(performance_data, f, indent=2, ensure_ascii=False)

    def format_performance_summary(self, performance_data):
        """Format performance data as readable summary for AI prompts"""
        if not performance_data:
            return "No historical performance data available."
        
        summary = "MULTI-TIMEFRAME PERFORMANCE (1M, 3M, 6M, 1Y, 3Y, 5Y):\n"
        
        for key, data in performance_data.items():
            summary += f"\n{data['icon']} {data['name']} ({data['category']}):"
            summary += f"\n  Current: {data['current_price']:,.2f}"
            
            tf_summary = []
            for label in ['1M', '3M', '6M', '1Y', '3Y', '5Y']:
                change = data['timeframes'].get(label)
                if change is not None:
                    tf_summary.append(f"{label}: {change:+.2f}%")
            
            if tf_summary:
                summary += "\n  " + " | ".join(tf_summary)
        
        return summary
    