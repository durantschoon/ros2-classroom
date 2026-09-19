---
id: sub-3e6b
ref: sf-008                 # fuller wording in docs/stages/SKILL-FEEDBACK.md
target_repo: github.com/durantschoon/claude-config
targets:
  - skills/stage-pipeline/SKILL.md
  - agent-templates/stage-executor.md
  - agent-templates/stage-reviewer.md
kind: symptom              # symptom = may be staged; mechanism = needs design session
occurrences: 5
author: Claude Fable 5.1, coordinator session (LLM author, not the human's words)
source_repo: github.com/durantschoon/ros2_turtlesim @ python-port
machine: WSL 2, Ubuntu 22.04, user durant
date: 2026-09-18
status: submitted         # curator sets: accepted <fr-id> | merged-into <fr-id> | declined <why>
evidence:
  - stage-02-REPORT.md Deviation 11 and each later report
---

# Every executor disclosed its commit trailer as a deviation

## What happened

Prompts ask for an 'exact single-line commit message'; executors add an
attribution trailer under standing instructions and report a deviation each
time. The new stage-reviewer checks the subject byte-for-byte, which is the
right unit.

## Suggested direction

Say 'exact subject line' in the skill, and in the executor template that the
trailer is expected.
