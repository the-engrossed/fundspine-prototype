# Decisions

One entry per block. Written at the time, not reconstructed afterwards.

## Block A — foundation (Sun 13:30)

**Postgres on port 5433, not 5432.** A local Postgres on the default port is the most
common reason a cold clone fails on someone else's machine. The cost of being explicit is
one line in `.env.example`.

**pgvector image rather than plain postgres:16.** The extension is not enabled by any
migration and no vector column exists. The image costs nothing and keeps the `/ask`
endpoint reachable if Sunday goes well; if it does not, nothing has to be undone.

**Sharpe is stored as `ratio_bps` (1.42x becomes 14200).** The rule is that financial
values are integers, and a unitless ratio is not an exception to it. One integer scale
across returns, fees and ratios means one formatting policy and no float anywhere.

**`FieldPath` is a closed enum, not a validated string pattern.** Field-level recall is
only meaningful against a known denominator, so the set of extractable things has to be
enumerable. An extractor emitting an unknown path fails validation and the fact is
dropped with a recorded reason, which is also the honest behaviour.

**Money is `BigInteger` cents, and `Numeric` is banned alongside `Float`.** `Numeric`
would be defensible, but allowing two correct answers invites a mixed codebase; one
allowed representation is enforceable by review.

**Both value and `_fact_id` columns are nullable, with pairing enforced in the domain
model rather than by a database constraint.** Six `CHECK` constraints would be six places
to forget when a metric is added. The Pydantic validator derives the pairs from
`model_fields`, so a new metric cannot ship without provenance.

**`session_scope(ctx)` is the only way to get a Session, and it sets the `app.tenant_id`
GUC.** RLS policies are not in this migration — they are named in the README as the
production step — but the variable those policies read is set on every session, so the
seam is exercised rather than sketched.

**The three hand-written implementations are left as failing stubs.** `Fact._invariants`,
`FundPeriodMetrics._every_value_is_fact_bound`, and (later) `guard.validate_prose` and
`R001_fee_bridge` are specified by tests and written by hand, per `AGENTS.md`.

## Block B — pipeline (Sun 14:55)

**Ground truth is recorded as each value is interpolated into the HTML, then
checked against ingest page text.** A quote that is not an exact substring
refuses to write the truth file. That is how citation validity stays a
substring match rather than a judgement.

**R001 uses Python `round` on annual bps / 4, then a performance fee on
excess over the quarterly hurdle.** 150 → 38 quarterly; 175 → 44. The Q1
bridge closes at 347 net; doc_2 states 387 (40 bps off). The body is
hand-written; goldens were aligned to that formula.

**High water mark is not a FieldPath.** It is True for this fund when terms
are materialized. Adding a path would expand the eval denominator for one
boolean; the terms table still stores it.

## Block D — render (Sun 18:50)

**Prose is a tone-enum sentence pair, not a live LLM call.** Billing was
exhausted and Moment 1 cannot wait on it. Numbers still enter only as
`[[fact:<uuid>]]`; the guard contract is unchanged. A prose model is a
drop-in behind `write_prose`.

**Templates call `f()`; the model never emits a digit.** Partner HTML is
branded from a `PartnerConfig` row (Apex navy/warm, Ridgeline slate/terse).
Identical figures, different voice. Provenance appendix lists page and
quote for every fact `f()` touched.

**`validate_prose` is hand-written against `tests/test_guard.py`.** Render
concatenates the disclosure onto the marked prose before the guard so G4
is a substring check rather than a template concern.

## Block C — v1 extract (Sun 20:13)

**Committed `evals/scorecards/v1_before.json` before any prompt edit.**
Citation validity 100%. Required recall 86.67% / 86.67% / 81.25%. The
misses are Sharpe and max drawdown with `period` null (values are
correct) plus `fund.share_class` on doc_3. R001 fires on doc_2 (40 bps).
v2 is a new prompt file, not an edit of v1.

## Block F — costs (Sun 20:30)

**USD micros, published gpt-4o-2024-08-06 list price.** $2.50 / 1M in, $10 / 1M
out. Prose is not billed. Whole-book math is 40 funds × 4 documents/year;
partner packets share the extract. Assumptions print next to the number.

**Five OTel spans to a JSONL file exporter:** extract.llm, validate.rules,
drift.evaluate, render.prose, render.guard. No Jaeger.

## Block G — CI (Sun 20:30)

**CI is pytest + ruff + mypy.** No API key, no Postgres, no LLM. The
scorecard gate is `evals/scorecards/baseline.json` floors plus
`regression_messages`. Breaking a rule or the guard fails the board;
degrading a prompt is `make eval` locally against the committed baseline.

## Block E — drift (Sun 18:50)

**D101 keys on (field_path, period) and ignores standing terms
(`period is None`).** Q1 NAV moving on the Q2 document is the restatement.
**D103 is the management-fee row only.** 150 → 175 is Moment 2; other terms
did not change.

**Blocking refuses partner 2026Q2 HTML and still renders the IC memo.**
The memo table shows formatted prior and new values, not raw integers.
The IC binder is doc_3 only so `f()` is unambiguous; both NAV figures
appear via `format_fact` on the drift pair.

