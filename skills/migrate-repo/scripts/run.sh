#!/usr/bin/env bash
# Bootstrap: run raptor's update.py without a local raptor checkout.
#
# Clones the template repo (default: raptor on Azure DevOps) at its newest
# copier tag, then runs scripts/update.py from that clone, forwarding all
# arguments. Because update.py and migrate_to_copier.py are siblings in the
# clone, the latest version of the migration script is the one that runs.
#
# Usage (from the root of the repo to update):
#   bash run.sh --check                 # preview
#   bash run.sh --yes                   # apply
#   TEMPLATE=<url> REF=<ref> bash run.sh --check
#
# Needs: git, uv. Requires python3 only to parse nothing — pure shell + git.
set -euo pipefail

TEMPLATE="${TEMPLATE:-git@ssh.dev.azure.com:v3/GemeenteRotterdam/DAPR/raptor}"
REF="${REF:-}"

command -v git >/dev/null || { echo "ERROR: git not found" >&2; exit 1; }
command -v uv  >/dev/null || { echo "ERROR: uv not found (curl -LsSf https://astral.sh/uv/install.sh | sh)" >&2; exit 1; }

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

echo "cloning $TEMPLATE ..." >&2
git clone --quiet --no-local "$TEMPLATE" "$work/template"

if [[ -z "$REF" ]]; then
  # newest tag that is a copier template (has copier.yaml/copier.yml)
  while read -r tag; do
    [[ "$tag" == *'^{}' ]] && continue
    if git -C "$work/template" cat-file -e "$tag:copier.yaml" 2>/dev/null \
       || git -C "$work/template" cat-file -e "$tag:copier.yml" 2>/dev/null; then
      REF="$tag"; break
    fi
  done < <(git -C "$work/template" for-each-ref --sort=-v:refname --format='%(refname:short)' refs/tags)
  REF="${REF:-HEAD}"
fi

git -C "$work/template" checkout --quiet "$REF"
echo "running update.py from $TEMPLATE @ $REF" >&2

cd "$work/template"
exec uv run --no-project --python 3.11 scripts/update.py "$@"
