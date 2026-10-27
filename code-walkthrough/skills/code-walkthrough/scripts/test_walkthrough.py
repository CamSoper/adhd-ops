#!/usr/bin/env python3
"""Tests for walkthrough.py. Standard library only: `python3 test_walkthrough.py`.

Each test builds a throwaway git repo whose origin is a local bare repo with a
GitHub-shaped URL swapped in afterwards, so permalinks and the "is the commit on
a remote?" check behave as they do on a real clone.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "walkthrough.py"
TEMPLATE = HERE.parent / "assets" / "template.html"

FILES = {
    "app/README.md": "# Tiny app\n\nStart at `cli.mjs`, which uses lib/core.mjs.\n",
    "app/cli.mjs": (
        "#!/usr/bin/env node\n"
        "import { decide } from \"./lib/core.mjs\";\n"
        "\n"
        "function main(argv) {\n"
        "  const verdict = decide(argv[2]);\n"
        "  console.log(verdict);\n"
        "}\n"
        "main(process.argv);\n"
    ),
    "app/lib/core.mjs": (
        "// ---------- rules ----------\n"
        "const LIMIT = 3;\n"
        "\n"
        "export function decide(input) {\n"
        "  if (!input) return \"refuse\";\n"
        "  if (input.length > LIMIT) return \"refuse\";\n"
        "  return \"ok\";\n"
        "}\n"
        "// </script> must not break the page\n"
        "function unused() {\n"
        "  return LIMIT;\n"
        "}\n"
    ),
    "app/tests/core.test.mjs": "import { decide } from \"../lib/core.mjs\";\n",
    "app/prompt.md": (
        "# Prompt\n"
        "\n"
        "Answer briefly.\n"
        "When the input is empty, reply with refuse and explain " + "why " * 20 + "in one line.\n"
        "Never guess.\n"
    ),
}


def run(*args, cwd=None, check=True, env_extra=None):
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "t@t", **(env_extra or {})}
    env = {k: v for k, v in env.items() if v is not None}   # None in env_extra unsets a variable
    r = subprocess.run(list(args), cwd=cwd, capture_output=True, text=True, env=env)
    if check and r.returncode != 0:
        raise AssertionError(f"{args} failed: {r.stderr}")
    return r


def plan(**over):
    p = {
        "ref": "HEAD",
        "scope": "app",
        "title": "Tiny App",
        "audience": "a new contributor",
        "goal": "change the limit safely",
        "summary": ["A tiny app."],
        "glossary": [{"term": "verdict", "means": "what `decide` returns"}],
        "overview_visual": {"kind": "flow", "caption": "Input goes in, a verdict comes out.",
                            "nodes": [{"label": "`cli.mjs`"}, {"label": "`decide`"}]},
        "chapters": [{
            "title": "The rule",
            "blurb": "Where the decision happens.",
            "wrap": {"takeaways": ["`decide` owns the rule."], "check": {"q": "What does an empty input get?", "a": "`refuse`."}},
            "steps": [
                {"title": "The entry point", "text": ["The CLI hands its argument to `decide`."],
                 "file": "app/cli.mjs", "from": "function main(argv) {", "to": "}",
                 "focus": ["const verdict = decide(argv[2]);"]},
                {"title": "The rule refuses long input", "text": ["Anything longer than `LIMIT` is refused."],
                 "file": "app/lib/core.mjs", "from": "export function decide(input) {", "to": "}",
                 "focus": ["if (input.length > LIMIT) return \"refuse\";"],
                 "callouts": [{"line": "if (!input) return \"refuse\";", "note": "Empty input is refused first."}],
                 "visual": {"kind": "ladder", "caption": "First match wins.",
                            "rungs": [{"test": "no input", "then": "`refuse`"}, {"test": "longer than `LIMIT`", "then": "`refuse`"}],
                            "otherwise": "`ok`"}},
                {"title": "The whole picture", "text": ["Two callers, one rule."],
                 "visual": {"kind": "sequence", "caption": "The CLI asks, the rule answers.",
                            "actors": ["CLI", "core"], "messages": [{"from": "CLI", "to": "core", "label": "`decide`"},
                                                                     {"from": "core", "to": "CLI", "label": "verdict"}]}},
            ],
        }],
    }
    p.update(over)
    return p


class Repo:
    def __init__(self, push=True):
        self.dir = tempfile.mkdtemp()
        self.work = Path(self.dir, "work")
        bare = Path(self.dir, "origin.git")
        run("git", "init", "-q", "--bare", str(bare))
        run("git", "init", "-q", "-b", "main", str(self.work))
        for path, text in FILES.items():
            f = self.work / path
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(text)
        run("git", "add", "-A", cwd=self.work)
        run("git", "commit", "-qm", "init", cwd=self.work)
        run("git", "remote", "add", "origin", str(bare), cwd=self.work)
        if push:
            run("git", "push", "-q", "origin", "main", cwd=self.work)
            run("git", "fetch", "-q", "origin", cwd=self.work)
        run("git", "remote", "set-url", "origin", "https://github.com/acme/tiny.git", cwd=self.work)

    def wt(self, *args, check=False):
        return run(sys.executable, "-I", str(SCRIPT), *args, cwd=self.work, check=check)

    def write_plan(self, p, name="plan.json"):
        path = Path(self.dir, name)
        path.write_text(json.dumps(p))
        return str(path)

    def build(self, p, extra=()):
        out = str(Path(self.dir, "page.html"))
        data = str(Path(self.dir, "data.json"))
        r = self.wt("build", self.write_plan(p), "--repo", str(self.work), "--template", str(TEMPLATE),
                    "--out", out, "--data-out", data, *extra)
        return r, out, data

    def close(self):
        shutil.rmtree(self.dir, ignore_errors=True)


class MapTests(unittest.TestCase):
    def setUp(self):
        self.r = Repo()

    def tearDown(self):
        self.r.close()

    def test_graph_outline_and_entries(self):
        m = json.loads(self.r.wt("map", "--repo", str(self.r.work), "--scope", "app", check=True).stdout)
        edges = {(e["from"], e["to"], e["via"]) for e in m["edges"]}
        self.assertIn(("app/cli.mjs", "app/lib/core.mjs", "import"), edges)
        self.assertIn(("app/README.md", "app/cli.mjs", "mention"), edges)
        self.assertIn("app/cli.mjs", m["entries"])
        self.assertEqual(m["hubs"][0]["path"], "app/lib/core.mjs")
        core = next(f for f in m["files"] if f["path"] == "app/lib/core.mjs")
        self.assertEqual([o["line"] for o in core["outline"]], [1, 4, 10])
        test = next(f for f in m["files"] if f["path"] == "app/tests/core.test.mjs")
        self.assertIn("test-or-fixture", test["roles"])
        self.assertEqual(m["repo_url"], "https://github.com/acme/tiny")

    def test_change_tour_limits_scope_to_the_diff(self):
        base = run("git", "rev-parse", "HEAD", cwd=self.r.work).stdout.strip()
        (self.r.work / "app/lib/core.mjs").write_text(FILES["app/lib/core.mjs"].replace("LIMIT = 3", "LIMIT = 4"))
        run("git", "commit", "-qam", "bump", cwd=self.r.work)
        m = json.loads(self.r.wt("map", "--repo", str(self.r.work), "--scope", "app", "--base", base, check=True).stdout)
        self.assertTrue(m["change_tour"])
        self.assertEqual([f["path"] for f in m["files"]], ["app/lib/core.mjs"])
        self.assertEqual(m["files"][0]["change"], {"added": 1, "removed": 1})


class BuildTests(unittest.TestCase):
    def setUp(self):
        self.r = Repo()

    def tearDown(self):
        self.r.close()

    def test_known_drift_and_self_review_reach_the_page(self):
        r, out, data = self.r.build(plan(review="self-review", known_drift="The README still names `cli.mjs` only."))
        self.assertEqual(r.returncode, 0, r.stderr)
        d = json.loads(Path(data).read_text())
        self.assertEqual((d["review"], d["known_drift"]), ("self-review", "The README still names `cli.mjs` only."))
        self.assertIn('D.review === "self-review"', Path(out).read_text())
        self.assertIn("Known drift", Path(out).read_text())
        r, _, _ = self.r.build(plan(review="peer"))
        self.assertIn("review must be one of", r.stderr)
        r, _, _ = self.r.build(plan(known_drift=["two", "paragraphs"]))
        self.assertIn("known_drift must be one non-empty paragraph", r.stderr)

    def test_happy_path_resolves_everything_from_git(self):
        r, out, data = self.r.build(plan())
        self.assertEqual(r.returncode, 0, r.stderr)
        d = json.loads(Path(data).read_text())
        s1, s2, s3 = d["chapters"][0]["steps"]
        self.assertEqual((s1["start"], s1["end"], s1["focus"]), (4, 7, [5]))
        self.assertEqual((s2["start"], s2["end"], s2["focus"]), (4, 8, [6]))
        self.assertEqual(s2["callouts"], [{"line": 5, "note": "Empty input is refused first."}])
        self.assertTrue(s3["concept"])
        sha = d["sha"]
        self.assertEqual(s1["permalink"], f"https://github.com/acme/tiny/blob/{sha}/app/cli.mjs#L4-L7")
        self.assertEqual(s1["cols"], 60)
        page = Path(out).read_text()
        self.assertIn("<title>Tiny App</title>", page)
        self.assertNotIn("/*__TOUR_DATA__*/", page)
        # "HEAD" moves; the build says which SHA to write into the plan instead.
        self.assertIn(f'set "ref": "{sha}"', r.stderr)
        r2, _, _ = self.r.build(plan(ref=sha))
        self.assertEqual((r2.returncode, r2.stderr), (0, ""))

    def test_snippet_text_cannot_close_the_script_tag(self):
        p = plan()
        p["chapters"][0]["steps"][1]["to"] = "// </script> must not break the page"
        r, out, _ = self.r.build(p)
        self.assertEqual(r.returncode, 0, r.stderr)
        page = Path(out).read_text()
        data_block = page.split('id="tour-data">', 1)[1].split("</script>", 1)[0]
        self.assertIn("<\\/script>", data_block)

    def test_every_problem_is_reported_and_nothing_is_written(self):
        p = plan()
        steps = p["chapters"][0]["steps"]
        steps[0]["file"] = "app/lib/core.mjs"
        steps[0]["from"] = "}"                                    # two of them: ambiguous
        steps[1]["focus"] = ["const LIMIT = 4;"]                  # not in the snippet
        steps[1]["visual"] = {"kind": "sequence", "caption": "x", "actors": ["a", "b"],
                              "messages": [{"from": "a", "to": "b", "label": "go"}]}   # too wide for a code step
        steps[2] = {"title": "Bare", "text": ["No code, no picture."]}
        r, out, _ = self.r.build(p)
        self.assertEqual(r.returncode, 1)
        self.assertIn("4 problem(s); nothing written", r.stderr)
        self.assertIn("'from' anchor matches", r.stderr)
        self.assertIn("focus line matches 0 lines", r.stderr)
        self.assertIn("needs the full width", r.stderr)
        self.assertIn("needs code (file/from/to) or a visual", r.stderr)
        self.assertFalse(Path(out).exists())

    def test_visual_schema_is_checked(self):
        p = plan()
        p["overview_visual"] = {"kind": "states", "caption": "c", "states": [{"label": "a"}, {"label": "b"}],
                                "edges": [], "exits": [{"from": "zzz", "label": "x", "to": "y"}]}
        p["chapters"][0]["steps"][1]["visual"] = {"kind": "timeline", "caption": "c", "unit": "day",
                                                  "points": [{"at": 14, "label": "a"}, {"at": 0, "label": "b"}]}
        r, _, _ = self.r.build(p)
        self.assertEqual(r.returncode, 1)
        self.assertIn("one edge label per step", r.stderr)
        self.assertIn("needs from (a state label)", r.stderr)
        self.assertIn("ascending order", r.stderr)

    def test_too_many_steps_in_a_chapter(self):
        p = plan()
        p["chapters"][0]["steps"] = p["chapters"][0]["steps"][:1] * 9
        r, _, _ = self.r.build(p)
        self.assertIn("has 9 steps", r.stderr)

    def test_no_links_mode(self):
        r, _, data = self.r.build(plan(), extra=["--no-links"])
        self.assertEqual(r.returncode, 0, r.stderr)
        d = json.loads(Path(data).read_text())
        self.assertFalse(d["links"])
        self.assertIsNone(d["chapters"][0]["steps"][0]["permalink"])


class UnpushedTests(unittest.TestCase):
    """SKILL.md, Step 1, "Unpushed commits": the user's own branch is toured as it is, links off."""

    def test_unpushed_commit_is_refused(self):
        r = Repo(push=False)
        try:
            res, out, _ = r.build(plan())
            self.assertEqual(res.returncode, 1)
            self.assertIn("isn't on any remote branch", res.stderr)
            self.assertIn("--no-links", res.stderr)
        finally:
            r.close()

    def test_unpushed_commit_builds_without_links(self):
        r = Repo(push=False)
        try:
            res, _, data = r.build(plan(), extra=["--no-links"])
            self.assertEqual(res.returncode, 0, res.stderr)
            d = json.loads(Path(data).read_text())
            self.assertFalse(d["links"])
            self.assertIsNone(d["chapters"][0]["steps"][0]["permalink"])
            self.assertEqual(d["repo"], "acme/tiny")         # still named after its GitHub origin
        finally:
            r.close()

    def test_uncommitted_edits_never_reach_the_page(self):
        r = Repo(push=False)
        try:
            (r.work / "app/cli.mjs").write_text(FILES["app/cli.mjs"].replace("console.log(verdict);", "console.log(\"EDITED\");"))
            (r.work / "app/lib/scratch.mjs").write_text("export const UNTRACKED = 1;\n")
            res, out, data = r.build(plan(), extra=["--no-links"])
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertIn("  console.log(verdict);", json.loads(Path(data).read_text())["chapters"][0]["steps"][0]["lines"])
            page = Path(out).read_text()
            self.assertNotIn("EDITED", page)
            self.assertNotIn("scratch.mjs", page)            # not in the code map either
        finally:
            r.close()

    def test_drift_on_an_unpushed_pin_compares_against_head(self):
        r = Repo()                                           # origin/main exists, so the old default would be it
        try:
            (r.work / "app/README.md").write_text(FILES["app/README.md"] + "\nMore.\n")
            run("git", "commit", "-qam", "local one", cwd=r.work)
            p = plan(ref=run("git", "rev-parse", "HEAD", cwd=r.work).stdout.strip())
            (r.work / "app/cli.mjs").write_text(FILES["app/cli.mjs"].replace("console.log(verdict);", "console.log(`${verdict}`);"))
            run("git", "commit", "-qam", "local two", cwd=r.work)
            rep = json.loads(r.wt("drift", r.write_plan(p), "--repo", str(r.work), check=True).stdout)
            self.assertEqual((rep["to_ref"], rep["commits"]), ("HEAD", 1))
            self.assertEqual({s["step"]: s["status"] for s in rep["steps"]}, {"1.1": "changed", "1.2": "same", "1.3": "concept"})
        finally:
            r.close()


