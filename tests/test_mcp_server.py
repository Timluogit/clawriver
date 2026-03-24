"""
ClawRiver MCP Server — 测试套件

覆盖：
- 协议测试：MCP 工具注册和发现
- 工具测试：参数验证、返回格式
- 集成测试：HTTP 调用链路（mock）
"""
import json
import os
import sys
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ═══════════════════════════════════════════════════════════════
#  1. 协议测试
# ═══════════════════════════════════════════════════════════════

class TestMCPServerProtocol:
    """MCP 服务器协议级别测试"""

    def test_tool_count_is_34(self):
        """验证工具总数为 34"""
        from memory_market_mcp.server import MemoryMarketMCPServer
        assert MemoryMarketMCPServer.tool_count() == 34

    def test_all_categories_present(self):
        """验证 7 个工具分类全部存在"""
        from memory_market_mcp.server import MemoryMarketMCPServer
        categories = MemoryMarketMCPServer.TOOL_CATEGORIES
        expected = {"记忆工具", "团队管理", "成员管理", "团队记忆", "团队积分", "团队活动", "团队洞察"}
        assert set(categories.keys()) == expected

    def test_category_counts(self):
        """验证每个分类的工具数量"""
        from memory_market_mcp.server import MemoryMarketMCPServer
        cats = MemoryMarketMCPServer.TOOL_CATEGORIES
        assert len(cats["记忆工具"]) == 10
        assert len(cats["团队管理"]) == 6
        assert len(cats["成员管理"]) == 5
        assert len(cats["团队记忆"]) == 6
        assert len(cats["团队积分"]) == 4
        assert len(cats["团队活动"]) == 2
        assert len(cats["团队洞察"]) == 1

    def test_list_tools_returns_34_names(self):
        """验证 list_tools 返回 34 个唯一名"""
        from memory_market_mcp.server import MemoryMarketMCPServer
        tools = MemoryMarketMCPServer.list_tools()
        assert len(tools) == 34
        assert len(set(tools)) == 34, "工具名不应重复"

    def test_fastmcp_instance_exists(self):
        """验证 FastMCP 实例已创建"""
        from memory_market_mcp.server import mcp
        assert mcp is not None
        assert mcp.name == "ClawRiver"

    def test_config_json_valid(self):
        """验证 config.json 是有效 JSON 且 total_tools=34"""
        config_path = os.path.join(os.path.dirname(__file__), "..", "memory_market_mcp", "config.json")
        with open(config_path) as f:
            config = json.load(f)
        assert config["total_tools"] == 34
        assert "tools" in config
        assert "transport" in config

    def test_config_json_tool_categories_sum(self):
        """验证 config.json 中各分类工具数之和 = 34"""
        config_path = os.path.join(os.path.dirname(__file__), "..", "memory_market_mcp", "config.json")
        with open(config_path) as f:
            config = json.load(f)
        total = sum(cat["count"] for cat in config["tools"].values())
        assert total == 34


# ═══════════════════════════════════════════════════════════════
#  2. 工具测试（mock HTTP 调用）
# ═══════════════════════════════════════════════════════════════

MOCK_SEARCH_RESULT = {
    "total": 2,
    "items": [
        {
            "title": "抖音爆款公式 v2",
            "category": "抖音/美妆",
            "price": 200,
            "avg_score": 4.5,
            "summary": "适用于美妆品类的短视频爆款公式",
            "format_type": "template",
        },
        {
            "title": "小红书种草文案模板",
            "category": "小红书/种草",
            "price": 0,
            "avg_score": 4.8,
            "summary": "高互动率种草文案模板合集",
            "format_type": "template",
        },
    ],
}

MOOK_BALANCE = {
    "credits": 5000,
    "total_earned": 12000,
    "total_spent": 7000,
}

MOCK_TEAM = {
    "team_id": "team-001",
    "name": "美妆运营组",
    "description": "专注美妆品类运营策略",
    "owner_agent_id": "agent-alice",
    "member_count": 3,
    "memory_count": 15,
    "credits": 8000,
    "is_active": True,
    "created_at": "2026-03-20T10:00:00",
}


