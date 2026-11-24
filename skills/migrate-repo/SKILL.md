---
name: migrate-repo
description: Update any raptor-generated repo to the latest raptor. For repos created with the old cookiecutter template (no .copier-answers.yml) it performs the one-time migration to copier; for repos already on copier it just runs copier update. Use when asked to "migrate a repo to copier", "update an old repo", "bring a repo up to the latest raptor", "migrate to copier", or when copier update fails because a repo has no .copier-answers.yml.
compatibility: "Needs a shell with git, uv and copier. No local raptor checkout required: the migration script is fetched from the remote template."
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
from the remote, checks out one ref and runs `update.py` from it, passing the
same ref and template on. The migration script that runs and the template it
migrates to are therefore always the same version.

**Safety rules:**
- Always `--check` (dry run) first and show the user the detected answers and
  the target ref before writing.
- Never run `--yes` without the user's go-ahead, and never push.
- The migration only rewrites *tracked* files; untracked files are left alone.
  It refuses to run if tracked files have uncommitted changes — ask the user to
  commit or `git stash` them first. The copier route (`copier update`) is stricter:
  it also refuses on untracked files, so ask the user to commit, move or
  `git stash -u` them.
- Migrate from a branch that is up to date with the remote's default branch.
  `--check` warns and `--yes` refuses when HEAD is behind it, because the PR
  back onto that branch re-conflicts with the commits missed. If it warns,
  report this to the user and suggest `git fetch && git rebase origin/<default>`
  (or merging it) before migrating; only pass `--allow-behind` when the user
  explicitly wants to proceed anyway.

## 1. Preview (read-only)

Run from the root of the repo to update. `--template` (or `TEMPLATE=`) defaults
to the raptor repo; `--ref` (or `REF=`) selects the template ref. The default is
the newest tag that contains `scripts/update.py`. If no tag has it yet, `run.sh`
stops and lists the branches that do: pass one with `--ref <branch>`.

```bash
timeout 900 bash <this skill's dir>/scripts/run.sh --check
# or, with a local raptor checkout (runs its working tree, uncommitted changes included):
uv run --no-project --python 3.11 <raptor>/scripts/update.py --check --template <raptor> --ref <ref>
```

Show the user, and get them to confirm:
- the `repo_type:` line, including the signals that decided it. A project repo
  (AML deployments, `[tool.uv] package = false`) migrated as a package repo gets
  its deployment pipelines deleted and a fake `src/<pkg>` added, so check this first;
- the `answers:` line (repo/package/project name, `type_deployment` for project
  repos, CI provider, DevOps org / project / feed, agent pool, author and user names).
  `repo_name` comes from the `origin` remote (a `repo_name:` line says so when the
  folder name differs, e.g. a `_3` clone);
- the `target:` ref;
- the `preview:` section: the trial merge (done in memory, nothing written) lists
  the files `--yes` would leave conflicted, delete and add. Many deletions of the
  repo's own files, or template example files appearing, usually mean a wrong answer.
  Conflicts that differ only in file mode are left out: `--yes` keeps the repo's version;
- the `check:` lines, if shown: added files that likely clash with the repo — a name
  that differs only in case from an existing file (e.g. `taskfile.yml` next to
  `Taskfile.yml`: keep one), template examples, and template tests next to the repo's
  own (they import the template's example code). Ask the user whether to keep them;
- the `pipelines:` section, if shown: a package repo with the old single pipeline
  (`azure-pipelines.yml` -> `devops_pipelines/templates/main.yml`). By default `--yes`
  switches it to the template's `ci` / `cd` / `release` pipelines and removes the listed
  old files. **Ask the user** whether to switch or keep the old pipeline
  (`--keep-old-pipelines`), before `--yes`. A `WARNING: tag … is not on github.com/…`
  there means the new pipelines can't fetch raptor's CI steps yet: tell the user;
- the `ci-warn:` lines, if shown: things this repo relies on that raptor's new CI
  steps don't do (no extras, no git submodules, no `.env`, no `release/*` builds, AML
  environment registration off). Show them with the switch question: each needs a
  repo-specific fix before the new CI passes, or is a reason to keep the old pipeline.
  Don't fix them on your own; ask the user.

Fix a wrong answer with `-d key=value` (repeatable), e.g. `-d repo_type=project_repo`
or `-d "user_name=Firstname Surname"`. If the template rejects a detected answer,
`--check` stops with the key and the reason; ask the user for the right value.

## 2. Apply

```bash
timeout 900 bash <this skill's dir>/scripts/run.sh --yes
```

(add `--keep-old-pipelines` if the user chose to keep the old pipeline.)

This creates the `migrate-to-copier` branch and merges **without committing**: the
pipeline switch is applied to the merge, and the hooks run before the commit. Two outcomes:

- **No conflicts** — run the hooks (below), then `git commit --no-edit`; report the
  branch and the review command `git diff <original-branch>..migrate-to-copier`.
- **Conflicts** — expected for template files the repo customized. For each, the
  template's side is what a fresh repo would have; keep the repo's own code where
  it matters. Resolve in the working tree, then `git add <files> && git commit`
  (not `git add -A`: the template may change `.gitignore` and expose local files):
  ```bash
  git checkout --theirs <file>   # accept the fresh template
  git checkout --ours   <file>   # keep the repo's customized version
  git rm <file>                  # the template deleted it
  ```
  Template *example* files (e.g. `component_a`, `example_package`, batch/online
  examples) that the repo deliberately deleted show up as modify/delete conflicts
  or as additions: keep them deleted. Don't resolve deployment pipelines
  (`devops_pipelines/`, `aml_deployments/`) by picking a side wholesale without
  the user: they carry the repo's production settings.

