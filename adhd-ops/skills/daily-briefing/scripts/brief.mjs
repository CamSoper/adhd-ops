#!/usr/bin/env node
// brief.mjs — deterministic builder for the morning-brief email (daily-briefing)
// and the shutdown email (shutdown skill).
//
// The model gathers data and writes the words; THIS script owns all structure.
// The One Big Thing card, the 3RD STRIKE badges, the stat pills, the delta-first
// "no movement" lines, the calm empty-state fallbacks, and the inline styling
// render from data, every time — they can't be dropped by a sloppy compose.
//
// Render-only: cross-run state (the mention ledger, run history) lives in the
// configured state store (see workspace-config), not in files this script owns.
//
// Zero dependencies (Node stdlib only). One subcommand:
//
//   render   stdin = spec JSON  -> stdout = full inline-HTML email
//
// The spec's `kind` field routes it: absent or "recap" -> the morning brief
// (../references/brief-spec.md), "shutdown" -> the shutdown email (same doc,
// "Shutdown spec" section; used by ../../shutdown/SKILL.md). Pass `render`
// output straight to your mail connector as an HTML body.
//
// The palette is a fixed dark identity regardless of client theme: near-black
// page, violet-tinted dark card, light text. Restyle by editing the constants
// below — never from the spec.

import { readFileSync } from "node:fs";

// ---------- helpers ----------

