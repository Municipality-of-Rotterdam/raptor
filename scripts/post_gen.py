"""Post-generation script for Raptor copier template."""
# ruff: noqa: INP001, T201, S101, S603, S607

import os
import re
import shutil
import subprocess
import sys

target_repo_dir = os.getcwd()
print(f"target repo dir: {target_repo_dir}")

# Read answers from environment variables set by copier
project_type = os.environ.get("COPIER_PROJECT_TYPE", "project")
ci_cd = os.environ.get("COPIER_CI_CD", "GitHub")
repo_name = os.environ.get("COPIER_REPO_NAME", "my_repo")
package_name = os.environ.get("COPIER_PACKAGE_NAME", "")
author_name = os.environ.get("COPIER_AUTHOR_NAME", "")
author_email = os.environ.get("COPIER_AUTHOR_EMAIL", "")

# ===========================
# Validation
# ===========================

if project_type == "package":
    PACKAGE_NAME_REGEX = r"^[a-zA-Z0-9_]+$"
    if not re.match(PACKAGE_NAME_REGEX, package_name):
        print(
            f"ERROR: package name '{package_name}' is not valid. Use only alphanumeric characters and underscores."
        )
        sys.exit(1)

    AUTHORREGEX = r"([A-Za-z]+ )+[A-Za-z]+$"
    EMAILREGEX = r"[A-Za-z0-9._]+@[A-Za-z0-9_].+[A-Za-z]+$"
    if not re.match(AUTHORREGEX, author_name):
        print(
            f"ERROR: author name '{author_name}' is not valid. Should be like: Name Surname"
        )
        sys.exit(1)
    if not re.match(EMAILREGEX, author_email):
        print(
            f"ERROR: author email '{author_email}' is not valid. Should be like: name@my.domain"
        )
        sys.exit(1)

if project_type == "project":
    MODULE_REGEX = r"^[a-zA-Z]([-a-zA-Z0-9]*[a-zA-Z0-9])?$"
    aml_base_deployment_name = repo_name.lower().replace(" ", "-").replace("_", "-")
    if not re.match(MODULE_REGEX, aml_base_deployment_name):
        print(
            f"ERROR: AML base name '{aml_base_deployment_name}' should only consist of letters, dashes and numbers, starting with a letter."
        )
        sys.exit(1)
    if not (3 <= len(aml_base_deployment_name) <= 20):
        print(
            f"ERROR: AML base name '{aml_base_deployment_name}' should be 3-20 characters."
        )
        sys.exit(1)

# ===========================
# Move selected repo contents to root, remove unused
# ===========================

keep_dir = f"{project_type}_repo"
other_dir = "package_repo" if project_type == "project" else "project_repo"

print(f"Moving {keep_dir}/ contents to root...")
for item in os.listdir(keep_dir):
    src = os.path.join(keep_dir, item)
    dst = os.path.join(target_repo_dir, item)
    if os.path.exists(dst):
        if os.path.isdir(dst) and not os.path.islink(dst):
            shutil.rmtree(dst)
        else:
            os.remove(dst)
    shutil.move(src, dst)
shutil.rmtree(keep_dir)
print(f"Removed {keep_dir}/")

if os.path.exists(other_dir):
    shutil.rmtree(other_dir)
    print(f"Removed {other_dir}/")

# Remove scripts/ and .copier-answers.yml
if os.path.exists("scripts"):
    shutil.rmtree("scripts")
    print("Removed scripts/")

# ===========================
# Conditional CI/CD folder cleanup
# ===========================

if ci_cd == "GitHub":
    devops_folders = ["devops_pipelines"]
    devops_files = ["azure-pipelines.yml", "azurepipelines-coverage.yml"]
    for folder in devops_folders:
        folder_path = os.path.join(target_repo_dir, folder)
        if os.path.exists(folder_path):
            print(f"Removing DevOps folder: {folder_path}")
            shutil.rmtree(folder_path)
    for file in devops_files:
        file_path = os.path.join(target_repo_dir, file)
        if os.path.exists(file_path):
            print(f"Removing DevOps file: {file_path}")
            os.remove(file_path)
elif ci_cd == "DevOps":
    github_folders = [".github"]
    for folder in github_folders:
        folder_path = os.path.join(target_repo_dir, folder)
        if os.path.exists(folder_path):
            print(f"Removing GitHub folder: {folder_path}")
            shutil.rmtree(folder_path)

# ===========================
# Git repo config
# ===========================

subprocess.call(
    ["git", "config", "--global", "--add", "safe.directory", target_repo_dir]
)
subprocess.call(["git", "init"])
subprocess.call(["git", "add", "."])
print("committing initialized repo")
subprocess.call(["git", "commit", "-m", "init"])

print("switching to new branch develop")
subprocess.call(["git", "checkout", "-b", "develop"])

if project_type == "package":
    print("creating documentation branch based on develop")
    subprocess.call(["git", "checkout", "-b", "generated/docs"])
    print("switching back to branch develop")
    subprocess.call(["git", "checkout", "develop"])
