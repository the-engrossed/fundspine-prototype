"""OpenTelemetry file exporter. No Jaeger. Spans land in traces/spans.jsonl."""

from __future__ import annotations

import json
from collections.abc import Sequence

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult

from fundspine.config import settings

_provider: TracerProvider | None = None


class JsonlSpanExporter(SpanExporter):
    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        dest = settings().trace_dir
        dest.mkdir(parents=True, exist_ok=True)
        path = dest / "spans.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            for span in spans:
                ctx = span.get_span_context()
                if ctx is None:
                    continue
                handle.write(
                    json.dumps(
                        {
                            "name": span.name,
                            "trace_id": f"{ctx.trace_id:032x}",
                            "span_id": f"{ctx.span_id:016x}",
                            "attributes": dict(span.attributes or {}),
                        }
                    )
                    + "\n"
                )
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        return None

    def force_flush(self, timeout_millis: int = 30_000) -> bool:
        return True


def _ensure() -> None:
    global _provider
    if _provider is not None:
        return
    provider = TracerProvider(resource=Resource.create({"service.name": "fundspine"}))
    provider.add_span_processor(SimpleSpanProcessor(JsonlSpanExporter()))
    trace.set_tracer_provider(provider)
    _provider = provider


def tracer() -> trace.Tracer:
    _ensure()
    return trace.get_tracer("fundspine")
