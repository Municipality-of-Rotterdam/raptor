# project_repo template: issues found while migrating sb_routeopt_fisha (2026-11-16)

Found while porting a real scheduled-pipeline project (sb_routeopt_fisha) onto the
`project_repo` template at `feature/migrate-skill`. Paths below are relative to
`project_repo/`; `<dp>` = `{% if ci_cd == 'DevOps' %}devops_pipelines{% endif %}`.
None of these are fixed in the template yet. In sb_routeopt_fisha they are worked
around in its own pipeline files (branch `migrate-to-copier`).

## 1. Code-only component changes don't redeploy the scheduled pipeline

`<dp>/templates/scheduled_pipeline_deployment.yml:14-19`: the `[pipelinejob]` and
`[schedule]` ChangedFiles rules only watch `aml_deployments/components/**/*.yml`.
A change to only `component_script.py` makes `create_components.yml` register a
new component version (its rule is `components/<name>/*`), but no new
pipelinejob or schedule gets created. The schedule pins the pipelinejob it was
created from, and so the component version, so the schedule keeps running the
old code.

Fix: watch the whole component folder, i.e. `aml_deployments/components/**`
instead of `**/*.yml`, in both rules. Consider adding `devops_pipelines/**` too:
the pipeline passes settings (compute, env vars) to the job via `--set`, so a
change there should also recreate the job and the schedule.

## 2. `force_deploy` is ignored by the create steps

`<dp>/templates/create_environments.yml:30` and `create_components.yml:29`: the
step condition is only `eq(variables['CheckChanges...'], 'true')`. The same goes
for both steps in `scheduled_pipeline_deployment.yml`. A manual run with
`force_deploy=true` (meant to "deploy now, before merging") therefore skips
everything that didn't change in the last commit. The parameter is never passed
down from `main.yml`.

Fix: add a `force_deploy` boolean parameter (default `false`) to the three
templates, pass `force_deploy: ${{ parameters.force_deploy }}` from `main.yml`,
and use:
```yaml
condition: >
  and(succeeded(), or(eq(variables['CheckChangesComponents.${{ component.name }}'], 'true'),
                      ${{ eq(parameters.force_deploy, true) }}))
```
Adding `succeeded()` also stops a later step from running after an earlier one failed.

## 3. README shows the GitHub badge note in DevOps repos (and vice versa)

`README.md:5-11`: both badge instructions are unconditional, so a DevOps repo
gets a "Github workflow status badge" note and a GitHub repo gets the Azure
DevOps one.

Fix: wrap them in `{% if ci_cd == 'DevOps' %}...{% elif ci_cd == 'GitHub' %}...{% endif %}`
(`_templates_suffix: ""` means README.md is already rendered by jinja).

## 4. `use_keyvault_template.yml` references a template that doesn't exist

`<dp>/templates/use_keyvault_template.yml:19` uses
`/devops_pipelines/templates/dummy_template.yml`, which isn't in the template. The
file is documentation ("copy this to main.yml"), so nothing breaks until someone
copies it and the pipeline fails on the missing template.

Fix: point it at a real template, or show an inline `- bash: echo ...` step that
uses `$(PAT)`, and say in the comment that it is an example.

## 5. Old and inconsistent pre-commit versions; short task name

- `pyproject.toml:9` pins `pre-commit=={{ precommit_version }}` (default `3.4.0`,
  `copier.yaml:140-144`), while `<dp>/templates/config.yml:5` installs
  `pre_commit_version: 2.19.0` in CI. Those are two different, old versions, and
  repos have meanwhile moved to `prek`. The CI hooks (check-jsonschema 0.37,
  mirrors-mypy v1.13) run under pre-commit 2.19.
  Fix: use one source of truth (e.g. `config.yml` from `{{ precommit_version }}`),
  bump it, or switch both to `prek` (`uv tool run prek run --all-files` in
  `pre_commit.yml`; `uvVersion` is already in `config.yml`).
- `<dp>/templates/create_environments.yml:18` uses `replacetokens@6` under its
  short name. Existing repos use `qetza.replacetokens.replacetokens-task.replacetokens@7`.
  The short name is ambiguous if another extension with a `replacetokens` task
  is installed in the org. Fix: use the fully qualified name, and consider v7.

## 6. Newly enabled mypy hook fails on existing deploy scripts (migration note)

`.pre-commit-config.yaml:43-46` enables mypy with the strict `[tool.mypy]` from
`pyproject.toml`. Older project repos had mypy commented out, so after migrating,
their `devops_pipelines/scripts/*.py` fail it (25 errors in sb_routeopt_fisha's
`deploy.py`), and the CI PreCommit stage then blocks Deploy. Not a template bug,
but worth a line in the migration notes or changelog. The migrate-repo skill now
tells you to run the hooks before committing.

## 7. Example files come back as conflicts on every migration

Repos that deleted the template examples (`aml_deployments/batch|online/*`,
`components/component_a|b`, `package_c`, `environments/example_package`) get
them back as modify/delete conflicts or additions in the migration (11 conflicts
of 19 in sb_routeopt_fisha). That's inherent to the 3-way merge; only noted
because it makes the preview look worse than it is. A possible improvement in
`migrate_to_copier.py`: for paths under known example folders that the repo
deleted since base, keep the deletion automatically and report it.
