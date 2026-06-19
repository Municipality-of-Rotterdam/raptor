# AI Reviewer Integration - Implementation Notes

## Overview
This repository contains the integration of an AI code reviewer workflow for Azure DevOps CI/CD pipelines. The feature analyzes PR changes using Mistral LLM and posts non-blocking review comments using pure PowerShell in the pipeline template.

## Architecture

### Key Change: PowerShell-Only Implementation
The AI reviewer logic has been moved from `package_repo/devops_pipelines/scripts/ai_reviewer.py` into `.azuredevops/templates/ai_reviewer.yml` as a PowerShell script. This allows:
- **Zero dependencies** in generated repositories
- **Automatic updates** when raptor templates are updated
- **No need to regenerate** existing repositories

### Files Modified

#### 1. `.azuredevops/templates/ai_reviewer.yml` (Updated)
Azure DevOps pipeline template that:
- Configures Python environment with uv (for pre-commit)
- Uses **PowerShell** to:
  - Fetch git diffs between PR branches
  - Call Mistral API for code analysis
  - Post PR comments via Azure DevOps REST API
- Runs as non-blocking stage on PRs
- No longer requires `ai_reviewer.py` in generated repos

#### 2. `package_repo/{{ cookiecutter.repo_name }}/devops_pipelines/templates/ci.yml` (Updated)
- Added `AIReview` stage between `PreCommit` and `UnitTest`
- Condition: `eq(variables['Build.Reason'], 'PullRequest')`
- Uses `.azuredevops/templates/ai_reviewer.yml@raptor`
- Removed `pat_username` and `pat` parameters (no longer needed)

#### 3. `package_repo/{{ cookiecutter.repo_name }}/pyproject.toml` (Updated)
Removed from `[dependency-groups]`:
- `azure-devops>=7.1.0b4`
- `requests>=2.32.0`

#### 4. `changelog.md` (Updated)
Documented the AI reviewer feature under [Unreleased] section.

## Environment Variables Required

Azure DevOps Pipeline Variables (configure per project):
- `url_env` - LLM chat-completions endpoint (OpenAI-compatible). For the self-hosted Azure ML
  endpoint this is the base URL plus `/chat/completions`, e.g.
  `https://qwen-endpoint.westeurope.inference.ml.azure.com/v1/chat/completions`
- `api_key` - API key for the endpoint (sent as `Authorization: Bearer <api_key>`)
- `model_name` - Model identifier sent in the request body, e.g. `/models/xxx`

PR comment posting uses the build's `System.AccessToken` (OAuth) — enable
"Allow scripts to access the OAuth token" on the job/pipeline. No PAT is required.

## PowerShell Implementation Details

The `ai_reviewer.yml` template now uses PowerShell for:

1. **Git Diff Retrieval**: Uses `git diff` command to get changes between branches
2. **Diff Parsing**: Parses unified diff format to extract file paths and changes
3. **LLM API Calls**: Uses `Invoke-RestMethod` to call the OpenAI-compatible Azure ML endpoint (Qwen)
4. **PR Comment Posting**: Uses Azure DevOps REST API to post review comments

All logic is self-contained in the YAML template - no external scripts needed.

## Next Steps / TODO

1. **Test the integration**: Create a test repository using the template and verify AI reviewer runs on PRs
2. **Mistral API setup**: Ensure API credentials are properly configured in Azure DevOps variable groups
3. **Tuning the system prompt**: The LLM prompt in `ai_reviewer.yml` may need adjustment based on review quality
4. **Consider rate limiting**: Add retry logic if Mistral API rate limits are hit
5. **Documentation**: Update README files to document the AI reviewer feature

## Benefits

- ✅ **No Python dependencies** in generated repositories
- ✅ **Zero maintenance** - updates propagate automatically from raptor
- ✅ **Simpler architecture** - all logic in one YAML file
- ✅ **Faster CI** - no need to sync test dependencies just for AI review

## Git Branch
Current branch: `feature/ai-reviewer-integration`
Ready for PR creation after testing.
