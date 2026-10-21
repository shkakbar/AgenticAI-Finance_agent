import os
from dotenv import load_dotenv

load_dotenv()
#============================================================================
#Ollama Configuration
#============================================================================
OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
#============================================================================
#Model names from .env (centralized configuration)
#============================================================================
CORE_MODEL = os.getenv('OLLAMA_MODEL')
FAST_MODEL = os.getenv('OLLAMA_FAST_MODEL')
DEEP_MODEL = os.getenv('OLLAMA_DEEP_MODEL')
FRED_API_KEY = os.getenv('FRED_API_KEY')
TRANSLATION_MODEL = os.getenv('OLLAMA_TRANSLATION_MODEL')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', CORE_MODEL) # Legacy support
FAST_MODEL = os.getenv('OLLAMA_FAST_MODEL', FAST_MODEL)
DEEP_MODEL = os.getenv('OLLAMA_DEEP_MODEL', DEEP_MODEL)
TRANSLATION_MODEL = os.getenv('OLLAMA_TRANSLATION_MODEL', TRANSLATION_MODEL)
EMBEDDING_MODEL = os.getenv('OLLAMA_EMBEDDING_MODEL', 'nomic-embed-text')

# ── Explicit model pins (override env resolution until .env loading is fixed) ──
FAST_MODEL = 'qwen2.5:7b-instruct'
DEEP_MODEL = 'qwen2.5:32b-instruct'

