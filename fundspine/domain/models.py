"""Core domain models.

Two invariants are enforced here rather than in the database, because they are
about meaning rather than storage:

  1. A Fact is atomic, cited and immutable.
  2. A materialized metric may not exist without the fact that produced it.

The second is the whole provenance guarantee. If a value can be set without a
fact_id, then somewhere downstream a number reaches a client document without a
page and a quote behind it, and the architecture is decoration.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator

from fundspine.domain.enums import UNIT_BY_FIELD, FactStatus, FieldPath, Unit
from fundspine.domain.ids import DocumentId, ExtractionRunId, FactId, FundId, TermsId


def expected_unit(field_path: FieldPath) -> Unit:
    """The unit a field_path is required to carry. Single source of truth for
    the Fact unit-coherence invariant and for the extractor's conversion step."""
    return UNIT_BY_FIELD[field_path]


class Period(BaseModel):
    """A reporting quarter. Comparable and orderable so drift can diff periods."""

    model_config = ConfigDict(frozen=True)

    year: int = Field(ge=2000, le=2100)
    quarter: int = Field(ge=1, le=4)

    @property
    def label(self) -> str:
        return f"{self.year}Q{self.quarter}"

    @property
    def start(self) -> date:
        return date(self.year, 3 * (self.quarter - 1) + 1, 1)

    @property
    def end(self) -> date:
        return date(self.year + 1, 1, 1) if self.quarter == 4 else date(
            self.year, 3 * self.quarter + 1, 1
        )

    def __lt__(self, other: Period) -> bool:
        return (self.year, self.quarter) < (other.year, other.quarter)

    @classmethod
    def parse(cls, label: str) -> Period:
        year, _, quarter = label.partition("Q")
        return cls(year=int(year), quarter=int(quarter))


class Fact(BaseModel):
    """An atomic, cited, immutable observation extracted from one page.

    Invariants (enforced below):
      - exactly one of value_numeric / value_text is set
      - unit agrees with the unit the field_path declares
      - a numeric value is an integer: basis points, ratio basis points, cents,
        months or days. There is no float anywhere in this system.
      - superseded_by is set if and only if status is SUPERSEDED
      - quote is verbatim from the cited page (checked by R004 against page text,
        which this model cannot see)
    """

    model_config = ConfigDict(frozen=True)

    fact_id: FactId
    fund_id: FundId
    document_id: DocumentId
    extraction_run_id: ExtractionRunId

    field_path: FieldPath
    value_numeric: int | None = None
    value_text: str | None = None
    unit: Unit
    period: str | None = None

    page_no: int = Field(ge=1)
    quote: str = Field(min_length=3)
    confidence: float = Field(ge=0.0, le=1.0)
    extractor: str

    status: FactStatus = FactStatus.CANDIDATE
    superseded_by: FactId | None = None

    @model_validator(mode="after")
    def _invariants(self) -> "Fact":
        """HAND-WRITTEN. Enforces Fact invariants and provenance integrity."""
        # 1. Namespace allow-list (must include 'fund' for fund.name identity facts)
        valid_namespaces = {"metrics", "terms", "narrative", "identity", "fund"}
        ns = self.field_path.split(".")[0]
        if ns not in valid_namespaces:
            raise ValueError(
                f"Unknown namespace '{ns}' in field_path '{self.field_path}'. "
                f"Allowed namespaces: {valid_namespaces}"
            )

        # 2. Exactly one of value_numeric or value_text is set (XOR)
        has_num = self.value_numeric is not None
        has_txt = self.value_text is not None
        if has_num == has_txt:
            raise ValueError(
                f"Fact '{self.field_path}' must have exactly one of value_numeric or value_text set (XOR)"
            )

        # 3. Unit validation against UNIT_BY_FIELD mapping
        # unit is NOT optional; it must match UNIT_BY_FIELD[self.field_path]
        expected_unit = UNIT_BY_FIELD.get(self.field_path)
        if expected_unit is not None and self.unit != expected_unit:
            raise ValueError(
                f"Unit mismatch for '{self.field_path}': expected {expected_unit}, got {self.unit}"
            )

        # 4. Text vs Numeric unit coupling:
        # unit is TEXT if and only if value_text is set
        is_text_unit = (str(self.unit).upper().endswith("TEXT") or self.unit == "TEXT")
        if is_text_unit != has_txt:
            raise ValueError(
                f"Fact '{self.field_path}': TEXT unit and value_text must travel together. "
                f"has_txt={has_txt}, unit={self.unit}"
            )

        if has_num:
            if not isinstance(self.value_numeric, int) or isinstance(self.value_numeric, bool):
                raise ValueError(f"Fact '{self.field_path}' value_numeric must be an integer (bps or cents)")

        # 5. Status / superseded_by coupling:
        # superseded_by is not None <==> status is FactStatus.SUPERSEDED
        is_superseded_status = (str(self.status).upper().endswith("SUPERSEDED"))
        has_superseded_by = (self.superseded_by is not None)
        if is_superseded_status != has_superseded_by:
            raise ValueError(
                f"Fact '{self.field_path}': superseded_by must be set if and only if status is SUPERSEDED"
            )

        # 6. Substantive quote
        if not self.quote or len(self.quote.strip()) <= 2:
            raise ValueError(f"Fact '{self.field_path}' quote must be substantive (at least 3 characters)")

        # 7. 1-indexed page
        if self.page_no < 1:
            raise ValueError(f"Fact '{self.field_path}' page_no must be >= 1, got {self.page_no}")

        # 8. Confidence probability
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"Fact '{self.field_path}' confidence must be between 0.0 and 1.0")

        # 9. Period format: YYYYQ[1-4] or YYYY-MM
        if self.period is not None:
            import re
            if not re.match(r"^(\d{4}Q[1-4]|\d{4}-(0[1-9]|1[0-2]))$", self.period):
                raise ValueError(f"Fact '{self.field_path}' has invalid period '{self.period}'")

        return self

