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
  the parts of a format): 1-4 numbered notes pinned to lines, each 15 words or fewer.

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
`ladder`, a `timeline`, a short `flow` or `states`, a 2-3 column `table`). `sequence` and wide tables
need a concept step or the overview; the build refuses them elsewhere.

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
 "rungs": [{"test": "fits the desk tier", "then": "(a) do it now"}, {"test": "needs Alex's OK", "then": "(b) stage a ✋"}],
 "otherwise": "optional: what happens when nothing matched"}

{"kind": "table", "caption": "...",
 "columns": ["Action", "Extra args"],
 "rows": [["`todo.date`", "`due`"], ["`todo.complete`", "none"]]}
```

`edges` in `states` has exactly one label per gap between consecutive states; an exit's `from` must
be one of the state labels. `timeline` points are numbers in ascending order, spaced in proportion
on wide screens.
