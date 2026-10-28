---
name: new-repo
description: Create a new Gemeente Rotterdam repo (package_repo pkg_* or project_repo) from the raptor copier template, or finish the setup of an existing copier repo, and set it up in Azure DevOps (repo, push, pipelines, pipeline permissions, default branch, branch policies, status badge) by running raptor's taskfile tasks. Steps that are already done are skipped. Use when asked for a "new repo", "nieuwe repo", "create repo", "create_new_repo", to set up a new package/project repo, or to set up / finish / check the environment or DevOps setup of an existing raptor repo.
compatibility: Needs a shell with git, task, copier, uv, direnv and the Azure CLI (azure-devops extension), and a local raptor clone.
---

# New (or existing) raptor repo + Azure DevOps setup

The work is done by raptor's taskfile tasks (`.taskfile/tasks/create_new_repo/taskfile.yml`, `setup_repo`). This
skill gathers the inputs, checks what is already done, asks for approval, runs the tasks, and only steps in when a
task fails: read the task, fix the cause, re-run it.

This skill lives in the raptor repo (`skills/new-repo`, Agent Skills format) and works in any agent that supports
skills. Installation: see `skills/README.md` in raptor.

**Asking the user**: where this skill says "ask", use the agent's structured question tool if it has one (options,
multiselect, previews), otherwise a numbered list of options in chat, and wait for the answer. A "preview" is shown in
the question tool's preview field, or else as a code block in the message just above the options.

**Safety rules:**
- The only commit is the template's own `init` commit (copier tasks, new repos only); the only push is the one
  approved in gate 1. Everything else is edited and staged, never committed or pushed.
- Stage only files the tasks changed (compare `git status --short` before and after). In an existing repo never
  `git add -A`: that would stage the user's own work.
- No change in Azure DevOps without approval: gate 1 (create repo + push) is a yes/no, gate 2 is Yes, all / Partially
  / No (Partially → multiselect).
  Tasks have `prompt:`s; pass `--yes` only for steps the user approved. Read-only calls (`az` show/list/GET,
  `task --status`) need no approval.
- **Never redo a step that is done.** Check every step first (section "Done checks") and offer or run only the
  missing ones. If a check can't tell (error, ambiguous), ask instead of running.
- Wrap network calls (`az`, `task` runs that call az/git/copier) in `timeout`. Never print `.env` or tokens.

## 0. Mode and preflight (read-only)

Run the preflight script of this skill (`scripts/preflight.sh` next to this file; it changes nothing) and do not
replace it with your own checks:
```bash
timeout 600 bash <this skill's dir>/scripts/preflight.sh --dir <the directory the user names, else the cwd>
# add --raptor <dir> when the user names a raptor clone
```
Show the user its `STOP`, `WARN` and `HINT` lines as they are, then act on the exit code:
- **1 (`RESULT=STOP`)**: stop here, change nothing. For a missing tool, offer to run the matching
  `setup_compute_instance:*` task (ask first); for a missing Azure login, ask the user to run the `az login` command
  from the output in their own terminal; with no raptor clone found, ask where it is (`--raptor`) or offer to clone
  `<GIT_ROOT>/raptor` (ask first). Then run the script again.
- **2 (`RESULT=WARN`)**: ask **Continue** / **Stop**. Stop: the user fixes it first (e.g. creates `~/.taskrc.yml` or
  the copier settings file like the example in the output, with the values from the company documentation) and asks
  again. A WARN that says
  "ask which one" (git roots differ) needs that answer before going on. A WARN about the `azure-devops` extension:
  offer the `create_new_repo:install_az_devops` task (ask first), then run the script again.
- **0 (`RESULT=OK`)**: go on.
- Never create or edit `~/taskfile.env`, `~/.taskrc.yml` or the copier settings yourself.

Use the `KEY=VALUE` lines of the output from here on, never your own guesses:
- `MODE=new` → step 1; `MODE=existing` → step 3, with `REPO_NAME`, `REPO_TYPE` from the output and the rest from
  `<DIR>/.copier-answers.yml`.
