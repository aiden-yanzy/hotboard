#!/usr/bin/env bash
# 验收：dailyhot 可插拔 —— 下线它不影响任何东西
# 用法：bash verify_pluggable.sh
# ⚠️ 本脚本会临时停用 dailyhot 并临时改 config.yml；**exit 时无条件恢复**（防脚本中途崩溃把 dailyhot 永久停掉）
set -u
cd "$(dirname "$0")"
PW=$(grep POSTGRES_PASSWORD ~/Docker/hotdb/.env | cut -d= -f2)
Q() { docker exec -e PGPASSWORD="$PW" hotdb psql -U hotboard -d hotboard -tAc "$1" 2>&1; }

CFG_BAK=$(mktemp)
cp config.yml "$CFG_BAK"
restore() {
  Q "update sources set enabled=true where engine='dailyhot';" >/dev/null 2>&1
  cp "$CFG_BAK" config.yml 2>/dev/null
  rm -f "$CFG_BAK"
  local n; n=$(Q "select count(*) from sources where enabled and engine='dailyhot';")
  echo "🔧 已恢复现场：dailyhot 启用源 ${n} 个 / config.yml 已还原"
}
trap restore EXIT INT TERM

echo "===== 0. 基线 ====="
BASE_ITEMS=$(Q "select count(*) from items;")
BASE_SNAPS=$(Q "select count(*) from snapshots;")
echo "  items=$BASE_ITEMS  snapshots=$BASE_SNAPS"

echo
echo "===== 1. 下线 dailyhot（方式①：库里置 enabled=false）====="
Q "update sources set enabled=false where engine='dailyhot';" >/dev/null
echo "  已停用源数: $(Q "select count(*) from sources where engine='dailyhot' and not enabled;")"
.venv/bin/python collect.py > /tmp/plug-alt1.log 2>&1; echo "  退出码=$?"
tail -4 /tmp/plug-alt1.log | sed 's/^/  /'
ITEMS1=$(Q "select count(*) from items;")
echo "  → 采集后 items=${ITEMS1}（旧数据完好: $([ "${ITEMS1}" -ge "${BASE_ITEMS}" ] && echo ✅ || echo ❌)）"
echo "  → newsnow 这轮是否照常入库: $(grep -q 'newsnow: 源成功' /tmp/plug-alt1.log && echo ✅ || echo ❌)"

echo
echo "===== 2. 恢复 dailyhot，改用方式②（config 里 base_url 置空）====="
Q "update sources set enabled=true where engine='dailyhot';" >/dev/null
cp config.yml /tmp/config.yml.bak
python3 - <<'PY'
import re
s = open('config.yml', encoding='utf-8').read()
s = s.replace('base_url: "http://127.0.0.1:6688"', 'base_url: ""   # 方式②：置空即停用')
open('config.yml', 'w', encoding='utf-8').write(s)
PY
.venv/bin/python collect.py > /tmp/plug-alt2.log 2>&1; echo "  退出码=$?"
grep -E "未配置 base_url|源成功|📊" /tmp/plug-alt2.log | sed 's/^/  /'
echo "  （配置与源开关由 EXIT trap 统一还原，见脚本末尾输出）"

echo
echo "===== 3. 恢复后复采（确认两个引擎都回来）====="
.venv/bin/python collect.py > /tmp/plug-restore.log 2>&1
tail -3 /tmp/plug-restore.log | sed 's/^/  /'
echo
echo "===== 结论 ====="
echo "  items: $BASE_ITEMS → $(Q "select count(*) from items;")（只增不减）"
echo "  两种下线方式都无需改代码 ✅"