function esc(v) {
  return String(v ?? "")
    // Voice invariant, enforced structurally: briefs write `--`, never an
    // em-dash. External data (email subjects, meeting titles) can smuggle one
    // in, so normalize instead of failing the send. En-dashes collapse to a
    // plain hyphen so time ranges ("2:00–3:15") stay readable.
    .replaceAll("—", "--")
    .replaceAll("–", "-")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

// A spec `sender` is a display name ("GitHub"), but upstream mail often arrives
// as "GitHub <noreply@github.com>". Drop the angle-bracketed address so the
// brief reads as names, not raw envelopes. Runs before esc(), while the literal
// <> are still present; falls back to the original if a sender somehow
// contained nothing but an address.
function senderName(v) {
  const s = String(v ?? "");
  const stripped = s.replace(/\s*<[^<>@\s]+@[^<>\s]+>\s*/g, " ").trim();
  return stripped || s.trim();
}

function readStdin() {
  try {
    return readFileSync(0, "utf8");
  } catch {
    return "";
  }
}

function die(msg) {
  process.stderr.write(`brief.mjs: ${msg}\n`);
  process.exit(1);
}

// ---------- palette (fixed dark identity) ----------

const PAGE_BG = "#1F1B21"; // page: near-black
const HEADER_BG = "#392960"; // header band: deep violet
const HEADER_TITLE = "#f5f5ff";
const HEADER_META = "#c3bdff";
const CARD_BG = "#231f33"; // card: violet-tinted dark
const TEXT = "#efeff0"; // primary body text
const SNARK = "#cbcace"; // secondary/editorial text
const FAINT = "#9997a0"; // eyebrows, meta, footer
const DIVIDER_C = "#46434c";
const LINK = "#dedbff";

const PILL_TONES = {
  neutral: { bg: "#46434c", fg: "#efeff0" },
  brand: { bg: "#492e8e", fg: "#dedbff" }, // violet — counts that are just facts
  good: { bg: "#165a31", fg: "#b6fbce" }, // green — wins
  warning: { bg: "#933d0d", fg: "#fef2c7" }, // amber — deadlines, gap flags
  danger: { bg: "#96171e", fg: "#ffe0e1" }, // red — someone's blocked / reauth
};

// Accent cards: { border, bg, banner } — bright accents over dark tints.
const CARD_BIG_THING = { border: "#9077f3", bg: "#392960", banner: "#dedbff" }; // violet
const CARD_DECIDE = { border: "#fb2c36", bg: "#611f22", banner: "#ff9fa4" }; // red
const CARD_TLDR = { border: "#f96c0b", bg: "#693420", banner: "#fdbe7c" }; // orange
const CARD_STALE = { border: "#00a896", bg: "#114642", banner: "#1efad9" }; // aqua
const NEEDS_ACTION = { border: "#fb2c36", bg: "#331f20", eyebrow: "#ff9fa4" }; // red, quieter
const BADGE_STRIKE = { bg: "#fb2c36", fg: "#1F1B21" };
const RANK_BADGE = { bg: "#492e8e", fg: "#dedbff" };
const SOURCE_CHIP = { bg: "#28448a", fg: "#cce4ff" }; // blue
const STRIKE_CHIP = { bg: "#46434c", fg: "#cbcace" }; // gray
const CHAT_HOT = "#fdbe7c"; // orange
const CHAT_FYI = FAINT;

const DIVIDER = `<div style="border-top:1px solid ${DIVIDER_C}; margin:16px 0;"></div>`;

// ---------- render primitives ----------

function eyebrow(label, color = FAINT) {
  return `<div style="font-size:11px; font-weight:700; letter-spacing:0.08em; color:${color}; text-transform:uppercase; margin-bottom:10px;">${esc(
    label
  )}</div>`;
}

function renderPill(p) {
  const tone = PILL_TONES[p.tone] || PILL_TONES.neutral;
  const text = [p.emoji, p.value, p.label].filter((x) => x !== undefined && x !== null && x !== "").join(" ");
  return `      <span style="display:inline-block; background:${tone.bg}; border-radius:20px; padding:4px 12px; font-size:13px; color:${tone.fg}; margin:0 4px 6px 0;">${esc(
    text
  )}</span>`;
}

function linkOrText(text, url, color = TEXT) {
  return url
    ? `<a href="${esc(url)}" style="color:${LINK}; text-decoration:underline;">${esc(text)}</a>`
    : `<span style="color:${color};">${esc(text)}</span>`;
}

function sourceChip(label) {
  if (!label) return "";
  return ` <span style="display:inline-block; background:${SOURCE_CHIP.bg}; color:${SOURCE_CHIP.fg}; border-radius:10px; padding:1px 8px; font-size:11px; font-weight:600; margin-left:6px; vertical-align:middle;">${esc(
    label
  )}</span>`;
}

// Subtle strike marker — visible but not a nag. Strike 1 renders nothing;
// validation caps needsAction strikes at 2 (strike 3 lives in decideToday),
// so the only chip this ever draws is "2nd mention".
function strikeChip(strike) {
  if (Number(strike) !== 2) return "";
  return ` <span style="display:inline-block; background:${STRIKE_CHIP.bg}; color:${STRIKE_CHIP.fg}; border-radius:10px; padding:1px 7px; font-size:11px; font-weight:600; vertical-align:middle;">2nd mention</span>`;
}

// ---------- sections ----------

function renderOneBigThing(o) {
  // Required — validated before we get here. Exactly one directive, structurally.
  const text = o.link
    ? `<a href="${esc(o.link)}" style="color:${HEADER_TITLE}; text-decoration:underline;">${esc(o.text)}</a>`
    : esc(o.text);
  return `      <div style="border-left:4px solid ${CARD_BIG_THING.border}; background:${CARD_BIG_THING.bg}; border-radius:0 8px 8px 0; padding:12px 16px; margin:16px 0;">
        <div style="font-size:13px; font-weight:700; color:${CARD_BIG_THING.banner}; margin-bottom:8px;">⭐ ONE BIG THING</div>
        <div style="font-size:15px; font-weight:700; color:${HEADER_TITLE};">${text}</div>
      </div>`;
}

function renderDecideToday(items) {
  if (!Array.isArray(items) || items.length === 0) return "";
  const rows = items
    .map((it) => {
      const badge = `<span style="display:inline-block; background:${BADGE_STRIKE.bg}; color:${BADGE_STRIKE.fg}; font-size:10px; font-weight:700; letter-spacing:0.04em; border-radius:4px; padding:1px 6px; margin-right:6px; vertical-align:middle;">3RD STRIKE</span>`;
      const note = it.strikeNote
        ? ` <span style="font-size:12px; color:${SNARK};">${esc(it.strikeNote)}</span>`
        : "";
      const options = (it.options || [])
        .map(
          (opt, i) =>
            `          <div style="font-size:13px; color:${SNARK}; margin:2px 0 0 8px;">${i + 1}. ${esc(opt)}</div>`
        )
        .join("\n");
      return `        <div style="margin-bottom:12px;">
          <div style="font-size:14px; color:${TEXT}; margin-bottom:4px;">${badge}${linkOrText(
        it.item,
        it.link
      )}${note}</div>
${options}
        </div>`;
    })
    .join("\n");
  return `      <div style="border-left:4px solid ${CARD_DECIDE.border}; background:${CARD_DECIDE.bg}; border-radius:0 8px 8px 0; padding:12px 16px; margin:16px 0;">
        <div style="font-size:13px; font-weight:700; color:${CARD_DECIDE.banner}; margin-bottom:8px;">🚨 DECIDE TODAY</div>
${rows}
      </div>`;
}

function renderTldr(items) {
  // The "No fires today." fallback is structural — an empty array always
  // renders the same calm line.
  const body =
    items.length === 0
      ? `        <div style="font-size:14px; color:${TEXT};">No fires today.</div>`
      : items
          .map(
            (b) =>
              `        <div style="font-size:14px; color:${TEXT}; margin-bottom:6px;">• ${esc(b)}</div>`
          )
          .join("\n");
  return `      <div style="border-left:4px solid ${CARD_TLDR.border}; background:${CARD_TLDR.bg}; border-radius:0 8px 8px 0; padding:12px 16px; margin:16px 0;">
        <div style="font-size:13px; font-weight:700; color:${CARD_TLDR.banner}; margin-bottom:8px;">⚡ TL;DR</div>
${body}
      </div>`;
}

function renderTodaysFocus(items) {
  const head = `      ${DIVIDER}
      ${eyebrow("🎯 TODAY'S FOCUS")}`;
  if (items.length === 0) {
    return `${head}
      <div style="font-size:14px; color:${SNARK};">See above -- light day.</div>`;
  }
  const rows = items
    .map((f, i) => {
      const badge = `<span style="display:inline-block; background:${RANK_BADGE.bg}; color:${RANK_BADGE.fg}; border-radius:10px; padding:1px 8px; font-size:12px; font-weight:700; margin-right:8px; vertical-align:middle;">${
        i + 1
      }</span>`;
      const why = f.why ? ` <span style="font-size:13px; color:${SNARK};">-- ${esc(f.why)}</span>` : "";
      return `      <div style="margin-bottom:10px; font-size:14px; color:${TEXT};">
        ${badge}<span style="font-weight:600;">${
        f.link
          ? `<a href="${esc(f.link)}" style="color:${LINK}; text-decoration:underline;">${esc(f.title)}</a>`
          : esc(f.title)
      }</span>${why}
      </div>`;
    })
    .join("\n");
  return `${head}
${rows}`;
}

function renderNeedsAction(items) {
  if (!Array.isArray(items) || items.length === 0) return "";
  const rows = items
    .map((it) => {
      const waiting = it.waitingOn
        ? `<span style="font-weight:700; color:${TEXT};">${esc(it.waitingOn)}</span> — `
        : "";
      const snark = it.snark ? ` <span style="font-size:13px; color:${SNARK};">-- ${esc(it.snark)}</span>` : "";
      return `      <div style="margin-bottom:10px; padding:10px 12px; background:${NEEDS_ACTION.bg}; border-left:4px solid ${NEEDS_ACTION.border}; border-radius:0 8px 8px 0;">
        <span style="font-size:14px; color:${TEXT};">${waiting}${
        it.link
          ? `<a href="${esc(it.link)}" style="color:${LINK}; text-decoration:underline;">${esc(it.title)}</a>`
          : `<span style="font-weight:600;">${esc(it.title)}</span>`
      }</span>${strikeChip(it.strike)}${snark}
      </div>`;
    })
    .join("\n");
  return `      ${DIVIDER}
      ${eyebrow("🔴 NEEDS ACTION", NEEDS_ACTION.eyebrow)}
${rows}`;
}

// Delta-first, structurally: changed rows render in full; unchanged content is
// ONE gray count line, never a table; both empty -> the section vanishes.
function renderDeltaBlock(title, rowsHtml, unchangedCount, unchangedNoun) {
  const n = Number(unchangedCount);
  const hasUnchanged = Number.isFinite(n) && n > 0;
  if (!rowsHtml && !hasUnchanged) return "";
  const unchangedLine = hasUnchanged
    ? `      <div style="font-size:13px; color:${SNARK}; margin-bottom:10px;">🟡 ${n} ${esc(
        unchangedNoun
      )}, no movement.</div>`
    : "";
  return `      ${DIVIDER}
      ${eyebrow(title)}
${[rowsHtml, unchangedLine].filter(Boolean).join("\n")}`;
}

function renderMeetings(d) {
  if (!d) return "";
  const rows = (d.changed || [])
    .map(
      (m) => `      <div style="margin-bottom:10px; font-size:14px; color:${TEXT};">
        ${linkOrText(m.item, m.link)}${sourceChip(m.source)}
      </div>`
    )
    .join("\n");
  return renderDeltaBlock("📝 MEETING ACTION ITEMS", rows, d.unchangedCount, "action items");
}

function renderCalendar(d) {
  if (!d) return "";
  const rows = (d.changed || [])
    .map(
      (e) => `      <div style="margin-bottom:10px;">
        <span style="font-size:12px; color:${FAINT}; display:block;">${esc(e.when)}${sourceChip(e.calendar)}</span>
        <span style="font-size:14px; font-weight:600; color:${TEXT};">${esc(e.title)}</span>${
        e.snark ? `\n        <span style="font-size:13px; color:${SNARK};"> -- ${esc(e.snark)}</span>` : ""
      }
      </div>`
    )
    .join("\n");
  return renderDeltaBlock("📅 CALENDAR", rows, d.unchangedCount, "events");
}

function renderChat(d) {
  if (!d) return "";
  const group = (label, color, items) => {
    if (!Array.isArray(items) || items.length === 0) return "";
    const rows = items
      .map(
        (s) => `      <div style="margin-bottom:8px; font-size:14px; color:${TEXT};">
        ${linkOrText(s.item, s.link)}${sourceChip(s.channel)}
      </div>`
      )
      .join("\n");
    return `      <div style="font-size:12px; font-weight:700; color:${color}; margin:6px 0;">${label}</div>
${rows}`;
  };
  const rows = [
    group("🔥 ACTIONABLE", CHAT_HOT, d.actionable),
    group("📡 FYI", CHAT_FYI, d.fyi),
  ]
    .filter(Boolean)
    .join("\n");
  return renderDeltaBlock("💬 CHAT", rows, d.unchangedCount, "threads");
}

function renderEmails(d) {
  if (!d) return "";
  const rows = (d.changed || [])
    .map(
      (m) => `      <div style="margin-bottom:10px;">
        <span style="font-size:14px; font-weight:600; color:${TEXT};">${esc(senderName(m.sender))}</span>
        <span style="font-size:13px; color:${SNARK};"> -- ${
        m.link
          ? `<a href="${esc(m.link)}" style="color:${LINK}; text-decoration:underline;">${esc(m.subject)}</a>`
          : esc(m.subject)
      }${m.snark ? ` -- ${esc(m.snark)}` : ""}</span>
      </div>`
    )
    .join("\n");
  return renderDeltaBlock("📧 IMPORTANT EMAILS", rows, d.unchangedCount, "emails");
}

function renderTracker(d) {
  if (!d) return "";
  const rows = (d.changed || [])
    .map(
      (g) => `      <div style="margin-bottom:10px;">
        <span style="font-size:14px; font-weight:600; color:${TEXT};">${linkOrText(
        g.title,
        g.link
      )}</span>${sourceChip(g.repo)}${
        g.detail ? `\n        <span style="font-size:13px; color:${SNARK};"> -- ${esc(g.detail)}</span>` : ""
      }
      </div>`
    )
    .join("\n");
  return renderDeltaBlock("🛠️ WORK TRACKER", rows, d.unchangedCount, "items");
}

// Current-context element: quiet by design. Active "current things" lead,
// snoozes render muted (they're consciously parked, not fires), expired
// snoozes get the one warm-colored resurface line. All date logic (active vs
// expired) happened upstream in the model — this only draws rows.
function renderFocusContext(m) {
  if (!m) return "";
  const current = (m.current || [])
    .map(
      (c) => `      <div style="margin-bottom:8px; font-size:14px; color:${TEXT};">
        ▸ ${linkOrText(c.note, c.link)} <span style="font-size:13px; color:${SNARK};">-- through ${esc(
        c.until
      )}</span>
      </div>`
    )
    .join("\n");
  const snoozed = (m.snoozed || [])
    .map(
      (s) => `      <div style="margin-bottom:8px; font-size:13px; color:${SNARK};">
        😴 ${esc(s.item)} -- snoozed until ${esc(s.until)}
      </div>`
    )
    .join("\n");
  const expired = (m.expired || [])
    .map(
      (e) => `      <div style="margin-bottom:8px; font-size:14px; color:${TEXT};">
        ⏰ <span style="font-weight:600; color:${CHAT_HOT};">${esc(
        e.item
      )}</span> <span style="font-size:13px; color:${SNARK};">-- snooze expired, back on the list${
        e.note ? ` -- ${esc(e.note)}` : ""
      }</span>
      </div>`
    )
    .join("\n");
  const candidates = (m.candidates || [])
    .map(
      (c) => `      <div style="margin-bottom:8px; font-size:14px; color:${TEXT};">
        ❓ ${linkOrText(c.item, c.link)} <span style="font-size:13px; color:${SNARK};">-- ${esc(
        c.note || "looks relevant -- say the word and I'll add it"
      )}</span>
      </div>`
    )
    .join("\n");
  const rows = [current, snoozed, expired, candidates].filter(Boolean).join("\n");
  return `      ${DIVIDER}
      ${eyebrow("🧭 CURRENT CONTEXT", CARD_STALE.banner)}
${rows}`;
}

function renderStaleCheck(sc) {
  if (!sc) return "";
  const intro = sc.intro
    ? `        <div style="font-size:13px; color:${SNARK}; margin-bottom:8px;">${esc(sc.intro)}</div>\n`
    : "";
  const rows = (sc.items || [])
    .map(
      (it) => `        <div style="margin-bottom:8px; font-size:14px; color:${TEXT};">
          <span style="font-weight:700;">${esc(it.n)}.</span> <span style="font-weight:600; color:${CARD_STALE.banner};">${esc(
        it.verdict
      )}</span> — ${linkOrText(it.item, it.link)}
        </div>`
    )
    .join("\n");
  return `      <div style="border-left:4px solid ${CARD_STALE.border}; background:${CARD_STALE.bg}; border-radius:0 8px 8px 0; padding:12px 16px; margin:16px 0;">
        <div style="font-size:13px; font-weight:700; color:${CARD_STALE.banner}; margin-bottom:8px;">🧹 STALE CHECK</div>
${intro}${rows}
      </div>`;
}

function renderFooter(f) {
  const todo = `<a href="${esc(f.todoListUrl)}" style="color:${LINK}; text-decoration:underline;">Backlog: ${esc(
    f.backlogCount
  )} items in the task list</a>`;
  const archive = f.archiveUrl
    ? ` · <a href="${esc(f.archiveUrl)}" style="color:${LINK}; text-decoration:underline;">Full detail in the archive</a>`
    : "";
  return `      ${DIVIDER.replace("margin:16px 0", "margin:20px 0 0")}
      <p style="font-size:12px; color:${FAINT}; margin:12px 0 0; text-align:center;">${todo}${archive}</p>
      <p style="font-size:12px; color:${FAINT}; margin:8px 0 0; text-align:center;">${esc(f.signoff)}</p>`;
}

// ---------- validation + assembly ----------

function requireString(spec, key) {
  if (typeof spec[key] !== "string" || spec[key].trim() === "") {
    die(`render: spec.${key} is required (nonempty string)`);
  }
}

function render(spec) {
  if (!spec || typeof spec !== "object" || Array.isArray(spec)) die("render: spec must be a JSON object");
  requireString(spec, "headerDate");
  requireString(spec, "sinceLabel");
  requireString(spec, "lede");
  const title = typeof spec.title === "string" && spec.title.trim() !== "" ? spec.title : "📋 Morning Brief";

  const pills = Array.isArray(spec.pills) ? spec.pills : null;
  if (!pills || pills.length === 0) die("render: spec.pills must be a nonempty array of stat chips");

  const obt = spec.oneBigThing;
  if (!obt || typeof obt !== "object" || Array.isArray(obt) || typeof obt.text !== "string" || obt.text.trim() === "") {
    die(
      "render: spec.oneBigThing must be an object with nonempty text — exactly ONE directive. " +
        "Ten priorities is zero priorities; pick the one."
    );
  }

  if (!Array.isArray(spec.tldr)) die("render: spec.tldr must be an array (empty = 'No fires today.')");
  if (spec.tldr.length > 5) {
    die(`render: tldr has ${spec.tldr.length} bullets — max 5. Cut it down, don't paper over it.`);
  }
  if (spec.tldr.some((b) => typeof b !== "string" || b.trim() === "")) {
    die("render: every tldr entry must be a nonempty string");
  }

  if (!Array.isArray(spec.todaysFocus)) {
    die("render: spec.todaysFocus must be an array (empty = 'See above -- light day.')");
  }
  if (spec.todaysFocus.length > 3) {
    die(`render: todaysFocus has ${spec.todaysFocus.length} items — max 3, ranked. Focus means focus.`);
  }
  for (const f of spec.todaysFocus) {
    if (!f || typeof f.title !== "string" || f.title.trim() === "") {
      die("render: every todaysFocus item needs a nonempty title");
    }
  }

  const decide = Array.isArray(spec.decideToday) ? spec.decideToday : [];
  for (const it of decide) {
    if (!it || typeof it.item !== "string" || it.item.trim() === "") {
      die("render: every decideToday item needs nonempty item text");
    }
    if (!Array.isArray(it.options) || it.options.length !== 3) {
      die(
        `render: decideToday item "${String(it.item).slice(0, 40)}" needs exactly 3 options ` +
          "(do it today / give it a due date / drop it) — that's the whole point of strike 3"
      );
    }
  }

  const needs = Array.isArray(spec.needsAction) ? spec.needsAction : [];
  for (const it of needs) {
    if (!it || typeof it.title !== "string" || it.title.trim() === "") {
      die("render: every needsAction item needs a nonempty title");
    }
    if (it.strike !== undefined) {
      const s = Number(it.strike);
      if (!Number.isFinite(s) || s < 1 || s > 2) {
        die(
          "render: needsAction strike must be 1 or 2 — strike-3 items belong in decideToday, " +
            "strike-4+ never renders again (SKILL.md Step 3)"
        );
      }
    }
  }

  const delta = spec.delta;
  if (!delta || typeof delta !== "object" || Array.isArray(delta)) {
    die("render: spec.delta is required (object; every subsection optional — empty sections vanish)");
  }
  const checkDelta = (name, sub, arrayKeys, rowKeys) => {
    if (sub === undefined || sub === null) return;
    if (typeof sub !== "object" || Array.isArray(sub)) die(`render: delta.${name} must be an object`);
    for (const k of arrayKeys) {
      if (sub[k] === undefined) continue;
      if (!Array.isArray(sub[k])) die(`render: delta.${name}.${k} must be an array`);
      for (const row of sub[k]) {
        for (const rk of rowKeys) {
          if (!row || typeof row[rk] !== "string" || row[rk].trim() === "") {
            die(`render: every delta.${name}.${k} row needs a nonempty "${rk}"`);
          }
        }
      }
    }
    if (sub.unchangedCount !== undefined) {
      const n = Number(sub.unchangedCount);
      if (!Number.isFinite(n) || n < 0) die(`render: delta.${name}.unchangedCount must be a number >= 0`);
    }
  };
  checkDelta("meetings", delta.meetings, ["changed"], ["item"]);
  checkDelta("calendar", delta.calendar, ["changed"], ["when", "title"]);
  checkDelta("chat", delta.chat, ["actionable", "fyi"], ["item"]);
  checkDelta("emails", delta.emails, ["changed"], ["sender", "subject"]);
  checkDelta("tracker", delta.tracker, ["changed"], ["title"]);

  const focus = spec.focus;
  if (focus !== undefined && focus !== null) {
    if (typeof focus !== "object" || Array.isArray(focus)) {
      die("render: focus, when present, must be an object");
    }
    for (const [key, rowKeys] of [
      ["current", ["note", "until"]],
      ["snoozed", ["item", "until"]],
      ["expired", ["item"]],
      ["candidates", ["item"]],
    ]) {
      if (focus[key] === undefined) continue;
      if (!Array.isArray(focus[key])) die(`render: focus.${key} must be an array`);
      for (const row of focus[key]) {
        for (const rk of rowKeys) {
          if (!row || typeof row[rk] !== "string" || row[rk].trim() === "") {
            die(`render: every focus.${key} row needs a nonempty "${rk}"`);
          }
        }
      }
    }
    const focusEmpty = ["current", "snoozed", "expired", "candidates"].every(
      (k) => !Array.isArray(focus[k]) || focus[k].length === 0
    );
    if (focusEmpty) {
      die(
        "render: focus, when present, needs at least one of current/snoozed/expired/candidates " +
          "nonempty — omit the focus key instead of sending an empty shell"
      );
    }
  }

  const sc = spec.staleCheck;
  if (sc !== undefined && sc !== null) {
    if (typeof sc !== "object" || Array.isArray(sc) || !Array.isArray(sc.items) || sc.items.length === 0) {
      die("render: staleCheck, when present, needs a nonempty items array");
    }
    for (const it of sc.items) {
      if (!it || it.n === undefined || typeof it.verdict !== "string" || typeof it.item !== "string") {
        die("render: every staleCheck item needs n, verdict, and item");
      }
    }
  }

  const f = spec.footer;
  if (!f || typeof f !== "object" || Array.isArray(f)) die("render: spec.footer is required");
  if (!Number.isFinite(Number(f.backlogCount))) die("render: footer.backlogCount must be a number");
  if (typeof f.todoListUrl !== "string" || f.todoListUrl.trim() === "") {
    die("render: footer.todoListUrl is required — the backlog line always deep-links to the task list");
  }
  if (typeof f.signoff !== "string" || f.signoff.trim() === "") {
    die("render: footer.signoff is required — one line that echoes One Big Thing");
  }
  if (!("archiveUrl" in f)) {
    die(
      "render: footer.archiveUrl key is required (value may be null when no archive exists or the " +
        "post failed) — decide explicitly; don't just forget the archive link"
    );
  }

  const sections = [
    renderOneBigThing(obt),
    renderDecideToday(decide),
    renderTldr(spec.tldr),
    renderTodaysFocus(spec.todaysFocus),
    renderNeedsAction(needs),
    renderFocusContext(focus),
    renderMeetings(delta.meetings),
    renderCalendar(delta.calendar),
    renderChat(delta.chat),
    renderEmails(delta.emails),
    renderTracker(delta.tracker),
    renderStaleCheck(sc),
  ].filter(Boolean);

  return `<div style="background-color:${PAGE_BG}; padding:16px; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <div style="max-width:600px; margin:0 auto;">
    <div style="background:${HEADER_BG}; border-radius:12px 12px 0 0; padding:24px 20px 16px;">
      <div style="font-size:22px; font-weight:700; color:${HEADER_TITLE};">${esc(title)}</div>
      <div style="font-size:13px; color:${HEADER_META}; margin-top:4px;">${esc(spec.headerDate)} · ${esc(
    spec.sinceLabel
  )}</div>
    </div>
    <div style="background:${CARD_BG}; border-radius:0 0 12px 12px; padding:20px; box-shadow:0 4px 12px rgba(0,0,0,0.2);">
      <p style="font-size:15px; color:${TEXT}; margin:0 0 12px;">${esc(spec.lede)}</p>
      <div style="margin-bottom:14px;">
${pills.map(renderPill).join("\n")}
      </div>
${sections.join("\n")}
${renderFooter(f)}
    </div>
  </div>
</div>
`;
}

// ---------- shutdown email (kind: "shutdown") ----------
//
// The evening half of the loop: celebrate what moved while the dopamine still
// attaches, park the open loops so the brain can put them down, and seed
// tomorrow's One Big Thing. Same structural philosophy as the brief — the
// invariants (≤5 wins, ≤5 loops, exactly one proposed OBT, the "stands unless
// you swap it" affordance) are enforced here so a sloppy compose can't drop
// them. Zero guilt is structural too: the empty-wins fallback is a calm fixed
// line, never a scold.

const CARD_WINS = { border: "#3ddc84", bg: "#153a26", banner: "#b6fbce" }; // green
const LOOP_ROW = { border: "#9077f3", bg: "#28223d", step: "#dedbff" }; // violet, quieter

function renderShutdownWins(items) {
  const body =
    items.length === 0
      ? `        <div style="font-size:14px; color:${TEXT};">No boxes checked today. It happens -- tomorrow's board is already set.</div>`
      : items
          .map(
            (w) =>
              `        <div style="font-size:14px; color:${TEXT}; margin-bottom:6px;">✅ ${linkOrText(
                w.text,
                w.link
              )}</div>`
          )
          .join("\n");
  return `      <div style="border-left:4px solid ${CARD_WINS.border}; background:${CARD_WINS.bg}; border-radius:0 8px 8px 0; padding:12px 16px; margin:16px 0;">
        <div style="font-size:13px; font-weight:700; color:${CARD_WINS.banner}; margin-bottom:8px;">🏆 WHAT MOVED TODAY</div>
${body}
      </div>`;
}

function renderShutdownLoops(items) {
  const head = `      ${DIVIDER}
      ${eyebrow("🧷 OPEN LOOPS, PARKED")}`;
  if (items.length === 0) {
    return `${head}
      <div style="font-size:14px; color:${SNARK};">Nothing left dangling. Clean shutdown.</div>`;
  }
  const rows = items
    .map(
      (l) => `      <div style="margin-bottom:10px; padding:10px 12px; background:${LOOP_ROW.bg}; border-left:4px solid ${LOOP_ROW.border}; border-radius:0 8px 8px 0;">
        <div style="font-size:14px; color:${TEXT};">${
        l.link
          ? `<a href="${esc(l.link)}" style="color:${LINK}; text-decoration:underline;">${esc(l.title)}</a>`
          : `<span style="font-weight:600;">${esc(l.title)}</span>`
      } <span style="font-size:13px; color:${SNARK};">-- ${esc(l.state)}</span></div>
        <div style="font-size:13px; color:${LOOP_ROW.step}; margin-top:3px;">→ first move: ${esc(l.nextStep)}</div>
      </div>`
    )
    .join("\n");
  return `${head}
      <div style="font-size:13px; color:${SNARK}; margin-bottom:10px;">Written down so you can put them down.</div>
${rows}`;
}

function renderShutdownTomorrow(t) {
  const obtText = t.obt.link
    ? `<a href="${esc(t.obt.link)}" style="color:${HEADER_TITLE}; text-decoration:underline;">${esc(t.obt.text)}</a>`
    : esc(t.obt.text);
  const meeting = t.firstMeeting
    ? `\n        <div style="font-size:13px; color:${SNARK}; margin-top:6px;">First meeting: ${esc(t.firstMeeting)}</div>`
    : "";
  const note = t.note
    ? `\n        <div style="font-size:13px; color:${SNARK}; margin-top:6px;">${esc(t.note)}</div>`
    : "";
  return `      <div style="border-left:4px solid ${CARD_BIG_THING.border}; background:${CARD_BIG_THING.bg}; border-radius:0 8px 8px 0; padding:12px 16px; margin:16px 0;">
        <div style="font-size:13px; font-weight:700; color:${CARD_BIG_THING.banner}; margin-bottom:8px;">⭐ TOMORROW'S ONE BIG THING (PROPOSED)</div>
        <div style="font-size:15px; font-weight:700; color:${HEADER_TITLE};">${obtText}</div>
        <div style="font-size:12px; color:${HEADER_META}; margin-top:6px;">Stands unless you swap it in the morning.</div>${meeting}${note}
      </div>`;
}

function renderShutdown(spec) {
  requireString(spec, "headerDate");
  requireString(spec, "lede");
  const title = typeof spec.title === "string" && spec.title.trim() !== "" ? spec.title : "🌇 Shutdown";

  const wins = Array.isArray(spec.wins) ? spec.wins : null;
  if (!wins) die("render: shutdown spec.wins must be an array (empty = the calm fallback line)");
  if (wins.length > 5) die(`render: shutdown wins has ${wins.length} entries — max 5. Pick the ones that felt like something.`);
  for (const w of wins) {
    if (!w || typeof w.text !== "string" || w.text.trim() === "") {
      die("render: every shutdown win needs nonempty text");
    }
  }

  const loops = Array.isArray(spec.loops) ? spec.loops : null;
  if (!loops) die("render: shutdown spec.loops must be an array (empty = 'clean shutdown')");
  if (loops.length > 5) {
    die(`render: shutdown loops has ${loops.length} entries — max 5. Parking a landfill isn't parking; fold the rest into the task list.`);
  }
  for (const l of loops) {
    for (const k of ["title", "state", "nextStep"]) {
      if (!l || typeof l[k] !== "string" || l[k].trim() === "") {
        die(`render: every shutdown loop needs a nonempty "${k}" — the next physical step is the whole point`);
      }
    }
  }

  const t = spec.tomorrow;
  if (!t || typeof t !== "object" || Array.isArray(t)) die("render: shutdown spec.tomorrow is required (object)");
  if (
    !t.obt ||
    typeof t.obt !== "object" ||
    Array.isArray(t.obt) ||
    typeof t.obt.text !== "string" ||
    t.obt.text.trim() === ""
  ) {
    die(
      "render: shutdown tomorrow.obt must be an object with nonempty text — exactly ONE proposed " +
        "directive, same law as the brief's One Big Thing"
    );
  }

  const pills = Array.isArray(spec.pills) ? spec.pills : [];

  const f = spec.footer;
  if (!f || typeof f !== "object" || Array.isArray(f)) die("render: shutdown spec.footer is required");
  if (typeof f.signoff !== "string" || f.signoff.trim() === "") {
    die("render: shutdown footer.signoff is required — one closing line that gives permission to stop");
  }

  const pillsBlock =
    pills.length > 0
      ? `      <div style="margin-bottom:14px;">
${pills.map(renderPill).join("\n")}
      </div>\n`
      : "";
  const todo = f.todoListUrl
    ? `<a href="${esc(f.todoListUrl)}" style="color:${LINK}; text-decoration:underline;">The list is in the task app</a> · `
    : "";

  return `<div style="background-color:${PAGE_BG}; padding:16px; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <div style="max-width:600px; margin:0 auto;">
    <div style="background:${HEADER_BG}; border-radius:12px 12px 0 0; padding:24px 20px 16px;">
      <div style="font-size:22px; font-weight:700; color:${HEADER_TITLE};">${esc(title)}</div>
      <div style="font-size:13px; color:${HEADER_META}; margin-top:4px;">${esc(spec.headerDate)}</div>
    </div>
    <div style="background:${CARD_BG}; border-radius:0 0 12px 12px; padding:20px; box-shadow:0 4px 12px rgba(0,0,0,0.2);">
      <p style="font-size:15px; color:${TEXT}; margin:0 0 12px;">${esc(spec.lede)}</p>
${pillsBlock}${renderShutdownWins(wins)}
${renderShutdownLoops(loops)}
${renderShutdownTomorrow(t)}
      ${DIVIDER.replace("margin:16px 0", "margin:20px 0 0")}
      <p style="font-size:12px; color:${FAINT}; margin:12px 0 0; text-align:center;">${todo}Day's closed. Anything above survives until morning.</p>
      <p style="font-size:12px; color:${FAINT}; margin:8px 0 0; text-align:center;">${esc(f.signoff)}</p>
    </div>
  </div>
</div>
`;
}

// ---------- main ----------

const [, , sub] = process.argv;

switch (sub) {
  case "render": {
    const raw = readStdin();
    if (!raw.trim()) die("render: no brief-spec JSON on stdin");
    let spec;
    try {
      spec = JSON.parse(raw);
    } catch (e) {
      die(`render: stdin is not valid JSON (${e.message})`);
    }
    if (spec && typeof spec === "object" && !Array.isArray(spec) && spec.kind !== undefined) {
      if (spec.kind !== "recap" && spec.kind !== "shutdown") {
        die(`render: unknown spec.kind '${spec.kind}' — use "recap" (or omit) or "shutdown"`);
      }
    }
    process.stdout.write(spec?.kind === "shutdown" ? renderShutdown(spec) : render(spec));
    break;
  }
  default:
    die(`unknown subcommand '${sub ?? ""}'. Use: render`);
}
