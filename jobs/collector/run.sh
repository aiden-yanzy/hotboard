#!/usr/bin/env bash
# 采集器定时入口（launchd 每 30 分钟调用）
# 日志按天落 logs/，保留 14 天；只保留最近 30 天的运行记录表由库内 crawl_runs 承担
cd "$(dirname "$0")" || exit 1
mkdir -p logs
LOG="logs/collect-$(date +%Y%m%d).log"
{
  echo "===== $(date '+%F %T') 采集开始 ====="
  .venv/bin/python collect.py 2>&1
  RC=$?                      # ⚠️ 先存起来：下面若再跑命令替换，$? 就被覆盖了
  echo "===== $(date '+%F %T') 结束（退出码 ${RC}）====="
} >> "$LOG"
# 日志保留 14 天
find logs -name 'collect-*.log' -mtime +14 -delete 2>/dev/null
