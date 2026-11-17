"""Migrate a cookiecutter-generated repo to the current copier template, in place.

Why this script exists
----------------------
``copier update`` brings a repo forward by re-rendering the *old* template (from
``.copier-answers.yml``) and 3-way-merging it against your repo. A repo generated
by the old cookiecutter template has no ``.copier-answers.yml`` and predates the
copier template entirely, so ``copier update`` cannot start from it. Seeding the
answers file by hand is a trap: copier then diffs from the seeded commit forward
and silently skips the whole cookiecutter -> copier jump.

This script does the jump correctly, for ANY source version (1.x, 2.x, ...) to
ANY target (3.x, 4.x, ...), by using a plain git 3-way merge:

    base   = the repo's first commit  (the pristine template output; the old
             cookiecutter post-gen hook commits "init" before any user edit)
    ours   = the repo's current HEAD  (base + all user work)
    theirs = ``copier copy`` of the target template, with answers derived from
             this repo

``git merge`` of theirs into ours (merge base = base) applies the real template
drift, keeps the user's code, and surfaces genuine conflicts instead of silently
clobbering them. It also writes ``.copier-answers.yml`` (from the target copy),
so every *later* update uses native ``copier update``.

Usage (from the root of the repo to migrate)
--------------------------------------------
    uv run --python 3.11 <raptor>/scripts/migrate_to_copier.py --check \
        --template <raptor_url_or_path>   # dry run
    uv run --python 3.11 <raptor>/scripts/migrate_to_copier.py --yes \
        --template <raptor_url_or_path>   # do it

The migration runs on a new branch (default ``migrate-to-copier``); the current
branch is never modified. Requires a clean working tree. ``--check`` does a trial
merge in memory and lists the conflicts, deletions and additions ``--yes`` would make. The template ref
defaults to its newest tag (pass ``--ref`` for a branch or specific tag).
Override detected answers with ``-d key=value`` (repeatable), same as copier.
A package repo with the old single pipeline (``azure-pipelines.yml`` ->
``devops_pipelines/templates/main.yml``) is switched to the template's
``ci``/``cd``/``release`` pipelines: ``--check`` lists the files and warns about
what the new CI may not handle, ``--yes`` removes the old files;
``--keep-old-pipelines`` keeps the old pipeline instead. ``--yes`` leaves the
merge staged, not committed, so the hooks can run first.
The branch being migrated should be up to date with the remote's default
branch: ``--yes`` refuses when it is behind, since the PR back onto that branch
would re-conflict with the commits missed (``--allow-behind`` overrides).

Stdlib only (tomllib needs python >= 3.11); shells out to git, rsync and copier.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

MIGRATE_BRANCH = "migrate-to-copier"


def git_env(*paths: Path) -> dict[str, str]:
    """Environment scoping git's ownership trust to the given directories.

    On network-mounted filesystems (CIFS) and in scratch dirs under a root-owned
    /tmp, the filesystem is owned by root while the process runs as the user, so
    git refuses to operate with "detected dubious ownership". Injecting the
    exception through the environment (rather than the command line) also covers
    git processes we do not spawn ourselves, such as the ones copier runs.

    ``GIT_TERMINAL_PROMPT=0`` makes any git command that would ask for credentials
    fail immediately instead of hanging forever on a terminal prompt (we capture
    output, so nobody could answer it anyway).
    """
    env = os.environ.copy()
    env.setdefault("GIT_TERMINAL_PROMPT", "0")
    base = int(env.get("GIT_CONFIG_COUNT", "0"))
    for offset, path in enumerate(dict.fromkeys(str(p) for p in paths)):
        env[f"GIT_CONFIG_KEY_{base + offset}"] = "safe.directory"
        env[f"GIT_CONFIG_VALUE_{base + offset}"] = path
    if paths:
        env["GIT_CONFIG_COUNT"] = str(base + len(dict.fromkeys(str(p) for p in paths)))
    return env


def run(
    cmd: list[str], cwd: Path, *, check: bool = True, trust: tuple[Path, ...] = ()
) -> subprocess.CompletedProcess[str]:
    env = git_env(cwd, *trust) if cmd and cmd[0] == "git" else None
    proc = subprocess.run(
        cmd, cwd=cwd, check=False, text=True, capture_output=True, env=env
    )
    if check and proc.returncode != 0:
        # output is captured, so a bare CalledProcessError would hide why it failed
        # (e.g. a git hook rejecting a commit): show it
        die(
            f"'{' '.join(cmd)}' failed (exit {proc.returncode}) in {cwd}:\n{proc.stdout}{proc.stderr}"
        )
    return proc


def die(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(1)


def git_head(repo: Path) -> str:
    return run(["git", "rev-parse", "HEAD"], repo).stdout.strip()


def first_commit(repo: Path) -> str:
    out = run(["git", "rev-list", "--max-parents=0", "HEAD"], repo).stdout.split()
    if not out:
        die("could not find a root commit")
    return out[-1]


def report_dirty(repo: Path, do_it: bool) -> None:
    """Warn on untracked files; block a real migration on tracked changes only.

    The migration is a git merge, which only rewrites *tracked* files; git
    itself refuses to clobber an untracked file a merge would create, so
    untracked files (``??``) are safe to leave in place and only warned about.
    Staged or unstaged changes to tracked files are fatal for ``--yes`` (a dry
    run never writes, so it only warns).
    """
    lines = run(["git", "status", "--porcelain"], repo).stdout.splitlines()
    if not lines:
        return
    tracked = [line for line in lines if not line.startswith("??")]
    untracked = [line for line in lines if line.startswith("??")]

    def show(items: list[str]) -> str:
        text = "\n".join(f"  {line}" for line in items[:20])
        if len(items) > 20:
            text += f"\n  ... and {len(items) - 20} more"
        return text

    if untracked:
        print(
            f"note: untracked files are left as-is by the migration:\n{show(untracked)}"
        )
    if not tracked:
        return
    if do_it:
        die(
            f"tracked files have uncommitted changes; commit or stash first:\n{show(tracked)}"
        )
    print(
        f"note: tracked files have uncommitted changes (--yes needs them clean):\n{show(tracked)}"
    )


def remote_default_branch(repo: Path, remote: str = "origin") -> str | None:
    """The remote's default branch name (e.g. ``develop``), or None if unknown.

    Read from the remote HEAD symref when present; otherwise populated with
    ``git remote set-head --auto`` (a network call, cheap and harmless), then
    narrowed to whichever of the usual names actually exists on the remote.
    """

    def read() -> str | None:
        out = run(
            [
                "git",
                "symbolic-ref",
                "--quiet",
                "--short",
                f"refs/remotes/{remote}/HEAD",
            ],
            repo,
            check=False,
        ).stdout.strip()
        return out.removeprefix(f"{remote}/") or None

    if read():
        return read()
    run(["git", "remote", "set-head", remote, "--auto"], repo, check=False)
    if read():
        return read()
    for name in ("develop", "main", "master"):
        if (
            run(
                [
                    "git",
                    "rev-parse",
                    "--verify",
                    "--quiet",
                    f"refs/remotes/{remote}/{name}",
                ],
                repo,
                check=False,
            ).returncode
            == 0
        ):
            return name
    return None


def check_fresh(repo: Path, do_it: bool, allow_behind: bool) -> None:
    """Warn (or block) when the branch being migrated is behind the default branch.

    The migration itself is a 3-way merge and handles an outdated branch fine,
    but the *resulting PR* re-conflicts with everything that landed on the
    default branch after this branch was cut -- exactly the work the migration
    would have to redo by hand. Rebasing onto the default branch first makes the
    PR contain only the template drift.

    A fetch failure (offline, no remote, no permission) is not fatal: freshness
    is a courtesy check, and refusing to migrate because a network call failed
    would be worse than warning about it.
    """
    remotes = run(["git", "remote"], repo).stdout.split()
    if not remotes:
        return
    remote = "origin" if "origin" in remotes else remotes[0]
    branch = remote_default_branch(repo, remote)
    if branch is None:
        print(
            "note: could not determine the remote's default branch; skipped the freshness check"
        )
        return
    remote_ref = f"{remote}/{branch}"
    fetch = run(["git", "fetch", "--quiet", remote, branch], repo, check=False)
    if fetch.returncode != 0:
        print(f"note: could not fetch {remote_ref}; skipped the freshness check")
        return
    behind = int(
        run(["git", "rev-list", "--count", f"HEAD..{remote_ref}"], repo).stdout.strip()
    )
    if behind == 0:
        print(f"fresh:   {remote_ref} has no commits missing from HEAD")
        return
    print(f"behind:  {remote_ref} has {behind} commit(s) that HEAD does not have:")
    log = run(
        ["git", "log", "--oneline", f"HEAD..{remote_ref}"], repo
    ).stdout.splitlines()
    print("\n".join(f"  {line}" for line in log[:10]))
    if len(log) > 10:
        print(f"  ... and {len(log) - 10} more")
    print(
        f"\nThe migration would branch from HEAD and the PR back onto {branch} would\n"
        f"re-conflict with those commits. Consider: git fetch && git rebase {remote_ref}\n"
        "(or merge it) before migrating."
    )
    if do_it and not allow_behind:
        die(
            f"HEAD is {behind} commit(s) behind {remote_ref}; update the branch first,\n"
            "or pass --allow-behind to migrate anyway"
        )


TYPE_DEPLOYMENTS = ("none", "batch", "online", "scheduled-pipeline")


def python_packages(src: Path) -> list[str]:
    """Import packages directly under ``src`` (dirs with an ``__init__.py``)."""
    if not src.is_dir():
        return []
    return sorted(
        p.name for p in src.iterdir() if p.is_dir() and (p / "__init__.py").is_file()
    )


def detect_repo_type(repo: Path, pyproject: dict) -> tuple[str, list[str]]:
    """``package_repo`` or ``project_repo``, plus the signals that decided it.

    A ``[project]`` table is *not* a package signal: every uv project has one,
    package or not. Package signals are an importable ``src/<pkg>`` and the
    ``pkg_`` naming convention; project signals are the AML deployment layout
    and uv's ``package = false``. A build backend without any of those is a
    weak package signal; nothing at all means a project repo.
    """
    package_signals: list[str] = []
    project_signals: list[str] = []
    if src_pkgs := python_packages(repo / "src"):
        package_signals.append(f"src/{src_pkgs[0]}/ package")
    if repo.resolve().name.startswith("pkg_"):
        package_signals.append("repo name starts with pkg_")
    for folder in ("aml_deployments", "components", "environments"):
        if (repo / folder).is_dir():
            project_signals.append(f"{folder}/ present")
    if pyproject.get("tool", {}).get("uv", {}).get("package") is False:
        project_signals.append("[tool.uv] package = false")

    if package_signals and project_signals:
        # mixed signals: an importable package under src/ is the strongest one
        kind = "package_repo" if src_pkgs else "project_repo"
        return kind, [*package_signals, *project_signals, "mixed signals: check this"]
    if package_signals:
        return "package_repo", package_signals
    if project_signals:
        return "project_repo", project_signals
    if "build-system" in pyproject or pyproject.get("tool", {}).get("poetry", {}).get(
        "packages"
    ):
        return "package_repo", ["build backend configured, no other signal"]
    return "project_repo", ["no package signal"]


def detect_type_deployment(repo: Path) -> str | None:
    """Deployment type of a project repo, or None to use the template default.

    The ``type_deployment`` variable in the old ``main.yml`` is what CD actually
    deploys (old templates spelled it ``scheduled_pipeline``); otherwise infer it
    from a single deployment folder under ``aml_deployments/``.
    """
    main_yml = repo / "devops_pipelines" / "templates" / "main.yml"
    if main_yml.is_file():
        m = re.search(
            r"name:\s*type_deployment\s*\n\s*value:\s*'?\"?([\w-]+)",
            main_yml.read_text(),
        )
        if m and (value := m.group(1).replace("_", "-")) in TYPE_DEPLOYMENTS:
            return value
    found = [
        kind
        for folder, kind in (
            ("scheduled_pipeline", "scheduled-pipeline"),
            ("batch", "batch"),
            ("online", "online"),
        )
        if (repo / "aml_deployments" / folder).is_dir()
    ]
    return found[0] if len(found) == 1 else None


def detect_answers(repo: Path) -> dict[str, str]:
    """Best-effort answers for the target template, read from the existing repo.

    Only high-signal answers are derived; versions and the rest fall back to the
    template defaults via ``copier --defaults``. Anything wrong can be fixed with
    ``--data key=value``.
    """
    answers: dict[str, str] = {}
    # the repo's name on the remote (…/_git/<name>, …/<name>.git); a clone folder may be renamed (repo_2, repo_3)
    folder = repo.resolve().name
    url = run(["git", "remote", "get-url", "origin"], repo, check=False).stdout.strip()
    remote_name = (
        re.sub(r"\.git$", "", url.rstrip("/").rsplit("/", 1)[-1].rsplit(":", 1)[-1])
        if url
        else ""
    )
    repo_name = remote_name or folder
    if remote_name and remote_name != folder:
        print(
            f"repo_name: {remote_name} (from the origin remote; the folder is {folder})"
        )
    answers["repo_name"] = repo_name

    pyproject = repo / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text()) if pyproject.is_file() else {}
    tool = data.get("tool", {})
    project = data.get("project", {})
    poetry = tool.get("poetry", {})

    repo_type, reasons = detect_repo_type(repo, data)
    answers["repo_type"] = repo_type
    print(
        f"repo_type: {repo_type} ({'; '.join(reasons)}); override with -d repo_type=..."
    )
    if repo_type == "package_repo":
        src_pkgs = python_packages(repo / "src")
        name = (
            src_pkgs[0]
            if src_pkgs
            else (
                project.get("name")
                or poetry.get("name")
                or repo_name.removeprefix("pkg_")
            )
        )
        # the distribution name may contain '-' / '.', the import package (src/<name>) may not
        answers["package_name"] = re.sub(r"[-.]", "_", name)
    else:
        answers["project_name"] = repo_name
        type_deployment = detect_type_deployment(repo)
        if type_deployment:
            answers["type_deployment"] = type_deployment

    # CI/CD platform
    if (repo / "devops_pipelines").is_dir():
        answers["ci_cd"] = "DevOps"
    elif (repo / ".github" / "workflows").is_dir():
        answers["ci_cd"] = "GitHub"

    # DevOps specifics from the old config.yml
    config = repo / "devops_pipelines" / "templates" / "config.yml"
    if config.is_file():
        text = config.read_text()
        for key, pattern in {
            "devops_organisation_name": r"devops_organisation:\s*(\S+)",
            "devops_project_name": r"devops_project:\s*(\S+)",
            "package_feed": r"dapr_feed:\s*(\S+)",
            "private_agent_name": r"sh_agent_pool_name:\s*'?([^'\n]+)'?",
        }.items():
            m = re.search(pattern, text)
            if m:
                answers[key] = m.group(1).strip()

    # author + description from pyproject
    authors = poetry.get("authors") or project.get("authors") or []
    if authors and isinstance(authors[0], dict) and authors[0].get("email"):
        answers["author_name"] = authors[0].get("name", "")
        answers["author_email"] = authors[0]["email"]
    elif authors and isinstance(authors[0], str):
        m = re.match(r"^(.*?)\s*<([^>]+)>", authors[0])
        if m:
            answers["author_name"], answers["author_email"] = (
                m.group(1).strip(),
                m.group(2),
            )
    description = project.get("description") or poetry.get("description")
    if description:
        answers["description"] = description

    # fall back to the git identity when pyproject declares no author
    if "author_name" not in answers:
        name = run(["git", "config", "user.name"], repo, check=False).stdout.strip()
        email = run(["git", "config", "user.email"], repo, check=False).stdout.strip()
        if name and email:
            answers["author_name"], answers["author_email"] = name, email

    # git identity defaults to the author
    if "author_name" in answers:
        answers.setdefault("user_name", answers["author_name"])
    if "author_email" in answers:
        answers.setdefault("user_email", answers["author_email"])

    # the uv that will maintain this repo's uv.lock (CI installs uvVersion from config.yml); the template
    # default may be older than the lock format the repo already uses
    uv = (
        run(["uv", "--version"], repo, check=False).stdout.split()
        if shutil.which("uv")
        else []
    )
    if len(uv) >= 2 and re.fullmatch(r"\d+\.\d+\.\d+", uv[1]):
        answers["uv_version"] = uv[1]

    return answers


# --- old single pipeline (azure-pipelines.yml -> main.yml) -> the template's ci / cd / release -----------------------

OLD_PIPELINE = "azure-pipelines.yml"


def old_pipeline_files(repo: Path, repo_type: str) -> list[str]:
    """Tracked files of the old single-pipeline layout of a package repo, or [] if it has none.

    Old package repos run one pipeline, ``azure-pipelines.yml`` extending
    ``devops_pipelines/templates/main.yml``; the 3.x package template has three
    (``ci``/``cd``/``release``) and no ``azure-pipelines.yml``. Newer repos and
    project repos (whose template still uses ``main.yml``) return [].
    """
    entry = repo / OLD_PIPELINE
    if (
        repo_type != "package_repo"
        or not entry.is_file()
        or "devops_pipelines/templates/main.yml" not in entry.read_text()
    ):
        return []
    return run(
        ["git", "ls-files", "--", OLD_PIPELINE, "devops_pipelines"], repo
    ).stdout.split()


def keep_old_pipelines(repo: Path, target: Path, old_files: list[str]) -> None:
    """Make the rendered template carry the repo's own pipeline files instead of the new ones.

    With the old files (HEAD content) in "theirs" and the template's pipeline
    files left out, the merge has nothing to change there: no conflicts, nothing
    added or removed under ``devops_pipelines/``.
    """
    new_dir = target / "devops_pipelines"
    for path in sorted(new_dir.rglob("*"), reverse=True) if new_dir.is_dir() else []:
        if path.is_file() and str(path.relative_to(target)) not in old_files:
            path.unlink()
    # the file mode too: a 100755 vs 100644 difference alone is an add/add conflict
    tree = run(["git", "ls-tree", "HEAD", "--", *old_files], repo).stdout.splitlines()
    modes = {
        path: meta.split()[0] for meta, path in (line.split("\t", 1) for line in tree)
    }
    for rel in old_files:
        dest = target / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(
            subprocess.run(
                ["git", "show", f"HEAD:{rel}"],
                cwd=repo,
                check=True,
                capture_output=True,
                env=git_env(repo),
            ).stdout
        )
        dest.chmod(0o755 if modes.get(rel) == "100755" else 0o644)


def pipeline_switch(old_files: list[str], target: Path) -> tuple[list[str], list[str]]:
    """(files to remove, files to take from the template) for the switch to ci / cd / release."""
    remove = [f for f in old_files if not (target / f).is_file()]
    take = [f for f in old_files if (target / f).is_file()]
    return remove, take


def show_pipeline_switch(old_files: list[str], target: Path, keep: bool) -> None:
    if not old_files:
        return
    if keep:
        print(
            f"\npipelines: old {OLD_PIPELINE} -> main.yml kept (--keep-old-pipelines); "
            "the template's ci/cd/release are left out"
        )
        return
    remove, take = pipeline_switch(old_files, target)
    added = sorted(
        str(p.relative_to(target))
        for p in (target / "devops_pipelines").rglob("*")
        if p.is_file() and str(p.relative_to(target)) not in old_files
    )
    print(
        f"\npipelines: old {OLD_PIPELINE} -> main.yml found: --yes switches to the template's ci / cd / release.\n"
        "           Ask the user first; --keep-old-pipelines keeps the old pipeline unchanged."
    )
    print("  remove:        " + ", ".join(remove))
    if take:
        print("  template's:    " + ", ".join(take) + "  (replaces the repo's version)")
    if added:
        print("  add:           " + ", ".join(added))
    print(
        "  DevOps after the push (separate, per step): create the pipelines, authorize them, switch build\n"
        "  validation to ci, delete the old pipeline once main has no azure-pipelines.yml"
    )
    for warning in github_ref_warnings(target):
        print(f"  WARNING: {warning}")


def github_ref_warnings(target: Path) -> list[str]:
    """The ci/cd/release ymls fetch raptor's steps from GitHub at a tag: warn when that tag isn't there (yet).

    A quick ``git ls-remote`` of the public GitHub repo; a network failure only
    says the check was skipped.
    """
    refs: set[tuple[str, str]] = set()
    for yml in (target / "devops_pipelines" / "templates").glob("*.yml"):
        for name, tag in re.findall(
            r"name:\s*(\S+)\s*\n\s*type:\s*github\s*\n(?:\s*\w+:.*\n)*?\s*ref:\s*refs/tags/(\S+)",
            yml.read_text(),
        ):
            refs.add((name, tag))
    out = []
    for name, tag in sorted(refs):
        try:
            proc = subprocess.run(
                [
                    "git",
                    "ls-remote",
                    "--tags",
                    f"https://github.com/{name}.git",
                    f"refs/tags/{tag}",
                ],
                check=False,
                text=True,
                capture_output=True,
                timeout=30,
                env=git_env(),
            )
        except subprocess.TimeoutExpired:
            proc = None
        if proc is None or proc.returncode != 0:
            out.append(
                f"could not check whether tag {tag} exists on github.com/{name} (offline?)"
            )
        elif not proc.stdout.strip():
            out.append(
                f"tag {tag} is not on github.com/{name}: the new pipelines can't fetch raptor's CI steps "
                "until it is published (they fail validation)"
            )
    return out


def ci_warnings(repo: Path, old_files: list[str]) -> list[str]:
    """Quick signals that the repo needs something raptor's ci/cd steps don't do.

    raptor's CI steps (``.azuredevops/templates/*@raptor``) run ``uv run --group
    test`` / ``uv sync --only-group ...``: default dependency groups only, no
    extras, no git submodules checked out, no ``.env``. Each warning names what
    the repo relies on; the fix is repo-specific, so nothing is changed here.
    """
    warnings: list[str] = []
    pyproject = repo / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text()) if pyproject.is_file() else {}
    uv = data.get("tool", {}).get("uv", {})
    gitmodules = repo / ".gitmodules"
    submodules = (
        re.findall(r"^\s*path\s*=\s*(\S+)", gitmodules.read_text(), re.M)
        if gitmodules.is_file()
        else []
    )
    for name, spec in uv.get("sources", {}).items():
        sources = spec if isinstance(spec, list) else [spec]
        for source in sources:
            path = str(source.get("path", "")).rstrip("/")
            if any(path == sub or path.startswith(f"{sub}/") for sub in submodules):
                warnings.append(
                    f"uv source {name} = git submodule {path}: CI doesn't check out submodules"
                )
        if extras := sorted({s["extra"] for s in sources if "extra" in s}):
            warnings.append(
                f"uv source {name} depends on extra(s) {', '.join(extras)}: CI installs no extras"
            )
    if any("extra" in item for group in uv.get("conflicts", []) for item in group):
        warnings.append("[tool.uv] conflicts between extras: CI can't select an extra")
    hooks = repo / ".pre-commit-config.yaml"
    if hooks.is_file():
        for m in re.finditer(
            r"-\s*id:\s*(\S+)(?:(?!\n\s*-\s*id:).)*?entry:[^\n]*\.env",
            hooks.read_text(),
            re.S,
        ):
            warnings.append(
                f"pre-commit hook {m.group(1)} reads .env: CI has none (all hooks run in CI)"
            )
    texts = {
        f: (repo / f).read_text()
        for f in old_files
        if f.endswith(".yml") and (repo / f).is_file()
    }
    for f, text in texts.items():
        for extra in re.findall(r"uv sync[^\n]*--extra[ =](\S+)", text):
            warnings.append(
                f"old pipeline installed --extra {extra} ({f}): the new CI can't"
            )
    main_yml = texts.get("devops_pipelines/templates/main.yml", "")
    if re.search(
        r"^\s*-\s*template:\s*/devops_pipelines/templates/register\.yml", main_yml, re.M
    ):
        warnings.append(
            "old pipeline registered an AML environment: set RegisterAmlEnv: True in config.yml"
        )
    if re.search(r"^\s*-\s*['\"]?release/", texts.get(OLD_PIPELINE, ""), re.M):
        warnings.append(
            "old pipeline ran on release/* branches: cd.yml only runs on main and develop"
        )
    return warnings


def show_ci_warnings(repo: Path, old_files: list[str], keep: bool) -> None:
    if not old_files or keep:
        return
    warnings = ci_warnings(repo, old_files)
    if warnings:
        print(
            f"\nci-warn:   {len(warnings)} thing(s) the new ci/cd may not handle for this repo (check before the switch):"
        )
        for w in warnings:
            print(f"  - {w}")


def apply_pipeline_switch(repo: Path, old_files: list[str], target: Path) -> None:
    """After the merge: drop the old pipeline files, take the template's version of shared ones."""
    remove, take = pipeline_switch(old_files, target)
    if remove:
        run(["git", "rm", "-q", "-f", "--", *remove], repo)
    unmerged = set(
        run(["git", "diff", "--name-only", "--diff-filter=U"], repo).stdout.split()
    )
    for f in take:
        if f in unmerged:
            run(["git", "checkout", "--theirs", "--", f], repo)
            run(["git", "add", "--", f], repo)
    print(
        f"pipelines: removed {len(remove)} old pipeline file(s); template's version of: {', '.join(take) or '-'}"
    )


