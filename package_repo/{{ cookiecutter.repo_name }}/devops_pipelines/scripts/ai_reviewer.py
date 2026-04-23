from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import subprocess
import argparse
import sys
import re
from typing import Dict, List, Literal, TypedDict

import requests
from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication
from azure.devops.v7_0.git.models import (
    GitBaseVersionDescriptor,
    GitTargetVersionDescriptor,
    GitRepository,
    GitCommitDiffs,
    GitPullRequest,
)
import difflib


class DiffType(TypedDict):
    """Represents a parsed file diff entry."""

    change_type: Literal[
        "add", "delete", "rename", "modify"
    ]  # One of: "add", "delete", "rename", "modify"
    diff: str  # Unified diff text for the file


class AzureDevOpsClient:
    def __init__(self, project: str):
        """
        Initialize an Azure DevOps client.

        Args:
            project (str): The name of the Azure DevOps project to work with.
        """
        org_url = os.getenv("AZURE_DEVOPS_ORG")
        pat = os.getenv("AZURE_DEVOPS_PAT")

        if not org_url or not pat:
            raise ValueError(
                "Set AZURE_DEVOPS_ORG and AZURE_DEVOPS_PAT in your .env file."
            )

        self.org_url: str = org_url
        self.pat: str = pat
        self.project: str = project

        creds = BasicAuthentication("", self.pat)
        self.connection: Connection = Connection(base_url=self.org_url, creds=creds)
        self.git = self.connection.clients.get_git_client()

    def _get_repo(self, name: str) -> GitRepository:
        """
        Retrieve a repository by its name.

        Args:
            name (str): The name of the repository to find.

        Returns:
            GitRepository: The matching repository object.

        Raises:
            ValueError: If no repository with the given name is found.
        """
        repos = self.git.get_repositories(self.project)
        for r in repos:
            if r.name == name:
                return r
        raise ValueError(f"Repository '{name}' not found")

    def get_branch_diffs(
        self, source_branch: str, target_branch: str, ignore: List[str]
    ) -> Dict[Path, DiffType]:
        """
        Get parsed diffs between two branches.

        Args:
            source_branch (str): Branch containing changes.
            target_branch (str): Branch to compare against.

        Returns:
            Dict[Path, DiffType]: Mapping of file paths to diff metadata.
        """
        diff = self._get_diff(source_branch=source_branch, target_branch=target_branch)
        parsed = self._parse_plain_diff(diff, ignore)
        return parsed

    def _parse_plain_diff(self, diff_text: str, ignore: List[str]) -> Dict[Path, DiffType]:
        """
        Parse a plain unified diff string into a dictionary of file changes.

        Args:
            diff_text (str): Raw unified diff output from `git diff`.

        Returns:
            Dict[str, DiffType]: Mapping of file path → diff metadata:
                {
                    "path/to/file.py": {
                        "change_type": "modify",
                        "diff": "<unified diff text>"
                    },
                    ...
                }

        Notes:
            - Files ending with `.lock` or `.ipynb` are skipped.
            - Change types are inferred from diff headers:
                * "add" → new file
                * "delete" → deleted file
                * "rename" → similarity index (rename/copy)
                * "modify" → default
            - Only diffs with hunk bodies (`@@ ... @@`) are included.
            Pure renames without content changes will be ignored.
        """
        result: Dict[Path, DiffType] = {}

        file_diffs = re.split(r"(?m)^diff --git ", diff_text)
        for section in file_diffs:
            if not section.strip():
                continue

            header_line = section.splitlines()[0]
            parts = header_line.split()
            if len(parts) < 2:
                continue

            b_path = parts[1]
            path = Path(b_path[2:] if b_path.startswith("b/") else b_path)

            if path.suffix in ignore:
                continue

            change_type: Literal['add', 'delete', 'rename', 'modify'] = "modify"
            if re.search(r"(?m)^new file mode", section):
                change_type = "add"
            elif re.search(r"(?m)^deleted file mode", section):
                change_type = "delete"
            elif re.search(r"(?m)^similarity index", section):
                change_type = "rename"

            diff_body_match = re.search(r"(?m)^@@.*", section)
            diff_body = section[diff_body_match.start() :] if diff_body_match else ""

            if not diff_body.strip():
                continue

            result[path] = {
                "change_type": change_type,
                "diff": diff_body,
            }

        return result

    def _get_diff(self, source_branch: str, target_branch: str, pad: int = 0) -> str:
        """
        Run `git diff` between two branches and return raw diff output.

        Args:
            source_branch (str): Branch to compare changes from.
            target_branch (str): Branch to compare against.
            pad (int): Number of context lines to include (default: 0).

        Returns:
            str: Raw unified diff output.
        """
        diff_cmd = ["git", "diff", f"{target_branch}...{source_branch}", f"-U{pad}"]
        result = subprocess.run(diff_cmd, capture_output=True, text=True, check=True)
        return result.stdout


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        "-o",
        help="Path to the JSON file to write comments to",
        default="pr_comments.json",
    )
    return parser.parse_args()


