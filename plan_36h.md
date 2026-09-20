# FundSpine — 36-Hour Plan

**Written:** Sat Sep 19, 2026, 10:00 PM ET · **Revised:** 10:15 PM after review
**Freeze:** Sun Sep 20, 8:30 PM ET
**Submit:** Mon Sep 21, 9:00 AM ET
**Call with Nik:** Wed Sep 23

Wall clock is 35 hours. Real working time is **~14.5 hours**. This document is the
authoritative scope. It supersedes the 72-hour spec, which stays in the repo as the
architecture of record — you will point at it on the call for what you *would* build.

---

## 1. The three pain points (re-verified Sep 19)

**P1 — White-label delivery is scaling faster than operational capacity.**
One 9-figure flagship client just launched and "~6 more clients that have signed or at
the finish line." Each partner is promised white-labeled proposals, branded materials,
institutional-grade IC memos, and custodian reporting. Every one of those is currently a
human assembling documents.

**P2 — Diligence and ongoing monitoring across ~13,000 funds with no data
infrastructure.** Tory screens 13,000 funds for the top 1%, then runs rolling
correlation, position-level risk, and a risk overlay. The screening is a one-time
filter. The monitoring is forever, and fund managers restate numbers.

**P3 — No engineering function. Non-engineers are building the automations.**
The Chief of Staff spec asks a non-engineer to "identify, design, and implement agentic
systems." The GTM spec asks a marketer to "architect scalable systems."

---

## 2. Three demo moments, one per pain point

This is the whole scope filter. **If a feature does not serve one of these three
moments, it is cut.** No exceptions, no "it's only twenty minutes."

**Moment 1 → P1.** One validated fund record renders two partner documents. Different
logo, different colour, different tone, different disclosure block. *Identical numbers.*
The line: "Your seventh client is a row in a config table, not seven times the work."

**Moment 2 → P2.** Ingest the Q2 document. The system detects that Q1 NAV was restated
and that the management fee changed to 175bps effective April 1. Partner-facing
documents are **refused**. The internal IC memo still renders, showing the conflict and
both values. The line: "This is monitoring, not onboarding. The failure mode isn't a bad
parse, it's a confidently correct document built on a number that changed."

**Moment 3 → P3.** The eval scorecard, and CI failing on a regression you introduced on
purpose. The line: "This is what an engineering function gives you that a prompt library
can't — the system tells you when it got worse, before a client does."

---

## 3. Scope: in, out, stretch

### IN — build all of this

| Area | Scope |
|---|---|
| Tables | **9**: fund, document, extraction_run, fact, fund_period_metrics, terms, partner, drift_event, artifact |
| Golden docs | **3** |
| Validation rules | **2**: R001 fee bridge, R004 citation valid |
| Drift detectors | **2**: D101 restatement, D103 terms change — both fire from doc 3 |
| Partners | **2**, single-fund commentary each |
| Guard | **Full** — G1 no-digits, G2 bad marker, G3 cross-tenant, G4 missing disclosure |
| Eval | Field-level scorecard, baseline diff, non-zero exit on regression |
| Telemetry | 5 spans, real OTel SDK, GenAI semantic conventions, file exporter |
| Costs | `make costs` prints a **rate** plus one stated-assumption extrapolation |
| Documents in | **HTML with explicit page divisions**, not generated PDFs |
| Output | Styled HTML |
| CI | Deterministic layers only — no API key. See section 3a. |

### CUT — say each of these out loud in the Loom

- **Next.js / TypeScript UI.** Deliberate. The hard part is the pipeline.
- **Auth, RLS, user accounts.** Tenant scoping is enforced in the session layer and the
  guard; database-level RLS is the production step.
- **Manager table, sleeves, multi-fund allocations.** One fund, two partners. Sleeves are
  a join table away and add no new failure mode.
- **R003 compounding, R005 weight-sum.** The rule *engine* is the artifact; two rules
  demonstrate it.
- **Page-break-split tables, footnote-contradicts-table.** These are the two hardest
  extraction cases and they are listed in the README as known gaps with the approach for
  each. Naming a limitation precisely is stronger than pretending it isn't there.
