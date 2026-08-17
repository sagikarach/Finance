#!/usr/bin/env bash
# Run Finance against a throwaway data directory — a safe "test account" with no
# real data. Everything (accounts, movements, the login session, profile, sync
# state) lives in the sandbox dir; the app starts logged-out and fresh and never
# touches your real data. Delete the dir to wipe, or pass a fresh path to reset.
#
#   scripts/run_sandbox.sh                  # uses ~/finance-sandbox
#   scripts/run_sandbox.sh /tmp/my-test     # custom dir
set -euo pipefail
DIR="${1:-$HOME/finance-sandbox}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "🧪 Finance sandbox"
echo "   data dir: $DIR"
echo "   (delete it to wipe; nothing here touches your real data)"
echo

FINANCE_DATA_DIR="$DIR" python "$ROOT/main.py"
