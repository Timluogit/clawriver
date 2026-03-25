#!/bin/bash
# ClawRiver 数据恢复脚本 - 将备份数据导入到新部署的服务
# 用法: bash scripts/restore.sh [API_URL]

BASE="${1:-https://clawriver.onrender.com}"
BACKUP_DIR="$(dirname "$0")/../data/backup"

if [ ! -f "$BACKUP_DIR/memories.json" ]; then
  echo "❌ 找不到备份文件: $BACKUP_DIR/memories.json"
  exit 1
fi

echo "🔄 开始恢复 ClawRiver 数据..."
echo "   目标: $BASE"

# 等待服务启动
echo -n "   等待服务启动..."
for i in $(seq 1 30); do
  CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/health" 2>/dev/null)
  if [ "$CODE" = "200" ]; then echo " OK"; break; fi
  echo -n "."
  sleep 2
done

# 1. 注册种子Agent
echo -n "  🤖 注册Agent..."
AGENT_RESP=$(curl -s -X POST "$BASE/api/v1/agents" \
  -H "Content-Type: application/json" \
  -d '{"name":"RestoreBot","description":"数据恢复Agent"}')
API_KEY=$(echo "$AGENT_RESP" | python3 -c "import json,sys; print(json.load(sys.stdin).get('api_key',''))" 2>/dev/null)
if [ -z "$API_KEY" ]; then echo " 失败"; exit 1; fi
echo " OK (Key: ${API_KEY:0:20}...)"

# 2. 恢复知识
echo -n "  📦 恢复知识..."
MEMORIES=$(cat "$BACKUP_DIR/memories.json")
SUCCESS=0
FAIL=0

# 用Python批量导入
python3 << PYEOF
import json, urllib.request, sys

api_key = "$API_KEY"
base = "$BASE"

with open("$BACKUP_DIR/memories.json", "r") as f:
    memories = json.load(f)

success = 0
fail = 0
for mem in memories:
    try:
        data = json.dumps({
            "title": mem["title"],
            "category": mem["category"],
            "summary": mem["summary"],
            "content": mem.get("content", {}),
            "price": mem.get("price", 0)
        }).encode()
        
        req = urllib.request.Request(
            f"{base}/api/v1/memories",
            data=data,
            headers={
                "Content-Type": "application/json",
                "X-API-Key": api_key
            },
            method="POST"
        )
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read())
        if result.get("success"):
            success += 1
            sys.stdout.write(".")
        else:
            fail += 1
            sys.stdout.write("x")
    except Exception as e:
        fail += 1
        sys.stdout.write("x")
    sys.stdout.flush()

print(f"\n  ✅ 成功: {success} ❌ 失败: {fail}")
PYEOF

# 3. 验证
echo ""
echo -n "  🔍 验证..."
curl -s "$BASE/api/v1/stats/overview" | python3 -c "
import json,sys
d=json.load(sys.stdin)['data']
print(f'知识:{d[\"total_memories\"]} Agent:{d[\"total_agents\"]} 分类:{d[\"total_categories\"]}')
"

echo ""
echo "✅ 恢复完成！"
