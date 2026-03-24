#!/usr/bin/env python3
"""
ClawRiver - 第一轮循环测试 v3
修复响应解析（data包装层）
"""
import httpx
import json
import time
import sys

BASE_URL = "http://localhost:8000"
API = f"{BASE_URL}/api/v1"

issues = []
test_results = []

def log_test(name, status, detail=""):
    result = {"name": name, "status": status, "detail": detail}
    test_results.append(result)
    icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
    print(f"  {icon} {name}: {status}" + (f" - {detail}" if detail else ""))
    if status == "FAIL":
        issues.append({"test": name, "detail": detail, "severity": "严重"})

def api_call(method, url, **kwargs):
    try:
        resp = getattr(httpx, method)(url, timeout=15, **kwargs)
        return resp
    except Exception as e:
        return None

def auth_headers(api_key):
    return {"X-API-Key": api_key}

def unwrap(resp):
    """统一解析响应：处理data包装层"""
    if not resp or resp.status_code != 200:
        return None
    data = resp.json()
    if isinstance(data, dict) and "data" in data:
        return data["data"]
    return data

# ============================================
# 场景1：新用户首次使用
# ============================================
print("\n" + "="*60)
print("场景1：新用户首次使用")
print("="*60)

ts = int(time.time())

# 1.1 注册Agent
print("\n--- 1.1 注册Agent ---")
resp = api_call("post", f"{API}/agents", json={
    "name": f"测试用户{ts}",
    "description": "第一轮测试用户"
})
data = unwrap(resp)
if data and data.get("agent_id"):
    agent1_key = data.get("api_key")
    agent1_id = data.get("agent_id")
    log_test("注册Agent", "PASS", f"id={agent1_id}, credits={data.get('credits')}")
else:
    log_test("注册Agent", "FAIL", resp.text[:300] if resp else "连接失败")
    agent1_key = None

# 1.2 获取Agent信息
print("\n--- 1.2 获取Agent信息 ---")
if agent1_key:
    resp = api_call("get", f"{API}/agents/me", headers=auth_headers(agent1_key))
    data = unwrap(resp)
    if data:
        log_test("获取Agent信息", "PASS", f"credits={data.get('credits')}, name={data.get('name')}")
    else:
        log_test("获取Agent信息", "FAIL", resp.text[:200] if resp else "连接失败")
else:
    log_test("获取Agent信息", "SKIP", "无API Key")

# 1.3 搜索记忆（空库测试）
print("\n--- 1.3 搜索记忆 ---")
all_memories = []
for q in ["python", "数据分析", "营销", "agent"]:
    resp = api_call("get", f"{API}/memories", params={"query": q, "page_size": 5})
    data = unwrap(resp)
    if data is not None:
        items = data.get("items", [])
        log_test(f"搜索 '{q}'", "PASS", f"{len(items)}条")
        if items and not all_memories:
            all_memories = items
    else:
        log_test(f"搜索 '{q}'", "FAIL", resp.text[:200] if resp else "连接失败")

# 浏览全部
resp = api_call("get", f"{API}/memories", params={"page_size": 10})
data = unwrap(resp)
if data:
    items = data.get("items", [])
    if items:
        all_memories = items
    log_test("浏览全部", "PASS", f"{len(items)}条")
else:
    log_test("浏览全部", "FAIL", resp.text[:200] if resp else "连接失败")

# ============================================
# 场景2：记忆创建者
# ============================================
print("\n" + "="*60)
print("场景2：记忆创建者")
print("="*60)

# 2.1 注册创建者
print("\n--- 2.1 注册创建者 ---")
resp = api_call("post", f"{API}/agents", json={
    "name": f"创建者{ts}",
    "description": "专业记忆提供者"
})
data = unwrap(resp)
if data and data.get("api_key"):
    agent2_key = data["api_key"]
    log_test("注册创建者", "PASS", f"credits={data.get('credits')}")
else:
    agent2_key = None
    log_test("注册创建者", "FAIL", resp.text[:300] if resp else "连接失败")

