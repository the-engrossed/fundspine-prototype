# FundSpine — Architecture of record

**Author context:** Tanmai Komatireddy | Fund-document reporting prototype

---

## 0. The one-sentence thesis

> A fund-of-funds platform does not have a document-parsing problem. It has a **provenance
> problem**: every number that reaches a client-branded artifact must be traceable to a page,
> a quote, and a validation rule — or the firm has fiduciary exposure it cannot audit.

FundSpine is the spine that enforces that: **document in → cited facts → validated record →
per-partner artifact out**, with drift detection over time and an eval harness that treats
prompts as versioned software.

Everything in this spec exists to defend that thesis. If a component does not defend it, it
got cut (see §7).

### Why this shape and not the obvious shape

The obvious shape is "RAG over fund PDFs + LLM writes the memo." That fails for three reasons:

1. **Vector retrieval destroys numeric context.** Chunking splits an 18% net return from the
   footnote that says returns are gross of a 20% performance fee. Cosine similarity has no
   opinion about which number is authoritative.
2. **Numbers must not be generated.** They must be *resolved* from a validated store and
   *injected*. The LLM's job is prose and structure, never arithmetic.
3. **The blast radius is a client communication.** A wrong fee in an artifact branded
   "Apex Wealth Partners" is not a bug ticket, it is a client relationship and possibly an
   Advisers Act problem.

So: **retrieval serves prose. SQL serves numbers.** RAG is a subcomponent, not the
architecture. Embeddings retrieve narrative text; every figure in a client artifact is
resolved from a validated relational record.

---

## 1. System architecture

```
                          ┌──────────────────────────────────────┐
                          │  SOURCE DOCUMENTS (synthetic)        │
                          │  tearsheet · monthly letter · PPM    │
                          └───────────────┬──────────────────────┘
                                          │
        ╔═════════════════════════════════▼═══════════════════════════════════╗
        ║  STAGE 1 — INGEST                                                   ║
        ║  fetch → sha256 (idempotency) → page split → table parse → text     ║
        ║  Deterministic. No LLM. Emits Page[] with page_no + bbox.            ║
        ╚═════════════════════════════════╤═══════════════════════════════════╝
                                          │
        ╔═════════════════════════════════▼═══════════════════════════════════╗
        ║  STAGE 2 — EXTRACT (the only LLM call that touches raw documents)   ║
        ║  Structured output → Pydantic → Fact[]                              ║
        ║  EVERY fact carries: field_path, value, unit, page_no, verbatim      ║
        ║  quote, extractor, confidence. No quote → no fact. Hard rule.        ║
        ╚═════════════════════════════════╤═══════════════════════════════════╝
                                          │
        ╔═════════════════════════════════▼═══════════════════════════════════╗
        ║  STAGE 3 — VALIDATE (deterministic rule engine, pure functions)     ║
        ║  intra-doc arithmetic · citation verification · unit sanity          ║
        ║  pass → fact.status = validated → materialize FundPeriodMetrics      ║
        ║  fail → RuleViolation → DriftEvent(kind=consistency)                 ║
        ╚═════════════════════════════════╤═══════════════════════════════════╝
                                          │
                    ┌─────────────────────┴─────────────────────┐
                    │                                           │
        ╔═══════════▼═══════════════════╗       ╔═══════════════▼═══════════════════╗
        ║  STAGE 4 — DRIFT              ║       ║  STAGE 5 — RENDER                 ║
        ║  new period vs. history:      ║       ║  SectionPlan (deterministic)       ║
        ║  · restatement                ║       ║      ↓                             ║
        ║  · return outlier (median/MAD)║       ║  numeric binding via f() → fact_id ║
        ║  · terms change               ║       ║      ↓                             ║
        ║  · strategy semantic drift    ║       ║  prose gen (LLM, fact-marked only) ║
        ║  · reporting lateness         ║       ║      ↓                             ║
        ║  severity → route → BLOCK ────╫──────▶║  unbound-numeral validator (gate)  ║
        ╚═══════════════════════════════╝       ║      ↓                             ║
                                                ║  ic_memo   |   partner_commentary  ║
                                                ╚════════════════════════════════════╝
                                          │
        ╔═════════════════════════════════▼═══════════════════════════════════╗
        ║  CROSS-CUTTING: OpenTelemetry trace per run · cost/latency per doc  ║
        ║  and per artifact · `make eval` scorecard · CI regression gate      ║
        ╚═════════════════════════════════════════════════════════════════════╝
```

