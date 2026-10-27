# Visual aids

A visual earns its place when it shows something prose is bad at: **order across actors, a
lifecycle, a branch, time, or a comparison.** It never decorates, and it never just restates the
snippet beside it. The template draws every kind from data, in both themes, at any width, so you
choose the kind and write the labels; you never write SVG or CSS.

## Rules

- **The code's own names.** Labels use the identifiers, states and terms the code uses, in
  backticks where they're code. The review's identifier check fails any backticked name that
  doesn't exist in scope.
- **Caption = what to notice**, stated as the takeaway, 25 words or fewer: "Nothing runs unless all
  three checks pass", not "Diagram of the checks". The page shows it above the visual as "Look for".
- **Placed where the concept is introduced**, at most one per step.
- **One big picture on the overview** (`overview_visual`): a `flow`, `sequence` or `states` of the
  spine scenario at the highest level.
- **Concept steps** (a step with a visual and no code) only when the picture *is* the content -- the
  whole lifecycle before its pieces, the full message sequence before each hop. At most one per
  chapter; most steps show code.
- **Callouts before diagrams** when the point is the anatomy of one snippet (the fields of a record,
  the parts of a format): 1-4 notes pinned to lines, lettered A-D, each 15 words or fewer.
- **Link the picture to the code.** On a code step, a `flow` node, `states` state, `timeline` point,
  `ladder` rung or `table` row can name the snippet line it stands for: `"line": "<exact text>"`.
  The item gets a line chip and the line gets a gutter dot; hovering or focusing the item lights
  the line, and tapping it (or Enter) pins the light and shows the line right under the item, so a
  phone never scrolls away from the picture. Link every item that has a single line; this is the cheapest way to make a
  diagram teach instead of decorate. A linked line can't also be a find-the-line answer on the same
  step.
- **Don't duplicate.** If a visual's items are linked to the same lines callouts would mark, drop
  the callouts and put their words in the items' `sub`.

## Kinds

| Kind | Use it for | Limits | Where |
|------|-----------|--------|-------|
| `flow` | a pipeline: stages a thing passes through | 2-6 nodes | anywhere |
| `sequence` | who talks to whom, in what order | 2-5 actors, 1-10 messages | overview or concept step |
| `states` | a lifecycle: states, what moves it on, and the ways out | 2-6 states, 4 exits | anywhere |
| `timeline` | clocks, expiries, schedules | 2-6 points | anywhere |
| `ladder` | ordered checks where the first match wins | 2-6 rungs | anywhere |
| `table` | a comparison or a closed set | 2-5 columns (3 on a code step), 1-8 rows | anywhere |

On a code step a visual sits under the narration in the narrow column, so keep it compact (a
`ladder`, a `timeline`, a short `flow` or `states`, a 2-3 column `table`). A `flow` or `states`
turns horizontal only when every node gets room, so 4 or more nodes stay a vertical list there and
go across only on a wide overview or concept step. `sequence` and wide tables
need a concept step or the overview; the build refuses them elsewhere.

You don't arrange anything for small screens: the template stacks a step as words, code, picture,
check, Next; turns a `sequence` into a numbered list where it can't fit; and gives a `sequence` of
4 or more messages a "step through it" control that reveals one message at a time.

The code map (`plan-format.md`, "The code map") isn't a visual kind: the build draws it from git,
so the file layout is never something you draw.

## Shapes

Every kind takes `kind` and `caption`. Labels and cells accept `backticks` for code.

```json
{"kind": "flow", "caption": "...",
 "nodes": [{"label": "Alex, in To Do", "sub": "ticks, deletes or drags"}, {"label": "Ada Desk"}],
 "loop": "optional: what carries the result back to the start"}

{"kind": "sequence", "caption": "...",
 "actors": ["Alex", "To Do", "Desk", "Workshop"],
 "messages": [{"from": "Alex", "to": "To Do", "label": "drags a task into 🤖"},
              {"from": "Desk", "to": "Desk", "label": "`classify` (a message to itself is a note)"}]}

{"kind": "states", "caption": "...",
 "states": [{"label": "queued", "sub": "optional"}, {"label": "picked up"}, {"label": "done"}],
 "edges": ["`dispatch`", "draft finished"],
 "exits": [{"from": "picked up", "label": "no outcome in 6 h", "to": "`workshop-died`"}]}

{"kind": "timeline", "caption": "...", "unit": "day",
 "points": [{"at": 0, "label": "✓? added"}, {"at": 14, "label": "mark comes off", "sub": "optional"}]}

{"kind": "ladder", "caption": "...",
 "rungs": [{"test": "no machine block marker", "then": "`refuse`", "line": "if (!t.deskMarker) {"},
           {"test": "needs Alex's OK", "then": "(b) stage a ✋"}],
 "otherwise": "optional: what happens when nothing matched"}

{"kind": "table", "caption": "...",
 "columns": ["Action", "Extra args"],
 "rows": [["`todo.date`", "`due`"], {"cells": ["`todo.complete`", "none"], "line": "<exact text>"}]}
```

`edges` in `states` has exactly one label per gap between consecutive states; an exit's `from` must
be one of the state labels. `timeline` points are numbers in ascending order, spaced in proportion
on wide screens. Any `nodes`, `states`, `points` or `rungs` item, and a `rows` entry written as
`{"cells": [...]}`, takes an optional `"line"` on a code step.
