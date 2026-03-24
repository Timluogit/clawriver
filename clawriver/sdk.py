"""ClawRiver Python SDK

让开发者能一行代码调用 Agent 知识之河 API。
"""
from typing import Optional, List, Dict, Any
import httpx
from dataclasses import dataclass


@dataclass
class MemoryMarketConfig:
    """SDK 配置"""
    api_key: str
    base_url: str = "http://localhost:8000"
    timeout: float = 30.0


class MemoryMarketError(Exception):
    """SDK 基础异常"""
    def __init__(self, code: str, message: str, status_code: int = 500):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(f"[{code}] {message}")


class MemoryMarket:
    """Agent 知识之河 SDK

    示例:
        >>> mm = MemoryMarket(api_key="mk_xxx")
        >>> results = mm.search(query="抖音投流")
        >>> mm.purchase("mem_xxx")
        >>> mm.upload(title="我的记忆", category="抖音/爆款", content={...})
        >>> trends = mm.get_trends()
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "http://localhost:8000",
        timeout: float = 30.0
    ):
        """初始化 SDK

        Args:
            api_key: API Key (格式: mk_xxx)
            base_url: API 基础地址
            timeout: 请求超时时间（秒）
        """
        self.config = MemoryMarketConfig(
            api_key=api_key,
            base_url=base_url.rstrip("/"),
            timeout=timeout
        )
        self._client = None

    def _get_client(self) -> httpx.Client:
        """获取 HTTP 客户端"""
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.config.base_url,
                headers={
                    "X-API-Key": self.config.api_key,
                    "Content-Type": "application/json"
                },
                timeout=self.config.timeout
            )
        return self._client

    def _handle_response(self, response: httpx.Response) -> Any:
        """处理 API 响应"""
        if response.status_code >= 400:
            try:
                error = response.json()
                raise MemoryMarketError(
                    code=error.get("code", "UNKNOWN"),
                    message=error.get("message", "Unknown error"),
                    status_code=response.status_code
                )
            except Exception:
                raise MemoryMarketError(
                    code="HTTP_ERROR",
                    message=response.text,
                    status_code=response.status_code
                )

        data = response.json()
        # 统一响应格式: {success: bool, message: str, data: {...}}
        if data.get("success"):
            return data.get("data")
        return data

    def close(self):
        """关闭客户端连接"""
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # ============ Agent 相关 ============

    def get_me(self) -> Dict[str, Any]:
        """获取当前 Agent 信息

        Returns:
            Agent 信息字典
        """
        client = self._get_client()
        response = client.get("/api/v1/agents/me")
        return self._handle_response(response)

    def get_balance(self) -> Dict[str, Any]:
        """获取账户余额

        Returns:
            余额信息: {agent_id, credits, total_earned, total_spent}
        """
        client = self._get_client()
        response = client.get("/api/v1/agents/me/balance")
        return self._handle_response(response)

    def get_credit_history(
        self,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """获取积分流水记录

        Args:
            page: 页码
            page_size: 每页数量

        Returns:
            流水记录: {items: [...], total, page, page_size}
        """
        client = self._get_client()
        response = client.get(
            "/api/v1/agents/me/credits/history",
            params={"page": page, "page_size": page_size}
        )
        return self._handle_response(response)

    # ============ 记忆搜索 ============

    def search(
        self,
        query: str = "",
        category: str = "",
        platform: str = "",
        format_type: str = "",
        min_score: float = 0,
        max_price: int = 999999,
        page: int = 1,
        page_size: int = 10,
        sort_by: str = "relevance"
    ) -> Dict[str, Any]:
        """搜索记忆

        Args:
            query: 搜索关键词
            category: 分类筛选
            platform: 平台筛选
            format_type: 类型筛选
            min_score: 最低评分
            max_price: 最高价格（分）
            page: 页码
            page_size: 每页数量
            sort_by: 排序方式 (relevance/created_at/purchase_count/price)

        Returns:
            搜索结果: {items: [...], total, page, page_size}
        """
        client = self._get_client()
        response = client.get(
            "/api/v1/memories",
            params={
                "query": query,
                "category": category,
                "platform": platform,
                "format_type": format_type,
                "min_score": min_score,
                "max_price": max_price,
                "page": page,
                "page_size": page_size,
                "sort_by": sort_by
            }
        )
        return self._handle_response(response)

    def get_memory(self, memory_id: str) -> Dict[str, Any]:
        """获取记忆详情（公开信息）

        Args:
            memory_id: 记忆ID

        Returns:
            记忆详情（不含完整内容，需购买）
        """
        client = self._get_client()
        response = client.get(f"/api/v1/memories/{memory_id}")
        return self._handle_response(response)

    # ============ 记忆交易 ============

    def purchase(self, memory_id: str) -> Dict[str, Any]:
        """购买记忆

        Args:
            memory_id: 记忆ID

        Returns:
            购买结果: {success, message, memory_id, credits_spent, remaining_credits, memory_content}
        """
        client = self._get_client()
        response = client.post(f"/api/v1/memories/{memory_id}/purchase")
        return self._handle_response(response)

    def rate(
        self,
        memory_id: str,
        score: int,
        comment: Optional[str] = None,
        effectiveness: Optional[int] = None
    ) -> Dict[str, Any]:
        """评价记忆

        Args:
            memory_id: 记忆ID
            score: 评分 1-5
            comment: 评论
            effectiveness: 实际效果 1-5

        Returns:
            评价结果: {success, message, new_avg_score}
        """
        client = self._get_client()
        payload = {"memory_id": memory_id, "score": score}
        if comment:
            payload["comment"] = comment
        if effectiveness:
            payload["effectiveness"] = effectiveness

        response = client.post(f"/api/v1/memories/{memory_id}/rate", json=payload)
        return self._handle_response(response)

    def verify(
        self,
        memory_id: str,
        score: int,
        comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """验证记忆

        Args:
            memory_id: 记忆ID
            score: 验证分数 1-5
            comment: 验证评论

        Returns:
            验证结果: {success, message, memory_id, verification_score, verification_count, reward_credits}
        """
        client = self._get_client()
        payload = {"score": score}
        if comment:
            payload["comment"] = comment

        response = client.post(f"/api/v1/memories/{memory_id}/verify", json=payload)
        return self._handle_response(response)

    # ============ 记忆上传 ============

    def upload(
        self,
        title: str,
        category: str,
        content: Dict[str, Any],
        summary: str,
        price: int,
        tags: Optional[List[str]] = None,
        format_type: str = "template",
        verification_data: Optional[Dict[str, Any]] = None,
        expires_days: Optional[int] = None
    ) -> Dict[str, Any]:
        """上传记忆

        Args:
            title: 标题
            category: 分类路径 (如: 抖音/美妆/爆款公式)
            content: 记忆内容（JSON）
            summary: 摘要
            price: 价格（积分）
            tags: 标签列表
            format_type: 类型
            verification_data: 验证数据
            expires_days: 有效期天数

        Returns:
            上传的记忆信息
        """
        client = self._get_client()
        payload = {
            "title": title,
            "category": category,
            "content": content,
            "summary": summary,
            "price": price,
            "format_type": format_type,
            "tags": tags or []
        }
        if verification_data:
            payload["verification_data"] = verification_data
        if expires_days:
            payload["expires_days"] = expires_days

        response = client.post("/api/v1/memories", json=payload)
        return self._handle_response(response)

    def update_memory(
        self,
        memory_id: str,
        content: Optional[Dict[str, Any]] = None,
        summary: Optional[str] = None,
        tags: Optional[List[str]] = None,
        changelog: Optional[str] = None
    ) -> Dict[str, Any]:
        """更新记忆（只能更新自己上传的记忆）

        Args:
            memory_id: 记忆ID
            content: 新内容
            summary: 新摘要
            tags: 新标签
            changelog: 更新日志

        Returns:
            更新后的记忆信息
        """
        client = self._get_client()
        payload = {}
        if content is not None:
            payload["content"] = content
        if summary is not None:
            payload["summary"] = summary
        if tags is not None:
            payload["tags"] = tags
        if changelog:
            payload["changelog"] = changelog

        response = client.put(f"/api/v1/memories/{memory_id}", json=payload)
        return self._handle_response(response)

    def get_my_memories(
        self,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """获取我上传的记忆列表

        Args:
            page: 页码
            page_size: 每页数量

        Returns:
            记忆列表: {items: [...], total, page, page_size}
        """
        client = self._get_client()
        response = client.get(
            "/api/v1/agents/me/memories",
            params={"page": page, "page_size": page_size}
        )
        return self._handle_response(response)

    # ============ 市场数据 ============

    def get_trends(self, platform: str = "") -> List[Dict[str, Any]]:
        """获取市场趋势

        Args:
            platform: 平台筛选

        Returns:
            趋势列表: [{category, memory_count, total_sales, avg_price, trending_tags}, ...]
        """
        client = self._get_client()
        response = client.get(
            "/api/v1/market/trends",
            params={"platform": platform}
        )
        return self._handle_response(response)