### Module layout

```
fundspine/
├── docker-compose.yml           # postgres:16 + pgvector, otel-collector, jaeger
├── Makefile                     # up, migrate, ingest, render, eval, trace
├── alembic/                     # migrations (schema is versioned, not ad-hoc DDL)
├── fundspine/
│   ├── domain/
│   │   ├── models.py            # Pydantic: Fact, FundPeriodMetrics, Terms, ...
│   │   ├── enums.py             # DocType, FactStatus, DriftKind, Severity, Tone
│   │   └── ids.py               # typed NewType ids — no bare str/UUID crossing layers
│   ├── ingest/
│   │   ├── loader.py            # sha256, page split
│   │   └── tables.py            # deterministic table extraction
│   ├── extract/
│   │   ├── extractor.py         # LLM structured output → Fact[]
│   │   └── prompts/v3/          # VERSIONED prompt dir. Never edit in place.
│   ├── validate/
│   │   ├── rules.py             # pure fns, registered by rule_id
│   │   └── engine.py            # runs registry, emits RuleViolation[]
│   ├── drift/
│   │   ├── rules.py             # inter-period detectors
│   │   └── router.py            # severity → ack | review | block
│   ├── render/
│   │   ├── plan.py              # SectionPlan — deterministic, no LLM
│   │   ├── binding.py           # f() resolver, registers fact_ids
│   │   ├── prose.py             # constrained LLM prose
│   │   ├── guard.py             # unbound-numeral validator
│   │   └── templates/
│   │       ├── ic_memo.md.j2
│   │       └── partner_commentary.md.j2
│   ├── repo/
│   │   ├── session.py           # tenant-context-required session factory
│   │   └── facts.py             # append-only writes
│   ├── obs/
│   │   └── tracing.py           # OTel setup, span helpers, GenAI conventions
│   └── api/
│       └── main.py              # FastAPI: /ingest, /artifacts, /drift, /facts/{id}
├── evals/
│   ├── golden/                  # 10 synthetic docs + ground-truth JSON
│   ├── run_eval.py
│   └── scorecards/              # COMMITTED. history is the point.
└── README.md                    # architecture + "what I did not build and why"
```

---

## 2. Schema

Postgres. Pydantic mirrors it at the boundary. Alembic-migrated from commit one — an
un-migrated schema means the model was never exercised.

### 2.1 The three design decisions that carry the whole system

**Decision 1 — Facts are append-only and immutable.**
A correction never mutates a row. It inserts a new `fact` and marks the prior
`status = 'superseded'` with `superseded_by`. Reason: **restatements are normal in alternatives.**
A manager reports an estimated NAV on the 15th and a final NAV on the 30th. If you `UPDATE`,
you have destroyed the evidence that the number moved — which is exactly the signal an
allocator wants. This is the highest-value domain detail in the build.

**Decision 2 — Terms are effective-dated.**
`mgmt_fee_bps` is not a column on `fund`. Fees, hurdles, lockups, and gates change. A Q2 memo
must compute with the terms in force during Q2, not today's terms. `effective_from` /
`effective_to`, and a fee change is *itself* a drift event.

**Decision 3 — No numeric value reaches an artifact except through a `fact_id`.**
`fund_period_metrics` stores value + `*_fact_id` FK side by side. The renderer physically
cannot emit a number it did not resolve through the binding layer (§4.2). Provenance is a
schema constraint, not a convention.

### 2.2 Tables

