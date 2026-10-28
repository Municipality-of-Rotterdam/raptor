#!/usr/bin/env bash
# Preflight for the new-repo skill: read-only checks of tools, config files, the raptor clone, the mode (new or
# existing repo), the git roots and the Azure DevOps login. Changes nothing (only a `git fetch` of the raptor clone).
#
# Usage: preflight.sh [--dir <dir>] [--raptor <raptor clone>] [--no-auth]
#   --dir      the repo (existing repo) or the parent directory for the new repo, default: current directory
#   --raptor   local raptor clone, default: the first one of: the clone holding this script, $RAPTOR_DIR,
#              <dir>/raptor, <dir>/../raptor, ~/repos/raptor
#   --no-auth  skip the Azure DevOps login check
#
# Output: one line per check (OK / INFO / WARN / STOP), then KEY=VALUE lines for the skill, then RESULT=...
# Exit code: 0 = all OK, 2 = only warnings (ask the user to continue or stop), 1 = stop (something required is missing).
# Never prints ~/taskfile.env itself, only the values of GIT_ROOT and GIT_ROOT_HTTPS.

# started with `sh preflight.sh` (dash on Ubuntu): run it again with bash
if [ -z "${BASH_VERSION:-}" ]; then exec bash "$0" "$@"; fi

set -u

DIR="$PWD"
RAPTOR=""
AUTH=1
while [ $# -gt 0 ]; do
  case "$1" in
    --dir) DIR="$2"; shift 2 ;;
    --raptor) RAPTOR="$2"; shift 2 ;;
    --no-auth) AUTH=0; shift ;;
    -h|--help) sed -n '2,13p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 64 ;;
  esac
done

N_STOP=0
N_WARN=0
ok()   { echo "OK    $*"; }
info() { echo "INFO  $*"; }
warn() { echo "WARN  $*"; N_WARN=$((N_WARN + 1)); }
stop() { echo "STOP  $*"; N_STOP=$((N_STOP + 1)); }

# value of KEY in a KEY=VALUE file (inline " # comment" and quotes removed)
env_value() {
  grep -E "^[[:space:]]*(export[[:space:]]+)?$1=" "$2" 2>/dev/null | tail -1 |
    sed -E "s/^[^=]*=//; s/[[:space:]]+#.*$//; s/^[[:space:]]*//; s/[[:space:]]*$//; s/^[\"']//; s/[\"']$//"
}
# value of a top level key in .copier-answers.yml
answer() {
  grep -E "^$1:" "$2" 2>/dev/null | head -1 | sed -E "s/^[^:]*:[[:space:]]*//; s/^[\"']//; s/[\"']$//"
}

if [ ! -d "$DIR" ]; then
  echo "STOP  directory $DIR does not exist"
  echo "RESULT=STOP"
  exit 1
fi
DIR="$(cd "$DIR" && pwd)"

# ---------- mode ----------
if [ -f "$DIR/.copier-answers.yml" ]; then
  MODE=existing
  ok "mode: existing repo ($DIR has .copier-answers.yml)"
elif [ -d "$DIR/.git" ] && [ -f "$DIR/copier.yaml" ]; then
  MODE=unsupported
  stop "$DIR is the raptor template itself: ask for the parent directory of the new repo (--dir), or the existing repo"
elif [ -d "$DIR/.git" ]; then
  MODE=unsupported
  stop "$DIR is a git repo without .copier-answers.yml (e.g. made with cookiecutter): out of scope for this skill"
else
  MODE=new
  ok "mode: new repo, created in $DIR"
fi

# ---------- tools ----------
check_tool() {  # name, version command
  local out
  if out=$(timeout 60 bash -c "$2" 2>/dev/null | head -1) && [ -n "$out" ]; then
    ok "$1: $out"
  else
    stop "$1 is not installed (or '$2' fails)"
  fi
}
check_tool git "git --version"
check_tool task "task --version"
check_tool uv "uv --version"
check_tool direnv "direnv --version"
[ "$MODE" = new ] && check_tool copier "copier --version"
check_tool az "az version --query '\"azure-cli\"' -o tsv"
AZ_DEVOPS=0
if command -v az >/dev/null 2>&1; then
  if timeout 60 az extension show -n azure-devops --query version -o tsv >/dev/null 2>&1; then
    AZ_DEVOPS=1
    ok "az extension azure-devops"
  else
    warn "az extension azure-devops is missing: the create_new_repo:install_az_devops task installs it (ask first), then run this script again"
  fi
fi