- **Jaeger container.** Spans go to a file. Swapping the exporter for Cloud Trace is a
  config line, and say so.
- **PDF generation and PDF parsing.** Golden documents are generated as HTML with explicit
  page divisions, and extraction reads that same text. Ground truth becomes an exact
  substring match against a string you control, `page_no` is whatever you assigned, and the
  PyMuPDF dependency disappears. Print one to PDF for appearance in the video if you like,
  but never extract from it. A real-PDF adapter with text normalization is a README line;
  nobody on the call will ask whether the bytes were a PDF, they will ask whether the quote
  is verifiable.
- **Real manager documents.** Synthetic on purpose — using a real fund letter without
  permission is a compliance smell, and synthetic gives you exact ground truth.
- **Agent frameworks.** Explicit control flow. Be ready to defend this; it's a real
  opinion, not laziness.
- **PDF output.** HTML renders, prints, and screenshots fine.

### PROMOTED — build this if you are anywhere near schedule at 6:00 PM Sunday

- **`POST /ask` with numeric refusal.** Answers narrative questions from embedded prose with
  page citations, and **refuses the retrieval path** for any question asking for a return,
  fee, NAV, Sharpe, or lockup — answering instead from the validated record via SQL, labelled
  "resolved from validated record, not retrieval."

  This was filed as a stretch in the first draft and that undersold it. The job description
  asks explicitly for RAG systems and LLM integration, and this endpoint is the one artifact
  that turns your thesis from a claim into executable behaviour: *the system knows which
  questions retrieval is allowed to answer.* Every other candidate will show a RAG demo that
  happily answers "what was the net return" from a vector search.

  **Build it even in stub form** — hardcoded keyword routing, three embedded prose chunks, no
  reranking. The refusal path is the whole point; the retrieval quality is not. 30 minutes.

---

## 3a. The CI decision — settle this now, not Monday

The first draft of this plan contradicted itself: it said CI runs on cached fixtures *and*
that you break a prompt to make CI fail. Those can't both be true. Resolved as follows, and
this goes in the README verbatim.

**CI gates the deterministic layers only.** Rules, binder, guard, domain validators, and a
scorecard diff against the committed `baseline.json`. No API key, no LLM calls, no flake,
runs in under a minute.

**The regression demo splits in two, and each half goes where it belongs:**

- **Break a rule or the guard** → CI fails. This is deterministic, so it fails reliably.
  **This is your screenshot.**
- **Degrade an extraction prompt** → run `make eval` locally and show the scorecard diff in
  the terminal: field recall dropping, citation validity dropping. This is the more
  interesting failure and it belongs on camera live, not in a CI log.

Say the boundary out loud in the video: "CI gates everything deterministic on every push.
The extraction eval costs money and needs a key, so it runs on demand and the scorecards are
committed — here's the diff." That is exactly how you would run it in production, and
knowing where that line sits is the senior signal.

---

## 4. The three golden documents

Fund: **Meridian Systematic Macro Fund, Class A**, manager Meridian Capital Management,
systematic global macro / CTA, firm AUM $480M, inception March 2018.

**doc_1 — Clean Q1 2026 tearsheet.** Monthly returns Jan/Feb/Mar, YTD, NAV, 36-month
Sharpe, max drawdown. Terms block: 150bps management, 20% performance, 500bps hurdle,
high water mark, 12-month lockup, 90-day notice. ~200 words of strategy narrative. All
arithmetic internally correct. *This is the happy path and the source of truth.*

**doc_2 — Q1 2026 monthly letter, seeded arithmetic error.** Stated net return does not
equal gross minus stated fees. Off by 40bps. *This is what R001 catches.*

**doc_3 — Q2 2026 tearsheet, does double duty.** Restates the Q1 NAV to a different
value than doc_1 reported, **and** states the management fee as 175bps effective April 1.
*This single document triggers both drift detectors and produces Moment 2.*

