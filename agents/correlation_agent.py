"""
Correlation Agent - Analyzes cross-asset correlations.
Grounded in the real 12x12 Pearson matrix from the Risk Agent.
"""
from agents.base_agent import BaseAgent


class CorrelationAgent(BaseAgent):
    def __init__(self, model_router=None, vector_db=None):
        super().__init__('CorrelationAgent', model_router, vector_db)

    def _format_matrix_digest(self, corr_matrix):
        """Build a token-efficient digest: strongest co-movements + diversifiers."""
        if not corr_matrix:
            return "(no quantitative correlation data available)"
        tickers = list(corr_matrix.keys())
        pairs = []
        for i, t1 in enumerate(tickers):
            for t2 in tickers[i + 1:]:
                val = corr_matrix.get(t1, {}).get(t2)
                if val is not None and t1 != t2:
                    pairs.append((t1, t2, float(val)))
        if not pairs:
            return "(no quantitative correlation data available)"
        pairs.sort(key=lambda x: x[2], reverse=True)
        #lines = ["STRONGEST CO-MOVEMENTS:"]
        lines = ["TICKER CONVENTIONS: .ST = Stockholm, .OL = Oslo, .CO = Copenhagen, ^GSPC = S&P 500, ^OMX = OMX Stockholm index. Never guess a company's business beyond what the symbol and market tell you."]
        for t1, t2, v in pairs[:8]:
            lines.append(f"- {t1} <-> {t2}: {v:+.2f}")
        weakest = [p for p in pairs if p[2] < 0.25][-5:]
        if weakest:
            lines.append("WEAKEST / DIVERSIFYING:")
            for t1, t2, v in weakest:
                lines.append(f"- {t1} <-> {t2}: {v:+.2f}")
        return "\n".join(lines)

    def execute(self, news_by_asset, market_summary, correlation_matrix=None):
        if not self.validate_input({'news_by_asset': news_by_asset}):
            return None

        news_context = "\n".join([f"- {asset}: {len(articles)} articles" for asset, articles in news_by_asset.items()])
        matrix_digest = self._format_matrix_digest(correlation_matrix or {})

        system_prompt = (
            "You are a quantitative analyst specializing in cross-asset correlations. "
            "GROUNDING RULES: "
            "1. Base your analysis ONLY on the CORRELATION MATRIX provided. Every claim must cite a specific coefficient from it. "
            "2. The NEWS DISTRIBUTION is background context only. NEVER use article counts as evidence of correlation, volatility, or market movement. "
            "3. Do NOT use markdown symbols (no #, *, **, ###). Plain text only. "
            "4. No investment advice, no recommendations, and no questions to the reader. "
            "5. If no matrix data is provided, state that plainly and stop."
        )
        user_prompt = (
            f"MARKET SUMMARY:\n{market_summary}\n\n"
            f"CORRELATION MATRIX (Pearson correlation of daily returns, trailing 12 months):\n{matrix_digest}\n\n"
            f"NEWS DISTRIBUTION (background only, not evidence):\n{news_context}\n\n"
            "TASK: Write 4-6 observations about the current cross-asset correlation structure. "
            "For each, use exactly this structure:\n"
            "OBSERVATION: <one sentence citing specific coefficients>\n"
            "INTERPRETATION: <what it implies about current market structure>"
        )

        self.log("Analyzing cross-asset correlations...")
        raw_analysis = self.model_router.generate_text(prompt=user_prompt, system_prompt=system_prompt, task_type='deep')

        return {'raw_analysis': raw_analysis if raw_analysis else "No correlation analysis available."}