| Table | Purpose | Notes / non-obvious columns |
|---|---|---|
| `manager` | The GP entity | `strategy_family`, `firm_aum_usd`, `inception_date` |
| `fund` | Vehicle | `manager_id`, `vehicle_type`, `share_class`, `currency`. Share class matters: fee terms differ by class. |
| `document` | Raw artifact | `sha256` UNIQUE → idempotent re-ingest. `doc_type`, `period_start/end`, `source_uri`, `page_count` |
| `extraction_run` | One pipeline execution | `model`, `prompt_version`, `schema_version`, `trace_id`, `token_in/out`, `cost_usd`, `status`. Joins telemetry to data. |
| `fact` | **Atomic unit** | `field_path` (dotted, e.g. `terms.mgmt_fee_bps`), `value_numeric`, `value_text`, `unit`, `period`, `page_no`, `bbox` jsonb, `quote`, `confidence`, `extractor`, `status`, `superseded_by` |
| `fund_period_metrics` | Materialized validated record | one row per (fund, period). Each metric paired with `<metric>_fact_id` |
| `terms` | Effective-dated economics | `mgmt_fee_bps`, `perf_fee_bps`, `hurdle_bps`, `high_water_mark`, `lockup_months`, `notice_days`, `gate_pct`, `effective_from/to`, `source_fact_ids` |
| `partner` | **White-label tenant** | `brand` jsonb (logo_uri, hex, wordmark), `tone` enum, `disclosure_block_md`, `jurisdiction`, `template_version` |
| `partner_sleeve` | Their branded fund-of-funds | `partner_id`, `sleeve_name`, `inception` |
| `sleeve_allocation` | Holdings | `sleeve_id`, `fund_id`, `weight_bps`, `effective_from`. `SUM(weight_bps) = 10000` enforced. |
| `artifact` | Rendered output | `kind`, `partner_id` (NULL = internal), `period`, `template_version`, `render_uri`, `fact_ids` uuid[], `eval_scores` jsonb, `approved_by/at`, `blocked_by_drift_id` |
| `drift_event` | Typed anomaly | `kind`, `severity`, `rule_id`, `prior_value`, `new_value`, `fact_id`, `status`, `hypotheses` jsonb, `notes` |
| `chunk` / `embedding` | pgvector, **prose only** | narrative sections for retrieval. Never the source of a number. |

### 2.3 Multi-tenancy

White-label means **Partner A's data must never appear in Partner B's context, including
inside a prompt.** Two enforcement points:

1. `repo/session.py` — session factory requires an explicit `tenant_ctx`. There is no way to
   get a session without one. Postgres RLS policies on `partner*` and `artifact` are written
   in the migration even if they are not fully exercised in this prototype.
2. `render/prose.py` — the prose call receives a `SectionPlan` already scoped to one partner.
   Assert on `partner_id` uniqueness of every fact in the payload before the call. **A prompt
   is an exfiltration surface.**

### 2.4 Skeleton — you implement the bodies

```python
# fundspine/domain/models.py
from decimal import Decimal
from pydantic import BaseModel, Field, model_validator

class Fact(BaseModel):
    """An atomic, cited, immutable observation extracted from one page.

    Invariants:
      - exactly one of value_numeric / value_text is set
      - quote is a verbatim substring of the page text at page_no
      - a Fact is never mutated; corrections are new Facts + supersede
    """
    field_path: str = Field(pattern=r"^[a-z_]+(\.[a-z_]+)+$")
    value_numeric: Decimal | None = None
    value_text: str | None = None
    unit: str | None = None          # "bps" | "usd" | "months" | "ratio" | None
    page_no: int = Field(ge=1)
    quote: str = Field(min_length=3)
    confidence: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _exactly_one_value(self) -> "Fact":
        raise NotImplementedError  # TODO(tanmai): enforce XOR + unit/value coherence


class FundPeriodMetrics(BaseModel):
    """Materialized validated record. Every metric is fact-bound."""
    net_return_bps: int | None = None
    net_return_fact_id: str | None = None
    # TODO(tanmai): gross_return, nav_usd, sharpe_36m, max_drawdown_bps
    # TODO(tanmai): write a validator asserting value-set ⟺ fact_id-set for EVERY pair.
    #   Do it generically off model_fields, not by hand — 8 hand-written pairs is where
    #   the bug will live.
```

**Store money and rates as integer basis points and integer cents.** Never float.
A financial value is an integer from the moment it leaves the page.

---

## 3. Validation rule engine

Pure functions, registered by `rule_id`, each returning `RuleViolation | None`. No LLM. This
is the layer that makes the system auditable, and it is cheap to build.

