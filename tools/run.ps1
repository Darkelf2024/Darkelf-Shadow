# Run Darkelf Shadow from source (Windows).
#   tools\run.ps1            # normal run
#   tools\run.ps1 -Log       # also write a session log to ~/.darkelf/logs
param([switch]$Log)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
if ($Log) { $env:DARKELF_DEV = "1" }
python (Join-Path $root "app\app.py")
