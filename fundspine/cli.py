from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> None:
    args = sys.argv[1:] if argv is None else argv
    if not args:
        raise SystemExit("usage: python -m fundspine.cli <ingest|render|drift|costs>")
    command = args[0]
    if command == "render":
        from fundspine.render.run import render_all

        render_all()
        return
    if command == "ingest":
        from fundspine.ingest.run import ingest_golden

        ingest_golden()
        return
    if command == "drift":
        from fundspine.drift.router import blocking, route
        from fundspine.drift.rules import D101_restatement, D103_terms_change
        from fundspine.render.from_golden import facts_from_golden
        from fundspine.telemetry import tracer

        prior = facts_from_golden("doc_1")
        incoming = facts_from_golden("doc_3")
        with tracer().start_as_current_span("drift.evaluate"):
            findings = D101_restatement(prior, incoming) + D103_terms_change(prior, incoming)
        for item in findings:
            print(
                f"{item.rule_id}\t{item.field_path.value}\t{item.period}\t"
                f"{item.prior_value}->{item.new_value}\t{route(item).value}"
            )
        print(f"{len(blocking(findings))} blocking event(s)")
        return
    if command == "costs":
        from fundspine.costs_report import print_costs

        print_costs()
        return
    raise SystemExit(f"unknown command: {command}")


if __name__ == "__main__":
    main()
