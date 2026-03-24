"""测试 SDK 和 CLI 功能"""
import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory_market import MemoryMarket, MemoryMarketError


def test_sdk_import():
    """测试 SDK 导入"""
    print("=== 测试 SDK 导入 ===")
    try:
        from memory_market import MemoryMarket, MemoryMarketError
        print("✅ SDK 导入成功")
        print(f"  MemoryMarket: {MemoryMarket}")
        print(f"  MemoryMarketError: {MemoryMarketError}")
        return True
    except Exception as e:
        print(f"❌ SDK 导入失败: {e}")
        return False


def test_sdk_init():
    """测试 SDK 初始化"""
    print("\n=== 测试 SDK 初始化 ===")
    try:
        mm = MemoryMarket(api_key="mk_test_123")
        print("✅ SDK 初始化成功")
        print(f"  API Key: {mm.config.api_key}")
        print(f"  Base URL: {mm.config.base_url}")
        print(f"  Timeout: {mm.config.timeout}")
        mm.close()
        return True
    except Exception as e:
        print(f"❌ SDK 初始化失败: {e}")
        return False


def test_sdk_context_manager():
    """测试上下文管理器"""
    print("\n=== 测试上下文管理器 ===")
    try:
        with MemoryMarket(api_key="mk_test_123") as mm:
            print("✅ 上下文管理器工作正常")
            print(f"  API Key: {mm.config.api_key}")
        print("✅ 连接已自动关闭")
        return True
    except Exception as e:
        print(f"❌ 上下文管理器测试失败: {e}")
        return False


def test_cli_import():
    """测试 CLI 导入"""
    print("\n=== 测试 CLI 导入 ===")
    try:
        from memory_market.cli import main, CLIConfig
        print("✅ CLI 导入成功")
        print(f"  main: {main}")
        print(f"  CLIConfig: {CLIConfig}")
        return True
    except Exception as e:
        print(f"❌ CLI 导入失败: {e}")
        return False


def test_cli_config():
    """测试 CLI 配置"""
    print("\n=== 测试 CLI 配置 ===")
    try:
        from memory_market.cli import CLIConfig, CONFIG_FILE, CONFIG_DIR
        import tempfile
        import json

        # 使用临时目录测试
        temp_dir = tempfile.mkdtemp()
        temp_config_file = os.path.join(temp_dir, "test_config.json")

        # 备份原始配置
        import memory_market.cli as cli_module
        original_config_file = cli_module.CONFIG_FILE
        original_config_dir = cli_module.CONFIG_DIR

        # 修改配置文件路径
        cli_module.CONFIG_FILE = Path(temp_config_file)
        cli_module.CONFIG_DIR = Path(temp_dir)

        # 测试保存和加载
        test_config = {"api_key": "mk_test_123", "base_url": "http://test.local:8000"}
        CLIConfig.save(test_config)
        loaded = CLIConfig.load()

        if loaded == test_config:
            print("✅ 配置保存和加载成功")
            print(f"  配置内容: {json.dumps(loaded, indent=2)}")
            result = True
        else:
            print(f"❌ 配置不匹配: {loaded} != {test_config}")
            result = False

        # 清理
        cli_module.CONFIG_FILE = original_config_file
        cli_module.CONFIG_DIR = original_config_dir
        import shutil
        shutil.rmtree(temp_dir)

        return result
    except Exception as e:
        print(f"❌ CLI 配置测试失败: {e}")
        return False


def test_error_handling():
    """测试错误处理"""
    print("\n=== 测试错误处理 ===")
    try:
        # 测试异常创建
        error = MemoryMarketError(
            code="TEST_ERROR",
            message="测试错误",
            status_code=400
        )
        print("✅ 异常创建成功")
        print(f"  代码: {error.code}")
        print(f"  消息: {error.message}")
        print(f"  状态码: {error.status_code}")
        print(f"  字符串: {str(error)}")
        return True
    except Exception as e:
        print(f"❌ 错误处理测试失败: {e}")
        return False


def test_all():
    """运行所有测试"""
    print("ClawRiver SDK & CLI 测试")
    print("=" * 50)

    tests = [
        test_sdk_import,
        test_sdk_init,
        test_sdk_context_manager,
        test_cli_import,
        test_cli_config,
        test_error_handling,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"\n❌ 测试执行出错: {e}")
            results.append(False)

    # 总结
    print("\n" + "=" * 50)
    print("测试总结:")
    passed = sum(results)
    total = len(results)
    print(f"  通过: {passed}/{total}")

    if passed == total:
        print("  ✅ 所有测试通过！")
        return 0
    else:
        print(f"  ❌ {total - passed} 个测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(test_all())
