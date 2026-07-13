"""Backtest histórico de programas de hedge para uma exportadora.

Caso de uso: a empresa exporta um valor fixo em USD todos os meses e
precisa decidir a política de proteção. Cada estratégia é um programa
rolante — todo mês a empresa trava (ou não) a receita que vai chegar
`lock_months` à frente:

* zero hedge      — converte cada recebimento ao câmbio do mês.
* trava de k meses — k meses antes do recebimento, vende USD a termo ao
  forward calculado por paridade coberta de juros com o CDI e a taxa
  americana vigentes na data da trava.

A granularidade é mensal: usamos o fechamento de cada mês como proxy da
data de trava e de liquidação, e t = k/12 na capitalização (equivalente
à convenção DU/252 quando o prazo é medido em meses cheios).
"""

from __future__ import annotations

import pandas as pd

ZERO_HEDGE = 0  # lock de 0 meses = converter no spot do recebimento


def forward_rate_monthly(
    spot: float, r_dom: float, r_for: float, months: int
) -> float:
    """Forward por paridade coberta de juros com prazo em meses.

        F = S * ((1 + r_dom) / (1 + r_for)) ^ (months / 12)

    Args:
        spot: câmbio à vista na data da trava (BRL/USD).
        r_dom: taxa doméstica anual (CDI), capitalização composta.
        r_for: taxa estrangeira anual, mesma convenção.
        months: prazo do contrato em meses.

    Returns:
        Preço forward em BRL por USD.
    """
    if spot <= 0:
        raise ValueError("spot deve ser positivo")
    if months < 0:
        raise ValueError("months não pode ser negativo")
    t = months / 12.0
    return spot * ((1.0 + r_dom) / (1.0 + r_for)) ** t


def effective_rates(
    data: pd.DataFrame,
    lock_months: int,
    start: str,
    end: str,
) -> pd.Series:
    """Câmbio efetivo (BRL/USD) de cada recebimento sob um programa de trava.

    Para o recebimento do mês m, a trava acontece no mês m - lock_months,
    ao forward vigente naquela data. Com lock_months = 0 o resultado é o
    próprio spot de m (zero hedge).

    Args:
        data: painel mensal com colunas ptax, cdi_aa, us_aa
            (saída de data.load_monthly_data).
        lock_months: antecedência da trava, em meses (0 = sem hedge).
        start, end: primeiro e último mês de recebimento ("YYYY-MM").

    Returns:
        Série indexada pelo mês do recebimento com o câmbio efetivo.
    """
    receipts = pd.period_range(start, end, freq="M")
    missing = receipts.difference(data.index)
    if len(missing) > 0:
        raise ValueError(f"painel sem dados para os meses {list(missing)}")

    if lock_months == ZERO_HEDGE:
        return data.loc[receipts, "ptax"].rename("effective_rate")

    lock_dates = receipts - lock_months
    missing = lock_dates.difference(data.index)
    if len(missing) > 0:
        raise ValueError(
            f"painel sem dados para as datas de trava {list(missing)}"
        )
    locks = data.loc[lock_dates]
    rates = [
        forward_rate_monthly(row.ptax, row.cdi_aa, row.us_aa, lock_months)
        for row in locks.itertuples()
    ]
    return pd.Series(rates, index=receipts, name="effective_rate")


def backtest_exporter(
    data: pd.DataFrame,
    monthly_usd: float,
    lock_schedules: dict[str, int],
    start: str,
    end: str,
) -> pd.DataFrame:
    """Roda o backtest de vários programas de hedge lado a lado.

    Args:
        data: painel mensal (ptax, cdi_aa, us_aa).
        monthly_usd: exportação mensal em USD (ex.: 1_000_000).
        lock_schedules: nome da estratégia -> meses de antecedência,
            ex.: {"Zero hedge": 0, "Trava 1m": 1, "Trava 6m": 6}.
        start, end: janela de recebimentos ("YYYY-MM").

    Returns:
        DataFrame (mês do recebimento x estratégia) com a receita em BRL
        de cada mês.
    """
    revenue = {
        name: effective_rates(data, months, start, end) * monthly_usd
        for name, months in lock_schedules.items()
    }
    return pd.DataFrame(revenue)


def summarize(revenue: pd.DataFrame, baseline: str | None = None) -> pd.DataFrame:
    """Resume o backtest: total, média, volatilidade e extremos por estratégia.

    Args:
        revenue: saída de backtest_exporter (receita mensal em BRL).
        baseline: nome da coluna usada como referência para a coluna
            "vs. baseline" (ex.: "Zero hedge"). None omite a comparação.

    Returns:
        DataFrame indexado por estratégia com as métricas em BRL:
        total no período, média mensal, desvio-padrão mensal, pior e
        melhor mês e, se houver baseline, a diferença de total.
    """
    stats = pd.DataFrame(
        {
            "total": revenue.sum(),
            "media_mensal": revenue.mean(),
            "desvio_padrao": revenue.std(),
            "pior_mes": revenue.min(),
            "melhor_mes": revenue.max(),
        }
    )
    if baseline is not None:
        stats["vs_baseline"] = stats["total"] - stats.loc[baseline, "total"]
    return stats
