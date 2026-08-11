# Brief spec & builder reference

The morning brief email -- and the shutdown email (shutdown skill; see "Shutdown spec" at the
bottom) -- are built by `scripts/brief.mjs` (zero-dep Node). **You do not write HTML.** You gather
the data, write the words, assemble one **brief-spec JSON**, and pipe it through the renderer. The
spec's optional `kind` field routes it: absent or `"recap"` → the morning brief; `"shutdown"` →
the shutdown email.

The script owns every structural guarantee (the One Big Thing card, 3RD STRIKE badges, stat pills,
delta "no movement" lines, the calm empty-state lines, HTML escaping, and stripping raw
`<account@domain.tld>` addresses off email sender names), so they can't be dropped. It **fails
loudly** (non-zero exit, reason on stderr) rather than render a broken email -- fix the spec and
re-run; never hand-author HTML around it.

The visual identity is a fixed dark card layout baked into the script. Restyle it by editing the
palette constants in `brief.mjs`, never from the spec.

## Rendering

```bash
node "$SCRIPT" render < /tmp/brief-spec.json > /tmp/brief.html
# stdout = inline-HTML email body; send via your mail connector
```

**The subject line is NOT part of the spec.** Author it in the send call and make it vary daily --
a constant subject is invisible by Thursday.

**Punctuation normalization:** the renderer replaces em-dashes (`—`) in string values with `--`
and en-dashes with `-`, so external data (an email subject, a meeting title) can't smuggle in a
style the voice rules exclude. Write `--` yourself anyway.

## Recap spec schema

| field | type | required | notes |
|-------|------|----------|-------|
| `title` | string | no | header title; defaults to `📋 Morning Brief` |
| `headerDate` | string | yes | e.g. `"Monday, June 29"` -- weekday resolved via `date(1)` |
| `sinceLabel` | string | yes | lookback label, e.g. `"since Fri 7:04 AM"` |
| `lede` | string | yes | 2–4 sentences: what kind of day it is, the headline |
| `pills` | array of pill | yes (≥1) | the stat-chips line; gap flags go here as `warning` pills |
| `oneBigThing` | object | yes | `{ text, link? }`. An object, not an array -- exactly one directive, structurally |
| `decideToday` | array | no | strike-3 items ONLY; `{ item, link?, strikeNote?, options[3] }`. Omit when empty (most days) |
| `tldr` | array of string | yes (0–5) | TODAY-only bullets. `[]` renders **"No fires today."** -- the calm fallback is structural |
| `todaysFocus` | array | yes (0–3) | `{ title, why?, link? }`, ranked by array order. `[]` renders **"See above -- light day."** |
| `needsAction` | array | no | `{ title, waitingOn?, strike?, snark?, link? }`. `strike` ∈ {1, 2}; 2 draws a subtle "2nd mention" chip |
| `focus` | object | no | the 🧭 CURRENT CONTEXT element (see below). When present, at least one array must be nonempty; otherwise **omit the key** |
| `delta` | object | yes | the delta sections (below); every subsection optional -- empty sections vanish |
| `staleCheck` | object | no | triage-day only -- `{ intro?, items: [{ n, verdict, item, link? }] }`, framed for one-line verdict replies |
| `footer` | object | yes | `{ backlogCount, todoListUrl, archiveUrl, signoff }` -- see below |

**Pill** `{ emoji, label, value?, tone }` with `tone` ∈ `neutral` · `brand` (facts) · `good`
(wins) · `warning` (deadlines, gaps) · `danger` (someone's blocked / needs reauth).

**decideToday** -- the 3-strike endgame. Each item carries exactly three options, in this order:
*do it today*, *give it a due date*, *drop it*. The renderer enforces the count. `strikeNote` is
the subtle "3rd mention -- this is the last one." aside.

**focus** -- the current-context layer, already partitioned by YOU into active vs expired via
`date(1)` (the renderer does zero date logic):

| array | row shape | renders as |
|---|---|---|
| `current` | `{ note, until, link? }` | `▸ <note> -- through <until>` |
| `snoozed` | `{ item, until }` | `😴 <item> -- snoozed until <until>` (muted) |
| `expired` | `{ item, note? }` | `⏰ <item> -- snooze expired, back on the list` |
| `candidates` | `{ item, note?, link? }` | `❓ <item> -- <note>` -- propose-only |

**delta** -- delta-first is structural: each subsection takes full `changed` rows plus one
`unchangedCount` number. Changed items render with links; unchanged content renders as ONE gray
`🟡 N <noun>, no movement.` line. Omit a subsection and it vanishes.

| subsection | row shape |
|---|---|
| `meetings` | `{ source?, item, link? }` |
| `calendar` | `{ when, title, snark?, calendar? }` |
| `chat` | `actionable: [{ channel?, item, link? }]`, `fyi: [...]` |
| `emails` | `{ sender, subject, snark?, link? }` |
| `tracker` | `{ repo?, title, detail?, link? }` |

**footer** `{ backlogCount, todoListUrl, archiveUrl, signoff }` -- `backlogCount` + `todoListUrl`
render the deep link into the task list; `archiveUrl`'s **key is required** but its value may be
`null` when no archive exists or the post failed (decide explicitly; don't just forget it).
`signoff` is one line that echoes One Big Thing.

Every free-text field is a voice slot; all of them are HTML-escaped by the renderer, so write
naturally.

## Shutdown spec (`kind: "shutdown"`)

| field | type | required | notes |
|-------|------|----------|-------|
| `kind` | `"shutdown"` | yes | routes the render |
| `title` | string | no | header title; defaults to `🌇 Shutdown` |
| `headerDate` | string | yes | |
| `lede` | string | yes | 1–3 sentences closing the day. Observational, never a verdict |
| `pills` | array of pill | no | omit or `[]` for none |
| `wins` | array | yes (0–5) | `{ text, link? }` → 🏆 green card. `[]` renders the fixed calm line -- the no-guilt fallback is structural |
| `loops` | array | yes (0–5) | `{ title, state, nextStep, link? }`. `nextStep` required per row -- the next *physical* move is the whole point. `[]` renders "Nothing left dangling. Clean shutdown." |
| `tomorrow` | object | yes | `{ obt: { text, link? }, firstMeeting?, note? }` -- exactly ONE proposed One Big Thing |
| `footer` | object | yes | `{ signoff, todoListUrl? }` |

The renderer dies on: >5 wins, >5 loops, a loop missing `title`/`state`/`nextStep`, a missing or
malformed `tomorrow.obt`, a missing `signoff`, or an unknown `kind`.
