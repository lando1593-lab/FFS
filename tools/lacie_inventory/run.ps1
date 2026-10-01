# One-command LaCie inventory for Windows (PowerShell). READ ONLY on the drive.
# Usage:  powershell -ExecutionPolicy Bypass -File tools\lacie_inventory\run.ps1            # auto-detect
#         powershell -ExecutionPolicy Bypass -File tools\lacie_inventory\run.ps1 -Root "E:\"  # explicit
param([string]$Root = "")
$ErrorActionPreference = "Stop"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Repo = Resolve-Path (Join-Path $Here "..\..")
$Out = Join-Path $Repo "data\lacie_catalog"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
  Write-Host "Installing uv (Python package manager) ..."
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
}

Set-Location (Join-Path $Repo "backend")
uv sync --extra dev --extra inventory

if ($Root -eq "") {
  $vols = Get-Volume | Where-Object { $_.DriveLetter -and $_.FileSystemLabel -match "lacie" }
  if ($vols.Count -eq 1) { $Root = "$($vols[0].DriveLetter):\" }
  else {
    Write-Host "Could not pick the LaCie volume automatically. Volumes:"
    Get-Volume | Where-Object { $_.DriveLetter } | Format-Table DriveLetter, FileSystemLabel, SizeRemaining, Size
    Write-Host 'Re-run with:  powershell -ExecutionPolicy Bypass -File tools\lacie_inventory\run.ps1 -Root "E:\"'
    exit 2
  }
}
Write-Host "Library root: $Root  (read-only)"
Write-Host "Output:       $Out"
uv run python (Join-Path $Here "inventory.py") $Root --out $Out
Write-Host ""
Write-Host "Done. Share: $Out\summary.md   (counts only, no document text)"
Write-Host "Keep local: catalog.csv, catalog.jsonl, catalog.sqlite in $Out"
