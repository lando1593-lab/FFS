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
`data/lacie_catalog/`. Then send `data/lacie_catalog/summary.md`. Type drive letters as `D:\`
without quotes; the output folder must be on a different drive than the library (enforced).

## A drive with personal files on it
Point the tool at the work folder rather than the drive root, e.g. `-Root "D:\Fireproofing"`.
If you do run the whole drive: photos, video and audio are never opened or hashed; they are
counted per top-level folder in `summary.md` (no names) and listed by folder in
`summary_paths.md`. Skip folders entirely with `--exclude "Christmas*" --exclude "Photos*"`
(pass through `run.ps1` / `run.sh` as extra arguments after the root).

## Manual path

```
cd backend && uv sync --extra dev --extra inventory
uv run python ../tools/lacie_inventory/inventory.py --find           # find the mount
uv run python ../tools/lacie_inventory/inventory.py /Volumes/LaCie --out ../data/lacie_catalog
```
Windows: `uv run python ..\tools\lacie_inventory\inventory.py E:\ --out ..\data\lacie_catalog`

Start with `--dry-run --max-files 200` to confirm the path, then run the full pass (it reads the
first 4 pages of every PDF, so expect roughly 1–3 files/second on a USB drive).

Outputs (in `--out`, default `data/lacie_catalog/`, git-ignored):
- `summary.md` — counts only (file classes, document types, manufacturers, decades, scanned PDFs,
  error and unclassified counts). **Share this one.** It names the volume but no files.
- `summary_paths.md` — top folders, error paths, unclassified paths. Contains folder and file
  names (often client/project names). Keep local unless you choose to share it.
- `catalog.csv` (Excel-friendly), `catalog.jsonl` (appended live during the run), `catalog.sqlite`
  — per-file rows with a ≤600-char text snippet. Keep local.
- `run.log` — start/stop, progress, whether the run was interrupted.

Ctrl-C writes a partial catalog marked PARTIAL. Re-running renames the previous outputs to
`*.prev` first.

What "read only" means precisely: the tool opens files for reading only and never creates,
renames, moves, or deletes anything on the drive. Reading can still bump "last accessed"
timestamps on some filesystems; file contents, names, and modified dates are untouched.

Classification is heuristic (keyword scoring with confidence). Everything is tagged
`historical`. Nothing in the catalog may become a code/product rule without a human promoting it
with a current authoritative source (ADR-0004).
