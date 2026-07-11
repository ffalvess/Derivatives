"""Simulação de câmbio e P&L de hedge para uma exportadora.

Caso de uso: a empresa recebe `notional` USD em `days` dias úteis e quer
saber como fica a distribuição da receita em BRL com e sem forward.
Referência teórica: Hull, caps. 3 e 6 (estratégias de hedge).
"""

from __future__ import annotations

import numpy as np

from .pricing import BASE_252, forward_price


def simulate_spot_paths(
    spot: float,
    vol: float,
    days: int,
    n_sims: int,
    drift: float = 0.0,
    seed: int | None = None,
) -> np.ndarray:
    """Simula trajetórias do câmbio via movimento browniano geométrico.

        S_{t+1} = S_t * exp((mu - vol^2/2) * dt + vol * sqrt(dt) * Z)

    Args:
        spot: câmbio inicial (BRL/USD).
        vol: volatilidade anualizada (ex.: 0.15 = 15% a.a.).
        days: horizonte em dias úteis.
        n_sims: número de trajetórias.
        drift: tendência anualizada do câmbio (0 = martingale, conservador).
            Sob a medida neutra ao risco seria r_dom - r_for.
        seed: semente para reprodutibilidade.

    Returns:
        Array (n_sims, days + 1); a coluna 0 é o spot inicial.
    """
    if days <= 0 or n_sims <= 0:
        raise ValueError("days e n_sims devem ser positivos")
    rng = np.random.default_rng(seed)
    dt = 1.0 / BASE_252
    z = rng.standard_normal((n_sims, days))
    log_returns = (drift - 0.5 * vol**2) * dt + vol * np.sqrt(dt) * z
    paths = np.empty((n_sims, days + 1))
    paths[:, 0] = spot
    paths[:, 1:] = spot * np.exp(np.cumsum(log_returns, axis=1))
    return paths


def pnl_unhedged(paths: np.ndarray, notional: float) -> np.ndarray:
    """Receita em BRL sem proteção: converte o notional ao câmbio final.

    Returns:
        Array (n_sims,) com a receita em BRL de cada cenário.
    """
    return paths[:, -1] * notional


def pnl_hedged(
    paths: np.ndarray,
    notional: float,
    F_contratado: float,
    hedge_ratio: float = 1.0,
) -> np.ndarray:
    """Receita em BRL com hedge (parcial ou total) via forward.

    A fração protegida é convertida ao preço travado F_contratado; o
    restante fica exposto ao câmbio de mercado no vencimento:

        receita = h * N * F + (1 - h) * N * S_T

    Args:
        paths: trajetórias simuladas do câmbio (saída de simulate_spot_paths).
        notional: recebível em USD.
        F_contratado: preço forward travado (BRL/USD).
        hedge_ratio: fração protegida, entre 0 e 1 (ex.: 0.5, 0.8, 1.0).

    Returns:
        Array (n_sims,) com a receita em BRL de cada cenário.
    """
    if not 0.0 <= hedge_ratio <= 1.0:
        raise ValueError("hedge_ratio deve estar entre 0 e 1")
    s_T = paths[:, -1]
    hedged_leg = hedge_ratio * notional * F_contratado
    open_leg = (1.0 - hedge_ratio) * notional * s_T
    return hedged_leg + open_leg


def layered_hedge(
    paths: np.ndarray,
    notional: float,
    schedule: list[tuple[int, float]],
    r_dom: float,
    r_for: float,
) -> np.ndarray:
    """Hedge em camadas: trava frações da exposição em datas diferentes.

    Prática comum de tesouraria: em vez de travar 100% no dia zero, a
    empresa trava, por exemplo, 1/3 da exposição a cada mês. Cada camada
    é travada ao preço forward vigente na data da trava (calculado sobre
    o spot simulado daquele dia, para o prazo remanescente).

    Args:
        paths: trajetórias simuladas do câmbio (n_sims, days + 1).
        notional: recebível total em USD.
        schedule: lista de (dia_da_trava, fração), ex.:
            [(0, 1/3), (21, 1/3), (42, 1/3)]. As frações devem somar <= 1;
            o que não for travado fica exposto ao spot final.
        r_dom: taxa doméstica anual (base 252) para precificar cada camada.
        r_for: taxa estrangeira anual.

    Returns:
        Array (n_sims,) com a receita em BRL de cada cenário.
    """
    maturity = paths.shape[1] - 1
    total_fraction = sum(f for _, f in schedule)
    if total_fraction > 1.0 + 1e-9:
        raise ValueError("as frações do schedule não podem somar mais que 1")

    revenue = np.zeros(paths.shape[0])
    for lock_day, fraction in schedule:
        if not 0 <= lock_day <= maturity:
            raise ValueError(f"dia de trava {lock_day} fora do horizonte")
        days_remaining = maturity - lock_day
        spot_at_lock = paths[:, lock_day]
        f_locked = forward_price(1.0, r_dom, r_for, days_remaining) * spot_at_lock
        revenue += fraction * notional * f_locked

    open_fraction = 1.0 - total_fraction
    revenue += open_fraction * notional * paths[:, -1]
    return revenue


def hedge_effectiveness(pnl_no_hedge: np.ndarray, pnl_with_hedge: np.ndarray) -> float:
    """Redução percentual da volatilidade da receita trazida pelo hedge.

    Returns:
        Ex.: 0.97 significa que o hedge eliminou 97% do desvio-padrão.
    """
    std_before = float(np.std(pnl_no_hedge))
    if std_before == 0.0:
        return 0.0
    return 1.0 - float(np.std(pnl_with_hedge)) / std_before
