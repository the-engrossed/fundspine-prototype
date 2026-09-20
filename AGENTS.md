FundSpine — Agent Rules
Read this before writing any code in this repo. These are invariants, not preferences.
If a request conflicts with a rule below, say so instead of silently working around it.

The one-line thesis
Retrieval serves prose. SQL serves numbers. No figure reaches a client-facing document
except through a fact ID with a page and a verbatim quote behind it.

Non-negotiable invariants
No invented numbers. No numeric value may appear in a rendered document unless it
was resolved from a validated fact row through render/binding.py. Never hardcode a
figure. Never let a model emit one directly into output.

The prose model may not emit digits at all. Narrative generation returns sentences
containing [[fact:<uuid>]] markers where a figure belongs; the template resolves each
marker through f(). Any bare digit in model output is a guard violation. Non-fact
quantities are spelled as words ("forty liquid futures markets") or supplied as facts.

Facts are append-only. Never UPDATE a value on the fact table. A correction
inserts a new row and sets the prior row's status='superseded' plus superseded_by.
History must survive — restatements are normal in alternatives, not exceptional.

Money and rates are integers. Basis points and cents, stored as BigInteger.
Never Float, never Numeric, never a Python float for a financial value. Convert
at the extraction boundary and nowhere else.

Terms are date-ranged and resolved as-of the period. Management fees, performance
fees, hurdles, lockups and gates live in terms with effective_from /
effective_to. Every rule and every render resolves the terms **in force during the
period being reported**. Never use current terms for a past quarter.

Every fact needs a citation. A fact row requires page_no and a quote that is
an exact substring of that page's text. No quote means no fact — drop it and record why.

Prompts are versioned files. Prompt text lives in extract/prompts/v1/, v2/, as
.md files loaded by name. Never edit a prompt in place; create the next version.

Vectors for prose, SQL for numbers. Embedding search may only retrieve narrative
text. Never resolve a financial figure by similarity search.

Tenant scoping is mandatory. Every database session requires an explicit tenant
context. There is no code path that opens a session without partner scope. A prompt is
an exfiltration surface: assert single-tenant scope on every payload before the call.

Scope — this is a weekend build, hold the line
Source documents are HTML, not PDF. Golden documents are generated as HTML with
explicit page divisions (<section class="page" data-page-no="N">). Ingest reads that HTML
and yields [{page_no, text}]. **Do not add PyMuPDF, pdfplumber, reportlab, or any PDF
library.** A real-PDF adapter is future work behind the same interface.

Nine tables only: fund, document, extraction_run, fact, fund_period_metrics,
terms, partner, drift_event, artifact. There is no manager table — manager name
and strategy family are columns on fund. There are no sleeve or allocation tables; a
partner receives commentary on a single fund.

Two validation rules: R001_fee_bridge, R004_citation_valid.
Two drift detectors: D101_restatement, D103_terms_change.

Do not add: LangChain, LangGraph, LlamaIndex or any agent framework — control flow is
explicit and that is a deliberate position. No authentication, user accounts, or JavaScript
frontend. No PDF output. No Jaeger container; OTel spans go to a file exporter.

Do not build anything that is not in plan_36h.md. If it looks like a twenty-minute
addition, it is not in scope. Ask first.

Hand-written — do not modify these
Three implementations are written by hand and must not be touched, refactored, or
"improved" unless explicitly asked:

the Fact model validators and the generic value⟺fact_id pairing validator
in fundspine/domain/models.py

validate_prose in fundspine/render/guard.py

R001_fee_bridge in fundspine/validate/rules.py

You may write tests against them. You may not rewrite them.

Style
Python 3.12. Full type hints on every signature. Pydantic v2. SQLAlchemy 2.0 typed ORM.

Validation rules are pure functions — no I/O, no database access inside a rule.

Side effects live only in repo/ and api/.

Keep modules small; split past roughly 200 lines.

Must pass ruff check and mypy.

Fail loudly. Do not add retry, repair, or fallback logic unless asked. Never return a
placeholder, a dash, or "N/A" where a value is missing — raise.

No Jupyter notebooks in this repo, ever.

Working style
Plan before diffing. For anything beyond one file, state the plan and wait.

Failing test first, then the implementation.

One concern per change. Do not refactor across module boundaries opportunistically.

Never modify anything under evals/golden/ once ground truth is committed.