#============================================================================
#API Keys
#============================================================================
NEWSAPI_KEY = os.getenv('NEWSAPI_KEY')
FINNHUB_KEY = os.getenv('FINNHUB_KEY')
ALPHA_VANTAGE_KEY = os.getenv('ALPHA_VANTAGE_KEY')
#============================================================================
#Regional Focus
#============================================================================
REGIONS = {
 'US': {
 'name': 'United States',
 'flag': '🇺🇸',
 'markets': ['NYSE', 'NASDAQ'],
 'currency': 'USD',
 'central_bank': 'Federal Reserve',
 'timezone': 'America/New_York',
 'keywords': ['Fed', 'FOMC', 'US economy', 'Wall Street', 'S&P 500', 'NASDAQ', 'Dow Jones', 'Treasury']
 },
 'EU': {
 'name': 'European Union',
 'flag': '🇪🇺',
 'markets': ['Euro Stoxx', 'DAX', 'FTSE'],
 'currency': 'EUR',
 'central_bank': 'ECB',
 'timezone': 'Europe/Berlin',
 'keywords': ['ECB', 'Eurozone', 'European economy', 'DAX', 'FTSE', 'European bonds']
 },
 'JP': {
 'name': 'Japan',
 'flag': '🇯🇵',
 'markets': ['Nikkei 225', 'TOPIX'],
 'currency': 'JPY',
 'central_bank': 'BOJ',
 'timezone': 'Asia/Tokyo',
 'keywords': ['BOJ', 'Bank of Japan', 'Nikkei', 'Japanese economy', 'JGB', 'Yen']
 },
 'CN': {
 'name': 'China',
 'flag': '🇨🇳',
 'markets': ['Shanghai Composite', 'CSI 300'],
 'currency': 'CNY',
 'central_bank': 'PBOC',
 'timezone': 'Asia/Shanghai',
 'keywords': ['PBOC', 'Chinese economy', 'Shanghai', 'CSI', 'Yuan', 'Renminbi']
 },
 'Nordics': {
 'name': 'Nordic Countries',
 'flag': '🌍',
 'markets': ['OMX Stockholm', 'Oslo Stock Exchange', 'OMX Copenhagen'],
 'currencies': ['SEK', 'NOK', 'DKK'],
 'timezone': 'Europe/Stockholm',
 'keywords': ['Nordic', 'Scandinavian', 'Stockholm', 'Oslo', 'Copenhagen']
 },
 'DK': {
 'name': 'Denmark',
 'flag': '🇩🇰',
 'markets': ['OMX Copenhagen'],
 'currency': 'DKK',
 'central_bank': 'Danmarks Nationalbank',
 'timezone': 'Europe/Copenhagen',
 'keywords': ['Denmark', 'Danish', 'Danmarks Nationalbank', 'Copenhagen', 'DKK']
 },
 'SE': {
 'name': 'Sweden',
 'flag': '🇸🇪',
 'markets': ['OMX Stockholm 30'],
 'currency': 'SEK',
 'central_bank': 'Riksbank',
 'timezone': 'Europe/Stockholm',
 'keywords': ['Sweden', 'Swedish', 'Riksbank', 'Stockholm', 'SEK', 'OMX Stockholm', 'Sweden economy']
 }
}
#============================================================================
#Asset Classes
#============================================================================
ASSET_CLASSES = {
 'stocks': {
 'name': 'Stocks',
 'icon': '📈',
 'keywords': ['stock', 'equity', 'shares', 'market rally', 'market crash', 'earnings', 'S&P', 'NASDAQ', 'Nikkei'],
 'color': '#28a745'
 },
 'bonds': {
 'name': 'Bonds',
 'icon': '🏦',
 'keywords': ['bond yield', 'treasury', 'interest rate', 'federal reserve', 'debt', 'fixed income', 'JGB', 'gilts'],
 'color': '#007bff'
 },
 'volatility': {
 'name': 'Volatility',
 'icon': '📉',
 'keywords': ['vix', 'volatility', 'fear gauge', 'options', 'implied'],
 'tickers': {
 'Indices': [
 {'symbol': '^VIX', 'name': 'CBOE VIX', 'flag': '🇺🇸'},
 {'symbol': '^VXN', 'name': 'Nasdaq VIX', 'flag': '🇺🇸'}
 ]
 }
 },
 'forex': {
 'name': 'Forex',
 'icon': '💱',
 'keywords': ['forex', 'fx', 'currency', 'exchange rate', 'central bank', 'interest rate', 'fed', 'ecb', 'riksbank'],
 'tickers': {
 'Major': [
 {'symbol': 'EURUSD=X', 'name': 'EUR/USD', 'flag': '🇪🇺/🇺🇸'},
 {'symbol': 'USDJPY=X', 'name': 'USD/JPY', 'flag': '🇺🇸/🇯🇵'},
 {'symbol': 'GBPUSD=X', 'name': 'GBP/USD', 'flag': '🇬🇧/🇺🇸'},
 ],
 'Nordic & Cross': [
 {'symbol': 'EURSEK=X', 'name': 'EUR/SEK', 'flag': '🇪🇺/🇸🇪'},
 {'symbol': 'JPYSEK=X', 'name': 'JPY/SEK', 'flag': '🇯🇵/🇸🇪'},
 {'symbol': 'SEKINR=X', 'name': 'SEK/INR', 'flag': '🇸🇪/🇮🇳'},
 {'symbol': 'USDSEK=X', 'name': 'USD/SEK', 'flag': '🇺🇸/🇸🇪'},
 {'symbol': 'USDDKK=X', 'name': 'USD/DKK', 'flag': '🇺🇸/🇩🇰'},
 ]
 }
 },
 'crypto': {
 'name': 'Crypto',
 'icon': '₿',
 'keywords': ['bitcoin', 'ethereum', 'cryptocurrency', 'blockchain', 'altcoin', 'BTC', 'ETH', 'crypto', 'solana', 'chainlink', 'polkadot', 'polygon', 'shib', 'sandbox', 'vechain', 'litecoin'],
 'color': '#f7931a'
 },
 'funds': {
 'name': 'Funds',
 'icon': '💼',
 'keywords': ['mutual fund', 'ETF', 'index fund', 'hedge fund', 'fund flow', 'assets under management'],
 'color': '#6f42c1'
 },
 'bullion': {
 'name': 'Bullion',
 'icon': '🥇',
 'keywords': ['gold', 'silver', 'precious metals', 'bullion', 'safe haven'],
 'color': '#ffc107'
 }
}
#============================================================================
#Sub-classes for sentiment analysis
#============================================================================
SUB_CLASSES = {
 'stocks': {
 'US Stocks': {'icon': '🇺🇸', 'keywords': ['S&P', 'NASDAQ', 'Dow', 'Wall Street', 'US stock']},
 'EU Stocks': {'icon': '🇪🇺', 'keywords': ['Euro Stoxx', 'DAX', 'FTSE', 'European stock']},
 'Asia Stocks': {'icon': '🌏', 'keywords': ['Nikkei', 'Shanghai', 'CSI', 'Asian stock']},
 'Nordic Stocks': {'icon': '🇸🇪', 'keywords': ['OMX', 'Stockholm', 'Copenhagen', 'Nordic stock']},
 },
 'bonds': {
 'Government Bonds': {'icon': '🏛️', 'keywords': ['treasury', 'government bond', 'sovereign', 'JGB', 'bund']},
 'Yield Curve': {'icon': '📉', 'keywords': ['yield curve', '10Y', '2Y', 'T-bill', 'short-term rate']},
 },
 'forex': {
 'Major FX': {'icon': '💵', 'keywords': ['EUR/USD', 'USD/JPY', 'GBP/USD', 'dollar index', 'DXY']},
 'Nordic FX': {'icon': '🇸🇪', 'keywords': ['SEK', 'DKK', 'NOK', 'krona', 'krone']},
 'EM FX': {'icon': '🌍', 'keywords': ['CNY', 'yuan', 'renminbi', 'emerging market currency']},
 },
 'crypto': {
 'Large Cap Crypto': {'icon': '🪙', 'keywords': ['bitcoin', 'BTC', 'ethereum', 'ETH']},
 'Mid Cap Crypto': {'icon': '💎', 'keywords': ['solana', 'SOL', 'chainlink', 'LINK', 'polkadot', 'DOT', 'polygon', 'POL',  'litecoin', 'LTC', 'bitcoin cash', 'BCH', 'vechain', 'VET']},
 'Meme & Alt': {'icon': '🐕', 'keywords': ['SHIB', 'shiba', 'sandbox', 'SAND', 'meme coin', 'altcoin']},
 },
 'funds': {
 'ETFs': {'icon': '📊', 'keywords': ['ETF', 'exchange traded', 'index fund']},
 'Active Funds': {'icon': '💼', 'keywords': ['mutual fund', 'hedge fund', 'active management']},
 },
 'bullion': {
 'Gold': {'icon': '🥇', 'keywords': ['gold', 'XAU']},
 'Silver': {'icon': '🥈', 'keywords': ['silver', 'XAG']},
 },
}
#============================================================================
#Market Tickers (UPDATED: Added Volatility and Nordic Cross pairs)
#============================================================================
MARKET_TICKERS = {
 'stocks': {
 'US': [
 {'symbol': '^GSPC', 'name': 'S&P 500', 'flag': '🇺🇸'},
 {'symbol': '^IXIC', 'name': 'NASDAQ', 'flag': '🇺🇸'},
 {'symbol': '^DJI', 'name': 'Dow Jones', 'flag': '🇺🇸'},
 ],
 'EU': [
 {'symbol': '^STOXX50E', 'name': 'Euro Stoxx 50', 'flag': '🇪🇺'},
 {'symbol': '^GDAXI', 'name': 'DAX', 'flag': '🇩🇪'},
 {'symbol': '^FTSE', 'name': 'FTSE 100', 'flag': '🇬🇧'},
 ],
 'ASIA': [
 {'symbol': '^N225', 'name': 'Nikkei 225', 'flag': '🇯🇵'},
 {'symbol': '000001.SS', 'name': 'Shanghai Comp', 'flag': '🇨🇳'},
 ],
 'NORDIC': [
 {'symbol': '^OMX', 'name': 'OMX Stockholm', 'flag': '🇸🇪'},
 {'symbol': '^OMXC25', 'name': 'OMX Copenhagen', 'flag': '🇩🇰'},
 ],
 },
 'bonds': {
 'yields': [
 {'symbol': '^TNX', 'name': 'US 10Y Yield', 'flag': '🇺🇸'},
 {'symbol': '^IRX', 'name': 'US 13-Week T-Bill', 'flag': '🇺🇸'},
 ],
 },
'energy': {
 'crude': [
 {'symbol': 'BZ=F', 'name': 'Brent Crude', 'flag': '🛢️'},
 {'symbol': 'CL=F', 'name': 'WTI Crude', 'flag': '🛢️'},
 {'symbol': 'NG=F', 'name': 'Natural Gas', 'flag': '🔥'},
],
},
 'forex': {
 'major': [
 {'symbol': 'DX-Y.NYB', 'name': 'USD Index', 'flag': '💵'},
 {'symbol': 'EURUSD=X', 'name': 'EUR/USD', 'flag': '💶'},
 {'symbol': 'USDINR=X', 'name': 'USD/INR', 'flag': '🇺🇸/🇮🇳'},
 {'symbol': 'JPY=X', 'name': 'USD/JPY', 'flag': '💴'},
 {'symbol': 'GBPUSD=X', 'name': 'GBP/USD', 'flag': '💷'},
 ],
 'nordic': [
 {'symbol': 'SEK=X', 'name': 'USD/SEK', 'flag': '🇸🇪'},
 {'symbol': 'DKK=X', 'name': 'USD/DKK', 'flag': '🇩🇰'},
 {'symbol': 'NOK=X', 'name': 'USD/NOK', 'flag': '🇳🇴'},
 ],
 'nordic_cross': [
 {'symbol': 'EURSEK=X', 'name': 'EUR/SEK', 'flag': '🇪🇺/🇸🇪'},
 {'symbol': 'JPYSEK=X', 'name': 'JPY/SEK', 'flag': '🇯🇵/🇸🇪'},
 {'symbol': 'SEKINR=X', 'name': 'SEK/INR', 'flag': '🇸🇪/🇮🇳'},
 ],
 'emerging': [
 {'symbol': 'CNY=X', 'name': 'USD/CNY', 'flag': '🇨🇳'},
 ],
 },
 'crypto': {
 'large_cap': [
 {'symbol': 'BTC-USD', 'name': 'Bitcoin', 'flag': '₿'},
 {'symbol': 'ETH-USD', 'name': 'Ethereum', 'flag': 'Ξ'},
 ],
 'mid_cap': [
 {'symbol': 'SOL-USD', 'name': 'Solana', 'flag': '◎'},
 {'symbol': 'BCH-USD', 'name': 'Bitcoin Cash', 'flag': '₿'},
 {'symbol': 'LTC-USD', 'name': 'Litecoin', 'flag': 'Ł'},
 {'symbol': 'LINK-USD', 'name': 'Chainlink', 'flag': '⬡'},
 {'symbol': 'DOT-USD', 'name': 'Polkadot', 'flag': '●'},
 {'symbol': 'VET-USD', 'name': 'VeChain', 'flag': '✓'},
 ],
 'meme_alt': [
 {'symbol': 'SHIB-USD', 'name': 'Shiba Inu', 'flag': '🐕'},
 {'symbol': 'SAND-USD', 'name': 'The Sandbox', 'flag': '🏖️'},
 ],
 },
 'bullion': {
 'metals': [
 {'symbol': 'GC=F', 'name': 'Gold', 'flag': '🥇'},
 {'symbol': 'SI=F', 'name': 'Silver', 'flag': '🥈'},
 ],
 },
 'volatility': {
 'indices': [
 {'symbol': '^VIX', 'name': 'CBOE VIX', 'flag': '🇺🇸'},
 {'symbol': '^VXN', 'name': 'Nasdaq VIX', 'flag': '🇺🇸'}
 ]
 }
}
#============================================================================
#Sector Definitions
#============================================================================
SECTOR_DEFINITIONS = {
 'US': {
 'Technology': {'ticker': 'XLK', 'icon': '💻', 'key_companies': ['Apple', 'Microsoft', 'Nvidia', 'Tesla', 'Meta']},
 'Financials': {'ticker': 'XLF', 'icon': '🏦', 'key_companies': ['JPMorgan', 'Bank of America', 'Goldman Sachs']},
 'Healthcare': {'ticker': 'XLV', 'icon': '🏥', 'key_companies': ['UnitedHealth', 'Johnson & Johnson', 'Pfizer']},
 'Energy': {'ticker': 'XLE', 'icon': '⛽', 'key_companies': ['ExxonMobil', 'Chevron', 'ConocoPhillips']},
 'Consumer Disc.': {'ticker': 'XLY', 'icon': '🛍️', 'key_companies': ['Amazon', 'Tesla', 'Home Depot']},
 'Industrials': {'ticker': 'XLI', 'icon': '🏭', 'key_companies': ['Boeing', 'Caterpillar', 'Honeywell']},
 'Real Estate': {'ticker': 'XLRE', 'icon': '🏢', 'key_companies': ['Prologis', 'American Tower']},
 'Utilities': {'ticker': 'XLU', 'icon': '⚡', 'key_companies': ['NextEra Energy', 'Duke Energy']},
 'Materials': {'ticker': 'XLB', 'icon': '🧱', 'key_companies': ['Linde', 'Air Products']},
 'Communication': {'ticker': 'XLC', 'icon': '📡', 'key_companies': ['Alphabet', 'Meta', 'Netflix']},
 'Consumer Staples': {'ticker': 'XLP', 'icon': '🛒', 'key_companies': ['Procter & Gamble', 'Coca-Cola']},
 },
 'Sweden': {
 'Technology': {'tickers': ['ERIC-B.ST', 'SPOT', 'HEXA-B.ST'], 'icon': '💻', 'key_companies': ['Ericsson', 'Spotify', 'Hexagon']},
 'Financials': {'tickers': ['SEB-A.ST', 'SWED-A.ST', 'SHB-A.ST'], 'icon': '🏦', 'key_companies': ['SEB', 'Swedbank', 'Handelsbanken']},
 'Industrials': {'tickers': ['VOLV-B.ST', 'ATCO-A.ST', 'SKF-B.ST'], 'icon': '🏭', 'key_companies': ['Volvo', 'Atlas Copco', 'SKF']},
 'Healthcare': {'tickers': ['AZN.ST', 'GETI-B.ST'], 'icon': '🏥', 'key_companies': ['AstraZeneca', 'Getinge']},
 'Consumer': {'tickers': ['HM-B.ST', 'ESSITY-B.ST'], 'icon': '🛍️', 'key_companies': ['H&M', 'Essity']},
 'Materials': {'tickers': ['SSAB-A.ST', 'BOL.ST', 'SAND.ST'], 'icon': '🧱', 'key_companies': ['SSAB', 'Boliden', 'Sandvik']},
 'Investment Cos.': {'tickers': ['INVE-A.ST', 'EQT.ST', 'KINV-B.ST'], 'icon': '💼', 'key_companies': ['Investor AB', 'EQT', 'Kinnevik']},
 },
}
#============================================================================
#Sweden Key Stocks
#============================================================================
SWEDEN_KEY_STOCKS = [
 {'symbol': 'VOLV-B.ST', 'name': 'Volvo B', 'sector': 'Industrials', 'icon': '🚛'},
 {'symbol': 'ERIC-B.ST', 'name': 'Ericsson B', 'sector': 'Technology', 'icon': '📡'},
 {'symbol': 'SWED-A.ST', 'name': 'Swedbank A', 'sector': 'Financials', 'icon': '🏦'},
 {'symbol': 'HM-B.ST', 'name': 'H&M B', 'sector': 'Consumer', 'icon': '👕'},
 {'symbol': 'AZN.ST', 'name': 'AstraZeneca', 'sector': 'Healthcare', 'icon': '💊'},
 {'symbol': 'ATCO-A.ST', 'name': 'Atlas Copco A', 'sector': 'Industrials', 'icon': '🔧'},
 {'symbol': 'SKF-B.ST', 'name': 'SKF B', 'sector': 'Industrials', 'icon': '⚙️'},
 {'symbol': 'SAND.ST', 'name': 'Sandvik', 'sector': 'Materials', 'icon': '🧱'},
 {'symbol': 'INVE-B.ST', 'name': 'Investor B', 'sector': 'Financials', 'icon': '💼'},
 {'symbol': 'SEB-A.ST', 'name': 'SEB A', 'sector': 'Financials', 'icon': '🏛️'},
 {'symbol': 'HEXA-B.ST', 'name': 'Hexagon B', 'sector': 'Technology', 'icon': '📐'},
 {'symbol': 'SSAB-A.ST', 'name': 'SSAB A', 'sector': 'Materials', 'icon': '🔩'},
]
#============================================================================
#Regional News Sources
#============================================================================
REGIONAL_NEWS_SOURCES = {
 'US': [
 'https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114',
 ],
 'EU': [
 'https://www.ft.com/rss/home',
 ],
 'JP': [

 ],
 'CN': [
 'https://www.scmp.com/rss/91/feed',
 ],
 'Nordics': [
 
 ],
 'DK': [
     
 ],
 'SE': [
 'https://se.investing.com/webmaster-tools/rss',
 'https://api.news.eu.nasdaq.com/news/rss/mainMarketNotices',
 'https://api.news.eu.nasdaq.com/news/rss/firstNorthNotices',
 'https://www.riksbank.se/en-gb/rss/',
 'https://www.riksgalden.se/en/press-and-publications/publications/rss/',
 'https://www.riksgalden.se/press-och-publicerat/publikationer/statsupplaning/rss2/',
 'https://www.riksgalden.se/en/press-and-publications/press-releases-and-news/newslists/newslist-government-debt/rss/',
 'https://www.riksgalden.se/press-och-publicerat/publikationer/riktlinjer/rss/',
 'https://rss-feed-api.aws.jyllands-posten.dk/finanswatch.se/latest',
 'https://www.placera.se/artiklar/rss.xml',
 ],
}
#============================================================================
#Native Language News Sources (translated to English)
#============================================================================
NATIVE_NEWS_SOURCES = {
 'SE': {
 'language': 'sv',
 'sources': [
 {'url': 'https://www.svd.se/when/feed', 'name': 'Svenska Dagbladet'},
 {'url': 'https://www.dn.se/nyheter/feed/', 'name': 'Dagens Nyheter'},
 {'url': 'https://sverigesradio.se/sida/feed/4762', 'name': 'Sveriges Radio Ekonomi'},
 {'url': 'https://www.di.se/rss', 'name': 'Dagens Industri'},
 {'url': 'https://www.svt.se/nyheter/rss', 'name': 'SVT Nyheter'},
 ]
 },
 'DK': {
 'language': 'da',
 'sources': [
 {'url': 'https://www.dr.dk/nyheder/service/feeds/allenyheder', 'name': 'DR Nyheder'},
 {'url': 'https://borsen.dk/rss', 'name': 'Børsen'},
 {'url': 'https://www.berlingske.dk/rss', 'name': 'Berlingske'},
 {'url': 'https://www.jyllands-posten.dk/rss', 'name': 'Jyllands-Posten'},
 ]
 },
 'JP': {
 'language': 'ja',
 'sources': [
 {'url': 'https://www3.nhk.or.jp/rss/news/cat07.xml', 'name': 'NHK Keizai'},
 {'url': 'https://toyokeizai.net/rss/list/', 'name': 'Toyo Keizai'},
 {'url': 'https://www.sankei.com/rss/feeds/economy.xml', 'name': 'Sankei Keizai'},
 ]
 },
}
#============================================================================
#Scheduling Configuration
#============================================================================
SCHEDULE_TIMES = {
 'US': [
 {'time': '07:00', 'label': 'US Pre-Market'},
 {'time': '09:30', 'label': 'US Market Open'},
 {'time': '12:00', 'label': 'US Midday'},
 {'time': '16:00', 'label': 'US Market Close'},
 {'time': '18:00', 'label': 'US After-Hours'},
 ],
 'EU': [
 {'time': '07:00', 'label': 'EU Pre-Market'},
 {'time': '09:00', 'label': 'EU Market Open'},
 {'time': '12:30', 'label': 'EU Midday'},
 {'time': '17:30', 'label': 'EU Market Close'},
 ],
 'ASIA': [
 {'time': '09:00', 'label': 'Tokyo Open'},
 {'time': '15:00', 'label': 'Tokyo Close'},
 {'time': '09:30', 'label': 'Shanghai Open'},
 {'time': '15:00', 'label': 'Shanghai Close'},
 ]
}
#============================================================================
#Watchlist (NEW: For Fundamental Analysis - PE, EPS, Dividends)
#============================================================================
WATCHLIST = [
 # US Equities
 {'symbol': 'AAPL', 'name': 'Apple Inc.', 'region': 'US'},
 {'symbol': 'MSFT', 'name': 'Microsoft Corp.', 'region': 'US'},
 {'symbol': 'NVDA', 'name': 'Nvidia Corp.', 'region': 'US'},
 {'symbol': 'JPM', 'name': 'JPMorgan Chase', 'region': 'US'},
 {'symbol': 'UNH', 'name': 'UnitedHealth Group', 'region': 'US'},
 # Sweden Equities
{'symbol': 'VOLV-B.ST', 'name': 'Volvo B', 'region': 'SE'},
{'symbol': 'SEB-A.ST', 'name': 'SEB A', 'region': 'SE'},
{'symbol': 'ERIC-B.ST', 'name': 'Ericsson B', 'region': 'SE'},
{'symbol': 'HEXA-B.ST', 'name': 'Hexagon B', 'region': 'SE'},
{'symbol': 'SAND.ST', 'name': 'Sandvik', 'region': 'SE'}
]

