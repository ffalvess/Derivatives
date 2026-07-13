"""Dados de mercado para o backtest: USD/BRL (PTAX), CDI e Treasury.

Duas fontes, na ordem:

1. `fetch_bcb_monthly` — busca as séries oficiais na API SGS do Banco
   Central (requer internet). PTAX venda é a série 1; o CDI anualizado
   base 252 é a série 4389.
2. `load_monthly_data` — lê o CSV versionado em `data/usdbrl_monthly.csv`,
   com fechamentos mensais aproximados de dez/2019 a dez/2025 compilados
   manualmente (PTAX, CDI e Treasury de 1 ano). É a fonte usada quando não
   há rede; os valores têm precisão de centavos no câmbio e de ~10 bps nas
   taxas, suficiente para comparar estratégias, não para marcar carteira.
"""

from __future__ import annotations

import io
import json
import urllib.request
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MONTHLY_CSV = DATA_DIR / "usdbrl_monthly.csv"

SGS_PTAX_VENDA = 1  # USD/BRL PTAX venda, diária
SGS_CDI_ANUAL = 4389  # CDI anualizado base 252, % a.a., diária


def load_monthly_data(path: Path | str = MONTHLY_CSV) -> pd.DataFrame:
    """Carrega o painel mensal versionado no repositório.

    Returns:
        DataFrame indexado por mês (PeriodIndex) com colunas:
        `ptax` (BRL/USD, fechamento do mês), `cdi_aa` e `us_aa`
        (taxas anuais em decimal, vigentes no fim do mês).
    """
    df = pd.read_csv(path)
    df["month"] = pd.PeriodIndex(df["month"], freq="M")
    return df.set_index("month").sort_index()


def _sgs_url(series_id: int, start: str, end: str) -> str:
    return (
        f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{series_id}/dados"
        f"?formato=json&dataInicial={start}&dataFinal={end}"
    )


def fetch_bcb_series(series_id: int, start: str, end: str) -> pd.Series:
    """Baixa uma série diária da API SGS do Banco Central.

    Args:
        series_id: código SGS (ex.: 1 = PTAX venda, 4389 = CDI a.a.).
        start, end: datas no formato dd/mm/aaaa.

    Returns:
        Série diária indexada por data.
    """
    with urllib.request.urlopen(_sgs_url(series_id, start, end), timeout=30) as resp:
        raw = json.load(io.TextIOWrapper(resp, encoding="utf-8"))
    s = pd.Series(
        [float(item["valor"]) for item in raw],
        index=pd.to_datetime([item["data"] for item in raw], format="%d/%m/%Y"),
    )
    return s.sort_index()


def fetch_bcb_monthly(start: str, end: str, us_aa: float = 0.04) -> pd.DataFrame:
    """Monta o painel mensal com dados oficiais do BCB (requer internet).

    PTAX e CDI vêm da API SGS; a taxa americana não é publicada pelo BCB,
    então entra como constante (`us_aa`) a menos que o chamador substitua
    a coluna depois com uma curva própria (ex.: FRED DGS1).

    Returns:
        DataFrame no mesmo formato de `load_monthly_data`.
    """
    ptax = fetch_bcb_series(SGS_PTAX_VENDA, start, end)
    cdi = fetch_bcb_series(SGS_CDI_ANUAL, start, end) / 100.0
    df = pd.DataFrame(
        {
            "ptax": ptax.groupby(ptax.index.to_period("M")).last(),
            "cdi_aa": cdi.groupby(cdi.index.to_period("M")).last(),
        }
    )
    df["us_aa"] = us_aa
    df.index.name = "month"
    return df.dropna()