@dataclass
class PRLineComment:
    """
    A single line-level comment suggestion.

    file_path: path relative to repo root, e.g. "src/pkg_aa_hackaton/foo.py"
    line:      1-based line number in the *new* (right) file
    message:   markdown text for the comment
    """
    file_path: str
    line: int
    message: str


def branch_exists(ref: str) -> bool:
    return subprocess.run(
        ["git", "rev-parse", "--verify", ref],
        capture_output=True
    ).returncode == 0


def normalize_branch(branch: str, pr_id: str) -> str:
    """
    Normalize Azure DevOps PR refs:
    - Source branch usually exists locally (e.g. 'feature/ai-reviewer')
    - Target branch only exists as remote (e.g. 'remotes/origin/feature/ai-reviewer-roel')
    - Merge commit exists as 'remotes/pull/<id>/merge'
    """
    if branch_exists(branch):
        return branch
    short = branch.replace("refs/heads/", "")
    remote_ref = f"remotes/origin/{short}"
    if branch_exists(remote_ref):
        return remote_ref
    merge_ref = f"remotes/pull/{pr_id}/merge"
    if branch_exists(merge_ref):
        return merge_ref
    raise RuntimeError(f"Branch {branch} not found locally")


def get_mistral_response(
    user_prompt: str,
    system_prompt: str = "You are a helpful assistant.",
    temperature: float = 0.7,
) -> str:
    url = os.getenv("url_env")
    api_key = os.getenv("api_key")

    if url is None or api_key is None:
        raise ValueError("Environment variables url_env and api_key must be set.")

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}

    body = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "response_format": {"type": "json_object"},
    }

    response = requests.post(url, json=body, headers=headers)
    response.raise_for_status()

    data = response.json()
    return str(data["choices"][0]["message"]["content"])


def prepare_llm_input(diffs: Dict[Path, DiffType], repo_base="."):
    """
    Prepare LLM input with only changed files.
    
    diffs: dict with file paths and change_type/diff
    repo_base: local path to the repo root
    """
    llm_input = {
        "diff": {},
        "file_contents": {
            "new_files": {},
            "existing_files": {},
            "removed_files": {}
        }
    }

    for _path, info in diffs.items():
        path = str(_path)
        abs_path = Path(repo_base) / _path

        llm_input["diff"][path] = info

        if info["change_type"] == "add":
            try:
                with open(abs_path, "r") as f:
                    llm_input["file_contents"]["new_files"][path] = f.read()
            except FileNotFoundError:
                llm_input["file_contents"]["new_files"][path] = None

        elif info["change_type"] == "edit":
            try:
                with open(abs_path, "r") as f:
                    llm_input["file_contents"]["existing_files"][path] = f.read()
            except FileNotFoundError:
                llm_input["file_contents"]["existing_files"][path] = None

        elif info["change_type"] == "delete":
            llm_input["file_contents"]["removed_files"][path] = None

    return llm_input