# One file per exclude in SKILL.md's snapshot block, so dropping any exclude fails the test.
EXCLUDED = {
    "app/node_modules/dep/index.js": "module.exports = 'NODE_MODULES_JUNK';\n",
    ".venv/lib/site.py": "VENV_JUNK = 1\n",
    "venv/bin/activate": "VENV2_JUNK\n",
    "app/__pycache__/core.cpython-312.pyc": "PYCACHE_JUNK\n",
    "app/dist/bundle.js": "DIST_JUNK\n",
    "app/build/out.js": "BUILD_JUNK\n",
    "target/debug/app": "TARGET_JUNK\n",
    ".terraform/providers/x": "TERRAFORM_JUNK\n",
    ".env": "TOKEN=SECRET_ENV\n",
    "app/.env.local": "TOKEN=SECRET_ENV_LOCAL\n",
    "certs/server.pem": "SECRET_PEM\n",
    "certs/server.key": "SECRET_KEY\n",
    "app/debug.log": "GITIGNORED_LOG\n",               # the folder's own .gitignore
}
def mapped_files(node):
    """Every file path in a built code map's tree."""
    for c in node.get("children", []):
        yield from (mapped_files(c) if c.get("dir") else [c["path"]])


HOOK = "#!/bin/sh\ntouch \"hook-$(basename \"$0\")\"\n"


