#!/usr/bin/env python3
"""
验证脚本 - 检查代码规范、文档完整性和测试覆盖率

Usage:
    python scripts/validate.py
"""
import os
import sys
import subprocess
from pathlib import Path
from typing import List, Tuple


class Colors:
    """ANSI颜色代码"""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """打印标题"""
    print(f"\n{Colors.BLUE}{Colors.BOLD}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BLUE}{Colors.BOLD}{text}{Colors.RESET}")
    print(f"{Colors.BLUE}{Colors.BOLD}{'=' * 60}{Colors.RESET}\n")


def print_success(text: str):
    """打印成功消息"""
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")


def print_warning(text: str):
    """打印警告消息"""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")


def print_error(text: str):
    """打印错误消息"""
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")


def run_command(cmd: List[str], description: str) -> Tuple[bool, str]:
    """运行命令并返回结果"""
    print(f"Running: {' '.join(cmd)}...")
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )
        success = result.returncode == 0
        return success, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)


def check_code_format() -> bool:
    """检查代码格式（Black）"""
    print_header("检查代码格式 (Black)")

    cmd = [
        sys.executable, "-m", "black",
        "--check",
        "--line-length=100",
        "app/", "tests/"
    ]

    success, output = run_command(cmd, "Black code format check")

    if success:
        print_success("代码格式检查通过")
        return True
    else:
        print_error("代码格式检查失败")
        print("\n输出:")
        print(output)
        return False


def check_linting() -> bool:
    """运行 Ruff linter"""
    print_header("运行 Linter (Ruff)")

    cmd = [sys.executable, "-m", "ruff", "check", "app/", "tests/"]

    success, output = run_command(cmd, "Ruff linter")

    if success:
        print_success("Linting 检查通过")
        return True
    else:
        print_error("Linting 检查失败")
        print("\n输出:")
        print(output)
        return False


def check_type_hints() -> bool:
    """检查类型提示（mypy）"""
    print_header("检查类型提示 (mypy)")

    cmd = [
        sys.executable, "-m", "mypy",
        "app/",
        "--ignore-missing-imports",
        "--no-strict-optional"
    ]

    success, output = run_command(cmd, "mypy type check")

    # mypy 只警告，不阻塞
    if success:
        print_success("类型检查通过")
        return True
    else:
        print_warning("类型检查发现问题（非阻塞）")
        print("\n输出:")
        print(output)
        return True  # 不阻塞 CI


def check_test_coverage() -> bool:
    """检查测试覆盖率"""
    print_header("检查测试覆盖率")

    if not os.path.exists("tests/"):
        print_warning("tests/ 目录不存在，跳过测试覆盖率检查")
        return True

    cmd = [
        sys.executable, "-m", "pytest",
        "tests/",
        "--cov=app",
        "--cov-report=term-missing",
        "--cov-report=xml",
        "-v"
    ]

    success, output = run_command(cmd, "pytest coverage")

    if success:
        # 解析输出获取覆盖率
        lines = output.split('\n')
        for line in lines:
            if 'TOTAL' in line and '%' in line:
                try:
                    coverage = int(line.split('%')[0].strip().split()[-1])
                    if coverage >= 60:
                        print_success(f"测试覆盖率: {coverage}%")
                        return True
                    else:
                        print_warning(f"测试覆盖率较低: {coverage}% (建议 >= 60%)")
                        return True  # 不阻塞 CI
                except (ValueError, IndexError):
                    pass

        print_success("测试运行完成")
        return True
    else:
        print_error("测试运行失败")
        print("\n输出:")
        print(output)
        return False


def check_documentation() -> bool:
    """检查文档完整性"""
    print_header("检查文档完整性")

    required_docs = [
        "README.md",
        "README.en.md",
        "CHANGELOG.md",
        "CONTRIBUTING.md"
    ]

    missing = []
    for doc in required_docs:
        if not os.path.exists(doc):
            missing.append(doc)
        else:
            print_success(f"找到文档: {doc}")

    if missing:
        print_warning(f"缺失文档: {', '.join(missing)}")
        return True  # 不阻塞 CI
    else:
        print_success("所有必需文档都存在")
        return True


def check_project_structure() -> bool:
    """检查项目结构"""
    print_header("检查项目结构")

    required_dirs = [
        "app/api",
        "app/core",
        "app/models",
        "app/services",
        "app/db"
    ]

    missing = []
    for dir_path in required_dirs:
        if not os.path.isdir(dir_path):
            missing.append(dir_path)
        else:
            print_success(f"找到目录: {dir_path}")

    if missing:
        print_error(f"缺失目录: {', '.join(missing)}")
        return False
    else:
        print_success("项目结构完整")
        return True


def check_dependencies() -> bool:
    """检查依赖文件"""
    print_header("检查依赖")

    files_to_check = ["requirements.txt", "pyproject.toml"]

    all_exist = True
    for file in files_to_check:
        if os.path.exists(file):
            print_success(f"找到依赖文件: {file}")
        else:
            print_error(f"缺失依赖文件: {file}")
            all_exist = False

    return all_exist


def check_gitignore() -> bool:
    """检查 .gitignore 文件"""
    print_header("检查 .gitignore")

    if not os.path.exists(".gitignore"):
        print_warning(".gitignore 文件不存在")
        return True  # 不阻塞

    required_entries = [
        "__pycache__",
        "*.pyc",
        ".venv",
        "venv/",
        ".env",
        "*.db",
        ".pytest_cache",
        ".coverage",
        "coverage.xml"
    ]

    with open(".gitignore", 'r') as f:
        content = f.read()

    all_present = True
    for entry in required_entries:
        if entry in content:
            print_success(f".gitignore 包含: {entry}")
        else:
            print_warning(f".gitignore 缺失: {entry}")
            all_present = False

    return True  # 不阻塞 CI


def main():
    """主函数"""
    print(f"{Colors.BOLD}{Colors.BLUE}")
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║          ClawRiver - 项目验证脚本                      ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print(f"{Colors.RESET}")

    os.chdir(Path(__file__).parent.parent)

    results = []

    # 运行所有检查
    results.append(("代码格式检查", check_code_format()))
    results.append(("Linting 检查", check_linting()))
    results.append(("类型提示检查", check_type_hints()))
    results.append(("测试覆盖率", check_test_coverage()))
    results.append(("文档完整性", check_documentation()))
    results.append(("项目结构", check_project_structure()))
    results.append(("依赖文件", check_dependencies()))
    results.append(("Git忽略文件", check_gitignore()))

    # 打印总结
    print_header("验证总结")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        if result:
            print_success(f"{name}")
        else:
            print_error(f"{name}")

    print(f"\n{Colors.BOLD}总计: {passed}/{total} 项检查通过{Colors.RESET}")

    # 决定退出码
    critical_checks = ["代码格式检查", "Linting 检查", "项目结构", "依赖文件"]
    failed_critical = [
        name for name, result in results
        if not result and name in critical_checks
    ]

    if failed_critical:
        print(f"\n{Colors.RED}{Colors.BOLD}关键检查失败: {', '.join(failed_critical)}{Colors.RESET}")
        return 1
    else:
        print(f"\n{Colors.GREEN}{Colors.BOLD}所有关键检查通过！{Colors.RESET}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
