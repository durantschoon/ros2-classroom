---
id: sub-2af8
ref: sf-005                 # fuller wording in docs/stages/SKILL-FEEDBACK.md
target_repo: github.com/durantschoon/claude-config
targets:
  - skills/stage-pipeline/SKILL.md
kind: mechanism              # symptom = may be staged; mechanism = needs design session
occurrences: 2
author: Claude Fable 5.1, coordinator session (LLM author, not the human's words)
source_repo: github.com/durantschoon/ros2_turtlesim @ python-port
machine: WSL 2, Ubuntu 22.04, user durant
date: 2026-09-18
status: submitted         # curator sets: accepted <fr-id> | merged-into <fr-id> | declined <why>
evidence:
  - stage-02-REPORT.md (two real bugs found by pinning; blind harness found by mutation 6)
  - stage-05-REPORT.md
---

# Porting without tests first would have been unverifiable

## What happened

Tests-only stages before port stages found two real bugs, made two parallel
ports checkable in seconds, and their mutation checks exposed a test harness
that could not see the thing it tested.

## Suggested direction

Practices seed: never change tests and the code they judge in one stage; a test
stage proves its tests can fail by mutation; this applies to the test suite
itself.
