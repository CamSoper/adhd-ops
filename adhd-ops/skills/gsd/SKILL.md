---
name: gsd
description: >
  The rescue command. The user surfaces mid-doomscroll -- "what should I do
  right now", "I've lost the afternoon", "get me moving", "/gsd" -- and needs
  direction and momentum, not a briefing. Reads the current-focus layer,
  today's brief, and the calendar runway, then hands back exactly ONE next
  action sized to the time actually available. Also carries poke mode -- the
  scheduled calendar-gap nudge pushed to the user's phone instead of waiting
  to be summoned. Reads workspace-config first for every binding.
version: 0.1.0
---

# GSD (Get Stuff Done)

The user has just noticed hours went somewhere they shouldn't have. They may or may not have read
today's brief. The job is **direction + momentum in under a minute of reading** -- not a status
report, not a retrospective, and absolutely not a guilt trip.

**Prerequisites:** `${CLAUDE_PLUGIN_ROOT}/skills/workspace-config/SKILL.md` for bindings and
voice. Poke mode additionally needs the configured push tool; no push tool configured → poke mode
simply never runs.

## Design principles

1. **Fast beats thorough.** Every input below is optional; the only hard requirement is producing
   one next action. Never spend minutes fetching before saying something useful.
2. **One action.** Same law as the brief's One Big Thing: ten suggestions is zero suggestions.
3. **Shrink the first step.** The activation energy of *starting* is the hurdle. The first step
   must be trivially small ("open the doc, write one sentence").
4. **Permission structure, not pressure.** Explicit permission to bail early -- "ten minutes
   counts" -- and exactly one smaller fallback. Deadline honesty is fine; shame is not.

## Step 1: Clock

```bash
TZ=<configured timezone> date "+%A %Y-%m-%d %H:%M"
```

Never infer the time or weekday. Everything downstream is sized to what's left of *this* day.

## Step 2: State reads (per the state contract)

- `focus/current.json` -- filter to **active** entries by `expires` vs today. Do NOT
  garbage-collect expired entries here; that's the morning brief's job. Missing file → empty.
- `shutdown/handoff.json` -- if it's from last night, its proposed One Big Thing is a strong
  candidate.

