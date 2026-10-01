# LaCie inventory tool (read-only)

Runs on the machine the LaCie drive is plugged into. It never writes inside the drive.

## Fastest path (no Python knowledge needed)
macOS / Linux, in a terminal at the repo root:
```
bash tools/lacie_inventory/run.sh                 # finds a volume named LaCie automatically
bash tools/lacie_inventory/run.sh "/Volumes/LaCie" # or give the path
```
Windows PowerShell, at the repo root:
```
powershell -ExecutionPolicy Bypass -File tools\lacie_inventory\run.ps1
powershell -ExecutionPolicy Bypass -File tools\lacie_inventory\run.ps1 -Root "E:\"
```
Both install `uv` if missing, set up the environment, run the inventory, and write to
`data/lacie_catalog/`. Then commit or send `data/lacie_catalog/summary.md`.

## Manual path

```
cd backend && uv sync --extra dev --extra inventory
uv run python ../tools/lacie_inventory/inventory.py --find           # find the mount
uv run python ../tools/lacie_inventory/inventory.py /Volumes/LaCie --out ../data/lacie_catalog
```
Windows: `uv run python ..\tools\lacie_inventory\inventory.py E:\ --out ..\data\lacie_catalog`

Start with `--dry-run --max-files 200` to confirm the path, then run the full pass (it reads the
first 4 pages of every PDF, so expect roughly 1–3 files/second on a USB drive).

Outputs (in `--out`, which is git-ignored under `data/`):
- `summary.md` — counts by document type, manufacturer, decade, folder; scanned PDFs; errors; unclassified list.
  **Share this file** (or commit it to `docs/research/lacie-summary.md`) — it contains no document text.
- `catalog.csv`, `catalog.jsonl`, `catalog.sqlite` — per-file rows with a ≤600-char snippet. Keep local.

Classification is heuristic (keyword scoring with confidence). Everything is tagged
`historical`. Nothing in the catalog may become a code/product rule without a human promoting it
with a current authoritative source (ADR-0004).
