#!/usr/bin/env python3
"""
ClawRiver - 第二轮循环测试
深入测试边界情况、数据一致性和高级功能
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
    if not resp or resp.status_code != 200:
        return None
    data = resp.json()
    if isinstance(data, dict) and "data" in data:
        return data["data"]
    return data

ts = int(time.time())

# ============================================
# 准备：注册测试用户
# ============================================
print("\n" + "="*60)
print("准备：注册测试用户")
print("="*60)

# 用户A：买家
resp = api_call("post", f"{API}/agents", json={"name": f"买家A{ts}", "description": "测试买家"})
data = unwrap(resp)
userA_key = data["api_key"] if data else None
log_test("注册买家A", "PASS" if userA_key else "FAIL")

# 用户B：卖家
resp = api_call("post", f"{API}/agents", json={"name": f"卖家B{ts}", "description": "测试卖家"})
data = unwrap(resp)
userB_key = data["api_key"] if data else None
log_test("注册卖家B", "PASS" if userB_key else "FAIL")

# 用户C：路人
resp = api_call("post", f"{API}/agents", json={"name": f"路人C{ts}", "description": "普通用户"})
data = unwrap(resp)
userC_key = data["api_key"] if data else None
log_test("注册路人C", "PASS" if userC_key else "FAIL")

# ============================================
# 场景1：数据一致性测试
# ============================================
print("\n" + "="*60)
print("场景1：数据一致性测试")
print("="*60)

# 1.1 卖家创建记忆
if userB_key:
    resp = api_call("post", f"{API}/memories", headers=auth_headers(userB_key), json={
        "title": "一致性测试记忆",
        "content": {"data": "test content for consistency"},
        "summary": "用于测试数据一致性的记忆数据",
        "category": "测试/一致性",
        "tags": ["test", "consistency"],
        "price": 50,
        "format_type": "template"
    })
    data = unwrap(resp)
    test_mem_id = data.get("memory_id") if data else None
    log_test("创建测试记忆", "PASS" if test_mem_id else "FAIL")

# 1.2 买家购买后积分变化
if userA_key and test_mem_id:
    # 获取购买前余额
    resp = api_call("get", f"{API}/agents/me", headers=auth_headers(userA_key))
    before_data = unwrap(resp)
    before_credits = before_data.get("credits", 0) if before_data else 0
    
    # 购买
    resp = api_call("post", f"{API}/memories/{test_mem_id}/purchase", headers=auth_headers(userA_key))
    purchase_data = unwrap(resp)
    credits_spent = purchase_data.get("credits_spent", 0) if purchase_data else 0
    
    # 获取购买后余额
    resp2 = api_call("get", f"{API}/agents/me", headers=auth_headers(userA_key))
    after_data = unwrap(resp2)
    after_credits = after_data.get("credits", 0) if after_data else 0
    
    deducted = before_credits - after_credits
    if deducted == 50 and credits_spent == 50:
        log_test("购买积分扣除正确", "PASS", f"扣除{deducted}")
    else:
        log_test("购买积分扣除正确", "FAIL", f"期望扣除50，实际扣除{deducted}(credits_spent={credits_spent})")

# 1.3 卖家积分增加
if userB_key:
    resp = api_call("get", f"{API}/agents/me", headers=auth_headers(userB_key))
    data = unwrap(resp)
    if data:
        credits = data.get("credits", 0)
        expected = 999999 + 50  # 初始积分 + 卖家收入
        if credits == expected:
            log_test("卖家积分到账", "PASS", f"credits={credits}")
        else:
            log_test("卖家积分到账", "WARN", f"credits={credits}, expected={expected}")
    else:
        log_test("卖家积分到账", "FAIL")

# ============================================
# 场景2：边界条件测试
# ============================================
print("\n" + "="*60)
print("场景2：边界条件测试")
print("="*60)

# 2.1 标题太短
if userB_key:
    resp = api_call("post", f"{API}/memories", headers=auth_headers(userB_key), json={
        "title": "a",
        "content": {"test": "short title"},
        "summary": "测试标题太短的情况，应该被拒绝",
        "category": "测试",
        "price": 10,
        "format_type": "template"
    })
    if resp and resp.status_code in [400, 422]:
        log_test("标题太短拒绝", "PASS")
    else:
        log_test("标题太短拒绝", "WARN", f"status={resp.status_code if resp else 'N/A'}")

# 2.2 摘要太短
if userB_key:
    resp = api_call("post", f"{API}/memories", headers=auth_headers(userB_key), json={
        "title": "正常标题测试",
        "content": {"test": "short summary"},
        "summary": "短",
        "category": "测试",
        "price": 10,
        "format_type": "template"
    })
    if resp and resp.status_code in [400, 422]:
        log_test("摘要太短拒绝", "PASS")
    else:
        log_test("摘要太短拒绝", "WARN", f"status={resp.status_code if resp else 'N/A'}")

# 2.3 超大分页参数
resp = api_call("get", f"{API}/memories", params={"page": 1, "page_size": 1000})
if resp and resp.status_code == 200:
    data = unwrap(resp)
    items = data.get("items", []) if data else []
    log_test("超大分页限制", "PASS" if len(items) <= 50 else "WARN", f"返回{len(items)}条")
else:
    log_test("超大分页限制", "WARN", f"status={resp.status_code if resp else 'N/A'}")

# 2.4 负数分页
resp = api_call("get", f"{API}/memories", params={"page": -1, "page_size": 10})
if resp and resp.status_code in [400, 422]:
    log_test("负数页码拒绝", "PASS")
else:
    log_test("负数页码拒绝", "WARN", f"status={resp.status_code if resp else 'N/A'}")

# 2.5 空内容创建记忆
if userB_key:
    resp = api_call("post", f"{API}/memories", headers=auth_headers(userB_key), json={
        "title": "空内容测试记忆",
        "content": {},
        "summary": "测试空内容是否被正确处理的记忆数据",
        "category": "测试",
        "price": 0,
        "format_type": "template"
    })
    if resp and resp.status_code == 200:
        log_test("空内容创建记忆", "WARN", "空内容被接受（可能需要验证）")
    elif resp and resp.status_code in [400, 422]:
        log_test("空内容创建记忆", "PASS", "正确拒绝空内容")
    else:
        log_test("空内容创建记忆", "WARN", f"status={resp.status_code if resp else 'N/A'}")

# ============================================
# 场景3：搜索功能深度测试
# ============================================
print("\n" + "="*60)
print("场景3：搜索功能深度测试")
print("="*60)

# 3.1 特殊字符搜索
for q in ["@#$%", "'; DROP TABLE memories;--", "<script>alert(1)</script>"]:
    resp = api_call("get", f"{API}/memories", params={"query": q, "page_size": 5})
    if resp and resp.status_code == 200:
        log_test(f"特殊字符搜索安全", "PASS", f"'{q[:20]}'")
    else:
        log_test(f"特殊字符搜索安全", "WARN", f"'{q[:20]}' status={resp.status_code if resp else 'N/A'}")

# 3.2 超长搜索词
long_q = "a" * 1000
resp = api_call("get", f"{API}/memories", params={"query": long_q, "page_size": 5})
if resp and resp.status_code == 200:
    log_test("超长搜索词处理", "PASS")
else:
    log_test("超长搜索词处理", "WARN", f"status={resp.status_code if resp else 'N/A'}")

# 3.3 分类筛选
resp = api_call("get", f"{API}/memories", params={"category": "测试", "page_size": 5})
if resp and resp.status_code == 200:
    data = unwrap(resp)
    log_test("分类筛选", "PASS", f"{len(data.get('items', [])) if data else 0}条")
else:
    log_test("分类筛选", "FAIL")

# 3.4 价格范围筛选
resp = api_call("get", f"{API}/memories", params={"max_price": 50, "page_size": 5})
if resp and resp.status_code == 200:
    data = unwrap(resp)
    items = data.get("items", []) if data else []
    all_in_range = all(item.get("price", 0) <= 50 for item in items)
    log_test("价格范围筛选", "PASS" if all_in_range else "WARN", 
             f"{len(items)}条，{'全部<=50' if all_in_range else '有超限'}")
else:
    log_test("价格范围筛选", "FAIL")

# 3.5 排序方式测试
for sort in ["relevance", "created_at", "purchase_count", "price"]:
    resp = api_call("get", f"{API}/memories", params={"sort_by": sort, "page_size": 5})
    if resp and resp.status_code == 200:
        log_test(f"排序 '{sort}'", "PASS")
    else:
        log_test(f"排序 '{sort}'", "FAIL")

# ============================================
# 场景4：团队高级功能
# ============================================
print("\n" + "="*60)
print("场景4：团队高级功能")
print("="*60)

# 4.1 创建团队
team_id = None
if userA_key:
    resp = api_call("post", f"{API}/teams", headers=auth_headers(userA_key), json={
        "name": f"深度测试团队{ts}",
        "description": "第二轮测试团队"
    })
    data = unwrap(resp)
    team_id = data.get("team_id") if data else None
    log_test("创建团队", "PASS" if team_id else "FAIL")

# 4.2 生成邀请码并加入
invite_code = None
if userA_key and team_id:
    resp = api_call("post", f"{API}/teams/{team_id}/invite", headers=auth_headers(userA_key),
                    json={"expires_days": 7})
    data = unwrap(resp)
    invite_code = data.get("code") if data else None
    
    if invite_code and userB_key:
        resp = api_call("post", f"{API}/teams/{team_id}/join", headers=auth_headers(userB_key),
                        json={"code": invite_code})
        log_test("成员加入团队", "PASS" if resp and resp.status_code == 200 else "FAIL")

# 4.3 创建团队记忆
if userA_key and team_id:
    resp = api_call("post", f"{API}/memories/team/{team_id}", headers=auth_headers(userA_key), json={
        "title": "团队协作经验总结",
        "content": {"tips": ["定期同步", "文档先行", "代码审查"]},
        "summary": "团队协作最佳实践：同步、文档、审查",
        "category": "管理/团队",
        "tags": ["团队", "协作"],
        "format_type": "template",
        "price": 0
    })
    data = unwrap(resp)
    team_mem_id = data.get("memory_id") if data else None
    log_test("创建团队记忆", "PASS" if team_mem_id else "FAIL")

# 4.4 团队成员查看团队记忆
if userB_key and team_id:
    resp = api_call("get", f"{API}/memories/team/{team_id}", headers=auth_headers(userB_key))
    data = unwrap(resp)
    items = data.get("items", []) if data else []
    log_test("团队成员查看记忆", "PASS" if items else "WARN", f"{len(items)}条")

# 4.5 团队积分统计
if team_id:
    resp = api_call("get", f"{API}/teams/{team_id}/stats/credits", headers=auth_headers(userA_key))
    if resp and resp.status_code == 200:
        log_test("查看团队积分统计", "PASS")
    else:
        log_test("查看团队积分统计", "WARN", f"status={resp.status_code if resp else 'N/A'}")

# 4.6 团队统计（需要尾部斜杠避免307重定向）
if team_id:
    resp = api_call("get", f"{API}/teams/{team_id}/stats/", headers=auth_headers(userA_key))
    if resp and resp.status_code == 200:
        log_test("查看团队统计", "PASS")
    else:
        log_test("查看团队统计", "WARN", f"status={resp.status_code if resp else 'N/A'}")

# ============================================
# 场景5：评价系统深度测试
# ============================================
print("\n" + "="*60)
print("场景5：评价系统深度测试")
print("="*60)

# 5.0 先进行第一次评价
if userA_key and test_mem_id:
    resp = api_call("post", f"{API}/memories/{test_mem_id}/rate",
                    headers=auth_headers(userA_key),
                    json={"memory_id": test_mem_id, "score": 4, "comment": "第一次评价"})
    if resp and resp.status_code == 200:
        log_test("第一次评价", "PASS")
    elif resp and resp.status_code == 400:
        log_test("第一次评价", "WARN", "可能已评价过（来自之前的测试）")
    else:
        log_test("第一次评价", "FAIL", resp.text[:200] if resp else "")

# 5.1 重复评价检测
if userA_key and test_mem_id:
    resp = api_call("post", f"{API}/memories/{test_mem_id}/rate",
                    headers=auth_headers(userA_key),
                    json={"memory_id": test_mem_id, "score": 3, "comment": "重复评价测试"})
    resp_text = resp.text[:200] if resp else "N/A"
    resp_code = resp.status_code if resp else 0
    is_rejected = resp and (resp_code == 400 or "已" in resp_text or "already" in resp_text.lower())
    print(f"    [DEBUG] 重复评价: code={resp_code}, rejected={is_rejected}, text={resp_text[:100]}")
    if is_rejected:
        log_test("重复评价检测", "PASS", "正确拒绝")
    else:
        log_test("重复评价检测", "WARN", f"status={resp_code}")

# 5.2 无效评分（超出范围）
if userC_key and test_mem_id:
    # C先购买
    api_call("post", f"{API}/memories/{test_mem_id}/purchase", headers=auth_headers(userC_key))
    resp = api_call("post", f"{API}/memories/{test_mem_id}/rate",
                    headers=auth_headers(userC_key),
                    json={"memory_id": test_mem_id, "score": 10, "comment": "超出范围评分"})
    if resp and resp.status_code in [400, 422]:
        log_test("超出范围评分拒绝", "PASS")
    else:
        log_test("超出范围评分拒绝", "WARN", f"status={resp.status_code if resp else 'N/A'}")

# 5.3 评分0
# 注册用户D用于此测试
respD = api_call("post", f"{API}/agents", json={"name": f"用户D{ts}", "description": "测试用户D"})
dataD = unwrap(respD)
userD_key = dataD.get("api_key") if dataD else None
if userD_key and test_mem_id:
    api_call("post", f"{API}/memories/{test_mem_id}/purchase", headers=auth_headers(userD_key))
    resp = api_call("post", f"{API}/memories/{test_mem_id}/rate",
                    headers=auth_headers(userD_key),
                    json={"memory_id": test_mem_id, "score": 0, "comment": "零分评价"})
    if resp and resp.status_code in [400, 422]:
        log_test("零分评分拒绝", "PASS")
    else:
        log_test("零分评分拒绝", "WARN", f"status={resp.status_code if resp else 'N/A'}")

# ============================================
# 场景6：记忆版本管理
# ============================================
print("\n" + "="*60)
print("场景6：记忆版本管理")
print("="*60)

if test_mem_id and userB_key:
    # 6.1 更新记忆
    resp = api_call("put", f"{API}/memories/{test_mem_id}", headers=auth_headers(userB_key), json={
        "summary": "更新后的记忆摘要，增加了新内容",
        "changelog": "v2: 增加了性能优化建议"
    })
    if resp and resp.status_code == 200:
        log_test("更新记忆", "PASS")
    else:
        log_test("更新记忆", "WARN", f"status={resp.status_code if resp else 'N/A'}")
    
    # 6.2 查看版本历史
    resp = api_call("get", f"{API}/memories/{test_mem_id}/versions")
    if resp and resp.status_code == 200:
        log_test("查看版本历史", "PASS")
    else:
        log_test("查看版本历史", "WARN", f"status={resp.status_code if resp else 'N/A'}")

# ============================================
# 场景7：记忆搜索类型测试
# ============================================
print("\n" + "="*60)
print("场景7：搜索类型测试")
print("="*60)

for stype in ["keyword", "semantic", "hybrid"]:
    resp = api_call("get", f"{API}/memories", params={
        "query": "python", "search_type": stype, "page_size": 5
    })
    if resp and resp.status_code == 200:
        data = unwrap(resp)
        items = data.get("items", []) if data else []
        log_test(f"搜索类型 '{stype}'", "PASS", f"{len(items)}条")
    else:
        log_test(f"搜索类型 '{stype}'", "FAIL", resp.text[:200] if resp else "连接失败")

# 无效搜索类型
resp = api_call("get", f"{API}/memories", params={
    "query": "test", "search_type": "invalid", "page_size": 5
})
if resp and resp.status_code in [400, 422]:
    log_test("无效搜索类型拒绝", "PASS")
else:
    log_test("无效搜索类型拒绝", "WARN", f"status={resp.status_code if resp else 'N/A'}")

# ============================================
# 总结
# ============================================
print("\n" + "="*60)
print("第二轮测试总结")
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

with open("test_results_round2.json", "w") as f:
    json.dump({"tests": test_results, "issues": issues}, f, ensure_ascii=False, indent=2)

print("\n结果已保存到 test_results_round2.json")
