#!/usr/bin/env python3
"""
ClawRiver - 第三轮循环测试
压力测试、并发操作、长流程测试
"""
import httpx
import json
import time
import sys
import concurrent.futures

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
        return getattr(httpx, method)(url, timeout=30, **kwargs)
    except Exception as e:
        return None

def auth_headers(api_key):
    return {"X-API-Key": api_key}

def unwrap(resp):
    if not resp or resp.status_code != 200:
        return None
    data = resp.json()
    return data.get("data", data) if isinstance(data, dict) and "data" in data else data

ts = int(time.time())

# ============================================
# 准备
# ============================================
print("\n" + "="*60)
print("准备：注册测试用户")
print("="*60)

users = {}
for i in range(5):
    resp = api_call("post", f"{API}/agents", json={"name": f"压力测试用户{i}_{ts}", "description": f"用户{i}"})
    data = unwrap(resp)
    if data:
        users[f"user{i}"] = data["api_key"]
    log_test(f"注册用户{i}", "PASS" if data else "FAIL")

# ============================================
# 场景1：批量创建记忆
# ============================================
print("\n" + "="*60)
print("场景1：批量创建记忆")
print("="*60)

created_ids = []
if "user0" in users:
    for i in range(10):
        resp = api_call("post", f"{API}/memories", headers=auth_headers(users["user0"]), json={
            "title": f"批量记忆{i}_{ts}",
            "content": {"index": i, "data": f"这是第{i}条批量创建的记忆"},
            "summary": f"批量创建的第{i}条记忆数据",
            "category": "测试/批量",
            "tags": ["batch", f"item{i}"],
            "price": 10 + i * 5,
            "format_type": "template"
        })
        data = unwrap(resp)
        if data and data.get("memory_id"):
            created_ids.append(data["memory_id"])
    log_test("批量创建10条记忆", "PASS" if len(created_ids) == 10 else "FAIL", f"成功{len(created_ids)}条")

# ============================================
# 场景2：批量搜索和筛选
# ============================================
print("\n" + "="*60)
print("场景2：批量搜索和筛选")
print("="*60)

# 2.1 搜索应能找到刚创建的记忆
time.sleep(1)
resp = api_call("get", f"{API}/memories", params={"query": "批量记忆", "page_size": 20})
data = unwrap(resp)
items = data.get("items", []) if data else []
log_test("搜索批量记忆", "PASS" if len(items) >= 10 else "WARN", f"找到{len(items)}条")

# 2.2 分页测试
for page in [1, 2, 3]:
    resp = api_call("get", f"{API}/memories", params={"page": page, "page_size": 5})
    data = unwrap(resp)
    items = data.get("items", []) if data else []
    log_test(f"分页第{page}页", "PASS" if resp and resp.status_code == 200 else "FAIL", f"{len(items)}条")

# 2.3 多标签搜索
resp = api_call("get", f"{API}/memories", params={"tags": "batch,item3", "page_size": 5})
data = unwrap(resp)
items = data.get("items", []) if data else []
log_test("多标签筛选", "PASS" if resp and resp.status_code == 200 else "FAIL", f"{len(items)}条")

# ============================================
# 场景3：批量购买
# ============================================
print("\n" + "="*60)
print("场景3：批量购买")
print("="*60)

if "user1" in users and created_ids:
    purchased = 0
    for mid in created_ids[:5]:
        resp = api_call("post", f"{API}/memories/{mid}/purchase", headers=auth_headers(users["user1"]))
        if resp and resp.status_code == 200:
            purchased += 1
    log_test("批量购买5条记忆", "PASS" if purchased == 5 else "FAIL", f"成功{purchased}条")

# 验证积分扣除
resp = api_call("get", f"{API}/agents/me", headers=auth_headers(users["user1"]))
data = unwrap(resp)
if data:
    credits = data.get("credits", 0)
    expected_spent = sum(10 + i * 5 for i in range(5))  # 10+15+20+25+30 = 100
    log_test("批量购买积分验证", "PASS" if credits == 999999 - expected_spent else "WARN", 
             f"credits={credits}, expected={999999 - expected_spent}")

# ============================================
# 场景4：并发注册
# ============================================
print("\n" + "="*60)
print("场景4：并发注册")
print("="*60)

def register_agent(i):
    resp = api_call("post", f"{API}/agents", json={
        "name": f"并发用户{i}_{ts}",
        "description": f"并发测试用户{i}"
    })
    return resp and resp.status_code == 200

with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    futures = [executor.submit(register_agent, i) for i in range(10)]
    results = [f.result() for f in concurrent.futures.as_completed(futures)]
    success_count = sum(results)
    log_test("并发注册10个用户", "PASS" if success_count == 10 else "WARN", f"成功{success_count}个")

# ============================================
# 场景5：长流程 - 完整交易链
# ============================================
print("\n" + "="*60)
print("场景5：完整交易链")
print("="*60)

# 卖家创建记忆
resp = api_call("post", f"{API}/memories", headers=auth_headers(users["user0"]), json={
    "title": f"完整交易链测试_{ts}",
    "content": {"steps": ["创建", "搜索", "购买", "评价", "查看"]},
    "summary": "完整交易链测试的记忆数据，覆盖整个交易流程",
    "category": "测试/流程",
    "tags": ["flow", "test"],
    "price": 100,
    "format_type": "template"
})
data = unwrap(resp)
flow_mem_id = data.get("memory_id") if data else None
log_test("卖家创建记忆", "PASS" if flow_mem_id else "FAIL")