Before committing, run the repo's hooks over everything:
`uv run prek run --all-files` (or `pre-commit run --all-files`). The template
may switch on new hooks (mypy, schema checks) that fail on existing code, and
the CI pre-commit stage would then block deployment.

**Start over** (the migration only created a branch, nothing is committed):
```bash
git merge --abort
git checkout <original-branch>
git branch -D migrate-to-copier
```

## 3. Finish

Before the PR, a package repo needs a new version: `cd` publishes the package, and the
PR's `ci` build fails with "Version already exists in feed view" on an unchanged
version. Bump the minor version with `uv version --bump minor` (it also updates
`uv.lock`; with a private index: `uv run --env-file .env -- uv version --bump minor`)
and add a `## [x.y.z] - <date>` section to `changelog.md` (template switch, pipeline
switch, removed files). Ask the user before committing it.

Review the diff, then open a PR from `migrate-to-copier`. From then on the repo
is a normal copier repo: `copier update --trust --vcs-ref <ref>` (or this same
command) keeps it current.

## 4. DevOps pipelines (only after a pipeline switch)

The repo now has `ci` / `cd` / `release` ymls, but DevOps still runs the old pipeline,
and the build validation on `develop`/`main` still points at it: the PR would fail on
the missing `azure-pipelines.yml`. These steps change Azure DevOps: **offer** each one,
show the exact command, and run it only after the user's OK. Never merge, never push.

Setup: run the new-repo preflight for `RAPTOR`, `T` (raptor's taskfile) and `GIT_ROOT_HTTPS`:
`bash <new-repo skill dir>/scripts/preflight.sh --dir <repo>` (it also checks the `az` login).
Below `TASK="timeout 900 task -t $T"`, `DV="REPO_NAME=<repo> GIT_ROOT_HTTPS=<GIT_ROOT_HTTPS>"`,
run in `<repo>`. `<repo>` is the repo's name in DevOps (the last part of the `origin` URL);
check it against the preflight's `REPO_NAME`. `task --dry` is **not** read-only here: it runs the tasks' `status:`
checks, which call `az`.

**A. After the user pushed the migration branch** (`git ls-remote --heads origin <branch>`):
1. Read-only, show the user: the old pipeline (id, name, folder):
   `az pipelines list --repository <repo> --repository-type tfsgit --org ... -p ... --query "[].[id,name,path,process.yamlFilename]" -o tsv`
   (the yml isn't in that list: `az pipelines show --id <id> --query process.yamlFilename`),
   and the policies on `develop` and `main`:
   `az repos policy list --repository-id <id> --branch <b> --query "[].[id,type.displayName,settings.buildDefinitionId]" -o tsv`.
2. `$TASK --yes create_new_repo:setup_build_pipelines_devops $DV PIPELINES="ci cd release" PIPELINE_BRANCH=<branch> PIPELINE_FOLDER='<old pipeline folder>'`
3. `$TASK --yes create_new_repo:authorize_pipeline_resources_devops $DV`
   (a WARNING that the service connection `github-ci-templates` is "not found" can just
   mean the user can't see it; the validation below shows whether GitHub is reachable).
   Then, read-only, validate each new pipeline's yml before switching the build check: the
   preview call compiles the yml with its templates and starts nothing. `yamlOverride`
   makes it check the local file, so it also works before a fix is pushed:
   ```bash
   python3 -c "import json; print(json.dumps({'previewRun': True, 'yamlOverride': open('devops_pipelines/templates/ci.yml').read(), 'resources': {'repositories': {'self': {'refName': 'refs/heads/<branch>'}}}}))" > preview_body.json
   az devops invoke --area pipelines --resource preview --route-parameters project=<project> pipelineId=<ci id> \
     --http-method POST --in-file preview_body.json --api-version 7.1-preview --org <org url> --query finalYaml -o tsv | head
   ```
   (same for `cd` and `release`; remove `preview_body.json` afterwards). An error here (e.g. a raptor tag
   that isn't on GitHub) would make every PR fail once step 4 makes `ci` required: report it, don't do step 4.
4. `$TASK --yes create_new_repo:setup_build_policies_devops $DV POLICY_BRANCHES=develop REPLACE_BUILD=true`
   (switches the existing build validation to `<repo> (ci)`; it also adds a missing
   reviewer or comment policy: tell the user which, from step 1).

The PR is then validated by the new `ci`: the first real run. On failure, fix it on the
branch (often one of the `ci-warn` items) and push again. The AI review stage may report
"LLM response hit max_tokens limit" on a large migration diff: it doesn't block the PR.

**B. After the user merged the PR:**
5. `$TASK --yes create_new_repo:set_pipelines_branch_devops $DV`
6. `$TASK --yes create_new_repo:setup_build_policies_devops $DV POLICY_BRANCHES=main REPLACE_BUILD=true`

**C. After the next `develop` -> `main` merge** (`main` and `release/*` run the old pipeline
from their own `azure-pipelines.yml` until then):
7. `$TASK --yes create_new_repo:remove_old_pipeline_devops $DV` (refuses while `origin/main`
   or an `origin/release/*` branch still has `azure-pipelines.yml`).

After each step, check its effect read-only (the queries of step 1, `az pipelines show`)
and report: these `az` calls have not been verified on every org setup. On a failure, stop
and report; don't work around it.
