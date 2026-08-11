# The Playbook

Executive-function support for ADHD brains, as a set of design patterns. This document is
self-contained: you can implement everything in it with an AI assistant, with scripts and cron, or
with paper and stubbornness. The `adhd-ops` plugin in this repo is one implementation.

## The premise

Executive dysfunction is an **architecture problem, not a willpower problem**.

The ADHD failure modes are predictable: starting is harder than doing; an unchanging reminder
becomes invisible by Thursday; ten priorities collapse into zero; open loops follow you into the
evening; shame about yesterday taxes today. None of these yield to trying harder, because none of
them are effort problems. They're design problems, and they have design solutions.

Every pattern below exists because a naive version failed first. The naive daily summary got
skimmed and then ignored. The naive reminder system trained banner blindness in under two weeks.
The naive "here's everything on your plate" list produced paralysis, not action. What survived is
what actually changed behavior.

Two resources are scarce and everything is designed around them:

- **Attention.** Anything delivered to an ADHD brain competes for attention it will not be given
  for free. Length, repetition, and blandness are all taxes on the reader. The system pays for
  every line it makes you read.
- **Activation energy.** The cost of *starting* dwarfs the cost of *doing*. Most of the machinery
  here is a crowbar aimed at that one gap.

## The laws

These are the transferable core. Every component in the daily loop is just these laws applied to a
time of day.

### 1. Push, not pull

A system that requires you to remember to check it has already failed -- remembering to check is
itself an executive function. Deliverables arrive where you already look (email, phone
notifications). Anything that lives behind a "just open the app" step is machine memory, not
communication.

### 2. One Big Thing

Exactly one directive at the top of the day. Not three, not a ranked five -- **ten priorities is
zero priorities**. Choosing is the executive function that's expensive; the system's job is to
spend that cost for you, before you wake up, and be wrong occasionally rather than neutral always.
Everything else in the brief is context; the One Big Thing is the answer to "what should I do?"

If you build only one thing from this playbook, build this.

### 3. Delta-first

Full detail only for what **changed** since the last report. Unchanged items collapse to a single
count line ("6 items, no movement") -- never re-listed, never re-tabled. Identical sections
reprinted daily train the reader to skim, and a skimming reader misses the one line that mattered.
The corollary: an empty section vanishes entirely. Never write "nothing new" five times.

### 4. No nag decay -- the 3-strike rule

Repetition without escalation is banner blindness. Anything repeated verbatim becomes wallpaper,
so the system is structurally forbidden from nagging:

- **Strikes 1–2:** the item appears normally (strike 2 gets a subtle "2nd mention" marker).
- **Strike 3:** the item stops being information and becomes a **forced decision** -- presented
  with exactly three options: *do it today*, *give it a real due date*, or *drop it*. No fourth
  option, no "I'll think about it."
- **Strike 4+:** the item **never appears again**. It's retired to the task app, where due-date
  reminders take over. The brief has said its piece.

This is the single most counterintuitive rule and the most important one after One Big Thing: the
system earns trust by *shutting up*. A reminder channel that never decays into noise is a reminder
channel you keep reading.

A refinement that matters: when several items retire at once, stagger their due dates across
successive workdays instead of stacking them on one day. Dumping every deferred decision on Monday
makes the heaviest list of the week land on the day with the least momentum.

### 5. The reward loop lives in the task app -- and celebration is load-bearing

Checkable boxes, due dates, reminders: the task app is the dopamine surface. The brief points;
the task app tracks. And **completed items get celebrated, briefly and sincerely, every time** --
in the morning brief and again at shutdown. This isn't decoration. ADHD motivation runs on
reward salience, and a system that only ever presents open loops is a system that punishes you
for looking at it. Wins reported the same day attach to the feeling of having done them; wins
reported never are wins the brain doesn't bank.

### 6. Shrink the first step

