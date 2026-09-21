from fundspine.costs import cost_micros, format_usd, mean_micros, render_costs_table


def test_cost_micros_uses_published_rates() -> None:
    # 1M in + 1M out → $2.50 + $10.00 = $12.50
    assert cost_micros(1_000_000, 1_000_000) == 12_500_000
    assert format_usd(12_500_000) == "$12.500000"


def test_mean_and_table_state_assumptions() -> None:
    mean = mean_micros((100, 200, 300))
    assert mean == 200
    table = render_costs_table(
        rows=(("golden://doc_1", 1000, 1000, cost_micros(1000, 1000)),),
        mean_document_micros=mean,
    )
    assert "funds on platform: 40" in table
    assert "documents per fund per year: 4" in table
    assert "partners receiving commentary: 7" in table
    assert "$" in table
