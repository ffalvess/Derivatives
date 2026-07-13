"""Gráficos do projeto: distribuição de receita, MTM e P&L por hedge ratio.

Paleta e estilo seguem uma convenção única em todos os gráficos:
azul = com hedge, aqua = sem hedge, grade discreta, um único eixo y.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

# Paleta (validada para daltonismo: ΔE adjacente 73.6)
COLOR_HEDGED = "#2a78d6"  # azul — série protegida
COLOR_UNHEDGED = "#1baf7a"  # aqua — série exposta
COLOR_INK = "#0b0b0b"
COLOR_MUTED = "#898781"
COLOR_GRID = "#e1e0d9"
COLOR_SURFACE = "#fcfcfb"

# Ordem de categorias para gráficos com várias estratégias:
# exposta primeiro, depois travas do prazo mais curto ao mais longo.
BACKTEST_COLORS = [COLOR_UNHEDGED, "#8a68d9", "#d97b2a", COLOR_HEDGED]


def _base_ax(figsize=(9, 5)):
    fig, ax = plt.subplots(figsize=figsize, facecolor=COLOR_SURFACE)
    ax.set_facecolor(COLOR_SURFACE)
    ax.grid(axis="y", color=COLOR_GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(COLOR_GRID)
    ax.tick_params(colors=COLOR_MUTED, labelsize=9)
    return fig, ax


def _fmt_millions(ax, axis: str = "x") -> None:
    formatter = mticker.FuncFormatter(lambda v, _: f"{v / 1e6:.2f}")
    (ax.xaxis if axis == "x" else ax.yaxis).set_major_formatter(formatter)


def plot_revenue_distribution(
    revenue_unhedged: np.ndarray,
    revenue_hedged: np.ndarray,
    bins: int = 60,
    save_path: str | None = None,
):
    """Histograma comparando a receita em BRL com e sem hedge.

    O gráfico principal do projeto: a distribuição larga (sem hedge)
    contra a distribuição estreita (com hedge).
    """
    fig, ax = _base_ax()
    # Percentis 0,5–99,5 evitam que meia dúzia de outliers estique o eixo x.
    combined = np.concatenate([revenue_unhedged, revenue_hedged])
    lo, hi = np.percentile(combined, [0.5, 99.5])
    edges = np.linspace(lo, hi, bins + 1)

    ax.hist(revenue_unhedged, bins=edges, color=COLOR_UNHEDGED, alpha=0.75,
            label=f"Sem hedge (σ = R$ {np.std(revenue_unhedged) / 1e3:,.0f} mil)")
    ax.hist(revenue_hedged, bins=edges, color=COLOR_HEDGED, alpha=0.75,
            label=f"Com hedge (σ = R$ {np.std(revenue_hedged) / 1e3:,.0f} mil)")

    ax.set_title("Receita da exportadora: com hedge vs sem hedge",
                 color=COLOR_INK, fontsize=13, loc="left", pad=12)
    ax.set_xlabel("Receita em 90 dias (R$ milhões)", color=COLOR_MUTED)
    ax.set_ylabel("Nº de cenários", color=COLOR_MUTED)
    _fmt_millions(ax, "x")
    ax.legend(frameon=False, labelcolor=COLOR_INK, fontsize=10)
    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, facecolor=COLOR_SURFACE)
    return fig, ax


def plot_forward_mtm(
    mtm_paths: np.ndarray,
    n_show: int = 40,
    save_path: str | None = None,
):
    """Evolução do MTM do forward ao longo da vida do contrato.

    Mostra uma amostra de trajetórias em cinza e destaca a mediana:
    o contrato nasce com valor zero e diverge conforme o câmbio se move.

    Args:
        mtm_paths: array (n_sims, days + 1) com o MTM diário de cada cenário.
        n_show: quantas trajetórias individuais exibir ao fundo.
    """
    fig, ax = _base_ax()
    days = np.arange(mtm_paths.shape[1])

    for row in mtm_paths[:n_show]:
        ax.plot(days, row, color=COLOR_MUTED, linewidth=0.6, alpha=0.35)
    median = np.median(mtm_paths, axis=0)
    p5, p95 = np.percentile(mtm_paths, [5, 95], axis=0)
    ax.fill_between(days, p5, p95, color=COLOR_HEDGED, alpha=0.12,
                    label="Faixa P5–P95")
    ax.plot(days, median, color=COLOR_HEDGED, linewidth=2, label="Mediana")
    ax.axhline(0, color=COLOR_INK, linewidth=0.8, linestyle="--", alpha=0.5)

    ax.set_title("MTM do forward vendido ao longo do contrato",
                 color=COLOR_INK, fontsize=13, loc="left", pad=12)
    ax.set_xlabel("Dias úteis desde o fechamento", color=COLOR_MUTED)
    ax.set_ylabel("MTM (R$ milhões)", color=COLOR_MUTED)
    _fmt_millions(ax, "y")
    ax.legend(frameon=False, labelcolor=COLOR_INK, fontsize=10)
    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, facecolor=COLOR_SURFACE)
    return fig, ax


def plot_backtest_rates(revenue_rates, save_path: str | None = None):
    """Câmbio efetivo mês a mês de cada programa de hedge no backtest.

    Args:
        revenue_rates: DataFrame (mês x estratégia) com o câmbio efetivo
            em BRL/USD de cada recebimento. A primeira coluna deve ser a
            estratégia sem hedge (vira a referência visual).
    """
    fig, ax = _base_ax(figsize=(10, 5))
    x = revenue_rates.index.to_timestamp()
    for color, column in zip(BACKTEST_COLORS, revenue_rates.columns):
        is_baseline = column == revenue_rates.columns[0]
        ax.plot(x, revenue_rates[column], color=color,
                linewidth=1.4 if is_baseline else 1.8,
                linestyle="--" if is_baseline else "-",
                label=column, alpha=0.9)

    ax.set_title("Câmbio efetivo de cada recebimento, por programa de hedge",
                 color=COLOR_INK, fontsize=13, loc="left", pad=12)
    ax.set_ylabel("BRL por USD", color=COLOR_MUTED)
    ax.legend(frameon=False, labelcolor=COLOR_INK, fontsize=9, ncols=2)
    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, facecolor=COLOR_SURFACE)
    return fig, ax


def plot_backtest_cumulative(revenue, baseline: str,
                             save_path: str | None = None):
    """Receita acumulada de cada estratégia em relação ao zero hedge.

    A linha de cada trava mostra quantos reais a mais (ou a menos) o
    programa acumulou até aquele mês frente a converter tudo no spot.

    Args:
        revenue: DataFrame (mês x estratégia) com a receita mensal em BRL.
        baseline: nome da coluna de referência (ex.: "Zero hedge").
    """
    fig, ax = _base_ax(figsize=(10, 5))
    x = revenue.index.to_timestamp()
    excess = revenue.cumsum().sub(revenue[baseline].cumsum(), axis=0)
    for color, column in zip(BACKTEST_COLORS, revenue.columns):
        if column == baseline:
            continue
        ax.plot(x, excess[column], color=color, linewidth=1.8, label=column)
    ax.axhline(0, color=COLOR_INK, linewidth=0.8, linestyle="--", alpha=0.5)

    ax.set_title(f"Receita acumulada vs. {baseline.lower()}",
                 color=COLOR_INK, fontsize=13, loc="left", pad=12)
    ax.set_ylabel("Diferença acumulada (R$ milhões)", color=COLOR_MUTED)
    _fmt_millions(ax, "y")
    ax.legend(frameon=False, labelcolor=COLOR_INK, fontsize=9)
    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, facecolor=COLOR_SURFACE)
    return fig, ax


def plot_pnl_by_hedge_ratio(
    hedge_ratios: np.ndarray,
    revenues_by_ratio: np.ndarray,
    save_path: str | None = None,
):
    """Receita esperada e incerteza (P5–P95) em função do hedge ratio.

    Conforme o hedge ratio sobe de 0% a 100%, a faixa de incerteza
    colapsa sobre a média — o trade-off central do projeto.

    Args:
        hedge_ratios: array (n_ratios,) com os ratios testados (0 a 1).
        revenues_by_ratio: array (n_ratios, n_sims) com a receita simulada
            para cada ratio.
    """
    fig, ax = _base_ax()
    mean = revenues_by_ratio.mean(axis=1)
    p5, p95 = np.percentile(revenues_by_ratio, [5, 95], axis=1)

    ax.fill_between(hedge_ratios * 100, p5, p95, color=COLOR_UNHEDGED,
                    alpha=0.18, label="Faixa P5–P95")
    ax.plot(hedge_ratios * 100, mean, color=COLOR_HEDGED, linewidth=2,
            label="Receita média")

    ax.set_title("Quanto mais hedge, menos incerteza na receita",
                 color=COLOR_INK, fontsize=13, loc="left", pad=12)
    ax.set_xlabel("Hedge ratio (%)", color=COLOR_MUTED)
    ax.set_ylabel("Receita em 90 dias (R$ milhões)", color=COLOR_MUTED)
    _fmt_millions(ax, "y")
    ax.legend(frameon=False, labelcolor=COLOR_INK, fontsize=10, loc="lower left")
    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, facecolor=COLOR_SURFACE)
    return fig, ax
