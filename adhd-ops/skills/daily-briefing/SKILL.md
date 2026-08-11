---
name: daily-briefing
description: >
  Execution logic for the scheduled morning brief. Not triggered directly by the
  user -- invoked by the morning-brief scheduled task. Gathers the delta since
  the last brief across calendar, chat, email, work tracker, and meeting notes;
  applies the 3-strike rule; picks exactly one Big Thing; renders through the
  deterministic builder; and delivers by email. Reads workspace-config first
  for every binding.
version: 0.1.0
---

# Morning Brief

Generate the morning brief and **deliver it as an email** to the user's delivery address. The
email is the artifact; everything else is machine memory.

**Prerequisites:** read `${CLAUDE_PLUGIN_ROOT}/skills/workspace-config/SKILL.md` first -- calendar
and task-list bindings, the state contract, data sources, and voice all live there. If its
required sections are unconfigured, stop and say so.

## Design principles (why this skill is shaped this way)

The brief competes for ADHD attention it will not be given for free (see the repo's PLAYBOOK.md
for the full argument):

1. **Push, not pull** -- the email is the deliverable. Archives are machine memory.
2. **Delta-first** -- full detail only for what CHANGED since the last brief. Unchanged content
   collapses to one count line. Identical sections reprinted daily train the reader to skim.
3. **No nag decay** -- the 3-strike rule forces a decision and then shuts up.
4. **One Big Thing** -- exactly one directive at the top. Ten priorities is zero priorities.
5. **Reward loop lives in the task app** -- the email points; the task app tracks. Completed items
   get celebrated briefly; that's the reward loop working.

The renderer (`scripts/brief.mjs`) hard-enforces the structural invariants -- exactly one Big
Thing, max 5 TL;DR bullets, max 3 focus items, exactly 3 options per forced decision -- so a
sloppy compose can't drop them.

## State (per the state contract in workspace-config)

- `briefing/state.json` -- source of truth for the **mention ledger** (strike counts),
  `lastRunAt` (the lookback anchor), and last-brief pointers. Read at start, **keep the version
  token** for the persist step.
- `briefing/history.ndjson` -- append-only, one record per run **including skipped ones**:
  `{ts, date, skipped: "ooo"|"holiday"|null, emailSent, gapFlags, runNote}`.
- `inbox/inbox.ndjson` -- the capture inbox (written by /park). Read early, harvest at the end
  (keep its version token).
- `shutdown/handoff.json` -- written by last night's shutdown; **read-only here**. Its proposed
  One Big Thing is a strong ranking input.
- `focus/current.json` -- current-thing and snooze entries. Partition by `expires` vs today:
  active entries feed ranking and snooze suppression; expired ones get an explicit resurface line
  and are garbage-collected in the persist step (keep the version token).

State store unreachable → run anyway from a 24-hour default window with an empty ledger, note it
in the run note, and skip all persistence. Delivery beats bookkeeping.

## Step 0: OOO / holiday gate (FIRST)

