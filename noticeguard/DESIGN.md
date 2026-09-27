---
name: NoticeGuard
description: Editorial legal. Paper ground, ink type, charcoal slabs, one accent per verdict.
colors:
  paper: "#F3F0EA"
  paper-2: "#EBE7DF"
  paper-3: "#E2DDD3"
  card: "#FBFAF7"
  hair: "#DAD5CC"
  ink: "#1A1917"
  ink-2: "#4A4740"
  muted: "#6B665E"
  slab: "#161513"
  slab-2: "#23211E"
  slab-hair: "#4A463F"
  cream: "#F3F0EA"
  cream-2: "#B9B3A8"
  accent-soft-ink: "#E8E1D2"
  ready: "#1F6B3A"
  ready-soft: "#DCEBDF"
  gap: "#9A6200"
  gap-soft: "#F3E6C6"
  adviser: "#7A1F2B"
  adviser-soft: "#F0D9DC"
typography:
  display:
    fontFamily: "Source Serif 4, Georgia, Times New Roman, serif"
    fontSize: "2.75rem"
    fontWeight: 500
    lineHeight: 1.08
    letterSpacing: "-0.015em"
  headline:
    fontFamily: "Source Serif 4, Georgia, Times New Roman, serif"
    fontSize: "1.35rem"
    fontWeight: 500
    lineHeight: 1.2
    letterSpacing: "-0.005em"
  title:
    fontFamily: "Source Serif 4, Georgia, Times New Roman, serif"
    fontSize: "1.05rem"
    fontWeight: 500
    lineHeight: 1.25
    letterSpacing: "-0.005em"
  quote:
    fontFamily: "Source Serif 4, Georgia, Times New Roman, serif"
    fontSize: "1.35rem"
    fontWeight: 400
    lineHeight: 1.35
    fontVariation: "italic"
  body:
    fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.5
  body-prose:
    fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif"
    fontSize: "15.5px"
    fontWeight: 400
    lineHeight: 1.6
  label:
    fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif"
    fontSize: "11.5px"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "0.08em"
  caption:
    fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif"
    fontSize: "12.5px"
    fontWeight: 400
    lineHeight: 1.4
rounded:
  hairline: "4px"
  sm: "8px"
  md: "14px"
  lg: "22px"
  pill: "999px"
spacing:
  xs: "6px"
  sm: "10px"
  md: "14px"
  lg: "18px"
  xl: "22px"
  gutter: "28px"
components:
  button-primary:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.cream}"
    rounded: "{rounded.pill}"
    padding: "9px 18px"
  button-primary-hover:
    backgroundColor: "#000000"
    textColor: "{colors.cream}"
  button-secondary:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    padding: "9px 18px"
  button-secondary-hover:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.cream}"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    padding: "9px 18px"
  button-ghost-hover:
    backgroundColor: "{colors.paper-2}"
    textColor: "{colors.ink}"
  button-on-dark:
    backgroundColor: "{colors.cream}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    padding: "9px 18px"
  button-sm:
    padding: "6px 12px"
  chip:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink-2}"
    rounded: "{rounded.pill}"
    padding: "3px 10px 3px 8px"
  chip-ready:
    backgroundColor: "{colors.ready-soft}"
    textColor: "{colors.ready}"
  chip-gap:
    backgroundColor: "{colors.gap-soft}"
    textColor: "{colors.gap}"
  chip-adviser:
    backgroundColor: "{colors.adviser-soft}"
    textColor: "{colors.adviser}"
  chip-ink:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.cream}"
  chip-doc:
    backgroundColor: "{colors.paper-2}"
    textColor: "{colors.ink}"
  slab:
    backgroundColor: "{colors.slab}"
    textColor: "{colors.cream}"
    rounded: "{rounded.lg}"
    padding: "30px 32px 28px"
  card:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "14px 16px"
  input:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "8px 10px"
  input-focus:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
  segmented:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    padding: "3px"
  segmented-selected:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.cream}"
  dropzone:
    backgroundColor: "{colors.card}"
    textColor: "{colors.muted}"
    rounded: "{rounded.md}"
    padding: "16px"
  footer:
    backgroundColor: "{colors.slab}"
    textColor: "{colors.cream-2}"
    padding: "10px 28px"
---

