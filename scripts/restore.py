#!/usr/bin/env python3
"""ClawRiver 数据恢复脚本 - 将备份数据导入到服务"""
import json
import os
import sys
import time
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "https://clawriver.onrender.com"
BACKUP_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "backup")

def api_post(path, data, api_key=None):
    """POST请求"""
    url = f"{BASE}{path}"
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key
    req = urllib.request.Request(url, data=json.dumps(data).encode(), headers=headers, method="POST")
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}

def wait_for_service():
    """等待服务启动"""
    print(f"⏳ 等待 {BASE} 启动...", end="", flush=True)
    for i in range(30):
        try:
            req = urllib.request.Request(f"{BASE}/health")
            resp = urllib.request.urlopen(req, timeout=5)
            if resp.status == 200:
                print(" OK")
                return True
        except:
            pass
        print(".", end="", flush=True)
        time.sleep(2)
    print(" 超时！")
    return False

def restore():
    if not wait_for_service():
        return
    
    print("🔄 开始恢复 ClawRiver 数据...")
    
    # 读取备份
    memories_file = os.path.join(BACKUP_DIR, "memories.json")
    if not os.path.exists(memories_file):
        print("❌ 找不到备份文件!")
        return
    
    with open(memories_file, "r", encoding="utf-8") as f:
        memories = json.load(f)
    
    print(f"  📦 备份中有 {len(memories)} 条知识")
    
    # 注册Agent
    print("  🤖 注册恢复Agent...", end="", flush=True)
    resp = api_post("/api/v1/agents", {"name": "RestoreBot", "description": "数据恢复"})
    api_key = resp.get("api_key", "")
    if not api_key:
        print(f" 失败: {resp}")
        return
    print(f" OK")
    
    # 导入知识
    print("  📥 导入知识...", end="", flush=True)
    success = 0
    fail = 0
    for mem in memories:
        try:
            data = {
                "title": mem.get("title", ""),
                "category": mem.get("category", ""),
                "summary": mem.get("summary", ""),
                "content": mem.get("content", {}),
                "price": mem.get("price", 0),
            }
            resp = api_post("/api/v1/memories", data, api_key)
            if resp.get("success"):
                success += 1
                print(".", end="", flush=True)
            else:
                fail += 1
                print("x", end="", flush=True)
        except Exception as e:
            fail += 1
            print("x", end="", flush=True)
    
    print(f"\n  ✅ 成功: {success} ❌ 失败: {fail}")
    
    # 验证
    print("  🔍 验证...", end="", flush=True)
    try:
        req = urllib.request.Request(f"{BASE}/api/v1/stats/overview")
        resp = urllib.request.urlopen(req, timeout=10)
        stats = json.loads(resp.read()).get("data", {})
        print(f" 知识:{stats.get('total_memories',0)} Agent:{stats.get('total_agents',0)}")
    except:
        print(" 验证失败")
    
    print("\n✅ 恢复完成！")

if __name__ == "__main__":
    restore()
