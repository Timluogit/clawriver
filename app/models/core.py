"""核心数据库表模型 - 从 tables.py re-export，保持向后兼容"""
from app.models.tables import Agent, Memory, Purchase, Rating, Transaction, SearchLog

__all__ = [
    "Agent",
    "Memory",
    "Purchase",
    "Rating",
    "Transaction",
    "SearchLog",
]
