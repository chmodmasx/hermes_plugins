#!/usr/bin/env bash
set -euo pipefail
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
if command -v hermes >/dev/null 2>&1; then hermes plugins disable gitea-hermes >/dev/null 2>&1 || true; fi
rm -rf "$HERMES_HOME/plugins/gitea-hermes" "$HERMES_HOME/skills/gitea-professional"
echo "Removed gitea-hermes plugin and gitea-professional skill."
echo "GITEA_BASE_URL/GITEA_TOKEN were intentionally left in $HERMES_HOME/.env; remove/rotate them explicitly if desired."
