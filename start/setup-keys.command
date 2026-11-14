#!/usr/bin/env bash
set -e
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"

PY="python3"
if [ -x ".venv/bin/python" ]; then PY=".venv/bin/python"; fi

echo "MV 工作台 · Key 配置"
echo "输入不回显；Key 只保存在本机 ~/.config/mv-workbench/keys.json"
echo

"$PY" scripts/mv_keys.py init
"$PY" scripts/mv_keys.py set runninghub
"$PY" scripts/mv_keys.py set router

echo
echo "两个 Key 已保存。可以关闭这个窗口，回到 agent 继续。"
read -r -p "按回车关闭..." _
