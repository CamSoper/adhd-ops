> Worked example from a private personal-assistant system, with names changed (the assistant is "Ada", the user "Alex"). The code it tours isn't public, so the plan can't be rebuilt; read it for the shape of a good analysis and plan.

# Ada Desk Walkthrough
Reader: someone new to ada-desk (or Alex, coming back to it). Goal: know where each rule lives,
and change one without breaking the contract. Pinned: cbdb488 (origin/main).
Purpose: let Alex answer Ada with To Do gestures he already makes -- a tick, a delete, a drag --
and act on them safely with nobody watching.

## Spine scenario
1. Alex ticks a ✋ go task (the simplest full loop: stage → tick → execute).
2. Alex drags a task into 🤖 and it comes back as a draft (reuses classify, claims, write rules).

## Trace
Scenario 1:
1. conventions.md -- `## Kind 1 -- ✋ go: ...` -- a producer stages the title + machine block
2. desk SKILL.md -- `5. **Classify.** ...` -- the run pipes its reads through `desk.mjs classify`
3. desk.mjs -- `parseBlock` -- the block is parsed strictly
4. desk.mjs -- `classifyTask`, ✋ branch -- provenance, validity, title-names-target, expiry → execute/refuse
5. desk SKILL.md -- `**\`execute\`** → for each, in order:` -- target re-read: exists, owned list, live title
6. desk SKILL.md -- `5. **Record it**` / "Two runs, one tick" -- Done line; every action idempotent
Scenario 2:
7. desk.mjs -- 🤖 branch -- everything is a handoff; Ada-made → title-only
8. desk SKILL.md -- `1. **Claim it.**` -- stamp, read back, stale claims
9. desk SKILL.md -- `3. **Make the tier call.**` -- (a) (b) (d) (c), first fit wins
10. desk SKILL.md -- `2. **Write the job line**` -- job line, one dispatch, never re-fire
11. workshop SKILL.md -- `### Dispatched -- validate the pointer` -- payload is a pointer
12. desk.mjs -- `workorder` -- is it real, queued work?
13. workshop SKILL.md -- `## Step 5` -- subagent builds, main session writes
14. workshop SKILL.md -- Step 6 one-shot -- Review ask in ✋, then ✓? on the task
15. desk.mjs -- `checkActions` / `mayMark` -- the ✓? clock

## Concepts
- trust boundary (what counts as Alex asking) -- needed by 4, 7 -- step 1.2
- provenance (Ada-made) -- needed by 4, 7 -- step 1.3
- script decides / verdict final -- needed by 2 onward -- steps 1.4, 2.2
- machine block, go vs tap, key, expires -- needed by 3-6 -- step 2.1 (callouts)
- `actions` verdicts → run steps -- needed by 2 onward -- step 2.2 (table)
- closed action set + idempotency -- needed by 6 -- step 2.6 (table)
- claim (write, read back) -- needed by 8, 13 -- step 3.2
- tier -- needed by 10 -- step 3.3
- Workshop (second routine) -- introduced at 10, pictured at 4.1 -- just in time, not up front
- ✓? -- used from 9 ("mark ✓?"), explained fully at 15 -- glossary covers the forward use

## Path
Chapter 1 -- Why it works this way: purpose and the trust model the code enforces
  1.1 To Do is the control surface -- purpose first
  1.2 Two things count as Alex talking -- the boundary every later check enforces
  1.3 A first-line marker makes a task Ada's -- provenance, needed by both scenarios
  1.4 A script, not the model, decides what tasks mean -- the design split, and "fix both" (flow)
Chapter 2 -- A tick on a ✋ go task: scenario 1, in execution order
  2.1 A go task is a title plus a block -- the format (callouts)
  2.2 Every run starts with the script's verdicts -- classify (table: verdict → step)
  2.3 The parser refuses instead of guessing -- parseBlock
  2.4 A tick runs only after four checks pass -- classify ✋ branch (ladder, callout on the resolved check)
  2.5 The target is checked again before anything changes -- execute
  2.6 Every action is safe to run twice -- record + idempotency (table)
Chapter 3 -- A drag into 🤖 becomes a job: scenario 2, desk side
  3.1 A drag into 🤖 is a request -- 🤖 branch
  3.2 Claim it, then read the claim back -- claims
  3.3 Picking the tier is the model's judgment call -- (ladder)
  3.4 Real work goes to the Workshop, once -- job line + dispatch
Chapter 4 -- The Workshop turns a job into a draft: scenario 2, Workshop side
  4.1 The task is the only channel between routines -- concept step (sequence)
  4.2 The dispatch payload is only a pointer
  4.3 workorder trusts the task, not the pointer
  4.4 A subagent builds, the main session writes
  4.5 The result lands back on the task -- conventions.md's worked task body (callouts; states with stale/died exits)
Chapter 5 -- Keeping it honest: what holds up over weeks
  5.1 An unticked ✓? comes off after 14 days -- (timeline)
  5.2 The task text is the only memory -- write rules
  5.3 Fixtures pin the script's verdicts -- and the gaps they don't cover
  5.4 Every rule has one home -- concept step (table): where each rule lives, what checks it

## Visuals
- overview: flow -- Alex in To Do → Desk → Workshop, loop back as ✓? + Review ask
- 1.4: flow -- read To Do → `desk.mjs classify` → act on verdicts
- 2.1: callouts -- the machine block's fields
- 2.2: table -- verdict → the run step that handles it
- 2.4: ladder -- the four refusals, in code order
- 2.6: table -- why each action is safe twice
- 3.3: ladder -- the tiers, first fit wins
- 4.1: sequence -- Alex, To Do, Desk, Workshop, Subagent
- 4.5: states -- handed off → claimed → queued → picked up → draft ready, with stale/died exits
- 5.1: timeline -- day 0 mark, day 14 revert, day 44 earliest re-mark
- 5.4: table -- rule → home → what checks it

## Cut
- Threads (threads.mjs, the board, Step 5½) -- a second feature on the same heartbeat; not on either spine
- your-tap evidence (Step 3) -- named in the glossary; a third scenario would push past 25 steps
- interactive mode, connector trouble, degradation -- operational edges, not the rule engine
- standing jobs, the nightly sweep's internals -- variants of the one-shot path shown
- README's two-routines section -- covered by the overview and 4.1, introduced just in time
- the constants block -- the clocks it holds appear where they act (2.4, 3.2, 4.5, 5.1)

## Review (round 1)
Mechanical: 0 must, 6 should. Reviewer subagent: 28 findings (7 must: four T5 accuracy -- a caption
that overclaimed, a states edge that contradicted 3.4, "posts", "every verdict is pinned" -- and
three T3 "restates the code"). All accepted except where a fix cited line numbers in narration
(replaced with callouts) and 3.2's compare-and-swap reason (its support sits in a later step).
Added 5.4 for T8. After revision: 0 must, 3 should declined -- 32-33 line snippets that are each
one whole function; cutting them hides refusals the narration names.
