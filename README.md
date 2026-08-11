# adhd-ops

**Executive-function support patterns for ADHD brains, plus a [Claude Code](https://code.claude.com)
plugin that runs them.**

This repo distills a personal AI-assistant system that's been running in production (on one human)
for a while now. People kept asking how it works, so here it is -- the ideas and the machinery,
scrubbed of anything personal. Every name, number, and example in this repo is fictional.

The premise, in one line: **executive dysfunction is an architecture problem, not a willpower
problem.** You don't fix it with resolve; you fix it by designing the system around the brain you
actually have. The rest of this repo is what that design turned out to look like.

## Two ways to use this

1. **Read [`PLAYBOOK.md`](PLAYBOOK.md).** The patterns -- One Big Thing, the 3-strike rule,
   delta-first briefings, structural zero-guilt, the shutdown ritual, the rescue command -- stand on
   their own. You can implement them with any assistant, a cron job and some scripts, or paper.
   The playbook is the actual knowledge; everything else is one implementation of it.
2. **Install the plugin.** If you use Claude Code with connectors to your calendar, task app, and
   email, the `adhd-ops` plugin turns the playbook into a running system: a morning brief, an
   evening shutdown, a `/gsd` rescue command, a `/park` capture command, follow-up triage, and a
   monthly retro.

## The system at a glance

```
        ┌─────────────────────────────────────────────────────┐
        │                                                     │
        ▼                                                     │
  🌅 MORNING BRIEF ──── the day's one directive, delta-only news
        │                                                     │
        │   ┌── /park ── capture stray thoughts, zero ceremony│
        │   │                                                 │
        │   └── /gsd ─── rescue: ONE next action, sized to    │
        │                the time actually left               │
        ▼                                                     │
  🌇 SHUTDOWN ───────── celebrate what moved, park open loops,│
        │               propose tomorrow's One Big Thing ─────┘
        │
  🧹 WEEKLY TRIAGE ──── reconcile the backlog against reality
        │
  🔁 MONTHLY RETRO ──── the system reads its own telemetry,
                        proposes exactly ONE tuning change
```

Every component obeys the same laws (argued in full in the playbook): push beats pull, one
directive beats ten priorities, repetition without escalation is banner blindness, celebration is
load-bearing, and guilt is never a feature.

## Install

```text
/plugin marketplace add CamSoper/adhd-ops
/plugin install adhd-ops@adhd-ops
```

Then work through the setup checklist in [`adhd-ops/README.md`](adhd-ops/README.md) -- the plugin
ships as a template, and the `workspace-config` skill is where you fill in your own calendars, task
list, state store, and voice. Nothing personal is baked in; nothing runs until you configure it.

**What you'll need:**

- Claude Code (the scheduled pieces run as [Claude Code web routines](https://code.claude.com/docs/en/claude-code-on-the-web);
  the interactive commands work anywhere Claude Code runs).
- Connectors/MCP servers for your calendar, task app, and email. The skills are written against
  *roles* (calendar, tasks, mail, chat), not specific products -- Microsoft To Do, Todoist, Google
  Calendar, Outlook, Gmail, Slack all work if a connector exists for them.
- A durable state store the assistant can read and write across sessions -- a private GitHub repo
  works fine (see the state contract in `workspace-config`).
- Optional: a push-notification channel (ntfy, Pushover, Home Assistant notify, ...) for the
  once-a-day rescue nudge. Everything degrades gracefully without it.

## Provenance and privacy

This is a sanitized public fork of a private personal system. The private version's config --
calendar IDs, task-list IDs, family details, employer specifics -- was never in this repo, and this
repo's git history began at publication. All people, employers, projects, and numbers appearing in
examples are invented. If you spot anything that looks like real personal data, open an issue.

## License

[MIT](LICENSE). Take the ideas; they're the point.
