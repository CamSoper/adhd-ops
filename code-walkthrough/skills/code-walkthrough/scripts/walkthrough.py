#!/usr/bin/env python3
"""walkthrough.py -- the mechanical half of the code-walkthrough skill.

Same split as the rest of this marketplace: the model reads the code, picks the
order and writes the words; this script owns everything that has to be exactly
right. A plan names every snippet by the exact text of its lines, never by line
number, and the script resolves those anchors against `git show <sha>:<path>`,
so every line number, snippet and permalink on the page comes from git.
Standard library only, JSON in and JSON out.

It reads committed code only, never a working tree. --repo can be a bare
snapshot of a plain folder (SKILL.md, Step 1, "Not a git repo"); a snapshot,
like unpushed commits, builds and reviews with --no-links.

Subcommands:

  map    --repo DIR --ref REF [--scope PATH ...] [--base REF]
      Evidence for the critical-path analysis: the in-scope files with their
      outlines (headings, top-level definitions), the reference graph between
      them (imports, and mentions of one file's path or name in another), fan-in
      and fan-out, entry-point candidates and hubs. --base makes it a change
      tour: scope becomes the files changed between merge-base(BASE, REF) and REF.

  build  PLAN --repo DIR --template FILE --out PAGE [--data-out FILE] [--no-links]
      Resolves every anchor, focus line, callout, visual line link and check
      answer (each must match exactly one line), validates the visuals, checks
      and the plan's limits, draws the code map from the scope at the pinned
      commit, refuses a commit no remote has unless --no-links (every
      permalink would 404), and writes the page. All problems are reported
      together; on any problem nothing is written.

  review PLAN --repo DIR [--no-links]
      The mechanical half of the review: per-step and per-chapter metrics, and
      flags keyed to references/review-rubric.md (A* = ADHD-friendliness, T* =
      teaching effectiveness). Includes the identifier check: every `backticked`
      token the narration, a visual, a check or a code-map note uses must exist
      somewhere in scope at the pinned commit, or it's flagged as a possible
      invention, and every one in a check must appear in the steps of the
      chapter that owns it. Also flags the author's word "spine" anywhere a
      reader sees it, pointers to later steps, and over-wide lines shown from
      prompt or config files.

  drift  PLAN --repo DIR [--to REF]
      What moved since the plan's pinned commit: for every code step, whether
      its snippet at REF is the same, moved, changed or no longer resolves.
      REF defaults to origin's default branch, or to HEAD when the pin is on no
      remote (unpushed commits, or a snapshot re-taken in the same repository).
      The refresh list, before anyone re-reads anything.

Exit codes: 0 = ok (review and drift: report written, flags or not), 1 =
invalid plan or input (problems on stderr), 2 = usage.

Tests: test_walkthrough.py, beside this file (`python3 test_walkthrough.py`).
"""

import argparse
import copy
import json
import os
import random
import re
import subprocess
import sys
import zlib
from collections import defaultdict
from pathlib import PurePosixPath

# ---------- limits (mirror references/plan-format.md and review-rubric.md) ----------

MAX_SPAN = 45          # lines per snippet, hard (build error)
SOFT_SPAN = 30         # lines per snippet, soft (review flag A4)
MAX_STEPS = 8          # steps per chapter, hard
STEPS_SOFT = 6         # steps per chapter, soft (A3)
MIN_STEPS = 3          # steps per chapter, soft
MAX_TOUR = 25          # steps per tour, soft
MAX_CALLOUTS = 4
MAX_FOCUS = 5
WORDS_SOFT = 70        # narration words per step (A2)
WORDS_HARD = 100
FIRST_SENTENCE = 22    # words (A1)
ECHO = 0.7             # (A1) share of the title's words a first sentence repeats...
ECHO_NEW = 4           # ...while adding this many new words or fewer: an echo, not a reason
LONG_SENTENCE = 28     # words (A8)
TITLE_WORDS = 9        # (T2)
CAPTION_WORDS = 25     # (T6)
CHAPTER_MINUTES = 10   # (A3)
MAX_CHOICES = 4
WRAP_CHECKS = 2        # checks at a chapter's end, hard
CHAPTER_CHECKS = 3     # checks per chapter, soft (T7)
CHOICE_WORDS = 20      # (T9)
WHY_WORDS = 25         # (T9)
NOTE_WORDS = 12        # code-map notes
MAP_LIST_LIMIT = 400   # files; above it, folders the tour never enters show a count only
WIDE_PROMPT_COLS = 110 # shown line width in a prompt or config file (A9)
PROMPT_EXTS = {".md", ".txt", ".yaml", ".yml", ".json"}
PROMPT_LANGS = {"markdown", "yaml", "plaintext", "text", "json"}
REVIEW_KINDS = ("independent", "self-review")
SPINE_RX = re.compile(r"\bspines?\b", re.I)
FORWARD_RX = re.compile(r"\(next step\)|\bnext step\b|\bwe'll see\b|\bin a later (?:step|chapter)\b"
                        r"|\bchapter \d+ (?:shows|explains|covers|will)\b|\bmore on (?:this|that) later\b", re.I)
CODE_COLS_MIN, CODE_COLS_MAX = 60, 150

LANGS = {".mjs": "javascript", ".cjs": "javascript", ".js": "javascript", ".jsx": "javascript",
         ".ts": "typescript", ".tsx": "typescript", ".json": "json", ".md": "markdown",
         ".py": "python", ".go": "go", ".sh": "bash", ".bash": "bash", ".yaml": "yaml",
         ".yml": "yaml", ".toml": "ini", ".html": "xml", ".css": "css", ".cs": "csharp",
         ".java": "java", ".rs": "rust", ".rb": "ruby", ".sql": "sql", ".tf": "plaintext"}

VISUALS = {
    # kind: (required keys, allowed on a code step)
    "flow": (["nodes"], True),
    "sequence": (["actors", "messages"], False),
    "states": (["states", "edges"], True),
    "timeline": (["unit", "points"], True),
    "ladder": (["rungs"], True),
    "table": (["columns", "rows"], True),
}
# The list of items in each kind that may carry a `line` link to the step's code.
LINKABLE = {"flow": "nodes", "states": "states", "timeline": "points", "ladder": "rungs", "table": "rows"}
STEP_ID = re.compile(r"^\d+\.\d+$")


class PlanError(Exception):
    pass


# ---------- git ----------

def git(repo, *args, binary=False):
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=not binary)
    if r.returncode != 0:
        err = r.stderr if not binary else r.stderr.decode("utf-8", "replace")
        raise PlanError(err.strip() or f"git {' '.join(args)} failed")
    return r.stdout


def pin(repo, ref):
    r = subprocess.run(["git", "-C", repo, "rev-parse", "--git-dir"], capture_output=True, text=True)
    if r.returncode != 0:
        raise PlanError(f"{repo} isn't a git repository ({r.stderr.strip()}); for a plain folder, snapshot it "
                        "and tour the snapshot with --no-links (SKILL.md, Step 1, \"Not a git repo\")")
    try:
        sha = git(repo, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}").strip()
    except PlanError:
        raise PlanError(f"{ref!r} isn't a commit in {repo}: fetch it first, or, if it was a snapshot's, "
                        "snapshot the folder again and pin the new commit (a snapshot's commits live only "
                        "in its repository)") from None
    committed = git(repo, "show", "-s", "--format=%cI", sha).strip()
    return sha, committed


def github_base(repo):
    try:
        url = git(repo, "remote", "get-url", "origin").strip()
    except PlanError:
        return None
    m = re.search(r"github\.com[:/]+([^/]+)/([^/]+?)(?:\.git)?/?$", url)
    return f"https://github.com/{m.group(1)}/{m.group(2)}" if m else None


def on_remote(repo, sha):
    return bool(git(repo, "branch", "-r", "--contains", sha).strip())


def repo_label(repo, links):
    """What the page calls the repo: owner/name when origin is on GitHub, links or
    not; else the directory's name, minus .git (a snapshot is named after its folder)."""
    base = links or github_base(repo)
    if base:
        return base.removeprefix("https://github.com/")
    return os.path.basename(os.path.abspath(repo)).removesuffix(".git") or "repo"


