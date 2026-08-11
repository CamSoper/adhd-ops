# Scheduled task prompt — weekly triage

Copy/paste this into a Claude Code web routine (one morning a week, before that day's morning
brief -- the brief folds this run's decision sheet into its stale-check section).

```text
This is the scheduled weekly-triage run (headless, no human in the loop). Run the adhd-ops
plugin's followup-triage skill in REPORT-ONLY mode exactly as written, starting with its
prerequisites and the OOO/holiday gate.
```
