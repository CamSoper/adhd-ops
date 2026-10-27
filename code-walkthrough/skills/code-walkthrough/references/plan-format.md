# The plan format

One JSON file. It holds the order, the words, the pictures and the questions, and names code only by
the exact text of its lines; `walkthrough.py build` turns it into the page. A complete example:
`references/examples/ada-desk.plan.json`.

## Top level

| Key | Required | What |
|-----|----------|------|
| `ref` | yes | the **full SHA** to pin; SKILL.md, Step 1, says which (pushed, the remote's version, unpushed commits, or a snapshot of a plain folder). Resolve a branch to its SHA before writing it here: a branch moves, so a plan that names one stops rebuilding the same page (the build warns). Refreshing a walkthrough is changing this on purpose |
| `scope` | | a path or list of paths; what the review's identifier check searches, what the code map draws, and the overview's label |
| `title` | yes | the page's name: 2-4 words, a name not a sentence ("Ada Desk Walkthrough") |
| `audience` | | who it's for, shown on the overview ("someone new to ada-desk") |
| `goal` | | what they can do by the end, finishing the sentence "By the end ..." |
| `summary` | yes | 1-2 short paragraphs: what the code is for and what the chapters cover |
| `glossary` | | `[{"term": "...", "means": "..."}]`: the terms of art, in plain words. The page also turns each term's first use in a step into a tap-for-the-meaning link |
| `overview_visual` | | the big picture (`visuals.md`) |
| `layout` | | notes for the code map, below |
| `chapters` | yes | 1 or more chapters, below |
| `artifact_url` | | where it's published, so a rebuild updates the same page |
| `known_drift` | | one short paragraph, shown on the overview: where the code and its docs, comments or live config disagree. The only place for drift notes |
| `review` | | `"independent"` (default) or `"self-review"` when no fresh reviewer could be spawned; the page footer says so |

The plan never holds a local path: the repo is `--repo` on the command line.

## The code map (`layout`)

The overview's "Where the code lives" card, and the map behind every step's file path, are drawn
by the build from the scope at the pinned commit: every file, its line count, the steps that show
it, and the roles `map` infers (`entry`, `hub`, `test`). Folders the walkthrough never enters fold
away. You write at most two things:

| Key | What |
|-----|------|
| `notes` | `{"<path>": "<12 words or fewer>"}`: what a file or folder is for. A folder's key ends in `/`. Note the files on the path and the big ones the tour cuts, so the reader sees what's left out and why. Backticks follow the same rule as narration |
| `hide` | `["<path>", "<folder>/"]`: noise to leave off entirely (vendored code, generated files). Never a file a step shows |

Every key must exist in scope at the pinned commit, or the build fails.

## A chapter

| Key | What |
|-----|------|
| `title` | short, the chapter's subject |
| `blurb` | one sentence: what the reader gets from it |
| `at` | optional: the label of the `overview_visual` node (a `flow` or `states`) this chapter happens in. Every step then shows the big picture as a strip with that node lit |
| `steps` | 1-8 steps (aim for 4-6) |
| `wrap.takeaways` | 1-3 one-line things the reader now knows. The checkpoint shows them *after* its questions, as the answer key to the chapter |
| `wrap.check` | the checkpoint's question: one check, or a list of 2 when the second tests the walkthrough's goal (below) |
| `wrap.pre` | optional `true`: ask the first `wrap.check` (a choice check) as a guess on the chapter's first step, before the reader has seen the answer |

After each chapter's last step the page adds a **checkpoint** screen: its questions, then the
takeaways, then what's next and "a good place to stop". From chapter 3, a checkpoint with one
question also offers, folded into one optional line, a choice question from two or more chapters
back that the reader missed or skipped, until a review gets it right.

## A step

**A code step** shows a snippet:

| Key | What |
|-----|------|
| `title` | the step's one idea, as a claim; 9 words or fewer |
| `text` | 1-2 paragraphs, 70 words or fewer in all. Inline `backticks` and `**bold**`. The first sentence adds something the title doesn't say |
| `file` | repo-relative path, inside `scope` (the build refuses one outside it: the code map, the identifier check and `drift` would all miss it) |
| `from` | the exact text of the snippet's first line |
| `to` | the exact text of its last line: the first line at or after `from` that matches |
| `focus` | the exact text of 1-5 lines to highlight (the point of the step) |
| `callouts` | optional, 1-4: `[{"line": "<exact text>", "note": "<15 words or fewer>"}]`. Lettered A-D on the page, so they never collide with a ladder's numbered rungs |
| `visual` | optional, a compact visual (`visuals.md`) shown under the text. Its items can link to lines of the snippet |
| `check` | optional, one check (below): a choice check, asked as a prediction above the narration, or a find-the-line check on this step's snippet |

**A concept step** has `title`, `text` and a `visual`, and no `file`: the picture fills the right
pane. Use one only when the picture is the content. It can carry a choice check, not a
find-the-line one.

## Checks

A check is a question the reader answers before seeing the answer. Every check commits first and
then explains; nothing is scored and nothing blocks Next. Three shapes:

**Choice** -- predict an outcome, pick a verdict:

```json
{"q": "Alex renamed the task before ticking. What happens?",
 "choices": [
   {"text": "The desk refuses; the target isn't touched", "right": true,
    "why": "The live title no longer equals `target_title`, so it isn't the task Alex approved."},
   {"text": "The move runs, because the task id still matches",
    "why": "The id finds the task, but the title check comes before any action."}],
 "see": "2.5"}
```

2-4 choices, exactly one `"right": true`. Every choice carries a `why` (25 words or fewer) and the
page shows all of them once the reader picks, so a wrong pick learns why it's wrong. Write the right
one first if you like: the build shuffles them, the same way on every rebuild. On a chapter's end
check, `see` (optional) names the step that answers it, `"c.s"`, in this chapter or an earlier one,
shown as a link back. On a step, a choice check is asked above the narration, as a prediction
the earlier steps make possible, with the step's highlights held back until the reader picks; the
narration is its answer, so it takes no `see`, and the step's title mustn't state it.

**Find the line** -- tap the line that decides a situation:

```json
{"q": "A task's body carries two `--- ada-desk ---` lines. Tap the line that refuses it.",
 "line": "<exact text of the answer line>",
 "why": "`at` collects every marker line, so a second one refuses the block before either is parsed."}
```

On a step, the answer is in that step's snippet. The step's focus highlights stay off, before the
tap so they don't give it away and after it so they don't read as more answers; the verdict shows
under the tapped line. A callout or visual link on the answer line is a build error for the same
reason. At a chapter's end, add `"step": "c.s"`: the checkpoint shows that
step's snippet, unhighlighted. The build proves the answer resolves to exactly one line of the
snippet; whether it's the *right* line is the reviewer's call (T9). Keep these on steps where you
can: a chapter-end one re-shows a whole snippet and makes the checkpoint long.

**Open** -- `{"q": "...", "a": "..."}`: think, then reveal. Only at a chapter's end, and the review
asks for a choice or find-the-line check in every chapter, because a folded answer is easy to peek
at.

How many: 1-3 per chapter, counting the end; at most one per step; and a chapter that asks its
end question up front (`pre`) gives its first step no check of its own. Put a mid-chapter check on a
decision point (the step where the code refuses, branches or expires), not on a definition.

Writing them, so each one makes the reader think instead of search:

- **Ask about a situation, not the answer's words.** "A body carries two markers: tap the line that
  refuses it", never "tap the line that says more than one machine block": the answer line's own
  error string would turn it into a text search.
- **`pre` only when this chapter is the first to teach the answer.** If an earlier chapter or its
  takeaways already gave it away, it's a review, not a prediction.
- **The end check tests this chapter**, and the last chapter's second check tests the walkthrough's
  goal ("you change this constant and nothing else: what breaks?"). Neither the chapter's title nor
  the step's title may state the answer: both are on screen while the question is.
- **No calendar arithmetic.** "Day 0 ... day 44", not "October 1 ... November 14": the question is
  the rule, not the month lengths.
- **Every `why` says why**, not what: why the right one is right, why each wrong one is wrong.
- **Only names the reader has seen.** Every `backticked` name in a check (question, choices, whys,
  answer) appears in the steps of the chapter that owns it, in the narration or the code shown. A
  review question resurfaced in a later checkpoint is fine: its own chapter taught it.

## Anchors

- **Exact whole-line text**, compared after trimming leading and trailing whitespace. Copy it from
  the file as it is at the pinned commit (`git show <ref>:<path>`), never from memory.
- **`from` must be unique in the file.** Lines like `}`, `return out;` or a blank line never are;
  start one line earlier or later.
- **`to`** is the first match at or after `from`, so it may repeat elsewhere in the file.
- **`focus`, callout, visual-link and check-answer lines must be unique within the snippet.**
  The build checks that; it can't check that the line is the one you meant.
- **Snippets are 45 lines at most** (the build refuses more) and should be 30 or fewer. If the point
  needs more, it's two steps.

## Words that point at code

- **Never cite a line number in the narration** ("line 619"). Line numbers move on the next refresh
  and the build can't check them. Point with what the build resolves: a focus line, a callout, or a
  visual item linked to the line by its text.
- **Backticks are for names that exist in the code**, everywhere: narration, visuals, checks,
  takeaways, code-map notes. The review checks every backticked name against the code in scope. A
  hypothetical example ("a task titled "Ada: pay the plumber"") goes in quotes, not backticks,
  or it's flagged as an invention.
- **Point back, never ahead.** No "(next step)", "later" or "Chapter 4 shows": reorder, or state the
  fact where it's first used. And no maintainer footnotes ("the description still says..."): that
  goes in `known_drift`.
- **Prompt and config files:** a step shows the 2-5 lines it's about. The review flags a shown line
  over 110 columns in a `.md`, `.txt`, YAML or JSON file.

What the build adds per step, which you never write: `start`, `end`, `focus`, callout, link and
check-answer line numbers, `lines` (the code itself), `cols` (the widest line, which sizes the code
pane), `symbol` (the function or section the snippet sits in, for the breadcrumb), `secs` (reading
time), and the GitHub `permalink` (none with `--no-links`). Per plan: the code map.
