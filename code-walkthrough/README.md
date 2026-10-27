# code-walkthrough

**"Walk me through this code" as a page you can page through.** Story on the left, the code on the
right exactly as it is at a pinned commit, every line number linked to that line on GitHub, diagrams
where a picture beats prose, and a To Do-style checklist that ticks off steps as you go. Chapters run
3-8 minutes and end with a check-yourself question.

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

`/walkthrough <what>` -- a path, a repo, a branch or a PR, plus anything about who it's for. Or just
ask: "walk me through the auth module", "make an onboarding walkthrough of the registry's build
pipeline", "explain this PR as a walkthrough".

## How it works

`skills/code-walkthrough/SKILL.md` is the procedure, in eight steps:

1. **Scope, reader, goal, pin**: what's in scope, who's reading, what they'll be able to do after, and
   a commit that's already on the remote.
2. **Map**: `walkthrough.py map` lists every in-scope file with its outline, the reference graph
   between files (imports and mentions), entry points and hubs.
3. **Critical path**: one concrete scenario traced through the code in execution order, every
   concept placed just before its first use, chunked into chapters, with a visual plan and a cut list
   (`references/critical-path.md`).
4. **Plan**: a JSON file holding the order, the words and the visuals, naming code only by the exact
   text of its lines (`references/plan-format.md`, `references/visuals.md`).
5. **Build**: `walkthrough.py build` resolves every anchor against `git show <sha>:<path>`, checks
   the visuals, sizes the code pane to the snippet's widest line, and writes a self-contained page.
6. **Review**: `walkthrough.py review` runs the mechanical checks (lengths, focus lines, chunking,
   check questions, and an identifier check against the code), then a fresh reviewer subagent judges
   order, accuracy and clarity against `references/review-rubric.md`. One revision round; zero
   `must` findings to publish.
7. **Publish** as a private claude.ai Artifact.
8. **Report** the link, the outline and what the review changed.

```text
code-walkthrough/
├── commands/walkthrough.md             # /walkthrough
└── skills/code-walkthrough/
    ├── SKILL.md                        # the procedure
    ├── assets/template.html            # the page: step-through, visuals, checklist, both themes
    ├── references/
    │   ├── critical-path.md            # the ordering method and analysis.md's shape
    │   ├── plan-format.md              # the plan JSON
    │   ├── visuals.md                  # when to draw what, and the six visual kinds
    │   ├── review-rubric.md            # T1-T10, A1-A9, the reviewer brief, revision rules
    │   └── examples/                   # ada-desk: plan + analysis, review round included
    └── scripts/
        ├── walkthrough.py              # map | build | review -- stdlib only
        └── test_walkthrough.py         # python3 test_walkthrough.py
```

## Where it fits

On demand only: nothing schedules a walkthrough, so it adds no surface to remember to check. It's a dev tool, like a code review. It pairs well with ADHD brains for the same reason the rest of this repo does: short chapters, one idea per step, the point first, and a checklist that shows progress.

## Limits

- Permalinks need a GitHub remote; anything else builds with `--no-links` (plain line numbers).
- The page embeds the code it shows. It publishes private; share it no wider than the repo.
- The map's reference graph is heuristic (JS/TS and Python imports, Go packages, and path or file
  name mentions in any text file). It's evidence for the analysis, not a call graph.
