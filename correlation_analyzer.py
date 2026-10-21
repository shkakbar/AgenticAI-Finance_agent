import ollama
from config import OLLAMA_MODEL, ASSET_CLASSES

class CorrelationAnalyzer:
    def __init__(self, model_router=None):
        """
        Initialize with optional model router for multi-model architecture.
        If router provided, uses DEEP model (14B) for complex correlation analysis.
        Otherwise falls back to default OLLAMA_MODEL.
        """
        if model_router:
            self.model = model_router.get_model('correlation')
            self.model_router = model_router
        else:
            self.model = OLLAMA_MODEL
            self.model_router = None
        
        print(f"    🔗 CorrelationAnalyzer using model: {self.model}")

    def analyze_cross_asset_correlations(self, news_by_asset, market_summary):
        asset_summaries = []
        for asset_class, news_items in news_by_asset.items():
            if news_items:
                asset_info = ASSET_CLASSES.get(asset_class, {})
                icon = asset_info.get('icon', '•')
                name = asset_info.get('name', asset_class)
                headlines = [item['news']['title'] for item in news_items[:3]]
                summary = f"{icon} {name}:\n" + "\n".join([f"  - {h}" for h in headlines])
                asset_summaries.append(summary)

        if not asset_summaries:
            return {'raw_analysis': 'No news data available for correlation analysis.'}

        prompt = f"""You are a senior cross-asset strategist. You have access to BOTH today's news headlines AND actual real-time market data.
            REAL-TIME MARKET DATA (as of today):
                {market_summary}
                TODAY'S NEWS HEADLINES BY ASSET CLASS:
                {chr(10).join(asset_summaries)}
                Your task: Analyze how the news correlates with ACTUAL market movements. Be specific about what the data confirms or contradicts.
                Provide a CRISP analysis in plain readable text (NO JSON, NO code). Use this exact format:
                OVERALL SENTIMENT: [Risk-On / Risk-Off / Mixed]
                MARKET REALITY CHECK:
                • [Asset] is [up/down X%] today, [confirming/contradicting] the news narrative because [reason]
                • [Asset] is [up/down X%] today, [confirming/contradicting] the news narrative because [reason]
                • [Add 2-3 more data-backed observations]
                KEY CORRELATIONS:
                • [Asset A] and [Asset B] are [moving together / diverging] - [brief reason tied to news]
                • [Asset A] and [Asset B] are [moving together / diverging] - [brief reason tied to news]
                SAFE HAVEN FLOWS: [Which assets are attracting capital and actual price moves - 1-2 sentences]
                RISK ASSETS: [Which assets are seeing outflows and actual price moves - 1-2 sentences]
                BOTTOM LINE: [One powerful sentence combining news + actual market data]
                Keep total response under 300 words. Be direct, specific, and reference actual numbers."""

        try:
            if self.model_router:
                content = self.model_router.chat('correlation', prompt)
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

        