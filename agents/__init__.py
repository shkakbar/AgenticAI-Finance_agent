"""
Multi-Agent Architecture for Finance Agent.
Each agent is specialized for a specific task and can run in parallel.
"""
from agents.base_agent import BaseAgent
from agents.news_agent import NewsAgent
from agents.market_agent import MarketAgent
from agents.sentiment_agent import SentimentAgent
from agents.sector_agent import SectorAgent
from agents.correlation_agent import CorrelationAgent
from agents.macro_agent import MacroAgent
from agents.micro_agent import MicroAgent
from agents.backtest_agent import BacktestAgent
from agents.report_agent import ReportAgent

all = [
 'BaseAgent',
 'NewsAgent',
 'MarketAgent',
 'SentimentAgent',
 'SectorAgent',
 'CorrelationAgent',
 'MacroAgent',
 'MicroAgent',
 'BacktestAgent',
 'ReportAgent',
]