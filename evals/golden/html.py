from __future__ import annotations


def _css() -> str:
    return """
      :root { --ink: #1b2430; --muted: #5c6b7a; --rule: #d5dbe3; --accent: #1f4e79; }
      body { font-family: "Iowan Old Style", "Palatino Linotype", Palatino, serif;
             color: var(--ink); margin: 0; background: #eef1f4; }
      .page { background: white; max-width: 720px; margin: 24px auto; padding: 48px 56px;
              border: 1px solid var(--rule); box-shadow: 0 1px 2px rgba(0,0,0,.04); }
      h1 { font-size: 22px; letter-spacing: .02em; margin: 0 0 4px; color: var(--accent); }
      h2 { font-size: 13px; text-transform: uppercase; letter-spacing: .14em;
           color: var(--muted); margin: 28px 0 10px; }
      .kicker { font-size: 12px; letter-spacing: .16em; text-transform: uppercase;
                color: var(--muted); }
      .meta { font-size: 13px; color: var(--muted); margin: 0 0 24px; }
      table { width: 100%; border-collapse: collapse; font-size: 14px; }
      th, td { text-align: left; padding: 6px 0; border-bottom: 1px solid var(--rule); }
      td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
      p { font-size: 14px; line-height: 1.55; }
    """


def wrap(title: str, body: str) -> str:
    return (
        "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
        f"<meta charset=\"utf-8\"/>\n<title>{title}</title>\n"
        f"<style>{_css()}</style>\n</head>\n<body>\n{body}\n</body>\n</html>\n"
    )