def file_lines(repo, sha, path, cache):
    if path not in cache:
        try:
            text = git(repo, "show", f"{sha}:{path}")
        except PlanError:
            cache[path] = None
            return None
        lines = text.split("\n")
        if lines and lines[-1] == "":
            lines.pop()
        cache[path] = lines
    return cache[path]


def tree(repo, sha, scopes):
    out = git(repo, "ls-tree", "-r", "-l", sha, "--", *(scopes or ["."]))
    files = []
    for row in out.splitlines():
        meta, path = row.split("\t", 1)
        _mode, kind, _obj, size = meta.split()
        if kind == "blob":
            files.append((path, int(size) if size != "-" else 0))
    return files


def read_texts(repo, sha, listing):
    """Text of every file in the listing, in one `git cat-file --batch`. Binary,
    non-UTF-8 and files over 512 KB come back in `skipped` instead."""
    want = [p for p, size in listing if size <= 512 * 1024 and "\n" not in p]
    texts, out, i = {}, b"", 0
    if want:
        r = subprocess.run(["git", "-C", repo, "cat-file", "--batch"], capture_output=True,
                           input="".join(f"{sha}:{p}\n" for p in want).encode("utf-8"))
        out = r.stdout
    for p in want:
        nl = out.find(b"\n", i)
        if nl < 0:
            break
        head = out[i:nl].split()
        i = nl + 1
        if len(head) < 3 or head[1] == b"missing":
            continue
        size = int(head[2])
        raw = out[i:i + size]
        i += size + 1
        if b"\0" in raw[:8192]:
            continue
        try:
            texts[p] = raw.decode("utf-8")
        except UnicodeDecodeError:
            pass
    return texts, [p for p, _ in listing if p not in texts]


def lang_of(path):
    return LANGS.get(PurePosixPath(path).suffix.lower(), "plaintext")


# ---------- map ----------

OUTLINE_RX = {
    "markdown": [re.compile(r"^(#{1,3})\s+(.+)$")],
    "javascript": [re.compile(r"^(?:export\s+)?(?:default\s+)?(?:async\s+)?function\*?\s+([\w$]+)"),
                   re.compile(r"^(?:export\s+)?class\s+([\w$]+)"),
                   re.compile(r"^(?:export\s+)?const\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:\(|function)"),
                   re.compile(r"^//\s*-{3,}\s*(.+?)\s*-{3,}\s*$")],
    "python": [re.compile(r"^(?:async\s+)?def\s+(\w+)"), re.compile(r"^class\s+(\w+)")],
    "go": [re.compile(r"^func\s+(?:\([^)]*\)\s*)?(\w+)"), re.compile(r"^type\s+(\w+)")],
    "csharp": [re.compile(r"^\s{0,8}(?:public|internal)\s+(?:static\s+|sealed\s+|abstract\s+|partial\s+)*(?:class|record|interface|enum)\s+(\w+)")],
}
OUTLINE_RX["typescript"] = OUTLINE_RX["javascript"]

JS_IMPORT = re.compile(r"""(?:import|export)\s[^'"`;]*?from\s*['"]([^'"]+)['"]|import\s*\(\s*['"]([^'"]+)['"]\s*\)|require\(\s*['"]([^'"]+)['"]\s*\)|^\s*import\s+['"]([^'"]+)['"]""", re.M)
PY_IMPORT = re.compile(r"^\s*from\s+(\.*[\w.]*)\s+import\b|^\s*import\s+([\w.]+)", re.M)
GO_IMPORT = re.compile(r'"([\w.\-/]+)"')

ENTRY_NAMES = re.compile(r"(^|/)(SKILL\.md|README(\.\w+)?|main\.\w+|index\.\w+|cli\.\w+|__main__\.py|Program\.cs)$", re.I)
TEST_PATH = re.compile(r"(^|/)(tests?|__tests__|spec|fixtures?|examples?|testdata)(/|$)|[._-](test|spec)s?\.\w+$|(^|/)test_\w+\.py$", re.I)


def outline(text, lang):
    rxs = OUTLINE_RX.get(lang, [])
    out, fence = [], False
    for i, line in enumerate(text.split("\n"), 1):
        if lang == "markdown" and line.lstrip().startswith("```"):
            fence = not fence
            continue
        if fence:
            continue
        for rx in rxs:
            m = rx.match(line)
            if m:
                out.append({"line": i, "text": line.strip()[:100]})
                break
        if len(out) >= 40:
            out.append({"line": None, "text": "... (outline truncated at 40)"})
            break
    return out


def symbol_at(lines, a, lang):
    """The name of the section or top-level definition the snippet starting at
    index `a` sits in, for the breadcrumb: the nearest markdown heading above it,
    or the nearest definition above it if no top-level line closes that
    definition first. None when there's no honest answer."""
    rxs = OUTLINE_RX.get(lang)
    if not rxs:
        return None

    def name(line):
        for rx in rxs:
            m = rx.match(line)
            if m:
                return (m.group(m.lastindex) if m.lastindex else line).strip()[:200]
        return None

    if lang == "markdown":
        if name(lines[a]):
            return None  # the snippet opens on its own heading, so the reader already sees it
        fence, last = False, None
        for line in lines[:a + 1]:
            if line.lstrip().startswith("```"):
                fence = not fence
            elif not fence and name(line):
                last = name(line)
        return last
    if name(lines[a]):
        return name(lines[a])
    for i in range(a - 1, -1, -1):
        line = lines[i]
        if name(line):
            return name(line)
        if lang == "python":
            if line and not line[0].isspace() and not line.startswith(("#", "@", ")", "]")):
                return None
        elif line.startswith("}"):
            return None
    return None


def resolve_js(spec, src, paths):
    if not spec.startswith("."):
        return None
    parts = []
    for p in f"{PurePosixPath(src).parent}/{spec}".split("/"):
        if p == "..":
            if parts:
                parts.pop()
        elif p != ".":
            parts.append(p)
    target = "/".join(parts)
    for cand in [target] + [target + e for e in (".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx")] + \
                [f"{target}/index{e}" for e in (".js", ".mjs", ".ts", ".tsx")]:
        if cand in paths:
            return cand
    return None


def resolve_py(mod, src, paths):
    if mod.startswith("."):
        dots = len(mod) - len(mod.lstrip("."))
        base = PurePosixPath(src).parent
        for _ in range(dots - 1):
            base = base.parent
        rest = mod.lstrip(".").replace(".", "/")
        stem = str(base / rest) if rest else str(base)
        for c in (f"{stem}.py", f"{stem}/__init__.py"):
            if c in paths:
                return c
        return None
    # An absolute module: try it from the repo root, then as a unique suffix
    # (a src/ layout, or a package nested under the scope).
    rest = mod.replace(".", "/")
    for c in (f"{rest}.py", f"{rest}/__init__.py"):
        if c in paths:
            return c
        hits = [p for p in paths if p.endswith("/" + c)]
        if len(hits) == 1:
            return hits[0]
    return None


