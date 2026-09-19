---
id: sub-25dd
ref: sf-006                 # fuller wording in docs/stages/SKILL-FEEDBACK.md
target_repo: github.com/durantschoon/claude-config
targets:
  - skills/stage-pipeline/SKILL.md
kind: symptom              # symptom = may be staged; mechanism = needs design session
occurrences: 1
author: Claude Fable 5.1, coordinator session (LLM author, not the human's words)
source_repo: github.com/durantschoon/ros2_turtlesim @ python-port
machine: WSL 2, Ubuntu 22.04, user durant
date: 2026-09-18
status: submitted         # curator sets: accepted <fr-id> | merged-into <fr-id> | declined <why>
evidence:
  - stage-03-PROMPT.md and stage-04-PROMPT.md, 'Running the gates without colliding'
---

# Parallel stages collided on runtime resources, not files

## What happened

Two stages with disjoint allow-lists both ran an end-to-end gate that binds a
host port, names a compose project, tags an image and joins a network domain.
Each needed its own value of all four, and so did the coordinator's
verification runs.

## Suggested direction

Extend 'disjoint allow-lists' to disjoint runtime resources, assigned per stage
in the prompt.
