---
description: Build an interactive walkthrough of some code -- a repo, a directory, or a PR -- and publish it as a private page
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent, Artifact
---

The user wants a guided walkthrough of some code. What to walk through (a path, a repo, a branch or PR,
and anything about who it's for):

$ARGUMENTS

Follow the `code-walkthrough` skill exactly, all eight steps, including the critical-path analysis
before the plan and the review before publishing:

@${CLAUDE_PLUGIN_ROOT}/skills/code-walkthrough/SKILL.md

(From a checkout without the plugin installed, that's
`code-walkthrough/skills/code-walkthrough/SKILL.md`.)

Nothing given → walk through the repo or directory this session is working in, and say so.