def survey(repo, sha, scopes, base=None, mentions=True, listing=None):
    """Everything `map` reports, minus the pin. The build reuses it for the code
    map; `mentions=False` skips the quadratic path-mention scan on big scopes."""
    changed = None
    if base:
        mb = git(repo, "merge-base", base, sha).strip()
        stat = git(repo, "diff", "--numstat", mb, sha, "--", *scopes)
        changed = {}
        for row in stat.splitlines():
            add, rem, path = row.split("\t", 2)
            changed[path] = {"added": None if add == "-" else int(add), "removed": None if rem == "-" else int(rem)}
    listing = listing if listing is not None else tree(repo, sha, scopes)
    if changed is not None:
        listing = [(p, s) for p, s in listing if p in changed]
    truncated = len(listing) > 600
    listing = listing[:600]

    texts, skipped = read_texts(repo, sha, listing)
    paths = set(texts)

    gomod = None
    try:
        m = re.search(r"^module\s+(\S+)", git(repo, "show", f"{sha}:go.mod"), re.M)
        gomod = m.group(1) if m else None
    except PlanError:
        pass

    # Basenames distinctive enough to count a bare mention as a reference.
    by_base = defaultdict(list)
    for p in paths:
        by_base[PurePosixPath(p).name].append(p)
    unique_base = {b: ps[0] for b, ps in by_base.items() if len(ps) == 1 and len(b) >= 6 and "." in b}

    edges = set()
    for src, text in texts.items():
        lang = lang_of(src)
        if lang in ("javascript", "typescript"):
            for m in JS_IMPORT.finditer(text):
                spec = next(g for g in m.groups() if g)
                dst = resolve_js(spec, src, paths)
                if dst and dst != src:
                    edges.add((src, dst, "import"))
        elif lang == "python":
            for m in PY_IMPORT.finditer(text):
                dst = resolve_py(m.group(1) or m.group(2), src, paths)
                if dst and dst != src:
                    edges.add((src, dst, "import"))
        elif lang == "go" and gomod:
            for m in GO_IMPORT.finditer(text):
                imp = m.group(1)
                if imp.startswith(gomod + "/"):
                    d = imp[len(gomod) + 1:]
                    for p in paths:
                        if str(PurePosixPath(p).parent) == d and p.endswith(".go") and not p.endswith("_test.go"):
                            edges.add((src, p, "import"))
        if not mentions:
            continue
        for dst in paths:
            if dst == src or (src, dst, "import") in edges:
                continue
            base_name = PurePosixPath(dst).name
            if dst in text or (unique_base.get(base_name) == dst and base_name in text):
                edges.add((src, dst, "mention"))

    fan_in, fan_out = defaultdict(int), defaultdict(int)
    for s, d, _ in edges:
        fan_out[s] += 1
        fan_in[d] += 1

    files = []
    for path, size in listing:
        if path not in texts:
            continue
        text = texts[path]
        lang = lang_of(path)
        roles = []
        if TEST_PATH.search(path):
            roles.append("test-or-fixture")
        if ENTRY_NAMES.search(path) or text.startswith("#!") or "__name__ == \"__main__\"" in text \
                or re.search(r"^func main\(", text, re.M) or re.search(r"(^|/)commands/[^/]+\.md$", path) \
                or "scheduled-task-prompt" in path:
            roles.append("entry")
        if lang == "markdown":
            roles.append("doc")
        elif lang in ("json", "yaml", "ini"):
            roles.append("data")
        else:
            roles.append("code")
        f = {"path": path, "lines": text.count("\n") + (0 if text.endswith("\n") else 1), "lang": lang,
             "roles": roles, "fan_in": fan_in[path], "fan_out": fan_out[path], "outline": outline(text, lang)}
        if changed is not None:
            f["change"] = changed.get(path)
        files.append(f)

    non_test = [f for f in files if "test-or-fixture" not in f["roles"]]
    hubs = sorted(non_test, key=lambda f: (-f["fan_in"], f["path"]))[:6]
    return {
        "scope": scopes,
        "change_tour": changed is not None,
        "totals": {"files": len(files), "lines": sum(f["lines"] for f in files)},
        "entries": [f["path"] for f in files if "entry" in f["roles"]],
        "hubs": [{"path": f["path"], "fan_in": f["fan_in"]} for f in hubs if f["fan_in"]],
        "files": files,
        "edges": [{"from": s, "to": d, "via": v} for s, d, v in sorted(edges)],
        "skipped": skipped,
        "truncated": truncated,
    }


def cmd_map(a):
    sha, committed = pin(a.repo, a.ref)
    out = {"sha": sha, "committed": committed, "repo_url": github_base(a.repo),
           **survey(a.repo, sha, a.scope or ["."], a.base)}
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
    print()


# ---------- the code map (build) ----------