# 2.2 创建记忆
print("\n--- 2.2 创建记忆 ---")
created_memory_ids = []
if agent2_key:
    memories_to_create = [
        {
            "title": "Python数据分析实战经验",
            "content": {"steps": ["pandas数据清洗", "fillna处理缺失值", "向量化操作优化"], "tip": "优先用query筛选"},
            "summary": "Python数据分析最佳实践：pandas数据清洗和缺失值处理技巧",
            "category": "Python/数据分析",
            "tags": ["python", "pandas", "数据分析"],
            "price": 50,
            "format_type": "template"
        },
        {
            "title": "抖音投流ROI优化方案",
            "content": {"strategy": "渐进式出价", "phases": ["3天最低出价", "达标后加价", "每周更新素材"], "roi": "2.0-2.5"},
            "summary": "抖音广告投放优化经验：渐进式出价策略，ROI提升至2.0以上",
            "category": "营销/抖音",
            "tags": ["抖音", "投流", "ROI"],
            "price": 100,
            "format_type": "strategy"
        },
        {
            "title": "FastAPI性能优化指南",
            "content": {"tech": ["异步驱动", "响应缓存", "连接池", "查询优化"], "benchmark": "QPS提升300%"},
            "summary": "FastAPI性能优化技巧：异步数据库驱动、缓存、连接池配置",
            "category": "开发/性能优化",
            "tags": ["fastapi", "性能", "优化"],
            "price": 30,
            "format_type": "template"
        }
    ]
    
    for mem in memories_to_create:
        resp = api_call("post", f"{API}/memories", headers=auth_headers(agent2_key), json=mem)
        data = unwrap(resp)
        if data and data.get("memory_id"):
            mid = data["memory_id"]
            created_memory_ids.append(mid)
            log_test(f"创建 '{mem['title']}'", "PASS", f"id={mid}")
        else:
            log_test(f"创建 '{mem['title']}'", "FAIL", resp.text[:300] if resp else "连接失败")

# 2.3 等待索引生效并搜索
print("\n--- 2.3 搜索刚创建的记忆 ---")
time.sleep(1)
resp = api_call("get", f"{API}/memories", params={"query": "python", "page_size": 5})
data = unwrap(resp)
if data:
    items = data.get("items", [])
    log_test("搜索 'python'", "PASS" if items else "WARN", f"{len(items)}条")
    if items:
        all_memories = items

resp = api_call("get", f"{API}/memories", params={"query": "抖音", "page_size": 5})
data = unwrap(resp)
if data:
    items = data.get("items", [])
    log_test("搜索 '抖音'", "PASS" if items else "WARN", f"{len(items)}条")

resp = api_call("get", f"{API}/memories", params={"query": "FastAPI", "page_size": 5})
data = unwrap(resp)
if data:
    items = data.get("items", [])
    log_test("搜索 'FastAPI'", "PASS" if items else "WARN", f"{len(items)}条")

# 2.4 查看我的记忆
if agent2_key:
    resp = api_call("get", f"{API}/agents/me/memories", headers=auth_headers(agent2_key))
    data = unwrap(resp)
    if data:
        items = data.get("items", [])
        log_test("查看我的记忆", "PASS" if items else "WARN", f"{len(items)}条")
    else:
        log_test("查看我的记忆", "FAIL", resp.text[:200] if resp else "连接失败")

# 2.5 查看记忆详情
print("\n--- 2.5 查看记忆详情 ---")
if all_memories:
    test_memory_id = all_memories[0].get("memory_id")
    resp = api_call("get", f"{API}/memories/{test_memory_id}")
    data = unwrap(resp)
    if data:
        log_test("查看记忆详情", "PASS", f"title={data.get('title')}")
    else:
        log_test("查看记忆详情", "FAIL", resp.text[:200] if resp else "连接失败")
else:
    test_memory_id = None
    log_test("查看记忆详情", "SKIP", "无可用记忆")

# ============================================
# 场景3：购买与评价
# ============================================
print("\n" + "="*60)
print("场景3：购买与评价")
print("="*60)

purchased_memory_id = None

# 3.1 购买记忆
if agent1_key and test_memory_id:
    resp = api_call("post", f"{API}/memories/{test_memory_id}/purchase", headers=auth_headers(agent1_key))
    if resp and resp.status_code == 200:
        log_test("购买记忆", "PASS")
        purchased_memory_id = test_memory_id
    else:
        error = resp.text[:300] if resp else "连接失败"
        log_test("购买记忆", "FAIL", error)

# 3.2 重复购买
if agent1_key and purchased_memory_id:
    resp = api_call("post", f"{API}/memories/{purchased_memory_id}/purchase", headers=auth_headers(agent1_key))
    if resp and (resp.status_code == 400 or "already" in resp.text.lower() or "已" in resp.text or "重复" in resp.text):
        log_test("重复购买检测", "PASS", "正确拒绝")
    else:
        log_test("重复购买检测", "WARN", f"status={resp.status_code if resp else 'N/A'}")

# 3.3 购买后查看详情
if agent1_key and purchased_memory_id:
    resp = api_call("get", f"{API}/memories/{purchased_memory_id}", headers=auth_headers(agent1_key))
    data = unwrap(resp)
    if data:
        has_content = bool(data.get("content"))
        log_test("购买后查看详情", "PASS" if has_content else "WARN", f"有内容={has_content}")
    else:
        log_test("购买后查看详情", "FAIL", resp.text[:200] if resp else "连接失败")

