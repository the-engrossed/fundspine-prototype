"""Typed identifiers.

Bare str or UUID crossing a layer boundary is how a partner_id ends up where a
fund_id belongs. NewType costs nothing at runtime and mypy catches the swap.
"""

from typing import NewType
from uuid import UUID, uuid4

FundId = NewType("FundId", UUID)
DocumentId = NewType("DocumentId", UUID)
ExtractionRunId = NewType("ExtractionRunId", UUID)
FactId = NewType("FactId", UUID)
TermsId = NewType("TermsId", UUID)
PartnerId = NewType("PartnerId", UUID)
DriftEventId = NewType("DriftEventId", UUID)
ArtifactId = NewType("ArtifactId", UUID)


def new_fund_id() -> FundId:
    return FundId(uuid4())


def new_document_id() -> DocumentId:
    return DocumentId(uuid4())


def new_extraction_run_id() -> ExtractionRunId:
    return ExtractionRunId(uuid4())


def new_fact_id() -> FactId:
    return FactId(uuid4())


def new_terms_id() -> TermsId:
    return TermsId(uuid4())


def new_partner_id() -> PartnerId:
    return PartnerId(uuid4())


def new_drift_event_id() -> DriftEventId:
    return DriftEventId(uuid4())


def new_artifact_id() -> ArtifactId:
    return ArtifactId(uuid4())
