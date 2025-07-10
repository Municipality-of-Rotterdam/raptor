"""Script to run after generating repo."""
# ruff: noqa: INP001, T201, S101, S603, S607

import logging
import os
import shutil
import subprocess

logger = logging.getLogger()

# This file will be executed from the root of the new repo
target_repo_dir = os.getcwd()
print(f"target repo dir: {target_repo_dir}")

target_repo_name = "{{cookiecutter.repo_name}}"
assert target_repo_dir.endswith(
    target_repo_name
), f"Unreachable exception! Target repository directory {target_repo_dir} does not end \
    with the target repository name {target_repo_name}, \
    cannot mark this directory as safe."


# ===========================
# Conditional folder cleanup
# ===========================

# Read the choice made by user for additional_prompts
choice = "{{cookiecutter.additional_prompts}}".lower()

if choice == "github":
    devops_folders = [
        "devops_pipelines",
    ]
    devops_files = [
        "azure-pipelines.yml",
        "azurepipelines-coverage.yml",
    ]
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

elif choice == "devops":
    github_folders = [
        ".github",
    ]
    for folder in github_folders:
        folder_path = os.path.join(target_repo_dir, folder)
        if os.path.exists(folder_path):
            print(f"Removing GitHub folder: {folder_path}")
            shutil.rmtree(folder_path)
else:
    print(f"Unknown choice for additional_prompts: {choice}. No folders removed.")

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

print("creating documentation branch based on develop")
subprocess.call(["git", "checkout", "-b", "generated/docs"])

print("switching back to branch develop")
subprocess.call(["git", "checkout", "develop"])
