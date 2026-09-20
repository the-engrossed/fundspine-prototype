# FundSpine — Build Spec & 72-Hour Execution Plan

**Author context:** Tanmai Komatireddy | Target: Equi, Founding Engineer & Applied AI Lead
**Submit by:** Friday, September 18, 2026, 3:00 PM ET
**Call with Nik Vrudhula (Chief of Staff & Agents):** Wednesday, September 23, 2026

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

The obvious shape is "RAG over fund PDFs + LLM writes the memo." That fails for three reasons
you should be able to state in one breath:

1. **Vector retrieval destroys numeric context.** Chunking splits an 18% net return from the
   footnote that says returns are gross of a 20% performance fee. Cosine similarity has no
   opinion about which number is authoritative.
2. **Numbers must not be generated.** They must be *resolved* from a validated store and
   *injected*. The LLM's job is prose and structure, never arithmetic.
3. **The blast radius is a client communication.** A wrong fee in an artifact branded
   "Apex Wealth Partners" is not a bug ticket, it is a client relationship and possibly an
   Advisers Act problem.

So: **retrieval serves prose. SQL serves numbers.** RAG is a subcomponent, not the
architecture. That single sentence is your strongest differentiator against the other 84
applicants, because the job spec asked for "RAG-based intelligence systems" and you are
delivering something strictly stronger while explaining why.

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
un-migrated schema in a repo you are submitting as a senior artifact is a tell.

### 2.1 The three design decisions that carry the whole system

**Decision 1 — Facts are append-only and immutable.**
A correction never mutates a row. It inserts a new `fact` and marks the prior
`status = 'superseded'` with `superseded_by`. Reason: **restatements are normal in alternatives.**
A manager reports an estimated NAV on the 15th and a final NAV on the 30th. If you `UPDATE`,
you have destroyed the evidence that the number moved — which is exactly the signal an
allocator wants. This is the highest-value domain detail in the build. Say the word
"restatement" on the Loom.

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

### 2.3 Multi-tenancy — the trap they will probe

White-label means **Partner A's data must never appear in Partner B's context, including
inside a prompt.** Two enforcement points:

1. `repo/session.py` — session factory requires an explicit `tenant_ctx`. There is no way to
   get a session without one. Postgres RLS policies on `partner*` and `artifact` are written
   in the migration even if you do not fully exercise them in 72 hours.
2. `render/prose.py` — the prose call receives a `SectionPlan` already scoped to one partner.
   Assert on `partner_id` uniqueness of every fact in the payload before the call. **A prompt
   is an exfiltration surface.** Say that sentence. Almost no candidate does.

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

**Store money and rates as integer basis points and integer cents.** Never float. If Nik's
call goes anywhere near numbers, "I don't hold financial values in floats" is a two-second
credibility deposit.

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

**The honest framing for the Loom:** a violation cannot distinguish "the model misread the
table" from "the manager's own reporting is internally inconsistent." Both happen; the second
is *more valuable* to surface. So `RuleViolation` carries a `hypotheses` field with both, and
routes to a human. Do not pretend the system knows which. Saying "I can't disambiguate these
two and here's why that's still useful" is a senior move.

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
Enumerated tone is testable in the eval harness. Say why you chose the constraint.

`disclosure_block_md` is appended verbatim by the renderer, keyed on
`partner.jurisdiction`, never LLM-touched, and G4-verified.

### 4.3 The two renderers

| | `ic_memo` (internal) | `partner_commentary` (white-label) |
|---|---|---|
| Audience | Equi investment team | The RIA's HNW client |
| Numbers | identical | identical |
| Open drift events | all, ranked | none |
| Rejected/low-confidence facts | shown with confidence | excluded entirely |
| Provenance | inline page + quote on every figure | footnoted source statement |
| Branding | Equi | partner logo, palette, wordmark |
| Disclosures | none | verbatim, jurisdiction-keyed |
| Tone | terse, hedged | partner's `tone` enum |

