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

- **Checks commit before they reveal.** Retrieval beats rereading (Rowland 2014), and a folded
  answer is easy to open before trying; answering in your head works only if you really try (Smith,
  Roediger & Karpicke 2013). Choice checks explain every option once picked, because explaining why
  beats giving the answer when the idea has to transfer (Butler, Godbole & Marsh 2013); a step's
  choice check is a prediction, asked above the narration that answers it, with the step's
  highlights held back until you pick; find-the-line checks hide the step's highlights until you
  tap, and the build resolves the answer to exactly one line of git. A chapter can ask its end
  question up front as a guess (prequestions help the questioned material most; St. Hilaire, Chan &
  Ahn 2024). Nothing is scored, nothing blocks Next: a gate is where an ADHD reader closes the tab.
  Retrieval practice works about as well for learners with ADHD (Knouse et al. 2016). Answers are
  stored with their question and the picked choice's or line's text, so a rebuild that changes a
  check forgets the old answer instead of misreading it.
- **Checkpoints, not walls.** One end-of-chapter question (questions between segments roughly halved
  mind-wandering in a lecture; Szpunar, Khan & Schacter 2013), the takeaways after it (so they don't
  give it away), what's next and "a good place to stop". From chapter 3, a question you missed or
  skipped two or more chapters back comes back as one optional line until you get it right. It all
  moved off the chapter's last step, which used to stack code, a table, the takeaways and the
  question into one tall column.
- **Always oriented.** Developers following LLM-generated code tours got lost after about four or
  five steps (Balfroid et al. 2026). The overview resumes at the screen you left, with how much
  you've opened and how long is left. A segmented track (every step and checkpoint) with minutes
  left; the overview's big picture as a strip with this chapter's node lit; a file breadcrumb with
  the function or section the snippet sits in, which opens the code map with the current file
  marked. The map is drawn from git, so it can't be invented.
- **Pictures tied to code.** Ladder rungs, states, timeline points and table rows can name the line
  they stand for, and light it on hover or tap (contiguity, Ginns 2006; signaling, Schneider et al.
  2018). Callouts are lettered so they never collide with a ladder's numbers.
- **Small screens read in order:** words, code, picture, check, Next. Code scrolls sideways with its
  line numbers pinned instead of wrapping; a sequence diagram becomes a numbered list, and any
  sequence of four or more messages can be stepped through one at a time.
- **Terms where you need them:** a glossary term's first use in a step is a tap for its meaning.

### The evidence

The same sources, with effect sizes and caveats, are in `references/review-rubric.md`, "Why these
items". Almost none of it was tested on adult developers, and none on developers with ADHD, so the
design is consistent with the evidence, not proven by it.

- **Code tours**
  - Balfroid, M., Albert, J., Aliti, D., Devroey, X., & Vanderose, B. (2026). How developers
    experience debugging unfamiliar codebases with code tours generated and evaluated by local
    LLMs. [arXiv:2607.26987](https://arxiv.org/abs/2607.26987)
  - Kara, Z. B., et al. (2026). LACY: Simulating expert mentoring for software onboarding with
    code tours. [arXiv:2603.25391](https://arxiv.org/abs/2603.25391). Expert-curated tours beat
    AI-only ones on a quiz, 83% to 57%, but with five learners and no significance test: a
    direction, not an effect size.
- **Checks and checkpoints**
  - Rowland, C. A. (2014). The effect of testing versus restudy on retention: A meta-analytic
    review of the testing effect. *Psychological Bulletin, 140*(6), 1432-1463.
    [doi:10.1037/a0037559](https://doi.org/10.1037/a0037559)
  - Butler, A. C., Godbole, N., & Marsh, E. J. (2013). Explanation feedback is better than
    correct answer feedback for promoting transfer of learning. *Journal of Educational
    Psychology, 105*(2), 290-298. [doi:10.1037/a0031026](https://doi.org/10.1037/a0031026)
  - St. Hilaire, K. J., Chan, J. C. K., & Ahn, D. (2024). Guessing as a learning intervention: A
    meta-analytic review of the prequestion effect. *Psychonomic Bulletin & Review, 31*, 411-441.
    [doi:10.3758/s13423-023-02353-8](https://doi.org/10.3758/s13423-023-02353-8)
  - Szpunar, K. K., Khan, N. Y., & Schacter, D. L. (2013). Interpolated memory tests reduce mind
    wandering and improve learning of online lectures. *PNAS, 110*(16), 6313-6317.
    [doi:10.1073/pnas.1221764110](https://doi.org/10.1073/pnas.1221764110)
  - Smith, M. A., Roediger, H. L., & Karpicke, J. D. (2013). Covert retrieval practice benefits
    retention as much as overt retrieval practice. *Journal of Experimental Psychology:
    Learning, Memory, and Cognition*.
- **Pictures**
  - Ginns, P. (2006). Integrating information: A meta-analysis of the spatial contiguity and
    temporal contiguity effects. *Learning and Instruction, 16*(6), 511-525.
    [doi:10.1016/j.learninstruc.2006.10.001](https://doi.org/10.1016/j.learninstruc.2006.10.001)
  - Schneider, S., Beege, M., Nebel, S., & Rey, G. D. (2018). A meta-analysis of how signaling
    affects learning with media. *Educational Research Review, 23*, 1-24.
  - Rey, G. D. (2012). A review of research and a meta-analysis of the seductive detail effect.
    *Educational Research Review, 7*(3), 216-237. Why visuals have to earn their place.
    [doi:10.1016/j.edurev.2012.05.003](https://doi.org/10.1016/j.edurev.2012.05.003)
  - Noetel, M., et al. (2022). Multimedia design for learning: An overview of reviews with
    meta-meta-analysis. *Review of Educational Research, 92*(3), 413-454. The overview the three
    above come through. [doi:10.3102/00346543211052329](https://doi.org/10.3102/00346543211052329)
- **ADHD**
  - Knouse, L. E., Rawson, K. A., Vaughn, K. E., & Dunlosky, J. (2016). Does testing improve
    learning for college students with attention-deficit/hyperactivity disorder? *Clinical
    Psychological Science*. [doi:10.1177/2167702614565175](https://doi.org/10.1177/2167702614565175)

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