The activation energy of starting is the hurdle, so the first step must be **trivially small and
immediately startable**: "open the doc and write one sentence," not "draft the proposal." If the
first step takes more than a minute, it's not a first step -- decompose it again. This applies
everywhere a task is presented: the rescue command's output, the shutdown ritual's "next move"
lines, task bodies in the backlog.

### 7. Permission structure, not pressure

Explicit permission to bail early -- "ten minutes counts" -- plus exactly **one** smaller fallback
("if that's too big right now, do the ten-minute version"). One fallback, not a menu; a menu of
fallbacks is a new decision to fail at. Deadline honesty is fine. Shame is never fine, and it's
also *ineffective*: guilt raises the activation energy of the very thing it's trying to prompt.

### 8. Externalized loops are droppable loops

An open loop written down **with its next physical step** is a loop the brain can release. Written
down *without* a next step, it's just listed -- the brain keeps clutching it, because "where was I
and how do I get back in?" is still unanswered. The next-step requirement is structural, not
stylistic: a parked loop without one should be rejected by whatever renders your shutdown report.

### 9. Zero guilt, structurally

Not "the tone should be kind" -- structurally. The shutdown report **has no "you didn't get to"
section in its schema**; there is nowhere for a scold to live. An empty wins list renders a fixed
calm line ("No boxes checked today. It happens -- tomorrow's board is already set."), never
commentary. What didn't happen today is tomorrow's material, not tonight's verdict. Tone rules
get broken under deadline pressure; schema rules don't.

### 10. Silence is a designed outcome

For anything that proactively interrupts (a nudge, a ping), the bar is high and **silence is the
expected common case**. One nudge per day, maximum, ever. A nudge that fires daily is invisible by
week two -- the same banner-blindness law as strike decay, applied to notifications. When in doubt,
don't send. The channel is worth having exactly as long as every interruption turns out to have
been worth it.

Two corollaries: never nudge someone who's already moving (interrupting flow to offer flow is
self-parody), and never reference a previously ignored nudge (that's a guilt mechanic wearing a
notification costume).

### 11. One decision, not four

Bundle related offers into a single yes. "Want the full ritual?" -- and one yes starts the focus
music, arms a check-in, and sets the room lighting, whichever of those exist. Starting is one
decision, not a sequence of small negotiations, because each negotiation is a fresh chance for the
starting energy to leak away. Declined or ignored means dropped instantly, with zero follow-up
selling.

### 12. A task body is a claim, not a fact

Everything a tracking system says about an item was true when it was written. The linked ticket's
state, who's waiting, what's blocking -- all of it ages, and confident triage over stale facts
produces well-formatted advice about a world that no longer exists. Before acting on a backlog
item, re-verify its claims against live reality, and **report the drift you find explicitly** --
the gap between recorded and actual state is usually the most valuable thing a triage session
produces.

### 13. Lanes: group by action, cheapest first

Classification ("stale," "blocked," "has updates") describes items; a work session needs items
grouped by **the action they require**: two-minute wins, unsticking, real work, not-yours,
decisions, rulings. Then order lanes by cost, cheapest first -- a lane of already-decided,
merely-unexecuted items buys momentum that carries into the hard ones. Opening a session with its
highest-friction question spends the best energy on the worst target.

Two rules that keep lanes honest: state what "done" looks like for every item (the observable that
ends it), and put long-lead asks early regardless of size -- an item gated on someone else's
response time only finishes early if it *starts* early.

### 14. Parking is a decision, not a failure

Items blocked on other people come **off your list** -- a task you can't act on is pure noise on a
list you have to scan. Record whose ball it is and what would wake the item, then let an automated
watcher bring it back when (and only when) the underlying thing actually moves. Similarly,
snoozing is deferral with a date, not deletion -- and when a snooze expires, the item returns at
its old urgency *explicitly*, never silently.

### 15. The system tunes itself -- one change at a time

