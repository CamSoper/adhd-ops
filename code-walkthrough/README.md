# code-walkthrough

**"Walk me through this code" as a page you can page through.** Story on the left, the code on the
right exactly as it is at a pinned commit, every line number linked to that line on GitHub, diagrams
whose parts light up the lines they stand for, and a map of where the code lives. Chapters run 3-8
minutes and end at a checkpoint that asks before it tells: predict what the code does, or tap the
line that does it, then see why. A track up top says where you are and how long is left.

It exists because the obvious alternatives fail in specific ways. The CodeTour extension is dormant
and lives in one editor; its tours point at your working copy, so they rot as the code moves.
LLM-written tours invent line numbers and run long. Here the code can't drift (it's pinned) and
can't be invented (a script copies it from git), and every walkthrough is reviewed for teaching and
ADHD-friendliness before it ships.

## Install and use

```text
/plugin marketplace add CamSoper/adhd-ops
/plugin install code-walkthrough@adhd-ops
```

`/walkthrough <what>` -- a path, a repo, a branch, a PR or a plain folder, plus anything about who
it's for. Or just ask: "walk me through the checkout service", "make an onboarding walkthrough of
the registry's build pipeline", "explain this PR as a walkthrough".

## How it works

`skills/code-walkthrough/SKILL.md` is the procedure, in eight steps:

1. **Scope, reader, goal, pin**: what's in scope, who's reading, what they'll be able to do after, and
   the commit to pin. Pushed code links to GitHub; unpushed commits, and a plain folder snapshotted
   into the scratch directory (never written to), tour as they are without links.
2. **Map**: `walkthrough.py map` lists every in-scope file with its outline, the reference graph
   between files (imports and mentions), entry points and hubs.
3. **Critical path**: one concrete scenario traced through the code in execution order, every
   concept placed just before its first use, chunked into chapters, with a visual plan and a cut list
   (`references/critical-path.md`).
4. **Plan**: a JSON file holding the order, the words and the visuals, naming code only by the exact
   text of its lines (`references/plan-format.md`, `references/visuals.md`).
5. **Build**: `walkthrough.py build` resolves every anchor, visual link and check answer against
   `git show <sha>:<path>`, checks the visuals, draws the code map from the scope, sizes the code
   pane to the snippet's widest line, and writes a self-contained page.
6. **Review**: `walkthrough.py review` runs the mechanical checks (lengths, title echoes, focus
   lines, chunking, peekable or giveaway checks, and an identifier check against the code), then a
   fresh reviewer subagent answers every check blind and judges order, accuracy and clarity against
   `references/review-rubric.md`. One revision round; zero `must` findings to publish.
7. **Publish** as a private claude.ai Artifact.
8. **Report** the link, the outline and what the review changed.

`walkthrough.py drift` refreshes one later: it says which steps' code moved, changed or broke since
the pin, so a refresh re-reads only those.

```text
code-walkthrough/
├── commands/walkthrough.md             # /walkthrough
└── skills/code-walkthrough/
    ├── SKILL.md                        # the procedure
    ├── assets/template.html            # the page: step-through, checks, checkpoints, code map, both themes
    ├── references/
    │   ├── critical-path.md            # the ordering method and analysis.md's shape
    │   ├── plan-format.md              # the plan JSON
    │   ├── visuals.md                  # when to draw what, and the six visual kinds
    │   ├── review-rubric.md            # T1-T11, A1-A9, the evidence, the reviewer brief, revision rules
    │   └── examples/                   # ada-desk: plan + analysis, review round included (names changed)
    └── scripts/
        ├── walkthrough.py              # map | build | review | drift -- stdlib only
        └── test_walkthrough.py         # python3 test_walkthrough.py
```

## The page, and why it's shaped this way

Each choice traces to the evidence in `references/review-rubric.md`, "Why these items", and to a
2026-10-24 focus group (an ADHD developer, an instructional designer, an information designer and a
simplifier) that clicked through the ada-desk walkthrough at desktop and phone widths.