Generate both **side by side in the Loom** and hover a number in each to show the same
`fact_id`. That is the four-second moment that makes the architecture self-evident without
narration.

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

### Two things to say out loud

**Why MAD, not standard deviation.** Hedge fund returns are fat-tailed and skewed. Mean/σ gets
dragged by the very outlier you are trying to detect, so σ-based bands under-flag exactly when
it matters. Median/MAD is robust. This is a one-sentence answer that tells an investment team
you are not naive about their data — Itay will register it instantly if he ever joins a call.

**`D104` is the weakest component in the build.** Embedding distance on strategy prose is a
soft signal with an arbitrary threshold and no labeled ground truth. Style drift is the real
fund-of-funds risk, so it is worth *gesturing* at, but say plainly: "this one is a heuristic I
would want to validate against labeled historical cases before anyone trusts it." Volunteering
the weakest link is worth more than five working features.

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

`equi.fund_id` · `equi.partner_id` · `equi.doc_type` · `equi.prompt_version` ·
`equi.schema_version` · `equi.facts_extracted` · `equi.facts_rejected` ·
`equi.rules_failed` · `equi.guard_violations` · `equi.retry_count` · `equi.cost_usd`

Using the standard conventions instead of homegrown attribute names is a small signal that you
live in this ecosystem rather than having read one blog post about it.

### 6.2 Unit economics — do not skip this

Instrument and display: **cost and latency per document, and per partner artifact.**

Then put a real number on screen in the Loom: *"$0.0X and Y seconds per manager document;
$0.XX and Z seconds per partner packet."*

Tory is a CEO scaling from 1 to 7 white-label clients. The question in his head is "what does
this cost per client per quarter." Almost no engineering candidate can answer a unit-economics
question from their own telemetry. You can, because you built the spans. This single slide may
matter more to the founders than the architecture diagram.

### 6.3 The eval harness — the most senior artifact in the submission

**Golden set: 10 synthetic documents you author, with ground-truth JSON.** Build these
**first**, tonight, before the extractor. Ground truth before implementation forces the schema
to be decided by what actually needs extracting, and it means you are never tuning against
vibes.

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

Be explicit in the README and on camera: **LLM-as-judge grades prose quality; deterministic
checks grade numbers.** Candidates who use a judge to validate arithmetic reveal that they do
not understand what they built. Naming the boundary shows you do.

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

Commit the scorecard history. Then, in the Loom, **show a scorecard diff where the eval caught
a regression you introduced.** A green board proves nothing. An eval that caught you being
wrong proves the harness is real. This is the moment that separates you from every other
applicant, because prompts-as-tested-versioned-software is precisely the discipline the market
is still missing.

---

## 7. Scope: what is IN, what is CUT

You have roughly 14 working hours before Friday afternoon, plus a day job you must keep quiet
at. Ruthlessness now is the whole game.

### IN — the spine, non-negotiable

Document → cited facts with page + verbatim quote → 5 validation rules → materialized
validated record → 2 drift detectors minimum (`D101`, `D103`) with blocking → dual artifact
render with the guard → OTel traces with cost/latency → 10-doc golden set → `make eval`
scorecard with a caught regression.

### CUT — and say each one out loud on camera

| Cut | Say this |
|---|---|
| Next.js / TypeScript UI | "Deliberately a FastAPI + server-rendered page. I put the 72 hours into the data spine, not the surface." |
| Auth, full RLS enforcement | Schema + policies written, tenant-context seam visible. "RLS goes here; I didn't exercise it in three days." |
| Real manager documents | Synthetic, and **say why**: using a real fund's letter in a demo is a compliance smell. Mentioning that awareness scores. |
| Agent framework (LangChain / LangGraph) | "Explicit control flow and a hand-rolled state machine. At this scale a graph framework adds indirection and removes the ability to reason about failure." Be ready to defend it — it is the correct call and they will test whether you hold it. |
| GCP deployment | Docker Compose locally. **Diagram** the GCP mapping in the README (Cloud Run workers, Pub/Sub decoupling ingest from extraction, Cloud SQL, GCS for raw artifacts). Do not attempt a deploy — that is where eight hours vanish. |
| Multi-provider fallback routing | One provider. Fallback is a distraction at prototype stage. |
| pgvector / `D104` | **First thing to cut if Thursday slips.** Least load-bearing, most expected. |