class TestMemoryTools:
    """记忆工具测试"""

    @pytest.mark.asyncio
    async def test_search_memories_success(self):
        """搜索记忆 — 成功场景"""
        with patch("memory_market_mcp.server.api_request", new_callable=AsyncMock, return_value=MOCK_SEARCH_RESULT):
            from memory_market_mcp.server import search_memories
            result = await search_memories(query="抖音爆款", limit=5)
            assert result["success"] is True
            assert result["total"] == 2
            assert len(result["items"]) == 2
            assert "formatted" in result

    @pytest.mark.asyncio
    async def test_search_memories_with_filters(self):
        """搜索记忆 — 带筛选参数"""
        mock_fn = AsyncMock(return_value=MOCK_SEARCH_RESULT)
        with patch("memory_market_mcp.server.api_request", mock_fn):
            from memory_market_mcp.server import search_memories
            await search_memories(
                query="美妆", platform="抖音", format_type="template",
                max_price=500, category="抖音/美妆"
            )
            call_args = mock_fn.call_args
            params = call_args[1]["params"] if "params" in call_args[1] else call_args[0][2]
            assert params["platform"] == "抖音"
            assert params["format_type"] == "template"
            assert params["max_price"] == 500

    @pytest.mark.asyncio
    async def test_search_memories_error(self):
        """搜索记忆 — API 报错"""
        with patch("memory_market_mcp.server.api_request", new_callable=AsyncMock, side_effect=Exception("timeout")):
            from memory_market_mcp.server import search_memories
            result = await search_memories(query="test")
            assert result["success"] is False
            assert "timeout" in result["error"]

    @pytest.mark.asyncio
    async def test_get_balance(self):
        """查看余额"""
        with patch("memory_market_mcp.server.api_request", new_callable=AsyncMock, return_value=MOOK_BALANCE):
            from memory_market_mcp.server import get_balance
            result = await get_balance()
            assert result["success"] is True
            assert result["credits"] == 5000
            assert "💰" in result["message"]

    @pytest.mark.asyncio
    async def test_upload_memory(self):
        """上传记忆"""
        mock_resp = {"memory_id": "mem-123", "title": "测试记忆"}
        with patch("memory_market_mcp.server.api_request", new_callable=AsyncMock, return_value=mock_resp):
            from memory_market_mcp.server import upload_memory
            result = await upload_memory(
                title="测试记忆", category="测试/分类", summary="摘要",
                content={"key": "value"}, price=100
            )
            assert result["success"] is True
            assert result["memory_id"] == "mem-123"

    @pytest.mark.asyncio
    async def test_purchase_memory_success(self):
        """购买记忆 — 成功"""
        mock_resp = {"success": True, "memory_content": {"formula": "A+B=C"}}
        with patch("memory_market_mcp.server.api_request", new_callable=AsyncMock, return_value=mock_resp):
            from memory_market_mcp.server import purchase_memory
            result = await purchase_memory("mem-001")
            assert result["success"] is True
            assert "✅" in result["message"]

    @pytest.mark.asyncio
    async def test_rate_memory(self):
        """评价记忆"""
        mock_resp = {"new_avg_score": 4.3}
        with patch("memory_market_mcp.server.api_request", new_callable=AsyncMock, return_value=mock_resp):
            from memory_market_mcp.server import rate_memory
            result = await rate_memory("mem-001", score=5, comment="很好")
            assert result["success"] is True
            assert result["new_avg_score"] == 4.3

    @pytest.mark.asyncio
    async def test_verify_memory(self):
        """验证记忆"""
        mock_resp = {
            "memory_id": "mem-001", "verification_score": 4.5,
            "verification_count": 3, "reward_credits": 5,
        }
        with patch("memory_market_mcp.server.api_request", new_callable=AsyncMock, return_value=mock_resp):
            from memory_market_mcp.server import verify_memory
            result = await verify_memory("mem-001", score=4)
            assert result["success"] is True
            assert result["reward_credits"] == 5


class TestTeamTools:
    """团队工具测试"""

    @pytest.mark.asyncio
    async def test_create_team(self):
        """创建团队"""
        with patch("memory_market_mcp.server.api_request", new_callable=AsyncMock, return_value=MOCK_TEAM):
            from memory_market_mcp.server import create_team
            result = await create_team("agent-alice", "美妆运营组", "专注美妆")
            assert result["success"] is True
            assert result["team"]["team_id"] == "team-001"

    @pytest.mark.asyncio
    async def test_get_team(self):
        """获取团队详情"""
        with patch("memory_market_mcp.server.api_request", new_callable=AsyncMock, return_value=MOCK_TEAM):
            from memory_market_mcp.server import get_team
            result = await get_team("team-001")
            assert result["success"] is True
            assert result["team"]["name"] == "美妆运营组"

    @pytest.mark.asyncio
    async def test_invite_member(self):
        """生成邀请码"""
        mock_resp = {"invite_code": "INV-ABC123", "expires_at": "2026-03-30"}
        with patch("memory_market_mcp.server.api_request", new_callable=AsyncMock, return_value=mock_resp):
            from memory_market_mcp.server import invite_member
            result = await invite_member("team-001")
            assert result["success"] is True
            assert "INV-" in result["invite"]["invite_code"]

    @pytest.mark.asyncio
    async def test_add_team_credits(self):
        """添加团队积分"""
        mock_resp = {"new_balance": 9000}
        with patch("memory_market_mcp.server.api_request", new_callable=AsyncMock, return_value=mock_resp):
            from memory_market_mcp.server import add_team_credits
            result = await add_team_credits("team-001", "agent-alice", 1000)
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_transfer_credits(self):
        """转移积分"""
        mock_resp = {"from_balance": 4000, "to_balance": 6000}
        with patch("memory_market_mcp.server.api_request", new_callable=AsyncMock, return_value=mock_resp):
            from memory_market_mcp.server import transfer_credits
            result = await transfer_credits("team-001", "agent-a", "agent-b", 1000)
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_log_activity(self):
        """记录活动"""
        mock_resp = {"activity_id": "act-001"}
        with patch("memory_market_mcp.server.api_request", new_callable=AsyncMock, return_value=mock_resp):
            from memory_market_mcp.server import log_activity
            result = await log_activity("team-001", "agent-a", "memory_created", "创建了新记忆")
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_delete_team_memory(self):
        """删除团队记忆"""
        with patch("memory_market_mcp.server.api_request", new_callable=AsyncMock, return_value={}):
            from memory_market_mcp.server import delete_team_memory
            result = await delete_team_memory("team-001", "mem-999", "agent-a")
            assert result["success"] is True
            assert "已删除" in result["message"]


