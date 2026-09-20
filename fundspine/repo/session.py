"""Tenant-context-required session factory.

There is no function here that returns a Session without a TenantContext. That
is the point: white-label means Partner A's rows must never be reachable while
serving Partner B, and the cheapest way to guarantee that is to make the unscoped
call impossible to write rather than merely discouraged.

Each session also sets the `app.tenant_id` GUC, which is the variable the row
level security policies read. RLS is not enabled in this build (see README), but
the seam it plugs into is here and exercised, not sketched.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from fundspine.config import settings
from fundspine.domain.ids import PartnerId

_engine: Engine | None = None
_factory: sessionmaker[Session] | None = None


@dataclass(frozen=True)
class TenantContext:
    """Who this unit of work is being performed on behalf of.

    partner_id is None only for INTERNAL work — ingestion, validation, drift,
    and the IC memo. Internal is a deliberate, named choice rather than the
    default you get by forgetting to pass anything.
    """

    partner_id: PartnerId | None
    label: str

    @classmethod
    def internal(cls) -> TenantContext:
        return cls(partner_id=None, label="internal")

    @classmethod
    def for_partner(cls, partner_id: PartnerId, slug: str) -> TenantContext:
        return cls(partner_id=partner_id, label=slug)

    @property
    def is_internal(self) -> bool:
        return self.partner_id is None

    @property
    def guc_value(self) -> str:
        return "internal" if self.partner_id is None else str(self.partner_id)


def engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(settings().database_url, future=True, pool_pre_ping=True)
    return _engine


def _session_factory() -> sessionmaker[Session]:
    global _factory
    if _factory is None:
        _factory = sessionmaker(bind=engine(), expire_on_commit=False, future=True)
    return _factory


@contextmanager
def session_scope(ctx: TenantContext) -> Iterator[Session]:
    """The only way to obtain a Session in this codebase.

    Commits on clean exit, rolls back on any exception. Does not swallow.
    """
    if not isinstance(ctx, TenantContext):
        raise TypeError("a session requires an explicit TenantContext")

    session = _session_factory()()
    try:
        session.execute(
            text("SELECT set_config('app.tenant_id', :tenant, true)"),
            {"tenant": ctx.guc_value},
        )
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
