#!/usr/bin/env python3
"""Tests for walkthrough.py. Standard library only: `python3 test_walkthrough.py`.

Each test builds a throwaway git repo whose origin is a local bare repo with a
GitHub-shaped URL swapped in afterwards, so permalinks and the "is the commit on
a remote?" check behave as they do on a real clone.
"""

import json
import os
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


def run(*args, cwd=None, check=True):
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "t@t"}
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

    def test_known_drift_and_self_review_reach_the_page(self):
        r, out, data = self.r.build(plan(review="self-review", known_drift="The README still names `cli.mjs` only."))
        self.assertEqual(r.returncode, 0, r.stderr)
        d = json.loads(Path(data).read_text())
        self.assertEqual((d["review"], d["known_drift"]), ("self-review", "The README still names `cli.mjs` only."))
        self.assertIn('D.review === "self-review"', Path(out).read_text())
        r, _, _ = self.r.build(plan(review="peer"))
        self.assertIn("review must be one of", r.stderr)

    def test_no_links_mode(self):
        r, _, data = self.r.build(plan(), extra=["--no-links"])
        self.assertEqual(r.returncode, 0, r.stderr)
        d = json.loads(Path(data).read_text())
        self.assertFalse(d["links"])
        self.assertIsNone(d["chapters"][0]["steps"][0]["permalink"])


class UnpushedTests(unittest.TestCase):
    def test_unpushed_commit_is_refused(self):
        r = Repo(push=False)
        try:
            res, out, _ = r.build(plan())
            self.assertEqual(res.returncode, 1)
            self.assertIn("isn't on any remote branch", res.stderr)
        finally:
            r.close()


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.r = Repo()

    def tearDown(self):
        self.r.close()

    def review(self, p):
        res = self.r.wt("review", self.r.write_plan(p), "--repo", str(self.r.work))
        self.assertEqual(res.returncode, 0, res.stderr)
        return json.loads(res.stdout)

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


    def test_spine_in_reader_text_is_a_must(self):
        p = plan(summary=["Follows one spine: an empty input."], known_drift="Nothing drifted.")
        p["chapters"][0]["steps"][0]["title"] = "The spine starts here"
        p["chapters"][0]["wrap"]["check"]["a"] = "`refuse`, the Spine's first exit."
        rep = self.review(p)
        got = {f["where"] for f in rep["flags"] if f["id"] == "T4" and f["severity"] == "must"}
        self.assertEqual(got, {"overview", "step 1.1", "chapter 1 wrap"})
        p["chapters"][0]["steps"][2]["visual"]["caption"] = "Spinel is a mineral, not the word."
        p["summary"] = ["Follows one scenario: an empty input."]
        p["chapters"][0]["steps"][0]["title"] = "The entry point"
        p["chapters"][0]["wrap"]["check"]["a"] = "`refuse`."
        self.assertFalse([f for f in self.review(p)["flags"] if f["id"] == "T4"])

    def test_check_names_must_be_taught_in_their_chapter(self):
        p = plan()
        ch1 = p["chapters"][0]
        ch2 = {"title": "The CLI", "blurb": "How input arrives.",
               "steps": [dict(ch1["steps"][0]), dict(ch1["steps"][0], title="Again"), dict(ch1["steps"][0], title="Thrice")],
               "wrap": {"takeaways": ["The CLI only forwards."],
                        "check": {"q": "What caps the input length?", "a": "`LIMIT`, via `decide`; never `madeUp`."}}}
        p["chapters"].append(ch2)
        rep = self.review(p)
        t7 = [f for f in rep["flags"] if f["id"] == "T7" and f["severity"] == "must"]
        self.assertEqual([f["where"] for f in t7], ["chapter 2 wrap"])
        self.assertIn("LIMIT", t7[0]["message"])
        self.assertNotIn("decide", t7[0]["message"])   # shown in chapter 2's code
        self.assertNotIn("madeUp", t7[0]["message"])   # already a T5 invention, not double-flagged
        self.assertTrue([f for f in rep["flags"] if f["id"] == "T5" and "madeUp" in f["message"]])

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


if __name__ == "__main__":
    unittest.main(verbosity=1)
