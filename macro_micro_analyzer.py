import ollama
from config import OLLAMA_MODEL


class MacroMicroAnalyzer:
    def __init__(self, model_router=None):
        """
        Initialize with optional model router for multi-model architecture.
        If router provided, uses DEEP model (14B) for complex macro/micro analysis.
        Otherwise falls back to default OLLAMA_MODEL.
        """
        if model_router:
            self.model = model_router.get_model('macro')
            self.model_router = model_router
        else:
            self.model = OLLAMA_MODEL
            self.model_router = None

        print(f"    🏛️  MacroMicroAnalyzer using model: {self.model}")

    def analyze_macro_impact(self, news_items, market_summary):
        """Analyze macroeconomic impact using news + real market data"""

        macro_keywords = [
            'fed', 'ecb', 'boj', 'pboc', 'riksbank', 'danmarks nationalbank',
            'interest rate', 'inflation', 'gdp', 'employment', 'unemployment',
            'cpi', 'ppi', 'central bank', 'monetary policy', 'fiscal policy',
            'treasury', 'bond yield', 'geopolitical'
        ]

        macro_news = [
            news for news in news_items
            if any(keyword in news['title'].lower() or keyword in news['summary'].lower()
                for keyword in macro_keywords)
        ]

        if not macro_news:
            return {'raw_analysis': 'No significant macroeconomic news identified in the current cycle.'}

        headlines = '\n'.join([
            f"• {n['title']} ({n.get('region_flag', '')} {n['region_name']})"
            for n in macro_news[:10]
        ])

        prompt = f"""You are a chief macroeconomist. You have access to BOTH macroeconomic news AND actual market data.
            REAL-TIME MARKET DATA:
            {market_summary}
            MACROECONOMIC NEWS HEADLINES:
            {headlines}
            Your task: Analyze the macro picture using BOTH news and actual market data. Reference specific numbers.
            Provide a CRISP analysis in plain readable text (NO JSON, NO code, NO markdown headers). Use this exact format:
            MACRO OUTLOOK: [Bullish / Bearish / Neutral / Mixed]
            MARKET SIGNALS (what the data says):
            • US 10Y Yield at [X%] ([up/down] [Y]bps) signals [interpretation]
            • USD Index at [X] ([up/down] [Y]%) signals [interpretation]
            • [Add 2-3 more data-backed observations]
            KEY DRIVERS (what the news says):
            • [Driver 1 with brief impact explanation]
            • [Driver 2 with brief impact explanation]
            • [Driver 3 with brief impact explanation]
            NEWS vs DATA ALIGNMENT:
            [1-2 sentences on whether news narrative matches actual market moves]
            REGIONAL FOCUS:
            • 🇺🇸 US: [1 sentence with data reference]
            • 🇪🇺 EU: [1 sentence with data reference]
            • 🇩🇰🇸🇪 Nordics: [1 sentence with SEK/DKK data reference]
            • 🇯🇵🇨🇳 Asia: [1 sentence with JPY/CNY data reference]
            BOTTOM LINE: [One powerful sentence combining news + market data]
            Keep total response under 350 words. Be direct, specific, and reference actual numbers."""

        try:
            if self.model_router:
                content = self.model_router.chat('macro', prompt)
                if content is None:
                    return {'raw_analysis': 'Analysis failed - model returned no response.'}
            else:
                response = ollama.chat(
                    model=self.model,
                    messages=[{'role': 'user', 'content': prompt}]
                )
                content = response['message']['content']

            return {'raw_analysis': content}
        except Exception as e:
            return {'raw_analysis': f'Analysis error: {str(e)}'}

    def analyze_micro_impact(self, news_items, market_summary):
        """Analyze microeconomic impact using news + real market data"""

        micro_keywords = [
            'earnings', 'revenue', 'profit', 'loss', 'acquisition', 'merger',
            'ipo', 'layoff', 'ceo', 'company', 'stock price', 'target',
            'upgrade', 'downgrade', 'sector', 'industry', 'novo nordisk',
            'ericsson', 'volvo', 'maersk', 'toyota', 'samsung', 'novo'
        ]

        micro_news = [
            news for news in news_items
            if any(keyword in news['title'].lower() or keyword in news['summary'].lower()
                for keyword in micro_keywords)
        ]

        if not micro_news:
            return {'raw_analysis': 'No significant company or sector-specific news identified.'}

        headlines = '\n'.join([
            f"• {n['title']} ({n.get('region_flag', '')} {n['region_name']})"
            for n in micro_news[:10]
        ])

        prompt = f"""You are a senior equity analyst. You have access to BOTH company/sector news AND actual market data.
            REAL-TIME MARKET DATA:
            {market_summary}
            COMPANY & SECTOR NEWS:
            {headlines}
            Your task: Analyze microeconomic impact using BOTH news and actual equity market data.
            Provide a CRISP analysis in plain readable text (NO JSON, NO code). Use this exact format:
            SECTOR SENTIMENT: [Bullish / Bearish / Mixed]
            EQUITY MARKET REALITY:
            • [Region] indices are [up/down X%] - [what this means for sectors]
            • [Add 2-3 more data-backed observations about equity markets]
            TOP SECTORS:
            • [Sector]: [Sentiment] - [Brief reason and key companies, with data reference]
            • [Sector]: [Sentiment] - [Brief reason and key companies, with data reference]
            • [Sector]: [Sentiment] - [Brief reason and key companies, with data reference]
            COMPANY SPOTLIGHT:
            • [Company]: [Impact] - [One-line reason with data reference if available]
            • [Company]: [Impact] - [One-line reason]
            • [Company]: [Impact] - [One-line reason]
            NEWS vs MARKET ALIGNMENT:
            [1-2 sentences on whether company news is reflected in actual stock moves]
            BOTTOM LINE: [One powerful sentence combining news + market data]
            Keep total response under 350 words. Be direct and actionable."""

        try:
            if self.model_router:
                content = self.model_router.chat('micro', prompt)
                if content is None:
                    return {'raw_analysis': 'Analysis failed - model returned no response.'}
            else:
                response = ollama.chat(
                    model=self.model,
                    messages=[{'role': 'user', 'content': prompt}]
                )
                content = response['message']['content']

            return {'raw_analysis': content}
        except Exception as e:
            return {'raw_analysis': f'Analysis error: {str(e)}'}

        