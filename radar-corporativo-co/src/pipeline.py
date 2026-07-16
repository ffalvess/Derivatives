"""Orquestração: coleta -> filtro -> dedup -> render.

Falha em uma fonte não derruba a edição: o erro vai para o rodapé
"fontes indisponíveis" e o restante segue.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

from .config import RAIZ_PROJETO, Config
from .dedup import (carregar_vistos, filtrar_novos, registrar_e_podar,
                    salvar_vistos)
from .fetchers.http import criar_sessao
from .fetchers.pncp import buscar_pncp
from .fetchers.querido_diario import buscar_querido_diario
from .fetchers.rss import buscar_rss
from .filtro import Filtro
from .models import Item
from .render import montar_edicao, renderizar

CAMINHO_VISTOS_PADRAO = RAIZ_PROJETO / "data" / "vistos.json"
FONTES_VALIDAS = ("rss", "pncp", "qd")


def _log(mensagem: str) -> None:
    print(mensagem, file=sys.stderr)


def coletar(cfg: Config, sessao, fontes: tuple[str, ...],
            inicio: date, fim: date) -> tuple[list[Item], list[str], int]:
    """Retorna (itens, nomes de fontes com erro, nº de fontes tentadas)."""
    itens: list[Item] = []
    com_erro: list[str] = []
    tentadas = 0

    if "rss" in fontes:
        for fonte in cfg.rss:
            tentadas += 1
            try:
                novos = buscar_rss(sessao, fonte, inicio, fim)
                _log(f"[rss] {fonte.nome}: {len(novos)} itens")
                itens.extend(novos)
            except Exception as exc:
                _log(f"[rss] {fonte.nome}: ERRO ({exc})")
                com_erro.append(fonte.nome)

    if "pncp" in fontes:
        tentadas += 1
        try:
            novos = buscar_pncp(sessao, cfg.pncp, cfg.estados, inicio, fim)
            _log(f"[pncp] {len(novos)} licitações")
            itens.extend(novos)
        except Exception as exc:
            _log(f"[pncp] ERRO ({exc})")
            com_erro.append("PNCP")

    if "qd" in fontes:
        tentadas += 1
        try:
            novos = buscar_querido_diario(sessao, cfg.querido_diario, inicio, fim)
            _log(f"[qd] {len(novos)} diários")
            itens.extend(novos)
        except Exception as exc:
            _log(f"[qd] ERRO ({exc})")
            com_erro.append("Querido Diário")

    return itens, com_erro, tentadas


def executar(cfg: Config, inicio: date, fim: date, *,
             fontes: tuple[str, ...] = FONTES_VALIDAS,
             usar_dedup: bool = True,
             incluir_licitacoes: bool = True,
             diretorio_saida: Path = RAIZ_PROJETO / "output",
             caminho_vistos: Path = CAMINHO_VISTOS_PADRAO,
             sessao=None) -> int:
    """Gera a edição. Retorna 0 se ela foi escrita, 1 se todas as fontes falharam."""
    sessao = sessao or criar_sessao()

    itens, com_erro, tentadas = coletar(cfg, sessao, fontes, inicio, fim)
    if tentadas > 0 and len(com_erro) >= tentadas:
        _log("Todas as fontes falharam; edição não gerada.")
        return 1

    itens = Filtro(cfg.filtro, cfg.cidades_uf).aplicar(itens)

    if usar_dedup:
        vistos = carregar_vistos(caminho_vistos)
        itens = filtrar_novos(itens, vistos)
        salvar_vistos(caminho_vistos, registrar_e_podar(vistos, itens, fim))

    edicao = montar_edicao(itens, cfg.estados, inicio, fim, fontes_com_erro=com_erro)
    gerados = renderizar(edicao, diretorio_saida, incluir_licitacoes=incluir_licitacoes)
    for caminho in gerados:
        print(caminho)
    return 0
