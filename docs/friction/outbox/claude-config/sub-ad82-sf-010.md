---
id: sub-ad82
ref: sf-010                 # fuller wording in docs/stages/SKILL-FEEDBACK.md
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
  - ros2_turtlesim python-port fix batches, each user-approved or disclosed: 57f2558, cefe7de, cfa66f3, 8e9eac5
---

# Small fixes between stages have no sanctioned path

## What happened

Three times a handful of few-line fixes had to land between stages. A full
stage for each costs two ten-minute gate runs plus an executor. The user
approved coordinator fix batches when asked; the skill says 'never implement a
stage yourself' and is silent on this.

## Suggested direction

Define a fix batch: user-approved, staged by path, every gate rerun, one commit
per concern, disclosed. Anything needing design is a stage.