# ── WATCHLIST 2.0: Enhanced multi-country universe ─────────────────────────
ENHANCED_WATCHLIST = [
    # ── UNITED STATES ──
    {'symbol': 'MSFT', 'name': 'Microsoft', 'country': 'US', 'currency': 'USD'},
    {'symbol': 'META', 'name': 'Meta', 'country': 'US', 'currency': 'USD'},
    {'symbol': 'AMZN', 'name': 'Amazon', 'country': 'US', 'currency': 'USD'},
    {'symbol': 'NVDA', 'name': 'Nvidia', 'country': 'US', 'currency': 'USD'},
    {'symbol': 'GOOGL', 'name': 'Alphabet', 'country': 'US', 'currency': 'USD'},
    {'symbol': 'AAPL', 'name': 'Apple', 'country': 'US', 'currency': 'USD'},
    {'symbol': 'TSM', 'name': 'TSMC', 'country': 'US', 'currency': 'USD'},
    # ── SWEDEN (Stockholm) ──
    {'symbol': 'ABB.ST', 'name': 'ABB', 'country': 'Sweden', 'currency': 'SEK'},
    {'symbol': 'ALFA.ST', 'name': 'Alfa Laval', 'country': 'Sweden', 'currency': 'SEK'},
    {'symbol': 'ASSA-B.ST', 'name': 'Assa Abloy B', 'country': 'Sweden', 'currency': 'SEK'},
    {'symbol': 'ATCO-A.ST', 'name': 'Atlas Copco A', 'country': 'Sweden', 'currency': 'SEK'},
    {'symbol': 'AZA.ST', 'name': 'Avanza Bank', 'country': 'Sweden', 'currency': 'SEK'},
    #{'symbol': 'BIOARCT-B.ST', 'name': 'BioArctic B', 'country': 'Sweden', 'currency': 'SEK'},
    {'symbol': 'BOL.ST', 'name': 'Boliden', 'country': 'Sweden', 'currency': 'SEK'},
    #{'symbol': 'BONES.ST', 'name': 'BONESUPPORT', 'country': 'Sweden', 'currency': 'SEK'},
    {'symbol': 'CAMX.ST', 'name': 'Camurus', 'country': 'Sweden', 'currency': 'SEK'},
    {'symbol': 'EPI-A.ST', 'name': 'Epiroc A', 'country': 'Sweden', 'currency': 'SEK'},
    {'symbol': 'HEXA-B.ST', 'name': 'Hexagon B', 'country': 'Sweden', 'currency': 'SEK'},
    {'symbol': 'HTRO.ST', 'name': 'Hexatronic', 'country': 'Sweden', 'currency': 'SEK'},
    {'symbol': 'HMS.ST', 'name': 'HMS Networks', 'country': 'Sweden', 'currency': 'SEK'},
    {'symbol': 'INDT.ST', 'name': 'Indutrade', 'country': 'Sweden', 'currency': 'SEK'},
    {'symbol': 'INVE-A.ST', 'name': 'Investor A', 'country': 'Sweden', 'currency': 'SEK'},
    {'symbol': 'IPCO.ST', 'name': 'Int. Petroleum', 'country': 'Norway', 'currency': 'SEK'},
    {'symbol': 'LATO-B.ST', 'name': 'Latour B', 'country': 'Sweden', 'currency': 'SEK'},
    #{'symbol': 'LEM.ST', 'name': 'Leading Edge Materials', 'country': 'Sweden', 'currency': 'SEK'},
    {'symbol': 'LIFCO-B.ST', 'name': 'Lifco B', 'country': 'Sweden', 'currency': 'SEK'},
    {'symbol': 'LUG.ST', 'name': 'Lundin Gold', 'country': 'Sweden', 'currency': 'SEK'},
    {'symbol': 'LUMI.ST', 'name': 'Lundin Mining', 'country': 'Sweden', 'currency': 'SEK'},
    #{'symbol': 'MGD.ST', 'name': 'Mangold', 'country': 'Sweden', 'currency': 'SEK'},
    #{'symbol': 'MEDCAP.ST', 'name': 'MedCap', 'country': 'Sweden', 'currency': 'SEK'},
    {'symbol': 'NCAB.ST', 'name': 'NCAB Group', 'country': 'Sweden', 'currency': 'SEK'},
    {'symbol': 'NIBE-B.ST', 'name': 'Nibe Industrier B', 'country': 'Sweden', 'currency': 'SEK'},
    #{'symbol': 'NNET.ST', 'name': 'Nordnet', 'country': 'Sweden', 'currency': 'SEK'},
    {'symbol': 'SAAB-B.ST', 'name': 'SAAB B', 'country': 'Sweden', 'currency': 'SEK'},
    {'symbol': 'SEB-A.ST', 'name': 'SEB A', 'country': 'Sweden', 'currency': 'SEK'},
    {'symbol': 'SECT-B.ST', 'name': 'Sectra B', 'country': 'Sweden', 'currency': 'SEK'},
    {'symbol': 'SWED-A.ST', 'name': 'Swedbank A', 'country': 'Sweden', 'currency': 'SEK'},
    {'symbol': 'SOBI.ST', 'name': 'Swedish Orphan Biovitrum', 'country': 'Sweden', 'currency': 'SEK'},
    {'symbol': 'UNIBAP.ST', 'name': 'Unibap Space', 'country': 'Sweden', 'currency': 'SEK'},
    {'symbol': 'VPLAY-A.ST', 'name': 'Viaplay A', 'country': 'Sweden', 'currency': 'SEK'},
    {'symbol': 'VPLAY-B.ST', 'name': 'Viaplay B', 'country': 'Sweden', 'currency': 'SEK'},
    {'symbol': 'VOLV-A.ST', 'name': 'Volvo A', 'country': 'Sweden', 'currency': 'SEK'},
    # ── NORWAY (Oslo) ──
    {'symbol': 'AKER.OL', 'name': 'Aker', 'country': 'Norway', 'currency': 'NOK'},
    {'symbol': 'AKRBP.OL', 'name': 'Aker BP', 'country': 'Norway', 'currency': 'NOK'},
    {'symbol': 'BWLPG.OL', 'name': 'BW LPG', 'country': 'Norway', 'currency': 'NOK'},
    {'symbol': 'FRO.OL', 'name': 'Frontline', 'country': 'Norway', 'currency': 'NOK'},
    {'symbol': 'KOG.OL', 'name': 'Kongsberg Gruppen', 'country': 'Norway', 'currency': 'NOK'},
    #{'symbol': 'KOGM.OL', 'name': 'Kongsberg Maritime', 'country': 'Norway', 'currency': 'NOK'},
    #{'symbol': 'TRMD-A.OL', 'name': 'TORM A', 'country': 'Norway', 'currency': 'NOK'},
    # ── DENMARK (Copenhagen) ──
    {'symbol': 'COLO-B.CO', 'name': 'Coloplast B', 'country': 'Denmark', 'currency': 'DKK'},
    {'symbol': 'DSV.CO', 'name': 'DSV', 'country': 'Denmark', 'currency': 'DKK'},
    {'symbol': 'GMAB.CO', 'name': 'Genmab', 'country': 'Denmark', 'currency': 'DKK'},
    {'symbol': 'NOVO-B.CO', 'name': 'Novo Nordisk B', 'country': 'Denmark', 'currency': 'DKK'},
    #{'symbol': 'NZYMB.CO', 'name': 'Novonesis B', 'country': 'Denmark', 'currency': 'DKK'},
    {'symbol': 'ZEAL.CO', 'name': 'Zealand Pharma', 'country': 'Denmark', 'currency': 'DKK'},
]

#============================================================================
#Logging 
#============================================================================
VERBOSE_LOGGING = os.getenv('VERBOSE_LOGGING', 'false').lower() in ('1', 'true', 'yes')