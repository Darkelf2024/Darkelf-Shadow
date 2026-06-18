#!/usr/bin/env bash
# Run Darkelf Shadow from source (Linux/macOS).
#   tools/run.sh            # normal run
#   tools/run.sh --log      # also write a session log to ~/.darkelf/logs
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ "${1:-}" == "--log" ]]; then export DARKELF_DEV=1; fi
exec python "$ROOT/app/app.py"