def code_map(repo, sha, scopes, name, visits, layout, errs):
    """The "where the code lives" tree: every in-scope file at the pinned commit,
    the steps that visit each one, and the roles `map` already infers. The model
    supplies only optional notes and paths to hide; nothing else is written by hand."""
    listing = tree(repo, sha, scopes)
    s = survey(repo, sha, scopes, mentions=len(listing) <= 200, listing=listing)
    info = {f["path"]: f for f in s["files"]}
    # A hub tag means something only if few files earn it: half the top fan-in, and at least 3.
    most = max((h["fan_in"] for h in s["hubs"]), default=0)
    hubs = {h["path"] for h in s["hubs"] if h["fan_in"] >= max(3, (most + 1) // 2)}
    paths = [p for p, _ in listing][:600]
    pathset = set(paths)

    layout = layout or {}
    notes, hide = layout.get("notes") or {}, layout.get("hide") or []
    if not isinstance(notes, dict) or not all(isinstance(v, str) and v.strip() for v in notes.values()):
        errs.append("layout.notes must map paths to one-line notes")
        notes = {}
    if not isinstance(hide, list):
        errs.append("layout.hide must be a list of paths")
        hide = []

    def exists(p):
        return p in pathset or (p.endswith("/") and any(x.startswith(p) for x in paths))

    for p in list(notes) + hide:
        if not exists(p):
            errs.append(f"layout: {p!r} isn't a file in scope at {sha[:7]}, or a folder in scope (end a folder with /)")
    hidden = {p for p in paths if any(p == h or (h.endswith("/") and p.startswith(h)) for h in hide)}
    for p in visits:
        if p in hidden:
            errs.append(f"layout: {p} is hidden but a step shows it")
    shown = [p for p in paths if p not in hidden]
    if not shown:
        return None

    parents = [PurePosixPath(p).parent.parts for p in shown]
    common = []
    for segs in zip(*parents):
        if len(set(segs)) != 1:
            break
        common.append(segs[0])
    root = "/".join(common)

    def new_dir(nm, path):
        return {"name": nm, "path": path, "dir": True, "children": []}

    top = new_dir(common[-1] if common else name, root)
    index = {root: top}
    for p in shown:
        parts = (p[len(root) + 1:] if root else p).split("/")
        cur, cur_path = top, root
        for seg in parts[:-1]:
            cur_path = f"{cur_path}/{seg}" if cur_path else seg
            if cur_path not in index:
                index[cur_path] = new_dir(seg, cur_path)
                cur["children"].append(index[cur_path])
            cur = index[cur_path]
        f = info.get(p, {})
        roles = [r for r, ok in (("hub", p in hubs), ("entry", "entry" in f.get("roles", [])),
                                 ("test", "test-or-fixture" in f.get("roles", []))) if ok]
        node = {"name": parts[-1], "path": p, "lines": f.get("lines"), "roles": roles}
        if visits.get(p):
            node["visits"] = visits[p]
        if notes.get(p):
            node["note"] = notes[p]
        cur["children"].append(node)

    big = len(shown) > MAP_LIST_LIMIT

    def finish(d, is_top=False):
        files = visited = 0
        for c in d["children"]:
            if c.get("dir"):
                finish(c)
                files += c["files"]
                visited += c["visited"]
            else:
                files += 1
                visited += bool(c.get("visits"))
        d["files"], d["visited"] = files, visited
        if notes.get(d["path"] + "/"):
            d["note"] = notes[d["path"] + "/"]
        d["children"].sort(key=lambda c: (not c.get("dir"), c["name"].lower()))
        # GitHub-style: a folder holding only one folder reads as one row ("skills/desk").
        while not is_top and len(d["children"]) == 1 and d["children"][0].get("dir"):
            only = d["children"][0]
            d.update(name=f"{d['name']}/{only['name']}", path=only["path"], children=only["children"])
            if only.get("note"):
                d["note"] = only["note"]
        if big and not visited and not is_top:
            d.pop("children")
            d["folded"] = True

    finish(top, True)
    return {"root": top["name"], "tree": top, "files": len(shown),
            "visited": top["visited"], "hidden": len(hidden), "truncated": s["truncated"]}


# ---------- plan resolution (build and review) ----------

def norm(s):
    return str(s).strip()


def words(s):
    return len(re.findall(r"\S+", s))


def sentences(paras):
    out = []
    for p in paras:
        flat = re.sub(r"`[^`]*`", "CODE", p)
        out += [s for s in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9`\"'(])", flat) if s.strip()]
    return out


def rows_of(v):
    """Table rows as cell lists, whether written as lists or {"cells", "line"}."""
    return [r.get("cells") if isinstance(r, dict) else r for r in v.get("rows", [])]


def check_visual(v, where, on_code_step, errs):
    if not isinstance(v, dict):
        errs.append(f"{where}: visual must be an object")
        return False
    kind = v.get("kind")
    if kind not in VISUALS:
        errs.append(f"{where}: visual kind {kind!r} isn't one of {', '.join(VISUALS)}")
        return False
    req, code_ok = VISUALS[kind]
    n_errs = len(errs)
    if on_code_step and not code_ok:
        errs.append(f"{where}: a {kind} visual needs the full width; put it on a concept step (no file)")
    if not norm(v.get("caption", "")):
        errs.append(f"{where}: visual needs a caption saying what to notice")
    for k in req:
        if k not in v:
            errs.append(f"{where}: {kind} visual needs {k!r}")
    if any(k not in v for k in req):
        return False

    def count(key, lo, hi):
        n = len(v[key]) if isinstance(v[key], list) else -1
        if not lo <= n <= hi:
            errs.append(f"{where}: {kind} {key} must be a list of {lo}-{hi} (got {n})")
            return False
        return True

    if kind == "flow":
        if count("nodes", 2, 6):
            for n in v["nodes"]:
                if not isinstance(n, dict) or not norm(n.get("label", "")):
                    errs.append(f"{where}: every flow node needs a label")
    elif kind == "sequence":
        if count("actors", 2, 5) and count("messages", 1, 10):
            actors = set(v["actors"])
            for m in v["messages"]:
                if not isinstance(m, dict) or m.get("from") not in actors or m.get("to") not in actors or not norm(m.get("label", "")):
                    errs.append(f"{where}: sequence message {m!r} needs from/to among the actors and a label")
    elif kind == "states":
        if count("states", 2, 6):
            if not isinstance(v["edges"], list) or len(v["edges"]) != len(v["states"]) - 1:
                errs.append(f"{where}: states needs exactly one edge label per step between states ({len(v['states']) - 1})")
            labels = {s.get("label") for s in v["states"] if isinstance(s, dict)}
            for x in v.get("exits", []):
                if not isinstance(x, dict) or x.get("from") not in labels or not norm(x.get("label", "")) or not norm(x.get("to", "")):
                    errs.append(f"{where}: states exit {x!r} needs from (a state label), label and to")
            if len(v.get("exits", [])) > 4:
                errs.append(f"{where}: states takes at most 4 exits")
    elif kind == "timeline":
        if count("points", 2, 6):
            ats = [p.get("at") for p in v["points"] if isinstance(p, dict)]
            if len(ats) != len(v["points"]) or not all(isinstance(x, (int, float)) for x in ats) or ats != sorted(ats):
                errs.append(f"{where}: timeline points need numeric 'at' values in ascending order")
    elif kind == "ladder":
        if count("rungs", 2, 6):
            for r in v["rungs"]:
                if not isinstance(r, dict) or not norm(r.get("test", "")) or not norm(r.get("then", "")):
                    errs.append(f"{where}: every ladder rung needs test and then")
    elif kind == "table":
        if count("columns", 2, 5 if not on_code_step else 3) and count("rows", 1, 8):
            for r in rows_of(v):
                if not isinstance(r, list) or len(r) != len(v["columns"]):
                    errs.append(f"{where}: every table row needs {len(v['columns'])} cells (a list, or {{\"cells\": [...], \"line\": ...}})")
    items = v.get(LINKABLE.get(kind, ""), [])
    if not on_code_step and any(isinstance(x, dict) and "line" in x for x in items if isinstance(items, list)):
        errs.append(f"{where}: a visual's line links need code beside them; use them on a code step")
    return len(errs) == n_errs


def link_lines(v, one_line):
    """Resolve each visual item's optional `line` to its line number in the snippet."""
    linked = []
    for item in v.get(LINKABLE.get(v["kind"], ""), []):
        if isinstance(item, dict) and "line" in item:
            n = one_line(item["line"], f"{v['kind']} line link")
            if n:
                item["ln"] = n
                linked.append(n)
    return linked


def check_shape(c, where, errs, on_step):
    """Validate a check's shape and return its kind, or None. Anchors resolve later."""
    if not isinstance(c, dict) or not norm(c.get("q", "")):
        errs.append(f"{where}: a check needs a question (q)")
        return None
    if on_step and "see" in c:
        errs.append(f"{where}: a step's own check is answered by that step; drop \"see\"")
        return None
    if "choices" in c:
        ch = c["choices"]
        if not isinstance(ch, list) or not 2 <= len(ch) <= MAX_CHOICES:
            errs.append(f"{where}: a choice check needs 2-{MAX_CHOICES} choices")
            return None
        if any(not isinstance(x, dict) or not norm(x.get("text", "")) or not norm(x.get("why", "")) for x in ch):
            errs.append(f"{where}: every choice needs text and why (the feedback shown once it's picked)")
            return None
        if sum(x.get("right") is True for x in ch) != 1:
            errs.append(f"{where}: exactly one choice must have \"right\": true")
            return None
        if len({norm(x["text"]).lower() for x in ch}) != len(ch):
            errs.append(f"{where}: two choices have the same text")
            return None
        return "choice"
    if "line" in c:
        if not norm(c.get("line", "")) or not norm(c.get("why", "")):
            errs.append(f"{where}: a find-the-line check needs line (the exact text of the answer) and why")
            return None
        if not on_step and not STEP_ID.match(str(c.get("step", ""))):
            errs.append(f"{where}: a find-the-line check at a chapter's end needs \"step\": the code step whose snippet it shows (\"2.3\")")
            return None
        return "line"
    if on_step:
        errs.append(f"{where}: a step's check is a choice or find-the-line check (choices, or line and why)")
        return None
    if not norm(c.get("a", "")):
        errs.append(f"{where}: a check needs choices, a line, or an answer (a)")
        return None
    return "open"


def resolve_check(c, kind, step_id=None):
    out = {"kind": kind, "q": c["q"]}
    if kind == "choice":
        # Shuffled once, at build, seeded by the question: the author can list the
        # right answer first, and every rebuild still shows the same order.
        choices = [{"text": x["text"], "why": x["why"], "right": x.get("right") is True} for x in c["choices"]]
        random.Random(zlib.crc32(c["q"].encode("utf-8"))).shuffle(choices)
        out["choices"] = choices
        if c.get("see") is not None:
            out["see"] = str(c["see"])
    elif kind == "line":
        out.update({"why": c["why"], "step": step_id or str(c["step"]), "line": c["line"]})
    else:
        out["a"] = c["a"]
    return out


def resolve_step(repo, sha, links, step, where, cache, errs, step_id=""):
    out = {"title": norm(step.get("title", "")), "text": step.get("text", [])}
    if not out["title"]:
        errs.append(f"{where}: missing title")
    if not isinstance(out["text"], list) or not out["text"] or not all(isinstance(p, str) and p.strip() for p in out["text"]):
        errs.append(f"{where}: text must be a list of non-empty paragraphs")
    chk = step.get("check")
    kind = check_shape(chk, f"{where} check", errs, True) if chk is not None else None
    if "file" not in step:
        if "visual" not in step:
            errs.append(f"{where}: a step needs code (file/from/to) or a visual (a concept step)")
        else:
            check_visual(step["visual"], where, False, errs)
            out["visual"] = step["visual"]
        if kind == "line":
            errs.append(f"{where}: a find-the-line check needs code on the step")
        elif kind:
            out["check"] = resolve_check(chk, kind, step_id)
        out["concept"] = True
        return out

    path = step["file"]
    lines = file_lines(repo, sha, path, cache)
    if lines is None:
        errs.append(f"{where}: {path} doesn't exist at {sha[:7]}")
        return None
    for k in ("from", "to"):
        if not norm(step.get(k, "")):
            errs.append(f"{where}: missing {k!r} anchor")
            return None
    starts = [i for i, l in enumerate(lines) if norm(l) == norm(step["from"])]
    if len(starts) != 1:
        errs.append(f"{where}: 'from' anchor matches {len(starts)} lines in {path} (needs exactly 1): {step['from']!r}")
        return None
    a = starts[0]
    ends = [i for i in range(a, len(lines)) if norm(lines[i]) == norm(step["to"])]
    if not ends:
        errs.append(f"{where}: 'to' anchor not found at or after the 'from' line in {path}: {step['to']!r}")
        return None
    b = ends[0]
    if b - a + 1 > MAX_SPAN:
        errs.append(f"{where}: snippet is {b - a + 1} lines (max {MAX_SPAN}); tighten the anchors or split the step")
        return None

    def one_line(text, label):
        hits = [i for i in range(a, b + 1) if norm(lines[i]) == norm(text)]
        if len(hits) != 1:
            errs.append(f"{where}: {label} matches {len(hits)} lines in the snippet (needs exactly 1): {text!r}")
            return None
        return hits[0] + 1

    focus = [n for n in (one_line(f, "focus line") for f in step.get("focus", [])) if n]
    callouts = []
    for c in step.get("callouts", []):
        if not isinstance(c, dict) or not norm(c.get("note", "")):
            errs.append(f"{where}: every callout needs a line and a note")
            continue
        n = one_line(c.get("line", ""), "callout line")
        if n:
            callouts.append({"line": n, "note": c["note"]})
    if len(callouts) > MAX_CALLOUTS:
        errs.append(f"{where}: {len(callouts)} callouts (max {MAX_CALLOUTS})")
    linked = []
    if "visual" in step:
        out["visual"] = copy.deepcopy(step["visual"])
        if check_visual(out["visual"], where, True, errs):
            linked = link_lines(out["visual"], one_line)
    if kind == "line":
        n = one_line(chk["line"], "check answer")
        if n and (n in linked or n in {c["line"] for c in callouts}):
            errs.append(f"{where}: the check's answer line also carries a callout or a visual link, which gives it away")
        if n:
            out["check"] = {**resolve_check(chk, kind, step_id), "ln": n}
    elif kind:
        out["check"] = resolve_check(chk, kind, step_id)

    snippet = lines[a:b + 1]
    widest = max((len(l.expandtabs(4)) for l in snippet), default=0)
    out.update({
        "concept": False,
        "file": path,
        "lang": lang_of(path),
        "start": a + 1,
        "end": b + 1,
        "lines": snippet,
        "symbol": symbol_at(lines, a, lang_of(path)),
        "focus": sorted(set(focus)),
        "callouts": sorted(callouts, key=lambda c: c["line"]),
        "cols": max(CODE_COLS_MIN, min(CODE_COLS_MAX, widest)),
        "permalink": f"{links}/blob/{sha}/{path}#L{a + 1}-L{b + 1}" if links else None,
        "fileUrl": f"{links}/blob/{sha}/{path}" if links else None,
    })
    return out


def step_seconds(s):
    secs = 10 + sum(words(p) for p in s["text"]) / 200 * 60
    if not s["concept"]:
        secs += 2 * len(s["lines"])
    if s.get("visual"):
        secs += 20
    if s.get("check"):
        secs += 25
    return secs


def in_scope(path, scope):
    return not scope or any(sc in (".", "") or path == sc.rstrip("/") or path.startswith(sc.rstrip("/") + "/") for sc in scope)


def default_branch(repo):
    for ref in ("origin/HEAD", "origin/main", "origin/master"):
        try:
            git(repo, "rev-parse", "--verify", "--quiet", ref)
            return git(repo, "rev-parse", "--abbrev-ref", ref).strip().removeprefix("origin/")
        except PlanError:
            pass
    return None


def resolve_plan(plan, repo, no_links, with_map=True):
    errs = []
    if not isinstance(plan, dict):
        raise PlanError("the plan must be a JSON object")
    for k in ("ref", "title", "summary", "chapters"):
        if k not in plan:
            errs.append(f"plan is missing {k!r}")
    if errs:
        raise PlanError("\n".join(errs))
    sha, committed = pin(repo, plan["ref"])
    links = None
    if not no_links:
        links = github_base(repo)
        if not links:
            errs.append("origin isn't a GitHub remote, so lines can't link anywhere; pass --no-links")
        elif not on_remote(repo, sha):
            errs.append(f"{sha[:7]} isn't on any remote branch, so every link would 404; pass --no-links to tour it "
                        "as it is, or pin the remote's version if the scope is the same there (SKILL.md, Step 1)")
    if plan.get("review", "independent") not in REVIEW_KINDS:
        errs.append(f"review must be one of {', '.join(REVIEW_KINDS)} (got {plan.get('review')!r})")
    if "known_drift" in plan and not (isinstance(plan["known_drift"], str) and norm(plan["known_drift"])):
        errs.append("known_drift must be one non-empty paragraph (a string)")
    ov = plan.get("overview_visual")
    ov_labels = set()
    if ov is not None and check_visual(ov, "overview", False, errs) and ov["kind"] in ("flow", "states"):
        ov_labels = {n.get("label") for n in ov["nodes" if ov["kind"] == "flow" else "states"]}

    scope = plan.get("scope", [])
    scope = [scope] if isinstance(scope, str) else scope
    cache, chapters, by_id = {}, [], {}
    for ci, ch in enumerate(plan["chapters"], 1):
        steps_in = ch.get("steps", [])
        if not 1 <= len(steps_in) <= MAX_STEPS:
            errs.append(f"chapter {ci} has {len(steps_in)} steps (1-{MAX_STEPS}); split or merge it")
        steps = []
        for si, st in enumerate(steps_in, 1):
            r = resolve_step(repo, sha, links, st, f"chapter {ci} step {si}", cache, errs, f"{ci}.{si}")
            if r and not r["concept"] and not in_scope(r["file"], scope):
                errs.append(f"chapter {ci} step {si}: {r['file']} is outside the plan's scope ({', '.join(scope)}); "
                            "widen scope, or the code map, the identifier check and drift all miss it")
            if r:
                r["secs"] = round(step_seconds(r))
                steps.append(r)
                by_id[f"{ci}.{si}"] = r
        wrap = ch.get("wrap") or {}
        raw = wrap.get("check")
        raw = [] if raw is None else raw if isinstance(raw, list) else [raw]
        if len(raw) > WRAP_CHECKS:
            errs.append(f"chapter {ci} ends with {len(raw)} checks (max {WRAP_CHECKS})")
        checks = []
        for k, c in enumerate(raw, 1):
            kind = check_shape(c, f"chapter {ci} check {k}", errs, False)
            if kind:
                checks.append(resolve_check(c, kind))
        pre = wrap.get("pre") is True
        if pre and (not checks or checks[0]["kind"] != "choice"):
            errs.append(f"chapter {ci}: \"pre\" asks the chapter's first check up front, so that check must be a choice check")
        if pre and steps_in and isinstance(steps_in[0], dict) and steps_in[0].get("check") is not None:
            errs.append(f"chapter {ci}: step 1 has its own check, and \"pre\" asks another before it; drop one")
        if "at" in ch and ch["at"] not in ov_labels:
            errs.append(f"chapter {ci}: \"at\" is {ch['at']!r}, which isn't a node label of the overview's flow or states visual")
        chapters.append({"title": norm(ch.get("title", "")), "blurb": ch.get("blurb", ""), "at": ch.get("at"), "steps": steps,
                         "wrap": {"takeaways": wrap.get("takeaways") or [], "checks": checks, "pre": pre},
                         "minutes": max(1, round((sum(s["secs"] for s in steps) + 30 * len(checks)) / 60))})
        if not norm(ch.get("title", "")):
            errs.append(f"chapter {ci} needs a title")

    # Second pass: what checks point at, now every step has resolved.
    for ci, ch in enumerate(chapters, 1):
        pointed = [(f"chapter {ci} check {k}", c) for k, c in enumerate(ch["wrap"]["checks"], 1)]
        pointed += [(f"chapter {ci} step {si} check", s["check"]) for si, s in enumerate(ch["steps"], 1) if s.get("check")]
        for where, c in pointed:
            see = c.get("see")
            if see and (see not in by_id or int(see.split(".")[0]) > ci):
                errs.append(f"{where}: \"see\" must name a step in this chapter or an earlier one (got {see!r})")
            if c["kind"] != "line":
                continue
            line = c.pop("line")
            if "ln" in c:
                continue
            target = by_id.get(c["step"])
            if not target or target["concept"]:
                errs.append(f"{where}: \"step\" must name a code step (got {c['step']!r})")
                continue
            hits = [target["start"] + k for k, l in enumerate(target["lines"]) if norm(l) == norm(line)]
            if len(hits) != 1:
                errs.append(f"{where}: the answer line matches {len(hits)} lines in step {c['step']}'s snippet (needs exactly 1): {line!r}")
            else:
                c["ln"] = hits[0]
    if errs:
        raise PlanError("\n".join(errs))

    repo_name = repo_label(repo, links)
    visits = defaultdict(list)
    for ci, ch in enumerate(chapters, 1):
        for si, s in enumerate(ch["steps"], 1):
            if not s["concept"] and f"{ci}.{si}" not in visits[s["file"]]:
                visits[s["file"]].append(f"{ci}.{si}")
    cmap = code_map(repo, sha, scope or ["."], repo_name.split("/")[-1], dict(visits), plan.get("layout"), errs) \
        if with_map else None
    if errs:
        raise PlanError("\n".join(errs))

    data = {
        "title": plan["title"],
        "repo": repo_name,
        "scope": scope,
        "audience": plan.get("audience", ""),
        "goal": plan.get("goal", ""),
        "summary": plan["summary"],
        "glossary": plan.get("glossary", []),
        "known_drift": plan.get("known_drift", ""),
        "review": plan.get("review", "independent"),
        "overview_visual": ov,
        "codemap": cmap,
        "sha": sha,
        "committed": committed,
        "links": bool(links),
        "commitUrl": f"{links}/commit/{sha}" if links else None,
        "treeUrl": (f"{links}/tree/{sha}/{scope[0]}" if len(scope) == 1 and scope[0] not in (".", "") else f"{links}/tree/{sha}") if links else None,
        "compareUrl": f"{links}/compare/{sha}...{branch}" if links and (branch := default_branch(repo)) else None,
        "minutes": sum(c["minutes"] for c in chapters),
        "chapters": chapters,
    }
    return data, cache


# ---------- build ----------

def cmd_build(a):
    plan = load_plan(a.plan)
    data, _ = resolve_plan(plan, a.repo, a.no_links)
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    blob = blob.replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    with open(a.template, encoding="utf-8") as f:
        template = f.read()
    if "/*__TOUR_DATA__*/" not in template:
        raise PlanError("the template has no /*__TOUR_DATA__*/ slot")
    page = template.replace("/*__TOUR_DATA__*/", blob).replace("__TOUR_TITLE__", esc_html(data["title"]))
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(page)
    if a.data_out:
        with open(a.data_out, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
    total = sum(len(c["steps"]) for c in data["chapters"])
    checks = sum(len(c["wrap"]["checks"]) + sum(1 for s in c["steps"] if s.get("check")) for c in data["chapters"])
    print(f"ok: {total} steps and {checks} checks in {len(data['chapters'])} chapters, about {data['minutes']} min, "
          f"pinned to {data['sha'][:7]} -> {a.out}")
    if plan["ref"] != data["sha"]:
        print(f"note: ref {plan['ref']!r} can move; set \"ref\": \"{data['sha']}\" in the plan so a rebuild shows the same code",
              file=sys.stderr)
    for ci, c in enumerate(data["chapters"], 1):
        for si, s in enumerate(c["steps"], 1):
            where = "concept" if s["concept"] else f"{s['file']}:{s['start']}-{s['end']} focus={s['focus']}"
            extra = f" visual={s['visual']['kind']}" if s.get("visual") else ""
            links = [x["ln"] for x in (s.get("visual") or {}).get(LINKABLE.get((s.get("visual") or {}).get("kind"), ""), [])
                     if isinstance(x, dict) and "ln" in x]
            extra += f" links={links}" if links else ""
            extra += f" callouts={[c['line'] for c in s['callouts']]}" if s.get("callouts") else ""
            if s.get("check"):
                extra += f" check={s['check']['kind']}" + (f"@{s['check']['ln']}" if "ln" in s["check"] else "")
            print(f"  {ci}.{si} {where}{extra}")
        kinds = [k["kind"] + (f"@{k['step']}:{k['ln']}" if k["kind"] == "line" else "") for k in c["wrap"]["checks"]]
        print(f"  {ci} end: checks={kinds}{' pre' if c['wrap']['pre'] else ''}")


def esc_html(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ---------- review ----------

STOPWORDS = set("""a an the and or but of to in on at by for with from is are was were be been it its this that these
those as so if then than not no only just into out up over under after before what which who when where why how all any
each every one two three four five can't cannot can does doesn't do don't never there their they them you your he his she
her we our""".split())


def content_words(s):
    return {w for w in re.findall(r"[a-z0-9_$][\w$'-]*", s.lower()) if len(w) > 2 and w not in STOPWORDS}


def said_words(s):
    """Content words plus symbols (🤖, ✋): what a reader would match by eye."""
    return content_words(s) | set(re.findall(r"[^\x00-\x7f\s\w]", s))


def visual_strings(v):
    if not v:
        return []
    out = [v.get("caption", "")]
    for n in v.get("nodes", []) + v.get("states", []):
        out += [n.get("label", ""), n.get("sub", "")]
    out += v.get("edges", []) + v.get("actors", []) + v.get("columns", [])
    out += [m.get("label", "") for m in v.get("messages", [])]
    out += [x for e in v.get("exits", []) for x in (e.get("label", ""), e.get("to", ""))]
    out += [x for p in v.get("points", []) for x in (p.get("label", ""), p.get("sub", ""))]
    out += [x for r in v.get("rungs", []) for x in (r.get("test", ""), r.get("then", ""))]
    out += [v.get("otherwise", ""), v.get("loop", "")]
    out += [c for r in rows_of(v) if isinstance(r, list) for c in r]
    return [s for s in out if isinstance(s, str)]


def check_strings(c):
    if not c:
        return []
    out = [c.get("q", ""), c.get("a", ""), c.get("why", "")]
    out += [x for ch in c.get("choices", []) for x in (ch["text"], ch["why"])]
    return [s for s in out if isinstance(s, str) and s]


def shown_strings(s):
    """What a step teaches in words: the narration, the title, the visual and the callouts."""
    return s["text"] + [s["title"]] + visual_strings(s.get("visual")) + [c["note"] for c in s.get("callouts", [])]


def step_strings(s):
    """Everything a step puts in front of the reader apart from its code: what it teaches, and its own check."""
    return shown_strings(s) + check_strings(s.get("check"))


def reader_text(data, plan):
    """Every reader-facing string on the page, with where it shows."""
    out = [("overview", x) for x in [data["title"], data["audience"], data["goal"], data["known_drift"]]
           + list(data["summary"]) + visual_strings(data.get("overview_visual"))
           + [g.get(k, "") for g in data.get("glossary", []) for k in ("term", "means")]]
    out += [("code map", x) for x in ((plan.get("layout") or {}).get("notes") or {}).values()]
    for ci, ch in enumerate(data["chapters"], 1):
        wrap = ch["wrap"]
        out += [(f"chapter {ci}", x) for x in [ch["title"], ch.get("blurb", "")]]
        out += [(f"chapter {ci} wrap", x) for x in list(wrap["takeaways"]) + [y for c in wrap["checks"] for y in check_strings(c)]]
        for si, s in enumerate(ch["steps"], 1):
            out += [(f"step {ci}.{si}", x) for x in step_strings(s)]
    return [(w, x) for w, x in out if isinstance(x, str) and x]


def is_prompt_file(s):
    return PurePosixPath(s["file"]).suffix.lower() in PROMPT_EXTS or s.get("lang") in PROMPT_LANGS


def missing_identifiers(strings, corpus):
    missing = []
    for s in strings:
        for span in re.findall(r"`([^`]+)`", s):
            if span.strip() in corpus:
                continue
            for tok in re.findall(r"[A-Za-z_$][\w.$-]{2,}", span):
                tok = tok.rstrip(".-")
                if len(tok) >= 3 and tok not in corpus and tok not in missing:
                    missing.append(tok)
    return missing


def check_flags(c, where, flag, cue="", answer_line=""):
    """T9's mechanical half: sizes and giveaways -- the longest answer, an answer the
    step's own title already states (a step's check is asked before its narration),
    and a find-the-line question that paraphrases the answer line's own text."""
    if c["kind"] == "choice":
        lens = [words(x["text"]) for x in c["choices"]]
        for x in c["choices"]:
            if words(x["text"]) > CHOICE_WORDS:
                flag("T9", "should", where, f"a {words(x['text'])}-word choice (target ≤ {CHOICE_WORDS}): {x['text'][:60]!r}")
            if words(x["why"]) > WHY_WORDS:
                flag("T9", "should", where, f"a {words(x['why'])}-word why (target ≤ {WHY_WORDS}): {x['why'][:60]!r}")
        right = next(words(x["text"]) for x in c["choices"] if x["right"])
        wrong = max(n for x, n in zip(c["choices"], lens) if not x["right"])
        if right >= 1.5 * wrong and right - wrong >= 4:
            flag("T9", "should", where, "the right choice is much the longest; readers learn to pick the long one")
        rw, cw = content_words(next(x["text"] for x in c["choices"] if x["right"])), content_words(cue)
        if cue and rw and (rw <= cw or len(rw & cw) >= 2):
            flag("T9", "should", where, "the step's title gives the right choice away, and the check is asked before the narration")
    elif c["kind"] == "line":
        if words(c["why"]) > WHY_WORDS:
            flag("T9", "should", where, f"a {words(c['why'])}-word why (target ≤ {WHY_WORDS})")
        said = said_words(" ".join(re.findall(r"[\"'`]([^\"'`]{6,})[\"'`]", answer_line)))
        shared = said & said_words(c["q"])
        if len(shared) >= 2 and len(shared) >= 0.4 * len(said):
            flag("T9", "should", where, "the question paraphrases the answer line's own text, so it's a search, not a read")


def answer_text(c, data):
    if c["kind"] != "line":
        return ""
    ci, si = (int(x) for x in c["step"].split("."))
    st = data["chapters"][ci - 1]["steps"][si - 1]
    return st["lines"][c["ln"] - st["start"]]


def cmd_review(a):
    plan = load_plan(a.plan)
    data, cache = resolve_plan(plan, a.repo, a.no_links, with_map=False)
    scopes = data["scope"] or ["."]
    texts, _ = read_texts(a.repo, data["sha"], tree(a.repo, data["sha"], scopes))
    corpus_parts = list(texts.values())
    corpus_parts += ["\n".join(ls) for ls in cache.values() if ls]
    corpus = "\n".join(corpus_parts)

    flags, per_step = [], []

    def flag(fid, sev, where, msg):
        flags.append({"id": fid, "severity": sev, "where": where, "message": msg})

    for k in ("audience", "goal"):
        if not norm(plan.get(k, "")):
            flag("A5", "should", "overview", f"no {k}: the overview should say who this is for and what they'll be able to do")
    visuals = (1 if data.get("overview_visual") else 0)
    if not data.get("overview_visual"):
        flag("T6", "should", "overview", "no overview visual: the big picture is the cheapest place for a diagram")
    total_steps = concept_steps = total_checks = 0
    for ci, ch in enumerate(data["chapters"], 1):
        cw = f"chapter {ci}"
        n = len(ch["steps"])
        total_steps += n
        if n < MIN_STEPS and len(data["chapters"]) > 1:
            flag("A3", "should", cw, f"only {n} steps; fold it into a neighbor or give it more to do")
        elif n > STEPS_SOFT:
            flag("A3", "should", cw, f"{n} steps (target ≤ {STEPS_SOFT}); readers lose the thread after about five")
        if ch["minutes"] > CHAPTER_MINUTES:
            flag("A3", "should", cw, f"about {ch['minutes']} min; split it (target ≤ {CHAPTER_MINUTES})")
        wrap = ch["wrap"]
        checks = list(wrap["checks"]) + [s["check"] for s in ch["steps"] if s.get("check")]
        total_checks += len(checks)
        if not wrap["checks"]:
            flag("T7", "must", cw, "no check at the chapter's end (wrap.check)")
        elif not any(c["kind"] in ("choice", "line") for c in checks):
            flag("T7", "should", cw, "no choice or find-the-line check: a folded answer is easy to peek at, so nothing is retrieved")
        if len(checks) > CHAPTER_CHECKS:
            flag("T7", "should", cw, f"{len(checks)} checks (target ≤ {CHAPTER_CHECKS})")
        tk = wrap["takeaways"]
        if not 1 <= len(tk) <= 3:
            flag("T7", "should", cw, f"{len(tk)} takeaways; give 1-3")
        for k, c in enumerate(wrap["checks"], 1):
            check_flags(c, f"{cw} check {k}", flag, answer_line=answer_text(c, data))
        missing = missing_identifiers(tk + [x for c in wrap["checks"] for x in check_strings(c)], corpus)
        if missing:
            flag("T5", "must", f"{cw} wrap", f"backticked names not found in scope at {data['sha'][:7]}: {', '.join(missing)}")
        taught = "\n".join(x for s in ch["steps"] for x in shown_strings(s) + list(s.get("lines", [])))
        owned = [(f"{cw} wrap", c) for c in wrap["checks"]] + \
                [(f"step {ci}.{si} check", s["check"]) for si, s in enumerate(ch["steps"], 1) if s.get("check")]
        for where, c in owned:
            shown = taught
            if c["kind"] == "line" and c.get("step"):      # a checkpoint re-shows that step's snippet
                tci, tsi = (int(x) for x in c["step"].split("."))
                shown += "\n" + "\n".join(data["chapters"][tci - 1]["steps"][tsi - 1].get("lines", []))
            invented = missing_identifiers(check_strings(c), corpus)
            untaught = [t for t in missing_identifiers(check_strings(c), shown) if t not in invented]
            if untaught:
                flag("T7", "must", where, f"the check names what chapter {ci}'s steps never show: {', '.join(untaught)}")
        for si, s in enumerate(ch["steps"], 1):
            w = f"step {ci}.{si}"
            wc = sum(words(p) for p in s["text"])
            sents = sentences(s["text"])
            first = words(sents[0]) if sents else 0
            longest = max((words(x) for x in sents), default=0)
            m = {"step": f"{ci}.{si}", "title": s["title"], "words": wc, "paragraphs": len(s["text"]),
                 "first_sentence_words": first, "longest_sentence_words": longest,
                 "concept": s["concept"], "visual": (s.get("visual") or {}).get("kind"),
                 "check": (s.get("check") or {}).get("kind")}
            if s.get("visual"):
                visuals += 1
            if s["concept"]:
                concept_steps += 1
            else:
                m.update({"snippet_lines": len(s["lines"]), "focus": len(s["focus"]), "callouts": len(s["callouts"])})
            per_step.append(m)
            if wc > WORDS_HARD:
                flag("A2", "must", w, f"{wc} words of narration (hard cap {WORDS_HARD}, target ≤ {WORDS_SOFT})")
            elif wc > WORDS_SOFT:
                flag("A2", "should", w, f"{wc} words of narration (target ≤ {WORDS_SOFT})")
            if len(s["text"]) > 2:
                flag("A2", "should", w, f"{len(s['text'])} paragraphs (target ≤ 2)")
            if first > FIRST_SENTENCE:
                flag("A1", "should", w, f"first sentence is {first} words; lead with the point in ≤ {FIRST_SENTENCE}")
            tw, fw = content_words(s["title"]), content_words(sents[0]) if sents else set()
            if len(tw) >= 3 and len(tw & fw) / len(tw) >= ECHO and len(fw - tw) <= ECHO_NEW:
                flag("A1", "should", w, "the first sentence repeats the title; make it add the why or the consequence")
            for x in sents:
                if words(x) > LONG_SENTENCE:
                    flag("A8", "should", w, f"{words(x)}-word sentence: {x[:90]!r}")
            if len(s["title"].split()) > TITLE_WORDS:
                flag("T2", "should", w, f"title is {len(s['title'].split())} words; make it a short claim")
            if any("\u2014" in p for p in s["text"]):
                flag("A8", "should", w, "em-dash in the narration; use a period or a comma")
            if not s["concept"]:
                if not s["focus"]:
                    flag("A4", "must", w, "no focus lines: the reader can't tell which lines matter")
                elif len(s["focus"]) > MAX_FOCUS:
                    flag("A4", "should", w, f"{len(s['focus'])} focus lines (target ≤ {MAX_FOCUS})")
                if len(s["lines"]) > SOFT_SPAN:
                    flag("A4", "should", w, f"{len(s['lines'])}-line snippet (target ≤ {SOFT_SPAN})")
                if s.get("visual") and s.get("check"):
                    flag("A7", "should", w, "code, a visual and a check on one step; move the check or the visual")
                elif s.get("visual") and wc > 60:
                    flag("A7", "should", w, "code, a visual and more than 60 words on one step; trim the words or move the visual")
                if is_prompt_file(s):
                    wide = sum(len(l.expandtabs(4)) > WIDE_PROMPT_COLS for l in s["lines"])
                    if wide:
                        flag("A9", "should", w, f"{wide} shown line(s) over {WIDE_PROMPT_COLS} columns in {s['file']}; "
                             "excerpt the 2-5 lines the step is about")
            elif wc > 80:
                flag("A7", "should", w, f"concept step with {wc} words; the picture should carry it")
            fwd = sorted({m.group(0).lower() for x in step_strings(s) for m in FORWARD_RX.finditer(x)})
            if fwd:
                flag("T10", "should", w, f"points ahead ({', '.join(repr(f) for f in fwd)}); reorder, or state the fact where it's first used")
            if s.get("visual"):
                cap = s["visual"].get("caption", "")
                if words(cap) > CAPTION_WORDS:
                    flag("T6", "should", w, f"visual caption is {words(cap)} words (target ≤ {CAPTION_WORDS})")
            if s.get("check"):
                check_flags(s["check"], f"{w} check", flag, cue=s["title"], answer_line=answer_text(s["check"], data))
            missing = missing_identifiers(step_strings(s), corpus)
            if missing:
                flag("T5", "must", w, f"backticked names not found in scope at {data['sha'][:7]}: {', '.join(missing)}")
    gl = [g.get("term", "") + " " + g.get("means", "") for g in data.get("glossary", [])]
    missing = missing_identifiers(gl + visual_strings(data.get("overview_visual")) + [data["known_drift"]], corpus)
    if missing:
        flag("T5", "must", "overview", f"backticked names not found in scope at {data['sha'][:7]}: {', '.join(missing)}")
    notes = (plan.get("layout") or {}).get("notes") or {}
    for p, note in notes.items():
        if words(note) > NOTE_WORDS:
            flag("A2", "should", "code map", f"the note on {p} is {words(note)} words (target ≤ {NOTE_WORDS})")
    missing = missing_identifiers(list(notes.values()), corpus)
    if missing:
        flag("T5", "must", "code map", f"backticked names not found in scope at {data['sha'][:7]}: {', '.join(missing)}")
    spine_at = []
    for w, x in reader_text(data, plan):
        if SPINE_RX.search(x) and w not in spine_at:
            spine_at.append(w)
    for w in spine_at:
        flag("T4", "must", w, "\"spine\" in reader-facing text; it's the author's word. Name the scenario in plain words")
    if total_steps > MAX_TOUR:
        flag("A3", "should", "tour", f"{total_steps} steps (target ≤ {MAX_TOUR}); cut or split into two tours")
    if visuals == 0:
        flag("T6", "must", "tour", "no visual aids at all")
    if concept_steps > len(data["chapters"]):
        flag("A7", "should", "tour", f"{concept_steps} concept steps for {len(data['chapters'])} chapters; most steps should show code")

    order = {"must": 0, "should": 1}
    flags.sort(key=lambda f: (order[f["severity"]], f["where"]))
    report = {
        "sha": data["sha"],
        "summary": {"chapters": len(data["chapters"]), "steps": total_steps, "minutes": data["minutes"],
                    "visuals": visuals, "concept_steps": concept_steps, "checks": total_checks,
                    "median_words": sorted(p["words"] for p in per_step)[len(per_step) // 2] if per_step else 0,
                    "must": sum(f["severity"] == "must" for f in flags),
                    "should": sum(f["severity"] == "should" for f in flags)},
        "flags": flags,
        "steps": per_step,
    }
    json.dump(report, sys.stdout, ensure_ascii=False, indent=1)
    print()


# ---------- drift ----------

def default_target(repo, sha):
    """Where the code goes next: origin's default branch for a pushed pin. A pin no
    remote has (unpushed commits, a snapshot) only moves on the local line, so HEAD."""
    if not on_remote(repo, sha):
        return "HEAD"
    branch = default_branch(repo)
    if not branch:
        raise PlanError("no origin/HEAD, origin/main or origin/master to compare against; pass --to (and fetch first)")
    return f"origin/{branch}"


def cmd_drift(a):
    plan = load_plan(a.plan)
    data, _ = resolve_plan(plan, a.repo, True, with_map=False)
    to = a.to or default_target(a.repo, data["sha"])
    to_sha, _ = pin(a.repo, to)
    commits = int(git(a.repo, "rev-list", "--count", f"{data['sha']}..{to_sha}").strip() or 0)
    touched = set(git(a.repo, "diff", "--name-only", data["sha"], to_sha, "--", *(data["scope"] or ["."])).splitlines())
    cache, rows, news = {}, {}, {}
    for ci, ch in enumerate(plan["chapters"], 1):
        for si, st in enumerate(ch.get("steps", []), 1):
            sid = f"{ci}.{si}"
            old = data["chapters"][ci - 1]["steps"][si - 1]
            row = {"step": sid, "title": old["title"]}
            rows[sid] = row
            if old["concept"]:
                row["status"] = "concept"
                continue
            row["file"] = old["file"]
            if old["file"] not in touched:
                row["status"] = "same"
                continue
            errs = []
            new = news[sid] = resolve_step(a.repo, to_sha, None, st, f"step {sid}", cache, errs, sid)
            if errs or not new:
                row.update(status="broken", problems=errs)
            elif new["lines"] != old["lines"]:
                row.update(status="changed", was=f"{old['start']}-{old['end']}", now=f"{new['start']}-{new['end']}")
            elif new["start"] != old["start"]:
                row.update(status="moved", was=f"{old['start']}-{old['end']}", now=f"{new['start']}-{new['end']}")
            else:
                row["status"] = "same"
    # A chapter-end find-the-line check points into another step's snippet: changed code can lose its answer.
    for ci, ch in enumerate(plan["chapters"], 1):
        raw = (ch.get("wrap") or {}).get("check")
        for k, c in enumerate(raw if isinstance(raw, list) else [raw] if raw else [], 1):
            row = rows.get(str(c.get("step"))) if isinstance(c, dict) and "line" in c else None
            if row and row["status"] == "changed":
                hits = sum(norm(l) == norm(c["line"]) for l in news[row["step"]]["lines"])
                if hits != 1:
                    row.update(status="broken", problems=[f"chapter {ci} check {k}: its answer line matches {hits} lines now"])
    counts = defaultdict(int)
    for r in rows.values():
        counts[r["status"]] += 1
    out = {"from": data["sha"], "to": to_sha, "to_ref": to, "commits": commits,
           "summary": dict(counts), "files_changed": sorted(touched), "steps": list(rows.values())}
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
    print()


# ---------- main ----------

def load_plan(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        raise PlanError(f"can't read the plan: {e}")


def main():
    ap = argparse.ArgumentParser(description="Build code walkthrough pages from a plan.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("map")
    m.add_argument("--repo", default=".")
    m.add_argument("--ref", default="HEAD")
    m.add_argument("--scope", action="append")
    m.add_argument("--base")
    b = sub.add_parser("build")
    b.add_argument("plan")
    b.add_argument("--repo", default=".")
    b.add_argument("--template", required=True)
    b.add_argument("--out", required=True)
    b.add_argument("--data-out")
    b.add_argument("--no-links", action="store_true")
    r = sub.add_parser("review")
    r.add_argument("plan")
    r.add_argument("--repo", default=".")
    r.add_argument("--no-links", action="store_true")
    d = sub.add_parser("drift")
    d.add_argument("plan")
    d.add_argument("--repo", default=".")
    d.add_argument("--to")
    a = ap.parse_args()
    try:
        {"map": cmd_map, "build": cmd_build, "review": cmd_review, "drift": cmd_drift}[a.cmd](a)
    except PlanError as e:
        lines = str(e).split("\n")
        tail = "; nothing written" if a.cmd == "build" else ""
        print(f"{len(lines)} problem(s){tail}:", file=sys.stderr)
        for line in lines:
            print(f"  - {line}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