```python
# fundspine/validate/rules.py
from typing import Callable, Protocol

class Rule(Protocol):
    rule_id: str
    severity: str          # "info" | "review" | "block"
    tolerance: Decimal
    def __call__(self, ctx: "ValidationCtx") -> "RuleViolation | None": ...

RULES: dict[str, Rule] = {}

def rule(rule_id: str, severity: str, tolerance: str = "0"):
    """Decorator registering a pure validation fn. Keeps the registry declarative
    so `make eval` can report catch-rate per rule_id."""
    ...  # TODO(tanmai)
```

### Ship these five. They are enough.

| `rule_id` | Check | Severity | Why it earns respect |
|---|---|---|---|
| `R001_fee_bridge` | gross return − (mgmt + perf fees, using **terms in force for the period**) ≈ net return | block | Proves you understand fund economics, not just PDFs |
| `R002_nav_walk` | `nav_t ≈ nav_{t-1} × (1 + net_return_t) ± flows` | block | Catches the highest-consequence extraction error |
| `R003_ytd_compound` | `Π(1 + monthly_i) − 1 ≈ reported_ytd` (geometric, **not** sum) | review | Using arithmetic summation here is the classic tell of someone who has never handled returns |
| `R004_citation_valid` | `fact.quote` is a verbatim substring of page `fact.page_no` | block | Programmatic hallucination detection. Brutal and cheap. |
| `R005_weights_sum` | sleeve allocations sum to 10000 bps | block | Trivial, but it is the one that would actually fire in production |

**The honest framing:** a violation cannot distinguish "the model misread the
table" from "the manager's own reporting is internally inconsistent." Both happen; the second
is *more valuable* to surface. So `RuleViolation` carries a `hypotheses` field with both, and
routes to a human. Do not pretend the system knows which.

---

## 4. Per-partner templating layer

This is the demo money shot: **one validated record, two artifacts, same numbers, different
brand and audience.** It is also where the naive approach silently fails, so it is where you
demonstrate judgment.

### 4.1 Four-stage split

```
SectionPlan (deterministic, Python)
    → NumericBinding  (deterministic, Jinja2 f() → registers fact_id)
        → Prose       (LLM, constrained, fact-marked)
            → Guard   (deterministic gate, can reject and retry)
```

**Stage A — `SectionPlan`. No LLM.** Computed from validated records: which sections appear,
which metrics populate each, which drift events surface (internal: all open; partner-facing:
none — they get resolved commentary, not raw anomalies), which peer comparisons are permitted.
Deterministic plan means **reproducible structure**. An LLM deciding "should I include a risk
section this quarter" is how you get inconsistent client reporting across quarters, which
compliance will eventually notice.

**Stage B — Numeric binding.** A custom Jinja2 global:

```python
# fundspine/render/binding.py
class FactBinder:
    """Resolves field_paths to formatted values and records provenance.

    Every call appends to self.used_fact_ids. The artifact's provenance set IS
    this list — not a post-hoc scan.
    """
    def f(self, field_path: str, *, fmt: str = "pct2") -> str:
        """Resolve → validated fact → format → register fact_id → return string.

        Raises UnboundFactError if no VALIDATED fact exists. Never falls back to
        a candidate or superseded fact. Never returns a placeholder.
        """
        raise NotImplementedError  # TODO(tanmai)
```

Template usage:

```jinja
Net return for the period was {{ f("metrics.net_return_bps") }}, against a management
fee of {{ f("terms.mgmt_fee_bps") }} and a performance fee of
{{ f("terms.perf_fee_bps") }} over a {{ f("terms.hurdle_bps") }} hurdle.
```

Formatting policy (bps→%, rounding, currency, negative-number convention) lives in `fmt`
handlers **once**. Rounding inconsistency across a document is the kind of thing an
institutional reader notices immediately.

**Stage C — Constrained prose.** The LLM receives **only**: the `SectionPlan`, the table of
already-resolved facts (`fact_id`, label, formatted value), the partner `tone` enum, and
length bounds. It never sees the raw PDF at this stage. Contract: any sentence making a
numeric claim must carry `[[fact:<uuid>]]`.

**Stage D — Guard.** Deterministic, and this is the component to be proudest of:

