---
description: Rescue command -- one next action sized to the time actually left, right now
allowed-tools: Read, Bash, AskUserQuestion
---

The user needs direction and momentum right now -- they may or may not have read today's brief,
and the afternoon went somewhere. Read the config and the gsd skill for the complete execution
flow:

1. @${CLAUDE_PLUGIN_ROOT}/skills/workspace-config/SKILL.md
2. @${CLAUDE_PLUGIN_ROOT}/skills/gsd/SKILL.md
3. @${CLAUDE_PLUGIN_ROOT}/skills/gsd/references/focus-audio.md

Execute the gsd skill instructions precisely. Speed matters more than completeness -- every input
is optional except the one next action.

Notes:

- Resolve state, calendar, and music tools against whatever connectors this environment actually
  has (bindings in workspace-config). Connector tools may permission-prompt; that's fine -- /gsd
  is always interactive.
- Nothing here is a prerequisite: the ritual offer silently drops the pieces the session doesn't
  have, and with every connector missing the command still delivers one small action.
