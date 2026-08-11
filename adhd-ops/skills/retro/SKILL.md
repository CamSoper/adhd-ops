---
name: retro
description: >
  The monthly retrospective -- the component that finally reads what everything
  else writes. Invoked by the monthly retro scheduled task, or by the user
  asking for "a retro", "how's the system doing", "what do the patterns say".
  Reads the history files (briefing, shutdown, gsd/poke), reports the patterns
  a daily view can't see, and proposes exactly one tuning change. Read-only
  against every log it consumes. Reads workspace-config first.
version: 0.1.0
---

# Retro

The suite writes telemetry -- briefing run notes, gsd/poke records, shutdown handoffs -- and
without this skill, nothing reads any of it. The retro closes the learning loop: once a month,
look at what actually happened, say what the patterns are, and propose **one** change. Not a
report card on the user -- a tune-up report on *the system*.

**Prerequisites:** `${CLAUDE_PLUGIN_ROOT}/skills/workspace-config/SKILL.md` (state contract,
bindings, voice). This run is **read-only against every log**: it never harvests the capture
inbox and never modifies tasks or state beyond its own output.

## Step 1: Read the month (tails, cheap)

All via `state_read` with a tail sized to ~5 weeks; every input optional -- absent files are just
an empty section, not an error:

- `briefing/history.ndjson` -- run cadence, strike escalations/retirements, gap flags, connector
  trouble.
- `shutdown/history.ndjson` -- shutdown consistency, wins-per-day shape, whether proposed One Big
  Things match what the next morning's brief actually led with.
- `gsd/history.ndjson` -- rescues: when they happen, which pick-rung fired, whether the ritual
  was taken; pokes: sent vs. silent, and whether a poked afternoon shows completions after the
  poke.

## Step 2: Find the patterns

Look for the things a daily view can't see. Non-exhaustive prompts:

- **Strike half-life** -- how long items live at each strike; do retirements eventually ship, or
  die?
- **Rescue shape** -- what time do /gsd calls and pokes cluster? Do poked afternoons look
  different from unpoked ones?
- **Handoff fidelity** -- do shutdown-proposed One Big Things become morning ones? Do they get
  *done*?
- **Current-thing usage** -- is the focus layer being fed, and do current-thing weeks look
  different in the win counts?
- **Noise audit** -- anything the brief keeps saying that never changes behavior (a recurring
  run-note paragraph, a pill nobody acts on) is a candidate for deletion. Less email is a
  feature.
- **Connector health** -- auth-shaped failures and how long they lasted.

Numbers stay honest: small n is small n -- say "3 rescues this month" rather than a percentage
dressed up as a trend.

## Step 3: Deliver

1. **Email** -- one short message via the shutdown renderer (`kind: "shutdown"` spec, reused:
   `title`: `"🔁 Retro"`, `wins` = the month's 3–5 headline patterns, `loops` = up to 3 "worth
   watching" items with their evidence as `state` and the watch as `nextStep`, `tomorrow.obt` =
   the one proposed tuning change, `footer.signoff` closes it). Subject:
   `🔁 Retro -- <month>: <headline>`.
2. **Archive** the full read with evidence (dates, links, counts) if an archive is configured.
3. **Exactly one proposed tuning change.** One, not a list -- the same law as One Big Thing.
   Frame it as a ❓ proposal with the evidence. If the user says yes in a live session:
   item-level changes (a threshold, a snooze) get applied via the normal write disciplines;
   rule-level changes are edits to this plugin's skill files -- point at the file and the line,
   and never pretend a runtime session edited a skill it can't reach.

## Step 4: Record

`state_append` to `retro/history.ndjson`:
`{ts, month, emailSent, proposal: "<the one change>", runNote}`.

## Degradation

Missing inputs shrink the retro; they never block it. If *every* history file is absent, say so --
that's itself the finding ("the system wrote no telemetry this month") -- and skip the email.
Mail down → archive only; the next brief's reauth machinery owns the loud part.
