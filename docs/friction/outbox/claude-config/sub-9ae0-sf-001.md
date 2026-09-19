---
id: sub-9ae0
ref: sf-001                 # fuller wording in docs/stages/SKILL-FEEDBACK.md
target_repo: github.com/durantschoon/claude-config
targets:
  - skills/stage-pipeline/SKILL.md
kind: mechanism              # symptom = may be staged; mechanism = needs design session
occurrences: 3
author: Claude Fable 5.1, coordinator session (LLM author, not the human's words)
source_repo: github.com/durantschoon/ros2_turtlesim @ python-port
machine: WSL 2, Ubuntu 22.04, user durant
date: 2026-09-18
status: submitted         # curator sets: accepted <fr-id> | merged-into <fr-id> | declined <why>
evidence:
  - docs/stages/README.md (this repo) 'Added by the retro before stage 05'
  - claude-config docs/stages/README.md:101 records the stale-base lesson; dot_files learned it first; this repo re-learned it 5 times
---

# Retro lessons never leave the repo they were learned in

## What happened

The retro step writes only to the repo's own practices section. General lessons
are re-learned per repo: the stale-worktree lesson exists in dot_files, in
claude-config's README, and now here, and never reached the skill's seed text.

## Suggested direction

Give the retro a second output: general lessons become submissions to the
skill's source repo (this outbox format, or friction rows once claude-config
has a log). Add a revision line to the skill so repos can tell when their
seeded practices are out of date.
