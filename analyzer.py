import ollama
from old_config import OLLAMA_MODEL, ASSET_CLASSES
from datetime import datetime

class FinanceAnalyzer:
    def __init__(self):
        self.model = OLLAMA_MODEL
    
    def analyze_news_impact(self, news_items):
        """Analyze news and predict market impact"""
        results = {
            'stocks': [],
            'funds': [],
            'crypto': [],
            'bullion': [],
            'bonds': []
        }
        
        for news in news_items:
            analysis = self._analyze_single_news(news)
            
            # Categorize by asset class
            for asset_class, keywords in ASSET_CLASSES.items():
                if any(keyword.lower() in news['title'].lower() or 
                      keyword.lower() in news['summary'].lower() 
                      for keyword in keywords):
                    results[asset_class].append({
                        'news': news,
                        'analysis': analysis
                    })
        
        return results
    
    def _analyze_single_news(self, news):
        """Use Qwen3 to analyze a single news item"""
        prompt = f"""You are a financial analyst. Analyze the following news and predict its impact on financial markets.

News Title: {news['title']}
News Summary: {news['summary']}

Provide analysis in the following format:
1. SENTIMENT: (Bullish/Bearish/Neutral)
2. IMPACT LEVEL: (High/Medium/Low)
3. AFFECTED ASSETS: (List specific assets or sectors)
4. SHORT-TERM OUTLOOK: (1-2 sentences)
5. KEY RISKS: (1-2 potential risks)

Be concise and specific."""

        try:
            response = ollama.chat(
                model=self.model,
                messages=[{'role': 'user', 'content': prompt}]
            )
            return response['message']['content']
        except Exception as e:
            return f"Analysis error: {str(e)}"
    
    def generate_summary_report(self, analysis_results):
        """Generate a comprehensive summary report"""
        report = f"""
# Financial News Impact Analysis Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

"""
        
        for asset_class, analyses in analysis_results.items():
            if analyses:
                report += f"\n## {asset_class.upper()}\n"
                report += f"Number of relevant news items: {len(analyses)}\n\n"
                
                for i, item in enumerate(analyses[:5], 1):  # Top 5 per category
                    report += f"### {i}. {item['news']['title']}\n"
                    report += f"**Source:** {item['news']['source']}\n"
                    report += f"**Published:** {item['news']['published']}\n\n"
                    report += f"**Analysis:**\n{item['analysis']}\n\n"
                    report += "---\n\n"
        
        return report