# 3.4 评价记忆
if agent1_key and purchased_memory_id:
    resp = api_call("post", f"{API}/memories/{purchased_memory_id}/rate",
                    headers=auth_headers(agent1_key),
                    json={"memory_id": purchased_memory_id, "score": 4, "comment": "很有用的经验"})
    if resp and resp.status_code == 200:
        log_test("评价记忆", "PASS")
    else:
        error = resp.text[:300] if resp else "连接失败"
        log_test("评价记忆", "FAIL", error)

# 3.5 未购买评价
if agent1_key and created_memory_ids and len(created_memory_ids) > 1:
    unrated_id = created_memory_ids[-1]
    resp = api_call("post", f"{API}/memories/{unrated_id}/rate",
                    headers=auth_headers(agent1_key),
                    json={"memory_id": unrated_id, "score": 3})
    if resp and resp.status_code in [400, 403]:
        log_test("未购买就评价", "PASS", "正确拒绝")
    else:
        log_test("未购买就评价", "WARN", f"status={resp.status_code if resp else 'N/A'}")

# 3.6 购买自己的记忆
if agent2_key and created_memory_ids:
    resp = api_call("post", f"{API}/memories/{created_memory_ids[0]}/purchase", headers=auth_headers(agent2_key))
    if resp and (resp.status_code == 400 or "self" in resp.text.lower() or "自己" in resp.text):
        log_test("购买自己的记忆", "PASS", "正确拒绝自购")
    else:
        log_test("购买自己的记忆", "WARN", f"status={resp.status_code if resp else 'N/A'}")

# ============================================
# 场景4：团队协作
# ============================================
print("\n" + "="*60)
print("场景4：团队协作")
print("="*60)

team_id = None

# 4.1 创建团队
print("\n--- 4.1 创建团队 ---")
resp = api_call("post", f"{API}/teams", headers=auth_headers(agent1_key), json={
    "name": f"测试团队{ts}",
    "description": "第一轮测试团队"
})
data = unwrap(resp)
if data and data.get("team_id"):
    team_id = data["team_id"]
    log_test("创建团队", "PASS", f"id={team_id}")
else:
    log_test("创建团队", "FAIL", resp.text[:300] if resp else "连接失败")

# 4.2 生成邀请码
invite_code = None
if agent1_key and team_id:
    resp = api_call("post", f"{API}/teams/{team_id}/invite", headers=auth_headers(agent1_key),
                    json={"expires_days": 7})
    data = unwrap(resp)
    if data and data.get("code"):
        invite_code = data["code"]
        log_test("生成邀请码", "PASS", f"code={invite_code}")
    else:
        log_test("生成邀请码", "FAIL", resp.text[:300] if resp else "连接失败")

# 4.3 邀请成员
if agent2_key and invite_code and team_id:
    resp = api_call("post", f"{API}/teams/{team_id}/join", headers=auth_headers(agent2_key),
                    json={"code": invite_code})
    if resp and resp.status_code == 200:
        log_test("邀请成员", "PASS")
    else:
        error = resp.text[:300] if resp else "连接失败"
        log_test("邀请成员", "FAIL", error)

# 4.4 查看团队信息
if team_id:
    resp = api_call("get", f"{API}/teams/{team_id}")
    data = unwrap(resp)
    if data:
        log_test("查看团队信息", "PASS", f"成员={data.get('member_count', '?')}")
    else:
        log_test("查看团队信息", "FAIL", resp.text[:200] if resp else "连接失败")

# 4.5 创建团队记忆
if agent1_key and team_id:
    resp = api_call("post", f"{API}/memories/team/{team_id}", headers=auth_headers(agent1_key), json={
        "title": "团队共享：敏捷开发经验",
        "content": {"method": "Scrum", "practices": ["15分钟站会", "2周Sprint", "看板"]},
        "summary": "敏捷开发最佳实践：Scrum框架、站会、Sprint、看板",
        "category": "管理/项目管理",
        "tags": ["敏捷", "Scrum"],
        "format_type": "template",
        "price": 0
    })
    if resp and resp.status_code == 200:
        log_test("创建团队记忆", "PASS")
    else:
        error = resp.text[:300] if resp else "连接失败"
        log_test("创建团队记忆", "FAIL", error)

# 4.6 获取团队记忆
if agent1_key and team_id:
    resp = api_call("get", f"{API}/memories/team/{team_id}", headers=auth_headers(agent1_key))
    data = unwrap(resp)
    if data is not None:
        items = data.get("items", [])
        log_test("获取团队记忆", "PASS", f"{len(items)}条")
    else:
        log_test("获取团队记忆", "FAIL", resp.text[:200] if resp else "连接失败")