State store absent or failing → degrade to Steps 3–4, say so in one clause ("state's unreachable,
working from the calendar"), and keep moving.

## Step 3: Today's brief (read, never re-scrape)

If an archive is configured, fetch today's brief from it: One Big Thing, Today's Focus, anything
in Decide Today. **Never re-run the morning's scrape** -- the brief already did that. No brief
today (weekend, holiday, pre-run hour)? Proceed without it.

## Step 4: Calendar runway

List today's remaining events on the primary calendar. Compute the **runway**: minutes until the
next meeting, or until a sane end of day if the calendar's clear. The action gets sized to the
runway -- a 40-minute gap gets a 40-minute-shaped task, not "ship the redesign."

## Step 5: Pick ONE action

Priority order -- first hit wins:

1. An active **`kind: "current"` entry** -- the declared current thing is the standing answer to
   "what should I be doing."
2. The brief's **One Big Thing** (or top unfinished focus item).
3. Last night's **handoff proposal**, if the brief never surfaced it.
4. **Calendar-driven prep** -- if the next meeting needs something from the user, that's the
   action.
5. The **smallest genuinely useful thing** you know about. Improvise honestly; don't invent
   busywork to have an answer.

Never surface an actively snoozed item -- it's parked for a reason, and a rescue moment is the
worst possible time to un-park it.

## Step 6: Deliver (in-conversation -- this is the whole artifact)

Voice per workspace-config, tuned for the moment: dry, warm, zero guilt. The acknowledgment is
matter-of-fact at most ("right, the afternoon happened") -- never a lecture, never more than one
line. Then:

- **The action**, stated plainly, sized to the runway, with a one-line *why now*.
- **The first step**, trivially small and immediately startable.
- **The bail clause** -- explicit permission to stop early; ten minutes counts.
- **One smaller fallback** -- if the action reads as too big right now, name the ten-minute
  version. One fallback, not a menu.

Total length: a few short paragraphs. Not an email, no HTML, no headers, no checklist.

## Step 6.5: Current-thing offer (once, only when it fits)

If `focus/current.json` had no active `kind: "current"` entry and the pick came from the brief or
handoff, tack on one line: "want me to make this the current thing for the week?" Yes → write the
entry (id slugged from the action, default expiry today + 14 days; CAS, retry-once). Ignored or
declined → dropped, never mentioned again this session. One offer max.

## Step 7: The ritual offer (one yes fires everything)

Starting is one decision, not four. After the action (and at most one Step 6.5 question), make
**one** bundled offer -- "want the full ritual?" -- and a single yes fires all of it:

- **Audio**: one pick per `${CLAUDE_PLUGIN_ROOT}/skills/gsd/references/focus-audio.md` --
  one-tap link, taste-based, no audiobooks (the reference says why).
- **Check-in**: arm one nudge ~45 minutes out via a `send_later`-style scheduling tool if the
  session has one. No such tool → this piece silently drops out of the bundle; never mention
  what's missing.
- **Environment**: if the session happens to have smart-home tools and the user has a focus
  scene, set it. Absent → same silent drop-out; never a permission-prompt detour mid-rescue.

Offer whichever pieces exist as **one** question, not a menu. Declined or ignored → drop
instantly, zero follow-up sell. The user can also take just one piece ("just the music") -- their
answer is the spec.

## Step 8: History (best-effort)

`state_append` one record to `gsd/history.ndjson`:

```json
{"ts": "<ISO>", "action": "<the action>", "source": "current", "minutes": 50, "audio": "offered", "audioAccepted": true, "checkinOffered": false, "currentSet": false}
```

`source` ∈ `current | brief | handoff | calendar | improvised` (which Step 5 rung fired);
`minutes` = the runway. State store absent → **skip silently**. This file exists so the retro can
notice patterns, not to score anything.

## Poke mode (scheduled -- the rescue that finds you)

The command is pull; this is the push half. Invoked **only** by the gsd-poke scheduled task
(headless, no human in the loop) -- never in a live session. The bar for speaking is high and
**silence is the designed common outcome**: a poke that fires daily is a notification the user
tunes out by Thursday.

1. **Gate.** Weekend → exit. Holiday or OOO (same check as the brief's Step 0) → exit.
2. **Once a day, ever.** `state_read` `gsd/poke.json` (`{lastPokeDate}`); already poked today →
   exit. State store unreachable → exit (better no poke than a double poke).
3. **Runway.** Free block ahead < 45 minutes → exit (nothing useful fits; don't poke someone
   into a gap they can't use).
4. **Momentum check.** Query the task list for tasks completed in the last ~2 hours. Anything
   there → exit silently -- they're moving; interrupting flow to offer flow is self-parody. Task
   app unreachable → exit (can't tell, so stay quiet).
5. **Poke.** One call to the configured push tool. The message is the runway plus one offer, with
   `/gsd` as the door: speakable, ~20 words, zero guilt, no second line. Something like
   `Two hours clear until your 3:00. Want an aim? Run /gsd when ready.` Vary the wording run to
   run; a constant poke is invisible by week two. Push tool fails → **exit silently** and let
   tomorrow's run try -- never substitute email, chat, or any other channel.
6. **Record.** `state_write` `gsd/poke.json` (`{lastPokeDate: <today>}`), and `state_append`
   `{"ts": ..., "kind": "poke", "minutes": <runway>}` to `gsd/history.ndjson`. A poke that never
   went out records nothing and doesn't burn the day's one poke.

No reply handling -- the poke is fire-and-forget. If the user wants the rescue they run /gsd and
the pull half takes over; if they don't, that's the end of it. The poke never nags about being
ignored, and never references a previously ignored poke.

## Degradation

| Missing | Behavior |
|---------|----------|
| State store | Steps 3–5 from brief + calendar; note it in one clause |
| Today's brief | Steps 2 + 4–5 from state + calendar |
| Calendar | Assume a modest runway (~45 min) and say so |
| Push tool (poke mode only) | Exit silently, record nothing, retry tomorrow |
| Everything | Improvise one small useful action from conversation context -- still deliver Step 6 in full |

The rescue never fails. Worst case, the entire output is "here's one small thing, here's the
first step, ten minutes counts."
