#!/usr/bin/env python3
"""
ClawRiver - 性能测试脚本
测试搜索延迟、并发能力、索引构建和内存使用
"""
import time
import asyncio
import tracemalloc
import statistics
import json
from typing import List, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime

# 测试配置
SMALL_DATASET = 100
MEDIUM_DATASET = 1000
LARGE_DATASET = 10000
REPEAT_100 = 100
CONCURRENT_10 = 10
CONCURRENT_50 = 50
CONCURRENT_100 = 100


@dataclass
class PerformanceResult:
    """性能测试结果"""
    test_name: str
    data_size: int
    iterations: int
    avg_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    min_ms: float
    max_ms: float
    target_ms: float
    passed: bool
    timestamp: str


class PerformanceTester:
    """性能测试器"""
    
    def __init__(self):
        self.results: List[PerformanceResult] = []
        self.start_time = time.time()
    
    def measure_latency(self, func, iterations: int = REPEAT_100) -> List[float]:
        """测量函数延迟"""
        latencies = []
        for _ in range(iterations):
            start = time.perf_counter()
            func()
            end = time.perf_counter()
            latencies.append((end - start) * 1000)  # 转换为毫秒
        return latencies
    
    def calculate_stats(self, latencies: List[float]) -> Dict[str, float]:
        """计算统计数据"""
        return {
            "avg_ms": statistics.mean(latencies),
            "p50_ms": statistics.median(latencies),
            "p95_ms": statistics.quantiles(latencies, n=20)[18],  # 95th percentile
            "p99_ms": statistics.quantiles(latencies, n=100)[98],  # 99th percentile
            "min_ms": min(latencies),
            "max_ms": max(latencies)
        }
    
    def test_vector_search_latency(self):
        """测试向量搜索延迟"""
        print("▶ 测试向量搜索延迟...")
        
        try:
            from app.search.in_memory_vector import InMemoryVectorEngine
            
            for data_size in [SMALL_DATASET, MEDIUM_DATASET, LARGE_DATASET]:
                engine = InMemoryVectorEngine()
                
                # 生成测试数据
                test_data = self._generate_test_memories(data_size)
                for mem in test_data:
                    engine.add_memory(mem["memory_id"], mem["content"], mem["metadata"])
                
                # 测量搜索延迟
                def search():
                    engine.search("test query", top_k=10)
                
                latencies = self.measure_latency(search)
                stats = self.calculate_stats(latencies)
                
                target_ms = 100
                passed = stats["p95_ms"] < target_ms
                
                result = PerformanceResult(
                    test_name="vector_search_latency",
                    data_size=data_size,
                    iterations=REPEAT_100,
                    avg_ms=stats["avg_ms"],
                    p50_ms=stats["p50_ms"],
                    p95_ms=stats["p95_ms"],
                    p99_ms=stats["p99_ms"],
                    min_ms=stats["min_ms"],
                    max_ms=stats["max_ms"],
                    target_ms=target_ms,
                    passed=passed,
                    timestamp=datetime.now().isoformat()
                )
                self.results.append(result)
                
                status = "✓" if passed else "✗"
                print(f"  {status} {data_size}条: avg={stats['avg_ms']:.2f}ms, p95={stats['p95_ms']:.2f}ms (目标<{target_ms}ms)")
        
        except ImportError as e:
            print(f"  ⚠ 跳过: {e}")
        except Exception as e:
            print(f"  ✗ 错误: {e}")
    
    def test_hybrid_search_latency(self):
        """测试混合搜索延迟"""
        print("▶ 测试混合搜索延迟...")
        
        try:
            from app.search.in_memory_hybrid import InMemoryHybridEngine
            
            for data_size in [SMALL_DATASET, MEDIUM_DATASET, LARGE_DATASET]:
                engine = InMemoryHybridEngine()
                
                # 生成测试数据
                test_data = self._generate_test_memories(data_size)
                for mem in test_data:
                    engine.add_memory(mem["memory_id"], mem["content"], mem["metadata"])
                
                # 测量搜索延迟
                def search():
                    engine.search("test query", top_k=10)
                
                latencies = self.measure_latency(search)
                stats = self.calculate_stats(latencies)
                
                target_ms = 150
                passed = stats["p95_ms"] < target_ms
                
                result = PerformanceResult(
                    test_name="hybrid_search_latency",
                    data_size=data_size,
                    iterations=REPEAT_100,
                    avg_ms=stats["avg_ms"],
                    p50_ms=stats["p50_ms"],
                    p95_ms=stats["p95_ms"],
                    p99_ms=stats["p99_ms"],
                    min_ms=stats["min_ms"],
                    max_ms=stats["max_ms"],
                    target_ms=target_ms,
                    passed=passed,
                    timestamp=datetime.now().isoformat()
                )
                self.results.append(result)
                
                status = "✓" if passed else "✗"
                print(f"  {status} {data_size}条: avg={stats['avg_ms']:.2f}ms, p95={stats['p95_ms']:.2f}ms (目标<{target_ms}ms)")
        
        except ImportError as e:
            print(f"  ⚠ 跳过: {e}")
        except Exception as e:
            print(f"  ✗ 错误: {e}")
    
    def test_concurrent_search(self):
        """测试并发搜索"""
        print("▶ 测试并发搜索...")
        
        try:
            from app.search.in_memory_vector import InMemoryVectorEngine
            
            engine = InMemoryVectorEngine()
            test_data = self._generate_test_memories(MEDIUM_DATASET)
            for mem in test_data:
                engine.add_memory(mem["memory_id"], mem["content"], mem["metadata"])
            
            async def search_task():
                start = time.perf_counter()
                engine.search("test query", top_k=10)
                return (time.perf_counter() - start) * 1000
            
            for n_concurrent in [CONCURRENT_10, CONCURRENT_50, CONCURRENT_100]:
                async def run_concurrent():
                    tasks = [search_task() for _ in range(n_concurrent)]
                    return await asyncio.gather(*tasks)
                
                latencies = asyncio.run(run_concurrent())
                stats = self.calculate_stats(latencies)
                
                target_ms = {10: 500, 50: 1000, 100: 2000}[n_concurrent]
                passed = stats["p95_ms"] < target_ms
                
                result = PerformanceResult(
                    test_name=f"concurrent_search_{n_concurrent}",
                    data_size=MEDIUM_DATASET,
                    iterations=n_concurrent,
                    avg_ms=stats["avg_ms"],
                    p50_ms=stats["p50_ms"],
                    p95_ms=stats["p95_ms"],
                    p99_ms=stats["p99_ms"],
                    min_ms=stats["min_ms"],
                    max_ms=stats["max_ms"],
                    target_ms=target_ms,
                    passed=passed,
                    timestamp=datetime.now().isoformat()
                )
                self.results.append(result)
                
                status = "✓" if passed else "✗"
                print(f"  {status} {n_concurrent}并发: avg={stats['avg_ms']:.2f}ms, p95={stats['p95_ms']:.2f}ms (目标<{target_ms}ms)")
        
        except ImportError as e:
            print(f"  ⚠ 跳过: {e}")
        except Exception as e:
            print(f"  ✗ 错误: {e}")
    
    def test_index_build_time(self):
        """测试索引构建时间"""
        print("▶ 测试索引构建时间...")
        
        try:
            from app.search.in_memory_vector import InMemoryVectorEngine
            
            for data_size in [SMALL_DATASET, MEDIUM_DATASET, LARGE_DATASET]:
                engine = InMemoryVectorEngine()
                test_data = self._generate_test_memories(data_size)
                
                start = time.perf_counter()
                for mem in test_data:
                    engine.add_memory(mem["memory_id"], mem["content"], mem["metadata"])
                build_time = (time.perf_counter() - start) * 1000
                
                target_ms = {100: 100, 1000: 1000, 10000: 10000}[data_size]
                passed = build_time < target_ms
                
                result = PerformanceResult(
                    test_name="index_build_time",
                    data_size=data_size,
                    iterations=1,
                    avg_ms=build_time,
                    p50_ms=build_time,
                    p95_ms=build_time,
                    p99_ms=build_time,
                    min_ms=build_time,
                    max_ms=build_time,
                    target_ms=target_ms,
                    passed=passed,
                    timestamp=datetime.now().isoformat()
                )
                self.results.append(result)
                
                status = "✓" if passed else "✗"
                print(f"  {status} {data_size}条: {build_time:.2f}ms (目标<{target_ms}ms)")
        
        except ImportError as e:
            print(f"  ⚠ 跳过: {e}")
        except Exception as e:
            print(f"  ✗ 错误: {e}")
    
    def test_memory_usage(self):
        """测试内存使用"""
        print("▶ 测试内存使用...")
        
        try:
            from app.search.in_memory_vector import InMemoryVectorEngine
            
            for data_size in [SMALL_DATASET, MEDIUM_DATASET, LARGE_DATASET]:
                tracemalloc.start()
                
                engine = InMemoryVectorEngine()
                test_data = self._generate_test_memories(data_size)
                for mem in test_data:
                    engine.add_memory(mem["memory_id"], mem["content"], mem["metadata"])
                
                current, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()
                
                peak_mb = peak / 1024 / 1024
                target_mb = {100: 10, 1000: 100, 10000: 500}[data_size]
                passed = peak_mb < target_mb
                
                result = PerformanceResult(
                    test_name="memory_usage",
                    data_size=data_size,
                    iterations=1,
                    avg_ms=peak_mb,
                    p50_ms=peak_mb,
                    p95_ms=peak_mb,
                    p99_ms=peak_mb,
                    min_ms=peak_mb,
                    max_ms=peak_mb,
                    target_ms=target_mb,
                    passed=passed,
                    timestamp=datetime.now().isoformat()
                )
                self.results.append(result)
                
                status = "✓" if passed else "✗"
                print(f"  {status} {data_size}条: {peak_mb:.2f}MB (目标<{target_mb}MB)")
        
        except ImportError as e:
            print(f"  ⚠ 跳过: {e}")
        except Exception as e:
            print(f"  ✗ 错误: {e}")
    
    def _generate_test_memories(self, count: int) -> List[Dict[str, Any]]:
        """生成测试记忆数据"""
        memories = []
        for i in range(count):
            memories.append({
                "memory_id": f"perf_test_{i:06d}",
                "content": f"测试记忆内容 {i} - 这是一段用于性能测试的文本内容，包含一些关键词如Python、机器学习、Docker等。",
                "metadata": {
                    "category": "测试",
                    "tags": ["测试", "性能"],
                    "price": 100,
                    "score": 4.5
                }
            })
        return memories
    
    def generate_report(self) -> str:
        """生成测试报告"""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.passed)
        failed_tests = total_tests - passed_tests
        
        report = f"""# 性能测试报告

## 执行时间
- 开始时间: {datetime.fromtimestamp(self.start_time).isoformat()}
- 结束时间: {datetime.now().isoformat()}
- 总耗时: {time.time() - self.start_time:.2f}秒

## 测试结果
- 总测试数: {total_tests}
- 通过数: {passed_tests}
- 失败数: {failed_tests}
- 通过率: {passed_tests * 100 / total_tests if total_tests > 0 else 0:.1f}%

## 详细结果

| 测试名称 | 数据量 | 平均延迟 | P95延迟 | 目标 | 状态 |
|----------|--------|----------|---------|------|------|
"""
        
        for result in self.results:
            status = "✓" if result.passed else "✗"
            report += f"| {result.test_name} | {result.data_size} | {result.avg_ms:.2f}ms | {result.p95_ms:.2f}ms | <{result.target_ms}ms | {status} |\n"
        
        report += f"""
## 总结
{'所有测试通过！' if failed_tests == 0 else f'{failed_tests}个测试失败，需要优化。'}
"""
        
        return report
    
    def save_results(self, filename: str = "performance_results.json"):
        """保存测试结果到JSON文件"""
        data = {
            "timestamp": datetime.now().isoformat(),
            "results": [asdict(r) for r in self.results]
        }
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✓ 结果已保存到 {filename}")


def main():
    """主函数"""
    print("=" * 60)
    print("  ClawRiver - 性能测试")
    print("=" * 60)
    print()
    
    tester = PerformanceTester()
    
    # 运行所有测试
    tester.test_vector_search_latency()
    tester.test_hybrid_search_latency()
    tester.test_concurrent_search()
    tester.test_index_build_time()
    tester.test_memory_usage()
    
    # 生成报告
    print()
    print("=" * 60)
    report = tester.generate_report()
    print(report)
    
    # 保存结果
    tester.save_results()
    
    # 保存报告
    with open("performance_report.md", 'w', encoding='utf-8') as f:
        f.write(report)
    print("✓ 报告已保存到 performance_report.md")


if __name__ == "__main__":
    main()
