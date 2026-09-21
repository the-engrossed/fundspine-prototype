# FundSpine

Retrieval serves prose. SQL serves numbers. No figure reaches a client-facing
document except through a fact ID with a page and a verbatim quote behind it.

That is a schema constraint, not a convention. Equi is scaling white-label
delivery faster than a human can assemble packets, and fund managers restate
numbers. This weekend prototype is the spine that makes both of those
survivable: **document in → cited facts → validated record → per-partner
artifact out**, with drift that can refuse a client document and an eval
harness that treats prompts as versioned software.

## Quickstart

Python 3.12, Docker, an OpenAI key for ingest only.

```bash
cp .env.example .env          # fill OPENAI_API_KEY for ingest/eval
make install
make up
make migrate
make golden
make ingest                   # live extract; costs money
make eval                     # diffs against evals/scorecards/baseline.json
make render                   # out/apex-2026Q1.html, ridgeline, IC memo
make drift
make costs
make check                    # ruff, mypy, pytest — no key, no LLM
```

Deterministic commands (`make golden`, `make render`, `make drift`, `make test`)
run without an API key. Render binds golden-validated facts so Moment 1 and
Moment 2 do not depend on billing.

## Architecture

```
  HTML golden docs                 closed FieldPath enum
  <section class="page">           integers only (bps, cents)
           │
           ▼
  ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
  │  INGEST         │     │  EXTRACT (LLM)  │     │  VALIDATE       │
  │  pages + sha256 │────▶│  quote or drop  │────▶│  R001 fee bridge│
  │  no PDF library │     │  prompts/v2     │     │  R004 citation  │
  └─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                           │
                         ┌─────────────────────────────────┴──────────┐
                         ▼                                            ▼
               ┌─────────────────┐                          ┌─────────────────┐
               │  DRIFT          │                          │  RENDER         │
               │  D101 restate   │  BLOCK ──refuse──┐       │  [[fact:uuid]]  │
               │  D103 terms     │                  │       │  guard G1–G4    │
               └─────────────────┘                  │       │  f() binder     │
                                                    │       └────────┬────────┘
                                                    │                │
                                                    ▼                ▼
                                          partner Q2 .blocked.txt    Apex + Ridgeline HTML
                                          IC memo still renders      same numbers, two brands
```

Nine tables: `fund`, `document`, `extraction_run`, `fact`,
`fund_period_metrics`, `terms`, `partner`, `drift_event`, `artifact`.
Control flow is explicit. There is no agent framework.

## Eval summary

CI does **not** call the model. The live extract is committed.

`evals/scorecards/v1_before.json` is prompt v1 (Sharpe/drawdown `period`
null; doc_3 missed `fund.share_class`).
`evals/scorecards/baseline.json` is prompt v2, the approved floor.

| doc | citation_validity | required_recall | exact_matches | extracted |
|---|---|---|---|---|
| doc_1 v1 | 100% | 86.67% | 14/16 | 16 |
| doc_1 v2 | 100% | **100%** | **16/16** | 16 |
| doc_2 v1 | 100% | 86.67% | 14/16 | 16 |
| doc_2 v2 | 100% | **100%** | **16/16** | 16 |
| doc_3 v1 | 100% | 81.25% | 14/17 | 17 |
| doc_3 v2 | 100% | **93.75%** | **16/17** | 16 |

R001 fires on doc_2 (stated net 387 bps vs expected 347, 40 bps off).
doc_3's remaining miss is the restated Q1 NAV as its own period-keyed fact.

`make eval` exits non-zero if citation validity, required recall, or exact
matches drop versus `baseline.json`.

## Costs

`make costs` prints this from `extraction_run` token counts. Money is integer
USD micros. Rate is the published gpt-4o-2024-08-06 list price.

model: gpt-4o-2024-08-06
rate: $2.50 / 1M input tokens, $10.00 / 1M output tokens
prose: not billed (tone-enum templates, not an LLM)

| document | tokens_in | tokens_out | cost |
|---|---|---|---|
| golden://doc_1 | 1218 | 1114 | $0.014185 |
| golden://doc_2 | 1082 | 1116 | $0.013865 |
| golden://doc_3 | 1258 | 1117 | $0.014315 |

**rate per document (mean of 3): $0.014121**
**rate per partner packet: $0.014121** (one extract; render is $0; not re-extracted per partner)

Assumptions — correct them and the arithmetic is the same:

- 40 funds on platform
- 4 documents per fund per year
- 7 partners receiving commentary
- 1 extract per fund per quarter

| horizon | extracts | model spend |
|---|---|---|
| one quarter | 40 | $0.564840 |
| one year | 160 | $2.259360 |
| partner packets / quarter (not extra LLM) | 280 | $0.564840 |

These goldens are short HTML tearsheets. A real manager PDF with scans would
raise `tokens_in`; the multiplication does not change.

## CI

CI gates the deterministic layers only. Rules, binder, guard, domain
validators, and a scorecard diff against the committed `baseline.json`. No
API key, no LLM calls, no flake, runs in under a minute.

The regression demo splits in two:

- **Break a rule or the guard** → CI fails. Deterministic. That is the screenshot.
- **Degrade an extraction prompt** → `make eval` locally; field recall and
  citation validity drop in the terminal. That belongs on camera, not in a
  CI log.

## What I did not build, and why

- **Next.js / a JavaScript frontend.** The hard part is the pipeline.
- **Auth, RLS policies, user accounts.** Tenant scoping is in the session
  layer and the guard; database RLS is the production step. The GUC those
  policies would read is already set on every session.
- **PDF parse and PDF output.** Goldens are HTML with explicit page
  divisions so citation validity is an exact substring. A real-PDF adapter
  sits in front of the same `[{page_no, text}]` interface.
- **LangChain / LangGraph / LlamaIndex.** Control flow is explicit.
- **Manager table, sleeves, multi-fund allocations.** One fund, two
  partners. Sleeves are a join table and add no new failure mode.
- **Live prose LLM.** Tone is an enum mapped to a sentence pair. Numbers
  still enter only as `[[fact:<uuid>]]`. A prose model is a drop-in behind
  `write_prose`.
- **Jaeger.** Five OTel spans (`extract.llm`, `validate.rules`,
  `drift.evaluate`, `render.prose`, `render.guard`) go to `traces/spans.jsonl`.
  Swapping the exporter for Cloud Trace is a config line.
- **`POST /ask`.** The stretch: retrieval for narrative, SQL for numbers,
  refusal when the question is a figure. Not this weekend.

First with real documents: a PDF text-normalization adapter, then the
ask-path refusal. The quote-or-drop rule does not change.
