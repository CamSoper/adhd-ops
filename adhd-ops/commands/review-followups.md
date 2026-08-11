---
description: Triage open follow-up items with fresh data from all sources
allowed-tools: Read, Grep, Bash, Agent, AskUserQuestion
---

Review and triage all open follow-up tasks from the configured follow-ups list.

First, read the config and the triage skill for the complete execution flow:

1. @${CLAUDE_PLUGIN_ROOT}/skills/workspace-config/SKILL.md
2. @${CLAUDE_PLUGIN_ROOT}/skills/followup-triage/SKILL.md

Execute the followup-triage skill instructions precisely, in interactive mode. Resolve task-app,
calendar, chat, mail, and tracker tools against whatever connectors this environment actually has
(bindings in workspace-config); connector tools may permission-prompt, which is fine in an
interactive session.
