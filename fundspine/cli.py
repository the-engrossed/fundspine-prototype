from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> None:
    args = sys.argv[1:] if argv is None else argv
    if not args:
        raise SystemExit("usage: python -m fundspine.cli <ingest|render|drift|costs>")
    command = args[0]
    if command == "ingest":
        from fundspine.ingest.run import ingest_golden

        ingest_golden()
        return
    if command in {"render", "drift", "costs"}:
        raise NotImplementedError(f"{command} is not built yet")
    raise SystemExit(f"unknown command: {command}")


if __name__ == "__main__":
    main()
