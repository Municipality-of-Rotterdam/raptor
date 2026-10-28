# Skills

Skills for AI coding agents (Claude Code, Codex, GitHub Copilot, Cursor, ...) in the
[Agent Skills](https://agentskills.io) format: one folder per skill with a `SKILL.md` (instructions for the agent)
and, if needed, `scripts/`. The agent loads a skill when a request matches its description.

| Skill | What it does |
|---|---|
| [new-repo](new-repo/SKILL.md) | Create a new package or project repo from raptor, or finish the setup of an existing one, including Azure DevOps (repo, pipelines, permissions, branch policies, status badge). It runs the tasks of a local raptor clone (see `.taskfile/readme.md`), skips what is done and asks before each change in Azure DevOps. |

## Installation

Install the skills for the agents you use (`-g`: for all your projects; `npx skills update` to update):

```
npx skills add https://dev.azure.com/GemeenteRotterdam/DAPR/_git/raptor -g
```

`npx` comes with Node.js. If `npx --version` fails, install Node.js with nvm (no sudo needed): run the install command
from the [nvm installation instructions](https://github.com/nvm-sh/nvm#installing-and-updating), open a new terminal
(to load nvm) and run `nvm install --lts`.

Or link a skill from your raptor clone, so it follows the checked-out branch, e.g.
`ln -s <raptor clone>/skills/new-repo ~/.agents/skills/` (Codex, Copilot, ...) or `~/.claude/skills/` (Claude Code).

Then just ask the agent, e.g. "create a new package repo".

## Prerequisites

The skills use the tools and config of a raptor setup (task, copier, uv, direnv, Azure CLI, `~/taskfile.env`,
`~/.taskrc.yml`, copier settings). Installing and configuring them is described in the company documentation
(Confluence) and in `.taskfile/readme.md`. A skill checks this first (e.g. `new-repo/scripts/preflight.sh`) and
tells you what is missing.

## Adding a skill

Add a folder `skills/<name>/` with a `SKILL.md` (frontmatter `name` equal to the folder name, and a `description`
that says when to use it) and add it to the table above. Put checks that must always run the same way in a script in
`scripts/` instead of loose commands in `SKILL.md`, so that also a small model can't get them wrong.
