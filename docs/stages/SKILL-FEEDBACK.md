# Feedback for the `stage-pipeline` skill and the `stage-executor` agent

Lessons from running the pipeline in this repository that are **not specific to
this repository**. The repo's own practices live in [README.md](README.md);
this file is the part that should travel upstream, to the skill's and the
agent's source, so the next repository starts with it.

It exists because the skill's retro step writes only to the repo's practices
section. Every retro therefore improved one repository and nothing else. The
first entry below closes that loop.

**How to use this file.** On the machine that holds the skill's source, apply
each `proposed` entry (or decline it), then set its status here to
`upstreamed <date>` or `declined <reason>` and commit. Each entry gives the
evidence and the exact text, so it can be applied without this session's
context.

| Status | Meaning |
|---|---|
| `proposed` | Not yet in the skill or agent source |
| `upstreamed <date>` | Applied upstream |
| `declined <reason>` | Considered and rejected |

---

## sf-001 — Retros must feed the skill, not just the repo

- **Target:** skill, "Automatic retro" section; and a new section
- **Status:** proposed
- **Evidence:** the retro before stage 05 here produced twelve general lessons.
  The skill's text gave them nowhere to go but this repo's README. The skill
  and agent on this machine are read-only Guix store items, so the coordinator
  could not have edited them even if told to.

