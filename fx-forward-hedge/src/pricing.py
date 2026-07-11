"""Precificação de forwards de câmbio (USD/BRL).

Implementa a paridade coberta de juros com as convenções brasileiras:
a taxa doméstica (CDI/pré) capitaliza em base 252 dias úteis.
Referência teórica: Hull, "Options, Futures and Other Derivatives", cap. 5.
"""

from __future__ import annotations

BASE_252 = 252  # dias úteis por ano (convenção brasileira para CDI)


def forward_price(spot: float, r_dom: float, r_for: float, days: int) -> float:
    """Preço justo do forward via paridade coberta de juros.

        F = S * (1 + r_dom)^(t) / (1 + r_for)^(t),  t = days / 252

    Intuição: comprar USD hoje e aplicar a juros americanos tem que
    render o mesmo que aplicar BRL no CDI e comprar USD a termo —
    caso contrário há arbitragem sem risco.

    Args:
        spot: câmbio à vista (BRL por USD).
        r_dom: taxa doméstica anual (ex.: CDI), capitalização composta base 252.
        r_for: taxa estrangeira anual (ex.: Treasury/SOFR), mesma convenção.
        days: prazo do contrato em dias úteis.

    Returns:
        Preço forward em BRL por USD.
    """
    if spot <= 0:
        raise ValueError("spot deve ser positivo")
    if days < 0:
        raise ValueError("days não pode ser negativo")
    t = days / BASE_252
    return spot * (1.0 + r_dom) ** t / (1.0 + r_for) ** t


def forward_mtm(
    F_contratado: float,
    F_atual: float,
    notional: float,
    r_dom: float,
    days_restantes: int,
    position: str = "long",
) -> float:
    """Marcação a mercado (MTM) de um forward ao longo da vida do contrato.

    O valor da posição é a diferença entre o forward vigente no mercado e o
    forward travado no contrato, aplicada ao notional e trazida a valor
    presente pela taxa doméstica:

        MTM_long = (F_atual - F_contratado) * notional / (1 + r_dom)^(t)

    Uma exportadora que *vende* USD a termo tem posição short: o MTM
    inverte de sinal (ela ganha quando o forward cai).

    Args:
        F_contratado: preço forward travado no início do contrato (BRL/USD).
        F_atual: preço forward de mercado para o mesmo vencimento (BRL/USD).
        notional: tamanho do contrato em USD.
        r_dom: taxa doméstica anual para desconto, base 252.
        days_restantes: dias úteis até o vencimento.
        position: "long" (comprado em USD) ou "short" (vendido em USD).

    Returns:
        Valor de mercado do contrato em BRL (positivo = a favor da posição).
    """
    if position not in ("long", "short"):
        raise ValueError("position deve ser 'long' ou 'short'")
    t = days_restantes / BASE_252
    mtm_long = (F_atual - F_contratado) * notional / (1.0 + r_dom) ** t
    return mtm_long if position == "long" else -mtm_long