**Format: HTML, not PDF.** Each document is one HTML file with explicit page divisions
(`<section class="page" data-page-no="1">`). The ingest layer reads the HTML, strips tags
per page, and hands the extractor `[{page_no, text}]` — the same shape a PDF loader would
produce, so the interface is honest and swapping in a PDF adapter later changes one module.

**Non-negotiable:** ground truth is **derived during generation**, not hand-written. As
the script emits each value it records the exact rendered string and the page it landed on,
and writes that into `doc_N.truth.json`. Because you control the text end to end, citation
validity is an **exact substring match** rather than a fuzzy one. If Cursor hardcodes a
truth file, reject the diff.

On camera, say the boundary plainly: "These are synthetic HTML documents so I have exact
ground truth. Real manager documents are PDFs and scans, and that's a text-extraction and
normalization layer in front of this — it's the first thing I'd build with real documents in
front of me." That is a stronger position than a fragile PDF round-trip, because the part
you are claiming works, provably works.

---

## 5. Schedule

### Block A — Saturday 10:00 PM – 12:00 AM (2.0h)

Scaffold, schema, migration, validators.

1. Prompt 1 from `cursor_prompts.md` (the Docker version — you have Docker). `make up`.
2. Prompt 2, but tell Cursor: **9 tables only** — drop manager, partner_sleeve,
   sleeve_allocation. Fold `manager_name` and `strategy_family` into `fund`.
3. `make migrate`. Confirm tables exist.
4. Drop in `tests/test_domain.py`. **Tonight only the Fact tests and the pairing
   tests** — run `pytest tests/test_domain.py -x -q -k "not terms"`. That's 17 tests.
   Terms tests wait for Block B.
5. Write the three validator bodies yourself. Generic pairing check off `model_fields`.

**Gate:** `pytest -k "not terms"` green. **Commit:** `feat: domain models, schema, validators`
**Then stop.** Do not start the extractor at midnight. Sleep is load-bearing tomorrow.

### Block B — Sunday 8:00 AM – 12:30 PM (4.5h)

The pipeline end to end, however rough.

1. Prompt 3, trimmed to **3 HTML documents** as specified above. Open all three in a
   browser and read them. (45 min — the HTML change buys you this)
2. Prompt 4, ingest: read HTML, split by page section, strip tags, sha256, idempotent
   re-ingest. No PyMuPDF. (20 min)
3. Prompt 5, extractor. (75 min)
4. Terms tests green. Prompt 6, **R001 and R004 only** — write R001 by hand after
   deciding the tolerance. R001 must resolve terms **as-of the period**, not read a
   constant. (60 min)
5. Prompt 7, eval harness. (45 min)

**Gate — 12:30 PM, the most important gate in this plan:** `make ingest && make eval`
prints a per-field scorecard. **The numbers do not need to be good. They need to exist.**
If there is no scorecard at 12:30, go to the triage ladder in section 6 before eating.

**Commit:** `feat: ingest, cited extraction, rule engine, eval harness`

### Block C — Sunday 1:15 PM – 3:00 PM (1.75h)

Accuracy. Read the failures, fix the prompts, create `prompts/v2/` — never edit `v1`.

Targets: citation validity **100%**, required-field recall **≥90%**, R001 fires on doc_2.

**Save the scorecard from before this block.** You show the improvement on camera.
**Commit** `fix: extraction accuracy pass`, then commit `baseline.json`.

### Block D — Sunday 3:00 PM – 6:00 PM (3.0h)

Rendering and the guard. This produces Moment 1.

1. Prompt 8, plan + binder + templates. (60 min)
2. Prompt 9, constrained prose. (30 min)
3. **Prompt 10, the guard — now the strong version.** The prose model is **forbidden from
   emitting digits at all.** Every number enters the document through `f("field.path")` in
   the template; the model writes sentences with `[[fact:<uuid>]]` markers where a figure
   belongs. Non-fact quantities get spelled as words ("forty liquid futures markets") or
   supplied as facts.

   G1 becomes: **any bare digit in model output is a violation.** One regex, no tolerance
   logic, no equivalence table, no ignore-list — and you never spend a minute debugging
   whether "2026" is a hallucinated number. The claim on camera gets simpler too: not "we
   check the model's numbers," but *"the model is not permitted to produce a number."*

   Keep the formatting-tolerant comparison you wrote for the binder's own tests — it still
   earns its place, and it's the function to talk about when asked how you'd handle a model
   that ignores the constraint. (45 min — cheaper than the tolerant version)
