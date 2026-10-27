# The plan format

One JSON file. It holds the order, the words and the pictures, and names code only by the exact text
of its lines; `walkthrough.py build` turns it into the page. A complete example:
`references/examples/ada-desk.plan.json`.

## Top level

| Key | Required | What |
|-----|----------|------|
| `ref` | yes | the **full SHA** to pin, on the remote. Resolve a branch to its SHA before writing it here: a branch moves, so a plan that names one stops rebuilding the same page (the build warns). Refreshing a walkthrough is changing this on purpose |
| `scope` | | a path or list of paths; what the review's identifier check searches, and the overview's label |
| `title` | yes | the page's name: 2-4 words, a name not a sentence ("Ada Desk Walkthrough") |
| `audience` | | who it's for, shown on the overview ("someone new to ada-desk") |
| `goal` | | what they can do by the end, finishing the sentence "By the end ..." |
| `summary` | yes | 1-2 short paragraphs: what the code is for and what the chapters cover |
| `glossary` | | `[{"term": "...", "means": "..."}]`: the terms of art, in plain words |
| `overview_visual` | | the big picture (`visuals.md`) |
| `chapters` | yes | 1 or more chapters, below |
| `artifact_url` | | where it's published, so a rebuild updates the same page |
| `known_drift` | | one short paragraph, shown on the overview: where the code and its docs, comments or live config disagree. The only place for drift notes |
| `review` | | `"independent"` (default) or `"self-review"` when no fresh reviewer could be spawned; the page footer says so |

The plan never holds a local path: the repo is `--repo` on the command line.

## A chapter

| Key | What |
|-----|------|
| `title` | short, the chapter's subject |
| `blurb` | one sentence: what the reader gets from it |
| `steps` | 1-8 steps (aim for 4-8) |
| `wrap.takeaways` | 1-3 one-line things the reader now knows |
| `wrap.check` | `{"q": "...", "a": "..."}`: a question the chapter answers, and its answer. Shown at the end of the chapter's last step, answer folded |

## A step

**A code step** shows a snippet:

| Key | What |
|-----|------|
| `title` | the step's one idea, as a claim; 9 words or fewer |
| `text` | 1-2 paragraphs, 70 words or fewer in all. Inline `backticks` and `**bold**` |
| `file` | repo-relative path |
| `from` | the exact text of the snippet's first line |
| `to` | the exact text of its last line: the first line at or after `from` that matches |
| `focus` | the exact text of 1-5 lines to highlight (the point of the step) |
| `callouts` | optional, 1-4: `[{"line": "<exact text>", "note": "<15 words or fewer>"}]` |
| `visual` | optional, a compact visual (`visuals.md`) shown under the text |

**A concept step** has `title`, `text` and a `visual`, and no `file`: the picture fills the right
pane. Use one only when the picture is the content.

## Anchors

- **Exact whole-line text**, compared after trimming leading and trailing whitespace. Copy it from
  the file as it is at the pinned commit (`git show <ref>:<path>`), never from memory.
- **`from` must be unique in the file.** Lines like `}`, `return out;` or a blank line never are;
  start one line earlier or later.
- **`to`** is the first match at or after `from`, so it may repeat elsewhere in the file.
- **`focus` and callout lines must be unique within the snippet.**
- **Snippets are 45 lines at most** (the build refuses more) and should be 30 or fewer. If the point
  needs more, it's two steps.

## Words that point at code

- **Never cite a line number in the narration** ("line 619"). Line numbers move on the next refresh
  and the build can't check them. Point with what the build resolves: a focus line, or a callout
  pinned to the line by its text.
- **Backticks are for names that exist in the code.** The review checks every backticked name
  against the code in scope. A hypothetical example ("a task titled "Ada: pay the plumber"")
  goes in quotes, not backticks, or it's flagged as an invention.

What the build adds per step, which you never write: `start`, `end`, `focus` and callout line
numbers, `lines` (the code itself), `cols` (the widest line, which sizes the code pane), and the
GitHub `permalink`.