def generate_comments(diffs):

    llm_input = prepare_llm_input(diffs)

    SYSTEM_PROMPT = """
    You are a code-review assistant. You receive a JSON object where each key is a file path and each value contains:
    - change_type
    - diff (unified diff format)

    Your task: analyze the diff and output structured JSON that can be used to post PR comments in Azure DevOps.

    ### PRIORITY ORDER
    1. correctness / bugs
    2. security issues
    3. maintainability / architecture
    4. performance
    5. readability / style

    ### OUTPUT FORMAT
    Return a single JSON object:

    {
    "<file_path>": {
        "summary": "Short description of what changed.",
        "comments": [
        {
            "message": "Description of the issue.",
            "proposed_solution": "Clear and actionable fix.",
            "category": "bug|security|maintainability|performance|style",
            "severity": "high|medium|low",

            "line_info": {
            "original_line": int | null,
            "new_line": int | null
            }
        }
        ]
    }
    }

    ### LINE NUMBER RULES
    Extract line numbers from diff hunks using these rules:

    - Each hunk starts with: @@ -X,Y +A,B @@
    - X = starting line in the original file
    - Y = number of lines in the original file hunk
    - A = starting line in the new file
    - B = number of lines in the new file hunk

    - For each line in the hunk:
    - Lines starting with '+' → increment new_line only
    - Lines starting with '-' → increment original_line only
    - Lines starting with ' ' → increment both original_line and new_line

    - For added or edited lines: set new_line to the line number in the new file
    - For removed lines: set new_line to null, but attach the comment to the **start of the removed block** (original_line)

    ### COMMENT LINE MATCHING
    - When suggesting a comment, first check if the target line **exactly matches a line in the diff**.
    - If no exact match is found:
    1. Use the snippet or surrounding context to locate the **closest line in the full file from the PR**.
    2. Attach the comment to that line.

    ### REQUIREMENTS
    - Only generate comments for real, meaningful issues.
    - Keep messages short and suitable for PR review.
    - proposed_solution must be specific and realistic.
    - Output must be valid JSON and contain nothing else.
    """

    prompt = json.dumps(llm_input, indent=2)
    result_str = get_mistral_response(
        user_prompt=prompt,
        system_prompt=SYSTEM_PROMPT,
        temperature=0.4,
    )

    print("[PR-BOT] Raw LLM output:", result_str, file=sys.stderr)

    try:
        review_output = json.loads(result_str)
    except json.JSONDecodeError as e:
        print(f"[PR-BOT] Failed to parse LLM output as JSON: {e}", file=sys.stderr)
        review_output = {}

    print(f"[PR-BOT] Parsed {len(review_output)} files from LLM output.", file=sys.stderr)

    return review_output


def generate_pr_comments(diffs) -> list[PRLineComment]:
    """
    Generate line-level comments from LLM review.
    """
    comments: list[PRLineComment] = []

    print("Preparing to send diffs to LLM for review")

    try:
        review_output = generate_comments(diffs=diffs)
        print(f"Created {len(review_output)} comments.")
    except Exception as e:
        print(f"LLM review failed: {e}")
        raise Exception from e

    for file_path, file_data in review_output.items():
        for c in file_data.get("comments"):
            line_info = c.get("line_info")
            new_line = line_info.get("new_line")
            original_line = line_info.get("original_line")

            comment_line = new_line if new_line is not None else original_line

            comments.append(
                PRLineComment(
                    file_path=file_path,
                    line=comment_line,
                    message=(
                        f"[PR-BOT]: [Severity: {c.get('severity')}], [Category: {c.get('category')}]\n"
                        f"{c.get('message', '')}\nSuggested fix: {c.get('proposed_solution', '')}"
                        + (f"\n(Note: line was removed starting at original line {original_line})"
                        if new_line is None else "")
                    )
                )
            )

    if not comments:
        print("No comments generated by LLM. Here is the diff for reference:\n")
        for file_path, info in diffs.items():
            print(f"--- {file_path} ({info.get('change_type')}) ---")
            print(info.get("diff", ""))
    
    return comments


def main() -> int:
    args = parse_args()
    
    pr_id = os.getenv("SYSTEM_PULLREQUEST_PULLREQUESTID")
    project = os.getenv("SYSTEM_TEAMPROJECT")
    source_branch = os.getenv("SYSTEM_PULLREQUEST_SOURCEBRANCH")
    target_branch = os.getenv("SYSTEM_PULLREQUEST_TARGETBRANCH")

    source_ref = normalize_branch(source_branch, pr_id)
    target_ref = normalize_branch(target_branch, pr_id)

    print(f"Diffing {target_ref}...{source_ref}")
        
    client = AzureDevOpsClient(project=project)
    file_diffs = client.get_branch_diffs(source_branch=source_ref, target_branch=target_ref, ignore=[".ipynb", ".lock"])

    print(f"Generating PR Comments for {len(file_diffs)} diffs.")
    comments = generate_pr_comments(diffs=file_diffs)

    print(f"Writing {len(comments)} to {args.output}")
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump([asdict(c) for c in comments], f, ensure_ascii=False, indent=2)

    print(f"All is well.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