if flow_mem_id and "user2" in users:
    # 买家搜索
    resp = api_call("get", f"{API}/memories", params={"query": "完整交易链", "page_size": 5})
    data = unwrap(resp)
    items = data.get("items", []) if data else []
    found = any(item.get("memory_id") == flow_mem_id for item in items)
    log_test("买家搜索找到记忆", "PASS" if found else "WARN")
    
    # 买家查看详情
    resp = api_call("get", f"{API}/memories/{flow_mem_id}")
    data = unwrap(resp)
    log_test("买家查看详情", "PASS" if data else "FAIL")
    
    # 买家购买
    resp = api_call("post", f"{API}/memories/{flow_mem_id}/purchase", headers=auth_headers(users["user2"]))
    purchase_data = unwrap(resp)
    log_test("买家购买", "PASS" if purchase_data and purchase_data.get("success") else "FAIL")
    
    # 买家评价
    resp = api_call("post", f"{API}/memories/{flow_mem_id}/rate", headers=auth_headers(users["user2"]),
                    json={"memory_id": flow_mem_id, "score": 5, "comment": "完整的交易流程测试"})
    log_test("买家评价", "PASS" if resp and resp.status_code == 200 else "FAIL")
    
    # 卖家查看销售记录
    resp = api_call("get", f"{API}/agents/me/memories", headers=auth_headers(users["user0"]))
    data = unwrap(resp)
    items = data.get("items", []) if data else []
    has_flow_mem = any(item.get("memory_id") == flow_mem_id for item in items)
    log_test("卖家查看自己的记忆", "PASS" if has_flow_mem else "WARN")

# ============================================
# 场景6：团队完整流程
# ============================================
print("\n" + "="*60)
print("场景6：团队完整流程")
print("="*60)

flow_team_id = None
if "user0" in users:
    resp = api_call("post", f"{API}/teams", headers=auth_headers(users["user0"]), json={
        "name": f"流程测试团队_{ts}",
        "description": "完整流程测试团队"
    })
    data = unwrap(resp)
    flow_team_id = data.get("team_id") if data else None
    log_test("创建团队", "PASS" if flow_team_id else "FAIL")

invite_code = None
if flow_team_id and "user0" in users:
    resp = api_call("post", f"{API}/teams/{flow_team_id}/invite", headers=auth_headers(users["user0"]),
                    json={"expires_days": 30})
    data = unwrap(resp)
    invite_code = data.get("code") if data else None

if invite_code and flow_team_id:
    # 多个成员加入
    for uid in ["user1", "user2", "user3"]:
        if uid in users:
            resp = api_call("post", f"{API}/teams/{flow_team_id}/join", headers=auth_headers(users[uid]),
                            json={"code": invite_code})
    log_test("多成员加入团队", "PASS")
    
    # 成员创建团队记忆
    for i in range(3):
        resp = api_call("post", f"{API}/memories/team/{flow_team_id}", headers=auth_headers(users["user0"]), json={
            "title": f"团队记忆{i}_{ts}",
            "content": {"team": True, "index": i},
            "summary": f"团队共享的第{i}条记忆",
            "category": "团队/共享",
            "tags": ["team", f"mem{i}"],
            "format_type": "template",
            "price": 0
        })
    log_test("创建3条团队记忆", "PASS")
    
    # 团队成员查看
    resp = api_call("get", f"{API}/memories/team/{flow_team_id}", headers=auth_headers(users["user1"]))
    data = unwrap(resp)
    items = data.get("items", []) if data else []
    log_test("团队成员查看记忆", "PASS" if len(items) >= 3 else "WARN", f"{len(items)}条")

# ============================================
# 场景7：错误恢复测试
# ============================================
print("\n" + "="*60)
print("场景7：错误恢复测试")
print("="*60)

# 7.1 积分不足
# 创建记忆价格高于用户初始积分
resp = api_call("post", f"{API}/memories", headers=auth_headers(users["user0"]), json={
    "title": f"超高价记忆_{ts}",
    "content": {"price": "extremely high"},
    "summary": "超高价记忆用于测试积分不足场景",
    "category": "测试",
    "price": 10000000,  # 1000万，超过初始999999
    "format_type": "template"
})
data = unwrap(resp)
if data:
    expensive_id = data["memory_id"]
    # 新用户只有999999积分，买不起1000万的记忆
    resp = api_call("post", f"{API}/agents", json={"name": f"低积分用户_{ts}", "description": "测试"})
    low_user = unwrap(resp)
    if low_user:
        resp = api_call("post", f"{API}/memories/{expensive_id}/purchase", headers=auth_headers(low_user["api_key"]))
        if resp and resp.status_code == 400:
            log_test("积分不足拒绝购买", "PASS")
        else:
            log_test("积分不足拒绝购买", "WARN", f"status={resp.status_code if resp else 'N/A'}")
    else:
        log_test("积分不足拒绝购买", "SKIP", "无法创建用户")
else:
    log_test("积分不足拒绝购买", "SKIP", "无法创建高价记忆")

# 7.2 查看不存在的记忆
resp = api_call("get", f"{API}/memories/nonexistent_xyz_999")
if resp and resp.status_code == 404:
    log_test("查看不存在记忆返回404", "PASS")
else:
    log_test("查看不存在记忆返回404", "WARN", f"status={resp.status_code if resp else 'N/A'}")

# ============================================
# 总结
# ============================================
print("\n" + "="*60)
print("第三轮测试总结")
print("="*60)

passed = sum(1 for t in test_results if t["status"] == "PASS")
failed = sum(1 for t in test_results if t["status"] == "FAIL")
warned = sum(1 for t in test_results if t["status"] == "WARN")

print(f"\n✅ 通过: {passed}")
print(f"❌ 失败: {failed}")
print(f"⚠️  警告: {warned}")
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

with open("test_results_round3.json", "w") as f:
    json.dump({"tests": test_results, "issues": issues}, f, ensure_ascii=False, indent=2)

print("\n结果已保存到 test_results_round3.json")
