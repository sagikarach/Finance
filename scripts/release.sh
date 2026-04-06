#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# release.sh  –  Bump version, tag, and push to trigger the GitHub Actions
#                build + release workflow.
#
# Usage:
#   scripts/release.sh 1.2.3
#
# The actual build, signing, and GitHub release is handled by:
#   .github/workflows/release.yml
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── 1. Validate argument ──────────────────────────────────────────────────────
if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <version>   e.g.  $0 1.2.3"
  exit 1
fi

VERSION="$1"
TAG="v${VERSION}"

cd "$(dirname "$0")/.."

# ── 2. Check for uncommitted changes ─────────────────────────────────────────
if ! git diff --quiet || ! git diff --staged --quiet; then
  echo "❌  You have uncommitted changes. Commit or stash them first."
  git status --short
  exit 1
fi

# ── 3. Check tag doesn't already exist ───────────────────────────────────────
if git rev-parse "${TAG}" &>/dev/null; then
  echo "❌  Tag ${TAG} already exists. Choose a different version."
  exit 1
fi

# ── 4. Bump version in source ─────────────────────────────────────────────────
echo "📝  Setting version to ${VERSION}..."
python3 -c "
import pathlib
p = pathlib.Path('finance/__version__.py')
p.write_text('__version__ = \"${VERSION}\"\n')
print(f'  → {p.read_text().strip()}')
"

# ── 5. Commit & tag ───────────────────────────────────────────────────────────
echo "🔖  Committing and tagging ${TAG}..."
git add finance/__version__.py
git commit -m "chore: bump version to ${VERSION}"
git tag "${TAG}"

# ── 6. Push — this triggers GitHub Actions ────────────────────────────────────
echo "🚀  Pushing commit + tag to GitHub..."
git push origin main
git push origin "${TAG}"

echo ""
echo "✅  Done! GitHub Actions is now building and publishing the release."
echo "    Watch progress at:"
echo "    https://github.com/sagikarach/Finance/actions"
echo ""
echo "    Release will appear at:"
echo "    https://github.com/sagikarach/Finance/releases/tag/${TAG}"