4. Seed two partners: Apex Wealth Partners (warm, navy) and Ridgeline Family Office
   (terse, slate). Single fund each, no sleeves. (30 min)

**Gate:** two branded HTML documents, same numbers, different voice. Unbound numerals: 0.
**Commit:** `feat: fact-bound rendering with prose guard, dual-partner output`

### Block E — Sunday 6:00 PM – 7:15 PM (1.25h)

Drift. This produces Moment 2.

Prompt 11, D101 + D103 + blocking. Ingest doc_3 and verify: Q1 NAV superseded, fee row
closed and reopened at 175bps, partner render **refused** with a readable reason, IC memo
still renders showing both values.

**Commit:** `feat: drift detection with artifact blocking`

### Block F — Sunday 7:15 PM – 8:15 PM (1.0h)

Costs, then README. Both are good tired-brain work — mechanical, verifiable, no narration.

1. Prompt 12, trimmed: **5 spans** — extract.llm, validate.rules, drift.evaluate,
   render.prose, render.guard. Real OTel SDK, GenAI semantic conventions, file exporter,
   no Jaeger. Then `make costs`, which must print a **rate plus one extrapolation** — see
   section 7. (30 min)
2. Prompt 15, README. **You write two sections yourself**: the thesis paragraph and "What I
   did not build, and why." Those are the two a reader judges you on. (30 min)

**CODE FREEZE 8:15 PM.** Anything unfinished becomes a README line. That is a strength.

### Block G — Sunday 8:15 PM – 9:00 PM (0.75h)

CI gate — Prompt 13, deterministic layers only per section 3a. Break a rule on purpose,
let CI fail, **screenshot it**, revert. Also deterministic, also fine when tired.

**Commit:** `ci: deterministic regression gate` — then **stop for the night.**

### Block H — Sunday 9:00 PM – 9:30 PM (0.5h) — THE INSURANCE TAKE

Record one complete pass, however tired you sound. Do not edit it. Do not rewatch it
looking for flaws.

**Why this exists:** at 9:30 PM Sunday you will have a submittable artifact in hand. Every
decision Monday morning then becomes an upgrade rather than a rescue, and nothing that goes
wrong before 9 AM can leave you with nothing to send.

### Block I — Monday 7:00 AM – 9:00 AM (2.0h)

1. **Re-record, rested.** (40 min) You will be noticeably better, and you'll be narrating
   code you last touched twelve hours ago rather than four minutes ago — which is closer to
   how you'll discuss it on Wednesday anyway. **Keep Sunday's take until the new one is
   uploaded and you have watched the first thirty seconds.**
2. Read the README once as a stranger. Fix the three worst things. (20 min)
3. **Submit the Ashby application by 9:00 AM.** This is the actual deliverable. Everything
   above is evidence attached to it.

---

## 6. Triage ladder

At each checkpoint, if you are behind, cut in this order. Decide fast and move on — the
cost of deliberating is higher than the cost of cutting.

| Checkpoint | If behind, cut |
|---|---|
| Sat 12:00 AM | **Test coverage, not models.** Make the 8 Fact-invariant tests green, defer the pairing and Terms tests to Block B. The schema ships whole. |
| Sun 10:00 AM | **The second partner.** One branded document plus the partner config table on screen, and you narrate what a second row changes. Moment 1 weakens but survives. |
| Sun 12:30 PM | **OTel spans.** Keep `make costs` reading token counts straight off `extraction_run`. You still get the unit-economics number, which is the part Tory cares about. |
| Sun 3:00 PM | **doc_2.** Seed the fee-bridge violation directly into the fact table to demonstrate R001. Honest, and you say so on camera. |
| Sun 6:00 PM | **Drift blocking.** Detect and log, don't block. Moment 2 becomes "here's what it caught" rather than "here's what it refused." |
| Sun 7:15 PM | **The CI gate.** Show the scorecard diff locally in the terminal instead — which section 3a already has you doing for the extraction half. |
| Sun 8:15 PM | **Polish.** Record the insurance take on whatever exists. Shipping beats finishing. |

