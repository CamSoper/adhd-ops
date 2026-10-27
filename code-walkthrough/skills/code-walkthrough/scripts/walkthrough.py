#!/usr/bin/env python3
"""walkthrough.py -- the mechanical half of the code-walkthrough skill.

Same split as the rest of this marketplace: the model reads the code, picks the
order and writes the words; this script owns everything that has to be exactly
right. A plan names every snippet by the exact text of its lines, never by line
number, and the script resolves those anchors against `git show <sha>:<path>`,
so every line number, snippet and permalink on the page comes from git.
Standard library only, JSON in and JSON out.

Subcommands:

  map    --repo DIR --ref REF [--scope PATH ...] [--base REF]
      Evidence for the critical-path analysis: the in-scope files with their
      outlines (headings, top-level definitions), the reference graph between
      them (imports, and mentions of one file's path or name in another), fan-in
      and fan-out, entry-point candidates and hubs. --base makes it a change
      tour: scope becomes the files changed between merge-base(BASE, REF) and REF.

  build  PLAN --repo DIR --template FILE --out PAGE [--data-out FILE] [--no-links]
      Resolves every anchor, focus line and callout (each must match exactly one
      line), validates the visuals and the plan's limits, refuses a commit no
      remote has (every permalink would 404), and writes the page. All problems
      are reported together; on any problem nothing is written.

  review PLAN --repo DIR [--no-links]
      The mechanical half of the review: per-step and per-chapter metrics, and
      flags keyed to references/review-rubric.md (A* = ADHD-friendliness, T* =
      teaching effectiveness). Includes the identifier check: every `backticked`
      token the narration or a visual uses must exist somewhere in scope at the
      pinned commit, or it's flagged as a possible invention.

Exit codes: 0 = ok (review: report written, flags or not), 1 = invalid plan or
input (problems on stderr), 2 = usage.

Tests: test_walkthrough.py, beside this file (`python3 test_walkthrough.py`).
"""

import argparse
import json
import math
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import PurePosixPath

# ---------- limits (mirror references/plan-format.md and review-rubric.md) ----------

MAX_SPAN = 45          # lines per snippet, hard (build error)
SOFT_SPAN = 30         # lines per snippet, soft (review flag A4)
MAX_STEPS = 8          # steps per chapter, hard
MIN_STEPS = 3          # steps per chapter, soft
MAX_TOUR = 25          # steps per tour, soft
MAX_CALLOUTS = 4
MAX_FOCUS = 5
WORDS_SOFT = 70        # narration words per step (A2)
WORDS_HARD = 100
FIRST_SENTENCE = 22    # words (A1)
LONG_SENTENCE = 28     # words (A8)
TITLE_WORDS = 9        # (T2)
CAPTION_WORDS = 25     # (T6)
CHAPTER_MINUTES = 10   # (A3)
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
    sha = git(repo, "rev-parse", f"{ref}^{{commit}}").strip()
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


def text_of(repo, sha, path, size):
    if size > 512 * 1024:
        return None
    raw = git(repo, "show", f"{sha}:{path}", binary=True)
    if b"\0" in raw[:8192]:
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None


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


def cmd_map(a):
    sha, committed = pin(a.repo, a.ref)
    scopes = a.scope or ["."]
    changed = None
    if a.base:
        mb = git(a.repo, "merge-base", a.base, sha).strip()
        stat = git(a.repo, "diff", "--numstat", mb, sha, "--", *scopes)
        changed = {}
        for row in stat.splitlines():
            add, rem, path = row.split("\t", 2)
            changed[path] = {"added": None if add == "-" else int(add), "removed": None if rem == "-" else int(rem)}
    listing = tree(a.repo, sha, scopes)
    if changed is not None:
        listing = [(p, s) for p, s in listing if p in changed]
    truncated = len(listing) > 600
    listing = listing[:600]

    texts, skipped = {}, []
    for path, size in listing:
        t = text_of(a.repo, sha, path, size)
        if t is None:
            skipped.append(path)
        else:
            texts[path] = t
    paths = set(texts)

    gomod = None
    try:
        m = re.search(r"^module\s+(\S+)", git(a.repo, "show", f"{sha}:go.mod"), re.M)
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
        for dst in paths:
            if dst == src or (src, dst, "import") in edges:
                continue
            base = PurePosixPath(dst).name
            if dst in text or (unique_base.get(base) == dst and base in text):
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
    out = {
        "sha": sha, "committed": committed, "repo_url": github_base(a.repo), "scope": scopes,
        "change_tour": changed is not None,
        "totals": {"files": len(files), "lines": sum(f["lines"] for f in files)},
        "entries": [f["path"] for f in files if "entry" in f["roles"]],
        "hubs": [{"path": f["path"], "fan_in": f["fan_in"]} for f in hubs if f["fan_in"]],
        "files": files,
        "edges": [{"from": s, "to": d, "via": v} for s, d, v in sorted(edges)],
        "skipped": skipped,
        "truncated": truncated,
    }
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
    print()


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


