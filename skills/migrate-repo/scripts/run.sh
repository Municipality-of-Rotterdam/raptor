#!/usr/bin/env bash
# Bootstrap: run raptor's update.py without a local raptor checkout.
#
# Clones the template repo (default: the public raptor repo on GitHub), checks out one
# template ref, runs scripts/update.py from that clone and passes the same ref
# on as --ref. So the migration script that runs and the template it migrates
# to are always the same version.
#
# The ref is REF=<ref> or --ref <ref>, the template TEMPLATE=<url|path> or
# --template <url|path> (same things); both are passed on to update.py. Default: the newest tag that
# has scripts/update.py (tags from before the migration script cannot run).
#
# Usage (from the root of the repo to update):
#   bash run.sh --check                          # preview
#   bash run.sh --yes                            # apply
#   bash run.sh --check --ref feature/my-branch  # a branch or specific tag
#   TEMPLATE=<url> REF=<ref> bash run.sh --check
#
# Needs: git, uv. Pure shell + git.
set -euo pipefail

TEMPLATE="${TEMPLATE:-https://github.com/Municipality-of-Rotterdam/raptor.git}"
REF="${REF:-}"

# --ref on the command line wins over REF=; it is taken out of the arguments
# here and passed on once below.
args=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --ref) [[ $# -ge 2 ]] || { echo "ERROR: --ref needs a value" >&2; exit 1; }
           REF="$2"; shift 2 ;;
    --ref=*) REF="${1#--ref=}"; shift ;;
    # --template is TEMPLATE: the clone and the migration target must agree
    --template) [[ $# -ge 2 ]] || { echo "ERROR: --template needs a value" >&2; exit 1; }
                TEMPLATE="$2"; shift 2 ;;
    --template=*) TEMPLATE="${1#--template=}"; shift ;;
    *) args+=("$1"); shift ;;
  esac
done

# The repo to update is wherever the user ran this from; update.py defaults
# --repo to its own cwd, which is the template clone, so pass it explicitly.
REPO="$(pwd -P)"

command -v git >/dev/null || { echo "ERROR: git not found" >&2; exit 1; }
command -v uv  >/dev/null || { echo "ERROR: uv not found (curl -LsSf https://astral.sh/uv/install.sh | sh)" >&2; exit 1; }

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

echo "cloning $TEMPLATE ..." >&2
git clone --quiet --no-local "$TEMPLATE" "$work/template"
tpl="$work/template"

if [[ -z "$REF" ]]; then
  # newest tag that can run the update: has scripts/update.py (and so is a
  # copier template too)
  while read -r tag; do
    [[ "$tag" == *'^{}' ]] && continue
    if git -C "$tpl" cat-file -e "$tag:scripts/update.py" 2>/dev/null; then
      REF="$tag"; break
    fi
  done < <(git -C "$tpl" for-each-ref --sort=-v:refname --format='%(refname:short)' refs/tags)
  if [[ -z "$REF" ]]; then
    echo "ERROR: no tag of $TEMPLATE has scripts/update.py yet." >&2
    branches="$(git -C "$tpl" for-each-ref --format='%(refname:lstrip=3)' refs/remotes/origin \
      | while read -r b; do [[ "$b" == HEAD ]] && continue
          if git -C "$tpl" cat-file -e "origin/$b:scripts/update.py" 2>/dev/null; then echo "  $b"; fi
        done)" || true
    if [[ -n "$branches" ]]; then
      echo "Branches that have it (pass one with --ref <branch>):" >&2
      echo "$branches" >&2
    fi
    exit 1
  fi
fi

git -C "$tpl" checkout --quiet "$REF" || { echo "ERROR: ref '$REF' not found in $TEMPLATE" >&2; exit 1; }
[[ -f "$tpl/scripts/update.py" ]] || { echo "ERROR: $TEMPLATE @ $REF has no scripts/update.py; pick a newer --ref" >&2; exit 1; }
echo "running update.py from $TEMPLATE @ $REF" >&2

# no exec: the EXIT trap must still clean up the clone
cd "$tpl"
status=0
uv run --no-project --python 3.11 scripts/update.py --repo "$REPO" --template "$TEMPLATE" --ref "$REF" ${args[@]+"${args[@]}"} || status=$?
exit "$status"