# 4.7 非成员访问
resp3 = api_call("post", f"{API}/agents", json={"name": f"路人{ts}", "description": "非成员"})
outsider_data = unwrap(resp3)
if outsider_data and team_id:
    outsider_key = outsider_data.get("api_key")
    resp = api_call("get", f"{API}/memories/team/{team_id}", headers=auth_headers(outsider_key))
    if resp and resp.status_code in [403, 404]:
        log_test("非成员访问团队", "PASS", "正确拒绝")
    else:
        log_test("非成员访问团队", "WARN", f"status={resp.status_code if resp else 'N/A'}")

# ============================================
# 场景5：高级功能
# ============================================
print("\n" + "="*60)
print("场景5：高级功能")
print("="*60)

# 积分历史
resp = api_call("get", f"{API}/agents/me/credits/history", headers=auth_headers(agent1_key))
data = unwrap(resp)
if data is not None:
    items = data.get("items", [])
    log_test("积分历史", "PASS", f"{len(items)}条记录")
else:
    log_test("积分历史", "FAIL", resp.text[:200] if resp else "连接失败")

# 市场趋势
resp = api_call("get", f"{API}/market/trends")
data = unwrap(resp)
if data is not None:
    log_test("市场趋势", "PASS", f"{len(data)}个分类")
else:
    log_test("市场趋势", "FAIL", resp.text[:200] if resp else "连接失败")

# 账户余额
resp = api_call("get", f"{API}/agents/me/balance", headers=auth_headers(agent1_key))
data = unwrap(resp)
if data and "credits" in data:
    log_test("账户余额", "PASS", f"credits={data['credits']}")
else:
    log_test("账户余额", "FAIL", resp.text[:200] if resp else "连接失败")

# ============================================
# 场景6：边界情况
# ============================================
print("\n" + "="*60)
print("场景6：边界情况")
print("="*60)

# 搜索不存在
resp = api_call("get", f"{API}/memories", params={"query": "zzz不存在xyz999", "page_size": 5})
data = unwrap(resp)
if data and len(data.get("items", [])) == 0:
    log_test("搜索不存在", "PASS", "0条")
else:
    log_test("搜索不存在", "WARN", f"返回{len(data.get('items',[])) if data else '?'}条")

# 查看不存在记忆
resp = api_call("get", f"{API}/memories/nonexistent_xyz_123")
if resp and resp.status_code in [404, 400]:
    log_test("查看不存在记忆", "PASS", f"{resp.status_code}")
elif resp and resp.status_code == 422:
    log_test("查看不存在记忆", "WARN", "返回422而非404（可能路由冲突）")
else:
    log_test("查看不存在记忆", "WARN", f"status={resp.status_code if resp else 'N/A'}")

# 无效API Key
resp = api_call("get", f"{API}/agents/me", headers={"X-API-Key": "invalid"})
if resp and resp.status_code in [401, 403]:
    log_test("无效API Key", "PASS", "正确拒绝")
else:
    log_test("无效API Key", "WARN", f"status={resp.status_code if resp else 'N/A'}")

# 空搜索
resp = api_call("get", f"{API}/memories", params={"query": "", "page_size": 5})
data = unwrap(resp)
if data is not None:
    log_test("空关键词搜索", "PASS")
else:
    log_test("空关键词搜索", "FAIL")

# 负数价格
resp = api_call("post", f"{API}/memories", headers=auth_headers(agent2_key), json={
    "title": "负数价格测试",
    "content": {"test": "data"},
    "summary": "测试负数价格是否被正确拒绝的测试数据",
    "category": "测试",
    "price": -10,
    "format_type": "template"
})
if resp and resp.status_code in [400, 422]:
    log_test("负数价格拒绝", "PASS")
else:
    log_test("负数价格拒绝", "WARN", f"status={resp.status_code if resp else 'N/A'}")

# ============================================
# 总结
# ============================================
print("\n" + "="*60)
print("第一轮测试总结")
print("="*60)

passed = sum(1 for t in test_results if t["status"] == "PASS")
failed = sum(1 for t in test_results if t["status"] == "FAIL")
warned = sum(1 for t in test_results if t["status"] == "WARN")
skipped = sum(1 for t in test_results if t["status"] == "SKIP")

print(f"\n✅ 通过: {passed}")
print(f"❌ 失败: {failed}")
print(f"⚠️  警告: {warned}")
print(f"⏭️  跳过: {skipped}")
print(f"📊 总计: {len(test_results)}")

if issues:
    print("\n🔴 严重问题:")
    for issue in issues:
        print(f"  - {issue['test']}: {issue['detail']}")

warnings = [t for t in test_results if t["status"] == "WARN"]
if warnings:
    print("\n🟡 警告问题:")
    for w in warnings:
        print(f"  - {w['name']}: {w['detail']}")

with open("test_results_round1.json", "w") as f:
    json.dump({"tests": test_results, "issues": issues}, f, ensure_ascii=False, indent=2)

print("\n结果已保存到 test_results_round1.json")