# ---------- config files ----------
TASKFILE_ENV="$HOME/taskfile.env"
ENV_GIT_ROOT=""
ENV_GIT_ROOT_HTTPS=""
if [ -f "$TASKFILE_ENV" ]; then
  ENV_GIT_ROOT=$(env_value GIT_ROOT "$TASKFILE_ENV")
  ENV_GIT_ROOT_HTTPS=$(env_value GIT_ROOT_HTTPS "$TASKFILE_ENV")
  for key in GIT_ROOT GIT_ROOT_HTTPS; do
    val=$([ "$key" = GIT_ROOT ] && echo "$ENV_GIT_ROOT" || echo "$ENV_GIT_ROOT_HTTPS")
    if [ -n "$val" ]; then
      ok "$key in ~/taskfile.env"
    elif [ "$MODE" = new ]; then
      stop "$key is not set in ~/taskfile.env (needed for a new repo)"
    else
      info "$key is not set in ~/taskfile.env (not needed, taken from the repo)"
    fi
  done
elif [ "$MODE" = new ]; then
  stop "~/taskfile.env does not exist (needed for a new repo: GIT_ROOT and GIT_ROOT_HTTPS)"
else
  info "~/taskfile.env does not exist (not needed for an existing repo)"
fi

if [ -f "$HOME/.taskrc.yml" ] || [ -f "$HOME/.taskrc.yaml" ]; then
  ok "~/.taskrc.yml"
else
  warn "~/.taskrc.yml does not exist (optional, but strongly recommended: taskfile config, needed to run raptor's tasks remotely)"
fi

# ---------- raptor clone ----------
has_tasks() { [ -f "$1/copier.yaml" ] && grep -q 'create_repo_devops' "$1/.taskfile/tasks/create_new_repo/taskfile.yml" 2>/dev/null; }
if [ -z "$RAPTOR" ]; then
  SCRIPT_DIR="$(cd "$(dirname "$(realpath "$0")")" && pwd)"
  for c in "$SCRIPT_DIR/../../.." "${RAPTOR_DIR:-}" "$DIR/raptor" "$DIR/../raptor" "$HOME/repos/raptor"; do
    if [ -n "$c" ] && has_tasks "$c"; then RAPTOR="$(cd "$c" && pwd)"; break; fi
  done
fi
RAPTOR_BEHIND=""
if [ -n "$RAPTOR" ] && has_tasks "$RAPTOR"; then
  RAPTOR="$(cd "$RAPTOR" && pwd)"
  branch=$(git -C "$RAPTOR" rev-parse --abbrev-ref HEAD 2>/dev/null)
  if timeout 60 git -C "$RAPTOR" fetch -q 2>/dev/null; then
    RAPTOR_BEHIND=$(git -C "$RAPTOR" rev-list --count 'HEAD..@{upstream}' 2>/dev/null || echo "")
  fi
  if [ -z "$RAPTOR_BEHIND" ]; then
    info "raptor clone: $RAPTOR (branch $branch, could not compare with its upstream)"
  elif [ "$RAPTOR_BEHIND" -gt 0 ]; then
    info "raptor clone: $RAPTOR (branch $branch, $RAPTOR_BEHIND commits behind its upstream: ask whether to pull)"
  else
    ok "raptor clone: $RAPTOR (branch $branch, up to date)"
  fi
else
  stop "no local raptor clone found (with copier.yaml and the create_new_repo tasks): ask where it is (--raptor <dir>), or offer to clone <GIT_ROOT>/raptor"
  RAPTOR=""
fi

# ---------- copier settings ----------
COPIER_SETTINGS=""
if [ "$MODE" = new ]; then
  COPIER_SETTINGS="${COPIER_SETTINGS_PATH:-$HOME/.config/copier/settings.yml}"
  if [ -f "$COPIER_SETTINGS" ]; then
    ok "copier settings: $COPIER_SETTINGS"
  else
    warn "copier settings $COPIER_SETTINGS does not exist (optional, but strongly recommended: your default answers; without it they come from a sibling repo or git config). The user creates it:"
    # the example lives in raptor's setup_copier_config task (it only prints, changes nothing)
    if [ -n "$RAPTOR" ]; then
      timeout 60 task -t "$RAPTOR/.taskfile/taskfile_main.yml" --silent setup_compute_instance:setup_copier_config 2>/dev/null |
        sed 's/^/      /'
    fi
    COPIER_SETTINGS=""
  fi
fi

