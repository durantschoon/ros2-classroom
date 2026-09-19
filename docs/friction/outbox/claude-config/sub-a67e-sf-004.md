---
id: sub-a67e
ref: sf-004                 # fuller wording in docs/stages/SKILL-FEEDBACK.md
target_repo: github.com/durantschoon/claude-config
targets:
  - skills/stage-pipeline/SKILL.md
  - agent-templates/stage-executor.md
kind: symptom              # symptom = may be staged; mechanism = needs design session
occurrences: 1
author: Claude Fable 5.1, coordinator session (LLM author, not the human's words)
source_repo: github.com/durantschoon/ros2_turtlesim @ python-port
machine: WSL 2, Ubuntu 22.04, user durant
date: 2026-09-18
status: submitted         # curator sets: accepted <fr-id> | merged-into <fr-id> | declined <why>
evidence:
  - ros2_turtlesim main 6bbc06d (the mistake), 9f9c33a (the forward fix)
---

# An unscoped git add swept an agent worktree into a commit

## What happened

Agent worktrees live inside the repository under .claude/worktrees/. A
coordinator `git add -A` committed one to the default branch as an embedded
repository. Caught before push; rewriting the commit was permission-blocked, so
it stays in history.

## Suggested direction

Scaffold step adds .claude/worktrees/ to .gitignore; practices seed and
executor contract say: stage by path, never `git add -A`.
