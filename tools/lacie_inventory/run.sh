#!/usr/bin/env bash
# One-command LaCie inventory for macOS / Linux. READ ONLY on the drive. Works on bash 3.2.
# Usage:  bash tools/lacie_inventory/run.sh                    # auto-detect a LaCie/Lacey volume
#         bash tools/lacie_inventory/run.sh "/Volumes/LaCie"   # explicit mount
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
OUT="$REPO/data/lacie_catalog"

if ! command -v uv >/dev/null 2>&1; then
  echo "Installing uv (Python package manager) ..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi

cd "$REPO/backend"
uv sync --extra dev --extra inventory

ROOT="${1:-}"
if [ -z "$ROOT" ]; then
  CANDS=()
  while IFS= read -r line; do [ -n "$line" ] && CANDS+=("$line"); done < <(uv run python "$HERE/inventory.py" --find)
  LACIE=()
  for c in ${CANDS[@]+"${CANDS[@]}"}; do
    case "$(printf '%s' "$c" | tr '[:upper:]' '[:lower:]')" in *lacie*|*lacey*) LACIE+=("$c");; esac
  done
  if [ "${#LACIE[@]}" -eq 1 ]; then
    ROOT="${LACIE[0]}"
  else
    echo "Could not pick the LaCie volume automatically. Candidates:"
    for c in ${CANDS[@]+"${CANDS[@]}"}; do echo "  $c"; done
    echo "Re-run with the path:  bash tools/lacie_inventory/run.sh \"/Volumes/<name>\""; exit 2
  fi
fi
echo "Library root: $ROOT  (read-only)"
echo "Output:       $OUT"
uv run python "$HERE/inventory.py" "$ROOT" --out "$OUT"
echo
echo "Share:      $OUT/summary.md   (counts only)"
echo "Keep local: $OUT/summary_paths.md, catalog.csv, catalog.jsonl, catalog.sqlite"