# ---------- git roots ----------
GIT_ROOT="$ENV_GIT_ROOT"
GIT_ROOT_HTTPS="$ENV_GIT_ROOT_HTTPS"
REPO_NAME=""
REPO_TYPE=""
if [ "$MODE" = existing ]; then
  A="$DIR/.copier-answers.yml"
  REPO_NAME=$(answer repo_name "$A")
  REPO_TYPE=$(answer repo_type "$A")
  org=$(answer devops_organisation_name "$A")
  project=$(answer devops_project_name "$A")
  if [ -n "$org" ] && [ -n "$project" ]; then
    ans_https="https://dev.azure.com/$org/$project"
    ans_ssh="git@ssh.dev.azure.com:v3/$org/$project"
    if [ -n "$GIT_ROOT_HTTPS" ] && [ "$GIT_ROOT_HTTPS" != "$ans_https" ]; then
      warn "GIT_ROOT_HTTPS differs: ~/taskfile.env has $GIT_ROOT_HTTPS, the answers file gives $ans_https: ask which one"
    fi
    GIT_ROOT_HTTPS="$ans_https"
    GIT_ROOT="$ans_ssh"
  fi
  origin=$(git -C "$DIR" remote get-url origin 2>/dev/null || echo "")
  if [ -n "$origin" ] && [ -n "$GIT_ROOT" ]; then
    case "$origin" in
      "$GIT_ROOT"/*|"$GIT_ROOT_HTTPS"/*|https://*@dev.azure.com/*) ;;
      *) warn "origin $origin is not in $GIT_ROOT: ask which one is right" ;;
    esac
  fi
fi
if [ -z "$GIT_ROOT_HTTPS" ] && [ "$MODE" = existing ]; then
  stop "GIT_ROOT_HTTPS is unknown (not in ~/taskfile.env, nor in the answers file)"
fi

# ---------- azure devops login ----------
if [ "$AUTH" = 0 ]; then
  info "Azure DevOps login: not checked (--no-auth)"
elif [ "$AZ_DEVOPS" = 1 ] && case "$GIT_ROOT_HTTPS" in https://dev.azure.com/*/*) true ;; *) false ;; esac; then
  org_url="${GIT_ROOT_HTTPS%/*}"
  project="${GIT_ROOT_HTTPS##*/}"
  if out=$(timeout 60 az devops project show --org "$org_url" -p "$project" --query name -o tsv 2>&1); then
    ok "Azure DevOps login: project $out"
  elif echo "$out" | grep -qiE 'AADSTS|az login|login command|credentials'; then
    tenant=$(timeout 30 az account show --query tenantId -o tsv 2>/dev/null)
    stop "not logged in to Azure DevOps: ask the user to run in their own terminal: az login --tenant ${tenant:-<tenant id>} --use-device-code"
  else
    stop "Azure DevOps project $project in $org_url not reachable: $(echo "$out" | head -1)"
  fi
elif [ "$AZ_DEVOPS" = 1 ] && [ -n "$GIT_ROOT_HTTPS" ]; then
  info "Azure DevOps login: not checked ($GIT_ROOT_HTTPS is not an Azure DevOps url)"
fi

# ---------- result ----------
echo
echo "MODE=$MODE"
echo "DIR=$DIR"
echo "RAPTOR=$RAPTOR"
echo "T=${RAPTOR:+$RAPTOR/.taskfile/taskfile_main.yml}"
echo "RAPTOR_BEHIND=$RAPTOR_BEHIND"
echo "GIT_ROOT=$GIT_ROOT"
echo "GIT_ROOT_HTTPS=$GIT_ROOT_HTTPS"
echo "COPIER_SETTINGS=${COPIER_SETTINGS:-}"
echo "REPO_NAME=$REPO_NAME"
echo "REPO_TYPE=$REPO_TYPE"
if [ "$N_STOP" -gt 0 ] || [ "$N_WARN" -gt 0 ]; then
  echo
  echo "HINT  How to install the tools and set up ~/taskfile.env, ~/.taskrc.yml and the copier settings is described in"
  echo "      the company documentation (Confluence) and in .taskfile/readme.md of raptor. 'task setup_compute_instance'"
  echo "      installs most tools, 'task setup_compute_instance:setup_copier_config' shows an example of the copier settings."
fi
if [ "$N_STOP" -gt 0 ]; then
  echo "RESULT=STOP"
  exit 1
elif [ "$N_WARN" -gt 0 ]; then
  echo "RESULT=WARN"
  exit 2
fi
echo "RESULT=OK"
exit 0
