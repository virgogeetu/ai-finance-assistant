from .base import BaseAgent
from .goal_agent import GoalPlanningAgent
from .market_agent import MarketAnalysisAgent
from .news_agent import NewsSynthesizerAgent
from .portfolio_agent import PortfolioAnalysisAgent
from .qa_agent import FinanceQAAgent
from .tax_agent import TaxEducationAgent

ALL_AGENTS = [FinanceQAAgent, PortfolioAnalysisAgent, MarketAnalysisAgent,
              GoalPlanningAgent, NewsSynthesizerAgent, TaxEducationAgent]
