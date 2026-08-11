---
name: followup-triage
description: >
  Use when the user asks to "review follow-ups", "triage my open items",
  "check on my follow-ups", "get caught up", or otherwise wants to work down
  the backlog in the configured follow-ups list. Turns a pile of stale
  follow-ups into a short ordered worklist and then works it down: reconciling
  what each task claims against live state, grouping what's left by the action
  it needs, cheapest first, and leaving whatever it doesn't close carrying
  accurate, evidence-bearing state. Also invoked by the weekly-triage scheduled
  task in report-only mode. Reads workspace-config first for every binding.
version: 0.1.0
---

# Follow-up Triage

Re-verify every open follow-up against reality, then resolve them: hard-evidence items
auto-complete (Tier 1), everything else gets a proposed verdict.

**Interactive mode is a work session, not a status report.** The measure of a good run is how
many items are *closed* by the end, not how many are accurately described. Two things drive that:
grouping items by the action they need and doing the cheap ones first (Phase 3.5), and refusing
to trust what the task bodies say (Phase 2).

**Prerequisites:** `${CLAUDE_PLUGIN_ROOT}/skills/workspace-config/SKILL.md` -- task conventions,
data-source bindings, the state contract, voice. Optionally `state_read` `focus/current.json`
(snooze awareness) -- absent or unreachable, classify without it and say so.

## Modes

| Mode | Trigger | Flow |
|------|---------|------|
| **Interactive** (default) | /review-followups or the user asking live | Phases 1–6 |
| **Report-only** | the weekly-triage scheduled task, before that day's brief | OOO gate, Phases 1–3, then Phase R. No lanes, no interaction, no email. |

Report-only mode runs the same OOO/holiday gate as the morning brief and exits on a day off.
Interactive mode skips the gate -- if the user is asking live, they want the answer.

## Phase 1: Gather

Query the follow-ups list for open items. Separate **assistant-created tasks** (body starts with
`Source:`) from **the user's manual tasks**. Triage **both** -- but manual tasks are **read-only**
throughout: classify and recommend, never write. (A task the user sat down and typed is stronger
signal than a scraped one -- excluding manual tasks from triage would have it exactly backwards.
The write ban is what protects them, not invisibility.)

No open items at all → "Inbox zero on follow-ups. Nice." and stop.

## Phase 2: A task body is a claim, not a fact (CRITICAL)

Every factual statement in a task body was true when some earlier run wrote it. Treat all of it --
the linked artifact's state, who's waiting, what's blocking, whose ball it is -- as **a claim to
re-verify**, never as ground truth. This is the single highest-yield rule in the skill; a run
that skips it produces confident, well-formatted advice about a world that no longer exists.

For every item, before classifying:

- **Re-read the live state of every linked artifact** (the PR/ticket's actual status, current
  reviewers, latest activity). A body that says "ready, no blockers" may describe something
  closed, conflicted, or rewritten since.
- **Check whether the work moved to someone else.** "Nobody else is holding it" ages badly.
- **Distrust the stated blocker.** If the item hasn't moved, the real blocker is often something
  else entirely. Where live state doesn't explain the stall, ask -- "what's actually blocking
  this?" beats another week of guessing.
- **Don't trust labels/statuses applied by automation** -- compare the artifact's own timestamps
  against the label's implied claim.

**Report every drift you find, explicitly.** Drift is a finding, not a correction to make
quietly -- the user is acting on the old model until told otherwise. Say what the body claimed,
what is actually true, and what that changes. This applies to your own earlier statements in the
same session too.

Batch searches; use parallel subagents for different sources; don't over-search a two-day-old
item.

## Phase 3: Classify

| Classification | Criteria | Action |
|----------------|----------|--------|
| **Tier 1 Done** | Hard evidence per the two-tier rule in workspace-config | Auto-complete immediately (assistant-created tasks ONLY), evidence line appended. Report -- never ask. |
| **Likely Done (Tier 2)** | Soft signals only ("done" in chat, a related-but-unlinked PR) | Propose: "looks done -- confirm?" Never auto-complete. |
| **Has Updates** | New activity, not resolved | Keep Open, with a summary of what moved |
| **Blocked on Others** | Someone else genuinely owes the next move | Recommend **Park** (Phase 6): off the list, body records whose ball it is and what wakes it. If it's been parked so long the other person clearly dropped it, the action is a nudge, not a drop. |
| **Stale** | No activity anywhere in 7+ days | Drop or re-commit |
| **Very Stale** | No activity anywhere in 14+ days | Strongly recommend Drop |
| **No Change** | Recent (<3 days), no new signals | Keep Open -- too early to call |

