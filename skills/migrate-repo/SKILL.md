---
name: migrate-repo
description: Update any raptor-generated repo to the latest raptor. For repos created with the old cookiecutter template (no .copier-answers.yml) it performs the one-time migration to copier; for repos already on copier it just runs copier update. Use when asked to "migrate a repo to copier", "update an old repo", "bring a repo up to the latest raptor", "migrate to copier", or when copier update fails because a repo has no .copier-answers.yml.
compatibility: Needs a shell with git, uv and copier. No local raptor checkout required: the migration script is fetched from the remote template.
---

# Migrate / update a raptor repo

Bring one repo up to the latest raptor. The entry point `scripts/update.py` in
the raptor template routes on the repo's type, so you run the same command either way:

- **copier-era repo** (has `.copier-answers.yml`): runs `copier update --trust`.
- **cookiecutter-era repo** (no `.copier-answers.yml`): `copier update` cannot
  start from it, so this fetches `scripts/migrate_to_copier.py` from the remote
  template at its newest copier tag and runs that one-time migration. It renders
  the target template into a scratch dir and does a git 3-way merge
  (base = the repo's first commit, ours = HEAD, theirs = fresh template), then
  writes `.copier-answers.yml` so every later update is native `copier update`.

The migration runs on a new branch (`migrate-to-copier`); the current branch is
never modified and nothing is pushed.

**Nothing is local**: `scripts/run.sh` (next to this file) clones the template
from the remote and runs `update.py` from it, so the latest version of the
migration script is always the one that runs.

**Safety rules:**
- Always `--check` (dry run) first and show the user the detected answers and
  the target ref before writing.
- Never run `--yes` without the user's go-ahead, and never push.
- The migration only rewrites *tracked* files; untracked files are left alone.
  It refuses to run if tracked files have uncommitted changes — ask the user to
  commit or `git stash` them first.
- Migrate from a branch that is up to date with the remote's default branch.
  `--check` warns and `--yes` refuses when HEAD is behind it, because the PR
  back onto that branch re-conflicts with the commits missed. If it warns,
  report this to the user and suggest `git fetch && git rebase origin/<default>`
  (or merging it) before migrating; only pass `--allow-behind` when the user
  explicitly wants to proceed anyway.

## 1. Preview (read-only)

Run from the root of the repo to update. `--template` defaults to the raptor
repo; `--ref` selects the template ref (default: its newest copier tag — pass a
branch like `feature/migrate-skill` while the migration script is not yet in a
release tag):

```bash
timeout 900 bash <this skill's dir>/scripts/run.sh --check
# or, with a local raptor checkout:
uv run --python 3.11 <raptor>/scripts/update.py --check
```

Show the user the `answers:` line (repo/package name, CI provider, DevOps org /
project / feed, agent pool, authors) and the `target:` ref. Fix a wrong answer
with `-d key=value` (repeatable), e.g. `-d repo_name=pkg_mypackage`.

## 2. Apply

```bash
timeout 900 bash <this skill's dir>/scripts/run.sh --yes
```

This creates the `migrate-to-copier` branch and merges. Two outcomes:

- **Clean merge** — report the branch and the review command
  `git diff <original-branch>..migrate-to-copier`.
- **Conflicts** — expected for template files the repo customized. For each, the
  template's side is what a fresh repo would have; keep the repo's own code where
  it matters. Resolve in the working tree, then `git add -A && git commit`:
  ```bash
  git checkout --theirs <file>   # accept the fresh template
  git checkout --ours   <file>   # keep the repo's customized version
  git rm <file>                  # the template deleted it
  ```

## 3. Finish

Review the diff, then open a PR from `migrate-to-copier`. From then on the repo
is a normal copier repo: `copier update --trust --vcs-ref <ref>` (or this same
command) keeps it current.