Check today (user's timezone, via `date(1)` -- never inferred) against the primary and holiday
calendars per workspace-config. OOO event or holiday → **exit after one state write**: append a
skipped-run record to `briefing/history.ndjson` and nothing else. That record is what lets the
gap check tell a holiday from a silently dead routine.

## Step 1: Lookback window

Everything from `lastRunAt` through now is in scope -- this absorbs weekends, holidays, and gaps
automatically. "Since the last brief" always means this dynamic window.

**Gap check:** list the calendar dates strictly between the last run and today. Any expected
workday (weekday, no holiday, no OOO) with neither a run record nor a skipped record in the
history tail gets one warning pill in the email: `⚠️ no brief ran <date> -- unexplained gap`.
Zero gaps (the normal case): say nothing.

## Step 2: Gather

All sources per workspace-config's bindings; every one optional. Tag every finding **changed** or
**unchanged** as you gather -- delta-first is a gather-time distinction.

1. **Capture inbox** -- `kind: "note"` entries are the highest-signal input in the run (the user
   telling tomorrow-self what matters); `kind: "tangent"` entries render as one FYI line each,
   never a task, never a nag.
2. **Chat** -- mentions, threads waiting on the user, and the self-notes channel if one is bound.
   When reading by timestamp, compute epoch values with `date(1)`, never by hand, and sanity-check
   with one unfiltered read -- silent timestamp bugs eat messages.
3. **Task app** -- open follow-ups (feed the ledger and Needs Action) and recently completed ones
   (dedup anchors + the wins line). Run `Watch:` checks per workspace-config's conventions.
4. **Work tracker** -- PRs/reviews waiting on the user, assigned issues, and the user's own open
   PRs (their outbound work gets the same no-nag-decay treatment as everyone else's requests).
5. **Calendar** -- today's events; anything needing prep is a focus candidate.
6. **Email** -- important unhandled mail in the window.
7. **Meeting notes** -- unchecked action items assigned to the user or unassigned.

## Step 3: The 3-strike rule

Read the mention ledger. For every open item that would appear in the email:

- **Strike 1–2:** present normally; increment the ledger. (Strike 2 renders a subtle "2nd
  mention" chip.)
- **Strike 3:** present in **Decide Today** -- an explicit demand with exactly three options: *do
  it today*, *give it a due date* (set one on the task), or *drop it* (complete with `[dropped]`).
  Mark the ledger `final-notice`.
- **Strike 4+ (`retired`):** the item NEVER appears in the email again. It lives in the task app;
  if it has no due date, set one on the next workday so the app's own reminders take over -- and
  when several items retire in the same run, **stagger them one per subsequent workday** rather
  than stacking the heaviest list on one day.

Ledger keys are normalized short slugs so wording drift doesn't reset counts. **Snoozes pause
strikes:** an item matching an active `kind: "snooze"` entry gets no increment, is excluded from
Needs Action / Decide Today, and renders as one muted `😴 snoozed until <date>` line. A snooze
that expired this run re-enters **at its stored strike count** -- deferral, not amnesty -- with an
explicit ⏰ resurface line. Dormant `Watch:` tasks accrue no strikes; they enter the ledger the
day they wake.

## Step 4: Rank

**One Big Thing** -- exactly one. Ranking order when inputs compete: an explicit self-note or
captured note > last night's shutdown handoff proposal > the active current thing > everything
else -- and a genuine fire (a person blocked, a hard deadline) overrides the lot. Continuity beats
cold re-derivation: yesterday-evening's proposal already picked tomorrow's fight.

**Today's Focus** -- 2–3 items max, ranked: people blocked on the user first, time-sensitive
second, quick wins third.

**Reply-shaped stalls get a draft.** When an item's next move is a reply (chat answer, review
response, email), the activation-energy problem isn't remembering -- it's composing. Draft the
reply in the archive (if one is configured) and suffix the email row with `draft ready`. The
email stays short; the draft waits where the user can grab it. Propose-only: nothing sends
without the user's say-so in a live session.

**Current-thing candidates (propose, don't write).** If `focus/current.json` has no active
`kind: "current"` entry and the run sees a focus declaration (a captured note declaring a push, an
action-item cluster around one theme), render at most **one** `❓ current thing?` candidate row.
Detection never writes state -- scraped content can't reprogram the focus layer (trust boundary,
no carve-out).

## Step 5: Compose and send

**You do not write HTML.** Assemble one brief-spec JSON per
`${CLAUDE_PLUGIN_ROOT}/skills/daily-briefing/references/brief-spec.md`, then:

```bash
SCRIPT="${CLAUDE_PLUGIN_ROOT:-adhd-ops}/skills/daily-briefing/scripts/brief.mjs"
[ -f "$SCRIPT" ] || SCRIPT="$(find . -path '*/daily-briefing/scripts/brief.mjs' | head -1)"
node "$SCRIPT" render < /tmp/brief-spec.json > /tmp/brief.html
```

Non-zero exit → stderr says exactly what's wrong; **fix the spec and re-run, never hand-author
HTML around the renderer.** Send the HTML via the mail connector to the delivery address.

**Subject:** `📋 Morning Brief -- <headline>` where the headline is the day's actual lede
(`📋 Morning Brief -- the vendor question + 3 reviews`), never boilerplate. A varying subject is
the first hook; a constant one is invisible by Thursday.

Voice per workspace-config: narrative, scannable, ruthless about length -- readable in ~2 phone
screens. If an archive destination is configured, post the full version (everything in the email
plus unchanged tables, dedup annotations, and the rendered ledger) there before sending, and link
it in the footer.

## Step 6: Task-app writes

- Create tasks for genuinely new action items (dedup against open tasks, completed tasks, and the
  previous brief; conventions in workspace-config). Give externally-gated tasks a `Watch:` line at
  birth so they start dormant instead of accruing strikes nobody can act on.
- Apply Tier 1 auto-completions per the two-tier rule; report each in the wins line with its
  evidence link.
- **Escalation sweep:** any ledger item at strike 2+ with no matching open task gets one; any
  review request appearing in a second consecutive brief gets one. High importance only when a
  person is actively blocked or the item is at strike 3+.

## Step 7: Persist (after the send)

Sequencing: compose → archive → **send** → persist. Per the state contract, all CAS with the
version tokens kept earlier, each conflict re-read/merge/retry-once:

1. `state_write` `briefing/state.json` -- updated ledger, `lastRunAt`, pointers.
2. `state_append` the run record to `briefing/history.ndjson`.
3. GC expired entries out of `focus/current.json` (drop only what's expired as of now).
4. Harvest exactly the consumed entries out of `inbox/inbox.ndjson` (match on `ts`; keep anything
   captured mid-run).

Send failed transiently → don't persist; the next run re-covers the window. Send failed
auth-shaped → persist with `emailSent: false` and a run note, so the next brief leads with the
reauth notice.

## Connector failures

- **Transient** (timeout, rate limit, 5xx): one quiet line where the gap matters, plus the run
  note. Next run self-heals.
- **Auth-shaped** (401, `invalid_grant`, token-expired, re-authenticate language): it will NOT
  self-heal. Surface loudly: a `danger` pill `🔑 <connector> needs reauth`, a lede sentence when
  the loss is structural, a run note naming the failing call. If the *mail* connector itself is
  the casualty, archive if possible, persist `emailSent: false`, and lead the next successful
  brief with the notice.
