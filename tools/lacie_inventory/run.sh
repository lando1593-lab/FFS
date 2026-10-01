#!/usr/bin/env bash
# One-command LaCie inventory for macOS / Linux. READ ONLY on the drive.
# Usage:  bash tools/lacie_inventory/run.sh                # auto-detect a LaCie volume
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
  mapfile -t CANDS < <(uv run python "$HERE/inventory.py" --find)
  LACIE=()
  for c in "${CANDS[@]}"; do case "$(echo "$c" | tr '[:upper:]' '[:lower:]')" in *lacie*) LACIE+=("$c");; esac; done
  if [ "${#LACIE[@]}" -eq 1 ]; then
    ROOT="${LACIE[0]}"
  else
    echo "Could not pick the LaCie volume automatically. Candidates:"; printf '  %s\n' "${CANDS[@]}"
    echo "Re-run with the path:  bash tools/lacie_inventory/run.sh \"/Volumes/<name>\""; exit 2
  fi
fi
echo "Library root: $ROOT  (read-only)"
echo "Output:       $OUT"
uv run python "$HERE/inventory.py" "$ROOT" --out "$OUT"
echo
echo "Done. Share: $OUT/summary.md   (counts only, no document text)"
echo "Keep local: $OUT/catalog.csv, catalog.jsonl, catalog.sqlite"