**Replace** the end of the "Automatic retro" paragraph ("…and update the repo's
Coordinator practices section in the same commit as the new prompt.") **with:**

> …and sort each finding into one of two places, in the same commit as the new
> prompt. A lesson about *this repo* (its gates, its environment, its shared
> files) goes into the repo's Coordinator practices section. A lesson that
> would be true in *any* repo goes into `docs/stages/SKILL-FEEDBACK.md` as a
> structured entry: id, target (skill or agent), evidence citing stage reports,
> the exact proposed text, and a status of `proposed`. Do not wait for a retro
> to record a general lesson; add the entry when you learn it.

**Add** a new section:

> ## Closing the loop with the skill itself
>
> The skill and the executor agent may be deployed read-only (a package store,
> a synced directory). Never edit them from inside a repo's session. The loop
> has three legs:
>
> 1. **Capture** — general lessons land in the repo's
>    `docs/stages/SKILL-FEEDBACK.md` (scaffold it with `docs/stages/README.md`).
> 2. **Harvest** — on the machine holding the skill's source, the user says
>    "harvest skill feedback from <repo>". Apply or decline each `proposed`
>    entry in the source, then mark it `upstreamed <date>` or `declined` in the
>    repo's file.
> 3. **Downstream** — this skill carries a `revision:` line. When scaffolding,
>    record it in the repo's README ("seeded from stage-pipeline revision N").
>    At every retro, compare: if the skill is newer, read its changelog and
>    merge the new seed practices into the repo's practices section.
>
> At every retro, also tell the user how many `proposed` entries are waiting.
> Unharvested feedback is the failure mode this section exists to prevent.

Also add `revision: 1` (and bump it on every edit) plus a short `## Changelog`
to the skill.

---

## sf-002 — The coordinator runs its own negative controls

- **Target:** skill, "The loop, per stage", step 1 (Author)
- **Status:** proposed
- **Evidence:** the coordinator's test payloads were wrong in 3 of the first 4
  stages. Stage 01: a negative control that could not fail at the severity the
  same prompt specified. Stage 03: a "remove the tool from PATH" command that
  left the tool on PATH. Stage 04: an example of "input the old code missed"
  that the old code matched. Each was caught by the executor. The first prompt
  written under this rule (stage 05) caught a harness flaw before launch.

**Add to step 1:**

> Before committing the prompt, **run every negative control, example input,
> and command it contains.** A payload that was never executed is a guess, and
> a wrong one costs the executor a deviation at best and pins nothing at worst.
> When the stage's approach is novel, prototype it and put the measured result
> in the prompt's motivation.

---

## sf-003 — Executor worktrees start at a stale commit

- **Target:** skill, step 2 (Launch); agent, contract item 2
- **Status:** proposed
- **Evidence:** 5 of 5 launches here. The isolated worktree was created at an
  old commit of the default branch, not at the branch holding the prompt.

**Add to the skill's prompt template, as the first thing after the title:**

> **First step, before anything else.** Check that this prompt file exists in
> your worktree. If it does not, `git fetch origin && git merge --ff-only
> origin/<base-branch>` and record it as a Deviation. If it is still missing,
> invoke the Blocked protocol.

**Add to the agent, contract item 2:**

> Your worktree may have been created at a stale commit. Verify your base
> before measuring any baseline; fast-forward to the named base if needed, and
> disclose it.

---

## sf-004 — Agent worktrees live inside the repository

- **Target:** skill, "First use in a repo: scaffold the envelope"; agent,
  contract item 5
- **Status:** proposed
- **Evidence:** a coordinator `git add -A` swept an executor's worktree
  (`.claude/worktrees/agent-…`) into a commit on the default branch as an
  embedded repository. Caught before push; the commit stays in history.

**Add to the scaffold steps:**

> Add `.claude/worktrees/` to the repo's `.gitignore` in the scaffold commit.

**Add to the skill's coordinator practices seed, and to the agent:**

> Stage files by path. Never `git add -A` or `git add .`.

---

## sf-005 — Tests before ports, and tests must prove they can fail

- **Target:** skill, coordinator practices seed; prompt template
- **Status:** proposed
- **Evidence:** the port here ran as tests-only stages (02, 05) followed by
  port stages (03, 04, 06). The tests-first stages found two real bugs by
  pinning them, and made two parallel ports verifiable in seconds. Mutation
  checks exposed a blind harness in stage 02 (text-mode capture hid the very
  carriage return under test).

**Add to the practices seed:**

> - **Never change the tests and the code they judge in the same stage.** Code
>   without coverage gets a tests-only stage first. The one exception is an
>   intentional behaviour change, where the prompt names the exact test edits
>   allowed.
> - **A test stage proves its tests can fail**: one temporary mutation per unit
>   under test, each shown to fail a test, each reverted. A test that cannot
>   fail is not a test. This applies to the test suite itself: if the suite is
>   to be refactored, it gets tests first too.

---

## sf-006 — Parallel stages need disjoint runtime resources

- **Target:** skill, step 2 (Launch)
- **Status:** proposed
- **Evidence:** stages 03 and 04 ran in parallel with disjoint file lists, but
  both ran an end-to-end suite that binds a host port, names a compose project,
  tags an image, and joins a network domain. Each needed its own of all four.

**Extend** "parallel stages MUST have disjoint allow-lists" **with:**

> …and disjoint **runtime resources**. If the gates start services, bind
> ports, name containers or images, or share a network, give each concurrent
> stage its own values in its prompt, and make the coordinator's own
> verification runs use isolated values too while any stage is in flight.

---

## sf-007 — Running the pipeline on an integration branch

- **Target:** skill, new short section
- **Status:** proposed
- **Evidence:** the user wanted the whole effort on a branch that merges to the
  default branch only when finished. The skill assumes the default branch
  throughout ("Commit it to the default branch FIRST").

**Add:**

> ## Integration-branch mode
>
> When the user wants the work kept off the default branch until it is done,
> name an integration branch and substitute it for "the default branch"
> everywhere above: prompts are committed to it, executors branch from it,
> stages merge into it. Sync the default branch into it at each stage merge so
> the eventual pull request stays mergeable. Promotion to the default branch is
> the user's act, preferably a merge commit so per-stage history survives.

---

## sf-008 — Commit message: exact subject line, trailer expected

- **Target:** skill, prompt template; agent, contract item 5
- **Status:** proposed
- **Evidence:** every executor added a `Co-Authored-By:` trailer under its own
  standing instructions, and had to disclose it as a deviation from "the exact
  single-line commit message".

**Change** "exact single-line commit message" to "exact commit **subject
line**", and add to the agent: "An attribution trailer required by your own
standing instructions is expected and is not a deviation."

---

## sf-009 — What to do when the executor agent is not registered

- **Target:** skill, step 2 (Launch)
- **Status:** proposed
- **Evidence:** at the first launch here the `stage-executor` agent type did
  not exist in the session (the agent file had synced after the session
  began). It appeared later.

**Add:**

> If the `stage-executor` agent type is not available, read
> `~/.claude/agents/stage-executor.md` and launch a general-purpose agent (same
> model, worktree isolation) with that contract embedded verbatim in the
> prompt. Tell the user you did so.

---

## sf-010 — Small coordinator fixes between stages

- **Target:** skill, top paragraph ("Never implement a stage yourself")
- **Status:** proposed
- **Evidence:** twice here a handful of few-line fixes had to land between
  stages (isolation of the test suite, lint coverage, a missing flag
  spelling). A full executor stage for each would have cost two ten-minute
  suite runs apiece. The user approved coordinator fix batches when asked.

**Add after** "Never implement a stage yourself":

> A *fix batch* is not a stage: a few small, already-understood fixes that
> unblock the next stage. The coordinator may make one **with the user's
> approval**, under the same discipline as a stage: staged by path, every gate
> rerun, one focused commit per concern, and disclosed to the user. Anything
> needing design, or touching more than a few lines per file, is a stage.

---

## sf-011 — Reverting a mutation when the work is uncommitted

- **Target:** agent, new contract item
- **Status:** proposed
- **Evidence:** stage 04's executor reverted a mutation with `git checkout --`,
  which restored the *committed* file, the old implementation, and discarded
  its uncommitted port. It recovered, and switched method.

**Add to the agent:**

> **Mutations and negative controls are reverted by copy-out and copy-back**,
> confirmed with a checksum. `git checkout --` restores the committed file,
> which may not be your work. Never run a baseline or a mutation while a gate
> that builds from the working tree is still running.

---

## sf-012 — Extra verification is welcome

- **Target:** agent, contract item 7
- **Status:** proposed
- **Evidence:** executors here went beyond their prompts in ways that mattered:
  running the fast tests under a real older interpreter, reaching skipped
  branches by mounting a fake `/proc/version`, comparing old and new output
  byte for byte. Item 7 ("do not start follow-on work") could be read as
  discouraging this.

**Add to item 7:**

> Read-only verification beyond what the prompt lists is welcome: it is not
> follow-on work. Disclose it under Deviations.

---

## sf-013 — Every skill and agent names its own source

- **Target:** skill and agent, frontmatter or a closing line; also `log-friction`
- **Status:** proposed
- **Evidence:** when the user asked where these lessons should go, nobody in
  the session knew where the skill came from. Finding out took walking a chain
  by hand: the skill directory is a symlink into the Guix store; the store item
  has no derivation, only a `files` referrer, which is Guix Home's signature;
  `guix home describe` names a stored `home/base.scm`; that file's comments
  mention `make apply`; a search found `~/dot_files`; its `claude/` submodule
  is the actual source. The answer is a repository, not a machine, but nothing
  in the deployed files says so.

**Add to each skill's and agent's text:**

> Source: `github.com/durantschoon/claude-config`, `skills/<name>/` (agents:
> `agents/<name>.md`). Deployed read-only by Guix Home from the `claude/`
> submodule of `dot_files` (`make apply`). Edit the source, never the deployed
> copy; harvest `docs/stages/SKILL-FEEDBACK.md` entries there.

With that line in place, the harvest step in `sf-001` can name where to go.
