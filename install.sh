#!/usr/bin/env bash
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="${HOME}/.agents/skills/zz-mv-gongzuotai"
BIN="${HOME}/.local/bin"
FORCE=0

while [ $# -gt 0 ]; do
  case "$1" in
    --target) TARGET="$2"; shift 2 ;;
    --bin) BIN="$2"; shift 2 ;;
    --force) FORCE=1; shift ;;
    -h|--help) echo "usage: ./install.sh [--target ~/.agents/skills/zz-mv-gongzuotai] [--bin ~/.local/bin] [--force]"; exit 0 ;;
    *) echo "unknown option: $1"; exit 1 ;;
  esac
done

PY="$(command -v python3 || true)"
if [ -z "$PY" ]; then echo "python3 not found (need 3.9+)"; exit 1; fi
"$PY" - <<'PY'
import sys
if sys.version_info < (3,9):
    raise SystemExit("Python 3.9+ required")
print("python", sys.version.split()[0])
PY

for tool in ffmpeg ffprobe; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "warning: $tool not found (timeline / duration checks need it)"
  fi
done

if [ -e "$TARGET" ] && [ "$FORCE" -ne 1 ]; then
  echo "target exists: $TARGET"
  echo "use --force to replace it"
  exit 1
fi
rm -rf "$TARGET"
mkdir -p "$TARGET" "$BIN"

for item in SKILL.md START_HERE.md references scripts templates contracts demo config README.md LICENSE NOTICE.md; do
  cp -R "$REPO/$item" "$TARGET/"
done
echo "installed skill: $TARGET"

mkdir -p "${HOME}/.config/mv-workbench"
chmod 700 "${HOME}/.config/mv-workbench" 2>/dev/null || true
if [ ! -f "${HOME}/.config/mv-workbench/keys.json" ]; then
  cp "$REPO/config/keys.example.json" "${HOME}/.config/mv-workbench/keys.json"
  chmod 600 "${HOME}/.config/mv-workbench/keys.json"
  echo "created: ~/.config/mv-workbench/keys.json"
fi

cat > "$BIN/mvwb" <<WRAP
#!/usr/bin/env bash
exec "$PY" "$TARGET/scripts/mvwb.py" "\$@"
WRAP
chmod +x "$BIN/mvwb"
echo "installed: $BIN/mvwb"
case ":$PATH:" in
  *":$BIN:"*) ;;
  *) echo "note: add $BIN to PATH, or run $TARGET/scripts/mvwb.py" ;;
esac

echo
echo "next:"
echo "  $BIN/mvwb doctor"
echo "  $BIN/mvwb demo"
