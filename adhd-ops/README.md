# adhd-ops (the plugin)

The running implementation of [the playbook](../PLAYBOOK.md). Read that first -- this README is
about wiring, not ideas.

## Architecture

```
skills/
  workspace-config/   ← YOUR configuration. Everything else reads this first.
  daily-briefing/     ← morning brief (scheduled). Renderer + spec contract live here.
  shutdown/           ← end-of-day email (scheduled). Reuses the briefing's renderer.
  gsd/                ← the rescue command (/gsd) + scheduled poke mode.
  followup-triage/    ← weekly triage (scheduled report + /review-followups interactive).
  retro/              ← monthly telemetry read (scheduled or on demand).
commands/
  gsd.md              ← /gsd
  park.md             ← /park
  review-followups.md ← /review-followups
scheduled-task-prompt-*.md  ← copy/paste templates for Claude Code web routines
```

Design rule inherited from the private original: **skills own behavior; scheduled-task prompts are
skeletal** (which skill to run, that the run is headless, any per-run flag -- nothing else). A
prompt is frozen into its trigger the moment you paste it, so anything that might change belongs
in the skill, which is fetched fresh at run time. Editing a `scheduled-task-prompt-*.md` file does
not change a live routine; re-paste when the prompt text itself matters.

The other structural rule: **the model writes the words, a script owns the structure.** The
morning brief and shutdown emails are rendered by `skills/daily-briefing/scripts/brief.mjs`
(zero-dependency Node), which hard-enforces the playbook's invariants -- exactly one Big Thing,
max 5 TL;DR bullets, exactly 3 options per forced decision, a required next step on every parked
loop, calm fixed empty-state lines. A sloppy compose can't drop them; the renderer fails loudly
instead of sending a broken email.

## Setup checklist

1. **Install** the plugin (see the repo root README).
2. **Fill in `skills/workspace-config/SKILL.md`.** It's a template with `⚠️ CONFIGURE` markers:
   your timezone, delivery email, calendars, task list, state store, notification channel, data
   sources, and voice. Every other skill resolves "the primary calendar," "the task list," "the
   state store" against what you write there. The plugin is inert until this is done -- skills
   that find an unconfigured template say so and stop.
3. **Set up a state store.** The system needs durable cross-run state (a few small JSON/NDJSON
   files). The simplest option is a **private GitHub repo** accessed through the GitHub MCP
   connector; the contract (compare-and-swap writes, append-only logs, a registry of paths) is
   specified in workspace-config. Don't skip the contract -- concurrent runs without CAS writes
   will eventually eat your state.
4. **Connect your connectors.** Calendar, task app, and mail are the load-bearing three. Chat and
   a work tracker (GitHub, etc.) enrich the brief but everything degrades gracefully without them.
5. **Create the routines.** In Claude Code web, create scheduled routines and paste the matching
   `scheduled-task-prompt-*.md` template into each:
   - morning brief -- workday mornings, before your day starts
   - shutdown -- workday late afternoon
   - gsd poke -- workday early afternoon (optional; needs a push channel)
   - weekly triage -- one morning a week, before that day's brief
   - retro -- monthly (optional)
6. **Dry-run.** Ask Claude Code interactively to "run the daily-briefing skill in dry-run mode"
   -- it will gather and compose but show you the result instead of sending. Fix config gaps
   before scheduling anything.

## Degradation philosophy

Every skill follows the same law (playbook, law 16): the deliverable goes out degraded rather
than not at all; missing connectors shrink a section and get one honest line, never a fake; and
failures that won't self-heal (expired auth) are surfaced loudly exactly once per day, while
transient ones stay quiet and let the next run self-heal. The rescue command is the extreme case:
with literally every data source down, it still produces one small action, a first step, and
permission to bail.

## Adapting to your stack

The skills name *roles*, not products: "the task app," "the primary calendar," "chat." Bindings
live in workspace-config, and the skills' tool examples (Microsoft To Do via an ms365 connector,
Google Calendar, Slack, Gmail) are examples, not requirements. If your stack differs, change the
binding table, not the skills.

If you replace the email channel entirely (say, a static site or a messaging app), keep two
properties: **push, not pull** (it must arrive where you already look) and **the renderer's
invariants** (whatever renders your version should refuse structurally-invalid output the same way
`brief.mjs` does).