def check_visual(v, where, on_code_step, errs):
    if not isinstance(v, dict):
        errs.append(f"{where}: visual must be an object")
        return
    kind = v.get("kind")
    if kind not in VISUALS:
        errs.append(f"{where}: visual kind {kind!r} isn't one of {', '.join(VISUALS)}")
        return
    req, code_ok = VISUALS[kind]
    if on_code_step and not code_ok:
        errs.append(f"{where}: a {kind} visual needs the full width; put it on a concept step (no file)")
    if not norm(v.get("caption", "")):
        errs.append(f"{where}: visual needs a caption saying what to notice")
    for k in req:
        if k not in v:
            errs.append(f"{where}: {kind} visual needs {k!r}")
    if any(k not in v for k in req):
        return

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
            for r in v["rows"]:
                if not isinstance(r, list) or len(r) != len(v["columns"]):
                    errs.append(f"{where}: every table row needs {len(v['columns'])} cells")


def resolve_step(repo, sha, links, step, where, cache, errs):
    out = {"title": norm(step.get("title", "")), "text": step.get("text", [])}
    if not out["title"]:
        errs.append(f"{where}: missing title")
    if not isinstance(out["text"], list) or not out["text"] or not all(isinstance(p, str) and p.strip() for p in out["text"]):
        errs.append(f"{where}: text must be a list of non-empty paragraphs")
    if "file" not in step:
        if "visual" not in step:
            errs.append(f"{where}: a step needs code (file/from/to) or a visual (a concept step)")
        else:
            check_visual(step["visual"], where, False, errs)
            out["visual"] = step["visual"]
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
    if "visual" in step:
        check_visual(step["visual"], where, True, errs)
        out["visual"] = step["visual"]

    snippet = lines[a:b + 1]
    widest = max((len(l.expandtabs(4)) for l in snippet), default=0)
    out.update({
        "concept": False,
        "file": path,
        "lang": lang_of(path),
        "start": a + 1,
        "end": b + 1,
        "lines": snippet,
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
    return secs


def resolve_plan(plan, repo, no_links):
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
            errs.append(f"{sha[:7]} isn't on any remote branch; push it (or pin an upstream ref) or every link 404s")
    if "overview_visual" in plan:
        check_visual(plan["overview_visual"], "overview", False, errs)

    cache, chapters = {}, []
    for ci, ch in enumerate(plan["chapters"], 1):
        steps_in = ch.get("steps", [])
        if not 1 <= len(steps_in) <= MAX_STEPS:
            errs.append(f"chapter {ci} has {len(steps_in)} steps (1-{MAX_STEPS}); split or merge it")
        steps = []
        for si, st in enumerate(steps_in, 1):
            r = resolve_step(repo, sha, links, st, f"chapter {ci} step {si}", cache, errs)
            if r:
                steps.append(r)
        wrap = ch.get("wrap", {})
        chapters.append({"title": norm(ch.get("title", "")), "blurb": ch.get("blurb", ""), "steps": steps,
                         "wrap": wrap, "minutes": max(1, round(sum(step_seconds(s) for s in steps) / 60))})
        if not norm(ch.get("title", "")):
            errs.append(f"chapter {ci} needs a title")
    if errs:
        raise PlanError("\n".join(errs))

    scope = plan.get("scope", [])
    scope = [scope] if isinstance(scope, str) else scope
    data = {
        "title": plan["title"],
        "repo": links.removeprefix("https://github.com/") if links else "",
        "scope": scope,
        "audience": plan.get("audience", ""),
        "goal": plan.get("goal", ""),
        "summary": plan["summary"],
        "glossary": plan.get("glossary", []),
        "overview_visual": plan.get("overview_visual"),
        "sha": sha,
        "committed": committed,
        "links": bool(links),
        "commitUrl": f"{links}/commit/{sha}" if links else None,
        "treeUrl": (f"{links}/tree/{sha}/{scope[0]}" if len(scope) == 1 and scope[0] not in (".", "") else f"{links}/tree/{sha}") if links else None,
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
    print(f"ok: {total} steps in {len(data['chapters'])} chapters, about {data['minutes']} min, pinned to {data['sha'][:7]} -> {a.out}")
    if plan["ref"] != data["sha"]:
        print(f"note: ref {plan['ref']!r} can move; set \"ref\": \"{data['sha']}\" in the plan so a rebuild shows the same code",
              file=sys.stderr)
    for ci, c in enumerate(data["chapters"], 1):
        for si, s in enumerate(c["steps"], 1):
            where = "concept" if s["concept"] else f"{s['file']}:{s['start']}-{s['end']} focus={s['focus']}"
            extra = f" visual={s['visual']['kind']}" if s.get("visual") else ""
            extra += f" callouts={[c['line'] for c in s['callouts']]}" if s.get("callouts") else ""
            print(f"  {ci}.{si} {where}{extra}")


def esc_html(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ---------- review ----------

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
    out += [c for r in v.get("rows", []) for c in r]
    return [s for s in out if isinstance(s, str)]


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


def cmd_review(a):
    plan = load_plan(a.plan)
    data, cache = resolve_plan(plan, a.repo, a.no_links)
    scopes = data["scope"] or ["."]
    corpus_parts = []
    for path, size in tree(a.repo, data["sha"], scopes):
        t = text_of(a.repo, data["sha"], path, size)
        if t:
            corpus_parts.append(t)
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
    total_steps = 0
    concept_steps = 0
    for ci, ch in enumerate(data["chapters"], 1):
        cw = f"chapter {ci}"
        n = len(ch["steps"])
        total_steps += n
        if n < MIN_STEPS and len(data["chapters"]) > 1:
            flag("A3", "should", cw, f"only {n} steps; fold it into a neighbor or give it more to do")
        if ch["minutes"] > CHAPTER_MINUTES:
            flag("A3", "should", cw, f"about {ch['minutes']} min; split it (target ≤ {CHAPTER_MINUTES})")
        wrap = ch.get("wrap") or {}
        check = wrap.get("check") or {}
        if not norm(check.get("q", "")) or not norm(check.get("a", "")):
            flag("T7", "must", cw, "no check-yourself question (wrap.check.q and .a)")
        tk = wrap.get("takeaways") or []
        if not 1 <= len(tk) <= 3:
            flag("T7", "should", cw, f"{len(tk)} takeaways; give 1-3")
        missing = missing_identifiers(tk + [check.get("q", ""), check.get("a", "")], corpus)
        if missing:
            flag("T5", "must", f"{cw} wrap", f"backticked names not found in scope at {data['sha'][:7]}: {', '.join(missing)}")
        for si, s in enumerate(ch["steps"], 1):
            w = f"step {ci}.{si}"
            wc = sum(words(p) for p in s["text"])
            sents = sentences(s["text"])
            first = words(sents[0]) if sents else 0
            longest = max((words(x) for x in sents), default=0)
            m = {"step": f"{ci}.{si}", "title": s["title"], "words": wc, "paragraphs": len(s["text"]),
                 "first_sentence_words": first, "longest_sentence_words": longest,
                 "concept": s["concept"], "visual": (s.get("visual") or {}).get("kind")}
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
                if s.get("visual") and wc > 60:
                    flag("A7", "should", w, "code, a visual and more than 60 words on one step; trim the words or move the visual")
            elif wc > 80:
                flag("A7", "should", w, f"concept step with {wc} words; the picture should carry it")
            if s.get("visual"):
                cap = s["visual"].get("caption", "")
                if words(cap) > CAPTION_WORDS:
                    flag("T6", "should", w, f"visual caption is {words(cap)} words (target ≤ {CAPTION_WORDS})")
            strings = s["text"] + [s["title"]] + visual_strings(s.get("visual")) + [c["note"] for c in s.get("callouts", [])]
            missing = missing_identifiers(strings, corpus)
            if missing:
                flag("T5", "must", w, f"backticked names not found in scope at {data['sha'][:7]}: {', '.join(missing)}")
    gl = [g.get("term", "") + " " + g.get("means", "") for g in data.get("glossary", [])]
    missing = missing_identifiers(gl + visual_strings(data.get("overview_visual")), corpus)
    if missing:
        flag("T5", "must", "overview", f"backticked names not found in scope at {data['sha'][:7]}: {', '.join(missing)}")
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
                    "visuals": visuals, "concept_steps": concept_steps,
                    "median_words": sorted(p["words"] for p in per_step)[len(per_step) // 2] if per_step else 0,
                    "must": sum(f["severity"] == "must" for f in flags),
                    "should": sum(f["severity"] == "should" for f in flags)},
        "flags": flags,
        "steps": per_step,
    }
    json.dump(report, sys.stdout, ensure_ascii=False, indent=1)
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
    a = ap.parse_args()
    try:
        {"map": cmd_map, "build": cmd_build, "review": cmd_review}[a.cmd](a)
    except PlanError as e:
        lines = str(e).split("\n")
        tail = "; nothing written" if a.cmd == "build" else ""
        print(f"{len(lines)} problem(s){tail}:", file=sys.stderr)
        for line in lines:
            print(f"  - {line}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
