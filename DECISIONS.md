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
