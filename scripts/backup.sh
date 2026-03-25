#!/bin/bash
# ClawRiver 数据备份脚本 - 从线上API导出所有数据
# 用法: bash scripts/backup.sh

BASE="https://clawriver.onrender.com"
BACKUP_DIR="$(dirname "$0")/../data/backup"
mkdir -p "$BACKUP_DIR"

echo "🔄 开始备份 ClawRiver 数据..."

# 1. 导出所有知识
echo -n "  📦 导出知识..."
PAGE=1
ALL_MEMORIES="[]"
while true; do
  RESP=$(curl -s "$BASE/api/v1/memories?page_size=50&page=$PAGE")
  ITEMS=$(echo "$RESP" | python3 -c "import json,sys; d=json.load(sys.stdin); print(json.dumps(d.get('data',{}).get('items',[])))" 2>/dev/null)
  COUNT=$(echo "$ITEMS" | python3 -c "import json,sys; print(len(json.loads(sys.stdin.read())))" 2>/dev/null)
  if [ "$COUNT" = "0" ] || [ -z "$COUNT" ]; then break; fi
  
  # 获取每个知识的完整内容（包括付费的）
  FULL_ITEMS="[]"
  for MID in $(echo "$ITEMS" | python3 -c "import json,sys; [print(i['memory_id']) for i in json.loads(sys.stdin.read())]" 2>/dev/null); do
    DETAIL=$(curl -s "$BASE/api/v1/memories/$MID" 2>/dev/null)
    FULL_ITEM=$(echo "$DETAIL" | python3 -c "import json,sys; d=json.load(sys.stdin); print(json.dumps(d.get('data',{})))" 2>/dev/null)
    if [ "$FULL_ITEM" != "{}" ] && [ -n "$FULL_ITEM" ]; then
      FULL_ITEMS=$(python3 -c "import json; items=json.loads('$FULL_ITEMS'); items.append(json.loads('''$FULL_ITEM''')); print(json.dumps(items))" 2>/dev/null || echo "$FULL_ITEMS")
    fi
  done
  
  ALL_MEMORIES=$(python3 -c "
import json
existing = json.loads('''$ALL_MEMORIES''')
new_items = json.loads('''$ITEMS''')
existing.extend(new_items)
print(json.dumps(existing))
" 2>/dev/null || echo "$ALL_MEMORIES")
  
  PAGE=$((PAGE+1))
done
echo "$ALL_MEMORIES" > "$BACKUP_DIR/memories.json"
MCOUNT=$(python3 -c "import json; print(len(json.load(open('$BACKUP_DIR/memories.json'))))" 2>/dev/null)
echo " $MCOUNT 条"

# 2. 导出交易记录
echo -n "  💰 导出交易..."
ALL_TX="[]"
for PAGE in 1 2 3 4 5; do
  RESP=$(curl -s "$BASE/api/v1/transactions/?page_size=50&page=$PAGE")
  ITEMS=$(echo "$RESP" | python3 -c "import json,sys; d=json.load(sys.stdin); print(json.dumps(d.get('data',{}).get('items',[])))" 2>/dev/null)
  COUNT=$(echo "$ITEMS" | python3 -c "import json,sys; print(len(json.loads(sys.stdin.read())))" 2>/dev/null)
  if [ "$COUNT" = "0" ] || [ -z "$COUNT" ]; then break; fi
  ALL_TX=$(python3 -c "import json; a=json.loads('''$ALL_TX'''); a.extend(json.loads('''$ITEMS''')); print(json.dumps(a))" 2>/dev/null || echo "$ALL_TX")
done
echo "$ALL_TX" > "$BACKUP_DIR/transactions.json"
TCOUNT=$(python3 -c "import json; print(len(json.load(open('$BACKUP_DIR/transactions.json'))))" 2>/dev/null)
echo " $TCOUNT 条"

# 3. 导出统计
echo -n "  📊 导出统计..."
curl -s "$BASE/api/v1/stats/overview" > "$BACKUP_DIR/stats.json"
echo " 完成"

# 4. 保存时间戳
echo "{\"backup_time\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\", \"memories\": $MCOUNT, \"transactions\": $TCOUNT}" > "$BACKUP_DIR/manifest.json"

echo ""
echo "✅ 备份完成！文件保存在:"
echo "   $BACKUP_DIR/"
ls -la "$BACKUP_DIR/"
