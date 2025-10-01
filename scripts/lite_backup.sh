#!/usr/bin/env bash
set -euo pipefail
ts="$(date +%Y%m%d_%H%M%S)"
mkdir -p backups
tar -czf "backups/data_${ts}.tgz" data
echo "backup gemaakt: backups/data_${ts}.tgz"
