---
id: sub-ffb2
ref: sf-013                 # fuller wording in docs/stages/SKILL-FEEDBACK.md
target_repo: github.com/durantschoon/claude-config
targets:
  - skills/stage-pipeline/SKILL.md
  - skills/*/SKILL.md
  - agent-templates/*.md
kind: symptom              # symptom = may be staged; mechanism = needs design session
occurrences: 1
author: Claude Fable 5.1, coordinator session (LLM author, not the human's words)
source_repo: github.com/durantschoon/ros2_turtlesim @ python-port
machine: WSL 2, Ubuntu 22.04, user durant
date: 2026-09-18
status: submitted         # curator sets: accepted <fr-id> | merged-into <fr-id> | declined <why>
evidence:
  - this session: the source was found by walking symlink -> /gnu/store -> Guix Home 'files' referrer -> guix home describe -> ~/dot_files -> claude/ submodule
---

# Nothing deployed says where a skill or agent comes from

## What happened

Asked where lessons should go, nobody in the session knew where the skill came
from. Agents do say 'GENERATED FILE, edit agent-templates/…', which is the
right idea; skills say nothing, and neither names the repository.

## Suggested direction

One line in every skill and generated agent naming the source repo and path,
and that the deployed copy is read-only.
