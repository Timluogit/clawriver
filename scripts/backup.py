#!/usr/bin/env python3
"""ClawRiver 数据备份脚本 - 从线上API导出所有数据"""
import json
import os
import urllib.request
from datetime import datetime

BASE = "https://clawriver.onrender.com"
BACKUP_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "backup")
os.makedirs(BACKUP_DIR, exist_ok=True)

def api_get(path):
    """GET请求"""
    try:
        url = f"{BASE}{path}"
        req = urllib.request.Request(url)
        resp = urllib.request.urlopen(req, timeout=15)
        return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}

def backup():
    print("🔄 开始备份 ClawRiver 数据...")
    
    # 1. 导出所有知识（含完整内容）
    print("  📦 导出知识...", end="", flush=True)
    all_memories = []
    for page in range(1, 10):
        data = api_get(f"/api/v1/memories?page_size=50&page={page}")
        items = data.get("data", {}).get("items", [])
        if not items:
            break
        
        # 获取每个知识的完整内容
        for item in items:
            mid = item["memory_id"]
            detail = api_get(f"/api/v1/memories/{mid}")
            full = detail.get("data", {})
            if full:
                all_memories.append(full)
                print(".", end="", flush=True)
    
    with open(os.path.join(BACKUP_DIR, "memories.json"), "w", encoding="utf-8") as f:
        json.dump(all_memories, f, ensure_ascii=False, indent=2)
    print(f" {len(all_memories)} 条")
    
    # 2. 导出交易记录
    print("  💰 导出交易...", end="", flush=True)
    all_transactions = []
    for page in range(1, 10):
        data = api_get(f"/api/v1/transactions/?page_size=50&page={page}")
        items = data.get("data", {}).get("items", [])
        if not items:
            break
        all_transactions.extend(items)
        print(".", end="", flush=True)
    
    with open(os.path.join(BACKUP_DIR, "transactions.json"), "w", encoding="utf-8") as f:
        json.dump(all_transactions, f, ensure_ascii=False, indent=2)
    print(f" {len(all_transactions)} 条")
    
    # 3. 导出统计
    print("  📊 导出统计...", end="", flush=True)
    stats = api_get("/api/v1/stats/overview")
    with open(os.path.join(BACKUP_DIR, "stats.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print(" 完成")
    
    # 4. 保存清单
    manifest = {
        "backup_time": datetime.utcnow().isoformat() + "Z",
        "memories": len(all_memories),
        "transactions": len(all_transactions),
        "categories": len(set(m.get("category", "") for m in all_memories)),
    }
    with open(os.path.join(BACKUP_DIR, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 备份完成！")
    print(f"   知识: {len(all_memories)} 条")
    print(f"   交易: {len(all_transactions)} 条")
    print(f"   分类: {manifest['categories']} 个")
    print(f"   时间: {manifest['backup_time']}")
    print(f"   目录: {BACKUP_DIR}")

if __name__ == "__main__":
    backup()
