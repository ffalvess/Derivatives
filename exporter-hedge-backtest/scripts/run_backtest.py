"""Roda o backtest da exportadora e gera os gráficos em assets/.

Uso:
    python scripts/run_backtest.py

Cenário: exportação de USD 1 milhão por mês, recebimentos de jan/2021 a
dez/2025 (60 meses), comparando zero hedge com travas de 1, 6 e 12 meses.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.backtest import backtest_exporter, summarize
from src.data import load_monthly_data
from src.plots import plot_backtest_cumulative, plot_backtest_rates

MONTHLY_USD = 1_000_000
START, END = "2021-01", "2025-12"
BASELINE = "Zero hedge"
SCHEDULES = {
    BASELINE: 0,
    "Trava 1 mês": 1,
    "Trava 6 meses": 6,
    "Trava 1 ano": 12,
}


def main() -> None:
    data = load_monthly_data()
    revenue = backtest_exporter(data, MONTHLY_USD, SCHEDULES, START, END)
    rates = revenue / MONTHLY_USD

    stats = summarize(revenue, baseline=BASELINE)
    def fmt(v: float) -> str:
        return f"R$ {v / 1e6:,.2f} mi"
    print(f"\nBacktest {START} a {END} — USD {MONTHLY_USD:,.0f}/mês\n")
    header = f"{'Estratégia':<16}{'Total':>16}{'Média/mês':>14}{'σ mensal':>12}{'Pior mês':>13}{'vs. zero':>16}"
    print(header)
    print("-" * len(header))
    for name, row in stats.iterrows():
        print(
            f"{name:<16}{fmt(row.total):>16}{fmt(row.media_mensal):>14}"
            f"{fmt(row.desvio_padrao):>12}{fmt(row.pior_mes):>13}{fmt(row.vs_baseline):>16}"
        )

    assets = ROOT / "assets"
    plot_backtest_rates(rates, save_path=str(assets / "backtest_effective_rates.png"))
    plot_backtest_cumulative(
        revenue, baseline=BASELINE,
        save_path=str(assets / "backtest_cumulative_vs_spot.png"),
    )
    print(f"\nGráficos salvos em {assets}/backtest_*.png")


if __name__ == "__main__":
    main()