Every component writes a little telemetry (when it ran, what it proposed, what got accepted).
Once a month, something reads it all and proposes **exactly one** tuning change -- same law as One
Big Thing, applied to self-improvement. A retro that proposes five changes produces zero changes.
The retro is a tune-up report on *the system*, never a report card on the human. Small numbers
stay honest: "3 rescues this month" is a fact; a percentage over n=3 is a costume.

### 16. Delivery beats bookkeeping

When a run partially fails, the deliverable still goes out -- degraded, with a one-line note about
what's missing -- and the record-keeping is skipped rather than the reverse. A system that fails
silent-but-tidy trains you to distrust its silence. Failures that will self-heal stay quiet;
failures that won't (an expired login, a dead token) get surfaced loudly and exactly once.

## The daily loop

Six components, each a time-of-day application of the laws.

### 🌅 The morning brief

A single email that opens the day: **One Big Thing** at the top, a five-bullet-max TL;DR of actual
fires, two or three focus items ranked by who's-blocked-first, forced decisions for anything at
strike 3, and delta-only news from calendar, chat, email, and wherever your work lives. Wins from
yesterday get celebrated in a stat line. Unchanged items are one gray count. The whole thing reads
in about two phone screens.

Why it works: it front-loads the one expensive decision (what matters today) to a machine that
made it before you woke up, and it keeps the reading cost low enough that you'll still be reading
it in month six. The brief competes for attention every single day; every law above exists because
of some week it lost that competition.

Worth stealing even without automation: write tomorrow's One Big Thing on an index card tonight.
That's the brief, minimum viable edition.

### 📥 Capture (`/park`)

