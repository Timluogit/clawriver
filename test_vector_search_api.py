"""测试向量搜索升级后的API功能"""
import asyncio
import httpx
import json
from typing import Dict, Any
import time


class MemoryMarketTester:
    """ClawRiver API 测试器"""

    def __init__(self, base_url: str = "http://localhost:8000/api/v1"):
        self.base_url = base_url
        self.client = httpx.Client(timeout=30.0)
        self.api_key = None

    def _print_header(self, title: str):
        """打印标题"""
        print("\n" + "=" * 60)
        print(title)
        print("=" * 60)

    def _print_result(self, test_name: str, success: bool, message: str = ""):
        """打印结果"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")
        if message:
            print(f"     {message}")

    def register_agent(self) -> Dict[str, Any]:
        """注册测试 Agent"""
        self._print_header("Register Test Agent")

        try:
            response = self.client.post(
                f"{self.base_url}/agents",
                json={
                    "name": "Search Test Agent",
                    "description": "Test agent for vector search"
                }
            )
            response.raise_for_status()
            data = response.json()

            if data.get("success"):
                agent = data.get("data", {})
                self.api_key = agent.get("api_key")
                self.client.headers["X-API-Key"] = self.api_key
                self._print_result("Register Agent", True)
                return agent
            else:
                self._print_result("Register Agent", False, data.get("message"))
                return {}

        except Exception as e:
            self._print_result("Register Agent", False, str(e))
            return {}

    def test_search_types(self, query: str):
        """测试三种搜索类型"""
        self._print_header(f"Test Search Types: '{query}'")

        search_types = ["vector", "keyword", "hybrid"]
        results = {}

        for search_type in search_types:
            try:
                start = time.time()
                response = self.client.get(
                    f"{self.base_url}/memories",
                    params={
                        "query": query,
                        "search_type": search_type,
                        "page_size": 5
                    }
                )
                elapsed = (time.time() - start) * 1000

                response.raise_for_status()
                data = response.json()

                if data.get("success"):
                    search_data = data.get("data", {})
                    results[search_type] = {
                        "items": search_data.get("items", []),
                        "total": search_data.get("total", 0),
                        "time": elapsed
                    }

                    # 显示前3个结果
                    print(f"\n{search_type.upper()} Search ({elapsed:.2f} ms):")
                    print(f"  Total: {search_data.get('total', 0)} results")

                    for idx, item in enumerate(search_data.get("items", [])[:3], 1):
                        print(f"  {idx}. [{item.get('title', 'N/A')}]")
                        print(f"     分类: {item.get('category', 'N/A')}")
                        print(f"     价格: {item.get('price', 0)} 分")
                else:
                    self._print_result(
                        f"{search_type.upper()} Search",
                        False,
                        data.get("message")
                    )

            except Exception as e:
                self._print_result(f"{search_type.upper()} Search", False, str(e))

        # 对比结果
        self._compare_results(query, results)

    def _compare_results(self, query: str, results: Dict[str, Any]):
        """对比不同搜索类型的结果"""
        print(f"\n{'=' * 60}")
        print("Search Type Comparison")
        print(f"{'=' * 60}")

        for search_type, data in results.items():
            items = data.get("items", [])
            time_ms = data.get("time", 0)
            total = data.get("total", 0)

            print(f"\n{search_type.upper()}:")
            print(f"  Results: {total}")
            print(f"  Time: {time_ms:.2f} ms")

            if items:
                titles = [item.get("title", "N/A") for item in items[:3]]
                print(f"  Top 3: {', '.join(titles)}")

    def test_filters(self):
        """测试筛选功能"""
        self._print_header("Test Filters")

        test_cases = [
            {
                "name": "Category Filter",
                "params": {"category": "抖音/爆款"},
                "expected": "Should return memories in 抖音/爆款 category"
            },
            {
                "name": "Price Filter",
                "params": {"max_price": 50},
                "expected": "Should return memories with price <= 50"
            },
            {
                "name": "Score Filter",
                "params": {"min_score": 4.0},
                "expected": "Should return memories with avg_score >= 4.0"
            },
            {
                "name": "Combined Filters",
                "params": {
                    "category": "抖音",
                    "max_price": 100,
                    "min_score": 4.0
                },
                "expected": "Should combine all filters"
            }
        ]

        for test_case in test_cases:
            try:
                response = self.client.get(
                    f"{self.base_url}/memories",
                    params={**test_case["params"], "search_type": "hybrid"}
                )
                response.raise_for_status()
                data = response.json()

                if data.get("success"):
                    search_data = data.get("data", {})
                    total = search_data.get("total", 0)

                    print(f"\n{test_case['name']}:")
                    print(f"  {test_case['expected']}")
                    print(f"  Found {total} results")

                    # 显示第一个结果
                    if search_data.get("items"):
                        item = search_data["items"][0]
                        print(f"  Example: {item.get('title', 'N/A')}")

                    self._print_result(test_case["name"], True, f"Found {total} results")
                else:
                    self._print_result(
                        test_case["name"],
                        False,
                        data.get("message")
                    )

            except Exception as e:
                self._print_result(test_case["name"], False, str(e))

    def test_performance(self):
        """测试性能"""
        self._print_header("Performance Test")

        queries = [
            "抖音爆款",
            "小红书文案",
            "直播带货",
            "视频制作"
        ]

        iterations = 5
        all_times = []

        for query in queries:
            query_times = []
            for i in range(iterations):
                try:
                    start = time.time()
                    response = self.client.get(
                        f"{self.base_url}/memories",
                        params={
                            "query": query,
                            "search_type": "hybrid",
                            "page_size": 10
                        }
                    )
                    elapsed = (time.time() - start) * 1000

                    response.raise_for_status()
                    query_times.append(elapsed)
                    all_times.append(elapsed)

                except Exception as e:
                    print(f"  Error: {e}")

            if query_times:
                avg_time = sum(query_times) / len(query_times)
                min_time = min(query_times)
                max_time = max(query_times)

                print(f"\nQuery: '{query}'")
                print(f"  Avg: {avg_time:.2f} ms")
                print(f"  Min: {min_time:.2f} ms")
                print(f"  Max: {max_time:.2f} ms")

        # 汇总
        if all_times:
            overall_avg = sum(all_times) / len(all_times)
            overall_min = min(all_times)
            overall_max = max(all_times)

            print(f"\n{'=' * 60}")
            print("Overall Performance")
            print(f"{'=' * 60}")
            print(f"Total queries: {len(all_times)}")
            print(f"Average: {overall_avg:.2f} ms")
            print(f"Min: {overall_min:.2f} ms")
            print(f"Max: {overall_max:.2f} ms")

            # 性能目标
            if overall_avg < 500:
                self._print_result("Performance Test", True, f"Avg: {overall_avg:.2f} ms (< 500ms)")
            else:
                self._print_result(
                    "Performance Test",
                    False,
                    f"Avg: {overall_avg:.2f} ms (>= 500ms)"
                )

    def test_backwards_compatibility(self):
        """测试向后兼容性"""
        self._print_header("Backwards Compatibility Test")

        test_cases = [
            {
                "name": "No search_type (default)",
                "params": {"query": "抖音爆款"},
                "expected": "Should use hybrid search by default"
            },
            {
                "name": "Old search_type: semantic",
                "params": {"query": "抖音爆款", "search_type": "semantic"},
                "expected": "Should work with old search_type"
            },
            {
                "name": "Old search_type: keyword",
                "params": {"query": "抖音爆款", "search_type": "keyword"},
                "expected": "Should work with old search_type"
            }
        ]

        for test_case in test_cases:
            try:
                response = self.client.get(
                    f"{self.base_url}/memories",
                    params=test_case["params"]
                )
                response.raise_for_status()
                data = response.json()

                if data.get("success"):
                    self._print_result(test_case["name"], True, test_case["expected"])
                else:
                    self._print_result(
                        test_case["name"],
                        False,
                        data.get("message")
                    )

            except Exception as e:
                self._print_result(test_case["name"], False, str(e))

    def run_all_tests(self):
        """运行所有测试"""
        print("\n" + "=" * 60)
        print("ClawRiver Vector Search API Test Suite")
        print("=" * 60)

        # 注册 Agent
        agent = self.register_agent()
        if not agent:
            print("Failed to register agent. Exiting.")
            return

        print(f"\nAgent ID: {agent.get('agent_id')}")
        print(f"API Key: {agent.get('api_key')}")

        # 测试搜索类型
        self.test_search_types("抖音爆款视频制作技巧")
        self.test_search_types("如何提高视频观看量")

        # 测试筛选功能
        self.test_filters()

        # 测试性能
        self.test_performance()

        # 测试向后兼容性
        self.test_backwards_compatibility()

        # 完成
        print("\n" + "=" * 60)
        print("All Tests Completed")
        print("=" * 60)


def main():
    """主函数"""
    tester = MemoryMarketTester()

    try:
        tester.run_all_tests()
    except KeyboardInterrupt:
        print("\nTests interrupted by user")
    except Exception as e:
        print(f"\nTest suite failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
