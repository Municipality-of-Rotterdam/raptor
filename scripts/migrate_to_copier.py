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
branch is never modified. Requires a clean working tree. The template ref
defaults to its newest tag (pass ``--ref`` for a branch or specific tag).
Override detected answers with ``-d key=value`` (repeatable), same as copier.

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
    """
    env = os.environ.copy()
    base = int(env.get("GIT_CONFIG_COUNT", "0"))
    for offset, path in enumerate(dict.fromkeys(str(p) for p in paths)):
        env[f"GIT_CONFIG_KEY_{base + offset}"] = "safe.directory"
        env[f"GIT_CONFIG_VALUE_{base + offset}"] = path
    if paths:
        env["GIT_CONFIG_COUNT"] = str(base + len(dict.fromkeys(str(p) for p in paths)))
    return env


def run(cmd: list[str], cwd: Path, *, check: bool = True, trust: tuple[Path, ...] = ()) -> subprocess.CompletedProcess[str]:
    env = git_env(cwd, *trust) if cmd and cmd[0] == "git" else None
    return subprocess.run(cmd, cwd=cwd, check=check, text=True, capture_output=True, env=env)


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
        print(f"note: untracked files are left as-is by the migration:\n{show(untracked)}")
    if not tracked:
        return
    if do_it:
        die(f"tracked files have uncommitted changes; commit or stash first:\n{show(tracked)}")
    print(f"note: tracked files have uncommitted changes (--yes needs them clean):\n{show(tracked)}")


def detect_answers(repo: Path) -> dict[str, str]:
    """Best-effort answers for the target template, read from the existing repo.

    Only high-signal answers are derived; versions and the rest fall back to the
    template defaults via ``copier --defaults``. Anything wrong can be fixed with
    ``--data key=value``.
    """
    answers: dict[str, str] = {}
    repo_name = repo.resolve().name
    answers["repo_name"] = repo_name

    # package vs project: a src/<pkg> layout or [tool.poetry]/[project] => package repo
    pyproject = repo / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text()) if pyproject.is_file() else {}
    tool = data.get("tool", {})
    project = data.get("project", {})
    poetry = tool.get("poetry", {})

    package_name = project.get("name") or poetry.get("name") or ""
    src_dirs = [p.name for p in (repo / "src").glob("*")] if (repo / "src").is_dir() else []
    if package_name or src_dirs:
        answers["repo_type"] = "package_repo"
        answers["package_name"] = package_name or (src_dirs[0] if src_dirs else repo_name.removeprefix("pkg_"))
    else:
        answers["repo_type"] = "project_repo"
        answers["project_name"] = repo_name

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
            answers["author_name"], answers["author_email"] = m.group(1).strip(), m.group(2)
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

    return answers


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
        ["git", "for-each-ref", "--sort=-v:refname", "--format=%(refname:short)", "refs/tags"],
        raptor,
        check=False,
    )
    tags = [t for t in proc.stdout.split() if not t.endswith("^{}")]
    for tag in tags:
        for marker in ("copier.yaml", "copier.yml"):
            if run(["git", "cat-file", "-e", f"{tag}:{marker}"], raptor, check=False).returncode == 0:
                return tag
    return "HEAD"


def build_target_copy(raptor: Path, ref: str | None, answers: dict[str, str], workdir: Path) -> tuple[Path, str]:
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
    clone = run(["git", "clone", "--quiet", "--no-local", str(raptor), str(tpl_dir)], workdir, check=False)
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
    proc = subprocess.run(cmd, check=False, text=True, capture_output=True, env=git_env(out_dir, tpl_dir))
    if proc.returncode != 0:
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
        text = re.sub(r"^_src_path: .*$", f"_src_path: {raptor}", text, count=1, flags=re.MULTILINE)
        answers_file.write_text(text, encoding="utf-8")
    return out_dir, resolved


def migrate(repo: Path, raptor: Path, ref: str | None, answers: dict[str, str], branch: str, do_it: bool) -> int:
    if run(["git", "rev-parse", "--is-inside-work-tree"], repo, check=False).returncode != 0:
        die(f"{repo} is not a git repo")
    if (repo / ".copier-answers.yml").is_file():
        die("repo already has a .copier-answers.yml; use 'copier update' instead")
    # only a real migration needs a clean tree; a dry run never writes
    report_dirty(repo, do_it)

    base = first_commit(repo)
    head = git_head(repo)
    original_branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], repo).stdout.strip()

    print(f"repo:      {repo}")
    print(f"base:      {base[:8]} (first commit = pristine template output)")
    print(f"ours:      {head[:8]} ({original_branch})")
    print("answers:   " + ", ".join(f"{k}={v}" for k, v in sorted(answers.items())))

    with tempfile.TemporaryDirectory() as tmp:
        target, resolved = build_target_copy(raptor, ref, answers, Path(tmp))
        print(f"target:    {raptor} @ {resolved}")

        if not do_it:
            print("\nDRY RUN: no changes made. Re-run with --yes to create the migration branch.")
            return 0

        theirs_branch = f"tmp/migrate-target-{head[:7]}"
        # Build 'theirs' in a throwaway worktree at the base commit instead of
        # rsyncing over the user's working tree: git-ignored files (.venv, .env,
        # .direnv) are invisible to 'git status', so the clean-tree check would
        # pass and 'rsync --delete' would destroy them in place.
        wt = Path(tmp) / "theirs"
        # The worktree lives outside the repo, so git checks its ownership too.
        add = run(["git", "worktree", "add", "--detach", str(wt), base], repo, check=False, trust=(wt,))
        if add.returncode != 0:
            die(f"git worktree add failed: {add.stdout}{add.stderr}")
        try:
            # theirs = target template output committed as a child of base, so
            # the merge base of (ours, theirs) is exactly base.
            run(["rsync", "-a", "--delete", "--exclude", ".git", f"{target}/", f"{wt}/"], wt)
            run(["git", "add", "-A"], wt)
            run(["git", "commit", "-q", "-m", f"template: {resolved}"], wt)
            theirs = run(["git", "rev-parse", "HEAD"], wt).stdout.strip()
        finally:
            run(["git", "worktree", "remove", "--force", str(wt)], repo, check=False, trust=(wt,))
            run(["git", "worktree", "prune"], repo, check=False)
        run(["git", "branch", "-q", theirs_branch, theirs], repo)

        run(["git", "checkout", "-q", "-b", branch, head], repo)
        merge = run(["git", "merge", "--no-ff", "-m", f"migrate to copier template {resolved}", theirs_branch], repo, check=False)
        sys.stdout.write(merge.stdout + merge.stderr)
        run(["git", "branch", "-q", "-D", theirs_branch], repo, check=False)

        if merge.returncode != 0:
            print(
                "\nConflicts to resolve (git status). The template's version of a "
                "conflicted file is what a fresh repo would have; keep your code where it matters.\n"
                f"When done: git add -A && git commit"
            )
            return 2

        print(f"\nDone. You are on branch '{branch}'. Review with:")
        print(f"  git diff {original_branch}..{branch}")
        print("Native 'copier update' will work for all later template versions.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", default=".", type=Path, help="repo to migrate (default: cwd)")
    parser.add_argument("--template", required=True, help="path or URL of the raptor template")
    parser.add_argument("--ref", default=None, help="template ref to migrate to (tag/branch; default: newest tag)")
    parser.add_argument("--branch", default=MIGRATE_BRANCH, help=f"branch to create (default: {MIGRATE_BRANCH})")
    parser.add_argument("-d", "--data", action="append", default=[], metavar="key=value", help="override a detected answer")
    parser.add_argument("--check", action="store_true", help="dry run: show what would happen")
    parser.add_argument("--yes", action="store_true", help="actually create the migration branch")
    args = parser.parse_args()

    repo = args.repo.resolve()
    answers = detect_answers(repo)
    answers.update(parse_data(args.data))

    if not (args.check or args.yes):
        die("refusing to write without --yes (use --check to preview)")

    return migrate(repo, args.template, args.ref, answers, args.branch, do_it=args.yes)


if __name__ == "__main__":
    raise SystemExit(main())
