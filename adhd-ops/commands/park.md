---
description: Park a thought or tangent for tomorrow's brief -- one line in, one line back, zero ceremony
allowed-tools: Read, Bash
---

The user is handing you something to hold so they can let go of it: a note for tomorrow's brief,
or a rabbit hole they're setting down. The arguments are the thing itself. **Speed is the whole
feature** -- one append, one line back, no questions unless the input is genuinely empty.

Bindings (state store, timezone) per @${CLAUDE_PLUGIN_ROOT}/skills/workspace-config/SKILL.md.

1. Clock: `TZ=<configured timezone> date -Iseconds`.
2. Classify from the words alone: a rabbit hole / idea / "look at this later" → `kind: "tangent"`;
   a priority / reminder / "make sure tomorrow..." → `kind: "note"`. When in doubt, `note`.
3. Append one record to `inbox/inbox.ndjson` (per the state contract):
   `{"ts": "<ISO>", "kind": "note"|"tangent", "text": "<the user's words, near-verbatim>", "context": "<link or one line, only if they gave one>"}`
4. Confirm in **one line**: "Parked. Tomorrow's brief has it." Nothing else -- no summary, no
   menu, no follow-up question.

No arguments at all → ask once what to park, then do the above. State store missing → say so in
one line and echo the text back so it isn't lost.