A zero-ceremony inbox for the thoughts that arrive at the wrong time. One line in ("park: check
whether the conference talk deadline moved"), one line back ("Parked. Tomorrow's brief has it."),
nothing else -- no questions, no categorization ceremony, no follow-up. Notes surface in the next
morning's brief as high-signal input; parked rabbit holes surface as one FYI line each.

Why it works: an ADHD brain generates its best reminders at the least actionable moments, and the
cost of *holding* a thought ("don't forget, don't forget") actively corrodes whatever you were
doing. Capture only works if it's cheaper than holding -- which means the capture interaction has
to cost approximately nothing. The moment capture asks a clarifying question, it's more expensive
than the anxiety it replaces, and it stops being used.

### 🛟 The rescue command (`/gsd`)

For the moment you surface mid-doomscroll and realize the afternoon went somewhere. On demand, the
system reads what it knows (today's brief, the declared current focus, the calendar) and hands
back **one next action, sized to the time actually remaining** -- a 40-minute gap gets a
40-minute-shaped task, not "ship the redesign." With it: a trivially small first step, explicit
permission to stop after ten minutes, and exactly one smaller fallback. Total read time: under a
minute. The acknowledgment of the lost afternoon is one matter-of-fact line, never a lecture.

Then one bundled offer -- "want the full ritual?" -- where a single yes starts focus audio, arms a
~45-minute check-in, and sets the room, whichever pieces exist (law 11).

The rescue never fails: with every data source down, the output is still "here's one small thing,
here's the first step, ten minutes counts."

**Poke mode** is the push half: once a day at most, if the calendar shows a usable free block and
there's no evidence of recent momentum, a single ~20-word nudge lands on your phone ("Two hours
clear until your 3:00. Want an aim?"). All the silence laws apply: never on weekends, never twice
a day, never when you're visibly moving, never a reference to an ignored nudge, and if anything
needed to check those conditions is unreachable -- stay silent. Silence is the designed common
outcome (law 10).

One hard-won sub-rule, as an example of thinking architecturally: **no audiobooks in the focus
audio**. Narrative audio competes for the same attention channel as focused work; you end up
rewinding, frustrated, having done neither. That's not a willpower observation, it's a channel
conflict -- so it's a rule in a file, not a thing to re-decide daily.

### 🌇 Shutdown

The end of the workday is the hardest transition in an ADHD day -- the moment open loops turn into
evening rumination. The shutdown email closes the loop in two phone screens:

1. **What moved** -- celebrated first, while the dopamine still attaches (law 5). Tomorrow it's
   bookkeeping; tonight it's a reward.
2. **Open loops, parked** -- each with where it stands and the first physical move back in
   (law 8). Written down so you can put them down.
3. **Tomorrow's One Big Thing, proposed** -- picked now, while today's context is still warm, so
   the morning starts as a continuation instead of a cold boot. The proposal stands by default;
   confirming it requires nothing. Zero-touch is the point.

No "you didn't get to" section exists (law 9). The sign-off gives permission to stop.

The morning brief treats last night's proposal as its strongest input, which closes the day-to-day
loop: evening-you picks tomorrow's fight, morning-you wakes up already aimed.

### 🧹 Weekly triage

Once a week (plus on demand), the backlog gets reconciled against reality. Every open item's
claims are re-verified against live state (law 12), classified (done / likely done / has updates /
blocked-on-others / stale / too-new-to-call), and then -- in an interactive session -- regrouped
into lanes ordered cheapest-first (law 13). Hard-evidence completions are applied automatically
and reported as wins; everything else is proposed, never assumed. Blocked items get parked off the
list with a watcher (law 14). Stale items face the same three-option forced choice as strike-3
items: recommit with a date, or drop.

The measure of a good triage session is how many items are *closed* by the end, not how many are
accurately described.

### 🔁 Monthly retro

Once a month the system reads its own telemetry -- brief run notes, rescue and nudge records,
shutdown handoffs -- and reports the patterns a daily view can't see: how long items live at each
strike, whether evening proposals actually become morning directives, whether nudged afternoons
look different from quiet ones, which recurring lines never change anyone's behavior (those are
deletion candidates -- less email is a feature). It ends with **exactly one** proposed tuning
change (law 15), with the evidence, framed as a question.

## Building your own

**With this repo's plugin:** install it, then work through the setup guide in
[`adhd-ops/README.md`](adhd-ops/README.md). You fill in a config skill (your calendars, task list,
state store, notification channel, voice) and paste three small scheduled-task prompts into
Claude Code web routines. The skills adapt to whatever connectors your environment actually has.

**Without any of it:** the laws don't need software.

- One Big Thing on an index card, chosen the night before, is laws 2 and half of the shutdown.
- A "parked loops" page where every entry must include the next physical move is law 8.
- A rule that any reminder you've written three times must now be scheduled or crossed out -- and
  may never be written a fourth time -- is law 4.
- Telling a friend "I'm doing ten minutes on X, that counts" is law 7.
- A capture notebook that lives in your pocket and never asks follow-up questions is `/park`.

**With a different assistant stack:** the skills in this repo are prompts plus one small
deterministic renderer script. The renderer pattern is worth copying regardless of stack: the
model gathers data and writes the words, but a **script owns the structure** -- it hard-enforces
the invariants (exactly one Big Thing, max five TL;DR bullets, exactly three options per forced
decision, next-step required on every parked loop, the calm empty-state lines) and refuses to
render anything that violates them. Structure that matters gets enforced by code, because prompts
drift and schemas don't. That's law 9 generalized: anything that must survive a sloppy compose
belongs in a validator, not in prose instructions.

## A note on tone

The private version of this system delivers everything in a distinct voice -- dry, funny, a little
sharp, warm underneath. That's not decoration either. A report that reads like a compliance
document loses the attention competition (law 3's evil twin: boring-but-correct is still unread).
Whatever voice you configure, the guardrails that matter are: the joke goes *around* the
directive, never instead of it; punch at tasks and bureaucracy, never at people; and when
something genuinely hard is happening in the human's life, drop the bit and be real.

Build the system that talks to you the way you'll actually keep listening to.