# Design System: NoticeGuard

## Overview

**Creative North Star: "The Case File on a Desk"**

NoticeGuard reads like a legal case file laid open on warm paper: one continuous cream surface, a dark charcoal verdict slab sitting on it like a bound cover, and a chain panel to the right that fills in when a sentence is clicked. There are no modals, no same-size stat cards, no transcript. Structure comes from hairlines and type, not from boxes; the only heavy objects on the page are the two charcoal slabs (verdict and draft) and the footer bar that pins the disclaimer.

Colour is disciplined to a single question: what is the verdict? Everything is ink on paper until a verdict is known, at which point one accent (green for ready, amber for gap, oxblood for adviser) appears on the slab glyph, the status chips, and the highlighted quote. Words carry the verdict; colour underlines it. The cream ground (#F3F0EA) was pinned by the user's brief, as were the serif display, charcoal rounded cards, and pill buttons; the build honours all four.

Density is that of a working tool, not a marketing page: 15px sans body, 13.5px tables, 12px chips, hairline separators at 1px, and a three-column desk that stays sticky on desktop and stacks in reading order on narrow screens.

**Key Characteristics:**
- One warm paper surface (#F3F0EA) with 1px hairline dividers; no borders heavier than 1px anywhere.
- Two charcoal slabs (verdict and draft) are the only high-contrast objects; they carry the only lifted shadow.
- Exactly one accent per verdict; nothing else on the page is chromatic.
- Source Serif 4 for headings, stage names, quotes, and drafted prose; system sans with tabular numerals for all UI.
- Pill buttons and pill chips; rounded corners scale 8 / 14 / 22px by object weight.
- Motion is short (160-320ms), exponential ease-out, and only ever responds to an action.

## Colors

A monochrome warm-grey ramp from paper to ink, with three verdict accents that are each paired with a soft tint for chip and highlight backgrounds.

### Primary
- **Ink** (`{colors.ink}`): all body text, headings, primary button fill, focus rings, border on emphasised cards (consequence box, diff banner, active route). Ink is also the default `--accent` before any verdict is known.
- **Charcoal Slab** (`{colors.slab}`): background of the verdict slab, the draft slab, and the sticky footer. A shade darker than ink so slab text (cream) is not the same object as page text inverted.
- **Slab Hover** (`{colors.slab-2}`): hover state for clickable sentences inside the draft slab; active sentences step one further to #2E2B26.
- **Slab Hairline** (`{colors.slab-hair}`): 1px borders on dark ground (cite pills, footer "more" button).

### Secondary (verdict accents)
- **Ready Green** (`{colors.ready}`) with **Ready Tint** (`{colors.ready-soft}`): "Evidence ready". Glyph disc on the slab, ready chips, "yes" run votes, highlight underline in the document view.
- **Gap Amber** (`{colors.gap}`) with **Gap Tint** (`{colors.gap-soft}`): "Evidence gap". Same roles, plus the 1px left rule on each "gap fix" item and "unclear" run votes.
- **Adviser Oxblood** (`{colors.adviser}`) with **Adviser Tint** (`{colors.adviser-soft}`): "Needs an adviser". Same roles, plus every error state: the error box, "conflicting" and "extraction rejected" chips, failed file rows, the withheld-draft notice, "no" run votes, and the remove-file hover.

### Neutral
- **Paper** (`{colors.paper}`): page ground, top bar, rail, default chip fill. Pinned by the user's brief.
- **Paper 2** (`{colors.paper-2}`): hover fill for rows and sentences, table header band, deadline pills, document chips, skeleton bars.
- **Paper 3** (`{colors.paper-3}`): declared as the third paper step; reserved for deeper recesses, used sparingly.
- **Card** (`{colors.card}`): the near-white fill for inputs, dropzone, evidence table, route cards, rule cards, votes, consequence box, and the document view. Sits one step lighter than paper so recessed containers read as sheets placed on the desk.
- **Hairline** (`{colors.hair}`): every 1px divider, input border, chip border, rail track.
- **Ink 2** (`{colors.ink-2}`): secondary text (route descriptions, table keys, deadline text, field labels), rail dots for past stages, bullets.
- **Muted** (`{colors.muted}`): tertiary text (ledes, captions, table headers, chain step labels, sources).
- **Cream** (`{colors.cream}`): text on charcoal. Same hex as Paper; kept as a separate token so slab text and page ground can diverge later without touching either.
- **Cream 2** (`{colors.cream-2}`): secondary text on charcoal (slab meta line, draft header, cite pills, footer), plus dashed dropzone border and line numbers on light ground.
- **Accent Soft (ink)** (`{colors.accent-soft-ink}`): the neutral highlight before a verdict exists: active sentence and active table row background, and `--accent-soft` at rest. Text selection uses the neighbouring #D8CDB8.

### Named Rules
**The One Accent Rule.** `body[data-verdict]` sets `--accent` and `--accent-soft` once, page-wide, to the verdict's colour pair; before a verdict they resolve to ink and the neutral soft tint. Every chromatic element (slab glyph, status chips, document highlight, gap rule) draws from that pair or from the three fixed verdict tokens. No fourth hue exists.

**The Words First Rule.** A verdict is always a sentence plus a drawn glyph; the accent underlines it. Never signal status by colour alone (see PRODUCT.md accessibility commitment).

**The Oxblood Is Also Error Rule.** The adviser accent doubles as the error colour. Do not introduce a separate red.

## Typography

**Display Font:** Source Serif 4, variable (opsz, wght, italic), self-hosted under static/fonts/ (with Georgia, Times New Roman fallback)
**Body Font:** system-ui sans stack (-apple-system, Segoe UI, Roboto, Helvetica, Arial)
**Label/Mono Font:** none; the sans carries labels, and numerals are tabular everywhere (`font-variant-numeric: tabular-nums` on body).

**Character:** An editorial serif does the talking (verdict heading, stage names, wordmark, quoted clauses, drafted statement) and a quiet system sans does the work (forms, tables, chips, meta). Italic serif is the register for quotes and for the second line of the verdict heading.

### Hierarchy
- **Display** (500, 2.75rem, 1.08, -0.015em): the verdict heading inside the slab, max 24ch, second clause in italic 400. Drops to 2.2rem below 1400px and 1.8rem below 640px. The empty-state heading uses 2.2rem / 1.12.
- **Headline** (500, 1.35rem, 1.2): section h2 ("The claim in plain language"); panel h2 is 1.2rem. Wordmark is 1.55rem / -0.01em with a 12px sans tagline.
- **Title** (500, 1.05-1.15rem, 1.15-1.25): h3, rail stage names (1.15rem), route titles (1.1rem), rule ids. Route numerals are 1.5rem serif in ink-2.
- **Quote** (400 italic, 1.35rem, 1.35): the statement block with a 1px ink left rule; chain sentence-text is 15.5rem-equivalent (15.5px) upright serif; table quotes and vote quotes are 12.5px italic serif in muted.
- **Body** (400, 15px, 1.5): default UI text. Result prose is 15.5px / 1.6 at max 72ch; slab explanation is 17px / 1.5 in #E4DFD5 at max 62ch; draft body is 16.5px / 1.6 serif at max 70ch.
- **Label** (600, 11.5-12.5px, uppercase where structural): chain step labels ("Document", "Quote", "Rule") at 11.5px / .08em uppercase with a trailing hairline; table headers at 12px / .04em uppercase; the "You are here" marker at 11.5px / .06em uppercase in an ink pill; field labels at 12.5px / .01em, sentence case.
- **Caption** (400, 12-13.5px, 1.35-1.5): ledes (13.5px muted), captions and sources (12-12.5px muted), footer (12.5px).

### Named Rules
**The Serif Speaks, Sans Works Rule.** Serif is reserved for what a reader would quote or read aloud: headings, stage names, clauses, the drafted statement, rule ids. Everything operational (labels, chips, tables, buttons, meta) is sans. A serif button or a sans headline is a defect.

**The Tabular Numerals Rule.** Dates, line numbers, run counts, and deadlines align because tabular numerals are set at the body level; do not override to proportional.

## Layout

One flex column: sticky top bar (14px 28px, hairline below, z 20), the process rail (22px 28px 18px, five equal columns on a single 1px track with 9px dots), the three-column work area, and a sticky charcoal footer (10px 28px, z 20). Page gutter is 28px; below 640px it is 16px.

The work grid is `320px / minmax(0, 1fr) / 420px` with a 28px gap and 26px top / 40px bottom padding. Left (inputs) and right (chain) columns are sticky at top 64px, capped at `100vh - 64px - 58px` and scroll internally; the right column is separated by a 1px hairline and 24px padding. At 1400px the side columns narrow to 290 / 360px. At 1100px the grid collapses to one column, columns lose stickiness, the rail becomes two columns and drops its track line, and the chain panel gains a top hairline. At 640px the rail is one column, slabs shrink to 22px 20px padding and 14px radius, the footer disclaimer clamps to one line behind a "more" toggle, and route/component grids simplify.

Vertical rhythm inside a column is hairline-separated sections at 22px padding, 12px below an h2, and 10-14px between list items. Prose measures: 72ch results, 62ch slab explanation, 60ch statement, 34ch chain empty-state, 28ch rail risk copy. No max-width container: the desk is full-bleed at 1920.

## Elevation & Depth

Hybrid, weighted toward tone. The paper world is flat: depth is conveyed by the Card fill (#FBFAF7) sitting one step lighter than Paper inside a 1px hairline, and by Paper 2 on hover. Shadows belong to the two charcoal slabs (always lifted) and to primary buttons on hover. Focus and active states use flat rings (box-shadow spread with no blur), which read as outlines, not lift.

### Shadow Vocabulary
- **Rest** (`box-shadow: 0 1px 2px rgba(26,25,23,.06), 0 2px 8px rgba(26,25,23,.06)`; `--shadow-1`): primary button on press.
- **Lifted** (`box-shadow: 0 6px 18px -6px rgba(26,25,23,.28), 0 2px 6px rgba(26,25,23,.08)`; `--shadow-2`): the verdict slab, the draft slab, the benchmark dialog, and the primary button on hover together with a 1px upward translate.
- **Inset bevel** (`box-shadow: 0 1px 0 rgba(255,255,255,.08) inset`): primary button at rest, a hairline of light along the top edge.
- **Sentence halo** (`box-shadow: 0 0 0 4px <fill>`): hover / active fill extended 4px beyond a clickable sentence or table quote so inline text reads as a soft block; Paper 2 on hover, Accent Soft (ink) when active, Slab 2 / #2E2B26 on the draft.
- **Focus ring** (`outline: 2px solid var(--ink); outline-offset: 2px; border-radius: 4px`): every focusable element. Inputs use `border-color: var(--ink)` plus `0 0 0 3px rgba(26,25,23,.08)` on focus instead of the outline.
- **Current-stage ring** (`0 0 0 4px var(--paper), 0 0 0 5px var(--ink)`): the rail dot for the current stage.
- **Highlight pulse** (`0 0 0 0` to `0 0 0 10px` of `color-mix(in srgb, var(--accent) 45%, transparent)`, 900ms, once): the quoted span when the chain panel opens.

### Named Rules
**The Slabs Float, Paper Lies Flat Rule.** Only charcoal objects and a hovered primary button carry a blurred shadow. Light containers get a hairline and a lighter fill, never a shadow.

## Shapes

Softly rounded, scaled by object weight: 4px for focus rings and inline sentence highlights, 8px (`--r-sm`) for inputs, file rows and votes, 14px (`--r-md`) for cards, dropzone, tables, routes, and the docview, 22px (`--r-lg`) for the two slabs and the benchmark dialog, and a full pill (`999px`) for every button, chip, cite, deadline, segmented control, and the "You are here" marker. Rounded corners never exceed 22px, and slabs step down to 14px below 640px.

Borders are always 1px: solid hairline by default, solid ink for emphasis (consequence box, diff banner, statement left rule, hovered or active route), dashed Cream 2 for the dropzone and "missing" chips, dashed hairline between fact rows. Glyphs are drawn SVG symbols at 14px inline, 12px in chips, 22px inside a 40px accent disc on the slab. Scrollbars are thin, drawn from the palette (#C9C2B6 thumb with a 3px paper gutter).

## Components

### Buttons
Slick pills, ink on paper, that lift on hover.
- **Shape:** full pill (999px), 14px / 500, 9px 18px padding, inline-flex with an 8px icon gap; `.sm` variant 13px at 6px 12px.
- **Primary:** ink fill, cream text, 1px ink border, inset top bevel. Hover: fill goes #000, lifts 1px, gains the Lifted shadow. Active: returns to rest with the Rest shadow. Disabled: 55% opacity, `cursor: progress`, no lift; a 14px currentColor spinner (2px ring, 0.8s linear) shows when `.loading`.
- **Secondary:** transparent with a 1px ink border and ink text; hover inverts to ink fill / cream text. Used for "Load Maya" / "Load Leo" and the check action.
- **Ghost:** transparent with a hairline border; hover swaps to an ink border on Paper 2 with no lift or shadow.
- **On-dark:** cream fill and border with ink text for buttons inside slabs (copy draft); hover goes white.
- **Transitions:** transform, box-shadow, background, colour, border at 160ms with `cubic-bezier(.16,1,.3,1)`.

### Chips
Small sans pills with a 12px drawn glyph; the primary carrier of status words.
- **Style:** 12px / 500, 3px 10px 3px 8px, 1px hairline border, Paper fill, Ink 2 text, 6px glyph gap, no wrapping.
- **Verdict variants:** `ready` / `gap` / `adviser` set text to the accent, fill to the accent tint, and border to `color-mix(in srgb, <accent> 35%, var(--hair))`.
- **Other variants:** `ink` (inverted ink pill), `doc` (Paper 2 fill, ink text, document glyph, 7px gap; used for filenames), `stated` (Paper 2 fill: "Stated by you"), `neutral` (muted text), `missing` (dashed border, muted), `conflicting` (oxblood text and border), `unavail` (60% opacity, italic: "when reached"). Cite pills inside the draft are a dark-ground sibling: 11.5px, 1px 8px, Slab Hairline border, Cream 2 text.

### Cards / Containers
Sheets on the desk: lighter than the paper, edged with a hairline.
- **Corner Style:** 14px (`--r-md`); 8px for the smallest rows (files, votes).
- **Background:** Card (#FBFAF7); Paper 2 for table header bands.
- **Shadow Strategy:** none at rest (see Elevation). Active route gets a flat 3px Paper 2 ring; the consequence box, diff banner, and benchmark caption use a 1px ink border instead of a shadow.
- **Border:** 1px hairline; 1px ink for emphasis; 1px oxblood for error and withheld states.
- **Internal Padding:** 14px 16px for routes, consequence, diff; 10px 12px for rule cards; 8px 10px for votes; 10px 14px for the rejected-spans disclosure.
- **Evidence table:** 13.5px, hairline row dividers, uppercase muted headers on a Paper 2 sticky band, serif 15px group rows, hover Paper 2, active Accent Soft; the italic serif quote under a value appears only on hover or active.

### Inputs / Fields
Quiet, paper-coloured, and ink-focused.
- **Style:** 1px hairline border, Card fill, 8px radius, 8px 10px padding, inherits 15px sans; labels 12.5px / 600 in Ink 2 with a 5px gap; captions 12px muted. Textareas start at 72px and resize vertically.
- **Hover:** border to Cream 2. **Focus:** border to ink with a 3px 8%-ink ring, no outline.
- **Radio / checkbox:** native controls with `accent-color: ink`, 15px, laid out as `.choice` rows with a 12.5px muted sub-line.
- **Segmented control:** a 3px-padded pill track on Card fill with a hairline; the checked label becomes an ink pill with cream text; keyboard focus draws the standard ink ring on the label.
- **Dropzone:** dashed Cream 2 border, 14px radius, 16px centred padding, muted 13.5px text; hover / drag-over turns the border ink, fill Paper 2, text ink. File rows below are 8px-radius Card rows with a 6px-radius native select and a muted remove glyph that turns oxblood on hover; failed rows get an oxblood border.
- **Error:** oxblood text on Adviser Tint with a 1px oxblood border, 14px radius, 12px 14px.

### Navigation
- **Top bar:** sticky, Paper fill, hairline below, 14px 28px; serif wordmark (1.55rem) with a 12px sans tagline; right side holds secondary small pills and a 14px Ink 2 text link with a 1px underline offset .18em. Wraps below 640px.
- **Process rail:** five serif stage names on one hairline track; dots are 9px rings (past: Ink 2 fill; current: ink with the Current-stage ring; future: Ink 2 text; idle: muted with hairline dot). The current stage carries a "You are here" ink pill; future stages show 12.5px muted risk copy at 28ch and a verdict chip per stage. Deadline pills sit below in Paper 2.
- **Footer:** sticky charcoal bar, Cream 2 12.5px text, cream links, 20px gaps; on phones the disclaimer clamps to one line with a hairline "more" pill.

### Verdict Slab (signature)
A charcoal bound cover on the paper: `{colors.slab}` fill, cream text, 22px radius, 30px 32px 28px padding, Lifted shadow. Headline grid is a 40px accent disc (white 22px glyph, `slab.ready|gap|adviser` sets the disc colour) beside the 2.75rem serif heading whose second clause is italic. Below: a 17px explanation in #E4DFD5 at 62ch, then a 12.5px Cream 2 meta line (stage, step, rules version). On arrival it settles in: scale 1.015 to 1, blur 3px to 0, opacity .6 to 1, 320ms ease-out (`.enter`); disabled under reduced motion.

### Draft Slab (signature)
Same charcoal material at 26px 30px: an italic serif 13.5px Cream 2 header, a serif 16.5px / 1.6 body in 10px-spaced sentences with inline cite pills, a withheld-notice variant with a 1px oxblood border and #F2A3AE text, and a Cream 2 footer with a "copied" confirmation in #8FD3A5.

### Chain Panel (signature)
The right column fills top-down when a sentence is clicked: hairline-separated steps (14px padding) each opened by an uppercase 11.5px muted label with a trailing hairline (Document, Quote, Fact, Rule, Mapping, Sentence, Status), a document-view box (Card fill, 14px radius, 12.5px text, 300px max height, 34px right-aligned line numbers in Cream 2) in which the quoted span is `<mark>` on Accent Soft with a 1px inset accent underline and a one-shot accent pulse; fact rows with dashed dividers; rule cards; and vote pills (`yes` green, `no` oxblood, `unclear` amber). The panel reveals with a 240ms 6px rise; the version line "Rules version 0.1.0" closes it.

### Sentence (signature)
Any traceable sentence, in prose or in the draft, is a `role="button"` span with a 4px radius that gains a Paper 2 halo on hover and an Accent Soft halo when active; inside the draft slab the halo is Slab 2 / #2E2B26. Table rows behave the same way.

## Do's and Don'ts

### Do:
- **Do** keep every divider, border, and rule at 1px; use fill (Card, Paper 2) and ink-coloured borders for emphasis, not weight.
- **Do** route every chromatic colour through the three verdict pairs; set `body[data-verdict]` and let `--accent` / `--accent-soft` cascade rather than hard-coding a verdict colour into a new element.
- **Do** pair every status colour with a word and a drawn SVG glyph (the `i-check` / `i-gap` / `i-person` symbols) so the status survives without colour.
- **Do** set headings, stage names, quotes, and drafted text in Source Serif 4 at weight 500 (400 italic for quotes) and everything operational in the system sans.
- **Do** use the pill for buttons, chips, and segmented controls, 14px radius for sheets, 22px for charcoal slabs.
- **Do** keep motion between 160ms and 320ms on `cubic-bezier(.16,1,.3,1)` and only in response to a user action; honour `prefers-reduced-motion` by zeroing durations.
- **Do** honour `[hidden] { display: none !important }`: toggle the attribute, never fight it with a display rule.
- **Do** hold the light colour scheme regardless of OS preference (`color-scheme: light` is forced); there is no dark theme.

### Don't:
- **Don't** add a fourth accent hue, a separate error red, or any colour on a chip, glyph, or highlight that is not one of the three verdict pairs.
- **Don't** put a blurred shadow on a light container; only charcoal slabs and a hovered primary button lift.
- **Don't** use emoji or icon fonts; glyphs are inline SVG symbols with `currentColor` strokes.
- **Don't** set the wordmark, headings, or quotes in the sans, or buttons, chips, and table text in the serif.
- **Don't** introduce modals, same-size stat cards, or a chat transcript into the tool surface; the desk is one continuous page (the benchmark page's native `<dialog>` for raw JSON is the only overlay and stays there).
- **Don't** use gradients as material; the only gradient in the build is the loading skeleton's shimmer, which is a transient state, not a surface.
