---
name: shutdown
description: >
  Execution logic for the end-of-day shutdown email. Not triggered directly --
  invoked by the shutdown scheduled task (workday late afternoon). Closes the
  day's loop: celebrates what actually moved while the dopamine still attaches,
  parks the open loops with their next physical step so the brain can put them
  down, and proposes tomorrow's One Big Thing so the morning starts as a
  continuation instead of a cold boot. Cheap reads only -- this run never
  scrapes. Reads workspace-config first for every binding.
version: 0.1.0
---

# Shutdown

The evening half of the loop. The morning brief opens the day; this closes it -- and the end of
the workday is the hardest transition in an ADHD day, the moment open loops turn into evening
rumination. Two phone screens: **what moved, what's parked, what tomorrow is for.**

**Prerequisites:** `${CLAUDE_PLUGIN_ROOT}/skills/workspace-config/SKILL.md` (bindings, state
contract, voice). Render contract: the "Shutdown spec" section of
`${CLAUDE_PLUGIN_ROOT}/skills/daily-briefing/references/brief-spec.md`.

## Design principles

1. **Celebrate first, while it still pays.** Wins reported tomorrow morning are bookkeeping; wins
   reported at the end of today are a reward loop. The 🏆 card leads.
2. **Externalized loops are droppable loops.** An open loop written down -- with its **next
   physical step** -- is one the brain can release. A loop without a next step is not parked,
   it's just listed; the renderer refuses it.
3. **Tomorrow starts tonight.** One proposed One Big Thing, picked while today's context is still
   warm. The morning brief treats it as a strong input. The proposal **stands by default** --
   confirming it requires nothing. Zero-touch is the point.
4. **Zero guilt, structurally.** No "you didn't get to" section exists in the spec. An empty wins
   array renders a calm fixed line, not a scold. What didn't happen today is tomorrow's material,
   not tonight's verdict.
5. **Cheap and fast.** No scraping, every input optional except the email itself. If a read
   fails, degrade and send anyway -- delivery beats bookkeeping.

## Step 0: Gate

Run the same OOO/holiday check as the morning brief (calendars per workspace-config). Day off →
exit silently: no email, no state writes -- a shutdown email on a day off is a work email on a day
off. **Weekend → exit** too (belt-and-suspenders against trigger-schedule drift). Clock everything
with `date(1)` in the configured timezone; never infer.

## Step 1: Gather the day (cheap reads, all optional)

1. **Today's brief** (from the archive if configured, else from `briefing/state.json` pointers) --
   this morning's One Big Thing and Decide Today items: did they move?
2. **Task app** -- tasks completed today (the wins) and open assistant-created tasks modified
   today (loop candidates).
3. **State** -- `briefing/state.json` (ledger context for loop framing), `focus/current.json`
   (the active current thing weights tomorrow's proposal), and a **read-only** peek at
   `inbox/inbox.ndjson` (a note captured today may *be* tomorrow's One Big Thing -- the morning
   brief harvests the inbox; this run never does).
4. **Calendar** -- what's left of today (a 5 PM meeting changes the sign-off) and tomorrow
   morning (the first meeting feeds the `tomorrow` block).

## Step 2: Compose the shutdown spec

One JSON per the Shutdown spec contract. Voice per workspace-config -- dry, warm, done for the
day.

- **`lede`** -- 1–3 sentences: the shape of the day, observationally. Never a productivity
  verdict.
- **`pills`** -- small true numbers if they help; omit on a quiet day rather than manufacturing
  stats.
- **`wins`** (≤5) -- completed boxes, merges, anything that moved because of the user. Real
  celebration, brief. Empty is fine; the renderer's calm fallback handles it.
- **`loops`** (≤5) -- the open threads the user actually touched or owns *right now*, each with
  `state` (where it stands) and `nextStep` (the first physical move back in -- "open the thread,
  write one sentence", not "finish the reply"). More than 5 candidates → the rest belong in the
  task app, not the email.
- **`tomorrow`** -- exactly one proposed One Big Thing. Priority: an unfinished Decide Today
  "do it today" commitment > the active current thing's next move > the morning's One Big Thing
  if it didn't happen (say so plainly, no shame) > the biggest open loop. Add `firstMeeting` and
  a one-line `note` when they change the shape of the morning.
- **`footer.signoff`** -- one line that gives permission to stop. The day is closed.

## Step 3: Render and send

```bash
SCRIPT="${CLAUDE_PLUGIN_ROOT:-adhd-ops}/skills/daily-briefing/scripts/brief.mjs"
[ -f "$SCRIPT" ] || SCRIPT="$(find . -path '*/daily-briefing/scripts/brief.mjs' | head -1)"
node "$SCRIPT" render < /tmp/shutdown-spec.json > /tmp/shutdown.html
```

Non-zero exit → fix the spec and re-run; never hand-author HTML. Send via the mail connector to
the delivery address, subject `🌇 Shutdown -- <the day's actual note>` (varying daily, same law
as the brief's subject).

## Step 4: Persist the handoff

1. `state_write` `shutdown/handoff.json` (CAS per the state contract):

   ```json
   {
     "date": "<today>",
     "proposedObt": { "text": "<the proposal>", "link": "<optional>" },
     "loops": [ { "title": "...", "state": "...", "nextStep": "...", "link": "..." } ]
   }
   ```

   This file is what tomorrow's brief reads as its strongest One Big Thing input.
2. `state_append` one record to `shutdown/history.ndjson`:
   `{ts, date, emailSent, wins: <n>, loops: <n>, obt: "<text>", runNote}` -- the retro reads
   this.

**Sequencing:** email first, then state -- if the send fails transiently, don't persist (a stale
handoff from a phantom shutdown would mislead the morning brief); if it fails auth-shaped,
persist with `emailSent: false` and a run note so the next brief can lead with the reauth notice.

## Degradation

| Missing | Behavior |
|---------|----------|
| Today's brief | Compose from task app + state + calendar; note it in the runNote |
| Task app | Wins from state only; say so in one clause -- never fake a win count |
| State store | Send the email anyway; skip Step 4; the morning brief just gets no handoff |
| Calendar | Omit `firstMeeting`; assume no late meeting |
| Everything | A two-line shutdown email is still a shutdown email: lede + one proposed tomorrow. Send it |
