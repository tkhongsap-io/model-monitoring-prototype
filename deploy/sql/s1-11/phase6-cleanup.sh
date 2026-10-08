#!/usr/bin/env bash
# S1-11 phase 6, on the test host VM, after `gcloud sql users delete monitor_app`:
# delete the temporary password files, the backup and this folder. Prints names only.
set -euo pipefail
SECRETS=/opt/model-monitor/secrets
rm -f "$SECRETS"/*.tmp "$SECRETS/backend.env.monitor_app.bak"
stat -c '%a %U %n' "$SECRETS"/*
rm -rf /tmp/s1-11
echo "PHASE 6 DONE"
