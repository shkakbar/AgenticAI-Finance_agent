import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from config import MARKET_TICKERS
import json
import os

class MarketDataFetcher:
    def __init__(self):
        self.cache_dir = 'data/market_cache'
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def fetch_ticker_data(self, symbol, name, flag, region=None):
        """Fetch price data for a single ticker"""
        try:
            ticker = yf.Ticker(symbol)
            
            # Get 5-day history to calculate daily and weekly changes
            hist = ticker.history(period='5d')
            
            if hist.empty or len(hist) < 1:
                return None
            
            current_price = hist['Close'].iloc[-1]
            
            # Daily change (vs previous close)
            daily_change = 0
            if len(hist) >= 2:
                prev_close = hist['Close'].iloc[-2]
                daily_change = ((current_price - prev_close) / prev_close) * 100
            
            # Weekly change (vs 5 days ago)
            weekly_change = 0
            if len(hist) >= 5:
                week_ago_close = hist['Close'].iloc[0]
                weekly_change = ((current_price - week_ago_close) / week_ago_close) * 100
            
            return {
                'symbol': symbol,
                'name': name,
                'flag': flag,
                'region': region,
                'price': round(current_price, 2),
                'daily_change': round(daily_change, 2),
                'weekly_change': round(weekly_change, 2),
                'daily_direction': 'up' if daily_change > 0 else 'down' if daily_change < 0 else 'flat',
                'weekly_direction': 'up' if weekly_change > 0 else 'down' if weekly_change < 0 else 'flat',
                'timestamp': datetime.now().isoformat(),
            }
        except Exception as e:
            print(f"    ⚠️  Error fetching {symbol}: {e}")
            return None
    
    def fetch_all_market_data(self):
        """Fetch market data for all tracked tickers"""
        market_data = {
            'stocks': {'US': [], 'EU': [], 'ASIA': [], 'NORDIC': []},
            'bonds': {'yields': []},
            'forex': {group: [] for group in MARKET_TICKERS['forex']},
            'crypto': {group: [] for group in MARKET_TICKERS['crypto']},
            'bullion': {'metals': []},
        }
        
        print("📊 Fetching real-time market data...")
        
        # Stocks
        for region, tickers in MARKET_TICKERS['stocks'].items():
            print(f"  📈 Fetching {region} stocks...")
            for t in tickers:
                data = self.fetch_ticker_data(t['symbol'], t['name'], t['flag'], region)
                if data:
                    market_data['stocks'][region].append(data)
        
        # Bonds
        print("  🏦 Fetching bond yields...")
        for t in MARKET_TICKERS['bonds']['yields']:
            data = self.fetch_ticker_data(t['symbol'], t['name'], t['flag'])
            if data:
                market_data['bonds']['yields'].append(data)
        
        # Forex
        for group, tickers in MARKET_TICKERS['forex'].items():
            print(f"  💱 Fetching {group} forex...")
            for t in tickers:
                data = self.fetch_ticker_data(t['symbol'], t['name'], t['flag'])
                if data:
                    market_data['forex'][group].append(data)
        
        # Crypto
        print("  ₿ Fetching crypto...")
        for group, tickers in MARKET_TICKERS['crypto'].items():
            print(f"    • {group}...")
            for t in tickers:
                data = self.fetch_ticker_data(t['symbol'], t['name'], t['flag'])
                if data:
                    market_data['crypto'][group].append(data)
        
        # Bullion
        print("  🥇 Fetching precious metals...")
        for t in MARKET_TICKERS['bullion']['metals']:
            data = self.fetch_ticker_data(t['symbol'], t['name'], t['flag'])
            if data:
                market_data['bullion']['metals'].append(data)
        
        # Cache the data
        self._cache_market_data(market_data)
        
        return market_data
    
    def _cache_market_data(self, market_data):
        """Cache market data for reference"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        cache_file = os.path.join(self.cache_dir, f'market_{timestamp}.json')
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(market_data, f, indent=2, ensure_ascii=False)
    
    def format_market_summary(self, market_data):
        """Format market data as a readable summary for AI prompts"""
        summary_parts = []
        
        # Stocks
        for region, tickers in market_data['stocks'].items():
            if tickers:
                lines = [f"{t['flag']} {t['name']}: {t['price']:,.2f} ({t['daily_change']:+.2f}% today, {t['weekly_change']:+.2f}% week)" for t in tickers]
                summary_parts.append(f"STOCKS ({region}):\n" + "\n".join(lines))
        
        # Bonds
        if market_data['bonds']['yields']:
            lines = [f"{t['flag']} {t['name']}: {t['price']:.2f}% ({t['daily_change']:+.2f}bps)" for t in market_data['bonds']['yields']]
            summary_parts.append("BONDS:\n" + "\n".join(lines))
        
        # Forex
        for group, tickers in market_data['forex'].items():
            if tickers:
                lines = [f"{t['flag']} {t['name']}: {t['price']:.4f} ({t['daily_change']:+.2f}% today)" for t in tickers]
                summary_parts.append(f"FOREX ({group.upper()}):\n" + "\n".join(lines))
        
        # Crypto
        for group, tickers in market_data['crypto'].items():
            if tickers:
                lines = [f"{t['flag']} {t['name']}: ${t['price']:,.2f} ({t['daily_change']:+.2f}% today, {t['weekly_change']:+.2f}% week)" for t in tickers]
                summary_parts.append(f"CRYPTO ({group.upper()}):\n" + "\n".join(lines))
        
        # Bullion
        if market_data['bullion']['metals']:
            lines = [f"{t['flag']} {t['name']}: ${t['price']:,.2f} ({t['daily_change']:+.2f}% today, {t['weekly_change']:+.2f}% week)" for t in market_data['bullion']['metals']]
            summary_parts.append("BULLION:\n" + "\n".join(lines))
        
        return "\n\n".join(summary_parts)