- `RAPTOR`, `T` (taskfile), `GIT_ROOT`, `GIT_ROOT_HTTPS`: use as is, never hardcode them.
- `RAPTOR_BEHIND` > 0: ask whether to pull the raptor clone.
- `COPIER_SETTINGS` (new repo): if set, its `defaults` go before the sibling answers for the personal answers
  (`user_name`, `user_email`, `author_*`), see step 1.

Below, `TASK="timeout 900 task -t $T"` and `DV="REPO_NAME=<repo> GIT_ROOT_HTTPS=<GIT_ROOT_HTTPS>"`, run in `<repo>`.

## Done checks

Taskfile first: every DevOps task has a `status:`, and `task --status` runs it without doing anything (exit 0 = done):
```bash
$TASK --status create_new_repo:create_repo_devops $DV
$TASK --status create_new_repo:add_remote $DV GIT_ROOT=<GIT_ROOT>             # develop is on the remote
$TASK --status create_new_repo:setup_build_pipeline_devops $DV PIPELINE=<name>  # a pipeline of this repo runs <name>.yml (any name)
$TASK --status create_new_repo:setup_default_branch_devops $DV
$TASK --status create_new_repo:setup_build_policy_devops $DV BRANCH=<branch>    # all 3 policy types on the branch
$TASK --status create_new_repo:add_status_badge_devops $DV                      # README has no "status badge" instructions
```
Not covered by a status, checked by the task itself: pipeline permissions (it only grants what is missing) and, per
branch, which of the 3 policy types exist (it only adds the missing ones). For gate 2, list the missing policy types:
`az repos policy list --repository-id <id> --branch <b> ... --query '[].type.displayName' -o tsv` (`--branch` is needed:
without it the list is empty).

## 1. Inputs (new repo)

**First ask only** (skip what the arguments already give), short, one line per item, no hints or explanations: repo
type `package_repo` (default) or `project_repo`, name, description (may be empty), for projects `type_deployment`
(none/batch/online/scheduled-pipeline). Ask about the template version only if the newest tag is a prerelease (newest
tag incl. betas: `timeout 30 git ls-remote --tags <src> | sed 's#.*refs/tags/##;/\^{}/d' | sort -V | tail -1`): that
prerelease, the newest stable tag, or (only when `$RAPTOR` is ahead of that tag or dirty) its `HEAD` incl. uncommitted
changes. Do not show the other answers in this first question.

Then, without asking, work out the rest:
- `<parent>`: the directory the user names, else the cwd. Siblings: the newest `<parent>/*/.copier-answers.yml`
  (`ls -t`), else the newest in `$RAPTOR/..`.
- Names for a package (the user may give the name with or without `pkg_`): strip a leading `pkg_` to get the base
  (lowercased, spaces and `-` removed, as `taskfile_main.yml` `REPO_NAME_DIRTY` does); repo name `pkg_<base>`
  (never `pkg_pkg_`), package name `<base>`. For a project: repo name = project name = the name as given (normalized).
- Template source: a git URL, never a local folder (`_src_path` lands in `.copier-answers.yml`; a folder breaks
  `copier update` for colleagues and other machines): `git -C $RAPTOR remote get-url origin`. Only the template version
  `HEAD` (uncommitted changes) needs the local folder `$RAPTOR`; then say so.
- Defaults for the other copier answers from the newest sibling answers file (personal answers from copier's
  `settings.yml` first, see step 0): user/author name+email, `ci_cd`,
  `devops_organisation_name`, `devops_project_name`, `private_agent_name`, `github_service_connection`,
  `package_feed`, `python_version`, `uv_version`, `precommit_version` (not raptor's `copier.yaml` defaults:
  placeholders, old versions). No sibling: user name/email from `git config --global`, the rest from `copier.yaml`
  and `~/taskfile.env`, and ask for what is still a placeholder.
- The target must be free: `<parent>/<repo>` doesn't exist (if it does and has `.copier-answers.yml`, switch to
  existing-repo mode), and `create_repo_devops` is not done (if it is, tell the user and ask before going on).

