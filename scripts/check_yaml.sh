#!/usr/bin/env bash
# Validate YAML files using PyYAML. Usage:
#   ./scripts/check_yaml.sh                # validate all *.yml / *.yaml
#   ./scripts/check_yaml.sh path/to/file   # validate specific files

set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-}"

_pick_python() {
  if [[ -n "${PYTHON_BIN}" ]]; then
    echo "${PYTHON_BIN}"
    return 0
  fi
  if command -v python3 >/dev/null 2>&1; then
    echo "python3"
  elif command -v python >/dev/null 2>&1; then
    echo "python"
  else
    echo ""
  fi
}

py=$(_pick_python)
if [[ -z "${py}" ]]; then
  echo "No python interpreter found (python3/python)."
  exit 1
fi

# Collect files: args or all *.yml / *.yaml
if [[ $# -gt 0 ]]; then
  files=("$@")
else
  mapfile -t files < <(find . -type f \( -name '*.yml' -o -name '*.yaml' \))
fi

if [[ ${#files[@]} -eq 0 ]]; then
  echo "No YAML files found."
  exit 0
fi

status=0
for f in "${files[@]}"; do
  if [[ ! -f "$f" ]]; then
    echo "Skip (not a file): $f"
    continue
  fi
  echo "Checking $f"
  if ! "${py}" - <<'PY' "$f"; then
    status=1
  fi
  continue
  PY
import sys
try:
    import yaml  # type: ignore
except ImportError:
    sys.stderr.write("PyYAML is required. Install with: python -m pip install pyyaml\n")
    sys.exit(1)

path = sys.argv[1]
try:
    with open(path, "r", encoding="utf-8") as fh:
        yaml.safe_load(fh)
except Exception as e:
    sys.stderr.write(f"YAML error in {path}: {e}\n")
    sys.exit(1)
sys.exit(0)
PY
done

if [[ $status -ne 0 ]]; then
  echo "YAML validation failed."
else
  echo "All YAML files are valid."
fi

exit $status


