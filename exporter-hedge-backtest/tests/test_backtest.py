"""Testes do backtest histórico: forward mensal, câmbio efetivo e resumo."""

import pandas as pd
import pytest

from src.backtest import (
    backtest_exporter,
    effective_rates,
    forward_rate_monthly,
    summarize,
)
from src.data import load_monthly_data


@pytest.fixture()
def panel() -> pd.DataFrame:
    """Painel sintético de 4 meses com taxas constantes."""
    months = pd.PeriodIndex(["2024-01", "2024-02", "2024-03", "2024-04"], freq="M")
    return pd.DataFrame(
        {"ptax": [5.00, 5.10, 4.90, 5.20], "cdi_aa": 0.12, "us_aa": 0.04},
        index=months,
    )


def test_forward_premium_positive_when_cdi_above_us():
    # Com CDI acima da taxa americana o forward negocia acima do spot.
    f = forward_rate_monthly(5.0, r_dom=0.12, r_for=0.04, months=12)
    assert f == pytest.approx(5.0 * 1.12 / 1.04)
    assert f > 5.0


def test_forward_zero_months_equals_spot():
    assert forward_rate_monthly(5.0, 0.12, 0.04, 0) == 5.0


def test_forward_rejects_bad_inputs():
    with pytest.raises(ValueError):
        forward_rate_monthly(-1.0, 0.12, 0.04, 1)
    with pytest.raises(ValueError):
        forward_rate_monthly(5.0, 0.12, 0.04, -1)


def test_zero_hedge_is_spot(panel):
    rates = effective_rates(panel, lock_months=0, start="2024-02", end="2024-04")
    pd.testing.assert_series_equal(
        rates, panel.loc["2024-02":"2024-04", "ptax"],
        check_names=False,
    )


def test_one_month_lock_uses_prior_month_forward(panel):
    rates = effective_rates(panel, lock_months=1, start="2024-02", end="2024-02")
    expected = forward_rate_monthly(5.00, 0.12, 0.04, 1)  # trava em 2024-01
    assert rates.loc[pd.Period("2024-02", "M")] == pytest.approx(expected)


def test_missing_lock_data_raises(panel):
    with pytest.raises(ValueError, match="trava"):
        effective_rates(panel, lock_months=6, start="2024-04", end="2024-04")


def test_backtest_and_summary_shapes(panel):
    schedules = {"Zero hedge": 0, "Trava 1 mês": 1}
    revenue = backtest_exporter(panel, 1_000_000, schedules, "2024-02", "2024-04")
    assert revenue.shape == (3, 2)

    stats = summarize(revenue, baseline="Zero hedge")
    assert stats.loc["Zero hedge", "vs_baseline"] == 0.0
    assert stats.loc["Zero hedge", "total"] == pytest.approx(
        (5.10 + 4.90 + 5.20) * 1_000_000
    )
    # Taxas constantes e prazo fixo: a trava embute sempre o mesmo prêmio
    # sobre o spot do mês anterior.
    premium = (1.12 / 1.04) ** (1 / 12)
    assert stats.loc["Trava 1 mês", "total"] == pytest.approx(
        (5.00 + 5.10 + 4.90) * premium * 1_000_000
    )


def test_bundled_dataset_covers_backtest_window():
    data = load_monthly_data()
    # Janela do estudo (jan/2021 a dez/2025) mais 12 meses de antecedência
    # para a trava de 1 ano.
    needed = pd.period_range("2020-01", "2025-12", freq="M")
    assert len(needed.difference(data.index)) == 0
    assert (data["ptax"] > 0).all()
    assert data["cdi_aa"].between(0, 0.20).all()
    assert data["us_aa"].between(0, 0.07).all()