# ═══════════════════════════════════════════════════════════════
#  3. 集成测试
# ═══════════════════════════════════════════════════════════════

class TestFormatting:
    """格式化函数测试"""

    def test_fmt_search_empty(self):
        from memory_market_mcp.server import fmt_search
        result = fmt_search({"items": [], "total": 0})
        assert "未找到" in result

    def test_fmt_search_with_items(self):
        from memory_market_mcp.server import fmt_search
        result = fmt_search(MOCK_SEARCH_RESULT)
        assert "2 条记忆" in result
        assert "抖音爆款公式" in result

    def test_fmt_content_empty(self):
        from memory_market_mcp.server import fmt_content
        assert fmt_content({}) == "(无内容)"

    def test_fmt_content_nested(self):
        from memory_market_mcp.server import fmt_content
        content = {"策略": {"步骤1": "分析", "步骤2": "执行"}, "备注": "仅供参考"}
        result = fmt_content(content)
        assert "【策略】" in result
        assert "步骤1: 分析" in result
        assert "备注: 仅供参考" in result

    def test_fmt_trends_empty(self):
        from memory_market_mcp.server import fmt_trends
        assert "暂无" in fmt_trends([])

    def test_fmt_trends_with_data(self):
        from memory_market_mcp.server import fmt_trends
        data = [{"category": "抖音/美妆", "memory_count": 120, "total_sales": 450, "avg_price": 250}]
        result = fmt_trends(data)
        assert "抖音/美妆" in result
        assert "120条" in result

    def test_fmt_my_memories_empty(self):
        from memory_market_mcp.server import fmt_my_memories
        assert "还没有上传" in fmt_my_memories({"items": [], "total": 0, "stats": {}})


class TestMCPServerWrapper:
    """MemoryMarketMCPServer 包装类测试"""

    def test_run_stdio(self):
        """测试 stdio 启动（mock mcp.run）"""
        from memory_market_mcp.server import MemoryMarketMCPServer, mcp
        with patch.object(mcp, "run") as mock_run:
            MemoryMarketMCPServer.run(transport="stdio")
            mock_run.assert_called_once()

    def test_run_sse(self):
        """测试 SSE 启动"""
        from memory_market_mcp.server import MemoryMarketMCPServer, mcp
        with patch.object(mcp, "run") as mock_run:
            MemoryMarketMCPServer.run(transport="sse", host="127.0.0.1", port=9999)
            mock_run.assert_called_once_with(transport="sse", host="127.0.0.1", port=9999)


class TestAPIRequest:
    """HTTP 客户端测试"""

    @pytest.mark.asyncio
    async def test_api_request_get(self):
        """GET 请求"""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"ok": True}
        mock_resp.raise_for_status = MagicMock()

        with patch("memory_market_mcp.server.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.request = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            from memory_market_mcp.server import api_request
            result = await api_request("GET", "/test")
            assert result == {"ok": True}

    @pytest.mark.asyncio
    async def test_api_request_post(self):
        """POST 请求"""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"created": True}
        mock_resp.raise_for_status = MagicMock()

        with patch("memory_market_mcp.server.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.request = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            from memory_market_mcp.server import api_request
            result = await api_request("POST", "/test", data={"key": "val"})
            assert result == {"created": True}


class TestEnvironmentConfig:
    """环境变量配置测试"""

    def test_default_api_base(self):
        from memory_market_mcp.server import _get_api_base
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("MEMORY_MARKET_API_URL", None)
            assert "localhost:8000" in _get_api_base()

    def test_custom_api_base(self):
        from memory_market_mcp.server import _get_api_base
        with patch.dict(os.environ, {"MEMORY_MARKET_API_URL": "http://prod:8000/api/v1"}):
            assert _get_api_base() == "http://prod:8000/api/v1"

    def test_api_key_from_env(self):
        from memory_market_mcp.server import _get_api_key
        with patch.dict(os.environ, {"MEMORY_MARKET_API_KEY": "sk-test-123"}):
            assert _get_api_key() == "sk-test-123"