class FundPeriodMetrics(BaseModel):
    """The materialized validated record. Every metric is fact-bound.

    Field naming is load-bearing: each value field `x` has a partner `x_fact_id`,
    and the validator below pairs them generically off model_fields rather than
    by hand. Eight hand-written pairs is exactly where the bug would live, and a
    generic check also means adding a metric cannot silently skip provenance.
    """

    model_config = ConfigDict(frozen=True)

    fund_id: FundId
    period: str

    gross_return_bps: int | None = None
    gross_return_bps_fact_id: FactId | None = None

    net_return_bps: int | None = None
    net_return_bps_fact_id: FactId | None = None

    ytd_return_bps: int | None = None
    ytd_return_bps_fact_id: FactId | None = None

    nav_usd_cents: int | None = None
    nav_usd_cents_fact_id: FactId | None = None

    sharpe_36m: int | None = None
    sharpe_36m_fact_id: FactId | None = None

    max_drawdown_bps: int | None = None
    max_drawdown_bps_fact_id: FactId | None = None

    @model_validator(mode="after")
    def _every_value_is_fact_bound(self) -> "FundPeriodMetrics":
        # Dynamically discover all metric fields that have a corresponding *_fact_id companion
        all_fields = set(self.model_fields.keys())
        paired_metrics = {f for f in all_fields if f"{f}_fact_id" in all_fields}

        for metric in paired_metrics:
            fact_id_field = f"{metric}_fact_id"
            val = getattr(self, metric)
            fid = getattr(self, fact_id_field)

            if (val is not None and fid is None) or (val is None and fid is not None):
                raise ValueError(
                    f"Provenance violation for '{metric}': value is {val} but {fact_id_field} is {fid}. "
                    f"Both must be set or neither."
                )
        return self

    def bound_fact_ids(self) -> list[FactId]:
        """Provenance set for this record, in declaration order."""
        return [
            fact_id
            for name in type(self).model_fields
            if name.endswith("_fact_id") and (fact_id := getattr(self, name)) is not None
        ]


class Terms(BaseModel):
    """Effective-dated economics.

    Fees are not columns on fund. A Q2 memo computes with the terms in force
    during Q2, and a fee change is itself a drift event. effective_to is None
    for the currently open row.
    """

    model_config = ConfigDict(frozen=True)

    terms_id: TermsId
    fund_id: FundId

    mgmt_fee_bps: int = Field(ge=0, le=10_000)
    perf_fee_bps: int = Field(ge=0, le=10_000)
    hurdle_bps: int = Field(ge=0, le=10_000)
    high_water_mark: bool
    lockup_months: int = Field(ge=0)
    notice_days: int = Field(ge=0)

    effective_from: date
    effective_to: date | None = None
    source_fact_ids: tuple[FactId, ...] = ()

    @model_validator(mode="after")
    def _range_is_ordered(self) -> Terms:
        if self.effective_to is not None and self.effective_to <= self.effective_from:
            raise ValueError(
                f"terms {self.terms_id}: effective_to {self.effective_to} "
                f"must be after effective_from {self.effective_from}"
            )
        return self

    def covers(self, day: date) -> bool:
        """Half-open interval: [effective_from, effective_to)."""
        if day < self.effective_from:
            return False
        return self.effective_to is None or day < self.effective_to
