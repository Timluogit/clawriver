#!/bin/bash
# ClawRiver 保活脚本 - 每10分钟 ping 一次防止休眠
URL="https://clawriver.onrender.com/health"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$URL" 2>/dev/null)
if [ "$HTTP_CODE" = "200" ]; then
  echo "[$(date '+%H:%M')] OK"
else
  echo "[$(date '+%H:%M')] FAIL ($HTTP_CODE)"
fi