**Never cut, at any hour:** citation-bound facts, the guard, the eval scorecard, and
**Terms**. The first three *are* the submission.

Terms earns its protection: it is two dates and six integer columns, and it is load-bearing
for two headline features. D103 is half of Moment 2, and R001 is only interesting because it
resolves the fee **in force during the period being reported** instead of reading a constant.
Hardcode the fees and your most domain-specific rule collapses into arithmetic against a
literal — which is exactly the thing that stops sounding senior the moment someone asks a
follow-up. Cheap to build, expensive to lose.

---

## 7. Loom shot list — 6 minutes, hard cap

**0:00–0:45 — The hypothesis.** Name the constraint as a hypothesis, once, then move on.
> "You've just launched your largest client and have about six more signed. My assumption
> is that the thing that binds first isn't parsing documents — it's that every one of
> those partners needs branded, defensible client materials, and the numbers inside them
> have to be right and traceable. I built against that assumption. Tell me where I'm wrong."

**0:45–1:30 — The thesis.** One diagram. Document → cited facts → validated record →
artifact.
> "Retrieval serves prose. SQL serves numbers. No figure reaches a client document except
> through a fact ID with a page and a quote behind it. That's a schema constraint, not a
> convention."

**1:30–3:00 — Moment 1.** Two partner documents side by side. Same numbers, different
brand and voice. Then open the provenance appendix and click through to a page and quote.

**3:00–4:30 — Moment 2.** Ingest doc_3 live. Show the drift events. Show the partner
render **refuse**, and the IC memo render anyway with both values visible.
> "A confidently correct document built on a number that changed is worse than no
> document. So the system refuses, and escalates to a human."

**4:30–5:30 — Moment 3.** The scorecard. The before-and-after from Block C. The CI
failure screenshot.
> "A green board proves nothing. Here's the eval catching me being wrong."

**5:30–6:00 — Costs and the cut list.** Give the rate, then **immediately do the
multiplication out loud with the assumptions stated.** A raw figure off three documents
invites "sure, at three documents" — the extrapolation is the number Tory is already
computing in his head, and showing you did it with explicit assumptions is worth more than
the rate itself.
> "$0.00X per document, $0.0X per partner packet. Assume forty funds on platform, four
> quarterly documents each, seven partners receiving commentary: that's roughly $X a quarter
> in model spend for the whole book. Those assumptions are on screen — correct them and the
> arithmetic is trivial to redo. And here's what I deliberately didn't build in a weekend,
> and what I'd do first with real documents in front of me."

`make costs` must print the rate **and** the extrapolation with its assumptions, so the
number on screen is one you can defend rather than one you computed in your head at 6 AM.

**Do not say:** anything about how long the role has been open. Do not call their current
automation duct tape — Nik built it. Do not claim a synthetic-document demo proves
production accuracy.

---

## 8. Rules for the next 14 hours

1. **`AGENTS.md` in the repo root before the first prompt.** Otherwise Cursor ignores your
   invariants.
2. **An entry in `DECISIONS.md` after every block.** 90 seconds. It's your interview crib
   sheet and it reads as unusually senior in a repo.
3. **Skim every diff.** Anything you can't summarize in one sentence goes in
   `QUESTIONS.md` — paste them to me in batches of five or six, don't stop each time.
4. **Three things stay hand-written:** the Fact invariants and the generic pairing
   validator, `guard.validate_prose`, and `R001_fee_bridge`. Those are what get asked
   about on Wednesday.
5. **Commit at every gate.** Never carry two broken things at once.
6. **Failing test first, then the implementation.** Cursor aims far better at a red test
   than at a paragraph of description.
7. **If something is not working after 20 minutes, cut it or ask me.** Do not spend 90
   minutes on a thing that was never in the demo.

0 expectation. 100% execution. 0 regrets.