- **Checks commit before they reveal.** Retrieval beats rereading, and a folded answer is easy to
  open before trying. Choice checks explain every option once picked; a step's choice check is a
  prediction, asked above the narration that answers it, with the step's highlights held back until
  you pick; find-the-line checks hide the step's
  highlights until you tap, and the build resolves the answer to exactly one line of git. A chapter
  can ask its end question up front as a guess (prequestions help the questioned material most).
  Nothing is scored, nothing blocks Next: a gate is where an ADHD reader closes the tab. Answers are
  stored with their question and the picked choice's or line's text, so a rebuild that changes a
  check forgets the old answer instead of misreading it.
- **Checkpoints, not walls.** One end-of-chapter question, the takeaways after it (so they don't
  give it away), what's next and "a good place to stop". From chapter 3, a question you missed or
  skipped two or more chapters back comes back as one optional line until you get it right. It all
  moved off the chapter's last step, which used to stack code, a table, the takeaways and the
  question into one tall column.
- **Always oriented.** The overview resumes at the screen you left, with how much you've opened and
  how long is left. A segmented track (every step and checkpoint) with minutes left;
  the overview's big picture as a strip with this chapter's node lit; a file breadcrumb with the
  function or section the snippet sits in, which opens the code map with the current file marked.
  The map is drawn from git, so it can't be invented.
- **Pictures tied to code.** Ladder rungs, states, timeline points and table rows can name the line
  they stand for, and light it on hover or tap (contiguity, signaling). Callouts are lettered so
  they never collide with a ladder's numbers.
- **Small screens read in order:** words, code, picture, check, Next. Code scrolls sideways with its
  line numbers pinned instead of wrapping; a sequence diagram becomes a numbered list, and any
  sequence of four or more messages can be stepped through one at a time.
- **Terms where you need them:** a glossary term's first use in a step is a tap for its meaning.

## Where it fits, and what would kill it

On demand only: nothing schedules a walkthrough and nothing nudges you toward one, so it adds no
surface you have to remember to check, no ask and no vocabulary. It's a dev tool, like a code
review. The checks live inside the page and nowhere else: answers stay
in that browser and nothing reports them.

**Kill it** if no walkthrough gets built in the two months after it ships. Nothing logs usage, and
answers stay in the reader's browser, so every kill line below is a question to ask yourself two
months in, and anything you can't say yes to goes:

- **Checks and checkpoints:** "did you answer the checkpoints in a walkthrough you read?" No → cut
  back to one end-of-chapter choice check per chapter (predictions, find-the-line, guesses and the
  spaced review go). Separately, if a reviewer subagent finds a wrong or ambiguous answer key (a T9
  `must`) in two of the first three walkthroughs built, say so in the build report: the generator
  can't be trusted with keys, and the checks go back to open questions.
- **Code map:** "did you use the map, or still open GitHub's file tree to get your bearings?" Tree →
  cut it. It sits below the chapter cards on the overview, so it never stands between you and Start.
- **Orientation extras** (the big-picture strip, the sequence stepper, line links and peeks, term
  popovers): one question, "did any of these earn their space?" Each one you can't name goes.

## Limits

- Line links need the pinned commit on a GitHub remote. Unpushed commits, other hosts and plain
  folders build with `--no-links`: plain line numbers, everything else the same.
- Committed code only. Uncommitted edits never show, and the skill says when some are in scope. A
  plain folder is snapshotted into a bare repository in the scratch directory, so nothing is written
  into it; its `.gitignore` applies, and dependency trees, build output and secrets files stay out.
- A snapshot's commit exists only in its snapshot repository. `drift` works on it within a session
  (snapshot again into the same repository) and later only if that repository was saved.
- The page embeds the code it shows. It publishes private, and private repos are a normal use. To
  share a page wider than its repo (a home system on a public portfolio), run SKILL.md's Step 6b
  exposure pass first.
- The map's reference graph is heuristic (JS/TS and Python imports, Go packages, and path or file
  name mentions in any text file). It's evidence for the analysis, not a call graph.

## Versioning

Bump `version` in `.claude-plugin/plugin.json` with every change; CI tags releases from it (root
README, "Versioning & releases").