```python
# fundspine/render/guard.py
def validate_prose(prose: str, binder: FactBinder) -> list[GuardViolation]:
    """Reject prose that invents or misstates numbers.

    Checks:
      G1  every numeric literal in `prose` matches a resolved fact value
          (formatting-tolerant compare) — otherwise UNBOUND_NUMERAL
      G2  every [[fact:id]] marker resolves to a fact in binder.used_fact_ids
      G3  no [[fact:id]] references a fact from another partner's scope
      G4  disclosure block present, verbatim, unmodified

    Retry policy: inject violations into the prompt, regenerate, max 2 attempts.
    Then fall back to the deterministic template-only prose stub and flag for human.
    NEVER emit an artifact with a G1 or G3 violation.
    """
    raise NotImplementedError  # TODO(tanmai)
```

`UNBOUND_NUMERAL` rate must be **0** on the eval set, and you report it as a headline metric.
"My generated client documents have a mathematically enforced zero-invented-number rate" is a
sentence that ends the reliability conversation.

### 4.2 Brand and tone — keep it an enum

`tone` is a **small enum** (`institutional_terse`, `advisory_warm`, `educational`), each mapped
to a fixed instruction block and few-shot pair. Not freeform per-partner prompt text.
Freeform tone strings are unversioned, untestable, and drift toward compliance problems.
Enumerated tone is testable in the eval harness.

`disclosure_block_md` is appended verbatim by the renderer, keyed on
`partner.jurisdiction`, never LLM-touched, and G4-verified.

### 4.3 The two renderers

| | `ic_memo` (internal) | `partner_commentary` (white-label) |
|---|---|---|
| Audience | Internal investment team | The RIA's HNW client |
| Numbers | identical | identical |
| Open drift events | all, ranked | none |
| Rejected/low-confidence facts | shown with confidence | excluded entirely |
| Provenance | inline page + quote on every figure | footnoted source statement |
| Branding | Platform house style | partner logo, palette, wordmark |
| Disclosures | none | verbatim, jurisdiction-keyed |
| Tone | terse, hedged | partner's `tone` enum |

Render both side by side and resolve a number in each to the same `fact_id`. That makes
the architecture self-evident: identical figures, different brand.

---

## 5. Drift detection

Two layers. Layer one already exists (§3, intra-document). Layer two is inter-period.

| `rule_id` | Detector | Method | Severity |
|---|---|---|---|
| `D101_restatement` | prior period's number changed beyond tolerance in a new document | fact history diff (free, given append-only) | block |
| `D102_return_outlier` | period return outside trailing distribution | **median + MAD**, trailing 36m, threshold ~3.5 modified z | review |
| `D103_terms_change` | fee / hurdle / lockup / gate changed | effective-dated `terms` diff. Pure SQL. | block |
| `D104_strategy_drift` | this period's strategy narrative diverges from baseline | cosine distance on section embedding vs. rolling baseline | review |
| `D105_reporting_late` | document arrived later than manager's own historical cadence | day-lag vs. trailing median | info |

### Two points

**Why MAD, not standard deviation.** Hedge fund returns are fat-tailed and skewed. Mean/σ gets
dragged by the very outlier you are trying to detect, so σ-based bands under-flag exactly when
it matters. Median/MAD is robust.

**`D104` is the weakest component in the build.** Embedding distance on strategy prose is a
soft signal with an arbitrary threshold and no labeled ground truth. Style drift is the real
fund-of-funds risk, so it is worth including, but it is a heuristic to validate against
labeled historical cases before anyone trusts it.

### Routing is the part that matters

Events are **typed, ranked, and routed** — not logged to a dashboard nobody opens.

```python
# fundspine/drift/router.py
def route(event: DriftEvent) -> Routing:
    """severity → action.

    info   → auto-ack, appears in ic_memo appendix
    review → IC review queue, ic_memo surfaces it prominently
    block  → sets artifact.blocked_by_drift_id; NO partner-facing artifact may be
             generated for ANY sleeve holding this fund until resolved
    """
```

That blocking behavior is the single most institutionally-legible feature in the system. It
says: the pipeline refuses to send a client document it cannot stand behind. Demo it — attempt
generation, watch it refuse, show the reason.

---

## 6. Trace and eval harness

### 6.1 OpenTelemetry

