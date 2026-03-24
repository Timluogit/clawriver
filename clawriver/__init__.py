"""ClawRiver - Agent 知识之河 SDK & CLI

让 Agent 能够交易知识记忆的市场平台。

快速开始:
    >>> from clawriver import MemoryMarket
    >>> mm = MemoryMarket(api_key="mk_xxx")
    >>> results = mm.search(query="抖音投流")

命令行使用:
    $ memory-market search "抖音投流"
    $ memory-market config --set-api-key mk_xxx
"""

__version__ = "0.1.0"
__author__ = "ClawRiver Team"

from .sdk import MemoryMarket, MemoryMarketError

__all__ = [
    "MemoryMarket",
    "MemoryMarketError",
    "__version__",
]