def parse_data(pairs: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for pair in pairs:
        if "=" not in pair:
            die(f"--data expects key=value, got '{pair}'")
        key, _, value = pair.partition("=")
        out[key] = value
    return out


def latest_tag(raptor: Path) -> str:
    """Newest tag that is a copier template, newest first by version order.

    Two things this deliberately avoids:
    - ``git describe --tags --abbrev=0`` only sees tags reachable from the
      checked-out branch, so a fresh clone whose default branch predates the
      newest tag silently picks an ancient version.
    - a plain newest-tag sort can land on a pre-copier (cookiecutter) tag,
      which ``copier copy`` cannot render at all.

    A copier template is recognised by its ``copier.yaml``/``copier.yml`` at
    the root, so this naturally skips the cookiecutter-era tags and, once
    stable 3.x/4.x tags exist, prefers those over pre-releases.
    """
    proc = run(
        [
            "git",
            "for-each-ref",
            "--sort=-v:refname",
            "--format=%(refname:short)",
            "refs/tags",
        ],
        raptor,
        check=False,
    )
    tags = [t for t in proc.stdout.split() if not t.endswith("^{}")]
    for tag in tags:
        for marker in ("copier.yaml", "copier.yml"):
            if (
                run(
                    ["git", "cat-file", "-e", f"{tag}:{marker}"], raptor, check=False
                ).returncode
                == 0
            ):
                return tag
    return "HEAD"


def build_target_copy(
    raptor: Path, ref: str | None, answers: dict[str, str], workdir: Path
) -> tuple[Path, str]:
    """Run ``copier copy`` of the target template into a scratch dir.

    Returns the output dir and the resolved template ref.

    The template is first cloned into a scratch dir: copier records ``_commit``
    by describing the template tree it rendered from, and a *dirty* template
    working tree makes it commit a phantom commit that does not exist upstream,
    which would break every later ``copier update``. A clean clone guarantees
    ``_commit`` is a real, reachable description of ``ref``.
    """
    tpl_dir = workdir / ".template"
    # the template validates repo_name against the destination folder name, so
    # render into a folder named after the repo (the clone dir is dotted so a
    # repo literally named 'template' can never collide with it)
    out_dir = workdir / answers.get("repo_name", "target")
    clone = run(
        ["git", "clone", "--quiet", "--no-local", str(raptor), str(tpl_dir)],
        workdir,
        check=False,
    )
    if clone.returncode != 0:
        # not a local path (or clone failed): copier can handle URLs itself;
        # without --vcs-ref copier uses the newest tag, same default as here.
        tpl_src = raptor
        resolved, vcs_ref = "(newest tag)", ref
    else:
        # default to the newest tag, like copier does: an untagged HEAD would
        # record a dev version that later tagged updates are rejected as.
        resolved = ref or latest_tag(tpl_dir)
        checkout = run(["git", "checkout", "--quiet", resolved], tpl_dir, check=False)
        if checkout.returncode != 0:
            die(f"ref '{resolved}' not found in template {raptor}")
        tpl_src = tpl_dir
        vcs_ref = resolved
    # --overwrite: the destination is a scratch dir, so a file already being
    # there is never the user's data; never stop on an interactive prompt.
    cmd = ["copier", "copy", "--trust", "--defaults", "--overwrite"]
    if vcs_ref:
        cmd += ["--vcs-ref", vcs_ref]
    for key, value in answers.items():
        cmd += ["--data", f"{key}={value}"]
    cmd += [str(tpl_src), str(out_dir)]
    # copier shells out to git inside the scratch output dir, which may sit on a
    # root-owned mount; trust both scratch paths for that subprocess.
    proc = subprocess.run(
        cmd, check=False, text=True, capture_output=True, env=git_env(out_dir, tpl_dir)
    )
    if proc.returncode != 0:
        # a detected answer the template rejects: say which and how to fix it,
        # instead of burying it at the end of a copier traceback
        m = re.search(r"Validation error for question '(\w+)': (.*)", proc.stderr)
        if m:
            key, reason = m.groups()
            die(
                f"the template rejects {key}={answers.get(key, '')!r}: {reason}\n"
                f"Pass the right value with: -d \"{key}=...\""
            )
        sys.stdout.write(proc.stdout)
        sys.stderr.write(proc.stderr)
        die(f"copier copy failed (exit {proc.returncode})")
    # copier's git task may have initialised a repo in the scratch copy; drop it,
    # we merge via the real repo's history.
    shutil.rmtree(out_dir / ".git", ignore_errors=True)
    # _src_path must be the canonical template URL/path the user passed, not the
    # scratch clone — later 'copier update' resolves the template from it.
    answers_file = out_dir / ".copier-answers.yml"
    if answers_file.exists():
        text = answers_file.read_text(encoding="utf-8")
        text = re.sub(
            r"^_src_path: .*$",
            f"_src_path: {raptor}",
            text,
            count=1,
            flags=re.MULTILINE,
        )
        answers_file.write_text(text, encoding="utf-8")
    return out_dir, resolved


def commit_target(repo: Path, base: str, target: Path, resolved: str, tmp: Path) -> str:
    """Commit the rendered template as a child of ``base``; return its sha.

    Built in a throwaway worktree at the base commit instead of rsyncing over
    the user's working tree: git-ignored files (.venv, .env, .direnv) are
    invisible to 'git status', so the clean-tree check would pass and
    'rsync --delete' would destroy them in place. Being a child of base makes
    the merge base of (ours, theirs) exactly base. The commit is not referenced
    by any branch, so a dry run leaves nothing behind (git gc drops it).
    """
    wt = tmp / "theirs"
    # The worktree lives outside the repo, so git checks its ownership too.
    add = run(
        ["git", "worktree", "add", "--detach", str(wt), base],
        repo,
        check=False,
        trust=(wt,),
    )
    if add.returncode != 0:
        die(f"git worktree add failed: {add.stdout}{add.stderr}")
    try:
        run(
            ["rsync", "-a", "--delete", "--exclude", ".git", f"{target}/", f"{wt}/"], wt
        )
        run(["git", "add", "-A"], wt)
        # --no-verify: the repo's own hooks (pre-commit/prek) also run in this
        # worktree; this throwaway commit must not be blocked or rewritten by them.
        run(["git", "commit", "-q", "--no-verify", "-m", f"template: {resolved}"], wt)
        return run(["git", "rev-parse", "HEAD"], wt).stdout.strip()
    finally:
        run(
            ["git", "worktree", "remove", "--force", str(wt)],
            repo,
            check=False,
            trust=(wt,),
        )
        run(["git", "worktree", "prune"], repo, check=False)


def preview_merge(
    repo: Path, head: str, theirs: str, limit: int = 40, switched: tuple[str, ...] = ()
) -> None:
    """Show what ``--yes`` would do: conflicts, deletions and additions vs HEAD.

    ``git merge-tree --write-tree`` (git >= 2.38) merges in the object store
    only, so neither the working tree, the index nor any ref is touched. Large
    deletions or a fake package skeleton here usually mean a wrong answer
    (e.g. repo_type).
    """
    proc = run(
        ["git", "merge-tree", "--write-tree", "--no-messages", head, theirs],
        repo,
        check=False,
    )
    if proc.returncode not in (0, 1):
        print(
            f"note: could not preview the merge (git >= 2.38 needed): {proc.stderr.strip()}"
        )
        return
    tree, *rest = proc.stdout.splitlines()
    # conflicted file info: "<mode> <object> <stage>\t<path>"
    info = [line for line in rest if "\t" in line]
    conflicts = list(dict.fromkeys(line.split("\t", 1)[1] for line in info))
    # conflicts on old pipeline files are resolved by the pipeline switch (shown in its own section)
    auto = [c for c in conflicts if c in switched]
    # same content on both sides, only the file mode differs: --yes keeps the repo's version
    mode_only = sorted(mode_only_conflicts(info) - set(switched))
    conflicts = [c for c in conflicts if c not in switched and c not in mode_only]
    status = run(
        ["git", "diff", "--name-status", "--no-renames", head, tree], repo
    ).stdout.splitlines()
    # conflicted paths are listed once, under conflicts, not again as added/modified
    changes = {
        code: [
            path
            for line in status
            if line.startswith(code)
            and (path := line.split("\t", 1)[1]) not in conflicts
        ]
        for code in "ADM"
    }

    def show(title: str, items: list[str]) -> None:
        print(f"{title} ({len(items)}):")
        for item in items[:limit]:
            print(f"  {item}")
        if len(items) > limit:
            print(f"  ... and {len(items) - limit} more")

    print(
        f"\npreview:   {len(conflicts)} conflicted, {len(changes['D'])} deleted, "
        f"{len(changes['A'])} added, {len(changes['M'])} modified (vs HEAD)"
    )
    if auto:
        print(
            f"           ({len(auto)} more conflict(s) on old pipeline files are resolved by the pipeline switch)"
        )
    if mode_only:
        print(
            f"           ({len(mode_only)} more conflict(s) differ only in file mode: --yes keeps the repo's version)"
        )
    if conflicts:
        show("conflicts", conflicts)
    if changes["D"]:
        show("deleted", changes["D"])
    if changes["A"]:
        show("added", changes["A"])
    checks = addition_checks(repo, head, changes["A"])
    if checks:
        print(f"\ncheck:     {len(checks)} added file(s) to look at before --yes:")
        for item in checks:
            print(f"  - {item}")


def resolve_mode_only(repo: Path) -> None:
    """After the merge: resolve conflicts that differ only in file mode with the repo's version."""
    info = run(["git", "ls-files", "-u"], repo).stdout.splitlines()
    paths = sorted(mode_only_conflicts(info))
    if paths:
        run(["git", "checkout", "--ours", "--", *paths], repo)
        run(["git", "add", "--", *paths], repo)
        print(
            f"mode-only: {len(paths)} conflict(s) differed only in file mode, kept the repo's version"
        )


def mode_only_conflicts(info: list[str]) -> set[str]:
    """Conflicted paths whose two sides (stages 2 and 3) have the same content.

    ``info`` holds ``git merge-tree`` / ``git ls-files -u`` lines
    ``<mode> <object> <stage>\\t<path>``. Old cookiecutter repos often have every
    file at 100755 while the template renders 100644, so an identical file added
    on both sides still conflicts, on the mode alone.
    """
    sides: dict[str, dict[str, str]] = {}
    for line in info:
        meta, path = line.split("\t", 1)
        _mode, obj, stage = meta.split()
        sides.setdefault(path, {})[stage] = obj
    return {p for p, s in sides.items() if "2" in s and "3" in s and s["2"] == s["3"]}


def addition_checks(repo: Path, head: str, added: list[str]) -> list[str]:
    """Added template files that likely clash with the repo: case-only name clashes and example files.

    A case clash (``taskfile.yml`` next to ``Taskfile.yml``) breaks checkouts on
    macOS/Windows. Template example files and tests assume the template's example
    code; a repo that changed or dropped it fails on them (e.g. a template
    ``tests/conftest.py`` importing example classes the repo's ``examples.py`` lacks).
    """
    ours = run(["git", "ls-tree", "-r", "--name-only", head], repo).stdout.splitlines()
    by_lower = {p.lower(): p for p in ours}
    has_tests = any(p.startswith("tests/") for p in ours)
    out = []
    for path in added:
        if (other := by_lower.get(path.lower())) and other != path:
            out.append(
                f"{path}: same name as the repo's {other} except for case; keep one (merge them)"
            )
        elif "example" in Path(path).name.lower() and not Path(path).name.startswith(
            "."
        ):  # not .env.example
            out.append(
                f"{path}: template example; keep it only if the repo uses the template's examples"
            )
        elif has_tests and path.startswith("tests/") and path.endswith(".py"):
            out.append(
                f"{path}: template test next to the repo's own tests; check it fits the repo's code"
            )
    return out


def migrate(
    repo: Path,
    raptor: Path,
    ref: str | None,
    answers: dict[str, str],
    branch: str,
    do_it: bool,
    allow_behind: bool = False,
    keep_pipelines: bool = False,
) -> int:
    if (
        run(["git", "rev-parse", "--is-inside-work-tree"], repo, check=False).returncode
        != 0
    ):
        die(f"{repo} is not a git repo")
    if (repo / ".copier-answers.yml").is_file():
        die("repo already has a .copier-answers.yml; use 'copier update' instead")
    # only a real migration needs a clean tree; a dry run never writes
    report_dirty(repo, do_it)
    check_fresh(repo, do_it, allow_behind)

    base = first_commit(repo)
    head = git_head(repo)
    original_branch = run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], repo
    ).stdout.strip()

    print(f"repo:      {repo}")
    print(f"base:      {base[:8]} (first commit = pristine template output)")
    print(f"ours:      {head[:8]} ({original_branch})")
    print("answers:   " + ", ".join(f"{k}={v}" for k, v in sorted(answers.items())))

    with tempfile.TemporaryDirectory() as tmp:
        target, resolved = build_target_copy(raptor, ref, answers, Path(tmp))
        print(f"target:    {raptor} @ {resolved}")
        old_files = old_pipeline_files(repo, answers.get("repo_type", ""))
        if old_files and keep_pipelines:
            keep_old_pipelines(repo, target, old_files)
        show_pipeline_switch(old_files, target, keep_pipelines)
        show_ci_warnings(repo, old_files, keep_pipelines)
        theirs = commit_target(repo, base, target, resolved, Path(tmp))
        switched = () if keep_pipelines else tuple(old_files)

        if not do_it:
            preview_merge(repo, head, theirs, switched=switched)
            print(
                "\nDRY RUN: no changes made. Re-run with --yes to create the migration branch."
            )
            return 0

        theirs_branch = f"tmp/migrate-target-{head[:7]}"
        run(["git", "branch", "-q", theirs_branch, theirs], repo)

        run(["git", "checkout", "-q", "-b", branch, head], repo)
        # --no-commit: the pipeline switch and the user's checks (hooks) belong in the merge commit
        merge = run(
            [
                "git",
                "merge",
                "--no-ff",
                "--no-commit",
                "-m",
                f"migrate to copier template {resolved}",
                theirs_branch,
            ],
            repo,
            check=False,
        )
        sys.stdout.write(merge.stdout + merge.stderr)
        run(["git", "branch", "-q", "-D", theirs_branch], repo, check=False)
        if switched:
            apply_pipeline_switch(repo, old_files, target)
        resolve_mode_only(repo)

        start_over = f"git merge --abort && git checkout {original_branch} && git branch -D {branch}"
        hooks = (
            "Newly enabled pre-commit hooks may fail on existing code: run them before committing\n"
            "  (uv run prek run --all-files, or pre-commit run --all-files)."
        )
        unmerged = run(
            ["git", "diff", "--name-only", "--diff-filter=U"], repo
        ).stdout.split()
        if unmerged:
            print(
                f"\n{len(unmerged)} conflict(s) to resolve (git status). The template's version of a "
                "conflicted file is what a fresh repo would have; keep your code where it matters.\n"
                f"{hooks}\nWhen done: git add <files> && git commit\nTo start over: {start_over}"
            )
            return 2

        print(
            f"\nMerged without conflicts, staged but not committed, on branch '{branch}'.\n{hooks}\n"
            f"Then: git commit --no-edit, and review with git diff {original_branch}..{branch}\n"
            f"To start over: {start_over}"
        )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--repo", default=".", type=Path, help="repo to migrate (default: cwd)"
    )
    parser.add_argument(
        "--template", required=True, help="path or URL of the raptor template"
    )
    parser.add_argument(
        "--ref",
        default=None,
        help="template ref to migrate to (tag/branch; default: newest tag)",
    )
    parser.add_argument(
        "--branch",
        default=MIGRATE_BRANCH,
        help=f"branch to create (default: {MIGRATE_BRANCH})",
    )
    parser.add_argument(
        "-d",
        "--data",
        action="append",
        default=[],
        metavar="key=value",
        help="override a detected answer",
    )
    parser.add_argument(
        "--check", action="store_true", help="dry run: show what would happen"
    )
    parser.add_argument(
        "--yes", action="store_true", help="actually create the migration branch"
    )
    parser.add_argument(
        "--allow-behind",
        action="store_true",
        help="migrate even when HEAD is behind the remote's default branch",
    )
    parser.add_argument(
        "--keep-old-pipelines",
        action="store_true",
        help=f"package repo with the old {OLD_PIPELINE}: keep it instead of switching to ci/cd/release",
    )
    args = parser.parse_args()

    repo = args.repo.resolve()
    answers = detect_answers(repo)
    answers.update(parse_data(args.data))

    if not (args.check or args.yes):
        die("refusing to write without --yes (use --check to preview)")

    return migrate(
        repo,
        args.template,
        args.ref,
        answers,
        args.branch,
        do_it=args.yes,
        allow_behind=args.allow_behind,
        keep_pipelines=args.keep_old_pipelines,
    )


if __name__ == "__main__":
    raise SystemExit(main())
