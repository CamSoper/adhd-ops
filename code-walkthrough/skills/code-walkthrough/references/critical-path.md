# Finding the critical path

The critical path is the order a reader needs the code explained in: the shortest route from "I've
never seen this" to the goal, where every step stands only on steps before it. It is usually **not**
the file order, the directory order, or the order the code was written in. This file is the method;
`map.json` is the evidence it runs on.

## Principles

1. **Purpose before mechanism.** The first step says what problem the code solves, in the code's
   own words if it has them (a README's opening, a header comment).
2. **One spine.** Follow one concrete scenario end to end, in execution order. A concrete event
   ("the user ticks a ✋ go task", "a request hits `/api/stacks`") beats an abstraction ("the
   validation layer"): every later step can point back to it.
3. **Just-in-time concepts.** Introduce a concept (a data shape, an invariant, a term) in the step
   right before the first step that needs it -- not in a glossary dump up front, not after it's
   been used.
4. **No forward references.** A step may use only what earlier steps introduced. If step 6 needs
   something step 9 explains, the order is wrong.
5. **One new idea per step.** Two ideas → two steps. A step that only restates code is cut.
6. **Decision points get their own steps.** The `if` that refuses, the clock that expires, the
   check that keeps two writers apart: that's where behavior, safety and bugs live, so that's where
   readers need to slow down.
7. **Edges last.** Secondary flows, error handling, configuration, and finally the tests -- framed
   as "how to change this safely", which is what the reader will do next.
8. **Cut hard.** Boilerplate, argument parsing, helpers whose name says everything, generated code,
   fixtures' contents. A walkthrough of 15 well-chosen steps teaches more than one of 40.

## Procedure

1. **Orient from the map.** `entries` say where execution and reading start; `hubs` say what the
   rest depends on (often the contract or core model); the edges between them sketch the main path.
   A hub with high fan-in is almost always on the critical path; a file nothing references and that
   isn't an entry rarely is.
2. **Read** the entries and hubs in full, then the files the main path runs through. Write the
   purpose in one sentence.
3. **Pick the spine scenario.** The most common or most important thing the code does, as one
   concrete event. For a change tour: the behavior the change alters, before → after. If one
   scenario can't reach the goal, pick a second that reuses the first's concepts -- never more
   than two.
4. **Trace it.** List every place the scenario touches, in execution order: file, the anchor line's
   text, and what happens there in one line. This list is the backbone of the walkthrough.
5. **Inventory concepts.** For each trace point, the concepts a reader must already hold to follow
   it. Each concept gets a home: the trace point that introduces it, or a short step just before
   its first use.
6. **Order.** Purpose → the concepts the first trace point needs → the trace, in execution order,
   with each remaining concept inserted just before its first use → the decision points and
   invariants the trace passed through, if they need more than one line each → how to change it
   safely (tests, fixtures, extension points). Then **check the order**: walk it and confirm no step
   leans on a later one.
7. **Chunk.** Chapters of 4-8 steps (3 is thin; 8 is the hard cap) at natural seams: a hand-off
   between components, a phase change in the trace, a change of actor. Each chapter gets a one-line
   promise (its blurb), 1-3 takeaways and a check-yourself question. Target 12-20 steps in all and
   3-8 minutes per chapter.
8. **Plan the visuals** (`visuals.md`): one big picture for the overview, then one wherever a
   concept is a sequence, a lifecycle, a branch, a timeline or a comparison.
9. **Write the cut list:** what's in scope but not on the path, and why. If a reader would expect to
   see it, say in the summary that the walkthrough skips it.

## Change tours (`--base`)

The spine is the change itself. Order: the problem (what was wrong or missing, before) → the core
change → what calls it and what it affects → the tests that pin the new behavior → the risks a
reviewer should check. The map's `change` field (lines added/removed per file) says where the weight
is; a file with a one-line change is usually a call site, not a chapter.

## analysis.md

Write `$W/analysis.md` in this shape -- it's what the reviewer checks the order against:

```markdown
# <title>
Reader: <who>. Goal: <by the end you can ...>. Pinned: <sha>.
Purpose: <one sentence>

## Spine scenario
<one concrete event>

## Trace
1. <file> -- `<anchor text>` -- <what happens>
2. ...

## Concepts
- <concept> -- needed by trace <n> -- introduced in step <c.s>

## Path
Chapter 1 -- <title>: <promise>
  1.1 <step title> -- <why here>
  ...

## Visuals
- overview: <kind> -- <what it shows>
- <c.s>: <kind> -- <what it shows>

## Cut
- <file or topic> -- <why it's not on the path>
```
