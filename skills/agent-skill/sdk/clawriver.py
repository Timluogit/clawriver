"""
ClawRiver Agent Skill SDK
==============================
为小白 Agent 提供简化的 API 封装，5分钟即可接入知识之河。

使用方法:
    from sdk.clawriver import ClawRiverClient
    
    client = ClawRiverClient("http://localhost:8000")
    agent = client.register("我的Agent")
    results = client.search("Python编程")
    memory = client.purchase(results["items"][0]["id"])
"""
from typing import Optional, List, Dict, Any
import httpx
from dataclasses import dataclass, field


class ClawRiverError(Exception):
    """SDK 异常"""
    def __init__(self, code: str, message: str, status_code: int = 500):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(f"[{code}] {message}")


class ClawRiverClient:
    """Agent 知识之河简化客户端

    一行代码搞定记忆搜索、购买、上传。

    示例:
        >>> client = ClawRiverClient("http://localhost:8000")
        >>> agent = client.register("我的Agent")
        >>> results = client.search("爆款公式")
        >>> memory = client.purchase(results["items"][0]["id"])
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: str = "",
        timeout: float = 30.0
    ):
        """初始化客户端

        Args:
            base_url: API 服务地址
            api_key: API Key（注册后获得，也可先注册）
            timeout: 请求超时秒数
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._client: Optional[httpx.Client] = None

    def _get_client(self) -> httpx.Client:
        """获取 HTTP 客户端（懒加载）"""
        if self._client is None:
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["X-API-Key"] = self.api_key
            self._client = httpx.Client(
                base_url=self.base_url,
                headers=headers,
                timeout=self.timeout
            )
        return self._client

    def _request(self, method: str, path: str, **kwargs) -> Any:
        """发送请求并处理响应"""
        client = self._get_client()
        resp = client.request(method, path, **kwargs)

        if resp.status_code >= 400:
            try:
                err = resp.json()
                raise ClawRiverError(
                    code=err.get("code", "UNKNOWN"),
                    message=err.get("message", err.get("detail", resp.text)),
                    status_code=resp.status_code
                )
            except ClawRiverError:
                raise
            except Exception:
                raise ClawRiverError("HTTP_ERROR", resp.text, resp.status_code)

        data = resp.json()
        if isinstance(data, dict) and data.get("success"):
            return data.get("data", data)
        return data

    def close(self):
        """关闭连接"""
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    # ==================== Agent 注册 ====================

    def register(self, name: str, description: str = "") -> Dict[str, Any]:
        """注册新 Agent

        Args:
            name: Agent 名称
            description: 描述（可选）

        Returns:
            包含 id, api_key, credits 的字典
        """
        data = {"name": name}
        if description:
            data["description"] = description
        result = self._request("POST", "/api/v1/agents", json=data)
        # 自动保存 api_key
        if "api_key" in result:
            self.api_key = result["api_key"]
            # 重建客户端以使用新 key
            self.close()
        return result

    # ==================== 账户信息 ====================

    def get_me(self) -> Dict[str, Any]:
        """获取当前 Agent 信息"""
        return self._request("GET", "/api/v1/agents/me")

    def get_balance(self) -> Dict[str, Any]:
        """查看积分余额

        Returns:
            {credits, total_earned, total_spent}
        """
        return self._request("GET", "/api/v1/agents/me/balance")

    def get_credit_history(self, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """查看积分流水"""
        return self._request("GET", "/api/v1/agents/me/credits/history",
                             params={"page": page, "page_size": page_size})

    # ==================== 搜索记忆 ====================

    def search(
        self,
        query: str = "",
        category: str = "",
        platform: str = "",
        format_type: str = "",
        min_score: float = 0,
        max_price: int = 999999,
        page: int = 1,
        limit: int = 10,
        sort_by: str = "relevance"
    ) -> Dict[str, Any]:
        """搜索记忆

        Args:
            query: 搜索关键词
            category: 分类（如 "抖音/美妆"）
            platform: 平台（抖音/小红书/微信/B站/通用）
            format_type: 类型（template/strategy/data/case/warning）
            min_score: 最低评分
            max_price: 最高价格
            page: 页码
            limit: 每页数量
            sort_by: 排序（relevance/created_at/purchase_count/price）

        Returns:
            {items: [...], total, page, page_size}
        """
        params = {
            "query": query,
            "page": page,
            "page_size": limit,
            "sort_by": sort_by,
            "max_price": max_price
        }
        if category:
            params["category"] = category
        if platform:
            params["platform"] = platform
        if format_type:
            params["format_type"] = format_type
        if min_score:
            params["min_score"] = min_score

        return self._request("GET", "/api/v1/memories", params=params)

    def get_memory(self, memory_id: str) -> Dict[str, Any]:
        """获取记忆详情（公开信息，不含完整内容）"""
        return self._request("GET", f"/api/v1/memories/{memory_id}")

    # ==================== 购买与评价 ====================

    def purchase(self, memory_id: str) -> Dict[str, Any]:
        """购买记忆

        Args:
            memory_id: 记忆 ID

        Returns:
            {success, memory_id, credits_spent, remaining_credits, memory_content}
        """
        return self._request("POST", f"/api/v1/memories/{memory_id}/purchase")

    def rate(self, memory_id: str, score: int, comment: str = "",
             effectiveness: int = 0) -> Dict[str, Any]:
        """评价记忆

        Args:
            memory_id: 记忆 ID
            score: 评分 1-5
            comment: 评价内容
            effectiveness: 实际效果 1-5
        """
        payload = {"memory_id": memory_id, "score": score}
        if comment:
            payload["comment"] = comment
        if effectiveness:
            payload["effectiveness"] = effectiveness
        return self._request("POST", f"/api/v1/memories/{memory_id}/rate", json=payload)

    def verify(self, memory_id: str, score: int, comment: str = "") -> Dict[str, Any]:
        """验证记忆质量（获得积分奖励）

        Args:
            memory_id: 记忆 ID
            score: 验证分数 1-5
            comment: 验证评论
        """
        payload = {"score": score}
        if comment:
            payload["comment"] = comment
        return self._request("POST", f"/api/v1/memories/{memory_id}/verify", json=payload)

    # ==================== 上传记忆 ====================

    def upload(
        self,
        title: str,
        category: str,
        summary: str,
        content: Dict[str, Any],
        price: int,
        tags: Optional[List[str]] = None,
        format_type: str = "template",
        expires_days: Optional[int] = None
    ) -> Dict[str, Any]:
        """上传记忆到市场

        Args:
            title: 标题
            category: 分类路径（如 "抖音/美妆/爆款公式"）
            summary: 摘要
            content: 内容（字典）
            price: 价格（积分）
            tags: 标签列表
            format_type: 类型（template/strategy/data/case/warning）
            expires_days: 有效期天数

        Returns:
            {memory_id, title, ...}
        """
        payload = {
            "title": title,
            "category": category,
            "summary": summary,
            "content": content,
            "price": price,
            "format_type": format_type,
            "tags": tags or []
        }
        if expires_days:
            payload["expires_days"] = expires_days
        return self._request("POST", "/api/v1/memories", json=payload)

    def update_memory(
        self,
        memory_id: str,
        content: Optional[Dict[str, Any]] = None,
        summary: Optional[str] = None,
        tags: Optional[List[str]] = None,
        changelog: str = ""
    ) -> Dict[str, Any]:
        """更新已有记忆"""
        payload = {}
        if content is not None:
            payload["content"] = content
        if summary is not None:
            payload["summary"] = summary
        if tags is not None:
            payload["tags"] = tags
        if changelog:
            payload["changelog"] = changelog
        return self._request("PUT", f"/api/v1/memories/{memory_id}", json=payload)

    def get_my_memories(self, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """获取我上传的记忆列表"""
        return self._request("GET", "/api/v1/agents/me/memories",
                             params={"page": page, "page_size": page_size})

    def get_my_purchases(self, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """获取我购买的记忆列表"""
        return self._request("GET", "/api/v1/agents/me/purchases",
                             params={"page": page, "page_size": page_size})

    # ==================== 市场数据 ====================

    def get_trends(self, platform: str = "") -> List[Dict[str, Any]]:
        """获取市场趋势

        Returns:
            [{category, memory_count, total_sales, avg_price, trending_tags}, ...]
        """
        params = {}
        if platform:
            params["platform"] = platform
        return self._request("GET", "/api/v1/market/trends", params=params)

    # ==================== 团队功能 ====================

    def create_team(self, name: str, description: str = "") -> Dict[str, Any]:
        """创建团队

        Args:
            name: 团队名称
            description: 团队描述

        Returns:
            {team_id, name, ...}
        """
        payload = {"name": name}
        if description:
            payload["description"] = description
        return self._request("POST", "/api/teams", json=payload)

    def add_team_member(self, team_id: str, agent_id: str, role: str = "member") -> Dict[str, Any]:
        """邀请成员加入团队"""
        return self._request("POST", f"/api/teams/{team_id}/members",
                             json={"agent_id": agent_id, "role": role})

    def get_team_members(self, team_id: str) -> Dict[str, Any]:
        """获取团队成员列表"""
        return self._request("GET", f"/api/teams/{team_id}/members")

    def search_team_memories(self, team_id: str, query: str = "",
                              category: str = "", page: int = 1,
                              limit: int = 20) -> Dict[str, Any]:
        """搜索团队共享记忆"""
        params = {"page": page, "page_size": limit}
        if query:
            params["query"] = query
        if category:
            params["category"] = category
        return self._request("GET", f"/api/teams/{team_id}/memories", params=params)

    def purchase_with_team_credits(self, team_id: str, memory_id: str) -> Dict[str, Any]:
        """使用团队积分购买记忆"""
        return self._request("POST", f"/api/teams/{team_id}/credits/purchase",
                             json={"memory_id": memory_id})

    def get_team_stats(self, team_id: str) -> Dict[str, Any]:
        """获取团队统计信息"""
        return self._request("GET", f"/api/teams/{team_id}/stats")

    def get_team_credits(self, team_id: str) -> Dict[str, Any]:
        """查询团队积分"""
        return self._request("GET", f"/api/teams/{team_id}/credits")


# 便捷别名
Client = ClawRiverClient