An item targeted by an active snooze in `focus/current.json` gets annotated
`😴 snoozed until <date>` and **no recommendation at all** -- the user already made that call.

## Phase 3.5: Assemble lanes (interactive mode)

Classification says what each item *is*. Lanes say what the user *does*. Regroup by **the action
required**, then order the lanes by cost. Typical lanes (derive from the actual items, don't
force the list):

- **Two-minute wins** -- anything already decided and merely unexecuted.
- **Unsticking** -- work that's done but rotted (an approved PR that grew conflicts, a decision
  made verbally and never written down).
- **Real work** -- the items needing actual attention.
- **Not yours** -- the Blocked-on-Others set, batched for one clearing pass.
- **Decisions** -- items whose only blocker is picking an option.
- **Rulings** -- the stale set: drop or re-date, no third option.

Ordering rules: **cheapest lane first** (momentum from easy closures carries into the hard ones);
**long-lead asks early** regardless of size (an item gated on someone else's response time only
finishes early if it starts early); **group by tool, not topic** (lanes sharing a context cost
less back-to-back).

Per item, state two things that are routinely assumed and routinely wrong: **what "done" looks
like** (the observable that ends it), and where superficially-similar items need different
procedures.

## Phase R: The triage report (report-only mode)

Replaces Phases 3.5–6 on the scheduled run.

1. Apply Tier 1 auto-completions (assistant-created tasks only), evidence lines appended.
2. Write a **decision sheet** to the archive (if configured): auto-completions with evidence,
   then every remaining open item **numbered** with a proposed verdict -- done / drop / still
   live -- plus evidence links and one line of editorial each. Number them so the user can reply
   with one-line verdicts later ("complete 1 and 3, drop 5").
3. **No email.** The handoff is: this run writes the sheet → the next morning brief folds it into
   its stale-check section. Two halves, one decision loop. (No archive configured → skip the
   sheet; the brief falls back to its own stale-item logic.)
4. Log a one-line run summary and exit. Connector failures: triage what the remaining sources
   support; auth-shaped failures get a `🔑 needs reauth` line at the top of the sheet.

## Phase 4: Present (interactive mode)

Lead with the **drift** found in Phase 2 and any lane whose framing changed because of it --
that's the part the user can't get anywhere else; the inventory is secondary. Then the overview
table (item / source / age / classification / recommendation), then wait for a go-ahead.

## Phase 5: Walk the lanes

Cheapest first. Batch the obvious (5+ items clearly done or droppable → one accept-all question
via `AskUserQuestion`, with a review-each escape hatch). Individual items get: what was found
(1–3 evidence bullets with links), the recommendation, one sentence of rationale, your call.
For stale items the user keeps: offer a due date -- a kept stale item with no date will just go
stale again.

## Phase 6: Apply

1. **Done:** complete, evidence line appended.
2. **Dropped:** complete AND append ` [dropped]` to the title.
3. **Keep Open:** no write, unless a due date was agreed.
4. **Parked (Blocked on Others):** complete -- parking gets the item **off the list**, because a
   task the user can't act on is pure noise on a list they have to scan. Rewrite the body first:
   whose ball it is, what would wake it. Don't leave it open "so it isn't forgotten," and don't
   invent a manual parked-state ritual -- that just moves the work onto the user.
5. **Manual items:** zero writes. Report the recommendation and evidence in one block the user
   can act on themselves, and say plainly that you didn't touch them.

**Write the reasoning, not just the status** (per workspace-config's conventions): completions
carry what was actually found; deferrals carry what makes the item actionable; corrected framings
say `CORRECTED <date>:` explicitly; retitle when the title is now wrong -- the title is what the
user reads in the list.

**Close the gaps the session opened:** create tasks for work discovered mid-session that nothing
tracks; name the tracking artifact for items that have none; and flag anything the morning brief
structurally can't see (e.g., an unassigned issue the user filed that no query will surface) --
say it out loud rather than assuming it's tracked.

Then the final summary: N closed, N dropped, N remaining.