**Then ask** one question "Generate the repo with these details?" with options **Yes** / **No** / **Run copier
manually**. Put the details in the preview of **Yes** (not in the question text), one per line:
```
Folder:        <parent>/pkg_x                   (full absolute path that will be created)
Repo type:     package_repo
Repo name:     pkg_x
Package name:  x                                (Project name: for a project_repo)
Description:   (empty)
Template:      <src> @ <tag or HEAD>
Python:        3.11
uv:            0.12.1
pre-commit:    3.4.0
Git user:      <user_name> <user_email>
CI/CD:         DevOps                           (just DevOps or GitHub)
```
Put the exact manual command in the preview of **Run copier manually**, and on that answer also print it in the reply
as a code block so it can be copied. The command prefills only what the user answered (type, name, description,
template version) and leaves copier to ask the rest interactively (no `--defaults`), e.g.:
```bash
cd <parent> && copier copy --trust <src> <repo> [--prereleases | --vcs-ref <tag> | --vcs-ref HEAD] \
  --data repo_type=<type> --data "description=<...>"
```
Tell the user to run it in their own terminal (copier prompts interactively, which the agent can't answer) and to
say when it's done; then continue at step 3 in existing-repo mode (check the `init` commit as in step 2). **No** →
ask what to change.

## 2. Generate (new repo)

In `<parent>`:
```bash
$TASK --yes create_new_repo:copier REPO_NAME=<repo> REPO_TYPE=<type> COPIER_URL=<src> \
  COPIER_ARGS='--prereleases --defaults --data "description=<...>" --data "user_name=<...>" ...'
# --prereleases for the newest (pre)release tag; --vcs-ref <tag> for a stable tag; --vcs-ref HEAD for the local HEAD
```
- Every answer as `--data "key=value"` inside COPIER_ARGS; `--defaults` keeps copier from prompting (it would hang).
- The template's tasks run: global `safe.directory`, `git init`, repo-local user, `init` commit on main,
  `checkout -b develop`. Check `git log --oneline --all` (one commit) and branches main + develop.

## 3. Environment

Where the env lives is decided by the disk: on local disk (`findmnt -T . -no FSTYPE` not cifs/smb/nfs/fuse;
`~/cloudfiles/code` on an Azure ML compute instance is cifs) without conda it is `<repo>/.venv`; on a network mount it
is `~/.local/share/uv/envs/<package_name>`; with conda (`USE_CONDA: true` in `taskfile.yml`) the conda env. `.envrc`
(direnv) sets this; never delete it (a colleague may clone the repo onto a mount). Read it first:
- **Disk-aware** (contains `findmnt`, current template): it sets nothing on local disk, so `direnv allow .` is safe on
  any disk; allow it (no "blocked" message on every `cd`) and run tasks via `direnv exec . ...`.
- **Old** (sets `UV_PROJECT_ENVIRONMENT` unconditionally): on local disk do NOT allow it (it would move the env off
  `.venv`); offer to replace it with `$RAPTOR/package_repo/.envrc` (`{{ package_name }}` filled in), edit + stage only.
  On a mount or with conda allow it as is.
- Agent instruction files (AGENTS.md, CLAUDE.md, ...) should not name the env location (it differs per machine); `uv run` finds it.

Run the `setup_repo` subtasks from `$T`, each skips what is done (`status:`). `task -t $T setup_repo` would miss the
repo's own `taskfile.yml` vars, so pass them (`PYTHON_VERSION`, `ENV_NAME`, `UV_SYNC_EXTRA`) from that file:
```bash
for t in register_git_maintenance init_submodules create_uv_env uv_sync precommit_install print_uv_path; do
  direnv exec . timeout 900 task -t $T -d . setup_repo:$t PYTHON_VERSION=<..> ENV_NAME=<..> || break; done
```
- With conda: `create_conda_env` and `print_conda_path` instead. `init_submodules` only when `SUBMODULES` is set; then
  also `precommit_install DIR=<submodule>` per submodule.
- Never recreate an existing env (`create_uv_env` checks `<env>/bin/python`).
- Failures: find the failing subtask in `$RAPTOR/.taskfile/tasks/setup_repo/taskfile.yml`, fix, re-run, report. Ask
  before changing anything global.
- Stage only files this step changed (normally `uv.lock` in a new repo). Report what was done and what was skipped.

## 4. DevOps gate 1: create repo + push

Done checks for `create_repo_devops` and `add_remote`. Both done → skip the gate, say so. Otherwise ask
(Create and push / Cancel), with only the missing steps as a numbered list in the preview of Create and push:
create repo `<repo>` in `<GIT_ROOT_HTTPS>`; add remote `<GIT_ROOT>/<repo>` (if no origin); `git push -u origin --all`
with the branches and their commit counts (new repo: only the template's `init` commit on main and develop). On
approval:
```bash
$TASK create_new_repo:install_az_devops
$TASK --yes create_new_repo:create_repo_devops $DV
$TASK --yes create_new_repo:add_remote $DV GIT_ROOT=<GIT_ROOT>
```
Check with `timeout 60 git ls-remote origin`.

## 5. DevOps gate 2: pipelines, branches, policies

Read-only first:
- Pipelines = the ymls among ci, cd, release, main in `devops_pipelines/templates/` (package: ci cd release;
  project: main). Build validation and badge use ci, or main without ci.yml.
- Done checks for each pipeline, the default branch and both branches' policies (with the missing policy types).
- Folder for new pipelines: this repo's existing pipelines, else the sibling repo's (`repo_name` in the newest sibling
  answers file):
  `az pipelines list --repository <repo or sibling> --repository-type tfsgit --org ... -p ... --query "[].path" -o tsv`
  (none → `\`).

Nothing missing → skip the gate, say so. Otherwise ask one single-select question "Create all of the steps shown
on the right?" with options **Yes, all** / **Partially** / **No**; put every missing step (below) as a numbered,
indented list in the preview of **Yes, all** (question text may render as one line, not as a list). Never ask with
an empty-selection-means-all multiselect: submitting nothing may come back as "did not answer". Only on **Partially**:
a second question with up to two multiselect questions "Which steps to create?", headers "Pipelines" and
"Branches", with only the missing steps as options; each option's description says what the task does. Then confirm in
your reply which steps will run.
- **Pipelines**: one item per missing pipeline `<repo> (<name>)` (in folder `<folder>`, skip first run), plus
  `Authorize pipeline resources` whenever any pipeline exists or will be created (it grants only missing access, only
  for these pipelines, never "all pipelines").
- **Branches**: `Default branch develop`, `Policies on develop`, `Policies on main`, each only if missing; a policy
  option names the missing types (of: 2 reviewers with requestor may approve own changes, comment resolution, build
  validation with the ci/main pipeline; cd/release are no build validation).
- A free-text answer wins over the ticks. No answer or unclear → ask again, never assume.

Run the selected tasks in `<repo>`, in this order, and stop at the first failure (diagnose, fix, re-run):
```bash
$TASK --yes create_new_repo:setup_build_pipelines_devops $DV PIPELINES="<selected names>" PIPELINE_FOLDER='<folder>'
$TASK --yes create_new_repo:authorize_pipeline_resources_devops $DV
$TASK --yes create_new_repo:setup_default_branch_devops $DV
$TASK --yes create_new_repo:setup_build_policies_devops $DV POLICY_BRANCHES="<develop and/or main>"
```
Authorization prints a WARNING when a resource isn't visible or the user lacks the rights (e.g. the GitHub service
connection): then the first run asks "This pipeline needs permission" and they click Permit.

## 6. Status badge (edit + stage only)

If not done: `$TASK create_new_repo:add_status_badge_devops $DV` (replaces the README's "NB: Add ... status badge" blocks
with the ci/main pipeline badge), then `git add README.md`. With policies on develop, the user commits the staged
changes on a branch and opens a PR; that PR is also the first real test of the build validation.

## 7. Summary

Report per step: done now, already done (skipped), skipped by the user, failed. What is staged. Links
`<GIT_ROOT_HTTPS>/_git/<repo>`, `<GIT_ROOT_HTTPS>/_build`, `<GIT_ROOT_HTTPS>/_git/<repo>/branches`. Next for the user:
commit the staged changes on a branch + PR, check `taskfile.yml` vars, select the interpreter `print_uv_path` printed.