One trace per `extraction_run`, `trace_id` persisted on the row so telemetry joins to data.

Spans: `ingest.fetch` · `ingest.hash` · `parse.tables` · `parse.text` · `extract.llm`
(one per section) · `validate.rules` · `persist.facts` · `drift.evaluate` · `render.plan` ·
`render.prose` · `render.guard` · `render.pdf`

Attributes — use the **OTel GenAI semantic conventions** where they exist
(`gen_ai.request.model`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`) rather than
inventing names, plus a namespaced domain set:

`fundspine.fund_id` · `fundspine.partner_id` · `fundspine.doc_type` · `fundspine.prompt_version` ·
`fundspine.schema_version` · `fundspine.facts_extracted` · `fundspine.facts_rejected` ·
`fundspine.rules_failed` · `fundspine.guard_violations` · `fundspine.retry_count` · `fundspine.cost_usd`

Use the standard conventions instead of homegrown attribute names.

### 6.2 Unit economics — do not skip this

Instrument and display: **cost and latency per document, and per partner artifact.**

Report a real number: cost and latency per manager document, and per partner packet.
The operating question is cost per client per quarter, answered from the spans rather
than from a separate estimate.

### 6.3 The eval harness

**Golden set: 10 synthetic documents, with ground-truth JSON.** Build these
**first**, before the extractor. Ground truth before implementation forces the schema
to be decided by what actually needs extracting, and it means the extractor is never tuned
against vibes.

Include these adversarial cases deliberately:

1. A restated NAV (prior period revised) → must fire `D101`
2. A mid-year fee change → must fire `D103`, and Q2 memo must use Q2 terms
3. A returns table split across a page break
4. A footnote that **overrides** the table ("returns shown gross of performance fee")
5. A scanned image page (no text layer)
6. A fund with a side pocket / illiquid bucket
7. A month where a redemption gate was invoked
8. Two share classes with different fee terms in one document
9. A seeded arithmetic error (net ≠ gross − fees) → must fire `R001`
10. A clean baseline document

**Metrics — field-level, not document-level.** Document-level accuracy hides everything.

| Metric | Definition | Target |
|---|---|---|
| Field exact-match | per `field_path`, tolerance-aware numeric compare | report per field, no cherry-picking |
| Field recall | required fields extracted at all | flag every miss |
| **Citation validity** | `quote` verbatim in cited page | **100%** — programmatically checkable |
| Rule catch-rate | seeded errors caught, per `rule_id` | report per rule |
| **Unbound-numeral rate** | G1 violations in final artifacts | **0%** |
| Cross-tenant leak | G3 violations | **0%** |
| Prose faithfulness | LLM-as-judge, 1–5 | **secondary signal only** |

Be explicit: **LLM-as-judge grades prose quality; deterministic checks grade numbers.**
A judge must not be used to validate arithmetic.

**`make eval` → committed scorecard + CI gate.**

```python
# evals/run_eval.py
def main() -> int:
    """Run the golden set, emit scorecards/<git_sha>.json + .md, diff against
    scorecards/baseline.json. Exit non-zero if any field's exact-match regresses
    beyond tolerance, or if citation-validity / unbound-numeral leave 100% / 0%.

    Wire into GitHub Actions. A prompt edit that degrades extraction FAILS THE BUILD.
    """
```

Commit the scorecard history, including a diff where the eval caught a regression that
was introduced on purpose. A green board proves nothing. An eval that caught a regression
proves the harness is real. Prompts are tested, versioned software.

---

## 7. Scope: what is IN, what is CUT

The spine below is in scope. Everything else in this section is a cut.

### IN — the spine, non-negotiable

Document → cited facts with page + verbatim quote → 5 validation rules → materialized
validated record → 2 drift detectors minimum (`D101`, `D103`) with blocking → dual artifact
render with the guard → OTel traces with cost/latency → 10-doc golden set → `make eval`
scorecard with a caught regression.

### CUT

| Cut | Why |
|---|---|
| Next.js / TypeScript UI | FastAPI plus server-rendered HTML. The time goes into the data spine, not the surface. |
| Auth, full RLS enforcement | Schema and the tenant-context seam are in place. RLS is the production step and is not exercised here. |
| Real manager documents | Synthetic, because using a real fund's letter in a demo is a compliance problem. |
| Agent framework (LangChain / LangGraph) | Explicit control flow. At this scale a graph framework adds indirection and removes the ability to reason about failure. |
| GCP deployment | Docker Compose locally. Diagram the GCP mapping in the README (Cloud Run workers, Pub/Sub decoupling ingest from extraction, Cloud SQL, GCS for raw artifacts). A live deploy is out of scope. |
| Multi-provider fallback routing | One provider. Fallback is a distraction at prototype stage. |
| pgvector / `D104` | First thing to drop if the schedule slips. Least load-bearing. |

### Cut priority if the schedule slips

Drop in this order: `D104` → pgvector → PDF rendering (ship clean HTML) → `D105` → the second
drift period.

**Never cut:** citation-bound facts, the guard, or the eval scorecard. Those three are the
core. Everything else can wait.

---

## 8. Build order

### First

- `docker-compose` up with Postgres; `alembic init`; first migration with the real schema
- `domain/models.py` — `Fact`, `FundPeriodMetrics`, `Terms`, enums, typed ids
- **Author golden docs 1–3 with ground-truth JSON.** Ground truth before extractor. Non-negotiable.
- Gate: `make up && make migrate` clean, three golden docs on disk with truth files

### Next

- `ingest/` — sha256 idempotency, page split, table parse
- `extract/extractor.py` — structured output → `Fact[]` with page + quote. Prompt in `prompts/v1/`
- `validate/` — the 5 rules + engine + `RuleViolation` with `hypotheses`
- `repo/facts.py` — append-only persistence, supersede path
- `evals/run_eval.py` — field-level scorecard, citation validity
- Gate: **one document → validated facts → passing scorecard printed to terminal.** If this is not in place, cut `D104`, pgvector, and PDF before adding surface area.

### Then

- `render/` — plan, binder, templates, prose, guard. Both renderers.
- `drift/` — `D101`, `D103`, router with blocking
- `obs/tracing.py` — spans end to end, cost/latency per doc and per artifact, Jaeger up
- Golden docs 4–10, including the restatement and fee-change cases
- Introduce a deliberate prompt regression, capture the scorecard diff, revert
- Gate: two periods ingested, both artifacts rendered, one blocking drift
  event, trace waterfall, cost/latency numbers, scorecard diff captured

### Close-out

- README: architecture diagram, the thesis (§0), GCP mapping diagram, and an explicit
  **"What I did not build, and why"** section.
- Repo hygiene: zero notebooks, full type hints, `ruff` + `mypy` clean, `make` targets work
  from a cold clone. `make up` has to succeed on a machine that has never seen the repo.
- Commit the scorecard history.

---

## 9. Design questions

**"Why not just RAG over the documents?"**
Retrieval serves prose; SQL serves numbers. Chunking splits a return from the footnote that
qualifies it, and cosine similarity has no notion of which figure is authoritative. I use
embeddings for narrative retrieval and a validated relational record for every number that
reaches a client artifact.

**"Why no agent framework?"**
At this scale the control flow is a five-stage pipeline with explicit retry policies. A graph
framework would add indirection between me and the failure modes, and the failure modes are
the product. If the workflow graph grows genuinely dynamic, that is the moment to adopt one —
not before.

**"How do you know the LLM didn't make up a number?"**
Because it structurally cannot reach the output. Numbers are resolved from validated facts and
injected by the binding layer; the prose model never emits a numeric literal that survives the
guard. Unbound-numeral rate is a measured metric and it is zero on my eval set. Separately,
citation validity is checked programmatically — every quote must be a verbatim substring of
the page it cites.

**"What's weakest here?"**
`D104`, the strategy-drift detector — embedding distance with a hand-picked threshold and no
labeled ground truth. Style drift is the real risk in a fund-of-funds, so it belongs in the
design, but I would not let anyone act on that signal until it was validated against labeled
historical cases. Second weakest: I ran this on synthetic documents, so the failure modes I
hardened against are the ones I imagined, not the ones a live set of managers would produce.

---

## 10. Standing rule

Do not reopen the schema once implementation has started. The spec is decided. If something
in here is wrong, you will find out by building it, not by thinking about it harder.