### The cut priority if Thursday collapses

Drop in this order: `D104` → pgvector → PDF rendering (ship clean HTML) → `D105` → the second
drift *demo* period.

**Never cut:** citation-bound facts, the guard, or the eval scorecard. Those three *are* the
differentiator. Everything else is table stakes.

---

## 8. The 72-hour schedule

### Tuesday night (2h — tonight)

- `docker-compose` up with Postgres; `alembic init`; first migration with the real schema
- `domain/models.py` — `Fact`, `FundPeriodMetrics`, `Terms`, enums, typed ids
- **Author golden docs 1–3 with ground-truth JSON.** Ground truth before extractor. Non-negotiable.
- Gate: `make up && make migrate` clean, three golden docs on disk with truth files

### Wednesday (5–6h)

- `ingest/` — sha256 idempotency, page split, table parse
- `extract/extractor.py` — structured output → `Fact[]` with page + quote. Prompt in `prompts/v1/`
- `validate/` — the 5 rules + engine + `RuleViolation` with `hypotheses`
- `repo/facts.py` — append-only persistence, supersede path
- `evals/run_eval.py` — field-level scorecard, citation validity
- Gate, end of Wednesday: **one document → validated facts → passing scorecard printed to terminal.** If you do not hit this, cut `D104`, pgvector, and PDF now rather than Thursday night.

### Thursday (5–6h)

- `render/` — plan, binder, templates, prose, guard. Both renderers.
- `drift/` — `D101`, `D103`, router with blocking
- `obs/tracing.py` — spans end to end, cost/latency per doc and per artifact, Jaeger up
- Golden docs 4–10, including the restatement and fee-change cases
- Introduce a deliberate prompt regression, capture the scorecard diff, revert
- Gate, end of Thursday: two periods ingested, both artifacts rendered, one blocking drift
  event, trace waterfall screenshot, cost/latency numbers, scorecard diff captured

### Friday morning (2h)

- README: architecture diagram, the thesis (§0), GCP mapping diagram, and an explicit
  **"What I did not build, and why"** section. That section is a strength signal, not a
  disclaimer.
- Repo hygiene: zero notebooks, full type hints, `ruff` + `mypy` clean, `make` targets work
  from a cold clone. Nik or whoever they route the repo to will try `make up`. It must work.
- Commit the scorecard history.

### Friday midday (2h) — record and submit

**Two takes maximum.** Shot list, ~4 minutes:

| Time | Shot |
|---|---|
| 0:00–0:45 | Hypothesis framing (from the previous session's opener — hedged, evidence-based, invites correction) |
| 0:45–1:45 | Live run. Ingest a manager letter. **Click a number in the output → page, bbox, verbatim quote.** Provenance in one gesture. |
| 1:45–2:30 | Both artifacts side by side. Same `fact_id`, different brand, different audience, disclosures verbatim. |
| 2:30–3:05 | Ingest the next period. Restatement fires. Partner artifact generation **refuses**. Show why. |
| 3:05–3:45 | Trace waterfall → cost and latency per document and per packet → eval scorecard diff catching the regression. |
| 3:45–4:00 | Close: the one weakest component named honestly (`D104`), and the question you want answered on the 23rd — inbound extraction or outbound partner generation. |

**Submit by 3:00 PM ET Friday.** It lands in Nik's Friday afternoon, not his weekend inbox.

---

## 9. The four questions you will be asked, and the answers

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
hardened against are the ones I imagined, not the ones your managers actually produce.

---

## 10. Standing rule

0 expectation. 100% execution. 0 regrets.

Do not spend Wednesday redesigning the schema. The spec is decided; the terminal is where the
next 14 hours belong. If something in here is wrong, you will find out by building it, not by
thinking about it harder.
