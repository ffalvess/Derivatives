"""Gráficos do backtest: câmbio efetivo por programa e receita acumulada.

Mesma convenção visual do projeto fx-forward-hedge: aqua = série exposta,
azul = série protegida, grade discreta, um único eixo y.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

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


def _base_ax(figsize=(10, 5)):
    fig, ax = plt.subplots(figsize=figsize, facecolor=COLOR_SURFACE)
    ax.set_facecolor(COLOR_SURFACE)
    ax.grid(axis="y", color=COLOR_GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(COLOR_GRID)
    ax.tick_params(colors=COLOR_MUTED, labelsize=9)
    return fig, ax


def _fmt_millions(ax) -> None:
    formatter = mticker.FuncFormatter(lambda v, _: f"{v / 1e6:.2f}")
    ax.yaxis.set_major_formatter(formatter)


def plot_backtest_rates(revenue_rates, save_path: str | None = None):
    """Câmbio efetivo mês a mês de cada programa de hedge no backtest.

    Args:
        revenue_rates: DataFrame (mês x estratégia) com o câmbio efetivo
            em BRL/USD de cada recebimento. A primeira coluna deve ser a
            estratégia sem hedge (vira a referência visual).
    """
    fig, ax = _base_ax()
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
    fig, ax = _base_ax()
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
    _fmt_millions(ax)
    ax.legend(frameon=False, labelcolor=COLOR_INK, fontsize=9)
    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, facecolor=COLOR_SURFACE)
    return fig, ax