class SnapshotTests(unittest.TestCase):
    """SKILL.md's "Not a git repo" commands, run as written, against a plain folder, under a
    global git config that would write into the folder or fail if the commands didn't guard it."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.folder, self.scratch = self.tmp / "my folder", self.tmp / "w"
        self.scratch.mkdir()
        for path, text in {**FILES, **EXCLUDED, ".gitignore": "*.log\n"}.items():
            f = self.folder / path
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(text)
        # A developer's global config: hooks (global, and copied in by an init template that has no
        # info/ folder), and forced signing with a signer that always fails.
        hooks, template = self.tmp / "hooks", self.tmp / "template" / "hooks"
        for d in (hooks, template):
            d.mkdir(parents=True)
            for name in ("pre-commit", "prepare-commit-msg", "commit-msg", "post-commit", "post-index-change"):
                (d / name).write_text(HOOK)
                (d / name).chmod(0o755)
        cfg = self.tmp / "global.gitconfig"
        cfg.write_text(f"[core]\n\thooksPath = {hooks}\n[init]\n\ttemplateDir = {template.parent}\n"
                       "[commit]\n\tgpgSign = true\n[gpg]\n\tprogram = false\n")
        # No identity from the environment: the block has to bring its own.
        self.env = {"W": str(self.scratch), "GIT_CONFIG_GLOBAL": str(cfg), "GIT_CONFIG_NOSYSTEM": "1",
                    "GIT_CEILING_DIRECTORIES": str(self.tmp), "GIT_AUTHOR_NAME": None, "GIT_AUTHOR_EMAIL": None,
                    "GIT_COMMITTER_NAME": None, "GIT_COMMITTER_EMAIL": None}
        self.snap = str(self.scratch / "my folder.git")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def block(self):
        text = (HERE.parent / "SKILL.md").read_text()
        blocks = re.findall(r"```bash\n(.*?)```", text, re.S)
        block = next(b for b in blocks if 'SNAP="$W/' in b)
        return [line.strip() for line in block.splitlines() if line.strip()]

    def snapshot(self, lines):
        script = "\n".join(lines).replace("<dir>", str(self.folder))
        run("bash", "-euc", script, cwd=self.tmp, env_extra=self.env)
        return run("git", "-C", self.snap, "rev-parse", "HEAD").stdout.strip()

    def contents(self):
        return {p.relative_to(self.folder).as_posix(): p.read_bytes() for p in sorted(self.folder.rglob("*")) if p.is_file()}

    def wt(self, *args, check=True):
        return run(sys.executable, "-I", str(SCRIPT), *args, cwd=self.tmp, check=check,
                   env_extra={"GIT_CEILING_DIRECTORIES": str(self.tmp)})

    def build(self, p, repo):
        path, out, data = self.tmp / "plan.json", self.tmp / "page.html", self.tmp / "data.json"
        path.write_text(json.dumps(p))
        res = self.wt("build", str(path), "--repo", repo, "--template", str(TEMPLATE), "--out", str(out),
                      "--data-out", str(data), "--no-links", check=False)
        return res, out, data

    def test_the_global_config_is_really_hostile(self):
        # Without the block's guards, the same config writes into the work tree and fails the commit.
        work = self.tmp / "control"
        work.mkdir()
        (work / "a.txt").write_text("a\n")
        run("git", "init", "-q", str(work), env_extra=self.env)
        run("git", "add", "-A", cwd=work, env_extra=self.env)
        r = run("git", "-c", "user.name=x", "-c", "user.email=x@x", "commit", "-qm", "x", cwd=work, check=False,
                env_extra=self.env)
        self.assertNotEqual(r.returncode, 0)
        self.assertTrue(list(work.glob("hook-*")))

    def test_a_plain_folder_tours_from_a_snapshot_it_never_touches(self):
        res, _, _ = self.build(plan(), str(self.folder))
        self.assertEqual(res.returncode, 1)
        self.assertIn("isn't a git repository", res.stderr)
        self.assertIn("snapshot", res.stderr)

        before = self.contents()
        sha = self.snapshot(self.block())
        self.assertEqual(self.contents(), before)            # nothing written, by git or by a hook
        files = run("git", "-C", self.snap, "ls-tree", "-r", "--name-only", "HEAD").stdout.splitlines()
        self.assertIn("app/lib/core.mjs", files)
        self.assertIn(".gitignore", files)
        for kept_out in EXCLUDED:
            self.assertNotIn(kept_out, files)

        m = json.loads(self.wt("map", "--repo", self.snap, "--ref", sha).stdout)
        self.assertIsNone(m["repo_url"])
        self.assertIn("app/lib/core.mjs", [f["path"] for f in m["files"]])

        p = plan(ref=sha, scope=".")
        res, out, data = self.build(p, self.snap)
        self.assertEqual(res.returncode, 0, res.stderr)
        d = json.loads(data.read_text())
        self.assertEqual((d["repo"], d["codemap"]["root"], d["links"]), ("my folder", "my folder", False))
        self.assertEqual(sorted(mapped_files(d["codemap"]["tree"])), sorted(files))
        page = out.read_text()
        self.assertIn("<title>Tiny App</title>", page)
        for text in EXCLUDED.values():
            self.assertNotIn(text.strip(), page)

        path = self.tmp / "plan.json"
        rep = json.loads(self.wt("review", str(path), "--repo", self.snap, "--no-links").stdout)
        self.assertEqual(rep["summary"]["must"], 0, rep["flags"])
        self.assertEqual(self.contents(), before)

    def test_a_snapshot_taken_again_drifts_against_the_last(self):
        block = self.block()
        old = self.snapshot(block)
        (self.folder / "app/cli.mjs").write_text(FILES["app/cli.mjs"].replace("console.log(verdict);", "console.log(`${verdict}`);"))
        again = [line for line in block if line.startswith('git --git-dir="$SNAP" --work-tree=')]
        self.assertEqual(len(again), 2)                      # "run the last two lines again"
        self.assertEqual(again, block[-2:])
        new = self.snapshot(block[:1] + again)               # SNAP= is a shell variable: set it again
        self.assertNotEqual(old, new)
        path = self.tmp / "plan.json"
        path.write_text(json.dumps(plan(ref=old)))
        rep = json.loads(self.wt("drift", str(path), "--repo", self.snap).stdout)
        self.assertEqual((rep["to"], rep["to_ref"], rep["commits"]), (new, "HEAD", 1))
        self.assertEqual({s["step"]: s["status"] for s in rep["steps"]}, {"1.1": "changed", "1.2": "same", "1.3": "concept"})
        # A snapshot repository that's gone (a later session) says what to do instead.
        fresh = self.tmp / "fresh.git"
        run("git", "init", "-q", "--bare", str(fresh))
        res = self.wt("drift", str(path), "--repo", str(fresh), check=False)
        self.assertEqual(res.returncode, 1)
        self.assertIn("snapshot the folder again", res.stderr)


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.r = Repo()

    def tearDown(self):
        self.r.close()

    def review(self, p):
        res = self.r.wt("review", self.r.write_plan(p), "--repo", str(self.r.work))
        self.assertEqual(res.returncode, 0, res.stderr)
        return json.loads(res.stdout)

    def test_spine_in_reader_text_is_a_must(self):
        p = plan(summary=["Follows one spine: an empty input."], known_drift="Nothing drifted.",
                 layout={"notes": {"app/cli.mjs": "where the spine starts"}})
        p["chapters"][0]["steps"][0]["title"] = "The spine starts here"
        p["chapters"][0]["steps"][0]["check"] = {"q": "What does the CLI pass on?", "choices": [
            {"text": "Its argument", "right": True, "why": "It hands `argv` on, the Spine's first move."},
            {"text": "Nothing", "why": "It always passes its argument."}]}
        p["chapters"][0]["wrap"]["check"]["a"] = "`refuse`, the Spine's first exit."
        rep = self.review(p)
        got = {f["where"] for f in rep["flags"] if f["id"] == "T4" and f["severity"] == "must"}
        self.assertEqual(got, {"overview", "code map", "step 1.1", "chapter 1 wrap"})
        p["chapters"][0]["steps"][2]["visual"]["caption"] = "Spinel is a mineral, not the word."
        p["summary"] = ["Follows one scenario: an empty input."]
        p["layout"] = {"notes": {"app/cli.mjs": "where input arrives"}}
        p["chapters"][0]["steps"][0]["title"] = "The entry point"
        p["chapters"][0]["steps"][0]["check"]["choices"][0]["why"] = "It hands `argv` on."
        p["chapters"][0]["wrap"]["check"]["a"] = "`refuse`."
        self.assertFalse([f for f in self.review(p)["flags"] if f["id"] == "T4"])

    def test_check_names_must_be_taught_in_their_chapter(self):
        p = plan()
        ch1 = p["chapters"][0]
        ch2 = {"title": "The CLI", "blurb": "How input arrives.",
               "steps": [dict(ch1["steps"][0]), dict(ch1["steps"][0], title="Again"), dict(ch1["steps"][0], title="Thrice")],
               "wrap": {"takeaways": ["The CLI only forwards."],
                        "check": {"q": "What caps the input length?", "a": "`LIMIT`, via `decide`; never `madeUp`."}}}
        ch2["steps"][1] = dict(ch2["steps"][1], check={"q": "Where does a long input stop?", "choices": [
            {"text": "At the rule", "right": True, "why": "`decide` checks it against `LIMIT`."},
            {"text": "At the CLI", "why": "The CLI only forwards its argument."}]})
        p["chapters"].append(ch2)
        rep = self.review(p)
        t7 = [f for f in rep["flags"] if f["id"] == "T7" and f["severity"] == "must"]
        self.assertEqual(sorted(f["where"] for f in t7), ["chapter 2 wrap", "step 2.2 check"])
        for f in t7:
            self.assertIn("LIMIT", f["message"])
            self.assertNotIn("decide", f["message"])   # shown in chapter 2's code
            self.assertNotIn("madeUp", f["message"])   # already a T5 invention, not double-flagged
        self.assertTrue([f for f in rep["flags"] if f["id"] == "T5" and "madeUp" in f["message"]])
        self.assertFalse([f for f in self.review(plan())["flags"] if f["id"] == "T7" and f["severity"] == "must"])

    def test_wide_lines_in_prompt_files_are_a_should(self):
        p = plan()
        p["chapters"][0]["steps"][2] = {"title": "The prompt refuses empty input",
                                        "text": ["The prompt mirrors the rule."], "file": "app/prompt.md",
                                        "from": "Answer briefly.", "to": "Never guess.", "focus": ["Never guess."]}
        rep = self.review(p)
        a9 = [f for f in rep["flags"] if f["id"] == "A9"]
        self.assertEqual([(f["severity"], f["where"]) for f in a9], [("should", "step 1.3")])
        self.assertIn("1 shown line(s) over 110", a9[0]["message"])
        self.assertFalse([f for f in self.review(plan())["flags"] if f["id"] == "A9"])

    def test_pointing_ahead_is_a_should(self):
        p = plan()
        p["chapters"][0]["steps"][0]["text"] = ["The CLI hands its argument to `decide` (next step)."]
        p["chapters"][0]["steps"][1]["visual"]["rungs"][0]["then"] = "`refuse`; Chapter 2 shows why"
        rep = self.review(p)
        t10 = [f for f in rep["flags"] if f["id"] == "T10"]
        self.assertEqual([(f["severity"], f["where"]) for f in t10], [("should", "step 1.1"), ("should", "step 1.2")])
        self.assertFalse([f for f in self.review(plan())["flags"] if f["id"] == "T10"])

    def test_clean_plan_has_no_must_flags(self):
        rep = self.review(plan())
        self.assertEqual(rep["summary"]["must"], 0, rep["flags"])
        self.assertEqual(rep["summary"]["visuals"], 3)

    def test_flags(self):
        p = plan()
        st = p["chapters"][0]["steps"]
        st[0]["text"] = ["word " * 75 + "and `decideFast` is invented."]
        st[0]["focus"] = []
        p["chapters"][0]["wrap"] = {"takeaways": []}
        del p["goal"]
        rep = self.review(p)
        got = {(f["id"], f["severity"], f["where"]) for f in rep["flags"]}
        self.assertIn(("A2", "should", "step 1.1"), got)
        self.assertIn(("A4", "must", "step 1.1"), got)
        self.assertIn(("T7", "must", "chapter 1"), got)
        self.assertIn(("A5", "should", "overview"), got)
        self.assertIn(("A1", "should", "step 1.1"), got)
        t5 = [f for f in rep["flags"] if f["id"] == "T5"]
        self.assertEqual(len(t5), 1)
        self.assertIn("decideFast", t5[0]["message"])

    def test_identifier_spans_found_whole_or_by_token(self):
        p = plan()
        p["chapters"][0]["steps"][0]["text"] = ["It calls `decide(argv[2])` and logs `verdict ...`."]
        rep = self.review(p)
        self.assertFalse([f for f in rep["flags"] if f["id"] == "T5"], rep["flags"])


def with_checks(**over):
    """The base plan plus one of each check kind, a visual line link and a chapter `at`."""
    p = plan(**over)
    ch = p["chapters"][0]
    st = ch["steps"]
    st[2]["check"] = {"q": "What does `main` print?",
                      "choices": [{"text": "the verdict", "right": True, "why": "It logs what `decide` returns."},
                                  {"text": "the input", "why": "The input only goes to `decide`."},
                                  {"text": "nothing", "why": "It calls `console.log` once."}]}
    st[1]["check"] = {"q": "Tap the line that accepts the input.", "line": "return \"ok\";",
                      "why": "Only input that passes both checks reaches it."}
    st[1]["visual"]["rungs"][1]["line"] = "if (input.length > LIMIT) return \"refuse\";"
    ch["at"] = "`decide`"
    ch["wrap"] = {"takeaways": ["`decide` owns the rule."], "pre": True, "check": [
        {"q": "What does an input longer than `LIMIT` get?", "see": "1.2",
         "choices": [{"text": "`refuse`", "right": True, "why": "The second rung refuses it."},
                     {"text": "`ok`", "why": "Only short input reaches `ok`."}]},
        {"q": "Tap the line that refuses empty input.", "step": "1.2", "line": "if (!input) return \"refuse\";",
         "why": "It runs first, before the length check."}]}
    return p


class CheckTests(unittest.TestCase):
    def setUp(self):
        self.r = Repo()

    def tearDown(self):
        self.r.close()

    def test_checks_links_and_at_resolve(self):
        r, _, data = self.r.build(with_checks())
        self.assertEqual(r.returncode, 0, r.stderr)
        ch = json.loads(Path(data).read_text())["chapters"][0]
        _, s2, s3 = ch["steps"]
        self.assertEqual(s3["check"]["kind"], "choice")
        self.assertEqual(sum(c["right"] for c in s3["check"]["choices"]), 1)
        self.assertEqual(ch["wrap"]["checks"][0]["see"], "1.2")
        self.assertEqual((s2["check"]["kind"], s2["check"]["ln"], s2["check"]["step"]), ("line", 7, "1.2"))
        self.assertNotIn("line", s2["check"])
        self.assertEqual(s2["visual"]["rungs"][1]["ln"], 6)
        self.assertNotIn("ln", s2["visual"]["rungs"][0])
        self.assertEqual(ch["at"], "`decide`")
        w = ch["wrap"]
        self.assertTrue(w["pre"])
        self.assertEqual([c["kind"] for c in w["checks"]], ["choice", "line"])
        self.assertEqual((w["checks"][1]["step"], w["checks"][1]["ln"]), ("1.2", 5))
        # The shuffle is seeded by the question: a rebuild shows the same order.
        r2, _, data2 = self.r.build(with_checks())
        self.assertEqual(json.loads(Path(data2).read_text())["chapters"][0]["steps"][2]["check"], s3["check"])

    def test_check_problems_are_reported(self):
        p = with_checks()
        ch = p["chapters"][0]
        st = ch["steps"]
        st[0]["check"] = dict(st[2]["check"])                              # a check on step 1, and "pre" too
        st[0]["check"]["choices"] = [dict(c, right=True) for c in st[0]["check"]["choices"]]  # three right answers
        st[1]["check"]["line"] = "if (!input) return \"refuse\";"         # the callout's line: gives it away
        st[2]["check"] = {"q": "Which line?", "line": "x", "why": "y"}   # concept step: no code to tap
        ch["at"] = "nowhere"
        ch["wrap"]["check"][0] = {"q": "Open question", "a": "an answer"}  # pre needs a choice first
        ch["wrap"]["check"][1]["step"] = "1.3"                            # a concept step
        r, _, _ = self.r.build(p)
        self.assertEqual(r.returncode, 1)
        for msg in ("exactly one choice must have", "gives it away", "needs code on the step",
                    "isn't a node label", "must be a choice check", "must name a code step",
                    "step 1 has its own check"):
            self.assertIn(msg, r.stderr)

    def test_see_and_scope_rules(self):
        p = with_checks()
        p["chapters"][0]["steps"][1]["check"]["see"] = "1.1"            # a step's check is answered by its step
        p["chapters"][0]["wrap"]["check"][0]["see"] = "2.1"             # no such step, and past this chapter
        p["scope"] = "app/lib"                                          # step 1.1 shows app/cli.mjs
        r, _, _ = self.r.build(p)
        self.assertEqual(r.returncode, 1)
        self.assertIn('drop "see"', r.stderr)
        self.assertIn('"see" must name a step in this chapter or an earlier one', r.stderr)
        self.assertIn("app/cli.mjs is outside the plan's scope", r.stderr)

    def test_visual_links_need_a_code_step_and_a_unique_line(self):
        p = plan()
        p["overview_visual"]["nodes"][0]["line"] = "function main(argv) {"
        p["chapters"][0]["steps"][1]["visual"]["rungs"][0]["line"] = "const LIMIT = 3;"   # outside the snippet
        r, _, _ = self.r.build(p)
        self.assertEqual(r.returncode, 1)
        self.assertIn("line links need code beside them", r.stderr)
        self.assertIn("ladder line link matches 0 lines", r.stderr)

    def test_review_flags_checks(self):
        p = with_checks()
        p["chapters"][0]["wrap"] = {"takeaways": ["x"], "check": {"q": "Why?", "a": "Because."}}
        for s in p["chapters"][0]["steps"]:
            s.pop("check", None)
        res = self.r.wt("review", self.r.write_plan(p), "--repo", str(self.r.work))
        rep = json.loads(res.stdout)
        self.assertIn(("T7", "should"), {(f["id"], f["severity"]) for f in rep["flags"]})
        p = with_checks()
        p["chapters"][0]["steps"][2]["check"]["choices"][0]["text"] = "the verdict that decide returns for the first argument"
        p["chapters"][0]["steps"][2]["check"]["choices"][2]["why"] = "`decideFast` does that."
        rep = json.loads(self.r.wt("review", self.r.write_plan(p), "--repo", str(self.r.work)).stdout)
        msgs = [f["message"] for f in rep["flags"]]
        self.assertTrue(any("much the longest" in m for m in msgs), msgs)
        self.assertTrue(any("decideFast" in m for m in msgs), msgs)
        self.assertEqual(rep["summary"]["checks"], 4)


class PageDataTests(unittest.TestCase):
    def setUp(self):
        self.r = Repo()

    def tearDown(self):
        self.r.close()

    def test_code_map_and_breadcrumb(self):
        p = plan(layout={"notes": {"app/lib/core.mjs": "the rule", "app/lib/": "the logic"}})
        r, _, data = self.r.build(p)
        self.assertEqual(r.returncode, 0, r.stderr)
        d = json.loads(Path(data).read_text())
        cm = d["codemap"]
        self.assertEqual((cm["root"], cm["files"], cm["visited"]), ("app", 5, 2))
        kids = {c["name"]: c for c in cm["tree"]["children"]}
        self.assertEqual(sorted(list(kids)[:2]), ["lib", "tests"])        # folders first
        self.assertEqual(list(kids)[2], "cli.mjs")                         # then files on the tour
        self.assertEqual(set(list(kids)[3:]), {"README.md", "prompt.md"})
        core = kids["lib"]["children"][0]
        self.assertEqual((core["visits"], core["note"], core["lines"]), (["1.2"], "the rule", 12))
        self.assertIn("hub", core["roles"])
        self.assertEqual(kids["lib"]["note"], "the logic")
        self.assertIn("entry", kids["cli.mjs"]["roles"])
        self.assertEqual(kids["tests"]["visited"], 0)
        s1, s2, _ = d["chapters"][0]["steps"]
        self.assertEqual((s1["symbol"], s2["symbol"]), ("main", "decide"))

    def test_code_map_layout_is_checked(self):
        p = plan(layout={"notes": {"app/nope.mjs": "x"}, "hide": ["app/lib/"]})
        r, _, _ = self.r.build(p)
        self.assertEqual(r.returncode, 1)
        self.assertIn("'app/nope.mjs' isn't a file in scope", r.stderr)
        self.assertIn("app/lib/core.mjs is hidden but a step shows it", r.stderr)

    def test_drift(self):
        p = plan()
        sha = run("git", "rev-parse", "HEAD", cwd=self.r.work).stdout.strip()
        p["ref"] = sha
        core = FILES["app/lib/core.mjs"].replace("const LIMIT = 3;", "const LIMIT = 3;\nconst UNUSED = 0;")
        (self.r.work / "app/lib/core.mjs").write_text(core)
        (self.r.work / "app/cli.mjs").write_text(FILES["app/cli.mjs"].replace("console.log(verdict);", "console.log(`${verdict}`);"))
        run("git", "commit", "-qam", "drift", cwd=self.r.work)
        rep = json.loads(self.r.wt("drift", self.r.write_plan(p), "--repo", str(self.r.work), "--to", "HEAD", check=True).stdout)
        status = {s["step"]: s["status"] for s in rep["steps"]}
        self.assertEqual(status, {"1.1": "changed", "1.2": "moved", "1.3": "concept"})
        self.assertEqual(rep["commits"], 1)
        (self.r.work / "app/cli.mjs").write_text("main();\n")
        run("git", "commit", "-qam", "gone", cwd=self.r.work)
        rep = json.loads(self.r.wt("drift", self.r.write_plan(p), "--repo", str(self.r.work), "--to", "HEAD", check=True).stdout)
        self.assertEqual(rep["steps"][0]["status"], "broken")

    def test_title_echo_and_long_chapter(self):
        p = plan()
        st = p["chapters"][0]["steps"]
        st[1]["title"] = "The rule refuses long input"
        st[1]["text"] = ["The rule refuses any long input."]
        st += [dict(st[0]) for _ in range(4)]
        rep = json.loads(self.r.wt("review", self.r.write_plan(p), "--repo", str(self.r.work)).stdout)
        got = {(f["id"], f["where"], f["message"][:20]) for f in rep["flags"]}
        self.assertIn(("A1", "step 1.2", "the first sentence r"), got)
        self.assertIn(("A3", "chapter 1", "7 steps (target ≤ 6)"), got)


class MoreRulesTests(unittest.TestCase):
    def setUp(self):
        self.r = Repo()

    def tearDown(self):
        self.r.close()

    def test_table_row_links_breadcrumbs_and_compare(self):
        p = plan()
        p["chapters"][0]["steps"][1]["visual"] = {
            "kind": "table", "caption": "Each refusal.", "columns": ["When", "Gets"],
            "rows": [{"cells": ["no input", "`refuse`"], "line": "if (!input) return \"refuse\";"}, ["too long", "`refuse`"]]}
        p["chapters"][0]["steps"][1]["callouts"] = []
        p["chapters"][0]["steps"].insert(0, {"title": "Start here", "text": ["The README points at the CLI."],
                                             "file": "app/README.md", "from": "# Tiny app", "to": "Start at `cli.mjs`, which uses lib/core.mjs.",
                                             "focus": ["Start at `cli.mjs`, which uses lib/core.mjs."]})
        r, _, data = self.r.build(p)
        self.assertEqual(r.returncode, 0, r.stderr)
        d = json.loads(Path(data).read_text())
        readme, _, core, _ = d["chapters"][0]["steps"]
        self.assertIsNone(readme["symbol"])                      # it opens on its own heading
        self.assertEqual(core["visual"]["rows"][0]["ln"], 5)
        self.assertNotIn("ln", json.dumps(p["chapters"][0]["steps"][2]["visual"]))  # the plan itself is untouched
        self.assertEqual(d["compareUrl"], f"https://github.com/acme/tiny/compare/{d['sha']}...main")

    def test_drift_rechecks_chapter_end_answers(self):
        p = with_checks()
        p["ref"] = run("git", "rev-parse", "HEAD", cwd=self.r.work).stdout.strip()
        # The chapter-end find-the-line answer (on step 1.2's snippet) disappears; step 1.2 still resolves.
        core = FILES["app/lib/core.mjs"].replace('  if (!input) return "refuse";\n', '  if (input == null) return "refuse";\n')
        (self.r.work / "app/lib/core.mjs").write_text(core)
        run("git", "commit", "-qam", "rename", cwd=self.r.work)
        p["chapters"][0]["steps"][1]["callouts"] = []
        rep = json.loads(self.r.wt("drift", self.r.write_plan(p), "--repo", str(self.r.work), "--to", "HEAD", check=True).stdout)
        row = next(s for s in rep["steps"] if s["step"] == "1.2")
        self.assertEqual(row["status"], "broken")
        self.assertIn("chapter 1 check 2", row["problems"][0])

    def test_giveaway_flags(self):
        p = with_checks()
        st = p["chapters"][0]["steps"]
        st[2]["title"] = "The verdict comes back to the CLI"
        st[2]["check"]["choices"][0]["text"] = "the verdict"
        p["chapters"][0]["wrap"]["check"][1]["q"] = "Tap the line whose returned verdict says refuse for empty input."
        rep = json.loads(self.r.wt("review", self.r.write_plan(p), "--repo", str(self.r.work)).stdout)
        msgs = [f["message"] for f in rep["flags"] if f["id"] == "T9"]
        self.assertTrue(any("title gives the right choice away" in m for m in msgs), msgs)


class CheckFlagTests(unittest.TestCase):
    """check_flags on its own: the giveaways a test repo is too small to stage."""

    def flags(self, c, **kw):
        sys.path.insert(0, str(HERE))
        try:
            import walkthrough
        finally:
            sys.path.pop(0)
        out = []
        walkthrough.check_flags(c, "here", lambda *f: out.append(f[3]), **kw)
        return out

    def test_find_the_line_question_that_paraphrases_its_answer(self):
        line = 'if (list !== "helper" && t.helper) return no("it\'s Helper-made and not in the 🤖 list, so nobody handed it off");'
        echo = {"kind": "line", "q": "A Helper-made task outside the 🤖 list: tap the line that refuses it.", "why": "x", "ln": 1}
        fresh = {"kind": "line", "q": "A dispatch names a task whose body starts \"Source: Mail\". Tap the line that refuses it.", "why": "x", "ln": 1}
        self.assertTrue(any("paraphrases" in m for m in self.flags(echo, answer_line=line)))
        self.assertFalse(self.flags(fresh, answer_line=line))

    def test_prediction_given_away_by_its_title(self):
        c = {"kind": "choice", "q": "What happens?", "choices": [
            {"text": "Real work goes to the Workshop", "right": True, "why": "x"}, {"text": "The desk does it", "right": False, "why": "y"}]}
        self.assertTrue(any("title gives" in m for m in self.flags(c, cue="Real work goes to the Workshop, once")))
        self.assertFalse(self.flags(c, cue="A job line, then one dispatch"))


class PageSmokeTests(unittest.TestCase):
    """Drives the built page in Chromium when Playwright is installed (it isn't in CI): no
    script errors, a choice and a find-the-line check answer, and phones stack in reading order."""

    SCRIPT = r"""
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch(), out = { errors: [] };
  const p = await b.newPage({ viewport: { width: 1280, height: 900 } });
  p.on('pageerror', (e) => out.errors.push(e.message));
  const url = 'file://' + process.argv[2];
  await p.goto(url + '#step-1-3'); await p.waitForTimeout(300);
  await p.locator('.check.predict button.opt').first().click(); await p.waitForTimeout(100);
  out.choice = await p.locator('.check.predict .verdict').count();
  await p.goto(url + '#step-1-2'); await p.waitForTimeout(300);
  await p.locator('.row[data-pick][data-n="7"]').click(); await p.waitForTimeout(100);
  out.line = await p.locator('.row.is-answer[data-n="7"]').count();
  await p.goto(url + '#check-1'); await p.waitForTimeout(300);
  out.checkpoint = await p.locator('.cp-view .check').count();
  const m = await b.newPage({ viewport: { width: 390, height: 700 } });
  m.on('pageerror', (e) => out.errors.push(e.message));
  await m.goto(url + '#step-1-2'); await m.waitForTimeout(300);
  out.order = await m.evaluate(() => {
    const y = (s) => document.querySelector(s).getBoundingClientRect().top;
    return y('.prose') < y('.pane') && y('.pane') < y('.story .nav');
  });
  console.log(JSON.stringify(out));
  await b.close();
})();
"""

    def test_page_in_a_browser(self):
        if not shutil.which("node") or run("node", "-e", "require('playwright')", check=False).returncode:
            self.skipTest("node with playwright isn't installed")
        r = Repo()
        try:
            res, out, _ = r.build(with_checks())
            self.assertEqual(res.returncode, 0, res.stderr)
            js = Path(r.dir, "smoke.js")
            js.write_text(self.SCRIPT)
            got = json.loads(run("node", str(js), out).stdout)
            self.assertEqual(got, {"errors": [], "choice": 1, "line": 1, "checkpoint": 2, "order": True})
        finally:
            r.close()


if __name__ == "__main__":
    unittest.main(verbosity=1)
